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

    def _make_fake_textractor_runtime(self, root):
        """Runtime do Textractor ficticio: o binario real e externo ao repositorio."""
        runtime = os.path.join(root, "Textractor-5.2.0", "Textractor", "x86")
        os.makedirs(runtime)
        with open(os.path.join(runtime, "TextractorCLI.exe"), "wb") as f:
            f.write(b"MZ fake textractor cli")
        with open(os.path.join(runtime, "texthook.dll"), "wb") as f:
            f.write(b"fake texthook")
        with open(os.path.join(runtime, "Copy to Clipboard.xdll"), "wb") as f:
            f.write(b"fake extension")
        return runtime

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
            runtime = self._make_fake_textractor_runtime(tmpdir)
            entries = build_install_plan(game_root, textractor_runtime_dir=runtime)

            destinations = {os.path.normpath(entry.destination) for entry in entries}

            # Backend
            for filename in ("tts_server.py", "tts_engines.py", "text_cleaner.py", "run_backend.bat"):
                self.assertIn(os.path.normpath(os.path.join(game_root, filename)), destinations)

            # Falcom hook / launcher
            self.assertIn(os.path.normpath(os.path.join(game_root, "falcom_text_hook.py")), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "falcom_voice_map.py")), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "falcom_win32_runtime.py")), destinations)
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
        import subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_mock_falcom_game(tmpdir)
            runtime = self._make_fake_textractor_runtime(tmpdir)
            result = install_game(game_root, textractor_runtime_dir=runtime)

            self.assertEqual(result.engine, "falcom")
            self.assertTrue(os.path.exists(os.path.join(game_root, "tts_server.py")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "falcom_text_hook.py")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "falcom_voice_map.py")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "falcom_win32_runtime.py")))
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

            # Verify installed falcom_text_hook.py imports cleanly from game_root without repo sys.path
            proc = subprocess.run(
                [sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {game_root!r}); import falcom_text_hook"],
                cwd=game_root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, proc.returncode, f"Installed falcom_text_hook failed to import: {proc.stderr}")


    def test_falcom_plan_raises_actionable_error_when_textractor_runtime_missing(self):
        from install_tts_mod import TextractorRuntimeMissing

        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_mock_falcom_game(tmpdir)
            missing = os.path.join(tmpdir, "runtime-ausente")

            with self.assertRaises(TextractorRuntimeMissing) as ctx:
                build_install_plan(game_root, textractor_runtime_dir=missing)

            message = str(ctx.exception)
            self.assertIn(missing, message)
            self.assertIn("Textractor", message)

    def test_falcom_plan_raises_when_textractor_cli_binary_is_missing(self):
        from install_tts_mod import TextractorRuntimeMissing

        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_mock_falcom_game(tmpdir)
            runtime = os.path.join(tmpdir, "runtime-incompleto")
            os.makedirs(runtime)

            with self.assertRaises(TextractorRuntimeMissing) as ctx:
                build_install_plan(game_root, textractor_runtime_dir=runtime)

            message = str(ctx.exception)
            self.assertIn("TextractorCLI.exe", message)
            self.assertIn(runtime, message)

    def test_renpy_install_does_not_require_textractor_runtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = os.path.join(tmpdir, "JogoRenPy")
            os.makedirs(os.path.join(game_root, "game"))
            with open(os.path.join(game_root, "JogoRenPy.exe"), "w", encoding="utf-8") as f:
                f.write("fake exe marker")

            entries = build_install_plan(
                game_root,
                textractor_runtime_dir=os.path.join(tmpdir, "runtime-ausente"),
            )

            self.assertTrue(entries)


if __name__ == "__main__":
    unittest.main()
