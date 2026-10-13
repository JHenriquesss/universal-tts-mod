import os
import struct
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALCOM_MOD_DIR = os.path.join(ROOT_DIR, "falcom_mod")
if FALCOM_MOD_DIR not in sys.path:
    sys.path.insert(0, FALCOM_MOD_DIR)


SC_TEXT_PATTERN = bytes.fromhex(
    "8B 74 24 20 E9 36 FB FF FF 3C 23 0F 85 3C 06 00 00"
)
THIRD_TEXT_PATTERN = bytes.fromhex(
    "89 B3 9C 39 00 00 E9 36 FB FF FF 3C 23 0F 85 3C 06 00 00"
)
FUNCTION_PROLOGUE = bytes.fromhex(
    "55 8B EC 83 E4 C0 81 EC 74 03 00 00 53 8B D9 56 57"
)


def make_fake_pe(path, text_pattern=SC_TEXT_PATTERN):
    data = bytearray(0x400)
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", data, 0x86, 1)
    struct.pack_into("<H", data, 0x94, 0xE0)
    section = 0x80 + 24 + 0xE0
    data[section:section + 8] = b".text\0\0\0"
    struct.pack_into("<I", data, section + 8, 0x200)
    struct.pack_into("<I", data, section + 12, 0x1000)
    struct.pack_into("<I", data, section + 16, 0x200)
    struct.pack_into("<I", data, section + 20, 0x200)
    data[0x220:0x220 + len(FUNCTION_PROLOGUE)] = FUNCTION_PROLOGUE
    data[0x2A0:0x2A0 + len(text_pattern)] = text_pattern
    with open(path, "wb") as stream:
        stream.write(data)


class TestFalcomTextractor(unittest.TestCase):
    def test_signature_scanner_returns_module_relative_full_string_hook(self):
        from falcom_textractor import build_dialogue_hook_code

        with tempfile.TemporaryDirectory() as tmpdir:
            exe = os.path.join(tmpdir, "ed6_win2_DX9.exe")
            make_fake_pe(exe)

            self.assertEqual(
                build_dialogue_hook_code(exe),
                "HSFN932#4@1020:ed6_win2_DX9.exe",
            )

    def test_signature_scanner_supports_the_3rd_engine_variant(self):
        from falcom_textractor import build_dialogue_hook_code

        with tempfile.TemporaryDirectory() as tmpdir:
            exe = os.path.join(tmpdir, "ed6_win3_DX9.exe")
            make_fake_pe(exe, THIRD_TEXT_PATTERN)

            self.assertEqual(
                build_dialogue_hook_code(exe),
                "HSFN932#4@1020:ed6_win3_DX9.exe",
            )

    def test_config_contains_only_validated_hook_and_clipboard_extension(self):
        from falcom_textractor import write_textractor_config

        with tempfile.TemporaryDirectory() as tmpdir:
            exe = os.path.join(tmpdir, "ed6_win2_DX9.exe")
            textractor_dir = os.path.join(tmpdir, "tts_textractor")
            os.makedirs(textractor_dir)
            make_fake_pe(exe)

            hook_code = write_textractor_config(tmpdir, exe, textractor_dir)

            with open(os.path.join(textractor_dir, "SavedHooks.txt"), encoding="utf-8") as stream:
                saved_hooks = stream.read()
            with open(os.path.join(textractor_dir, "SavedExtensions.txt"), encoding="utf-8") as stream:
                extensions = stream.read()

            self.assertEqual(hook_code, "HSFN932#4@1020:ed6_win2_DX9.exe")
            self.assertEqual(saved_hooks.count("HSFN932#4"), 2)
            self.assertNotIn("RS932", saved_hooks)
            self.assertNotIn("HBN932", saved_hooks)
            self.assertEqual(extensions, "")


if __name__ == "__main__":
    unittest.main()
