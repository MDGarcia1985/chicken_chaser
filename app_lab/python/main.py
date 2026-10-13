# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: MPL-2.0
# File: app_lab/python/main.py
# Purpose: Preserve one camera owner and expose stopped diagnostic status in WebUI.
# Owner: Michael Garcia; upstream baseline: Arduino; contributor: Codex / ChatGPT.
# Contact: Pending confirmation. File license: MPL-2.0 (derived baseline).
# Constraints: live payload adapter unresolved, no physical motor transport.
# Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-005.
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from chicken_chaser.operator import install_webui
from arduino.app_utils import App, Logger
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_bricks.web_ui import WebUI
from arduino.app_peripherals.camera import Camera


class Diagnostics:
    """Purpose: Display actual callback availability without inventing coordinates.
    Design: bounded latest summary; physical arm rejects. Workflow: WebUI probe.
    Data Handoff: status compatible with local view, outputs always stopped.
    """
    def __init__(self):
        """Purpose: Initialize stopped diagnostics. Design: one summary only.
        Workflow: application startup. Data Handoff: lock/summary owner.
        """
        self.lock=threading.Lock()
        self.labels={}
        self.received=None

    def action(self, action, mode="turn"):
        """Purpose: Reject motion before adapter validation. Design: no motor RPCs.
        Workflow: local controls. Data Handoff: arm false; stop/disarm accepted.
        """
        return action in ("stop","disarm","clear")

    def callback(self, detections):
        """Purpose: Preserve baseline console observations. Design: latest label counts,
        no coordinate guesses. Workflow: one camera's on_detect_all callback.
        Data Handoff: status summary/console; full records via tools/probe_uno.py.
        """
        for key,values in detections.items():
            for value in values:
                logger.info(f"Detected {key} with confidence {value.get('confidence', 'N/A')}")
        with self.lock:
            self.labels={key:len(values) for key,values in detections.items()}
            self.received=time.monotonic_ns()

    def status(self):
        """Purpose: Expose conservative live diagnostic status.
        Design: labels reported without assumed boxes; timing marked receipt only.
        Workflow: WebUI polling. Data Handoff: JSON-safe stopped view.
        """
        with self.lock:
            unavailable={"status":"unavailable","distance_mm":None,"age_ms":None}
            return {"dry_run":True,"ready_for_autonomous_motion":False,"behavior":"DISARMED",
                "reason":"Device adapter and wiring validation required before arming", "mode":"diagnostics",
                "selected":None,"detections":[],"scenario":"live diagnostics",
                "telemetry":{"commanded":[0,0],"applied":[0,0],"front":unavailable,"rear":unavailable,
                    "fault":"device_integration_unverified","physical_outputs":False},
                "camera":f"Live callback labels: {self.labels}; receipt ns: {self.received}. Negotiated layout unresolved.",
                "model":"Installed model identity/weights/labels require probe inventory",
                "preview":"Unavailable: shared preview API not yet verified"}


logger=Logger("ChickenChaserDiagnostics")
diagnostics=Diagnostics()
ui,assets_owner=install_webui(diagnostics,WebUI)
camera=Camera(resolution=(640,480),fps=30)
detector=VideoObjectDetection(camera=camera,confidence=.5,debounce_sec=0.0)
detector.on_detect_all(diagnostics.callback)
App.run()
