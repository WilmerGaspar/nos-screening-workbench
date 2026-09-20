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


def pareto_front(rows: List[Dict], cooling: bool = False) -> List[str]:
    """Non-dominated in (NOS, manuf) or (kappa_score, manuf) when cooling."""
    front = []
    xkey = "kappa_score" if cooling else "NOS"
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
