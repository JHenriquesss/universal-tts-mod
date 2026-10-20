import ast
import os
import re
import sys
import textwrap
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

MOD_PATH = os.path.join(ROOT_DIR, "renpy_mod", "tts_mod.rpy")

# Nomes que o jogo e a screen do mod chamam. Eles vivem no store do Ren'Py,
# entao o cliente nao pode deixar de defini-los.
PUBLIC_CLIENT_API = (
    "tts_state",
    "tts_connect",
    "tts_kill",
    "tts_notify",
    "tts_status_message",
    "tts_speak",
    "tts_speak_once",
    "tts_start_callback",
    "tts_increase_speed",
    "tts_decrease_speed",
    "tts_toggle_auto",
    "tts_toggle_audio",
)


def _read_mod_source():
    with open(MOD_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def _python_blocks(source):
    """Os blocos python do .rpy, sem o codigo de screen (sintaxe do Ren'Py)."""
    blocks = []
    current = None
    kind = None
    for line in source.splitlines():
        stripped = line.strip()
        header = re.match(r"^(init|screen|label)\b.*:\s*$", stripped)
        if header:
            if current:
                blocks.append((kind, current))
            current = []
            kind = header.group(1)
            continue
        if current is None:
            continue
        if stripped and not line.startswith(("    ", "\t")):
            blocks.append((kind, current))
            current = []
            kind = None
            continue
        current.append(line)
    if current:
        blocks.append((kind, current))
    return [
        textwrap.dedent("\n".join(block))
        for kind, block in blocks
        if kind == "init" and block
    ]


def _defined_names(source):
    names = set()
    for body in _python_blocks(source):
        tree = ast.parse(body)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    names.add(alias.asname or alias.name)
    return names


def _imported_modules(source):
    modules = set()
    for body in _python_blocks(source):
        for node in ast.walk(ast.parse(body)):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".")[0])
    return modules


class TestTTSClientLayout(unittest.TestCase):
    def test_the_python_blocks_of_the_mod_compile(self):
        """Um erro de sintaxe no .rpy so apareceria dentro do jogo."""
        blocks = _python_blocks(_read_mod_source())

        self.assertTrue(blocks, "the mod must keep its python blocks")
        for block in blocks:
            compile(block, "tts_mod.rpy", "exec")

    def test_the_public_client_api_stays_available(self):
        """O jogo e a screen chamam esses nomes: eles nao podem sumir."""
        names = _defined_names(_read_mod_source())

        for name in PUBLIC_CLIENT_API:
            self.assertIn(name, names)

    def test_every_module_the_client_imports_ships_with_the_mod(self):
        """Modulo importado e modulo entregue: o jogo instala os dois."""
        from install_tts_mod import REQUIRED_GAME_FILES

        modules = _imported_modules(_read_mod_source())
        client_modules = {
            name for name in modules if name.startswith("tts_client_")
        }

        self.assertTrue(client_modules, "the client is expected to use modules")
        for name in client_modules:
            self.assertIn(
                name + ".py",
                REQUIRED_GAME_FILES,
                "{} is imported by the mod and must be installed with it".format(name),
            )
            self.assertTrue(
                os.path.isfile(os.path.join(ROOT_DIR, "renpy_mod", name + ".py")),
                "{} must exist in renpy_mod/".format(name),
            )


if __name__ == "__main__":
    unittest.main()
