import os
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


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

    def test_detects_nested_rpgmaker_mz_game_root(self):
        """Um MZ dentro de outra pasta precisa ser detectado como o jogo real.

        A deteccao por fallback so olha a pasta informada, entao um jogo
        aninhado nunca era encontrado e o instalador abortava sem motivo claro.
        """
        from install_tts_mod import detect_game_engine

        with tempfile.TemporaryDirectory() as tmpdir:
            outer = os.path.join(tmpdir, "Outer")
            game_root = os.path.join(outer, "Inner")
            os.makedirs(os.path.join(game_root, "data"))
            os.makedirs(os.path.join(game_root, "js"))
            with open(os.path.join(game_root, "js", "rmz_core.js"), "w", encoding="utf-8") as f:
                f.write("// rmz_core")
            with open(os.path.join(game_root, "data", "System.json"), "w", encoding="utf-8") as f:
                f.write("{}")

            engine, detected_root = detect_game_engine(outer)

            self.assertEqual(engine, "rpgmaker_mz")
            self.assertEqual(os.path.normpath(detected_root), os.path.normpath(game_root))

    def test_tts_only_plan_copies_required_files_and_root_backend_helper(self):
        from install_tts_mod import build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)

            entries = build_install_plan(outer)
            destinations = {os.path.normpath(entry.destination) for entry in entries}

            for filename in (
                "tts_mod.rpy",
                "tts_server.py",
                "tts_engines.py",
                "text_cleaner.py",
                "tts_protocol.py",
                "tts_client_state.py",
                "tts_client_voice.py",
                "tts_client_hooks.py",
                "tts_client_auto.py",
                "tts_client_commands.py",
                "tts_client_speech.py",
            ):
                self.assertIn(os.path.normpath(os.path.join(game_dir, filename)), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "run_backend.bat")), destinations)
            self.assertIn(os.path.normpath(os.path.join(game_root, "JOGAR_COM_TTS.bat")), destinations)

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
            for filename in (
                "tts_mod.rpy",
                "tts_server.py",
                "tts_engines.py",
                "text_cleaner.py",
                "tts_protocol.py",
                "tts_client_state.py",
                "tts_client_voice.py",
                "tts_client_hooks.py",
                "tts_client_auto.py",
                "tts_client_commands.py",
                "tts_client_speech.py",
            ):
                self.assertTrue(os.path.exists(os.path.join(game_dir, filename)))
            self.assertTrue(os.path.exists(os.path.join(game_root, "run_backend.bat")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "JOGAR_COM_TTS.bat")))
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
            self.assertFalse(os.path.exists(os.path.join(game_root, "JOGAR_COM_TTS.bat")))

    def test_install_game_with_voice_map_copies_to_game_and_root(self):
        from install_tts_mod import install_game

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)
            vmap_path = os.path.join(tmpdir, "custom_voice_map.json")
            with open(vmap_path, "w", encoding="utf-8") as f:
                f.write('{"test_char": "af_heart"}')

            result = install_game(outer, voice_map=vmap_path)

            self.assertTrue(os.path.exists(os.path.join(game_dir, "voice_map.json")))
            self.assertTrue(os.path.exists(os.path.join(game_root, "voice_map.json")))

    def test_install_game_with_choice_hints_file_copies_overlay_and_custom_hints(self):
        from install_tts_mod import install_game

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)
            hints_path = os.path.join(tmpdir, "my_custom_hints.rpy")
            with open(hints_path, "w", encoding="utf-8") as f:
                f.write('GENERATED_CHOICE_HINTS = {("label", "cap"): "effect"}')

            result = install_game(outer, choice_hints_file=hints_path)

            self.assertTrue(os.path.exists(os.path.join(game_dir, "choice_hints_core.py")))
            self.assertTrue(os.path.exists(os.path.join(game_dir, "zzz_mod_choice_consequences.rpy")))
            self.assertTrue(os.path.exists(os.path.join(game_dir, "zzz_mod_choice_hints_generated.rpy")))
            with open(os.path.join(game_dir, "zzz_mod_choice_hints_generated.rpy"), "r", encoding="utf-8") as f:
                self.assertIn("effect", f.read())

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
            self.assertTrue(os.path.exists(os.path.join(game_root, "JOGAR_COM_TTS.bat")))
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

    def test_install_creates_outer_delegate_launchers_for_nested_game(self):
        from install_tts_mod import install_game

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, _game_dir = self._make_nested_game(tmpdir)

            install_game(outer)

            outer_jogar = os.path.join(outer, "jogar.bat")
            outer_jogar_tts = os.path.join(outer, "JOGAR_COM_TTS.bat")
            self.assertTrue(os.path.exists(outer_jogar), "Missing outer jogar.bat")
            self.assertTrue(os.path.exists(outer_jogar_tts), "Missing outer JOGAR_COM_TTS.bat")
            with open(outer_jogar_tts, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("GrandmasHouse-0.68-pc", content)

    def test_install_game_with_custom_default_voice(self):
        from install_tts_mod import install_game

        with tempfile.TemporaryDirectory() as tmpdir:
            outer, game_root, game_dir = self._make_nested_game(tmpdir)

            install_game(outer, default_voice="am_onyx")

            tts_mod_dest = os.path.join(game_dir, "tts_mod.rpy")
            self.assertTrue(os.path.exists(tts_mod_dest))
            with open(tts_mod_dest, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn('TTS_VOICE = "am_onyx"', content)


if __name__ == "__main__":
    unittest.main()

