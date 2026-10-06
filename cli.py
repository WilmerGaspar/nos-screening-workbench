#!/usr/bin/env python3
"""Command-line screening for notebooks and CI."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from interface import DEFAULT_SHARE_MAX, DEFAULT_TIM_KAPPA, DEFAULT_TIM_UM
from nos_score import run_demo, run_live
from pipeline import evaluate_candidates
from ranking import rank_stability
from stack_sites import DEFAULT_SITE, SITES


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
    p.add_argument("--site", default=DEFAULT_SITE, choices=list(SITES.keys()))
    p.add_argument("--tim-kappa", type=float, default=DEFAULT_TIM_KAPPA, help="TIM k in W/mK (assumption)")
    p.add_argument("--tim-um", type=float, default=DEFAULT_TIM_UM, help="TIM bond line in um (assumption)")
    p.add_argument("--share-max", type=float, default=DEFAULT_SHARE_MAX, help="max coating share of dT, 0-1")
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
    cfg = {
        "process": args.process, "temp": args.temp, "application": args.application,
        "substrate": args.substrate, "die": args.die, "site": args.site,
        "thickness_um": args.thickness_um, "area_cm2": args.area_cm2, "power_w": args.power_w,
        "t_sink_c": args.t_sink, "tim_kappa": args.tim_kappa, "tim_um": args.tim_um,
        "share_max": args.share_max, "cooling": cooling,
    }
    ranked = evaluate_candidates(cands, cfg)

    print(f"source={source} process={args.process} T={args.temp} app={args.application} site={args.site} n={len(ranked)}")
    if not ranked:
        print("no phases for that system in this source")
        return 1
    print(f"{'rank':<5}{'formula':<10}{'score':<8}{'iface':<7}{'dCTE':<7}{'k':<7}{'k_need':<8}{'dTcoat':<8}{'dTtim':<7}{'verdict'}")
    for r in ranked[:15]:
        k = "-" if r.get("kappa_wm_k") is None else f"{r['kappa_wm_k']:.1f}"
        dc = "-" if r.get("dcte_max") is None else f"{r['dcte_max']:.1f}"
        dt = "-" if r.get("dt_coat") is None else f"{r['dt_coat']:.2f}"
        print(f"{r['rank']:<5}{r['formula']:<10}{r['combined']:<8.3f}{r['interface_score']:<7.2f}{dc:<7}{k:<7}{r['kappa_needed']:<8.1f}{dt:<8}{r['dt_tim']:<7.2f}{r['verdict']}")
    if cooling:
        top = rank_stability(ranked)[0]
        print(f"rank stability: {top['formula']} first in {top['share_first']:.0%} of {top['of']} weight sets")

    if args.out:
        path = Path(args.out)
        keys = ["rank", "formula", "combined", "verdict", "NOS", "manuf_score", "interface_score", "dcte_max",
                "kappa_wm_k", "kappa_needed", "coat_share", "dt_coat", "dt_tim", "manuf_risk", "tier", "e_above_hull", "material_id"]
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
