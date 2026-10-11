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


def test_vrh_reads_the_dict_that_current_mp_api_returns():
    from nos_score import _vrh
    # Test inputs only (not material data): the shape mp-api 0.46 / emmet-core 0.87 return.
    assert _vrh({"voigt": 101.0, "reuss": 99.0, "vrh": 100.0}) == 100.0
    assert _vrh({"voigt": 101.0, "reuss": 99.0}) is None


def test_vrh_reads_an_object_with_a_vrh_attribute():
    from types import SimpleNamespace
    from nos_score import _vrh
    assert _vrh(SimpleNamespace(voigt=101.0, reuss=99.0, vrh=100.0)) == 100.0
    assert _vrh(SimpleNamespace(voigt=101.0)) is None


def test_vrh_none_stays_none():
    from nos_score import _vrh
    assert _vrh(None) is None
    assert _vrh({}) is None


def test_alcu_system_returns_the_four_measured_phases():
    from demo_systems import CITED_PHASES, DEMO_SYSTEMS
    from pipeline import DEFAULTS, evaluate_candidates
    assert "Al,Cu" in [s["key"] for s in DEMO_SYSTEMS]
    elements = [e.strip() for e in "Al,Cu".split(",")]  # same split as the app sidebar
    rows = evaluate_candidates(run_demo(elements, exact_chemsys=True), dict(DEFAULTS))
    kappa = {r["formula"]: r["kappa_wm_k"] for r in rows}
    assert kappa == {"Al4Cu9": 38.6, "Al2Cu3": 25.9, "AlCu": 73.4, "Al2Cu": 62.0}
    assert all("DOI 10.1002/adem.202501357" in r["thermal_citation"] for r in rows)
    # The "7 cited phases" preset stays as it was.
    seven = ["NiAl", "Ni3Al", "CoAl", "FeAl", "FeTi", "NiGa", "Ni3Ga"]
    assert CITED_PHASES == seven
    assert sorted(r["formula"] for r in run_demo(["cited7"])) == sorted(seven)


def _app(system=None):
    """Run app.py headless (Streamlit AppTest) with the default sidebar, optionally with another chemical system."""
    import os
    import warnings
    from streamlit.testing.v1 import AppTest
    warnings.filterwarnings("ignore")
    os.environ.pop("NOS_EVAL_FORM_URL", None)
    os.environ.pop("MP_API_KEY", None)
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=180)
    at.run()
    if system:
        next(s for s in at.selectbox if s.label == "Sistema químico").set_value(system).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_default_demo_unchanged_by_reference_systems():
    at = _app()
    assert [m.value for m in at.markdown if m.value.startswith("## ")] == ["## NiAl"]  # recommendation card
    assert any(m.label == "Puntaje" and m.value == "0.807" for m in at.metric)
    infos = [i.value for i in at.info]
    assert any("NiAl queda 1.º en el 92%" in v for v in infos)
    assert not any(v.startswith("Sistema de referencia") for v in infos)
    coupon = [d.proto.id for d in at.get("download_button") if "dl_coupon" in d.proto.id]
    assert len(coupon) == 2  # coupon sheet in the card and in the downloads row
    assert [p.proto.popover.label for p in at.get("popover")] == ["Solicitar estudio o probeta", "Evalúa esta herramienta (2 min)"]


def test_reference_system_alcu_shows_info_instead_of_card():
    from demo_systems import DEMO_SYSTEMS, is_reference
    assert [s["key"] for s in DEMO_SYSTEMS if is_reference(s["key"])] == ["Al,Cu"]
    at = _app("Al,Cu")
    assert not [m.value for m in at.markdown if m.value.startswith("## ")]  # no recommendation card
    infos = [i.value for i in at.info]
    assert ("Sistema de referencia: fases medidas que crecen en uniones Al/Cu, no recubrimientos. "
            "La de menor κ es Al2Cu3 (25.9 W/m·K).") in infos
    assert not any("Estabilidad del ranking" in v for v in infos)
    assert not any("dl_coupon" in d.proto.id for d in at.get("download_button"))  # no coupon sheet
    assert [p.proto.popover.label for p in at.get("popover")] == ["Evalúa esta herramienta (2 min)"]  # no study request
    # Table, phase map and per-phase detail stay.
    assert [s.value for s in at.subheader][:3] == ["Ranking", "Mapa de fases", "Detalle por fase"]
    assert len(at.get("plotly_chart")) == 1
    assert any(m.label == "κ bulk / κ necesaria" for m in at.metric)


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
        test_vrh_reads_the_dict_that_current_mp_api_returns,
        test_vrh_reads_an_object_with_a_vrh_attribute,
        test_vrh_none_stays_none,
        test_alcu_system_returns_the_four_measured_phases,
        test_default_demo_unchanged_by_reference_systems,
        test_reference_system_alcu_shows_info_instead_of_card,
    ]
    for fn in tests:
        fn()
        print(f"ok  {fn.__name__}")
    print("all tests passed")
