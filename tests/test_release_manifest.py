import os
import sys
import tempfile
import unittest
import zipfile


sys.dont_write_bytecode = True


class TestReleaseManifest(unittest.TestCase):
    def test_tts_only_manifest_lists_required_sources_and_destinations(self):
        from release_manifest import build_release_manifest

        entries = build_release_manifest()
        destinations = {entry.destination for entry in entries}
        sources = {entry.source for entry in entries}

        for filename in ("tts_mod.rpy", "tts_server.py", "tts_engines.py", "text_cleaner.py"):
            self.assertIn(os.path.join("game", filename), destinations)
            self.assertIn(os.path.join("renpy_mod", filename), sources)
        self.assertIn("run_backend.bat", destinations)
        self.assertIn(os.path.join("renpy_mod", "run_backend.bat"), sources)

    def test_manifest_sources_exist(self):
        from release_manifest import build_release_manifest, validate_release_manifest

        result = validate_release_manifest(build_release_manifest())

        self.assertTrue(result.ok, result.message)

    def test_manifest_excludes_optional_overlay_and_generated_artifacts(self):
        from release_manifest import build_release_manifest

        entries = build_release_manifest()
        names = {os.path.basename(entry.source) for entry in entries} | {os.path.basename(entry.destination) for entry in entries}

        for forbidden in (
            "choice_hints_core.py",
            "zzz_mod_choice_consequences.rpy",
            "zzz_mod_choice_hints_generated.rpy",
            "tts_server.log",
            "tts_ready.txt",
            "__pycache__",
            "tests",
        ):
            self.assertNotIn(forbidden, names)
        self.assertFalse(any(name.endswith(".pyc") for name in names))

    def test_manifest_matches_installer_tts_only_filenames(self):
        from install_tts_mod import REQUIRED_GAME_FILES, ROOT_HELPER_FILES
        from release_manifest import build_release_manifest

        expected = {os.path.join("game", filename) for filename in REQUIRED_GAME_FILES}
        expected.update(ROOT_HELPER_FILES)

        self.assertEqual(expected, {entry.destination for entry in build_release_manifest()})

    def test_build_release_archive_contains_exact_manifest_destinations(self):
        from release_manifest import build_release_archive, build_release_manifest

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "tts_mod_release.zip")

            result = build_release_archive(output_path)

            self.assertEqual(output_path, result.archive_path)
            self.assertTrue(os.path.exists(output_path))
            with zipfile.ZipFile(output_path) as archive:
                names = set(archive.namelist())
            self.assertEqual({entry.destination.replace(os.sep, "/") for entry in build_release_manifest()}, names)

    def test_release_archive_excludes_optional_and_generated_artifacts(self):
        from release_manifest import build_release_archive

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "tts_mod_release.zip")
            build_release_archive(output_path)

            with zipfile.ZipFile(output_path) as archive:
                names = archive.namelist()

        forbidden = (
            "choice_hints_core.py",
            "zzz_mod_choice_consequences.rpy",
            "zzz_mod_choice_hints_generated.rpy",
            "tts_server.log",
            "tts_ready.txt",
            "__pycache__",
            "tests/",
        )
        for name in names:
            self.assertFalse(name.endswith(".pyc"), name)
            for item in forbidden:
                self.assertNotIn(item, name)

    def test_build_release_archive_rejects_missing_output_parent(self):
        from release_manifest import build_release_archive

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "missing", "tts_mod_release.zip")

            with self.assertRaises(ValueError):
                build_release_archive(output_path)

    def test_release_metadata_exposes_package_identity_without_runtime_config(self):
        from release_manifest import PACKAGE_NAME, RELEASE_VERSION

        self.assertEqual("renpy-tts-mod", PACKAGE_NAME)
        self.assertRegex(RELEASE_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertNotIn("TTS_PORT", RELEASE_VERSION)
        self.assertNotIn("TTS_VOICE", RELEASE_VERSION)
        self.assertNotIn("TTS_ENGINE", RELEASE_VERSION)

    def test_default_archive_path_includes_package_and_version(self):
        from release_manifest import PACKAGE_NAME, RELEASE_VERSION, default_archive_path

        with tempfile.TemporaryDirectory() as tmpdir:
            path = default_archive_path(tmpdir)

            self.assertEqual(os.path.join(tmpdir, f"{PACKAGE_NAME}-{RELEASE_VERSION}.zip"), path)
            self.assertNotIn("C:\\Users\\joseh", path)

    def test_build_release_archive_uses_default_versioned_name_when_output_missing(self):
        from release_manifest import PACKAGE_NAME, RELEASE_VERSION, build_release_archive, build_release_manifest

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = build_release_archive()
            finally:
                os.chdir(old_cwd)

            self.assertEqual(os.path.join(tmpdir, f"{PACKAGE_NAME}-{RELEASE_VERSION}.zip"), result.archive_path)
            with zipfile.ZipFile(result.archive_path) as archive:
                names = set(archive.namelist())
            self.assertEqual({entry.destination.replace(os.sep, "/") for entry in build_release_manifest()}, names)


if __name__ == "__main__":
    unittest.main()
