"""
Valida os .rpy instalados no jogo com o parser real do Ren'Py do proprio jogo.

Um erro de sintaxe em um .rpy quebra o jogo no boot, entao este passo
confirma que o mod compila na versao do Ren'Py que o jogo usa.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rpyc_ast import bootstrap_renpy  # noqa: E402


def use_real_style_module(game_root):
    """O registro de propriedades de estilo vem do `renpy.style` real."""
    import importlib
    import types

    import renpy
    try:
        module = importlib.import_module("renpy.style")
    except Exception:
        return False
    renpy.style = module
    sys.modules["renpy.style"] = module
    return hasattr(module, "prefixed_all_properties")


def main():
    game_root = sys.argv[1]
    bootstrap_renpy(game_root)

    # O parser usa a config do jogo para resolver caminhos.
    import renpy
    renpy.config.alternate_unelide_path = None
    renpy.config.basedir = game_root
    renpy.config.gamedir = os.path.join(game_root, "game")
    renpy.config.renpy_base = os.path.join(game_root, "renpy")
    renpy.config.name = "CampusConfidential"
    renpy.bytecode_version = 1
    renpy.script_version = 5003000
    print("registro de estilo real:", use_real_style_module(game_root))

    import renpy.parser  # noqa: E402

    targets = []
    game_dir = os.path.join(game_root, "game")
    for name in sorted(os.listdir(game_dir)):
        if name.endswith(".rpy"):
            targets.append(os.path.join(game_dir, name))

    failures = 0
    for path in targets:
        name = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                filedata = handle.read()
            renpy.parser.parse_errors = []
            renpy.parser.deferred_parse_errors = collections.defaultdict(list)
            stmts = renpy.parser.parse(path, filedata=filedata)
            errors = list(renpy.parser.parse_errors)
            for values in renpy.parser.deferred_parse_errors.values():
                errors.extend(values)
            if errors:
                failures += 1
                print("  FAIL {:<42} {}".format(name, "; ".join(str(e) for e in errors)[:160]))
            else:
                count = len(stmts) if stmts else 0
                print("  OK   {:<42} {} nos".format(name, count))
        except Exception as exc:
            failures += 1
            print("  FAIL {:<42} {}".format(name, exc))
            if os.environ.get("TTS_RPY_TRACE"):
                import traceback
                traceback.print_exc()

    print("arquivos .rpy verificados: {} | falhas: {}".format(len(targets), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
