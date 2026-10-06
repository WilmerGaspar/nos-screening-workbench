from __future__ import annotations
import io, os
from pathlib import Path
from urllib.parse import quote
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from nos_score import run_demo, run_live
from pipeline import evaluate_candidates
from ranking import RELIABILITY_WEIGHTS, normalize_weights, rank_stability
from die_stack import DIES
from thermal import APPLICATIONS, SUBSTRATES
from interface import DEFAULT_SHARE_MAX, DEFAULT_TIM_KAPPA, DEFAULT_TIM_UM
from demo_systems import DEMO_SYSTEMS
from standards import STANDARDS
from i18n import LANGS, t, verdict_text
from report_pdf import build_pdf, build_zip_all_langs
from coupon_pdf import build_coupon_pdf, pick_phase
from stack_sites import DEFAULT_SITE, SITES, TIM_REF, site_note

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "logo.jpg"
VERSION = "v0.3"
st.set_page_config(page_title="NOS Screening Workbench", page_icon="◆", layout="wide")
PROCESS_OPTIONS = {"PVD (sputter / arc)": "pvd", "Thermal spray / HVOF": "thermal_spray", "Electroplating": "electroplating"}
TIER_COLORS = {"Experimentally verified": "#0f766e", "Partially backed": "#ca8a04", "Well-calculated (DFT)": "#1d4ed8", "Exploratory": "#6b7280"}
DEFAULT_CONTACT = "wilmergasparespinoza@gmail.com"

def _secret(name, default=""):
    val = os.environ.get(name, "")
    if val: return val
    try: return str(st.secrets.get(name, "") or default)
    except Exception: return default

def _mp_key():
    return _secret("MP_API_KEY")

def _contact():
    return _secret("NOS_CONTACT_EMAIL", DEFAULT_CONTACT) or DEFAULT_CONTACT

def header(lang):
    c1, c2 = st.columns([1, 8])
    with c1:
        if LOGO.exists(): st.image(str(LOGO), width=72)
    with c2:
        st.title(t(lang, "title")); st.caption(t(lang, "subtitle") + f"  ·  {VERSION}")

