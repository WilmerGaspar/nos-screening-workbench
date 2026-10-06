"""Layer sites. Each site names the materials the coating touches.

`neighbors` drives the CTE comparison in interface.py:
  "die"       -> the die picked in the sidebar (Si, SiC, GaN, GaAs)
  "substrate" -> the substrate / baseplate picked in the sidebar
  any other   -> a fixed material from thermal.SUBSTRATES (e.g. Cu of the DBC, Al bond wire)
`heat_path` says whether the coating sits in the main heat path (then kappa relevance is checked).
"""

SITES = {
    "chip_metallization": {
        "label": "Chip top-side metallization (bond pad)",
        "aqg": "PCsec / QL-01",
        "fail": "dVCE(sat) / dVDS tip. +5%",
        "heat_path": False,
        "neighbors": [("die", "die"), ("Al", "Al bond wire")],
        "blurb": "Con die-attach sinterizado, la fatiga del wirebond y de la metalizacion del pad pasa a dominar (Scarpa et al., arXiv:2608.08363).",
    },
    "die_attach": {
        "label": "Die-attach (chip -> DBC)",
        "aqg": "PCsec / QL-01",
        "fail": "dVCE(sat) / dVDS tip. +5%",
        "heat_path": True,
        "neighbors": [("die", "die"), ("Cu", "Cu (DBC copper)")],
        "blurb": "Capa junto al die. Power cycling corto. No es un TIM.",
    },
    "dbc_baseplate": {
        "label": "DBC -> baseplate",
        "aqg": "PCmin / QL-02",
        "fail": "dRth(j-c) tip. +20%",
        "heat_path": True,
        "neighbors": [("Cu", "Cu (DBC copper)"), ("substrate", "baseplate")],
        "blurb": "Capa gruesa / soldadura del sustrato. Rth del modulo.",
    },
    "bond_coat": {
        "label": "Bond-coat / oxidacion (no camino de calor)",
        "aqg": "TC / TST + oxidacion",
        "fail": "delam",
        "heat_path": False,
        "neighbors": [("substrate", "substrate")],
        "blurb": "Proteccion, no spreader. FeAl vive aqui.",
    },
    "cold_plate": {
        "label": "Cold plate / leadframe (Cu)",
        "aqg": "IEC 60747-15 Rth por switch",
        "fail": "fuera de Rth,max",
        "heat_path": True,
        "neighbors": [("substrate", "substrate")],
        "blurb": "Capa sobre Cu. R = t/kA es un termino, no el datasheet.",
    },
}
DEFAULT_SITE = "cold_plate"

TIM_REF = [
    {"name": "Thermal grease", "kappa": "3-8", "form": "TIM", "note": "Interfaz; no recubrimiento."},
    {"name": "Gap pad / TIM pad", "kappa": "5-15", "form": "TIM", "note": "Compliable; no fase intermetalica."},
    {"name": "Solder attach", "kappa": "~50", "form": "metal", "note": "Die-attach clasico."},
    {"name": "NiAl bulk (Terada 2002)", "kappa": "92.2", "form": "bulk 300 K", "note": "No es TIM. No es k de capa PVD."},
    {"name": "Cu", "kappa": "401", "form": "metal", "note": "Cold plate / leadframe."},
]


def site_spec(site_key):
    return SITES.get(site_key) or SITES[DEFAULT_SITE]


def site_note(site_key):
    spec = site_spec(site_key)
    return f"Sitio: {spec['label']}. Ensayo: {spec['aqg']}. Fallo: {spec['fail']}. {spec['blurb']}"
