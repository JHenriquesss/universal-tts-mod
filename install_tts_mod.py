import argparse
import os
import shutil
from dataclasses import dataclass


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RENPY_MOD_DIR = os.path.join(PROJECT_ROOT, "renpy_mod")
UNITY_MOD_DIR = os.path.join(PROJECT_ROOT, "unity_mod")
BEPINEX_PACK_DIR = os.path.join(UNITY_MOD_DIR, "bepinex_pack")

RENPY_REQUIRED_GAME_FILES = (
    "tts_mod.rpy",
    "tts_server.py",
    "tts_engines.py",
    "text_cleaner.py",
)

RENPY_OPTIONAL_CHOICE_FILES = (
    "choice_hints_core.py",
    "zzz_mod_choice_consequences.rpy",
    "zzz_mod_choice_hints_generated.rpy",
)

ROOT_HELPER_FILES = ("run_backend.bat",)
FORBIDDEN_NAMES = {"__pycache__", "tts_server.log", "tts_ready.txt"}


@dataclass(frozen=True)
class CopyEntry:
    source: str
    destination: str


@dataclass(frozen=True)
class InstallResult:
    game_root: str
    engine: str
    planned: list
    installed: list
    skipped: list


def detect_game_engine(game_folder):
    """
    Detects whether target game folder is Ren'Py or Unity.
    """
    root = os.path.abspath(game_folder)
    for current, dirnames, filenames in os.walk(root):
        # Unity check
        if any(d.endswith("_Data") for d in dirnames) or "UnityPlayer.dll" in filenames or "MonoBleedingEdge" in dirnames:
            return "unity", current
        # Ren'Py check
        if "game" in dirnames and any(name.lower().endswith(".exe") for name in filenames):
            return "renpy", current

    # Default fallback check
    if os.path.exists(os.path.join(root, "game")):
        return "renpy", root
    return "unknown", root


def build_install_plan(game_folder, with_choice_overlay=False):
    engine, game_root = detect_game_engine(game_folder)
    entries = []

    if engine == "renpy":
        game_dir = os.path.join(game_root, "game")
        for filename in RENPY_REQUIRED_GAME_FILES:
            entries.append(_copy_entry(RENPY_MOD_DIR, filename, os.path.join(game_dir, filename)))

        if with_choice_overlay:
            for filename in RENPY_OPTIONAL_CHOICE_FILES:
                source = os.path.join(RENPY_MOD_DIR, filename)
                if os.path.exists(source):
                    entries.append(CopyEntry(source, os.path.join(game_dir, filename)))

        for filename in ROOT_HELPER_FILES:
            entries.append(_copy_entry(RENPY_MOD_DIR, filename, os.path.join(game_root, filename)))

    elif engine == "unity":
        # 1. Servidor backend na raiz do jogo
        for filename in ("tts_server.py", "tts_engines.py", "text_cleaner.py", "run_backend.bat"):
            source = os.path.join(RENPY_MOD_DIR, filename)
            if os.path.exists(source):
                entries.append(CopyEntry(source, os.path.join(game_root, filename)))

        # 2. Injetar BepInEx completo se ainda nao instalado no jogo
        if os.path.exists(BEPINEX_PACK_DIR):
            for root_dir, dirnames, filenames in os.walk(BEPINEX_PACK_DIR):
                for f in filenames:
                    src_path = os.path.join(root_dir, f)
                    rel_path = os.path.relpath(src_path, BEPINEX_PACK_DIR)
                    dst_path = os.path.join(game_root, rel_path)
                    entries.append(CopyEntry(src_path, dst_path))

        # 3. Plugin KokoroTtsPlugin.dll
        dll_plugin = os.path.join(UNITY_MOD_DIR, "KokoroTtsPlugin.dll")
        if os.path.exists(dll_plugin):
            plugin_dir = os.path.join(game_root, "BepInEx", "plugins")
            entries.append(CopyEntry(dll_plugin, os.path.join(plugin_dir, "KokoroTtsPlugin.dll")))
        else:
            # Fallback para o arquivo .cs se a DLL nao estiver compilada
            src_plugin = os.path.join(UNITY_MOD_DIR, "src", "KokoroTtsPlugin.cs")
            if os.path.exists(src_plugin):
                plugin_dir = os.path.join(game_root, "BepInEx", "plugins")
                entries.append(CopyEntry(src_plugin, os.path.join(plugin_dir, "KokoroTtsPlugin.cs")))

    else:
        raise ValueError(f"Não foi possível identificar a engine do jogo em: {game_folder}")

    return engine, game_root, _validate_entries(entries)


def install_game(game_folder, with_choice_overlay=False, dry_run=False):
    engine, game_root, planned = build_install_plan(game_folder, with_choice_overlay=with_choice_overlay)
    installed = []

    if not dry_run:
        for entry in planned:
            os.makedirs(os.path.dirname(entry.destination), exist_ok=True)
            shutil.copy2(entry.source, entry.destination)
            installed.append(entry.destination)

    return InstallResult(game_root=game_root, engine=engine, planned=planned, installed=installed, skipped=[])


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Instalador Universal do Mod TTS (Ren'Py + Unity).")
    parser.add_argument("--game-folder", required=True, help="Caminho para a pasta do jogo.")
    parser.add_argument("--with-choice-overlay", action="store_true", help="Instalação de overlays de escolha (apenas Ren'Py).")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem escrever arquivos.")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = install_game(args.game_folder, with_choice_overlay=args.with_choice_overlay, dry_run=args.dry_run)

    action = "Simulou instalação de" if args.dry_run else "Instalado"
    print(f"[{result.engine.upper()}] {action} {len(result.planned)} arquivos em {result.game_root}")
    for entry in result.planned:
        print(f"  {os.path.basename(entry.source)} -> {entry.destination}")
    return 0


def _copy_entry(source_dir, filename, destination):
    source = os.path.join(source_dir, filename)
    if not os.path.exists(source):
        raise ValueError(f"Arquivo de origem ausente: {source}")
    return CopyEntry(source, destination)


def _validate_entries(entries):
    valid = []
    for entry in entries:
        name = os.path.basename(entry.source)
        if name in FORBIDDEN_NAMES or name.endswith(".pyc") or "tests" in entry.source.split(os.sep):
            continue
        valid.append(entry)
    return valid


if __name__ == "__main__":
    raise SystemExit(main())
