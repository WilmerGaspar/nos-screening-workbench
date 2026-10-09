"""Display-only labels for the Streamlit UI (v0.5).

The data modules (thermal.APPLICATIONS, demo_systems, standards, PROCESS_OPTIONS) keep their
original text because the PDFs, CSVs and e-mails use it. This module only changes what the
screen shows in each language. No numbers are changed: every number in a label below is
copied from the source module.
"""
from __future__ import annotations

from thermal import APPLICATIONS
from demo_systems import DEMO_SYSTEMS
from standards import STANDARDS

_APPS = {
    "es": {
        "cpu_cold_plate": ("Cold plate de CPU / centro de datos", "Dominan la κ y el CTE frente al Cu."),
        "si_power_module": ("Módulo de potencia Si (IGBT / MOSFET)", "Temperatura de unión (Tj) ~150 °C."),
        "sic_power_module": ("Módulo de potencia SiC", "Temperatura de unión (Tj) 175-200 °C."),
        "generic_coating": ("Recubrimiento genérico de alta T (no para refrigeración)", "Sin umbral de κ."),
    },
}

_SYSTEMS = {
    "es": {
        "cited7": "7 fases citadas  ·  dictamen térmico completo",
        "Ni,Al": "Ni-Al  ·  NiAl + Ni3Al (IGBT)",
        "Co,Al": "Co-Al  ·  CoAl 37 W/mK",
        "Fe,Al": "Fe-Al  ·  FeAl 12 W/mK (no es difusor de calor)",
        "Fe,Ti": "Fe-Ti  ·  FeTi 73 W/mK",
        "Ni,Ga": "Ni-Ga  ·  NiGa + Ni3Ga",
        "Ti,Al": "Ti-Al  ·  sin κ citable",
        "Ni,Ti": "Ni-Ti  ·  sin κ citable",
        "Co,Ti": "Co-Ti  ·  sin κ citable",
        "Zn,Fe": "Zn-Fe  ·  galvanizado",
        "Fe,Cr": "Fe-Cr  ·  sin κ citable",
    },
    "en": {
        "cited7": "7 cited phases  ·  full thermal verdict",
        "Ni,Al": "Ni-Al  ·  NiAl + Ni3Al (IGBT)",
        "Co,Al": "Co-Al  ·  CoAl 37 W/mK",
        "Fe,Al": "Fe-Al  ·  FeAl 12 W/mK (not a spreader)",
        "Fe,Ti": "Fe-Ti  ·  FeTi 73 W/mK",
        "Ni,Ga": "Ni-Ga  ·  NiGa + Ni3Ga",
        "Ti,Al": "Ti-Al  ·  no citable κ",
        "Ni,Ti": "Ni-Ti  ·  no citable κ",
        "Co,Ti": "Co-Ti  ·  no citable κ",
        "Zn,Fe": "Zn-Fe  ·  galvanized",
        "Fe,Cr": "Fe-Cr  ·  no citable κ",
    },
}

_PROCESSES = {
    "es": {
        "PVD (sputter / arc)": "PVD (pulverización catódica / arco)",
        "Thermal spray / HVOF": "Proyección térmica (thermal spray) / HVOF",
        "Electroplating": "Electrodeposición",
        "Arc / flame wire spray": "Proyección por arco / llama con alambre",
        "Other": "Otro",
    },
}

_TIERS = {
    "es": {
        "Experimentally verified": "Verificado experimentalmente",
        "Partially backed": "Parcialmente respaldado",
        "Well-calculated (DFT)": "Calculado con DFT",
        "Exploratory": "Exploratorio",
    },
}

