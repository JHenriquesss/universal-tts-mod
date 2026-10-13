import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "being_super_voice_map.json")
CHOICE_HINTS_SAMPLE = os.path.join(SAMPLES_DIR, "being_super_choice_hints_generated.rpy")
TARGET_OUTER_ROOT = r"D:\Games\Being_Super_Chapter_1-0.31.LIGHT.testbuild-win"
TARGET_GAME_ROOT = os.path.join(
    TARGET_OUTER_ROOT, "Being_Super_Chapter_1-0.31.LIGHT.testbuild-win"
)
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestBeingSuperVoiceMap(unittest.TestCase):
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
        self.assertGreater(len(self.voice_map_data), 100)

    def test_choice_hints_sample_exists_and_populated(self):
        self.assertTrue(
            os.path.exists(CHOICE_HINTS_SAMPLE),
            f"Sample file {CHOICE_HINTS_SAMPLE} does not exist",
        )
        with open(CHOICE_HINTS_SAMPLE, "r", encoding="utf-8") as f:
            lines = [l for l in f if l.strip().startswith("(")]
        self.assertGreater(len(lines), 1000)

    def test_protagonist_and_narrator_voices_are_am_onyx(self):
        protagonist_tags = [
            "default", "player", "Player", "mc", "MC", "Mc",
            "narrator", "Narrator", "NARRATOR", "nar", "m", "M",
            "you", "You", "YOU", "r", "R",
            "[mc_name]", "[MC_name]", "mc_name", "MC_name",
            "b", "B", "Your Thoughts", "your thoughts",
            "yourheart", "Your Heart", "yourcock", "Your Cock",
            "rr", "Replicated [MC_name]", "dad", "[DAD_name]",
            "father", "Your Fathers Soul", "death", "[DEATH_name]",
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
            "ruby", "Ruby", "ruby_talk_gym",
            "taylor", "Taylor", "taylor_angry_convo", "taylor_happy_convo",
            "nikki", "Nikki", "nikki_angry_convo", "nikki_happy_convo",
            "ana", "Ana", "ana_angry_convo", "ana_happy_convo",
            "susan", "Susan", "susan_talk_gym",
            "victoria", "Victoria", "vic", "Vic", "VICTITS", "Victorias tits",
            "veronica", "Veronica",
            "rain", "Rain", "rain_talk_gym",
            "luna", "Luna",
            "brook", "Brooklyn",
            "dani", "Dani",
            "nina", "Nina",
            "gothgirl", "Goth Girl",
            "karen", "Karen Wood, the News Anchor",
            "peabody", "Miss Peabody",
            "mrswillow", "Mrs Willowbrook",
            "nurse", "Nurse",
            "waitress", "Waitress",
            "britishgirl", "[British_Girl_name]",
            "april", "Doctor April Fox",
            "repran", "Random Reporter",
            "MUTwolfgirl", "[MUTANT_WolfGirl_name]",
            "miranda", "Miranda",
            "MeterMaid", "Meter Maid",
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
            "hans", "Hans",
            "horse", "Horse",
            "bigwayne", "Big Wayne",
            "brut", "Brutus",
            "Bobby", "bobby",
            "earl", "Earl",
            "dexter", "Dexter",
            "heath", "Heath The Jock",
            "jack", "Jack The Jock",
            "chad", "Chad The Jock",
            "jocks", "Jocks",
            "frank", "Frank Da Nurse",
            "ike", "Ike",
            "chris", "Chris",
            "shan", "Shan",
            "sam", "Sam",
            "maximillion", "Maximillion Caesar",
            "mayor", "Mayor of Quiettown",
            "oldman", "Random Old Man",
            "boy", "Boy",
            "courier", "courier",
            "dev", "Mr Sandman, the Dev!",
            "blonde", "Mister Blonde",
            "red", "Mister Red",
            "lens", "Mister Lens",
            "bird", "Mister Bird",
            "cre", "The Creature",
            "Arjoo", "arjun", "Arjun",
            "brick", "The Brick",
            "botanist", "The Botanist",
            "cuntry", "A Cuntry Boy",
            "steel", "A SteelHeart",
            "hudson", "Hudson",
            "news", "News Person",
            "beggar", "Beggar",
            "randdoc", "Random Doctor",
            "teamleader", "Team Leader",
            "caexec", "CaesarCorp Executive",
            "mysteryman", "Mystery Man",
            "spy", "CaesarCorp Spy",
            "cop", "Cop",
            "hillygrunt", "Hillbilly Grunt One",
            "hillbilly", "Hillbilly",
            "hillbillyJed", "Jed",
            "lee", "Captain Lee",
            "leefake", "Fake Captain Lee",
            "cas", "Caesar Eagle",
            "ast", "Astronaut",
            "angry", "Angry Man",
            "manager", "Manager at CaesarCorp HQ",
            "casec", "CaesarCorp Security",
            "gg", "CaesarCorp Grunt",
            "CaesarEmployee", "Caesarcorp Employee",
            "MUTdan", "[MUTANT_Dan_name]",
            "MUTsamss", "[MUTANT_Samss_name]",
            "mut", "[Mutant_Group_Name]",
            "redwolf", "Mysterious Red Wolf",
            "pig", "Pig",
            "owl", "Owl",
            "bottle", "Mister Bottle",
            "child", "Moonchild",
            "grad", "Graduate",
            "hacker", "Hacker",
            "miller", "Miller, the hacker",
            "techguy", "Tech guy",
            "alloy", "Alloy, the contact",
            "Cinwork", "Cinema Worker",
            "CreepyCam", "Old Creepy Camera Guy",
            "EvanH", "Evan Hartley",
            "rand_glob", "Random Glob",
            "globSAVED", "The Glob you spared",
            "IllGlob", "Illegal Glob",
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

        # Outer root launchers
        for launcher in ("run_backend.bat", "JOGAR_COM_TTS.bat", "jogar.bat"):
            path = os.path.join(TARGET_OUTER_ROOT, launcher)
            self.assertTrue(os.path.exists(path), f"Missing outer launcher: {path}")

        # Inner game root launchers
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

        for hint_file in (
            "choice_hints_core.py",
            "zzz_mod_choice_consequences.rpy",
            "zzz_mod_choice_hints_generated.rpy",
        ):
            path = os.path.join(TARGET_GAME_DIR, hint_file)
            self.assertTrue(os.path.exists(path), f"Missing choice hints file: {path}")


if __name__ == "__main__":
    unittest.main()
