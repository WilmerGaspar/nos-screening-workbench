# Traction playbook (Antler / 14 days)

Antler does not need 10k users. They need evidence that a buyer opened the demo
and asked for the next step.

## What counts

Counts:
- 8–15 calls with coating / thermal / power-electronics engineers
- 3 people who ran the Streamlit link without you in the room
- 1 written “send me the CSV / I’d try this on a coupon”
- a public URL you can click in the interview

Does not count:
- GitHub stars
- “I posted on LinkedIn”
- friends who say “se ve chévere”
- claiming cooling without a coupon

## Vehicle this week: Streamlit Community Cloud

Use Streamlit as the *demo*, not as the company.

1. Repo: https://github.com/WilmerGaspar/nos-screening-workbench
2. https://share.streamlit.io → New app
3. Main file: `app.py`
4. Python packages: `requirements-cloud.txt` (no pymatgen; demo offline only)
5. You get `https://xxxxx.streamlit.app`

Script of the 3-minute demo:

1. Mission = Si power module, Cu, Ni–Al, PVD, 20 µm, 50 W.
2. Point to NiAl: κ = 92.2 W/m·K, R_coat ≈ 0.0022 K/W, verdict proceed_to_coupon.
3. Switch to Fe–Al: not_a_heat_spreader.
4. Say the sentence: “This is the pre-filter. The product is the coupon.”

## Who to write (20 names, not 200)

- process engineers at HVOF / PVD job shops
- packaging / thermal engineers at SiC module makers
- one professor who already deposits Fe–Al or Ni–Al
- one person at a TIM or cold-plate vendor

Mail of 5 lines:

> I built a pre-filter that ranks intermetallic coating phases by process
> (PVD/HVOF/plate) and published κ, then prints R_coat = t/κA.
> 3-minute demo: [streamlit URL]
> If you screen Ni–Al or Fe–Al today, I want 15 minutes on what the tool
> gets wrong. I am not selling a TIM.

## Metric board for Antler

| Week | Outreach | Calls | Unattended demo runs | Written next-step |
|---|---|---|---|---|
| 1 | 20 | 5 | 3 | 1 |
| 2 | +20 | +5 | +3 | +1 |

Bring that table, the URL, and one quote. That is traction at this stage.
