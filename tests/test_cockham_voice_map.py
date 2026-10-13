import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "cockham_voice_map.json")
TARGET_GAME_ROOT = os.path.join(
    PROJECT_ROOT, "Jogo atual", "Cockham-v0.8.1-pc", "Cockham-v0.8.1-pc"
)
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestCockhamVoiceMap(unittest.TestCase):
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
            "default", "player", "Player", "PLAYER",
            "mc", "MC", "Mc",
            "narrator", "Narrator", "NARRATOR", "nar", "NAR", "Nar",
            "you", "You",
            "[player]", "[player_name]", "player_name"
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
            # Main heroes / heroines
            "cm", "CM", "Captain MILF", "captain milf",
            "pg", "PG", "Powergirl", "powergirl",
            "bw", "BW", "Black Widow", "black widow",
            "ww", "WW", "Wonder Woman", "wonder woman",
            "lc", "LC", "Lara Crotch", "lara crotch",
            "ag", "AG", "Audit Girl", "audit girl",
            "lp", "LP", "Lois Pane", "lois pane",
            "ef", "EF", "Emma Frost", "emma frost",
            "cs01", "CS01", "cs02", "CS02", "Captain Sawyer", "captain sawyer",
            "sg", "SG", "Supergirl", "supergirl",
            "ex", "EX", "Excella", "excella",
            "hq", "HQ", "Harley Quiff", "harley quiff",
            "pi", "PI", "Poison Ivy", "poison ivy",
            "cw", "CW", "Catwoman", "catwoman",
            "hu", "HU", "She-Hulk", "she-hulk",
            "aw", "AW", "Ada Wang", "ada wang",
            "so", "SO", "Sophia", "sophia",
            "ka", "KA", "Kate", "kate",
            "ta", "TA", "Tabitha Gala-Vag", "tabitha gala-vag",
            "bk", "BK", "Barbara Keen", "barbara keen",
            "sc", "SC", "Scarlet", "scarlet",
            "da", "DA", "Sergeant dani", "sergeant dani",
            "an", "AN", "Angela", "angela",
            "de", "DE", "Demona", "demona",
            "ho", "HO", "Honoka", "honoka",
            "aj", "AJ", "Ajizzai", "ajizzai",
            "nt", "NT", "Agent Natalya", "agent natalya",
            "ig", "IG", "SS nurse Ingrid", "ss nurse ingrid",
            "fr", "FR", "Valkyrie Frieda", "valkyrie frieda",
            "me", "ME", "Queen Mera", "queen mera",
            "lu", "LU", "Sexy Luthor", "sexy luthor",
            "ck", "CK", "Catherine Krass", "catherine krass",
            "ba", "BA", "Blue Alien", "blue alien",
            "pa", "PA", "Purple Alien", "purple alien",
            "qc", "QC", "Queen Cleopatra", "queen cleopatra",
            "sk", "SK", "Agent Skully", "agent skully",
            "ls", "LS", "LianShi", "lianshi",
            "lo", "LO", "Lolly", "lolly",
            "af", "AF", "Africa", "africa",
            "ja", "JA", "Jasmine", "jasmine",
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
            "bm", "BM", "Batman", "batman",
            "sm", "SM", "Superman", "superman",
            "cl", "CL", "Clark Kunt", "clark kunt",
            "na", "NA", "Colonel Stroheim", "colonel stroheim",
            "mk", "MK", "Mayor Krass", "mayor krass",
            "mb", "MB", "Mafia Boss", "mafia boss",
            "st", "ST", "Samson Goldcock", "samson goldcock",
            "jo", "JO", "Joker", "joker",
            "th", "TH", "Thug", "thug",
            "hm01", "HM01", "Henchman01", "henchman01",
            "hm02", "HM02", "Henchman02", "henchman02",
            "gg", "GG", "Gutsy Goon", "gutsy goon",
            "hb", "HB", "Hobo", "hobo",
            "cd", "CD", "Cab Driver", "cab driver",
            "ah", "AH", "Adolf Hitler", "adolf hitler",
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

        # Check hints generated file has Cockham hints
        hints_path = os.path.join(TARGET_GAME_DIR, "zzz_mod_choice_hints_generated.rpy")
        with open(hints_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("ScarletDialogues", content)
        self.assertIn("ScarlettBreast", content)

    def test_cockham_tts_mod_default_voice_is_am_onyx(self):
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game folder {TARGET_GAME_ROOT} not present")

        tts_mod_path = os.path.join(TARGET_GAME_DIR, "tts_mod.rpy")
        self.assertTrue(os.path.exists(tts_mod_path))
        with open(tts_mod_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('TTS_VOICE = "am_onyx"', content)

    def test_cockham_tts_mod_has_latest_features(self):
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game folder {TARGET_GAME_ROOT} not present")

        tts_mod_path = os.path.join(TARGET_GAME_DIR, "tts_mod.rpy")
        self.assertTrue(os.path.exists(tts_mod_path))
        with open(tts_mod_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("def tts_toggle_audio():", content)
        self.assertIn("_tts_install_save_compat_hook", content)
        self.assertIn("_tts_install_display_hook", content)
        self.assertIn("playback_done_time", content)
        self.assertIn("tts_audio_enabled", content)


if __name__ == "__main__":
    unittest.main()
