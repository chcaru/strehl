"""M95 arm 13c -- the defocus null, because arm 13b's controls failed.

WHY THIS EXISTS. Arm 13b fitted an in-band noise floor against exposure level and
then failed two of its own three controls:

    Q3 negative (held-out flat tiles, should read 0)  S = +0.2506, bar 0.25  FAIL
    Q2 power    (plant S_true = 0.50)                 S = +0.6253, bar 0.12  FAIL
    Q2 power    (plant S_true = 0.90)                 S = +0.9250            PASS

By the bar I registered before running it, arm 13b's headline (S_detail = 0.1698,
"NOISE-DOMINATED") is VOID. It is reported void and is not quoted as a result.

THE FAILURE IS FULLY DIAGNOSTIC AND THAT IS WHY THIS ARM EXISTS. A single scalar
explains both numbers. If the true noise is c times the fitted floor, then a tile
that is pure noise reads S = 1 - 1/c, and a planted tile at S_true = 0.5 reads
1 - 1/(2c). Q3 gives c = 1/(1-0.2506) = 1.3341. That predicts Q2's 0.50 arm at
1 - 1/2.6682 = 0.6252 against the 0.6253 observed -- four significant figures. So
the model is right and the CALIBRATION is wrong, and the cause is identifiable:
"flattest by gradient variance" is a spatial-domain criterion that says nothing
about power at 0.30-0.48 cyc/px, so the calibration set was not the signal-free
set I assumed.

THE FIX IS TO STOP FITTING AND USE A PHYSICS-GUARANTEED NULL. This is a FOCUS
STACK. For any fixed tile position, the frames in which that position is far from
focus are low-passed by the defocus disc, whose cutoff is far below 0.30 cyc/px
once the disc is several pixels wide. Such a tile therefore holds sensor noise
and the demosaic's response to sensor noise, and essentially no subject detail,
at the SAME position, the SAME sensor, the SAME illumination and the SAME
demosaic as the in-focus frame. No fit, no sensor constant, no dark frame.

    P_focus   = band power at that position in the frame where it is sharpest
    P_defocus = band power at that position in the frame where it is softest
    S         = 1 - P_defocus * levelcorr / P_focus

levelcorr rescales the noise for the small exposure difference between the two
frames using arm 13b's own a + b*L. ARM 13B'S CALIBRATION BIAS CANNOT PROPAGATE
HERE: levelcorr is a RATIO of that function at two nearby levels, and a scalar
error c cancels exactly in a ratio. That is why the broken fit is still usable
for this one job and not for arm 13b's.

-------------------------------------------------------------------------------
PRE-REGISTERED BARS -- committed BEFORE this script was run.

N1  NULL. Between the two MOST defocused frames at the same position -- both
    signal-free by construction, so the true S is 0 -- the estimator must return
    median |S| <= 0.25. This is the control arm 13b failed, rebuilt on a pair
    that is null by physics rather than by my choice of criterion.

N2  POWER. Plant a zero-mean band-limited field into the ACTUAL PIXELS of the
    most-defocused tile at S_true = 0.50 and 0.90, then measure the planted
    tile's band power exactly as any other tile is measured, referenced to the
    second-most-defocused frame. Must recover each within +/- 0.12.
    The plant is a real image, not a constructed power value: arm 12's R3 taught
    me that a control which computes its own answer cannot fail.

N3  NON-DEGENERACY. The argmax-over-frames must not be one single frame for
    every position, or "sharpest frame" is not tracking focus at all. Require
    >= 4 distinct argmax frames across the 40 positions.

HEADLINE, S_detail, median over the 40 positions arm 8 selected:
    <= 0.20 -> the scoring band is NOISE-DOMINATED on the very tiles the
               +0.1160 dex was measured on; that number must never be quoted as
               sharpness without the rider.
    >= 0.50 -> the band carries real captured signal; the kernel gain is real
               sharpening and my published framing stands.
    between -> PARTIAL, stated as partial.

KNOWN LIMITATION, STATED BEFORE RUNNING. Magnification breathes across a focus
run, so a fixed pixel window does not track exactly the same scene point across
299 frames. That makes the defocused reference noisier, not biased: it cannot
manufacture in-band signal where the optics deliver none. N1 is the control that
would expose it if it did.

MY REGISTERED PREDICTION. PARTIAL, S_detail 0.35-0.65. Arm 13's part A found only
2.82% of this band inside the red/blue CFA Nyquist cell, which pushes down; but
these 40 positions are the sharpest in the frame and the optics still deliver
MTF 0.345 -> 0.056 across the band, which pushes up. My last two predictions were
both wrong, so this one is offered with no confidence at all.
-------------------------------------------------------------------------------
"""

import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np

from x2_pairs import BAND, TILE, IMAGES, load_luma, pick_tiles
from x11_bandsignal import band_power, band_limited_field, decode_dark as decode_rawpy

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

STACK = r"D:\personal\macro\bee-3-cpl"
NFRAMES = 12
NPOS = 40
N1_MAX = 0.25
N2_TOL = 0.12
N3_MIN_DISTINCT = 4
S_NOISE = 0.20
S_REAL = 0.50


