"""Combine NOS, manufacturability and optional thermal fit into one rank."""

from __future__ import annotations

from typing import Dict, List, Optional

DEFAULT_NOS_WEIGHT = 0.55
COOLING_WEIGHTS = {"nos": 0.30, "manuf": 0.30, "thermal": 0.40}


def combined_score(
    nos: float,
    manuf: float,
    w_nos: float = DEFAULT_NOS_WEIGHT,
    thermal: Optional[float] = None,
    w_thermal: float = 0.0,
) -> float:
    if thermal is None or w_thermal <= 0:
        return w_nos * float(nos) + (1.0 - w_nos) * float(manuf)
    w_manuf = max(0.0, 1.0 - w_nos - w_thermal)
    return w_nos * float(nos) + w_manuf * float(manuf) + w_thermal * float(thermal)


def attach_ranks(
    rows: List[Dict],
    w_nos: float = DEFAULT_NOS_WEIGHT,
    w_thermal: float = 0.0,
) -> List[Dict]:
    out = []
    for row in rows:
        item = dict(row)
        item["combined"] = round(
            combined_score(
                item["NOS"],
                item["manuf_score"],
                w_nos=w_nos,
                thermal=item.get("kappa_score"),
                w_thermal=w_thermal,
            ),
            4,
        )
        out.append(item)
    out.sort(key=lambda r: (r["combined"], r["NOS"]), reverse=True)
    for i, row in enumerate(out, start=1):
        row["rank"] = i
    return out


# --- v0.3: reliability-first ranking for power-electronics interfaces -----------------
# Bulk kappa no longer enters the score. It acts only as a gate (verdict "kappa_significant")
# when the coating takes a meaningful share of the coating+TIM temperature drop.
RELIABILITY_WEIGHTS = {"nos": 0.25, "manuf": 0.35, "interface": 0.40}
VERDICT_CAPS = {"kappa_significant": 0.45, "process_veto": 0.25}
# Rank by verdict tier first, score second. A phase with unknown CTE must not win
# just because "unknown" is scored neutral: known-and-testable comes before unknown.
VERDICT_ORDER = {
    "proceed_to_coupon": 0,
    "coupon_high_cte_risk": 1,
    "coupon_cte_unknown": 2,
    "kappa_significant": 3,
    "process_veto": 4,
}


def _tier(row: Dict) -> int:
    return VERDICT_ORDER.get(row.get("verdict") or "", 2)


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    keys = ("nos", "manuf", "interface")
    vals = {k: max(0.0, float(weights.get(k, 0.0))) for k in keys}
    total = sum(vals.values())
    if total <= 0:
        return dict(RELIABILITY_WEIGHTS)
    return {k: v / total for k, v in vals.items()}


def reliability_score(row: Dict, weights: Dict[str, float]) -> float:
    w = normalize_weights(weights)
    score = (
        w["nos"] * float(row["NOS"])
        + w["manuf"] * float(row["manuf_score"])
        + w["interface"] * float(row["interface_score"])
    )
    cap = VERDICT_CAPS.get(row.get("verdict") or "")
    if cap is not None:
        score = min(score, cap)
    return score


def attach_reliability_ranks(rows: List[Dict], weights: Optional[Dict[str, float]] = None) -> List[Dict]:
    weights = weights or RELIABILITY_WEIGHTS
    out = []
    for row in rows:
        item = dict(row)
        item["combined"] = round(reliability_score(item, weights), 4)
        out.append(item)
    out.sort(key=lambda r: (-_tier(r), r["combined"], r["interface_score"], r["NOS"]), reverse=True)
    for i, row in enumerate(out, start=1):
        row["rank"] = i
    return out


def weight_grid(step: float = 0.05, w_min: float = 0.10) -> List[Dict[str, float]]:
    """All (nos, manuf, interface) weight sets on a grid, each >= w_min, summing to 1."""
    n = int(round(1.0 / step))
    lo = int(round(w_min / step))
    grid = []
    for a in range(lo, n + 1):
        for b in range(lo, n + 1 - a):
            c = n - a - b
            if c >= lo:
                grid.append({"nos": a * step, "manuf": b * step, "interface": c * step})
    return grid


def rank_stability(rows: List[Dict], step: float = 0.05, w_min: float = 0.10) -> List[Dict]:
    """How often each phase ranks first across the weight grid.

    Answers "why these weights?" before anyone asks: if the leader stays first across
    most reasonable weightings, the choice does not hinge on the default 25/35/40.
    """
    if not rows:
        return []
    grid = weight_grid(step, w_min)
    wins: Dict[str, int] = {}
    for w in grid:
        best = max(rows, key=lambda r: (-_tier(r), reliability_score(r, w), r["interface_score"], r["NOS"]))
        name = best.get("formula") or best.get("material_id")
        wins[name] = wins.get(name, 0) + 1
    total = len(grid)
    out = [{"formula": k, "share_first": v / total, "n": v, "of": total} for k, v in wins.items()]
    out.sort(key=lambda d: d["share_first"], reverse=True)
    return out


def pareto_front(rows: List[Dict], cooling: bool = False, xkey: Optional[str] = None) -> List[str]:
    """Non-dominated in (x, manuf). x = interface_score when cooling (v0.3), NOS otherwise."""
    front = []
    if xkey is None:
        xkey = "interface_score" if cooling else "NOS"
    for a in rows:
        ax = a.get(xkey)
        if ax is None:
            ax = a["NOS"]
        dominated = False
        for b in rows:
            if b is a:
                continue
            bx = b.get(xkey)
            if bx is None:
                bx = b["NOS"]
            if (
                bx >= ax
                and b["manuf_score"] >= a["manuf_score"]
                and (bx > ax or b["manuf_score"] > a["manuf_score"])
            ):
                dominated = True
                break
        if not dominated:
            front.append(a.get("material_id") or a.get("formula"))
    return front
