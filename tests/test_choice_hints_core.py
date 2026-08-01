import os
import re
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME_RPY = os.path.join(ROOT_DIR, "renpy_mod", "zzz_mod_choice_consequences.rpy")


class TestChoiceHintsCore(unittest.TestCase):
    def test_curated_hints_override_generated_and_aliases_are_registered(self):
        from renpy_mod.choice_hints_core import build_choice_hints, lookup_choice_hint

        hints = build_choice_hints(
            generated={("lab", "Don’t go"): "generated", "Plain": "generated plain"},
            curated={("lab", "Don't go"): "curated"},
        )

        self.assertEqual("curated", lookup_choice_hint(hints, "lab", "Don’t go"))
        self.assertEqual("curated", lookup_choice_hint(hints, "lab", "Don't go"))
        self.assertEqual("generated plain", lookup_choice_hint(hints, None, "Plain"))

    def test_label_scoped_lookup_does_not_leak_other_label_caption(self):
        from renpy_mod.choice_hints_core import build_choice_hints, lookup_choice_hint

        hints = build_choice_hints(
            generated={
                ("scene_a", "Say nothing"): "a consequence",
                ("scene_b", "Say nothing"): "b consequence",
            },
            curated={},
        )

        self.assertEqual("a consequence", lookup_choice_hint(hints, "scene_a", "Say nothing"))
        self.assertEqual("b consequence", lookup_choice_hint(hints, "scene_b", "Say nothing"))
        self.assertIsNone(lookup_choice_hint(hints, "scene_c", "Say nothing"))

    def test_display_caption_strips_requirement_prefixes_only_when_real_text_remains(self):
        from renpy_mod.choice_hints_core import display_choice_caption

        self.assertEqual("Go outside", display_choice_caption("(Charisma: 5) Go outside"))
        self.assertEqual("(Stay)", display_choice_caption("(Stay)"))

    def test_hint_format_colors_positive_negative_and_neutral_chunks(self):
        from renpy_mod.choice_hints_core import format_hint_for_display

        formatted = format_hint_for_display("Requer: key; love += 1, money -= 2; Ramo Alice")

        self.assertIn("{color=#4ade80}love += 1{/color}", formatted)
        self.assertIn("{color=#f87171}money -= 2{/color}", formatted)
        self.assertIn("{color=#c8c8c8}Ramo Alice{/color}", formatted)
        self.assertNotIn("Requer", formatted)

    def test_unknown_caption_returns_none(self):
        from renpy_mod.choice_hints_core import build_choice_hints, lookup_choice_hint

        hints = build_choice_hints(generated={"Known": "hint"}, curated={})

        self.assertIsNone(lookup_choice_hint(hints, None, "Unknown"))


class TestChoiceOverlayCompatibility(unittest.TestCase):
    def test_public_screen_names_remain_declared(self):
        with open(RUNTIME_RPY, "r", encoding="utf-8") as f:
            source = f.read()

        for screen_name in ("mod_choice_row", "choice", "consequences_stats_overlay", "mod_toolbar"):
            self.assertRegex(source, r"(?m)^screen\s+" + re.escape(screen_name) + r"\s*\(")

    def test_runtime_file_delegates_core_logic_to_choice_hints_core(self):
        with open(RUNTIME_RPY, "r", encoding="utf-8") as f:
            source = f.read()

        self.assertIn("choice_hints_core", source)
        self.assertNotIn("def mod_hint_chunk_color", source)
        self.assertNotIn("def mod_strip_requirement_segments", source)


if __name__ == "__main__":
    unittest.main()
