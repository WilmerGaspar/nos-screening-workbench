"""
Materials Project query + NOS scoring.

Live mode requires MP_API_KEY. Offline mode uses demo_data.py.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from scoring import (
    TIER_WEIGHT,
    confidence_tier,
    crustal_score,
    mechanical_score,
    nos_score,
    stability_score,
)


def _composition_from_mp(doc) -> Dict[str, float]:
    try:
        return {str(k): float(v) for k, v in doc.composition.get_el_amt_dict().items()}
    except Exception:
        return {}


def _icsd_ids(doc) -> List:
    db = getattr(doc, "database_IDs", None) or {}
    return db.get("icsd", []) if isinstance(db, dict) else []


def _vrh(mod) -> Optional[float]:
    if not mod:
        return None
    return getattr(mod, "vrh", None)


def score_record(raw: Dict) -> Dict:
    e_hull = raw.get("e_above_hull")
    bulk = raw.get("bulk_modulus")
    shear = raw.get("shear_modulus")
    has_el = bulk is not None and shear is not None
    stability_ok = e_hull is not None and float(e_hull) < 0.05
    flagged = bool(raw.get("flagged_gnome"))
    if flagged is False and raw.get("theoretical") and not raw.get("has_icsd") and not has_el:
        flagged = True

    tier = confidence_tier(
        is_theoretical=bool(raw.get("theoretical")),
        has_icsd=bool(raw.get("has_icsd")),
        flagged_gnome=flagged,
        has_full_elasticity=has_el,
        stability_ok=stability_ok,
    )
    s_stab = stability_score(e_hull)
    s_mech = mechanical_score(bulk, shear)
    s_abund = crustal_score(raw.get("composition") or {})
    s_conf = TIER_WEIGHT[tier]
    return {
        **raw,
        "flagged_gnome": flagged,
        "tier": tier,
        "score_stability": round(s_stab, 4),
        "score_mechanical": round(s_mech, 4),
        "score_abundance": round(s_abund, 4),
        "score_confidence": round(s_conf, 4),
        "NOS": round(nos_score(s_stab, s_mech, s_abund, s_conf), 4),
        "data_gap_mechanical": not has_el,
    }


def run_demo(elements: List[str], exact_chemsys: bool = True) -> List[Dict]:
    from demo_data import load_demo

    rows = [score_record(r) for r in load_demo(elements, exact_chemsys=exact_chemsys)]
    rows.sort(key=lambda r: r["NOS"], reverse=True)
    return rows


def run_live(
    elements: List[str],
    api_key: Optional[str] = None,
    max_results: int = 120,
    exact_chemsys: bool = True,
) -> List[Dict]:
    api_key = api_key or os.environ.get("MP_API_KEY", "")
    if not api_key:
        raise RuntimeError("MP_API_KEY is not set.")

    from mp_api.client import MPRester

    fields = [
        "material_id",
        "formula_pretty",
        "composition",
        "energy_above_hull",
        "theoretical",
        "database_IDs",
        "bulk_modulus",
        "shear_modulus",
    ]

    query = {
        "fields": fields,
        "num_elements": (len(elements), len(elements)) if exact_chemsys else (2, 4),
    }
    if exact_chemsys:
        query["chemsys"] = "-".join(sorted(elements))
    else:
        query["elements"] = elements

    results: List[Dict] = []
    with MPRester(api_key) as mpr:
        docs = mpr.materials.summary.search(**query)
        for d in docs[:max_results]:
            bulk = _vrh(getattr(d, "bulk_modulus", None))
            shear = _vrh(getattr(d, "shear_modulus", None))
            raw = {
                "material_id": d.material_id,
                "formula": d.formula_pretty,
                "composition": _composition_from_mp(d),
                "e_above_hull": d.energy_above_hull,
                "theoretical": bool(d.theoretical),
                "has_icsd": bool(_icsd_ids(d)),
                "flagged_gnome": False,
                "bulk_modulus": bulk,
                "shear_modulus": shear,
                "source": "materials_project",
            }
            results.append(score_record(raw))

    uniq = {}
    for row in results:
        uniq[row["material_id"]] = row
    out = list(uniq.values())
    out.sort(key=lambda r: r["NOS"], reverse=True)
    return out
