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
from stack_sites import DEFAULT_SITE, SITES, site_note, site_spec, tim_ref
import results as rlog

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "logo.jpg"
VERSION = "v0.4"
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
    site_key = st.sidebar.selectbox(t(lang, "site"), site_keys, index=site_keys.index(DEFAULT_SITE), format_func=lambda k: site_spec(k, lang)["label"])
    st.sidebar.caption(site_spec(site_key, lang)["blurb"])
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
    run = st.sidebar.button(t(lang, "run"), type="primary", width="stretch")
    cleaned = [e.strip() for e in sys_key.split(",") if e.strip()]
    return {"elements": cleaned, "exact": exact, "process": PROCESS_OPTIONS[process_label], "process_label": process_label, "temp": temp, "w_nos": w_nos, "weights": weights, "cooling": cooling, "application": app_key, "substrate": substrate, "die": die, "thickness_um": thickness_um, "area_cm2": area_cm2, "power_w": power_w, "t_sink_c": t_sink_c, "budget": 0.05, "tim_kappa": tim_kappa, "tim_um": tim_um, "share_max": share_pct / 100.0, "live": source == t(lang, "live") and has_key, "mp_key": mp_key, "max_results": max_results, "run": run, "standard": std_key, "lang": lang, "site": site_key}

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_live(elements, exact, max_results, _api_key):
    # One Materials Project query per (system, exact, max) per hour; the key is not hashed.
    return run_live(list(elements), api_key=_api_key, max_results=max_results, exact_chemsys=exact)

def screen(cfg):
    lang = cfg.get("lang", "en")
    token = ",".join(cfg.get("elements") or []).replace(" ", "").lower()
    if token not in {"cited7", "cited"} and len(cfg["elements"]) < 2:
        st.warning(t(lang, "empty")); return None, None
    if cfg["live"]:
        try:
            cands = _cached_live(tuple(cfg["elements"]), cfg["exact"], cfg["max_results"], cfg.get("mp_key")); mode = "materials_project"
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
    st.plotly_chart(fig, width="stretch")

def tim_panel(cfg, lang):
    st.subheader(t(lang, "tim_title"))
    st.caption(site_note(cfg.get("site") or DEFAULT_SITE, lang))
    st.dataframe(pd.DataFrame(tim_ref(lang)), width="stretch", hide_index=True)

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
    st.dataframe(df, width="stretch", hide_index=True, height=320)
    buf = io.StringIO(); df.to_csv(buf, index=False)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.download_button(t(lang,"csv"), data=buf.getvalue(), file_name=f"nos_ranking_{lang}.csv", mime="text/csv", on_click="ignore")
    with c2: st.download_button(t(lang,"pdf"), data=build_pdf(lang, cfg, rows, mode), file_name=f"nos_report_{lang}.pdf", mime="application/pdf", on_click="ignore")
    with c3: st.download_button(t(lang,"pdf_all"), data=build_zip_all_langs(cfg, rows, mode), file_name="nos_reports_es_en_fr_de.zip", mime="application/zip", on_click="ignore")
    phase = pick_phase(rows)
    with c4:
        if phase:
            st.download_button(t(lang, "coupon_pdf"), data=build_coupon_pdf(cfg, rows, phase=phase, contact=f"Wilmer Espinoza - {_contact()}"), file_name=f"nos_coupon_{phase.get('formula','phase')}.pdf", mime="application/pdf", on_click="ignore")
        else:
            st.caption(verdict_text(lang, "process_veto"))

def email_options(lang, label, subject, body, primary=False):
    """A mailto: link alone opens a blank tab when the browser has no mail app (e.g. Gmail
    users on the web), so offer webmail compose links and the text to copy as well."""
    to, su, bo = quote(_contact()), quote(subject), quote(body)
    gmail = f"https://mail.google.com/mail/?view=cm&fs=1&to={to}&su={su}&body={bo}"
    outlook = f"https://outlook.live.com/mail/0/deeplink/compose?to={to}&subject={su}&body={bo}"
    mailto = f"mailto:{_contact()}?subject={su}&body={bo}"
    c1, c2, c3 = st.columns(3)
    with c1: st.link_button(f"{label} · Gmail", gmail, type="primary" if primary else "secondary", width="stretch")
    with c2: st.link_button(f"{label} · Outlook", outlook, width="stretch")
    with c3: st.link_button(t(lang, "email_app"), mailto, width="stretch")
    with st.expander(t(lang, "email_copy")):
        st.markdown(f"{t(lang, 'email_to')}: **{_contact()}**")
        st.code(subject, language=None)
        st.code(body, language=None)

