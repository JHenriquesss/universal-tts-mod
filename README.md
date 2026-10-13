# Universal TTS Mod (Ren'Py + Unity + Falcom ED6 + RPG Maker MZ) - Kokoro Socket Backend

Reads dialogue aloud in real time using a local Kokoro TTS backend. The game-side mod sends dialogue over a local TCP socket to avoid blocking the game UI while audio is generated.

Supports **Ren'Py**, **Unity**, **RPG Maker MZ**, with experimental **Falcom ED6 (Trails in the Sky FC / SC / the 3rd)** integration.

## Current Architecture

- `renpy_mod/tts_mod.rpy`: Ren'Py client integration, hotkeys, dialogue callback.
- `renpy_mod/tts_server.py`: Local socket server on `127.0.0.1:5050` by default.
- `renpy_mod/tts_engines.py`: Kokoro playback engine plus test mock (`TTS_VOICE = "af_heart"`).
- `renpy_mod/text_cleaner.py`: Removes tags/control text and normalizes punctuation before speech.
- `unity_mod/KokoroTtsPlugin.dll`: Unity BepInEx plugin C# assembly for capturing UI.Text and TextMeshPro dialogue.
- `rpgmaker_mz_mod/TTSModMZ.js`: RPG Maker MZ plugin connecting to the Kokoro TTS server over NW.js TCP socket.
- `falcom_mod/falcom_textractor.py`: Finds the full-dialogue ED6 hook by executable signature and writes a clean Textractor configuration.
- `falcom_mod/falcom_text_hook.py`: Reads only the private UTF-16 output pipe of `TextractorCLI.exe`, filters duplicate captures, and sends dialogue to the TTS backend.
- `falcom_mod/falcom_launcher.py`: Owns the backend, game, and private Textractor bridge processes and captures their console logs.
- `falcom_mod/JOGAR_COM_TTS.bat`: 1-click launcher for the Trails in the Sky ED6 games.
- `install_tts_mod.py`: Universal installer script with automatic engine detection (Ren'Py vs Unity vs Falcom vs RPG Maker MZ).

### Required files

- `tts_mod.rpy`
- `tts_server.py`
- `tts_engines.py`
- `text_cleaner.py`

### Optional choice overlay files

- `choice_hints_core.py`
- `zzz_mod_choice_consequences.rpy`
- `zzz_mod_choice_hints_generated.rpy`

Protocol commands sent to the backend:

- `STOP`: Stop current playback and clear queued speech.
- `SET_SPEED:<value>`: Update speech speed.
- `SET_VOICE:<voice>`: Update Kokoro voice for future speech (default `TTS_VOICE = "af_heart"`).
- any other non-empty line: Clean and speak that dialogue line.
- `QUIT`: Shut down the backend.

## Installation

### Automatic Installer (Recommended)

Run the universal installer on any game folder:

```bat
python install_tts_mod.py --game-folder "path\to\GameFolder"
```

The installer detects whether the game is **Ren'Py**, **Unity**, **RPG Maker MZ**, or **Falcom (Trails in the Sky)** automatically:
- **Ren'Py**: Copies `.rpy` scripts into `game/` and helper backend.
- **Unity**: Installs **BepInEx 5** framework and `KokoroTtsPlugin.dll` into `BepInEx/plugins/`.
- **RPG Maker MZ**: Copies backend and launcher, installs `TTSModMZ.js` in `js/plugins/`, registers the plugin in `js/plugins.js`, and configures `voice_map.json`.
- **Falcom ED6**: Copies the backend and launcher, installs `TextractorCLI.exe` and its runtime in `tts_textractor`, and generates the correct dialogue hook automatically from the installed executable.

## TTS-Only Install And Run

1. Run `INSTALAR_TTS_MOD.bat` or run:
   ```bat
   python install_tts_mod.py --game-folder "path\to\GameFolder"
   ```
2. Verify backend with:
   ```bat
   python smoke_check.py
   ```
3. Run `run_backend.bat` in the target game root folder (or use `JOGAR_COM_TTS.bat` on Falcom games).
4. Launch the game.
5. In game, press `v` to connect/reconnect (check `game/tts_server.log` if needed).

For the Falcom ED6 games, the same installation and launcher workflow applies to:

- **Trails in the Sky FC**
- **Trails in the Sky SC**
- **Trails in the Sky the 3rd**

Run the installer against that game's own root folder, then start it with the generated `JOGAR_COM_TTS.bat`. `falcom_textractor.py` regenerates the correct dialogue hook automatically for the installed executable, including the supported ED6 engine variants, so manual hook searches or Textractor configuration should not be needed.

The Falcom bridge does not use the Windows clipboard. It receives only the private output of `TextractorCLI.exe`, so text copied or typed in a browser or another application cannot be sent to TTS. The `falcom_launcher.py` supervisor records launcher output in `tts_backend_console.log` and bridge diagnostics in `falcom_text_hook.log`; it stops only the processes it created when the game exits.

## Choice Hint Extraction

Extract choice hints from script archives:

```bat
python extract_menu_hints_generic.py --game-path "path\to\game" --output "zzz_mod_choice_hints_generated.rpy"
python extract_menu_hints_generic.py --archive "path\to\archive.rpa" --output "zzz_mod_choice_hints_generated.rpy"
```

## Backend Smoke Check

Test backend startup and synthesis without opening a game:

```bat
set TTS_ENGINE=mock
python smoke_check.py
```
This check does not require kokoro or GPU to pass when running with mock engine.

## Release Hygiene

Check release directory cleanliness:

```bat
python release_manifest.py --check
```

## Release Archives

Create versioned release archives for distribution:

```bat
python release_manifest.py --archive
```
This produces `tts_mod_release.zip` and versioned archive `renpy-tts-mod-1.0.0.zip`.

## Final Release Checklist

1. `python -m unittest discover -s tests` passes completely.
2. `python smoke_check.py` succeeds in mock mode.
3. `python release_manifest.py --check` confirms exactly matches the release manifest.
4. `python release_manifest.py --archive` creates clean TTS-only zip without generated runtime test artifacts.

## Release Status

TTS-only release work is complete. Distribution package is available as `renpy-tts-mod-1.0.0.zip`. The optional choice overlay remains opt-in.

## Tests

Run the test suite with:

```bat
python -m unittest discover -s tests
```
