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


def _app(system=None, lang="es"):
    """Run app.py headless (Streamlit AppTest) with the default sidebar, optionally with another chemical system."""
    import os
    import warnings
    from streamlit.testing.v1 import AppTest
    warnings.filterwarnings("ignore")
    os.environ.pop("NOS_EVAL_FORM_URL", None)
    os.environ.pop("MP_API_KEY", None)
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=180)
    at.run()
    if lang == "en":  # changing the language resets the other selectors, so it goes first
        next(s for s in at.selectbox if s.label == "Language / Idioma").set_value("en").run()
    if system:
        label = "Chemical system" if lang == "en" else "Sistema químico"
        next(s for s in at.selectbox if s.label == label).set_value(system).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _map(at):
    """(trace names with point counts, layout.showlegend) of the phase map."""
    import json
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    return [(d.get("name"), len(d.get("x", []))) for d in spec["data"]], spec["layout"].get("showlegend")


def _page_text(at):
    """Every element of the rendered page as protobuf text (labels, values, chart specs, code blocks)."""
    out = []
    def walk(node):
        if getattr(node, "proto", None) is not None:
            out.append(str(node.proto))
        for child in (getattr(node, "children", None) or {}).values():
            walk(child)
    walk(at._tree)
    return "\n".join(out)


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


def test_other_systems_keep_evidence_score_and_order():
    from demo_systems import DEMO_SYSTEMS, is_reference
    at = _app()
    # Default demo: NiAl first, 0.807, 92 %, evidence label and map as before.
    fase = next(s for s in at.selectbox if s.label == "Fase")
    assert fase.options[0] == "01 · NiAl (0.807)"
    assert any(m.label == "Puntaje" and m.value == "0.807" for m in at.metric)
    assert any("NiAl queda 1.º en el 92%" in i.value for i in at.info)
    assert _map(at) == ([("Verificado experimentalmente", 7)], None)
    # Every other system: no reference label, no forced legend.
    for key in [s["key"] for s in DEMO_SYSTEMS if not is_reference(s["key"]) and s["key"] != "cited7"]:
        next(s for s in at.selectbox if s.label == "Sistema químico").set_value(key).run()
        assert not at.exception, (key, [e.message for e in at.exception])
        if not at.get("plotly_chart"):  # Co,Ti has no demo phase: no map at all
            assert not run_demo([e.strip() for e in key.split(",")]), key
            continue
        traces, legend = _map(at)
        assert legend is None and traces and all(name != "Medido (referencia)" for name, _ in traces), key


def test_alcu_shows_measured_reference_never_exploratory():
    for lang, bad, good in (("es", "Exploratorio", "Medido (referencia)"), ("en", "Exploratory", "Measured (reference)")):
        at = _app("Al,Cu", lang)
        text = _page_text(at)
        assert bad not in text and bad.lower() not in text, lang
        assert good in text, lang
        assert _map(at) == ([(good, 4)], True), lang


def test_measured_reference_label_only_for_cited_demo_rows():
    from demo_systems import REFERENCE_TIER, shown_tier
    demo = {"source": "demo", "kappa_wm_k": 25.9, "tier": "Exploratory"}
    live = {"source": "materials_project", "kappa_wm_k": 73.4, "tier": "Exploratory"}  # polymorph matched by composition
    no_k = {"source": "demo", "kappa_wm_k": None, "tier": "Exploratory"}
    assert shown_tier(demo, True) == REFERENCE_TIER == "Measured (reference)"
    assert shown_tier(live, True) == "Exploratory"
    assert shown_tier(no_k, True) == "Exploratory"
    assert shown_tier(demo, False) == "Exploratory"


