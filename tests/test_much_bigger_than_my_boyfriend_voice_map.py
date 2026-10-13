import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "much_bigger_than_my_boyfriend_voice_map.json")
TARGET_GAME_ROOT = r"D:\Games\Much_Bigger_Than_my_Boyfriend\Much Bigger Than my Boyfriend"
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestMuchBiggerThanMyBoyfriendVoiceMap(unittest.TestCase):
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
        self.assertGreater(len(self.voice_map_data), 40)

    def test_protagonist_and_narrator_voices_are_am_onyx(self):
        protagonist_tags = [
            "default", "narrator", "Narrator", "NARRATOR", "None", "n", "N",
            "player", "Player", "PLAYER", "you", "You", "YOU", "me", "Me", "ME",
            "t", "T", "st", "ST", "Tim", "tim", "TIM",
            "boyfriend", "Boyfriend", "BOYFRIEND", "bf", "BF",
            "mc", "MC", "Mc", "[player]", "[player_name]", "player_name"
        ]
        for tag in protagonist_tags:
            self.assertIn(tag, self.voice_map_data, f"Tag {tag} missing in voice map")
            self.assertEqual(
                self.voice_map_data[tag],
                "am_onyx",
                f"Tag {tag} expected am_onyx but got {self.voice_map_data[tag]}",
            )

    def test_male_characters_strictly_am_voices(self):
        males = [
            # Tim (protagonist)
            "t", "T", "st", "ST", "Tim", "tim", "TIM",
            # Mike (antagonist/bully)
            "m", "M", "sm", "SM", "Mike", "mike", "MIKE",
            # Ray (friend)
            "r", "R", "sr", "SR", "Ray", "ray", "RAY",
            # Doctor
            "d", "D", "Doctor", "doctor", "DOCTOR", "doc", "Doc"
        ]
        for tag in males:
            self.assertIn(tag, self.voice_map_data, f"Male tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("am_") or voice.startswith("bm_"),
                f"Male tag {tag} assigned non-male voice: {voice}",
            )

    def test_female_characters_strictly_af_voices(self):
        females = [
            # Alice
            "a", "A", "sa", "SA", "Alice", "alice", "ALICE",
            # Paige
            "p", "P", "sp", "SP", "Paige", "paige", "PAIGE",
            # Mike's Mum
            "mm", "MM", "smm", "SMM", "nmm", "NMM",
            "Mikes Mum", "mikes mum", "MIKES MUM", "Mike's Mum", "mike's mum",
            "Mum", "mum", "Mother", "mother",
            # Cynthia / Claudia
            "c", "C", "Cynthia", "cynthia", "CYNTHIA", "Claudia", "claudia", "CLAUDIA",
            # Girl Wall
            "wq", "WQ", "Girl Wall", "girl wall", "GIRL WALL", "GirlWall",
            # Nurse
            "nurse", "Nurse", "NURSE",
            # Teacher
            "teacher", "Teacher", "TEACHER",
            # People
            "people", "People", "PEOPLE"
        ]
        for tag in females:
            self.assertIn(tag, self.voice_map_data, f"Female tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("af_") or voice.startswith("bf_"),
                f"Female tag {tag} assigned non-female voice: {voice}",
            )

    def test_installed_target_files_exist_when_game_present(self):
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game root {TARGET_GAME_ROOT} does not exist on this machine")

        outer_dir = os.path.dirname(TARGET_GAME_ROOT)
        # Outer launchers
        for outer_launcher in ("JOGAR_COM_TTS.bat", "jogar.bat"):
            path = os.path.join(outer_dir, outer_launcher)
            self.assertTrue(os.path.exists(path), f"Missing outer launcher: {path}")

        # Root files
        for root_file in ("run_backend.bat", "JOGAR_COM_TTS.bat", "jogar.bat", "voice_map.json"):
            path = os.path.join(TARGET_GAME_ROOT, root_file)
            self.assertTrue(os.path.exists(path), f"Missing root file: {path}")

        # Game files
        for game_file in (
            "tts_mod.rpy",
            "tts_server.py",
            "tts_engines.py",
            "text_cleaner.py",
            "voice_map.json",
        ):
            path = os.path.join(TARGET_GAME_DIR, game_file)
            self.assertTrue(os.path.exists(path), f"Missing game mod file: {path}")

    def test_tts_mod_has_audio_toggle_and_screen_button(self):
        tts_mod_path = os.path.join(PROJECT_ROOT, "renpy_mod", "tts_mod.rpy")
        with open(tts_mod_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("def tts_toggle_audio", content)
        self.assertIn("tts_toggle_audio", content)
        self.assertIn("Áudio TTS", content)
        self.assertIn("tts_audio_enabled", content)

    def test_auto_advance_respects_vibor_in_scene_and_native_voice(self):
        tts_mod_path = os.path.join(PROJECT_ROOT, "renpy_mod", "tts_mod.rpy")
        with open(tts_mod_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("vibor_in_scene", content)
        self.assertIn("renpy.music.is_playing(\"voice\")", content)


if __name__ == "__main__":
    unittest.main()

