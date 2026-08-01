# Phases

## Current DV State
- Current phase: 19
- Step: closed
- Trunk: pass
- Evidence: `python -m unittest discover -s tests: Ran 88 tests in 6.003s OK; release artifact generated and manifest-verified`
- Source: `.dv-state.json`

## Closed Phases
| Phase | Name | Outcome | Scope | Tests |
|---|---|---|---|---|
| 1 | startup-safety-and-protocol-tests | ok | Deferred Ren'Py auto-connect; safe notify; socket protocol tests; README aligned. | 18 green |
| 2 | kokoro-only-lightness-cleanup | ok | Removed unsupported Edge/Sherpa deps/classes; isolated logs; blocked deploy artifacts. | 23 green |
| 3 | choice-overlay-refactor | ok | Added tested choice-hint core; overlay delegates lookup/display formatting; public screens preserved. | 30 green |
| 4 | configurable-pronunciation-overrides | ok | Moved cleaner constants to module scope; added optional pronunciation overrides. | 35 green |
| 5 | backend-shutdown-and-reconnect | ok | Added graceful `QUIT`, socket close, terminate wait, timeout kill checks. | 38 green |
| 6 | backend-diagnostics-and-status | ok | Added startup context, command event logs, bounded text previews, TTS status helper. | 42 green |
| 7 | configurable-voice-selection | ok | Added `TTS_VOICE`, `SET_VOICE`, selected voice worker state, voice diagnostics. | 45 green |
| 8 | install-and-deploy-checklist | ok | Added precise deploy checklist, optional choice overlay files, voice/protocol docs tests. | 50 green |
| 9 | menu-hints-extractor-cli | ok | Extractor CLI replaced hardcoded path with CLI args and byte-based extraction/render functions. | 55 green |
| 10 | extractor-docs-and-wiki | ok | Added extractor CLI README examples and updated wiki through Phase 10. | 59 green |
| 11 | game-install-script-and-grandmashouse-installs | ok | Added reusable TTS-only installer; installed into both GrandmasHouse nested roots; removed stale optional/artifact files. | 64 green |
| 12 | backend-runtime-smoke-check | ok | Added mock-engine backend smoke-check CLI/API with command/QUIT verification and timeout cleanup. | 67 green |
| 13 | user-facing-install-run-guide | ok | Added safe TTS-only install/run workflow: installer, smoke check, manual backend, in-game validation. | 70 green |
| 14 | release-package-hygiene | ok | Added read-only release manifest/check CLI with source/destination/exclusion tests. | 76 green |
| 15 | release-archive-command | ok | Added TTS-only zip archive command; archive entries exactly match manifest; forbidden artifacts excluded. | 80 green |
| 16 | release-versioning-and-distribution | ok | Added package/version metadata, default versioned archive path, optional CLI archive output, README versioned archive docs. | 84 green |
| 17 | release-notes-and-final-checklist | ok | Added final TTS-only release checklist: full suite, smoke check, manifest check, archive command, exact manifest contents, artifact exclusions. | 86 green |
| 18 | socket-server-test-flakiness | ok | Hardened socket tests with ready-file polling, diagnostics, cleanup, graceful socket shutdown; focused suite passed 5x. | 88 green |
| 19 | release-artifact-generation | ok | Generated `renpy-tts-mod-1.0.0.zip`; verified default archive contents exactly match TTS-only release manifest. | 88 green |

## Phase Carry-Overs
- Phase 1: none.
- Phase 2: none.
- Phase 3: none.
- Phase 4: none.
- Phase 5: none.
- Phase 6: none.
- Phase 7: none.
- Phase 8: none.
- Phase 9: none.
- Phase 10: none.
- Phase 11: none.
- Phase 12: none.
- Phase 13: none.
- Phase 14: none.
- Phase 15: none.
- Phase 16: none.
- Phase 17: none.
- Phase 18: none.
- Phase 19: none.

## Cross-Refs
- Test tree: [[02-test-tree.md#test-tree]]
- Decisions: [[04-decisions.md#decisions]]
- Open threads: [[06-open-threads.md#open-threads]]
