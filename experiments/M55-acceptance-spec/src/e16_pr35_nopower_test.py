"""M55b E16 -- PR35 property test for the NO-POWER amendment to b6_rollup.

PRE-REGISTERED as PR35 in the session store BEFORE the amendment was written and
before this file existed.  Four observables, all four decided here except the
inertness one, which is decided by a full calibrate.py re-run.

The deciding observable is OBSERVABLE 2: discipline 403 permits amending a
pre-registered spec only if the amendment can ONLY TIGHTEN.  Removing cells from
a denominator is normally a LOOSENING, so this is a real risk and not a formality.
It is tested against the actual pre-amendment code, extracted from git, not
against a paraphrase of it.

Rule 39: every claim here is paired with a planted wrong answer, and the planted
answer must be shown PASSING the old code, or the test has no power.
No corpus data is read.

FIRST-RUN DISCLOSURE (rule 39, kept deliberately).  The first execution of this
file failed 3 of 12 assertions, and all three were defects in the PLANTS, not in
the amendment: both planted wrong answers were placed inside `coffee-bean`, which
is one stack and four cells, so two damaged cells read 50% for that subject and
the PRE-EXISTING per-subject clause rejected them before the new clause could be
reached.  A plant that an older clause already catches proves nothing about a new
one.  The plants were moved into `bee` (three stacks, twelve cells, 11/12 = 91.7%,
which the old code accepts) and the |z| ladder was changed to vary within a stack
rather than across stacks, so that a `bee` cell can be placed in the lowest-|z|
third.  The amendment was not touched.  See section 12 of the report.
"""
import os, subprocess, sys, random

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import spec_v1 as S

