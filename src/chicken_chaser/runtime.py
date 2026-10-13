"""File: src/chicken_chaser/runtime.py
Purpose: Connect perception, behavior and C++ authority in a runnable dry-run.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: no physical adapter; synthetic fixtures explicitly identified.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
"""
import argparse
from collections import deque
import json
import secrets
import threading
import time
from .behavior import Behavior
from .bridge import SimBridge
from .contracts import load_config
from .vision import age_ms
from .contracts import ROOT


def fixture(frame_id, now, center=440):
    """Purpose: Synthetic normalized perception. Design: known 640x480 single view.
    Workflow: explicit dry-run demo only. Data Handoff: contract fixture, no camera.
    """
    return {"schema_version": "1.0.0", "label": "person", "confidence": .9,
        "box": [center-30,100,center+30,220], "coordinates": "xyxy_pixels_processing_view",
        "width": 640, "height": 480, "frame_id": frame_id, "received_ms": now,
        "capture_ms": now, "latency_bound_ms": None}


class LatestObservation:
    """Purpose: Bound observation backlog. Design: newest wins, empty frames matter.
    Workflow: callback producer/control consumer. Data Handoff: at most one frame.
    """
    def __init__(self):
        """Purpose: Initialize bounded queue. Design: separate callback lock.
        Workflow: startup. Data Handoff: empty mailbox.
        """
        self.lock = threading.Lock()
        self.queue = deque(maxlen=1)

    def put(self, records):
        """Purpose: Replace old frame. Design: callback must not perform bridge I/O.
        Workflow: producer. Data Handoff: latest normalized frame.
        """
        with self.lock:
            self.queue.append(records)

    def take(self):
        """Purpose: Consume newest once. Design: no replay from periodic heartbeat.
        Workflow: control tick. Data Handoff: frame or None; queue emptied.
        """
        with self.lock:
            return self.queue.pop() if self.queue else None


