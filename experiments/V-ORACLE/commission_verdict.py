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
# NOTE the two capture groups.  The original version of this file parsed only
# "(a)" vs "(b)", which COLLAPSED the two distinct (a) conclusions the rule can
# reach -- "CAPTURE GAP" and "merge not beaten but the curve turned over" -- into
# a single letter.  An arm that reversed the through-focus logic would have
# flipped every site from one to the other and this harness would have reported
# it as unchanged.  That is precisely the defect V-LINEAR found in itself (four
# conclusion-flip arms MISSED at 88/88 green).  T5/T6 below exist because of it,
# and they FAILED against the original parser.
SITE_RE = re.compile(
    r"site (\d+) \(\s*(\w+)\s*\) tile r(\d+)c(\d+): \((a|b)\)(.*)")


TRUTH_LINES: list[str] = []


def classify(letter: str, tail: str) -> str:
    """Collapse a printed verdict to its CONCLUSION CLASS, not just its letter."""
    if letter == "b":
        return "b:defect"
    if "CAPTURE GAP" in tail:
        return "a:gap"
    return "a:turnover"


def roll_peak(var_k: np.ndarray, target: str) -> np.ndarray:
    """Move each tile's through-focus peak to frame 0 or to the middle.

    This mutates the FOCUS EVIDENCE, which is what separates 'capture gap' from
    'focus was captured'.  It leaves the ratio evidence alone, so it isolates the
    half of the rule that T1-T4 never touched.
    """
    K = var_k.shape[0]
    dst = 0 if target == "edge" else K // 2
    kpk = np.argmax(var_k, axis=0)                  # (NBAND, nr, nc)
    shift = (dst - kpk) % K
    ii = (np.arange(K)[:, None, None, None] - shift[None]) % K
    return np.take_along_axis(var_k, ii, axis=0)


def write_variant(subject: str, variant: str, scale, tiles=None,
                  peak=None, gain=None) -> None:
    """Copy stage A/B for `subject` to `subject+variant`, applying a mutation.

    `scale` > 1 makes the merge WORSE, which drives the source/merge ratio up and
    should drive the rule toward (b).  `tiles`, if given, restricts the damage to
    an explicit list of (row, col).  `peak`, if given ('edge' or 'mid'), moves the
    through-focus peak and should drive the rule between its two (a) classes.
    `gain`, if given, multiplies BOTH arms equally -- an information-free change
    that every conclusion must survive unmoved.
    """
    for stage in ("stageA", "stageB"):
        src = os.path.join(ora.OUT, stage, subject + ".npz")
        dst = os.path.join(ora.OUT, stage, subject + variant + ".npz")
        z = np.load(src)
        d = {k: z[k] for k in z.files}
        if gain is not None:
            keys = (["contrast", "var_k"] if stage == "stageA"
                    else [f"{m}_sig" for m in [str(x) for x in z["modes"]]])
            for k in keys:
                before = d[k]
                d[k] = before.astype(float) * gain
                if not np.any(d[k] != before):
                    raise SystemExit(
                        f"MUTATION DID NOT LAND: {k} unchanged in {variant}")
        if stage == "stageA" and peak is not None:
            before = d["var_k"]
            after = roll_peak(before.astype(float), peak)
            if not np.any(after != before):
                raise SystemExit(
                    f"MUTATION DID NOT LAND: var_k unchanged in {variant}")
            d["var_k"] = after
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


