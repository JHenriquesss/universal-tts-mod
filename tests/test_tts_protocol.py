import json
import os
import queue
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
if RENPY_MOD_DIR not in sys.path:
    sys.path.insert(0, RENPY_MOD_DIR)

import tts_protocol
from tts_protocol import (
    CLIENT_COMMANDS,
    CMD_HELLO,
    CMD_PLAYBACK_DONE,
    CMD_QUIT,
    CMD_SET_LANG,
    CMD_SET_SPEED,
    CMD_SET_VOICE,
    CMD_STOP,
    PRESERVED_ON_STOP,
    drain_preserving,
)


class TestTtsProtocol(unittest.TestCase):
    def test_stop_preserves_voice_speed_and_lang_configuration(self):
        q = queue.Queue()
        q.put((CMD_SET_VOICE, "am_adam"))
        q.put((CMD_SET_SPEED, 1.5))
        q.put((CMD_SET_LANG, "p"))
        q.put(("SPEAK", "Pending line"))

        preserved = drain_preserving(q)

        self.assertEqual(
            sorted(item[0] for item in preserved),
            sorted([CMD_SET_VOICE, CMD_SET_SPEED, CMD_SET_LANG]),
        )
        self.assertEqual(q.qsize(), 0, "the pending speech must be discarded")

    def test_drain_releases_the_discarded_tasks(self):
        q = queue.Queue()
        q.put(("SPEAK", "one"))
        q.put(("SPEAK", "two"))

        drain_preserving(q)

        self.assertEqual(
            q.unfinished_tasks,
            0,
            "discarded speech must not leak unfinished tasks in the queue",
        )

    def test_preserved_configuration_stays_pending_until_the_worker_runs_it(self):
        q = queue.Queue()
        q.put((CMD_SET_LANG, "p"))
        q.put(("SPEAK", "dropped"))

        preserved = drain_preserving(q)
        for item in preserved:
            q.put(item)

        self.assertEqual(
            q.unfinished_tasks,
            1,
            "the preserved configuration must stay pending for the worker",
        )

    def test_client_commands_cover_the_whole_protocol(self):
        for command in (
            CMD_STOP,
            CMD_SET_SPEED,
            CMD_SET_VOICE,
            CMD_SET_LANG,
            CMD_HELLO,
            CMD_QUIT,
        ):
            self.assertIn(command, CLIENT_COMMANDS)

    def test_preserved_commands_are_a_subset_of_the_client_commands(self):
        for command in PRESERVED_ON_STOP:
            self.assertIn(command, CLIENT_COMMANDS)

    def test_playback_done_is_a_server_to_client_command(self):
        self.assertNotIn(
            CMD_PLAYBACK_DONE,
            CLIENT_COMMANDS,
            "PLAYBACK_DONE is sent by the backend, never requested by the client",
        )

    def test_bounded_log_rotates_to_single_backup_when_limit_exceeded(self):
        self.assertTrue(hasattr(tts_protocol, "append_bounded_log"))
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "tts_server.log")
            for idx in range(12):
                tts_protocol.append_bounded_log(
                    log_path,
                    f"entry-{idx}-" + ("x" * 60),
                    max_bytes=350,
                )

            self.assertTrue(os.path.isfile(log_path))
            self.assertTrue(os.path.isfile(log_path + ".1"))
            self.assertLessEqual(os.path.getsize(log_path), 450)
            with open(log_path, "r", encoding="utf-8") as handle:
                lines = [json.loads(line)["msg"] for line in handle if line.strip()]
            self.assertTrue(lines)
            self.assertIn("entry-11-", lines[-1])

    def test_bounded_log_rejects_invalid_or_negative_env_limits(self):
        self.assertTrue(hasattr(tts_protocol, "append_bounded_log"))
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "tts_server.log")
            for bad_limit in ("-100", "0", "not-a-number"):
                with mock.patch.dict(os.environ, {"TTS_MAX_LOG_BYTES": bad_limit}):
                    tts_protocol.append_bounded_log(log_path, f"msg-{bad_limit}")

            self.assertTrue(os.path.isfile(log_path))
            self.assertFalse(os.path.exists(log_path + ".1"))

    def test_is_pid_alive_handles_live_dead_and_invalid_pids(self):
        self.assertTrue(hasattr(tts_protocol, "is_pid_alive"))
        for invalid in (None, 0, -5, "not_pid"):
            self.assertFalse(tts_protocol.is_pid_alive(invalid))

        sleeper = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self.assertTrue(tts_protocol.is_pid_alive(sleeper.pid))
        finally:
            sleeper.terminate()
            sleeper.wait(timeout=5)
            for stream in (sleeper.stdout, sleeper.stderr):
                if stream is not None:
                    stream.close()

        self.assertFalse(tts_protocol.is_pid_alive(sleeper.pid))


if __name__ == "__main__":
    unittest.main()
