#!/usr/bin/env python3
"""
V-EYES: independent re-check of restore.rs's no-ringing claim.

THE CLAIM UNDER TEST
--------------------
`crates/strehl-core/src/restore.rs` lines 87-88:

    //! largest profile change anywhere is **0.0035 of the step**, and there is
    //! no ringing to see. It does not ring because it is too weak to ring.

ORCH asked for this to be re-checked by someone who did not write it, on the
grounds that "a filter strong enough to help is strong enough to ring, and
those are the same knob." That is the right instinct and it is the reason this
check exists: the A/B showed a REAL gain on coffee-bubbles (2-D peak 1.6682,
band-weighted energy +19%), so the antecedent of the module's own argument --
that the filter is too weak -- is exactly what is no longer obviously true.

WHY THIS IS MEASURED ON DELIVERED PIXELS AND NOT A SYNTHETIC STEP
------------------------------------------------------------------
The module's own number comes from its self-test. Repeating a self-test is not
an independent check; it re-runs the same code path with the same assumptions
about which edge, which plane and which gain. This measures the two REAL
rendered masters -- same subject, same binary, same command line, one switch
apart -- and finds its edges in the picture rather than constructing them.

That is a strictly harder test in one specific way that matters: a real edge
carries the demosaic, the gather and the merge on top of the restoration, and
ringing that the module's isolated `restore_plane` self-test cannot see because
it never runs those stages is visible here.

HOW AN EDGE IS FOUND, AND WHY THE APPROACH MUST BE FLAT
-------------------------------------------------------
"Overshoot" is only meaningful if the signal was flat before the edge; on a
textured approach any excursion is indistinguishable from detail the filter was
supposed to restore. So candidate edges are required to have

    * a large monotone step across a short run (a genuine edge, not a ramp),
    * both approaches FLAT -- residual std below a stated fraction of the step,
    * and enough clear run either side to see a ring if one exists.

Sites are ranked by step size and the flattest are taken. The number kept, the
flatness threshold and the run length are all printed, because an overshoot
statistic computed over a hand-chosen edge set is worth nothing.

WHAT IS REPORTED
----------------
For each edge, the largest excursion beyond the local plateau on each side, as
a fraction of the step, in BOTH arms. The plain arm is not assumed to be
ring-free -- it is measured, because the gather and demosaic have their own
overshoot and attributing theirs to the restoration would be the same error in
the opposite direction. The reported number for the restoration is the
DIFFERENCE, plain -> restored.

COMMISSIONING
-------------
Two planted arms, because a ringing detector that has only ever seen real data
cannot distinguish "no ringing" from "cannot see ringing":

  PLANTED RING  a known unsharp-mask overshoot is added to the plain arm at a
                stated amplitude; the detector must report it, and must report
                it as roughly the planted amplitude.
  PLANTED NULL  the plain arm compared against itself; the detector must report
                ~0 and anything else is a noise floor that bounds the real
                reading from below.

Usage:
    python ringing_check.py <subject> [--edges N]
"""
import argparse
import hashlib
import pathlib
import sys

import cv2
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from softness_verdict3 import luma_linear   # noqa: E402

AB = pathlib.Path(r"C:\dev\strehl-out\V-EYES\restore-ab")

RUN = 12          # clear pixels required either side of the edge
EDGE = 4          # pixels the transition itself is allowed to occupy
FLAT = 0.06       # approach std must be under this fraction of the step
MIN_STEP = 2000.0  # DN; a real edge, not a gradient


