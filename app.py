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
import ui_text as ui
import feedback

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "logo.jpg"
VERSION = "v0.5"
st.set_page_config(page_title="NOS Screening Workbench", page_icon="◆", layout="wide")
PROCESS_OPTIONS = {"PVD (sputter / arc)": "pvd", "Thermal spray / HVOF": "thermal_spray", "Electroplating": "electroplating"}
TIER_COLORS = {"Experimentally verified": "#0f766e", "Partially backed": "#ca8a04", "Well-calculated (DFT)": "#1d4ed8", "Exploratory": "#6b7280"}
DEFAULT_CONTACT = "wilmergasparespinoza@gmail.com"
# Display only: the verdict codes themselves (and the CSV) are unchanged.
VERDICT_COLOR = {"proceed_to_coupon": "green", "coupon_high_cte_risk": "orange", "coupon_cte_unknown": "orange",
                 "kappa_significant": "red", "process_veto": "red"}
VERDICT_DOT = {"green": "🟢", "orange": "🟠", "red": "🔴"}
UI_LANGS = ("es", "en")

def show_df(df, lang, fmt=None, column_config=None):
    """Screen-only copy: numbers formatted as text and empty cells as "sin dato" / "no data".
    st.dataframe draws nulls as "None" whatever the Styler says, so the copy holds strings.
    The CSV downloads are built from the original data elsewhere and keep empty cells."""
    fmt = fmt or {}
    na = t(lang, "no_data")
    view = df.copy()
    cfg = dict(column_config or {})
    for col in view.columns:
        if col in fmt:
            view[col] = df[col].map(lambda v, f=fmt[col]: na if pd.isna(v) else f.format(v))
            cfg[col] = {**cfg.get(col, st.column_config.Column()), "alignment": "right"}
        elif df[col].isna().any():
            view[col] = df[col].map(lambda v: na if v is None or (isinstance(v, float) and pd.isna(v)) else v)
    st.dataframe(view, width="stretch", hide_index=True, column_config=cfg)

def _ranking_fmt(lang):
    f = {t(lang, "d_score"): "{:.4f}", "NOS": "{:.4f}", t(lang, "d_manuf"): "{:.4f}", t(lang, "d_iface"): "{:.4f}",
         t(lang, "d_dcte"): "{:.1f}", t(lang, "d_kbulk"): "{:.1f}", t(lang, "d_kneed"): "{:.1f}",
         t(lang, "d_dtc"): "{:.2f}", t(lang, "d_dtt"): "{:.2f}"}
    return f

def _secret(name, default=""):
    val = os.environ.get(name, "")
    if val: return val
    try: return str(st.secrets.get(name, "") or default)
    except Exception: return default

def _mp_key():
    return _secret("MP_API_KEY")

def _contact():
    return _secret("NOS_CONTACT_EMAIL", DEFAULT_CONTACT) or DEFAULT_CONTACT

def verdict_label(lang, code, dot=False):
    code = code or "coupon_cte_unknown"
    label = t(lang, f"vl_{code}")
    return f"{VERDICT_DOT[VERDICT_COLOR.get(code, 'orange')]} {label}" if dot else label

def header(lang):
    c1, c2 = st.columns([1, 8])
    with c1:
        if LOGO.exists(): st.image(str(LOGO), width=72)
    with c2:
        st.title(t(lang, "title"))
        st.markdown(f"#### {t(lang, 'welcome')}")
        st.caption(t(lang, "subtitle") + f"  ·  {VERSION}")
    cols = st.columns(3)
    for col, n in zip(cols, (1, 2, 3)):
        with col, st.container(border=True):
            st.markdown(f"**{t(lang, f'step{n}_t')}**")
            st.caption(t(lang, f"step{n}_d"))

