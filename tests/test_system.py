"""File: tests/test_system.py
Purpose: Meaningful configuration, vision and Python/C++/operator regressions.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: synthetic observations only, real hardware tests separately blocked.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002, DEV-2026-10-12-004.
"""
import http.client
import json
from pathlib import Path
import re
import tempfile
import unittest
import importlib.util
from chicken_chaser.contracts import ROOT, UniqueLoader, load_config, validate
from chicken_chaser.vision import normalize, validate_detection
from chicken_chaser.behavior import Behavior
from chicken_chaser.bridge import SimBridge, RouterTransport
from chicken_chaser.runtime import Runtime, LatestObservation, fixture
from chicken_chaser.operator import serve
import yaml


class ContractTests(unittest.TestCase):
    """Purpose: Configuration and schema gate. Design: fail closed on malformed input.
    Workflow: T1. Data Handoff: unittest evidence.
    """
    def test_defaults_and_manifest(self):
        """Purpose: Validate unresolved defaults. Design: hardware cannot enable.
        Workflow: startup contract test. Data Handoff: assertions.
        """
        config = load_config()
        self.assertFalse(config["hardware"]["enabled"])
        self.assertIsNone(config["hardware"]["motors"]["left"]["in1"])
        validate("model",json.loads((ROOT/"config/model_manifest.json").read_text()))
        for path in (ROOT/"schemas").glob("*.json"):
            from jsonschema import Draft202012Validator
            Draft202012Validator.check_schema(json.loads(path.read_text()))

    def test_duplicates_nonfinite_versions_and_motion(self):
        """Purpose: Reject dangerous contract alternatives. Design: duplicates and
        nonfinite values cannot override valid values. Workflow: config boundary.
        Data Handoff: expected validation exceptions.
        """
        with self.assertRaises(ValueError):
            yaml.load("pin: 1\npin: 2\n",Loader=UniqueLoader)
        for mutate in (
            lambda c: c.update(schema_version="0.0.0"),
            lambda c: c["simulation"].update(max_duty=float("nan")),
            lambda c: c["hardware"].update(enabled=True),
            lambda c: c["hardware"].update(vm_v=5),
            lambda c: c["behavior"].update(reverse_enabled=True),
            lambda c: c["camera"].update(payload_mapping={"wrong":"field"}),
            lambda c: c.update(unrecognized=True)):
            c=load_config(); mutate(c)
            with self.assertRaises(Exception):
                validate("config",c)

    def test_conflicting_pins_and_mixed_limits(self):
        """Purpose: Check cross-field constraints. Design: schema plus semantic checks.
        Workflow: authoritative load. Data Handoff: arming prerequisites rejected.
        """
        for mutate in (
            lambda c: c["hardware"]["motors"]["left"].update(in1=1,in2=1),
            lambda c: c["behavior"].update(max_forward=.5),
            lambda c: c["simulation"].update(deadband=.3)):
            c=load_config(); mutate(c)
            with tempfile.TemporaryDirectory(dir=ROOT / "build") as folder:
                p=Path(folder)/"runtime.yaml"; p.write_text(yaml.safe_dump(c))
                with self.assertRaises(ValueError):
                    load_config(p)

    def test_generated_contracts_and_mcu_match_authority(self):
        """Purpose: Prevent checked-in artifact drift. Design: regenerate in isolated
        workspace directory, compare exact output. Workflow: contract boundary.
        Data Handoff: schema/header conformance assertions.
        """
        with tempfile.TemporaryDirectory(dir=ROOT/"build") as folder:
            for name in ("create_schemas","generate_mcu"):
                spec=importlib.util.spec_from_file_location(name,ROOT/"tools"/f"{name}.py")
                module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
                if name == "create_schemas":
                    module.ROOT=Path(folder); module.main()
                    for path in (ROOT/"schemas").glob("*.json"):
                        self.assertEqual(path.read_text(),(Path(folder)/"schemas"/path.name).read_text())
                else:
                    destination=Path(folder)/"generated.hpp"
                    module.generate(destination=destination)
                    self.assertEqual(destination.read_text(),(ROOT/"firmware/generated_config.hpp").read_text())


