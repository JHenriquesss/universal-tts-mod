import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "after_the_fall_voice_map.json")
TARGET_GAME_ROOT = r"D:\Games\AfterTheFall-0.5-pc\AfterTheFall-0.5-pc"
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestAfterTheFallVoiceMap(unittest.TestCase):
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

    def test_protagonist_voices_are_am_onyx(self):
        protagonist_tags = [
            "default", "Adam", "adam", "ADAM", "p", "P", "mc", "MC", "player", "Player",
            "[player_name]", "player_name", "Guardian", "guardian",
            "[MainLunaRelation]", "MainLunaRelation"
        ]
        for tag in protagonist_tags:
            self.assertIn(tag, self.voice_map_data, f"Tag {tag} missing in voice map")
            self.assertEqual(
                self.voice_map_data[tag],
                "am_onyx",
                f"Tag {tag} expected am_onyx but got {self.voice_map_data[tag]}",
            )

    def test_female_characters_strictly_af_voices(self):
        females = [
            "Anne", "anne", "ANNE", "Mom", "mom",
            "Luna", "luna", "LUNA", "Ward", "ward", "[Luna_relation]",
            "Emily", "emily", "EMILY",
            "Alice", "alice", "ALICE", "Friend", "friend",
            "Sara", "sara", "SARA",
            "Mei", "mei", "MEI",
            "Rim", "rim", "RIM",
            "Lucy", "lucy", "LUCY",
            "Elen", "elen", "ELEN",
            "Woman", "woman", "WOMAN",
            "narrator", "Narrator", "Unknown", "unknown"
        ]
        for tag in females:
            self.assertIn(tag, self.voice_map_data, f"Female tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("af_"),
                f"Female tag {tag} assigned non-female voice: {voice}",
            )

    def test_male_characters_strictly_am_voices(self):
        males = [
            "Samuel", "samuel", "SAMUEL",
            "Tom", "tom", "TOM",
            "Cole", "cole", "COLE",
            "Thomas", "thomas", "THOMAS",
            "Alan", "alan", "ALAN",
            "Sam", "sam", "SAM",
            "Miller", "miller", "MILLER",
            "Yuri", "yuri", "YURI",
            "Williams", "williams", "WILLIAMS",
            "Graves", "graves", "GRAVES",
            "Jonathan", "jonathan", "JONATHAN",
            "Mitcher", "mitcher", "MITCHER",
            "bōsa", "bosa", "Bosa", "BŌSA"
        ]
        for tag in males:
            self.assertIn(tag, self.voice_map_data, f"Male tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("am_"),
                f"Male tag {tag} assigned non-male voice: {voice}",
            )

    def test_installed_target_files_exist_when_game_present(self):
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game folder {TARGET_GAME_ROOT} not present")

        # Game root launchers
        for launcher in ("run_backend.bat", "JOGAR_COM_TTS.bat", "jogar.bat", "voice_map.json"):
            path = os.path.join(TARGET_GAME_ROOT, launcher)
            self.assertTrue(os.path.exists(path), f"Missing root launcher: {path}")

        # Game folder mod scripts
        for mod_file in ("tts_mod.rpy", "tts_server.py", "tts_engines.py", "text_cleaner.py", "voice_map.json"):
            path = os.path.join(TARGET_GAME_DIR, mod_file)
            self.assertTrue(os.path.exists(path), f"Missing game mod file: {path}")

    def test_installed_choice_hints_files_exist_when_game_present(self):
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game folder {TARGET_GAME_ROOT} not present")

        # Choice overlay files
        for overlay_file in ("choice_hints_core.py", "zzz_mod_choice_consequences.rpy", "zzz_mod_choice_hints_generated.rpy"):
            path = os.path.join(TARGET_GAME_DIR, overlay_file)
            self.assertTrue(os.path.exists(path), f"Missing choice overlay file: {path}")

        # Check hints generated file has After The Fall hints
        hints_path = os.path.join(TARGET_GAME_DIR, "zzz_mod_choice_hints_generated.rpy")
        with open(hints_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("AnneLingerieNightTIme", content)
        self.assertIn("CumInLuna", content)


if __name__ == "__main__":
    unittest.main()
