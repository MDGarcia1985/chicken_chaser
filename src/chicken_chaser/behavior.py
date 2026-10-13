"""File: src/chicken_chaser/behavior.py
Purpose: Stable target association and bounded visual steering.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: PWM is not velocity; association cannot guarantee identity after crossing.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
"""
from .vision import age_ms, validate_detection
from jsonschema import ValidationError


def overlap(a, b):
    """Purpose: Associate boxes by IoU. Design: class is checked separately.
    Workflow: frame selection. Data Handoff: dimensionless overlap [0,1].
    """
    x1, y1, x2, y2 = a["box"]
    u1, v1, u2, v2 = b["box"]
    intersection = max(0, min(x2,u2)-max(x1,u1))*max(0, min(y2,v2)-max(y1,v1))
    return intersection/((x2-x1)*(y2-y1)+(u2-u1)*(v2-v1)-intersection)


def nearby(a, b):
    """Purpose: Allow gradual motion without confidence switching.
    Design: normalized centroid distance OR box IoU. Workflow: association.
    Data Handoff: candidate boolean; multiple matches remain ambiguous.
    """
    if (a["width"],a["height"]) != (b["width"],b["height"]):
        return False
    ax, ay, bx, by = sum(a["box"][::2])/2, sum(a["box"][1::2])/2, sum(b["box"][::2])/2, sum(b["box"][1::2])/2
    return overlap(a,b) >= .1 or ((ax-bx)/a["width"])**2+((ay-by)/a["height"])**2 <= .15**2


class Behavior:
    """Purpose: Acquire and retain a visual target. Design: explicit operator arm,
    fresh unique frames, no online adaptation. Workflow: loop-owned instance.
    Data Handoff: state, selected record, signed duty requests or stop.
    """
    def __init__(self, config):
        """Purpose: Set stopped defaults. Design: injected validated behavior config.
        Workflow: startup. Data Handoff: disarmed state and empty association.
        """
        self.config = config
        self.state = "DISARMED"
        self.armed = False
        self.selected = None
        self.stable = 0
        self.last_frame = 0
        self.last_received = -1
        self.reason = ""
        self.mode = "turn"

    def arm(self, mode="turn"):
        """Purpose: Explicit simulation/verified operator arm. Design: follow opt-in.
        Workflow: after MCU prerequisites. Data Handoff: acquiring, zero output.
        """
        if self.state == "FAULT" or mode not in ("turn", "follow"):
            return False
        if mode == "follow" and not self.config["follow_enabled"]:
            return False
        self.disarm()
        self.armed = True
        self.mode = mode
        self.state = "ACQUIRING"
        return True

    def disarm(self):
        """Purpose: Revoke target authority. Design: no automatic rearm.
        Workflow: stop/disconnect/operator. Data Handoff: empty acquisition.
        """
        self.armed = False
        self.selected = None
        self.stable = 0
        if self.state != "FAULT":
            self.state = "DISARMED"

    def clear_fault(self):
        """Purpose: Deliberately clear stopped perception faults. Design: no rearm.
        Workflow: operator after MCU clearance checks. Data Handoff: DISARMED state.
        """
        if self.armed:
            return False
        self.state = "DISARMED"
        self.reason = ""
        self.selected = None
        self.stable = 0
        return True

    def lose(self, state, reason):
        """Purpose: Stop on unsafe perception. Design: reacquire across fresh frames.
        Workflow: invalid/stale/ambiguous frame. Data Handoff: zero duties.
        """
        self.state = state
        self.reason = reason
        self.selected = None
        self.stable = 0
        return (0.0,0.0)

    def update(self, records, now, front_clear, rear_clear):
        """Purpose: Produce one command per usable new frame.
        Design: retain spatial association; ambiguous matches stop. Capture time or
        measured transport bound required. Workflow: newest bounded observation.
        Data Handoff: normalized left/right requests; exceptions become FAULT.
        """
        if not self.armed:
            return (0.0,0.0)
        if not front_clear or not rear_clear:
            return self.lose("BLOCKED", "range_clearance")
        try:
            for record in records:
                validate_detection(record)
            candidates = [r for r in records if r["label"] == self.config["target_label"]
                and r["confidence"] >= self.config["confidence"]]
            if not candidates:
                return self.lose("TARGET_LOST", "no_target")
            keys = {(r["frame_id"],r["received_ms"],r["width"],r["height"]) for r in candidates}
            if len(keys) != 1:
                return self.lose("FAULT", "mixed_frames")
            first = candidates[0]
            frame_id = first["frame_id"]
            if frame_id <= self.last_frame or first["received_ms"] <= self.last_received:
                return self.lose("TARGET_LOST", "replayed_frame")
            self.last_frame = frame_id
            self.last_received = first["received_ms"]
            if any(age_ms(r,now) >= self.config["observation_age_ms"] for r in candidates):
                return self.lose("TARGET_LOST", "stale_or_unbounded_latency")
            if self.selected:
                if age_ms(self.selected,now) >= self.config["observation_age_ms"]:
                    self.selected = None
                    self.stable = 0
                else:
                    candidates = [r for r in candidates if nearby(self.selected,r)]
            if len(candidates) != 1:
                return self.lose("TARGET_LOST", "ambiguous_or_missing_association")
            self.selected = candidates[0]
            self.stable += 1
            self.reason = ""
            if self.stable < self.config["stable_frames"]:
                self.state = "ACQUIRING"
                return (0.0,0.0)
            self.state = "TRACKING"
            center = (self.selected["box"][0]+self.selected["box"][2])/2
            error = 2*(center/self.selected["width"]-self.config["aim_x"])
            turn = 0 if abs(error) <= self.config["deadband"] else max(-self.config["max_turn"],min(self.config["max_turn"],error*self.config["gain"]))
            forward = self.config["max_forward"] if self.mode == "follow" and abs(error) <= self.config["deadband"] else 0
            return (forward+turn,forward-turn)
        except (ValueError, KeyError, TypeError, ValidationError) as error:
            return self.lose("FAULT",str(error))
