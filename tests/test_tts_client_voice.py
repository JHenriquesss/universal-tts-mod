import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


class FakeStore(object):
    def __init__(self, **attributes):
        for name, value in attributes.items():
            setattr(self, name, value)


class TestTTSClientVoice(unittest.TestCase):
    def test_strip_tags_removes_renpy_markup(self):
        from renpy_mod.tts_client_voice import strip_tags

        self.assertEqual(strip_tags("{b}Bold{/b} text"), "Bold text")
        self.assertEqual(strip_tags(""), "")
        self.assertEqual(strip_tags(None), "")

    def test_clean_speaker_name_uses_the_substitute_when_it_yields_text(self):
        from renpy_mod.tts_client_voice import clean_speaker_name

        def substitute(value):
            return "{color=#fff}Alice{/color}"

        self.assertEqual(clean_speaker_name("Alice", substitute), "Alice")
        self.assertEqual(clean_speaker_name("Alice"), "Alice")
        self.assertIsNone(clean_speaker_name(None))
        self.assertIsNone(clean_speaker_name(""))

    def test_clean_speaker_name_falls_back_when_the_substitute_fails(self):
        from renpy_mod.tts_client_voice import clean_speaker_name

        def broken(value):
            raise RuntimeError("no interpolation here")

        self.assertEqual(clean_speaker_name("{b}Bob{/b}", broken), "Bob")

    def test_collect_context_names_reads_every_source(self):
        from renpy_mod.tts_client_voice import collect_context_names

        store = FakeStore(player_name="Mia", mc_name="")
        persistent = FakeStore(player_name="michael")

        names = collect_context_names(("player_name", "mc_name"), (store, persistent))

        self.assertEqual(names, {"mia", "michael"})
        self.assertEqual(collect_context_names(("player_name",), (None,)), set())

    def test_normalize_speaker_drops_the_thought_suffix(self):
        from renpy_mod.tts_client_voice import normalize_speaker

        self.assertEqual(normalize_speaker("Mia's thoughts"), "Mia")
        self.assertEqual(normalize_speaker("Mia’s thought"), "Mia")
        self.assertEqual(normalize_speaker("Mia"), "Mia")

    def test_exact_voice_map_hit_wins(self):
        from renpy_mod.tts_client_voice import resolve_voice

        voice_map = {"mia": "af_sarah", "narrator": "af_nicole"}

        self.assertEqual(resolve_voice("Mia", voice_map), "af_sarah")

    def test_without_a_speaker_the_map_falls_back_to_narrator_then_default(self):
        from renpy_mod.tts_client_voice import resolve_voice

        self.assertEqual(
            resolve_voice(None, {"narrator": "af_nicole"}),
            "af_nicole",
        )
        self.assertEqual(
            resolve_voice(None, {"player": "af_bella"}),
            "af_bella",
        )
        self.assertEqual(
            resolve_voice(None, {"default": "af_kore"}),
            "af_kore",
        )
        self.assertEqual(
            resolve_voice(None, {}, current_voice="af_sky", default_voice="af_heart"),
            "af_sky",
        )
        self.assertEqual(
            resolve_voice(None, {}, default_voice="af_heart"),
            "af_heart",
        )

    def test_without_a_speaker_the_last_speaker_is_used(self):
        from renpy_mod.tts_client_voice import resolve_voice

        voice_map = {"mia": "af_sarah"}

        self.assertEqual(
            resolve_voice(None, voice_map, last_speaker="Mia"),
            "af_sarah",
        )

    def test_thought_suffix_resolves_to_the_character_voice(self):
        from renpy_mod.tts_client_voice import resolve_voice

        voice_map = {"mia": "af_sarah"}

        self.assertEqual(resolve_voice("Mia's thoughts", voice_map), "af_sarah")

    def test_protagonist_alias_and_player_name_use_the_mc_voice(self):
        from renpy_mod.tts_client_voice import resolve_voice

        voice_map = {"mc": "am_adam", "narrator": "af_nicole"}

        self.assertEqual(resolve_voice("Player", voice_map), "am_adam")
        self.assertEqual(resolve_voice("me", voice_map), "am_adam")
        self.assertEqual(
            resolve_voice("Mia", voice_map, player_names={"mia"}),
            "am_adam",
        )

    def test_partner_alias_and_partner_name_use_the_bf_voice(self):
        from renpy_mod.tts_client_voice import resolve_voice

        voice_map = {"bf": "af_river"}

        self.assertEqual(resolve_voice("bf", voice_map), "af_river")
        self.assertEqual(
            resolve_voice("Oliver", voice_map, bf_names={"oliver"}),
            "af_river",
        )

    def test_unknown_speaker_without_a_masculine_word_falls_back_to_the_female_pool(self):
        from renpy_mod.tts_client_voice import FEMALE_POOL, resolve_voice

        voice = resolve_voice("Zelda", {})

        self.assertIn(voice, FEMALE_POOL)

    def test_masculine_word_in_the_name_uses_the_male_pool(self):
        from renpy_mod.tts_client_voice import MALE_POOL, resolve_voice

        voice = resolve_voice("Uncle Bob", {})

        self.assertIn(voice, MALE_POOL)

    def test_the_same_speaker_always_resolves_to_the_same_voice(self):
        from renpy_mod.tts_client_voice import resolve_voice

        self.assertEqual(resolve_voice("Zelda", {}), resolve_voice("Zelda", {}))


if __name__ == "__main__":
    unittest.main()
