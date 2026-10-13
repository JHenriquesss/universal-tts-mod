import os
import sys
import unittest

sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
if RENPY_MOD_DIR not in sys.path:
    sys.path.insert(0, RENPY_MOD_DIR)

from text_cleaner import TextCleaner


class TestFalcomTextCleaner(unittest.TestCase):
    """
    Testes unitários para limpeza de tags e códigos de controle da Falcom (ED6 / Trails in the Sky).
    """

    def test_removes_falcom_color_tags(self):
        raw = "#0CJoshua, did you find anything?#0C"
        cleaned = TextCleaner.clean(raw)
        self.assertEqual(cleaned, "Joshua, did you find anything?")

    def test_removes_falcom_key_wait_and_pause_tags(self):
        raw = "I understand.#1K#1000W Let's proceed to the guild."
        cleaned = TextCleaner.clean(raw)
        self.assertEqual(cleaned, "I understand. Let's proceed to the guild.")

    def test_removes_falcom_voice_and_position_tags(self):
        raw = "#1234V#0P#50FWait for me!#1K"
        cleaned = TextCleaner.clean(raw)
        self.assertEqual(cleaned, "Wait for me!")

    def test_removes_multiline_falcom_dialogue_with_embedded_tags(self):
        raw = "#0CEstelle#0C\n#2CWhat in the world is that?!#1K\n#0CCassius#0C\nCalm down, Estelle.#1K"
        cleaned = TextCleaner.clean(raw)
        self.assertNotIn("#0C", cleaned)
        self.assertNotIn("#1K", cleaned)
        self.assertIn("Estelle", cleaned)
        self.assertIn("What in the world is that?!", cleaned)
        self.assertIn("Calm down, Estelle.", cleaned)

    def test_removes_raw_byte_control_codes(self):
        raw = "Hello\x01\x02\x07world!\x03"
        cleaned = TextCleaner.clean(raw)
        self.assertEqual(cleaned, "Hello world!")

    def test_handles_complex_falcom_scena_string(self):
        raw = "#0C#1K#3S#500W#2P#1122V[Joshua]#0C\n#1CWe should report back to Schera right away.#1K"
        cleaned = TextCleaner.clean(raw)
        self.assertEqual(cleaned, "[Joshua] We should report back to Schera right away.")


if __name__ == "__main__":
    unittest.main()
