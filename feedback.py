"""Evaluation request ("Rate this tool") and the setup lines shared with the study request.

Pure Python: no Streamlit. The app shows these texts; nothing is stored or sent by the app.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from stack_sites import site_spec
from thermal import APPLICATIONS


# Last setup line for a reference system (Al,Cu is the only one): it replaces "Top phase in my run".
REFERENCE_LINE = "Reference system: Al/Cu joint phases; lowest kappa: {phase} ({k} W/mK)"


def lowest_kappa(rows) -> Optional[Tuple[str, str]]:
    """(formula, kappa as shown, e.g. "25.9") of the row with the lowest measured kappa, or None."""
    with_k = [r for r in rows or [] if r.get("kappa_wm_k") is not None]
    if not with_k:
        return None
    low = min(with_k, key=lambda r: r["kappa_wm_k"])
    return low["formula"], f"{low['kappa_wm_k']:.1f}"


def setup_lines(cfg: Dict, phase: Optional[Dict], reference: Optional[Tuple[str, str]] = None) -> List[str]:
    """The setup lines of the study-request e-mail (same text as before this module existed).
    reference: (phase, kappa) for a reference system; it replaces the top-phase line."""
    phase = phase or {}
    site_en = site_spec(cfg.get("site"), "en")["label"]
    if reference:
        last = REFERENCE_LINE.format(phase=reference[0], k=reference[1])
    else:
        last = f"Top phase in my run: {phase.get('formula', '-')} ({phase.get('verdict', '-')})"
    return [
        f"Application: {APPLICATIONS[cfg['application']]['label']}",
        f"Layer site: {site_en}",
        f"Process: {cfg.get('process_label')} - {cfg.get('thickness_um')} um on {cfg.get('substrate')}",
        f"Service T: {cfg.get('temp')} C - TIM: {cfg.get('tim_um')} um at {cfg.get('tim_kappa')} W/mK",
        last,
    ]


def form_url(raw) -> str:
    """Only an https:// address is used as the form link; anything else (empty, http://,
    javascript:, ...) gives "" so the app falls back to e-mail. Surrounding spaces (easy to
    paste into Secrets by accident) are removed first."""
    raw = raw.strip() if isinstance(raw, str) else raw
    if isinstance(raw, str) and raw.startswith("https://"):
        return raw
    return ""


# Subject for a reference system (Al,Cu is the only one): no top phase in it.
REFERENCE_SUBJECT = "NOS evaluation - Al-Cu reference - {site_en}"


def eval_subject(formula, site_en, reference: bool = False) -> str:
    if reference:
        return REFERENCE_SUBJECT.format(site_en=site_en)
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
