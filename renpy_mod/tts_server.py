# -*- coding: utf-8 -*-
import io
import json
import os
import queue
import secrets
import sys
import threading
import time
import warnings

warnings.filterwarnings("ignore")

here = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
if here not in sys.path:
    sys.path.insert(0, here)

log_dir = os.environ.get("TTS_LOG_DIR") or here
log_path = os.path.join(log_dir, "tts_server.log")
status_path = os.path.join(log_dir, "tts_ready.txt")

from tts_protocol import (  # noqa: E402
    CMD_HELLO,
    CMD_PLAYBACK_DONE,
    CMD_QUIT,
    CMD_SET_LANG,
    CMD_SET_SPEED,
    CMD_SET_VOICE,
    CMD_STOP,
    append_bounded_log,
    apply_thread_env_limits,
    drain_preserving,
    has_cli_flag,
    is_pid_alive,
    iter_socket_lines,
    lower_process_priority,
    normalize_lang_code as _normalize_lang,
    parse_cli_float_flag,
    parse_cli_int_flag,
    remove_owned_status,
    resolve_cpu_threads,
    resolve_engine_name,
    resolve_idle_timeout,
    status_has_live_ready,
    strip_cli_flags,
    trim_working_set,
)


def _log(msg):
    try:
        append_bounded_log(log_path, msg)
    except Exception:
        pass


def setup_logger():
    class Logger(object):
        def __init__(self, original_stream):
            self.original_stream = original_stream

        def write(self, message):
            if message.strip():
                _log(f"{message.strip()}")
                if self.original_stream:
                    try:
                        self.original_stream.write(message)
                        self.original_stream.flush()
                    except Exception:
                        pass

        def flush(self):
            if self.original_stream:
                try:
                    self.original_stream.flush()
                except Exception:
                    pass

    orig_stdout, orig_stderr = sys.stdout, sys.stderr
    sys.stdout = Logger(sys.__stdout__ if sys.__stdout__ else orig_stdout)
    sys.stderr = Logger(sys.__stderr__ if sys.__stderr__ else orig_stderr)


if sys.platform == "win32":
    try:
        if hasattr(sys.stdin, "buffer") and sys.stdin.buffer is not None:
            sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
        elif hasattr(sys, "__stdin__") and sys.__stdin__ is not None and hasattr(sys.__stdin__, "buffer"):
            sys.stdin = io.TextIOWrapper(sys.__stdin__.buffer, encoding="utf-8", errors="replace")
    except Exception as e:
        _log(f"Aviso: Não foi possível reconfigurar stdin: {e}")

setup_logger()

_speech_queue = queue.Queue(maxsize=10)
_activity = {"last_ts": time.monotonic(), "busy": False}
DEFAULT_VOICE = "af_heart"
# Sem falas por esse tempo, a RAM ociosa do backend volta para o Windows.
IDLE_TRIM_SECONDS = 30.0


def _touch_activity():
    _activity["last_ts"] = time.monotonic()


def _new_instance_token():
    return secrets.token_hex(8)


def _preview_text(text, limit=80):
    text = str(text).replace("\n", " ").replace("\r", " ")
    return text if len(text) <= limit else text[:limit] + "..."


