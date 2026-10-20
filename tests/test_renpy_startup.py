import os
import re
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TTS_MOD_PATH = os.path.join(ROOT_DIR, "renpy_mod", "tts_mod.rpy")


def read_client_module(filename):
    """Fonte de um modulo do cliente Ren'Py."""
    with open(os.path.join(ROOT_DIR, "renpy_mod", filename), "r", encoding="utf-8") as f:
        return f.read()


class TestRenpyStartupSafety(unittest.TestCase):
    def test_auto_connect_is_deferred_outside_init_block(self):
        with open(TTS_MOD_PATH, "r", encoding="utf-8") as f:
            source = f.read()

        init_match = re.search(r"init\s+(?:999|1000)\s+python:\s*(.*)\Z", source, re.S)
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

    def _module_source(self, filename):
        return read_client_module(filename)

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
        hooks = self._module_source("tts_client_hooks.py")

        self.assertIn("_tts_install_phone_callback_wrappers", source)
        self.assertIn("Phone_SendSound", source)
        self.assertIn("Phone_ReceiveSound", source)
        self.assertIn("original(event, interact=interact, **kwargs)", hooks)
        self.assertIn("on_text(extract_callback_text(kwargs))", hooks)

    def test_phone_callback_wrappers_patch_existing_function_references(self):
        hooks = self._module_source("tts_client_hooks.py")

        self.assertIn("patch_phone_callback_function", hooks)
        self.assertIn("types.FunctionType", hooks)
        self.assertIn("original.__code__ = patched.__code__", hooks)
        self.assertIn("setattr(store, name, patch_phone_callback_function(original, on_text))", hooks)

    def test_tts_speak_sends_stop_before_set_voice(self):
        body = self._module_source("tts_client_speech.py")

        self.assertIn('sendall(b"STOP\\n")', body)
        self.assertIn('"SET_VOICE:"', body)
        self.assertLess(body.index('sendall(b"STOP\\n")'), body.index('"SET_VOICE:"'))

    def test_gender_aware_voice_resolution(self):
        with open(os.path.join(ROOT_DIR, "renpy_mod", "tts_client_voice.py"), "r", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("FEMALE_POOL", source)
        self.assertIn("MALE_POOL", source)

    def test_client_reads_the_backend_instance_token_from_the_status_file(self):
        body = self._function_body("_tts_backend_instance_token")

        self.assertIn("tts_ready.txt", body)
        self.assertIn("READY|", body)

    def test_client_requests_the_instance_token_with_hello(self):
        body = self._function_body("_tts_send_hello")

        self.assertIn("HELLO", body)
        self.assertIn("sendall", body)

    def test_listener_rejects_a_backend_belonging_to_another_instance(self):
        body = self._function_body("_tts_socket_listener")

        self.assertIn("HELLO:", body)
        self.assertIn("expected_backend_token", body)

    def test_spawned_backend_token_is_captured_before_the_listener_starts(self):
        body = self._function_body("tts_connect")

        self.assertIn("expected_backend_token", body)
        self.assertIn("_tts_send_hello", body)


class TestRenpyAutoForwardLifecycle(unittest.TestCase):
    def _source(self):
        with open(TTS_MOD_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def _module_source(self, filename):
        return read_client_module(filename)

    def _function_body(self, name):
        source = self._source()
        match = re.search(r"(?ms)^    def " + re.escape(name) + r"\([^)]*\):\n(.*?)(?=^    def |^    class |^init python:|\Z)", source)
        self.assertIsNotNone(match, f"expected function {name} in tts_mod.rpy")
        return match.group(1)

    def test_no_problematic_afm_callback_blocking_auto_forward(self):
        source = self._source()
        self.assertNotIn(
            "config.afm_callback = _tts_afm_callback",
            source,
            "config.afm_callback must not be overridden with a function returning False, as Ren'Py cancels auto mode",
        )

    def test_tts_toggle_auto_synchronizes_preferences_and_forces_interaction_restart(self):
        body = self._module_source("tts_client_commands.py")
        self.assertIn("preferences.afm_enable", body)
        self.assertIn("preferences.afm_after_click", body)
        self.assertIn("preferences.afm_time", body)
        self.assertIn("restart_interaction()", body)

    def test_tts_toggle_auto_advances_immediately_if_not_playing(self):
        body = self._module_source("tts_client_commands.py")
        self.assertIn("auto_advance_flag", body)

    def test_auto_advance_action_synchronizes_quick_menu_and_respects_choice_screen(self):
        source = self._source()
        auto = self._module_source("tts_client_auto.py")
        self.assertIn("class TTSAutoAdvanceAction(Action):", source)
        self.assertIn('get_screen("choice")', auto)
        self.assertIn("end_interaction(True)", auto)
        self.assertIn("afm_after_click", auto)

    def test_screen_auto_button_accessible_regardless_of_socket(self):
        source = self._source()
        screen_match = re.search(r"(?ms)screen tts_auto_forward_checker\(\):.*?\Z", source)
        self.assertIsNotNone(screen_match)
        screen_body = screen_match.group(0)
        self.assertNotIn(
            "if tts_state.sock:\n        vbox:\n            xalign 0.99",
            screen_body,
            "Auto forward UI should not be hidden completely when socket is reconnecting or not yet initialized",
        )

    def test_tts_state_setstate_does_not_clobber_active_connection(self):
        with open(os.path.join(ROOT_DIR, "renpy_mod", "tts_client_state.py"), "r", encoding="utf-8") as f:
            source = f.read()
        self.assertIn("def __setstate__(self", source)
        setstate_match = re.search(r"(?ms)def __setstate__\(self, d\):.*?(?=def |\Z)", source)
        self.assertIsNotNone(setstate_match)
        setstate_body = setstate_match.group(0)
        self.assertIn("self.is_playing = False", setstate_body)

    def test_save_compat_hook_registered_and_safeguards_loads(self):
        source = self._source()
        hooks = self._module_source("tts_client_hooks.py")
        self.assertIn("_tts_install_save_compat_hook()", source)
        self.assertIn("def _tts_install_save_compat_hook():", source)
        self.assertIn('config.load_failed_label = "_after_load"', hooks)
        self.assertIn("script.has_label = compat_has_label", hooks)
        self.assertIn("script.lookup = compat_lookup", hooks)

    def test_auto_forward_watchdog_unfreezes_stuck_playback(self):
        auto = self._module_source("tts_client_auto.py")
        self.assertIn("speak_start_time", auto)
        self.assertIn("expected_duration", auto)
        self.assertIn("auto_advance_flag = True", auto)

    def test_toggle_auto_advances_if_audio_expired_or_stuck(self):
        body = self._module_source("tts_client_commands.py")
        self.assertIn("speak_start_time", body)
        self.assertIn("expected_duration", body)

    def test_keymap_covers_both_uppercase_and_lowercase_a(self):
        source = self._source()
        self.assertIn("'a': tts_toggle_auto", source)
        self.assertIn("'A': tts_toggle_auto", source)
        self.assertIn("'shift_K_a': tts_toggle_auto", source)
        self.assertIn("'K_a': tts_toggle_auto", source)
        self.assertIn("toggle_afm", source)

    def test_socket_disconnect_resets_is_playing(self):
        body = self._function_body("_tts_socket_listener")
        self.assertIn("tts_state.is_playing = False", body)

    def test_kokoro_engine_implements_stop_and_queue_drain(self):
        with open("renpy_mod/tts_engines.py", "r", encoding="utf-8") as f:
            engine_source = f.read()
        self.assertIn("def stop(self):", engine_source)
        stop_match = re.search(r"(?ms)class KokoroEngine.*?def stop\(self\):(.*?)(?=def |\Z)", engine_source)
        self.assertIsNotNone(stop_match, "KokoroEngine must implement stop()")
        stop_body = stop_match.group(1)
        self.assertIn("self.stop_flag = True", stop_body)
        self.assertIn('"STOP"', stop_body)

    def test_display_hook_installed_to_prevent_premature_renpy_say_advance(self):
        source = self._source()
        hooks = self._module_source("tts_client_hooks.py")
        self.assertIn("def _tts_install_display_hook():", source)
        self.assertIn("_tts_install_display_hook()", source)
        self.assertIn("renpy.display.tts", source)
        self.assertIn("is_active", hooks)

    def test_auto_advance_action_respects_post_playback_pause(self):
        auto = self._module_source("tts_client_auto.py")
        self.assertIn("playback_done_time", auto)

    def test_watchdog_uses_relaxed_timeout_to_never_cut_legitimate_speech(self):
        auto = self._module_source("tts_client_auto.py")
        # Deve usar no mínimo 30s ou 40s de tolerância para não cortar falas longas
        self.assertTrue(
            "30.0" in auto or "40.0" in auto,
            "Watchdog must have at least 30s tolerance to prevent cut-off",
        )


if __name__ == "__main__":
    unittest.main()

