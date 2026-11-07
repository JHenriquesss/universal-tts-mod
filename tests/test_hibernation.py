"""Testes de desligamento controlado, opt-in de ociosidade, auto-wake e JOGAR_COM_TTS.bat."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import types
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
SERVER_SCRIPT = os.path.join(RENPY_MOD_DIR, "tts_server.py")

if RENPY_MOD_DIR not in sys.path:
    sys.path.insert(0, RENPY_MOD_DIR)

import tts_client_commands  # noqa: E402
import tts_protocol  # noqa: E402


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_ready(status_path, timeout=8.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if os.path.isfile(status_path):
            with open(status_path, "r", encoding="utf-8") as handle:
                content = handle.read().strip()
            if content.startswith("READY|"):
                return content
        time.sleep(0.05)
    raise AssertionError(f"Backend did not publish READY| in {status_path}")


def _read_log_messages(log_path):
    if not os.path.isfile(log_path):
        return []
    messages = []
    with open(log_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                messages.append(json.loads(line).get("msg", ""))
    return messages


def _extract_init_999_python():
    with open(os.path.join(RENPY_MOD_DIR, "tts_mod.rpy"), "r", encoding="utf-8") as handle:
        source = handle.read()
    block = source.split("init 999 python:\n", 1)[1].split("\ninit python:", 1)[0]
    return textwrap.dedent(block)


class HibernationProtocolAndLauncherTest(unittest.TestCase):
    def test_idle_timeout_is_disabled_by_default_and_supports_explicit_opt_in(self):
        self.assertEqual(tts_protocol.DEFAULT_IDLE_TIMEOUT_SECONDS, 0.0)
        self.assertEqual(tts_protocol.resolve_idle_timeout(None, None), 0.0)
        self.assertEqual(tts_protocol.resolve_idle_timeout("45", None), 45.0)
        self.assertEqual(tts_protocol.resolve_idle_timeout(None, "120.5"), 120.5)
        self.assertEqual(tts_protocol.resolve_idle_timeout("0", "120"), 0.0)
        self.assertEqual(tts_protocol.resolve_idle_timeout("-15", "120"), 0.0)
        self.assertEqual(tts_protocol.resolve_idle_timeout(None, "0"), 0.0)
        self.assertEqual(tts_protocol.resolve_idle_timeout("not-a-number", None), 0.0)
        self.assertEqual(tts_protocol.resolve_idle_timeout("nan", None), 0.0)

        argv = [
            "tts_server.py",
            "a",
            "af_heart",
            "1.35",
            "--exit-on-disconnect",
            "--idle-timeout",
            "180",
            "--parent-pid",
            "4242",
        ]
        self.assertTrue(tts_protocol.has_cli_flag(argv, "--exit-on-disconnect"))
        self.assertEqual(tts_protocol.parse_cli_float_flag(argv, "--idle-timeout"), 180.0)
        self.assertEqual(tts_protocol.parse_cli_int_flag(argv, "--parent-pid"), 4242)
        self.assertEqual(tts_protocol.strip_cli_flags(argv[1:]), ["a", "af_heart", "1.35"])

    def test_jogar_com_tts_bat_passes_exit_on_disconnect_to_run_backend(self):
        with open(os.path.join(RENPY_MOD_DIR, "JOGAR_COM_TTS.bat"), "r", encoding="utf-8") as f:
            jogar_bat = f.read()
        with open(os.path.join(RENPY_MOD_DIR, "run_backend.bat"), "r", encoding="utf-8") as f:
            run_bat = f.read()

        self.assertIn("run_backend.bat --exit-on-disconnect", jogar_bat)
        self.assertIn("%*", run_bat)

    def test_opted_in_idle_timeout_unblocks_connected_client_readline_immediately(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            port = _free_port()
            status_path = os.path.join(tmpdir, "tts_ready.txt")
            log_path = os.path.join(tmpdir, "tts_server.log")
            env = os.environ.copy()
            env["TTS_ENGINE"] = "mock"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["TTS_LOG_DIR"] = tmpdir
            env["TTS_PORT"] = str(port)

            proc = subprocess.Popen(
                [sys.executable, SERVER_SCRIPT, "en", "None", "1.0", "--idle-timeout", "0.45"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            client = None
            try:
                _wait_for_ready(status_path)
                # Keep a live TCP client connected so the server sits inside
                # conn.makefile("r").readline() when the idle timer fires.
                client = socket.create_connection(("127.0.0.1", port), timeout=3.0)
                client.sendall(b"HELLO\n")
                reply = client.makefile("r", encoding="utf-8").readline().strip()
                self.assertTrue(reply.startswith("HELLO:"))

                returncode = proc.wait(timeout=3.0)
                self.assertEqual(returncode, 0)
                self.assertFalse(os.path.exists(status_path))
                logs = _read_log_messages(log_path)
                self.assertTrue(any("idle_hibernate" in msg for msg in logs), logs)
            finally:
                if client is not None:
                    try:
                        client.close()
                    except OSError:
                        pass
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=2)
                for s in (proc.stdout, proc.stderr):
                    if s is not None:
                        s.close()

    def test_server_exits_when_client_disconnects_with_exit_on_disconnect_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            port = _free_port()
            status_path = os.path.join(tmpdir, "tts_ready.txt")
            log_path = os.path.join(tmpdir, "tts_server.log")
            env = os.environ.copy()
            env["TTS_ENGINE"] = "mock"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["TTS_LOG_DIR"] = tmpdir
            env["TTS_PORT"] = str(port)
            env.pop("TTS_IDLE_TIMEOUT", None)

            proc = subprocess.Popen(
                [sys.executable, SERVER_SCRIPT, "--exit-on-disconnect"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            try:
                _wait_for_ready(status_path)
                with socket.create_connection(("127.0.0.1", port), timeout=3.0) as client:
                    client.sendall(b"HELLO\n")
                    reply = client.makefile("r", encoding="utf-8").readline().strip()
                    self.assertTrue(reply.startswith("HELLO:"))

                returncode = proc.wait(timeout=5.0)
                self.assertEqual(returncode, 0)
                self.assertFalse(os.path.exists(status_path))
                logs = _read_log_messages(log_path)
                self.assertIn("idle_timeout=0.0", "\n".join(logs))
                self.assertTrue(any("exit_on_disconnect=true" in msg for msg in logs), logs)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=2)
                for s in (proc.stdout, proc.stderr):
                    if s is not None:
                        s.close()


class ClientHibernateAndAutoWakeTest(unittest.TestCase):
    def test_toggle_audio_calls_on_disable_and_on_enable_hooks(self):
        events = []
        sock = types.SimpleNamespace(sent=[], sendall=lambda data: sock.sent.append(data))
        state = types.SimpleNamespace(
            tts_audio_enabled=True,
            sock=sock,
            is_playing=True,
            pending_speech=("stale line", "af_heart"),
        )
        persistent = types.SimpleNamespace(tts_audio_enabled=True)

        off_res = tts_client_commands.toggle_audio(
            state,
            persistent,
            lambda msg: events.append(msg),
            lambda: None,
            on_disable=lambda: events.append("disabled_hook"),
            on_enable=lambda: events.append("enabled_hook"),
        )
        self.assertFalse(off_res)
        self.assertIsNone(state.pending_speech)
        self.assertIn(b"STOP\n", sock.sent)
        self.assertIn("disabled_hook", events)
        self.assertNotIn("enabled_hook", events)

        events.clear()
        on_res = tts_client_commands.toggle_audio(
            state,
            persistent,
            lambda msg: events.append(msg),
            lambda: None,
            on_disable=lambda: events.append("disabled_hook"),
            on_enable=lambda: events.append("enabled_hook"),
        )
        self.assertTrue(on_res)
        self.assertIn("enabled_hook", events)
        self.assertNotIn("disabled_hook", events)

    def test_renpy_client_hibernates_on_audio_off_and_auto_wakes_pending_speech(self):
        code = _extract_init_999_python()
        with tempfile.TemporaryDirectory() as gamedir:
            fake_cfg = types.SimpleNamespace(
                gamedir=gamedir,
                basedir=gamedir,
                all_character_callbacks=[],
                underlay=[],
                keymap={},
                start_callbacks=[],
                after_load_callbacks=[],
                quit_callbacks=[],
                overlay_screens=[],
            )
            persistent = types.SimpleNamespace(
                tts_auto_forward=False,
                tts_audio_enabled=False,
                tts_speed=1.25,
            )
            preferences = types.SimpleNamespace(afm_enable=False, afm_after_click=True, afm_time=15.0)
            store = types.SimpleNamespace(_preferences=preferences)
            fake_renpy = types.SimpleNamespace(
                config=fake_cfg,
                store=store,
                persistent=persistent,
                game=types.SimpleNamespace(script=None),
                Keymap=lambda **kw: kw,
                notify=lambda msg: None,
                substitute=lambda s: s,
                restart_interaction=lambda: None,
            )
            ns = {
                "renpy": fake_renpy,
                "config": fake_cfg,
                "persistent": persistent,
                "_preferences": preferences,
            }
            exec(compile(code, "tts_mod.rpy", "exec"), ns)
            import atexit
            atexit.unregister(ns["tts_shutdown"])

            state = ns["tts_state"]
            connect_calls = []
            ns["tts_connect"] = lambda quiet=False: connect_calls.append(quiet) or True

            state.tts_audio_enabled = False
            ns["tts_speak"]("Muted line", voice="af_heart")
            self.assertIsNone(state.pending_speech)
            self.assertEqual(connect_calls, [])

            state.tts_audio_enabled = True
            state.sock = None
            state.connecting = False
            ns["tts_speak"]("Hello after LoL match", voice="am_adam")
            time.sleep(0.05)
            self.assertEqual(state.pending_speech, ("Hello after LoL match", "am_adam"))
            self.assertEqual(connect_calls, [True])

            sent_packets = []
            state.sock = types.SimpleNamespace(sendall=lambda data: sent_packets.append(data))
            ns["_tts_flush_pending_speech"]()
            self.assertIsNone(state.pending_speech)
            joined = b"".join(sent_packets)
            self.assertIn(b"SET_VOICE:am_adam\n", joined)
            self.assertIn(b"Hello after LoL match\n", joined)


if __name__ == "__main__":
    unittest.main()