def _worker(engine, initial_speed, initial_voice):
    speed = initial_speed
    voice = initial_voice or DEFAULT_VOICE
    trimmed = True  # o engine ja fez o trim depois de carregar
    while True:
        try:
            task = _speech_queue.get(timeout=1)
            if task is None:
                break

            trimmed = False
            _activity["busy"] = True
            _touch_activity()
            cmd, data = task
            if cmd == "SET_SPEED":
                speed = data
            elif cmd == "SET_VOICE":
                voice = data or voice
            elif cmd == "SET_LANG":
                if hasattr(engine, "set_lang"):
                    try:
                        engine.set_lang(data)
                        _log(f"engine.set_lang lang={data}")
                    except Exception as err:
                        _log(f"engine.set_lang error={err}")
            elif cmd == "SPEAK":
                data = str(data)
                for apo in ["’", "‘", "´", "`", "′", "’"]:
                    data = data.replace(apo, "'")
                _log(f"Processando: {_preview_text(data)}")
                _log(f"speak voice={voice} text_preview={_preview_text(data)}")
                engine.speak(data, voice=voice, speed=speed)
            elif cmd == "STOP":
                engine.stop()

            _activity["busy"] = False
            _touch_activity()
            _speech_queue.task_done()
        except queue.Empty:
            idle_for = time.monotonic() - _activity["last_ts"]
            if not trimmed and not _activity["busy"] and idle_for >= IDLE_TRIM_SECONDS:
                trimmed = True
                if trim_working_set():
                    _log(f"idle_trim after={idle_for:.0f}s")
            continue
        except Exception as e:
            _activity["busy"] = False
            _touch_activity()
            _log(f"Erro no worker thread: {e}")
            # A tarefa ja foi retirada da fila: sem o task_done o contador de
            # pendencias cresce a cada falha.
            try:
                _speech_queue.task_done()
            except ValueError:
                pass


def _make_engine(lang, config=None):
    from tts_engines import KokoroEngine, MockEngine

    config = config or {}
    engine_name = resolve_engine_name(os.environ.get("TTS_ENGINE"), config.get("engine"))
    if engine_name == "mock":
        _log("Usando engine mock para testes.")
        return MockEngine()
    return KokoroEngine(lang=lang, model=config.get("onnx_model"), g2p=config.get("onnx_g2p"))


