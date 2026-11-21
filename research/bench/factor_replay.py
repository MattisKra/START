"""Apply the recorded Python policy to Fable's prices on the same settled field."""
from rate_check_replay import compare
from claimbot_shadow.checks import check


def gap(field, original, changed):
    lo, hi, il, ih = compare(field, original, changed)
    return {k: [round(left, 2), round(right, 2)] for k, left, right in (
        ("reviewer_saving", lo, hi), ("issuer_change", il, ih), ("net", lo + il, hi + ih))}


def replay(field, python, receipt, config):
    a, b = config["charge_factor"], config["limit_factor"]
    if min(a, b) <= 0:
        return {"status": "python_policy_is_not_two_positive_multipliers"}
    rows = receipt["lines"]
    native = {r["index"]: (r["charge_price"], r["acceptance_limit"]) for r in rows}
    # Holding each charge fixed isolates the effect of changing the review limit.
    # This is an action-ratio diagnostic; it requires no estimate of Fable's median.
    matched = {pos: (charge, round(b / a * charge, 2) if limit > 0 else 0.)
               for pos, (charge, limit) in native.items()}
    report = dict(charge_factor=a, limit_factor=b,
                  fixed_charge_ratio_vs_native=gap(field, native, matched),
                  fixed_charge_ratio_vs_python=gap(field, python, matched))
    # A second sensitivity check treats the quoted charge itself as a price anchor.
    anchor = {pos: (round(a * charge, 2), round(b * charge, 2) if limit > 0 else 0.)
              for pos, (charge, limit) in native.items()}
    report["charge_as_median_vs_native"] = gap(field, native, anchor)
    report["charge_as_median_vs_python"] = gap(field, python, anchor)
    issues = check(rows, set(field))
    if issues:
        report["explicit_beliefs"] = {"status": "unavailable", "issues": issues}
        return report
    hybrid = {r["index"]: (round(a * r["fair_median_gross_if_valid"], 2),
                           round(b * r["fair_median_gross_if_valid"], 2)
                           if 1 - r["p_valid"] < config["reject_p"] else 0.) for r in rows}
    report["explicit_beliefs"] = dict(status="scored", hybrid_actions=hybrid,
                                      python_factors_vs_native=gap(field, native, hybrid),
                                      fable_beliefs_vs_python_beliefs=gap(field, python, hybrid),
                                      native_vs_python=gap(field, python, native))
    return report
