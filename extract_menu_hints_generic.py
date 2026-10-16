import argparse
import os
import re


DEFAULT_ARCHIVE_NAME = "scripts.rpa"
DEFAULT_OUTPUT_NAME = "zzz_mod_choice_hints_generated.rpy"


LABEL_RE = re.compile(r"^\s*label\s+([a-zA-Z0-9_]+)\s*:")
MENU_RE = re.compile(r"^(\s*)menu(?:\s+[a-zA-Z0-9_]+)?\s*:")
CHOICE_SINGLE_RE = re.compile(
    r"^(\s*)(?:\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)')(?:\s*\([^)]*\))?(?:\s*if\s+.*)?\s*:$"
)
CHOICE_MULTI_RE = re.compile(
    r"^(\s*)(?:\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)')(?:\s*\([^)]*\))?\s*if\s*\("
)

EFFECT_PATTERNS = [
    re.compile(r"\$?\s*([a-zA-Z0-9_]+\s*(?:\+=|-=|=)\s*[a-zA-Z0-9_\"'\.]+)"),
    re.compile(r"([a-zA-Z0-9_]+\.(?:append|remove|add)\([^\)]*\))"),
    re.compile(r"(route_[a-zA-Z0-9_]+\s*=\s*(?:True|False))"),
]


def extract_choice_hints(data):
    if isinstance(data, bytes):
        text = data.decode("utf-8", "ignore")
    else:
        text = data

    lines = [line.rstrip("\r\n") for line in text.splitlines()]
    hints = {}
    current_label = "unknown"
    stack = []
    i = 0
    n = len(lines)

    while i < n:
        raw_line = lines[i]
        sline = raw_line.strip()

        if not sline or sline.startswith("#"):
            if stack and stack[-1][0] == "choice":
                stack[-1][4].append(sline)
            i += 1
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))

        lbl_m = LABEL_RE.match(raw_line)
        if lbl_m:
            current_label = lbl_m.group(1)
            _unwind_stack(stack, hints)
            i += 1
            continue

        menu_m = MENU_RE.match(raw_line)
        if menu_m:
            m_indent = len(menu_m.group(1))
            _unwind_stack_to_indent(stack, m_indent, hints)
            stack.append(("menu", m_indent, current_label))
            i += 1
            continue

        if _has_enclosing_menu(stack, indent):
            choice_info = _match_choice_header(lines, i)
            if choice_info:
                c_indent, caption, end_hdr_idx = choice_info
                _unwind_choices_to_indent(stack, c_indent, hints)
                caption = caption.replace('\\"', '"').replace("\\'", "'")
                stack.append(("choice", c_indent, current_label, caption, []))
                i = end_hdr_idx + 1
                continue

        _unwind_stack_to_indent(stack, indent, hints)
        if stack and stack[-1][0] == "choice":
            stack[-1][4].append(sline)
        i += 1

    _unwind_stack(stack, hints)
    return hints


def _has_enclosing_menu(stack, indent):
    for item in reversed(stack):
        if item[0] == "menu":
            return indent > item[1]
    return False


def _match_choice_header(lines, idx):
    line = lines[idx]
    s = line.rstrip()
    m = CHOICE_SINGLE_RE.match(s)
    if m:
        indent = len(m.group(1))
        caption = m.group(2) if m.group(2) is not None else m.group(3)
        return indent, caption, idx

    m = CHOICE_MULTI_RE.match(s)
    if m:
        indent = len(m.group(1))
        caption = m.group(2) if m.group(2) is not None else m.group(3)
        cur = idx
        while cur < len(lines) and not lines[cur].rstrip().endswith(":"):
            cur += 1
        return indent, caption, cur

    return None


def _unwind_stack(stack, hints):
    while stack:
        top = stack.pop()
        if top[0] == "choice":
            _record_choice_effects(top, hints)


def _unwind_stack_to_indent(stack, indent, hints):
    while stack and stack[-1][1] >= indent:
        top = stack.pop()
        if top[0] == "choice":
            _record_choice_effects(top, hints)


def _unwind_choices_to_indent(stack, indent, hints):
    while stack and stack[-1][0] == "choice" and stack[-1][1] >= indent:
        top = stack.pop()
        _record_choice_effects(top, hints)


def _record_choice_effects(choice_item, hints):
    _, _, label, caption, branch_lines = choice_item
    effects = _extract_effects_from_lines(branch_lines)
    if effects:
        _merge_hint(hints, (label, caption), effects)


