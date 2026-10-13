"""File: src/chicken_chaser/recording.py
Purpose: Opt-in bounded normalized observations for offline labeling.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: no online weights, no default recording. DEV-2026-10-12-001.
"""
import json
from pathlib import Path
import uuid
from .vision import validate_detection


class Recorder:
    """Purpose: Preserve optional observations. Design: per-session file, fixed quota.
    Workflow: explicitly enabled runtime. Data Handoff: JSONL to offline labeling;
    these are detections, not automatically correct ground-truth annotations.
    """
    def __init__(self, folder, limit=1000):
        """Purpose: Create session output only on opt-in. Design: exclusive unique file.
        Workflow: enabled startup. Data Handoff: output owner; max 1000 frames/session.
        """
        Path(folder).mkdir(parents=True,exist_ok=True)
        self.path=Path(folder)/f"observations-{uuid.uuid4().hex}.jsonl"
        self.file=self.path.open("x",encoding="utf-8")
        self.limit=limit
        self.count=0

    def add(self, records):
        """Purpose: Append one normalized frame. Design: explicit quota stops recording;
        validation prevents malformed records. Workflow: newest frame consumed.
        Data Handoff: durable JSONL, bool false when quota full, exceptions on I/O.
        """
        if self.count >= self.limit:
            return False
        for record in records:
            validate_detection(record)
        self.file.write(json.dumps(records,allow_nan=False)+"\n")
        self.file.flush()
        self.count+=1
        return True

    def close(self):
        self.file.close()
