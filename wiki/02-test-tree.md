# Test Tree

## Trunk
- Command: `python -m unittest discover -s tests`
- Latest evidence: `Ran 368 tests in 8.9s OK` (2026-10-19, after the P4 client split block).
- Batch script: `run_tests.bat` wraps cleaner + integration tests but trunk evidence uses direct unittest discovery.
- The recorded count is asserted by `tests/test_wiki_state.py` against the real discovery count, so this page cannot silently go stale.
- The recorded count is the count of the **committed** trunk: copy it from the output of
  the run itself, never add up the new tests by hand. The count was overstated by
  arithmetic between the P2 and P3 blocks and the guard was red the whole time.
- The guard compares against the working tree, so uncommitted tests make it fail locally
  until they are committed together with the new count.

## Branches
| Branch | File | Asserts |
|---|---|---|
| Text cleaner | `tests/test_cleaner.py` | Ren'Py tag removal, escapes, whitespace, punctuation, slang/apostrophes, mojibake (including the truncated `â€` that must not become an ellipsis), gerunds with the dropped `g` (`thinkin'` -> `thinking`, `ain'`/`notin'` left alone), Falcom tags that must not eat a `#` inside a word, default/custom pronunciation overrides, hot-path guard. |
| Falcom text cleaner | `tests/test_falcom_cleaner.py` | Falcom-specific portrait tags and pronunciation overrides. |
| Socket protocol | `tests/test_server.py` | Mock backend starts on isolated port; accepts `SET_SPEED`, `SET_VOICE`, `SET_LANG`, `STOP`, `HELLO`, text, `QUIT`; ignores empty cleaned text; no real Kokoro/audio dependency. |
| Backend instance identity | `tests/test_server.py` | Token published per instance, `HELLO` handshake, busy port fails fast with an actionable error, tokens differ between backends, token mismatch is logged. |
| Protocol rules | `tests/test_tts_protocol.py` | `STOP` preserves voice/speed/language, discarded tasks are released, preserved configuration stays pending for the worker. |
| Client voice layer | `tests/test_tts_client_voice.py` | Speaker name cleanup, store context names, thought suffix, voice map hits, protagonist/partner aliases, male/female pools. |
| Client state | `tests/test_tts_client_state.py` | State restored from the persistent, voice map loaded from the game folder, the voice map surviving a save and load. |
| Client rules | `tests/test_tts_client_rules.py` | Phone callback wrappers, save compatibility hook, display hook, auto-advance timeout and native voice rules, speed/auto/audio commands. |
| Client layout | `tests/test_tts_client_layout.py` | The mod stays under the file size limit, its python blocks compile, the public client API stays available, every imported client module ships with the mod. |
| Ren'Py startup/lifecycle | `tests/test_renpy_startup.py` | Auto-connect deferred; safe notify helper; `tts_kill()` sends `QUIT`, closes socket, waits/escalates process; bad socket reference cleared; instance token captured and mismatched instance rejected. |
| Auto-advance | `tests/test_auto_advance.py` | Auto-forward on playback end, user interaction resets, no afm callback blocking. |
| Cache and multi-voice | `tests/test_tts_cache_and_multivoice.py` | Cache key and storage, cache pruning during the session, model version in the cache key, Falcom portrait voice map, single `stop()` and queue drain. |
| Lightness/package | `tests/test_lightness_cleanup.py` | No unsupported Edge/Sherpa deps/classes/docs; mock only via env; no deploy artifacts under `renpy_mod`; `qwen_voice_pro` kept as a labelled spike out of the requirements, the installer and the CI. |
| Choice hints core | `tests/test_choice_hints_core.py` | Curated overrides generated; Unicode aliasing; label-scoped lookup; display caption stripping; hint color formatting; public Ren'Py screen names preserved. |
| Extractor CLI | `tests/test_extract_menu_hints.py` | Byte fixture extraction, generated output shape, CLI path resolution, nested menus, no personal hardcoded paths. |
| Installer | `tests/test_install_tts_mod.py` | Nested Ren'Py root detection; TTS-only copy plan; artifact/choice-overlay exclusion; dry-run does not write. |
| Falcom installer | `tests/test_falcom_installer.py` | Falcom engine detection; Textractor runtime preflight fails fast when missing; install plan and copy with a hermetic runtime. |
| Falcom hook | `tests/test_falcom_hook.py` | Textractor hook, duplicate/fragment detection, multi-voice selection, speed hack. |
| Falcom launcher | `tests/test_falcom_launcher.py` | Supervisor owns backend/game/bridge processes and only stops what it created. |
| Falcom textractor | `tests/test_falcom_textractor.py` | Executable signature scan and Textractor configuration writing. |
| RPG Maker MZ mod | `tests/test_rpgmaker_mz_mod.py` | Plugin JS contract, plugin registration, voice map wiring. |
| Voice maps | `tests/test_*_voice_map.py` (10 files) | Per-game speaker-to-voice maps: after_the_fall, baking_with_chocolate, being_super, cockham, femboy_sorority, grandmas_house, milf_obsession, much_bigger_than_my_boyfriend, shadows_of_trust, the_home_of_pleasure, university_of_problems. |
| Backend smoke check | `tests/test_smoke_check.py` | Mock backend process starts, accepts command, logs context/events, exits via `QUIT`; timeout kills child. |
| Release manifest/archive | `tests/test_release_manifest.py` | Manifest sources/destinations match installer; forbidden files excluded; archive zip names exactly match manifest; missing output parent rejected; package/version metadata; default versioned archive path. |
| README/wiki docs | `tests/test_readme_deploy_docs.py`, `tests/test_wiki_state.py` | Deploy checklist, voice/protocol docs, extractor CLI examples, TTS-only workflow, release hygiene/archive docs, final release checklist, wiki open-thread state, and code-derived guards for the supported engines and the protocol commands. |
| Release artifact verification | Phase 19 checklist commands | Full suite, `smoke_check.py`, `release_manifest.py --check`, default archive generation, zip contents exactly match manifest, forbidden artifacts absent. |

## Test Invariants
- No skipped tests.
- Mock backend selected only by `TTS_ENGINE=mock`.
- Test subprocesses set `PYTHONDONTWRITEBYTECODE=1` and `TTS_LOG_DIR` tempdir to avoid dirtying deployable `renpy_mod/`.
- Release/archive tests inspect final zip artifact names; no installed game folder mutation.

## Cross-Refs
- Architecture: [[01-architecture.md#architecture]]
- Phases: [[03-phases.md#phases]]
