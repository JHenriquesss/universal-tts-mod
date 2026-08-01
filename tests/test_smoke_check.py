import os
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_SCRIPT = os.path.join(ROOT_DIR, "renpy_mod", "tts_server.py")


class TestBackendSmokeCheck(unittest.TestCase):
    def test_smoke_check_starts_mock_backend_sends_command_and_quits(self):
        from smoke_check import run_smoke_check

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_smoke_check(server_script=SERVER_SCRIPT, log_dir=tmpdir, timeout=10)

            self.assertTrue(result.ok, result.message)
            self.assertIn("engine=mock", "\n".join(result.log_messages))
            self.assertIn("command=SET_SPEED", "\n".join(result.log_messages))
            self.assertIn("command=QUIT", "\n".join(result.log_messages))
            self.assertIsNotNone(result.port)
            self.assertEqual(0, result.returncode)

    def test_smoke_check_timeout_kills_child_process_and_reports_error(self):
        from smoke_check import run_smoke_check

        with tempfile.TemporaryDirectory() as tmpdir:
            script = os.path.join(tmpdir, "hang_server.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write("import time\ntime.sleep(60)\n")

            result = run_smoke_check(server_script=script, log_dir=tmpdir, timeout=0.5)

            self.assertFalse(result.ok)
            self.assertIn("timeout", result.message.lower())
            self.assertIsNotNone(result.returncode)


if __name__ == "__main__":
    unittest.main()
