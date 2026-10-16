import sys
sys.dont_write_bytecode = True
import argparse
import os
import shutil
from dataclasses import dataclass


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RENPY_MOD_DIR = os.path.join(PROJECT_ROOT, "renpy_mod")
MOD_DIR = RENPY_MOD_DIR
UNITY_MOD_DIR = os.path.join(PROJECT_ROOT, "unity_mod")
FALCOM_MOD_DIR = os.path.join(PROJECT_ROOT, "falcom_mod")
RPGMAKER_MZ_MOD_DIR = os.path.join(PROJECT_ROOT, "rpgmaker_mz_mod")
TEXTRACTOR_RUNTIME_DIR = os.path.join(
    PROJECT_ROOT, "tools", "Textractor-5.2.0", "Textractor", "x86"
)
BEPINEX_PACK_DIR = os.path.join(UNITY_MOD_DIR, "bepinex_pack")

RENPY_REQUIRED_GAME_FILES = (
    "tts_mod.rpy",
    "tts_server.py",
    "tts_engines.py",
    "text_cleaner.py",
)
REQUIRED_GAME_FILES = RENPY_REQUIRED_GAME_FILES

RENPY_OPTIONAL_CHOICE_FILES = (
    "choice_hints_core.py",
    "zzz_mod_choice_consequences.rpy",
    "zzz_mod_choice_hints_generated.rpy",
)

