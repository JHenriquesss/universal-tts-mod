# Glossary

## Runtime Terms
- `tts_mod.rpy`: Ren'Py game-side integration script.
- `tts_server.py`: Python TCP backend that cleans/speaks received text.
- `KokoroEngine`: supported TTS runtime engine.
- `MockEngine`: test-only fake engine selected by `TTS_ENGINE=mock`.
- `TTS_PORT`: socket port env/config value; default `5050`.
- `TTS_LOG_DIR`: backend log/status output directory; tests point this to tempdir.
- `TTS_VOICE`: default Kokoro voice config, initially `af_heart`.

## Protocol Terms
- `STOP`: socket command; stop playback/clear queued speech.
- `SET_SPEED:<value>`: socket command; update speed in worker.
- `SET_VOICE:<voice>`: socket command; update voice in worker.
- `QUIT`: socket command; backend exits.
- Text line: any other non-empty cleaned line; queued for speech.

## Cleaner Terms
- Ren'Py tags: inline markup like `{i}`, `{w}`, `{nw}` removed before speech.
- Mojibake: UTF-8 bytes decoded as wrong encoding; cleaner normalizes common cases.
- Pronunciation override: regex pattern to replacement mapping passed to `TextCleaner.clean()`.

## Choice Overlay Terms
- Choice hints: mapped consequences shown beside Ren'Py menu choices.
- Generated hints: external `GENERATED_CHOICE_HINTS` dictionary from extractor.
- Curated hints: manual overrides in `CURATED_CHOICE_HINTS`; override generated entries.
- Unicode alias: normalized caption key for curly apostrophes/quotes.
- Extractor CLI: `extract_menu_hints_generic.py`; generates `zzz_mod_choice_hints_generated.rpy` from archive/script bytes.

## Install/Release Terms
- TTS-only install: default deploy path; required TTS files plus `run_backend.bat`; no choice overlay.
- Nested Ren'Py game root: inner folder containing `game/` and executable inside an outer release folder.
- Installer: `install_tts_mod.py`; copies TTS-only payload into detected game root; dry-run supported.
- Backend smoke check: `smoke_check.py`; mock-engine socket/process verification before game launch.
- Release manifest: `release_manifest.py` list of source files and target destinations for TTS-only payload.
- Release archive: zip built from release manifest; entries are `game/*` plus root helper.
- Package/version metadata: `PACKAGE_NAME` + `RELEASE_VERSION` in `release_manifest.py`; used for default archive filename, not runtime config.
- Final release checklist: README section tying together full suite, smoke check, manifest check, archive build, exact manifest contents, artifact exclusions.
- Generated release artifact: `renpy-tts-mod-1.0.0.zip`; manifest-verified TTS-only zip produced in Phase 19.
- Backend ready status: `tts_ready.txt` `READY|...`; test harness waits for it before socket connect.

## Cross-Refs
- Architecture: [[01-architecture.md#architecture]]
- Test tree: [[02-test-tree.md#test-tree]]