def sidebar():
    sb = st.sidebar
    # FR/DE stay available for the 4-language PDF ZIP, not as UI languages.
    lang = sb.selectbox("Language / Idioma", list(UI_LANGS), format_func=lambda k: LANGS[k], index=0)
    sb.header(t(lang, "mission"))
    app_key = sb.selectbox(t(lang, "application"), list(APPLICATIONS.keys()), format_func=lambda k: ui.app_label(lang, k), index=1)
    spec = APPLICATIONS[app_key]; cooling = app_key != "generic_coating"
    sb.caption(ui.app_blurb(lang, app_key))
    site_keys = list(SITES.keys())
    site_key = sb.selectbox(t(lang, "site"), site_keys, index=site_keys.index(DEFAULT_SITE), format_func=lambda k: site_spec(k, lang)["label"], help=t(lang, "h_site"))
    sb.caption(site_spec(site_key, lang)["blurb"])
    keys = [s["key"] for s in DEMO_SYSTEMS]
    default_idx = keys.index("cited7") if "cited7" in keys else 0
    sys_key = sb.selectbox(t(lang, "system"), keys, index=default_idx, format_func=lambda k: ui.system_label(lang, k), help=t(lang, "h_system"))
    process_label = sb.selectbox(t(lang, "process"), list(PROCESS_OPTIONS.keys()), format_func=lambda k: ui.process_label(lang, k))
    substrate = sb.selectbox(t(lang, "substrate"), list(SUBSTRATES.keys()), index=list(SUBSTRATES.keys()).index(spec["default_substrate"]))
    thickness_um = sb.slider(t(lang, "thickness"), 1, 200, 20, 1, help=t(lang, "h_thickness"))

    weights = dict(RELIABILITY_WEIGHTS); w_nos = 0.55
    mp_key = _mp_key(); has_key = bool(mp_key)
    with sb.expander(t(lang, "adv_h"), expanded=False):
        st.caption(t(lang, "adv_caption"))
        st.markdown(f"**{t(lang, 'adv_stack')}**")
        die = st.selectbox(t(lang, "die"), list(DIES.keys()), index=0)
        temp = st.slider(t(lang, "temp"), 25, 800, int(spec["default_temp_c"]), 5)
        area_cm2 = st.number_input(t(lang, "area"), min_value=0.01, max_value=100.0, value=1.0, step=0.1)
        power_w = st.number_input(t(lang, "power"), min_value=1.0, max_value=500.0, value=50.0, step=1.0)
        t_sink_c = st.number_input(t(lang, "sink"), min_value=0.0, max_value=120.0, value=45.0, step=1.0)
        st.divider()
        st.markdown(f"**{t(lang, 'tim_h')}**", help=t(lang, "h_tim"))
        st.caption(t(lang, "tim_caption"))
        tim_kappa = st.number_input(t(lang, "tim_kappa"), min_value=0.5, max_value=50.0, value=float(DEFAULT_TIM_KAPPA), step=0.5, help=t(lang, "h_kappa"))
        tim_um = st.number_input(t(lang, "tim_um"), min_value=1.0, max_value=500.0, value=float(DEFAULT_TIM_UM), step=5.0, help=t(lang, "h_tim"))
        share_pct = st.slider(t(lang, "share_max"), 2, 50, int(round(DEFAULT_SHARE_MAX * 100)), 1)
        st.divider()
        if cooling:
            st.markdown(f"**{t(lang, 'weights_h')}**")
            wn = st.slider(t(lang, "w_nos"), 0, 100, int(RELIABILITY_WEIGHTS["nos"] * 100), 5)
            wm = st.slider(t(lang, "w_manuf"), 0, 100, int(RELIABILITY_WEIGHTS["manuf"] * 100), 5)
            wi = st.slider(t(lang, "w_iface"), 0, 100, int(RELIABILITY_WEIGHTS["interface"] * 100), 5, help=t(lang, "h_cte"))
            weights = normalize_weights({"nos": wn, "manuf": wm, "interface": wi})
            st.caption(" / ".join(f"{k} {v:.0%}" for k, v in weights.items()))
        else:
            w_nos = st.slider("NOS", 0.30, 0.80, 0.55, 0.05)
        st.divider()
        st.markdown(f"**{t(lang, 'adv_data')}**")
        std_key = st.selectbox(t(lang, "standard"), list(STANDARDS.keys()), index=0 if cooling else 3, format_func=lambda k: ui.standard(lang, k)["label"])
        source = st.radio(t(lang, "source"), [t(lang, "demo"), t(lang, "live")], index=0 if not has_key else 1)
        exact = st.toggle(t(lang, "exact"), value=True)
        max_results = st.slider(t(lang, "max_api"), 20, 200, 80, 10)
    live = source == t(lang, "live") and has_key
    # The demo runs by itself; the button is only needed to query Materials Project.
    run = sb.button(t(lang, "run"), type="primary", width="stretch") if live else False
    cleaned = [e.strip() for e in sys_key.split(",") if e.strip()]
    return {"elements": cleaned, "exact": exact, "process": PROCESS_OPTIONS[process_label], "process_label": process_label, "temp": temp, "w_nos": w_nos, "weights": weights, "cooling": cooling, "application": app_key, "substrate": substrate, "die": die, "thickness_um": thickness_um, "area_cm2": area_cm2, "power_w": power_w, "t_sink_c": t_sink_c, "budget": 0.05, "tim_kappa": tim_kappa, "tim_um": tim_um, "share_max": share_pct / 100.0, "live": live, "mp_key": mp_key, "max_results": max_results, "run": run, "standard": std_key, "lang": lang, "site": site_key}

