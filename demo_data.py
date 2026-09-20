"""Offline demonstration set. source='demo' must never be labelled as live MP."""
from __future__ import annotations
from typing import Dict, List

DEMO_CANDIDATES: List[Dict] = [
    {"material_id": "demo-FeAl", "formula": "FeAl", "composition": {"Fe": 1, "Al": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 152.0, "shear_modulus": 73.0, "source": "demo", "note": "B2 FeAl."},
    {"material_id": "demo-Fe3Al", "formula": "Fe3Al", "composition": {"Fe": 3, "Al": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 140.0, "shear_modulus": 68.0, "source": "demo", "note": "D03 Fe3Al."},
    {"material_id": "demo-Al13Fe4", "formula": "Al13Fe4", "composition": {"Al": 13, "Fe": 4}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 110.0, "shear_modulus": 55.0, "source": "demo", "note": "Krasnowski 2022."},
    {"material_id": "demo-Fe2Al5", "formula": "Fe2Al5", "composition": {"Fe": 2, "Al": 5}, "e_above_hull": 0.01, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 105.0, "shear_modulus": 50.0, "source": "demo"},
    {"material_id": "demo-FeAl3", "formula": "FeAl3", "composition": {"Fe": 1, "Al": 3}, "e_above_hull": 0.005, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 100.0, "shear_modulus": 48.0, "source": "demo"},
    {"material_id": "demo-Zn13Fe", "formula": "Zn13Fe", "composition": {"Zn": 13, "Fe": 1}, "e_above_hull": 0.02, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 80.0, "shear_modulus": 35.0, "source": "demo", "note": "Galvanizing zeta."},
    {"material_id": "demo-ZnFe", "formula": "ZnFe", "composition": {"Zn": 1, "Fe": 1}, "e_above_hull": 0.04, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 95.0, "shear_modulus": 42.0, "source": "demo"},
    {"material_id": "demo-NiAl", "formula": "NiAl", "composition": {"Ni": 1, "Al": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 160.0, "shear_modulus": 80.0, "source": "demo", "note": "B2 NiAl. k=92.2 W/mK Terada 1995."},
    {"material_id": "demo-CoAl", "formula": "CoAl", "composition": {"Co": 1, "Al": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 165.0, "shear_modulus": 85.0, "source": "demo", "note": "B2 CoAl. k~37 W/mK."},
    {"material_id": "demo-Ni3Al", "formula": "Ni3Al", "composition": {"Ni": 3, "Al": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 170.0, "shear_modulus": 90.0, "source": "demo"},
    {"material_id": "demo-Ni2Al3", "formula": "Ni2Al3", "composition": {"Ni": 2, "Al": 3}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 145.0, "shear_modulus": 72.0, "source": "demo"},
    {"material_id": "demo-TiAl", "formula": "TiAl", "composition": {"Ti": 1, "Al": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 110.0, "shear_modulus": 70.0, "source": "demo"},
    {"material_id": "demo-Ti3Al", "formula": "Ti3Al", "composition": {"Ti": 3, "Al": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 120.0, "shear_modulus": 55.0, "source": "demo"},
    {"material_id": "demo-TiAl3", "formula": "TiAl3", "composition": {"Ti": 1, "Al": 3}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 100.0, "shear_modulus": 82.0, "source": "demo"},
    {"material_id": "demo-FeCr", "formula": "FeCr", "composition": {"Fe": 1, "Cr": 1}, "e_above_hull": 0.03, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 180.0, "shear_modulus": 90.0, "source": "demo"},
    {"material_id": "demo-Ni3Ti", "formula": "Ni3Ti", "composition": {"Ni": 3, "Ti": 1}, "e_above_hull": 0.0, "theoretical": False, "has_icsd": True, "flagged_gnome": False, "bulk_modulus": 175.0, "shear_modulus": 85.0, "source": "demo"},
    {"material_id": "demo-exploratory-Al2Fe", "formula": "Al2Fe", "composition": {"Al": 2, "Fe": 1}, "e_above_hull": 0.12, "theoretical": True, "has_icsd": False, "flagged_gnome": True, "bulk_modulus": None, "shear_modulus": None, "source": "demo"},
    {"material_id": "demo-WAl", "formula": "WAl", "composition": {"W": 1, "Al": 1}, "e_above_hull": 0.08, "theoretical": True, "has_icsd": False, "flagged_gnome": False, "bulk_modulus": 200.0, "shear_modulus": 140.0, "source": "demo"},
]

def matches_elements(composition: Dict[str, float], wanted: List[str], exact_chemsys: bool) -> bool:
    present = {el for el, amt in composition.items() if amt}
    wanted_set = set(wanted)
    if exact_chemsys:
        return present == wanted_set
    return wanted_set.issubset(present)

def load_demo(elements: List[str], exact_chemsys: bool = True) -> List[Dict]:
    rows = [dict(r) for r in DEMO_CANDIDATES if matches_elements(r["composition"], elements, exact_chemsys)]
    return rows if rows else [dict(r) for r in DEMO_CANDIDATES]