def _extract_effects_from_lines(branch_lines):
    effects = []
    text_block = "\n".join(branch_lines)

    for pattern in EFFECT_PATTERNS:
        for match in pattern.finditer(text_block):
            effect = match.group(1).replace("$", "").strip()
            if _is_control_expression(effect):
                continue
            if effect not in effects:
                effects.append(effect)

    if not effects:
        jump_match = re.search(r"jump\s+([a-zA-Z0-9_]+)", text_block)
        if jump_match:
            effects.append("Jump -> " + jump_match.group(1))

    return effects


def _is_control_expression(effect):
    return (
        effect.startswith("if ")
        or effect.startswith("elif ")
        or "==" in effect
        or ">=" in effect
        or "<=" in effect
        or "!=" in effect
    )


def _merge_hint(hints, key, effects):
    if key not in hints:
        hints[key] = "; ".join(effects)
        return

    existing = hints[key].split("; ")
    for effect in effects:
        if effect not in existing:
            existing.append(effect)
    hints[key] = "; ".join(existing)


def render_generated_hints(hints):
    lines = [
        "# Generated by extract_menu_hints_generic.py",
        "init -2 python:",
        "    GENERATED_CHOICE_HINTS = {",
    ]

    for label, caption in sorted(hints.keys()):
        hint = hints[(label, caption)]
        lines.append("        ('{}', '{}'): '{}',".format(_escape(label), _escape(caption), _escape(hint)))

    lines.append("    }")
    return "\n".join(lines) + "\n"


import textwrap


def load_prior_hints(prior_path):
    if not prior_path or not os.path.exists(prior_path):
        return {}
    with open(prior_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = [
        line for line in content.splitlines()
        if not line.strip().startswith("init") and not line.strip().startswith("#")
    ]
    scope = {}
    try:
        exec(textwrap.dedent("\n".join(lines)), scope)
        return scope.get("GENERATED_CHOICE_HINTS", {})
    except Exception:
        return {}


def extract_from_directory(game_dir):
    hints = {}
    for root_dir, _subdirs, filenames in os.walk(game_dir):
        for filename in sorted(filenames):
            if filename.endswith(".rpy") and not filename.startswith("zzz_mod_choice_hints_generated"):
                file_path = os.path.join(root_dir, filename)
                try:
                    with open(file_path, "rb") as f:
                        file_hints = extract_choice_hints(f.read())
                    hints.update(file_hints)
                except Exception:
                    continue
    return hints


def run_extraction(target_path, output_path, prior_hints_path=None):
    if os.path.isdir(target_path):
        hints = extract_from_directory(target_path)
    else:
        with open(target_path, "rb") as archive_file:
            hints = extract_choice_hints(archive_file.read())

    if prior_hints_path:
        prior = load_prior_hints(prior_hints_path)
        merged = dict(prior)
        merged.update(hints)
        hints = merged

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(render_generated_hints(hints))

    return len(hints)


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Extract Ren'Py menu consequence hints from an archive-like file or game folder.")
    parser.add_argument("--game-path", help="Game folder used to derive default archive/output paths.")
    parser.add_argument("--archive", help="Input archive/script file or folder path. Defaults to <game-path>/scripts.rpa or <game-path>.")
    parser.add_argument("--output", help="Output .rpy path. Defaults to <game-path>/zzz_mod_choice_hints_generated.rpy.")
    parser.add_argument("--prior-hints", help="Path to prior episode zzz_mod_choice_hints_generated.rpy to merge.")
    return parser


def resolve_paths(args):
    archive_path = args.archive
    output_path = args.output

    if args.game_path:
        default_archive = os.path.join(args.game_path, DEFAULT_ARCHIVE_NAME)
        if not archive_path:
            if os.path.exists(default_archive) or not os.path.exists(args.game_path):
                archive_path = default_archive
            else:
                archive_path = args.game_path
        output_path = output_path or os.path.join(args.game_path, DEFAULT_OUTPUT_NAME)

    if not archive_path or not output_path:
        raise ValueError("Provide --archive and --output, or provide --game-path for defaults.")

    return archive_path, output_path


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        archive_path, output_path = resolve_paths(args)
        count = run_extraction(archive_path, output_path, prior_hints_path=args.prior_hints)
    except Exception as exc:
        parser.error(str(exc))
        return 2

    print("Extracted {} choice hints to {}".format(count, output_path))
    return 0


def _escape(value):
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


if __name__ == "__main__":
    raise SystemExit(main())
