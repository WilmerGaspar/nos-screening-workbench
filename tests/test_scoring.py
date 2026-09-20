import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from manufacturability import evaluate
from ranking import attach_ranks
from scoring import nos_score, pugh_ratio, stability_score
from nos_score import run_demo
from thermal import evaluate_thermal, kappa_score
from die_stack import evaluate_stack, r_layer


def test_stability_monotone():
    assert stability_score(0.0) > stability_score(0.05) > stability_score(0.2)


def test_pugh_ti_al3_brittle():
    assert pugh_ratio(100.0, 82.0) < 1.75


def test_electroplating_veto_on_tial():
    mat = {
        "formula": "TiAl",
        "composition": {"Ti": 1, "Al": 1},
        "theoretical": False,
        "has_icsd": True,
        "bulk_modulus": 110.0,
        "shear_modulus": 70.0,
    }
    res = evaluate(mat, "electroplating", 300)
    assert res.veto is True
    assert res.risk_level == "unsuitable"


def test_electroplating_allows_znfe():
    mat = {
        "formula": "Zn13Fe",
        "composition": {"Zn": 13, "Fe": 1},
        "theoretical": False,
        "has_icsd": True,
        "bulk_modulus": 80.0,
        "shear_modulus": 35.0,
    }
    res = evaluate(mat, "electroplating", 80)
    assert res.veto is False
    assert res.score > 0.4


def test_process_changes_ranking():
    demo = run_demo(["Fe", "Al"], exact_chemsys=True)
    assert demo

    def combined_for(process, temp):
        rows = []
        for c in demo:
            m = evaluate(c, process, temp)
            rows.append({**c, "manuf_score": m.score})
        return attach_ranks(rows)

    pvd = combined_for("PVD", 450)
    plate = combined_for("electroplating", 80)
    al13_pvd = next(r for r in pvd if r["formula"] == "Al13Fe4")
    al13_plate = next(r for r in plate if r["formula"] == "Al13Fe4")
    assert al13_plate["manuf_score"] < al13_pvd["manuf_score"]


def test_nos_bounds():
    assert 0 <= nos_score(1, 1, 1, 1) <= 1
    assert nos_score(0, 0, 0, 0) == 0


def test_nial_is_heat_spreader_on_cu():
    res = evaluate_thermal("NiAl", substrate="Cu", application="cpu_cold_plate")
    assert res.kappa_wm_k == 92.2
    assert res.heat_spreader_ok is True
    assert res.verdict == "proceed_to_coupon"


def test_feal_not_heat_spreader():
    res = evaluate_thermal("FeAl", substrate="Cu", application="cpu_cold_plate")
    assert res.kappa_wm_k == 12.0
    assert res.verdict == "not_a_heat_spreader"


def test_unknown_phase_not_invented():
    res = evaluate_thermal("Al13Fe4", substrate="Cu", application="sic_power_module")
    assert res.kappa_wm_k is None
    assert res.verdict == "missing_thermal_data"
    assert res.score <= 0.2


def test_kappa_score_monotone():
    assert kappa_score(12) < kappa_score(37) < kappa_score(92)


def test_r_coat_nial_20um_1cm2():
    r = r_layer(20e-6, 92.2, 1e-4)
    assert 0.0020 < r < 0.0024
    stack = evaluate_stack("NiAl", thickness_um=20, area_cm2=1.0, power_w=50, t_sink_c=45)
    assert stack.r_coat_k_per_w is not None
    assert stack.within_budget is True
    assert stack.verdict == "stack_within_budget"


def test_r_coat_feal_over_budget_if_thick():
    stack = evaluate_stack("FeAl", thickness_um=200, area_cm2=1.0, power_w=50, budget_k_per_w=0.05)
    assert stack.r_coat_k_per_w is not None
    assert stack.within_budget is False


def test_stack_no_invented_kappa():
    stack = evaluate_stack("Al13Fe4")
    assert stack.r_coat_k_per_w is None
    assert stack.verdict == "missing_thermal_data"


if __name__ == "__main__":
    tests = [
        test_stability_monotone,
        test_pugh_ti_al3_brittle,
        test_electroplating_veto_on_tial,
        test_electroplating_allows_znfe,
        test_process_changes_ranking,
        test_nos_bounds,
        test_nial_is_heat_spreader_on_cu,
        test_feal_not_heat_spreader,
        test_unknown_phase_not_invented,
        test_kappa_score_monotone,
        test_r_coat_nial_20um_1cm2,
        test_r_coat_feal_over_budget_if_thick,
        test_stack_no_invented_kappa,
    ]
    for fn in tests:
        fn()
        print(f"ok  {fn.__name__}")
    print("all tests passed")