def sidebar():
    lang = st.sidebar.selectbox("Language / Idioma", list(LANGS.keys()), format_func=lambda k: LANGS[k], index=0)
    st.sidebar.header(t(lang, "mission"))
    app_key = st.sidebar.selectbox(t(lang, "application"), list(APPLICATIONS.keys()), format_func=lambda k: APPLICATIONS[k]["label"], index=1)
    spec = APPLICATIONS[app_key]; cooling = app_key != "generic_coating"
    st.sidebar.caption(spec["blurb"])
    keys = [s["key"] for s in DEMO_SYSTEMS]
    default_idx = keys.index("cited7") if "cited7" in keys else 0
    sys_key = st.sidebar.selectbox(t(lang, "system"), keys, index=default_idx, format_func=lambda k: next(s["label"] for s in DEMO_SYSTEMS if s["key"] == k))
    exact = st.sidebar.toggle(t(lang, "exact"), value=True)
    std_key = st.sidebar.selectbox(t(lang, "standard"), list(STANDARDS.keys()), index=0 if cooling else 3, format_func=lambda k: STANDARDS[k]["label"])
    site_keys = list(SITES.keys())
    site_key = st.sidebar.selectbox(t(lang, "site"), site_keys, index=site_keys.index(DEFAULT_SITE), format_func=lambda k: SITES[k]["label"])
    st.sidebar.caption(SITES[site_key]["blurb"])
    process_label = st.sidebar.selectbox(t(lang, "process"), list(PROCESS_OPTIONS.keys()))
    substrate = st.sidebar.selectbox(t(lang, "substrate"), list(SUBSTRATES.keys()), index=list(SUBSTRATES.keys()).index(spec["default_substrate"]))
    temp = st.sidebar.slider(t(lang, "temp"), 25, 800, int(spec["default_temp_c"]), 5)
    die = st.sidebar.selectbox(t(lang, "die"), list(DIES.keys()), index=0)
    thickness_um = st.sidebar.slider(t(lang, "thickness"), 1, 200, 20, 1)
    area_cm2 = st.sidebar.number_input(t(lang, "area"), min_value=0.01, max_value=100.0, value=1.0, step=0.1)
    power_w = st.sidebar.number_input(t(lang, "power"), min_value=1.0, max_value=500.0, value=50.0, step=1.0)
    t_sink_c = st.sidebar.number_input(t(lang, "sink"), min_value=0.0, max_value=120.0, value=45.0, step=1.0)
    with st.sidebar.expander(t(lang, "tim_h"), expanded=False):
        st.caption(t(lang, "tim_caption"))
        tim_kappa = st.number_input(t(lang, "tim_kappa"), min_value=0.5, max_value=50.0, value=float(DEFAULT_TIM_KAPPA), step=0.5)
        tim_um = st.number_input(t(lang, "tim_um"), min_value=1.0, max_value=500.0, value=float(DEFAULT_TIM_UM), step=5.0)
        share_pct = st.slider(t(lang, "share_max"), 2, 50, int(round(DEFAULT_SHARE_MAX * 100)), 1)
    weights = dict(RELIABILITY_WEIGHTS); w_nos = 0.55
    if cooling:
        with st.sidebar.expander(t(lang, "weights_h"), expanded=False):
            wn = st.slider(t(lang, "w_nos"), 0, 100, int(RELIABILITY_WEIGHTS["nos"] * 100), 5)
            wm = st.slider(t(lang, "w_manuf"), 0, 100, int(RELIABILITY_WEIGHTS["manuf"] * 100), 5)
            wi = st.slider(t(lang, "w_iface"), 0, 100, int(RELIABILITY_WEIGHTS["interface"] * 100), 5)
            weights = normalize_weights({"nos": wn, "manuf": wm, "interface": wi})
            st.caption(" / ".join(f"{k} {v:.0%}" for k, v in weights.items()))
    else:
        w_nos = st.sidebar.slider("NOS", 0.30, 0.80, 0.55, 0.05)
    st.sidebar.divider(); st.sidebar.subheader(t(lang, "source"))
    mp_key = _mp_key(); has_key = bool(mp_key)
    source = st.sidebar.radio(t(lang, "mode"), [t(lang, "demo"), t(lang, "live")], index=0 if not has_key else 1)
    max_results = st.sidebar.slider(t(lang, "max_api"), 20, 200, 80, 10)
    run = st.sidebar.button(t(lang, "run"), type="primary", use_container_width=True)
    cleaned = [e.strip() for e in sys_key.split(",") if e.strip()]
    return {"elements": cleaned, "exact": exact, "process": PROCESS_OPTIONS[process_label], "process_label": process_label, "temp": temp, "w_nos": w_nos, "weights": weights, "cooling": cooling, "application": app_key, "substrate": substrate, "die": die, "thickness_um": thickness_um, "area_cm2": area_cm2, "power_w": power_w, "t_sink_c": t_sink_c, "budget": 0.05, "tim_kappa": tim_kappa, "tim_um": tim_um, "share_max": share_pct / 100.0, "live": source == t(lang, "live") and has_key, "mp_key": mp_key, "max_results": max_results, "run": run, "standard": std_key, "lang": lang, "site": site_key}

def screen(cfg):
    lang = cfg.get("lang", "en")
    token = ",".join(cfg.get("elements") or []).replace(" ", "").lower()
    if token not in {"cited7", "cited"} and len(cfg["elements"]) < 2:
        st.warning(t(lang, "empty")); return None, None
    if cfg["live"]:
        try:
            cands = run_live(cfg["elements"], api_key=cfg.get("mp_key"), max_results=cfg["max_results"], exact_chemsys=cfg["exact"]); mode = "materials_project"
        except Exception as exc:
            st.error(str(exc)); cands = run_demo(cfg["elements"], exact_chemsys=cfg["exact"]); mode = "demo_fallback"
    else:
        cands = run_demo(cfg["elements"], exact_chemsys=cfg["exact"]); mode = "demo"
    if not cands:
        st.warning(t(lang, "no_rows")); return None, None
    return evaluate_candidates(cands, cfg), mode

