# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
# SPDX-License-Identifier: MPL-2.0
# File: app_lab/python/baseline.py
# Purpose: Preserve the owner-tested console camera capture/detection path.
# Owner: Michael Garcia; upstream example: Arduino; annotation contributor: Codex / ChatGPT.
# Contact: Pending confirmation. File license: MPL-2.0.
# Constraint: no WebUI, motor commands or second capture connection. DEV-2026-10-12-001.

from arduino.app_utils import App, Logger
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_peripherals.camera import Camera

CONFIDENCE_THRESHOLD = 0.5
logger = Logger("VideoObjectDetectionApp")

camera = Camera(resolution=(640, 480), fps=30)
detection_stream = VideoObjectDetection(camera=camera,confidence=CONFIDENCE_THRESHOLD,debounce_sec=0.0)


def send_detections_to_console(detections: dict):
    """Purpose: Log all classifications using the working baseline.
    Design: unchanged label-to-list iteration, no box/timing assumptions.
    Workflow: detector callback. Data Handoff: console labels/confidence only.
    """
    for key, values in detections.items():
        for value in values:
            logger.info(f"Detected {key} with confidence {value.get('confidence', 'N/A')}")


detection_stream.on_detect_all(send_detections_to_console)
App.run()
