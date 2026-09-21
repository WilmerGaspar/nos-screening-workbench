"""Published room-temperature bulk kappa. No invented numbers."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# cite_ok rows only. CoAl / FeAl / Ni3Al wait for the figure.
KAPPA_RT: Dict[str, Dict] = {
    "NiAl": {
        "kappa": 92.2, "T_K": 300, "method": "laser-flash",
        "cte_ppm_k": 15.1, "form": "bulk",
        "citation": "Terada 2002, Mater. Trans. 43:3167, DOI 10.2320/matertrans.43.3167",
        "note": "B2 NiAl stoich. Maximum at stoichiometry.",
    },
    "FeTi": {
        "kappa": 73.0, "T_K": 300, "method": "laser-flash",
        "cte_ppm_k": None, "form": "bulk",
        "citation": "Terada 1995, Intermetallics 3:347, DOI 10.1016/0966-9795(95)94253-B",
        "note": "Largest titanide in the 1995 series.",
    },
    "NiGa": {
        "kappa": 23.0, "T_K": 300, "method": "laser-flash",
        "cte_ppm_k": None, "form": "bulk",
        "citation": "Terada 1995, Intermetallics 3:347, DOI 10.1016/0966-9795(95)94253-B",
        "note": "Largest gallide in the 1995 series. Backlog.",
    },
    "Ni3Ga": {
        "kappa": 32.8, "T_K": 300, "method": "laser-flash",
        "cte_ppm_k": None, "form": "bulk",
        "citation": "Hanai 1996, Intermetallics 4:S41, DOI 10.1016/0966-9795(96)00004-0",
        "note": "Abstract: 32.8 largest among six L12 A3B. Backlog.",
    },
}

SUBSTRATES = {
    "Cu": {"cte_ppm_k": 16.5, "kappa": 401.0, "role": "cold plate"},
    "Al": {"cte_ppm_k": 23.1, "kappa": 237.0, "role": "heat sink"},
    "Si": {"cte_ppm_k": 2.6, "kappa": 149.0, "role": "die"},
    "SiC": {"cte_ppm_k": 4.0, "kappa": 370.0, "role": "WBG die"},
    "Ni": {"cte_ppm_k": 13.4, "kappa": 90.9, "role": "barrier"},
    "316SS": {"cte_ppm_k": 16.0, "kappa": 15.0, "role": "hardware"},
}

APPLICATIONS = {
    "cpu_cold_plate": {"label": "CPU / datacenter cold plate", "default_temp_c": 95, "default_substrate": "Cu", "min_kappa": 40.0, "blurb": "kappa and CTE-to-Cu dominate."},
    "si_power_module": {"label": "Si IGBT / MOSFET module", "default_temp_c": 150, "default_substrate": "Cu", "min_kappa": 25.0, "blurb": "Junction ~150 C."},
    "sic_power_module": {"label": "SiC power module", "default_temp_c": 185, "default_substrate": "Cu", "min_kappa": 25.0, "blurb": "Junction 175-200 C."},
    "generic_coating": {"label": "Generic high-T coating (not cooling)", "default_temp_c": 450, "default_substrate": "316SS", "min_kappa": None, "blurb": "No kappa gate."},
}

VERDICT_COPY = {
    "proceed_to_coupon": "Follow with a coupon. kappa and CTE are defensible.",
    "calphad_then_coupon": "Run equilibrium at junction T, then a coupon.",
    "not_a_heat_spreader": "Do not use as the heat path. Bond-coat / oxide only.",
    "missing_thermal_data": "No citable kappa. Out of the cooling rank.",
}

@dataclass
class ThermalResult:
    score: float
    kappa_wm_k: Optional[float]
    cte_ppm_k: Optional[float]
    dcte_ppm_k: Optional[float]
    citation: Optional[str]
    approximate: bool
    notes: List[str] = field(default_factory=list)
    verdict: str = "missing_thermal_data"
    heat_spreader_ok: bool = False

def _norm_formula(formula: str) -> str:
    return "".join(ch for ch in (formula or "") if ch.isalnum())

def lookup(formula: str) -> Optional[Dict]:
    key = _norm_formula(formula)
    for name, data in KAPPA_RT.items():
        if _norm_formula(name) == key:
            return {"phase": name, **data}
    return None

def kappa_score(kappa: float) -> float:
    k = max(float(kappa), 1.0)
    return max(0.0, min(1.0, math.log10(k) / math.log10(200.0)))

def cte_match_score(cte_coat: float, cte_sub: float) -> float:
    delta = abs(float(cte_coat) - float(cte_sub))
    return max(0.0, min(1.0, 1.0 - delta / 16.0))

def evaluate_thermal(formula: str, substrate: str = "Cu", application: str = "si_power_module") -> ThermalResult:
    notes: List[str] = []
    app = APPLICATIONS.get(application, APPLICATIONS["si_power_module"])
    sub = SUBSTRATES.get(substrate, SUBSTRATES["Cu"])
    rec = lookup(formula)
    if rec is None:
        notes.append("No citable RT kappa (DOI + T + method). Do not invent a number.")
        return ThermalResult(0.15, None, None, None, None, False, notes, "missing_thermal_data", False)
    kappa = float(rec["kappa"])
    cte = rec.get("cte_ppm_k")
    notes.append(f"k = {kappa:.1f} W/mK (bulk, {rec.get('T_K', 300)} K, {rec.get('method', 'laser-flash')}). {rec['citation']}")
    notes.append("k is bulk at ~300 K, not coating k and not TIM k.")
    s_k = kappa_score(kappa)
    dcte = None
    s_cte = 0.55
    if cte is not None:
        dcte = abs(float(cte) - float(sub["cte_ppm_k"]))
        s_cte = cte_match_score(cte, sub["cte_ppm_k"])
        notes.append(f"CTE coat {cte:.1f} vs {substrate} {sub['cte_ppm_k']:.1f} (d={dcte:.1f} ppm/K).")
    min_k = app.get("min_kappa")
    spreader_ok = min_k is None or kappa >= float(min_k)
    if min_k is not None and not spreader_ok:
        notes.append(f"Below the {app['label']} gate of {min_k:.0f} W/mK.")
    score = 0.70 * s_k + 0.30 * s_cte
    if not spreader_ok:
        score = min(score, 0.45)
        verdict = "not_a_heat_spreader"
    elif kappa >= 70 and (dcte is None or dcte <= 8):
        verdict = "proceed_to_coupon"
    else:
        verdict = "calphad_then_coupon"
    return ThermalResult(
        round(max(0.0, min(1.0, score)), 4),
        kappa, cte, None if dcte is None else round(dcte, 2),
        rec["citation"], False, notes, verdict, spreader_ok and kappa >= 40,
    )
