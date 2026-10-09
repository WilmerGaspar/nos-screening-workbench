"""Coupon results log (v0.4).

One record per coupon per stage of the protocol in coupon_pdf.py:
  stage 0 = as deposited, 1 = quick shock (comparative), 2 = representative cycling.

The reading rules mirror section D of the coupon sheet ("How to read the result"):
a crack or spallation that starts at the coating / base-metal boundary means the
interface limits. No numeric pass/fail thresholds are invented here: porosity,
thickness and IMC thickness are recorded as measured, not judged.

Pure Python: no Streamlit, no I/O besides string (de)serialization. Records live in
the user's session; persistence is the downloaded CSV/JSON.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date
from typing import Dict, List, Optional, Tuple

SCHEMA_VERSION = "nos-coupon-log/1"

STAGES = ("0", "1", "2")
TAPE = ("not_done", "pass", "fail")
SPALLATION = ("none", "edge", "partial", "full")
CRACK_ORIGIN = ("not_checked", "none_seen", "coating_substrate_interface", "within_coating", "substrate")

TEXT_FIELDS = ("coupon_id", "date", "coating", "process", "shop", "substrate", "notes")
CHOICE_FIELDS = {"stage": STAGES, "tape_test": TAPE, "spallation": SPALLATION, "crack_origin": CRACK_ORIGIN}
# name -> (min, max) inclusive; None = open
NUMBER_FIELDS = {
    "target_thickness_um": (0.0, 5000.0),
    "thickness_um": (0.0, 5000.0),
    "porosity_pct": (0.0, 100.0),
    "cycles": (0.0, 1e9),
    "peak_temp_c": (-60.0, 1500.0),
    "imc_thickness_um": (0.0, 5000.0),
    "contact_resistance_mohm": (0.0, 1e9),
}
BOOL_FIELDS = ("share_anonymized",)

FIELDS: Tuple[str, ...] = (
    "coupon_id", "date", "coating", "process", "shop", "substrate", "target_thickness_um",
    "stage", "thickness_um", "porosity_pct", "tape_test", "spallation", "crack_origin",
    "cycles", "peak_temp_c", "imc_thickness_um", "contact_resistance_mohm",
    "notes", "share_anonymized",
)

OUTCOMES = ("interface_limited", "coating_limited", "substrate_issue", "passed_stage", "incomplete")


def new_record(**values) -> Dict:
    rec = {f: None for f in FIELDS}
    rec.update({"date": date.today().isoformat(), "stage": "0", "tape_test": "not_done",
                "spallation": "none", "crack_origin": "not_checked", "share_anonymized": False})
    rec.update({k: v for k, v in values.items() if k in rec})
    return rec


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def problems(rec: Dict) -> List[Tuple[str, str, Tuple]]:
    """Structured problems: (field, code, params). code in required, choice, number, range,
    whole, cycles_needed. validate() renders them in English; the app translates them."""
    out: List[Tuple[str, str, Tuple]] = []
    for f in ("coupon_id", "coating"):
        if _blank(rec.get(f)):
            out.append((f, "required", ()))
    for f, allowed in CHOICE_FIELDS.items():
        if str(rec.get(f)) not in allowed:
            out.append((f, "choice", tuple(allowed)))
    for f, (lo, hi) in NUMBER_FIELDS.items():
        v = rec.get(f)
        if _blank(v):
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            out.append((f, "number", ()))
            continue
        if x < lo or x > hi:
            out.append((f, "range", (lo, hi)))
    if not _blank(rec.get("cycles")):
        try:
            if float(rec["cycles"]) != int(float(rec["cycles"])):
                out.append(("cycles", "whole", ()))
        except (TypeError, ValueError):
            pass
    if str(rec.get("stage")) in ("1", "2") and _blank(rec.get("cycles")):
        out.append(("cycles", "cycles_needed", ()))
    return out


_EN = {
    "required": "{f} is required",
    "choice": "{f} must be one of {p}",
    "number": "{f} must be a number",
    "range": "{f} must be between {lo:g} and {hi:g}",
    "whole": "{f} must be a whole number",
    "cycles_needed": "cycles is required for stage 1 and 2",
}


def render_problem(field: str, code: str, params: Tuple, template: Optional[str] = None, label: Optional[str] = None) -> str:
    tpl = template or _EN[code]
    lo, hi = (params + (None, None))[:2] if code == "range" else (None, None)
    return tpl.format(f=label or field, p=", ".join(map(str, params)), lo=lo or 0.0, hi=hi or 0.0)


def validate(rec: Dict) -> List[str]:
    """Return a list of problems in English; empty list = valid."""
    return [render_problem(f, c, p) for f, c, p in problems(rec)]


def outcome(rec: Dict) -> str:
    """Reading rule of the coupon sheet, section D. No invented thresholds."""
    crack = rec.get("crack_origin")
    spall = rec.get("spallation")
    if crack == "coating_substrate_interface" or spall in ("partial", "full") or rec.get("tape_test") == "fail":
        return "interface_limited"
    if crack == "within_coating":
        return "coating_limited"
    if crack == "substrate":
        return "substrate_issue"
    if rec.get("tape_test") == "pass" and spall in ("none", "edge") and crack == "none_seen":
        return "passed_stage"
    return "incomplete"


def _clean(rec: Dict) -> Dict:
    out = new_record()
    for f in FIELDS:
        v = rec.get(f)
        if f in NUMBER_FIELDS:
            out[f] = None if _blank(v) else float(v)
            if f == "cycles" and out[f] is not None:
                out[f] = int(out[f])
        elif f in BOOL_FIELDS:
            out[f] = str(v).strip().lower() in ("true", "1", "yes", "si", "sí") if isinstance(v, str) else bool(v)
        elif f in CHOICE_FIELDS:
            out[f] = None if _blank(v) else str(v).strip()
        else:
            out[f] = None if _blank(v) else str(v).strip()
    return out


def add(records: List[Dict], rec: Dict) -> Tuple[List[Dict], List[str]]:
    """Validate and append. Same coupon_id + stage replaces the earlier entry."""
    errors = validate(rec)
    if errors:
        return records, errors
    clean = _clean(rec)
    kept = [r for r in records if not (r["coupon_id"] == clean["coupon_id"] and str(r["stage"]) == str(clean["stage"]))]
    return kept + [clean], []


def to_csv(records: List[Dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(FIELDS) + ["outcome"], lineterminator="\n")
    w.writeheader()
    for r in records:
        row = {f: ("" if r.get(f) is None else r.get(f)) for f in FIELDS}
        row["outcome"] = outcome(r)
        w.writerow(row)
    return buf.getvalue()


def to_json(records: List[Dict]) -> str:
    payload = {"schema": SCHEMA_VERSION, "records": [{**r, "outcome": outcome(r)} for r in records]}
    return json.dumps(payload, indent=2, ensure_ascii=False)


def from_csv(text: str) -> Tuple[List[Dict], List[str]]:
    """Load a log written by to_csv. Bad rows are skipped and reported, never guessed."""
    records: List[Dict] = []
    problems: List[str] = []
    reader = csv.DictReader(io.StringIO(text))
    missing = [f for f in ("coupon_id", "coating", "stage") if f not in (reader.fieldnames or [])]
    if missing:
        return [], [f"not a NOS coupon log: missing column(s) {', '.join(missing)}"]
    for i, row in enumerate(reader, start=2):
        records, errs = add(records, {k: row.get(k) for k in FIELDS})
        if errs:
            problems.append(f"row {i}: " + "; ".join(errs))
    return records, problems


def summarize(records: List[Dict]) -> List[Dict]:
    """Per coating: coupons, highest stage reached, outcome counts."""
    groups: Dict[str, Dict] = {}
    for r in records:
        g = groups.setdefault(r["coating"], {"coating": r["coating"], "coupons": set(), "max_stage": "0",
                                             **{o: 0 for o in OUTCOMES}})
        g["coupons"].add(r["coupon_id"])
        g["max_stage"] = max(g["max_stage"], str(r["stage"]))
        g[outcome(r)] += 1
    out = []
    for g in groups.values():
        out.append({**g, "coupons": len(g["coupons"])})
    out.sort(key=lambda d: (-d["passed_stage"], d["interface_limited"], d["coating"]))
    return out


def email_summary(records: List[Dict], limit: int = 25) -> str:
    """Short plain-text lines for a mailto body (URLs have length limits)."""
    lines = []
    for r in records[:limit]:
        bits = [f"{r['coupon_id']}", f"{r['coating']}", f"stage {r['stage']}", outcome(r)]
        if r.get("thickness_um") is not None:
            bits.append(f"t={r['thickness_um']:g} um")
        if r.get("porosity_pct") is not None:
            bits.append(f"porosity={r['porosity_pct']:g}%")
        if r.get("cycles") is not None:
            bits.append(f"cycles={r['cycles']}")
        lines.append(" | ".join(bits))
    if len(records) > limit:
        lines.append(f"... and {len(records) - limit} more (see attached CSV)")
    return "\n".join(lines)
