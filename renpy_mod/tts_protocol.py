# -*- coding: utf-8 -*-
"""Protocolo do socket TTS: comandos, regras de fila e utilitarios de runtime.

Fica em um modulo proprio, sem efeitos de import, para que as regras de fila,
rotacao de log, flags de CLI, hibernacao por ociosidade e verificacao de
processo pai possam ser testadas de forma deterministica sem subir um backend.
"""

import json
import math
import os
import time

# Comandos enviados pelo cliente ao backend.
CMD_STOP = "STOP"
CMD_SET_SPEED = "SET_SPEED"
CMD_SET_VOICE = "SET_VOICE"
CMD_SET_LANG = "SET_LANG"
CMD_HELLO = "HELLO"
CMD_QUIT = "QUIT"

# Comando enviado pelo backend ao cliente.
CMD_PLAYBACK_DONE = "PLAYBACK_DONE"

# Protocolo aceito pelo backend.
CLIENT_COMMANDS = (
    CMD_STOP,
    CMD_SET_SPEED,
    CMD_SET_VOICE,
    CMD_SET_LANG,
    CMD_HELLO,
    CMD_QUIT,
)

# Comandos enviados pelo backend ao cliente.
SERVER_COMMANDS = (CMD_PLAYBACK_DONE,)

# Comandos que o STOP preserva: o STOP cancela a fala pendente, nao a configuracao.
PRESERVED_ON_STOP = (CMD_SET_VOICE, CMD_SET_SPEED, CMD_SET_LANG)

# Limite padrao do log JSON do backend (2 MiB, com 1 backup .1).
DEFAULT_MAX_LOG_BYTES = 2 * 1024 * 1024

# Fechamento por ociosidade desativado por padrao (0.0); opt-in via --idle-timeout ou TTS_IDLE_TIMEOUT.
DEFAULT_IDLE_TIMEOUT_SECONDS = 0.0

VALUE_CLI_FLAGS = ("--port", "--parent-pid", "--idle-timeout")
BOOL_CLI_FLAGS = ("--exit-on-disconnect",)

LANG_ALIASES = {
    "en": "a", "en-us": "a", "english": "a", "us": "a",
    "en-gb": "b", "uk": "b", "british": "b",
    "es": "e", "spanish": "e", "fr": "f", "french": "f",
    "hi": "h", "hindi": "h", "it": "i", "italian": "i",
    "ja": "j", "jp": "j", "japanese": "j",
    "pt": "p", "pt-br": "p", "portuguese": "p",
    "zh": "z", "chinese": "z",
}


def normalize_lang_code(lang):
    key = str(lang or "a").strip().lower()
    return LANG_ALIASES.get(key, key or "a")


def status_has_live_ready(path):
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().startswith("READY|")
    except OSError:
        return False


def remove_owned_status(path, instance_token):
    if not instance_token or not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as handle:
            current = handle.read()
        if current.startswith(f"READY|{instance_token}|"):
            os.remove(path)
    except OSError:
        pass


def iter_socket_lines(conn, shutdown_event, timeout=0.4):
    """Le linhas UTF-8 de ``conn`` sem ``makefile()``, permitindo fechamento imediato no Windows."""
    import socket as socket_mod

    conn.settimeout(timeout)
    buf = b""
    while not shutdown_event.is_set():
        try:
            chunk = conn.recv(4096)
        except socket_mod.timeout:
            continue
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf and not shutdown_event.is_set():
            raw_line, buf = buf.split(b"\n", 1)
            yield raw_line.decode("utf-8", errors="replace")
    if buf and not shutdown_event.is_set():
        yield buf.decode("utf-8", errors="replace")


def parse_cli_int_flag(argv, flag):
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            try:
                return int(argv[i + 1])
            except ValueError:
                return None
    return None


def parse_cli_float_flag(argv, flag):
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            try:
                val = float(argv[i + 1])
                if not math.isnan(val) and not math.isinf(val):
                    return val
            except ValueError:
                return None
    return None


def has_cli_flag(argv, flag):
    return flag in argv


def strip_cli_flags(argv, value_flags=VALUE_CLI_FLAGS, bool_flags=BOOL_CLI_FLAGS):
    """Remove flags conhecidas da lista de argumentos preservando os posicionais."""
    positional = []
    skip_next = False
    for arg in argv:
        if skip_next:
            skip_next = False
            continue
        if arg in value_flags:
            skip_next = True
            continue
        if arg in bool_flags:
            continue
        positional.append(arg)
    return positional


def resolve_idle_timeout(cli_value=None, env_value=None, default=DEFAULT_IDLE_TIMEOUT_SECONDS):
    """Resolve o timeout de hibernacao (em segundos); <= 0 desativa (retorna 0.0)."""
    for candidate in (cli_value, env_value):
        if candidate is None or str(candidate).strip() == "":
            continue
        try:
            parsed = float(candidate)
        except (TypeError, ValueError):
            continue
        if math.isnan(parsed) or math.isinf(parsed):
            continue
        return 0.0 if parsed <= 0.0 else parsed
    return float(default)


