"""File: tools/records.py
Purpose: Append complete engineering/test records with actual local-zone timestamps.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: Never edit existing journal entries. DEV-2026-10-12-001.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def append_record(kind, identifier, title, metadata, sections):
    """Purpose: Preserve evidence. Design: append-only records, duplicate ID rejection.
    Workflow: Called immediately after decisions/checks. Data Handoff: durable Markdown.
    Timestamp uses explicit EDT for this October 12 session; callers need zone adjustment
    outside daylight time. Does not infer a test outcome.
    """
    path = ROOT / ("DEVNOTES.md" if kind == "DEV" else "TEST_LOG.md")
    old = path.read_text() if path.exists() else ""
    if f"### {identifier} " in old:
        raise ValueError("Record ID already exists")
    now = datetime.now(timezone(timedelta(hours=-4)))
    body = f"### {identifier} — {title}\n\n**Date:** {now:%Y-%m-%d}  \n**Time:** {now:%H:%M:%S} America/New_York (UTC−04:00)  \n"
    for key, value in metadata.items():
        body += f"**{key}:** {value}  \n"
    for key, value in sections.items():
        body += f"\n#### {key}\n\n{value}\n"
    if kind == "DEV":
        body += "\n---\n\n---\n\n"
    else:
        body += "\n---\n\n"
    with path.open("a", encoding="utf-8") as file:
        if not old:
            file.write(f"# {'Development notes' if kind == 'DEV' else 'Test log'}\n\n")
        file.write(body)


def decision(number, title, problem, outcome, impact, deferred="None"):
    """Purpose: Record complete decision. Design: every required section retained.
    Workflow: Decision time. Data Handoff: immutable DEV entry.
    """
    append_record("DEV", f"DEV-2026-10-12-{number:03}", title,
        {"Engineer": "Codex / ChatGPT", "Status": "ACCEPTED", "Type": "DECISION"}, {
        "Problem": problem,
        "Context and Constraints": "Prompt revision 1 and supplied standards govern. Hardware readiness remains false. Owner Michael Garcia; contact and project license pending confirmation.",
        "Solutions Considered": "Implement portable core plus fail-closed adapters; defer device-only verification. Rejected guessing wiring, callback coordinates or installed versions.",
        "Trade-offs": "Enables meaningful host validation; device integration and physical behavior require separate evidence.",
        "Final Outcome": outcome,
        "Implementation Impact": impact,
        "Verification Required": "T0 for all implementation files; T1 module tests; T2 Python/C++ and operator boundaries; T3 regression. Device builds and physical tests separately recorded.",
        "Related Records": "- DEVNOTES: None\n- Tests: Pending\n- Source: " + impact,
        "Next Steps": "Implement and execute available host gates; gather device prerequisites.",
        "Deferred Decisions": deferred})


def test(number, title, level, result, files, objective, procedure, actual, evidence, related="None", disposition="Host work may proceed; physical verification remains required."):
    """Purpose: Record executed evidence or explicit blockage. Design: no implicit PASS.
    Workflow: After each gate. Data Handoff: immutable TEST entry with disposition.
    """
    append_record("TEST", f"TEST-2026-10-12-{number:03}", title,
        {"Tester": "Codex / ChatGPT", "Level": level, "Result": result}, {
        "Scope": title, "Files Under Validation": files, "Objective": objective,
        "Preconditions": "Windows host, Python 3.13, GCC UCRT64; hardware absent unless explicitly stated.",
        "Procedure": procedure, "Expected Result": objective, "Actual Result": actual,
        "Evidence": evidence, "Failures / Observations": "No physical evidence is implied. " + (actual if result != "PASS" else "None."),
        "Related DEVNOTES": "DEV-2026-10-12-001; DEV-2026-10-12-002", "Related Tests": related,
        "Disposition": disposition})
