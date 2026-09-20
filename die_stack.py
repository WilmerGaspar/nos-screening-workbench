"""Die + 1-D coating thermal resistance. R_coat = t/(kappa A). Does not invent interface R."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from thermal import lookup, SUBSTRATES

DIES: Dict[str, Dict] = {
    "Si": {"eg_ev_300k": 1.12, "kappa_wm_k": 148.0, "cte_ppm_k": 2.6, "role": "CMOS / IGBT die", "citation": "Sze & Ng, typical 300 K values."},
    "SiC": {"eg_ev_300k": 3.26, "kappa_wm_k": 370.0, "cte_ppm_k": 4.0, "role": "4H-SiC power die", "citation": "Typical 4H-SiC 300 K handbook range."},
    "GaN": {"eg_ev_300k": 3.44, "kappa_wm_k": 160.0, "cte_ppm_k": 5.6, "role": "GaN HEMT / power die", "citation": "Mid-range bulk GaN 300 K screening value."},
    "GaAs": {"eg_ev_300k": 1.42, "kappa_wm_k": 55.0, "cte_ppm_k": 5.7, "role": "RF die", "citation": "Typical GaAs 300 K handbook values."},
}

@dataclass
class StackResult:
    r_coat_k_per_w: Optional[float]
    dt_coat_k: Optional[float]
    tj_lower_bound_c: Optional[float]
    budget_k_per_w: float
    within_budget: Optional[bool]
    kappa_used: Optional[float]
    thickness_m: float
    area_m2: float
    notes: List[str] = field(default_factory=list)
    verdict: str = "missing_thermal_data"

def r_layer(thickness_m: float, kappa_wm_k: float, area_m2: float) -> float:
    if kappa_wm_k <= 0 or area_m2 <= 0:
        raise ValueError("kappa and area must be positive")
    return float(thickness_m) / (float(kappa_wm_k) * float(area_m2))

def evaluate_stack(formula: str, thickness_um: float = 20.0, area_cm2: float = 1.0, power_w: float = 50.0, t_sink_c: float = 45.0, budget_k_per_w: float = 0.05, die: str = "Si", substrate: str = "Cu") -> StackResult:
    notes: List[str] = []
    t_m = max(float(thickness_um), 0.0) * 1e-6
    a_m2 = max(float(area_cm2), 1e-6) * 1e-4
    rec = lookup(formula)
    if rec is None:
        notes.append("No published phase kappa: R_coat is not computed.")
        return StackResult(None, None, None, budget_k_per_w, None, None, t_m, a_m2, notes, "missing_thermal_data")
    kappa = float(rec["kappa"])
    r_coat = r_layer(t_m, kappa, a_m2)
    dt = float(power_w) * r_coat
    tj_lb = float(t_sink_c) + dt
    ok = r_coat <= budget_k_per_w
    notes.append(f"R_coat = t/(kA) = {r_coat:.4f} K/W (t={thickness_um} um, A={area_cm2} cm2, k={kappa} W/mK).")
    notes.append(rec["citation"])
    notes.append(f"Coating-only dT at {power_w} W: {dt:.2f} K. Tj lower bound {tj_lb:.1f} C. Missing TIM/interface.")
    verdict = "stack_within_budget" if ok else "stack_over_budget"
    return StackResult(round(r_coat, 5), round(dt, 3), round(tj_lb, 2), budget_k_per_w, ok, kappa, t_m, a_m2, notes, verdict)
