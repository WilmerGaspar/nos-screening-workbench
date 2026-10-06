"""One evaluation path for the app and the CLI (v0.3).

candidates (demo or Materials Project, already NOS-scored)
  -> manufacturability (process, temperature)
  -> interface (CTE vs the materials at the layer site + chemistry watch items)
  -> thermal relevance (coating share of the coating+TIM dT; kappa the film needs)
  -> 1-D stack numbers (R_coat, dT, Tj lower bound) where a citable kappa exists
  -> verdict -> rank (reliability weights in cooling mode, NOS/manuf otherwise)
"""
from __future__ import annotations

from typing import Dict, List

from die_stack import evaluate_stack
from interface import (
    DEFAULT_SHARE_MAX,
    DEFAULT_TIM_KAPPA,
    DEFAULT_TIM_UM,
    FLAG_TEXT,
    decide,
    evaluate_interface,
    thermal_relevance,
)
from manufacturability import evaluate as evaluate_manuf
from ranking import (
    DEFAULT_NOS_WEIGHT,
    RELIABILITY_WEIGHTS,
    attach_ranks,
    attach_reliability_ranks,
    pareto_front,
)
from stack_sites import DEFAULT_SITE, site_spec
from thermal import evaluate_thermal

DEFAULTS = {
    "process": "pvd",
    "temp": 150,
    "application": "si_power_module",
    "substrate": "Cu",
    "die": "Si",
    "site": DEFAULT_SITE,
    "thickness_um": 20.0,
    "area_cm2": 1.0,
    "power_w": 50.0,
    "t_sink_c": 45.0,
    "budget": 0.05,
    "tim_kappa": DEFAULT_TIM_KAPPA,
    "tim_um": DEFAULT_TIM_UM,
    "share_max": DEFAULT_SHARE_MAX,
    "cooling": True,
    "w_nos": DEFAULT_NOS_WEIGHT,
}


def evaluate_row(cand: Dict, cfg: Dict) -> Dict:
    c = {**DEFAULTS, **{k: v for k, v in cfg.items() if v is not None}}
    site = site_spec(c["site"])
    manuf = evaluate_manuf(cand, c["process"], c["temp"])
    legacy = evaluate_thermal(cand["formula"], c["substrate"], c["application"])
    iface = evaluate_interface(cand["formula"], cand.get("composition") or {}, c["site"], c["die"], c["substrate"])
    rel = thermal_relevance(
        legacy.kappa_wm_k, c["thickness_um"], c["tim_kappa"], c["tim_um"],
        c["area_cm2"], c["power_w"], c["share_max"],
    )
    stack = evaluate_stack(
        cand["formula"], thickness_um=c["thickness_um"], area_cm2=c["area_cm2"],
        power_w=c["power_w"], t_sink_c=c["t_sink_c"], budget_k_per_w=c["budget"],
        die=c["die"], substrate=c["substrate"],
    )
    verdict = decide(manuf.veto, bool(site["heat_path"]), rel.verdict, iface)
    return {
        **cand,
        "manuf_score": manuf.score,
        "manuf_risk": manuf.risk_level,
        "manuf_notes": manuf.notes,
        "veto": manuf.veto,
        # interface (v0.3)
        "interface_score": iface.score,
        "coat_cte": iface.coat_cte,
        "dcte_max": iface.dcte_max,
        "worst_neighbor": iface.worst_neighbor,
        "neighbors": iface.neighbors,
        "interface_notes": iface.notes,
        "flags": iface.flags,
        "flag_notes": [FLAG_TEXT[f] for f in iface.flags if f in FLAG_TEXT],
        # thermal relevance (v0.3)
        "heat_path": bool(site["heat_path"]),
        "kappa_wm_k": legacy.kappa_wm_k,
        "thermal_citation": legacy.citation,
        "kappa_needed": rel.kappa_needed,
        "coat_share": rel.share_bulk,
        "film_margin": rel.film_margin,
        "dt_coat": rel.dt_coat_k,
        "dt_tim": rel.dt_tim_k,
        "relevance_verdict": rel.verdict,
        "relevance_notes": rel.notes,
        # 1-D stack (unchanged physics, kept for the lab sheet)
        "r_coat": stack.r_coat_k_per_w,
        "tj_lower_bound": stack.tj_lower_bound_c,
        # legacy v0.2 kappa score: kept in the data for comparison, not used in the rank
        "kappa_score_v02": legacy.score,
        "verdict": verdict,
    }


def evaluate_candidates(cands: List[Dict], cfg: Dict) -> List[Dict]:
    rows = [evaluate_row(c, cfg) for c in cands]
    if not rows:
        return []
    cooling = cfg.get("cooling", True)
    if cooling:
        ranked = attach_reliability_ranks(rows, cfg.get("weights") or RELIABILITY_WEIGHTS)
    else:
        ranked = attach_ranks(rows, w_nos=cfg.get("w_nos", DEFAULT_NOS_WEIGHT))
    front = set(pareto_front(ranked, cooling=cooling))
    for r in ranked:
        r["pareto"] = (r.get("material_id") in front) or (r.get("formula") in front)
    return ranked
