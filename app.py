"""NOS Screening Workbench — public demo. Author: Wilmer Gaspar Espinoza Castillo"""
from __future__ import annotations
import io, os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from manufacturability import evaluate
from nos_score import run_demo, run_live
from ranking import COOLING_WEIGHTS, attach_ranks, pareto_front
from die_stack import DIES, evaluate_stack
from thermal import APPLICATIONS, SUBSTRATES, VERDICT_COPY, evaluate_thermal
from demo_systems import DEMO_SYSTEMS
from standards import STANDARDS
from i18n import LANGS, t, verdict_text
from report_pdf import build_pdf, build_zip_all_langs

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "logo.jpg"
st.set_page_config(page_title="NOS Screening Workbench", page_icon="\u25c6", layout="wide")
PROCESS_OPTIONS = {"PVD (sputter / arc)": "pvd", "Thermal spray / HVOF": "thermal_spray", "Electroplating": "electroplating"}
TIER_COLORS = {"Experimentally verified": "#0f766e", "Partially backed": "#ca8a04", "Well-calculated (DFT)": "#1d4ed8", "Exploratory": "#6b7280"}

def _mp_key():
    key = os.environ.get("MP_API_KEY", "")
    if key: return key
    try: return str(st.secrets.get("MP_API_KEY", "") or "")
    except Exception: return ""

def header(lang):
    c1, c2 = st.columns([1, 8])
    with c1:
        if LOGO.exists(): st.image(str(LOGO), width=72)
    with c2:
        st.title(t(lang, "title"))
        st.caption(t(lang, "subtitle"))

def sidebar():
    lang = st.sidebar.selectbox("Language / Idioma", list(LANGS.keys()), format_func=lambda k: LANGS[k], index=0)
    st.sidebar.header(t(lang, "mission"))
    app_key = st.sidebar.selectbox(t(lang, "application"), list(APPLICATIONS.keys()), format_func=lambda k: APPLICATIONS[k]["label"], index=1)
    spec = APPLICATIONS[app_key]
    cooling = app_key != "generic_coating"
    st.sidebar.caption(spec["blurb"])
    default_sys = "Ni,Al" if cooling else "Fe,Al"
    keys = [s["key"] for s in DEMO_SYSTEMS]
    default_idx = keys.index(default_sys) if default_sys in keys else 0
    sys_key = st.sidebar.selectbox(t(lang, "system"), keys, index=default_idx, format_func=lambda k: next(s["label"] for s in DEMO_SYSTEMS if s["key"] == k))
    exact = st.sidebar.toggle(t(lang, "exact"), value=True)
    std_key = st.sidebar.selectbox(t(lang, "standard"), list(STANDARDS.keys()), index=0 if cooling else 3, format_func=lambda k: STANDARDS[k]["label"])
    process_label = st.sidebar.selectbox(t(lang, "process"), list(PROCESS_OPTIONS.keys()))
    substrate = st.sidebar.selectbox(t(lang, "substrate"), list(SUBSTRATES.keys()), index=list(SUBSTRATES.keys()).index(spec["default_substrate"]))
    temp = st.sidebar.slider(t(lang, "temp"), 25, 800, int(spec["default_temp_c"]), 5)
    die = st.sidebar.selectbox(t(lang, "die"), list(DIES.keys()), index=0)
    thickness_um = st.sidebar.slider(t(lang, "thickness"), 1, 200, 20, 1)
    area_cm2 = st.sidebar.number_input(t(lang, "area"), min_value=0.01, max_value=100.0, value=1.0, step=0.1)
    power_w = st.sidebar.number_input(t(lang, "power"), min_value=1.0, max_value=500.0, value=50.0, step=1.0)
    t_sink_c = st.sidebar.number_input(t(lang, "sink"), min_value=0.0, max_value=120.0, value=45.0, step=1.0)
    budget = st.sidebar.number_input(t(lang, "budget"), min_value=0.005, max_value=1.0, value=0.05, step=0.005)
    if cooling:
        w_nos, w_thermal = COOLING_WEIGHTS["nos"], COOLING_WEIGHTS["thermal"]
    else:
        w_nos = st.sidebar.slider("NOS", 0.30, 0.80, 0.55, 0.05); w_thermal = 0.0
    st.sidebar.divider()
    st.sidebar.subheader(t(lang, "source"))
    mp_key = _mp_key(); has_key = bool(mp_key)
    source = st.sidebar.radio(t(lang, "mode"), [t(lang, "demo"), t(lang, "live")], index=0 if not has_key else 1)
    max_results = st.sidebar.slider(t(lang, "max_api"), 20, 200, 80, 10)
    run = st.sidebar.button(t(lang, "run"), type="primary", use_container_width=True)
    cleaned = [e.strip() for e in sys_key.split(",") if e.strip()]
    return {"elements": cleaned, "exact": exact, "process": PROCESS_OPTIONS[process_label], "process_label": process_label, "temp": temp, "w_nos": w_nos, "w_thermal": w_thermal, "cooling": cooling, "application": app_key, "substrate": substrate, "die": die, "thickness_um": thickness_um, "area_cm2": area_cm2, "power_w": power_w, "t_sink_c": t_sink_c, "budget": budget, "live": source == t(lang, "live") and has_key, "mp_key": mp_key, "max_results": max_results, "run": run, "standard": std_key, "lang": lang}

