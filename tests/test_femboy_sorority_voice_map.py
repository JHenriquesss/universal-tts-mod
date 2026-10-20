import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "femboy_sorority_voice_map.json")
CHOICE_HINTS_SAMPLE = os.path.join(SAMPLES_DIR, "femboy_sorority_choice_hints_generated.rpy")
TARGET_GAME_ROOT = r"D:\Games\FemboySorority-0.4-Public-pc\FemboySorority-0.4-pc"
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestFemboySororityVoiceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(VOICE_MAP_SAMPLE):
            with open(VOICE_MAP_SAMPLE, "r", encoding="utf-8") as f:
                cls.voice_map_data = json.load(f)
        else:
            cls.voice_map_data = {}

    def test_voice_map_sample_exists_and_loaded(self):
        self.assertTrue(
            os.path.exists(VOICE_MAP_SAMPLE),
            f"Sample file {VOICE_MAP_SAMPLE} does not exist",
        )
        self.assertGreater(len(self.voice_map_data), 30)

    def test_choice_hints_sample_exists(self):
        self.assertTrue(
            os.path.exists(CHOICE_HINTS_SAMPLE),
            f"Choice hints file {CHOICE_HINTS_SAMPLE} does not exist",
        )

    def test_protagonist_voices_are_am_onyx(self):
        protagonist_tags = [
            "default", "narrator", "Narrator", "NARRATOR", "None", "n", "N",
            "player", "Player", "PLAYER", "you", "You", "YOU", "me", "Me", "ME",
            "mc", "MC", "Mc", "m", "M", "name", "Name", "NAME", "[name]", "[mc]",
            "Hugh", "hugh", "HUGH"
        ]
        for tag in protagonist_tags:
            self.assertIn(tag, self.voice_map_data, f"Tag {tag} missing in voice map")
            self.assertEqual(
                self.voice_map_data[tag],
                "am_onyx",
                f"Tag {tag} expected am_onyx but got {self.voice_map_data[tag]}",
            )

    def test_female_and_femboy_characters_strictly_af_voices(self):
        females = [
            "sc", "SC", "Sc", "Scarlett", "scarlett", "SCARLETT",
            "f1", "F1", "Jade", "jade", "JADE",
            "f2", "F2", "Mila", "mila", "MILA",
            "f4", "F4", "Zoe", "zoe", "ZOE",
            "f5", "F5", "Alice", "alice", "ALICE",
            "ec", "EC", "Ec", "Candy", "candy", "CANDY",
            "jw", "JW", "Jw", "Waitress", "waitress", "WAITRESS",
            "cl1", "CL1", "Cl1", "Bella", "bella", "BELLA",
            "cl2", "CL2", "Cl2", "Luna", "luna", "LUNA",
            "gw", "GW", "Gw", "Lana", "lana", "LANA",
            "gn", "GN", "Gn", "Genie", "genie", "GENIE",
            "ecrp", "ECRP", "Ecrp", "Isabella", "isabella", "ISABELLA"
        ]
        for tag in females:
            self.assertIn(tag, self.voice_map_data, f"Female/femboy tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("af_"),
                f"Tag {tag} assigned non-female voice: {voice}",
            )

    def test_male_characters_strictly_am_voices(self):
        males = [
            "ol", "OL", "Ol", "Ollie", "ollie", "OLLIE",
            "clt", "CLT", "Clt", "Arnold", "arnold", "ARNOLD",
            "ud", "UD", "Ud", "Unknown", "unknown", "UNKNOWN"
        ]
        for tag in males:
            self.assertIn(tag, self.voice_map_data, f"Male tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("am_"),
                f"Male tag {tag} assigned non-male voice: {voice}",
            )

    def test_installed_target_files_exist_when_game_present(self):
        outer_dir = os.path.dirname(TARGET_GAME_ROOT)
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game folder {TARGET_GAME_ROOT} not present")

        # Outer folder launchers
        for outer_launcher in ("JOGAR_COM_TTS.bat", "jogar.bat"):
            path = os.path.join(outer_dir, outer_launcher)
            self.assertTrue(os.path.exists(path), f"Missing outer launcher: {path}")

        # Game root launchers
        for launcher in ("run_backend.bat", "JOGAR_COM_TTS.bat", "jogar.bat", "voice_map.json"):
            path = os.path.join(TARGET_GAME_ROOT, launcher)
            self.assertTrue(os.path.exists(path), f"Missing root launcher: {path}")

        # Game folder mod scripts
        for mod_file in (
            "tts_mod.rpy",
            "tts_server.py",
            "tts_engines.py",
            "text_cleaner.py",
            "voice_map.json",
            "choice_hints_core.py",
            "zzz_mod_choice_consequences.rpy",
            "zzz_mod_choice_hints_generated.rpy",
        ):
            path = os.path.join(TARGET_GAME_DIR, mod_file)
            self.assertTrue(os.path.exists(path), f"Missing game mod file: {path}")


if __name__ == "__main__":
    unittest.main()

