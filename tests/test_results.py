"""v0.4 tests: coupon results log (results.py)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import results as rlog


def _rec(**kw):
    base = dict(coupon_id="C-01", coating="Ni-Al 95/5", process="Arc / flame wire spray", substrate="Cu", stage="0")
    base.update(kw)
    return rlog.new_record(**base)


def test_required_fields_and_ranges():
    assert rlog.validate(_rec()) == []
    assert any("coupon_id" in e for e in rlog.validate(_rec(coupon_id=" ")))
    assert any("coating" in e for e in rlog.validate(_rec(coating="")))
    assert any("porosity_pct" in e for e in rlog.validate(_rec(porosity_pct=120)))
    assert any("thickness_um" in e for e in rlog.validate(_rec(thickness_um="abc")))
    assert any("stage" in e for e in rlog.validate(_rec(stage="3")))


def test_cycles_needed_after_stage_0():
    assert any("cycles" in e for e in rlog.validate(_rec(stage="1")))
    assert rlog.validate(_rec(stage="1", cycles=10)) == []
    assert any("whole number" in e for e in rlog.validate(_rec(stage="1", cycles=2.5)))


def test_outcome_follows_coupon_sheet_rules():
    assert rlog.outcome(_rec(crack_origin="coating_substrate_interface")) == "interface_limited"
    assert rlog.outcome(_rec(spallation="partial")) == "interface_limited"
    assert rlog.outcome(_rec(tape_test="fail")) == "interface_limited"
    assert rlog.outcome(_rec(crack_origin="within_coating")) == "coating_limited"
    assert rlog.outcome(_rec(crack_origin="substrate")) == "substrate_issue"
    assert rlog.outcome(_rec(tape_test="pass", spallation="none", crack_origin="none_seen")) == "passed_stage"
    assert rlog.outcome(_rec(tape_test="pass")) == "incomplete"  # section not checked yet
    # porosity alone never decides: no invented threshold
    assert rlog.outcome(_rec(porosity_pct=40, tape_test="pass", crack_origin="none_seen")) == "passed_stage"


def test_add_replaces_same_coupon_and_stage():
    log, err = rlog.add([], _rec(tape_test="pass"))
    assert not err and len(log) == 1
    log, _ = rlog.add(log, _rec(tape_test="fail"))
    assert len(log) == 1 and log[0]["tape_test"] == "fail"
    log, _ = rlog.add(log, _rec(stage="1", cycles=10))
    assert len(log) == 2
    same, err = rlog.add(log, _rec(coupon_id=""))
    assert err and same is log


def test_csv_round_trip_and_bad_rows():
    log, _ = rlog.add([], _rec(thickness_um=150, porosity_pct=4.5, tape_test="pass", crack_origin="none_seen"))
    log, _ = rlog.add(log, _rec(coupon_id="C-02", stage="1", cycles=10, peak_temp_c=150, spallation="edge",
                                tape_test="pass", crack_origin="none_seen", share_anonymized=True))
    text = rlog.to_csv(log)
    back, problems = rlog.from_csv(text)
    assert problems == [] and len(back) == 2
    assert back[0]["thickness_um"] == 150.0 and back[1]["cycles"] == 10 and back[1]["share_anonymized"] is True
    assert rlog.to_csv(back) == text
    broken = text + "C-03,,,,,,,9,,,,,,,,,,,,\n"
    back2, problems2 = rlog.from_csv(broken)
    assert len(back2) == 2 and len(problems2) == 1
    junk, p = rlog.from_csv("a,b\n1,2\n")
    assert junk == [] and "missing column" in p[0]


def test_json_and_summary_and_email():
    log, _ = rlog.add([], _rec(tape_test="pass", crack_origin="none_seen"))
    log, _ = rlog.add(log, _rec(coupon_id="C-02", crack_origin="coating_substrate_interface"))
    log, _ = rlog.add(log, _rec(coupon_id="C-03", coating="NiAl (PVD)", tape_test="pass", crack_origin="none_seen"))
    payload = json.loads(rlog.to_json(log))
    assert payload["schema"] == rlog.SCHEMA_VERSION and payload["records"][1]["outcome"] == "interface_limited"
    summ = {s["coating"]: s for s in rlog.summarize(log)}
    assert summ["Ni-Al 95/5"]["coupons"] == 2 and summ["Ni-Al 95/5"]["interface_limited"] == 1
    body = rlog.email_summary(log)
    assert "C-02" in body and "interface_limited" in body and len(body.splitlines()) == 3


def test_structured_problems_render_in_any_language():
    probs = rlog.problems(_rec(coupon_id="", porosity_pct=120, stage="1"))
    codes = {(f, c) for f, c, _ in probs}
    assert ("coupon_id", "required") in codes and ("porosity_pct", "range") in codes and ("cycles", "cycles_needed") in codes
    f, c, p = next(x for x in probs if x[1] == "range")
    assert rlog.render_problem(f, c, p) == "porosity_pct must be between 0 and 100"
    es = rlog.render_problem(f, c, p, template="{f}: debe estar entre {lo:g} y {hi:g}", label="Porosidad (%)")
    assert es == "Porosidad (%): debe estar entre 0 y 100"
    assert rlog.validate(_rec()) == [] and rlog.problems(_rec()) == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in tests:
        fn()
        print(f"ok  {fn.__name__}")
    print("all tests passed")
