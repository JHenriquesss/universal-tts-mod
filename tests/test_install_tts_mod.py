import os
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True


class TestInstallTTSMod(unittest.TestCase):
    def _make_nested_game(self, root):
        outer = os.path.join(root, "GrandmasHouse-0.68-pc")
        game_root = os.path.join(outer, "GrandmasHouse-0.68-pc")
        game_dir = os.path.join(game_root, "game")
        os.makedirs(game_dir)
        with open(os.path.join(game_root, "GrandmasHouse.exe"), "w", encoding="utf-8") as f:
            f.write("fake exe marker")
        return outer, game_root, game_dir

    def test_detects_nested_renpy_game_root_from_outer_folder(self):
        from install_tts_mod import find_game_root

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, _game_dir = self._make_nested_game(tmpdir)

            self.assertEqual(os.path.normpath(game_root), os.path.normpath(find_game_root(outer)))

    def test_tts_only_plan_copies_required_files_and_root_backend_helper(self):
        from install_tts_mod import build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)

            entries = build_install_plan(outer)
            destinations = {os.path.normpath(entry.destination) for entry in entries}

            for filename in ("tts_mod.rpy", "tts_server.py", "tts_engines.py", "text_cleaner.py"):
                self.assertIn(os.path.normpath(os.path.join(game_dir, filename)), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "run_backend.bat")), destinations)

    def test_tts_only_plan_excludes_choice_overlay_and_artifacts_by_default(self):
        from install_tts_mod import build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, _game_root, _game_dir = self._make_nested_game(tmpdir)

            entries = build_install_plan(outer)
            names = {os.path.basename(entry.destination) for entry in entries}

            for forbidden in (
                "choice_hints_core.py",
                "zzz_mod_choice_consequences.rpy",
                "zzz_mod_choice_hints_generated.rpy",
                "tts_server.log",
                "tts_ready.txt",
                "__pycache__",
            ):
                self.assertNotIn(forbidden, names)
            self.assertFalse(any(name.endswith(".pyc") for name in names))

    def test_install_game_copies_tts_only_files(self):
        from install_tts_mod import install_game

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)

            result = install_game(outer)

            self.assertGreaterEqual(len(result.installed), 5)
            for filename in ("tts_mod.rpy", "tts_server.py", "tts_engines.py", "text_cleaner.py"):
                self.assertTrue(os.path.exists(os.path.join(game_dir, filename)))
            self.assertTrue(os.path.exists(os.path.join(game_root, "run_backend.bat")))
            self.assertFalse(os.path.exists(os.path.join(game_dir, "zzz_mod_choice_consequences.rpy")))

    def test_dry_run_does_not_write_files(self):
        from install_tts_mod import install_game

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)

            result = install_game(outer, dry_run=True)

            self.assertGreaterEqual(len(result.planned), 5)
            self.assertEqual([], result.installed)
            self.assertFalse(os.path.exists(os.path.join(game_dir, "tts_mod.rpy")))
            self.assertFalse(os.path.exists(os.path.join(game_root, "run_backend.bat")))

    def test_gui_installer_uses_selected_main_game_folder(self):
        from install_tts_mod_gui import install_selected_game

        messages = []

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)

            result = install_selected_game(
                askdirectory=lambda title: outer,
                showinfo=lambda title, message: messages.append((title, message)),
            )

            self.assertEqual(os.path.normpath(game_root), os.path.normpath(result.game_root))
            self.assertTrue(os.path.exists(os.path.join(game_dir, "tts_mod.rpy")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "run_backend.bat")))
            self.assertIn("TTS mod installed", messages[0][0])

    def test_gui_installer_cancel_does_not_install(self):
        from install_tts_mod_gui import install_selected_game

        messages = []

        result = install_selected_game(
            askdirectory=lambda title: "",
            showinfo=lambda title, message: messages.append((title, message)),
        )

        self.assertIsNone(result)
        self.assertEqual([], messages)


if __name__ == "__main__":
    unittest.main()
