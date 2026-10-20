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

    def test_tracked_files_do_not_contain_placeholder_stubs(self):
        """Stub de LFS ou placeholder nao pode ser versionado como se fosse artefato real.

        Os arquivos de tts_models/ guardavam o conteudo "Entry not found" e
        "Not Found" no lugar dos binarios, sem nenhuma avisao.
        """
        import subprocess

        try:
            result = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git is not available in this environment")

        stub_contents = {
            "Entry not found",
            "Not Found",
            "version https://git-lfs.github.com/spec/v1",
        }
        offenders = []
        for relative in result.stdout.split("\0"):
            if not relative:
                continue
            path = os.path.join(ROOT_DIR, relative)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read(4096).strip()
            except (OSError, UnicodeDecodeError):
                continue
            if content in stub_contents or content.startswith("version https://git-lfs"):
                offenders.append(relative)

        self.assertEqual(
            offenders,
            [],
            "placeholder files must not be tracked: {}".format(offenders),
        )

    def test_tooling_scripts_do_not_carry_a_personal_home_path(self):
        """Os scripts de tools/ sao de uso pontual e nao podem ficar presos a maquina.

        Um caminho de usuario versionado deixa o script inutil para qualquer
        outra pessoa e expõe a estrutura de pastas de quem escreveu ele.
        """
        import re

        personal_path = re.compile(r"[A-Za-z]:\\+Users\\+", re.IGNORECASE)
        offenders = []
        for directory in (os.path.join(ROOT_DIR, "tools"),):
            if not os.path.isdir(directory):
                continue
            for name in sorted(os.listdir(directory)):
                if not name.endswith(".py"):
                    continue
                path = os.path.join(directory, name)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if personal_path.search(content):
                    offenders.append(os.path.join("tools", name))

        self.assertEqual(
            offenders,
            [],
            "tooling scripts must not hardcode a personal home path: {}".format(offenders),
        )

    def test_docs_do_not_claim_removed_runtime_protocols(self):
        readme = read_project_file("README.md")

        for stale_claim in ("Edge-TTS", "CACHE:", "stdin", "stdout", "READY"):
            self.assertNotIn(stale_claim, readme)


if __name__ == "__main__":
    unittest.main()
