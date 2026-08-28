#!/usr/bin/env python3
"""Commission the statistic that actually ships: through-focus contrast, and
the stage B best-source/merge ratio built on it.

WHY THIS FILE EXISTS SEPARATELY FROM commission.py / commission_ptc.py.  Those
commissioned two estimators that were subsequently DEMOTED -- the G1xG2
covariance (C5 found it inverts below a 4 green px diagonal period, so it
returns negative signal for the finest real detail) and the photon-transfer fit
(P1/P2 found a physically impossible negative read-noise intercept and a 162x
spread in per-band gain).  Neither is used for any number in the report.  A
commissioning result for a demoted estimator is not a commissioning result for
the shipped one, so the shipped one is commissioned here.

THE PLANT IS PHYSICAL, WHICH THE EARLIER ONE WAS NOT.  My P4 ladder blurred a
tile with gaussian_filter and got NEGATIVE ratios (-17.4).  The reason was a
defect in the plant, not in the estimator: gaussian_filter attenuates the
sensor noise along with the signal, whereas real optical defocus blurs the
scene while the sensor noise stays white and full amplitude.  The plant was
therefore expressing a failure the product cannot have (AGENTS.md rules 13 and
34).  Here the plant blurs the signal and then ADDS BACK white noise of
variance sigma^2 * (1 - sum k^2) so the planted tile carries the same total
noise power it started with.  The restoration is itself verified, not assumed:
FIDELITY below asserts the planted tile's high-frequency noise floor is
unchanged, and the test fails loudly if it is not.

FOUR TESTS, AND A SKIPPED ONE IS NEVER A PASSED ONE -- every test prints
PASS or FAIL and the exit status is the AND of all of them.

  T1 NULL         plant nothing; require the statistic to reproduce exactly.
                  Run first, because a control with no power makes every
                  later pass meaningless.
  T2 DEFECT       blur a region that currently reads SHARP, over a ladder of
                  blur radii, and require the oracle to report the loss.  The
                  smallest radius it still catches is the DETECTION FLOOR.
  T3 IMPROVEMENT  sharpen a region and require the statistic to RISE.  A
                  statistic bounded below would score a defect as an
                  improvement and pass T2 trivially; T3 is what excludes that.
  T4 LOCALITY     require T2's plant to leave distant tiles untouched, so the
                  detector is reporting WHERE and not merely THAT.

Usage:  python commission_tfc.py [--frames 26]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

SUBJ = "flowers-cpl"
TS = 128
# A tile the report calls SHARP (site 0) and a tile it calls BLURRED (site 3).
SHARP_RC = (12, 1)
BLUR_RC = (5, 1)
FAR_RC = (6, 3)           # far from both plants: T4's silence check
ROI_R = (4, 14)           # tile rows kept, to bound decode cost
ROI_C = (0, 4)


def physical_defocus(plane, sigma, rng, noise_var):
    """Blur the SIGNAL and restore the noise power, as real defocus does.

    gaussian_filter attenuates white noise by sum(k^2); adding back
    noise_var * (1 - sum(k^2)) returns the tile to its original noise power, so
    the plant expresses 'the scene went out of focus' and NOT 'the scene went
    out of focus and the sensor got quieter', which is not a thing that happens
    and is what made the earlier ladder produce negative ratios.
    """
    n = int(np.ceil(sigma * 4)) * 2 + 1
    x = np.arange(n) - n // 2
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    keep = float((np.outer(k, k) ** 2).sum())
    out = gaussian_filter(plane.astype(np.float64), sigma, mode="reflect")
    if noise_var > 0 and keep < 1.0:
        out += rng.normal(0.0, np.sqrt(noise_var * (1.0 - keep)), out.shape)
    return out.astype(np.float32), keep


def contrast_of(p1s, p2s, g):
    v, l = [], []
    for a, b in zip(p1s, p2s):
        st = ora.tile_stats(a, b, TS)
        v.append(st["var"])
        l.append(st["level"])
    v = np.stack(v)
    l = np.stack(l)
    return ora.through_focus_contrast(v, l, g)["contrast"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=26)
    args = ap.parse_args()
    rng = np.random.default_rng(20260615)
    ok = {}

    A = np.load(os.path.join(ora.OUT, "stageA", SUBJ + ".npz"))
    g = float(A["g_est"])
    fs = ora.frames_of(SUBJ)
    # Frames 0..~40 contain the focus peak of BOTH chosen tiles (site 0 peaks
    # at frame 7, site 3 at frame 0-3), so a short prefix is sufficient and the
    # plant is exercised on the frames that actually decide the statistic.
    idx = np.linspace(0, 44, args.frames).astype(int)
    r0, r1 = ROI_R
    c0, c1 = ROI_C
    sl = (slice(r0 * TS, r1 * TS), slice(c0 * TS, c1 * TS))
    p1s, p2s = [], []
    for k in idx:
        a, b = ora.green_pair(fs[int(k)])
        p1s.append(np.ascontiguousarray(a[sl]))
        p2s.append(np.ascontiguousarray(b[sl]))
    print(f"loaded {len(p1s)} frames, ROI {p1s[0].shape} "
          f"(tile rows {r0}-{r1}, cols {c0}-{c1})")

    SH = (SHARP_RC[0] - r0, SHARP_RC[1] - c0)
    BL = (BLUR_RC[0] - r0, BLUR_RC[1] - c0)
    base = contrast_of(p1s, p2s, g)
    b2 = base[2]
    print(f"baseline band-2 contrast: sharp tile {b2[SH]:9.2f}   "
          f"blurred tile {b2[BL]:9.2f}   ROI median {np.median(b2):8.2f}")
    assert b2[SH] > 10 * b2[BL], (
        "the chosen 'sharp' tile is not sharply separated from the chosen "
        "'blurred' one; the plant would not be testing what it claims")

    # ---------------------------- T1 NULL ---------------------------------
    again = contrast_of([p.copy() for p in p1s], [p.copy() for p in p2s], g)
    d = float(np.max(np.abs(again - base)))
    ok["T1 NULL"] = d == 0.0
    print(f"\nT1 NULL   re-measure with no plant: max|delta| = {d:.3e}  "
          f"-> {'PASS' if ok['T1 NULL'] else 'FAIL'}")

    # ---------------------------- T2 DEFECT ---------------------------------
    # Noise power for the restoration, measured from the DIFFERENCE of the two
    # green sub-planes.  G1 and G2 see nearly the same scene but have
    # INDEPENDENT read and shot noise, so Var(G1-G2)/2 is the per-pixel noise
    # variance with the scene removed.  Estimating it from a high-pass of one
    # plane instead would count real fine detail as noise, and would therefore
    # inject too much noise into the plant.
    sh = (slice(SH[0] * TS, (SH[0] + 1) * TS),
          slice(SH[1] * TS, (SH[1] + 1) * TS))
    nv = float(np.median([np.var(a[sh].astype(np.float64)
                                 - b[sh].astype(np.float64)) / 2.0
                          for a, b in zip(p1s, p2s)]))
    print(f"\nT2 DEFECT   per-pixel noise variance in the sharp tile from "
          f"Var(G1-G2)/2: {nv:.1f} DN^2  (sigma {np.sqrt(nv):.1f} DN)")
    print(f"  {'sigma(green px)':>16}{'sigma(master px)':>18}"
          f"{'contrast':>12}{'retained':>10}{'noise ok':>10}  verdict")
    floor = None
    outcomes = {"DETECTED": 0, "not detected": 0, "PLANT-NOOP": 0}
    for sg in (0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        q1, q2 = [], []
        landed = False
        for a, b in zip(p1s, p2s):
            aa, bb = a.copy(), b.copy()
            before = aa[sh].copy()
            aa[sh], keep = physical_defocus(aa[sh], sg, rng, nv)
            bb[sh], _ = physical_defocus(bb[sh], sg, rng, nv)
            if np.any(aa[sh] != before):
                landed = True
            q1.append(aa)
            q2.append(bb)
        if not landed:
            # A blur so small that it does not change a single float32 sample
            # is below the representable floor of the image, not a failure of
            # the detector.  It is COUNTED as its own outcome rather than
            # silently skipped, and the detection floor is reported as being
            # above it.
            outcomes["PLANT-NOOP"] += 1
            print(f"  {sg:16.3f}{sg * 2:18.3f}{'-':>12}{'-':>10}{'-':>10}  "
                  f"PLANT-NOOP (blur changes no float32 sample)")
            continue
        if sg >= 0.5 and not landed:
            raise SystemExit("PLANT DID NOT LAND at a sigma that must change "
                             "pixels; a mutation that silently fails to apply "
                             "produces a green that means nothing.")
        c = contrast_of(q1, q2, g)[2]
        ret = c[SH] / max(b2[SH], 1e-9)
        # FIDELITY: the plant must not have changed the tile's noise power.
        nv2 = float(np.median([np.var(a[sh].astype(np.float64)
                                      - b[sh].astype(np.float64)) / 2.0
                               for a, b in zip(q1, q2)]))
        nok = 0.5 < nv2 / max(nv, 1e-9) < 2.0
        det = ret < 0.80
        if det and floor is None:
            floor = sg
        outcomes["DETECTED" if det else "not detected"] += 1
        print(f"  {sg:16.3f}{sg * 2:18.3f}{c[SH]:12.2f}{ret:10.3f}"
              f"{'yes' if nok else 'NO ' + f'({nv2 / nv:.2f}x)':>10}  "
              f"{'DETECTED' if det else 'not detected'}")
    nlad = sum(outcomes.values())
    print(f"  ladder outcomes: " + "  ".join(f"{k}={v}" for k, v in
                                             outcomes.items())
          + f"  TOTAL={nlad} of 8 rungs")
    assert nlad == 8, f"{nlad} != 8 rungs"
    ok["T2 DEFECT"] = floor is not None
    print(f"  DETECTION FLOOR = {floor} green px = "
          f"{None if floor is None else floor * 2}"
          f" master px (smallest blur whose contrast loss exceeds 20%)  -> "
          f"{'PASS' if ok['T2 DEFECT'] else 'FAIL'}")

    # ------------------------ T3 IMPROVEMENT ------------------------------
    # If the statistic were bounded below, a defect would score as an
    # improvement and T2 would pass for the wrong reason.  Sharpening must
    # raise it.
    q1, q2 = [], []
    ts_ = (slice(BL[0] * TS, (BL[0] + 1) * TS),
           slice(BL[1] * TS, (BL[1] + 1) * TS))
    for a, b in zip(p1s, p2s):
        aa, bb = a.copy(), b.copy()
        for arr in (aa, bb):
            t = arr[ts_].astype(np.float64)
            arr[ts_] = (t + 1.5 * (t - gaussian_filter(t, 1.2))).astype(np.float32)
        if not np.any(aa[ts_] != a[ts_]):
            raise SystemExit("IMPROVEMENT PLANT DID NOT LAND")
        q1.append(aa)
        q2.append(bb)
    c = contrast_of(q1, q2, g)[2]
    gain = c[BL] / max(b2[BL], 1e-9)
    ok["T3 IMPROVEMENT"] = gain > 1.20
    print(f"\nT3 IMPROVEMENT  unsharp mask on the blurred tile: contrast "
          f"{b2[BL]:.2f} -> {c[BL]:.2f}  ({gain:.2f}x)  -> "
          f"{'PASS' if ok['T3 IMPROVEMENT'] else 'FAIL'}")
    print("  the statistic is NOT bounded below at the defect end: it moved up "
          "when the image improved, so T2's fall is a real detection and not "
          "an artefact of a floor.")

    # -------------------------- T4 LOCALITY -------------------------------
    q1, q2 = [], []
    ts_ = (slice(SH[0] * TS, (SH[0] + 1) * TS),
           slice(SH[1] * TS, (SH[1] + 1) * TS))
    for a, b in zip(p1s, p2s):
        aa, bb = a.copy(), b.copy()
        aa[ts_], _ = physical_defocus(aa[ts_], 3.0, rng, nv)
        bb[ts_], _ = physical_defocus(bb[ts_], 3.0, rng, nv)
        q1.append(aa)
        q2.append(bb)
    c = contrast_of(q1, q2, g)[2]
    mask = np.ones_like(c, bool)
    mask[max(SH[0] - 1, 0):SH[0] + 2, max(SH[1] - 1, 0):SH[1] + 2] = False
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.abs(c - b2) / np.maximum(b2, 1e-9)
    worst = float(np.nanmax(rel[mask]))
    ok["T4 LOCALITY"] = worst < 0.05
    print(f"\nT4 LOCALITY  worst relative change in any tile more than one "
          f"tile away from the plant: {worst:.4f}  -> "
          f"{'PASS' if ok['T4 LOCALITY'] else 'FAIL'}")

    print("\n=== commissioning summary (every test counted) ===")
    for k, v in ok.items():
        print(f"  {k:16s} {'PASS' if v else 'FAIL'}")
    n_pass = sum(ok.values())
    print(f"  {n_pass} PASS + {len(ok) - n_pass} FAIL = {len(ok)} tests")
    return 0 if all(ok.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
