"""One-page coupon request (v0.3, interface-first).

The page is what a lab or a coating shop receives. It names the phase, says why kappa is
or is not the lever, and lays out a two-stage test whose result decides the next step.
Text is kept ASCII so it renders even without the DejaVu font.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from stack_sites import site_spec

# Sites where the layer also touches the semiconductor die.
DIE_SITES = ("die_attach", "chip_metallization")

_DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
_DEJAVU_B = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
_FONT, _FONT_B = "Helvetica", "Helvetica-Bold"


def _fonts():
    global _FONT, _FONT_B
    if _DEJAVU.exists():
        pdfmetrics.registerFont(TTFont("DejaVuC", str(_DEJAVU)))
        _FONT = "DejaVuC"
        if _DEJAVU_B.exists():
            pdfmetrics.registerFont(TTFont("DejaVuCB", str(_DEJAVU_B)))
            _FONT_B = "DejaVuCB"
        else:
            _FONT_B = "DejaVuC"


def _st():
    base = getSampleStyleSheet()
    return {
        "h": ParagraphStyle("ch", parent=base["Heading1"], fontName=_FONT_B, fontSize=13, spaceAfter=2),
        "h2": ParagraphStyle("ch2", parent=base["Heading2"], fontName=_FONT_B, fontSize=9.5, spaceBefore=5, spaceAfter=2),
        "b": ParagraphStyle("cb", parent=base["BodyText"], fontName=_FONT, fontSize=8, leading=10.2),
        "s": ParagraphStyle("cs", parent=base["BodyText"], fontName=_FONT, fontSize=7, leading=8.8, textColor=colors.HexColor("#374151")),
        "cell": ParagraphStyle("cc", parent=base["BodyText"], fontName=_FONT, fontSize=7.5, leading=9.2),
        "cellb": ParagraphStyle("ccb", parent=base["BodyText"], fontName=_FONT_B, fontSize=7.5, leading=9.2, textColor=colors.white),
    }


def pick_phase(rows):
    """First-ranked phase ready for a coupon; else the best phase without a process veto."""
    if not rows:
        return None
    for r in rows:
        if r.get("verdict") == "proceed_to_coupon":
            return r
    for r in rows:
        if r.get("verdict") != "process_veto":
            return r
    return None


def _fmt(v, spec, dash="-"):
    return dash if v is None else format(v, spec)


def _kv_table(pairs, styles, widths=(46 * mm, 132 * mm)):
    data = [[Paragraph(k, styles["cellb"]), Paragraph(v, styles["cell"])] for k, v in pairs]
    t = Table(data, colWidths=list(widths))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#111827")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def _kappa_line(row, cfg):
    if not row.get("heat_path"):
        return "Layer is not on the main heat path: kappa is not a selection criterion here."
    share = row.get("coat_share")
    need = row.get("kappa_needed")
    pct = f"{float(cfg.get('share_max', 0.10)):.0%}"
    if row.get("kappa_wm_k") is None:
        return (f"No citable bulk kappa. The film needs >= {_fmt(need, '.1f')} W/mK to stay under {pct} "
                f"of the coating+TIM dT. Measure film kappa only if the interface survives stage 2.")
    margin = row.get("film_margin") or 0.0
    return (f"Coating takes {share:.1%} of the coating+TIM dT at bulk kappa. The film needs >= "
            f"{_fmt(need, '.1f')} W/mK to stay under {pct}; it may lose up to {margin:.0%} of its bulk "
            f"kappa before that. Do not spend lab budget on film kappa first.")


def _base_metal_line(site_key, cfg):
    substrate = cfg.get("substrate", "Cu")
    if site_key not in DIE_SITES:
        return f"{substrate} - same as the layer's neighbor at this site"
    die = cfg.get("die") or "Si"
    metal = "Cu (DBC copper)" if site_key == "die_attach" else "Al (bond wire)"
    return (f"Two sides: {metal} and the {die} die. A metal-only coupon does not test the die side: "
            f"add {die} coupons (or real {die} dies) coated the same way.")


def build_coupon_pdf(cfg, rows, phase=None, contact=None):
    _fonts()
    styles = _st()
    row = dict(phase or pick_phase(rows) or {})
    site_key = cfg.get("site") or "cold_plate"
    site = site_spec(site_key, "en")
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=12 * mm, bottomMargin=11 * mm, title="NOS coupon request",
                            author="Wilmer Gaspar Espinoza Castillo")
    story = []
    story.append(Paragraph("NOS coupon request - interface first", styles["h"]))
    story.append(Paragraph(
        f"{date.today().isoformat()} - Pre-filter output (NOS Screening Workbench v0.3). This page is the request, "
        "not the result. No AQG 324 / IEC compliance is claimed.", styles["s"]))
    story.append(Spacer(1, 2 * mm))

    formula = row.get("formula", "-")
    neighbors = ", ".join(f"{n} ({c:.1f} ppm/K)" for n, c in (row.get("neighbors") or []))
    cte = row.get("coat_cte")
    dcte = row.get("dcte_max")
    cte_txt = "no value in catalog - measure on the coupon" if cte is None else (
        f"{cte:.1f} ppm/K (no DOI in repo - verify); max dCTE {dcte:.1f} ppm/K vs {row.get('worst_neighbor')}")
    kappa = row.get("kappa_wm_k")
    kappa_txt = "no citable value" if kappa is None else f"{kappa:.1f} W/mK - {row.get('thermal_citation') or ''}"
    dt_txt = "-" if row.get("dt_coat") is None else (
        f"coating {row['dt_coat']:.2f} K vs TIM {row['dt_tim']:.2f} K at {cfg.get('power_w')} W over "
        f"{cfg.get('area_cm2')} cm2 (TIM {cfg.get('tim_um')} um at {cfg.get('tim_kappa')} W/mK, user assumption)")
    story.append(Paragraph("A. Phase and why", styles["h2"]))
    story.append(_kv_table([
        ("Phase / verdict", f"<b>{formula}</b> - rank {row.get('rank', '-')} - {row.get('verdict', '-')}"),
        ("Process / thickness", f"{cfg.get('process_label', cfg.get('process', ''))} - target {cfg.get('thickness_um')} um"),
        ("Layer site", f"{site['label']} - touches: {neighbors or '-'}"),
        ("Coating CTE", cte_txt),
        ("Bulk kappa (upper bound)", kappa_txt),
        ("Is kappa the lever?", _kappa_line(row, cfg)),
        ("dT split", dt_txt),
        ("Watch in cross-section", "<br/>".join(row.get("flag_notes") or ["-"])),
    ], styles))

    story.append(Paragraph("B. Coupon (fill in)", styles["h2"]))
    story.append(_kv_table([
        ("Base metal", _base_metal_line(site_key, cfg)),
        ("Size / finish", "____ x ____ x ____ mm ; surface prep / Ra: ________"),
        ("Coupons per stage", "stage 0: ____   stage 1: ____   stage 2: ____ (keep 1 uncoated reference)"),
        ("Coupons supplied by", "requester (machined to drawing) / lab - ________"),
    ], styles))

    story.append(Paragraph("C. Test sequence", styles["h2"]))
    service_t = cfg.get("temp")
    seq = [
        ["Stage", "What", "Measure", "Gate to continue"],
        ["0 As deposited", "Section one coupon.", "Thickness, porosity, delamination (cross-section); tape adhesion test.",
         "Dense, adherent layer. If not: fix the process before cycling."],
        ["1 Quick shock (comparative)",
         f"10 cycles: heat to T_peak >= {service_t} C (service T of this setup) on a hot plate or furnace with a "
         "thermocouple - not an open flame, it oxidizes Cu; hold about 1 min; quench in water.",
         "Tape test + cross-section after cycle 10.",
         "No spallation or delamination. Harsher than service: use it to compare phases, not to predict life."],
        ["2 Representative",
         f"Match the module's temperature swing and dwell. Site test: {site['aqg']}.",
         "Cross-section + contact resistance at: as deposited, >= 2 intermediate checkpoints, end.",
         "Where and when the first crack starts."],
    ]
    seq_rows = [[Paragraph(c, styles["cellb"] if i == 0 else styles["cell"]) for c in r] for i, r in enumerate(seq)]
    t = Table(seq_rows, colWidths=[26 * mm, 58 * mm, 50 * mm, 44 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(t)
    story.append(Paragraph("Safety: quenching hot metal in water splashes and makes steam - face shield and heat gloves.", styles["s"]))

    story.append(Paragraph("D. How to read the result", styles["h2"]))
    for line in (
        "Crack or delamination that starts at the coating / base-metal boundary: the interface limits. Change process, surface prep or add a bond layer; kappa is not the lever.",
        "Interdiffusion zone or interface oxide in the section: report its thickness at each checkpoint; growth with cycles is the signal.",
        "Dense, adherent layer that survives stage 2: candidate for module-level Rth (IEC 60747-15) and power cycling on the named site.",
        "Send back: section images, adhesion result and contact resistance per checkpoint. They feed the next screening run.",
    ):
        story.append(Paragraph("- " + line, styles["b"]))

    story.append(Spacer(1, 2.5 * mm))
    who = contact or "Wilmer Espinoza - wilmergasparespinoza@gmail.com"
    story.append(Paragraph(
        f"Contact: {who}. Protocol from published kappa (DOI above), 1-D conduction and practitioner input from "
        "materials engineers (2026-10). c 2026 Wilmer Gaspar Espinoza Castillo - CC BY-NC-SA 4.0.", styles["s"]))
    doc.build(story)
    return buf.getvalue()
