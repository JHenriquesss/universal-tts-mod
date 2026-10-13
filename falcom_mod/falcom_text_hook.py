import argparse
import collections
import ctypes
from ctypes import wintypes
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time

try:
    from text_cleaner import TextCleaner
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from text_cleaner import TextCleaner


# Constantes do Windows API
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_READWRITE = 0x04
PAGE_READONLY = 0x02
PAGE_EXECUTE_READWRITE = 0x40
PAGE_EXECUTE_READ = 0x20
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
CF_UNICODETEXT = 13
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


try:
    from falcom_voice_map import (
        CHARACTER_NAME_VOICE_MAP,
        PORTRAIT_VOICE_MAP,
        resolve_falcom_voice,
        voice_for_face_id,
    )
except ImportError:
    from .falcom_voice_map import (
        CHARACTER_NAME_VOICE_MAP,
        PORTRAIT_VOICE_MAP,
        resolve_falcom_voice,
        voice_for_face_id,
    )


class FalcomTextHook:
    """
    Hook e monitor de texto para jogos Falcom ED6 (Trails in the Sky FC, SC, the 3rd).
    Lê a memória do processo do jogo em tempo real e transmite os diálogos via TCP Socket (127.0.0.1:5050).
    """

    DEFAULT_IGNORE_EXACT = {
        "Save", "Load", "Config", "System", "Camp", "Status", "Equip",
        "Magic", "Item", "Book", "Bracer", "Quit", "Yes", "No", "Cancel",
        "OK", "Attack", "Craft", "Arts", "S-Craft", "Move", "Run", "Retry",
        "Wait", "Tactics", "Formation", "Auto", "Skip", "Log", "Notebook",
    }

    TARGET_PROCESS_NAMES = {
        "ed6_win2_dx9.exe",
        "ed6_win2.exe",
        "ed6_win_dx9.exe",
        "ed6_win.exe",
        "ed6_win3_dx9.exe",
        "ed6_win3.exe",
        "ed7_win.exe",
        "ed7_win_dx9.exe",
    }

    def __init__(
        self,
        host="127.0.0.1",
        port=None,
        max_history=30,
        settle_seconds=0.35,
        textractor_burst_gap=0.4,
        speed=None,
        base_dir=None,
    ):
        self.host = host
        self._port_explicit = port is not None
        self.port = int(port) if port is not None else int(os.environ.get("TTS_PORT", 5050))
        self.socket = None
        self.is_connected = False
        self.last_sent_text = ""
        self.history = collections.deque(maxlen=max_history)
        self.ignore_set = set(self.DEFAULT_IGNORE_EXACT)
        self.k32 = ctypes.windll.kernel32 if os.name == "nt" else None
        self.u32 = ctypes.windll.user32 if os.name == "nt" else None
        if self.k32 and self.u32:
            self._configure_win32_api()
        self.last_clipboard_text = ""
        self.memory_chunk_signatures = {}
        self.settle_seconds = float(settle_seconds)
        self.pending_dialogue = None
        self.pending_since = None
        self.textractor_process = None
        self.textractor_burst_gap = float(textractor_burst_gap)
        self.last_textractor_capture_at = None
        self.textractor_burst_has_sent = False
        self.last_detected_voice = None
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.speed = 1.25
        self._load_config()
        if speed is not None:
            self.speed = round(max(0.5, min(3.0, float(speed))), 2)
        self.target_pid = None
        self.speedhack_enabled = False
        self.tts_enabled = True
        self._hotkey_thread = None
        self._hotkey_running = False

    def _configure_win32_api(self):
        """Declara tipos Win32 para preservar handles e ponteiros em Python 64-bit."""
        self.k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        self.k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        self.k32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
        self.k32.Process32First.restype = wintypes.BOOL
        self.k32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
        self.k32.Process32Next.restype = wintypes.BOOL
        self.k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.k32.OpenProcess.restype = wintypes.HANDLE
        self.k32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.k32.CloseHandle.restype = wintypes.BOOL
        self.k32.ReadProcessMemory.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.LPVOID,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.k32.ReadProcessMemory.restype = wintypes.BOOL
        self.k32.WriteProcessMemory.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.LPCVOID,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self.k32.WriteProcessMemory.restype = wintypes.BOOL
        self.k32.VirtualProtectEx.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            ctypes.c_size_t,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.k32.VirtualProtectEx.restype = wintypes.BOOL
        self.k32.VirtualQueryEx.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            ctypes.POINTER(MEMORY_BASIC_INFORMATION),
            ctypes.c_size_t,
        ]
        self.k32.VirtualQueryEx.restype = ctypes.c_size_t
        self.k32.GlobalLock.argtypes = [wintypes.HANDLE]
        self.k32.GlobalLock.restype = wintypes.LPVOID
        self.k32.GlobalUnlock.argtypes = [wintypes.HANDLE]
        self.k32.GlobalUnlock.restype = wintypes.BOOL
        self.u32.OpenClipboard.argtypes = [wintypes.HWND]
        self.u32.OpenClipboard.restype = wintypes.BOOL
        self.u32.GetClipboardData.argtypes = [wintypes.UINT]
        self.u32.GetClipboardData.restype = wintypes.HANDLE
        self.u32.CloseClipboard.argtypes = []
        self.u32.CloseClipboard.restype = wintypes.BOOL

    def is_target_process(self, proc_name):
        """Verifica se o executável pertence à família Falcom ED6/ED7."""
        if not proc_name:
            return False
        return proc_name.strip().lower() in self.TARGET_PROCESS_NAMES

    def find_target_process(self):
        """Localiza o PID e nome do executável do jogo em execução."""
        if not self.k32:
            return None, None

        h_snapshot = self.k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if h_snapshot == INVALID_HANDLE_VALUE or not h_snapshot:
            return None, None

        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)

        try:
            if self.k32.Process32First(h_snapshot, ctypes.byref(pe)):
                while True:
                    exe_name = pe.szExeFile.decode(errors="ignore")
                    if self.is_target_process(exe_name):
                        return pe.th32ProcessID, exe_name
                    if not self.k32.Process32Next(h_snapshot, ctypes.byref(pe)):
                        break
        finally:
            self.k32.CloseHandle(h_snapshot)

        return None, None

    def _load_config(self):
        """Carrega configurações persistentes de velocidade e preferências."""
        config_path = os.path.join(self.base_dir, "tts_config.json")
        if os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "speed" in data:
                        self.speed = round(max(0.5, min(3.0, float(data["speed"]))), 2)
                    if "port" in data and not self._port_explicit:
                        self.port = int(data["port"])
            except Exception:
                pass

    def _save_config(self):
        """Salva a velocidade atual no tts_config.json para persistência preservando outras chaves."""
        config_path = os.path.join(self.base_dir, "tts_config.json")
        try:
            data = {}
            if os.path.isfile(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data = loaded
                except Exception:
                    pass
            data["speed"] = self.speed
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def set_speed(self, speed):
        """Atualiza a velocidade do TTS e envia comando SET_SPEED ao servidor."""
        self.speed = round(max(0.5, min(3.0, float(speed))), 2)
        if self.socket and self.is_connected:
            try:
                self.socket.sendall(f"SET_SPEED:{self.speed}\n".encode("utf-8"))
            except Exception:
                pass
        self._save_config()
        print(f"[VELOCIDADE TTS] Velocidade definida para: {self.speed:.2f}x")
        return self.speed

    def increase_speed(self, delta=0.1):
        """Aumenta a velocidade da fala (+0.10x, até 3.00x), como no Ren'Py."""
        new_speed = self.set_speed(self.speed + delta)
        self._beep(1200, 35)
        return new_speed

    def decrease_speed(self, delta=0.1):
        """Diminui a velocidade da fala (-0.10x, até 0.50x), como no Ren'Py."""
        new_speed = self.set_speed(self.speed - delta)
        self._beep(750, 35)
        return new_speed

    def _beep(self, freq, duration_ms):
        """Emite feedback sonoro sutil no Windows sem bloquear execução."""
        if os.name == "nt":
            try:
                import winsound
                threading.Thread(
                    target=winsound.Beep,
                    args=(int(freq), int(duration_ms)),
                    daemon=True,
                ).start()
            except Exception:
                pass

    TURBO_PATCHES = [
        (0x4cb009, b"\x74\x33", b"\x90\x90"),  # Field delta time
        (0x4cbbaa, b"\x74\x29", b"\x90\x90"),  # Field character logic/movement
        (0x4cd7ca, b"\x74\x35", b"\x90\x90"),  # Field camera/scene
        (0x42366e, b"\x74\x41", b"\x90\x90"),  # Battle speed/animation
        (0x4a27e0, b"\x8b\x0d\x44\xa8\x7f\x00", b"\xb0\x01\xc3\x90\x90\x90"),  # IsTurboButtonPressed -> True
    ]

    def _get_target_handle(self):
        """Retorna handle com permissões de leitura/escrita no processo do jogo."""
        if not self.k32:
            return None
        pid = getattr(self, "target_pid", None)
        if not pid:
            pid, _ = self.find_target_process()
            if pid:
                self.target_pid = pid
        if not pid:
            return None
        # PROCESS_VM_READ (0x10) | PROCESS_VM_WRITE (0x20) | PROCESS_VM_OPERATION (0x08) | PROCESS_QUERY_INFORMATION (0x400)
        h_proc = self.k32.OpenProcess(0x0438, False, int(pid))
        return h_proc

    def toggle_speedhack(self, force_state=None):
        """
        Alterna ou define o Speedhack 2x (Turbo Mode oficial da Falcom) diretamente na memória do jogo.
        Pressione F1 para ligar/desligar em tempo real.
        """
        if not self.k32:
            return False

        h_proc = self._get_target_handle()
        if not h_proc:
            print("[SPEEDHACK] Processo do jogo não localizado para alternar Speedhack.")
            return False

        PAGE_EXECUTE_READWRITE = 0x40
        old_protect = wintypes.DWORD()
        n = ctypes.c_size_t()

        target_state = (not getattr(self, "speedhack_enabled", False)) if force_state is None else bool(force_state)

        try:
            if target_state:
                # Valida se os bytes em memória correspondem aos esperados antes de alterar
                valid = True
                for addr, orig, rep in self.TURBO_PATCHES:
                    buf = (ctypes.c_uint8 * len(orig))()
                    if self.k32.ReadProcessMemory(h_proc, ctypes.c_void_p(addr), buf, len(orig), ctypes.byref(n)):
                        if bytes(buf) != orig and bytes(buf) != rep:
                            valid = False
                            break
                    else:
                        valid = False
                        break
                if not valid:
                    print("[SPEEDHACK] Assinatura de código diferente; Speedhack ignorado para segurança.")
                    return False

                # Ativar Speedhack 2x (NOP / Força Turbo nativo)
                for addr, orig, rep in self.TURBO_PATCHES:
                    self.k32.VirtualProtectEx(
                        h_proc, ctypes.c_void_p(addr), len(rep), PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)
                    )
                    self.k32.WriteProcessMemory(
                        h_proc, ctypes.c_void_p(addr), rep, len(rep), ctypes.byref(n)
                    )
                self.speedhack_enabled = True
                self._beep(1400, 50)
                print("[SPEEDHACK] >>> Turbo 2x ATIVADO [F1] <<<")
            else:
                # Desativar Speedhack (restaurar bytes originais 1x)
                for addr, orig, rep in self.TURBO_PATCHES:
                    self.k32.WriteProcessMemory(
                        h_proc, ctypes.c_void_p(addr), orig, len(orig), ctypes.byref(n)
                    )
                    self.k32.VirtualProtectEx(
                        h_proc, ctypes.c_void_p(addr), len(orig), old_protect, ctypes.byref(old_protect)
                    )
                self.speedhack_enabled = False
                self._beep(700, 50)
                print("[SPEEDHACK] >>> Turbo 2x DESATIVADO (Velocidade Normal 1x) [F1] <<<")
            return self.speedhack_enabled
        finally:
            self.k32.CloseHandle(h_proc)

    def start_hotkey_listener(self):
        """Inicia escuta global de atalhos de teclado (+/-, Numpad +/-, F1) para controle em tempo real."""
        if os.name != "nt" or not self.u32:
            return

        if self._hotkey_thread and self._hotkey_thread.is_alive():
            return

        self._hotkey_running = True
        self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self._hotkey_thread.start()

    def stop_hotkey_listener(self):
        """Encerra a escuta global de atalhos e restaura o jogo para 1x se o Speedhack estiver ativo."""
        self._hotkey_running = False
        self._hotkey_thread = None
        if getattr(self, "speedhack_enabled", False):
            try:
                self.toggle_speedhack(force_state=False)
            except Exception:
                pass

    def toggle_tts(self, force_state=None):
        """Alterna ou define a ativação do TTS (Mute / Unmute) via tecla F2."""
        new_state = (not getattr(self, "tts_enabled", True)) if force_state is None else bool(force_state)
        self.tts_enabled = new_state
        if not self.tts_enabled:
            # Envia comando STOP para cortar imediatamente a voz se estiver falando
            if self.socket and self.is_connected:
                try:
                    self.socket.sendall(b"STOP\n")
                except Exception:
                    pass
            self._beep(600, 45)
            print("[TTS] >>> Vozes DESATIVADAS (Modo Leitura Silenciosa) [F2] <<<")
        else:
            self._beep(1300, 45)
            print("[TTS] >>> Vozes ATIVADAS [F2] <<<")
        return self.tts_enabled

    def _hotkey_loop(self):
        """Loop de polling leve (~40ms) verificando teclas + / -, Numpad + / -, F1 (Speedhack) e F2 (Mute TTS)."""
        VK_ADD = 0x6B        # Numpad +
        VK_SUBTRACT = 0x6D   # Numpad -
        VK_OEM_PLUS = 0xBB   # Tecla + / =
        VK_OEM_MINUS = 0xBD  # Tecla - / _
        VK_F1 = 0x70         # Tecla F1 (Toggle Speedhack 2x)
        VK_F2 = 0x71         # Tecla F2 (Toggle TTS / Modo Leitura Silenciosa)

        prev_states = {
            VK_ADD: False,
            VK_SUBTRACT: False,
            VK_OEM_PLUS: False,
            VK_OEM_MINUS: False,
            VK_F1: False,
            VK_F2: False,
        }

        while getattr(self, "_hotkey_running", False):
            try:
                for vk, is_increase in [
                    (VK_ADD, True),
                    (VK_SUBTRACT, False),
                    (VK_OEM_PLUS, True),
                    (VK_OEM_MINUS, False),
                ]:
                    down = bool(self.u32.GetAsyncKeyState(vk) & 0x8000)
                    if down and not prev_states[vk]:
                        if is_increase:
                            self.increase_speed()
                        else:
                            self.decrease_speed()
                    prev_states[vk] = down

                # Checa tecla F1 para alternar Speedhack 2x
                f1_down = bool(self.u32.GetAsyncKeyState(VK_F1) & 0x8000)
                if f1_down and not prev_states[VK_F1]:
                    self.toggle_speedhack()
                prev_states[VK_F1] = f1_down

                # Checa tecla F2 para alternar TTS (Mute / Unmute)
                f2_down = bool(self.u32.GetAsyncKeyState(VK_F2) & 0x8000)
                if f2_down and not prev_states[VK_F2]:
                    self.toggle_tts()
                prev_states[VK_F2] = f2_down

                time.sleep(0.04)
            except Exception:
                time.sleep(0.1)

    def connect(self):
        """Estabelece conexão TCP com o servidor TTS local."""
        try:
            self.disconnect()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            self.socket = sock
            self.is_connected = True
            # Sincroniza velocidade atual com o servidor
            if self.speed:
                try:
                    self.socket.sendall(f"SET_SPEED:{self.speed}\n".encode("utf-8"))
                except Exception:
                    pass
            return True
        except Exception:
            self.is_connected = False
            self.socket = None
            return False

    def disconnect(self):
        """Encerra a conexão com o socket."""
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def is_valid_dialogue(self, text):
        """Verifica se a string é um diálogo válido e não ruído de sistema."""
        if not text:
            return False
        stripped = text.strip()
        if len(stripped) < 3:
            return False
        if stripped in self.ignore_set:
            return False
        if stripped.isdigit():
            return False
        if re.fullmatch(r"#\d+", stripped):
            return False
        if any(marker in stripped for marker in ("\\", "_", "|")):
            return False
        # Ignorar caminhos de arquivo ou extensões de engine
        if re.search(
            r"\.(dat|dir|wav|ogg|avi|bmp|png|exe|dll)\b|\s*\._[A-Z0-9]{2}\b",
            stripped,
            flags=re.I,
        ):
            return False
        letters = re.findall(r"[A-Za-z]", stripped)
        digits = re.findall(r"\d", stripped)
        if len(letters) < 3 or len(digits) > len(letters) // 2:
            return False
        non_ascii = sum(ord(char) > 127 for char in stripped)
        if non_ascii > max(2, len(stripped) // 10):
            return False
        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", stripped)
        has_sentence_punctuation = bool(re.search(r"[.!?]", stripped))
        if len(words) < 2 and not has_sentence_punctuation:
            return False
        return True

    def process_raw_text(self, raw_text):
        """Limpa as tags Falcom e normaliza a string para síntese de voz."""
        if not raw_text:
            return ""
        collapsed = self.collapse_textractor_suffix_replays(str(raw_text))
        return TextCleaner.clean(self.keep_current_textractor_page(collapsed))

    @staticmethod
    def keep_current_textractor_page(raw_text):
        """
        Corta o bloco antes da próxima caixa, marcada por um novo retrato #...F.
        Não corta no meio de frases ou em pausas com reticências (...),
        apenas quando a frase anterior possui pontuação terminal completa.
        """
        text = str(raw_text or "")
        previous_end = 0
        has_dialogue_text = False
        for tag in re.finditer(r"#\d+[A-Za-z]", text):
            between = text[previous_end : tag.start()]
            words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", between)
            if len(words) >= 2 or len(re.findall(r"[A-Za-z]", between)) >= 3:
                has_dialogue_text = True

            if has_dialogue_text and tag.group().endswith("F"):
                accumulated_before_tag = text[: tag.start()].rstrip()
                without_ellipsis = re.sub(r"\.{2,}", "", accumulated_before_tag).rstrip()
                has_terminal_punct = bool(re.search(r"[.!?][\"']?$", without_ellipsis))
                if has_terminal_punct:
                    return text[: tag.start()]

            previous_end = tag.end()
        return text

    def is_duplicate_or_fragment(self, cleaned):
        """Retorna True se o texto for repetição, fragmento ou sufixo de diálogo recente."""
        if not cleaned:
            return True
        if cleaned == self.last_sent_text or cleaned in self.history:
            return True
        
        all_recent = list(self.history)
        if self.last_sent_text:
            all_recent.append(self.last_sent_text)
            
        for prev in all_recent:
            # Substring total: o novo texto está contido no texto anterior
            if cleaned in prev:
                return True
            # Sufixo: o texto anterior termina com o novo texto
            if len(cleaned) >= 6 and prev.endswith(cleaned):
                return True
            # Sobreposição significativa (caso haja pequenas variações de pontuação)
            if len(cleaned) >= 20 and len(prev) >= 20:
                if cleaned[:25] in prev and cleaned[-20:] in prev:
                    return True
        return False

    def observe_textractor_capture(self, raw_text, now=None):
        """Libera no máximo a primeira caixa nova de cada rajada do renderizador."""
        now = time.monotonic() if now is None else float(now)
        if (
            self.last_textractor_capture_at is None
            or now - self.last_textractor_capture_at >= self.textractor_burst_gap
        ):
            self.textractor_burst_has_sent = False
        self.last_textractor_capture_at = now

        if self.textractor_burst_has_sent:
            return None

        self.last_detected_voice = resolve_falcom_voice(raw_text)

        cleaned = self.process_raw_text(raw_text)
        if not self.is_valid_dialogue(cleaned):
            return None

        if self.is_duplicate_or_fragment(cleaned):
            return None

        self.textractor_burst_has_sent = True
        return cleaned

    @staticmethod
    def collapse_textractor_suffix_replays(raw_text, sample_size=32):
        """Remove sufixos repetidos gerados quando um hook de string dispara em cada tag."""
        text = str(raw_text or "")
        for tag in list(re.finditer(r"#\d+[A-Za-z]", text))[1:]:
            start = tag.start()
            sample = text[start : start + sample_size]
            if len(sample) >= 12 and text.find(sample, 0, start) >= 0:
                return text[:start]
        return text

    def extract_dialogues_from_buffer(self, buffer):
        """
        Extrai sequências de diálogo válidas de um bloco de memória binário.
        """
        if not buffer:
            return []

        results = []
        # Falcom ED6 usa CP1252 / Shift-JIS / UTF-8 com tags #...
        # Procura strings terminadas em nulo com tamanho razoável
        for match in re.finditer(rb"(?:#[0-9]+[A-Z]|[\x20-\x7E\xA0-\xFF]){5,500}\x00", buffer):
            raw_bytes = match.group()[:-1]
            try:
                text = raw_bytes.decode("cp1252", errors="ignore").strip()
            except Exception:
                continue

            cleaned = self.process_raw_text(text)
            if self.is_valid_dialogue(cleaned):
                results.append(cleaned)

        return results

    def dialogues_from_changed_chunk(self, address, data):
        """Extrai texto somente quando um bloco já conhecido muda de conteúdo."""
        signature = hashlib.blake2b(data, digest_size=8).digest()
        previous = self.memory_chunk_signatures.get(address)
        self.memory_chunk_signatures[address] = signature
        if previous is None or previous == signature:
            return []
        return self.extract_dialogues_from_buffer(data)

    def select_dialogue_candidate(self, dialogues):
        """Escolhe no máximo uma frase natural entre os buffers alterados."""
        valid = {text for text in dialogues if self.is_valid_dialogue(text)}
        if not valid:
            return None

        def score(text):
            words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
            punctuation_bonus = 25 if re.search(r"[.!?]", text) else 0
            return punctuation_bonus + min(len(text), 160) + (len(words) * 4)

        return max(valid, key=score)

    def observe_dialogue_candidate(self, candidate, now=None):
        """Espera o texto parar de crescer antes de liberá-lo para síntese."""
        now = time.monotonic() if now is None else float(now)
        if candidate and candidate != self.pending_dialogue:
            self.pending_dialogue = candidate
            self.pending_since = now
            return None
        if not self.pending_dialogue or self.pending_since is None:
            return None
        if now - self.pending_since < self.settle_seconds:
            return None
        stable = self.pending_dialogue
        self.pending_dialogue = None
        self.pending_since = None
        return stable

    def should_send(self, text):
        """Controla debounce e histórico para evitar repetições contínuas de texto."""
        if not text or not self.is_valid_dialogue(text):
            return False
        return not self.is_duplicate_or_fragment(text)

    def send_text(self, text, voice=None):
        """Transmite a fala e a voz correspondente para o servidor TTS."""
        if not text:
            return False

        if not getattr(self, "tts_enabled", True):
            # Modo silencioso ativo pelo jogador (F2)
            return False

        if not self.socket:
            if not self.connect():
                return False

        actual_voice = voice if voice else resolve_falcom_voice(text)
        commands = [
            f"SET_VOICE:{actual_voice}",
            "STOP",
            text,
        ]
        payload = ("\n".join(commands) + "\n").encode("utf-8")

        try:
            self.socket.sendall(payload)
            self.last_sent_text = text
            self.history.append(text)
            print(f"[FALA DETECTADA] [{actual_voice}] {text}")
            return True
        except Exception:
            self.disconnect()
            return False

    def check_clipboard(self, send=True):
        """Lê o texto do clipboard (caso o usuário use Textractor/Agent em conjunto)."""
        if not self.u32:
            return None

        try:
            if self.u32.OpenClipboard(None):
                try:
                    h_data = self.u32.GetClipboardData(CF_UNICODETEXT)
                    if h_data:
                        text_ptr = self.k32.GlobalLock(h_data)
                        if text_ptr:
                            try:
                                text = ctypes.wstring_at(text_ptr)
                                if text and text != self.last_clipboard_text:
                                    self.last_clipboard_text = text
                                    if send:
                                        voice = resolve_falcom_voice(text)
                                        cleaned = self.process_raw_text(text)
                                        if self.should_send(cleaned):
                                            self.send_text(cleaned, voice=voice)
                                            return cleaned
                            finally:
                                self.k32.GlobalUnlock(h_data)
                finally:
                    self.u32.CloseClipboard()
        except Exception:
            pass
        return None

    @staticmethod
    def iter_region_chunks(start_addr, region_size, max_chunk_size=256 * 1024):
        """Percorre uma região inteira sem alocar buffers maiores que o limite."""
        offset = 0
        while offset < region_size:
            chunk_size = min(max_chunk_size, region_size - offset)
            yield start_addr + offset, chunk_size
            offset += chunk_size

    def scan_memory_range(self, h_proc, start_addr, size):
        """Lê e processa um bloco de memória do processo alvo."""
        data = self.read_memory_range(h_proc, start_addr, size)
        if data:
            dialogues = self.extract_dialogues_from_buffer(data)
            for dial in dialogues:
                if self.should_send(dial):
                    voice = resolve_falcom_voice(dial)
                    self.send_text(dial, voice=voice)
                    return dial
        return None

    def read_memory_range(self, h_proc, start_addr, size):
        """Retorna bytes legíveis do processo sem interpretar ou enviar texto."""
        if not self.k32:
            return None
        read_buf = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        success = self.k32.ReadProcessMemory(
            h_proc, ctypes.c_void_p(start_addr), read_buf, size, ctypes.byref(bytes_read)
        )
        if not success or bytes_read.value == 0:
            return None
        return read_buf.raw[: bytes_read.value]

    def monitor_loop(self, poll_interval=0.5):
        """
        Loop principal de monitoramento de memória e diálogo de Trails in the Sky.
        """
        print(f"[FalcomTextHook] Conectando ao servidor TTS em {self.host}:{self.port}...")
        while not self.is_connected:
            if self.connect():
                print("[FalcomTextHook] Conectado ao servidor TTS com sucesso!")
                break
            time.sleep(1.0)

        print("[FalcomTextHook] Procurando processo do Trails in the Sky...")
        current_pid = None
        h_proc = None

        self.start_hotkey_listener()
        try:
            while True:
                # 1. Checagem rápida de clipboard / Textractor
                self.check_clipboard()

                # 2. Localizar processo do jogo
                if not current_pid or not h_proc:
                    pid, exe_name = self.find_target_process()
                    if pid:
                        current_pid = pid
                        self.target_pid = pid
                        h_proc = self.k32.OpenProcess(
                            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid
                        )
                        self.memory_chunk_signatures.clear()
                        self.pending_dialogue = None
                        self.pending_since = None
                        print(f"[FalcomTextHook] Jogo detectado: {exe_name} (PID: {pid})")
                        print("[FalcomTextHook] Monitorando diálogos em tempo real...")
                    else:
                        time.sleep(1.0)
                        continue

                # 3. Escanear a seção .data (0x5B8000 a 0x3000000) e buffers ativos
                mbi = MEMORY_BASIC_INFORMATION()
                addr = 0x00400000  # ImageBase fixo de Trails in the Sky
                changed_dialogues = []

                while addr < 0x20000000:
                    if not self.k32.VirtualQueryEx(
                        h_proc, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
                    ):
                        break

                    # Verifica se o bloco de memória está alocado e acessível para leitura
                    is_readable = (
                        mbi.State == MEM_COMMIT
                        and (mbi.Protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE))
                        and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))
                    )

                    if is_readable and mbi.RegionSize > 0:
                        for chunk_addr, chunk_size in self.iter_region_chunks(
                            mbi.BaseAddress, mbi.RegionSize
                        ):
                            data = self.read_memory_range(h_proc, chunk_addr, chunk_size)
                            if data:
                                changed_dialogues.extend(
                                    self.dialogues_from_changed_chunk(chunk_addr, data)
                                )

                    addr = (mbi.BaseAddress or 0) + mbi.RegionSize

                candidate = self.select_dialogue_candidate(changed_dialogues)
                stable_dialogue = self.observe_dialogue_candidate(candidate)
                if stable_dialogue and self.should_send(stable_dialogue):
                    voice = resolve_falcom_voice(stable_dialogue)
                    self.send_text(stable_dialogue, voice=voice)

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            print("\n[FalcomTextHook] Encerrando monitor...")
        finally:
            self.stop_hotkey_listener()
            if h_proc and self.k32:
                self.k32.CloseHandle(h_proc)
            self.disconnect()

    def monitor_clipboard_loop(self, poll_interval=0.1, max_cycles=None):
        """Encaminha somente texto do clipboard; nunca abre nem lê o processo do jogo."""
        print(f"[FalcomTextHook] Modo clipboard-only em {self.host}:{self.port}...")
        while not self.is_connected:
            if self.connect():
                print("[FalcomTextHook] Conectado ao servidor TTS com sucesso!")
                break
            time.sleep(1.0)

        # O conteúdo que já estava no clipboard antes do bridge abrir é
        # apenas uma linha de base; somente mudanças posteriores são falas novas.
        self.check_clipboard(send=False)
        self.start_hotkey_listener()
        cycles = 0
        try:
            while max_cycles is None or cycles < max_cycles:
                self.check_clipboard()
                cycles += 1
                if max_cycles is None or cycles < max_cycles:
                    time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\n[FalcomTextHook] Encerrando monitor de clipboard...")
        finally:
            self.stop_hotkey_listener()
            self.disconnect()

    @staticmethod
    def _write_textractor_command(process, command, process_id):
        payload = f"{command} -P{int(process_id)}\n".encode("utf-16-le")
        process.stdin.write(payload)
        process.stdin.flush()

    @staticmethod
    def parse_textractor_output_line(line, expected_hook):
        """Retorna somente texto originado do hook privado solicitado."""
        line = str(line or "").rstrip("\r\n")
        marker = f":{expected_hook}]"
        if marker not in line or "] " not in line:
            return None
        return line.split("] ", 1)[1]

    def monitor_textractor_cli(
        self,
        textractor_cli,
        process_id,
        hook_code,
        popen_factory=subprocess.Popen,
        max_lines=None,
    ):
        """Recebe texto pelo stdout privado do TextractorCLI, sem usar o clipboard."""
        print(f"[FalcomTextHook] TextractorCLI privado para PID {int(process_id)}...")
        while not self.is_connected:
            if self.connect():
                print("[FalcomTextHook] Conectado ao servidor TTS com sucesso!")
                break
            time.sleep(1.0)

        process = popen_factory(
            [os.path.abspath(textractor_cli)],
            cwd=os.path.dirname(os.path.abspath(textractor_cli)),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.textractor_process = process
        attached = False
        hook_inserted = False
        lines_seen = 0
        reader = io.TextIOWrapper(process.stdout, encoding="utf-16-le", newline="")
        self.target_pid = int(process_id)
        self.start_hotkey_listener()
        try:
            self._write_textractor_command(process, "attach", process_id)
            attached = True
            for line in reader:
                lines_seen += 1
                if "Textractor: pipe connected" in line and not hook_inserted:
                    self._write_textractor_command(process, hook_code, process_id)
                    hook_inserted = True

                raw_text = self.parse_textractor_output_line(line, hook_code)
                if raw_text is not None:
                    cleaned = self.observe_textractor_capture(raw_text)
                    if cleaned and self.should_send(cleaned):
                        self.send_text(cleaned, voice=getattr(self, "last_detected_voice", None))

                if max_lines is not None and lines_seen >= max_lines:
                    break
        finally:
            self.stop_hotkey_listener()
            if attached:
                try:
                    self._write_textractor_command(process, "detach", process_id)
                except Exception:
                    pass
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            self.textractor_process = None
            self.disconnect()


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Bridge TTS para jogos Falcom ED6")
    parser.add_argument(
        "--clipboard-only",
        action="store_true",
        help="Lê somente o clipboard fornecido pelo Textractor; não examina a memória do jogo.",
    )
    parser.add_argument("--textractor-cli")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--hook-code")
    parser.add_argument(
        "--speed",
        type=float,
        default=None,
        help="Velocidade da fala (ex: 1.25, padrão ajustável com teclas +/-)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Porta TCP do servidor TTS (padrão: tts_config.json, TTS_PORT ou 5050)",
    )
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    hook = FalcomTextHook(speed=args.speed, port=args.port)
    if args.textractor_cli:
        if args.pid is None or not args.hook_code:
            raise SystemExit("--textractor-cli requer --pid e --hook-code")
        hook.monitor_textractor_cli(args.textractor_cli, args.pid, args.hook_code)
    elif args.clipboard_only:
        hook.monitor_clipboard_loop()
    else:
        hook.monitor_loop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