def metrics(rows, mode, cooling, lang):
    a,b,c,d = st.columns(4)
    a.metric(t(lang,"candidates"), len(rows)); b.metric(t(lang,"pareto"), sum(1 for r in rows if r["pareto"]))
    if cooling:
        c.metric(t(lang,"kappa_ok"), sum(1 for r in rows if r.get("relevance_verdict") == "kappa_not_limiting"))
        d.metric(t(lang,"coupon"), sum(1 for r in rows if r.get("verdict") == "proceed_to_coupon"))
    else:
        c.metric("risk", sum(1 for r in rows if r["manuf_risk"] in ("low","medium")))
        d.metric(t(lang,"source"), "Demo" if mode.startswith("demo") else "MP")

def stability_panel(rows, lang):
    viable = [r for r in rows if r.get("verdict") != "process_veto"]
    stab = rank_stability(viable)
    if not stab: return
    top = stab[0]
    st.info(f"**{t(lang,'stability')}:** " + t(lang, "stability_line").format(f=top["formula"], p=top["share_first"], n=top["of"]))

def scatter(rows, cooling, lang):
    fig = go.Figure()
    xkey = "interface_score" if cooling else "NOS"
    for tier, color in TIER_COLORS.items():
        chunk = [r for r in rows if r["tier"] == tier]
        if not chunk: continue
        fig.add_trace(go.Scatter(x=[r[xkey] for r in chunk], y=[r["manuf_score"] for r in chunk], mode="markers", name=tier, marker=dict(size=[16 if r["pareto"] else 11 for r in chunk], color=color, symbol=["diamond" if r["pareto"] else "circle" for r in chunk]), text=[f"{r['formula']} · {r.get('verdict')}" for r in chunk], hoverinfo="text"))
    fig.update_layout(height=440, xaxis=dict(range=[0,1], title=t(lang,"col_iface") if cooling else "NOS"), yaxis=dict(range=[0,1], title="Manuf"), template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

def tim_panel(cfg):
    st.subheader("Esto no es un TIM / This is not a TIM")
    st.caption(site_note(cfg.get("site") or DEFAULT_SITE))
    st.dataframe(pd.DataFrame(TIM_REF), use_container_width=True, hide_index=True)

def _num(v, spec):
    return None if v is None else float(format(v, spec))

def table(rows, cooling, lang, cfg, mode):
    df = pd.DataFrame([{
        "Rank": r["rank"], "Formula": r["formula"], "Score": r["combined"], "NOS": r["NOS"], "Manuf": r["manuf_score"],
        t(lang,"col_iface"): r.get("interface_score"), t(lang,"col_dcte"): r.get("dcte_max"),
        t(lang,"col_verdict"): r.get("verdict"), "k bulk": r.get("kappa_wm_k"), t(lang,"col_kneed"): r.get("kappa_needed"),
        t(lang,"col_dtc"): _num(r.get("dt_coat"), ".2f"), t(lang,"col_dtt"): _num(r.get("dt_tim"), ".2f"),
        t(lang,"col_flags"): len(r.get("flags") or []),
    } for r in rows])
    st.dataframe(df, use_container_width=True, hide_index=True, height=320)
    buf = io.StringIO(); df.to_csv(buf, index=False)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.download_button(t(lang,"csv"), data=buf.getvalue(), file_name=f"nos_ranking_{lang}.csv", mime="text/csv")
    with c2: st.download_button(t(lang,"pdf"), data=build_pdf(lang, cfg, rows, mode), file_name=f"nos_report_{lang}.pdf", mime="application/pdf")
    with c3: st.download_button(t(lang,"pdf_all"), data=build_zip_all_langs(cfg, rows, mode), file_name="nos_reports_es_en_fr_de.zip", mime="application/zip")
    phase = pick_phase(rows)
    with c4:
        if phase:
            st.download_button("Coupon request PDF", data=build_coupon_pdf(cfg, rows, phase=phase, contact=f"Wilmer Espinoza - {_contact()}"), file_name=f"nos_coupon_{phase.get('formula','phase')}.pdf", mime="application/pdf")
        else:
            st.caption(verdict_text(lang, "process_veto"))

def request_panel(rows, cfg, lang):
    st.subheader(t(lang, "request_h"))
    phase = pick_phase(rows) or {}
    subject = f"NOS study request - {phase.get('formula', '')} - {SITES.get(cfg.get('site'), {}).get('label', '')}"
    body = "\n".join([
        "Hi Wilmer,", "",
        "I ran the NOS Screening Workbench and would like a study / coupon for my case.", "",
        f"Application: {APPLICATIONS[cfg['application']]['label']}",
        f"Layer site: {SITES.get(cfg.get('site'), {}).get('label', '')}",
        f"Process: {cfg.get('process_label')} - {cfg.get('thickness_um')} um on {cfg.get('substrate')}",
        f"Service T: {cfg.get('temp')} C - TIM: {cfg.get('tim_um')} um at {cfg.get('tim_kappa')} W/mK",
        f"Top phase in my run: {phase.get('formula', '-')} ({phase.get('verdict', '-')})", "",
        "My real stack / what fails today:", "",
        "Company / role (optional):", "",
    ])
    url = f"mailto:{_contact()}?subject={quote(subject)}&body={quote(body)}"
    st.link_button(t(lang, "request_btn"), url, type="primary")
    st.caption(t(lang, "request_caption"))

def detail(rows, lang):
    labels = [f"{r['rank']:02d} · {r['formula']} ({r['combined']:.3f})" for r in rows[:40]]
    if not labels: return
    choice = st.selectbox(t(lang,"fiche"), labels); row = rows[labels.index(choice)]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(t(lang,"col_iface"), f"{row['interface_score']:.3f}", None if row.get("dcte_max") is None else f"dCTE {row['dcte_max']:.1f} ppm/K", delta_color="off")
    c2.metric("Manuf", f"{row['manuf_score']:.3f}")
    c3.metric("k bulk / " + t(lang,"col_kneed"), ("—" if row.get("kappa_wm_k") is None else f"{row['kappa_wm_k']:.1f}") + f" / {row['kappa_needed']:.1f}")
    c4.metric("Score", f"{row['combined']:.3f}")
    verdict = row.get("verdict") or "coupon_cte_unknown"
    st.info(f"{t(lang,'verdict_h')}: {verdict} — {verdict_text(lang, verdict)}")
    with st.expander(t(lang, "notes_h"), expanded=True):
        for line in (row.get("interface_notes") or []) + (row.get("relevance_notes") or []) + (row.get("flag_notes") or []) + (row.get("manuf_notes") or []):
            st.markdown(f"- {line}")
        if row.get("thermal_citation"):
            st.caption(row["thermal_citation"])

def standards_panel(std_key, lang):
    spec = STANDARDS[std_key]
    st.subheader(t(lang,"tests_h"))
    st.caption(spec["blurb"])
    st.dataframe(pd.DataFrame(spec["tests"]), use_container_width=True, hide_index=True)
    st.info(spec["next_step"])

def main():
    cfg = sidebar(); lang = cfg.get("lang","es"); header(lang)
    if not cfg["run"]:
        st.info(t(lang,"empty")); tim_panel(cfg); standards_panel(cfg["standard"], lang); return
    rows, mode = screen(cfg)
    if rows is None: return
    st.success(f"{len(rows)} · {APPLICATIONS[cfg['application']]['label']} · {cfg['substrate']} · {SITES.get(cfg.get('site'),{}).get('label','')}")
    metrics(rows, mode, cfg["cooling"], lang)
    if cfg["cooling"]: stability_panel(rows, lang)
    scatter(rows, cfg["cooling"], lang)
    st.subheader(t(lang,"ranking")); table(rows, cfg["cooling"], lang, cfg, mode)
    request_panel(rows, cfg, lang)
    st.subheader(t(lang,"verdict_h")); detail(rows, lang)
    tim_panel(cfg)
    standards_panel(cfg["standard"], lang)
    st.caption(t(lang,"disclaimer") + "  ·  (c) 2026 Wilmer Gaspar Espinoza Castillo")

if __name__ == "__main__":
    main()
