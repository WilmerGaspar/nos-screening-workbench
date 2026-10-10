"""v0.6 tests: evaluation request (feedback.py) and the study-request e-mail it shares lines with."""
import os
import sys
import warnings
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import feedback
from coupon_pdf import pick_phase
from nos_score import run_demo
from pipeline import DEFAULTS, evaluate_candidates
from stack_sites import SITES, site_spec
from thermal import APPLICATIONS


def _old_request_body(cfg, phase):
    """The study-request body exactly as request_panel built it before feedback.py (main 450e1e6)."""
    phase = phase or {}
    site_en = site_spec(cfg.get("site"), "en")["label"]
    return "\n".join([
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


def _new_request_body(cfg, phase):
    """The same body built the way request_panel builds it now (setup_lines in the middle)."""
    return "\n".join([
        "Hi Wilmer,", "",
        "I ran the NOS Screening Workbench and would like a study / coupon for my case.", "",
        *feedback.setup_lines(cfg, phase), "",
        "My real stack / what fails today:", "",
        "Company / role (optional):", "",
    ])


def _demo_cfg(**extra):
    # Same values as the app sidebar defaults (si_power_module, cold plate, PVD, 20 um, Cu, 150 C, TIM 50 um @ 4 W/mK).
    return {**DEFAULTS, "application": "si_power_module", "site": "cold_plate", "process_label": "PVD (sputter / arc)",
            "thickness_um": 20, "substrate": "Cu", "temp": 150, "tim_um": 50.0, "tim_kappa": 4.0, **extra}


def test_eval_body_has_five_questions_and_setup():
    cfg = _demo_cfg()
    phase = pick_phase(evaluate_candidates(run_demo(["cited7"]), cfg))
    lines = feedback.setup_lines(cfg, phase)
    body = feedback.eval_body(lines)
    expected = "\n".join([
        "Hi Wilmer,",
        "",
        "My evaluation of the NOS Screening Workbench:",
        "",
        "1. My role (company engineer / researcher / coating shop / student / other) and organization (optional):",
        "",
        "2. For my case, is the recommendation technically right? (yes / partly / no) Why?",
        "",
        "3. What is wrong or missing?",
        "",
        "4. Would I use it in my work? For what?",
        "",
        "5. Would I try it on a real case of mine? May you quote this evaluation? (with my name / anonymously / no)",
        "",
        "My setup:",
    ] + lines)
    assert body == expected
    positions = [body.index(f"\n{n}. ") for n in range(1, 6)]
    assert positions == sorted(positions)
    setup = body.split("My setup:\n", 1)[1].split("\n")
    assert setup == lines and len(lines) == 5
    assert "Top phase in my run: NiAl (proceed_to_coupon)" in setup


def test_eval_subject():
    assert feedback.eval_subject("NiAl", "Cold plate / leadframe (Cu)") == "NOS evaluation - NiAl - Cold plate / leadframe (Cu)"


def test_form_url_accepts_only_https():
    assert feedback.form_url("https://forms.gle/x") == "https://forms.gle/x"
    for bad in ("", "http://x", "javascript:alert(1)", None, " https://forms.gle/x", "HTTPS://forms.gle/x", "data:text/html,x"):
        assert feedback.form_url(bad) == "", bad


def test_setup_lines_match_the_old_request_lines():
    phases = [None, {}, {"formula": "NiAl", "verdict": "proceed_to_coupon"}]
    n = 0
    for app in APPLICATIONS:
        for site in SITES:
            for proc in ("PVD (sputter / arc)", "Thermal spray / HVOF", "Electroplating"):
                for phase in phases:
                    cfg = _demo_cfg(application=app, site=site, process_label=proc, thickness_um=60, substrate="316SS",
                                    temp=185, tim_um=100.0, tim_kappa=2.5)
                    assert _new_request_body(cfg, phase) == _old_request_body(cfg, phase), (app, site, proc, phase)
                    n += 1
    assert n == len(APPLICATIONS) * len(SITES) * 3 * len(phases)


def test_request_panel_body_unchanged_in_the_app():
    """Run app.py (Streamlit AppTest) and compare the study-request e-mail with the pre-change body."""
    warnings.filterwarnings("ignore")
    from streamlit.testing.v1 import AppTest
    os.environ.pop("NOS_EVAL_FORM_URL", None)
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    cfg = _demo_cfg()
    phase = pick_phase(evaluate_candidates(run_demo(["cited7"]), cfg))
    old = _old_request_body(cfg, phase)
    shown = [c.value for c in at.code if c.value.startswith("Hi Wilmer,\n\nI ran")]
    assert len(shown) == 1, len(shown)
    assert shown[0] == old.rstrip("\n")  # st.code drops the trailing newline when it is displayed
    # The Gmail link carries the full body; it must be byte-identical to the old one.
    urls = [e.proto.url for e in at.get("link_button") if e.proto.url.startswith("https://mail.google.com/")]
    request_urls = [u for u in urls if parse_qs(urlparse(u).query)["su"][0].startswith("NOS study request - ")]
    assert len(request_urls) == 1, urls
    q = parse_qs(urlparse(request_urls[0]).query, keep_blank_values=True)
    assert q["body"][0] == old
    assert q["su"][0] == "NOS study request - NiAl - Cold plate / leadframe (Cu)"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"ok  {fn.__name__}")
    print("all tests passed")
