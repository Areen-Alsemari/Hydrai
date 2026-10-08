"""Process-independent seed derivation. Python's built-in hash() on strings
is randomized per process (PYTHONHASHSEED), so it must never be used to
derive seeds -- that silently makes "deterministic given base_seed" false
across runs. blake2b of the joined parts is stable everywhere."""

from __future__ import annotations

import hashlib


def stable_seed(*parts: object) -> int:
    digest = hashlib.blake2b("|".join(str(p) for p in parts).encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % (2**63)
