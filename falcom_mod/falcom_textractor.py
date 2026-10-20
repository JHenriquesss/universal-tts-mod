import os
import re
import struct


TEXT_ROUTINE_PATTERNS = {
    "sc": re.compile(rb"\x8b\x74\x24\x20\xe9....\x3c\x23\x0f\x85....", re.DOTALL),
    "3rd": re.compile(rb"\x89\xb3....\xe9....\x3c\x23\x0f\x85....", re.DOTALL),
    "fc": re.compile(rb"\x80\xf9\x23\x0f\x85....", re.DOTALL),
}

TEXT_FUNCTION_PROLOGUE = re.compile(
    rb"\x55\x8b\xec\x83\xe4\xc0\x81\xec....\x53\x8b\xd9\x56\x57",
    re.DOTALL,
)


def _pe_sections(data):
    if len(data) < 0x40:
        raise ValueError("Executável PE inválido: cabeçalho DOS incompleto")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise ValueError("Executável PE inválido: assinatura PE ausente")
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    section_table = pe_offset + 24 + optional_size
    for index in range(section_count):
        offset = section_table + (index * 40)
        name = data[offset : offset + 8].rstrip(b"\0").decode("ascii", errors="ignore")
        virtual_address = struct.unpack_from("<I", data, offset + 12)[0]
        raw_size = struct.unpack_from("<I", data, offset + 16)[0]
        raw_offset = struct.unpack_from("<I", data, offset + 20)[0]
        yield name, virtual_address, raw_offset, raw_size


def find_dialogue_hook_module_offset(executable_path):
    """Localiza por assinatura a instrução executada ao iniciar tags de diálogo ED6."""
    with open(executable_path, "rb") as stream:
        data = stream.read()
    try:
        _name, section_rva, raw_offset, raw_size = next(
            section for section in _pe_sections(data) if section[0] == ".text"
        )
    except StopIteration as exc:
        raise ValueError("Seção .text não encontrada no executável Falcom") from exc

    text = data[raw_offset : raw_offset + raw_size]
    executable_name = os.path.basename(executable_path).lower()
    if executable_name.startswith("ed6_win3"):
        patterns = (TEXT_ROUTINE_PATTERNS["3rd"],)
    elif executable_name.startswith("ed6_win2"):
        patterns = (TEXT_ROUTINE_PATTERNS["sc"],)
    elif executable_name.startswith("ed6_win"):
        patterns = (TEXT_ROUTINE_PATTERNS["fc"],)
    else:
        patterns = tuple(TEXT_ROUTINE_PATTERNS.values())

    matches = [match for pattern in patterns for match in pattern.finditer(text)]
    if len(matches) != 1:
        raise ValueError(
            "Assinatura de diálogo Falcom incompatível: "
            f"esperado 1 resultado, encontrado(s) {len(matches)}"
        )

    signature_start = matches[0].start()
    search_start = max(0, signature_start - 0x1000)
    prologues = list(TEXT_FUNCTION_PROLOGUE.finditer(text, search_start, signature_start))
    if not prologues:
        raise ValueError("Entrada da função de texto Falcom não encontrada")
    # A função recebe a string inteira em [esp+4] antes de interpretar tags.
    return section_rva + prologues[-1].start()


def build_dialogue_hook_code(executable_path):
    module_offset = find_dialogue_hook_module_offset(executable_path)
    executable_name = os.path.basename(executable_path)
    return f"HSFN932#4@{module_offset:X}:{executable_name}"


def write_textractor_config(game_dir, executable_path, textractor_dir):
    """Grava uma configuração mínima: um hook validado e clipboard."""
    game_dir = os.path.abspath(game_dir)
    executable_path = os.path.abspath(executable_path)
    textractor_dir = os.path.abspath(textractor_dir)
    os.makedirs(textractor_dir, exist_ok=True)
    hook_code = build_dialogue_hook_code(executable_path)

    with open(os.path.join(textractor_dir, "SavedGames.txt"), "w", encoding="utf-8") as stream:
        stream.write(executable_path)
    with open(os.path.join(textractor_dir, "SavedExtensions.txt"), "w", encoding="utf-8") as stream:
        stream.write("")
    with open(os.path.join(textractor_dir, "SavedHooks.txt"), "w", encoding="utf-8") as stream:
        stream.write(f"{executable_path} , {hook_code} , |0:0:{hook_code}\n")
    return hook_code
