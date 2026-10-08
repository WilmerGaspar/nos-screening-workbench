# Methodology — NOS Screening Workbench v0.3

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

## 4. Thermal relevance (v0.3; replaces the v0.2 cooling score)

Bulk kappa (published only, Terada 1995/2002, Hanai 1996, Williams 1987) is an upper bound
for a deposited film. It no longer enters the score.

Al-Cu intermetallics (v0.3.1): Al4Cu9 38.6, Al2Cu3 25.9, AlCu 73.4, Al2Cu 62.0 W/m.K, ambient
temperature, k = alpha cp rho (xenon flash, DSC, Archimedes), cast and homogenized samples
(Nazarahari et al., Adv. Eng. Mater. 2026, DOI 10.1002/adem.202501357, Table 3). The paper's
zeta sample is two-phase and is not used. No CTE is reported, so these rows get
coupon_cte_unknown. Thin films of the same phases differ (smaller grains, higher hardness,
per the same paper), so these are bulk reference values, not film values.

R''_coat = t / kappa,  R''_TIM = t_TIM / kappa_TIM  (K.m2/W, 1-D, no interface R invented)

share = R''_coat / (R''_coat + R''_TIM)   (independent of area)

kappa_needed = t (1 - s_max) / (s_max R''_TIM)   (default s_max = 0.10)

film_margin = 1 - kappa_needed / kappa_bulk   (how much of the bulk value the film may lose)

TIM defaults (4 W/m.K, 50 um) are editable assumptions, not measurements.

## 5. Interface

The layer site lists the materials the coating touches (die, DBC Cu, baseplate, Al wire).
dCTE_max = max |CTE_coat - CTE_neighbor|; interface score = clip(1 - dCTE_max / 16, 0, 1).
Unknown CTE scores 0.5 and gets the verdict coupon_cte_unknown. CTE values carried in
thermal.py have no DOI in this repo and are flagged `cte_uncited`.

Chemistry watch items change the coupon sheet, not the score:
- ni_fe_into_cu, al_ti_oxide: practitioner input (unpublished, 2026-10).
- al_cu_imc (Al meets Cu at the site): Al-Cu IMCs are harder than Al and Cu and are the
  mechanical weak point of the interface; theta (Al2Cu) can turn into Al4Cu9 under local Al
  depletion, reported at 175-250 C in Al-Cu wire bonds (Xu et al., Acta Mater. 2011, as cited
  by Nazarahari et al. 2026).

## 6. Verdict and rank

Priority: process_veto > kappa_significant (heat-path sites only) > coupon_cte_unknown >
coupon_high_cte_risk (dCTE > 8 ppm/K) > proceed_to_coupon.

Reliability rank (cooling applications): C = 0.25 NOS + 0.35 M + 0.40 I, weights editable.
Rows are ordered by verdict tier, then C. Caps: kappa_significant 0.45, process_veto 0.25.
Rank stability = share of 120 weight sets (each weight 0.10-0.80, step 0.05) in which a
phase ranks first.

The v0.2 kappa score (0.30 NOS + 0.30 M + 0.40 kappa) is kept in the data as
kappa_score_v02 for comparison only.
