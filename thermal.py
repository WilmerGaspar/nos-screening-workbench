"""Published room-temperature bulk kappa. Lookup by composition, not string."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from formula_match import composition_key

KAPPA_RT: Dict[str, Dict] = {
    "NiAl": {"kappa": 92.2, "T_K": 300, "method": "laser-flash", "cte_ppm_k": 15.1, "form": "bulk",
             "citation": "Terada 2002, Mater. Trans. 43:3167, DOI 10.2320/matertrans.43.3167",
             "note": "B2 NiAl stoich."},
    "CoAl": {"kappa": 37.0, "T_K": 300, "method": "laser-flash", "cte_ppm_k": 15.0, "form": "bulk",
             "citation": "Terada 1995, Intermetallics 3:347, DOI 10.1016/0966-9795(95)94253-B",
             "note": "B2 CoAl. Order NiAl > CoAl > FeAl."},
    "FeAl": {"kappa": 12.0, "T_K": 300, "method": "laser-flash", "cte_ppm_k": 21.0, "form": "bulk",
             "citation": "Terada 1995, Intermetallics 3:347, DOI 10.1016/0966-9795(95)94253-B",
             "note": "B2 FeAl. Bond-coat / oxide, not heat path."},
    "Ni3Al": {"kappa": 28.5, "T_K": 300, "method": "laser-flash", "cte_ppm_k": 12.5, "form": "bulk",
              "citation": "Terada 2002 Mater. Trans. 43:3167; Williams JAP 61 (1987) 1486 DOI 10.1063/1.338929",
              "note": "L12 Ni3Al stoich."},
    "FeTi": {"kappa": 73.0, "T_K": 300, "method": "laser-flash", "cte_ppm_k": None, "form": "bulk",
             "citation": "Terada 1995, Intermetallics 3:347, DOI 10.1016/0966-9795(95)94253-B",
             "note": "Largest titanide in the 1995 series."},
    "NiGa": {"kappa": 23.0, "T_K": 300, "method": "laser-flash", "cte_ppm_k": None, "form": "bulk",
             "citation": "Terada 1995, Intermetallics 3:347, DOI 10.1016/0966-9795(95)94253-B",
             "note": "Largest gallide in the 1995 series."},
    "Ni3Ga": {"kappa": 32.8, "T_K": 300, "method": "laser-flash", "cte_ppm_k": None, "form": "bulk",
              "citation": "Hanai 1996, Intermetallics 4:S41, DOI 10.1016/0966-9795(96)00004-0",
              "note": "Largest among six L12 A3B in the abstract."},
    # Al-Cu intermetallics that grow at Al/Cu interfaces (wire bonds, Al-bearing layers on Cu).
    # Nazarahari et al., Adv. Eng. Mater. 2026, 28, e202501357, Table 3: k = alpha * cp * rho,
    # alpha by xenon flash, cp by DSC, rho by Archimedes, at ambient temperature. Cast and
    # homogenized 550 C / 48 h: bulk values, not thin-film values. The paper's zeta sample is
    # two-phase (zeta1 + eta2) and is left out on purpose. No CTE is reported.
    "Al4Cu9": {"kappa": 38.6, "T_K": None, "T_label": "ambient", "method": "xenon flash + DSC", "cte_ppm_k": None,
               "form": "bulk (cast)",
               "citation": "Nazarahari 2026, Adv. Eng. Mater. 28:e202501357, DOI 10.1002/adem.202501357",
               "note": "gamma1, 30.8 at.% Al nominal. Cu-rich Al-Cu IMCs conduct less than the others."},
    "Al2Cu3": {"kappa": 25.9, "T_K": None, "T_label": "ambient", "method": "xenon flash + DSC", "cte_ppm_k": None,
               "form": "bulk (cast)",
               "citation": "Nazarahari 2026, Adv. Eng. Mater. 28:e202501357, DOI 10.1002/adem.202501357",
               "note": "delta, 40 at.% Al nominal. Lowest k of the five phases measured."},
    "AlCu": {"kappa": 73.4, "T_K": None, "T_label": "ambient", "method": "xenon flash + DSC", "cte_ppm_k": None,
             "form": "bulk (cast)",
             "citation": "Nazarahari 2026, Adv. Eng. Mater. 28:e202501357, DOI 10.1002/adem.202501357",
             "note": "eta2, 48.75 at.% Al nominal (51.3 measured); twins seen in the sample."},
    "Al2Cu": {"kappa": 62.0, "T_K": None, "T_label": "ambient", "method": "xenon flash + DSC", "cte_ppm_k": None,
              "form": "bulk (cast)",
              "citation": "Nazarahari 2026, Adv. Eng. Mater. 28:e202501357, DOI 10.1002/adem.202501357",
              "note": "theta, 66.7 at.% Al nominal; Al4Cu9 precipitates at grain boundaries (k +/- 3.2)."},
}


def temp_label(rec: Dict) -> str:
    """'300 K' for rows with a stated temperature, 'ambient' when the source only says ambient."""
    if rec.get("T_K") is not None:
        return f"{rec['T_K']} K"
    return str(rec.get("T_label") or "T not stated")

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

def lookup(formula: str) -> Optional[Dict]:
    key = composition_key(formula)
    if not key:
        return None
    for name, data in KAPPA_RT.items():
        if composition_key(name) == key:
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
    notes.append(f"k = {kappa:.1f} W/mK ({rec.get('form', 'bulk')}, {temp_label(rec)}, {rec.get('method', 'laser-flash')}). {rec['citation']}")
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
