import argparse
import os
import tempfile
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(ROOT_DIR, "extract_menu_hints_generic.py")


class TestMenuHintsExtractor(unittest.TestCase):
    def test_extract_hints_from_bytes(self):
        from extract_menu_hints_generic import extract_choice_hints

        data = b'''
label start:
    menu:
        "Help her":
            $ love += 1
            $ route_alice = True
        "Leave":
            jump bad_end
label other:
    menu:
        "Help her":
            $ love -= 1
'''

        hints = extract_choice_hints(data)

        self.assertEqual("love += 1; route_alice = True", hints[("start", "Help her")])
        self.assertEqual("Jump -> bad_end", hints[("start", "Leave")])
        self.assertEqual("love -= 1", hints[("other", "Help her")])

    def test_render_generated_hints_output_shape(self):
        from extract_menu_hints_generic import render_generated_hints

        output = render_generated_hints({("start", "Help her"): "love += 1"})

        self.assertIn("init -2 python:", output)
        self.assertIn("GENERATED_CHOICE_HINTS = {", output)
        self.assertIn("('start', 'Help her'): 'love += 1'", output)

    def test_cli_parser_accepts_paths_and_derives_defaults(self):
        from extract_menu_hints_generic import build_arg_parser, resolve_paths

        parser = build_arg_parser()
        args = parser.parse_args(["--game-path", "game"])
        archive, output = resolve_paths(args)

        self.assertEqual(os.path.join("game", "scripts.rpa"), archive)
        self.assertEqual(os.path.join("game", "zzz_mod_choice_hints_generated.rpy"), output)

        args = parser.parse_args(["--archive", "a.rpa", "--output", "out.rpy"])
        archive, output = resolve_paths(args)

        self.assertEqual("a.rpa", archive)
        self.assertEqual("out.rpy", output)

    def test_run_extraction_writes_output_file(self):
        from extract_menu_hints_generic import run_extraction

        data = b'label start:\n    menu:\n        "Go":\n            $ points += 1\n'

        with tempfile.TemporaryDirectory() as tmpdir:
            archive = os.path.join(tmpdir, "scripts.rpa")
            output = os.path.join(tmpdir, "hints.rpy")
            with open(archive, "wb") as f:
                f.write(data)

            count = run_extraction(archive, output)

            self.assertEqual(1, count)
            with open(output, "r", encoding="utf-8") as f:
                rendered = f.read()
            self.assertIn("GENERATED_CHOICE_HINTS", rendered)
            self.assertIn("points += 1", rendered)

    def test_script_has_no_personal_hardcoded_windows_path(self):
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertNotIn("C:\\Users\\joseh", source)
        self.assertNotIn("How_I_Became_a_Hero", source)


if __name__ == "__main__":
    unittest.main()
