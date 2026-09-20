"""NOS Screening Workbench — public demo. Author: Wilmer Gaspar Espinoza Castillo"""
from __future__ import annotations
import io
import os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from manufacturability import evaluate
from nos_score import run_demo, run_live
from ranking import COOLING_WEIGHTS, attach_ranks, pareto_front
from die_stack import DIES, evaluate_stack
from thermal import APPLICATIONS, SUBSTRATES, VERDICT_COPY, evaluate_thermal

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "logo.jpg"

st.set_page_config(page_title="NOS Screening Workbench", page_icon="\u25c6", layout="wide")
PROCESS_OPTIONS = {"PVD (sputter / arc)": "pvd", "Thermal spray / HVOF": "thermal_spray", "Electroplating": "electroplating"}
TIER_COLORS = {"Experimentally verified": "#0f766e", "Partially backed": "#ca8a04", "Well-calculated (DFT)": "#1d4ed8", "Exploratory": "#6b7280"}

def _mp_key() -> str:
    key = os.environ.get("MP_API_KEY", "")
    if key:
        return key
    try:
        return str(st.secrets.get("MP_API_KEY", "") or "")
    except Exception:
        return ""

def header():
    c1, c2 = st.columns([1, 8])
    with c1:
        if LOGO.exists():
            st.image(str(LOGO), width=72)
    with c2:
        st.title("NOS Screening Workbench")
        st.caption("Pre-filtro de fases intermetalicas. Kappa publicado (Terada). No sustituye CALPHAD ni un cupon.")

def sidebar():
    st.sidebar.header("Mision")
    app_key = st.sidebar.selectbox("Aplicacion", list(APPLICATIONS.keys()), format_func=lambda k: APPLICATIONS[k]["label"], index=1)
    spec = APPLICATIONS[app_key]
    cooling = app_key != "generic_coating"
    st.sidebar.caption(spec["blurb"])
    default_alloy = "Ni, Al" if cooling else "Fe, Al"
    alloy = st.sidebar.text_input("Sistema quimico", value=default_alloy)
    exact = st.sidebar.toggle("Solo ese sistema (chemsys exacto)", value=True)
    process_label = st.sidebar.selectbox("Proceso de deposito", list(PROCESS_OPTIONS.keys()))
    substrate = st.sidebar.selectbox("Sustrato", list(SUBSTRATES.keys()), index=list(SUBSTRATES.keys()).index(spec["default_substrate"]))
    temp = st.sidebar.slider("Temperatura de servicio / juntura (C)", 25, 800, int(spec["default_temp_c"]), 5)
    die = st.sidebar.selectbox("Die", list(DIES.keys()), index=0)
    thickness_um = st.sidebar.slider("Espesor de capa (um)", 1, 200, 20, 1)
    area_cm2 = st.sidebar.number_input("Area (cm2)", min_value=0.01, max_value=100.0, value=1.0, step=0.1)
    power_w = st.sidebar.number_input("Potencia del die (W)", min_value=1.0, max_value=500.0, value=50.0, step=1.0)
    t_sink_c = st.sidebar.number_input("T del sink (C)", min_value=0.0, max_value=120.0, value=45.0, step=1.0)
    budget = st.sidebar.number_input("Presupuesto R_coat (K/W)", min_value=0.005, max_value=1.0, value=0.05, step=0.005)
    if cooling:
        w_nos, w_thermal = COOLING_WEIGHTS["nos"], COOLING_WEIGHTS["thermal"]
        st.sidebar.caption("Ranking cooling: 30% NOS + 30% proceso + 40% k/CTE.")
    else:
        w_nos = st.sidebar.slider("Peso del NOS", 0.30, 0.80, 0.55, 0.05)
        w_thermal = 0.0
    st.sidebar.divider()
    st.sidebar.subheader("Fuente de datos")
    mp_key = _mp_key()
    has_key = bool(mp_key)
    source = st.sidebar.radio("Modo", ["Demo offline (reproducible)", "Materials Project (API)"], index=0 if not has_key else 1)
    max_results = st.sidebar.slider("Maximo de fases (API)", 20, 200, 80, 10)
    if source.startswith("Materials") and not has_key:
        st.sidebar.warning("No hay MP_API_KEY (env o Streamlit Secrets). Se usara demo.")
    run = st.sidebar.button("Ejecutar screening", type="primary", use_container_width=True)
    cleaned = []
    for e in alloy.split(","):
        token = e.strip()
        if token:
            cleaned.append(token[0].upper() + token[1:].lower() if len(token) > 1 else token.upper())
    return {
        "elements": cleaned, "exact": exact, "process": PROCESS_OPTIONS[process_label],
        "process_label": process_label, "temp": temp, "w_nos": w_nos, "w_thermal": w_thermal,
        "cooling": cooling, "application": app_key, "substrate": substrate, "die": die,
        "thickness_um": thickness_um, "area_cm2": area_cm2, "power_w": power_w,
        "t_sink_c": t_sink_c, "budget": budget, "live": source.startswith("Materials") and has_key,
        "mp_key": mp_key, "max_results": max_results, "run": run,
    }

