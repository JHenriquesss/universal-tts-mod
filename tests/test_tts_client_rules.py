import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
for path in (ROOT_DIR, RENPY_MOD_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from tts_client_auto import (
    next_native_voice_state,
    playback_timed_out,
    should_end_interaction,
    unvoiced_reading_delay,
)
from tts_client_commands import (
    decrease_speed,
    increase_speed,
    send_speed,
    toggle_audio,
    toggle_auto,
)
from tts_client_hooks import (
    extract_callback_text,
    install_display_hook,
    install_phone_callback_wrappers,
    install_save_compat_hook,
    wrap_phone_callback,
)


class FakeSocket(object):
    def __init__(self):
        self.sent = []

    def sendall(self, payload):
        self.sent.append(payload)


class FakeState(object):
    def __init__(self, **attributes):
        self.speed = 1.25
        self.sock = None
        self.auto_forward = False
        self.tts_audio_enabled = True
        self.is_playing = False
        self.speak_start_time = 0.0
        self.expected_duration = 5.0
        self.playback_done_time = 0.0
        self.auto_advance_flag = False
        for name, value in attributes.items():
            setattr(self, name, value)


class FakePreferences(object):
    def __init__(self, afm_enable=False):
        self.afm_enable = afm_enable
        self.afm_after_click = False
        self.afm_time = 0


class FakePersistent(object):
    pass


class TestTTSClientHooks(unittest.TestCase):
    def test_extract_callback_text_finds_the_spoken_text(self):
        self.assertEqual(extract_callback_text({"what": "Oi"}), "Oi")
        self.assertEqual(extract_callback_text({"text": "Oi"}), "Oi")
        self.assertEqual(extract_callback_text({"message": "Oi"}), "Oi")
        self.assertIsNone(extract_callback_text({}))
        self.assertIsNone(extract_callback_text(None))

    def test_wrapped_callback_speaks_on_begin_and_show_done(self):
        spoken = []

        def original(event, interact=True, **kwargs):
            return event

        wrapped = wrap_phone_callback(original, spoken.append)

        wrapped("begin", what="Oi")
        wrapped("show_done", what="Tchau")
        wrapped("other", what="Nada")

        self.assertEqual(spoken, ["Oi", "Tchau"])

    def test_wrapped_callback_survives_a_callback_without_interact(self):
        seen = []

        def original(event, **kwargs):
            seen.append(event)

        wrap_phone_callback(original, lambda text: None)("begin", what="Oi")

        self.assertEqual(seen, ["begin"])

    def test_phone_callback_wrappers_patch_the_store(self):
        spoken = []
        store = type("Store", (), {"Phone_SendSound": staticmethod(lambda event, **kwargs: None)})()

        install_phone_callback_wrappers(store, spoken.append)

        self.assertTrue(getattr(store.Phone_SendSound, "_tts_wrapped", False))

    def test_save_compat_hook_resolves_an_old_statement(self):
        class FakeScript(object):
            def __init__(self):
                self.namemap = {
                    ("a.rpy", 1, 5): "start",
                    ("a.rpy", 2, 7): "start",
                }

            def has_label(self, label):
                return label in self.namemap

            def lookup(self, label):
                return self.namemap[label]

        script = FakeScript()
        config = type("Config", (), {})()

        install_save_compat_hook(script, config=config)

        self.assertTrue(script.has_label(("a.rpy", 1, 5)))
        self.assertEqual(script.lookup(("a.rpy", 1, 5)), "start")
        self.assertEqual(config.load_failed_label, "_after_load")

    def test_save_compat_hook_ignores_a_script_without_namemap(self):
        install_save_compat_hook(None, config=None, store=None)

    def test_display_hook_reports_the_tts_as_active_while_playing(self):
        class FakeDisplayTTS(object):
            def is_active(self):
                return False

        display = FakeDisplayTTS()
        playing = {"value": False}

        install_display_hook(display, lambda: playing["value"])

        self.assertFalse(display.is_active())
        playing["value"] = True
        self.assertTrue(display.is_active())


class TestTTSClientAuto(unittest.TestCase):
    def test_playback_timed_out_only_after_the_expected_time(self):
        self.assertFalse(playback_timed_out(False, 0.0, 5.0, 1000.0))
        self.assertFalse(playback_timed_out(True, 0.0, 5.0, 10.0))
        self.assertTrue(playback_timed_out(True, 0.0, 5.0, 1000.0))

    def test_unvoiced_reading_delay_grows_with_the_line(self):
        self.assertGreaterEqual(unvoiced_reading_delay("a" * 400), 5.0)
        self.assertGreaterEqual(unvoiced_reading_delay(""), 2.0)
        self.assertLess(unvoiced_reading_delay("curta"), 3.0)

    def test_native_voice_state_marks_the_end_of_the_audio(self):
        detected, end_time, finished = next_native_voice_state(False, None, True, 100.0)
        self.assertTrue(detected)
        self.assertIsNone(end_time)
        self.assertFalse(finished)

        detected, end_time, finished = next_native_voice_state(True, None, False, 100.0)
        self.assertTrue(detected)
        self.assertEqual(end_time, 100.0)
        self.assertFalse(finished)

        detected, end_time, finished = next_native_voice_state(True, 100.0, False, 101.0)
        self.assertFalse(detected)
        self.assertTrue(finished)

    def test_the_interaction_ends_only_outside_a_choice(self):
        self.assertFalse(should_end_interaction(True, True, True, 0.0, 10.0))
        self.assertFalse(should_end_interaction(False, True, False, 0.0, 10.0))
        self.assertFalse(should_end_interaction(True, False, False, 0.0, 10.0))
        self.assertFalse(should_end_interaction(True, True, False, 10.0, 10.1))
        self.assertTrue(should_end_interaction(True, True, False, 0.0, 10.0))


class TestTTSClientCommands(unittest.TestCase):
    def test_send_speed_notifies_and_sends_the_command(self):
        messages = []
        state = FakeState(speed=1.5, sock=FakeSocket())

        send_speed(state, messages.append)

        self.assertEqual(messages, ["Velocidade TTS: 1.50x"])
        self.assertEqual(state.sock.sent, [b"SET_SPEED:1.5\n"])

    def test_speed_changes_are_clamped_and_saved(self):
        messages = []
        persistent = FakePersistent()
        state = FakeState(speed=1.25, sock=FakeSocket())

        increase_speed(state, persistent, messages.append)
        self.assertEqual(state.speed, 1.35)
        self.assertEqual(persistent.tts_speed, 1.35)

        state.speed = 0.55
        decrease_speed(state, persistent, messages.append)
        self.assertEqual(state.speed, 0.5)

        state.speed = 3.0
        increase_speed(state, persistent, messages.append)
        self.assertEqual(state.speed, 3.0)

    def test_toggle_auto_syncs_the_preferences_and_saves_the_choice(self):
        messages = []
        persistent = FakePersistent()
        preferences = FakePreferences()
        restarted = []
        state = FakeState()

        toggle_auto(state, persistent, preferences, messages.append, lambda: restarted.append(True))

        self.assertTrue(state.auto_forward)
        self.assertTrue(preferences.afm_enable)
        self.assertTrue(preferences.afm_after_click)
        self.assertEqual(preferences.afm_time, 15.0)
        self.assertTrue(persistent.tts_auto_forward)
        self.assertEqual(len(restarted), 1)

    def test_toggle_auto_releases_a_line_whose_audio_expired(self):
        persistent = FakePersistent()
        preferences = FakePreferences()
        state = FakeState(is_playing=True, speak_start_time=0.0, expected_duration=5.0)

        toggle_auto(
            state,
            persistent,
            preferences,
            lambda message: None,
            lambda: None,
            now=1000.0,
        )

        self.assertFalse(state.is_playing)
        self.assertTrue(state.auto_advance_flag)

    def test_toggle_audio_stops_the_playback_when_it_turns_off(self):
        messages = []
        persistent = FakePersistent()
        state = FakeState(tts_audio_enabled=True, sock=FakeSocket(), is_playing=True)

        result = toggle_audio(state, persistent, messages.append, lambda: None)

        self.assertFalse(result)
        self.assertFalse(state.tts_audio_enabled)
        self.assertEqual(state.sock.sent, [b"STOP\n"])
        self.assertFalse(state.is_playing)
        self.assertFalse(persistent.tts_audio_enabled)


if __name__ == "__main__":
    unittest.main()
