# Development notes

### DEV-2026-10-12-001 — Portable implementation and unresolved device prerequisites

**Date:** 2026-10-12  
**Time:** 08:55:25 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT  
**Status:** ACCEPTED  
**Type:** DECISION  

#### Problem

Documents only; no installed Arduino package, CLI or device access is established.

#### Context and Constraints

Prompt revision 1 and supplied standards govern. Hardware readiness remains false. Owner Michael Garcia; contact and project license pending confirmation.

#### Solutions Considered

Implement portable core plus fail-closed adapters; defer device-only verification. Rejected guessing wiring, callback coordinates or installed versions.

#### Trade-offs

Enables meaningful host validation; device integration and physical behavior require separate evidence.

#### Final Outcome

Preserve canonical metadata unchanged. Runtime YAML and schemas are separate from proposed architecture. Implement host C++ enforcement and Python dry-run; hardware enable always rejected until a verified board adapter exists.

#### Implementation Impact

config/runtime.yaml; schemas; firmware; src; README.md

#### Verification Required

T0 for all implementation files; T1 module tests; T2 Python/C++ and operator boundaries; T3 regression. Device builds and physical tests separately recorded.

#### Related Records

- DEVNOTES: None
- Tests: Pending
- Source: config/runtime.yaml; schemas; firmware; src; README.md

#### Next Steps

Implement and execute available host gates; gather device prerequisites.

#### Deferred Decisions

Pins, VM rail, breakout ratings, toolchain, library versions and camera payload/layout/timing.

---

---

### DEV-2026-10-12-002 — One-use MCU lease and new-observation commands

**Date:** 2026-10-12  
**Time:** 08:55:25 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT  
**Status:** ACCEPTED  
**Type:** DECISION  

#### Problem

Sequence alone cannot reject delayed queues or renewed old visual observations.

#### Context and Constraints

Prompt revision 1 and supplied standards govern. Hardware readiness remains false. Owner Michael Garcia; contact and project license pending confirmation.

#### Solutions Considered

Implement portable core plus fail-closed adapters; defer device-only verification. Rejected guessing wiring, callback coordinates or installed versions.

#### Trade-offs

Enables meaningful host validation; device integration and physical behavior require separate evidence.

#### Final Outcome

MCU offers fixed-expiry one-use epochs. Each accepted command uses increasing observation/sequence and the minimum of remaining epoch, lifetime and observation age budget. Stop revokes arming and epoch. Host validates vision timing; no cross-clock comparisons. Capture timing/latency absent means raw callbacks cannot steer.

#### Implementation Impact

firmware/core.hpp; firmware/core.cpp; src/chicken_chaser/contracts.py; schemas/command.schema.json

#### Verification Required

T0 for all implementation files; T1 module tests; T2 Python/C++ and operator boundaries; T3 regression. Device builds and physical tests separately recorded.

#### Related Records

- DEVNOTES: None
- Tests: Pending
- Source: firmware/core.hpp; firmware/core.cpp; src/chicken_chaser/contracts.py; schemas/command.schema.json

#### Next Steps

Implement and execute available host gates; gather device prerequisites.

#### Deferred Decisions

Device transport scheduling, mailbox atomicity and camera latency must be measured.

---

---

### DEV-2026-10-12-003 — Windows simulation dependency correction

**Date:** 2026-10-12  
**Time:** 09:01:18 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT  
**Status:** ACCEPTED  
**Type:** DECISION  

#### Problem

TEST-2026-10-12-006 failed because libwinpthread-1.dll was a dynamic dependency outside the Python DLL search path.

#### Context and Constraints

Prompt revision 1 and supplied standards govern. Hardware readiness remains false. Owner Michael Garcia; contact and project license pending confirmation.

#### Solutions Considered

Implement portable core plus fail-closed adapters; defer device-only verification. Rejected guessing wiring, callback coordinates or installed versions.

#### Trade-offs

Enables meaningful host validation; device integration and physical behavior require separate evidence.

#### Final Outcome

Link GCC host DLL with -shared -static so compiler runtime dependencies are embedded. Do not alter global DLL search paths. Preserve failed test record.

#### Implementation Impact

firmware/host_api.cpp; tools/build_host.py; build/chicken_host.dll

#### Verification Required

T0 for all implementation files; T1 module tests; T2 Python/C++ and operator boundaries; T3 regression. Device builds and physical tests separately recorded.

#### Related Records

- DEVNOTES: None
- Tests: Pending
- Source: firmware/host_api.cpp; tools/build_host.py; build/chicken_host.dll

#### Next Steps

Implement and execute available host gates; gather device prerequisites.

#### Deferred Decisions

None

---

---

### DEV-2026-10-12-004 — Consume acquisition epochs with stopped commands

**Date:** 2026-10-12  
**Time:** 09:04:10 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT  
**Status:** ACCEPTED  
**Type:** DECISION  

#### Problem

TEST-2026-10-12-009 showed an epoch held through acquisition left too little time before normal next frame.

#### Context and Constraints

Prompt revision 1 and supplied standards govern. Hardware readiness remains false. Owner Michael Garcia; contact and project license pending confirmation.

#### Solutions Considered

Implement portable core plus fail-closed adapters; defer device-only verification. Rejected guessing wiring, callback coordinates or installed versions.

#### Trade-offs

Enables meaningful host validation; device integration and physical behavior require separate evidence.

#### Final Outcome

Send zero-output commands during acquisition, each using a new source observation. This consumes the epoch without enabling movement; tracking requires the configured stable-frame count.

#### Implementation Impact

src/chicken_chaser/runtime.py; tests/test_system.py

