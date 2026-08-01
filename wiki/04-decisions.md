# Decisions

## 2026-06-07
| Phase | Decision | Why | Alternatives Rejected |
|---|---|---|---|
| 1 | Use current socket protocol as source of truth. | Code used TCP `127.0.0.1:5050`; stale tests/docs expected stdin/stdout/cache. | Restoring old pipe/cache protocol. |
| 1 | Defer auto-connect via Ren'Py start callback. | Traceback showed `renpy.notify` unsafe during init. | Direct `tts_connect(quiet=True)` in `init python`. |
| 1 | Add `TTS_PORT` configurability. | Multiple old backend processes can occupy `5050`; tests need isolation. | Hardcoded port in all contexts. |
| 2 | Make runtime Kokoro-only. | Edge/Sherpa classes/deps were nonfunctional/stale; lighter deploy path. | Keeping dummy multimotor claims. |
| 2 | Keep `MockEngine` but test-only. | Integration tests need no model/audio hardware. | Loading real Kokoro in tests. |
| 3 | Extract `choice_hints_core.py`. | Lookup/formatting needs Python tests independent of Ren'Py screen parsing. | Leaving 700+ line mixed UI/core file. |
| 3 | Preserve public screen names. | Ren'Py compatibility risk if `choice`, toolbar, overlay names change. | Renaming/replacing screens during refactor. |
| 4 | Make pronunciations overrideable. | Game-specific names should not be rebuilt inside `clean()` hot path; callers need custom maps. | Hardcoded inline dictionary only. |
| 5 | Graceful backend shutdown before kill. | Avoid stale backend processes/sockets; preserve safe escalation. | Immediate terminate/kill without `QUIT`/wait. |
| 7 | Make voice selection configurable. | Avoid hardcoded runtime voice; preserve `af_heart` as default config. | Hardcoded worker `af_heart`. |
| 9 | Convert extractor to CLI + functions. | Reuse across games; test without real archives or personal paths. | Hardcoded local Windows path script. |
| 11 | Default installer is TTS-only. | Choice overlay overrides global Ren'Py `screen choice(items)` and may conflict with games; user selected TTS-only for GrandmasHouse. | Installing optional overlay by default. |
| 11 | Installer accepts outer release folder and detects nested game root. | GrandmasHouse folders contain nested Ren'Py root; user should not identify inner path manually. | Requiring exact inner game root path. |
| 12 | Smoke check uses `TTS_ENGINE=mock`. | Verify socket/process lifecycle without Kokoro downloads or real audio hardware. | Using real Kokoro for smoke tests. |
| 14 | Release manifest is read-only source of package boundary. | Keep installer/docs/archive aligned; prevent runtime/generated artifact drift. | Ad hoc package copy lists. |
| 15 | Archive entries use install destinations. | Zip can be extracted/copied into game root directly. | Storing project source paths inside zip. |
| 16 | Keep release metadata in release tooling only. | Package/version identity needed for archives; runtime config must stay separate. | Duplicating `TTS_PORT`/`TTS_VOICE`/`TTS_ENGINE` in release metadata. |
| 17 | Final release checklist stays TTS-only and mock-validated. | Release can be verified without real Kokoro audio and without optional overlay risk. | Requiring real audio validation or default overlay packaging. |
| 18 | Wait for backend ready file before socket connect in tests. | Windows connect timing caused transient timeouts/resets; ready status is deterministic backend signal. | Blind connect loop as sole setup synchronization. |
| 19 | Generate release artifact from manifest, not ad hoc file list. | Ensures zip payload equals tested TTS-only package boundary. | Manual zip creation. |

## Cross-Refs
- Architecture: [[01-architecture.md#architecture]]
- Phases: [[03-phases.md#phases]]