def test_reference_table_rows_sorted_by_kappa_with_empty_scores():
    from demo_systems import reference_table_rows
    from pipeline import DEFAULTS, evaluate_candidates
    rows = evaluate_candidates(run_demo(["Al", "Cu"]), dict(DEFAULTS))
    shown = reference_table_rows(rows)
    assert [(r["rank"], r["formula"], r["kappa_wm_k"]) for r in shown] == [
        (1, "Al2Cu3", 25.9), (2, "Al4Cu9", 38.6), (3, "Al2Cu", 62.0), (4, "AlCu", 73.4)]
    assert all(r["NOS"] is None and r["combined"] is None for r in shown)  # no stability / mechanics data
    assert [r["formula"] for r in rows] == ["Al2Cu", "AlCu", "Al2Cu3", "Al4Cu9"]  # the rows themselves are untouched
    assert all(r["NOS"] is not None for r in rows)
    # A row that has Materials Project stability and elasticity keeps its numbers; a row without kappa goes last.
    full = {"formula": "X", "kappa_wm_k": None, "e_above_hull": 0.0, "bulk_modulus": 1.0, "shear_modulus": 1.0, "NOS": 0.5, "combined": 0.4, "rank": 1}
    last = reference_table_rows([full] + rows)[-1]
    assert last["formula"] == "X" and last["NOS"] == 0.5 and last["combined"] == 0.4 and last["rank"] == 5


def test_alcu_tables_sorted_by_kappa_and_default_tables_unchanged():
    at = _app()
    # Default demo: NiAl first, 0.807, 92 %; full table ordered by score with numbers in NOS / score.
    assert any("NiAl queda 1.º en el 92%" in i.value for i in at.info)
    full = at.dataframe[1].value
    assert list(full["Puesto"]) == list(range(1, 8)) and full["Fase"].iloc[0] == "NiAl"
    assert full["Puntaje"].iloc[0] == "0.8075"  # 4 decimals in the table; the detail shows 0.807
    assert any(m.label == "Puntaje" and m.value == "0.807" for m in at.metric)
    assert "sin dato" not in set(full["Puntaje"]) | set(full["NOS"])
    assert [float(v) for v in full["Puntaje"]] == sorted((float(v) for v in full["Puntaje"]), reverse=True)
    # Al-Cu: both tables sorted by kappa bulk (first = the info line's phase), NOS / score "sin dato".
    next(s for s in at.selectbox if s.label == "Sistema químico").set_value("Al,Cu").run()
    assert not at.exception, [e.message for e in at.exception]
    short, full = at.dataframe[0].value, at.dataframe[1].value
    order = ["Al2Cu3", "Al4Cu9", "Al2Cu", "AlCu"]
    assert list(short["Fase"]) == order and list(full["Fase"]) == order
    assert list(short["Puesto"]) == list(full["Puesto"]) == [1, 2, 3, 4]
    assert list(full["κ bulk (W/m·K)"]) == ["25.9", "38.6", "62.0", "73.4"]
    assert set(full["Puntaje"]) == set(full["NOS"]) == {"sin dato"}
    assert any("La de menor κ es Al2Cu3 (25.9 W/m·K)" in i.value for i in at.info)


def _old_pdf_rows(lang, rows):
    """PDF ranking rows exactly as build_pdf made them before reference systems (main 3051ad5), verdict as text."""
    from i18n import verdict_text
    out = []
    for r in rows[:20]:
        k = r.get("kappa_wm_k"); dc = r.get("dcte_max"); kn = r.get("kappa_needed")
        out.append([str(r.get("rank")), r.get("formula",""), f"{r.get('combined',0):.3f}", f"{r.get('manuf_score',0):.3f}", "-" if dc is None else f"{dc:.1f}", verdict_text(lang, r.get("verdict") or "coupon_cte_unknown"), "-" if k is None else f"{k:.1f}", "-" if kn is None else f"{kn:.1f}"])
    return out


def _alcu_rows(**cfg):
    from pipeline import DEFAULTS, evaluate_candidates
    return evaluate_candidates(run_demo(["Al", "Cu"]), {**DEFAULTS, **cfg})


