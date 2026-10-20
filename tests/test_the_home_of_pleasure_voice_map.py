import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "the_home_of_pleasure_voice_map.json")
CHOICE_HINTS_SAMPLE = os.path.join(SAMPLES_DIR, "the_home_of_pleasure_choice_hints_generated.rpy")
TARGET_GAME_ROOT = r"D:\Games\TheHomeOfPleasure-0.3.3-pc"
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestTheHomeOfPleasureVoiceMap(unittest.TestCase):
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

    def test_choice_hints_sample_exists(self):
        self.assertTrue(
            os.path.exists(CHOICE_HINTS_SAMPLE),
            f"Choice hints file {CHOICE_HINTS_SAMPLE} does not exist",
        )

    def test_protagonist_and_narrator_voices_are_am_onyx(self):
        protagonist_tags = [
            "default", "narrator", "Narrator", "NARRATOR", "None", "n", "N",
            "player", "Player", "PLAYER", "you", "You", "YOU", "me", "Me", "ME",
            "mc", "MC", "Mc", "[PlayerName]", "[player]", "[player_name]", "PlayerName", "player_name",
            "aa1", "AA1", "???", "blank"
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
            # Mr Noonan
            "mr", "Mr", "MR", "Mr Noonan", "mr noonan", "MR NOONAN", "Noonan", "noonan",
            # Paul
            "p", "P", "Paul", "paul", "PAUL",
            # Tony
            "t", "T", "Tony", "tony", "TONY",
            # D.I. Stoker
            "di", "Di", "DI", "D.I. Stoker", "d.i. stoker", "DI Stoker", "di stoker", "Stoker", "stoker",
            # Mr Li
            "li", "Li", "LI", "Mr Li", "mr li", "MR LI", "Li", "li",
            # Secondaries
            "Andre", "andre", "ANDRE",
            "Angry boyfriend", "angry boyfriend",
            "Bald Man", "Bald man", "bald man",
            "Boss", "boss", "BOSS",
            "Council Worker", "council worker",
            "Gentleman", "gentleman",
            "His friend", "his friend",
            "Mick", "mick", "MICK",
            "Paul's friend", "paul's friend",
            "Police Officer", "police officer",
            "Regional Manager", "regional manager",
            "Ride attendant", "ride attendant",
            "Ronnie", "ronnie", "RONNIE",
            "Stephen", "stephen", "STEPHEN",
            "The Phantom Shitter", "the phantom shitter",
            "The men", "the men",
            "Thomas", "thomas", "THOMAS",
            "Undercover officer", "undercover officer",
            "Vince", "vince", "VINCE",
            "Waiter", "waiter", "WAITER",
            "Young man", "young man"
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
            # Sophie
            "s", "S", "Sophie", "sophie", "SOPHIE",
            # Beth
            "b", "B", "Beth", "beth", "BETH",
            # Bo
            "bo", "Bo", "BO",
            # Grace
            "g", "G", "Grace", "grace", "GRACE",
            # Kate
            "k", "K", "Kate", "kate", "KATE",
            # Angela
            "a", "A", "Angela", "angela", "ANGELA",
            # Jessica
            "j", "J", "Jessica", "jessica", "JESSICA",
            # Cara
            "c", "C", "Cara", "cara", "CARA",
            # Lilith
            "l", "L", "Lilith", "lilith", "LILITH",
            # Jennifer
            "jn", "Jn", "JN", "Jennifer", "jennifer", "JENNIFER", "Jen", "jen", "JEN",
            # Ellie
            "e", "E", "Ellie", "ellie", "ELLIE",
            # Chyou
            "ch", "Ch", "CH", "Chyou", "chyou", "CHYOU",
            # Georgina
            "ge", "Ge", "GE", "Georgina", "georgina", "GEORGINA",
            # Secondaries
            "Anya Malkova", "anya malkova",
            "Blonde woman", "blonde woman", "Blondie", "blondie",
            "Redhead", "redhead",
            "Cashier", "cashier",
            "Customer", "customer",
            "Guest", "guest",
            "Jane", "jane",
            "Mrs Li", "mrs li",
            "Receptionist", "receptionist",
            "Shopkeeper", "shopkeeper",
            "Sophie's friend", "sophie's friend",
            "Staff", "staff",
            "Waitress", "waitress",
            "Woman", "woman"
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
            "choice_hints_core.py",
            "zzz_mod_choice_consequences.rpy",
            "zzz_mod_choice_hints_generated.rpy",
            "voice_map.json",
        ):
            path = os.path.join(TARGET_GAME_DIR, game_file)
            self.assertTrue(os.path.exists(path), f"Missing game mod file: {path}")


if __name__ == "__main__":
    unittest.main()
