"""
Teste ponta a ponta do backend Kokoro real, usando os arquivos instalados no
CampusConfidential: sobe o servidor da pasta game/ do jogo, manda uma fala e
confirma a sintese e o PLAYBACK_DONE.
"""
import os
import socket
import subprocess
import sys
import time

HOST = "127.0.0.1"


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def wait_for_port(port, deadline, process):
    last = None
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("servidor encerrou antes de abrir a porta: {}".format(process.returncode))
        try:
            sock = socket.create_connection((HOST, port), timeout=0.5)
            sock.close()
            return True
        except OSError as exc:
            last = exc
            time.sleep(0.5)
    raise TimeoutError("timeout abrindo a porta {}: {}".format(port, last))


def main():
    game_dir = sys.argv[1]
    python_exe = sys.argv[2]
    server = sys.argv[3] if len(sys.argv) > 3 else os.path.join(game_dir, "game", "tts_server.py")
    log_dir = os.path.join(game_dir, "game")
    port = free_port()

    env = os.environ.copy()
    env["TTS_ENGINE"] = "kokoro"
    env["TTS_LOG_DIR"] = log_dir
    env["TTS_PORT"] = str(port)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    print("iniciando backend real:", server)
    stdout_path = os.path.join(log_dir, "e2e_server_stdout.log")
    stdout_file = open(stdout_path, "w", encoding="utf-8")
    process = subprocess.Popen(
        [python_exe, "-u", server, "a", "af_heart", "1.0", "--port", str(port)],
        stdout=stdout_file, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env, cwd=game_dir,
    )

    ready_path = os.path.join(log_dir, "tts_ready.txt")
    if os.path.exists(ready_path):
        os.remove(ready_path)

    try:
        # O sinal de prontidao real e o arquivo tts_ready.txt.
        deadline = time.time() + 300
        while time.time() < deadline:
            if process.poll() is not None:
                raise RuntimeError("servidor encerrou antes de ficar pronto: {}".format(process.returncode))
            if os.path.isfile(ready_path):
                with open(ready_path, "r", encoding="utf-8") as f:
                    status = f.read().strip()
                if status.startswith("READY"):
                    print("pronto:", status[:120])
                    break
            time.sleep(1)
        else:
            raise TimeoutError("timeout aguardando tts_ready.txt")

        with socket.create_connection((HOST, port), timeout=10) as sock:
            sock.settimeout(120)
            stream = sock.makefile("r", encoding="utf-8", errors="replace")

            sock.sendall(b"HELLO\n")
            hello = stream.readline().strip()
            print("HELLO ->", hello)

            sock.sendall(b"SET_VOICE:af_bella\n")
            sock.sendall(b"SET_SPEED:1.1\n")
            line = "Good morning Professor Winters, I would like to ask about today's assignment."
            print("falando:", line)
            sock.sendall((line + "\n").encode("utf-8"))

            done = None
            deadline = time.time() + 120
            while time.time() < deadline:
                response = stream.readline()
                if not response:
                    break
                response = response.strip()
                print("  <-", response)
                if response == "PLAYBACK_DONE":
                    done = response
                    break

            sock.sendall(b"QUIT\n")

        print("PLAYBACK_DONE recebido:", bool(done))
    finally:
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
        stdout_file.close()

    print("exit code:", process.returncode)

    print("--- saida do servidor ---")
    if os.path.isfile(stdout_path):
        with open(stdout_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f.read().splitlines()[-25:]:
                print("   ", line[:220])

    log_path = os.path.join(log_dir, "tts_server.log")
    if os.path.isfile(log_path):
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().strip().splitlines()
        print("--- ultimas linhas do tts_server.log ---")
        for line in lines[-12:]:
            print("   ", line[:220])

    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