# Standards: same codes and numbers as standards.py, text per language.
_STANDARDS = {
    "es": {
        "aqg324": {
            "label": "ECPE AQG 324 (automotriz, Rel. 04.1/2025)",
            "blurb": "Guía de la industria para módulos en vehículos <= 3.5 t. Si en el texto principal, SiC en un anexo.",
            "tests": [
                ("PCsec / QL-01", "Ciclado de potencia corto", "wirebond, die-attach", "dVCE(sat) típ. +5%"),
                ("PCmin / QL-02", "Ciclado de potencia largo", "DBC-placa base, capas gruesas", "dRth típ. +20%"),
                ("HTRB / QL-05", "Polarización inversa a alta temperatura (HTRB)", "chip / pasivación", "fuga según protocolo"),
                ("H3TRB / QL-07", "Humedad + polarización", "encapsulado e interfaces", "fuga / corrosión"),
                ("TC / TST", "Ciclado / choque térmico", "dCTE capa-sustrato y capa-chip", "delaminación / Rth"),
            ],
            "next_step": "El workbench elige la fase. La cualificación de la probeta se hace fuera de esta herramienta. No afirmar que cumple AQG 324.",
        },
        "iec_pc": {
            "label": "IEC 60749-34-1:2025 (ciclado de potencia)",
            "blurb": "Método IEC de ciclado de potencia para IGBT / MOSFET / diodo.",
            "tests": [
                ("PCsec (1-30 s)", "Variación de Tvj (ΔTvj)", "wirebond y die-attach", "dVCE/VDS/VF >= +5%"),
                ("PCmin (>= 3 min)", "Variación de Tc (ΔTc)", "sustrato-placa base", "dRth(j-c) >= +20%"),
            ],
            "next_step": "La R_coat de la demo no es la Rth,jc.",
        },
        "iec_rth": {
            "label": "IEC 60747-15:2024 (Rth de dispositivos aislados)",
            "blurb": "La Rth se declara por interruptor (switch); apartado 6.2.4.",
            "tests": [
                ("6.2.4", "Rth por interruptor", "chip -> carcasa (case)", "fuera de Rth,max"),
                ("aislamiento", "Ensayo de aislamiento", "DBC / capa sobre placa base", "ruptura / fuga"),
            ],
            "next_step": "La κ bulk no entra en la hoja de datos (datasheet). Entra la Rth medida.",
        },
        "generic": {
            "label": "Recubrimiento genérico (sin cualificación de módulo)",
            "blurb": "Solo proceso + oxidación.",
            "tests": [
                ("probeta", "Adherencia + oxidación + CTE", "la capa", "delaminación (criterio del taller)"),
            ],
            "next_step": "No uses este modo para presentar un caso de IGBT.",
        },
    },
    "en": {
        "aqg324": {
            "label": "ECPE AQG 324 (automotive, Rel. 04.1/2025)",
            "blurb": "Industry guideline for modules in vehicles <= 3.5 t. Si in the main text, SiC in an annex.",
            "tests": [
                ("PCsec / QL-01", "Short power cycling", "wirebond, die attach", "dVCE(sat) typ. +5%"),
                ("PCmin / QL-02", "Long power cycling", "DBC-baseplate, thick layers", "dRth typ. +20%"),
                ("HTRB / QL-05", "High temperature reverse bias", "chip / passivation", "leakage per protocol"),
                ("H3TRB / QL-07", "Humidity + bias", "encapsulation and interfaces", "leakage / corrosion"),
                ("TC / TST", "Thermal cycling / shock", "dCTE coating-substrate and coating-die", "delamination / Rth"),
            ],
            "next_step": "The workbench picks the phase. The coupon is qualified elsewhere. Do not claim AQG 324 compliance.",
        },
        "iec_pc": {
            "label": "IEC 60749-34-1:2025 (power cycling)",
            "blurb": "IEC power-cycling method for IGBT / MOSFET / diode.",
            "tests": [
                ("PCsec (1-30 s)", "Tvj swing", "wirebond and attach", "dVCE/VDS/VF >= +5%"),
                ("PCmin (>= 3 min)", "Tc swing", "substrate-baseplate", "dRth(j-c) >= +20%"),
            ],
            "next_step": "The demo R_coat is not Rth,jc.",
        },
        "iec_rth": {
            "label": "IEC 60747-15:2024 (Rth of isolated devices)",
            "blurb": "Rth is declared per switch (clause 6.2.4).",
            "tests": [
                ("6.2.4", "Rth per switch", "die -> case", "outside Rth,max"),
                ("insulation", "Insulation test", "DBC / layer on baseplate", "breakdown / leakage"),
            ],
            "next_step": "Bulk κ does not go into the datasheet. Measured Rth does.",
        },
        "generic": {
            "label": "Generic coating (no module qualification)",
            "blurb": "Process + oxidation only.",
            "tests": [
                ("coupon", "Adhesion + oxidation + CTE", "the coating", "delamination (shop criterion)"),
            ],
            "next_step": "Do not use this mode to pitch an IGBT case.",
        },
    },
}


def app_label(lang, key):
    return _APPS.get(lang, {}).get(key, (APPLICATIONS[key]["label"], None))[0]


def app_blurb(lang, key):
    return _APPS.get(lang, {}).get(key, (None, APPLICATIONS[key]["blurb"]))[1]


