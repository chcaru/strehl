"""M55b -- property test for b6_rollup, written because the rename exposed that
B6's coverage kill condition existed only in prose.  Rule 39: plant a wrong
answer and require the test to reject it.  Golden vectors pin values; these
pin properties.  No corpus data is read.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spec_v1 as S


def cell(stack, roi, passed=True, wrong=False):
    return dict(ref=1.0, test=0.9, d=0.1, status="Ok", status_test="Ok", z=9.0,
                z_pass=True, detected=passed, wrong_sign=wrong, passed=passed,
                stack=stack, roi=roi)


def full(over=None):
    out = []
    for st in S.HELD_OUT:
        for i in range(S.TH["b6_min_rois"]):
            out.append(cell(st, i))
    for (st, i), kw in (over or {}).items():
        for c in out:
            if c["stack"] == st and c["roi"] == i:
                c.update(kw)
    return out


def main():
    print("=" * 78)
    print("M55b -- b6_rollup property test (no corpus data read)")
    print("=" * 78)
    checks = []

    r = S.b6_rollup(full())
    checks.append(("complete, all pass -> PASS", r["passed"] is True, r["kill"]))

    # PLANTED WRONG ANSWER: pooled fraction is above threshold, one subject is not.
    bad = full({("wrapped-text-1", 0): dict(passed=False, detected=False),
                  ("wrapped-text-2", 0): dict(passed=False, detected=False)})
    r = S.b6_rollup(bad)
    pooled = r["frac_passed"]
    old_verdict = pooled >= 1.0 - S.TH["b6_quantile"] and r["n_wrong_sign"] == 0
    checks.append((f"planted: pooled {100*pooled:.1f}% >= 90%, subject 'wrapped-text' "
                   f"{100*r['subject_frac']['wrapped-text']:.0f}% -> must KILL",
                   (r["passed"] is False) and old_verdict, r["kill"]))

    r = S.b6_rollup([cell("bee-1", i) for i in range(24)])
    checks.append(("24 cells from one stack -> KILL", r["passed"] is False, r["kill"]))

    r = S.b6_rollup([{k: v for k, v in c.items() if k != "stack"} for c in full()])
    checks.append(("cells that do not declare stack -> KILL", r["passed"] is False, r["kill"]))

    thin = [c for c in full() if not (c["stack"] == "bee-2" and c["roi"] == 3)]
    r = S.b6_rollup(thin)
    checks.append(("one stack with only 3 ROIs -> KILL", r["passed"] is False, r["kill"]))

    r = S.b6_rollup(full({("bee-3", 2): dict(wrong_sign=True)}))
    checks.append(("one wrong-sign cell -> KILL", r["passed"] is False, r["kill"]))

    # every held-out stack present but only two subjects would be impossible with
    # the real set, so check the subject clause directly with a synthetic set.
    r = S.b6_rollup([cell(st, i) for st in ("bee-1", "bee-2", "bee-3",
                                            "wrapped-text-1", "wrapped-text-2", "bee-1")
                     for i in range(4)])
    checks.append(("6 stack-slots but only 2 subjects -> KILL", r["passed"] is False, r["kill"]))

    bad = 0
    for name, ok, kill in checks:
        print(f"   {'PASS' if ok else 'FAIL':4s}  {name}")
        if kill:
            print(f"          kill: {kill}")
        bad += 0 if ok else 1
    print(f"\n   -> {len(checks) - bad}/{len(checks)} property assertions hold")
    if bad:
        raise SystemExit(f"{bad} property assertion(s) FAILED")


if __name__ == "__main__":
    main()