def main():
    import socket

    positional = strip_cli_flags(sys.argv[1:])
    requested_lang = positional[0] if len(positional) > 0 else "a"
    lang = _normalize_lang(requested_lang)
    voice = positional[1] if len(positional) > 1 and positional[1] not in ("", "None") else DEFAULT_VOICE
    try:
        speed = float(positional[2]) if len(positional) > 2 else 1.25
    except Exception:
        speed = 1.25

    host = "127.0.0.1"
    config_file = os.path.join(here, "tts_config.json")
    configured_port = None
    cfg = {}
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            cfg = loaded if isinstance(loaded, dict) else {}
            if "port" in cfg:
                configured_port = int(cfg["port"])
        except Exception:
            pass

    cli_port = parse_cli_int_flag(sys.argv, "--port")
    parent_pid = parse_cli_int_flag(sys.argv, "--parent-pid")
    cli_idle = parse_cli_float_flag(sys.argv, "--idle-timeout")
    raw_cli_idle = None
    if "--idle-timeout" in sys.argv:
        idx = sys.argv.index("--idle-timeout")
        raw_cli_idle = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
    idle_timeout = resolve_idle_timeout(
        cli_idle if cli_idle is not None else raw_cli_idle,
        os.environ.get("TTS_IDLE_TIMEOUT"),
    )
    exit_on_disconnect = has_cli_flag(sys.argv, "--exit-on-disconnect")

    try:
        if cli_port is not None:
            port = cli_port
        elif "TTS_PORT" in os.environ:
            port = int(os.environ["TTS_PORT"])
        elif configured_port is not None:
            port = configured_port
        else:
            port = 5050
    except Exception:
        port = 5050
    engine_name = resolve_engine_name(os.environ.get("TTS_ENGINE"), cfg.get("engine"))

    _log(f"Iniciando servidor robusto (v2) em {host}:{port}...")
    _log(
        f"startup_context engine={engine_name} lang={lang} requested_lang={requested_lang} "
        f"voice={voice} port={port} speed={speed} parent_pid={parent_pid} "
        f"idle_timeout={idle_timeout} exit_on_disconnect={exit_on_disconnect} log_dir={log_dir}"
    )
    print(f"--- SERVIDOR TTS KOKORO ONLINE EM {host}:{port} ---")
    print("Aguardando conexao do jogo...")

    try:
        # Bind ANTES de importar modulos pesados ou mexer no tts_ready.txt.
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_sock.bind((host, port))
        except OSError as bind_error:
            try:
                server_sock.close()
            except Exception:
                pass
            message = (
                "porta {port} ja esta em uso por outra instancia do backend TTS. "
                "Feche o backend anterior (ou o jogo anterior) e execute novamente."
            ).format(port=port)
            _log(f"bind_failed port={port} error={bind_error}")
            print("!!! " + message)
            if not status_has_live_ready(status_path):
                with open(status_path, "w", encoding="utf-8") as f:
                    f.write("ERROR|" + message)
            return 1

        if os.path.exists(status_path):
            try:
                os.remove(status_path)
            except OSError:
                pass

        server_sock.listen(1)

        # Antes de importar o onnxruntime: poucos nucleos e prioridade abaixo do jogo.
        cpu_threads = resolve_cpu_threads(os.environ.get("TTS_THREADS"))
        apply_thread_env_limits(cpu_threads)
        low_priority = lower_process_priority(os.environ.get("TTS_PRIORITY"))
        _log(f"lightness cpu_threads={cpu_threads} low_priority={low_priority}")

        from text_cleaner import TextCleaner
        from tts_engines import get_available_voices

        engine = _make_engine(lang, cfg)

        t = threading.Thread(target=_worker, args=(engine, speed, voice), daemon=True)
        t.start()

        instance_token = _new_instance_token()
        voices_list = ",".join(get_available_voices())
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(f"READY|{instance_token}|{voices_list}")

        _touch_activity()
        _log("Servidor pronto.")
        print("Servidor inicializado com sucesso. Pressione Ctrl+C para encerrar.")

        active_conn = None
        conn_lock = threading.Lock()
        shutdown_event = threading.Event()

        def _trigger_shutdown(reason):
            if shutdown_event.is_set():
                return
            _log(reason)
            shutdown_event.set()
            remove_owned_status(status_path, instance_token)
            try:
                engine.stop()
            except Exception:
                pass
            with conn_lock:
                if active_conn is not None:
                    # conn.makefile("r") mantem refcount extra no socket: sem SHUT_RDWR,
                    # active_conn.close() nao desbloqueia f.readline() no Windows.
                    try:
                        active_conn.shutdown(socket.SHUT_RDWR)
                    except Exception:
                        pass
                    try:
                        active_conn.close()
                    except Exception:
                        pass
            try:
                server_sock.close()
            except Exception:
                pass

        if parent_pid and parent_pid > 0:
            def _watch_parent():
                while not shutdown_event.is_set():
                    if not is_pid_alive(parent_pid):
                        _trigger_shutdown(f"parent_exited pid={parent_pid}")
                        return
                    time.sleep(0.4)

            threading.Thread(target=_watch_parent, daemon=True).start()

        if idle_timeout > 0.0:
            poll_interval = min(0.5, max(0.05, idle_timeout / 4.0))

            def _watch_idle():
                while not shutdown_event.is_set():
                    idle_for = time.monotonic() - _activity["last_ts"]
                    if not _activity["busy"] and _speech_queue.empty() and idle_for >= idle_timeout:
                        print(f"[*] TTS ocioso por {idle_timeout:.1f}s — hibernando para liberar RAM/VRAM.")
                        _trigger_shutdown(f"idle_hibernate timeout={idle_timeout}")
                        return
                    time.sleep(poll_interval)

            threading.Thread(target=_watch_idle, daemon=True).start()

        def on_playback_done():
            _touch_activity()
            with conn_lock:
                if active_conn:
                    try:
                        active_conn.sendall((CMD_PLAYBACK_DONE + "\n").encode("utf-8"))
                    except Exception:
                        pass
        engine.on_playback_done = on_playback_done

        while not shutdown_event.is_set():
            try:
                conn, addr = server_sock.accept()
            except OSError:
                if shutdown_event.is_set():
                    return 0
                raise
            _touch_activity()
            _log(f"Conectado por {addr}")
            print(f"[*] Jogo conectado: {addr}")

            with conn_lock:
                active_conn = conn

            with conn:
                try:
                    for raw_line in iter_socket_lines(conn, shutdown_event):
                        line = raw_line.strip()
                        if not line:
                            continue
                        _touch_activity()

                        if line == CMD_STOP:
                            _log("command=STOP")
                            preserved = drain_preserving(_speech_queue)
                            try:
                                _speech_queue.put_nowait((CMD_STOP, None))
                            except Exception:
                                pass
                            for item in preserved:
                                try:
                                    _speech_queue.put_nowait(item)
                                except Exception:
                                    pass
                            continue
                        if line == CMD_QUIT:
                            _trigger_shutdown("command=QUIT")
                            return 0
                        if line.startswith(CMD_SET_SPEED + ":"):
                            raw_speed = line[10:].strip()
                            valid_speed = None
                            try:
                                import math
                                parsed = float(raw_speed)
                                if not math.isnan(parsed) and not math.isinf(parsed) and 0.1 <= parsed <= 5.0:
                                    valid_speed = parsed
                            except Exception:
                                pass
                            if valid_speed is not None:
                                speed = valid_speed
                                _log(f"command=SET_SPEED speed={speed}")
                                try:
                                    _speech_queue.put(("SET_SPEED", speed), timeout=0.5)
                                except Exception:
                                    pass
                            else:
                                _log(f"command=SET_SPEED ignored=invalid raw={raw_speed}")
                            continue
                        if line.startswith(CMD_SET_VOICE + ":"):
                            requested_voice = line[10:].strip()
                            if requested_voice:
                                voice = requested_voice
                                _log(f"command=SET_VOICE voice={voice}")
                                _speech_queue.put(("SET_VOICE", voice))
                            else:
                                _log("command=SET_VOICE ignored=empty")
                            continue
                        if line.startswith(CMD_SET_LANG + ":"):
                            normalized = _normalize_lang(line[9:].strip())
                            if normalized:
                                lang = normalized
                                _log(f"command=SET_LANG lang={lang}")
                                _speech_queue.put(("SET_LANG", lang))
                            else:
                                _log("command=SET_LANG ignored=empty")
                            continue
                        if line == CMD_HELLO or line.startswith(CMD_HELLO + ":"):
                            requested = line[6:].strip() if ":" in line else ""
                            if requested and requested != instance_token:
                                _log(f"handshake=token_mismatch requested={requested}")
                            else:
                                _log("handshake=ok")
                            try:
                                conn.sendall(("HELLO:" + instance_token + "\n").encode("utf-8"))
                            except Exception:
                                pass
                            continue

                        cleaned_text = TextCleaner.clean(line)
                        if cleaned_text:
                            print(f"\n[TEXTO RECEBIDO] {_preview_text(cleaned_text)}")
                            _log(f"text_preview={_preview_text(cleaned_text)}")
                            try:
                                _speech_queue.put(("SPEAK", cleaned_text), timeout=1.0)
                            except queue.Full:
                                _log("speech_queue=full dropped_oldest")
                                try:
                                    _speech_queue.get_nowait()
                                except Exception:
                                    pass
                                _speech_queue.put(("SPEAK", cleaned_text))
                        else:
                            _log("text_ignored=empty_after_cleaning")
                            print("[!] Texto vazio após limpeza (ignorado)")
                            on_playback_done()
                except Exception as ex:
                    if not shutdown_event.is_set():
                        _log(f"Connection error: {ex}")
                finally:
                    with conn_lock:
                        if active_conn is conn:
                            active_conn = None

            if not shutdown_event.is_set():
                if exit_on_disconnect:
                    print("[*] Jogo encerrado — desligando servidor TTS automaticamente.")
                    _trigger_shutdown("exit_on_disconnect=true")
                    return 0
                _log("Conexão encerrada pelo cliente.")
                print("[!] Jogo desconectado. Aguardando nova conexao...")
        return 0

    except Exception as e:
        _log(f"ERRO CRÍTICO: {e}")
        print(f"!!! ERRO CRITICO: {e}")
        with open(status_path, "w", encoding="utf-8") as f:
            f.write("ERROR|" + str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