@st.cache_data(ttl=3600, show_spinner=False)
def _cached_live(elements, exact, max_results, _api_key):
    # One Materials Project query per (system, exact, max) per hour; the key is not hashed.
    return run_live(list(elements), api_key=_api_key, max_results=max_results, exact_chemsys=exact)

# Downloads are built once per (language, setup, results) instead of on every click.
@st.cache_data(show_spinner=False, max_entries=64)
def _report_pdf(lang, cfg, rows, mode):
    return build_pdf(lang, cfg, rows, mode)

@st.cache_data(show_spinner=False, max_entries=32)
def _report_zip(cfg, rows, mode):
    return build_zip_all_langs(cfg, rows, mode)

@st.cache_data(show_spinner=False, max_entries=64)
def _coupon_pdf(cfg, rows, contact):
    return build_coupon_pdf(cfg, rows, phase=pick_phase(rows), contact=contact)

def _pdf_cfg(cfg):
    return {k: v for k, v in cfg.items() if k not in ("run", "mp_key")}

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
        c.metric(t(lang,"kappa_ok"), sum(1 for r in rows if r.get("relevance_verdict") == "kappa_not_limiting"), help=t(lang, "h_kappa"))
        d.metric(t(lang,"coupon"), sum(1 for r in rows if r.get("verdict") == "proceed_to_coupon"), help=t(lang, "h_coupon"))
    else:
        c.metric("risk", sum(1 for r in rows if r["manuf_risk"] in ("low","medium")))
        d.metric(t(lang,"source"), "Demo" if mode.startswith("demo") else "MP")

def stability_line(rows, lang):
    viable = [r for r in rows if r.get("verdict") != "process_veto"]
    stab = rank_stability(viable)
    if not stab: return None
    top = stab[0]
    return f"**{t(lang,'stability')}:** " + t(lang, "stability_line").format(f=top["formula"], p=top["share_first"], n=top["of"])

def coupon_button(cfg, rows, lang, key):
    if not pick_phase(rows):
        st.caption(verdict_text(lang, "process_veto")); return
    phase = pick_phase(rows)
    st.download_button(t(lang, "coupon_pdf"), data=_coupon_pdf(_pdf_cfg(cfg), rows, f"Wilmer Espinoza - {_contact()}"),
                       file_name=f"nos_coupon_{phase.get('formula','phase')}.pdf", mime="application/pdf",
                       on_click="ignore", key=key, help=t(lang, "h_coupon"), width="stretch")

