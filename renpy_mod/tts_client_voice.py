# -*- coding: utf-8 -*-
"""Voice resolution rules for the Ren'Py TTS client.

These rules used to live inside ``tts_mod.rpy``, where they could only be
exercised from inside Ren'Py. Here they are pure: the client passes the voice
map and the names it found in the store, and the module decides which voice
speaks the line.
"""

import re


PLAYER_NAME_KEYS = (
    "player_name", "povname", "pc_name", "mc_name", "mcname", "mcN", "mcn",
    "hero_name", "protagonist_name", "user_name", "name", "firstname",
    "first_name", "galleryMC", "gallerymc",
)

BF_NAME_KEYS = ("bfname", "bf_name", "boyfriend_name")

PROTAGONIST_ALIASES = (
    "player", "mc", "anon", "[player_name]", "[povname]",
    "[firstname]", "narrarator", "narrator", "me", "you",
)

MALE_WORDS = frozenset({
    "man", "boy", "guy", "male", "dad", "father", "brother", "mr", "sir",
    "uncle", "grandfather", "grandpa", "doctor", "cop", "police", "officer",
    "waiter", "mechanic", "landlord", "husband", "butler", "agent", "bodyguard",
    "hermit", "dentist", "clerk", "priest", "king", "prince", "lord", "coach",
})

MALE_POOL = (
    "am_adam", "am_fenrir", "am_eric", "am_michael", "am_onyx", "am_puck",
)

FEMALE_POOL = (
    "af_heart", "af_bella", "af_sarah", "af_sky",
    "af_nicole", "af_kore", "af_aoede", "af_jessica", "af_river",
)

DEFAULT_VOICE = "af_heart"


def strip_tags(text):
    """Remove as tags do Ren'Py de um texto."""
    return re.sub(r"\{[^}]*\}", "", str(text or "")).strip()


def clean_speaker_name(raw, substitute=None):
    """Nome do locutor sem as tags.

    ``substitute`` e o ``renpy.substitute``, usado quando existe: ele resolve as
    variaveis do jogo antes da limpeza. Sem ele, ou quando ele falha, o texto
    bruto apenas perde as tags.
    """
    if not raw:
        return None
    if substitute is not None:
        try:
            cleaned = strip_tags(substitute(str(raw)))
            if cleaned:
                return cleaned
        except Exception:
            pass
    return strip_tags(raw)


def collect_context_names(keys, sources):
    """Nomes de protagonista ou parceiro achados em qualquer um dos stores."""
    found = set()
    for source in sources:
        if source is None:
            continue
        for attr in keys:
            value = getattr(source, attr, None)
            if value is not None:
                name = str(value).strip().lower()
                if name:
                    found.add(name)
    return found


def normalize_speaker(speaker):
    """Tira o sufixo de pensamento: "Mia's thoughts" vira "Mia"."""
    return re.sub(
        r"['\u2019]s?\s+thoughts?",
        "",
        str(speaker or "").strip(),
        flags=re.IGNORECASE,
    ).strip()


def _pool_voice(pool, speaker_lower):
    """Escolhe a voz do pool de forma estavel para o mesmo locutor."""
    return pool[sum(ord(char) for char in speaker_lower) % len(pool)]


def resolve_voice(
    speaker=None,
    voice_map=None,
    player_names=frozenset(),
    bf_names=frozenset(),
    current_voice=None,
    default_voice=DEFAULT_VOICE,
    last_speaker=None,
):
    """Voz que fala a linha do locutor informado.

    ``player_names`` e ``bf_names`` sao os nomes que o cliente encontrou no
    store e no persistent; ``last_speaker`` e quem falou por ultimo, usado
    quando a linha nao tem locutor proprio.
    """
    voice_map = voice_map or {}

    if not speaker:
        last_who = str(last_speaker or "").strip().lower()
        if last_who:
            for key, voice in voice_map.items():
                if key.lower() == last_who:
                    return voice
        return (
            voice_map.get("narrator")
            or voice_map.get("player")
            or voice_map.get("default")
            or current_voice
            or default_voice
        )

    speaker_clean = str(speaker).strip()
    speaker_lower = speaker_clean.lower()

    for key, voice in voice_map.items():
        if key.lower() == speaker_lower:
            return voice

    base_speaker = normalize_speaker(speaker_clean)
    base_lower = base_speaker.lower()
    if base_lower != speaker_lower:
        for key, voice in voice_map.items():
            if key.lower() == base_lower:
                return voice
        speaker_lower = base_lower

    if (speaker_lower in PROTAGONIST_ALIASES) or (speaker_lower in player_names):
        return (
            voice_map.get("mc")
            or voice_map.get("player")
            or voice_map.get("narrator")
            or voice_map.get("default")
            or "am_onyx"
        )

    if (speaker_lower in ("bf", "boyfriend", "[bfname]")) or (speaker_lower in bf_names):
        return voice_map.get("bf") or voice_map.get("boyfriend") or "am_adam"

    tokens = set(re.findall(r"[a-z]+", speaker_lower))
    if tokens & MALE_WORDS:
        return _pool_voice(MALE_POOL, speaker_lower)

    return _pool_voice(FEMALE_POOL, speaker_lower)
