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

    def test_install_direct_game_root_does_not_create_launchers_in_parent_folder(self):
        from install_tts_mod import install_game

        with tempfile.TemporaryDirectory() as tmpdir:
            collection_dir = os.path.join(tmpdir, "VisualNovels")
            game_root = os.path.join(collection_dir, "MyGame")
            game_dir = os.path.join(game_root, "game")
            os.makedirs(game_dir, exist_ok=True)
            with open(os.path.join(game_root, "MyGame.exe"), "wb") as f:
                f.write(b"MZ")
            with open(os.path.join(game_dir, "scripts.rpa"), "wb") as f:
                f.write(b"RPA-3.0 ")

            install_game(game_root)

            self.assertFalse(os.path.exists(os.path.join(collection_dir, "jogar.bat")))
            self.assertFalse(os.path.exists(os.path.join(collection_dir, "JOGAR_COM_TTS.bat")))

    def test_validate_entries_does_not_drop_files_when_repo_parent_is_named_tests(self):
        from unittest import mock
        from install_tts_mod import CopyEntry, _validate_entries

        fake_root = os.path.join("C:", os.sep, "work", "tests", "tts_repo")
        fake_src = os.path.join(fake_root, "renpy_mod", "tts_server.py")
        with mock.patch("install_tts_mod.PROJECT_ROOT", fake_root):
            kept = _validate_entries([CopyEntry(fake_src, os.path.join("C:", os.sep, "game", "tts_server.py"))])
        self.assertEqual(len(kept), 1)

    def test_launchers_and_installer_scripts_are_consistent_with_onnx_runtime(self):
        with open(os.path.join(ROOT_DIR, "falcom_mod", "JOGAR_COM_TTS.bat"), "r", encoding="utf-8") as f:
            falcom_bat = f.read()
        self.assertIn(r"%LOCALAPPDATA%\UniversalKokoroTTS\runtime\Scripts\python.exe", falcom_bat)

        with open(os.path.join(ROOT_DIR, "instalar.bat"), "r", encoding="utf-8") as f:
            instalar = f.read()
        self.assertIn(r".venv\Scripts\python.exe -m spacy download en_core_web_sm", instalar)

        for rel in (("renpy_mod", "run_backend.bat"), ("renpy_mod", "tts_client_state.py")):
            with open(os.path.join(ROOT_DIR, *rel), "r", encoding="utf-8") as f:
                self.assertNotIn("PyTorch so-CPU", f.read(), f"Stale PyTorch comment in {rel}")


def _batch_lines_reading_errorlevel_inside_a_block(source):
    """Linhas que leem ``%errorlevel%`` dentro de um bloco ``( ... )``.

    O cmd expande ``%var%`` quando le o bloco inteiro, antes de rodar o
    primeiro comando dele. Dentro do bloco, ``%errorlevel%`` ainda e o valor
    de antes do bloco: o instalar.bat acusava erro depois de um winget bem
    sucedido e deixava passar a falha do ``python -m venv``. ``if errorlevel 1``
    e avaliado na hora e e a forma correta.
    """
    offending = []
    depth = 0
    for number, raw in enumerate(source.splitlines(), 1):
        line = raw.strip()
        if line.startswith("::") or line.lower().startswith("rem "):
            continue
        if depth > 0 and "%errorlevel%" in line.lower():
            offending.append((number, line))
        depth += line.count("(") - line.count(")")
        depth = max(depth, 0)
    return offending


class TestBatchScriptsErrorlevel(unittest.TestCase):
    def test_batch_scripts_do_not_read_errorlevel_inside_blocks(self):
        import subprocess

        tracked = subprocess.run(
            ["git", "ls-files", "*.bat"], cwd=ROOT_DIR, capture_output=True, text=True
        ).stdout.split()
        self.assertIn("instalar.bat", tracked)
        for rel in tracked:
            with open(os.path.join(ROOT_DIR, rel), "r", encoding="utf-8", errors="replace") as f:
                offending = _batch_lines_reading_errorlevel_inside_a_block(f.read())
            self.assertEqual(offending, [], f"{rel} reads %errorlevel% inside a block")

    def test_detector_flags_the_parse_time_expansion_bug(self):
        bug = 'if %errorlevel% neq 0 (\n    winget install x\n    if %errorlevel% neq 0 (\n        exit /b 1\n    )\n)\n'
        self.assertEqual([number for number, _ in _batch_lines_reading_errorlevel_inside_a_block(bug)], [3])