def recommendation_card(rows, cfg, lang, mode):
    phase = pick_phase(rows)
    with st.container(border=True, key="rec_card"):
        st.caption(t(lang, "rec_h").upper())
        if not phase:
            st.warning(t(lang, "rec_none"))
        else:
            left, right = st.columns([3, 2], gap="large")
            with left:
                st.markdown(f"## {phase['formula']}")
                code = phase.get("verdict") or "coupon_cte_unknown"
                st.badge(verdict_label(lang, code), color=VERDICT_COLOR.get(code, "orange"))
                st.markdown(verdict_text(lang, code))
                reasons = []
                if phase.get("dt_coat") is not None:
                    reasons.append(t(lang, "rec_dt").format(dc=phase["dt_coat"], dt=phase["dt_tim"]))
                else:
                    reasons.append(t(lang, "rec_dt_none").format(dt=phase["dt_tim"]))
                if phase.get("dcte_max") is not None:
                    reasons.append(t(lang, "rec_dcte").format(d=phase["dcte_max"], n=ui.neighbor(lang, phase.get("worst_neighbor"))))
                else:
                    reasons.append(t(lang, "rec_dcte_none"))
                n_flags = len(phase.get("flags") or [])
                reasons.append(t(lang, "rec_flags").format(n=n_flags) if n_flags else t(lang, "rec_flags_none"))
                st.markdown("\n".join(f"- {r}" for r in reasons))
            with right:
                coupon_button(cfg, rows, lang, key="dl_coupon_card")
                with st.popover(t(lang, "request_btn"), width="stretch"):
                    request_panel(rows, cfg, lang)
                with st.popover(t(lang, "eval_btn"), width="stretch", key="eval_pop"):
                    eval_panel(rows, cfg, lang, key="eval_pop", short=True)
        if cfg["cooling"]:
            line = stability_line(rows, lang)
            if line: st.info(line)
        src = "Demo" if mode.startswith("demo") else "Materials Project"
        st.caption(t(lang, "rec_context").format(n=len(rows), app=ui.app_label(lang, cfg["application"]), sub=cfg["substrate"],
                                                   site=site_spec(cfg.get("site"), lang)["label"], src=src))
    metrics(rows, mode, cfg["cooling"], lang)

def scatter(rows, cooling, lang):
    fig = go.Figure()
    xkey = "interface_score" if cooling else "NOS"
    for tier, color in TIER_COLORS.items():
        chunk = [r for r in rows if r["tier"] == tier]
        if not chunk: continue
        fig.add_trace(go.Scatter(x=[r[xkey] for r in chunk], y=[r["manuf_score"] for r in chunk], mode="markers", name=ui.tier_label(lang, tier), marker=dict(size=[16 if r["pareto"] else 11 for r in chunk], color=color, symbol=["diamond" if r["pareto"] else "circle" for r in chunk]), text=[f"{r['formula']} · {verdict_label(lang, r.get('verdict'))}" for r in chunk], hoverinfo="text"))
    fig.update_layout(height=400, xaxis=dict(range=[0,1], title=t(lang,"ax_x") if cooling else "NOS"), yaxis=dict(range=[0,1], title=t(lang, "ax_y")), template="plotly_white", margin=dict(t=20))
    st.caption(t(lang, "chart_caption") if cooling else t(lang, "chart_caption_generic"))
    st.plotly_chart(fig, width="stretch")

def tim_panel(cfg, lang):
    st.subheader(t(lang, "tim_title"))
    st.caption(site_note(cfg.get("site") or DEFAULT_SITE, lang))
    st.dataframe(pd.DataFrame(tim_ref(lang)), width="stretch", hide_index=True,
                 column_config={"name": st.column_config.TextColumn(t(lang, "tim_col_name")),
                                "kappa": st.column_config.TextColumn("κ (W/m·K)", help=t(lang, "h_kappa")),
                                "form": st.column_config.TextColumn(t(lang, "tim_col_form")),
                                "note": st.column_config.TextColumn(t(lang, "tim_col_note"))})

def _num(v, spec):
    return None if v is None else float(format(v, spec))

def _csv_frame(rows, lang):
    # Same columns, headers and verdict codes as before v0.5: this is what the CSV exports.
    return pd.DataFrame([{
        "Rank": r["rank"], "Formula": r["formula"], "Score": r["combined"], "NOS": r["NOS"], "Manuf": r["manuf_score"],
        t(lang,"col_iface"): r.get("interface_score"), t(lang,"col_dcte"): r.get("dcte_max"),
        t(lang,"col_verdict"): r.get("verdict"), "k bulk": r.get("kappa_wm_k"), t(lang,"col_kneed"): r.get("kappa_needed"),
        t(lang,"col_dtc"): _num(r.get("dt_coat"), ".2f"), t(lang,"col_dtt"): _num(r.get("dt_tim"), ".2f"),
        t(lang,"col_flags"): len(r.get("flags") or []),
    } for r in rows])