def system_label(lang, key):
    fallback = next(s["label"] for s in DEMO_SYSTEMS if s["key"] == key)
    return _SYSTEMS.get(lang, _SYSTEMS["en"]).get(key, fallback)


def process_label(lang, key):
    return _PROCESSES.get(lang, {}).get(key, key)


def tier_label(lang, key):
    return _TIERS.get(lang, {}).get(key, key)


def standard(lang, key):
    """{label, blurb, tests: [(code, name, hits, fail)], next_step} in the UI language."""
    pack = _STANDARDS.get(lang) or _STANDARDS["en"]
    if key in pack:
        return pack[key]
    spec = STANDARDS[key]
    return {"label": spec["label"], "blurb": spec["blurb"], "next_step": spec["next_step"],
            "tests": [(x["code"], x["name"], x["hits"], x["fail"]) for x in spec["tests"]]}


# --- Per-phase notes (display only) ---------------------------------------------------------
# The notes are produced in English by interface.py, pipeline.py, manufacturability.py and
# thermal.py and also go into the PDFs. On screen, Spanish users see a translation built from
# the same text: every number is copied from the English note as matched text, never recomputed.
# A note that matches no pattern is shown unchanged.
import re

_FIXED_ES = {
    "Ni/Fe next to Cu: look for an interdiffusion zone in the cross-section (practitioner input; may be negligible near 150 C - measure, do not assume).":
        "Ni/Fe junto al Cu: buscar una zona de interdifusión en el corte (aporte práctico no publicado; puede ser despreciable cerca de 150 °C: medir, no suponer).",
    "Al/Ti in the coating: look for surface oxide at the interface in the cross-section (practitioner input).":
        "Al/Ti en el recubrimiento: buscar óxido superficial en la interfaz en el corte (aporte práctico no publicado).",
    "Coating CTE has no DOI in this repo: verify the value before quoting it.":
        "El CTE del recubrimiento no tiene DOI en este repositorio: verificar el valor antes de citarlo.",
    "No CTE value for this phase: the interface verdict needs a coupon.":
        "Sin valor de CTE para esta fase: el dictamen de la interfaz necesita una probeta.",
    "Coating touches a semiconductor die: metallic coatings sit far from the die CTE.":
        "El recubrimiento toca un chip semiconductor: los recubrimientos metálicos quedan lejos del CTE del chip.",
    "Al and Cu meet at this interface: Al-Cu intermetallics can grow there. They are harder than Al and Cu (a mechanical weak point), and theta (Al2Cu) can turn into Al4Cu9 when Al runs short, reported at 175-250 C in Al-Cu wire bonds (Xu et al. 2011, cited in Nazarahari et al. 2026, DOI 10.1002/adem.202501357). Measure the IMC thickness at each checkpoint.":
        "Al y Cu se encuentran en esta interfaz: ahí pueden crecer intermetálicos Al-Cu. Son más duros que el Al y el Cu (un punto débil mecánico), y theta (Al2Cu) puede convertirse en Al4Cu9 cuando falta Al, observado a 175-250 °C en uniones por hilo Al-Cu (wire bonds; Xu et al. 2011, citado en Nazarahari et al. 2026, DOI 10.1002/adem.202501357). Medir el espesor del intermetálico en cada punto de control.",
    "No citable bulk kappa: measure film kappa on the coupon only if the interface survives.":
        "Sin κ bulk citable: medir la κ de la capa depositada en la probeta solo si la interfaz sobrevive.",
    "Even at bulk kappa (an upper bound) the coating is a meaningful thermal term.":
        "Incluso con la κ bulk (un límite superior), el recubrimiento es un término térmico importante.",
    "No coating CTE in the catalog: interface score set to neutral 0.5.":
        "Sin CTE del recubrimiento en el catálogo: puntaje de interfaz neutro de 0.5.",
    "Aqueous electroplating veto: majority of chemistry is not plateable from water baths.":
        "Veto de electrodeposición acuosa: la mayor parte de la composición no se puede depositar desde baños acuosos.",
    "Constituents are aqueous-plateable. Expect a conversion anneal.":
        "Los constituyentes se pueden depositar en baño acuoso. Prever un recocido de difusión para formar la fase.",
    "High Zn is a poor HVOF match.": "Un contenido alto de Zn encaja mal con HVOF.",
    "Published spray trail.": "Hay literatura publicada de proyección térmica.",
    "No spray literature trail in the ruleset.": "Sin literatura de proyección térmica en las reglas.",
    "PVD can deposit most intermetallics; residual stress is the risk.":
        "El PVD puede depositar la mayoría de los intermetálicos; el riesgo es la tensión residual.",
    "Service T above the Zn-rich window (~200 C).": "T de servicio por encima del rango de uso de las fases ricas en Zn (~200 °C).",
    "T>450 C without Al/Cr/Si scale former.": "T > 450 °C sin formador de capa de óxido protectora (Al/Cr/Si).",
    "T>600 C: interdiffusion and softening dominate.": "T > 600 °C: dominan la interdifusión y el ablandamiento.",
    "No elasticity data; Pugh not computed.": "Sin datos elásticos; no se calcula el criterio de Pugh.",
    "Zn-Fe zeta; service ~200 C.": "Zn-Fe zeta; servicio ~200 °C.",
    "Al13Fe4 / Al2O3 scale; Krasnowski 2022.": "Al13Fe4 / capa de Al2O3; Krasnowski 2022.",
    "Fe4Al13 alumina former; Krasnowski 2022.": "Fe4Al13, formador de alúmina; Krasnowski 2022.",
}