def request_panel(rows, cfg, lang):
    st.subheader(t(lang, "request_h"))
    phase = pick_phase(rows) or {}
    site_en = site_spec(cfg.get("site"), "en")["label"]
    subject = f"NOS study request - {phase.get('formula', '')} - {site_en}"
    body = "\n".join([
        "Hi Wilmer,", "",
        "I ran the NOS Screening Workbench and would like a study / coupon for my case.", "",
        f"Application: {APPLICATIONS[cfg['application']]['label']}",
        f"Layer site: {site_en}",
        f"Process: {cfg.get('process_label')} - {cfg.get('thickness_um')} um on {cfg.get('substrate')}",
        f"Service T: {cfg.get('temp')} C - TIM: {cfg.get('tim_um')} um at {cfg.get('tim_kappa')} W/mK",
        f"Top phase in my run: {phase.get('formula', '-')} ({phase.get('verdict', '-')})", "",
        "My real stack / what fails today:", "",
        "Company / role (optional):", "",
    ])
    email_options(lang, t(lang, "request_btn"), subject, body, primary=True)
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
    st.dataframe(pd.DataFrame(spec["tests"]), width="stretch", hide_index=True)
    st.info(spec["next_step"])

def _opt(label, lang, **kw):
    return st.number_input(label, value=None, placeholder=t(lang, "f_optional"), **kw)

def _next_coupon_id(log):
    ids = {r["coupon_id"] for r in log}
    n = len(ids) + 1
    while f"C-{n:02d}" in ids:
        n += 1
    return f"C-{n:02d}"

def results_panel(cfg, lang, top_phase):
    st.subheader(t(lang, "log_h"))
    st.caption(t(lang, "log_caption"))
    log = st.session_state.setdefault("coupon_log", [])
    # The ID field must move on after each add/undo/upload, or the next stage-0 entry would
    # silently replace the previous coupon (results.add treats same ID + stage as a correction).
    if st.session_state.pop("log_id_stale", False) or "lf_coupon_id" not in st.session_state:
        st.session_state["lf_coupon_id"] = _next_coupon_id(log)
    flash = st.session_state.pop("log_flash", None)

    up = st.file_uploader(t(lang, "log_upload"), type=["csv"], key="log_upload")
    if up is not None:
        sig = (up.name, up.size)
        if st.session_state.get("log_upload_sig") != sig:
            loaded, problems = rlog.from_csv(up.getvalue().decode("utf-8", errors="replace"))
            st.session_state["coupon_log"] = log = loaded
            st.session_state["log_upload_sig"] = sig
            st.session_state["log_upload_problems"] = problems
            st.session_state["lf_coupon_id"] = _next_coupon_id(log)
        st.success(t(lang, "log_loaded").format(n=len(log)))
        problems = st.session_state.get("log_upload_problems") or []
        if problems:
            st.warning(t(lang, "log_problems") + "\n" + "\n".join(f"- {p}" for p in problems[:20]))

    with st.form("coupon_form", clear_on_submit=False):
        st.markdown(f"**{t(lang, 'log_form_h')}**")
        c1, c2, c3 = st.columns(3)
        with c1:
            coupon_id = st.text_input(t(lang, "f_coupon_id"), key="lf_coupon_id")
            coating = st.text_input(t(lang, "f_coating"), value=(top_phase or {}).get("formula", ""))
            process = st.selectbox(t(lang, "f_process"), list(PROCESS_OPTIONS.keys()) + ["Arc / flame wire spray", "Other"],
                                   index=list(PROCESS_OPTIONS.keys()).index(cfg.get("process_label")) if cfg.get("process_label") in PROCESS_OPTIONS else 0)
            shop = st.text_input(t(lang, "f_shop"))
            subs = list(SUBSTRATES.keys())
            substrate = st.selectbox(t(lang, "f_substrate"), subs, index=subs.index(cfg["substrate"]) if cfg.get("substrate") in subs else 0)
            target = st.number_input(t(lang, "f_target"), min_value=0.0, max_value=5000.0, value=float(cfg.get("thickness_um") or 20.0), step=5.0)
        with c2:
            stage = st.radio(t(lang, "f_stage"), list(rlog.STAGES), horizontal=True)
            tape = st.selectbox(t(lang, "f_tape"), list(rlog.TAPE))
            spall = st.selectbox(t(lang, "f_spall"), list(rlog.SPALLATION))
            crack = st.selectbox(t(lang, "f_crack"), list(rlog.CRACK_ORIGIN))
            cycles = _opt(t(lang, "f_cycles"), lang, min_value=0, step=1)
            peak = _opt(t(lang, "f_peak"), lang, min_value=-60.0, max_value=1500.0, step=5.0)
        with c3:
            thick = _opt(t(lang, "f_thickness"), lang, min_value=0.0, max_value=5000.0, step=1.0)
            poro = _opt(t(lang, "f_porosity"), lang, min_value=0.0, max_value=100.0, step=0.5)
            imc = _opt(t(lang, "f_imc"), lang, min_value=0.0, max_value=5000.0, step=0.5)
            rc = _opt(t(lang, "f_rc"), lang, min_value=0.0, step=0.01)
            notes = st.text_area(t(lang, "f_notes"), height=90)
        share = st.checkbox(t(lang, "f_share"), value=False)
        submitted = st.form_submit_button(t(lang, "log_add"), type="primary")

    if submitted:
        rec = rlog.new_record(coupon_id=coupon_id, coating=coating, process=process, shop=shop, substrate=substrate,
                              target_thickness_um=target, stage=stage, thickness_um=thick, porosity_pct=poro,
                              tape_test=tape, spallation=spall, crack_origin=crack, cycles=cycles, peak_temp_c=peak,
                              imc_thickness_um=imc, contact_resistance_mohm=rc, notes=notes, share_anonymized=share)
        new_log, errors = rlog.add(log, rec)
        if errors:
            st.error("\n".join(f"- {e}" for e in errors))
        else:
            st.session_state["coupon_log"] = new_log
            st.session_state["log_id_stale"] = True
            st.session_state["log_flash"] = t(lang, "log_added").format(id=coupon_id, stage=stage, outcome=rlog.outcome(new_log[-1]))
            st.rerun()
    if flash:
        st.success(flash)

    if not log:
        st.info(t(lang, "log_empty"))
        return
    a, b, c = st.columns(3)
    a.metric(t(lang, "log_n"), len({r["coupon_id"] for r in log}))
    b.metric(t(lang, "log_iface"), sum(1 for r in log if rlog.outcome(r) == "interface_limited"))
    c.metric(t(lang, "log_pass"), sum(1 for r in log if rlog.outcome(r) == "passed_stage"))
    df = pd.DataFrame([{**r, "outcome": rlog.outcome(r)} for r in log])
    st.dataframe(df, width="stretch", hide_index=True)
    last = log[-1]
    st.info(f"{last['coupon_id']} · {t(lang, 'f_stage')} {last['stage']}: {t(lang, 'o_' + rlog.outcome(last))}")
    st.markdown(f"**{t(lang, 'log_summary_h')}**")
    st.dataframe(pd.DataFrame(rlog.summarize(log)), width="stretch", hide_index=True)
    d1, d2, d4 = st.columns(3)
    with d1: st.download_button(t(lang, "log_csv"), data=rlog.to_csv(log), file_name="nos_coupon_log.csv", mime="text/csv", on_click="ignore")
    with d2: st.download_button(t(lang, "log_json"), data=rlog.to_json(log), file_name="nos_coupon_log.json", mime="application/json", on_click="ignore")
    with d4:
        if st.button(t(lang, "log_undo")):
            st.session_state["coupon_log"] = log[:-1]
            st.session_state["log_id_stale"] = True
            st.rerun()
    body = "Hi Wilmer,\n\nCoupon results from the NOS log:\n\n" + rlog.email_summary(log) + "\n\n(CSV and cross-section photos attached.)\n"
    email_options(lang, t(lang, "log_send"), "NOS coupon results", body)
    st.caption(t(lang, "log_send_caption"))