def test_reference_detail_notes_hide_deposition_and_cte_notes():
    from demo_systems import reference_detail_notes
    from interface import FLAG_TEXT
    hidden = [FLAG_TEXT["al_ti_oxide"], FLAG_TEXT["cte_missing"], "No coating CTE in the catalog: interface score set to neutral 0.5."]
    for process in ("pvd", "thermal_spray", "electroplating"):
        for r in _alcu_rows(process=process):
            everything = (r["interface_notes"] + r["relevance_notes"] + r["flag_notes"] + r["manuf_notes"])
            assert all(h in everything for h in hidden), (process, r["formula"])  # the hidden notes do exist
            shown = reference_detail_notes(r)
            assert not set(hidden) & set(shown)
            assert [n for n in shown if n in r["manuf_notes"]] == [n for n in r["manuf_notes"] if "Pugh" in n] != []
            kept = r["relevance_notes"] + [n for n in r["flag_notes"] if n not in hidden]
            assert all(n in shown for n in kept)
            assert any(n.startswith("TIM term") for n in shown) and any(n.startswith("Coating at bulk kappa") for n in shown)
            assert any(n.startswith("Al and Cu meet") for n in shown) and any("~36 um" in n for n in shown)
    assert "PVD can deposit most intermetallics; residual stress is the risk." in _alcu_rows(process="pvd")[0]["manuf_notes"]


def test_alcu_detail_shows_no_hidden_notes():
    import ui_text as ui
    from demo_systems import reference_detail_notes
    from interface import FLAG_TEXT
    rows = {r["formula"]: r for r in _alcu_rows()}
    for lang, notes_h, code in (("es", "Notas de esta fase", "Código del dictamen"), ("en", "Notes on this phase", "Verdict code")):
        at = _app("Al,Cu", lang)
        fase = next(s for s in at.selectbox if s.label in ("Fase", "Phase"))
        assert fase.options == ["01 · Al2Cu3 (κ 25.9)", "02 · Al4Cu9 (κ 38.6)", "03 · Al2Cu (κ 62.0)", "04 · AlCu (κ 73.4)"], lang
        for option in fase.options:
            next(s for s in at.selectbox if s.label in ("Fase", "Phase")).set_value(option).run()
            assert not at.exception, [e.message for e in at.exception]
            row = rows[option.split(" · ")[1].split(" (")[0]]
            hidden = [FLAG_TEXT["al_ti_oxide"], FLAG_TEXT["cte_missing"], "No coating CTE in the catalog: interface score set to neutral 0.5."]
            hidden += [n for n in row["manuf_notes"] if "Pugh" not in n]
            exp = [e for e in at.expander if e.label == notes_h]
            assert len(exp) == 1, (lang, option)
            shown = [m.value for m in exp[0].markdown]
            assert shown == [f"- {ui.note(lang, n)}" for n in reference_detail_notes(row)], (lang, option)
            assert not any(ui.note(lang, h) in v for h in hidden for v in shown), (lang, option)
            assert exp[0].caption[0].value == row["thermal_citation"]
            # Only the kappa metric in the detail; no verdict badge, verdict text or verdict code.
            detail_metrics = [m.label for m in at.metric][4:]
            assert detail_metrics == ["κ bulk / " + ("κ necesaria" if lang == "es" else "κ needed")], (lang, detail_metrics)
            assert not any("badge[" in m.value for m in at.markdown)
            assert not any(c.value.startswith(code) for c in at.caption)


