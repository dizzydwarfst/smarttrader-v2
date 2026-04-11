"""
serialization_utils.py - Shared helpers for JSON-safe payloads.
"""

from __future__ import annotations

import math


def make_json_safe(value, seen=None):
    """Convert nested objects into JSON-safe data without circular references."""
    if seen is None:
        seen = set()

    if isinstance(value, dict):
        obj_id = id(value)
        if obj_id in seen:
            return "<circular>"
        seen.add(obj_id)
        safe = {
            str(key): make_json_safe(item, seen)
            for key, item in value.items()
        }
        seen.remove(obj_id)
        return safe

    if isinstance(value, (list, tuple, set)):
        obj_id = id(value)
        if obj_id in seen:
            return ["<circular>"]
        seen.add(obj_id)
        safe = [make_json_safe(item, seen) for item in value]
        seen.remove(obj_id)
        return safe

    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return make_json_safe(value.item(), seen)
        except Exception:
            pass

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, (str, int, bool)) or value is None:
        return value

    return str(value)
