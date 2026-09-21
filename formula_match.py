from __future__ import annotations
import math
import re
from typing import Dict, FrozenSet, Optional, Tuple

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")

def parse_counts(formula: str) -> Dict[str, int]:
    raw = "".join(ch for ch in (formula or "") if ch.isalnum())
    if not raw:
        return {}
    counts: Dict[str, int] = {}
    for el, n in _TOKEN.findall(raw):
        counts[el] = counts.get(el, 0) + (int(n) if n else 1)
    return counts

def _gcd_all(nums) -> int:
    vals = [int(v) for v in nums if v]
    if not vals:
        return 1
    g = vals[0]
    for v in vals[1:]:
        g = math.gcd(g, v)
    return g or 1

def composition_key(formula: str) -> FrozenSet[Tuple[str, int]]:
    counts = parse_counts(formula)
    if not counts:
        return frozenset()
    g = _gcd_all(counts.values())
    return frozenset((el, amt // g) for el, amt in counts.items())

def same_phase(a: str, b: str) -> bool:
    ka, kb = composition_key(a), composition_key(b)
    return bool(ka) and ka == kb

def match_row(formula: str, rows, name_field: str = "phase"):
    key = composition_key(formula)
    if not key:
        return None
    for row in rows:
        if composition_key(str(row.get(name_field) or "")) == key:
            return dict(row)
    return None
