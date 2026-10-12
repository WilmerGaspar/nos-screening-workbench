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


REFERENCE_TIER = "Measured (reference)"


def shown_tier(row, reference):
    """Evidence label the app shows for a row. In a reference system, a demo row with a cited measured
    kappa is "Measured (reference)" (display only; NOS, score and order are not changed). Materials
    Project rows keep their own tier: kappa is matched by composition, so a live polymorph is not
    necessarily the measured phase."""
    if reference and row.get("source") == "demo" and row.get("kappa_wm_k") is not None:
        return REFERENCE_TIER
    return row["tier"]


def reference_table_rows(rows):
    """Rows as the ranking tables and the CSV show them in a reference system: sorted by kappa bulk
    (lowest first; rows without kappa last), position renumbered in that order, and NOS / score left
    empty when they rest on stability or mechanics we do not have (no Materials Project data)."""
    ordered = sorted(rows, key=lambda r: (r.get("kappa_wm_k") is None, r.get("kappa_wm_k") or 0.0))
    out = []
    for i, r in enumerate(ordered, 1):
        missing = r.get("e_above_hull") is None or r.get("bulk_modulus") is None or r.get("shear_modulus") is None
        out.append({**r, "rank": i, **({"NOS": None, "combined": None} if missing else {})})
    return out


# Notes left out of the detail of a reference system: they are about depositing the phase or about its
# CTE / interface score, which do not apply to a phase that grows at a joint. Pugh notes stay.
_NO_CTE_INTERFACE_NOTE = "No coating CTE in the catalog: interface score set to neutral 0.5."


def reference_detail_notes(row):
    """Engine notes (English, before translation) shown in the detail of a reference system: interface,
    thermal-relevance and flag notes as usual, minus the deposition notes (manufacturability, except Pugh),
    the Al/Ti oxide flag and the two "no CTE" notes."""
    from interface import FLAG_TEXT
    hidden = {FLAG_TEXT["al_ti_oxide"], FLAG_TEXT["cte_missing"], _NO_CTE_INTERFACE_NOTE}
    pugh = [n for n in row.get("manuf_notes") or [] if "Pugh" in n]
    lines = (row.get("interface_notes") or []) + (row.get("relevance_notes") or []) + (row.get("flag_notes") or []) + pugh
    return [n for n in lines if n not in hidden]


def is_reference(key):
    """Reference systems: measured phases shown for their kappa, not coatings to deposit.
    The app shows no recommendation card, coupon sheet, study request or rank stability for them."""
    return any(s["key"] == key and s.get("reference") for s in DEMO_SYSTEMS)
