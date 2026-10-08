"""v0.3 tests: interface-first ranking, kappa relevance, coupon sheet."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coupon_pdf import build_coupon_pdf, pick_phase
from demo_data import load_demo
from interface import evaluate_interface, thermal_relevance
from nos_score import run_demo
from pipeline import DEFAULTS, evaluate_candidates
from ranking import rank_stability, weight_grid
from report_pdf import build_zip_all_langs


def _run(site="cold_plate", system=("cited7",), **extra):
    cfg = {**DEFAULTS, "site": site, "process_label": "PVD (sputter / arc)", **extra}
    return cfg, evaluate_candidates(run_demo(list(system)), cfg)


def test_no_match_returns_empty_not_whole_catalog():
    assert load_demo(["W", "Zn"], exact_chemsys=True) == []
    assert load_demo(["W", "Zn"], exact_chemsys=False) == []


def test_relevance_numbers_nial_20um():
    rel = thermal_relevance(92.2, 20, tim_kappa=4.0, tim_um=50, area_cm2=1.0, power_w=50, share_max=0.10)
    assert abs(rel.dt_tim_k - 6.25) < 1e-6
    assert abs(rel.kappa_needed - 14.4) < 0.01
    assert 0.016 < rel.share_bulk < 0.018
    assert abs(rel.dt_coat_k - 0.1085) < 1e-3
    assert rel.verdict == "kappa_not_limiting"
    assert 0.84 < rel.film_margin < 0.85


def test_share_does_not_depend_on_area():
    a = thermal_relevance(37.0, 20, area_cm2=0.5)
    b = thermal_relevance(37.0, 20, area_cm2=4.0)
    assert a.share_bulk == b.share_bulk and a.kappa_needed == b.kappa_needed
    assert a.dt_coat_k > b.dt_coat_k


def test_unknown_kappa_still_gets_a_bar():
    rel = thermal_relevance(None, 20)
    assert rel.verdict == "kappa_unknown" and rel.kappa_needed > 0 and rel.dt_coat_k is None


def test_feal_matters_on_heat_path_not_on_bond_coat():
    _, cold = _run("cold_plate")
    _, bond = _run("bond_coat")
    feal_cold = next(r for r in cold if r["formula"] == "FeAl")
    feal_bond = next(r for r in bond if r["formula"] == "FeAl")
    assert feal_cold["verdict"] == "kappa_significant"
    assert feal_bond["verdict"] == "proceed_to_coupon"


def test_site_sets_the_cte_comparison():
    cold = evaluate_interface("NiAl", {"Ni": 1, "Al": 1}, "cold_plate", die="Si", substrate="Cu")
    die = evaluate_interface("NiAl", {"Ni": 1, "Al": 1}, "die_attach", die="Si", substrate="Cu")
    assert abs(cold.dcte_max - 1.4) < 0.01
    assert abs(die.dcte_max - 12.5) < 0.01
    assert die.worst_neighbor.startswith("Si")


def test_unknown_cte_never_ranks_first_over_known():
    for site in ("cold_plate", "die_attach", "chip_metallization", "dbc_baseplate"):
        _, rows = _run(site)
        assert rows[0]["dcte_max"] is not None, site


def test_default_demo_story():
    _, rows = _run("cold_plate")
    assert rows[0]["formula"] == "NiAl" and rows[0]["verdict"] == "proceed_to_coupon"
    assert rows[-1]["formula"] == "FeAl"
    stab = rank_stability(rows)
    assert stab[0]["formula"] == "NiAl" and stab[0]["share_first"] > 0.8


def test_chemistry_flags():
    nial = evaluate_interface("NiAl", {"Ni": 1, "Al": 1}, "cold_plate", substrate="Cu")
    coal = evaluate_interface("CoAl", {"Co": 1, "Al": 1}, "cold_plate", substrate="Cu")
    assert "ni_fe_into_cu" in nial.flags and "ni_fe_into_cu" not in coal.flags
    assert "al_ti_oxide" in coal.flags
    nial_ss = evaluate_interface("NiAl", {"Ni": 1, "Al": 1}, "cold_plate", substrate="316SS")
    assert "ni_fe_into_cu" not in nial_ss.flags


def test_weight_grid_sums_to_one():
    grid = weight_grid()
    assert len(grid) == 120
    assert all(abs(sum(w.values()) - 1.0) < 1e-9 and min(w.values()) >= 0.1 - 1e-9 for w in grid)


def test_veto_goes_last():
    cfg = {**DEFAULTS, "process": "electroplating", "site": "cold_plate"}
    rows = evaluate_candidates(run_demo(["Ti", "Al"]), cfg)
    assert rows and all(r["verdict"] == "process_veto" for r in rows)


def test_coupon_pdf_is_one_page_and_names_the_phase():
    cfg, rows = _run("cold_plate")
    pdf = build_coupon_pdf(cfg, rows)
    assert pdf.startswith(b"%PDF")
    assert len(re.findall(rb"/Type /Page[^s]", pdf)) == 1
    assert pick_phase(rows)["formula"] == "NiAl"


def test_reports_build_in_four_languages():
    cfg, rows = _run("dbc_baseplate")
    assert len(build_zip_all_langs(cfg, rows, "demo")) > 1000


def test_alcu_kappa_rows_are_cited_and_matched_by_composition():
    from thermal import evaluate_thermal, lookup, temp_label
    assert lookup("CuAl2")["kappa"] == 62.0 and lookup("Al2Cu")["phase"] == "Al2Cu"
    assert lookup("Cu9Al4")["kappa"] == 38.6
    for f in ("Al4Cu9", "Al2Cu3", "AlCu", "Al2Cu"):
        rec = lookup(f)
        assert "10.1002/adem.202501357" in rec["citation"] and rec["cte_ppm_k"] is None
        assert temp_label(rec) == "ambient"
    assert lookup("Al9Cu11") is None  # two-phase zeta sample left out on purpose
    assert "ambient" in evaluate_thermal("AlCu").notes[0]
    assert "300 K" in evaluate_thermal("NiAl").notes[0]


def test_alcu_flag_only_where_al_meets_cu():
    nial_cu = evaluate_interface("NiAl", {"Ni": 1, "Al": 1}, "cold_plate", substrate="Cu")
    nial_ss = evaluate_interface("NiAl", {"Ni": 1, "Al": 1}, "cold_plate", substrate="316SS")
    feti_cu = evaluate_interface("FeTi", {"Fe": 1, "Ti": 1}, "cold_plate", substrate="Cu")
    cu_pad = evaluate_interface("Al2Cu", {"Al": 2, "Cu": 1}, "chip_metallization", die="Si", substrate="Cu")
    assert "al_cu_imc" in nial_cu.flags and "al_cu_imc" not in nial_ss.flags
    assert "al_cu_imc" not in feti_cu.flags and "al_cu_imc" in cu_pad.flags


def test_demo_story_unchanged_by_alcu_data():
    _, rows = _run("cold_plate")
    assert [r["formula"] for r in rows][:3] == ["NiAl", "CoAl", "Ni3Al"]
    assert rows[0]["combined"] == 0.8075


def test_imc_thickness_threshold():
    from interface import alcu_imc_kappa_min, imc_thickness_threshold_um
    phase, k = alcu_imc_kappa_min()
    assert phase == "Al2Cu3" and k == 25.9
    t = imc_thickness_threshold_um(25.9, tim_kappa=4.0, tim_um=50, share_max=0.10)
    assert 35.9 < t < 36.1
    _, rows = _run("cold_plate")
    nial = next(r for r in rows if r["formula"] == "NiAl")
    feti = next(r for r in rows if r["formula"] == "FeTi")
    assert nial["imc_t_max_um"] == 36.0 and any("Al-Cu IMC growth" in n for n in nial["flag_notes"])
    assert feti["imc_t_max_um"] is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"ok  {fn.__name__}")
    print("all tests passed")
