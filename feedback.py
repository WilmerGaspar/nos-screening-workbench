"""Evaluation request ("Rate this tool") and the setup lines shared with the study request.

Pure Python: no Streamlit. The app shows these texts; nothing is stored or sent by the app.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from stack_sites import site_spec
from thermal import APPLICATIONS


def setup_lines(cfg: Dict, phase: Optional[Dict]) -> List[str]:
    """The setup lines of the study-request e-mail (same text as before this module existed)."""
    phase = phase or {}
    site_en = site_spec(cfg.get("site"), "en")["label"]
    return [
        f"Application: {APPLICATIONS[cfg['application']]['label']}",
        f"Layer site: {site_en}",
        f"Process: {cfg.get('process_label')} - {cfg.get('thickness_um')} um on {cfg.get('substrate')}",
        f"Service T: {cfg.get('temp')} C - TIM: {cfg.get('tim_um')} um at {cfg.get('tim_kappa')} W/mK",
        f"Top phase in my run: {phase.get('formula', '-')} ({phase.get('verdict', '-')})",
    ]


def form_url(raw) -> str:
    """Only an https:// address is used as the form link; anything else (empty, http://,
    javascript:, ...) gives "" so the app falls back to e-mail. Surrounding spaces (easy to
    paste into Secrets by accident) are removed first."""
    raw = raw.strip() if isinstance(raw, str) else raw
    if isinstance(raw, str) and raw.startswith("https://"):
        return raw
    return ""


def eval_subject(formula, site_en) -> str:
    return f"NOS evaluation - {formula} - {site_en}"


EVAL_QUESTIONS = (
    "1. My role (company engineer / researcher / coating shop / student / other) and organization (optional):",
    "2. For my case, is the recommendation technically right? (yes / partly / no) Why?",
    "3. What is wrong or missing?",
    "4. Would I use it in my work? For what?",
    "5. Would I try it on a real case of mine? May you quote this evaluation? (with my name / anonymously / no)",
)


def eval_body(lines: List[str]) -> str:
    out = ["Hi Wilmer,", "", "My evaluation of the NOS Screening Workbench:", ""]
    for q in EVAL_QUESTIONS:
        out += [q, ""]
    out.append("My setup:")
    out += list(lines)
    return "\n".join(out)