def _colcfg(lang):
    C = st.column_config.Column
    return {
        t(lang, "d_rank"): C(width="small"),
        t(lang, "d_score"): C(help=t(lang, "h_score")),
        t(lang, "d_iface"): C(help=t(lang, "h_cte")),
        t(lang, "d_dcte"): C(help=t(lang, "h_cte")),
        t(lang, "d_kbulk"): C(help=t(lang, "h_kappa")),
        t(lang, "d_kneed"): C(help=t(lang, "h_kappa")),
        t(lang, "d_dtc"): C(help=t(lang, "h_dtc")),
        t(lang, "d_dtt"): C(help=t(lang, "h_dtt")),
        t(lang, "d_flags"): C(help=t(lang, "h_flags")),
    }

def table(rows, cooling, lang, cfg, mode):
    short = pd.DataFrame([{
        t(lang, "d_rank"): r["rank"], t(lang, "d_phase"): r["formula"],
        t(lang, "d_verdict"): verdict_label(lang, r.get("verdict"), dot=True),
        t(lang, "d_dcte"): r.get("dcte_max"), t(lang, "d_dtc"): _num(r.get("dt_coat"), ".2f"), t(lang, "d_dtt"): _num(r.get("dt_tim"), ".2f"),
    } for r in rows])
    show_df(short, lang, {k: v for k, v in _ranking_fmt(lang).items() if k in short.columns}, column_config=_colcfg(lang))
    with st.expander(t(lang, "full_table")):
        full = pd.DataFrame([{
            t(lang, "d_rank"): r["rank"], t(lang, "d_phase"): r["formula"], t(lang, "d_score"): r["combined"], "NOS": r["NOS"],
            t(lang, "d_manuf"): r["manuf_score"], t(lang, "d_iface"): r.get("interface_score"), t(lang, "d_dcte"): r.get("dcte_max"),
            t(lang, "d_verdict"): verdict_label(lang, r.get("verdict"), dot=True), t(lang, "d_kbulk"): r.get("kappa_wm_k"),
            t(lang, "d_kneed"): r.get("kappa_needed"), t(lang, "d_dtc"): _num(r.get("dt_coat"), ".2f"),
            t(lang, "d_dtt"): _num(r.get("dt_tim"), ".2f"), t(lang, "d_flags"): len(r.get("flags") or []),
        } for r in rows])
        show_df(full, lang, _ranking_fmt(lang), column_config=_colcfg(lang))
    buf = io.StringIO(); _csv_frame(rows, lang).to_csv(buf, index=False)
    st.markdown(f"**{t(lang, 'downloads')}**")
    c1,c2,c3,c4 = st.columns(4)
    pcfg = _pdf_cfg(cfg)
    with c1: st.download_button(t(lang,"csv"), data=buf.getvalue(), file_name=f"nos_ranking_{lang}.csv", mime="text/csv", on_click="ignore", width="stretch")
    with c2: st.download_button(t(lang,"pdf"), data=_report_pdf(lang, pcfg, rows, mode), file_name=f"nos_report_{lang}.pdf", mime="application/pdf", on_click="ignore", width="stretch")
    with c3: st.download_button(t(lang,"pdf_all"), data=_report_zip(pcfg, rows, mode), file_name="nos_reports_es_en_fr_de.zip", mime="application/zip", on_click="ignore", width="stretch")
    with c4: coupon_button(cfg, rows, lang, key="dl_coupon_row")

def email_options(lang, label, subject, body, primary=False, short=False, key=None):
    """A mailto: link alone opens a blank tab when the browser has no mail app (e.g. Gmail
    users on the web), so offer webmail compose links and the text to copy as well.
    key: prefix for widget keys when the same block appears twice on a page."""
    k = (lambda s: f"{key}_{s}") if key else (lambda s: None)
    to, su, bo = quote(_contact()), quote(subject), quote(body)
    gmail = f"https://mail.google.com/mail/?view=cm&fs=1&to={to}&su={su}&body={bo}"
    outlook = f"https://outlook.live.com/mail/0/deeplink/compose?to={to}&subject={su}&body={bo}"
    mailto = f"mailto:{_contact()}?subject={su}&body={bo}"
    # In the narrow popover the three buttons go one under the other.
    c1, c2, c3 = (st.container(), st.container(), st.container()) if short else st.columns(3)
    g_label, o_label = (t(lang, "open_gmail"), t(lang, "open_outlook")) if short else (f"{label} · Gmail", f"{label} · Outlook")
    with c1: st.link_button(g_label, gmail, type="primary" if primary else "secondary", width="stretch", key=k("gmail"))
    with c2: st.link_button(o_label, outlook, width="stretch", key=k("outlook"))
    with c3: st.link_button(t(lang, "email_app"), mailto, width="stretch", key=k("mailto"))
    with st.expander(t(lang, "email_copy"), key=k("copy")):
        st.markdown(f"{t(lang, 'email_to')}: **{_contact()}**")
        st.code(subject, language=None)
        st.code(body, language=None)

