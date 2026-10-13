# -*- coding: utf-8 -*-
import re


MOJIBAKE_PAIRS = [
    ("â€¦", "..."),
    ("â€\x9d", '"'),
    ("â€œ", '"'),
    ("â€™", "'"),
    ("â€˜", "'"),
    ("â€”", "—"),
    ("â€“", "–"),
    ("â€", "..."),
    ("Â", ""),
]

APOSTROPHES = ['’', '‘', '´', '`', '′', '’', 'ʼ', '’', '‘']

SPECIAL_REPLACEMENTS = {
    '—': ' ',
    '–': ' ',
    '…': '...',
    '*': '',
    '~': '',
    '“': '"',
    '”': '"',
    '„': '"',
    '♪': '', '♫': '', '♬': '', '🎵': '',
    '★': '', '☆': '',
    '♥': '', '♡': '', '❤': '', '🖤': '',
    '☕': '',
    '‑': '-',
    '\ufe0e': '', '\ufe0f': '',
    '\u200b': '', '\u200c': '', '\u200d': '', '\ufeff': '',
    '【': '[', '】': ']',
    '「': '"', '」': '"',
    '『': '"', '』': '"',
}

SLANG_MAP = {
    r"(?<!\w)more'n(?!\w)": "more than",
    r"(?<!\w)'bout(?!\w)": "about",
    r"(?<!\w)d'ya(?!\w)": "do you",
    r"(?<!\w)'cause(?!\w)": "because",
    r"(?<!\w)nuthin'(?!\w)": "nothing",
    r"\bnuthin\b": "nothing",
    r"(?<!\w)somefin'(?!\w)": "something",
    r"\bsomefin\b": "something",
    r"\bfink\b": "think",
    r"\bwiv\b": "with",
    r"\bova\b": "over",
    r"(?<!\w)'ello(?!\w)": "hello",
    r"\bdis\b": "this",
    r"\bdat\b": "that",
    r"\bfer\b": "for",
    r"(?<!\w)n'(?!\w)": "and",
    r"(?<!\w)an'(?!\w)": "and",
    r"(?<!\w)'round(?!\w)": "around",
    r"(?<!\w)'im(?!\w)": "him",
    r"(?<!\w)'er(?!\w)": "her",
    r"(?<!\w)in't(?!\w)": "isn't",
    r"\binnit\b": "isn't it",
}

DEFAULT_PRONUNCIATION_OVERRIDES = {
    r"\bKal'trath\b": "Kal trath",
    r"\bHeleon\b": "He-leon",
    r"\bNadia\b": "Nah-dee-ah",
    r"\bNahdia\b": "Nah-dee-ah",
    r"\bDezno\b": "Dez-no",
    r"\bEllie\b": "El-lee",
}

FALCOM_PRONUNCIATION_OVERRIDES = {
    r"\bSepith\b": "Seh-pith",
    r"\bSept-Terrion\b": "Sept Tair-ree-on",
    r"\bSeptian\b": "Sep-tee-an",
    r"\bBracer\b": "Bray-ser",
    r"\bOrbment\b": "Orb-ment",
    r"\bGrancel\b": "Gran-sell",
    r"\bZeiss\b": "Zice",
    r"\bRolent\b": "Ro-lent",
    r"\bBose\b": "Boz",
    r"\bRuan\b": "Roo-ahn",
    r"\bOuroboros\b": "Oo-roh-boh-ros",
    r"\bEsmelas\b": "Ez-meh-las",
    r"\bCarnelia\b": "Car-neel-ee-ah",
    r"\bWeissmann\b": "Vice-man",
    r"\bLoewe\b": "Leh-veh",
    r"\bRenne\b": "Ren",
    r"\bBleublanc\b": "Bluh-blahn",
    r"\bWalter\b": "Wall-ter",
    r"\bLuciola\b": "Loo-chee-oh-lah",
    r"\bCampanella\b": "Cam-pah-neh-lah",
}

