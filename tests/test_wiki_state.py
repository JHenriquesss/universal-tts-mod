import os
import re
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")
if RENPY_MOD_DIR not in sys.path:
    sys.path.insert(0, RENPY_MOD_DIR)

OPEN_THREADS_PATH = os.path.join(ROOT_DIR, "wiki", "06-open-threads.md")
PHASES_PATH = os.path.join(ROOT_DIR, "wiki", "03-phases.md")
ARCHITECTURE_PATH = os.path.join(ROOT_DIR, "wiki", "01-architecture.md")
TEST_TREE_PATH = os.path.join(ROOT_DIR, "wiki", "02-test-tree.md")
README_PATH = os.path.join(ROOT_DIR, "README.md")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _discovered_test_count():
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.join(ROOT_DIR, "tests"),
        top_level_dir=ROOT_DIR,
    )
    return suite.countTestCases()


class TestWikiState(unittest.TestCase):
    def test_extractor_hardcoded_path_is_not_open_thread(self):
        open_threads = _read(OPEN_THREADS_PATH)

        self.assertNotIn("hardcoded local path", open_threads)
        self.assertNotIn("hardcoded local game path", open_threads)
        self.assertNotIn("How_I_Became_a_Hero", open_threads)

    def test_phase_9_extractor_cli_is_recorded(self):
        phases = _read(PHASES_PATH)

        self.assertIn("menu-hints-extractor-cli", phases)
        self.assertIn("Extractor CLI", phases)

    def test_phase_19_release_artifact_is_recorded(self):
        phases = _read(PHASES_PATH)
        architecture = _read(ARCHITECTURE_PATH)

        self.assertIn("Current phase: 19", phases)
        self.assertIn("release-artifact-generation", phases)
        self.assertIn("renpy-tts-mod-1.0.0.zip", architecture)
        self.assertIn("TTS-only", architecture)

    def test_wiki_records_the_current_trunk_evidence(self):
        test_tree = _read(TEST_TREE_PATH)
        recorded = re.search(r"Ran (\d+) tests", test_tree)

        self.assertIsNotNone(recorded, "the test tree must record the trunk evidence")
        self.assertEqual(
            int(recorded.group(1)),
            _discovered_test_count(),
            "the test tree must record the current trunk count, otherwise it goes stale silently",
        )

    def test_wiki_records_no_active_carryover(self):
        open_threads = _read(OPEN_THREADS_PATH)

        self.assertIn("No active DV carry-over after Phase 21", open_threads)

    def test_wiki_records_release_stop_decision(self):
        open_threads = _read(OPEN_THREADS_PATH)

        self.assertIn("TTS-only release work is complete", open_threads)
        self.assertIn("No active DV carry-over after Phase 21", open_threads)
        self.assertIn("optional choice overlay remains opt-in", open_threads)

    def test_wiki_records_multi_engine_architecture_and_closed_legacy_overlay_thread(self):
        architecture = _read(ARCHITECTURE_PATH)
        open_threads = _read(OPEN_THREADS_PATH)

        self.assertIn("falcom_mod/falcom_text_hook.py", architecture)
        self.assertIn("falcom_mod/falcom_win32_runtime.py", architecture)
        self.assertNotIn("still contains Ren'Py UI and legacy wrapper functions", open_threads)
        self.assertIn("build_additive_button_caption", open_threads)

    def test_architecture_documents_the_unity_plugin_that_actually_exists(self):
        architecture = _read(ARCHITECTURE_PATH)

        self.assertIn(
            "unity_mod/src/KokoroTtsPlugin.cs",
            architecture,
            "the Unity path is the BepInEx plugin; the old python hook files no longer exist",
        )
        self.assertNotIn(
            "unity_mod/unity_text_hook.py",
            architecture,
            "the architecture page must not document files that were removed from the repository",
        )

    def test_docs_mention_every_engine_the_installer_supports(self):
        from install_tts_mod import SUPPORTED_ENGINES

        readme = _read(README_PATH)
        architecture = _read(ARCHITECTURE_PATH)

        for engine_id, display_name in SUPPORTED_ENGINES.items():
            self.assertIn(
                display_name,
                readme,
                f"the README must document the {engine_id} engine",
            )
            self.assertIn(
                display_name,
                architecture,
                f"the architecture wiki must document the {engine_id} engine",
            )

    def test_docs_document_every_protocol_command(self):
        from tts_protocol import CLIENT_COMMANDS, SERVER_COMMANDS

        readme = _read(README_PATH)
        architecture = _read(ARCHITECTURE_PATH)

        for command in CLIENT_COMMANDS + SERVER_COMMANDS:
            self.assertIn(
                command,
                readme,
                f"the README must document the {command} command",
            )
            self.assertIn(
                command,
                architecture,
                f"the architecture wiki must document the {command} command",
            )


if __name__ == "__main__":
    unittest.main()