class Runtime:
    """Purpose: Host application vertical slice. Design: loop owns all authority;
    operator actions serialize through lock. Workflow: CLI/HTTP dry-run.
    Data Handoff: status, simulated command and applied duty.
    """
    def __init__(self, config=None):
        """Purpose: Construct disarmed simulation. Design: authority digest checked.
        Workflow: startup. Data Handoff: no movement until explicit simulation arm.
        """
        self.config = config or load_config()
        self.bridge = SimBridge(self.config)
        self.behavior = Behavior(self.config["behavior"])
        self.lock = threading.RLock()
        self.origin = time.monotonic()
        self.session = secrets.randbelow(2147483646)+1
        self.sequence = 0
        self.frame = 0
        self.scenario = "tracking"
        self.mailbox = LatestObservation()
        self.latest = None
        self.last_frame_time = -40
        self.closed = False
        self.recorder = None
        if self.config["behavior"]["recording_enabled"]:
            from .recording import Recorder
            self.recorder = Recorder(ROOT / "captures")

    def now(self):
        return int((time.monotonic()-self.origin)*1000)

    def action(self, action, mode="turn"):
        """Purpose: Handle explicit operator intent. Design: independent fault clear,
        no reconnect rearm. Workflow: authenticated local endpoint/CLI.
        Data Handoff: boolean state change; all arming remains synthetic.
        """
        with self.lock:
            now = self.now()
            if action in ("stop","disarm"):
                self.bridge.stop(now)
                self.behavior.disarm()
                return True
            if action == "clear":
                if self.bridge.clear_fault(now):
                    return self.behavior.clear_fault()
                return False
            if action == "arm":
                if self.behavior.state == "FAULT":
                    return False
                if mode not in ("turn","follow"):
                    return False
                if mode == "follow" and not self.config["behavior"]["follow_enabled"]:
                    return False
                if self.bridge.arm(self.session,now):
                    self.sequence = 0
                    return self.behavior.arm(mode)
                return False
            if action in ("tracking","lost","ambiguous","obstacle","bridge_loss"):
                self.scenario = action
                return True
            raise ValueError("Unknown operator action")

    def step(self, now=None, synthetic=True):
        """Purpose: Connect newest perception to an expiring C++ command.
        Design: lease obtained before synthetic capture; target loss stops and
        disarms MCU. No repeat commands without new observations. Workflow: 10 ms
        host loop target (not measured MCU cadence). Data Handoff: status dictionary.
        """
        with self.lock:
            now = self.now() if now is None else now
            if synthetic and self.scenario != "bridge_loss":
                self.bridge.ranges(now,front=200 if self.scenario == "obstacle" else 1000)
            telemetry = self.bridge.telemetry(now)
            lease = self.bridge.lease(now) if self.behavior.armed and self.scenario != "bridge_loss" else None
            if synthetic and now-self.last_frame_time >= 40:
                self.frame += 1
                self.last_frame_time = now
                records = [] if self.scenario == "lost" else [fixture(self.frame,now)]
                if self.scenario == "ambiguous":
                    records.append(fixture(self.frame,now,center=450))
                self.mailbox.put(records)
            records = self.mailbox.take()
            if records is not None:
                self.latest = records
                if self.recorder:
                    try:
                        self.recorder.add(records)
                    except Exception:
                        self.bridge.stop(now)
                        self.behavior.lose("FAULT","recording_failed")
                        self.behavior.armed = False
                        return self.status(now)
                clear = lambda side: telemetry[side]["status"] == "valid" and telemetry[side]["distance_mm"] >= self.config["simulation"]["clearance_mm"]
                left,right = self.behavior.update(records,now,clear("front"),clear("rear"))
                if self.behavior.state in ("TARGET_LOST","BLOCKED","FAULT"):
                    self.bridge.stop(now)
                    self.behavior.armed = False
                elif lease and self.behavior.selected and self.behavior.state in ("TRACKING","ACQUIRING"):
                    self.sequence += 1
                    selected = self.behavior.selected
                    request = {"schema_version": "1.0.0", "session": lease["session"], "sequence": self.sequence,
                        "generation": lease["generation"], "epoch": lease["epoch"], "mode": self.behavior.mode,
                        "left": left, "right": right, "observation": selected["frame_id"],
                        "observation_age_ms": int(age_ms(selected,now)), "lifetime_ms": lease["remaining_ms"]}
                    if not self.bridge.send(request,now):
                        self.behavior.lose("FAULT","command_rejected")
                        self.behavior.armed = False
            if not telemetry["state"] == "TRACKING" and telemetry["fault"]:
                self.behavior.lose("BLOCKED" if telemetry["fault"] == "range_blocked" else "FAULT",telemetry["fault"])
                self.behavior.armed = False
            return self.status(now)

    def status(self, now=None):
        """Purpose: Report operator state. Design: clearly label simulated outputs,
        unresolved real camera/model and unavailable preview. Workflow: HTTP polling.
        Data Handoff: JSON-safe status; no raw capture connection.
        """
        with self.lock:
            now = self.now() if now is None else now
            telemetry = self.bridge.telemetry(now)
            if telemetry["fault"] and self.behavior.armed:
                self.behavior.lose("BLOCKED" if telemetry["fault"] == "range_blocked" else "FAULT",telemetry["fault"])
                self.behavior.armed = False
            return {"dry_run": True, "ready_for_autonomous_motion": False,
                "behavior": self.behavior.state, "reason": self.behavior.reason, "mode": self.behavior.mode,
                "selected": self.behavior.selected, "detections": self.latest,
                "telemetry": telemetry, "scenario": self.scenario,
                "preview": "Unavailable: no verified shared-stream API",
                "camera": "Synthetic fixture; real negotiated view unresolved",
                "model": "Synthetic person proxy; installed model manifest unresolved"}

    def close(self):
        """Purpose: Stop on orderly termination. Design: finally path; hardware
        termination guarantees belong to independent MCU watchdog. Workflow: shutdown.
        Data Handoff: disarmed simulator and released core.
        """
        with self.lock:
            if not self.closed:
                self.bridge.stop(self.now())
                self.bridge.close()
                if self.recorder:
                    self.recorder.close()
                self.closed = True


def main():
    """Purpose: Run console demo or local operator view. Design: dry-run only.
    Workflow: python -m chicken_chaser.runtime. Data Handoff: console JSON/local UI;
    Ctrl-C always closes the simulator.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Explicitly arm synthetic turn-only demonstration")
    parser.add_argument("--ui", action="store_true", help="Local fallback UI on 127.0.0.1:7000")
    parser.add_argument("--seconds", type=float, default=3)
    args = parser.parse_args()
    runtime = Runtime()
    server = None
    try:
        runtime.step()
        if args.demo:
            runtime.action("arm")
        if args.ui:
            from .operator import serve
            server = serve(runtime)
            print("Dry-run operator view: http://127.0.0.1:7000 (loopback only)",flush=True)
        end = float("inf") if args.ui else time.monotonic()+args.seconds
        last_print = 0
        while time.monotonic() < end:
            status = runtime.step()
            if not args.ui and runtime.now()-last_print >= 250:
                print(json.dumps(status,allow_nan=False),flush=True)
                last_print = runtime.now()
            time.sleep(.01)
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.shutdown()
            server.server_close()
        runtime.close()


if __name__ == "__main__":
    main()
