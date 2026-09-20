"""
NOS scoring primitives.

All formulas are deterministic and documented in METHODOLOGY.md.
This module has no I/O and no API calls.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

# Crustal abundance (ppm). Rudnick & Gao (2014), Treatise on Geochemistry.
CRUSTAL_ABUNDANCE_PPM: Dict[str, float] = {
    "O": 461000, "Si": 282000, "Al": 82300, "Fe": 56300, "Ca": 41500,
    "Na": 23600, "Mg": 23300, "K": 21500, "Ti": 5650, "Mn": 774,
    "P": 655, "Zn": 67, "Cu": 27, "Ni": 47, "Cr": 92, "V": 97,
    "Zr": 132, "Sn": 2.1, "W": 1.0, "Co": 24.3, "Pb": 14.8, "Ga": 16,
    "Ge": 1.4, "Nb": 8.0, "Y": 19, "Mo": 1.1, "Sr": 320, "Ba": 456,
    "C": 324, "S": 621, "N": 83, "F": 557, "Cl": 472, "Li": 16,
    "B": 11, "Be": 1.9, "Sc": 14, "Co": 24.3, "As": 4.8, "Se": 0.09,
    "Rb": 49, "Ag": 0.056, "Cd": 0.09, "In": 0.056, "Sb": 0.2,
    "Te": 0.001, "I": 0.7, "Cs": 2.0, "La": 31, "Ce": 63, "Hf": 5.3,
    "Ta": 0.9, "Re": 0.0002, "Os": 0.000041, "Ir": 0.000037,
    "Pt": 0.0005, "Au": 0.0013, "Hg": 0.03, "Bi": 0.18, "Th": 5.6, "U": 1.3,
}

TIER_WEIGHT = {
    "Experimentally verified": 1.00,
    "Partially backed": 0.75,
    "Well-calculated (DFT)": 0.55,
    "Exploratory": 0.30,
}

NOS_WEIGHTS = {
    "stability": 0.25,
    "mechanical": 0.30,
    "abundance": 0.25,
    "confidence": 0.20,
}

# Pugh (1954): B/G > 1.75 correlates with ductile behaviour.
PUGH_DUCTILE_THRESHOLD = 1.75


def crustal_score(composition: Dict[str, float]) -> float:
    """Mass-fraction-weighted log abundance, normalized to crustal oxygen."""
    total_mass = sum(composition.values())
    if total_mass <= 0:
        return 0.0
    weighted_ppm = 0.0
    for el, frac in composition.items():
        ppm = CRUSTAL_ABUNDANCE_PPM.get(el, 0.5)
        weighted_ppm += (frac / total_mass) * ppm
    if weighted_ppm <= 0:
        return 0.0
    score = math.log10(weighted_ppm + 1.0) / math.log10(461000.0)
    return max(0.0, min(1.0, score))


def stability_score(e_above_hull: Optional[float]) -> float:
    """Exponential decay; 0.05 eV/atom is the conventional metastability window."""
    if e_above_hull is None:
        return 0.0
    return math.exp(-float(e_above_hull) / 0.05)


def mechanical_score(bulk_modulus: Optional[float], shear_modulus: Optional[float]) -> float:
    """Equal-weight VRH bulk/shear, capped at 400 GPa."""
    if bulk_modulus is None or shear_modulus is None:
        return 0.0
    b = min(max(float(bulk_modulus), 0.0), 400.0) / 400.0
    s = min(max(float(shear_modulus), 0.0), 400.0) / 400.0
    return 0.5 * b + 0.5 * s


def pugh_ratio(bulk_modulus: Optional[float], shear_modulus: Optional[float]) -> Optional[float]:
    if bulk_modulus is None or shear_modulus is None:
        return None
    if float(shear_modulus) <= 0:
        return None
    return float(bulk_modulus) / float(shear_modulus)


def confidence_tier(
    is_theoretical: bool,
    has_icsd: bool,
    flagged_gnome: bool,
    has_full_elasticity: bool,
    stability_ok: bool,
) -> str:
    if not is_theoretical and has_icsd:
        return "Experimentally verified"
    if is_theoretical and has_icsd:
        return "Partially backed"
    if (not flagged_gnome) and has_full_elasticity and stability_ok:
        return "Well-calculated (DFT)"
    return "Exploratory"


def nos_score(stability: float, mechanical: float, abundance: float, confidence: float) -> float:
    return (
        NOS_WEIGHTS["stability"] * stability
        + NOS_WEIGHTS["mechanical"] * mechanical
        + NOS_WEIGHTS["abundance"] * abundance
        + NOS_WEIGHTS["confidence"] * confidence
    )
