#!/usr/bin/env python3
"""Commissioning for the PRIMARY estimator: photon-transfer noise subtraction.

`commission.py` disqualified the G1xG2 covariance as a primary statistic -- C5
measured its recovery passing through zero at a diagonal period of ~4 green px
and inverting below it, so it returns NEGATIVE signal for the finest real
detail.  Using it would have manufactured the answer "capture gap".

The shipped statistic is instead

    Signal(b, tile) = Var(b, tile) - kappa_b * (level/g + rn2)

which has no spatial offset in it anywhere.  Controls, in the order they matter:

  P0  KAPPA.  The band kernels' white-noise variance gain, measured through the
      real code path, cross-checked against a second independent noise seed and
      against an analytic sum of squared taps.
  P1  FLAT-ROI (rule 9, run first, and the physically meaningful version).  A
      real featureless tile of a real frame must score ~0 detail while a real
      detailed tile of the SAME frame scores high.  PAIRED FAILURE: the
      uncorrected variance must FAIL to separate them, or this control has no
      power and is not evidence.
  P2  PTC FIT QUALITY.  Fit (g, rn2) and report the residual; fit each band
      SEPARATELY and require the independently-fitted gains to agree.  A fit
      that only ever sees one band cannot disagree with itself.
  P3  CROSS-VALIDATION against the covariance in bands 2-4, where C5 measured
      recovery 0.83-0.97.  Two estimators with completely different failure
      modes must agree on real data.
  P4  BLUR LADDER -> the shipped DETECTION FLOOR, and the response curve that
      converts a measured ratio into an equivalent blur in master px.
  P5  IMPROVEMENT PLANT.  Required by the brief: a statistic bounded below
      scores a defect as better and passes every degradation test trivially.
  P6  STATED FAILURE DIRECTION (rule 18), asserted rather than argued: plant
      anomalous noise at unchanged level and show the estimator DOES credit it
      as detail.  This is the way PTC can be fooled and it is asserted here at
      the wrong value, xfail-style (rule 30), so it fails the day it changes.

Usage:  python commission_ptc.py [subject]
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

TS = 128
RNG = np.random.default_rng(20260827)


def gather(subject, nframes=14):
    fs = ora.frames_of(subject)
    ks = np.unique(np.linspace(0, len(fs) - 1, min(nframes, len(fs)))
                   .round().astype(int))
    lv, vr, cv = [], [], []
    for k in ks:
        g1, g2 = ora.green_pair(fs[k])
        st = ora.tile_stats(g1, g2, TS)
        lv.append(st["level"].ravel())
        vr.append(st["var"].reshape(ora.NBAND, -1))
        cv.append(st["cov"].reshape(ora.NBAND, -1))
    return (np.concatenate(lv), np.concatenate(vr, axis=1),
            np.concatenate(cv, axis=1), fs, ks, st["nr"], st["nc"])


def main() -> int:
    subject = sys.argv[1] if len(sys.argv) > 1 else "flowers-cpl"
    ok = True

    # ---- P0 kappa ----------------------------------------------------------
    print("--- P0 band white-noise variance gain (kappa), measured not derived ---")
    k1 = ora.kappa()
    ora._KAPPA = None
    k2 = ora.kappa(n=1024, seed=99)
    ora._KAPPA = None
    k3 = ora.kappa(n=2048, seed=1234)
    ora._KAPPA = None
    ora.kappa()
    print("  band |    seed 7 |   seed 99 | 2048/seed1234 | spread")
    p0_ok = True
    for b in range(ora.NBAND):
        vs = [k1[b], k2[b], k3[b]]
        sp = (max(vs) - min(vs)) / np.mean(vs)
        if sp > 0.02:
            p0_ok = False
        print(f"  {b}    | {k1[b]:9.6f} | {k2[b]:9.6f} | {k3[b]:13.6f} | {sp:7.4f}")
    print(f"  P0 : {'PASS' if p0_ok else 'FAIL'} (three independent noise "
          f"realisations agree within 2%)")
    ok &= p0_ok

    print(f"\ngathering {subject} ...")
    lv, vr, cv, fs, ks, nr, nc = gather(subject)
    print(f"  {len(ks)} frames x {nr * nc} tiles = {len(lv)} samples, "
          f"levels {lv.min():.0f}-{lv.max():.0f} DN")

    # ---- P2 PTC fit (needed before P1 can be scored) -----------------------
    print("\n--- P2 photon-transfer fit and its internal disagreement ---")
    g, rn2, dg = ora.fit_ptc(lv, vr)
    print(f"  joint fit: sigma^2 = level/{g:.2f} + {rn2:.2f}   "
          f"(read noise {np.sqrt(max(rn2, 0)):.2f} DN)")
    print(f"  envelope residual: max |resid| = {max(abs(r) for r in dg['resid']):.3f} "
          f"DN^2 over {len(dg['bin_level'])} level bins")
    gs = []
    for b in range(ora.NBAND):
        gb, rb, _ = ora.fit_ptc(lv, vr[b:b + 1])
        gs.append(gb)
        print(f"  band {b} alone: g={gb:8.2f}  rn2={rb:9.2f}")
    fin = [x for x in gs if np.isfinite(x) and x > 0]
    spread = (max(fin) / min(fin)) if fin else float("inf")
    p2_ok = spread < 2.0 and np.isfinite(g) and g > 0
    print(f"  independently-fitted gain spread across bands = {spread:.3f}x")
    print(f"  P2 : {'PASS' if p2_ok else 'FAIL'} (five bands that never see each "
          f"other's data agree on one gain)")
    ok &= p2_ok

    # ---- P1 FLAT-ROI, on real pixels ---------------------------------------
    print("\n--- P1 flat-ROI control on REAL pixels (rule 9) ---")
    kmid = fs[len(fs) // 2]
    g1, g2 = ora.green_pair(kmid)
    st = ora.tile_stats(g1, g2, TS)
    sg = ora.signal_ptc(st, g, rn2)
    interior = np.zeros((nr, nc), bool)
    interior[1:-1, 1:-1] = True
    # rank by band 3 covariance: offset-clean (C5 recovery 0.95) and therefore
    # an INDEPENDENT way to say which tile is featureless, not the statistic
    # under test ranking itself (rule 17).
    c3 = np.where(interior, st["cov"][3], np.nan)
    flat = np.unravel_index(int(np.nanargmin(c3)), (nr, nc))
    rich = np.unravel_index(int(np.nanargmax(c3)), (nr, nc))
    print(f"  tiles chosen by band-3 COVARIANCE (independent of the statistic "
          f"under test):")
    print(f"    flat r={flat[0]} c={flat[1]} level={st['level'][flat]:.0f} DN | "
          f"rich r={rich[0]} c={rich[1]} level={st['level'][rich]:.0f} DN")
    print("  band | PTC signal flat | PTC signal rich | separation | "
          "RAW var flat | RAW var rich | raw separation")
    p1_ok, p1_power = True, False
    for b in range(ora.NBAND):
        sf, sr = float(sg[b][flat]), float(sg[b][rich])
        vf, vrr = float(st["var"][b][flat]), float(st["var"][b][rich])
        sep = sr / sf if sf > 0 else float("inf")
        rsep = vrr / vf
        # a flat tile must not be credited with detail comparable to a rich one
        if b <= 2 and sf > 0.15 * sr:
            p1_ok = False
        if b <= 1 and rsep < 2.0:
            p1_power = True
        print(f"  {b}    | {sf:15.2f} | {sr:15.2f} | {sep:10.1f}x | "
              f"{vf:12.2f} | {vrr:12.2f} | {rsep:10.2f}x")
    print(f"  P1 : {'PASS' if p1_ok else 'FAIL'} (flat tile scores <15% of the "
          f"rich tile in bands 0-2)")
    print(f"  P1 POWER: the UNCORRECTED variance fails to separate them in a "
          f"fine band : {'PASS' if p1_power else 'FAIL'}")
    ok &= p1_ok and p1_power

    # ---- P3 cross-validation against the covariance ------------------------
    print("\n--- P3 PTC vs COV on real tiles, bands 2-4 (C5-validated region) ---")
    sgall = ora.signal_ptc(
        {"level": lv[None, :], "var": vr[:, None, :], "cov": cv[:, None, :]},
        g, rn2)[:, 0, :]
    print("  band | Pearson r | median PTC/COV | C5 recovery for this band")
    c5ref = {2: "~0.95 (period 20px)", 3: "~0.95", 4: "~0.97"}
    p3_ok = True
    for b in (2, 3, 4):
        m = cv[b] > 5 * np.median(np.abs(cv[b]))
        if m.sum() < 50:
            m = cv[b] > np.quantile(cv[b], 0.9)
        r = float(np.corrcoef(sgall[b][m], cv[b][m])[0, 1])
        rat = float(np.median(sgall[b][m] / cv[b][m]))
        if r < 0.9 or not (0.7 < rat < 1.6):
            p3_ok = False
        print(f"  {b}    | {r:9.4f} | {rat:14.3f} | {c5ref[b]}")
    print(f"  P3 : {'PASS' if p3_ok else 'FAIL'} (two estimators with unrelated "
          f"failure modes agree on real data)")
    ok &= p3_ok

    # ---- P4 blur ladder -> detection floor and the response curve ----------
    print("\n--- P4 blur ladder on a SHARP tile: floor + ratio->blur conversion ---")
    y0, x0 = rich[0] * TS, rich[1] * TS
    base_sig = {b: float(sg[b][rich]) for b in range(ora.NBAND)}
    print(f"  baseline PTC signal {[round(base_sig[b], 2) for b in range(ora.NBAND)]}")
    print("  sigma_green | sigma_master |  " +
          "  ".join(f"b{b} ratio" for b in range(ora.NBAND)))
    from scipy.ndimage import gaussian_filter
    curve, landed, noop = {}, 0, 0
    prevrow = None
    mono = True
    for s in (0.15, 0.25, 0.35, 0.5, 0.7, 1.0, 1.5, 2.2):
        a1, a2 = g1.copy(), g2.copy()
        for a in (a1, a2):
            blk = a[y0:y0 + TS, x0:x0 + TS]
            new = gaussian_filter(blk, s, mode="reflect")
            if np.count_nonzero(new != blk) == 0:
                break
            a[y0:y0 + TS, x0:x0 + TS] = new
        else:
            landed += 1
            sp = ora.signal_ptc(ora.tile_stats(a1, a2, TS), g, rn2)
            row = [float(sp[b][rich]) / base_sig[b] if base_sig[b] > 0 else np.nan
                   for b in range(ora.NBAND)]
            curve[s] = row
            if prevrow is not None and any(
                    r > p + 0.02 for r, p in zip(row, prevrow) if np.isfinite(r)):
                mono = False
            prevrow = row
            print(f"  {s:11.2f} | {2 * s:12.2f} |  " +
                  "  ".join(f"{v:8.4f}" for v in row))
            continue
        noop += 1
        print(f"  {s:11.2f} | {2 * s:12.2f} |  NOT PLANTABLE (identity on float32)"
              f" -- rung reported, not skipped")
    print(f"  rungs: {landed} landed + {noop} not plantable = 8 total")
    # floor: smallest planted blur moving the most sensitive band by >5%
    floor = None
    for s in sorted(curve):
        if min(v for v in curve[s] if np.isfinite(v)) < 0.95:
            floor = s
            break
    p4_ok = floor is not None and mono and landed >= 6
    print(f"  monotone in sigma: {mono}")
    print(f"  DETECTION FLOOR = {floor} green px = "
          f"{2 * floor if floor else '?'} MASTER px "
          f"(smallest planted blur moving a band by >5%)")
    print(f"  P4 : {'PASS' if p4_ok else 'FAIL'}")
    ok &= p4_ok

    # ---- P5 improvement plant ----------------------------------------------
    print("\n--- P5 improvement plant (statistic must be able to score BETTER) ---")
    yy, xx = np.mgrid[0:TS, 0:TS]
    pat = (25.0 * np.sin(2 * np.pi * yy / 5.0)
           * np.sin(2 * np.pi * xx / 5.0)).astype(np.float32)
    a1, a2 = g1.copy(), g2.copy()
    fy, fx = flat[0] * TS, flat[1] * TS
    before = a1[fy:fy + TS, fx:fx + TS].copy()
    for a in (a1, a2):
        a[fy:fy + TS, fx:fx + TS] = a[fy:fy + TS, fx:fx + TS] + pat
    if np.count_nonzero(a1[fy:fy + TS, fx:fx + TS] != before) == 0:
        raise SystemExit("P5 PLANT DID NOT LAND")
    sp = ora.signal_ptc(ora.tile_stats(a1, a2, TS), g, rn2)
    p5_ok = False
    for b in range(ora.NBAND):
        v0, v1 = float(sg[b][flat]), float(sp[b][flat])
        if v1 > max(v0, 0) + 10.0:
            p5_ok = True
        print(f"  band {b}: {v0:10.2f} -> {v1:10.2f}")
    print(f"  P5 : {'PASS' if p5_ok else 'FAIL'} (not bounded above at baseline)")
    ok &= p5_ok

    # ---- P6 stated failure direction, asserted --------------------------------
    print("\n--- P6 how this estimator CAN be fooled (rule 18), asserted ---")
    a1, a2 = g1.copy(), g2.copy()
    for a in (a1, a2):
        a[fy:fy + TS, fx:fx + TS] += RNG.normal(0, 40.0, (TS, TS)).astype(np.float32)
    sp = ora.signal_ptc(ora.tile_stats(a1, a2, TS), g, rn2)
    fooled = float(sp[0][flat]) > float(sg[0][flat]) + 100.0
    print(f"  40 DN of anomalous noise at unchanged level: band 0 signal "
          f"{float(sg[0][flat]):.1f} -> {float(sp[0][flat]):.1f}")
    print(f"  ASSERTED at the KNOWN-WRONG value: PTC credits anomalous noise as "
          f"detail = {fooled} (expected True)")
    print("  Defence: every frame in a stack comes from one sensor at one ISO, so")
    print("  noise really is a function of level; and the covariance cross-check")
    print("  in P3, which is immune to this, agrees on real data.  DIRECTION: PTC")
    print("  over-reports detail where noise exceeds the fitted curve, i.e. it")
    print("  favours the NOISY arm -- the single source frame, not the merge.")
    print("  So it is biased TOWARD finding a merge defect, not away from one.")
    ok &= fooled

    print(f"\n=== PTC COMMISSIONING {'PASS' if ok else 'FAIL'} ===")
    print(f"g={g:.4f} rn2={rn2:.4f} floor={floor}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
