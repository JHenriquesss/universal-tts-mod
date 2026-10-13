import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALCOM_MOD_DIR = os.path.join(ROOT_DIR, "falcom_mod")
if FALCOM_MOD_DIR not in sys.path:
    sys.path.insert(0, FALCOM_MOD_DIR)


class TestFalcomLauncher(unittest.TestCase):
    def test_launcher_starts_backend_hook_and_game_with_owned_processes(self):
        from falcom_launcher import run_launcher

        backend = MagicMock()
        game = MagicMock()
        hook = MagicMock()
        backend.poll.return_value = None
        hook.poll.return_value = None
        game.wait.return_value = 0
        game.pid = 4321

        with tempfile.TemporaryDirectory() as game_dir:
            os.makedirs(os.path.join(game_dir, "tts_textractor"))
            textractor_exe = os.path.join(game_dir, "tts_textractor", "TextractorCLI.exe")
            with open(textractor_exe, "wb") as stream:
                stream.write(b"MZ")
            with patch(
                "falcom_launcher.build_dialogue_hook_code",
                return_value="HSFN932#4@12F4E0:ed6_win2_DX9.exe",
            ) as build_hook, patch(
                "falcom_launcher.subprocess.Popen",
                side_effect=[backend, game, hook],
            ) as popen:
                result = run_launcher(
                    game_dir=game_dir,
                    game_executable="ed6_win2_DX9.exe",
                    python_executable=r"C:\Python\python.exe",
                )

        self.assertEqual(result, 0)
        self.assertEqual(popen.call_count, 3)
        backend_command = popen.call_args_list[0].args[0]
        game_command = popen.call_args_list[1].args[0]
        hook_command = popen.call_args_list[2].args[0]
        self.assertEqual(backend_command[1], "-u")
        self.assertTrue(game_command[0].endswith("ed6_win2_DX9.exe"))
        self.assertEqual(hook_command[1], "-u")
        self.assertIn("--textractor-cli", hook_command)
        self.assertIn(textractor_exe, hook_command)
        self.assertIn("--pid", hook_command)
        self.assertIn("4321", hook_command)
        self.assertIn("--hook-code", hook_command)
        self.assertNotIn("--clipboard-only", hook_command)
        build_hook.assert_called_once()
        backend.terminate.assert_called_once_with()
        hook.terminate.assert_called_once_with()

    def test_batch_delegates_to_supervisor_without_global_python_taskkill(self):
        batch_path = os.path.join(FALCOM_MOD_DIR, "JOGAR_COM_TTS.bat")
        with open(batch_path, "r", encoding="utf-8") as batch_file:
            content = batch_file.read().lower()

        self.assertIn("falcom_launcher.py", content)
        self.assertIn(r"%localappdata%\programs\python\python312\python.exe", content)
        self.assertNotIn("taskkill /f /im python.exe", content)

    def test_batch_shows_hotkey_help_and_forwards_arguments(self):
        batch_path = os.path.join(FALCOM_MOD_DIR, "JOGAR_COM_TTS.bat")
        with open(batch_path, "r", encoding="utf-8") as batch_file:
            content = batch_file.read()

        self.assertIn("F1", content)
        self.assertIn("F2", content)
        self.assertIn("%*", content)

    def test_check_port_in_use_detects_bound_port(self):
        import socket
        from falcom_launcher import check_port_in_use

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            self.assertTrue(check_port_in_use(port))

    def test_get_configured_port_from_config_file(self):
        import json
        from falcom_launcher import get_configured_port

        with tempfile.TemporaryDirectory() as game_dir:
            cfg_path = os.path.join(game_dir, "tts_config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"port": 5055, "speed": 1.1}, f)
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TTS_PORT", None)
                self.assertEqual(get_configured_port(game_dir), 5055)

    def test_get_configured_port_from_env_overrides_default(self):
        from falcom_launcher import get_configured_port

        with tempfile.TemporaryDirectory() as game_dir:
            with patch.dict(os.environ, {"TTS_PORT": "5060"}):
                self.assertEqual(get_configured_port(game_dir), 5060)

    def test_get_configured_port_defaults_to_5050(self):
        from falcom_launcher import get_configured_port

        with tempfile.TemporaryDirectory() as game_dir:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TTS_PORT", None)
                self.assertEqual(get_configured_port(game_dir), 5050)

    def test_launcher_propagates_custom_port_to_backend_and_hook(self):
        from falcom_launcher import run_launcher

        backend = MagicMock()
        game = MagicMock()
        hook = MagicMock()
        backend.poll.return_value = None
        hook.poll.return_value = None
        game.wait.return_value = 0
        game.pid = 4321

        with tempfile.TemporaryDirectory() as game_dir:
            os.makedirs(os.path.join(game_dir, "tts_textractor"))
            textractor_exe = os.path.join(game_dir, "tts_textractor", "TextractorCLI.exe")
            with open(textractor_exe, "wb") as stream:
                stream.write(b"MZ")
            with patch(
                "falcom_launcher.build_dialogue_hook_code",
                return_value="HSFN932#4@12F4E0:ed6_win2_DX9.exe",
            ), patch(
                "falcom_launcher.subprocess.Popen",
                side_effect=[backend, game, hook],
            ) as popen, patch(
                "falcom_launcher.check_port_in_use",
                return_value=False,
            ) as mock_check_port:
                result = run_launcher(
                    game_dir=game_dir,
                    game_executable="ed6_win2_DX9.exe",
                    python_executable=r"C:\Python\python.exe",
                    port=5055,
                )

        self.assertEqual(result, 0)
        mock_check_port.assert_called_once_with(5055)
        backend_kwargs = popen.call_args_list[0].kwargs
        hook_command = popen.call_args_list[2].args[0]
        self.assertEqual(backend_kwargs.get("env", {}).get("TTS_PORT"), "5055")
        self.assertIn("--port", hook_command)
        self.assertIn("5055", hook_command)

    def test_launcher_arg_parser_supports_port(self):
        from falcom_launcher import build_arg_parser

        args = build_arg_parser().parse_args(["--port", "5055"])
        self.assertEqual(args.port, 5055)


if __name__ == "__main__":
    unittest.main()

