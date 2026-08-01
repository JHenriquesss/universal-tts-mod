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
            "Yes", "No", "Cancel", "Ok", "Settings", "Relations", "Inventory", "Gallery", "Help",
            "Crowd", "Kandhasarian Emissaries", "Baron Maffren"
        };

        private string[] ignoreContains = new string[]
        {
            "Choice Taken", "Path Choice", "Quest Complete", "Level Up", "Achievement"
        };

        void Awake()
        {
            Logger.LogInfo("Kokoro TTS Plugin v1.3.0 (Com P/Invoke Spacebar Auto-Advance) Carregado.");
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

            ScanSceneForDialogue();
            ProcessDebounce();
        }

        private void SimulateSpacebar()
        {
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

            // 2. Scan TextMeshPro / Outros componentes de Texto via Reflexao
            try
            {
                UnityEngine.Object[] objects = FindObjectsOfType(typeof(Component));
                foreach (var obj in objects)
                {
                    try
                    {
                        Component comp = obj as Component;
                        if (comp != null && comp.gameObject.activeInHierarchy)
                        {
                            string typeName = comp.GetType().Name;
                            if (typeName.Contains("Text") || typeName.Contains("TMP"))
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
                    }
                    catch { }
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
                debounceTimer = DEBOUNCE_DELAY;
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

                socket = new TcpClient("127.0.0.1", 5050);
                NetworkStream stream = socket.GetStream();
                writer = new StreamWriter(stream, new UTF8Encoding(false));
                reader = new StreamReader(stream, new UTF8Encoding(false));
                isConnected = true;
                Logger.LogInfo("--> Conectado com sucesso ao servidor Kokoro TTS em 127.0.0.1:5050!");

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
