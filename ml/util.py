from __future__ import annotations

import numpy as np


def strip_private(obj):
    """Recursively drop keys starting with '_' and the pooled 'oof' arrays, so
    result dicts are JSON-serializable."""
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not str(k).startswith("_") and k != "oof"}
    if isinstance(obj, (list, tuple)):
        return [strip_private(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