def find_edges(a, want, rng):
    """Horizontal edges with flat approaches on both sides."""
    h, w = a.shape
    half = RUN + EDGE // 2
    cands = []
    ys = rng.choice(h, size=min(h, 4000), replace=False)
    for y in ys:
        row = a[y]
        # coarse: where does the row move fastest?
        d = np.abs(row[EDGE:] - row[:-EDGE])
        xs = np.argsort(d)[::-1][:12]
        for x0 in xs:
            x = int(x0) + EDGE // 2
            if x - half < 0 or x + half >= w:
                continue
            left = row[x - half:x - EDGE // 2]
            right = row[x + EDGE // 2 + 1:x + half + 1]
            if len(left) < RUN or len(right) < RUN:
                continue
            step = abs(float(right.mean()) - float(left.mean()))
            if step < MIN_STEP:
                continue
            # flat approach: detrend each side and require small residual
            def flat(v):
                t = np.arange(len(v))
                k = np.polyfit(t, v, 1)
                return float(np.std(v - np.polyval(k, t)))
            if flat(left) > FLAT * step or flat(right) > FLAT * step:
                continue
            cands.append((step, int(y), x))
    cands.sort(reverse=True)
    # de-duplicate: no two edges from the same neighbourhood
    keep, seen = [], set()
    for step, y, x in cands:
        k = (y // 32, x // 32)
        if k in seen:
            continue
        seen.add(k)
        keep.append((step, y, x))
        if len(keep) >= want:
            break
    return keep


def excursion(row, x, step):
    """Largest excursion beyond each plateau, as a fraction of the step.

    The plateau level is taken from the FAR half of each approach. The near
    half is where a ring would live, so it must not be allowed to define the
    level it is then measured against -- that is how an overshoot detector
    talks itself into reading zero.
    """
    half = RUN + EDGE // 2
    left = row[x - half:x - EDGE // 2]
    right = row[x + EDGE // 2 + 1:x + half + 1]
    lo = float(left[:RUN // 2].mean())
    hi = float(right[-RUN // 2:].mean())
    if hi >= lo:
        # rising edge: overshoot is above the high plateau, undershoot below the low
        over = (float(right.max()) - hi) / step
        under = (lo - float(left.min())) / step
    else:
        # falling edge: the roles of the two sides swap
        over = (float(left.max()) - lo) / step
        under = (hi - float(right.min())) / step
    return max(over, 0.0), max(under, 0.0)


def score(A, B, edges, label):
    """Report the DELTA distribution, not just its maximum.

    A max over 200 edges is an order statistic and it is the noisiest summary
    available. The module's claim is about "the largest profile change
    anywhere", so the max has to be reported -- but quoting it alone would
    misrepresent a filter whose typical edge is untouched. Percentiles say
    which of those two pictures is true.
    """
    dov, dun, absov = [], [], []
    for step, y, x in edges:
        oa, ua = excursion(A[y], x, step)
        ob, ub = excursion(B[y], x, step)
        absov.append(ob)
        dov.append(ob - oa)
        dun.append(ub - ua)
    d = np.maximum(np.array(dov), np.array(dun))
    q = np.percentile(d, [50, 90, 99])
    print(f"  {label}")
    print(f"    delta excursion  P50 {q[0]:+.4f}  P90 {q[1]:+.4f}  "
          f"P99 {q[2]:+.4f}  MAX {d.max():+.4f}")
    print(f"    edges above the published 0.0035: "
          f"{int((d > 0.0035).sum())}/{len(d)} ({100 * (d > 0.0035).mean():.1f}%)")
    print(f"    absolute overshoot in this arm   P50 {np.median(absov):.4f}  "
          f"MAX {max(absov):.4f}")
    return float(d.max()), float(q[0]), float((d > 0.0035).mean())


def stratify(A, B, edges):
    """Separate RINGING from amplified NOISE, which the delta conflates.

    These are different defects and the distinction decides which claim is
    being falsified. Ringing is a property of the filter's step response: it
    scales WITH the step, so measured as a fraction of the step it is flat in
    step size. Amplified noise is a fixed number of DN regardless of the edge
    it sits next to, so as a fraction of the step it falls as 1/step.

    Fitting log(delta) against log(step) therefore separates them by slope:

        slope ~  0   ->  ringing (fraction of step is scale-free)
        slope ~ -1   ->  noise   (a constant DN excursion, divided by the step)

    This only works where the step sizes span a real range. coffee-bubbles'
    edges are all near full scale, so the test is uninformative there and is
    reported as such rather than fitted to a 1.1x span and believed.
    """
    steps = np.array([e[0] for e in edges], float)
    d = []
    for step, y, x in edges:
        oa, ua = excursion(A[y], x, step)
        ob, ub = excursion(B[y], x, step)
        d.append(max(ob - oa, ub - ua))
    d = np.array(d)
    span = steps.max() / steps.min()
    print(f"\n  RINGING-vs-NOISE, step span {span:.1f}x")
    if span < 3.0:
        print("    step sizes too narrow to separate; test not run")
        return None
    m = d > 0
    if m.sum() < 20:
        print(f"    only {int(m.sum())} edges with a positive delta; test not run")
        return None
    k = np.polyfit(np.log(steps[m]), np.log(d[m]), 1)
    print(f"    log-log slope {k[0]:+.2f}   (0 = ringing, -1 = amplified noise)")
    # the same thing without a fit, so the verdict does not rest on one line
    lo = steps < np.median(steps)
    print(f"    delta as fraction of step:  small edges (med {np.median(steps[lo]):.0f} DN) "
          f"P50 {np.median(d[lo]):.4f}")
    print(f"                                large edges (med {np.median(steps[~lo]):.0f} DN) "
          f"P50 {np.median(d[~lo]):.4f}")
    print(f"    delta in ABSOLUTE DN:       small {np.median(d[lo] * steps[lo]):.0f}  "
          f"large {np.median(d[~lo] * steps[~lo]):.0f}")
    return float(k[0])


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest().upper()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("subject")
    p.add_argument("--edges", type=int, default=200)
    # The cap is in the filename because restore_ab.py now tags renders by cap,
    # after finding that a shared "MASTER-restore.tiff" name would have served
    # a cached render from a DIFFERENT cap to the absurd-cap potency probe.
    p.add_argument("--cap", default="1.7")
    a = p.parse_args()

    pa = AB / a.subject / "MASTER-plain.tiff"
    pb = AB / a.subject / f"MASTER-restore-{a.cap}.tiff"
    for q in (pa, pb):
        if not q.exists():
            print(f"missing {q}")
            return 1
    print(f"A {pa.name}  sha {sha256(pa)[:16]}")
    print(f"B {pb.name}  sha {sha256(pb)[:16]}")
    A = luma_linear(tifffile.imread(str(pa))).astype(np.float64)
    B = luma_linear(tifffile.imread(str(pb))).astype(np.float64)

    rng = np.random.default_rng(3)
    edges = find_edges(A, a.edges, rng)
    print(f"{a.subject}: {len(edges)} hard edges with flat approaches")
    print(f"  criteria: step >= {MIN_STEP:.0f} DN, approach std < {FLAT:.0%} of step, "
          f"{RUN} px clear run, {EDGE} px transition")
    if len(edges) < 20:
        print("  too few edges to conclude")
        return 2
    steps = [e[0] for e in edges]
    print(f"  step size: median {np.median(steps):.0f} DN, "
          f"range {min(steps):.0f}-{max(steps):.0f} DN\n")

    print("MEASURED")
    real, real_med, real_frac = score(A, B, edges, "restored vs plain")
    slope = stratify(A, B, edges)

    print("\nCOMMISSIONING")
    # NULL: plain against itself. Must read ~0.
    nul, _, _ = score(A, A, edges, "planted NULL (A vs A)")
    # RING: known unsharp overshoots planted on the plain arm, two amplitudes,
    # so the detector has to be monotone in amplitude and not merely non-zero.
    seen = []
    for k in (0.25, 0.63):
        blur = cv2.GaussianBlur(A.astype(np.float32), (0, 0), 2.0).astype(np.float64)
        P = A + k * (A - blur)
        m, _, _ = score(A, P, edges, f"planted RING k={k:.2f}")
        seen.append(m)
    ok = nul < 1e-9 and seen[0] > 10 * max(nul, 1e-12) and seen[1] > seen[0]
    print(f"  commissioning: null {nul:.6f}, ring {seen[0]:.4f} -> {seen[1]:.4f} "
          f"-> {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("  detector not commissioned; no verdict issued")
        return 2

    print("\nVERDICT")
    print(f"  null floor (detector noise)      {nul:.4f} of step")
    print(f"  restoration, typical edge (P50)  {real_med:+.4f} of step")
    print(f"  restoration, worst of {len(edges)} edges  {real:+.4f} of step")
    print(f"  fraction of edges over 0.0035    {100 * real_frac:.1f}%")
    print(f"  module's published claim         0.0035 of step")
    if real <= 0.0035:
        print("  -> claim HOLDS, including at the worst edge measured")
    elif real_med <= 0.0035:
        print(f"  -> claim holds at the TYPICAL edge and FAILS in the tail: "
              f"the worst edge exceeds it by x{real / 0.0035:.1f}")
    else:
        print(f"  -> claim FAILS even at the typical edge, by x{real_med / 0.0035:.1f}")
    if slope is not None:
        if slope < -0.6:
            print(f"  -> but the slope {slope:+.2f} says this is amplified NOISE, "
                  f"not ringing: a fixed DN excursion divided by the step")
        elif slope > -0.3:
            print(f"  -> the slope {slope:+.2f} says this IS ringing: "
                  f"scale-free in the step, as a step response must be")
        else:
            print(f"  -> slope {slope:+.2f} is between the two mechanisms; "
                  f"both are present and neither is cleanly separated")
    return 0


if __name__ == "__main__":
    sys.exit(main())

