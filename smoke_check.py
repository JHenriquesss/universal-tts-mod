import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass


HOST = "127.0.0.1"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SERVER_SCRIPT = os.path.join(ROOT_DIR, "renpy_mod", "tts_server.py")


@dataclass
class SmokeCheckResult:
    ok: bool
    message: str
    port: int | None = None
    returncode: int | None = None
    log_messages: list[str] | None = None


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def _read_log_messages(log_path):
    if not os.path.exists(log_path):
        return []
    messages = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line).get("msg", ""))
            except json.JSONDecodeError:
                messages.append(line)
    return messages


def _terminate(process):
    if process.poll() is not None:
        return process.returncode
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    return process.returncode


def _connect(process, port, deadline):
    last_error = None
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"backend exited before accepting connection: {process.returncode}")
        try:
            sock = socket.create_connection((HOST, port), timeout=0.25)
            sock.settimeout(1.0)
            return sock
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    raise TimeoutError(f"timeout waiting for backend socket: {last_error}")


def run_smoke_check(server_script=DEFAULT_SERVER_SCRIPT, log_dir=None, timeout=10):
    port = _free_port()
    owns_log_dir = log_dir is None
    tempdir = tempfile.TemporaryDirectory() if owns_log_dir else None
    log_dir = tempdir.name if tempdir else log_dir
    log_path = os.path.join(log_dir, "tts_server.log")
    env = os.environ.copy()
    env["TTS_ENGINE"] = "mock"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TTS_LOG_DIR"] = log_dir
    env["TTS_PORT"] = str(port)
    process = None

    try:
        process = subprocess.Popen(
            [sys.executable, server_script, "en", "None", "1.0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        deadline = time.time() + timeout
        with _connect(process, port, deadline) as sock:
            sock.sendall(b"SET_SPEED:1.1\n")
            sock.sendall(b"Smoke check line.\n")
            sock.sendall(b"QUIT\n")

        remaining = max(0.1, deadline - time.time())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            _terminate(process)
            messages = _read_log_messages(log_path)
            return SmokeCheckResult(False, f"timeout waiting for backend exit: {exc}", port, process.returncode, messages)

        messages = _read_log_messages(log_path)
        if process.returncode != 0:
            return SmokeCheckResult(False, f"backend exited with {process.returncode}", port, process.returncode, messages)
        return SmokeCheckResult(True, "backend smoke check passed", port, process.returncode, messages)
    except Exception as exc:
        if process is not None:
            _terminate(process)
        messages = _read_log_messages(log_path)
        return SmokeCheckResult(False, str(exc), port, process.returncode if process else None, messages)
    finally:
        if process is not None:
            for stream_name in ("stdout", "stderr"):
                stream = getattr(process, stream_name, None)
                if stream:
                    stream.close()
        if tempdir is not None:
            tempdir.cleanup()


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Run a mock-engine smoke check against the TTS socket backend.")
    parser.add_argument("--server-script", default=DEFAULT_SERVER_SCRIPT)
    parser.add_argument("--log-dir", default=None)
    parser.add_argument("--timeout", type=float, default=10)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    result = run_smoke_check(args.server_script, args.log_dir, args.timeout)
    print(result.message)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