_NEIGHBORS_ES = [("(substrate)", "(sustrato)"), ("(baseplate)", "(placa base)"), ("Cu (DBC copper)", "Cu (cobre del DBC)"),
                 ("Al bond wire", "hilo de Al (bond wire)"), (" die", " (chip)")]

_PATTERNS_ES = [
    (r"^TIM term: (\S+) um at (\S+) W/mK (?:->|→) dT_TIM = (\S+) K at (\S+) W over (\S+) cm2 \(editable assumption\)\.$",
     "Término del TIM: {0} µm a {1} W/m·K → ΔT_TIM = {2} K con {3} W en {4} cm² (supuesto editable)."),
    (r"^Film kappa needed to keep the coating (?:<=|≤) (\S+) of the coating\+TIM dT: (\S+) W/mK\.$",
     "κ de la capa depositada necesaria para que la capa no pase del {0} del ΔT capa+TIM: {1} W/m·K."),
    (r"^Coating at bulk kappa (\S+) W/mK: dT_coat = (\S+) K, (\S+) of the coating\+TIM dT\.$",
     "Capa con κ bulk {0} W/m·K: ΔT_capa = {1} K, el {2} del ΔT capa+TIM."),
    (r"^The film may lose up to (\S+) of its bulk kappa before it matters\.$",
     "La capa depositada puede perder hasta el {0} de su κ bulk antes de que importe."),
    (r"^CTE coat (\S+) vs (.+) (?:->|→) dCTE (\S+) ppm/K\.$",
     "CTE de la capa {0} frente a {1} → ΔCTE {2} ppm/K."),
    (r"^Thermal side of Al-Cu IMC growth: even the lowest-k phase measured \((\S+), (\S+) W/mK\) stays under (\S+) of the IMC\+TIM dT up to ~(\S+) um\. Below that, IMC growth is a mechanical question \(cracking, hardness\), not a thermal one\.$",
     "Lado térmico del crecimiento de intermetálicos Al-Cu: incluso la fase medida de menor κ ({0}, {1} W/m·K) se queda por debajo del {2} del ΔT intermetálico+TIM hasta ~{3} µm. Por debajo de eso, el crecimiento del intermetálico es una cuestión mecánica (grietas, dureza), no térmica."),
    (r"^Partial electroplating fit\. Difficult: (.+)$", "Electrodeposición parcialmente viable. Difíciles: {0}"),
    (r"^T>450 C with oxide formers: (.+)$", "T > 450 °C con formadores de capa de óxido protectora: {0}"),
    (r"^Pugh B/G = (\S+) < 1\.75 brittle tendency \(Pugh 1954\)\.$", "Pugh B/G = {0} < 1.75: tendencia frágil (Pugh 1954)."),
    (r"^Pugh B/G = (\S+) (?:>=|≥) 1\.75 more ductile tendency\.$", "Pugh B/G = {0} ≥ 1.75: tendencia más dúctil."),
]


def _neighbor_es(text):
    for a, b in _NEIGHBORS_ES:
        text = text.replace(a, b)
    return text


def note(lang, line):
    """Screen translation of one engine note. Unknown notes are returned unchanged."""
    if lang != "es" or not line:
        return line
    if line in _FIXED_ES:
        return _FIXED_ES[line]
    for pat, tpl in _PATTERNS_ES:
        m = re.match(pat, line)
        if m:
            groups = [_neighbor_es(g) for g in m.groups()]
            return tpl.format(*groups)
    return line


def neighbor(lang, label):
    return _neighbor_es(label) if lang == "es" and label else label