def _write_pe(path, machine):
    """Executavel minimo: so o cabecalho que o instalador le para saber a arquitetura."""
    header = bytearray(0x84)
    header[0:2] = b"MZ"
    header[0x3C:0x40] = (0x80).to_bytes(4, "little")
    header[0x80:0x84] = b"PE\x00\x00"
    with open(path, "wb") as f:
        f.write(bytes(header) + machine.to_bytes(2, "little"))


class TestUnityInstallPreflight(unittest.TestCase):
    def _make_unity_game(self, root, machine=0x8664):
        game_root = os.path.join(root, "SomeUnityGame")
        os.makedirs(os.path.join(game_root, "SomeUnityGame_Data", "Managed"))
        _write_pe(os.path.join(game_root, "SomeUnityGame.exe"), machine)
        _write_pe(os.path.join(game_root, "UnityPlayer.dll"), machine)
        return game_root

    def _destinations(self, plan, game_root):
        return {os.path.relpath(entry.destination, game_root) for entry in plan}

    def test_mono_x64_game_gets_bepinex_and_plugin(self):
        from install_tts_mod import build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_unity_game(tmpdir)
            destinations = self._destinations(build_install_plan(game_root), game_root)

        self.assertIn("winhttp.dll", destinations)
        self.assertIn(os.path.join("BepInEx", "plugins", "KokoroTtsPlugin.dll"), destinations)

    def test_il2cpp_game_is_rejected_with_an_explicit_reason(self):
        from install_tts_mod import UnsupportedUnityGame, build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_unity_game(tmpdir)
            _write_pe(os.path.join(game_root, "GameAssembly.dll"), 0x8664)
            with self.assertRaises(UnsupportedUnityGame) as ctx:
                build_install_plan(game_root)
        self.assertIn("IL2CPP", str(ctx.exception))

    def test_32_bit_game_is_rejected_because_the_bepinex_pack_is_64_bit(self):
        from install_tts_mod import UnsupportedUnityGame, build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_unity_game(tmpdir, machine=0x014C)
            with self.assertRaises(UnsupportedUnityGame) as ctx:
                build_install_plan(game_root)
        self.assertIn("32 bits", str(ctx.exception))

    def test_existing_bepinex_5_is_kept_and_only_the_plugin_is_added(self):
        from install_tts_mod import build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_unity_game(tmpdir)
            core = os.path.join(game_root, "BepInEx", "core")
            os.makedirs(core)
            with open(os.path.join(core, "BepInEx.dll"), "wb") as f:
                f.write(b"user bepinex")
            destinations = self._destinations(build_install_plan(game_root), game_root)

        self.assertNotIn("winhttp.dll", destinations)
        self.assertNotIn(os.path.join("BepInEx", "core", "BepInEx.dll"), destinations)
        self.assertIn(os.path.join("BepInEx", "plugins", "KokoroTtsPlugin.dll"), destinations)

    def test_bepinex_6_is_rejected(self):
        from install_tts_mod import UnsupportedUnityGame, build_install_plan

        with tempfile.TemporaryDirectory() as tmpdir:
            game_root = self._make_unity_game(tmpdir)
            core = os.path.join(game_root, "BepInEx", "core")
            os.makedirs(core)
            with open(os.path.join(core, "BepInEx.Core.dll"), "wb") as f:
                f.write(b"bepinex 6")
            with self.assertRaises(UnsupportedUnityGame) as ctx:
                build_install_plan(game_root)
        self.assertIn("BepInEx 6", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