class TextCleaner:
    """
    Limpa o texto do Ren'Py e Falcom ED6 para ser lido pelo TTS.
    Remove tags, lida com escapes, normaliza pontuação e extrai locutor.
    """

    @staticmethod
    def extract_face_id(raw_text):
        """Retorna o ID numérico do retrato Falcom #...F se presente, ou None."""
        if not raw_text:
            return None
        m = re.search(r"#(\d+)F", str(raw_text))
        return int(m.group(1)) if m else None
    
    @staticmethod
    def clean(text, pronunciation_overrides=None):
        if not text:
            return ""
            
        # 1. Converter para string e garantir que estamos lidando com unicode
        text = str(text)
        
        # 1.5. Limpeza de MOJIBAKE (UTF-8 lido como CP1252)
        # Frequentemente ocorre em jogos traduzidos ou arquivos salvos com encoding errado.
        for bad, good in MOJIBAKE_PAIRS:
            text = text.replace(bad, good)

        # 2. Normalização AGRESSIVA de apóstrofos (antes de qualquer outra coisa)
        # Inclui variantes de aspas simples e caracteres modificadores que parecem apóstrofos
        for apo in APOSTROPHES:
            text = text.replace(apo, "'")
        
        # 3. Proteger escapes de chaves {{ e }} e colchetes [[ e ]]
        text = text.replace('{{', '__LBRACE__').replace('}}', '__RBRACE__')
        text = text.replace('[[', '__LBRACKET__').replace(']]', '__RBRACKET__')
        
        # 4. Remover tags do Ren'Py {...}, HTML/RichText (<...>), Falcom ED6 (#...) e RPG Maker (\N[1], \C[n], etc.)
        # Resolução de atores e escape codes do RPG Maker
        cleaned = re.sub(r'\\\[N\]1', 'Reid', text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\N\[11\]', 'Liora', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\N\[\d*\]', 'Reid', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\n\[1\]', 'Reid', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\V\[\d+\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\c\[\d+\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\I,', ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\[a-zA-Z]+\[[^\]]*\]', ' ', cleaned)
        cleaned = re.sub(r'\\[\.\|\^!><{}\\$#]', ' ', cleaned)

        # Tags do Ren'Py, HTML e Falcom
        cleaned = re.sub(r'\{[^}]*\}', ' ', cleaned)
        cleaned = re.sub(r'<[^>]*>', ' ', cleaned)
        cleaned = re.sub(r'#{2,}', ' ', cleaned)
        cleaned = re.sub(r'#\d*[CWVPFSKcwvpfsk]', ' ', cleaned)
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', cleaned)
        
        # 5. Restaurar chaves e colchetes protegidos
        cleaned = cleaned.replace('__LBRACE__', '{').replace('__RBRACE__', '}')
        cleaned = cleaned.replace('__LBRACKET__', '[').replace('__RBRACKET__', ']')
        
        # 6. Normalizar outros caracteres especiais
        for old, new in SPECIAL_REPLACEMENTS.items():
            cleaned = cleaned.replace(old, new)

        # 7. Normalizar pontuação excessiva
        cleaned = re.sub(r'\?+', '?', cleaned)
        cleaned = re.sub(r'\!+', '!', cleaned)
        cleaned = re.sub(r'[\?!]{2,}', '?!', cleaned)
        cleaned = re.sub(r'\.{2,}', '...', cleaned)
        # O renderer ED6 pode juntar linhas sem inserir espaço no buffer.
        cleaned = re.sub(r'([.!?])(?=[A-Z])', r'\1 ', cleaned)

        # 8. Expansão de gírias/abreviações comuns que confundem o TTS
        # ya -> you, ye -> you
        cleaned = re.sub(r'\b(ya|ye)\b', 'you', cleaned, flags=re.IGNORECASE)
        # gonna -> going to, wanna -> want to, dunno -> don't know
        cleaned = re.sub(r'\bgonna\b', 'going to', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bwanna\b', 'want to', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bdunno\b', "don't know", cleaned, flags=re.IGNORECASE)
        # ain't -> ain't (motor entende), mas aint/fockin/etc precisam de ajuste
        cleaned = re.sub(r'\baint\b', "ain't", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bfockin\b', "fucking", cleaned, flags=re.IGNORECASE)
        
        # Contrações caipiras e britânicas específicas
        for pattern, replacement in SLANG_MAP.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # comin' -> coming, doin' -> doing, somethin' -> something
        cleaned = re.sub(r'\b([A-Za-z]+in)\'(?=\s|$|[.,!?])', r'\1g', cleaned)
        
        # Proteção extra para 'em (them)
        cleaned = re.sub(r"(^|\s)'em\b", r"\1them", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(^|\s)\'(\w+)\b', r'\1\2', cleaned)

        # 9. Limpeza de onomatopeias de pausa
        # Removido duplicatas e adicionado suporte a mais variações
        cleaned = re.sub(r'\b(Uhh|Umm|Mmm|Awww|Grrr|Haha|Hehehe|Ooof|Grrrr)\b', '', cleaned, flags=re.IGNORECASE)
        
        # 9.5. Correções de Pronúncia para nomes específicos do jogo (Opcional/Customizável)
        # Se o TTS tiver dificuldade com nomes fantasiosos, podemos ajudar aqui
        active_pronunciations = DEFAULT_PRONUNCIATION_OVERRIDES.copy()
        if pronunciation_overrides:
            active_pronunciations.update(pronunciation_overrides)
        for pattern, replacement in active_pronunciations.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # 9.8. Remover espaços antes de pontuação gerados por tags
        cleaned = re.sub(r'\s+([.,!?;:])', r'\1', cleaned)

        # 10. Remover espaços em branco extras
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned
