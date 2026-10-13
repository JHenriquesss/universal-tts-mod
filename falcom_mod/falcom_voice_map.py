import os
import re
import sys

try:
    from text_cleaner import TextCleaner
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from text_cleaner import TextCleaner


# Mapeamento de Retratos Falcom ED6 para vozes Kokoro
PORTRAIT_VOICE_MAP = {
    0: "af_heart",    # Estelle Bright (0-9, 1000-1009)
    1: "am_adam",     # Joshua Bright (10-19, 1010-1019)
    2: "af_sarah",    # Scherazard Harvey (20-29, 1020-1029)
    3: "am_fenrir",   # Olivier Lenheim (30-39, 1030-1039)
    4: "af_sky",      # Kloe Rinz (40-49, 1040-1049)
    5: "am_onyx",     # Agate Crosner (50-59, 1050-1059)
    6: "af_bella",    # Tita Russell (60-69, 1060-1069)
    7: "am_eric",     # Zin Vathek (70-79, 1070-1079)
    8: "am_michael",  # Kevin Graham (80-89, 1080-1089)
    9: "af_nicole",   # Anelace Elfead (90-99, 1090-1099)
}


def voice_for_face_id(face_id):
    """Retorna a voz Kokoro correspondente ao ID do retrato Falcom, ou None."""
    if face_id is None:
        return None

    # Estelle Bright SC outfit (todas as expressões: 1000 a 1029)
    if 1000 <= face_id <= 1029:
        return "af_heart"

    # Olivier SC outfit (1030 a 1039)
    if 1030 <= face_id <= 1039:
        return "am_fenrir"

    # Kloe SC outfit (1040 a 1049)
    if 1040 <= face_id <= 1049:
        return "af_sky"

    # Tita SC outfit (1060 a 1069)
    if 1060 <= face_id <= 1069:
        return "af_bella"

    # Agate SC expressions (550 a 559)
    if 550 <= face_id <= 559:
        return "am_onyx"

    # Joshua SC scenes / alternative (490 a 499, 590 a 599, 1710 a 1719)
    if (490 <= face_id <= 499) or (590 <= face_id <= 599) or (1710 <= face_id <= 1719):
        return "am_adam"

    # Dorothy (150 a 159)
    if 150 <= face_id <= 159:
        return "af_bella"

    # Josette (210 a 219)
    if 210 <= face_id <= 219:
        return "af_sarah"

    # Julia (700 a 709)
    if 700 <= face_id <= 709:
        return "af_sarah"

    base_id = (face_id % 1000) if face_id >= 1000 else face_id
    char_group = base_id // 10
    return PORTRAIT_VOICE_MAP.get(char_group)


# Mapeamento estendido de nomes de personagens Falcom ED6 para vozes Kokoro
CHARACTER_NAME_VOICE_MAP = {
    # Estelle Bright
    "estelle": "af_heart",
    "estelle bright": "af_heart",
    "eh-stell": "af_heart",
    "eh-stell bright": "af_heart",

    # Joshua Bright
    "joshua": "am_adam",
    "joshua bright": "am_adam",
    "josh-wah": "am_adam",
    "josh-wah bright": "am_adam",

    # Scherazard Harvey
    "scherazard": "af_sarah",
    "scherazard harvey": "af_sarah",
    "schera": "af_sarah",
    "share-ah-zard": "af_sarah",

    # Olivier Lenheim
    "olivier": "am_fenrir",
    "olivier lenheim": "am_fenrir",
    "oh-liv-ee-ay": "am_fenrir",
    "olivert": "am_fenrir",

    # Kloe Rinz / Klaudia
    "kloe": "af_sky",
    "kloe rinz": "af_sky",
    "klaudia": "af_sky",
    "klaudia von auslese": "af_sky",
    "kloh-ee": "af_sky",

    # Agate Crosner
    "agate": "am_onyx",
    "agate crosner": "am_onyx",
    "ah-gate": "am_onyx",

    # Tita Russell
    "tita": "af_bella",
    "tita russell": "af_bella",
    "tee-tah": "af_bella",

    # Zin Vathek
    "zin": "am_eric",
    "zin vathek": "am_eric",

    # Kevin Graham
    "kevin": "am_michael",
    "kevin graham": "am_michael",
    "father kevin": "am_michael",

    # Anelace Elfead
    "anelace": "af_nicole",
    "anelace elfead": "af_nicole",

    # Kurt Nardin
    "kurt": "am_adam",
    "kurt nardin": "am_adam",

    # Cassius Bright
    "cassius": "am_eric",
    "cassius bright": "am_eric",
    "kass-ee-us": "am_eric",

    # Russell family
    "prof. russell": "am_eric",
    "professor russell": "am_eric",
    "albert russell": "am_eric",
    "russell": "am_eric",
    "erika": "af_sarah",
    "erika russell": "af_sarah",
    "dan": "am_eric",
    "dan russell": "am_eric",

    # Bracer Guild
    "elnan": "am_adam",
    "aina": "af_sarah",
    "lugran": "am_eric",
    "jean": "am_adam",

    # Capua Family
    "josette": "af_sarah",
    "josette capua": "af_sarah",
    "kyle": "am_onyx",
    "kyle capua": "am_onyx",
    "don": "am_eric",
    "don capua": "am_eric",

    # Royal Guard & Military
    "julia": "af_sarah",
    "julia schwarz": "af_sarah",
    "richard": "am_adam",
    "alan richard": "am_adam",
    "colonel richard": "am_adam",
    "mueller": "am_onyx",
    "mueller vander": "am_onyx",
    "major mueller": "am_onyx",
    "morgan": "am_eric",
    "general morgan": "am_eric",
    "cid": "am_adam",
    "alicia": "af_sarah",
    "queen alicia": "af_sarah",

    # Ouroboros
    "renne": "af_bella",
    "walter": "am_fenrir",
    "luciola": "af_sarah",
    "loo-chee-oh-lah": "af_sarah",
    "bleublanc": "am_fenrir",
    "bluh-blahn": "am_fenrir",
    "weissmann": "am_michael",
    "georg weissmann": "am_michael",
    "professor weissmann": "am_michael",
    "vice-man": "am_michael",
    "campanella": "af_sky",
    "cam-pah-neh-lah": "af_sky",
    "loewe": "am_adam",
    "leh-veh": "am_adam",
    "leonhardt": "am_adam",
    "lorence": "am_adam",
    "gilbert": "am_fenrir",

    # Civilians / Journalists
    "dorothy": "af_bella",
    "dorothy hyatt": "af_bella",
    "nial": "am_fenrir",
    "nial burns": "am_fenrir",
    "klaus": "am_eric",
    "mayor klaus": "am_eric",
    "dalmore": "am_eric",
    "mayor dalmore": "am_eric",
    "theresia": "af_sarah",
    "edel": "af_sarah",
}


