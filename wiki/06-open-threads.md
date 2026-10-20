# Open Threads

## Known Follow-Ups
- Choice screen override remains global `screen choice(items)`; native `kwargs["hint"]` and `dialogueTextOutlines` are preserved additively via `build_additive_button_caption`.
- TTS-only release work is complete; optional choice overlay remains opt-in.
- No active DV carry-over after Phase 21.
- Code review 2026-10 filed as [[07-review-2026-10.md#revisão-de-código--2026-10]]: Falcom Textractor preflight (Falcom-only), socket instance-token + `SO_EXCLUSIVEADDRUSE` for backend-stability, cache pruning during session, `SET_LANG` preserved on `STOP`, and coupled wiki+test update to stop the doc drift.
- P0 (Falcom Textractor preflight), P1 (backend instance token + fail-fast port binding + cache pruning during the session) and the whole P2 group (shared protocol module, `SET_LANG` preserved on `STOP`, `task_done` on the error path, `MODEL_VERSION` in the cache key, wiki+test coupling with code-derived guards, placeholder files removed) were implemented on 2026-10-19. The P3 and P4 items of the review remain open.
- The wiki/test drift is currently *pinned by a green test*: `tests/test_wiki_state.py` asserts `unity_mod/unity_text_hook.py` in the architecture page and `Ran 88 tests` in the test tree, both stale. Doc and test must change in the same commit.

## Closed Bugs/Risks
- Init-phase `renpy.notify` crash risk mitigated by deferred start callback and safe notify helper.
- Stale pipe/cache/Edge docs/tests removed from main path.
- Port collision risk reduced with `TTS_PORT` and isolated test ports.
- Generated deploy artifacts blocked by tests.
- Extractor hardcoded-path risk resolved by `extract_menu_hints_generic.py` CLI.
- Backend hardcoded voice risk resolved by `TTS_VOICE` and `SET_VOICE`.
- Stale GrandmasHouse optional overlay/log/ready/pycache artifacts removed during Phase 11 TTS-only install.
- Backend lifecycle smoke risk reduced by `smoke_check.py` mock-engine command/QUIT test.
- Release package drift reduced by `release_manifest.py --check` and exact-manifest archive tests.
- Untraceable release zip risk reduced by default versioned `renpy-tts-mod-1.0.0.zip` naming.
- Release process omission risk reduced by final README checklist.
- Socket test flakiness reduced by ready-file polling, richer setup diagnostics, and repeated focused test evidence.
- Release artifact existence/contents verified by generated `renpy-tts-mod-1.0.0.zip` matching manifest exactly.
- Dead `_legacy_*` functions in `zzz_mod_choice_consequences.rpy` removed (reduced to <250 lines) and additive native hint preservation hardened via `build_additive_button_caption`.
- Monolithic `falcom_text_hook.py` decomposed into `falcom_text_hook.py` (<500 lines) and `falcom_win32_runtime.py` (<500 lines), with `falcom_voice_map.py` and `falcom_win32_runtime.py` included in `install_tts_mod.py`.

## Cross-Refs
- Phases: [[03-phases.md#phases]]
- Decisions: [[04-decisions.md#decisions]]