def screening_view(cfg, lang):
    if not st.session_state.get("nos_ran"):
        st.info(t(lang,"empty")); tim_panel(cfg, lang); standards_panel(cfg["standard"], lang); return None
    rows, mode = screen(cfg)
    if rows is None: return None
    st.success(f"{len(rows)} · {APPLICATIONS[cfg['application']]['label']} · {cfg['substrate']} · {site_spec(cfg.get('site'), lang)['label']}")
    metrics(rows, mode, cfg["cooling"], lang)
    if cfg["cooling"]: stability_panel(rows, lang)
    scatter(rows, cfg["cooling"], lang)
    st.subheader(t(lang,"ranking")); table(rows, cfg["cooling"], lang, cfg, mode)
    request_panel(rows, cfg, lang)
    st.subheader(t(lang,"verdict_h")); detail(rows, lang)
    tim_panel(cfg, lang)
    standards_panel(cfg["standard"], lang)
    return rows

def main():
    cfg = sidebar(); lang = cfg.get("lang","es"); header(lang)
    if cfg["run"]:
        # After the first run, results stay on screen and follow every sidebar change.
        st.session_state["nos_ran"] = True
    tab_screen, tab_log = st.tabs([t(lang, "tab_screen"), t(lang, "tab_log")])
    with tab_screen:
        rows = screening_view(cfg, lang)
    with tab_log:
        results_panel(cfg, lang, pick_phase(rows) if rows else None)
    st.caption(t(lang,"disclaimer") + "  ·  (c) 2026 Wilmer Gaspar Espinoza Castillo")

if __name__ == "__main__":
    main()
