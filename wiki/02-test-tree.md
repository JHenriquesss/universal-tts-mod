# Test Tree

## Trunk
- Command: `python -m unittest discover -s tests`
- Latest evidence: `Ran 88 tests in 6.003s OK` from Phase 19 close.
- Batch script: `run_tests.bat` wraps cleaner + integration tests but trunk evidence uses direct unittest discovery.

## Branches
| Branch | File | Asserts |
|---|---|---|
| Text cleaner | `tests/test_cleaner.py` | Ren'Py tag removal, escapes, whitespace, punctuation, slang/apostrophes, mojibake, default/custom pronunciation overrides, hot-path guard. |
| Socket protocol | `tests/test_server.py` | Mock backend starts on isolated port; accepts `SET_SPEED`, `STOP`, text, `QUIT`; ignores empty cleaned text; no real Kokoro/audio dependency. |
| Ren'Py startup/lifecycle | `tests/test_renpy_startup.py` | Auto-connect deferred; safe notify helper; `tts_kill()` sends `QUIT`, closes socket, waits/escalates process; bad socket reference cleared. |
| Lightness/package | `tests/test_lightness_cleanup.py` | No unsupported Edge/Sherpa deps/classes/docs; mock only via env; no deploy artifacts under `renpy_mod`. |
| Choice hints core | `tests/test_choice_hints_core.py` | Curated overrides generated; Unicode aliasing; label-scoped lookup; display caption stripping; hint color formatting; public Ren'Py screen names preserved. |
| Extractor CLI | `tests/test_extract_menu_hints.py` | Byte fixture extraction, generated output shape, CLI path resolution, no personal hardcoded paths. |
| Installer | `tests/test_install_tts_mod.py` | Nested Ren'Py root detection; TTS-only copy plan; artifact/choice-overlay exclusion; dry-run does not write. |
| Backend smoke check | `tests/test_smoke_check.py` | Mock backend process starts, accepts command, logs context/events, exits via `QUIT`; timeout kills child. |
| Release manifest/archive | `tests/test_release_manifest.py` | Manifest sources/destinations match installer; forbidden files excluded; archive zip names exactly match manifest; missing output parent rejected; package/version metadata; default versioned archive path. |
| README/wiki docs | `tests/test_readme_deploy_docs.py`, `tests/test_wiki_state.py` | Deploy checklist, voice/protocol docs, extractor CLI examples, TTS-only workflow, release hygiene/archive docs, final release checklist, wiki open-thread state. |
| Release artifact verification | Phase 19 checklist commands | Full suite, `smoke_check.py`, `release_manifest.py --check`, default archive generation, zip contents exactly match manifest, forbidden artifacts absent. |

## Test Invariants
- No skipped tests.
- Mock backend selected only by `TTS_ENGINE=mock`.
- Test subprocesses set `PYTHONDONTWRITEBYTECODE=1` and `TTS_LOG_DIR` tempdir to avoid dirtying deployable `renpy_mod/`.
- Release/archive tests inspect final zip artifact names; no installed game folder mutation.

## Cross-Refs
- Architecture: [[01-architecture.md#architecture]]
- Phases: [[03-phases.md#phases]]
