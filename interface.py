"""Interface-first screening (v0.3).

Why this module exists
----------------------
v0.2 ranked cooling candidates with bulk kappa as 40 % of the score. For coatings of
5-50 um that is the wrong lever: the coating's own conduction term is small next to the
TIM, and what decides survival is the interface (CTE mismatch, adhesion, soundness).

This module therefore:
1. turns kappa into a *relevance check* (what share of the coating+TIM temperature drop
   the coating takes, and how much kappa the film actually needs);
2. scores the interface by the CTE mismatch against the materials the layer touches at
   the chosen site;
3. raises chemistry *watch items* for the coupon cross-section (not score penalties);
4. issues one decision verdict per phase.

Evidence tiers used here
------------------------
- Arithmetic: R'' = t / kappa (1-D conduction). No interface resistance is invented.
- Published: bulk kappa rows in thermal.KAPPA_RT (laser-flash, DOI).
- Published (2026): Al-Cu intermetallics are harder than Al and Cu and are the mechanical weak
  point of Al-Cu interfaces; defects cut interface k by about 30 % (Nazarahari et al.,
  DOI 10.1002/adem.202501357). Used only for the al_cu_imc watch item and Al-Cu kappa rows.
- Practitioner input (unpublished, collected 2026-10, materials engineers): interface
  stability and coating soundness decide before kappa; film kappa differs from bulk;
  Ni/Fe may diffuse into Cu; Al/Ti surface oxidation can affect interface stability.
  These only produce watch items and the coupon protocol, never a hidden score change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from die_stack import DIES
from stack_sites import site_spec
from thermal import SUBSTRATES, lookup

# Carried over from v0.2 (proceed_to_coupon required dCTE <= 8 ppm/K).
DCTE_COUPON_MAX = 8.0
# dCTE at which the interface score reaches 0 (same scale as thermal.cte_match_score).
DCTE_ZERO_SCORE = 16.0
# Unknown CTE is neither rewarded nor punished in the score; the verdict says "measure".
UNKNOWN_INTERFACE_SCORE = 0.5

DEFAULT_TIM_KAPPA = 4.0     # W/m.K, inside the 3-8 grease range of stack_sites.TIM_REF
DEFAULT_TIM_UM = 50.0       # um bond line: an editable assumption, not a measured value
DEFAULT_SHARE_MAX = 0.10    # coating may take at most 10 % of the coating+TIM dT

FLAG_TEXT = {
    "ni_fe_into_cu": "Ni/Fe next to Cu: look for an interdiffusion zone in the cross-section "
                     "(practitioner input; may be negligible near 150 C - measure, do not assume).",
    "al_ti_oxide": "Al/Ti in the coating: look for surface oxide at the interface in the "
                   "cross-section (practitioner input).",
    "cte_uncited": "Coating CTE has no DOI in this repo: verify the value before quoting it.",
    "cte_missing": "No CTE value for this phase: the interface verdict needs a coupon.",
    "die_cte_mismatch": "Coating touches a semiconductor die: metallic coatings sit far from the die CTE.",
    "al_cu_imc": "Al and Cu meet at this interface: Al-Cu intermetallics can grow there. They are harder "
                 "than Al and Cu (a mechanical weak point), and theta (Al2Cu) can turn into Al4Cu9 when Al "
                 "runs short, reported at 175-250 C in Al-Cu wire bonds (Xu et al. 2011, cited in "
                 "Nazarahari et al. 2026, DOI 10.1002/adem.202501357). Measure the IMC thickness at each checkpoint.",
}

VERDICTS = (
    "proceed_to_coupon",
    "coupon_high_cte_risk",
    "coupon_cte_unknown",
    "kappa_significant",
    "process_veto",
)


@dataclass
class ThermalRelevance:
    kappa_bulk: Optional[float]
    kappa_needed: float
    share_bulk: Optional[float]
    film_margin: Optional[float]
    dt_coat_k: Optional[float]
    dt_tim_k: float
    verdict: str
    notes: List[str] = field(default_factory=list)


@dataclass
class InterfaceResult:
    neighbors: List[Tuple[str, float]]
    coat_cte: Optional[float]
    dcte_max: Optional[float]
    worst_neighbor: Optional[str]
    score: float
    flags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def thermal_relevance(
    kappa_bulk: Optional[float],
    thickness_um: float,
    tim_kappa: float = DEFAULT_TIM_KAPPA,
    tim_um: float = DEFAULT_TIM_UM,
    area_cm2: float = 1.0,
    power_w: float = 50.0,
    share_max: float = DEFAULT_SHARE_MAX,
) -> ThermalRelevance:
    """Share of the (coating + TIM) temperature drop taken by the coating.

    Area cancels in the share, so the verdict does not depend on A; the dT values do.
    kappa_needed is the film kappa at which the coating takes exactly `share_max`.
    Bulk kappa is an upper bound for a deposited film, so film_margin says how much of
    the bulk value the film may lose before the coating becomes a meaningful term.
    """
    if thickness_um <= 0 or tim_kappa <= 0 or tim_um <= 0 or area_cm2 <= 0:
        raise ValueError("thickness, TIM kappa, TIM thickness and area must be positive")
    if not 0.0 < share_max < 1.0:
        raise ValueError("share_max must be between 0 and 1")
    t_coat = float(thickness_um) * 1e-6
    a_m2 = float(area_cm2) * 1e-4
    r_tim = float(tim_um) * 1e-6 / float(tim_kappa)          # K.m2/W
    dt_tim = float(power_w) * r_tim / a_m2
    kappa_needed = t_coat * (1.0 - share_max) / (share_max * r_tim)
    notes = [
        f"TIM term: {tim_um:g} um at {tim_kappa:g} W/mK -> dT_TIM = {dt_tim:.2f} K at {power_w:g} W over {area_cm2:g} cm2 (editable assumption).",
        f"Film kappa needed to keep the coating <= {share_max:.0%} of the coating+TIM dT: {kappa_needed:.1f} W/mK.",
    ]
    if kappa_bulk is None:
        notes.append("No citable bulk kappa: measure film kappa on the coupon only if the interface survives.")
        return ThermalRelevance(None, round(kappa_needed, 2), None, None, None, round(dt_tim, 3), "kappa_unknown", notes)
    r_coat = t_coat / float(kappa_bulk)
    share = r_coat / (r_coat + r_tim)
    dt_coat = float(power_w) * r_coat / a_m2
    margin = 1.0 - kappa_needed / float(kappa_bulk)
    notes.append(f"Coating at bulk kappa {kappa_bulk:g} W/mK: dT_coat = {dt_coat:.2f} K, {share:.1%} of the coating+TIM dT.")
    if share <= share_max:
        notes.append(f"The film may lose up to {margin:.0%} of its bulk kappa before it matters.")
        verdict = "kappa_not_limiting"
    else:
        notes.append("Even at bulk kappa (an upper bound) the coating is a meaningful thermal term.")
        verdict = "kappa_limiting"
    return ThermalRelevance(
        float(kappa_bulk), round(kappa_needed, 2), round(share, 4),
        round(margin, 4) if margin > 0 else 0.0,
        round(dt_coat, 4), round(dt_tim, 3), verdict, notes,
    )


# Lowest measured k among the cited Al-Cu IMC rows (Al2Cu3, 25.9 W/mK; DOI 10.1002/adem.202501357).
ALCU_DOI = "10.1002/adem.202501357"


def alcu_imc_kappa_min() -> Tuple[str, float]:
    from thermal import KAPPA_RT
    rows = [(name, float(r["kappa"])) for name, r in KAPPA_RT.items() if ALCU_DOI in r.get("citation", "")]
    return min(rows, key=lambda x: x[1])


def imc_thickness_threshold_um(kappa_imc: float, tim_kappa: float = DEFAULT_TIM_KAPPA,
                               tim_um: float = DEFAULT_TIM_UM, share_max: float = DEFAULT_SHARE_MAX) -> float:
    """IMC thickness (um) at which an IMC layer alone takes `share_max` of the IMC+TIM dT.

    share = R_imc / (R_imc + R_TIM) <= s  ->  t <= s / (1 - s) * R_TIM * kappa_imc
    Area cancels. 1-D, no interface resistance invented.
    """
    if kappa_imc <= 0 or tim_kappa <= 0 or tim_um <= 0 or not 0.0 < share_max < 1.0:
        raise ValueError("kappa, TIM values must be positive and share_max in (0, 1)")
    r_tim = float(tim_um) * 1e-6 / float(tim_kappa)
    return share_max / (1.0 - share_max) * r_tim * float(kappa_imc) * 1e6


def site_neighbors(site_key: str, die: str = "Si", substrate: str = "Cu") -> List[Tuple[str, float]]:
    """(label, CTE ppm/K) of each material the coating touches at this site."""
    out: List[Tuple[str, float]] = []
    for ref, label in site_spec(site_key)["neighbors"]:
        if ref == "die":
            spec = DIES.get(die) or DIES["Si"]
            out.append((f"{die} die", float(spec["cte_ppm_k"])))
        elif ref == "substrate":
            spec = SUBSTRATES.get(substrate) or SUBSTRATES["Cu"]
            out.append((f"{substrate} ({label})", float(spec["cte_ppm_k"])))
        else:
            out.append((label, float(SUBSTRATES[ref]["cte_ppm_k"])))
    return out


def _neighbor_materials(site_key: str, die: str, substrate: str) -> List[str]:
    mats = []
    for ref, _ in site_spec(site_key)["neighbors"]:
        mats.append(die if ref == "die" else substrate if ref == "substrate" else ref)
    return mats


def chemistry_flags(composition: Dict[str, float], neighbor_materials: List[str]) -> List[str]:
    present = {el for el, amt in (composition or {}).items() if amt}
    flags = []
    if "Cu" in neighbor_materials and present & {"Ni", "Fe"}:
        flags.append("ni_fe_into_cu")
    if present & {"Al", "Ti"}:
        flags.append("al_ti_oxide")
    if any(m in DIES for m in neighbor_materials):
        flags.append("die_cte_mismatch")
    if ("Al" in present and "Cu" in neighbor_materials) or ("Cu" in present and "Al" in neighbor_materials):
        flags.append("al_cu_imc")
    return flags


def dcte_score(dcte: float) -> float:
    return max(0.0, min(1.0, 1.0 - float(dcte) / DCTE_ZERO_SCORE))


def evaluate_interface(formula: str, composition: Dict[str, float], site_key: str,
                       die: str = "Si", substrate: str = "Cu") -> InterfaceResult:
    neighbors = site_neighbors(site_key, die, substrate)
    flags = chemistry_flags(composition, _neighbor_materials(site_key, die, substrate))
    rec = lookup(formula)
    coat_cte = None if rec is None else rec.get("cte_ppm_k")
    notes: List[str] = []
    if coat_cte is None:
        flags.append("cte_missing")
        notes.append("No coating CTE in the catalog: interface score set to neutral 0.5.")
        return InterfaceResult(neighbors, None, None, None, UNKNOWN_INTERFACE_SCORE, flags, notes)
    if not rec.get("cte_source"):
        flags.append("cte_uncited")
    deltas = [(label, abs(float(coat_cte) - cte)) for label, cte in neighbors]
    worst_label, worst = max(deltas, key=lambda x: x[1])
    for label, d in deltas:
        notes.append(f"CTE coat {coat_cte:.1f} vs {label} -> dCTE {d:.1f} ppm/K.")
    return InterfaceResult(neighbors, float(coat_cte), round(worst, 2), worst_label, round(dcte_score(worst), 4), flags, notes)


def decide(veto: bool, heat_path: bool, relevance_verdict: str, iface: InterfaceResult) -> str:
    """One verdict per phase, in priority order."""
    if veto:
        return "process_veto"
    if heat_path and relevance_verdict == "kappa_limiting":
        return "kappa_significant"
    if iface.dcte_max is None:
        return "coupon_cte_unknown"
    if iface.dcte_max > DCTE_COUPON_MAX:
        return "coupon_high_cte_risk"
    return "proceed_to_coupon"