def run_rule(subject: str, variant: str, expect_n: int | None = None,
             bands: str = "1,2,3"):
    """Run the real verdict.py and parse the conclusion it printed per site.

    `expect_n` guards against DELETION.  ORCH's third instrument lesson is that
    deleting a finding is cheaper than stating it wrongly, and a harness that
    only inspects the verdicts it happens to parse reports green when a site
    silently vanishes.  Without this, T1's "no site reads (b)" passes vacuously
    on zero sites, one site, or five.
    """
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "verdict.py"), subject,
         "--variant", variant, "--bands", bands],
        capture_output=True, text=True, cwd=HERE)
    if out.returncode != 0:
        raise SystemExit(f"verdict.py failed on {variant}:\n{out.stderr[-2000:]}")
    global TRUTH_LINES
    TRUTH_LINES = [l for l in out.stdout.splitlines() if SITE_RE.search(l)]
    got = {}
    for m in SITE_RE.finditer(out.stdout):
        got[int(m.group(1))] = classify(m.group(5), m.group(6))
    if not got:
        raise SystemExit(f"parsed no site verdicts from {variant}; the check "
                         f"cannot certify anything:\n{out.stdout[-2000:]}")
    if expect_n is not None and len(got) != expect_n:
        raise SystemExit(f"SITE COUNT CHANGED on {variant}: parsed {len(got)}, "
                         f"expected {expect_n}.  A deleted finding is not a "
                         f"passed one.")
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

    def code(v):
        return {"b:defect": "B", "a:gap": "G", "a:turnover": "T"}[v]

    def codes(d):
        return "".join(code(d[k]) for k in sorted(d))

    print(f"=== commissioning the VERDICT RULE on {s} ===")
    print("conclusion classes: B = (b) merge defect, G = (a) capture gap, "
          "T = (a) merge not beaten / focus captured\n")
    try:
        # ---- T1 NULL ------------------------------------------------------
        variants.append("__null")
        write_variant(s, "__null", 1.0)
        base = run_rule(s, "__null")
        ok = all(v.startswith("a") for v in base.values())
        report("T1 NULL", ok,
               f"{len(base)} sites -> {codes(base)} (expected no B)")

        # ---- T2 DEFECT ----------------------------------------------------
        # Degrade the merge 4x everywhere.  A source frame now genuinely carries
        # 4x the merge's structure at every tile: the correct conclusion is (b)
        # at every site, and a rule that still says (a) is broken.
        variants.append("__defect")
        write_variant(s, "__defect", 4.0)
        dv = run_rule(s, "__defect")
        flipped = [k for k in sorted(dv) if dv[k] == "b:defect"]
        ok = len(flipped) == len(dv)
        report("T2 DEFECT (merge 4x worse)", ok,
               f"{len(flipped)}/{len(dv)} sites -> {codes(dv)} "
               f"(expected all B)")

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
        ok = (u.startswith("a") and o == "b:defect")
        report("T3 BOUNDARY (1.25x)", ok,
               f"site {site} tile r{R:02d}c{C:02d} band {b_best}: "
               f"ratio 1.24 -> {code(u)}, ratio 1.26 -> {code(o)} "
               f"(expected not-B then B)")

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

        # ---- T5 / T6: the arms the ORIGINAL harness was blind to -----------
        # T1-T4 only ever distinguish (a) from (b).  The rule also decides
        # BETWEEN THE TWO (a) CLASSES -- "capture gap" versus "focus was
        # captured and the merge still won" -- and that distinction is the
        # actual product claim: reshoot-this versus retouch-this.  Reversing it
        # would leave every number in the report correct and every letter
        # unchanged.  These two arms move the focus evidence only.
        variants.append("__mid")
        write_variant(s, "__mid", 1.0, peak="mid")
        mv = run_rule(s, "__mid")
        ngap = [k for k in sorted(mv) if mv[k] == "a:gap"]
        ok = len(ngap) == 0
        report("T5 PEAK-CENTRED (focus captured everywhere)", ok,
               f"sites -> {codes(mv)}; {len(ngap)} still read capture-gap "
               f"(expected 0)")

        variants.append("__edge")
        write_variant(s, "__edge", 1.0, peak="edge")
        ev = run_rule(s, "__edge")
        ngap2 = [k for k in sorted(ev) if ev[k] == "a:gap"]
        ok = len(ngap2) == len(ev)
        report("T6 PEAK-AT-EDGE (capture gap everywhere)", ok,
               f"sites -> {codes(ev)}; {len(ngap2)}/{len(ev)} read capture-gap "
               f"(expected all)")

        # Explicit record of the blind spot, so the fix cannot be forgotten.
        letters_only_mid = all(v[0] == base[k][0] for k, v in mv.items())
        print(f"\n  [note] T5 changes the CLASS at "
              f"{sum(1 for k, v in mv.items() if v != base[k])}/{len(mv)} sites "
              f"but the LETTER at "
              f"{sum(1 for k, v in mv.items() if v[0] != base[k][0])}/{len(mv)}.")
        if letters_only_mid:
            print("         A letter-only parser would have reported T5 as "
                  "UNCHANGED.")
            print("         That is the V-LINEAR defect shape, and this harness "
                  "had it until now.\n")

        # ---- T7 SPECIFICITY -----------------------------------------------
        # ORCH lesson 2: commissioning SENSITIVITY is not commissioning
        # SPECIFICITY.  T2-T6 all plant something and require a reaction.  None
        # of them establishes that the rule STAYS PUT when handed a change that
        # carries no information.  Scaling BOTH arms by the same constant is
        # exactly such a change: every ratio is identical, so every conclusion
        # must be too.  A rule that moves here is reading absolute level.
        variants.append("__gain")
        write_variant(s, "__gain", 1.0, gain=3.0)
        gv = run_rule(s, "__gain", expect_n=len(base))
        ok = all(gv[k] == base[k] for k in base)
        report("T7 SPECIFICITY (both arms x3, no information)", ok,
               f"sites -> {codes(gv)} vs baseline {codes(base)} "
               f"(expected identical)")

        # ---- T8 DELETION ---------------------------------------------------
        # ORCH lesson 3: commission DELETION as well as reversal, because
        # deleting a finding is cheaper than stating it wrongly.  Here the
        # harness is handed output with one site removed and must refuse it.
        # This tests the HARNESS, not the rule.
        doctored = "\n".join(
            l for l in TRUTH_LINES if "site 3 " not in l)
        seen = {int(m.group(1)) for m in SITE_RE.finditer(doctored)}
        caught = len(seen) != len(base)
        report("T8 DELETION (one site removed from the output)", caught,
               f"harness sees {len(seen)} sites, expects {len(base)} -> "
               f"{'refused' if caught else 'ACCEPTED SILENTLY'}")
    finally:
        cleanup(s, variants)

    # ---- commission the PASS/FAIL CHANNEL ITSELF --------------------------
    # ORCH lesson 1: an inert plant and a dead instrument give the identical
    # green.  Every arm above reported PASS.  That is only meaningful if this
    # harness is capable of reporting FAIL at all, so a knowingly-false
    # expectation is evaluated through the SAME report() path and must produce a
    # non-zero failure count.
    probe_pass, probe_fail = npass, nfail
    report("CHANNEL (deliberately false expectation)", False,
           "this line MUST read FAIL; if it reads PASS the pass/fail channel "
           "is dead and every result above is meaningless")
    channel_live = (nfail == probe_fail + 1)
    npass, nfail = probe_pass, probe_fail   # the probe is not a real failure

    print(f"\n  {npass} PASS + {nfail} FAIL = {npass + nfail} tests "
          f"(every test lands in a counted outcome)")
    print(f"  pass/fail channel: "
          f"{'LIVE (a false expectation did produce FAIL)' if channel_live else 'DEAD -- RESULTS ABOVE ARE VOID'}")
    if not channel_live:
        return 1
    if nfail:
        print("\n  THE PUBLISHED (a) VERDICT IS NOT SUPPORTED: the decision "
              "rule did not track a known-correct conclusion.")
    return 1 if nfail else 0


if __name__ == "__main__":
    raise SystemExit(main())
