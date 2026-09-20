#!/usr/bin/env python3
"""Command-line screening for notebooks and CI."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from manufacturability import evaluate
from nos_score import run_demo, run_live
from ranking import COOLING_WEIGHTS, attach_ranks
from die_stack import evaluate_stack
from thermal import evaluate_thermal


def parse_args():
    p = argparse.ArgumentParser(description="NOS screening workbench (CLI)")
    p.add_argument("--elements", default="Fe,Al", help="Comma-separated elements")
    p.add_argument("--process", default="pvd", choices=["pvd", "thermal_spray", "electroplating"])
    p.add_argument("--temp", type=float, default=450.0)
    p.add_argument("--live", action="store_true", help="Query Materials Project")
    p.add_argument("--allow-extra-elements", action="store_true")
    p.add_argument("--application", default="generic_coating",
                   choices=["cpu_cold_plate", "si_power_module", "sic_power_module", "generic_coating"])
    p.add_argument("--substrate", default="Cu")
    p.add_argument("--die", default="Si")
    p.add_argument("--thickness-um", type=float, default=20.0)
    p.add_argument("--area-cm2", type=float, default=1.0)
    p.add_argument("--power-w", type=float, default=50.0)
    p.add_argument("--t-sink", type=float, default=45.0)
    p.add_argument("--out", default="", help="Optional CSV path")
    p.add_argument("--json", default="", help="Optional JSON path")
    return p.parse_args()


def main():
    args = parse_args()
    elements = [e.strip() for e in args.elements.split(",") if e.strip()]
    exact = not args.allow_extra_elements
    if args.live:
        cands = run_live(elements, exact_chemsys=exact)
        source = "materials_project"
    else:
        cands = run_demo(elements, exact_chemsys=exact)
        source = "demo"

    cooling = args.application != "generic_coating"
    rows = []
    for c in cands:
        m = evaluate(c, args.process, args.temp)
        t = evaluate_thermal(c["formula"], args.substrate, args.application)
        s = evaluate_stack(
            c["formula"],
            thickness_um=args.thickness_um,
            area_cm2=args.area_cm2,
            power_w=args.power_w,
            t_sink_c=args.t_sink,
            die=args.die,
            substrate=args.substrate,
        )
        rows.append({
            **c,
            "manuf_score": m.score,
            "manuf_risk": m.risk_level,
            "veto": m.veto,
            "kappa_score": t.score,
            "kappa_wm_k": t.kappa_wm_k,
            "thermal_verdict": t.verdict,
            "r_coat": s.r_coat_k_per_w,
            "dt_coat": s.dt_coat_k,
            "tj_lower_bound": s.tj_lower_bound_c,
            "stack_verdict": s.verdict,
        })
    w_th = COOLING_WEIGHTS["thermal"] if cooling else 0.0
    w_nos = COOLING_WEIGHTS["nos"] if cooling else 0.55
    ranked = attach_ranks(rows, w_nos=w_nos, w_thermal=w_th)

    print(f"source={source} process={args.process} T={args.temp} app={args.application} n={len(ranked)}")
    print(f"{'rank':<5}{'formula':<12}{'comb':<8}{'k':<8}{'Rcoat':<10}{'dT':<8}{'Tj_lo':<8}{'verdict'}")
    for r in ranked[:15]:
        k = "-" if r.get("kappa_wm_k") is None else f"{r['kappa_wm_k']:.1f}"
        rc = "-" if r.get("r_coat") is None else f"{r['r_coat']:.4f}"
        dt = "-" if r.get("dt_coat") is None else f"{r['dt_coat']:.2f}"
        tj = "-" if r.get("tj_lower_bound") is None else f"{r['tj_lower_bound']:.1f}"
        print(f"{r['rank']:<5}{r['formula']:<12}{r['combined']:<8.3f}{k:<8}{rc:<10}{dt:<8}{tj:<8}{r['thermal_verdict']}")

    if args.out:
        path = Path(args.out)
        keys = ["rank", "formula", "combined", "NOS", "manuf_score", "manuf_risk", "tier", "e_above_hull", "material_id"]
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(ranked)
        print(f"wrote {path}")
    if args.json:
        Path(args.json).write_text(json.dumps(ranked, indent=2, default=str))
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