def drain_preserving(queue_obj, preserved_commands=PRESERVED_ON_STOP):
    """Esvazia a fila de falas e devolve os itens de configuracao que sobrevivem a um STOP.

    Descarta a fala pendente e preserva a configuracao (voz, velocidade, idioma).
    Cada item descartado e liberado com task_done, senao o contador de tarefas
    pendentes da fila cresce a cada STOP.
    """
    import queue as queue_module

    preserved = []
    while not queue_obj.empty():
        try:
            item = queue_obj.get_nowait()
        except queue_module.Empty:
            break
        if item[0] in preserved_commands:
            preserved.append(item)
        try:
            queue_obj.task_done()
        except ValueError:
            pass
    return preserved


def _resolve_max_log_bytes(max_bytes=None):
    if max_bytes is not None:
        try:
            parsed = int(max_bytes)
            if parsed > 0:
                return parsed
        except (TypeError, ValueError):
            pass
    raw_env = os.environ.get("TTS_MAX_LOG_BYTES")
    if raw_env is not None:
        try:
            parsed_env = int(raw_env)
            if parsed_env > 0:
                return parsed_env
        except (TypeError, ValueError):
            pass
    return DEFAULT_MAX_LOG_BYTES


def append_bounded_log(log_path, msg, max_bytes=None):
    """Acrescenta uma linha JSON ao log, rotacionando para .1 ao atingir o teto."""
    limit = _resolve_max_log_bytes(max_bytes)
    entry = json.dumps({"timestamp": time.time(), "msg": msg}) + "\n"
    encoded_len = len(entry.encode("utf-8", errors="replace"))
    try:
        if os.path.isfile(log_path):
            current_size = os.path.getsize(log_path)
            if current_size > 0 and (current_size + encoded_len) > limit:
                os.replace(log_path, log_path + ".1")
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(entry)
    except OSError:
        pass


def is_pid_alive(pid):
    """Retorna True se o processo ``pid`` ainda estiver em execucao no SO."""
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False

    if os.name == "nt":
        import ctypes

        synchronize = 0x00100000
        wait_timeout = 0x00000102
        error_access_denied = 5
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(synchronize, False, pid_int)
        if not handle:
            return kernel32.GetLastError() == error_access_denied
        try:
            return kernel32.WaitForSingleObject(handle, 0) == wait_timeout
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid_int, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


# --- Leveza do backend -------------------------------------------------------
# O backend divide a maquina com o jogo e outros programas pesados. Por padrao
# ele usa poucos nucleos, roda com prioridade abaixo do normal e devolve ao
# Windows a RAM que nao esta usando quando fica ocioso.

THREAD_ENV_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
MAX_DEFAULT_CPU_THREADS = 4
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


def resolve_cpu_threads(env_value=None, cpu_count=None):
    """Threads de sintese: ``TTS_THREADS`` valido ou ~1/4 dos nucleos logicos (1..4)."""
    try:
        requested = int(str(env_value).strip())
        if requested > 0:
            return requested
    except (TypeError, ValueError):
        pass
    logical = cpu_count if cpu_count is not None else (os.cpu_count() or 4)
    return max(1, min(MAX_DEFAULT_CPU_THREADS, int(logical) // 4))


def apply_thread_env_limits(threads, environ=None):
    """Limita os pools OpenMP/MKL. Precisa rodar ANTES de importar o onnxruntime."""
    env = os.environ if environ is None else environ
    for name in THREAD_ENV_VARS:
        env.setdefault(name, str(threads))


def lower_process_priority(env_value=None):
    """Baixa a prioridade do processo para o jogo e o Windows terem preferencia.

    ``TTS_PRIORITY=normal`` desativa. Retorna True quando a prioridade mudou.
    """
    if str(env_value or "").strip().lower() == "normal":
        return False
    if os.name != "nt":
        try:
            os.nice(5)
            return True
        except (AttributeError, OSError):
            return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        return bool(kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS))
    except Exception:
        return False


def trim_working_set():
    """Devolve ao Windows as paginas de RAM que o backend nao esta tocando.

    O carregamento do modelo deixa centenas de MB de buffers mortos no heap.
    Sem o trim eles ficam na RAM fisica ate o Windows entrar em aperto. As
    paginas que a sintese realmente usa voltam sozinhas no proximo acesso.
    """
    if os.name != "nt":
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        psapi.EmptyWorkingSet.argtypes = [ctypes.c_void_p]
        return bool(psapi.EmptyWorkingSet(kernel32.GetCurrentProcess()))
    except Exception:
        return False


def resolve_engine_name(env_value=None, config_value=None):
    """Motor de sintese do backend: ``kokoro`` (ONNX Runtime) ou ``mock`` (testes).

    ``TTS_ENGINE=mock`` vence; o ``engine`` do ``tts_config.json`` tambem pode
    pedir ``mock``. Qualquer outro valor, incluindo o antigo ``onnx`` da fase de
    testes, cai no Kokoro.
    """
    for value in (env_value, config_value):
        if str(value or "").strip().lower() == "mock":
            return "mock"
    return "kokoro"
