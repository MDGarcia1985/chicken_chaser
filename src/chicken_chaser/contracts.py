"""File: src/chicken_chaser/contracts.py
Purpose: Load authoritative YAML and validate logical records against JSON Schema.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: Reject duplicates, nonfinite numbers and missing motion prerequisites.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
"""
import json
import math
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


class UniqueLoader(yaml.SafeLoader):
    """Purpose: Reject ambiguous YAML. Design: SafeLoader only.
    Workflow: Used by load_config. Data Handoff: unique mappings or ValueError.
    """


def unique_mapping(loader, node, deep=False):
    """Purpose: Enforce unique keys. Design: no last-value-wins wiring.
    Workflow: YAML mapping construction. Data Handoff: dict or ValueError.
    """
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def finite_tree(value):
    """Purpose: Reject NaN/Inf. Design: recursive across all records.
    Workflow: Before schema validation. Data Handoff: ValueError on unsafe number.
    """
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Nonfinite number")
    if isinstance(value, dict):
        for item in value.values():
            finite_tree(item)
    elif isinstance(value, list):
        for item in value:
            finite_tree(item)


def validate(kind, value):
    """Purpose: Validate logical contracts. Design: closed versioned schemas.
    Workflow: At configuration and transport boundaries. Data Handoff: same value
    or jsonschema.ValidationError/ValueError; no hardware side effects.
    """
    finite_tree(value)
    schema = json.loads((ROOT / "schemas" / f"{kind}.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(value)
    return value


def load_config(path=ROOT / "config/runtime.yaml"):
    """Purpose: Read one runtime authority. Design: proposed architecture is separate.
    Workflow: Startup/generation. Data Handoff: validated configuration; errors abort.
    """
    value = yaml.load(Path(path).read_text(), Loader=UniqueLoader)
    validate("config", value)
    pins = [value["hardware"]["motors"][side][pin]
            for side in ("left", "right") for pin in ("in1", "in2")]
    known = [pin for pin in pins if pin is not None]
    if len(set(known)) != len(known):
        raise ValueError("Motor pins must be distinct")
    if value["hardware"]["enabled"]:
        raise ValueError("Device adapter not validated: hardware enable is inhibited in revision 1")
    sim, behavior = value["simulation"], value["behavior"]
    if sim["deadband"] >= sim["max_duty"]:
        raise ValueError("Motor deadband must be below limit")
    if behavior["max_forward"] + behavior["max_turn"] > sim["max_duty"]:
        raise ValueError("Behavior mix exceeds motor limit")
    return value