class VisionTests(unittest.TestCase):
    """Purpose: Normalize and retain targets. Design: test real boundaries with
    explicit synthetic payload mapping. Workflow: T1. Data Handoff: assertions.
    """
    def setUp(self):
        """Purpose: Prepare isolated behavior. Design: no state leakage between tests.
        Workflow: unittest. Data Handoff: explicitly armed simulation config.
        """
        self.b=Behavior(load_config()["behavior"])
        self.assertTrue(self.b.arm())

    def acquire(self, center=440):
        """Purpose: Exercise public acquisition. Design: unique frames and timing.
        Workflow: fixtures. Data Handoff: tracking behavior after three frames.
        """
        for i in range(1,4):
            result=self.b.update([fixture(i,i*40,center)],i*40,True,True)
            if i<3:
                self.assertEqual(result,(0,0))
        return result

    def test_acquisition_and_error_sign(self):
        """Purpose: Check normalized steering and deadband. Design: actual view width.
        Workflow: public behavior interface. Data Handoff: bounded differential duty.
        """
        left,right=self.acquire()
        self.assertEqual(self.b.state,"TRACKING")
        self.assertGreater(left,0); self.assertLess(right,0)
        self.assertLessEqual(abs(left),.15)
        self.b.disarm(); self.b.arm()
        # Frame counter remains monotonic even across disarm.
        for i in range(4,7):
            result=self.b.update([fixture(i,i*40,320)],i*40,True,True)
        self.assertEqual(result,(0,0))

    def test_retains_associated_target(self):
        """Purpose: Avoid highest-confidence switching. Design: distant distractor.
        Workflow: established target then multi-object frame. Data Handoff: same box.
        """
        self.acquire()
        a=fixture(4,160,445); a["confidence"]=.6
        b=fixture(4,160,80); b["confidence"]=.99
        self.b.update([a,b],160,True,True)
        self.assertEqual(self.b.selected["box"],a["box"])

    def test_ambiguity_loss_stale_invalid_and_replay(self):
        """Purpose: Stop unsafe observations. Design: independent public failure cases.
        Workflow: new behavior for each case. Data Handoff: zero commands and state.
        """
        cases=[[],[fixture(4,160,440),fixture(4,160,450)],
               [fixture(4,0)], [fixture(3,120)]]
        for records in cases:
            self.setUp(); self.acquire()
            self.assertEqual(self.b.update(records,160,True,True),(0,0))
            self.assertEqual(self.b.state,"TARGET_LOST")
        self.setUp(); self.acquire(); r=fixture(4,160); r["confidence"]=2
        self.assertEqual(self.b.update([r],160,True,True),(0,0))
        self.assertEqual(self.b.state,"FAULT")
        self.assertFalse(self.b.arm())
        self.b.armed=False; self.b.disarm()
        self.assertFalse(self.b.arm())
        self.assertTrue(self.b.clear_fault()); self.assertTrue(self.b.arm())

    def test_receipt_time_is_not_capture_time(self):
        """Purpose: Prevent unknown transport age driving. Design: measured latency
        bound required when capture timestamp unavailable. Workflow: normalized record.
        Data Handoff: stopped behavior when freshness cannot be bounded.
        """
        r=fixture(1,40); r["capture_ms"]=None
        self.assertEqual(self.b.update([r],40,True,True),(0,0))
        self.assertIn("unbounded",self.b.reason)
        self.setUp()
        for i in range(1,4):
            r=fixture(i,i*40); r["capture_ms"]=None; r["latency_bound_ms"]=20
            self.b.update([r],i*40,True,True)
        self.assertEqual(self.b.state,"TRACKING")

    def test_ranges_and_follow_flag(self):
        """Purpose: Stop on beam failure and gate follow. Design: reverse disabled.
        Workflow: operator and sensor boundary. Data Handoff: BLOCKED zero output.
        """
        self.acquire()
        self.assertEqual(self.b.update([fixture(4,160)],160,False,True),(0,0))
        self.assertEqual(self.b.state,"BLOCKED")
        self.assertFalse(self.b.arm("follow"))

    def test_view_transform_and_missing_mapping(self):
        """Purpose: Verify stereo coordinate conversion. Design: explicit xywh
        normalized mapping, chosen right eye; other-eye boxes dropped.
        Workflow: adapter boundary. Data Handoff: one correct processing-view target.
        """
        mapping={"confidence_key":"score","box_key":"bounds","format":"xywh","units":"normalized"}
        payload={"person":[{"score":.9,"bounds":[.7,.2,.1,.2]}, {"score":.8,"bounds":[.1,.2,.1,.2]}]}
        records=normalize(payload,mapping,(1280,480),"stereo_horizontal","right",1,0,20)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["width"],640)
        self.assertAlmostEqual(records[0]["box"][0],256)
        self.assertAlmostEqual(records[0]["box"][2],384)
        with self.assertRaises(ValueError):
            normalize(payload,None,(1280,480),"stereo_horizontal","right",1,0)
        bad=fixture(1,0); bad["box"]=[0,0,700,480]
        with self.assertRaises(ValueError):
            validate_detection(bad)