def main():
    rng = np.random.default_rng(20260824)
    with open(os.path.join(OUT, "x12_bandsnr.json"), "r", encoding="utf-8") as fh:
        ptc = json.load(fh)
    a, b = ptc["fit_a"], ptc["fit_b"]

    print("=" * 78)
    print("M95 arm 13c -- the defocus null: how much of the band is real signal?")
    print("=" * 78)
    print(f"  levelcorr from arm 13b PTC: floor(L) = {a:.4e} + {b:.4e}*L")
    print("  (used only as a RATIO between two levels, so its scalar bias cancels)")

    A = load_luma(IMAGES["A"]["path"])
    pos = pick_tiles(A, n=NPOS)
    print(f"  {len(pos)} positions -- the same 40 tiles arm 8 selected")

    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))
    idx = np.unique(np.linspace(0, len(files) - 1, NFRAMES).astype(int))
    print(f"  {len(files)} frames in stack; sampling {len(idx)} of them\n")

    nf, npz = len(idx), len(pos)
    T = np.zeros((nf, npz, TILE, TILE), dtype=np.float32)
    P = np.zeros((nf, npz))
    L = np.zeros((nf, npz))
    for i, k in enumerate(idx):
        img = decode_rawpy(files[k])
        for j, (y, x) in enumerate(pos):
            t = np.ascontiguousarray(img[y : y + TILE, x : x + TILE])
            T[i, j] = t
            P[i, j] = band_power(t, *BAND)
            L[i, j] = float(t.mean())
        print(f"    frame {os.path.basename(files[k])}  mean band power {P[i].mean():.4e}")
        del img

    order = np.argsort(P, axis=0)
    i_max, i_min, i_min2 = order[-1, :], order[0, :], order[1, :]
    ar = np.arange(npz)

    def levelcorr(i_from, i_to):
        """Scale noise measured at frame i_from's level to frame i_to's level."""
        return (a + b * L[i_to, ar]) / (a + b * L[i_from, ar])

    S = 1.0 - P[i_min, ar] * levelcorr(i_min, i_max) / P[i_max, ar]
    med = float(np.median(S))

    distinct = len(set(i_max.tolist()))
    n3 = bool(distinct >= N3_MIN_DISTINCT)
    print(f"\n  N3 non-degeneracy: {distinct} distinct sharpest-frames across {npz} "
          f"positions (bar >= {N3_MIN_DISTINCT}) {'PASS' if n3 else 'FAIL'}")

    S_null = 1.0 - P[i_min, ar] * levelcorr(i_min, i_min2) / P[i_min2, ar]
    n1 = bool(abs(float(np.median(S_null))) <= N1_MAX)
    print(f"  N1 null (two most-defocused frames, true S = 0): median S = "
          f"{float(np.median(S_null)):+.4f} (bar |S|<={N1_MAX}) {'PASS' if n1 else 'FAIL'}")

    n2 = {}
    for s_true in (0.50, 0.90):
        hat = []
        for j in range(npz):
            t = T[i_min[j], j].astype(np.float64)
            pn = P[i_min[j], j]
            f = band_limited_field(rng, TILE, *BAND)
            pf = band_power(f, *BAND)
            want = pn * s_true / (1.0 - s_true)          # planted signal band power
            planted = t + f * np.sqrt(want / pf)          # a REAL image, then measured
            ptest = band_power(planted, *BAND)
            ref = P[i_min2[j], j] * ((a + b * L[i_min[j], j]) / (a + b * L[i_min2[j], j]))
            hat.append(1.0 - ref / ptest)
        got = float(np.median(hat))
        ok = bool(abs(got - s_true) <= N2_TOL)
        n2[f"{s_true:.2f}"] = {"S_hat": got, "pass": ok}
        print(f"  N2 power: plant S_true={s_true:.2f} -> S_hat={got:+.4f} "
              f"{'PASS' if ok else 'FAIL'}")

    verdict = ("NOISE-DOMINATED" if med <= S_NOISE else "REAL SIGNAL" if med >= S_REAL else "PARTIAL")
    ctrl = bool(n1 and n3 and all(v["pass"] for v in n2.values()))
    ratio = float(np.median(P[i_max, ar] / P[i_min, ar]))
    print(f"\n  focus/defocus band power ratio, median: {ratio:.3f}x")
    print(f"  S_detail  median {med:+.4f}   mean {float(S.mean()):+.4f}   "
          f"min {float(S.min()):+.4f}   max {float(S.max()):+.4f}")
    print(f"  bars: <={S_NOISE} noise-dominated, >={S_REAL} real signal")
    print(f"  HEADLINE VERDICT: {verdict}")
    print(f"  controls all pass: {ctrl}")
    if not ctrl:
        print("  *** a control FAILED -- the headline is VOID by pre-registration ***")

    J = {"bars": {"N1_max": N1_MAX, "N2_tol": N2_TOL, "N3_min_distinct": N3_MIN_DISTINCT,
                  "S_noise": S_NOISE, "S_real": S_REAL},
         "frames": [os.path.basename(files[k]) for k in idx],
         "ptc_a": a, "ptc_b": b,
         "N1_median": float(np.median(S_null)), "N1_pass": n1,
         "N2": n2, "N3_distinct": int(distinct), "N3_pass": n3,
         "focus_defocus_ratio_median": ratio,
         "S_detail_median": med, "S_detail_mean": float(S.mean()),
         "S_detail_min": float(S.min()), "S_detail_max": float(S.max()),
         "S_detail_all": [float(x) for x in S], "verdict": verdict,
         "controls_all_pass": ctrl}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "x13_focusnull.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    print("wrote out/x13_focusnull.json")


if __name__ == "__main__":
    main()
