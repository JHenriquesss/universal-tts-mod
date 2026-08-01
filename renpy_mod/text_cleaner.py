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
    '♪': '', '♫': '',
    '★': '', '☆': '',
    '♥': '', '♡': '',
    '【': '[', '】': ']',
    '「': '"', '」': '"',
    '『': '"', '』': '"',
}

SLANG_MAP = {
    r"\bmore'n\b": "more than",
    r"\b'bout\b": "about",
    r"\bd'ya\b": "do you",
    r"\b'cause\b": "because",
    r"\bnuthin'\b": "nothing",
    r"\bnuthin\b": "nothing",
    r"\bsomefin'\b": "something",
    r"\bsomefin\b": "something",
    r"\bfink\b": "think",
    r"\bda\b": "the",
    r"\bwiv\b": "with",
    r"\bova\b": "over",
    r"\b'ello\b": "hello",
    r"\bdis\b": "this",
    r"\bdat\b": "that",
    r"\bfer\b": "for",
    r"\bn'\b": "and",
    r"\ban'\b": "and",
    r"\b'round\b": "around",
    r"\b'im\b": "him",
    r"\b'er\b": "her",
    r"\bin't\b": "isn't",
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

class TextCleaner:
    """
    Limpa o texto do Ren'Py para ser lido pelo TTS.
    Remove tags, lida com escapes e normaliza pontuação.
    """
    
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
        
        # 4. Remover tags do Ren'Py {...} e HTML/RichText (<...>)
        cleaned = re.sub(r'\{[^}]*\}', '', text)
        cleaned = re.sub(r'<[^>]*>', '', cleaned)
        
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
        cleaned = re.sub(r'\b(\w+n)\'(?=\s|$|[.,!?])', r'\1g', cleaned)
        
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

        # 10. Remover espaços em branco extras
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return cleaned