OLD_SHA = "54a8305"          # the last commit before the PR35 amendment
OLD_PATH = os.path.join(os.environ.get("TEMP", HERE), "m55b_spec_v0_frozen.py")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def load_old():
    """The pre-amendment b6_rollup, from git.  Not a paraphrase."""
    src = subprocess.run(
        ["git", "show", f"{OLD_SHA}:experiments/M55-acceptance-spec/src/spec_v1.py"],
        cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert "b6_strata" not in src, "OLD_SHA already contains the amendment"
    with open(OLD_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    import importlib.util
    spec = importlib.util.spec_from_file_location("spec_v0", OLD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cell(stack, roi, z=9.0, powered=True, passed=True, wrong=False, declare_z=True):
    c = dict(ref=1.0, test=0.9, d=0.1, status="Ok", status_test="Ok", z=z,
             detected=passed, wrong_sign=wrong, passed=passed,
             stack=stack, roi=roi)
    if declare_z:
        c["z_pass"] = powered
    return c


def build(n_unpowered=0, n_fail=0, one_subject=False, n_wrong=0, zmode="varied"):
    """24 cells over the real held-out set: 6 stacks x 4 ROIs, 3 subjects."""
    cells = []
    for si, st in enumerate(S.HELD_OUT):
        for i in range(S.TH["b6_min_rois"]):
            k = si * 4 + i
            z = (4.0 + 0.7 * (i * 6 + si)) if zmode == "varied" else 9.0
            cells.append(cell(st, i, z=z))
    order = list(range(24))
    if one_subject:                       # concentrate damage in the 'bee' subject
        order = [k for k, c in enumerate(cells) if S.SUBJECT_OF[c["stack"]] == "bee"] + \
                [k for k, c in enumerate(cells) if S.SUBJECT_OF[c["stack"]] != "bee"]
    for k in order[:n_unpowered]:
        cells[k]["z_pass"] = False
        cells[k]["passed"] = False        # exactly what b6_cell computes: detected AND z_pass
    for k in order[n_unpowered:n_unpowered + n_fail]:
        cells[k]["passed"] = False
        cells[k]["detected"] = False
    for k in order[n_unpowered + n_fail:n_unpowered + n_fail + n_wrong]:
        cells[k]["wrong_sign"] = True
    return cells


def main():
    V0 = load_old()
    print("=" * 78)
    print("M55b E16 -- PR35: NO-POWER, CANNOT-ACCEPT and the low-|z| stratum")
    print("=" * 78)
    print(f"  old code from git {OLD_SHA}, new code from the working tree.")
    print("  No corpus data is read.\n")
    checks = []

    # ---------------------------------------------------------------- OBS 2
    print("  OBSERVABLE 2 -- strict tightening, exhaustive over 64 configurations")
    print("  falsifier: ANY configuration ACCEPTed by the new code that the old rejected")
    newly_accepted, newly_blocked, unchanged, rows = [], 0, 0, []
    for nu in range(4):
        for nf in range(4):
            for one in (False, True):
                for nw in range(2):
                    cs = build(nu, nf, one, nw)
                    old = V0.b6_rollup([dict(c) for c in cs])
                    new = S.b6_rollup([dict(c) for c in cs])
                    tag = f"unpowered={nu} fail={nf} one_subject={one} wrong={nw}"
                    if new["verdict"] == "ACCEPT" and not old["passed"]:
                        newly_accepted.append((tag, old["kill"]))
                    if old["passed"] and new["verdict"] != "ACCEPT":
                        newly_blocked += 1
                        rows.append((tag, new["verdict"], new["kill"]))
                    if old["passed"] == (new["verdict"] == "ACCEPT"):
                        unchanged += 1
    print(f"     configurations tested            64")
    print(f"     NEWLY ACCEPTED (must be 0)       {len(newly_accepted)}")
    print(f"     newly blocked or rejected        {newly_blocked}")
    print(f"     verdict unchanged                {unchanged}")
    for tag, v, k in rows[:6]:
        print(f"        {tag:52s} -> {v}")
    checks.append(("OBS2: no configuration is newly ACCEPTed (strictly tightening)",
                   len(newly_accepted) == 0,
                   "; ".join(t for t, _ in newly_accepted[:3])))
    checks.append(("OBS2: the amendment is not inert -- it blocks at least one case "
                   "the old code accepted", newly_blocked > 0, ""))

    # ---------------------------------------------------------------- OBS 3
    print("\n  OBSERVABLE 3 -- planted wrong answer: 1 NO-POWER cell in `bee`, pooled 95.8%")
    cs = build(n_unpowered=1, n_fail=0, one_subject=True, n_wrong=0)
    old, new = V0.b6_rollup([dict(c) for c in cs]), S.b6_rollup([dict(c) for c in cs])
    print(f"     old code: passed={old['passed']}  pooled {100*old['frac_passed']:.1f}%"
          f"  kill={old['kill']}")
    print(f"     new code: verdict={new['verdict']}  n_no_power={new['n_no_power']}"
          f"  powered {new['n_powered']}  blocked={new['blocked']}")
    checks.append(("OBS3: the planted answer PASSES the old code (the test has power)",
                   old["passed"] is True, ""))
    checks.append(("OBS3: the planted answer is CANNOT-ACCEPT under the new code",
                   new["verdict"] == "CANNOT-ACCEPT", new["kill"]))
    checks.append(("OBS3: CANNOT-ACCEPT is not REJECT and not ACCEPT",
                   new["verdict"] not in ("ACCEPT", "REJECT") and new["passed"] is False, ""))

    # ---------------------------------------------------------------- OBS 4
    print("\n  OBSERVABLE 4 -- planted wrong answer: 90%+ overall, failures in the")
    print("                  lowest-|z| third.  Must not be ACCEPTed.")
    cs = build()                                   # 24 powered cells
    bee = [k for k, c in enumerate(cs) if S.SUBJECT_OF[c["stack"]] == "bee"]
    lo = sorted(bee, key=lambda k: cs[k]["z"])[:1]
    for k in lo:
        cs[k]["passed"] = False
        cs[k]["detected"] = False
    print(f"     the single failing cell is {cs[lo[0]]['stack']}[{cs[lo[0]]['roi']}]"
          f" at |z| = {cs[lo[0]]['z']:.1f}; its subject `bee` reads 11/12 = 91.7%")
    old, new = V0.b6_rollup([dict(c) for c in cs]), S.b6_rollup([dict(c) for c in cs])
    st = new["low_z_stratum"]
    print(f"     pooled {100*new['frac_passed']:.1f}% (gate {100*(1-S.TH['b6_quantile']):.0f}%)"
          f"   lowest stratum: {st['n']} cells, |z| <= {st['z_max']:.1f},"
          f" {100*st['frac_passed']:.0f}% pass")
    print(f"     old code: passed={old['passed']}   new code: verdict={new['verdict']}")
    print(f"     new kill: {new['kill']}")
    checks.append(("OBS4: the stratum plant PASSES the old code (the test has power)",
                   old["passed"] is True, old["kill"]))
    checks.append(("OBS4: the stratum plant is REJECTed by the new code",
                   new["verdict"] == "REJECT", new["kill"]))
    checks.append(("OBS4: the same two failures placed in the HIGHEST stratum are "
                   "tolerated by the 10% budget", True, ""))
    cs2 = build()
    hi = sorted(bee, key=lambda k: -cs2[k]["z"])[:1]
    for k in hi:
        cs2[k]["passed"] = False
        cs2[k]["detected"] = False
    new2 = S.b6_rollup([dict(c) for c in cs2])
    print(f"     control: the SAME one failure at the TOP of the |z| range -> {new2['verdict']}")
    checks[-1] = ("OBS4 control: the same single failure in the HIGHEST stratum -> "
                  "ACCEPT, so the stratum gate is about WHERE the failure is, not "
                  "how many there are", new2["verdict"] == "ACCEPT", new2["kill"])

    # ---------------------------------------------------------------- extras
    print("\n  ADDITIONAL PROPERTIES")
    cs = build()
    for c in cs:
        del c["z_pass"]
    r = S.b6_rollup(cs)
    checks.append(("a cell that does not declare z_pass blocks (B9 was not run)",
                   r["verdict"] == "CANNOT-ACCEPT", r["kill"]))

    clean = S.b6_rollup(build())
    checks.append(("a complete, powered, all-passing set is still ACCEPTed "
                   "(the battery is passable)", clean["verdict"] == "ACCEPT", clean["kill"]))

    rng = random.Random(11)
    base = build(n_unpowered=1, n_fail=2, one_subject=True, n_wrong=0)
    v0 = S.b6_rollup([dict(c) for c in base])
    same = True
    for _ in range(20):
        sh = [dict(c) for c in base]
        rng.shuffle(sh)
        r = S.b6_rollup(sh)
        same = same and (r["verdict"] == v0["verdict"] and r["kill"] == v0["kill"])
    checks.append(("the verdict and the kill string do not depend on the order the "
                   "cells are supplied in (20 shuffles)", same, ""))

    import itertools
    sole_pooled = 0
    for r in (1, 2, 3):
        for combo in itertools.combinations(range(24), r):
            cs3 = build()
            for k in combo:
                cs3[k]["passed"] = False
                cs3[k]["detected"] = False
            rr = S.b6_rollup([dict(c) for c in cs3])
            pooled_fail = rr["frac_passed"] < 1.0 - S.TH["b6_quantile"]
            subj_fail = "subject groups below" in (rr["kill"] or "")
            if pooled_fail and not subj_fail:
                sole_pooled += 1
    print(f"     {sole_pooled} of 2324 failure placements (1, 2 or 3 failing cells)"
          f" trip the pooled 90% gate WITHOUT tripping the per-subject gate")
    checks.append(("the pooled 90% gate is never the binding constraint at these "
                   "subject sizes -- the per-subject clause is strictly stronger",
                   sole_pooled == 0, f"{sole_pooled} placements"))

    deg = build(zmode="tied")
    r = S.b6_rollup(deg)
    checks.append(("with every |z| identical the stratum is DEGENERATE and is skipped, "
                   "not silently applied to an arbitrary third",
                   r["low_z_stratum"] is None and r["n_distinct_z"] == 1, ""))

    bad = 0
    print()
    for name, ok, detail in checks:
        print(f"   {'PASS' if ok else 'FAIL':4s}  {name}")
        if detail:
            print(f"          {detail}")
        bad += 0 if ok else 1
    print(f"\n   -> {len(checks) - bad}/{len(checks)} property assertions hold")
    if bad:
        raise SystemExit(f"{bad} property assertion(s) FAILED")


if __name__ == "__main__":
    main()
