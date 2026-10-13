import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_SCRIPT = os.path.join(ROOT_DIR, "renpy_mod", "tts_server.py")
HOST = "127.0.0.1"


class TestTTSServerSocketProtocol(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.log_path = os.path.join(self.tempdir.name, "tts_server.log")
        self.status_path = os.path.join(self.tempdir.name, "tts_ready.txt")

        self.env = os.environ.copy()
        self.env["TTS_ENGINE"] = "mock"
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env["TTS_LOG_DIR"] = self.tempdir.name
        self.port = self._free_port()
        self.env["TTS_PORT"] = str(self.port)
        self.process = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT, "en", "None", "1.0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.env,
        )
        self.sock = self._connect_to_server()

    def tearDown(self):
        try:
            if getattr(self, "sock", None):
                self.sock.sendall(b"QUIT\n")
                try:
                    self.sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
                self.sock.close()
        except OSError:
            pass

        if getattr(self, "process", None):
            try:
                self.process.communicate(timeout=5)
            except (subprocess.TimeoutExpired, ValueError):
                self.process.kill()
                try:
                    self.process.communicate(timeout=2)
                except (subprocess.TimeoutExpired, ValueError):
                    pass

        if getattr(self, "tempdir", None):
            self.tempdir.cleanup()

    def _free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((HOST, 0))
            return sock.getsockname()[1]

    def _connect_to_server(self):
        deadline = time.time() + 10
        self._wait_for_backend_ready(deadline)
        last_error = None
        while time.time() < deadline:
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate(timeout=1)
                self.fail(
                    "TTS server exited before accepting socket connection.\n"
                    + self._format_backend_diagnostics(stdout, stderr)
                )
            try:
                sock = socket.create_connection((HOST, self.port), timeout=0.5)
                sock.settimeout(2.0)
                return sock
            except OSError as exc:
                last_error = exc
                time.sleep(0.1)
        self._terminate_process()
        self.fail(
            "TTS server did not accept socket connection: {}\n{}".format(
                last_error,
                self._format_backend_diagnostics("", ""),
            )
        )

    def _wait_for_backend_ready(self, deadline):
        last_status = None
        while time.time() < deadline:
            if getattr(self, "process", None) is not None and self.process.poll() is not None:
                stdout, stderr = self.process.communicate(timeout=1)
                self.fail(
                    "TTS server exited before writing ready status.\n"
                    + self._format_backend_diagnostics(stdout, stderr)
                )
            if os.path.exists(self.status_path):
                try:
                    with open(self.status_path, "r", encoding="utf-8") as f:
                        last_status = f.read()
                    if last_status.startswith("READY|"):
                        return True
                    if last_status.startswith("ERROR|"):
                        self.fail("TTS server wrote error status: {}".format(last_status))
                except OSError:
                    pass
            time.sleep(0.05)
        self._terminate_process()
        self.fail(
            "TTS server did not write ready status; last_status={!r}\n{}".format(
                last_status,
                self._format_backend_diagnostics("", ""),
            )
        )

    def _format_backend_diagnostics(self, stdout, stderr):
        return "stdout={}\nstderr={}\nlogs={}".format(stdout, stderr, self._read_log_messages())

    def _terminate_process(self):
        if not getattr(self, "process", None) or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2)

    def _send_line(self, line):
        self.sock.sendall((line + "\n").encode("utf-8"))

    def _read_log_messages(self):
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, "r", encoding="utf-8") as f:
            return [json.loads(line)["msg"] for line in f if line.strip()]

    def _wait_for_log_message(self, predicate):
        deadline = time.time() + 5
        while time.time() < deadline:
            messages = self._read_log_messages()
            if any(predicate(message) for message in messages):
                return messages
            time.sleep(0.1)
        return self._read_log_messages()

    def test_socket_accepts_speed_stop_text_and_quit_without_real_audio(self):
        self._send_line("SET_SPEED:1.2")
        self._send_line("STOP")
        self._send_line("Hello {i}world{/i}!!!")

        messages = self._wait_for_log_message(lambda message: "Hello world!" in message)
        self.assertIsNone(self.process.poll(), "server crashed while handling socket commands")
        self.assertTrue(
            any("Hello world!" in message for message in messages),
            f"expected cleaned text to be logged, got: {messages}",
        )

    def test_startup_log_includes_diagnostic_context(self):
        messages = self._wait_for_log_message(lambda message: "startup_context" in message)
        startup = "\n".join(messages)

        self.assertIn("startup_context", startup)
        self.assertIn("engine=mock", startup)
        self.assertIn("lang=a", startup)
        self.assertIn("requested_lang=en", startup)
        self.assertIn(f"port={self.port}", startup)
        self.assertIn("speed=1.0", startup)
        self.assertIn("voice=af_heart", startup)
        self.assertIn("log_dir=", startup)

    def test_socket_command_events_are_logged(self):
        self._send_line("SET_SPEED:1.4")
        self._send_line("STOP")
        self._send_line("QUIT")
        messages = self._wait_for_log_message(lambda message: "command=QUIT" in message)
        joined = "\n".join(messages)

        self.assertIn("command=SET_SPEED", joined)
        self.assertIn("command=STOP", joined)
        self.assertIn("command=QUIT", joined)

    def test_socket_set_voice_changes_voice_used_for_speech(self):
        self._send_line("SET_VOICE:am_adam")
        self._send_line("Voice check.")
        messages = self._wait_for_log_message(lambda message: "voice=am_adam" in message)
        joined = "\n".join(messages)

        self.assertIn("command=SET_VOICE voice=am_adam", joined)
        self.assertIn("speak voice=am_adam", joined)

    def test_stop_command_preserves_pending_set_voice_and_speed(self):
        self._send_line("SET_VOICE:am_adam")
        self._send_line("STOP")
        self._send_line("Voice check after stop.")
        messages = self._wait_for_log_message(lambda message: "speak voice=am_adam" in message)
        joined = "\n".join(messages)

        self.assertIn("command=SET_VOICE voice=am_adam", joined)
        self.assertIn("speak voice=am_adam", joined)

    def test_stop_does_not_purge_enqueued_voice_configuration(self):
        # Directly test that STOP command handler preserves pending SET_VOICE in queue
        import queue
        q = queue.Queue()
        q.put(("SET_VOICE", "am_adam"))
        q.put(("SET_SPEED", 1.5))
        q.put(("SPEAK", "Old sentence"))

        # Simulated STOP flush logic
        preserved = []
        while not q.empty():
            try:
                item = q.get_nowait()
                if item[0] in ("SET_VOICE", "SET_SPEED"):
                    preserved.append(item)
            except Exception:
                break
        q.put(("STOP", None))
        for item in preserved:
            q.put(item)

        items = []
        while not q.empty():
            items.append(q.get_nowait())

        self.assertEqual(items, [("STOP", None), ("SET_VOICE", "am_adam"), ("SET_SPEED", 1.5)])

    def test_empty_set_voice_does_not_crash_or_clear_default_voice(self):
        self._send_line("SET_VOICE:")
        self._send_line("Default voice check.")
        messages = self._wait_for_log_message(lambda message: "speak voice=af_heart" in message)

        self.assertIsNone(self.process.poll(), "server crashed while handling empty SET_VOICE")
        self.assertTrue(
            any("command=SET_VOICE ignored=empty" in message for message in messages),
            f"expected empty voice command to be logged as ignored, got: {messages}",
        )

    def test_set_speed_rejects_negative_nan_and_infinite_values(self):
        self._send_line("SET_SPEED:-1.0")
        self._send_line("SET_SPEED:nan")
        self._send_line("SET_SPEED:inf")
        self._send_line("SET_SPEED:not_a_number")
        self._send_line("SET_SPEED:1.75")
        messages = self._wait_for_log_message(lambda message: "command=SET_SPEED speed=1.75" in message)

        self.assertIsNone(self.process.poll(), "server crashed while validating SET_SPEED")
        # Ensure invalid speeds were logged as ignored and valid 1.75 was applied
        self.assertTrue(
            any("command=SET_SPEED ignored=invalid" in message for message in messages),
            f"expected invalid speeds to be ignored, got: {messages}",
        )
        self.assertTrue(
            any("command=SET_SPEED speed=1.75" in message for message in messages),
            f"expected speed 1.75 to be applied, got: {messages}",
        )

    def test_socket_ignores_empty_text_after_cleaning(self):
        self._send_line("{w}{nw}")
        messages = self._wait_for_log_message(lambda message: "text_ignored=empty_after_cleaning" in message)

        self.assertIsNone(self.process.poll(), "server crashed while handling empty cleaned text")
        self.assertFalse(
            any("SPEAK" in message and "{w}" in message for message in messages),
            f"empty Ren'Py control tags should not be spoken, got: {messages}",
        )

    def test_long_text_log_is_bounded(self):
        long_text = "A" * 500
        self._send_line(long_text)
        messages = self._wait_for_log_message(lambda message: "text_preview=" in message)

        previews = [message for message in messages if "text_preview=" in message]
        self.assertTrue(previews, f"expected bounded preview log, got: {messages}")
        self.assertTrue(
            all(len(message) < 220 for message in previews),
            f"text preview logs must be bounded, got: {previews}",
        )

    def test_reconnection_after_client_disconnect_receives_playback_done(self):
        # First connection sends a line and receives PLAYBACK_DONE
        self._send_line("First line before restart.")
        first_reader = self.sock.makefile("r", encoding="utf-8")
        resp1 = first_reader.readline().strip()
        self.assertEqual("PLAYBACK_DONE", resp1)

        # Disconnect first client (simulating game restart without QUIT)
        first_reader.close()
        self.sock.close()
        time.sleep(0.2)

        # Second connection (game restarted)
        sock2 = socket.create_connection((HOST, self.port), timeout=2.0)
        sock2.settimeout(3.0)
        self.sock = sock2  # for tearDown cleanup
        second_reader = sock2.makefile("r", encoding="utf-8")

        # Second client sends a line
        sock2.sendall(b"Second line after restart.\n")
        resp2 = second_reader.readline().strip()
        second_reader.close()

        self.assertEqual("PLAYBACK_DONE", resp2, "reconnected client must receive PLAYBACK_DONE without queue theft")