#### Verification Required

T0 for all implementation files; T1 module tests; T2 Python/C++ and operator boundaries; T3 regression. Device builds and physical tests separately recorded.

#### Related Records

- DEVNOTES: None
- Tests: Pending
- Source: src/chicken_chaser/runtime.py; tests/test_system.py

#### Next Steps

Implement and execute available host gates; gather device prerequisites.

#### Deferred Decisions

None

---

---

### DEV-2026-10-12-005 — Local operator controls and WebUI gate

**Date:** 2026-10-12  
**Time:** 09:05:57 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT  
**Status:** ACCEPTED  
**Type:** DECISION  

#### Problem

Installed WebUI is unavailable here; upstream API defaults bind on all interfaces.

#### Context and Constraints

Prompt revision 1 and supplied standards govern. Hardware readiness remains false. Owner Michael Garcia; contact and project license pending confirmation.

#### Solutions Considered

Implement portable core plus fail-closed adapters; defer device-only verification. Rejected guessing wiring, callback coordinates or installed versions.

#### Trade-offs

Enables meaningful host validation; device integration and physical behavior require separate evidence.

#### Final Outcome

Provide working desktop loopback status view with token/Host/Origin protection, plus WebUI integration that checks required constructor arguments and binds loopback. No competing camera is opened. Status explicitly reports preview unavailable.

#### Implementation Impact

src/chicken_chaser/operator.py; assets/index.html; app_lab

#### Verification Required

T0 for all implementation files; T1 module tests; T2 Python/C++ and operator boundaries; T3 regression. Device builds and physical tests separately recorded.

#### Related Records

- DEVNOTES: None
- Tests: Pending
- Source: src/chicken_chaser/operator.py; assets/index.html; app_lab

#### Next Steps

Implement and execute available host gates; gather device prerequisites.

#### Deferred Decisions

Installed WebUI execution and shared inference-preview support need on-device verification.

---

---

### DEV-2026-10-12-006 — Workspace-owned temporary artifacts

**Date:** 2026-10-12  
**Time:** 09:08:30 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT  
**Status:** ACCEPTED  
**Type:** DECISION  

#### Problem

TEST-2026-10-12-012 failed before an assertion because sandbox system temporary folder was not writable.

#### Context and Constraints

Prompt revision 1 and supplied standards govern. Hardware readiness remains false. Owner Michael Garcia; contact and project license pending confirmation.

#### Solutions Considered

Implement portable core plus fail-closed adapters; defer device-only verification. Rejected guessing wiring, callback coordinates or installed versions.

#### Trade-offs

Enables meaningful host validation; device integration and physical behavior require separate evidence.

#### Final Outcome

Use temporary directories beneath build for contract fixtures and WebUI assets; cleanup stays confined to the workspace.

#### Implementation Impact

tests/test_system.py; src/chicken_chaser/operator.py

#### Verification Required

T0 for all implementation files; T1 module tests; T2 Python/C++ and operator boundaries; T3 regression. Device builds and physical tests separately recorded.

#### Related Records

- DEVNOTES: None
- Tests: Pending
- Source: tests/test_system.py; src/chicken_chaser/operator.py

#### Next Steps

Implement and execute available host gates; gather device prerequisites.

#### Deferred Decisions

None

---

---

### DEV-2026-10-12-007 — Host milestone and physical handoff

**Date:** 2026-10-12  
**Time:** 09:24:07 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT  
**Status:** IMPLEMENTED  
**Type:** DECISION  

#### Problem

Complete authorized implementation while installed-device and physical prerequisites remain unavailable.

#### Context and Constraints

Preserve prototype metadata, owner hardware statement and readiness false. Historical failures remain append-only. TEST-2026-10-12-017 blocks device integration.

#### Solutions Considered

Host-tested core, normalized perception interface and stopped diagnostic scaffolds; rejected inventing physical GPIO, library or timing evidence.

#### Trade-offs

Dry-run behavior and operator controls are usable; actual motion, preview and real vision/bridge/sensor adapters remain unverified and inhibited.

#### Final Outcome

Implemented schemas/config generation, portable DRV8871 outputs and ranging, command enforcement, Python behavior, host bridge, operator page, recording, probes and documentation. Final mapping schema is closed; native owner cannot be used after destruction. Unused CMake scaffolding was removed; tools/build_host.py is the supported builder. No publication or hardware readiness change.

#### Implementation Impact

README.md; docs/CONTRACTS.md; docs/CONFIGURATION.md; docs/PHYSICAL_VALIDATION.md; source/tests/tools/firmware/schemas; THIRD_PARTY_NOTICES.md; LICENSES.

#### Verification Required

Host gates executed in TEST-2026-10-12-018 and TEST-2026-10-12-019. JavaScript/record audit follows. On-device compilation, real callbacks, GPIO/sensors, bridge loss/Python kill and physical timing remain blocked.

#### Related Records

- DEVNOTES: DEV-2026-10-12-001 through DEV-2026-10-12-006
- Tests: TEST-2026-10-12-017; TEST-2026-10-12-018; TEST-2026-10-12-019
- Source: README.md; firmware; src; tests; tools; docs.

#### Next Steps

Power/common-ground inspection and VM measurement with motor power disconnected; inspect installed APIs and actual payloads; follow ordered physical checklist.

#### Deferred Decisions

Actual wiring/polarity/PWM, sensor library/electrical settings, measured watchdog/reversal/latency, model identity/labels, canonical contact/project license and autonomous readiness. Owner Michael Garcia must supply/validate physical evidence; no failed-test engineering exception is self-authorized.

---

---

