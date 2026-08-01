import re


HINT_GREEN = "#4ade80"
HINT_RED = "#f87171"
HINT_NEUTRAL = "#c8c8c8"


def normalize_caption_unicode(value):
    if not isinstance(value, str) or not value:
        return value
    result = value
    for char in ("\u2019", "\u2018", "\u2032", "\u00b4", "\u02bc"):
        result = result.replace(char, "'")
    return result.replace("\u201c", '"').replace("\u201d", '"')


def build_choice_hints(generated=None, curated=None):
    hints = {}
    hints.update(generated or {})
    hints.update(curated or {})
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
        elif isinstance(key, str):
            normalized = normalize_caption_unicode(key)
            if normalized != key:
                extra.setdefault(normalized, value)
    for key, value in extra.items():
        hints.setdefault(key, value)


def lookup_choice_hint(hints, current_label, caption):
    cap = normalize_caption_unicode(caption)
    if not cap:
        return None

    if current_label is not None:
        label_hint = hints.get((current_label, cap))
        if label_hint is not None:
            return label_hint

    caption_hint = hints.get(cap)
    if caption_hint is not None:
        return caption_hint

    for key, value in hints.items():
        if not (isinstance(key, tuple) and len(key) == 2):
            continue
        label, key_caption = key
        if normalize_caption_unicode(key_caption) != cap:
            continue
        if current_label is not None and label != current_label:
            continue
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
