import argparse
import json
import os
import subprocess
import sys

try:
    from falcom_textractor import build_dialogue_hook_code
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from falcom_textractor import build_dialogue_hook_code


GAME_EXECUTABLES = (
    "ed6_win2_DX9.exe",
    "ed6_win2.exe",
    "ed6_win_DX9.exe",
    "ed6_win.exe",
    "ed6_win3_DX9.exe",
    "ed6_win3.exe",
)


def find_game_executable(game_dir):
    """Retorna o primeiro executável ED6 suportado presente na pasta."""
    for filename in GAME_EXECUTABLES:
        if os.path.isfile(os.path.join(game_dir, filename)):
            return filename
    raise FileNotFoundError(f"Nenhum executável ED6 suportado em: {game_dir}")


def _terminate_owned_process(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def check_port_in_use(port=5050, host="127.0.0.1"):
    """Retorna True se a porta local estiver ocupada."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
        return False
    except OSError:
        return True


def get_configured_port(game_dir, default=5050):
    """Obtém a porta configurada via variável de ambiente TTS_PORT ou tts_config.json."""
    env_port = os.environ.get("TTS_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass
    config_file = os.path.join(game_dir, "tts_config.json")
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if "port" in cfg:
                    return int(cfg["port"])
        except Exception:
            pass
    return default


def run_launcher(game_dir, game_executable=None, python_executable=None, port=None):
    """Inicia backend, jogo, Textractor e bridge; encerra somente os filhos criados."""
    game_dir = os.path.abspath(game_dir)
    port = int(port) if port is not None else get_configured_port(game_dir)
    if check_port_in_use(port):
        print(f"[AVISO] Porta {port} ja em uso! Verifique se ha outro jogo ou tts_server aberto.")
    game_executable = game_executable or find_game_executable(game_dir)
    python_executable = python_executable or sys.executable
    backend = None
    hook = None

    game_path = os.path.join(game_dir, game_executable)
    textractor_dir = os.path.join(game_dir, "tts_textractor")
    textractor_cli = os.path.join(textractor_dir, "TextractorCLI.exe")
    if not os.path.isfile(textractor_cli):
        raise FileNotFoundError(
            f"TextractorCLI do mod não encontrado: {textractor_cli}. "
            "Execute novamente o instalador TTS."
        )
    hook_code = build_dialogue_hook_code(game_path)

    backend_log_path = os.path.join(game_dir, "tts_backend_console.log")
    hook_log_path = os.path.join(game_dir, "falcom_text_hook.log")
    print(f"[1/3] Backend TTS: {backend_log_path}")
    print(f"[2/3] Jogo: {game_executable}")
    print(f"[3/3] Bridge Textractor privado: {hook_log_path}")

    configured_speed = None
    config_file = os.path.join(game_dir, "tts_config.json")
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if "speed" in cfg:
                    configured_speed = str(cfg["speed"])
        except Exception:
            pass

    server_cmd = [python_executable, "-u", os.path.join(game_dir, "tts_server.py")]
    if configured_speed:
        server_cmd.extend(["a", "af_heart", configured_speed])

    server_env = os.environ.copy()
    server_env["TTS_PORT"] = str(port)

    with open(backend_log_path, "a", encoding="utf-8", buffering=1) as backend_log, open(
        hook_log_path, "a", encoding="utf-8", buffering=1
    ) as hook_log:
        try:
            backend = subprocess.Popen(
                server_cmd,
                cwd=game_dir,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
                env=server_env,
            )
            game = subprocess.Popen([game_path], cwd=game_dir)

            hook_cmd = [
                python_executable,
                "-u",
                os.path.join(game_dir, "falcom_text_hook.py"),
                "--textractor-cli",
                textractor_cli,
                "--pid",
                str(game.pid),
                "--hook-code",
                hook_code,
                "--port",
                str(port),
            ]
            if configured_speed:
                hook_cmd.extend(["--speed", configured_speed])

            hook = subprocess.Popen(
                hook_cmd,
                cwd=game_dir,
                stdout=hook_log,
                stderr=subprocess.STDOUT,
            )
            return game.wait()
        finally:
            _terminate_owned_process(hook)
            _terminate_owned_process(backend)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Launcher Kokoro TTS para Falcom ED6")
    parser.add_argument("--game-dir", default=os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--game-executable")
    parser.add_argument("--port", type=int, default=None, help="Porta TCP do servidor TTS")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        return run_launcher(args.game_dir, args.game_executable, port=args.port)
    except Exception as exc:
        print(f"[ERRO] Falha ao iniciar o mod TTS: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
