import os
import queue
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
if RENPY_MOD_DIR not in sys.path:
    sys.path.insert(0, RENPY_MOD_DIR)

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


if __name__ == "__main__":
    unittest.main()
