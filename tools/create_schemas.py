"""File: tools/create_schemas.py
Purpose: Generate closed JSON Schemas and the safe runtime authority.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: Simulation defaults are unvalidated physically. DEV-2026-10-12-001.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def obj(properties):
    """Purpose: Close a record. Design: all fields required, no extras.
    Workflow: Schema construction. Data Handoff: schema object.
    """
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def number(lo, hi):
    """Purpose: Define finite bounded duty/units. Design: shared schema generation.
    Workflow: Field construction. Data Handoff: numeric schema.
    """
    return {"type": "number", "minimum": lo, "maximum": hi}


def integer(lo, hi):
    """Purpose: Bound counters to MCU representation. Design: unsigned range.
    Workflow: Field construction. Data Handoff: integer schema.
    """
    return {"type": "integer", "minimum": lo, "maximum": hi}


def nullable(schema):
    """Purpose: Preserve unresolved prerequisites. Design: explicit null.
    Workflow: Hardware field construction. Data Handoff: union schema.
    """
    return {"anyOf": [schema, {"type": "null"}]}


def write(name, schema):
    """Purpose: Publish contracts. Design: reproducible JSON draft 2020-12.
    Workflow: Run from repository root. Data Handoff: schema file.
    """
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": name, **schema}
    path = ROOT / "schemas" / f"{name}.schema.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(schema, indent=2) + "\n")


def main():
    """Purpose: Define configuration/detection/bridge/model contracts.
    Design: generators share field definitions; runtime verifies each record.
    Workflow: Developer command. Data Handoff: schemas consumed by Python and generator.
    """
    boolean = {"type": "boolean"}
    text = {"type": "string", "minLength": 1, "maxLength": 128}
    counter = integer(1, 2147483647)
    version = {"const": "1.0.0"}
    pin = nullable(integer(0, 255))
    motor = obj({"in1": pin, "in2": pin, "invert": nullable(boolean)})
    write("config", obj({
        "schema_version": version, "prototype_revision": {"const": 1},
        "ready_for_autonomous_motion": {"const": False},
        "hardware": obj({"enabled": {"const": False}, "vm_v": nullable(number(6.5, 45)),
            "current_limit_a": nullable(number(0.01, 3.6)),
            "pins_verified": {"const": False}, "power_verified": {"const": False},
            "timing_verified": {"const": False},
            "motors": obj({"left": motor, "right": motor}),
            "front_uart": nullable(text), "front_baud": nullable(integer(1, 1000000)),
            "rear_bus": nullable(text), "rear_address": nullable(integer(8, 119)),
            "pwm_bits": nullable(integer(1, 16)), "control_period_ms": nullable(integer(1, 1000))}),
        "simulation": obj({"lease_ms": integer(1, 500), "sensor_age_ms": integer(1, 1000),
            "clearance_mm": integer(1, 8000), "max_duty": number(0.01, 1),
            "deadband": number(0, 0.5), "ramp_per_s": number(0.01, 10),
            "reversal_ms": integer(1, 2000)}),
        "behavior": obj({"target_label": text, "confidence": number(0, 1),
            "stable_frames": integer(2, 100), "observation_age_ms": integer(1, 1000),
            "gain": number(0, 1), "aim_x": number(0, 1), "deadband": number(0, .5),
            "max_turn": number(0, .5), "max_forward": number(0, .5),
            "follow_enabled": boolean, "reverse_enabled": {"const": False},
            "recording_enabled": boolean}),
        "camera": obj({"negotiated_width": nullable(integer(1, 8192)),
            "negotiated_height": nullable(integer(1, 8192)),
            "layout": nullable({"enum": ["single", "stereo_horizontal"]}),
            "view": nullable({"enum": ["single", "left", "right"]}),
            "payload_mapping": nullable(obj({"confidence_key": text, "box_key": text,
                "format": {"enum": ["xyxy", "xywh"]}, "units": {"enum": ["pixels", "normalized"]}})),
            "latency_bound_ms": nullable(integer(1, 1000))})}))
    write("command", obj({"schema_version": version, "session": counter,
        "sequence": counter, "generation": counter, "epoch": counter,
        "mode": {"enum": ["turn", "follow"]}, "left": number(-1, 1), "right": number(-1, 1),
        "observation": counter, "observation_age_ms": integer(0, 1000),
        "lifetime_ms": integer(1, 500)}))
    write("lease", obj({"schema_version": version, "session": counter,
        "generation": counter, "epoch": counter, "remaining_ms": integer(0, 500)}))
    write("stop", obj({"schema_version": version, "action": {"const": "stop"}}))
    write("detection", obj({"schema_version": version, "label": text,
        "confidence": number(0, 1), "box": {"type": "array", "items": number(0, 8192), "minItems": 4, "maxItems": 4},
        "coordinates": {"const": "xyxy_pixels_processing_view"}, "width": integer(1, 8192),
        "height": integer(1, 8192), "frame_id": counter,
        "received_ms": number(0, 1e15), "capture_ms": nullable(number(0, 1e15)),
        "latency_bound_ms": nullable(integer(1, 1000))}))
    sample = obj({"status": {"enum": ["valid", "invalid", "stale", "unavailable"]},
        "distance_mm": nullable(integer(1, 8000)), "age_ms": nullable(integer(0, 2147483647))})
    write("telemetry", obj({"schema_version": version, "session": integer(0, 2147483647),
        "generation": integer(0, 2147483647), "ack_sequence": integer(0, 2147483647),
        "state": {"enum": ["DISARMED", "TRACKING", "BLOCKED", "FAULT"]},
        "commanded": {"type": "array", "items": number(-1, 1), "minItems": 2, "maxItems": 2},
        "applied": {"type": "array", "items": number(-1, 1), "minItems": 2, "maxItems": 2},
        "front": sample, "rear": sample, "fault": {"type": "string"}, "physical_outputs": {"const": False}}))
    write("model", obj({"schema_version": version, "identity": nullable(text),
        "artifact": nullable(text), "sha256": nullable({"type": "string", "pattern": "^[a-f0-9]{64}$"}),
        "labels": nullable({"type": "array", "items": text, "uniqueItems": True}),
        "preprocessing": nullable(text), "confidence": number(0, 1),
        "dependencies": {"type": "object", "additionalProperties": {"type": "string"}},
        "evaluation_record": nullable(text), "rollback_artifact": nullable(text)}))


if __name__ == "__main__":
    main()
