import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
for path in (ROOT_DIR, RENPY_MOD_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from tts_client_hooks import (
    install_say_capture,
    resolve_say_text,
    resolve_say_who,
)


class FakeStore(object):
    def __init__(self, who=None, what=None):
        self._last_say_who = who
        self._last_say_what = what


class FakeState(object):
    def __init__(self):
        self.last_say_who = None
        self.last_say_what = None


class FakeExports(object):
    def __init__(self):
        self.calls = []

    def say(self, who, what, *args, **kwargs):
        self.calls.append((who, what, args, kwargs))
        return "said"


class FakeRenpy(object):
    def __init__(self):
        self.exports = FakeExports()


class SayCaptureTest(unittest.TestCase):
    """O texto da fala tem de chegar ao cliente em qualquer jogo.

    O callback ``all_character_callbacks`` do Ren'Py 7 nao entrega o texto: os
    argumentos extras vem de ``Character.cb_args``, que fica vazio quando o
    personagem nao define propriedades ``cb``. Sem o say envolto, o jogo
    conectava no backend e nao mandava nenhuma fala para ser lida.
    """

    def test_callback_without_text_falls_back_to_the_store(self):
        store = FakeStore(who="Man", what="Ey! Don't you fucking whistle at my daughter!")

        # Os kwargs reais do Ren'Py 7: sem "what" e sem "who".
        kwargs = {"interact": True, "type": "say"}

        self.assertEqual(
            resolve_say_text(kwargs, None, store),
            "Ey! Don't you fucking whistle at my daughter!",
        )
        self.assertEqual(resolve_say_who(kwargs, None, store), "Man")

    def test_captured_say_wins_over_the_store(self):
        store = FakeStore(who="Man", what="linha antiga")
        captured = "linha nova"

        self.assertEqual(resolve_say_text({}, captured, store), "linha nova")

    def test_callback_text_wins_over_everything(self):
        store = FakeStore(what="linha antiga")

        self.assertEqual(resolve_say_text({"what": "linha do callback"}, "capturada", store),
                         "linha do callback")

    def test_capture_records_the_line_sent_by_the_game(self):
        state = FakeState()
        renpy = FakeRenpy()

        self.assertTrue(install_say_capture(state, renpy))
        self.assertEqual(renpy.exports.say("Man", "Get inside."), "said")

        self.assertEqual(state.last_say_who, "Man")
        self.assertEqual(state.last_say_what, "Get inside.")

    def test_capture_is_installed_only_once(self):
        state = FakeState()
        renpy = FakeRenpy()

        self.assertTrue(install_say_capture(state, renpy))
        first = renpy.exports.say
        self.assertFalse(install_say_capture(state, renpy))
        self.assertIs(renpy.exports.say, first)

    def test_capture_failure_is_not_fatal(self):
        class BrokenExports(object):
            pass

        class BrokenRenpy(object):
            exports = BrokenExports()

        self.assertFalse(install_say_capture(FakeState(), BrokenRenpy()))

    def test_capture_resets_last_spoken_on_each_new_say(self):
        state = FakeState()
        state.last_spoken = "Yes."
        renpy = FakeRenpy()

        self.assertTrue(install_say_capture(state, renpy))
        renpy.exports.say("Alice", "Yes.")

        self.assertEqual(state.last_say_what, "Yes.")
        self.assertIsNone(state.last_spoken)


if __name__ == "__main__":
    unittest.main()
