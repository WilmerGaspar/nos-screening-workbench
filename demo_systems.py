DEMO_SYSTEMS = [
    {"key": "cited7", "label": "7 fases citadas  ·  dictamen termico completo"},
    {"key": "Ni,Al", "label": "Ni-Al  ·  NiAl + Ni3Al (IGBT)"},
    {"key": "Co,Al", "label": "Co-Al  ·  CoAl 37 W/mK"},
    {"key": "Fe,Al", "label": "Fe-Al  ·  FeAl 12 W/mK (no spreader)"},
    {"key": "Fe,Ti", "label": "Fe-Ti  ·  FeTi 73 W/mK"},
    {"key": "Ni,Ga", "label": "Ni-Ga  ·  NiGa + Ni3Ga"},
    {"key": "Ti,Al", "label": "Ti-Al  ·  sin k citable"},
    {"key": "Ni,Ti", "label": "Ni-Ti  ·  sin k citable"},
    {"key": "Co,Ti", "label": "Co-Ti  ·  sin k citable"},
    {"key": "Zn,Fe", "label": "Zn-Fe  ·  galvanizado"},
    {"key": "Fe,Cr", "label": "Fe-Cr  ·  sin k citable"},
    {"key": "Al,Cu", "label": "Al-Cu  ·  intermetálicos de la interfaz Al/Cu (Nazarahari 2026)", "reference": True},
]
CITED_PHASES = ["NiAl", "Ni3Al", "CoAl", "FeAl", "FeTi", "NiGa", "Ni3Ga"]


def is_reference(key):
    """Reference systems: measured phases shown for their kappa, not coatings to deposit.
    The app shows no recommendation card, coupon sheet, study request or rank stability for them."""
    return any(s["key"] == key and s.get("reference") for s in DEMO_SYSTEMS)
