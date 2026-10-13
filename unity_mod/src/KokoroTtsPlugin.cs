using BepInEx.Configuration;
using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Threading;
using System.Runtime.InteropServices;
using BepInEx;
using UnityEngine;
using UnityEngine.UI;

namespace KokoroTts
{
    [BepInPlugin("com.kokoro.tts.unity", "Kokoro TTS Plugin", "1.3.0")]
    public class KokoroTtsPlugin : BaseUnityPlugin
    {
        [DllImport("user32.dll")]
        private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

        private const byte VK_SPACE = 0x20;
        private const uint KEYEVENTF_KEYUP = 0x0002;

        private TcpClient socket;
        private StreamWriter writer;
        private StreamReader reader;
        private Thread listenerThread;
        private bool isConnected = false;
        private bool autoForward = false;
        private bool shouldAutoAdvance = false;

        private ConfigEntry<string> serverHost;
        private ConfigEntry<int> serverPort;
        private ConfigEntry<string> defaultVoice;
        private ConfigEntry<float> debounceDelay;
        private ConfigEntry<float> scanInterval;
        private ConfigEntry<string> customIgnoreTerms;

        private float nextScanTime = 0f;

        // Buffer e temporizador para efeito Maquina de Escrever (Typewriter)
        private string candidateText = "";
        private float debounceTimer = 0f;
        private const float DEBOUNCE_DELAY = 0.35f;

        // Historico para evitar loops e duplicacao de falas recentes
        private Queue<string> recentHistory = new Queue<string>();
        private const int MAX_HISTORY = 15;

        private HashSet<string> ignoreExact = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "Save", "Load", "Options", "Back", "Quit", "Auto", "Skip", "Log", "Prefs", "Menu",
            "Yes", "No", "Cancel", "Ok", "Settings", "Relations", "Inventory", "Gallery", "Help"
        };

        private string[] ignoreContains = new string[]
        {
            "Choice Taken", "Path Choice", "Quest Complete", "Level Up", "Achievement"
        };

        private static Type _cachedTmpType = null;
        private static bool _tmpTypeSearched = false;

