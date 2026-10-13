import os
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from install_tts_mod import detect_game_engine, build_install_plan, install_game, find_game_root
from tests.test_falcom_textractor import make_fake_pe


class TestFalcomInstaller(unittest.TestCase):
    """
    Testes unitários para detecção e instalação do mod TTS em jogos Falcom (Trails in the Sky SC / ED6).
    """

    def _make_mock_falcom_game(self, root):
        game_root = os.path.join(root, "Trails in the Sky SC")
        os.makedirs(game_root, exist_ok=True)
        # Cria arquivos típicos do Trails in the Sky SC
        make_fake_pe(os.path.join(game_root, "ed6_win2_DX9.exe"))
        with open(os.path.join(game_root, "ED6_DT06.dat"), "w", encoding="utf-8") as f:
            f.write("fake dat marker")
        with open(os.path.join(game_root, "ED6_DT06.dir"), "w", encoding="utf-8") as f:
            f.write("fake dir marker")
        return game_root

    def test_detects_falcom_engine_by_exe_and_dat_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_mock_falcom_game(tmpdir)
            engine, detected_root = detect_game_engine(game_root)

            self.assertEqual(engine, "falcom")
            self.assertEqual(os.path.normpath(detected_root), os.path.normpath(game_root))

    def test_find_game_root_resolves_falcom_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_mock_falcom_game(tmpdir)
            self.assertEqual(os.path.normpath(game_root), os.path.normpath(find_game_root(game_root)))

    def test_build_install_plan_for_falcom_includes_backend_and_hook_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_mock_falcom_game(tmpdir)
            entries = build_install_plan(game_root)

            destinations = {os.path.normpath(entry.destination) for entry in entries}

            # Backend
            for filename in ("tts_server.py", "tts_engines.py", "text_cleaner.py", "run_backend.bat"):
                self.assertIn(os.path.normpath(os.path.join(game_root, filename)), destinations)

            # Falcom hook / launcher
            self.assertIn(os.path.normpath(os.path.join(game_root, "falcom_text_hook.py")), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "JOGAR_COM_TTS.bat")), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "falcom_launcher.py")), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "falcom_textractor.py")), destinations)
            self.assertIn(
                os.path.normpath(os.path.join(game_root, "tts_textractor", "TextractorCLI.exe")),
                destinations,
            )
            self.assertNotIn(
                os.path.normpath(os.path.join(game_root, "tts_textractor", "Copy to Clipboard.xdll")),
                destinations,
            )

    def test_install_game_copies_falcom_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_mock_falcom_game(tmpdir)
            result = install_game(game_root)

            self.assertEqual(result.engine, "falcom")
            self.assertTrue(os.path.exists(os.path.join(game_root, "tts_server.py")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "falcom_text_hook.py")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "falcom_launcher.py")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "JOGAR_COM_TTS.bat")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "tts_textractor", "TextractorCLI.exe")))
            with open(
                os.path.join(game_root, "tts_textractor", "SavedHooks.txt"),
                encoding="utf-8",
            ) as stream:
                saved_hooks = stream.read()
            self.assertIn("HSFN932#4", saved_hooks)
            self.assertNotIn("RS932", saved_hooks)


if __name__ == "__main__":
    unittest.main()
