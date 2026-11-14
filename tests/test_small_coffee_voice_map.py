import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "small_coffee_voice_map.json")
TARGET_GAME_ROOT = r"D:\Games\SmallCoffee-0.36-male-pc\SmallCoffee-0.36-male-pc"
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")

PROTAGONIST_TAGS = [
    "default", "narrator", "None", "player", "Player", "mc", "MC",
    "name", "Nighten", "you", "me", "name_only",
    "[name]", "[player_name]", "[firstname]", "E", "n_nvl",
]

MALE_TAGS = [
    "hug", "Hugo", "sac", "Sacha", "axel", "Axel", "seb", "Sebastian",
    "bru", "Bruno", "sam", "Samuel", "sal", "Salomon", "jay", "Jay",
]

FEMALE_TAGS = [
    "est", "Estelle", "lin", "Linda", "cam", "Camille", "lis", "Lisa",
    "zoey", "Zoey", "mar", "Mrs.Gillsberg", "isa", "Isabelle", "ana",
    "Anaïs", "sar", "Sarah", "elise", "Elise", "olia", "Olivia", "jul",
    "Julie", "tra", "Tracy", "bet", "Betty", "emm", "Emma", "gm", "Marion",
    "elo", "Elodie", "m_nvl", "Marie", "sab", "Sabrina", "clara", "Clara",
    "mil", "Mila", "av", "Ava", "emi", "Emily", "rav", "Chloe", "jeni",
    "Jennifer", "mela", "Melany", "jen", "Jenny", "ros", "Rose", "lau",
    "Laura", "club", "Club people", "est_student", "Student", "cat", "Cat",
    "elisa", "Elisa",
]


class TestSmallCoffeeVoiceMap(unittest.TestCase):
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
        for tag in PROTAGONIST_TAGS:
            self.assertIn(tag, self.voice_map_data, f"Tag {tag} missing in voice map")
            self.assertEqual(
                self.voice_map_data[tag],
                "am_onyx",
                f"Tag {tag} expected am_onyx but got {self.voice_map_data[tag]}",
            )

    def test_male_characters_strictly_am_voices(self):
        for tag in MALE_TAGS:
            self.assertIn(tag, self.voice_map_data, f"Male tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("am_"),
                f"Male tag {tag} assigned non-male voice: {voice}",
            )

    def test_female_characters_strictly_af_voices(self):
        for tag in FEMALE_TAGS:
            self.assertIn(tag, self.voice_map_data, f"Female tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith("af_"),
                f"Female tag {tag} assigned non-female voice: {voice}",
            )

    def test_installed_game_copy_matches_the_sample(self):
        installed = os.path.join(TARGET_GAME_DIR, "voice_map.json")
        if not os.path.exists(installed):
            self.skipTest("SmallCoffee-0.36-male-pc is not installed on this machine")
        with open(installed, "r", encoding="utf-8") as f:
            self.assertEqual(self.voice_map_data, json.load(f))


if __name__ == "__main__":
    unittest.main()