        private static Type GetTmpType()
        {
            if (!_tmpTypeSearched)
            {
                _tmpTypeSearched = true;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    var t = assembly.GetType("TMPro.TMP_Text") ?? assembly.GetType("TMPro.TextMeshProUGUI");
                    if (t != null)
                    {
                        _cachedTmpType = t;
                        break;
                    }
                }
            }
            return _cachedTmpType;
        }

        void Awake()
        {
            serverHost = Config.Bind("Connection", "Host", "127.0.0.1", "Endereço IP do servidor Kokoro TTS");
            serverPort = Config.Bind("Connection", "Port", 5050, "Porta TCP do servidor Kokoro TTS");
            defaultVoice = Config.Bind("Voice", "DefaultVoice", "af_heart", "Voz padrão do Kokoro TTS");
            debounceDelay = Config.Bind("Timing", "DebounceDelay", 0.35f, "Tempo de debounce (segundos) para máquina de escrever");
            scanInterval = Config.Bind("Timing", "ScanInterval", 0.2f, "Intervalo em segundos entre varreduras de cena (evita picos de CPU/GC)");
            customIgnoreTerms = Config.Bind("Dialogue", "IgnoredExactTerms", "", "Termos adicionais separados por vírgula para ignorar na leitura");

            if (customIgnoreTerms != null && !string.IsNullOrEmpty(customIgnoreTerms.Value))
            {
                foreach (var term in customIgnoreTerms.Value.Split(new char[] { ',' }, StringSplitOptions.RemoveEmptyEntries))
                {
                    string trimmed = term.Trim();
                    if (!string.IsNullOrEmpty(trimmed))
                    {
                        ignoreExact.Add(trimmed);
                    }
                }
            }

            Logger.LogInfo("Kokoro TTS Plugin v1.4.0 (Otimizado via BepInEx) Carregado.");
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.V))
            {
                ConnectToServer();
            }

            if (Input.GetKeyDown(KeyCode.A))
            {
                autoForward = !autoForward;
                Logger.LogInfo("TTS Modo Automático: " + (autoForward ? "LIGADO" : "DESLIGADO"));
            }

            // Auto-advance no Unity quando o audio do TTS terminar
            if (shouldAutoAdvance)
            {
                shouldAutoAdvance = false;
                if (autoForward)
                {
                    Logger.LogInfo("[TTS] Áudio finalizado. Simulando pulo de frase (Espaço)...");
                    SimulateSpacebar();
                }
            }

            if (!isConnected || socket == null || !socket.Connected)
                return;

            if (Time.time >= nextScanTime)
            {
                float interval = scanInterval != null ? scanInterval.Value : 0.2f;
                nextScanTime = Time.time + Mathf.Max(0.05f, interval);
                ScanSceneForDialogue();
            }

            ProcessDebounce();
        }

        private void SimulateSpacebar()
        {
            // Proteção contra simulação fora de foco (ex: jogador deu Alt+Tab)
            if (!Application.isFocused)
            {
                return;
            }

            // Proteção de plataforma para evitar crash em Linux/Mac/Steam Deck nativo
            if (Application.platform != RuntimePlatform.WindowsPlayer && Application.platform != RuntimePlatform.WindowsEditor)
            {
                return;
            }

            try
            {
                keybd_event(VK_SPACE, 0, 0, UIntPtr.Zero);
                keybd_event(VK_SPACE, 0, KEYEVENTF_KEYUP, UIntPtr.Zero);
            }
            catch (Exception ex)
            {
                Logger.LogError("Erro ao simular avanco via teclado: " + ex.Message);
            }
        }

        private void ScanSceneForDialogue()
        {
            string bestTextOnScreen = "";
            int bestLength = 0;

            // 1. Scan UI.Text com try/catch isolado por componente
            Text[] legacyTexts = FindObjectsOfType<Text>();
            foreach (var comp in legacyTexts)
            {
                try
                {
                    if (comp != null && comp.gameObject.activeInHierarchy && comp.enabled)
                    {
                        string cleaned = CleanRichText(comp.text);
                        if (IsValidDialogue(cleaned) && cleaned.Length > bestLength)
                        {
                            bestTextOnScreen = cleaned;
                            bestLength = cleaned.Length;
                        }
                    }
                }
                catch { }
            }

            // 2. Scan TextMeshPro focado pelo tipo (evita percorrer todos os 10k componentes da cena)
            try
            {
                Type tmpType = GetTmpType();
                if (tmpType != null)
                {
                    UnityEngine.Object[] tmpObjects = FindObjectsOfType(tmpType);
                    foreach (var obj in tmpObjects)
                    {
                        try
                        {
                            Component comp = obj as Component;
                            if (comp != null && comp.gameObject.activeInHierarchy)
                            {
                                var prop = comp.GetType().GetProperty("text");
                                if (prop != null)
                                {
                                    string val = prop.GetValue(comp, null) as string;
                                    string cleaned = CleanRichText(val);
                                    if (IsValidDialogue(cleaned) && cleaned.Length > bestLength)
                                    {
                                        bestTextOnScreen = cleaned;
                                        bestLength = cleaned.Length;
                                    }
                                }
                            }
                        }
                        catch { }
                    }
                }
            }
            catch { }

            if (!string.IsNullOrEmpty(bestTextOnScreen))
            {
                UpdateCandidateText(bestTextOnScreen);
            }
        }

        private string CleanRichText(string input)
        {
            if (string.IsNullOrEmpty(input)) return "";
            string text = Regex.Replace(input, @"<[^>]*>", "").Trim();
            text = Regex.Replace(text, @"\s+", " ");
            return text;
        }

        private bool IsValidDialogue(string text)
        {
            if (string.IsNullOrEmpty(text) || text.Length < 3) return false;
            if (ignoreExact.Contains(text)) return false;

            double numVal;
            if (double.TryParse(text, out numVal)) return false;

            foreach (var sub in ignoreContains)
            {
                if (text.IndexOf(sub, StringComparison.OrdinalIgnoreCase) >= 0)
                    return false;
            }

            return true;
        }

        private void UpdateCandidateText(string newText)
        {
            if (recentHistory.Contains(newText)) return;

            if (newText != candidateText)
            {
                candidateText = newText;
                debounceTimer = debounceDelay != null ? debounceDelay.Value : DEBOUNCE_DELAY;
            }
        }

        private void ProcessDebounce()
        {
            if (string.IsNullOrEmpty(candidateText)) return;

            if (debounceTimer > 0f)
            {
                debounceTimer -= Time.deltaTime;
                if (debounceTimer <= 0f)
                {
                    if (!recentHistory.Contains(candidateText))
                    {
                        SendTextToTTS(candidateText);
                        AddToHistory(candidateText);
                    }
                    candidateText = "";
                }
            }
        }

        private void AddToHistory(string text)
        {
            recentHistory.Enqueue(text);
            if (recentHistory.Count > MAX_HISTORY)
            {
                recentHistory.Dequeue();
            }
        }

        private void ConnectToServer()
        {
            try
            {
                DisconnectSocket();

                string host = serverHost != null ? serverHost.Value : "127.0.0.1";
                int port = serverPort != null ? serverPort.Value : 5050;

                socket = new TcpClient(host, port);
                NetworkStream stream = socket.GetStream();
                writer = new StreamWriter(stream, new UTF8Encoding(false));
                reader = new StreamReader(stream, new UTF8Encoding(false));
                isConnected = true;
                Logger.LogInfo($"--> Conectado com sucesso ao servidor Kokoro TTS em {host}:{port}!");

                if (defaultVoice != null && !string.IsNullOrEmpty(defaultVoice.Value))
                {
                    writer.WriteLine("SET_VOICE:" + defaultVoice.Value);
                    writer.Flush();
                }

                listenerThread = new Thread(ListenServerEvents);
                listenerThread.IsBackground = true;
                listenerThread.Start();
            }
            catch (Exception ex)
            {
                Logger.LogError("Falha ao conectar no servidor TTS: " + ex.Message);
                isConnected = false;
            }
        }

        private void ListenServerEvents()
        {
            try
            {
                while (isConnected && reader != null)
                {
                    string line = reader.ReadLine();
                    if (line == null) break;

                    if (line.Trim() == "PLAYBACK_DONE")
                    {
                        shouldAutoAdvance = true;
                    }
                }
            }
            catch
            {
                isConnected = false;
            }
        }

        private void SendTextToTTS(string text)
        {
            try
            {
                if (writer != null && socket != null && socket.Connected)
                {
                    writer.WriteLine("STOP");
                    writer.WriteLine(text);
                    writer.Flush();
                    Logger.LogInfo("[TTS ENVIADO] " + text);
                }
            }
            catch (Exception ex)
            {
                Logger.LogError("Erro ao enviar payload TCP: " + ex.Message);
                isConnected = false;
            }
        }

        private void DisconnectSocket()
        {
            isConnected = false;
            if (socket != null)
            {
                try { socket.Close(); } catch { }
                socket = null;
            }
        }

        void OnDestroy()
        {
            DisconnectSocket();
        }
    }
}