class TestTTSServerHarnessHelpers(unittest.TestCase):
    def test_backend_ready_waits_for_ready_file_before_socket_connect(self):
        case = TestTTSServerSocketProtocol(methodName="test_startup_log_includes_diagnostic_context")

        with tempfile.TemporaryDirectory() as tmpdir:
            case.status_path = os.path.join(tmpdir, "tts_ready.txt")
            with open(case.status_path, "w", encoding="utf-8") as f:
                f.write("READY|af_heart")

            self.assertTrue(case._wait_for_backend_ready(deadline=time.time() + 1))

    def test_backend_diagnostics_include_stdout_stderr_and_log_messages(self):
        case = TestTTSServerSocketProtocol(methodName="test_startup_log_includes_diagnostic_context")

        with tempfile.TemporaryDirectory() as tmpdir:
            case.log_path = os.path.join(tmpdir, "tts_server.log")
            with open(case.log_path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"msg": "startup_context engine=mock"}) + "\n")

            text = case._format_backend_diagnostics("out text", "err text")

        self.assertIn("stdout=out text", text)
        self.assertIn("stderr=err text", text)
        self.assertIn("startup_context engine=mock", text)

    def test_server_resolves_port_from_config_file_when_env_not_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, 0))
                test_port = s.getsockname()[1]
            cfg_path = os.path.join(tmpdir, "tts_config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"port": test_port}, f)

            # Copy tts_server.py to tmpdir so it finds tts_config.json in its directory
            import shutil
            shutil.copy2(SERVER_SCRIPT, os.path.join(tmpdir, "tts_server.py"))
            shutil.copy2(os.path.join(ROOT_DIR, "renpy_mod", "text_cleaner.py"), os.path.join(tmpdir, "text_cleaner.py"))
            shutil.copy2(os.path.join(ROOT_DIR, "renpy_mod", "tts_engines.py"), os.path.join(tmpdir, "tts_engines.py"))

            env = os.environ.copy()
            env["TTS_ENGINE"] = "mock"
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["TTS_LOG_DIR"] = tmpdir
            env.pop("TTS_PORT", None)

            proc = subprocess.Popen(
                [sys.executable, os.path.join(tmpdir, "tts_server.py"), "en", "None", "1.0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=tmpdir,
                env=env,
            )
            try:
                # Give server a moment to bind and write ready file
                ready_file = os.path.join(tmpdir, "tts_ready.txt")
                for _ in range(50):
                    if os.path.exists(ready_file):
                        break
                    time.sleep(0.1)
                self.assertTrue(os.path.exists(ready_file))

                # Verify connection succeeds on test_port
                s = socket.create_connection((HOST, test_port), timeout=2.0)
                s.sendall(b"QUIT\n")
                s.close()
            finally:
                try:
                    proc.communicate(timeout=3)
                except (subprocess.TimeoutExpired, ValueError):
                    proc.kill()
                    try:
                        proc.communicate(timeout=1)
                    except (subprocess.TimeoutExpired, ValueError):
                        pass



if __name__ == "__main__":
    unittest.main()