def request_panel(rows, cfg, lang):
    st.markdown(f"**{t(lang, 'request_h')}**")
    phase = pick_phase(rows) or {}
    site_en = site_spec(cfg.get("site"), "en")["label"]
    subject = f"NOS study request - {phase.get('formula', '')} - {site_en}"
    body = "\n".join([
        "Hi Wilmer,", "",
        "I ran the NOS Screening Workbench and would like a study / coupon for my case.", "",
        *feedback.setup_lines(cfg, phase), "",
        "My real stack / what fails today:", "",
        "Company / role (optional):", "",
    ])
    email_options(lang, t(lang, "request_btn"), subject, body, primary=True, short=True)
    st.caption(t(lang, "request_caption"))

def eval_panel(rows, cfg, lang, key, short):
    """'Rate this tool': a Google Form when NOS_EVAL_FORM_URL is an https:// link, else e-mail.
    Nothing is stored by the app."""
    st.markdown(f"**{t(lang, 'eval_h')}**")
    st.markdown(t(lang, "eval_intro"))
    phase = pick_phase(rows) if rows else None
    lines = feedback.setup_lines(cfg, phase)
    url = feedback.form_url(_secret("NOS_EVAL_FORM_URL"))
    if url:
        st.link_button(t(lang, "eval_open_form"), url, type="primary", key=f"{key}_form")
        st.markdown(t(lang, "eval_setup"))
        st.code("\n".join(lines), language=None)
        st.caption(t(lang, "eval_caption_form"))
    else:
        site_en = site_spec(cfg.get("site"), "en")["label"]
        subject = feedback.eval_subject((phase or {}).get("formula", ""), site_en)
        email_options(lang, t(lang, "eval_btn"), subject, feedback.eval_body(lines), primary=True, short=short, key=key)
        st.caption(t(lang, "eval_caption_email"))

def detail(rows, lang):
    labels = [f"{r['rank']:02d} · {r['formula']} ({r['combined']:.3f})" for r in rows[:40]]
    if not labels: return
    choice = st.selectbox(t(lang,"fiche"), labels); row = rows[labels.index(choice)]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric(t(lang,"d_iface"), f"{row['interface_score']:.3f}", None if row.get("dcte_max") is None else f"ΔCTE {row['dcte_max']:.1f} ppm/K", delta_color="off", help=t(lang, "h_cte"))
    c2.metric(t(lang, "d_manuf"), f"{row['manuf_score']:.3f}")
    c3.metric("κ bulk / " + t(lang,"d_kneed").split(" (")[0], ("—" if row.get("kappa_wm_k") is None else f"{row['kappa_wm_k']:.1f}") + f" / {row['kappa_needed']:.1f}", help=t(lang, "h_kappa"))
    c4.metric(t(lang, "d_score"), f"{row['combined']:.3f}", help=t(lang, "h_score"))
    verdict = row.get("verdict") or "coupon_cte_unknown"
    st.badge(verdict_label(lang, verdict), color=VERDICT_COLOR.get(verdict, "orange"))
    st.markdown(verdict_text(lang, verdict))
    st.caption(t(lang, "code_caption").format(c=verdict))
    with st.expander(t(lang, "notes_h"), expanded=True):
        for line in (row.get("interface_notes") or []) + (row.get("relevance_notes") or []) + (row.get("flag_notes") or []) + (row.get("manuf_notes") or []):
            st.markdown(f"- {ui.note(lang, line)}")
        if row.get("thermal_citation"):
            st.caption(row["thermal_citation"])

