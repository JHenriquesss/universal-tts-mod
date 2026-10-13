import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_shadows_of_trust_voice_map():
    return {
        "default": "am_onyx",
        "narrator": "am_onyx",
        "Narrator": "am_onyx",
        "None": "am_onyx",
        "player": "am_onyx",
        "Player": "am_onyx",
        "you": "am_onyx",
        "You": "am_onyx",
        "me": "am_onyx",
        "Me": "am_onyx",
        "mc": "am_onyx",
        "MC": "am_onyx",
        "Josh": "am_onyx",
        "josh": "am_onyx",
        "[store.player_name]": "am_onyx",
        "[player_name]": "am_onyx",
        "store.player_name": "am_onyx",
        "player_name": "am_onyx",
        "th": "am_onyx",
        "TH": "am_onyx",
        "Thoughts": "am_onyx",
        "thoughts": "am_onyx",
        
        # Beth
        "b": "af_heart",
        "B": "af_heart",
        "Beth": "af_heart",
        "beth": "af_heart",
        "bt": "af_heart",
        "BT": "af_heart",
        "Beth Thoughts": "af_heart",
        "beth thoughts": "af_heart",

        # Martina
        "m": "af_bella",
        "M": "af_bella",
        "Martina": "af_bella",
        "martina": "af_bella",
        "mt": "af_bella",
        "MT": "af_bella",
        "Martina Thoughts": "af_bella",
        "martina thoughts": "af_bella",

        # Susan
        "s": "af_sarah",
        "S": "af_sarah",
        "Susan": "af_sarah",
        "susan": "af_sarah",
        "st": "af_sarah",
        "ST": "af_sarah",
        "Susan Thoughts": "af_sarah",
        "susan thoughts": "af_sarah",

        # Naomi (Critical: in this game, 'n' is Naomi, a female character)
        "n": "af_sky",
        "N": "af_sky",
        "Naomi": "af_sky",
        "naomi": "af_sky",

        # Terry
        "t": "am_adam",
        "T": "am_adam",
        "Terry": "am_adam",
        "terry": "am_adam",

        # Finn
        "f": "am_fenrir",
        "F": "am_fenrir",
        "Finn": "am_fenrir",
        "finn": "am_fenrir",

        # Karen
        "k": "af_nicole",
        "K": "af_nicole",
        "Karen": "af_nicole",
        "karen": "af_nicole",

        # Gloria
        "g": "af_kore",
        "G": "af_kore",
        "Gloria": "af_kore",
        "gloria": "af_kore",

        # Eddie
        "e": "am_eric",
        "E": "am_eric",
        "Eddie": "am_eric",
        "eddie": "am_eric",

        # Ivy
        "i": "af_alloy",
        "I": "af_alloy",
        "Ivy": "af_alloy",
        "ivy": "af_alloy",

        # Malcolm
        "mb": "am_michael",
        "MB": "am_michael",
        "Malcolm": "am_michael",
        "malcolm": "am_michael",

        # Beth's dad
        "d": "am_michael",
        "D": "am_michael",
        "Beth's dad": "am_michael",
        "beth's dad": "am_michael",
        "Dad": "am_michael",
        "dad": "am_michael",

        # Teacher / Professor (Female professor)
        "te": "af_jessica",
        "TE": "af_jessica",
        "Teacher": "af_jessica",
        "teacher": "af_jessica",
        "Professor": "af_jessica",
        "professor": "af_jessica",

        # Thug
        "tg": "am_onyx",
        "TG": "am_onyx",
        "Thug": "am_onyx",
        "thug": "am_onyx",

        # Brian
        "br": "am_liam",
        "BR": "am_liam",
        "Brian": "am_liam",
        "brian": "am_liam",

        # Jackson
        "j": "am_puck",
        "J": "am_puck",
        "Jackson": "am_puck",
        "jackson": "am_puck",

        # Leela
        "l": "af_nova",
        "L": "af_nova",
        "le": "af_nova",
        "LE": "af_nova",
        "Leela": "af_nova",
        "leela": "af_nova",

        # Edward
        "ed": "am_fenrir",
        "ED": "am_fenrir",
        "Edward": "am_fenrir",
        "edward": "am_fenrir",

        # Jane
        "jan": "af_sarah",
        "JAN": "af_sarah",
        "Jane": "af_sarah",
        "jane": "af_sarah",

        # Lara
        "lar": "af_sky",
        "LAR": "af_sky",
        "Lara": "af_sky",
        "lara": "af_sky",

        # Annie
        "ann": "af_bella",
        "ANN": "af_bella",
        "Annie": "af_bella",
        "annie": "af_bella",

        # Lisa
        "lis": "af_nicole",
        "LIS": "af_nicole",
        "Lisa": "af_nicole",
        "lisa": "af_nicole",

        # Guards
        "gr1": "am_adam",
        "GR1": "am_adam",
        "gr2": "am_adam",
        "GR2": "am_adam",
        "Guard 1": "am_adam",
        "guard 1": "am_adam",
        "Guard 2": "am_adam",
        "guard 2": "am_adam",
        "Guard": "am_adam",
        "guard": "am_adam",

        # Rocco
        "r": "am_fenrir",
        "R": "am_fenrir",
        "Rocco": "am_fenrir",
        "rocco": "am_fenrir",

        # Stripper
        "strt": "af_heart",
        "STRT": "af_heart",
        "Stripper": "af_heart",
        "stripper": "af_heart",

        # Jenny
        "je": "af_alloy",
        "JE": "af_alloy",
        "Jenny": "af_alloy",
        "jenny": "af_alloy",

        # Ariana
        "a": "af_kore",
        "A": "af_kore",
        "Ariana": "af_kore",
        "ariana": "af_kore",

        # Sieglinnde
        "Sieglinnde": "af_sarah",
        "sieglinnde": "af_sarah",

        # Principal
        "Long": "am_michael",
        "Principal Long": "am_michael",
        "Principal": "am_michael",
        "principal": "am_michael",

        # Unknown
        "who": "am_echo",
        "WHO": "am_echo",
        "???": "am_echo",
        "Unknown": "am_echo",
        "unknown": "am_echo",
    }


class TestShadowsOfTrustVoiceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.voice_map_data = get_shadows_of_trust_voice_map()

    def test_all_male_characters_strictly_am_voices(self):
        males = [
            "mc", "Josh", "t", "Terry", "f", "Finn", "e", "Eddie",
            "mb", "Malcolm", "d", "Beth's dad", "tg", "Thug",
            "br", "Brian", "j", "Jackson", "ed", "Edward",
            "gr1", "Guard 1", "gr2", "Guard 2", "r", "Rocco",
            "Principal Long"
        ]
        for name in males:
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("am_"),
                f"Male character {name} got non-am voice {voice}"
            )

    def test_all_female_characters_strictly_af_voices(self):
        females = [
            "b", "Beth", "bt", "Beth Thoughts",
            "m", "Martina", "mt", "Martina Thoughts",
            "s", "Susan", "st", "Susan Thoughts",
            "n", "Naomi",
            "k", "Karen",
            "g", "Gloria",
            "i", "Ivy",
            "te", "Teacher", "Professor",
            "l", "le", "Leela",
            "jan", "Jane",
            "lar", "Lara",
            "ann", "Annie",
            "lis", "Lisa",
            "strt", "Stripper",
            "je", "Jenny",
            "a", "Ariana",
            "Sieglinnde"
        ]
        for name in females:
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("af_"),
                f"Female character {name} got non-af voice {voice}"
            )

    def test_naomi_is_female_and_overrides_renpy_default_n(self):
        self.assertTrue(self.voice_map_data["n"].startswith("af_"))
        self.assertTrue(self.voice_map_data["Naomi"].startswith("af_"))

    def test_narrator_and_default_are_am_onyx(self):
        self.assertEqual(self.voice_map_data["narrator"], "am_onyx")
        self.assertEqual(self.voice_map_data["default"], "am_onyx")
        self.assertEqual(self.voice_map_data["None"], "am_onyx")

    def test_installed_voice_map_matches_expected_if_deployed(self):
        target_path = r"D:\Games\ShadowsOfTrust-0.6-pc\ShadowsOfTrust-0.6-pc\voice_map.json"
        if os.path.exists(target_path):
            with open(target_path, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
            self.assertEqual(disk_data, self.voice_map_data)


if __name__ == "__main__":
    unittest.main()