def test_reference_pdf_rows_and_other_systems_pdf_unchanged():
    from demo_systems import DEMO_SYSTEMS, is_reference
    from pipeline import DEFAULTS, evaluate_candidates
    from report_pdf import build_pdf, ranking_rows
    label = {"es": "Medido (referencia)", "en": "Measured (reference)", "fr": "Measured (reference)", "de": "Measured (reference)"}
    for lang in ("es", "en", "fr", "de"):
        got = ranking_rows(lang, _alcu_rows(), reference=True)
        assert [c[:4] for c in got] == [["1", "Al2Cu3", "-", "-"], ["2", "Al4Cu9", "-", "-"], ["3", "Al2Cu", "-", "-"], ["4", "AlCu", "-", "-"]]
        assert [c[5] for c in got] == [label[lang]] * 4 and [c[6] for c in got] == ["25.9", "38.6", "62.0", "73.4"]
    # Every other system, several setups, 4 languages: the PDF rows are exactly the old ones.
    n = 0
    for s in DEMO_SYSTEMS:
        if is_reference(s["key"]):
            continue
        for site in ("cold_plate", "die_attach"):
            for process in ("pvd", "thermal_spray"):
                cfg = {**DEFAULTS, "site": site, "process": process}
                rows = evaluate_candidates(run_demo([e.strip() for e in s["key"].split(",")]), cfg)
                for lang in ("es", "en", "fr", "de"):
                    assert ranking_rows(lang, rows, reference=False) == _old_pdf_rows(lang, rows), (s["key"], site, process, lang)
                    n += 1
    assert n == 11 * 2 * 2 * 4
    # build_pdf (and so the 4-language ZIP) asks for the reference rows only for Al,Cu.
    import report_pdf
    calls = []
    original = report_pdf.ranking_rows
    report_pdf.ranking_rows = lambda lang, rows, reference=False: calls.append(reference) or original(lang, rows, reference)
    try:
        for elements in (["Al", "Cu"], ["cited7"], ["Ni", "Al"]):
            cfg = {**DEFAULTS, "elements": elements, "process_label": "PVD (sputter / arc)"}
            assert build_pdf("es", cfg, evaluate_candidates(run_demo(elements), cfg), "demo")[:5] == b"%PDF-"
        report_pdf.build_zip_all_langs({**DEFAULTS, "elements": ["Al", "Cu"]}, _alcu_rows(), "demo")
    finally:
        report_pdf.ranking_rows = original
    assert calls == [True, False, False, True, True, True, True]


def test_other_systems_detail_unchanged():
    from demo_systems import DEMO_SYSTEMS, is_reference
    import ui_text as ui
    from interface import FLAG_TEXT
    at = _app()
    assert any("NiAl queda 1.º en el 92%" in i.value for i in at.info)
    assert any(m.label == "Puntaje" and m.value == "0.807" for m in at.metric)
    # The default detail (NiAl) still lists the notes a reference system hides.
    notes = [m.value for m in next(e for e in at.expander if e.label == "Por qué este dictamen").markdown]
    for n in ("PVD can deposit most intermetallics; residual stress is the risk.", FLAG_TEXT["al_ti_oxide"]):
        assert f"- {ui.note('es', n)}" in notes, n
    for key in [s["key"] for s in DEMO_SYSTEMS if not is_reference(s["key"])]:
        next(s for s in at.selectbox if s.label == "Sistema químico").set_value(key).run()
        assert not at.exception, (key, [e.message for e in at.exception])
        fase = [s for s in at.selectbox if s.label == "Fase"]
        if not fase:  # Co,Ti has no demo phase
            assert not run_demo([e.strip() for e in key.split(",")]), key
            continue
        assert all(o.endswith(")") and "(κ" not in o and o.split("(")[-1][:2] == "0." for o in fase[0].options), key
        assert [m.label for m in at.metric][4:] == ["Interfaz", "Fabricación", "κ bulk / κ necesaria", "Puntaje"], key
        assert [e.label for e in at.expander if e.label in ("Por qué este dictamen", "Notas de esta fase")] == ["Por qué este dictamen"], key
        assert any(c.value.startswith("Código del dictamen: ") for c in at.caption), key
        assert any("badge[" in m.value for m in at.markdown), key


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
        test_other_systems_keep_evidence_score_and_order,
        test_alcu_shows_measured_reference_never_exploratory,
        test_measured_reference_label_only_for_cited_demo_rows,
        test_reference_table_rows_sorted_by_kappa_with_empty_scores,
        test_alcu_tables_sorted_by_kappa_and_default_tables_unchanged,
        test_reference_detail_notes_hide_deposition_and_cte_notes,
        test_alcu_detail_shows_no_hidden_notes,
        test_reference_pdf_rows_and_other_systems_pdf_unchanged,
        test_other_systems_detail_unchanged,
    ]
    for fn in tests:
        fn()
        print(f"ok  {fn.__name__}")
    print("all tests passed")
