import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "samples")
VOICE_MAP_SAMPLE = os.path.join(SAMPLES_DIR, "hibah_s2_voice_map.json")
OUTER_GAME_DIR = r"D:\Games\How_I_Became_a_Hero_S2-0.20-pc"
TARGET_GAME_ROOT = os.path.join(OUTER_GAME_DIR, "HIBAH_S2-0.20-pc")
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


PROTAGONIST_TAGS = [
    "m", "m_nvl", "[mc]", "mc", "MC", "Dezno", "Dez-no", "Ethan",
    "[persistent.pname]", "persistent.pname", "pname",
    "player", "Player", "you", "You", "me", "Me",
    "narrator", "Narrator", "default", "None", "",
]

FEMALE_TAGS = [
    "la", "Layla", "kora", "Kora", "cha", "cha_nvl", "Chanel",
    "mom", "Mom", "paz", "Paz", "mi", "Miriel", "mis", "Misty",
    "lyra", "Lyra", "si", "su", "Sibilla", "rixxa", "Rixxa",
    "ast", "Asteria", "los", "Losille", "sha", "Shalana",
    "daka", "Daka", "arw", "Arwen", "bibi", "Bibi", "rose", "Rose",
    "mira", "Mirandrith", "neri", "Neridelle", "erd", "Erdie",
    "elara", "Elara", "thalia", "Thalia", "mu", "Mu",
    "the", "Thessalia", "dri", "Drinja", "val", "Valandria",
    "aga", "Agaressa", "bri", "Bridget", "zamna", "Zamna",
    "ser", "Serena", "isa", "Isabella", "rina", "Rina",
    "renna", "Renna", "bess", "Bess", "de", "Deena",
    "vic", "Victoria", "elo", "Elodie", "tra", "Trasha",
    "oli", "Olivia", "ha", "Harda", "ann", "Annael",
    "zel", "Zelia", "cla", "Claudia", "syl", "Syllia",
    "donna", "Donna", "lin", "Linda", "sylv", "Sylvara",
    "kum", "Kumiko", "the_girls", "The Girls", "gid", "Gidith",
    "selena", "Selena", "woman", "Woman", "ind", "Indis",
    "py", "Pyria", "sar", "Sarya", "yris", "Yris",
    "ad", "Adriana", "aleris", "Aleris", "phel", "Phelorna",
    "angryw", "Angry woman", "joy", "Joy", "Astralath",
    "cir", "Cirtha", "tha", "Thalae",
]

MALE_TAGS = [
    "unk", "???", "aa", "Aaron", "rasu", "Rasu", "tu", "Turgon",
    "theo", "Theodmer", "dad", "Dad", "car", "Carnis",
    "bel", "Beleg", "aim", "Aimon", "ulf", "Ulfin",
    "reth", "Reth", "ja", "Jared", "ela", "Elas",
    "prork", "Prork", "mort", "Morthil", "gan", "Gantar",
    "tom", "Tom", "bubu", "Bubu", "art", "Arthur",
    "mar", "Martin", "olg", "Olgren", "amd", "Amdir",
    "ael", "Aelrion", "ara", "Aran", "seb", "Sebastian",
    "mas", "Mason", "kids", "Kids", "toross", "Toross",
    "angrym", "Angry man", "dal", "Dalmoth", "elred", "Elred",
    "bor", "Bor", "fel", "Felvius", "golem", "Golem",
    "crowd", "Crowd",
    "p1", "Prisoner #1", "p2", "Prisoner #2", "p3", "Prisoner #3",
    "p4", "Prisoner #4", "p5", "Prisoner #5",
]


class TestHibahS2VoiceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(VOICE_MAP_SAMPLE):
            with open(VOICE_MAP_SAMPLE, "r", encoding="utf-8") as f:
                cls.voice_map_data = json.load(f)
        else:
            cls.voice_map_data = {}

    def test_voice_map_sample_exists_and_covers_cast(self):
        self.assertTrue(
            os.path.exists(VOICE_MAP_SAMPLE),
            f"Sample file {VOICE_MAP_SAMPLE} does not exist",
        )
        self.assertGreater(len(self.voice_map_data), 180)

    def test_protagonist_and_narrator_voices_are_am_onyx(self):
        for tag in PROTAGONIST_TAGS:
            self.assertIn(tag, self.voice_map_data, f"Tag {tag} missing in voice map")
            self.assertEqual(
                self.voice_map_data[tag],
                "am_onyx",
                f"Tag {tag} expected am_onyx but got {self.voice_map_data[tag]}",
            )

    def test_female_characters_strictly_female_voices(self):
        for tag in FEMALE_TAGS:
            self.assertIn(tag, self.voice_map_data, f"Female tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith(("af_", "bf_")),
                f"Female tag {tag} got non-female voice: {voice}",
            )

    def test_male_characters_strictly_male_voices(self):
        for tag in MALE_TAGS:
            self.assertIn(tag, self.voice_map_data, f"Male tag {tag} missing in voice map")
            voice = self.voice_map_data[tag]
            self.assertTrue(
                voice.startswith(("am_", "bm_")),
                f"Male tag {tag} got non-male voice: {voice}",
            )

    def test_deployed_game_uses_universal_mod_and_has_no_legacy_artifacts(self):
        if not os.path.exists(TARGET_GAME_ROOT):
            self.skipTest(f"Target game root {TARGET_GAME_ROOT} does not exist on this machine")

        from install_tts_mod import RENPY_REQUIRED_GAME_FILES, ROOT_HELPER_FILES

        for fname in RENPY_REQUIRED_GAME_FILES + ("voice_map.json",):
            self.assertTrue(
                os.path.exists(os.path.join(TARGET_GAME_DIR, fname)),
                f"Missing required game file: {fname}",
            )
        for fname in ROOT_HELPER_FILES + ("voice_map.json",):
            self.assertTrue(
                os.path.exists(os.path.join(TARGET_GAME_ROOT, fname)),
                f"Missing required root file: {fname}",
            )
        for fname in ROOT_HELPER_FILES:
            self.assertTrue(
                os.path.exists(os.path.join(OUTER_GAME_DIR, fname)),
                f"Missing outer launcher file: {fname}",
            )

        with open(os.path.join(TARGET_GAME_DIR, "tts_mod.rpy"), "r", encoding="utf-8") as f:
            self.assertIn('TTS_VOICE = "am_onyx"', f.read())

        with open(os.path.join(TARGET_GAME_DIR, "voice_map.json"), "r", encoding="utf-8") as f:
            self.assertEqual(self.voice_map_data, json.load(f))

        for legacy in (
            os.path.join(TARGET_GAME_DIR, "zz_tts_kokoro.rpy"),
            os.path.join(TARGET_GAME_DIR, "zz_tts_kokoro.rpyc"),
            os.path.join(OUTER_GAME_DIR, "kokoro-tts"),
            os.path.join(OUTER_GAME_DIR, "Iniciar jogo com voz.bat"),
            os.path.join(OUTER_GAME_DIR, "Parar-servidor.bat"),
        ):
            self.assertFalse(os.path.exists(legacy), f"Legacy broken mod artifact still exists: {legacy}")


if __name__ == "__main__":
    unittest.main()
