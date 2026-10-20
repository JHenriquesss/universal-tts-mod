import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "milf_obsession_voice_map.json")
TARGET_GAME_ROOT = r"D:\Games\MILF_Obsession-0.5.0-pc\MILF_Obsession-0.5.0-pc"
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestMilfObsessionVoiceMap(unittest.TestCase):
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
        self.assertGreater(len(self.voice_map_data), 50)

    def test_protagonist_and_narrator_voices_are_am_onyx(self):
        protagonist_tags = [
            "m", "M", "mc", "MC", "Bruce", "bruce", "BRUCE",
            "[persistent.player_name]", "[player_name]",
            "player", "Player", "you", "You", "me", "Me",
            "narrator", "Narrator", "default", "None", "n", "N"
        ]
        for tag in protagonist_tags:
            self.assertIn(tag, self.voice_map_data, f"Tag {tag} missing in voice map")
            self.assertEqual(
                self.voice_map_data[tag],
                "am_onyx",
                f"Tag {tag} expected am_onyx but got {self.voice_map_data[tag]}",
            )

    def test_all_male_characters_strictly_am_voices(self):
        males = [
            # Protagonist
            "m", "mc", "Bruce", "bruce",
            # Richard
            "ri", "RI", "Richard", "richard",
            # Elijah
            "el", "EL", "Elijah", "elijah",
            # Russell
            "ru", "RU", "Russell", "russell",
            # Logan
            "lo", "LO", "Logan", "logan",
            # Mark
            "mar", "MAR", "Mark", "mark",
            # Slick
            "s", "S", "Slick", "slick",
            # Jalen
            "ja", "JA", "Jalen", "jalen",
            # Matthew
            "mt", "MT", "Matthew", "matthew",
            # Simom
            "si", "SI", "Simom", "simom", "Simon", "simon",
            # Brayden
            "ba", "BA", "Brayden", "brayden",
            # Caleb
            "cl", "CL", "Caleb", "caleb",
            # Cop
            "po", "PO", "Cop", "cop", "Police", "police",
            # Joseph
            "jo", "JO", "Joseph", "joseph",
            # Customer
            "cu", "Customer", "customer", "cub", "Customer B", "cuc",
        ]
        for name in males:
            self.assertIn(name, self.voice_map_data, f"Male character {name} missing in voice map")
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("am_") or voice.startswith("bm_"),
                f"Male character {name} got non-male voice {voice}",
            )

    def test_all_female_characters_strictly_af_voices(self):
        females = [
            # Carmen
            "ca", "CA", "Carmen", "carmen",
            # Abigail
            "ab", "AB", "Abigail", "abigail",
            # Casey
            "cs", "CS", "Casey", "casey",
            # Brianna
            "br", "BR", "Brianna", "brianna",
            # Charlotte
            "ch", "CH", "Charlotte", "charlotte",
            # Nadine
            "na", "NA", "Nadine", "nadine",
            # Katherine
            "k", "K", "Katherine", "katherine", "Kath", "kath",
            # Mia
            "mi", "MI", "Mia", "mia",
            # Lily
            "li", "LI", "Lily", "lily",
            # Darlene
            "da", "DA", "Darlene", "darlene",
            # Heather
            "he", "HE", "Heather", "heather",
            # Selena
            "se", "SE", "Selena", "selena",
            # Aurora
            "au", "AU", "Aurora", "aurora",
            # Shanice
            "sh", "SH", "Shanice", "shanice",
            # Madison
            "md", "MD", "Madison", "madison", "Madson", "madson",
            # Courtney
            "co", "CO", "Courtney", "courtney",
            # Margot
            "ma", "MA", "Margot", "margot",
            # Jelena
            "je", "JE", "Jelena", "jelena",
            # Brielle
            "bi", "BI", "Brielle", "brielle",
        ]
        for name in females:
            self.assertIn(name, self.voice_map_data, f"Female character {name} missing in voice map")
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("af_") or voice.startswith("bf_"),
                f"Female character {name} got non-female voice {voice}",
            )

    def test_deployed_files_exist_when_target_directory_present(self):
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game root {TARGET_GAME_ROOT} does not exist on this machine")

        game_dir = TARGET_GAME_DIR
        required_game_files = [
            "tts_mod.rpy",
            "tts_server.py",
            "tts_engines.py",
            "text_cleaner.py",
            "voice_map.json",
        ]
        required_root_files = [
            "run_backend.bat",
            "JOGAR_COM_TTS.bat",
            "jogar.bat",
            "voice_map.json",
        ]

        for fname in required_game_files:
            fpath = os.path.join(game_dir, fname)
            self.assertTrue(
                os.path.exists(fpath),
                f"Required game file missing: {fpath}",
            )

        for fname in required_root_files:
            fpath = os.path.join(TARGET_GAME_ROOT, fname)
            self.assertTrue(
                os.path.exists(fpath),
                f"Required root file missing: {fpath}",
            )


if __name__ == "__main__":
    unittest.main()
