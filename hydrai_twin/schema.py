"""
Output record schema, per the original handoff's target dataset fields:
episode_id, timestamp, system_context, measurements, simulation_ground_truth, labels.

One record = one timestep. `episode_id` groups a sequence of records produced
by a single call to the episode generator.
"""

from __future__ import annotations

from typing import Any


def build_record(
    episode_id: str,
    timestamp_iso: str,
    system_context: dict[str, Any],
    measurements: dict[str, float],
    simulation_ground_truth: dict[str, Any],
    labels: dict[str, Any],
) -> dict[str, Any]:
    return {
        "episode_id": episode_id,
        "timestamp": timestamp_iso,
        "system_context": system_context,
        "measurements": measurements,
        "simulation_ground_truth": simulation_ground_truth,
        "labels": labels,
    }
