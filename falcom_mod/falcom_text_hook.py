import argparse
import collections
import ctypes
import io
import json
import os
import re
import socket
import subprocess
import sys
import time

try:
    from text_cleaner import TextCleaner
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from text_cleaner import TextCleaner

try:
    from falcom_voice_map import (
        CHARACTER_NAME_VOICE_MAP, PORTRAIT_VOICE_MAP, resolve_falcom_voice, voice_for_face_id,
    )
    from falcom_win32_runtime import (
        CF_UNICODETEXT, FalcomWin32RuntimeMixin, INVALID_HANDLE_VALUE, MEM_COMMIT,
        MEMORY_BASIC_INFORMATION, PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE, PAGE_GUARD,
        PAGE_NOACCESS, PAGE_READONLY, PAGE_READWRITE, PROCESS_QUERY_INFORMATION,
        PROCESS_VM_READ, PROCESSENTRY32, TH32CS_SNAPPROCESS,
    )
except ImportError:
    from .falcom_voice_map import (
        CHARACTER_NAME_VOICE_MAP, PORTRAIT_VOICE_MAP, resolve_falcom_voice, voice_for_face_id,
    )
    from .falcom_win32_runtime import (
        CF_UNICODETEXT, FalcomWin32RuntimeMixin, INVALID_HANDLE_VALUE, MEM_COMMIT,
        MEMORY_BASIC_INFORMATION, PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE, PAGE_GUARD,
        PAGE_NOACCESS, PAGE_READONLY, PAGE_READWRITE, PROCESS_QUERY_INFORMATION,
        PROCESS_VM_READ, PROCESSENTRY32, TH32CS_SNAPPROCESS,
    )


class FalcomTextHook(FalcomWin32RuntimeMixin):
    """
    Hook e monitor de texto para jogos Falcom ED6 (Trails in the Sky FC, SC, the 3rd).
    Lê a memória do processo do jogo ou pipe privado do TextractorCLI em tempo real e
    transmite os diálogos via TCP Socket (127.0.0.1:5050).
    """

    DEFAULT_IGNORE_EXACT = {
        "Save", "Load", "Config", "System", "Camp", "Status", "Equip",
        "Magic", "Item", "Book", "Bracer", "Quit", "Yes", "No", "Cancel",
        "OK", "Attack", "Craft", "Arts", "S-Craft", "Move", "Run", "Retry",
        "Wait", "Tactics", "Formation", "Auto", "Skip", "Log", "Notebook",
    }

    def __init__(
        self, host="127.0.0.1", port=None, max_history=30, settle_seconds=0.35,
        textractor_burst_gap=0.4, speed=None, base_dir=None,
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

    def connect(self):
        """Estabelece conexão TCP com o servidor TTS local."""
        try:
            self.disconnect()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            self.socket = sock
            self.is_connected = True
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
        if len(stripped) < 3 or stripped in self.ignore_set or stripped.isdigit():
            return False
        if re.fullmatch(r"#\d+", stripped):
            return False
        if any(marker in stripped for marker in ("\\", "_", "|")):
            return False
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
            if cleaned in prev:
                return True
            if len(cleaned) >= 6 and prev.endswith(cleaned):
                return True
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

    def should_send(self, text):
        """Controla debounce e histórico para evitar repetições contínuas de texto."""
        if not text or not self.is_valid_dialogue(text):
            return False
        return not self.is_duplicate_or_fragment(text)

    def send_text(self, text, voice=None):
        """Transmite a fala e a voz correspondente para o servidor TTS."""
        if not text or not getattr(self, "tts_enabled", True):
            return False
        if not self.socket and not self.connect():
            return False

        actual_voice = voice if voice else resolve_falcom_voice(text)
        commands = [f"SET_VOICE:{actual_voice}", "STOP", text]
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

    def _wait_for_server_connection(self):
        while not self.is_connected:
            if self.connect():
                print("[FalcomTextHook] Conectado ao servidor TTS com sucesso!")
                break
            time.sleep(1.0)

    def monitor_loop(self, poll_interval=0.5):
        """Loop principal de monitoramento de memória e diálogo de Trails in the Sky."""
        print(f"[FalcomTextHook] Conectando ao servidor TTS em {self.host}:{self.port}...")
        self._wait_for_server_connection()
        print("[FalcomTextHook] Procurando processo do Trails in the Sky...")
        current_pid = None
        h_proc = None

        self.start_hotkey_listener()
        try:
            while True:
                self.check_clipboard()
                if not current_pid or not h_proc:
                    pid, exe_name = self.find_target_process()
                    if not pid:
                        time.sleep(1.0)
                        continue
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

                changed_dialogues = self._scan_process_memory(h_proc)
                candidate = self.select_dialogue_candidate(changed_dialogues)
                stable_dialogue = self.observe_dialogue_candidate(candidate)
                if stable_dialogue and self.should_send(stable_dialogue):
                    self.send_text(stable_dialogue, voice=resolve_falcom_voice(stable_dialogue))
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
        self._wait_for_server_connection()
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
        self, textractor_cli, process_id, hook_code, popen_factory=subprocess.Popen, max_lines=None
    ):
        """Recebe texto pelo stdout privado do TextractorCLI, sem usar o clipboard."""
        print(f"[FalcomTextHook] TextractorCLI privado para PID {int(process_id)}...")
        self._wait_for_server_connection()
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
        "--clipboard-only", action="store_true",
        help="Lê somente o clipboard fornecido pelo Textractor; não examina a memória do jogo.",
    )
    parser.add_argument("--textractor-cli")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--hook-code")
    parser.add_argument("--speed", type=float, default=None, help="Velocidade da fala (ex: 1.25)")
    parser.add_argument("--port", type=int, default=None, help="Porta TCP do servidor TTS")
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
