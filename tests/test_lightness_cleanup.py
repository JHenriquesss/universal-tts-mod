import os
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENPY_MOD_DIR = os.path.join(ROOT_DIR, "renpy_mod")


def read_project_file(*parts):
    with open(os.path.join(ROOT_DIR, *parts), "r", encoding="utf-8") as f:
        return f.read()


class TestKokoroOnlyLightnessCleanup(unittest.TestCase):
    def test_main_dependencies_do_not_install_unsupported_engines(self):
        requirements = read_project_file("requirements.txt").lower()
        installer = read_project_file("instalar.bat").lower()

        self.assertNotIn("edge-tts", requirements)
        self.assertNotIn("edge-tts", installer)
        self.assertNotIn("sherpa", requirements)
        self.assertNotIn("sherpa", installer)
        self.assertNotIn("aiohttp", requirements, "aiohttp was only needed by the removed Edge path")

    def test_runtime_engine_module_has_no_dead_engine_classes(self):
        source = read_project_file("renpy_mod", "tts_engines.py")

        self.assertNotIn("class EdgeTTSEngine", source)
        self.assertNotIn("class SherpaOnnxEngine", source)
        self.assertIn("class KokoroEngine", source)
        self.assertIn("class MockEngine", source)

    def test_mock_engine_is_test_only_by_environment_switch(self):
        server = read_project_file("renpy_mod", "tts_server.py")

        self.assertIn('os.environ.get("TTS_ENGINE", "kokoro")', server)
        self.assertIn('engine_name == "mock"', server)
        self.assertIn("return KokoroEngine", server)

    def test_mock_engine_does_not_probe_audio_devices(self):
        source = read_project_file("renpy_mod", "tts_engines.py")
        mock_class = source.split("class MockEngine", 1)[-1]

        self.assertIn("def __init__(self):", mock_class)
        self.assertIn("self._default_device_id = -1", mock_class)
        self.assertNotIn("super().__init__", mock_class)
        self.assertNotIn("sounddevice", mock_class)

    def test_deployable_mod_folder_has_no_generated_artifacts(self):
        forbidden_names = {"__pycache__", "tts_server.log", "tts_ready.txt"}
        found = []
        for current_dir, dirnames, filenames in os.walk(RENPY_MOD_DIR):
            for dirname in dirnames:
                if dirname in forbidden_names:
                    found.append(os.path.relpath(os.path.join(current_dir, dirname), ROOT_DIR))
            for filename in filenames:
                if filename in forbidden_names or filename.endswith(".pyc"):
                    found.append(os.path.relpath(os.path.join(current_dir, filename), ROOT_DIR))

        self.assertEqual([], sorted(found))

    def test_docs_do_not_claim_removed_runtime_protocols(self):
        readme = read_project_file("README.md")

        for stale_claim in ("Edge-TTS", "CACHE:", "stdin", "stdout", "READY"):
            self.assertNotIn(stale_claim, readme)


if __name__ == "__main__":
    unittest.main()