class IntegrationTests(unittest.TestCase):
    """Purpose: Cross Python/C++ and UI boundaries. Design: actual host shared library,
    no duplicated Python motor simulator. Workflow: T2/T3. Data Handoff: assertions.
    """
    def test_mailbox_newest_only(self):
        """Purpose: Bound queues. Design: latest frame replaces old even when empty.
        Workflow: callback/control handoff. Data Handoff: no stale backlog.
        """
        box=LatestObservation(); box.put([1]); box.put([])
        self.assertEqual(box.take(),[]); self.assertIsNone(box.take())

    def test_cpp_command_watchdog_and_invalid_contract(self):
        """Purpose: Exercise logical contracts through typed C ABI. Design: epoch
        expiration/replay/invalid record stops immediately. Workflow: transport boundary.
        Data Handoff: schema-valid stopped telemetry and explicit rejection.
        """
        b=SimBridge(load_config())
        try:
            b.ranges(0); self.assertTrue(b.arm(1,0)); lease=b.lease(0)
            record={"schema_version":"1.0.0","session":1,"sequence":1,"generation":lease["generation"],
                "epoch":lease["epoch"],"mode":"turn","left":.1,"right":-.1,
                "observation":1,"observation_age_ms":0,"lifetime_ms":150}
            self.assertTrue(b.send(record,0)); self.assertGreater(b.telemetry(20)["applied"][0],0)
            self.assertEqual(b.telemetry(150)["applied"],[0,0])
            b.ranges(160); self.assertTrue(b.clear_fault(160)); self.assertTrue(b.arm(2,160))
            self.assertFalse(b.send(record,160)); self.assertEqual(b.telemetry(160)["state"],"FAULT")
            record["left"]=float("inf")
            with self.assertRaises(ValueError):
                b.send(record,161)
            self.assertEqual(b.telemetry(161)["applied"],[0,0])
        finally:
            b.close()

    def test_drift_blocks_loading(self):
        """Purpose: Reject independently changed MCU constants. Design: digest match.
        Workflow: bridge construction. Data Handoff: ValueError before arming.
        """
        config=load_config(); config["simulation"]["lease_ms"]=140
        with self.assertRaises(ValueError):
            SimBridge(config)

    def test_closed_native_owner_cannot_be_used(self):
        """Purpose: Prevent use-after-close at operator shutdown. Design: explicit
        native lifetime guard. Workflow: bridge shutdown boundary. Data Handoff: error.
        """
        b=SimBridge(load_config()); b.close(); b.close()
        with self.assertRaises(RuntimeError):
            b.telemetry(0)

    def test_vertical_slice_target_loss_obstacle_and_bridge_loss(self):
        """Purpose: Sustain tracking then stop for critical failures.
        Design: manual deterministic host timestamps; no real capture or GPIO.
        Workflow: perception-behavior-command-telemetry integration.
        Data Handoff: no motion after loss/obstacle/watchdog, no automatic rearm.
        """
        for scenario in ("lost","obstacle","bridge_loss","ambiguous"):
            r=Runtime()
            try:
                r.step(0); self.assertTrue(r.action("arm"))
                for now in range(10,251,10):
                    status=r.step(now)
                self.assertEqual(status["behavior"],"TRACKING")
                self.assertGreater(status["telemetry"]["applied"][0],0)
                r.scenario=scenario
                for now in range(260,501,10):
                    status=r.step(now)
                self.assertEqual(status["telemetry"]["applied"],[0,0])
                self.assertFalse(r.behavior.armed)
                r.scenario="tracking"
                self.assertEqual(r.step(510)["telemetry"]["applied"],[0,0])
            finally:
                r.close()

    def test_local_operator_security_and_stop(self):
        """Purpose: Test actual HTTP control boundary. Design: token, origin and host.
        Workflow: serve ephemeral loopback port, request page/status/control.
        Data Handoff: rejected unauthorized action and accepted immediate stop.
        """
        r=Runtime(); r.step(0); server=serve(r,0)
        connection=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=2)
        try:
            connection.request("GET","/"); response=connection.getresponse()
            self.assertEqual(response.status,200); html=response.read().decode()
            token=re.search(r'name="control-token" content="([a-f0-9]+)"',html).group(1)
            connection.request("GET","/api/status"); response=connection.getresponse()
            self.assertFalse(json.loads(response.read())["ready_for_autonomous_motion"])
            connection.request("POST","/api/control",json.dumps({"action":"arm"}),{"Content-Type":"application/json"})
            response=connection.getresponse(); self.assertEqual(response.status,403); response.read()
            headers={"X-Control-Token":token,"Content-Type":"application/json","Origin":"https://evil.invalid"}
            connection.request("POST","/api/control",json.dumps({"action":"arm"}),headers)
            response=connection.getresponse(); self.assertEqual(response.status,403); response.read()
            headers.pop("Origin")
            connection.request("POST","/api/control",json.dumps({"action":"stop"}),headers)
            response=connection.getresponse(); self.assertEqual(response.status,200)
            self.assertTrue(json.loads(response.read())["accepted"])
            connection.request("GET","/api/status",headers={"Host":"evil.invalid"})
            response=connection.getresponse(); self.assertEqual(response.status,403); response.read()
        finally:
            connection.close(); server.shutdown(); server.server_close(); r.close()

    def test_router_stop_timeout_and_motion_block(self):
        """Purpose: Check supported RPC scaffold. Design: bounded stop timeout;
        unavailable motion adapter rejects. Workflow: fake call records public args.
        Data Handoff: no claim of on-device transport validation.
        """
        class Fake:
            def call(self,name,*,timeout):
                return (name,timeout)
        bridge=RouterTransport(Fake())
        self.assertEqual(bridge.stop(),("cc_stop",.1))
        with self.assertRaises(RuntimeError):
            bridge.send({})

    def test_recording_opt_in_and_quota(self):
        """Purpose: Validate offline collection. Design: exclusive per-session file,
        fixed quota, normalized records; default runtime recording stays off.
        Workflow: temporary workspace output. Data Handoff: readable JSONL.
        """
        from chicken_chaser.recording import Recorder
        r=Runtime()
        try:
            self.assertIsNone(r.recorder)
        finally:
            r.close()
        with tempfile.TemporaryDirectory(dir=ROOT/"build") as folder:
            recorder=Recorder(folder,limit=1)
            self.assertTrue(recorder.add([fixture(1,0)]))
            self.assertFalse(recorder.add([fixture(2,40)]))
            recorder.close()
            records=json.loads(recorder.path.read_text().strip())
            self.assertEqual(records[0]["frame_id"],1)


if __name__ == "__main__":
    unittest.main()
