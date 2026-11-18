import json
import os
import pickle
import sys
import tempfile
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


class FakePersistent(object):
    def __init__(self, **attributes):
        for name, value in attributes.items():
            setattr(self, name, value)


class FakeConfig(object):
    def __init__(self, gamedir=None, basedir=None):
        self.gamedir = gamedir
        self.basedir = basedir


class TestTTSClientState(unittest.TestCase):
    def test_state_is_restored_from_the_persistent(self):
        from renpy_mod.tts_client_state import TTSState

        persistent = FakePersistent(
            tts_auto_forward=True,
            tts_audio_enabled=False,
            tts_speed=1.75,
        )

        state = TTSState(persistent=persistent, default_voice="af_sarah")

        self.assertTrue(state.auto_forward)
        self.assertFalse(state.tts_audio_enabled)
        self.assertEqual(state.speed, 1.75)
        self.assertEqual(state.current_voice, "af_sarah")

    def test_missing_persistent_values_fall_back_to_the_defaults(self):
        from renpy_mod.tts_client_state import TTSState

        state = TTSState(persistent=None, default_voice="af_heart")

        self.assertFalse(state.auto_forward)
        self.assertTrue(state.tts_audio_enabled)
        self.assertEqual(state.speed, 1.25)
        self.assertEqual(state.current_voice, "af_heart")
        self.assertIsNone(state.sock)
        self.assertIsNone(state.proc)

    def test_a_saved_speed_of_none_does_not_break_the_state(self):
        from renpy_mod.tts_client_state import TTSState

        state = TTSState(persistent=FakePersistent(tts_speed=None))

        self.assertEqual(state.speed, 1.25)

    def test_the_voice_map_is_loaded_from_the_game_folder(self):
        from renpy_mod.tts_client_state import TTSState

        with tempfile.TemporaryDirectory() as gamedir:
            with open(os.path.join(gamedir, "voice_map.json"), "w", encoding="utf-8") as handle:
                json.dump({"Mia": "af_sarah"}, handle)

            state = TTSState(config=FakeConfig(gamedir=gamedir, basedir=None))

            self.assertEqual(state.voice_map, {"Mia": "af_sarah"})

    def test_the_voice_map_survives_a_save_and_load(self):
        """Um save antigo nao pode deixar o jogo sem o mapa de vozes."""
        from renpy_mod.tts_client_state import TTSState

        with tempfile.TemporaryDirectory() as gamedir:
            with open(os.path.join(gamedir, "voice_map.json"), "w", encoding="utf-8") as handle:
                json.dump({"Mia": "af_sarah"}, handle)

            state = TTSState(config=FakeConfig(gamedir=gamedir, basedir=None))
            state.speed = 2.0
            restored = pickle.loads(pickle.dumps(state))

            self.assertEqual(restored.speed, 2.0)
            self.assertEqual(restored.voice_map, {"Mia": "af_sarah"})

    def test_a_missing_voice_map_file_leaves_the_map_empty(self):
        from renpy_mod.tts_client_state import TTSState

        with tempfile.TemporaryDirectory() as gamedir:
            state = TTSState(config=FakeConfig(gamedir=gamedir, basedir=None))

            self.assertEqual(state.voice_map, {})
            self.assertIsNone(state.voice_map_error)

    def test_out_of_bounds_saved_speed_is_clamped_on_init_and_unpickle(self):
        from renpy_mod.tts_client_state import TTSState

        high = TTSState(persistent=FakePersistent(tts_speed=2.8))
        low = TTSState(persistent=FakePersistent(tts_speed=0.1))
        self.assertEqual(high.speed, 2.0)
        self.assertEqual(low.speed, 0.5)

        raw = pickle.dumps(high)
        restored = TTSState()
        restored.__setstate__({"speed": 2.9, "auto_forward": False})
        self.assertEqual(restored.speed, 2.0)
        self.assertIsNotNone(raw)

    def test_invalid_voice_map_records_diagnostic_error_instead_of_silent_pass(self):
        from renpy_mod.tts_client_state import TTSState

        with tempfile.TemporaryDirectory() as gamedir:
            bad_path = os.path.join(gamedir, "voice_map.json")
            with open(bad_path, "w", encoding="utf-8") as handle:
                handle.write("{broken json,")

            state = TTSState(config=FakeConfig(gamedir=gamedir, basedir=None))
            self.assertEqual(state.voice_map, {})
            self.assertIsNotNone(state.voice_map_error)
            self.assertIn("voice_map.json", state.voice_map_error)

            with open(bad_path, "w", encoding="utf-8") as handle:
                json.dump(["not", "a", "dict"], handle)

            notices = []
            state.reload_voice_map(notify=notices.append)
            self.assertIsNotNone(state.voice_map_error)
            self.assertIn("list", state.voice_map_error)
            self.assertEqual(len(notices), 1)


if __name__ == "__main__":
    unittest.main()
