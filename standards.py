from __future__ import annotations
from typing import Dict, List

STANDARDS: Dict[str, Dict] = {
    "aqg324": {
        "label": "ECPE AQG 324 (auto, Rel. 04.1/2025)",
        "blurb": "Guia de industria para modulos en vehiculos <= 3.5 t. Si en el cuerpo, SiC en anexo.",
        "applies_to": "modulo + tecnologia de ensamble",
        "tests": [
            {"code": "PCsec / QL-01", "name": "Power cycling corto", "hits": "wirebond, die attach", "fail": "dVCE(sat) tip. +5%"},
            {"code": "PCmin / QL-02", "name": "Power cycling largo", "hits": "DBC-baseplate, capas gruesas", "fail": "dRth tip. +20%"},
            {"code": "HTRB / QL-05", "name": "High temperature reverse bias", "hits": "chip / pasivacion", "fail": "fuga segun protocolo"},
            {"code": "H3TRB / QL-07", "name": "Humedad + bias", "hits": "encapsulado e interfaces", "fail": "fuga / corrosion"},
            {"code": "TC / TST", "name": "Thermal cycling / shock", "hits": "dCTE capa-sustrato y capa-die", "fail": "delam / Rth"},
        ],
        "next_step": "El workbench elige la fase. El cupon se califica fuera. No afirmar cumple AQG 324.",
    },
    "iec_pc": {
        "label": "IEC 60749-34-1:2025 (power cycling)",
        "blurb": "Metodo IEC de ciclos en potencia para IGBT/MOSFET/diodo.",
        "applies_to": "modulo de potencia",
        "tests": [
            {"code": "PCsec (1-30 s)", "name": "Swing de Tvj", "hits": "wirebond y attach", "fail": "dVCE/VDS/VF >= +5%"},
            {"code": "PCmin (>= 3 min)", "name": "Swing de Tc", "hits": "sustrato-baseplate", "fail": "dRth(j-c) >= +20%"},
        ],
        "next_step": "R_coat del demo no es Rth,jc.",
    },
    "iec_rth": {
        "label": "IEC 60747-15:2024 (Rth dispositivo aislado)",
        "blurb": "Rth se declara por switch (parrafo 6.2.4).",
        "applies_to": "modulo / IPM (datasheet)",
        "tests": [
            {"code": "6.2.4", "name": "Rth por switch", "hits": "die -> case", "fail": "fuera de Rth,max"},
            {"code": "aislamiento", "name": "Ensayo de aislamiento", "hits": "DBC / capa sobre baseplate", "fail": "ruptura / fuga"},
        ],
        "next_step": "kappa bulk no entra al datasheet. Entra Rth medido.",
    },
    "generic": {
        "label": "Recubrimiento generico (sin cualificacion de modulo)",
        "blurb": "Solo proceso + oxidacion.",
        "applies_to": "capa / bond-coat",
        "tests": [
            {"code": "cupon", "name": "Adherencia + oxidacion + CTE", "hits": "la capa", "fail": "delam — criterio del shop"},
        ],
        "next_step": "No uses este modo para pitch de IGBT.",
    },
}

def list_keys() -> List[str]:
    return list(STANDARDS.keys())