def standards_panel(std_key, lang):
    spec = ui.standard(lang, std_key)
    st.subheader(t(lang,"tests_h"))
    st.caption(f"{spec['label']} · {spec['blurb']}")
    df = pd.DataFrame(spec["tests"], columns=[t(lang, "code"), t(lang, "test"), t(lang, "hits"), t(lang, "fail")])
    st.dataframe(df, width="stretch", hide_index=True)
    st.info(spec["next_step"])

def context_panel(cfg, lang, expanded=False):
    with st.expander(t(lang, "context_h"), expanded=expanded):
        tim_panel(cfg, lang)
        standards_panel(cfg["standard"], lang)

def _opt(label, lang, **kw):
    return st.number_input(label, value=None, placeholder=t(lang, "f_optional"), **kw)

def _choice(lang, field):
    return lambda code: t(lang, f"c_{field}_{code}")

def _log_table(log, lang):
    """Readable view of the log. The CSV keeps the codes; this is display only."""
    rows = []
    for r in log:
        rows.append({
            t(lang, "f_coupon_id"): r["coupon_id"],
            t(lang, "f_coating"): r["coating"],
            t(lang, "f_stage"): t(lang, f"c_stage_{r['stage']}"),
            t(lang, "f_thickness"): r.get("thickness_um"),
            t(lang, "f_porosity"): r.get("porosity_pct"),
            t(lang, "f_tape"): t(lang, f"c_tape_test_{r['tape_test']}"),
            t(lang, "f_spall"): t(lang, f"c_spallation_{r['spallation']}"),
            t(lang, "f_crack"): t(lang, f"c_crack_origin_{r['crack_origin']}"),
            t(lang, "f_cycles"): r.get("cycles"),
            t(lang, "f_shop"): r.get("shop"),
            t(lang, "col_result"): t(lang, "os_" + rlog.outcome(r)),
        })
    return pd.DataFrame(rows)

def _summary_table(log, lang):
    rows = []
    for s in rlog.summarize(log):
        row = {t(lang, "f_coating"): s["coating"], t(lang, "col_coupons"): s["coupons"],
               t(lang, "col_max_stage"): t(lang, f"c_stage_{s['max_stage']}")}
        for o in rlog.OUTCOMES:
            row[t(lang, "os_" + o)] = s[o]
        rows.append(row)
    return pd.DataFrame(rows)

def _next_coupon_id(log):
    ids = {r["coupon_id"] for r in log}
    n = len(ids) + 1
    while f"C-{n:02d}" in ids:
        n += 1
    return f"C-{n:02d}"

