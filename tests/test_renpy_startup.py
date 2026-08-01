import os
import re
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTS_MOD_PATH = os.path.join(ROOT_DIR, "renpy_mod", "tts_mod.rpy")


class TestRenpyStartupSafety(unittest.TestCase):
    def test_auto_connect_is_deferred_outside_init_block(self):
        with open(TTS_MOD_PATH, "r", encoding="utf-8") as f:
            source = f.read()

        init_match = re.search(r"init\s+1000\s+python:\s*(.*)\Z", source, re.S)
        self.assertIsNotNone(init_match, "expected tts_mod.rpy to keep its init block")
        init_body = init_match.group(1)

        self.assertNotIn(
            "tts_connect(quiet=True)",
            init_body,
            "auto-connect must be deferred; calling tts_connect during init can crash renpy.notify",
        )
        self.assertIn(
            "config.start_callbacks.append",
            source,
            "startup connect should be registered for post-init execution",
        )

    def test_notify_calls_go_through_safe_helper(self):
        with open(TTS_MOD_PATH, "r", encoding="utf-8") as f:
            source = f.read()

        direct_notify_calls = re.findall(r"(?<!def\s)renpy\.notify\(", source)
        self.assertEqual(
            [],
            direct_notify_calls,
            "use a safe notification helper instead of direct renpy.notify calls",
        )


class TestRenpyBackendLifecycle(unittest.TestCase):
    def _source(self):
        with open(TTS_MOD_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def _function_body(self, name):
        source = self._source()
        match = re.search(r"(?ms)^    def " + re.escape(name) + r"\([^)]*\):\n(.*?)(?=^    def |^    class |\Z)", source)
        self.assertIsNotNone(match, f"expected function {name} in tts_mod.rpy")
        return match.group(1)

    def test_tts_kill_sends_quit_before_closing_socket(self):
        body = self._function_body("tts_kill")

        self.assertIn('sendall(b"QUIT\\n")', body)
        self.assertLess(body.index('sendall(b"QUIT\\n")'), body.index("tts_state.sock.close()"))

    def test_tts_kill_waits_then_escalates_backend_process_shutdown(self):
        body = self._function_body("tts_kill")

        self.assertIn("tts_state.proc.terminate()", body)
        self.assertIn("tts_state.proc.wait", body)
        self.assertIn("tts_state.proc.kill()", body)
        self.assertLess(body.index("tts_state.proc.terminate()"), body.index("tts_state.proc.wait"))
        self.assertLess(body.index("tts_state.proc.wait"), body.index("tts_state.proc.kill()"))

    def test_socket_health_check_clears_bad_socket_reference(self):
        body = self._function_body("tts_connect")
        bad_socket_block = re.search(r"(?ms)if tts_state\.sock:.*?except.*?tts_state\.sock\s*=\s*None", body)

        self.assertIsNotNone(
            bad_socket_block,
            "failed socket health check must clear tts_state.sock before reconnecting",
        )

    def test_status_helper_reports_socket_process_and_speed(self):
        body = self._function_body("tts_status_message")

        self.assertIn("tts_state.sock", body)
        self.assertIn("tts_state.proc", body)
        self.assertIn("tts_state.speed", body)
        self.assertIn("socket=", body)
        self.assertIn("process=", body)
        self.assertIn("speed=", body)

    def test_renpy_startup_exposes_and_passes_configured_voice(self):
        source = self._source()

        self.assertIn('TTS_LANG = "a"', source)
        self.assertIn('TTS_VOICE = "af_heart"', source)
        self.assertIn("TTS_VOICE", source)
        self.assertIn("server_script, TTS_LANG, TTS_VOICE", source)

    def test_phone_callback_wrappers_preserve_custom_callbacks_and_speak_text(self):
        source = self._source()

        self.assertIn("_tts_install_phone_callback_wrappers", source)
        self.assertIn("Phone_SendSound", source)
        self.assertIn("Phone_ReceiveSound", source)
        self.assertIn("original(event, interact=interact, **kwargs)", source)
        self.assertIn("tts_speak_once(_tts_extract_callback_text(kwargs))", source)

    def test_phone_callback_wrappers_patch_existing_function_references(self):
        source = self._source()

        self.assertIn("_tts_patch_phone_callback_function", source)
        self.assertIn("types.FunctionType", source)
        self.assertIn("original.__code__ = patched.__code__", source)
        self.assertIn("setattr(renpy.store, name, _tts_patch_phone_callback_function(original))", source)


if __name__ == "__main__":
    unittest.main()
