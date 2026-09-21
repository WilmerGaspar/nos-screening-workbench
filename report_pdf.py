from __future__ import annotations
import io, zipfile
from datetime import date
from pathlib import Path
from typing import Dict, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from i18n import t, verdict_text
from standards import STANDARDS

_DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
_DEJAVU_B = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
_FONT, _FONT_B = "Helvetica", "Helvetica-Bold"

def _register_fonts():
    global _FONT, _FONT_B
    if _DEJAVU.exists():
        pdfmetrics.registerFont(TTFont("DejaVu", str(_DEJAVU)))
        _FONT = "DejaVu"
        if _DEJAVU_B.exists():
            pdfmetrics.registerFont(TTFont("DejaVuBold", str(_DEJAVU_B)))
            _FONT_B = "DejaVuBold"
        else:
            _FONT_B = "DejaVu"

def _styles():
    base = getSampleStyleSheet()
    return {
        "h": ParagraphStyle("h", parent=base["Heading1"], fontName=_FONT_B, fontSize=14, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=_FONT_B, fontSize=11, spaceBefore=8, spaceAfter=4),
        "b": ParagraphStyle("b", parent=base["BodyText"], fontName=_FONT, fontSize=9, leading=12),
        "s": ParagraphStyle("s", parent=base["BodyText"], fontName=_FONT, fontSize=8, leading=11, textColor=colors.HexColor("#444444")),
        "cell": ParagraphStyle("cell", parent=base["BodyText"], fontName=_FONT, fontSize=7, leading=9),
    }

def build_pdf(lang, cfg, rows, mode):
    _register_fonts()
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm, title=t(lang,"report_title"), author="Wilmer Gaspar Espinoza Castillo")
    story = []
    story.append(Paragraph(t(lang,"report_title"), styles["h"]))
    story.append(Paragraph(t(lang,"subtitle"), styles["s"]))
    story.append(Paragraph(f"{date.today().isoformat()}  ·  {mode}", styles["s"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(t(lang,"disclaimer"), styles["s"]))
    story.append(Paragraph(t(lang,"report_cfg"), styles["h2"]))
    cfg_rows = [
        [t(lang,"application"), str(cfg.get("application",""))],
        [t(lang,"system"), ", ".join(cfg.get("elements") or [])],
        [t(lang,"process"), str(cfg.get("process_label",""))],
        [t(lang,"substrate"), str(cfg.get("substrate",""))],
        [t(lang,"temp"), f"{cfg.get('temp')} C"],
        [t(lang,"thickness"), f"{cfg.get('thickness_um')} um"],
        [t(lang,"standard"), STANDARDS.get(cfg.get("standard") or "", {}).get("label","")],
    ]
    ct = Table(cfg_rows, colWidths=[55*mm, 120*mm])
    ct.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),_FONT),("FONTSIZE",(0,0),(-1,-1),8),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#f3f4f6")),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#d1d5db"))]))
    story.append(ct)
    story.append(Paragraph(t(lang,"report_rank"), styles["h2"]))
    data = [["Rank", t(lang,"col_formula"), "NOS", "Manuf", t(lang,"col_verdict"), "k", "R_coat"]]
    for r in rows[:20]:
        k = r.get("kappa_wm_k"); rc = r.get("r_coat")
        data.append([str(r.get("rank")), r.get("formula",""), f"{r.get('NOS',0):.3f}", f"{r.get('manuf_score',0):.3f}", Paragraph(verdict_text(lang, r.get("thermal_verdict") or "missing_thermal_data"), styles["cell"]), "-" if k is None else f"{k:.1f}", "-" if rc is None else f"{rc:.4f}"])
    rt = Table(data, colWidths=[12*mm, 22*mm, 16*mm, 16*mm, 70*mm, 18*mm, 22*mm])
    rt.setStyle(TableStyle([("FONTNAME",(0,0),(-1,0),_FONT_B),("FONTSIZE",(0,0),(-1,-1),7),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#111827")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#d1d5db")),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(rt)
    std_key = cfg.get("standard")
    if std_key in STANDARDS:
        spec = STANDARDS[std_key]
        story.append(Paragraph(t(lang,"report_std"), styles["h2"]))
        story.append(Paragraph(spec["label"] + " — " + spec.get("next_step",""), styles["s"]))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("c 2026 Wilmer Gaspar Espinoza Castillo · CC BY-NC-SA 4.0", styles["s"]))
    doc.build(story)
    return buf.getvalue()

def build_zip_all_langs(cfg, rows, mode):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for lang in ("es","en","fr","de"):
            zf.writestr(f"nos_report_{lang}.pdf", build_pdf(lang, cfg, rows, mode))
    return buf.getvalue()
