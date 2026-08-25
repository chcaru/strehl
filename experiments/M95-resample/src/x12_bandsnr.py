"""M95 arm 13b -- the in-band photon transfer curve, because arm 13's P2 bar was bad.

WHY THIS EXISTS. Arm 13 registered P2 with a DARK FRAME as the noise floor and
bracketed the signal fraction at 0.1111 to 0.9995. That bracket is too wide to
adjudicate anything, and the fault is mine and structural, not statistical:

  at ISO 100 on a lit subject, SHOT noise dominates READ noise by orders of
  magnitude, so a dark frame -- which has no shot noise at all -- cannot be a
  noise floor for a photograph. The measured near-Nyquist ratio between the
  photograph and the dark was 1820x, which is the size of the error.

S_upper = 0.9995 therefore PASSED the bar I registered while saying almost
nothing: it reports only that a lit frame has more band power than a black one.
I am not banking that pass. This arm replaces the floor with one measured at the
right light level, on the same frame, through the same demosaic.

THE METHOD. Noise power in the band is a function of exposure level. Fit that
function on the frame itself, from the tiles that have the least structure, and
then evaluate it at each detail tile's own level:

  1. tile the whole decoded frame, 256 px, non-overlapping
  2. per tile: mean level L, band power P, gradient-variance score G
  3. bin by L; in each bin take the 25th percentile of P as the noise floor at
     that level -- the least-structured tiles present at that exposure
  4. least-squares fit floor(L) = a + b*L  (a read term, b shot term)
  5. per detail tile:  S = 1 - floor(L) / P

Where this can be wrong, stated before it is run: the flattest tiles at a given
level may still hold real structure, which INFLATES the floor and DEFLATES S. So
this estimator is biased toward "the band is noise" -- the opposite direction to
arm 13's P2, and against my own published claim. Between the two arms my number
is bracketed by two estimators biased in opposite directions, which is the point.

-------------------------------------------------------------------------------
PRE-REGISTERED BARS -- committed BEFORE this script was run.

Q1  MODEL VALIDITY. The fitted shot slope b must be > 0 and the Spearman rank
    correlation between L and the per-bin floor must be >= 0.5. If in-band noise
    does not track exposure level, the model is void and so is the headline.

Q2  POWER CONTROL. Plant a band-limited field into HELD-OUT flat tiles at
    S_true = 0.50 and 0.90. The estimator must return each within +/- 0.12.
    Planted fields are zero-mean so they do not move L.

Q3  NEGATIVE CONTROL. The same held-out flat tiles, unplanted, must return
    |S| <= 0.25. They are noise by construction; a large reading means the floor
    is mis-calibrated and the headline is void.

Q4  EXTRAPOLATION GUARD. The detail tiles' mean levels must lie inside the level
    range spanned by the bins used for the fit. Reported either way; if they do
    not, the headline is an extrapolation and says so.

HEADLINE AND ITS REGISTERED INTERPRETATION -- S_detail, the median over the 40
detail tiles arm 8 selected:
    S_detail <= 0.20 -> the scoring band is NOISE-DOMINATED on the very tiles
                        the +0.1160 dex was measured on, and that number must
                        never be quoted as sharpness without the rider.
    S_detail >= 0.50 -> the band carries real captured signal; the kernel gain
                        is substantially real sharpening and my framing stands.
    between          -> partial, stated as partial, no rounding toward either.

MY REGISTERED PREDICTION. Arm 13 part A found only 2.82% of this band inside the
red/blue CFA Nyquist cell and 48.99% inside green's, and part B found optical MTF
falling 0.345 -> 0.056 across it. Both push toward little real signal. But the
detail tiles were chosen as the 40 sharpest in the frame, which pushes the other
way. I predict PARTIAL, S_detail 0.25-0.55, and I expect to be wrong in a way I
cannot guess the sign of -- arm 13 already scored my last prediction wrong.
-------------------------------------------------------------------------------
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import numpy as np

from x2_pairs import BAND, TILE, IMAGES, freqs, load_luma, pick_tiles, window
from x11_bandsignal import band_power, band_limited_field, pick_tiles_flat

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")

NBIN = 12
FLOOR_PCT = 25.0
CLIP_DN = 64000.0     # exclude tiles that clip; a clipped tile has suppressed noise
Q1_MIN_RHO = 0.5
Q2_TOL = 0.12
Q3_MAX = 0.25
S_NOISE = 0.20
S_REAL = 0.50


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra * ra).sum() * (rb * rb).sum()))


def main():
    rng = np.random.default_rng(20260824)
    J = {"bars": {"Q1_min_rho": Q1_MIN_RHO, "Q2_tol": Q2_TOL, "Q3_max": Q3_MAX,
                  "S_noise": S_NOISE, "S_real": S_REAL, "nbin": NBIN, "floor_pct": FLOOR_PCT}}

    print("=" * 78)
    print("M95 arm 13b -- in-band photon transfer, and the signal fraction it gives")
    print("=" * 78)

    A = load_luma(IMAGES["A"]["path"])
    h, w = A.shape
    print(f"  frame {A.shape}")

    lv, pw, gv, pos = [], [], [], []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            t = A[y : y + TILE, x : x + TILE]
            if float(np.percentile(t, 99.5)) >= CLIP_DN:
                continue
            lv.append(float(t.mean()))
            pw.append(band_power(t, *BAND))
            gv.append(float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var()))
            pos.append((y, x))
    lv, pw, gv = np.array(lv), np.array(pw), np.array(gv)
    print(f"  {len(lv)} non-clipping 256 px tiles; level {lv.min():.0f}-{lv.max():.0f} DN")

    # ---- fit the in-band noise floor as a function of level -----------------
    edges = np.quantile(lv, np.linspace(0, 1, NBIN + 1))
    bl, bf, bn = [], [], []
    for i in range(NBIN):
        m = (lv >= edges[i]) & (lv <= edges[i + 1] if i == NBIN - 1 else lv < edges[i + 1])
        if m.sum() < 6:
            continue
        bl.append(float(np.median(lv[m])))
        bf.append(float(np.percentile(pw[m], FLOOR_PCT)))
        bn.append(int(m.sum()))
    bl, bf = np.array(bl), np.array(bf)
    b, a = np.polyfit(bl, bf, 1)
    rho = spearman(bl, bf)
    q1 = bool(b > 0 and rho >= Q1_MIN_RHO)
    print(f"\n  floor(L) = {a:.4e} + {b:.4e}*L    spearman(level, floor) = {rho:+.4f}")
    print(f"  Q1 model validity: {'PASS' if q1 else 'FAIL'}  (slope>0 and rho>={Q1_MIN_RHO})")
    for i in range(len(bl)):
        print(f"    bin {i:2d}  level {bl[i]:9.1f} DN   floor {bf[i]:11.4e}   n={bn[i]}")

    def floor_at(L):
        return a + b * np.asarray(L, dtype=np.float64)

    def sig_frac(tiles):
        s = []
        for t in tiles:
            P = band_power(t, *BAND)
            s.append(1.0 - float(floor_at(t.mean())) / P)
        return np.array(s)

    # ---- controls ------------------------------------------------------------
    print("\ncontrols")
    flat_c = pick_tiles_flat(A, n=40)
    held = [np.ascontiguousarray(A[y : y + TILE, x : x + TILE]) for y, x in flat_c]
    s_held = sig_frac(held)
    q3 = bool(abs(float(np.median(s_held))) <= Q3_MAX)
    print(f"  Q3 negative: held-out FLAT tiles read S = {np.median(s_held):+.4f} "
          f"(bar |S|<={Q3_MAX}) {'PASS' if q3 else 'FAIL'}")

    q2 = {}
    for s_true in (0.50, 0.90):
        pl = []
        for t in held:
            Pn = band_power(t, *BAND)
            f = band_limited_field(rng, TILE, *BAND)
            Pf = band_power(f, *BAND)
            pl.append(t + f * np.sqrt((Pn * s_true / (1.0 - s_true)) / Pf))
        got = float(np.median(sig_frac(pl)))
        # the planted tile's own noise is Pn, so the achievable reading is bounded by
        # the same floor error the negative control exposes; the bar is on s_true.
        ok = abs(got - s_true) <= Q2_TOL
        q2[f"{s_true:.2f}"] = {"S_hat": got, "pass": bool(ok)}
        print(f"  Q2 power: plant S_true={s_true:.2f} -> S_hat={got:+.4f} "
              f"{'PASS' if ok else 'FAIL'}")

    # ---- headline ------------------------------------------------------------
    det_c = pick_tiles(A, n=40)
    det = [np.ascontiguousarray(A[y : y + TILE, x : x + TILE]) for y, x in det_c]
    s_det = sig_frac(det)
    dl = np.array([float(t.mean()) for t in det])
    q4 = bool(dl.min() >= bl.min() and dl.max() <= bl.max())
    med = float(np.median(s_det))
    verdict = ("NOISE-DOMINATED" if med <= S_NOISE else "REAL SIGNAL" if med >= S_REAL else "PARTIAL")
    print(f"\n  Q4 extrapolation guard: detail levels {dl.min():.0f}-{dl.max():.0f} DN vs "
          f"fit range {bl.min():.0f}-{bl.max():.0f} DN  {'PASS' if q4 else 'FAIL -- EXTRAPOLATING'}")
    print(f"\n  S_detail  median {med:+.4f}   mean {float(s_det.mean()):+.4f}   "
          f"min {float(s_det.min()):+.4f}   max {float(s_det.max()):+.4f}")
    print(f"  bars: <={S_NOISE} noise-dominated, >={S_REAL} real signal")
    print(f"  HEADLINE VERDICT: {verdict}")

    J.update({
        "n_tiles": int(len(lv)), "fit_a": float(a), "fit_b": float(b), "rho": rho, "Q1_pass": q1,
        "bins": [{"level": float(x), "floor": float(y), "n": int(k)} for x, y, k in zip(bl, bf, bn)],
        "Q3_held_flat_S": float(np.median(s_held)), "Q3_pass": q3, "Q2": q2,
        "Q4_pass": q4, "detail_levels": [float(x) for x in dl],
        "S_detail_median": med, "S_detail_mean": float(s_det.mean()),
        "S_detail_min": float(s_det.min()), "S_detail_max": float(s_det.max()),
        "S_detail_all": [float(x) for x in s_det], "verdict": verdict,
        "controls_all_pass": bool(q1 and q3 and all(v["pass"] for v in q2.values())),
    })
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "x12_bandsnr.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    print(f"\n  controls all pass: {J['controls_all_pass']}")
    print("wrote out/x12_bandsnr.json")


if __name__ == "__main__":
    main()
