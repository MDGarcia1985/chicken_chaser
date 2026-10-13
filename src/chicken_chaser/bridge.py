"""File: src/chicken_chaser/bridge.py
Purpose: Schema-checked Python/C++ simulation and supported Router Bridge scaffold.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: simulation does not write GPIO; actual wire encoding is not JSON.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
"""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import threading
from .contracts import ROOT, validate


class SimBridge:
    """Purpose: Exercise the real C++ enforcement core from Python.
    Design: serialized C ABI, authoritative-config digest check. Workflow: dry-run.
    Data Handoff: logical contract records; no device transport emulation claim.
    """
    def __init__(self, config, library=None):
        """Purpose: Load host core. Design: explicit ownership and typed ABI.
        Workflow: after build. Data Handoff: locked C++ instance or load/hash error.
        """
        library = Path(library or ROOT / "build" / ("chicken_host.dll" if os.name == "nt" else "libchicken_host.so"))
        self.lib = C.CDLL(str(library))
        types = {
            "cc_create": ([],C.c_void_p), "cc_destroy": ([C.c_void_p],None),
            "cc_config_hash": ([],C.c_char_p), "cc_range": ([C.c_void_p,C.c_int,C.c_int,C.c_uint,C.c_uint32],None),
            "cc_command": ([C.c_void_p]+[C.c_uint32]*7+[C.c_float,C.c_float,C.c_int,C.c_uint32],C.c_int)}
        for name in ("arm", "offer", "remaining", "clear"):
            types["cc_"+name] = ([C.c_void_p]+([C.c_uint32]*2 if name == "arm" else [C.c_uint32]), C.c_uint32)
        for name in ("stop", "tick"):
            types["cc_"+name] = ([C.c_void_p,C.c_uint32],None)
        for name in ("generation", "session", "ack", "armed"):
            types["cc_"+name] = ([C.c_void_p],C.c_uint32)
        types["cc_fault"] = ([C.c_void_p],C.c_char_p)
        types["cc_left"] = ([C.c_void_p],C.c_float)
        types["cc_right"] = ([C.c_void_p],C.c_float)
        for name, (args, result) in types.items():
            function = getattr(self.lib,name)
            function.argtypes, function.restype = args,result
        digest = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
        if self.lib.cc_config_hash().decode() != digest:
            raise ValueError("MCU configuration drift: regenerate and rebuild")
        self.ptr = self.lib.cc_create()
        self.lock = threading.RLock()
        self.config = config
        self.samples = {side: {"status": "unavailable", "distance_mm": None, "at": None} for side in ("front","rear")}
        self.commanded = [0.0,0.0]

    def ensure_open(self):
        """Purpose: Reject calls after native owner destruction. Design: no null C++
        dereference. Workflow: inside each bridge lock. Data Handoff: RuntimeError.
        """
        if not self.ptr:
            raise RuntimeError("Simulator is closed")

    def ranges(self, now, front=1000, rear=1000, valid=True):
        """Purpose: Inject clearly marked synthetic sensors. Design: only dry-run caller.
        Workflow: fixtures/demo. Data Handoff: mm and local timestamps to core.
        """
        with self.lock:
            self.ensure_open()
            for index, (side, mm) in enumerate((("front",front),("rear",rear))):
                usable = valid and isinstance(mm,int) and 1 <= mm <= (8000 if side == "front" else 2000)
                self.samples[side] = {"status": "valid" if usable else "invalid", "distance_mm": mm if usable else None, "at": now}
                self.lib.cc_range(self.ptr,index,2 if usable else 1,mm if usable else 0,now)

    def arm(self, session, now):
        """Purpose: Explicit simulation arm. Design: core checks sensors/faults.
        Workflow: operator/demo. Data Handoff: boolean acceptance.
        """
        with self.lock:
            self.ensure_open()
            return bool(self.lib.cc_arm(self.ptr,session,now))

    def clear_fault(self, now):
        """Purpose: Clear stopped recoverable fault. Design: separate from arm.
        Workflow: operator. Data Handoff: boolean, no movement.
        """
        with self.lock:
            self.ensure_open()
            return bool(self.lib.cc_clear(self.ptr,now))

    def stop(self, now):
        """Purpose: Unconditional disarm. Design: bypass command validation.
        Workflow: error/operator/loss. Data Handoff: C++ zero output.
        """
        with self.lock:
            self.ensure_open()
            self.lib.cc_stop(self.ptr,now)
            self.commanded = [0.0,0.0]

    def lease(self, now):
        """Purpose: Fetch expiring epoch. Design: queries cannot renew same epoch.
        Workflow: BEFORE acquiring source observation. Data Handoff: validated lease.
        """
        with self.lock:
            self.ensure_open()
            epoch = self.lib.cc_offer(self.ptr,now)
            if not epoch:
                return None
            return validate("lease", {"schema_version": "1.0.0", "session": self.lib.cc_session(self.ptr),
                "generation": self.lib.cc_generation(self.ptr), "epoch": epoch,
                "remaining_ms": self.lib.cc_remaining(self.ptr,now)})

    def send(self, record, now):
        """Purpose: Validate bridge boundary. Design: malformed requests stop first.
        Workflow: one command/new observation/epoch. Data Handoff: C++ acceptance/ack.
        """
        with self.lock:
            self.ensure_open()
            try:
                validate("command",record)
            except Exception:
                self.stop(now)
                raise
            self.commanded = [record["left"],record["right"]]
            return bool(self.lib.cc_command(self.ptr,*[record[k] for k in (
                "session","sequence","generation","epoch","observation","observation_age_ms","lifetime_ms")],
                record["left"],record["right"],int(record["mode"]=="follow"),now))

    def telemetry(self, now):
        """Purpose: Run local enforcement and report state. Design: sample ages remain
        visible after expiry. Workflow: every simulated control tick. Data Handoff:
        validated telemetry; applied PWM is synthetic, physical_outputs false.
        """
        with self.lock:
            self.ensure_open()
            self.lib.cc_tick(self.ptr,now)
            samples = {}
            for side, sample in self.samples.items():
                age = None if sample["at"] is None else now-sample["at"]
                status = sample["status"]
                if status == "valid" and age >= self.config["simulation"]["sensor_age_ms"]:
                    status = "stale"
                samples[side] = {"status": status, "distance_mm": sample["distance_mm"], "age_ms": age}
            fault = self.lib.cc_fault(self.ptr).decode()
            armed = bool(self.lib.cc_armed(self.ptr))
            return validate("telemetry", {"schema_version": "1.0.0", "session": self.lib.cc_session(self.ptr),
                "generation": self.lib.cc_generation(self.ptr), "ack_sequence": self.lib.cc_ack(self.ptr),
                "state": "TRACKING" if armed else ("BLOCKED" if fault == "range_blocked" else "FAULT" if fault else "DISARMED"),
                "commanded": self.commanded, "applied": [self.lib.cc_left(self.ptr),self.lib.cc_right(self.ptr)],
                "front": samples["front"], "rear": samples["rear"], "fault": fault, "physical_outputs": False})

    def close(self):
        """Purpose: Release simulator. Design: explicit lifetime prevents stale pointer.
        Workflow: finally/shutdown. Data Handoff: destroyed C++ owner.
        """
        with self.lock:
            if self.ptr:
                self.lib.cc_destroy(self.ptr)
                self.ptr = None


class RouterTransport:
    """Purpose: Supported RPC scaffold after installed-version verification.
    Design: native Bridge.call/notify; no JSON wire claim. Workflow: device bring-up.
    Data Handoff: stop RPC only; motion intentionally blocked by unavailable bindings.
    """
    def __init__(self, bridge):
        """Purpose: Inject inspected API. Design: no import on desktop.
        Workflow: device probe confirms call/notify. Data Handoff: transport reference.
        """
        self.bridge = bridge

    def stop(self):
        """Purpose: Request immediate device stop. Design: bounded RPC plus watchdog
        on failure; never promises a physical disconnect. Workflow: operator/shutdown.
        Data Handoff: cc_stop response or timeout/connection exception.
        """
        return self.bridge.call("cc_stop", timeout=.1)

    def send(self, record):
        """Purpose: Enforce integration gate. Design: device command marshalling not
        invented. Workflow: any premature device motion attempt. Data Handoff: error.
        """
        raise RuntimeError("Device motion binding blocked: inspect installed MCU/Python APIs and validate wiring first")