ROOT_HELPER_FILES = ("run_backend.bat", "JOGAR_COM_TTS.bat", "jogar.bat")
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
    Detects whether target game folder is Ren'Py, Unity or Falcom (ED6 / Trails in the Sky).
    """
    root = os.path.abspath(game_folder)
    for current, dirnames, filenames in os.walk(root):
        # Falcom check (ED6 / Trails in the Sky)
        if any(f.lower().startswith("ed6_win") or f.lower().startswith("ed7_win") for f in filenames) or \
           any(f.upper().startswith("ED6_DT") or f.upper().startswith("ED7_DT") for f in filenames):
            return "falcom", current
        # Unity check
        if any(d.endswith("_Data") for d in dirnames) or "UnityPlayer.dll" in filenames or "MonoBleedingEdge" in dirnames:
            return "unity", current
        # RPG Maker MZ / MV check
        if "data" in dirnames and ("js" in dirnames or any(f.endswith(".json") for f in filenames)):
            if "rmmz_core.js" in filenames or any(f.lower() in ("system.json", "actors.json") for f in filenames):
                return "rpgmaker_mz", current
            if "package.json" in filenames:
                return "rpgmaker_mz", current
        # Ren'Py check
        if "game" in dirnames and any(name.lower().endswith(".exe") for name in filenames):
            return "renpy", current

    # Default fallback checks
    if os.path.exists(os.path.join(root, "data", "System.json")) or os.path.exists(os.path.join(root, "js", "rmmz_core.js")):
        return "rpgmaker_mz", root
    if os.path.exists(os.path.join(root, "game")):
        return "renpy", root
    return "unknown", root


def find_game_root(game_folder):
    """Retorna o diretório raiz detectado do jogo."""
    _engine, root = detect_game_engine(game_folder)
    return root


def build_install_plan(game_folder, with_choice_overlay=False, voice_map=None, choice_hints_file=None):
    engine, game_root = detect_game_engine(game_folder)
    entries = []

    if choice_hints_file:
        with_choice_overlay = True

    if engine == "renpy":
        game_dir = os.path.join(game_root, "game")
        for filename in RENPY_REQUIRED_GAME_FILES:
            entries.append(_copy_entry(RENPY_MOD_DIR, filename, os.path.join(game_dir, filename)))

        if with_choice_overlay:
            for filename in ("choice_hints_core.py", "zzz_mod_choice_consequences.rpy"):
                source = os.path.join(RENPY_MOD_DIR, filename)
                if os.path.exists(source):
                    entries.append(CopyEntry(source, os.path.join(game_dir, filename)))
            hints_source = choice_hints_file or os.path.join(RENPY_MOD_DIR, "zzz_mod_choice_hints_generated.rpy")
            if os.path.exists(hints_source):
                entries.append(CopyEntry(hints_source, os.path.join(game_dir, "zzz_mod_choice_hints_generated.rpy")))

        for filename in ROOT_HELPER_FILES:
            entries.append(_copy_entry(RENPY_MOD_DIR, filename, os.path.join(game_root, filename)))

        if voice_map and os.path.exists(voice_map):
            entries.append(CopyEntry(voice_map, os.path.join(game_dir, "voice_map.json")))
            entries.append(CopyEntry(voice_map, os.path.join(game_root, "voice_map.json")))

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

    elif engine == "falcom":
        # 1. Servidor backend na raiz do jogo
        for filename in ("tts_server.py", "tts_engines.py", "text_cleaner.py", "run_backend.bat"):
            source = os.path.join(RENPY_MOD_DIR, filename)
            if os.path.exists(source):
                entries.append(CopyEntry(source, os.path.join(game_root, filename)))

        # 2. Scripts e Hook do Falcom
        for filename in (
            "falcom_text_hook.py",
            "falcom_voice_map.py",
            "falcom_win32_runtime.py",
            "falcom_launcher.py",
            "falcom_textractor.py",
            "JOGAR_COM_TTS.bat",
            "sora_voice_generator.py",
        ):
            source = os.path.join(FALCOM_MOD_DIR, filename)
            if os.path.exists(source):
                entries.append(CopyEntry(source, os.path.join(game_root, filename)))

        # 3. Runtime x86 oficial do Textractor. Só a extensão de clipboard
        # é instalada; tradução e filtros externos não fazem parte do fluxo.
        excluded_configs = {
            "SavedGames.txt",
            "SavedHooks.txt",
            "SavedExtensions.txt",
            "Textractor.ini",
        }
        for root_dir, _dirnames, filenames in os.walk(TEXTRACTOR_RUNTIME_DIR):
            for filename in filenames:
                if filename in excluded_configs:
                    continue
                if filename.lower().endswith(".xdll"):
                    continue
                source = os.path.join(root_dir, filename)
                relative = os.path.relpath(source, TEXTRACTOR_RUNTIME_DIR)
                destination = os.path.join(game_root, "tts_textractor", relative)
                entries.append(CopyEntry(source, destination))

    elif engine in ("rpgmaker_mz", "rpgmaker"):
        # 1. Servidor backend na raiz do jogo
        for filename in ("tts_server.py", "tts_engines.py", "text_cleaner.py", "run_backend.bat"):
            source = os.path.join(RENPY_MOD_DIR, filename)
            if os.path.exists(source):
                entries.append(CopyEntry(source, os.path.join(game_root, filename)))

        # 2. Launcher JOGAR_COM_TTS.bat
        launcher_src = os.path.join(RPGMAKER_MZ_MOD_DIR, "JOGAR_COM_TTS.bat")
        if os.path.exists(launcher_src):
            entries.append(CopyEntry(launcher_src, os.path.join(game_root, "JOGAR_COM_TTS.bat")))

        # 3. Plugin JS em js/plugins/TTSModMZ.js
        plugin_src = os.path.join(RPGMAKER_MZ_MOD_DIR, "TTSModMZ.js")
        if os.path.exists(plugin_src):
            entries.append(CopyEntry(plugin_src, os.path.join(game_root, "js", "plugins", "TTSModMZ.js")))

        # 4. Mapa de vozes na raiz do jogo
        vmap_src = os.path.join(RPGMAKER_MZ_MOD_DIR, "voice_map.json")
        if os.path.exists(vmap_src):
            entries.append(CopyEntry(vmap_src, os.path.join(game_root, "voice_map.json")))

    else:
        raise ValueError(f"Não foi possível identificar a engine do jogo em: {game_folder}")

    return _validate_entries(entries)


def register_rpgmaker_mz_plugin(game_root):
    """
    Registra o plugin TTSModMZ no final do array $plugins em js/plugins.js,
    preservando com segurança todos os plugins existentes.
    """
    plugins_js_path = os.path.join(game_root, "js", "plugins.js")
    if not os.path.exists(plugins_js_path):
        return False

    with open(plugins_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "TTSModMZ" in content:
        return True

    idx = content.rfind("]")
    if idx == -1:
        return False

    prefix = content[:idx].rstrip()
    if prefix.endswith("["):
        entry = '\n{"name":"TTSModMZ","status":true,"description":"Universal Kokoro TTS Mod for RPG Maker MZ","parameters":{}}\n'
    else:
        entry = ',\n{"name":"TTSModMZ","status":true,"description":"Universal Kokoro TTS Mod for RPG Maker MZ","parameters":{}}\n'

    new_content = content[:idx].rstrip() + entry + content[idx:]
    with open(plugins_js_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def create_outer_launchers(outer_folder, inner_root):
    rel_path = os.path.relpath(inner_root, outer_folder)
    jogar_content = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'cd /d "%~dp0{rel_path}"\r\n'
        'if exist "jogar.bat" (\r\n'
        '    call "jogar.bat" %*\r\n'
        ') else (\r\n'
        f'    echo [ERRO] jogar.bat nao encontrado na subpasta {rel_path}.\r\n'
        '    pause\r\n'
        ')\r\n'
    )
    jogar_com_tts_content = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'cd /d "%~dp0{rel_path}"\r\n'
        'if exist "JOGAR_COM_TTS.bat" (\r\n'
        '    call "JOGAR_COM_TTS.bat" %*\r\n'
        ') else (\r\n'
        f'    echo [ERRO] JOGAR_COM_TTS.bat nao encontrado na subpasta {rel_path}.\r\n'
        '    pause\r\n'
        ')\r\n'
    )
    run_backend_content = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'cd /d "%~dp0{rel_path}"\r\n'
        'if exist "run_backend.bat" (\r\n'
        '    call "run_backend.bat" %*\r\n'
        ') else (\r\n'
        f'    echo [ERRO] run_backend.bat nao encontrado na subpasta {rel_path}.\r\n'
        '    pause\r\n'
        ')\r\n'
    )
    outer_jogar = os.path.join(outer_folder, "jogar.bat")
    outer_tts = os.path.join(outer_folder, "JOGAR_COM_TTS.bat")
    outer_backend = os.path.join(outer_folder, "run_backend.bat")
    with open(outer_jogar, "w", encoding="utf-8") as f:
        f.write(jogar_content)
    with open(outer_tts, "w", encoding="utf-8") as f:
        f.write(jogar_com_tts_content)
    with open(outer_backend, "w", encoding="utf-8") as f:
        f.write(run_backend_content)
    return [outer_jogar, outer_tts, outer_backend]


def install_game(
    game_folder,
    with_choice_overlay=False,
    dry_run=False,
    voice_map=None,
    choice_hints_file=None,
    default_voice=None,
):
    import re
    engine, game_root = detect_game_engine(game_folder)
    planned = build_install_plan(
        game_folder,
        with_choice_overlay=with_choice_overlay,
        voice_map=voice_map,
        choice_hints_file=choice_hints_file,
    )
    installed = []

    if not dry_run:
        for entry in planned:
            os.makedirs(os.path.dirname(entry.destination), exist_ok=True)
            shutil.copy2(entry.source, entry.destination)
            installed.append(entry.destination)

            if entry.destination.endswith(".rpy"):
                rpyc_target = entry.destination + "c"
                if os.path.exists(rpyc_target):
                    try:
                        os.remove(rpyc_target)
                    except Exception:
                        pass

            if default_voice and os.path.basename(entry.destination) == "tts_mod.rpy":
                with open(entry.destination, "r", encoding="utf-8") as f:
                    mod_code = f.read()
                mod_code = re.sub(
                    r'TTS_VOICE\s*=\s*["\'][^"\']+["\']',
                    f'TTS_VOICE = "{default_voice}"',
                    mod_code,
                    count=1,
                )
                with open(entry.destination, "w", encoding="utf-8") as f:
                    f.write(mod_code)

        if os.path.normpath(os.path.abspath(game_folder)) != os.path.normpath(game_root):
            outer_installed = create_outer_launchers(os.path.abspath(game_folder), game_root)
            installed.extend(outer_installed)
        else:
            parent = os.path.dirname(game_root)
            parent_name = os.path.basename(parent).lower()
            if parent and parent_name and parent_name not in ("games", "jogos", "steamapps", "common", ""):
                outer_installed = create_outer_launchers(parent, game_root)
                installed.extend(outer_installed)

        if engine in ("rpgmaker_mz", "rpgmaker"):
            register_rpgmaker_mz_plugin(game_root)

        if engine == "falcom":
            from falcom_mod.falcom_textractor import write_textractor_config

            executables = [
                name
                for name in os.listdir(game_root)
                if name.lower().startswith(("ed6_win", "ed7_win"))
                and name.lower().endswith(".exe")
            ]
            if not executables:
                raise ValueError("Executável Falcom não encontrado para configurar o Textractor")
            executable = next(
                (name for name in executables if "dx9" in name.lower()),
                executables[0],
            )
            textractor_dir = os.path.join(game_root, "tts_textractor")
            write_textractor_config(
                game_root,
                os.path.join(game_root, executable),
                textractor_dir,
            )

    return InstallResult(game_root=game_root, engine=engine, planned=planned, installed=installed, skipped=[])



def build_arg_parser():
    parser = argparse.ArgumentParser(description="Instalador Universal do Mod TTS (Ren'Py + Unity).")
    parser.add_argument("--game-folder", required=True, help="Caminho para a pasta do jogo.")
    parser.add_argument("--with-choice-overlay", action="store_true", help="Instalação de overlays de escolha (apenas Ren'Py).")
    parser.add_argument("--choice-hints-file", help="Caminho para arquivo customizado de hints geradas (habilita overlay de escolhas).")
    parser.add_argument("--voice-map", help="Caminho para arquivo voice_map.json customizado para o jogo.")
    parser.add_argument("--default-voice", help="Voz padrão para o narrador/MC no tts_mod.rpy (ex: am_onyx, af_heart).")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem escrever arquivos.")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = install_game(
        args.game_folder,
        with_choice_overlay=args.with_choice_overlay,
        dry_run=args.dry_run,
        voice_map=args.voice_map,
        choice_hints_file=args.choice_hints_file,
        default_voice=args.default_voice,
    )

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
