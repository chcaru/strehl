"""Commission the VERDICT RULE, not the statistic.

commission_tfc.py commissions the sharpness statistic: plant a blur, require the
number to fall.  That is necessary and it is not sufficient.  The thing this lane
actually delivered is a *conclusion* -- "(a) capture gap, not our bug" -- and a
conclusion is produced by a decision rule sitting on top of the statistic.  A
decision rule that is structurally incapable of emitting (b) would print (a) on
every input, agree with the prior, and pass every test that only ever checks
numbers.  My whole result would be vacuous and nothing I had run would say so.

This is the same defect family the orchestrator flagged in V-NEVERWORSE's report
verifier: a check that tests for the PRESENCE of "refuted" survives the section's
verdict being flipped to "confirmed".  The remedy there and here is identical --
commission with a mutation that flips the CONCLUSION, not one that perturbs a
number, and pin each check to the specific claim it certifies.

So: feed verdict.py inputs whose correct conclusion is known in advance, by
mutating the merge arm, and require the printed verdict to follow.

  T1 NULL      unmutated             -> every site must read (a)
  T2 DEFECT    merge degraded 4x     -> every site must read (b)
  T3 BOUNDARY  merge degraded to sit  -> the rule must flip at its stated 1.25x
               either side of 1.25x      threshold and not somewhere else
  T4 LOCALITY  one site's tile only   -> only that site may flip; the rest silent

T2 is the test that matters.  If it fails, the (a) verdict this lane published is
an artefact of the rule and not a measurement of the data.

Mutations are numeric, but they carry the same hard-error requirement as a string
mutation anchored on a unique line: if the mutation does not actually change the
array, the test is not green, it is void.  Every mutation below asserts that it
landed before the rule is ever run.

Usage:  python commission_verdict.py [--subject flowers-cpl]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

import numpy as np

import ora

HERE = os.path.dirname(os.path.abspath(__file__))
SITE_RE = re.compile(r"site (\d+) \(\s*(\w+)\s*\) tile r(\d+)c(\d+): \((a|b)\)")


def write_variant(subject: str, variant: str, scale, tiles=None) -> None:
    """Copy stage A/B for `subject` to `subject+variant`, dividing the merge arm.

    `scale` > 1 makes the merge WORSE, which drives the source/merge ratio up and
    should drive the rule toward (b).  `tiles`, if given, restricts the damage to
    an explicit list of (row, col).
    """
    for stage in ("stageA", "stageB"):
        src = os.path.join(ora.OUT, stage, subject + ".npz")
        dst = os.path.join(ora.OUT, stage, subject + variant + ".npz")
        z = np.load(src)
        d = {k: z[k] for k in z.files}
        if stage == "stageB" and scale != 1.0:
            touched = 0
            for m in [str(x) for x in z["modes"]]:
                a = d[f"{m}_sig"].astype(float).copy()
                before = a.copy()
                if tiles is None:
                    a /= scale
                else:
                    for (r, c) in tiles:
                        a[:, r, c] /= scale
                # Hard-error if the mutation did not land.  A mutation that
                # silently fails to apply produces a green that means nothing.
                if not np.any(a != before):
                    raise SystemExit(
                        f"MUTATION DID NOT LAND: {m}_sig unchanged in {variant}")
                touched += int(np.sum(a != before))
                d[f"{m}_sig"] = a
            if touched == 0:
                raise SystemExit(f"MUTATION DID NOT LAND: {variant}")
        np.savez(dst, **d)


def run_rule(subject: str, variant: str):
    """Run the real verdict.py and parse the conclusion it printed per site."""
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "verdict.py"), subject,
         "--variant", variant],
        capture_output=True, text=True, cwd=HERE)
    if out.returncode != 0:
        raise SystemExit(f"verdict.py failed on {variant}:\n{out.stderr[-2000:]}")
    got = {}
    for m in SITE_RE.finditer(out.stdout):
        got[int(m.group(1))] = m.group(5)
    if not got:
        raise SystemExit(f"parsed no site verdicts from {variant}; the check "
                         f"cannot certify anything:\n{out.stdout[-2000:]}")
    return got


def cleanup(subject: str, variants) -> None:
    for v in variants:
        for stage in ("stageA", "stageB"):
            p = os.path.join(ora.OUT, stage, subject + v + ".npz")
            if os.path.exists(p):
                os.remove(p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="flowers-cpl")
    args = ap.parse_args()
    s = args.subject
    variants = []
    npass = nfail = 0

    def report(name, ok, detail):
        nonlocal npass, nfail
        if ok:
            npass += 1
        else:
            nfail += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    print(f"=== commissioning the VERDICT RULE on {s} ===\n")
    try:
        # ---- T1 NULL ------------------------------------------------------
        variants.append("__null")
        write_variant(s, "__null", 1.0)
        base = run_rule(s, "__null")
        ok = all(v == "a" for v in base.values())
        report("T1 NULL", ok,
               f"{len(base)} sites, verdicts "
               f"{''.join(base[k] for k in sorted(base))} (expected all 'a')")

        # ---- T2 DEFECT ----------------------------------------------------
        # Degrade the merge 4x everywhere.  A source frame now genuinely carries
        # 4x the merge's structure at every tile: the correct conclusion is (b)
        # at every site, and a rule that still says (a) is broken.
        variants.append("__defect")
        write_variant(s, "__defect", 4.0)
        dv = run_rule(s, "__defect")
        flipped = [k for k in sorted(dv) if dv[k] == "b"]
        ok = len(flipped) == len(dv)
        report("T2 DEFECT (merge 4x worse)", ok,
               f"{len(flipped)}/{len(dv)} sites now read (b) "
               f"{''.join(dv[k] for k in sorted(dv))} (expected all 'b')")

        # ---- T3 BOUNDARY --------------------------------------------------
        # The rule states a 1.25x threshold.  Drive one site's best band to sit
        # just under and just over it and require the flip to happen there, so
        # the published threshold is the one actually enforced.
        A = np.load(os.path.join(ora.OUT, "stageA", s + ".npz"))
        B = np.load(os.path.join(ora.OUT, "stageB", s + ".npz"))
        con, mrg = A["contrast"], B["point_sig"]
        import verdict as V
        site = 0
        my, mx, _ = V.FLOWERS_SITES[site]
        R, C = base and None, None
        # recover the tile verdict.py chose for site 0 from its own printed row
        out = subprocess.run(
            [sys.executable, os.path.join(HERE, "verdict.py"), s,
             "--variant", "__null"], capture_output=True, text=True, cwd=HERE)
        m = SITE_RE.search(out.stdout)
        R, C = int(m.group(3)), int(m.group(4))
        b_best = max((1, 2, 3), key=lambda b: con[b, R, C] / max(mrg[b, R, C], 1e-9))
        r_now = con[b_best, R, C] / max(mrg[b_best, R, C], 1e-9)
        lo, hi = 1.24 / r_now, 1.26 / r_now
        variants += ["__under", "__over"]
        write_variant(s, "__under", lo, tiles=[(R, C)])
        write_variant(s, "__over", hi, tiles=[(R, C)])
        u, o = run_rule(s, "__under")[site], run_rule(s, "__over")[site]
        ok = (u == "a" and o == "b")
        report("T3 BOUNDARY (1.25x)", ok,
               f"site {site} tile r{R:02d}c{C:02d} band {b_best}: "
               f"ratio 1.24 -> ({u}), ratio 1.26 -> ({o}) "
               f"(expected a then b)")

        # ---- T4 LOCALITY --------------------------------------------------
        # Damage exactly one site's tile.  Only that site may change verdict; a
        # rule that flips its neighbours is reading the wrong tile.
        variants.append("__local")
        write_variant(s, "__local", 8.0, tiles=[(R, C)])
        lv = run_rule(s, "__local")
        changed = [k for k in sorted(lv) if lv[k] != base.get(k)]
        ok = changed == [site]
        report("T4 LOCALITY", ok,
               f"sites whose verdict changed: {changed} (expected [{site}])")
    finally:
        cleanup(s, variants)

    print(f"\n  {npass} PASS + {nfail} FAIL = {npass + nfail} tests "
          f"(every test lands in a counted outcome)")
    if nfail:
        print("\n  THE PUBLISHED (a) VERDICT IS NOT SUPPORTED: the decision "
              "rule did not track a known-correct conclusion.")
    return 1 if nfail else 0


if __name__ == "__main__":
    raise SystemExit(main())
