"""Checagens previas do instalador: falham antes de copiar um mod que nao funcionaria.

Cada engine tem uma dependencia que o instalador nao consegue suprir sozinho
(o runtime do Textractor no Falcom, um jogo Unity Mono x64 para o BepInEx 5).
Sem estas checagens a instalacao "concluia" com sucesso e o jogo ficava mudo.
"""

import os

# A engine Falcom depende do runtime x86 do Textractor, que e um binario externo
# grande e de terceiros: nao e versionado neste repositorio.
TEXTRACTOR_REQUIRED_FILES = ("TextractorCLI.exe",)


class TextractorRuntimeMissing(ValueError):
    """Runtime externo do Textractor ausente ou incompleto (engine Falcom)."""


def validate_textractor_runtime(runtime_dir):
    """
    Valida o runtime do Textractor exigido pela engine Falcom.

    Levanta TextractorRuntimeMissing com orientacao acionavel quando o runtime
    nao esta disponivel, em vez de deixar a instalacao "concluir" com sucesso e
    produzir um jogo sem a ponte de dialogo.
    """
    if not os.path.isdir(runtime_dir):
        raise TextractorRuntimeMissing(
            "Runtime do Textractor ausente em: {}. A engine Falcom exige o runtime "
            "x86 do Textractor 5.2.0, que e uma dependencia externa e nao acompanha "
            "este repositorio. Coloque o runtime nessa pasta (ou informe "
            "--textractor-runtime) e execute o instalador novamente.".format(runtime_dir)
        )

    missing = [
        name
        for name in TEXTRACTOR_REQUIRED_FILES
        if not os.path.isfile(os.path.join(runtime_dir, name))
    ]
    if missing:
        raise TextractorRuntimeMissing(
            "Runtime do Textractor incompleto em: {}. Arquivo(s) obrigatorio(s) "
            "ausente(s): {}. Reinstale o runtime x86 do Textractor 5.2.0 nessa "
            "pasta (ou informe --textractor-runtime) e execute o instalador "
            "novamente.".format(runtime_dir, ", ".join(missing))
        )

    return runtime_dir


class UnsupportedUnityGame(ValueError):
    """Jogo Unity em que o pacote BepInEx 5 x64 do mod nao funciona."""


# Maquina do cabecalho PE (IMAGE_FILE_HEADER.Machine).
PE_MACHINE_X86 = 0x014C


def _pe_machine(path):
    """Arquitetura de um .exe/.dll do Windows, ou None se nao der para ler."""
    try:
        with open(path, "rb") as handle:
            header = handle.read(0x400)
        if header[:2] != b"MZ":
            return None
        offset = int.from_bytes(header[0x3C:0x40], "little")
        if header[offset:offset + 4] != b"PE\x00\x00":
            return None
        return int.from_bytes(header[offset + 4:offset + 6], "little")
    except (OSError, ValueError):
        return None


def validate_unity_target(game_root):
    """Recusa jogos Unity em que o BepInEx 5 x64 do mod nao carregaria.

    Sem esta checagem o instalador copiava o BepInEx em qualquer jogo Unity e
    "concluia" com sucesso, mas o plugin nunca carregava: o BepInEx 5 so roda
    em jogos Mono, o winhttp.dll do pacote e 64 bits e o plugin e compilado
    contra a API do BepInEx 5.
    """
    data_dirs = [name for name in os.listdir(game_root) if name.endswith("_Data")]
    if os.path.isfile(os.path.join(game_root, "GameAssembly.dll")) or any(
        os.path.isdir(os.path.join(game_root, name, "il2cpp_data")) for name in data_dirs
    ):
        raise UnsupportedUnityGame(
            "Jogo Unity IL2CPP em {}: o mod usa o BepInEx 5, que so funciona em jogos "
            "Unity Mono. Jogos IL2CPP nao sao suportados.".format(game_root)
        )
    if os.path.isfile(os.path.join(game_root, "BepInEx", "core", "BepInEx.Core.dll")):
        raise UnsupportedUnityGame(
            "O jogo em {} ja tem o BepInEx 6, e o plugin do mod e feito para o BepInEx 5. "
            "Remova o BepInEx 6 ou use outra copia do jogo.".format(game_root)
        )
    candidates = [os.path.join(game_root, "UnityPlayer.dll")] + [
        os.path.join(game_root, name[: -len("_Data")] + ".exe") for name in data_dirs
    ]
    machines = [_pe_machine(path) for path in candidates if os.path.isfile(path)]
    if PE_MACHINE_X86 in machines:
        raise UnsupportedUnityGame(
            "Jogo Unity de 32 bits em {}: o pacote BepInEx do mod e de 64 bits e nao "
            "carregaria nesse jogo.".format(game_root)
        )

