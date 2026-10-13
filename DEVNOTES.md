# Development notes

### DEV-2026-10-13-001 — Owner-selected dual licensing

**Date:** 2026-10-13  
**Time:** 07:24:00 America/New_York (UTC−04:00)  
**Engineer:** Codex / ChatGPT, under Michael Garcia's direction  
**Status:** IMPLEMENTED  
**Type:** DECISION

#### Problem

The owner requested dual MIT and Mozilla licensing; project documents still described licensing as pending.

#### Context and Constraints

The owner authorized this change. Third-party licenses and notices, including the embedded Arduino MPL-2.0 example, remain applicable.

#### Solutions Considered

MIT OR MPL-2.0 (recipient choice); requiring both licenses. Recipient choice implements the requested dual licensing.

#### Trade-offs

Recipients can select either license for original project material; file-specific third-party requirements remain separate.

#### Final Outcome

Original Chicken Chaser code and documentation use MIT OR MPL-2.0. Copyright holder: Michael Garcia, 2026. Full license texts and a scope notice were added.

#### Implementation Impact

LICENSE, LICENSE-MIT, LICENSE-MPL-2.0, README.md, chicken_chaser_master.yaml, chicken_chaser_brief.md, config/chicken_chaser_architecture.yaml, docs/chicken_chaser_architecture.md.

#### Verification Required

Documentation-only change: verify complete license text, local links and consistent identifiers. No implementation behavior or T1–T3 runtime gate changes.

#### Related Records

- DEVNOTES: None
- Tests: Not applicable (documentation-only; static integrity checks performed)
- Source: Listed under Implementation Impact

#### Next Steps

Use SPDX-License-Identifier: MIT OR MPL-2.0 for future original source files; preserve third-party file-specific notices.

#### Deferred Decisions

Canonical project contact remains pending confirmation.

---

---
