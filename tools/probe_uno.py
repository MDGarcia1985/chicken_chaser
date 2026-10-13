"""File: tools/probe_uno.py
Purpose: Inspect installed UNO Q APIs and optionally capture complete raw records.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: run on board inside App Lab environment; capture owns the camera alone.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import subprocess
import sys
import time


def inventory():
    """Purpose: Identify installed versions/signatures/source rather than guessing.
    Design: read-only import/source inspection, no camera instantiation.
    Workflow: before adapter definition. Data Handoff: complete JSON inventory/errors.
    """
    report={"python":sys.version,"modules":{},"packages":{}}
    for name,symbols in {
        "arduino.app_utils":["App","Bridge"],
        "arduino.app_bricks.video_objectdetection":["VideoObjectDetection"],
        "arduino.app_bricks.web_ui":["WebUI"],
        "arduino.app_peripherals.camera":["Camera"]}.items():
        try:
            module=importlib.import_module(name)
            item={"file":module.__file__,"symbols":{}}
            for symbol in symbols:
                value=getattr(module,symbol)
                item["symbols"][symbol]={"signature":str(inspect.signature(value)),"source":inspect.getsource(value)}
            report["modules"][name]=item
        except Exception as error:
            report["modules"][name]={"error":str(error)}
    for distribution in importlib.metadata.distributions():
        name=distribution.metadata.get("Name","")
        if any(term in name.lower() for term in ("arduino","edge","opencv","web","fastapi")):
            report["packages"][name]=distribution.version
    for args in (["arduino-cli","version"],["arduino-cli","core","list"],["arduino-cli","lib","list"]):
        try:
            result=subprocess.run(args,capture_output=True,text=True,timeout=10)
            report[" ".join(args)]={"exit":result.returncode,"stdout":result.stdout,"stderr":result.stderr}
        except (OSError,subprocess.TimeoutExpired) as error:
            report[" ".join(args)]={"error":str(error)}
    return report


def capture():
    """Purpose: Record actual callback fields before adapting them.
    Design: preserve user-tested camera selection/capture settings; never drives.
    Workflow: separate App Lab probe, baseline stopped first. Data Handoff: complete
    raw records and receipt monotonic ns to stdout. Receipt is NOT capture time.
    Camera dimensions/layout still need negotiated-frame inspection, not defaults.
    """
    from arduino.app_utils import App
    from arduino.app_bricks.video_objectdetection import VideoObjectDetection
    from arduino.app_peripherals.camera import Camera
    camera=Camera(resolution=(640,480),fps=30)
    detector=VideoObjectDetection(camera=camera,confidence=.5,debounce_sec=0.0)

    def callback(detections):
        """Purpose: Preserve complete raw payload. Design: no coordinate extraction.
        Workflow: on_detect_all callback. Data Handoff: diagnostic stdout record.
        """
        print(json.dumps({"received_monotonic_ns":time.monotonic_ns(),"detections":detections},default=repr),flush=True)

    detector.on_detect_all(callback)
    App.run()


def main():
    """Purpose: CLI inspection with opt-in raw capture/artifact digest.
    Design: stdout avoids silently rewriting manifest; no numerical weights in YAML.
    Workflow: board inspection. Data Handoff: inventory/hash or raw callback stream.
    """
    parser=argparse.ArgumentParser()
    parser.add_argument("--capture",action="store_true")
    parser.add_argument("--weights",type=Path)
    args=parser.parse_args()
    print(json.dumps(inventory(),indent=2),flush=True)
    if args.weights:
        digest=hashlib.sha256()
        with args.weights.open("rb") as file:
            for block in iter(lambda:file.read(1024*1024),b""):
                digest.update(block)
        print(json.dumps({"artifact":str(args.weights),"sha256":digest.hexdigest()}),flush=True)
    if args.capture:
        capture()


if __name__ == "__main__":
    main()
