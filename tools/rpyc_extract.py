"""
Extrai personagens, falas e menus do AST compilado (.rpyc) de um jogo Ren'Py 8.

Jogos Ren'Py 8 normalmente so distribuiem .rpyc compilado, entao os extratores
baseados em texto (.rpy / .rpa) nao funcionam. Aqui o AST e lido direto do
slot 2 do .rpyc usando o proprio runtime do jogo, o que devolve:

- `characters`: variavel do script -> nome de exibicao do personagem.
- `speakers`: quem fala e com que frequencia.
- `menus`: rotulo, legenda da escolha e efeitos da branch.

O script roda com o Python embarcado no jogo (Python 3.9 do Ren'Py 8).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rpyc_ast import bootstrap_renpy, load_ast  # noqa: E402


def ast_module():
    """`renpy.ast` so existe depois do bootstrap do pacote falso."""
    return sys.modules["renpy.ast"]


EFFECT_PATTERNS = [
    re.compile(r"\$\s*([a-zA-Z0-9_]+\s*(?:\+=|-=|=)\s*[a-zA-Z0-9_]+[\"'\.]+)"),
    re.compile(r"([a-zA-Z0-9_]+\.(?:append|remove|add)\([^\)]*\))"),
    re.compile(r"(route_[a-zA-Z0-9_]+\s*=\s*(?:True|False))"),
]

# `nome = Character("Nome de exibicao", ...)`
CHARACTER_ASSIGN_RE = re.compile(
    r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:renpy\.character\.)?Character\s*\("
    r"\s*(?:[uUbBrR]?)(?P<q>[\"'])(?P<name>(?:\\.|(?!(?P=q)).)*)(?P=q)",
    re.S,
)

# Em um `define`, o fonte e apenas a expressao: `Character("Nome", ...)`.
CHARACTER_EXPR_RE = re.compile(
    r"(?:renpy\.character\.)?Character\s*\("
    r"\s*(?:[uUbBrR]?)(?P<q>[\"'])(?P<name>(?:\\.|(?!(?P=q)).)*)(?P=q)",
    re.S,
)


def is_control_expression(effect):
    return (
        effect.startswith("if ")
        or effect.startswith("elif ")
        or "==" in effect
        or ">=" in effect
        or "<=" in effect
        or "!=" in effect
    )


def extract_effects(sources, jumps):
    """Monta os efeitos de uma branch a partir das linhas python e dos jumps."""
    effects = []
    text_block = "\n".join(sources)

    for pattern in EFFECT_PATTERNS:
        for match in pattern.finditer(text_block):
            effect = match.group(1).replace("$", "").strip()
            if is_control_expression(effect):
                continue
            if effect not in effects:
                effects.append(effect)

    if not effects:
        for jump in jumps:
            effect = "Jump -> {}".format(jump)
            if effect not in effects:
                effects.append(effect)

    return effects


def collect_nodes(node, seen=None):
    """
    Todos os nos descendentes de `node`, em ordem de percurso.

    O AST do Ren'Py e um DAG, nao uma arvore: os mesmos nos sao
    compartilhados entre varios pais. Sem o conjunto de visitados a
    travessia explode exponencialmente.
    """
    if seen is None:
        seen = set()

    found = []
    stack = list(node) if isinstance(node, (list, tuple)) else [node]
    while stack:
        current = stack.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        found.append(current)
        try:
            children = []
            current.get_children(children.append)
        except Exception:
            children = []
        for child in reversed(children):
            stack.append(child)
    return found


def node_source(node):
    """Texto-fonte de um no python, quando houver."""
    code = getattr(node, "code", None)
    source = getattr(code, "source", None)
    if isinstance(source, str):
        return source
    return None


def block_sources(block):
    """Textos python e jumps presentes em uma branch."""
    sources = []
    jumps = []
    for child in collect_nodes(block):
        kind = type(child).__name__
        if kind == "Python":
            source = node_source(child)
            if source:
                sources.append(source)
        elif kind == "Define":
            source = node_source(child)
            if source:
                sources.append("{} = {}".format(child.varname, source))
        elif kind == "Jump":
            target = getattr(child, "target", None)
            if isinstance(target, str):
                jumps.append(target)
    return sources, jumps


def extract_from_file(path):
    """Dados brutos de um .rpyc: personagens, falas e menus."""
    stmts = load_ast(path)

    seen = set()
    root_nodes = []
    for stmt in stmts:
        root_nodes.extend(collect_nodes(stmt, seen))

    # RÃ³tulo de cada nÃ³: o bloco de cada label define o escopo dos seus filhos.
    label_of = {}
    for node in root_nodes:
        if type(node).__name__ != "Label":
            continue
        for child in collect_nodes(node.block):
            label_of[id(child)] = node.name

    characters = {}
    speakers = {}
    dialogue = {}
    menus = []
    ast = ast_module()

    for node in root_nodes:
        if isinstance(node, ast.Say):
            who = getattr(node, "who", None)
            if isinstance(who, str) and who.strip():
                who = who.strip()
                speakers[who] = speakers.get(who, 0) + 1
                text = getattr(node, "what", None)
                if isinstance(text, str) and text.strip():
                    lines = dialogue.setdefault(who, [])
                    if len(lines) < 80:
                        lines.append(text.strip())

        elif isinstance(node, ast.Define):
            source = node_source(node) or ""
            match = CHARACTER_EXPR_RE.search(source)
            if match:
                characters[node.varname] = match.group("name")
            elif node.varname not in characters:
                characters[node.varname] = None

        elif isinstance(node, ast.Python):
            source = node_source(node) or ""
            for match in CHARACTER_ASSIGN_RE.finditer(source):
                characters.setdefault(match.group(1), match.group("name"))

        elif isinstance(node, ast.Menu):
            label = label_of.get(id(node))
            for caption, condition, block in node.items:
                sources, jumps = block_sources(block)
                menus.append(
                    {
                        "label": label,
                        "file": os.path.basename(getattr(node, "filename", "") or ""),
                        "line": getattr(node, "linenumber", 0),
                        "caption": caption if isinstance(caption, str) else str(caption),
                        "condition": condition if isinstance(condition, str) else "",
                        "effects": extract_effects(sources, jumps),
                    }
                )

    return {
        "characters": characters,
        "speakers": speakers,
        "dialogue": dialogue,
        "menus": menus,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    game_root = argv[0]
    output_path = argv[1] if len(argv) > 1 else None

    bootstrap_renpy(game_root)

    scripts_dir = os.path.join(game_root, "game")
    rpyc_files = []
    for root_dir, _dirs, files in os.walk(scripts_dir):
        if os.path.basename(root_dir) == "cache":
            continue
        for name in sorted(files):
            if name.endswith(".rpyc"):
                rpyc_files.append(os.path.join(root_dir, name))

    characters = {}
    speakers = {}
    dialogue = {}
    menus = []
    failed = []

    for index, path in enumerate(rpyc_files, 1):
        rel = os.path.relpath(path, game_root)
        try:
            data = extract_from_file(path)
        except Exception as exc:
            failed.append((rel, repr(exc)))
            continue
        for varname, name in data["characters"].items():
            if characters.get(varname) is None:
                characters[varname] = name
        for who, count in data["speakers"].items():
            speakers[who] = speakers.get(who, 0) + count
        for who, lines in data.get("dialogue", {}).items():
            existing = dialogue.setdefault(who, [])
            for line in lines:
                if len(existing) >= 80:
                    break
                existing.append(line)
        menus.extend(data["menus"])
        if index % 20 == 0:
            print("  ...{}/{} arquivos".format(index, len(rpyc_files)), flush=True)

    result = {
        "files": len(rpyc_files),
        "failed": failed,
        "characters": characters,
        "speakers": speakers,
        "dialogue": dialogue,
        "menus": menus,
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, sort_keys=True)

    print("arquivos lidos: {} (falhas: {})".format(len(rpyc_files) - len(failed), len(failed)))
    print("personagens definidos:", len(characters))
    print("locutores distintos:", len(speakers))
    print("menus:", len(menus))
    if failed:
        for path, error in failed[:10]:
            print("  FALHA", path, error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