def screen(cfg):
    if len(cfg["elements"]) < 2:
        st.warning(t(cfg.get("lang","en"), "empty")); return None, None
    if cfg["live"]:
        try:
            cands = run_live(cfg["elements"], api_key=cfg.get("mp_key"), max_results=cfg["max_results"], exact_chemsys=cfg["exact"]); mode = "materials_project"
        except Exception as exc:
            st.error(str(exc)); cands = run_demo(cfg["elements"], exact_chemsys=cfg["exact"]); mode = "demo_fallback"
    else:
        cands = run_demo(cfg["elements"], exact_chemsys=cfg["exact"]); mode = "demo"
    rows = []
    for c in cands:
        manuf = evaluate(c, cfg["process"], cfg["temp"])
        therm = evaluate_thermal(c["formula"], cfg["substrate"], cfg["application"])
        stack = evaluate_stack(c["formula"], thickness_um=cfg["thickness_um"], area_cm2=cfg["area_cm2"], power_w=cfg["power_w"], t_sink_c=cfg["t_sink_c"], budget_k_per_w=cfg["budget"], die=cfg["die"], substrate=cfg["substrate"])
        rows.append({**c, "manuf_score": manuf.score, "manuf_risk": manuf.risk_level, "manuf_notes": manuf.notes, "veto": manuf.veto, "kappa_score": therm.score, "kappa_wm_k": therm.kappa_wm_k, "cte_ppm_k": therm.cte_ppm_k, "dcte_ppm_k": therm.dcte_ppm_k, "thermal_citation": therm.citation, "thermal_notes": therm.notes, "thermal_verdict": therm.verdict, "heat_spreader_ok": therm.heat_spreader_ok, "r_coat": stack.r_coat_k_per_w, "dt_coat": stack.dt_coat_k, "tj_lower_bound": stack.tj_lower_bound_c, "stack_verdict": stack.verdict, "stack_notes": stack.notes, "within_budget": stack.within_budget, "citation_line": getattr(therm, "citation", None)})
    ranked = attach_ranks(rows, w_nos=cfg["w_nos"], w_thermal=cfg["w_thermal"])
    front = set(pareto_front(ranked, cooling=cfg["cooling"]))
    for r in ranked:
        r["pareto"] = (r.get("material_id") in front) or (r.get("formula") in front)
    return ranked, mode

def metrics(rows, mode, cooling, lang):
    a,b,c,d = st.columns(4)
    a.metric(t(lang,"candidates"), len(rows))
    b.metric(t(lang,"pareto"), sum(1 for r in rows if r["pareto"]))
    if cooling:
        c.metric(t(lang,"citable"), sum(1 for r in rows if r.get("kappa_wm_k") is not None))
        d.metric(t(lang,"coupon"), sum(1 for r in rows if r.get("thermal_verdict")=="proceed_to_coupon"))
    else:
        c.metric("risk", sum(1 for r in rows if r["manuf_risk"] in ("low","medium")))
        d.metric(t(lang,"source"), "Demo" if mode.startswith("demo") else "MP")