def results_panel(cfg, lang, top_phase):
    st.subheader(t(lang, "log_h"))
    st.caption(t(lang, "log_caption"), help=t(lang, "h_coupon"))
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
            process = st.selectbox(t(lang, "f_process"), list(PROCESS_OPTIONS.keys()) + ["Arc / flame wire spray", "Other"], format_func=lambda k: ui.process_label(lang, k),
                                   index=list(PROCESS_OPTIONS.keys()).index(cfg.get("process_label")) if cfg.get("process_label") in PROCESS_OPTIONS else 0)
            shop = st.text_input(t(lang, "f_shop"))
            subs = list(SUBSTRATES.keys())
            substrate = st.selectbox(t(lang, "f_substrate"), subs, index=subs.index(cfg["substrate"]) if cfg.get("substrate") in subs else 0)
            target = st.number_input(t(lang, "f_target"), min_value=0.0, max_value=5000.0, value=float(cfg.get("thickness_um") or 20.0), step=5.0)
        with c2:
            stage = st.radio(t(lang, "f_stage"), list(rlog.STAGES), horizontal=True, format_func=_choice(lang, "stage"))
            tape = st.selectbox(t(lang, "f_tape"), list(rlog.TAPE), format_func=_choice(lang, "tape_test"))
            spall = st.selectbox(t(lang, "f_spall"), list(rlog.SPALLATION), format_func=_choice(lang, "spallation"))
            crack = st.selectbox(t(lang, "f_crack"), list(rlog.CRACK_ORIGIN), format_func=_choice(lang, "crack_origin"))
            cycles = _opt(t(lang, "f_cycles"), lang, min_value=0, step=1)
            peak = _opt(t(lang, "f_peak"), lang, min_value=-60.0, max_value=1500.0, step=5.0)
        with c3:
            thick = _opt(t(lang, "f_thickness"), lang, min_value=0.0, max_value=5000.0, step=1.0)
            poro = _opt(t(lang, "f_porosity"), lang, min_value=0.0, max_value=100.0, step=0.5)
            imc = _opt(t(lang, "f_imc"), lang, min_value=0.0, max_value=5000.0, step=0.5)
            rc = _opt(t(lang, "f_rc"), lang, min_value=0.0, step=0.01)
            notes = st.text_area(t(lang, "f_notes"), height=90)
        st.caption(t(lang, "f_optional_note"))
        share = st.checkbox(t(lang, "f_share"), value=False)
        submitted = st.form_submit_button(t(lang, "log_add"), type="primary")

    if submitted:
        rec = rlog.new_record(coupon_id=coupon_id, coating=coating, process=process, shop=shop, substrate=substrate,
                              target_thickness_um=target, stage=stage, thickness_um=thick, porosity_pct=poro,
                              tape_test=tape, spallation=spall, crack_origin=crack, cycles=cycles, peak_temp_c=peak,
                              imc_thickness_um=imc, contact_resistance_mohm=rc, notes=notes, share_anonymized=share)
        new_log, errors = rlog.add(log, rec)
        if errors:
            labels = {"coupon_id": "f_coupon_id", "coating": "f_coating", "stage": "f_stage", "tape_test": "f_tape",
                      "spallation": "f_spall", "crack_origin": "f_crack", "target_thickness_um": "f_target",
                      "thickness_um": "f_thickness", "porosity_pct": "f_porosity", "cycles": "f_cycles",
                      "peak_temp_c": "f_peak", "imc_thickness_um": "f_imc", "contact_resistance_mohm": "f_rc"}
            msgs = [rlog.render_problem(f, c, p, template=t(lang, "e_" + c), label=t(lang, labels.get(f, f)))
                    for f, c, p in rlog.problems(rec)]
            st.error("\n".join(f"- {m}" for m in msgs))
        else:
            st.session_state["coupon_log"] = new_log
            st.session_state["log_id_stale"] = True
            st.session_state["log_flash"] = t(lang, "log_added").format(id=coupon_id, stage=stage, outcome=t(lang, "os_" + rlog.outcome(new_log[-1])))
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
    show_df(_log_table(log, lang), lang, {t(lang, k): "{:g}" for k in ("f_thickness", "f_porosity", "f_cycles")})
    last = log[-1]
    stage_label = t(lang, "c_stage_" + str(last["stage"]))
    st.info(f"{last['coupon_id']} · {stage_label}: {t(lang, 'o_' + rlog.outcome(last))}")
    st.markdown(f"**{t(lang, 'log_summary_h')}**")
    st.dataframe(_summary_table(log, lang), width="stretch", hide_index=True)
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
    if cfg["live"] and not st.session_state.get("live_ran"):
        st.info(t(lang, "live_hint")); context_panel(cfg, lang, expanded=True); return None
    rows, mode = screen(cfg)
    if rows is None:
        context_panel(cfg, lang, expanded=True); return None
    recommendation_card(rows, cfg, lang, mode)
    st.subheader(t(lang, "summary_h")); table(rows, cfg["cooling"], lang, cfg, mode)
    st.subheader(t(lang, "chart_h")); scatter(rows, cfg["cooling"], lang)
    st.subheader(t(lang, "detail_h")); detail(rows, lang)
    context_panel(cfg, lang)
    return rows

def main():
    cfg = sidebar(); lang = cfg.get("lang","es"); header(lang)
    if cfg["run"]:
        # Materials Project results stay on screen and follow every later sidebar change.
        st.session_state["live_ran"] = True
    tab_screen, tab_log = st.tabs([t(lang, "tab_screen"), t(lang, "tab_log")])
    with tab_screen:
        rows = screening_view(cfg, lang)
        with st.container(border=True, key="eval_box"):
            eval_panel(rows, cfg, lang, key="eval_box", short=False)
    with tab_log:
        results_panel(cfg, lang, pick_phase(rows) if rows else None)
    st.caption(t(lang,"disclaimer") + "  ·  (c) 2026 Wilmer Gaspar Espinoza Castillo")

if __name__ == "__main__":
    main()
