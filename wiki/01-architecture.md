# Architecture

## Runtime Shape
- Ren'Py side: `renpy_mod/tts_mod.rpy`; registers callbacks/hotkeys, starts/connects backend after Ren'Py init, sends socket commands.
- Backend side: `renpy_mod/tts_server.py`; TCP server on `127.0.0.1:${TTS_PORT:-5050}`; accepts `STOP`, `SET_SPEED:<value>`, `SET_VOICE:<voice>`, `SET_LANG:<lang>`, `HELLO`, `QUIT`, text lines.
- Backend instance identity: every backend instance publishes a random token and binds exclusively (`SO_EXCLUSIVEADDRUSE` on Windows, `SO_REUSEADDR` on POSIX), so a leftover instance holding the port makes the new backend fail fast with an explicit error instead of silently sharing it; a client asks `HELLO` and receives `HELLO:<token>`.
- Engine side: `renpy_mod/tts_engines.py`; supported runtime path is `KokoroEngine`; `MockEngine` test-only via `TTS_ENGINE=mock`.
- Text cleanup: `renpy_mod/text_cleaner.py`; removes Ren'Py tags/control text, normalizes punctuation/slang/mojibake, applies default or caller-provided pronunciation overrides.
- Choice overlay: `renpy_mod/zzz_mod_choice_consequences.rpy`; Ren'Py UI/screens; delegates core lookup/formatting and additive caption construction to `renpy_mod/choice_hints_core.py`.
- Choice hint extractor: `extract_menu_hints_generic.py`; CLI accepts `--game-path` or explicit `--archive`/`--output`, extracts hints from bytes via indentation-stack menu parser, renders `GENERATED_CHOICE_HINTS` file.
- Falcom ED6 side: `falcom_mod/falcom_text_hook.py` + `falcom_mod/falcom_win32_runtime.py` + `falcom_mod/falcom_voice_map.py`; hooks TextractorCLI/memory/clipboard for Trails in the Sky and sends multi-voice commands to the TCP TTS server.
- Unity side: `unity_mod/unity_text_hook.py` + `unity_mod/unity_voice_map.py`; monitors BepInEx/XUnity logs or clipboard and bridges Unity games to the TCP TTS server.
- Installer: `install_tts_mod.py`; detects engine (`renpy`, `falcom`, `unity`), copies TTS-only files by default for Ren'Py, optional choice overlay only via explicit flag.
- Smoke check: `smoke_check.py`; starts backend with `TTS_ENGINE=mock`, isolated port/log dir, sends socket command + `QUIT`, cleans up child process.
- Release manifest/archive: `release_manifest.py`; read-only manifest check, package/version metadata, default versioned TTS-only zip builder using manifest destinations.

## Backend Lifecycle
- Auto-connect deferred via `config.start_callbacks`; no direct `tts_connect(quiet=True)` inside init block.
- Notifications routed through safe helper; direct `renpy.notify(...)` avoided in mod code.
- `tts_kill()` sends `QUIT\n`, closes socket, terminates process, waits briefly, escalates to kill on timeout.
- Broken socket health checks clear `tts_state.sock` before reconnect.

## Packaging Boundary
- TTS-only deploy payload: `game/tts_mod.rpy`, `game/tts_server.py`, `game/tts_engines.py`, `game/text_cleaner.py`, root `run_backend.bat`.
- `install_tts_mod.py --game-folder <folder>` copies same payload into detected game root; default excludes choice overlay.
- `release_manifest.py --check` verifies payload sources exist without mutating game folders.
- `release_manifest.py --archive <zip>` writes zip entries exactly matching manifest destinations; `--archive` without value writes default `renpy-tts-mod-1.0.0.zip`.
- Generated release artifact: `renpy-tts-mod-1.0.0.zip`; TTS-only; verified entries `game/text_cleaner.py`, `game/tts_engines.py`, `game/tts_mod.rpy`, `game/tts_server.py`, `run_backend.bat`.
- Final release checklist in README requires full suite, `smoke_check.py`, `release_manifest.py --check`, `release_manifest.py --archive`, exact manifest-content guarantee, artifact exclusions.
- Choice overlay files only if using choice-hint feature: `choice_hints_core.py`, `zzz_mod_choice_consequences.rpy`, generated hints.
- Tests enforce no `renpy_mod/__pycache__`, `*.pyc`, `*.log`, or `tts_ready.txt` artifacts.
- Requirements/install path: Kokoro, sounddevice, soundfile, numpy. Edge/Sherpa/cache paths removed.

## Configuration
- `TTS_ENGINE = "kokoro"`; tests set `TTS_ENGINE=mock`.
- `TTS_LANG = "en"` passed to backend.
- `TTS_PORT = 5050`; tests isolate with free ephemeral port.
- `TTS_VOICE = "af_heart"`; runtime can change voice with `SET_VOICE:<voice>`.
- Speed stored in `persistent.tts_speed`; runtime sends `SET_SPEED:<value>`.

## Cross-Refs
- Tests: [[02-test-tree.md#test-tree]]
- Decisions: [[04-decisions.md#decisions]]
- Glossary: [[05-glossary.md#glossary]]