def screen(cfg):
    if len(cfg["elements"]) < 2:
        st.warning("Indica al menos dos elementos, por ejemplo Ni, Al.")
        return None, None
    if cfg["live"]:
        try:
            cands = run_live(cfg["elements"], api_key=cfg.get("mp_key"), max_results=cfg["max_results"], exact_chemsys=cfg["exact"])
            mode = "materials_project"
        except Exception as exc:
            st.error(f"Fallo Materials Project: {exc}")
            cands = run_demo(cfg["elements"], exact_chemsys=cfg["exact"])
            mode = "demo_fallback"
    else:
        cands = run_demo(cfg["elements"], exact_chemsys=cfg["exact"])
        mode = "demo"
    rows = []
    for c in cands:
        manuf = evaluate(c, cfg["process"], cfg["temp"])
        therm = evaluate_thermal(c["formula"], cfg["substrate"], cfg["application"])
        stack = evaluate_stack(c["formula"], thickness_um=cfg["thickness_um"], area_cm2=cfg["area_cm2"], power_w=cfg["power_w"], t_sink_c=cfg["t_sink_c"], budget_k_per_w=cfg["budget"], die=cfg["die"], substrate=cfg["substrate"])
        rows.append({**c, "manuf_score": manuf.score, "manuf_risk": manuf.risk_level, "manuf_notes": manuf.notes, "veto": manuf.veto, "kappa_score": therm.score, "kappa_wm_k": therm.kappa_wm_k, "cte_ppm_k": therm.cte_ppm_k, "dcte_ppm_k": therm.dcte_ppm_k, "thermal_citation": therm.citation, "thermal_notes": therm.notes, "thermal_verdict": therm.verdict, "heat_spreader_ok": therm.heat_spreader_ok, "r_coat": stack.r_coat_k_per_w, "dt_coat": stack.dt_coat_k, "tj_lower_bound": stack.tj_lower_bound_c, "stack_verdict": stack.verdict, "stack_notes": stack.notes, "within_budget": stack.within_budget})
    ranked = attach_ranks(rows, w_nos=cfg["w_nos"], w_thermal=cfg["w_thermal"])
    front = set(pareto_front(ranked, cooling=cfg["cooling"]))
    for r in ranked:
        r["pareto"] = (r.get("material_id") in front) or (r.get("formula") in front)
    return ranked, mode

def metrics(rows, mode, cooling):
    a, b, c, d = st.columns(4)
    a.metric("Candidatos", len(rows))
    b.metric("Frente de Pareto", sum(1 for r in rows if r["pareto"]))
    if cooling:
        c.metric("Con k citable", sum(1 for r in rows if r.get("kappa_wm_k") is not None))
        d.metric("Listos para cupon", sum(1 for r in rows if r.get("thermal_verdict") == "proceed_to_coupon"))
    else:
        c.metric("Riesgo bajo / medio", sum(1 for r in rows if r["manuf_risk"] in ("low", "medium")))
        d.metric("Fuente", "Demo" if mode.startswith("demo") else "Materials Project")

