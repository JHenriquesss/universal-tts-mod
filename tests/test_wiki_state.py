import os
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPEN_THREADS_PATH = os.path.join(ROOT_DIR, "wiki", "06-open-threads.md")
PHASES_PATH = os.path.join(ROOT_DIR, "wiki", "03-phases.md")
ARCHITECTURE_PATH = os.path.join(ROOT_DIR, "wiki", "01-architecture.md")
TEST_TREE_PATH = os.path.join(ROOT_DIR, "wiki", "02-test-tree.md")


class TestWikiState(unittest.TestCase):
    def test_extractor_hardcoded_path_is_not_open_thread(self):
        with open(OPEN_THREADS_PATH, "r", encoding="utf-8") as f:
            open_threads = f.read()

        self.assertNotIn("hardcoded local path", open_threads)
        self.assertNotIn("hardcoded local game path", open_threads)
        self.assertNotIn("How_I_Became_a_Hero", open_threads)

    def test_phase_9_extractor_cli_is_recorded(self):
        with open(PHASES_PATH, "r", encoding="utf-8") as f:
            phases = f.read()

        self.assertIn("menu-hints-extractor-cli", phases)
        self.assertIn("Extractor CLI", phases)

    def test_phase_19_release_artifact_is_recorded(self):
        with open(PHASES_PATH, "r", encoding="utf-8") as f:
            phases = f.read()
        with open(ARCHITECTURE_PATH, "r", encoding="utf-8") as f:
            architecture = f.read()

        self.assertIn("Current phase: 19", phases)
        self.assertIn("release-artifact-generation", phases)
        self.assertIn("renpy-tts-mod-1.0.0.zip", architecture)
        self.assertIn("TTS-only", architecture)

    def test_wiki_records_latest_trunk_and_no_active_carryover(self):
        with open(TEST_TREE_PATH, "r", encoding="utf-8") as f:
            test_tree = f.read()
        with open(OPEN_THREADS_PATH, "r", encoding="utf-8") as f:
            open_threads = f.read()

        self.assertIn("Ran 88 tests", test_tree)
        self.assertIn("No active DV carry-over after Phase 21", open_threads)

    def test_wiki_records_release_stop_decision(self):
        with open(OPEN_THREADS_PATH, "r", encoding="utf-8") as f:
            open_threads = f.read()

        self.assertIn("TTS-only release work is complete", open_threads)
        self.assertIn("No active DV carry-over after Phase 21", open_threads)
        self.assertIn("optional choice overlay remains opt-in", open_threads)


if __name__ == "__main__":
    unittest.main()
