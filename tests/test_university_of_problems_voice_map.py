import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_GAME_ROOT = r"D:\Games\University_of_Problems-1.9.5-Extended-pc\University_of_Problems-1.9.5-(Extended)-pc"
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


def build_uop_voice_map():
    """Generates the canonical Kokoro TTS voice map for University of Problems."""
    return {
        # Protagonist / Narrator / Unassigned
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
        "name": "am_onyx",
        "[name]": "am_onyx",
        "mct": "am_onyx",
        "[name]’s thoughts": "am_onyx",
        "[name]'s thoughts": "am_onyx",
        "[name] thoughts": "am_onyx",

        # Unknown / Utility
        "un": "am_onyx",
        "un2": "am_onyx",
        "un3": "am_onyx",
        "un4": "am_onyx",
        "???": "am_onyx",
        "tv": "am_onyx",
        "TV": "am_onyx",
        "tel": "am_onyx",
        "Telephone": "am_onyx",
        "cinema": "am_onyx",
        "Screen": "am_onyx",

        # Male Characters
        "guy": "am_adam",
        "Guy": "am_adam",
        "cm": "am_puck",
        "College buddy": "am_puck",
        "crowd": "am_onyx",
        "Crowd": "am_onyx",
        "travis": "am_eric",
        "Travis": "am_eric",
        "professor": "am_michael",
        "Professor": "am_michael",
        "commentator1": "am_eric",
        "Commentator #1": "am_eric",
        "commentator2": "am_adam",
        "Commentator #2": "am_adam",
        "e": "am_adam",
        "Eric": "am_adam",
        "eric": "am_adam",
        "d": "am_puck",
        "Daniel": "am_puck",
        "daniel": "am_puck",
        "w": "am_michael",
        "President Pollard": "am_michael",
        "Pollard": "am_michael",
        "j": "am_adam",
        "Jack": "am_adam",
        "jack": "am_adam",
        "landeck": "am_michael",
        "Dr Landeck": "am_michael",
        "niko": "am_puck",
        "Niko": "am_puck",
        "m": "am_eric",
        "Mortimo": "am_eric",
        "mortimo": "am_eric",
        "ma": "am_adam",
        "Marco": "am_adam",
        "marco": "am_adam",
        "v": "am_fenrir",
        "Vlad": "am_fenrir",
        "vlad": "am_fenrir",
        "ja": "am_fenrir",
        "Jaime": "am_fenrir",
        "jaime": "am_fenrir",
        "f": "am_puck",
        "Fergus": "am_puck",
        "fergus": "am_puck",
        "maxi": "am_fenrir",
        "Maximus": "am_fenrir",
        "maximus": "am_fenrir",
        "mic": "am_adam",
        "Mickey": "am_adam",
        "mickey": "am_adam",
        "zac": "am_eric",
        "Zac": "am_eric",
        "zac": "am_eric",

        # Female Characters - Main Heroines & College Girls
        "a": "af_heart",
        "Ashley": "af_heart",
        "ashley": "af_heart",
        "asht": "af_heart",
        "Ashley’s thoughts": "af_heart",
        "Ashley's thoughts": "af_heart",

        "c": "af_bella",
        "Carol": "af_bella",
        "carol": "af_bella",
        "ct": "af_bella",
        "Carol’s thoughts": "af_bella",
        "Carol's thoughts": "af_bella",

        "s": "af_sarah",
        "Sara": "af_sarah",
        "sara": "af_sarah",
        "st": "af_sarah",
        "Sara’s thoughts": "af_sarah",
        "Sara's thoughts": "af_sarah",

        "n": "af_nicole",
        "Natalie": "af_nicole",
        "natalie": "af_nicole",
        "nt": "af_nicole",
        "Natalie’s thoughts": "af_nicole",
        "Natalie's thoughts": "af_nicole",

        "r": "af_sky",
        "Rachel": "af_sky",
        "rachel": "af_sky",
        "rt": "af_sky",
        "Rachel’s thoughts": "af_sky",
        "Rachel's thoughts": "af_sky",

        "ro": "af_kore",
        "Roxy": "af_kore",
        "roxy": "af_kore",
        "rot": "af_kore",
        "Roxy’s thoughts": "af_kore",
        "Roxy's thoughts": "af_kore",

        "y": "af_aoede",
        "Yuki": "af_aoede",
        "yuki": "af_aoede",
        "yt": "af_aoede",
        "Yuki’s thoughts": "af_aoede",
        "Yuki's thoughts": "af_aoede",

        "k": "af_river",
        "Kim": "af_river",
        "kim": "af_river",
        "kt": "af_river",
        "Kim’s thoughts": "af_river",
        "Kim's thoughts": "af_river",

        "nik": "af_jessica",
        "Nikki": "af_jessica",
        "nikki": "af_jessica",
        "nikt": "af_jessica",
        "Nikki’s thoughts": "af_jessica",
        "Nikki's thoughts": "af_jessica",

        # Supporting Female Characters
        "ab": "af_heart",
        "Abby": "af_heart",
        "abby": "af_heart",

        "alyssa": "af_bella",
        "Alyssa": "af_bella",

        "cleo": "af_sky",
        "Cleo": "af_sky",

        "cou": "af_nicole",
        "Courtney": "af_nicole",
        "courtney": "af_nicole",

        "dana": "af_sarah",
        "Dana": "af_sarah",

        "emma": "af_kore",
        "Emma": "af_kore",

        "erin": "af_aoede",
        "Erin": "af_aoede",

        "girl": "af_heart",
        "Girl": "af_heart",
        "girls": "af_heart",
        "Girls": "af_heart",

        "gwen": "af_river",
        "Gwen": "af_river",

        "ingrid": "af_jessica",
        "Ingrid": "af_jessica",

        "ivy": "af_bella",
        "Ivy": "af_bella",

        "jackie": "af_sky",
        "Jackie": "af_sky",

        "kiely": "af_heart",
        "Kiely": "af_heart",

        "lau": "af_sarah",
        "Laura": "af_sarah",
        "laura": "af_sarah",

        "lexi": "af_kore",
        "Lexi": "af_kore",

        "mall": "af_aoede",
        "Mallory": "af_aoede",
        "mallory": "af_aoede",

        "mary": "af_nicole",
        "Mary": "af_nicole",

        "med": "af_aoede",
        "Nurse": "af_aoede",

        "mom": "af_sarah",
        "Mom": "af_sarah",

        "mr": "af_jessica",
        "Mrs Cooper": "af_jessica",

        "msmerritt": "af_sky",
        "Ms Merritt": "af_sky",

        "mspowell": "af_bella",
        "Ms Powell": "af_bella",

        "nm": "af_river",
        "Ms Meadows": "af_river",

        "peggy": "af_river",
        "Peggy": "af_river",

        "rochelle": "af_heart",
        "Rochelle": "af_heart",

        "sa": "af_bella",
        "Sasha": "af_bella",
        "sasha": "af_bella",

        "solberg": "af_kore",
        "Ms. Solberg": "af_kore",

        "taylor": "af_sky",
        "Taylor": "af_sky",

        "waitress": "af_heart",
        "Waitress": "af_heart",
    }


class TestUniversityOfProblemsVoiceMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        voice_map_path = os.path.join(TARGET_GAME_DIR, "voice_map.json")
        if not os.path.exists(voice_map_path):
            voice_map_path = os.path.join(TARGET_GAME_ROOT, "voice_map.json")
        if os.path.exists(voice_map_path):
            with open(voice_map_path, "r", encoding="utf-8") as f:
                cls.voice_map_data = json.load(f)
        else:
            cls.voice_map_data = {}

    def test_build_uop_voice_map_validity(self):
        vmap = build_uop_voice_map()
        self.assertTrue(bool(vmap))
        for k, v in vmap.items():
            self.assertTrue(v.startswith(("af_", "am_")), f"Invalid voice {v} for key {k}")

    def test_deployed_voice_map_matches_canonical(self):
        if not self.voice_map_data:
            self.skipTest("Target voice_map.json not yet installed on disk")
        canonical = build_uop_voice_map()
        for k, v in canonical.items():
            self.assertIn(k, self.voice_map_data, f"Missing key in deployed voice_map: {k}")
            self.assertEqual(self.voice_map_data[k], v, f"Mismatch for key {k}")

    def test_all_male_characters_strictly_am_voices(self):
        canonical = build_uop_voice_map()
        males = [
            "mc", "MC", "name", "[name]", "mct",
            "guy", "Guy", "cm", "College buddy", "crowd", "Crowd",
            "travis", "Travis", "professor", "Professor",
            "commentator1", "Commentator #1", "commentator2", "Commentator #2",
            "e", "Eric", "d", "Daniel", "w", "President Pollard",
            "j", "Jack", "landeck", "Dr Landeck", "niko", "Niko",
            "m", "Mortimo", "ma", "Marco", "v", "Vlad",
            "ja", "Jaime", "f", "Fergus", "maxi", "Maximus",
            "mic", "Mickey", "zac", "Zac"
        ]
        for name in males:
            self.assertIn(name, canonical)
            voice = canonical[name]
            self.assertTrue(
                voice.startswith("am_"),
                f"Male character {name} got non-am voice {voice}",
            )

    def test_all_female_characters_strictly_af_voices(self):
        canonical = build_uop_voice_map()
        females = [
            "a", "Ashley", "asht", "Ashley’s thoughts",
            "c", "Carol", "ct", "Carol’s thoughts",
            "s", "Sara", "st", "Sara’s thoughts",
            "n", "Natalie", "nt", "Natalie’s thoughts",
            "r", "Rachel", "rt", "Rachel’s thoughts",
            "ro", "Roxy", "rot", "Roxy’s thoughts",
            "y", "Yuki", "yt", "Yuki’s thoughts",
            "k", "Kim", "kt", "Kim’s thoughts",
            "nik", "Nikki", "nikt", "Nikki’s thoughts",
            "ab", "Abby", "alyssa", "Alyssa", "cleo", "Cleo",
            "cou", "Courtney", "dana", "Dana", "emma", "Emma",
            "erin", "Erin", "girl", "Girl", "girls", "Girls",
            "gwen", "Gwen", "ingrid", "Ingrid", "ivy", "Ivy",
            "jackie", "Jackie", "kiely", "Kiely", "lau", "Laura",
            "lexi", "Lexi", "mall", "Mallory", "mary", "Mary",
            "med", "Nurse", "mom", "Mom", "mr", "Mrs Cooper",
            "msmerritt", "Ms Merritt", "mspowell", "Ms Powell",
            "nm", "Ms Meadows", "peggy", "Peggy", "rochelle", "Rochelle",
            "sa", "Sasha", "solberg", "Ms. Solberg", "taylor", "Taylor",
            "waitress", "Waitress"
        ]
        for name in females:
            self.assertIn(name, canonical)
            voice = canonical[name]
            self.assertTrue(
                voice.startswith("af_"),
                f"Female character {name} got non-af voice {voice}",
            )


if __name__ == "__main__":
    unittest.main()