def scatter(rows, cooling):
    fig = go.Figure()
    for tier, color in TIER_COLORS.items():
        chunk = [r for r in rows if r["tier"] == tier]
        if not chunk:
            continue
        xs = [r["kappa_score"] if cooling else r["NOS"] for r in chunk]
        fig.add_trace(go.Scatter(x=xs, y=[r["manuf_score"] for r in chunk], mode="markers", name=tier, marker=dict(size=[16 if r["pareto"] else 11 for r in chunk], color=color, symbol=["diamond" if r["pareto"] else "circle" for r in chunk]), text=[f"{r['formula']} rank {r['rank']} k={r.get('kappa_wm_k')}" for r in chunk], hoverinfo="text"))
    fig.update_layout(title="k/CTE vs proceso" if cooling else "NOS vs proceso", xaxis_title="score termico" if cooling else "NOS", yaxis_title="Manufacturabilidad", height=500, xaxis=dict(range=[0, 1]), yaxis=dict(range=[0, 1]), template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

def table(rows, cooling):
    df = pd.DataFrame([{"Rank": r["rank"], "Formula": r["formula"], "Combined": r["combined"], "NOS": r["NOS"], "Manuf": r["manuf_score"], "Riesgo": r["manuf_risk"], "Dictamen": r.get("thermal_verdict"), "k_WmK": r.get("kappa_wm_k"), "R_coat": r.get("r_coat"), "dT_K": r.get("dt_coat"), "Tj_min_C": r.get("tj_lower_bound"), "Pareto": "si" if r["pareto"] else "", "id": r.get("material_id")} for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True, height=420)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button("Descargar ranking CSV", data=buf.getvalue(), file_name="nos_ranking.csv", mime="text/csv")

def detail(rows):
    labels = [f"{r['rank']:02d} · {r['formula']} ({r['combined']:.3f})" for r in rows[:40]]
    if not labels:
        return
    choice = st.selectbox("Ficha / dictamen", labels)
    row = rows[labels.index(choice)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("NOS", f"{row['NOS']:.3f}")
    c2.metric("Manuf", f"{row['manuf_score']:.3f}")
    c3.metric("k (W/mK)", "—" if row.get("kappa_wm_k") is None else f"{row['kappa_wm_k']:.1f}")
    c4.metric("Combined", f"{row['combined']:.3f}")
    s1, s2, s3 = st.columns(3)
    s1.metric("R_coat (K/W)", "—" if row.get("r_coat") is None else f"{row['r_coat']:.4f}")
    s2.metric("dT capa (K)", "—" if row.get("dt_coat") is None else f"{row['dt_coat']:.2f}")
    s3.metric("Tj min (C)", "—" if row.get("tj_lower_bound") is None else f"{row['tj_lower_bound']:.1f}")
    verdict = row.get("thermal_verdict") or "missing_thermal_data"
    st.info(f"Dictamen fase: {verdict} — {VERDICT_COPY.get(verdict, '')}\nDictamen stack: {row.get('stack_verdict')}")
    for title, key in [("Stack", "stack_notes"), ("Termicas", "thermal_notes"), ("Proceso", "manuf_notes")]:
        st.write(f"**{title}**")
        for note in row.get(key) or []:
            st.write(f"- {note}")

def main():
    header()
    cfg = sidebar()
    if not cfg["run"]:
        st.info("Elige mision y ejecuta. Demo offline no necesita API. Live MP usa MP_API_KEY.")
        return
    rows, mode = screen(cfg)
    if rows is None:
        return
    tag = APPLICATIONS[cfg["application"]]["label"]
    st.success(f"{len(rows)} fases · {tag} · {cfg['substrate']} · {cfg['process_label']} · T={cfg['temp']} C · {"DEMO" if mode.startswith("demo") else "MP live"}")
    metrics(rows, mode, cfg["cooling"])
    scatter(rows, cfg["cooling"])
    st.subheader("Ranking")
    table(rows, cfg["cooling"])
    st.subheader("Dictamen")
    detail(rows)
    st.caption("(c) 2026 Wilmer Gaspar Espinoza Castillo · CC BY-NC-SA 4.0")

if __name__ == "__main__":
    main()
