import os
import re
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(ROOT_DIR, "README.md")


class TestReadmeDeployDocs(unittest.TestCase):
    def setUp(self):
        with open(README_PATH, "r", encoding="utf-8") as f:
            self.readme = f.read()
        self.lower = self.readme.lower()

    def test_required_deploy_file_checklist_is_precise(self):
        for filename in ("tts_mod.rpy", "tts_server.py", "tts_engines.py", "text_cleaner.py"):
            self.assertIn(f"`{filename}`", self.readme)

        self.assertIn("Required files", self.readme)

    def test_optional_choice_overlay_files_are_documented(self):
        for filename in (
            "choice_hints_core.py",
            "zzz_mod_choice_consequences.rpy",
            "zzz_mod_choice_hints_generated.rpy",
        ):
            self.assertIn(f"`{filename}`", self.readme)

        self.assertIn("Optional choice overlay files", self.readme)

    def test_voice_configuration_and_protocol_are_documented(self):
        self.assertIn('TTS_VOICE = "af_heart"', self.readme)
        self.assertIn("`SET_VOICE:<voice>`", self.readme)

    def test_docs_do_not_reintroduce_stale_runtime_claims(self):
        for stale in ("edge-tts", "cache:", "ready|", "pipe protocol"):
            self.assertNotIn(stale, self.lower)

        self.assertNotRegex(self.lower, r"\bstdin\b.*\bstdout\b|\bstdout\b.*\bstdin\b")

    def test_docs_do_not_tell_users_to_copy_generated_or_test_artifacts(self):
        install_section = self.readme.split("## Installation", 1)[-1].split("## TTS-Only Install And Run", 1)[0]

        forbidden = ("__pycache__", ".pyc", ".log", "tests/", "tts_ready.txt")
        for item in forbidden:
            self.assertNotIn(item, install_section)

        self.assertNotRegex(install_section, re.compile(r"copy\s+all\s+files", re.I))

    def test_extractor_cli_usage_is_documented(self):
        self.assertIn("## Choice Hint Extraction", self.readme)
        self.assertIn("python extract_menu_hints_generic.py --game-path", self.readme)
        self.assertIn("python extract_menu_hints_generic.py --archive", self.readme)
        self.assertIn("--output", self.readme)
        self.assertIn("zzz_mod_choice_hints_generated.rpy", self.readme)

    def test_extractor_docs_do_not_reference_local_sample_paths(self):
        self.assertNotIn("How_I_Became_a_Hero", self.readme)
        self.assertNotIn("C:\\Users\\joseh", self.readme)

    def test_backend_smoke_check_usage_is_documented(self):
        self.assertIn("## Backend Smoke Check", self.readme)
        self.assertIn("python smoke_check.py", self.readme)
        self.assertIn("TTS_ENGINE=mock", self.readme)
        self.assertIn("does not require", self.lower)
        self.assertIn("kokoro", self.lower)

    def test_tts_only_install_run_workflow_is_documented(self):
        self.assertIn("## TTS-Only Install And Run", self.readme)
        self.assertIn("INSTALAR_TTS_MOD.bat", self.readme)
        self.assertIn("python install_tts_mod.py --game-folder", self.readme)
        self.assertIn("python smoke_check.py", self.readme)
        self.assertIn("run_backend.bat", self.readme)
        self.assertIn("launch the game", self.lower)
        self.assertIn("press `v`", self.lower)
        self.assertIn("game/tts_server.log", self.readme)

    def test_tts_only_workflow_keeps_optional_overlay_separate(self):
        workflow = self.readme.split("## TTS-Only Install And Run", 1)[-1].split("## Choice Hint Extraction", 1)[0]

        self.assertNotIn("choice_hints_core.py", workflow)
        self.assertNotIn("zzz_mod_choice_consequences.rpy", workflow)
        self.assertNotIn("zzz_mod_choice_hints_generated.rpy", workflow)
        self.assertNotRegex(workflow, re.compile(r"copy\s+all\s+files", re.I))

    def test_tts_only_workflow_does_not_reference_local_paths_or_artifacts(self):
        workflow = self.readme.split("## TTS-Only Install And Run", 1)[-1].split("## Choice Hint Extraction", 1)[0]

        for forbidden in ("C:\\Users\\joseh", "GrandmasHouse-0.68-pc", "__pycache__", ".pyc", "tts_ready.txt", "tests/"):
            self.assertNotIn(forbidden, workflow)
        self.assertNotRegex(workflow, re.compile(r"copy\s+.*\.log", re.I))

    def test_release_hygiene_check_usage_is_documented(self):
        self.assertIn("## Release Hygiene", self.readme)
        self.assertIn("python release_manifest.py --check", self.readme)

    def test_release_hygiene_docs_do_not_reference_local_paths_or_artifacts(self):
        section = self.readme.split("## Release Hygiene", 1)[-1].split("## Tests", 1)[0]

        for forbidden in ("C:\\Users\\joseh", "GrandmasHouse-0.68-pc", "__pycache__", ".pyc", "tts_ready.txt", "tests/"):
            self.assertNotIn(forbidden, section)
        self.assertNotIn("choice_hints_core.py", section)
        self.assertNotIn("zzz_mod_choice_consequences.rpy", section)

    def test_release_archive_usage_is_documented(self):
        self.assertIn("python release_manifest.py --archive", self.readme)
        self.assertIn("tts_mod_release.zip", self.readme)

    def test_versioned_release_archive_usage_is_documented(self):
        self.assertIn("python release_manifest.py --archive", self.readme)
        self.assertIn("versioned", self.lower)
        self.assertIn("renpy-tts-mod", self.readme)

    def test_final_release_checklist_is_documented(self):
        self.assertIn("## Final Release Checklist", self.readme)
        checklist = self.readme.split("## Final Release Checklist", 1)[-1].split("## Tests", 1)[0]

        self.assertIn("python -m unittest discover -s tests", checklist)
        self.assertIn("python smoke_check.py", checklist)
        self.assertIn("python release_manifest.py --check", checklist)
        self.assertIn("python release_manifest.py --archive", checklist)
        self.assertIn("exactly matches the release manifest", checklist)

    def test_final_release_checklist_safety_wording(self):
        checklist = self.readme.split("## Final Release Checklist", 1)[-1].split("## Tests", 1)[0]

        for required in ("TTS-only", "generated", "runtime", "test artifacts"):
            self.assertIn(required, checklist)
        for forbidden in ("C:\\Users\\joseh", "GrandmasHouse-0.68-pc", "choice_hints_core.py"):
            self.assertNotIn(forbidden, checklist)
        self.assertNotRegex(checklist, re.compile(r"real\s+kokoro\s+audio\s+required", re.I))

    def test_release_stop_decision_is_documented(self):
        self.assertIn("## Release Status", self.readme)
        section = self.readme.split("## Release Status", 1)[-1].split("## Tests", 1)[0]

        self.assertIn("TTS-only release work is complete", section)
        self.assertIn("renpy-tts-mod-1.0.0.zip", section)
        self.assertIn("optional choice overlay remains opt-in", section)
        self.assertNotIn("choice_hints_core.py", section)
        self.assertNotIn("C:\\Users\\joseh", section)


if __name__ == "__main__":
    unittest.main()
