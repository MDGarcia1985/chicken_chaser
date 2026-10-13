"""File: src/chicken_chaser/vision.py
Purpose: Normalize verified payload mappings into one processing-view contract.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: No assumed Brick box keys, stereo layout or capture clock.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
"""
from math import isfinite
from .contracts import validate


def validate_detection(record):
    """Purpose: Check geometry beyond schema. Design: xyxy in the chosen view.
    Workflow: perception boundary. Data Handoff: valid record or ValueError.
    """
    validate("detection", record)
    x1, y1, x2, y2 = record["box"]
    if not (0 <= x1 < x2 <= record["width"] and 0 <= y1 < y2 <= record["height"]):
        raise ValueError("Box outside processing view or empty")
    return record


def normalize(payload, mapping, dimensions, layout, view, frame_id, received_ms, latency_bound_ms=None):
    """Purpose: Adapt a captured-and-verified label-to-list payload.
    Design: explicit confidence/box key mapping, format and units; crossing-eye
    boxes rejected. No guessed timestamp field. Workflow: after device probe.
    Data Handoff: validated records with receipt time; capture time unknown.
    """
    if not isinstance(mapping, dict) or set(mapping) != {"confidence_key", "box_key", "format", "units"}:
        raise ValueError("Verified payload mapping is required")
    if mapping["format"] not in ("xyxy", "xywh") or mapping["units"] not in ("pixels", "normalized"):
        raise ValueError("Unsupported coordinates")
    width, height = dimensions
    if layout == "single" and view == "single":
        xoffset, output_width = 0, width
    elif layout == "stereo_horizontal" and view in ("left", "right") and width % 2 == 0:
        output_width = width // 2
        xoffset = 0 if view == "left" else output_width
    else:
        raise ValueError("Negotiated layout and processing view unresolved")
    result = []
    if not isinstance(payload, dict):
        raise ValueError("Expected label-to-list payload")
    for label, values in payload.items():
        if not isinstance(values, list):
            raise ValueError("Expected records per label")
        for value in values:
            box = list(value[mapping["box_key"]])
            if len(box) != 4 or not all(isinstance(v, (int, float)) and isfinite(v) for v in box):
                raise ValueError("Invalid raw box")
            if mapping["units"] == "normalized":
                box = [box[0]*width, box[1]*height, box[2]*width, box[3]*height]
            if mapping["format"] == "xywh":
                box[2] += box[0]
                box[3] += box[1]
            if not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
                raise ValueError("Raw box outside negotiated frame")
            if box[0] < xoffset or box[2] > xoffset+output_width:
                continue
            box[0] -= xoffset
            box[2] -= xoffset
            result.append(validate_detection({"schema_version": "1.0.0", "label": label,
                "confidence": value[mapping["confidence_key"]], "box": box,
                "coordinates": "xyxy_pixels_processing_view", "width": output_width, "height": height,
                "frame_id": frame_id, "received_ms": received_ms, "capture_ms": None,
                "latency_bound_ms": latency_bound_ms}))
    return result


def age_ms(record, now):
    """Purpose: Bound actual observation age. Design: receipt alone insufficient;
    capture_ms is permitted only after same-clock normalization. Workflow: behavior.
    Data Handoff: conservative ms or infinity when timing unavailable/future.
    """
    if record["capture_ms"] is not None:
        age = now-record["capture_ms"]
        if record["capture_ms"] > record["received_ms"]:
            return float("inf")
    elif record["latency_bound_ms"] is not None:
        age = now-record["received_ms"]+record["latency_bound_ms"]
    else:
        return float("inf")
    return age if age >= 0 and now >= record["received_ms"] else float("inf")
