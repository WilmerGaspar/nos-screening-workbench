"""Process-aware manufacturability scoring. Screening prior, not qualification."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from scoring import PUGH_DUCTILE_THRESHOLD, pugh_ratio

AQUEOUS_PLATEABLE = {
    "Zn", "Ni", "Cr", "Cu", "Fe", "Co", "Sn", "Ag", "Au", "Cd",
    "In", "Pb", "Mn", "Rh", "Pd", "Pt",
}
COMMON_PVD_TARGETS = {
    "Al", "Ti", "Cr", "Ni", "Cu", "Zn", "Fe", "Zr", "Nb", "Mo",
    "Ta", "W", "Si", "C", "Ag", "Au", "V", "Co", "Sn",
}
SPRAY_KNOWN_FAMILIES = (("Ni", "Al"), ("Fe", "Al"), ("Ni", "Cr"), ("Co", "Cr"), ("Co", "Al"))
HIGH_TEMP_ANCHORS = {
    "Al13Fe4": {"max_temp_c": 500.0, "bonus": 0.12, "note": "Al13Fe4 / Al2O3 scale; Krasnowski 2022."},
    "Fe4Al13": {"max_temp_c": 500.0, "bonus": 0.12, "note": "Fe4Al13 alumina former; Krasnowski 2022."},
    "Zn13Fe": {"max_temp_c": 200.0, "bonus": -0.10, "note": "Zn-Fe zeta; service ~200 C."},
}

@dataclass
class ManufacturabilityResult:
    score: float
    risk_level: str
    notes: List[str] = field(default_factory=list)
    process_fit: float = 0.0
    thermal_fit: float = 0.0
    mechanical_fit: float = 0.0
    evidence_fit: float = 0.0
    recommended_processes: List[str] = field(default_factory=list)
    veto: bool = False

def _elements(composition: Dict[str, float]) -> List[str]:
    return [el for el, amt in composition.items() if amt and amt > 0]

def _atomic_fraction(composition: Dict[str, float], element: str) -> float:
    total = sum(composition.values())
    return 0.0 if total <= 0 else float(composition.get(element, 0.0)) / total

def _formula_key(formula: str) -> str:
    return "".join(ch for ch in (formula or "") if ch.isalnum())

def _risk(score: float, veto: bool) -> str:
    if veto:
        return "unsuitable"
    if score >= 0.75:
        return "low"
    if score >= 0.55:
        return "medium"
    if score >= 0.35:
        return "high"
    return "very_high"

def evaluate(material: Dict, process: str, max_service_temp_c: float) -> ManufacturabilityResult:
    notes: List[str] = []
    veto = False
    formula = material.get("formula") or ""
    composition: Dict[str, float] = material.get("composition") or {}
    elements = _elements(composition)
    process_key = (process or "pvd").lower().replace(" ", "_").replace("/", "_")
    if process_key in {"thermal_spray___hvof", "thermal_spray_hvof", "hvof", "thermal_spray"}:
        process_key = "thermal_spray"
    if process_key in {"electroplating", "electrodeposition"}:
        process_key = "electroplating"

    process_fit = 0.55
    recommended: List[str] = []
    if process_key == "electroplating":
        total = sum(composition.values()) or 1.0
        plateable_frac = sum(v for el, v in composition.items() if el in AQUEOUS_PLATEABLE) / total
        process_fit = 0.15 + 0.80 * plateable_frac
        hard = [el for el in elements if el not in AQUEOUS_PLATEABLE]
        if plateable_frac < 0.35:
            veto = True
            notes.append("Aqueous electroplating veto: majority of chemistry is not plateable from water baths.")
        elif hard:
            notes.append("Partial electroplating fit. Difficult: " + ", ".join(hard))
        else:
            notes.append("Constituents are aqueous-plateable. Expect a conversion anneal.")
        recommended.append("electroplating + conversion anneal" if plateable_frac >= 0.35 else "not electroplating")
    elif process_key == "thermal_spray":
        family_hit = any(a in elements and b in elements for a, b in SPRAY_KNOWN_FAMILIES)
        process_fit = 0.70 if family_hit else 0.42
        if _atomic_fraction(composition, "Zn") >= 0.25:
            process_fit -= 0.22
            notes.append("High Zn is a poor HVOF match.")
        notes.append("Published spray trail." if family_hit else "No spray literature trail in the ruleset.")
        recommended.append("HVOF / thermal spray")
    else:
        common = sum(1 for el in elements if el in COMMON_PVD_TARGETS)
        process_fit = 0.48 + 0.10 * min(common, 4)
        notes.append("PVD can deposit most intermetallics; residual stress is the risk.")
        recommended.append("PVD (sputter / arc)")
    process_fit = max(0.0, min(1.0, process_fit))

    thermal_fit = 0.70
    if max_service_temp_c > 200 and _atomic_fraction(composition, "Zn") >= 0.20:
        thermal_fit -= 0.35
        notes.append("Service T above the Zn-rich window (~200 C).")
    if max_service_temp_c > 450:
        formers = [el for el in ("Al", "Cr", "Si") if el in elements]
        if formers:
            thermal_fit += 0.10
            notes.append("T>450 C with oxide formers: " + ", ".join(formers))
        else:
            thermal_fit -= 0.20
            notes.append("T>450 C without Al/Cr/Si scale former.")
    if max_service_temp_c > 600:
        thermal_fit -= 0.12
        notes.append("T>600 C: interdiffusion and softening dominate.")
    key = _formula_key(formula)
    for anchor, data in HIGH_TEMP_ANCHORS.items():
        if _formula_key(anchor) == key:
            notes.append(data["note"])
            if data["max_temp_c"] < max_service_temp_c:
                thermal_fit -= 0.20
            else:
                thermal_fit += data["bonus"]
    thermal_fit = max(0.0, min(1.0, thermal_fit))

    ratio = pugh_ratio(material.get("bulk_modulus"), material.get("shear_modulus"))
    if ratio is None:
        mechanical_fit = 0.45
        notes.append("No elasticity data; Pugh not computed.")
    else:
        mechanical_fit = max(0.0, min(1.0, (ratio - 0.6) / 2.0))
        if ratio < PUGH_DUCTILE_THRESHOLD:
            notes.append(f"Pugh B/G = {ratio:.2f} < 1.75 brittle tendency (Pugh 1954).")
        else:
            notes.append(f"Pugh B/G = {ratio:.2f} >= 1.75 more ductile tendency.")

    if material.get("has_icsd") and not material.get("theoretical"):
        evidence_fit = 0.90
    elif material.get("has_icsd"):
        evidence_fit = 0.70
    elif material.get("theoretical"):
        evidence_fit = 0.28
    else:
        evidence_fit = 0.50

    score = 0.35 * process_fit + 0.25 * thermal_fit + 0.20 * mechanical_fit + 0.20 * evidence_fit
    if veto:
        score = min(score, 0.25)
    score = max(0.0, min(1.0, score))
    return ManufacturabilityResult(
        score=round(score, 4),
        risk_level=_risk(score, veto),
        notes=notes,
        process_fit=round(process_fit, 4),
        thermal_fit=round(thermal_fit, 4),
        mechanical_fit=round(mechanical_fit, 4),
        evidence_fit=round(evidence_fit, 4),
        recommended_processes=recommended,
        veto=veto,
    )
