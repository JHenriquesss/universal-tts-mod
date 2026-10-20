import json
import os
import unittest

sys_dont_write_bytecode = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_GAME_ROOT = os.path.join(
    PROJECT_ROOT,
    "Jogo atual",
    "GrandmasHouse-0.53-pc",
    "GrandmasHouse-0.53-pc",
)
TARGET_GAME_DIR = os.path.join(TARGET_GAME_ROOT, "game")


class TestGrandmasHouseVoiceMap(unittest.TestCase):
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

    def setUp(self):
        if not self.voice_map_data:
            self.skipTest("GrandmasHouse-0.53-pc voice_map.json not found on disk")

    def test_voice_map_exists_and_not_empty(self):
        self.assertTrue(bool(self.voice_map_data), "voice_map.json should exist and not be empty")

    def test_protagonist_and_narrator_voices(self):
        for tag in ("mc", "MC", "mcN", "[mcN]", "Thomas", "thomas", "narrator", "default", "None", "you", "me"):
            self.assertIn(tag, self.voice_map_data)
            self.assertEqual(
                self.voice_map_data[tag],
                "am_onyx",
                f"Tag {tag} expected am_onyx but got {self.voice_map_data.get(tag)}",
            )

    def test_all_male_characters_strictly_am_voices(self):
        males = [
            "mc", "MC", "mcN", "Thomas", "thomas",
            "omar", "Omar",
            "prst", "Father Peters", "father peters", "Peters",
            "jer", "Jerome", "jerome",
            "marc", "Marcel", "marcel",
            "lr", "Larry", "larry",
        ]
        for name in males:
            self.assertIn(name, self.voice_map_data)
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("am_"),
                f"Male character {name} got non-am voice {voice}",
            )

    def test_all_female_characters_strictly_af_voices(self):
        females = [
            "l", "e", "Elizabeth", "elizabeth", "Grandma", "grandma",
            "nn", "Allison", "allison",
            "a", "Amelia", "amelia",
            "c", "Catherine", "catherine",
            "shw", "Shawna", "shawna",
            "aal", "Aaliyah", "aaliyah",
            "maid", "Shizuka", "shizuka",
            "mass", "Aiko", "aiko",
            "jam", "Jamila", "jamila",
            "bty", "Betty", "betty",
            "fi", "Fiona", "fiona",
            "soph", "Sophia", "sophia",
            "tya", "Tanya", "tanya",
            "doc", "Priya", "priya",
            "eln", "Elaine", "elaine",
            "krn", "Karen", "karen",
            "mbl", "Mabel", "mabel",
            "smar", "Sister Maria", "sister maria",
            "mila", "Mila", "mila",
            "jada", "Jada", "jada",
            "svt", "Svetlana", "svetlana",
            "lina", "Lina", "lina",
            "nbr", "Natalia", "natalia",
            "ply", "Polly", "polly",
            "cop", "Sandra", "sandra",
            "ri", "Riona", "riona",
            "isa", "Isabella", "isabella",
            "asa", "Asami", "asami",
            "oph", "Ophelia", "ophelia",
            "pav", "Paveena", "paveena",
            "lil", "Lily", "lily",
            "pet", "Petunia", "petunia",
            "twn", "Twins", "twins",
            "ela", "Ella", "ella",
            "eli", "Ellie", "ellie",
            "zel", "Zelda", "zelda",
            "jos", "Josianne", "josianne",
            "minn", "Minnie", "minnie",
            "dog", "Molly", "molly",
            "ana", "Annabelle", "annabelle",
            "jas", "Jasmine", "jasmine",
            "bran", "Brandi", "brandi",
            "an", "Anne", "anne",
            "imo", "Imogene", "imogene",
            "kar", "Karina", "karina",
            "lee", "Misses Lee", "misses lee",
        ]
        for name in females:
            self.assertIn(name, self.voice_map_data)
            voice = self.voice_map_data[name]
            self.assertTrue(
                voice.startswith("af_"),
                f"Female character {name} got non-af voice {voice}",
            )


if __name__ == "__main__":
    unittest.main()
