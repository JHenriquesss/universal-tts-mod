"""Diagnostico da estrutura do AST: onde os menus vivem e como os rotulos se ligam."""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rpyc_ast  # noqa: E402
import rpyc_extract  # noqa: E402


def main():
    game_root = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None

    rpyc_extract.bootstrap_renpy(game_root)
    ast = rpyc_extract.ast_module()

    files = []
    for root_dir, _dirs, names in os.walk(os.path.join(game_root, "game")):
        for name in sorted(names):
            if name.endswith(".rpyc") and "screen" not in name.lower():
                files.append(os.path.join(root_dir, name))
    files.sort()

    if target:
        files = [f for f in files if target.lower() in f.lower()]

    for path in files:
        stmts = rpyc_ast.load_ast(path)
        seen = set()
        nodes = []
        for stmt in stmts:
            nodes.extend(rpyc_extract.collect_nodes(stmt, seen))

        kinds = collections.Counter(type(n).__name__ for n in nodes)
        menus = [n for n in nodes if isinstance(n, ast.Menu)]
        if not menus:
            continue

        print("=== {} ===".format(os.path.relpath(path, game_root)))
        print("  nós: {} | {}".format(
            len(nodes),
            ", ".join("{}={}".format(k, v) for k, v in kinds.most_common(6))))

        # Top-level: o que existe logo abaixo da raiz do arquivo.
        print("  raiz: {}".format(
            ", ".join("{}@{}".format(type(s).__name__, getattr(s, "linenumber", "")) for s in stmts)))

        labels = [n for n in nodes if type(n).__name__ == "Label"]
        print("  labels: {}".format([n.name for n in labels][:6]))

        for menu in menus[:2]:
            print("  menu @{}:{}".format(os.path.basename(menu.filename), menu.linenumber))
            print("    has_caption={}".format(menu.has_caption))
            for caption, condition, block in menu.items[:2]:
                print("    cap={!r} cond={!r} block={}".format(
                    caption, condition, len(block or [])))
                for child in (block or [])[:5]:
                    print("       -> {} {}:{}".format(
                        type(child).__name__,
                        os.path.basename(str(getattr(child, "filename", ""))),
                        getattr(child, "linenumber", "")))
        print()


if __name__ == "__main__":
    main()
