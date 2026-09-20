# Methodology — NOS Screening Workbench v0.2

This document is the contract with the user. If a number appears in the UI, it is produced by one of the formulas below.

## 1. What the tool is allowed to claim

The workbench is a **pre-filter**. It ranks phases so an engineer can decide what to send to CALPHAD, DFT follow-up, or a coating coupon. It does **not**:

- invent thermal conductivity for unknown phases
- qualify a coating for service
- replace process windows from a job shop or OEM spec
- treat GNoME / theoretical entries as synthesized materials

Live Materials Project rows are labelled `materials_project`. The offline set is labelled `demo`.

## 2. NOS

NOS = 0.25 S_stab + 0.30 S_mech + 0.25 S_abund + 0.20 S_conf

S_stab = exp(-E_hull / 0.05) with E_hull in eV/atom.

Mechanical: VRH bulk and shear, each capped at 400 GPa. Missing elasticity => S_mech = 0.

Abundance: mass-fraction-weighted crustal ppm from Rudnick & Gao 2014, log-normalized to oxygen.

Evidence tiers: Experimentally verified 1.00, Partially backed 0.75, Well-calculated (DFT) 0.55, Exploratory 0.30.

## 3. Manufacturability

M = 0.35 P + 0.25 T + 0.20 F + 0.20 E

Electroplating veto if plateable atomic fraction < 0.35. Combined score capped at 0.25 on veto. Pugh B/G < 1.75 flagged brittle.

## 4. Chip-cooling layer

Published kappa only (Terada 1995/2002): NiAl 92.2, CoAl 37, Ni3Al 28.5, FeAl 12 W/m-K.
Unknown phases: missing_thermal_data, score 0.15. No rule-of-mixtures.

R_coat = t / (kappa A). Tj lower bound = T_sink + P * R_coat. Interface R is not invented.

Cooling rank: C = 0.30 NOS + 0.30 M + 0.40 T_thermal
