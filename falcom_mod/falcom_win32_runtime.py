import ctypes
from ctypes import wintypes
import hashlib
import os
import re
import threading
import time

try:
    from falcom_voice_map import resolve_falcom_voice
except ImportError:
    from .falcom_voice_map import resolve_falcom_voice


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


class FalcomWin32RuntimeMixin:
    """
    Camada Win32 para inspeção de processos, leitura/escrita de memória,
    Speedhack 2x (Turbo Mode), hotkeys globais e clipboard para jogos Falcom ED6.
    """

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

    TURBO_PATCHES = [
        (0x4CB009, b"\x74\x33", b"\x90\x90"),  # Field delta time
        (0x4CBBAA, b"\x74\x29", b"\x90\x90"),  # Field character logic/movement
        (0x4CD7CA, b"\x74\x35", b"\x90\x90"),  # Field camera/scene
        (0x42366E, b"\x74\x41", b"\x90\x90"),  # Battle speed/animation
        (0x4A27E0, b"\x8b\x0d\x44\xa8\x7f\x00", b"\xb0\x01\xc3\x90\x90\x90"),  # IsTurboButtonPressed -> True
    ]

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
        return self.k32.OpenProcess(0x0438, False, int(pid))

    def toggle_speedhack(self, force_state=None):
        """Alterna ou define o Speedhack 2x (Turbo Mode) diretamente na memória do jogo."""
        if not self.k32:
            return False

        h_proc = self._get_target_handle()
        if not h_proc:
            print("[SPEEDHACK] Processo do jogo não localizado para alternar Speedhack.")
            return False

        old_protect = wintypes.DWORD()
        n = ctypes.c_size_t()
        target_state = (not getattr(self, "speedhack_enabled", False)) if force_state is None else bool(force_state)

        try:
            if target_state:
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

                for addr, _orig, rep in self.TURBO_PATCHES:
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
                for addr, orig, _rep in self.TURBO_PATCHES:
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
        """Inicia escuta global de atalhos de teclado (+/-, Numpad +/-, F1, F2)."""
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
        """Loop de polling leve (~40ms) verificando teclas + / -, Numpad + / -, F1 e F2."""
        vk_add, vk_subtract = 0x6B, 0x6D
        vk_oem_plus, vk_oem_minus = 0xBB, 0xBD
        vk_f1, vk_f2 = 0x70, 0x71
        prev_states = {
            vk_add: False,
            vk_subtract: False,
            vk_oem_plus: False,
            vk_oem_minus: False,
            vk_f1: False,
            vk_f2: False,
        }

        while getattr(self, "_hotkey_running", False):
            try:
                for vk, is_increase in (
                    (vk_add, True),
                    (vk_subtract, False),
                    (vk_oem_plus, True),
                    (vk_oem_minus, False),
                ):
                    down = bool(self.u32.GetAsyncKeyState(vk) & 0x8000)
                    if down and not prev_states[vk]:
                        if is_increase:
                            self.increase_speed()
                        else:
                            self.decrease_speed()
                    prev_states[vk] = down

                f1_down = bool(self.u32.GetAsyncKeyState(vk_f1) & 0x8000)
                if f1_down and not prev_states[vk_f1]:
                    self.toggle_speedhack()
                prev_states[vk_f1] = f1_down

                f2_down = bool(self.u32.GetAsyncKeyState(vk_f2) & 0x8000)
                if f2_down and not prev_states[vk_f2]:
                    self.toggle_tts()
                prev_states[vk_f2] = f2_down

                time.sleep(0.04)
            except Exception:
                time.sleep(0.1)

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

    def extract_dialogues_from_buffer(self, buffer):
        """Extrai sequências de diálogo válidas de um bloco de memória binário."""
        if not buffer:
            return []
        results = []
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

    def _scan_process_memory(self, h_proc):
        """Percorre as regiões de memória graváveis do processo e extrai diálogos alterados."""
        mbi = MEMORY_BASIC_INFORMATION()
        addr = 0x00400000
        changed_dialogues = []
        while addr < 0x20000000:
            if not self.k32.VirtualQueryEx(
                h_proc, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)
            ):
                break
            is_readable = (
                mbi.State == MEM_COMMIT
                and (mbi.Protect & (PAGE_READWRITE | PAGE_EXECUTE_READWRITE))
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))
            )
            if is_readable and mbi.RegionSize > 0:
                for chunk_addr, chunk_size in self.iter_region_chunks(mbi.BaseAddress, mbi.RegionSize):
                    data = self.read_memory_range(h_proc, chunk_addr, chunk_size)
                    if data:
                        changed_dialogues.extend(self.dialogues_from_changed_chunk(chunk_addr, data))
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        return changed_dialogues

