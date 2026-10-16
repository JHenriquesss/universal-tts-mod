# -*- coding: utf-8 -*-
import re

try:
    string_types = (basestring, bytes)
except NameError:
    string_types = (str, bytes)


def _to_unicode(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            try:
                return value.decode("latin1", "ignore")
            except Exception:
                return str(value)
    return value


HINT_GREEN = "#4ade80"
HINT_RED = "#f87171"
HINT_NEUTRAL = "#c8c8c8"


def normalize_caption_unicode(value):
    if not isinstance(value, string_types) or not value:
        return value
    result = _to_unicode(value)
    for char in ("\u2019", "\u2018", "\u2032", "\u00b4", "\u02bc"):
        result = result.replace(char, "'")
    result = result.replace("\u201c", '"').replace("\u201d", '"')
    result = result.replace("\u2026", "...")
    result = result.replace("\u2013", "-").replace("\u2014", "-")
    return result.replace("\u00a0", " ")


def build_choice_hints(generated=None, curated=None):
    hints = {}
    for source in (generated, curated):
        if not source:
            continue
        for key, value in source.items():
            if isinstance(key, tuple) and len(key) == 2:
                label, caption = key
                u_label = _to_unicode(label) if label is not None else None
                u_caption = normalize_caption_unicode(caption)
                hints[(u_label, u_caption)] = value
            elif isinstance(key, string_types):
                hints[normalize_caption_unicode(key)] = value
            else:
                hints[key] = value
    _register_unicode_aliases(hints)
    return hints


def _register_unicode_aliases(hints):
    extra = {}
    for key, value in list(hints.items()):
        if isinstance(key, tuple) and len(key) == 2:
            label, caption = key
            normalized = normalize_caption_unicode(caption)
            if normalized != caption:
                extra.setdefault((label, normalized), value)
            stripped = display_choice_caption(normalized)
            if stripped != normalized:
                extra.setdefault((label, stripped), value)
        elif isinstance(key, string_types):
            normalized = normalize_caption_unicode(key)
            if normalized != key:
                extra.setdefault(normalized, value)
            stripped = display_choice_caption(normalized)
            if stripped != normalized:
                extra.setdefault(stripped, value)
    for key, value in extra.items():
        hints.setdefault(key, value)


def clean_caption_for_match(value):
    if not isinstance(value, string_types) or not value:
        return value
    s = _to_unicode(value).replace("\\n", " ").replace("\n", " ")
    s = re.sub(r"\{[^}]*\}", "", s)
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # remove sufixo tipico do MLT como (More Content) para matching base
    s = re.sub(r"\s*\(More Content\)\s*$", "", s, flags=re.I).strip()
    return normalize_caption_unicode(s)


def lookup_choice_hint(hints, current_label, caption):
    if current_label is not None:
        current_label = _to_unicode(current_label)
    cap = normalize_caption_unicode(caption)
    if not cap:
        return None

    candidates = [cap]
    stripped = display_choice_caption(cap)
    if stripped and stripped not in candidates:
        candidates.append(stripped)
    clean = clean_caption_for_match(cap)
    if clean and clean not in candidates:
        candidates.append(clean)
    clean_stripped = display_choice_caption(clean)
    if clean_stripped and clean_stripped not in candidates:
        candidates.append(clean_stripped)

    for cand in candidates:
        if current_label is not None:
            label_hint = hints.get((current_label, cand))
            if label_hint is not None:
                return label_hint
        caption_hint = hints.get(cand)
        if caption_hint is not None:
            return caption_hint

    for key, value in hints.items():
        if not (isinstance(key, tuple) and len(key) == 2):
            continue
        label, key_caption = key
        if current_label is not None and label != current_label:
            continue
        key_norm = normalize_caption_unicode(key_caption)
        if key_norm in candidates or clean_caption_for_match(key_norm) in candidates:
            return value
        key_stripped = display_choice_caption(key_norm)
        if key_stripped in candidates or (stripped and key_stripped == stripped):
            return value

    return None


def display_choice_caption(caption):
    source = normalize_caption_unicode(caption)
    if not source:
        return source

    rest = source
    while True:
        match = re.match(r"^\([^)]+\)\s+", rest)
        if not match:
            break
        rest = rest[match.end():].lstrip()
    return rest if rest else source


def build_additive_button_caption(caption, item_kwargs=None, hints_enabled=False):
    """
    Constrói a legenda visível do botão de escolha de forma aditiva:
    1. Remove prefixos de requisitos técnicos da legenda base via display_choice_caption.
    2. Preserva e concatena kwargs['hint'] nativos do jogo quando hints_enabled=True,
       sem descartar parênteses legítimos do hint nativo e sem falhar se item_kwargs for None.
    """
    base_label = display_choice_caption(caption)
    if hints_enabled and isinstance(item_kwargs, dict):
        native_hint = item_kwargs.get("hint")
        if native_hint:
            return "{} {}".format(base_label, native_hint)
    return base_label


def format_hint_for_display(raw_hint):
    if not raw_hint:
        return ""

    units = []
    for segment in _strip_requirement_segments(raw_hint).split(";"):
        segment = segment.strip()
        if not segment:
            continue
        if "," in segment and ("+=" in segment or "-=" in segment or re.search(r"\s[+-]\d", segment)):
            units.extend(part.strip() for part in segment.split(",") if part.strip())
        else:
            units.append(segment)

    parts = []
    for unit in units:
        escaped = unit.replace("{", "{{").replace("}", "}}").replace("[", "[[")
        parts.append("{color=" + _hint_chunk_color(unit) + "}" + escaped + "{/color}")
    return "; ".join(parts)


def _strip_requirement_segments(raw_hint):
    kept = []
    for segment in raw_hint.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        if segment.lower().startswith("requer"):
            continue
        kept.append(segment)
    return "; ".join(kept) if kept else raw_hint


def _hint_chunk_color(chunk):
    text = chunk.strip()
    if not text:
        return HINT_NEUTRAL

    lowered = text.lower()
    if lowered.startswith("ramo ") or "sem vari" in lowered:
        return HINT_NEUTRAL
    if "-=" in text:
        return HINT_RED
    if "+=" in text:
        return HINT_GREEN
    if re.search(r"\s-\d+", text) and "level" not in lowered:
        return HINT_RED
    if re.search(r"\s\+\d+", text) or re.search(r"^\+\d", text):
        return HINT_GREEN
    if "poss" in lowered and ("mc_exp" in lowered or "bonus_xp" in lowered):
        return HINT_GREEN
    if "bónus" in lowered or "bonus" in lowered:
        return HINT_GREEN
    if re.search(r"[=\s]-\d+\s*$", text):
        return HINT_RED
    if re.search(r"[=\s]\+\d+\s*$", text):
        return HINT_GREEN
    return HINT_NEUTRAL
