SITES = {
    "die_attach": {"label": "Die-attach (chip -> DBC)", "aqg": "PCsec / QL-01", "fail": "dVCE(sat) / dVDS tip. +5%", "heat_path": True, "blurb": "Capa junto al die. Power cycling corto. No es un TIM."},
    "dbc_baseplate": {"label": "DBC -> baseplate", "aqg": "PCmin / QL-02", "fail": "dRth(j-c) tip. +20%", "heat_path": True, "blurb": "Capa gruesa / soldadura del sustrato. Rth del modulo."},
    "bond_coat": {"label": "Bond-coat / oxidacion (no camino de calor)", "aqg": "TC / TST + oxidacion", "fail": "delam", "heat_path": False, "blurb": "Proteccion, no spreader. FeAl vive aqui."},
    "cold_plate": {"label": "Cold plate / leadframe (Cu)", "aqg": "IEC 60747-15 Rth por switch", "fail": "fuera de Rth,max", "heat_path": True, "blurb": "Capa sobre Cu. R = t/kA es un termino, no el datasheet."},
}
TIM_REF = [
    {"name": "Thermal grease", "kappa": "3-8", "form": "TIM", "note": "Interfaz; no recubrimiento."},
    {"name": "Gap pad / TIM pad", "kappa": "5-15", "form": "TIM", "note": "Compliable; no fase intermetalica."},
    {"name": "Solder attach", "kappa": "~50", "form": "metal", "note": "Die-attach clasico."},
    {"name": "NiAl bulk (Terada 2002)", "kappa": "92.2", "form": "bulk 300 K", "note": "No es TIM. No es k de capa PVD."},
    {"name": "Cu", "kappa": "401", "form": "metal", "note": "Cold plate / leadframe."},
]
def site_note(site_key):
    spec = SITES.get(site_key) or SITES["cold_plate"]
    return f"Sitio: {spec['label']}. Ensayo: {spec['aqg']}. Fallo: {spec['fail']}. {spec['blurb']}"
