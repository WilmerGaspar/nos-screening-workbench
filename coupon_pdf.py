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
from stack_sites import SITES, TIM_REF, site_note
from standards import STANDARDS
_DEJAVU = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
_FONT, _FONT_B = "Helvetica", "Helvetica-Bold"
def _fonts():
    global _FONT, _FONT_B
    if _DEJAVU.exists():
        pdfmetrics.registerFont(TTFont("DejaVuC", str(_DEJAVU))); _FONT=_FONT_B="DejaVuC"
def _st():
    base = getSampleStyleSheet()
    return {"h": ParagraphStyle("ch", parent=base["Heading1"], fontName=_FONT_B, fontSize=13, spaceAfter=4), "h2": ParagraphStyle("ch2", parent=base["Heading2"], fontName=_FONT_B, fontSize=10, spaceBefore=6, spaceAfter=3), "b": ParagraphStyle("cb", parent=base["BodyText"], fontName=_FONT, fontSize=9, leading=12), "s": ParagraphStyle("cs", parent=base["BodyText"], fontName=_FONT, fontSize=8, leading=10, textColor=colors.HexColor("#333333"))}
def pick_phase(rows):
    if not rows: return None
    for r in rows:
        if r.get("thermal_verdict")=="proceed_to_coupon": return r
    for r in rows:
        if r.get("kappa_wm_k") is not None: return r
    return rows[0]
def build_coupon_pdf(cfg, rows, phase=None):
    _fonts(); styles=_st(); row = phase or pick_phase(rows); buf=io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm, title="NOS coupon spec")
    story=[]
    story.append(Paragraph("NOS coupon spec — one page", styles["h"]))
    story.append(Paragraph("Pre-filter only. Published bulk kappa is not module Rth. Do not claim AQG 324 / IEC compliance.", styles["s"]))
    story.append(Paragraph(date.today().isoformat(), styles["s"]))
    site_key = cfg.get("site") or "cold_plate"; site = SITES.get(site_key) or SITES["cold_plate"]
    formula = (row or {}).get("formula","—"); kappa=(row or {}).get("kappa_wm_k"); rcoat=(row or {}).get("r_coat")
    cite = (row or {}).get("citation_line") or (row or {}).get("thermal_citation") or ""
    spec_tbl = [["Phase", str(formula)],["kappa bulk 300 K", "—" if kappa is None else f"{kappa:.1f} W/mK"],["Citation", str(cite)[:180]],["Process", str(cfg.get("process_label",""))],["Substrate", str(cfg.get("substrate",""))],["Thickness", f"{cfg.get('thickness_um')} um"],["R_coat = t/kA", "—" if rcoat is None else f"{rcoat:.4f} K/W"],["Layer site", site["label"]],["Test that hits this site", f"{site['aqg']}  fail {site['fail']}"],["Target standard (info)", STANDARDS.get(cfg.get("standard") or "", {}).get("label","")],["Phase verdict", str((row or {}).get("thermal_verdict",""))]]
    t0=Table(spec_tbl, colWidths=[48*mm,128*mm])
    t0.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),_FONT),("FONTSIZE",(0,0),(-1,-1),8),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#111827")),("TEXTCOLOR",(0,0),(0,-1),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#d1d5db"))]))
    story.append(t0); story.append(Paragraph(site_note(site_key), styles["s"]))
    story.append(Paragraph("This is not a TIM", styles["h2"]))
    tim=[["Class","k W/mK","Form","Note"]]+[ [i["name"],i["kappa"],i["form"],i["note"]] for i in TIM_REF]
    t1=Table(tim, colWidths=[48*mm,28*mm,30*mm,70*mm])
    t1.setStyle(TableStyle([("FONTNAME",(0,0),(-1,0),_FONT_B),("FONTSIZE",(0,0),(-1,-1),8),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f2937")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#d1d5db")),("BACKGROUND",(0,4),(-1,4),colors.HexColor("#ecfdf5"))]))
    story.append(t1)
    story.append(Paragraph("Lab next step", styles["h2"]))
    story.append(Paragraph("Deposit the phase. Measure Rth on the mounted stack (IEC 60747-15). Power-cycle the named interface. This page is the request, not the result.", styles["b"]))
    story.append(Spacer(1,6*mm))
    story.append(Paragraph("c 2026 Wilmer Gaspar Espinoza Castillo · CC BY-NC-SA 4.0", styles["s"]))
    doc.build(story)
    return buf.getvalue()
