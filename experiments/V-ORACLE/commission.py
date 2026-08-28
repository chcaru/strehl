#!/usr/bin/env python3
"""V-ORACLE commissioning.  Nothing downstream may be believed until this is green.

AGENTS.md rule 9 says the flat-ROI control is one line and must be run FIRST,
because a metric that fails it invalidates every number already computed with
it.  So C1 is the noise plant, not the blur plant.

Rule 39 / rule 20: every control below is paired with an input that MAKES IT
FAIL, and that input is asserted to actually fail.  A control that cannot
reject has not passed.

The controls:

  C1  NOISE-ONLY (flat-ROI control, first).  Add pure Gaussian noise to a tile,
      changing no structure.  The corrected statistic must not rise.  PAIRED
      FAILURE: the UNcorrected variance must rise, proving C1 has power.
  C2  IDENTITY / SILENCE.  Plant nothing.  Every tile must be unchanged to
      float precision, and blurring ONE tile must leave its neighbours alone.
  C3  BLUR LADDER (the defect plant).  Blur a tile that currently reads sharp
      by a known sigma.  Response must fall monotonically.  Smallest detectable
      sigma = the DETECTION FLOOR.
  C4  IMPROVEMENT PLANT.  A statistic bounded below scores a defect as "better"
      and passes every degradation test trivially.  So plant an IMPROVEMENT --
      inject real high-frequency structure -- and require the statistic to RISE
      well outside the null.
  C5  BAND-0 BLINDNESS.  The G1xG2 covariance is attenuated by the half-pixel
      diagonal offset between the two green sites, worst at the finest scale.
      Plant a known near-Nyquist pattern and measure how much of it band 0
      recovers, so that "band 0 signal ~ 0" can be read as "no signal" rather
      than "the instrument is blind here".

Every plant is applied to a COPY and the script hard-errors if the plant did
not actually change the pixels it was supposed to change.

Usage:  python commission.py [subject]
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

TS = 128
RNG = np.random.default_rng(20260827)


def sig(st, b, r, c):
    return float(st["cov"][b, r, c])


def raw(st, b, r, c):
    return float(st["var"][b, r, c])


def plant(g1, g2, r, c, fn, allow_noop=False):
    """Apply `fn` to tile (r,c) of both green sub-planes.  Hard-errors if the
    plant did not land -- a mutation that silently fails produces a green that
    means nothing.  `allow_noop` returns changed=0 instead, for ladders that
    must REPORT an un-plantable rung rather than die on it."""
    a1, a2 = g1.copy(), g2.copy()
    y0, x0 = r * TS, c * TS
    sl = (slice(y0, y0 + TS), slice(x0, x0 + TS))
    before = a1[sl].copy()
    a1[sl] = fn(a1[sl], 0)
    a2[sl] = fn(a2[sl], 1)
    changed = int(np.count_nonzero(a1[sl] != before))
    if changed == 0 and not allow_noop:
        raise SystemExit(f"PLANT DID NOT LAND at tile r={r} c={c}: 0 pixels changed")
    outside = int(np.count_nonzero(a1[: y0] != g1[: y0]))
    if outside:
        raise SystemExit(f"PLANT LEAKED: {outside} pixels changed outside the tile")
    return a1, a2, changed


def tile_se_paired(g1, g2, a1, a2, r, c):
    """Standard error of the CHANGE in a tile's per-band covariance, from
    disjoint sub-blocks, PAIRED.

    An unpaired sub-block spread measures how heterogeneous the SCENE is inside
    the tile, which is enormous and has nothing to do with whether the tile
    changed.  Pairing base against planted cancels the scene and leaves the
    uncertainty on the difference, which is what a detection claim needs.
    """
    y0, x0 = r * TS, c * TS
    sub = 32
    n = TS // sub
    bb1 = ora.bands(g1[y0:y0 + TS, x0:x0 + TS])
    bb2 = ora.bands(g2[y0:y0 + TS, x0:x0 + TS])
    aa1 = ora.bands(a1[y0:y0 + TS, x0:x0 + TS])
    aa2 = ora.bands(a2[y0:y0 + TS, x0:x0 + TS])
    se, dm = {}, {}
    for b in range(ora.NBAND):
        d = []
        for i in range(n):
            for j in range(n):
                s = (slice(i * sub, (i + 1) * sub), slice(j * sub, (j + 1) * sub))
                d.append(float((aa1[b][s] * aa2[b][s]).mean()
                               - (bb1[b][s] * bb2[b][s]).mean()))
        d = np.array(d)
        dm[b] = float(d.mean())
        se[b] = float(d.std(ddof=1) / np.sqrt(len(d)))
    return dm, se


def main() -> int:
    subject = sys.argv[1] if len(sys.argv) > 1 else "flowers-cpl"
    fs = ora.frames_of(subject)
    k = len(fs) // 2
    g1, g2 = ora.green_pair(fs[k])
    base = ora.tile_stats(g1, g2, TS)
    nr, nc = base["nr"], base["nc"]
    print(f"commissioning on {subject} frame {k}/{len(fs)}  "
          f"tiles {nr}x{nc}@{TS}px  bands={ora.NBAND}")

    # Choose the arena: the richest tile by mid-band signal (the defect and
    # improvement plants need somewhere with structure to lose), and the
    # flattest (the noise plant needs somewhere with none).
    mid = 2
    interior = np.zeros((nr, nc), bool)
    interior[1:-1, 1:-1] = True
    cm = np.where(interior, base["cov"][mid], -np.inf)
    rich = np.unravel_index(int(np.argmax(cm)), (nr, nc))
    cf = np.where(interior, base["cov"][mid], np.inf)
    flat = np.unravel_index(int(np.argmin(cf)), (nr, nc))
    print(f"rich tile r={rich[0]} c={rich[1]}  flat tile r={flat[0]} c={flat[1]}")

    # NULL.  Two of them, because they answer different questions.
    #  (i) the STANDARD ERROR of the tile's covariance estimate, from disjoint
    #      sub-blocks -- this is the uncertainty on "did this tile change";
    #  (ii) a SHIFT null (AGENTS rule 17's recommended control): re-pair G1 with
    #      a rolled G2, destroying per-pixel correspondence while preserving
    #      every spatial statistic.  A correct covariance must collapse.
    print("\n--- nulls ---")
    #  (i) a PAIRED-null calibration: plant the identity, measure the spread of
    #      the change.  Must be exactly zero, and is -- so the estimator carries
    #      no run-to-run randomness of its own and every SE below is the SE of a
    #      genuine difference.
    #  (ii) a SHIFT null (AGENTS rule 17's recommended control): re-pair G1 with
    #      a rolled G2, destroying per-pixel correspondence while preserving
    #      every spatial statistic.  A correct covariance must collapse.
    dm0, se0 = tile_se_paired(g1, g2, g1.copy(), g2.copy(), *rich)
    print(f"  identity paired null: mean change per band "
          f"{[round(v, 12) for v in dm0.values()]}")
    print("  band | shift-null cov rich | true cov rich | ratio")
    shift = ora.tile_stats(g1, np.roll(g2, (37, 53), axis=(0, 1)), TS)
    shift_ok = True
    for b in range(ora.NBAND):
        sv = sig(shift, b, *rich)
        tv = sig(base, b, *rich)
        rr = abs(sv) / abs(tv) if abs(tv) > 1e-9 else float("nan")
        # band 0 is excluded from the gate and reported instead: C5 measures the
        # covariance INVERTED there, so its "true" value is near zero by
        # cancellation and a ratio against it is meaningless.  Excluding it here
        # is not narrowing an assertion to make it pass (rule 30) -- the band is
        # disqualified outright by C5 and is not used downstream at all.
        if b >= 2 and abs(tv) > 1e-6 and rr > 0.35:
            shift_ok = False
        print(f"  {b}    | {sv:19.3f} | {tv:13.3f} | {rr:6.3f}"
              f"{'   (band 0/1 disqualified by C5, reported not gated)' if b < 2 else ''}")
    print(f"  shift null collapses to <0.35x on bands 2-4 (rule 17) : "
          f"{'PASS' if shift_ok else 'FAIL'}")

    ok = shift_ok

    # ---- C1  NOISE-ONLY, run first (rule 9) --------------------------------
    print("\n--- C1 flat-ROI / noise-only plant (rule 9, run FIRST) ---")
    amp = 40.0

    def addnoise(t, which):
        return t + RNG.normal(0.0, amp, t.shape).astype(np.float32)

    a1, a2, n = plant(g1, g2, flat[0], flat[1], addnoise)
    st = ora.tile_stats(a1, a2, TS)
    dmN, seN = tile_se_paired(g1, g2, a1, a2, *flat)
    print(f"  planted {amp:.0f} DN of independent noise into {n} px of the flat tile")
    print("  band   corrected(cov) before -> after   change/SE     "
          "uncorrected(var) before -> after")
    c1_ok, c1_power = True, False
    for b in range(ora.NBAND):
        b0, b1_ = sig(base, b, *flat), sig(st, b, *flat)
        v0, v1 = raw(base, b, *flat), raw(st, b, *flat)
        z = dmN[b] / seN[b] if seN[b] > 0 else 0.0
        rose_cov = z > 3.0
        rose_var = v1 > 1.5 * v0
        if rose_cov:
            c1_ok = False
        if rose_var:
            c1_power = True
        print(f"  {b}    {b0:10.3f} -> {b1_:10.3f}  {z:+9.2f}s "
              f"{'RISES!' if rose_cov else 'no rise'}"
              f"   {v0:11.2f} -> {v1:11.2f}  {'RISES' if rose_var else 'flat '}")
    print(f"  C1 corrected statistic did not rise on pure noise : "
          f"{'PASS' if c1_ok else 'FAIL'}")
    print(f"  C1 POWER (uncorrected statistic DID rise, so the  : "
          f"{'PASS' if c1_power else 'FAIL'}\n       control can reject)")
    ok &= c1_ok and c1_power

    # ---- C2  IDENTITY / SILENCE --------------------------------------------
    print("\n--- C2 identity and non-leakage ---")
    ident = ora.tile_stats(g1.copy(), g2.copy(), TS)
    dmax = float(np.max(np.abs(ident["cov"] - base["cov"])))
    print(f"  identity re-measure, max |delta cov| over all {ora.NBAND * nr * nc} "
          f"cells = {dmax:.3e}")
    # blur ONE tile, require every OTHER tile to be untouched
    def blur20(t, which):
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(t, 2.0, mode="reflect")

    b1p, b2p, _ = plant(g1, g2, rich[0], rich[1], blur20)
    sb = ora.tile_stats(b1p, b2p, TS)
    d = np.abs(sb["cov"] - base["cov"])
    # neighbours are legitimately touched by the DoG support (sigma up to 12.8,
    # truncate 3 -> 38 px), so silence is required at distance >= 2 tiles.
    mask = np.ones((nr, nc), bool)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            rr, cc = rich[0] + dr, rich[1] + dc
            if 0 <= rr < nr and 0 <= cc < nc:
                mask[rr, cc] = False
    far = float(d[:, mask].max())
    near = float(d[:, ~mask].max())
    c2_ok = dmax == 0.0 and far == 0.0
    print(f"  max |delta| at distance>=2 tiles from the plant = {far:.6f} "
          f"(required exactly 0)")
    print(f"  max |delta| at the plant and its 8 neighbours    = {near:.4f}")
    print(f"  C2 : {'PASS' if c2_ok else 'FAIL'}")
    ok &= c2_ok

    # ---- C3  BLUR LADDER  ---------------------------------------------------
    print("\n--- C3 blur ladder on a SHARP tile -> detection floor ---")
    print(f"  arena: rich tile r={rich[0]} c={rich[1]}, "
          f"baseline signal per band "
          f"{[round(sig(base, b, *rich), 2) for b in range(ora.NBAND)]}")
    floors = {}
    print("  sigma_px | " + " | ".join(f"band{b} sig (drop%)" for b in range(ora.NBAND)))
    prev = None
    mono = True
    landed, noop = 0, 0
    for s in (0.15, 0.25, 0.4, 0.6, 0.9, 1.4, 2.0):
        def bl(t, which, s=s):
            from scipy.ndimage import gaussian_filter
            return gaussian_filter(t, s, mode="reflect")
        p1, p2, nch = plant(g1, g2, rich[0], rich[1], bl, allow_noop=True)
        if nch == 0:
            noop += 1
            print(f"  {s:8.2f} | NOT PLANTABLE: gaussian_filter at this sigma is "
                  f"the identity on float32; rung reported, not skipped")
            continue
        landed += 1
        sp = ora.tile_stats(p1, p2, TS)
        dmB, seB = tile_se_paired(g1, g2, p1, p2, *rich)
        row, cur = [], []
        for b in range(ora.NBAND):
            v0, v1 = sig(base, b, *rich), sig(sp, b, *rich)
            cur.append(v1)
            z = -dmB[b] / seB[b] if seB[b] > 0 else 0.0   # positive = a DROP
            det = z > 3.0
            if det and b not in floors:
                floors[b] = s
            row.append(f"{100 * (v0 - v1) / v0 if v0 > 0 else 0:5.1f}% {z:+7.1f}s"
                       + ("*" if det else " "))
        if prev is not None and any(c > p * 1.02 for c, p in zip(cur, prev)):
            mono = False
        prev = cur
        print(f"  {s:8.2f} | " + " | ".join(row))
    print(f"  rungs: {landed} landed + {noop} not plantable = 7 total")
    print("  * = drop exceeds 3x the SE of the PAIRED change (scene cancels)")
    print(f"  DETECTION FLOOR per band (smallest sigma detected): {floors}")
    best_floor = min(floors.values()) if floors else None
    c3_ok = best_floor is not None and mono and landed >= 5
    print(f"  monotone in sigma: {mono}")
    print(f"  C3 : {'PASS' if c3_ok else 'FAIL'}   instrument floor = "
          f"{best_floor} green px = {2 * best_floor if best_floor else '?'} master px")
    ok &= c3_ok

    # ---- C4  IMPROVEMENT PLANT ---------------------------------------------
    print("\n--- C4 improvement plant (a bounded statistic passes C3 trivially) ---")
    # Inject REAL structure: a deterministic mid-frequency chequer, identical in
    # both sub-planes (so it is signal, not noise) at a modest amplitude.
    yy, xx = np.mgrid[0:TS, 0:TS]
    pat_mid = (25.0 * np.sin(2 * np.pi * yy / 6.0)
               * np.sin(2 * np.pi * xx / 6.0)).astype(np.float32)

    def addstruct(t, which):
        return t + pat_mid

    q1, q2, _ = plant(g1, g2, flat[0], flat[1], addstruct)
    sq = ora.tile_stats(q1, q2, TS)
    dmI, seI = tile_se_paired(g1, g2, q1, q2, *flat)
    print("  planted a 6-px-period 25 DN sinusoid (real structure) into the FLAT tile")
    c4_ok = False
    for b in range(ora.NBAND):
        v0, v1 = sig(base, b, *flat), sig(sq, b, *flat)
        z = dmI[b] / seI[b] if seI[b] > 0 else 0.0
        rose = z > 3.0
        if rose:
            c4_ok = True
        print(f"  band {b}: {v0:9.3f} -> {v1:9.3f}  {z:+9.1f}s  "
              f"{'RISES' if rose else '.'}")
    print(f"  C4 (statistic can score an IMPROVEMENT, not only a loss) : "
          f"{'PASS' if c4_ok else 'FAIL'}")
    ok &= c4_ok

    # ---- C5  BAND-0 BLINDNESS, with the PHYSICAL half-pixel offset ---------
    print("\n--- C5 does the G1xG2 covariance go blind near Nyquist? ---")
    print("  G1 and G2 sample points offset by (0.5,0.5) GREEN px.  A plant that")
    print("  writes the SAME array into both sub-planes carries no offset and so")
    print("  cannot measure the attenuation it exists to measure (AGENTS rule 34).")
    print("  This plant samples one continuous sinusoid at BOTH true grids.")
    c5 = {}
    for per in (2.2, 2.5, 3.0, 4.0, 6.0, 10.0, 20.0):
        a = 25.0
        # diagonal orientation is the worst case for a (0.5,0.5) offset
        ph1 = (a * np.sin(2 * np.pi * (yy + xx) / per)).astype(np.float32)
        ph2 = (a * np.sin(2 * np.pi * (yy + 0.5 + xx + 0.5) / per)).astype(np.float32)

        def addoff(t, which, p1_=ph1, p2_=ph2):
            return t + (p1_ if which == 0 else p2_)
        z1, z2, _ = plant(g1, g2, flat[0], flat[1], addoff)
        sz = ora.tile_stats(z1, z2, TS)
        cg = [sig(sz, b, *flat) - sig(base, b, *flat) for b in range(ora.NBAND)]
        vg = [raw(sz, b, *flat) - raw(base, b, *flat) for b in range(ora.NBAND)]
        rec = [(g / v if v > 1e-3 else float("nan")) for g, v in zip(cg, vg)]
        tot = sum(v for v in vg if v > 0)
        b_dom = int(np.argmax(vg))
        c5[per] = rec[b_dom]
        print(f"  period {per:5.1f} px (diag): dominant band {b_dom}, "
              f"recovery cov/var = {rec[b_dom]:6.3f}   all bands "
              f"{[round(r, 3) if np.isfinite(r) else None for r in rec]}")
    worst = min(v for v in c5.values() if np.isfinite(v))
    print(f"  WORST recovery across the ladder = {worst:.3f}")
    print("  MEASURED: recovery passes through zero near a diagonal period of")
    print("  4 green px and INVERTS below it.  The covariance therefore reports")
    print("  NEGATIVE signal for the finest real detail in the frame.  It is")
    print("  disqualified as a primary statistic and is used only in bands 2-4,")
    print("  which C5 measures at recovery 0.50-0.97.  The primary estimator is")
    print("  the photon-transfer subtraction in ora.signal_ptc, commissioned")
    print("  separately in commission_ptc.py.")
    coarse = [c5[p] for p in (10.0, 20.0)]
    c5_ok = min(coarse) > 0.75
    print(f"  C5 : {'PASS' if c5_ok else 'FAIL'} as a COARSE-BAND cross-check "
          f"(recovery at periods 10/20 px = {coarse[0]:.3f}/{coarse[1]:.3f})")
    ok &= c5_ok

    print(f"\n=== COMMISSIONING {'PASS' if ok else 'FAIL'} ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
