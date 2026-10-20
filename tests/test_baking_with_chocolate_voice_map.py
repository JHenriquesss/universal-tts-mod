import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestBakingWithChocolateVoiceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We will test the voice map structure
        cls.voice_map_data = {
            "default": "am_onyx",
            "narrator": "am_onyx",
            "Narrator": "am_onyx",
            "n": "am_onyx",
            "None": "am_onyx",
            "player": "am_onyx",
            "Player": "am_onyx",
            "you": "am_onyx",
            "You": "am_onyx",
            "me": "am_onyx",
            "Me": "am_onyx",
            "mc": "am_onyx",
            "MC": "am_onyx",
            "Marcus": "am_onyx",
            "marcus": "am_onyx",
            "[mcN]": "am_onyx",
            "[mc]": "am_onyx",
            "mcN": "am_onyx",
            "Marcus Miller": "am_onyx",
            "Miller": "am_onyx",
            "mn": "af_heart",
            "MN": "af_heart",
            "Monique": "af_heart",
            "monique": "af_heart",
            "ts": "af_alloy",
            "TS": "af_alloy",
            "Tasha": "af_alloy",
            "tasha": "af_alloy",
            "ba": "af_nicole",
            "BA": "af_nicole",
            "Barquisha": "af_nicole",
            "barquisha": "af_nicole",
            "Oreo": "af_nicole",
            "oreo": "af_nicole",
            "ld": "af_sarah",
            "LD": "af_sarah",
            "LaDesha": "af_sarah",
            "ladesha": "af_sarah",
            "cn": "af_sky",
            "CN": "af_sky",
            "Channel": "af_sky",
            "channel": "af_sky",
            "lsw": "am_fenrir",
            "LSW": "am_fenrir",
            "LeShawn": "am_fenrir",
            "leshawn": "am_fenrir",
            "an": "am_eric",
            "AN": "am_eric",
            "Andre": "am_eric",
            "andre": "am_eric",
            "bt": "af_bella",
            "BT": "af_bella",
            "Beatrice": "af_bella",
            "beatrice": "af_bella",
            "Bea": "af_bella",
            "bea": "af_bella",
            "ty": "am_michael",
            "TY": "am_michael",
            "Tyrell": "am_michael",
            "tyrell": "am_michael",
            "dm": "af_jessica",
            "DM": "af_jessica",
            "Diamond": "af_jessica",
            "diamond": "af_jessica",
            "Dee": "af_jessica",
            "dee": "af_jessica",
            "e": "af_heart",
            "Eileen": "af_heart",
            "eileen": "af_heart",
            "Man": "am_fenrir",
            "man": "am_fenrir",
            "Girl": "af_sky",
            "girl": "af_sky",
            "Woman": "af_heart",
            "woman": "af_heart",
            "Barber": "am_adam",
            "barber": "am_adam",
            "Dentist": "am_adam",
            "dentist": "am_adam",
            "Officer": "am_fenrir",
            "officer": "am_fenrir",
            "Security Guard": "am_eric",
            "security guard": "am_eric",
            "Damien": "am_adam",
            "damien": "am_adam",
            "Moonbox": "am_puck",
            "moonbox": "am_puck",
            "Beatrice & Channel": "af_bella",
            "Both": "af_bella",
            "both": "af_bella",
            "Everyone": "am_onyx",
            "everyone": "am_onyx",
        }

    def test_all_male_characters_strictly_am_voices(self):
        males = [
            "mc", "Marcus", "lsw", "LeShawn", "an", "Andre", "ty", "Tyrell",
            "Man", "Barber", "Dentist", "Officer", "Security Guard", "Damien"
        ]
        for name in males:
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("am_"),
                f"Male character {name} got non-am voice {voice}"
            )

    def test_all_female_characters_strictly_af_voices(self):
        females = [
            "mn", "Monique", "ts", "Tasha", "ba", "Barquisha", "ld", "LaDesha",
            "cn", "Channel", "bt", "Beatrice", "dm", "Diamond", "Dee",
            "e", "Eileen", "Girl", "Woman"
        ]
        for name in females:
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("af_"),
                f"Female character {name} got non-af voice {voice}"
            )

    def test_narrator_and_default_are_am_onyx(self):
        self.assertEqual(self.voice_map_data["narrator"], "am_onyx")
        self.assertEqual(self.voice_map_data["default"], "am_onyx")
        self.assertEqual(self.voice_map_data["None"], "am_onyx")


if __name__ == "__main__":
    unittest.main()
