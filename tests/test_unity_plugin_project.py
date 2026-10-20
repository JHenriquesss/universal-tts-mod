import os
import re
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITY_MOD_DIR = os.path.join(ROOT_DIR, "unity_mod")
CSPROJ_PATH = os.path.join(UNITY_MOD_DIR, "src", "KokoroTtsPlugin.csproj")
PLUGIN_DLL_PATH = os.path.join(UNITY_MOD_DIR, "KokoroTtsPlugin.dll")

# Assemblies que existiam em duplicidade na raiz do plugin: as copias do
# BepInEx ficam em bepinex_pack/BepInEx/core e sao as usadas pelo instalador.
DUPLICATED_AT_ROOT = (
    "0Harmony.dll",
    "BepInEx.dll",
    "Mono.Cecil.dll",
    "MonoMod.RuntimeDetour.dll",
    "MonoMod.Utils.dll",
)


class TestUnityPluginProject(unittest.TestCase):
    def _csproj_source(self):
        with open(CSPROJ_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def test_every_referenced_assembly_exists(self):
        hint_paths = re.findall(r"<HintPath>([^<]+)</HintPath>", self._csproj_source())

        self.assertTrue(hint_paths, "the project must reference the BepInEx and UnityEngine assemblies")
        for hint_path in hint_paths:
            resolved = os.path.normpath(
                os.path.join(os.path.dirname(CSPROJ_PATH), hint_path.replace("\\", os.sep))
            )
            self.assertTrue(
                os.path.exists(resolved),
                "referenced assembly is missing: {}".format(resolved),
            )

    def test_duplicate_assemblies_are_not_kept_at_the_plugin_root(self):
        for filename in DUPLICATED_AT_ROOT:
            self.assertFalse(
                os.path.exists(os.path.join(UNITY_MOD_DIR, filename)),
                "{} is duplicated in bepinex_pack and must not live at the plugin root".format(filename),
            )

    def test_the_compiled_plugin_is_committed(self):
        self.assertTrue(
            os.path.exists(PLUGIN_DLL_PATH),
            "the compiled plugin must be committed, otherwise the installer has nothing to ship",
        )

    def test_the_project_builds_reproducibly(self):
        source = self._csproj_source()

        self.assertIn(
            "<Deterministic>true</Deterministic>",
            source,
            "the build must be deterministic for the CI drift check to hold",
        )
        self.assertIn(
            "<IncludeSourceRevisionInInformationalVersion>false</IncludeSourceRevisionInInformationalVersion>",
            source,
            "the commit hash must not be embedded in the binary, or every commit would change it",
        )


if __name__ == "__main__":
    unittest.main()