def scatter(rows, cooling):
    fig = go.Figure()
    for tier, color in TIER_COLORS.items():
        chunk = [r for r in rows if r["tier"] == tier]
        if not chunk: continue
        xs = [r["kappa_score"] if cooling else r["NOS"] for r in chunk]
        fig.add_trace(go.Scatter(x=xs, y=[r["manuf_score"] for r in chunk], mode="markers", name=tier, marker=dict(size=[16 if r["pareto"] else 11 for r in chunk], color=color, symbol=["diamond" if r["pareto"] else "circle" for r in chunk]), text=[f"{r['formula']} {r.get('kappa_wm_k')}" for r in chunk], hoverinfo="text"))
    fig.update_layout(height=500, xaxis=dict(range=[0,1]), yaxis=dict(range=[0,1]), template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

def table(rows, cooling, lang, cfg, mode):
    df = pd.DataFrame([{"Rank": r["rank"], "Formula": r["formula"], "Combined": r["combined"], "NOS": r["NOS"], "Manuf": r["manuf_score"], "Riesgo": r["manuf_risk"], "Dictamen": r.get("thermal_verdict"), "k_WmK": r.get("kappa_wm_k"), "R_coat": r.get("r_coat"), "dT_K": r.get("dt_coat"), "Tj_min_C": r.get("tj_lower_bound"), "Pareto": "si" if r["pareto"] else "", "id": r.get("material_id")} for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True, height=420)
    buf = io.StringIO(); df.to_csv(buf, index=False)
    c1,c2,c3 = st.columns(3)
    with c1: st.download_button(t(lang,"csv"), data=buf.getvalue(), file_name=f"nos_ranking_{lang}.csv", mime="text/csv")
    with c2: st.download_button(t(lang,"pdf"), data=build_pdf(lang, cfg, rows, mode), file_name=f"nos_report_{lang}.pdf", mime="application/pdf")
    with c3: st.download_button(t(lang,"pdf_all"), data=build_zip_all_langs(cfg, rows, mode), file_name="nos_reports_es_en_fr_de.zip", mime="application/zip")

def detail(rows, lang):
    labels = [f"{r['rank']:02d} · {r['formula']} ({r['combined']:.3f})" for r in rows[:40]]
    if not labels: return
    choice = st.selectbox(t(lang,"fiche"), labels)
    row = rows[labels.index(choice)]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("NOS", f"{row['NOS']:.3f}"); c2.metric("Manuf", f"{row['manuf_score']:.3f}")
    c3.metric("k", "—" if row.get("kappa_wm_k") is None else f"{row['kappa_wm_k']:.1f}")
    c4.metric("Combined", f"{row['combined']:.3f}")
    verdict = row.get("thermal_verdict") or "missing_thermal_data"
    st.info(f"{t(lang,'verdict_h')}: {verdict} — {verdict_text(lang, verdict)}")
    for title, key in [("Stack","stack_notes"), ("Thermal","thermal_notes"), ("Process","manuf_notes")]:
        st.write(f"**{title}**")
        for note in row.get(key) or []: st.write(f"- {note}")

def standards_panel(std_key, lang):
    spec = STANDARDS[std_key]
    st.subheader(t(lang,"tests_h"))
    st.caption(spec["blurb"] + " · " + t(lang,"applies") + ": " + spec["applies_to"])
    st.dataframe(pd.DataFrame([{t(lang,"code"): x["code"], t(lang,"test"): x["name"], t(lang,"hits"): x["hits"], t(lang,"fail"): x["fail"]} for x in spec["tests"]]), use_container_width=True, hide_index=True)
    st.info(spec["next_step"])

def main():
    cfg = sidebar(); lang = cfg.get("lang","es")
    header(lang)
    if not cfg["run"]:
        st.info(t(lang,"empty")); standards_panel(cfg["standard"], lang); return
    rows, mode = screen(cfg)
    if rows is None: return
    st.success(f"{len(rows)} · {APPLICATIONS[cfg['application']]['label']} · {cfg['substrate']} · {cfg['process_label']}")
    metrics(rows, mode, cfg["cooling"], lang)
    scatter(rows, cfg["cooling"])
    st.subheader(t(lang,"ranking")); table(rows, cfg["cooling"], lang, cfg, mode)
    st.subheader(t(lang,"verdict_h")); detail(rows, lang)
    standards_panel(cfg["standard"], lang)
    st.caption(t(lang,"disclaimer") + "  ·  (c) 2026 Wilmer Gaspar Espinoza Castillo · CC BY-NC-SA 4.0")

if __name__ == "__main__":
    main()