def resolve_falcom_voice(raw_text, default_voice="af_heart"):
    """
    Identifica com alta precisão a voz Kokoro para o texto Falcom.
    Prioridades:
    1. Tag explícita de locutor (#0CNome#0C, [Nome], Nome:)
    2. Auto-identificação no texto (ex: 'I, Estelle Bright...', 'I, Eh-stell...')
    3. ID do retrato (#...F) via voice_for_face_id
    4. Voz padrão fallback (af_heart) - NUNCA retorna None, eliminando 'Sticky Voice'
    """
    if not raw_text:
        return default_voice

    text_str = str(raw_text)

    # 1. Extração por tags de nome explícitas
    # #0CNome#0C (padrão de script Falcom)
    for m in re.finditer(r"#0C([^#\n\r]+)#0C", text_str):
        raw_name = m.group(1).strip().lower()
        name = re.sub(r"[\[\]]", "", raw_name).strip()
        if name in CHARACTER_NAME_VOICE_MAP:
            return CHARACTER_NAME_VOICE_MAP[name]
        first_word = name.split()[0] if name else ""
        if first_word in CHARACTER_NAME_VOICE_MAP:
            return CHARACTER_NAME_VOICE_MAP[first_word]

    # [Nome] (comum em dumps de script / Textractor)
    for m in re.finditer(r"\[([A-Za-z. \-]{2,25})\]", text_str):
        name = m.group(1).strip().lower()
        if name in CHARACTER_NAME_VOICE_MAP:
            return CHARACTER_NAME_VOICE_MAP[name]
        first_word = name.split()[0] if name else ""
        if first_word in CHARACTER_NAME_VOICE_MAP:
            return CHARACTER_NAME_VOICE_MAP[first_word]

    # Nome: (prefixo de fala)
    m_prefix = re.match(r"^\s*([A-Za-z. \-]{2,20}):", text_str)
    if m_prefix:
        name = m_prefix.group(1).strip().lower()
        if name in CHARACTER_NAME_VOICE_MAP:
            return CHARACTER_NAME_VOICE_MAP[name]
        first_word = name.split()[0] if name else ""
        if first_word in CHARACTER_NAME_VOICE_MAP:
            return CHARACTER_NAME_VOICE_MAP[first_word]

    # 2. Auto-apresentação no texto (ex: 'I, Estelle Bright...', 'I, Eh-stell...')
    m_intro = re.search(r"\bI,\s*([A-Za-z\-]+)(?:\s+[A-Za-z\-]+)?\b", text_str, re.IGNORECASE)
    if m_intro:
        first_name = m_intro.group(1).strip().lower()
        if first_name in CHARACTER_NAME_VOICE_MAP:
            return CHARACTER_NAME_VOICE_MAP[first_name]

    # 3. Retrato Falcom (#...F)
    face_id = TextCleaner.extract_face_id(text_str)
    if face_id is not None:
        portrait_voice = voice_for_face_id(face_id)
        if portrait_voice:
            return portrait_voice

    # 4. Fallback padrão seguro (garante que nunca haverá voz vazia)
    return default_voice
