"""M95 arm 13d -- is arm 13c's headline an artifact of its level correction?

WHY THIS EXISTS, AND IT IS MY OWN RESULT I AM ATTACKING. Arm 13c passed all four
of its pre-registered controls and returned S_detail = +0.1138, "noise-dominated".
One line of its own output impeaches it. The median focus/defocus band power
ratio was 1.965x. With a neutral level correction the estimator would then read
1 - 1/1.965 = +0.491, which is the "real signal" bucket, not the noise bucket.
The gap between +0.491 and +0.1138 is entirely the level correction

    levelcorr = (a + b*L_focus) / (a + b*L_defocus),     a = -91.939, b = 0.13717

and the implied median correction is about 1.74x. That term is therefore doing
MORE work than the measurement it corrects, and I did not test it. Worse, I can
show my own N1 null could not have tested it: N1 compares the two MOST defocused
frames, which sit at almost the same exposure level, so levelcorr ~ 1 there and
the control passes whether the correction is right or catastrophically wrong.
That is a control which cannot fail in the dimension that matters -- exactly the
defect discipline 706 names, and exactly the defect I caught in 13c's own N2
plant before running it. I missed it in N1.

THE SPECIFIC RISK. Arm 13b's scalar calibration error c cancels in a ratio and
that argument is still sound. But the SHAPE of a + b*L does not cancel. With
a = -91.9 and b = 0.1372 the fitted floor is 0.1372*(L - 670), a line with a
large negative intercept, so between L = 2000 and L = 4000 it predicts a 2.50x
change in noise power where pure shot noise predicts 2.00x. If that shape is
wrong the headline moves.

-------------------------------------------------------------------------------
PRE-REGISTERED, committed BEFORE running.

Three level-correction models, spanning the physically defensible range:

  M-none   levelcorr = 1
           No correction. Correct only if the two frames are at the same level.
           This is the model that MAXIMISES S -- it is the arm most favourable to
           my published +0.1160 dex framing, and I am including it for that
           reason.
  M-shot   levelcorr = L_focus / L_defocus
           Pure shot noise, variance proportional to signal. The textbook floor
           at ISO 100 on a lit subject, where shot dominates read by orders of
           magnitude (arm 13 measured photograph:dark at 1820x near Nyquist).
  M-ptc    levelcorr = (a + b*L_f)/(a + b*L_d)
           Arm 13c's model, the measured in-band PTC.

BARS
  D1  Every model must independently pass 13c's N1 null (median |S| <= 0.25) and
      both N2 plants (recover 0.50 and 0.90 within +/-0.12) on that model's own
      arithmetic. A model failing its own controls is not admissible evidence.
  D2  HEADLINE ROBUST only if all admissible models land in the same verdict
      bucket (<=0.20 noise / >=0.50 real / between partial). If they disagree,
      arm 13c's headline is downgraded to a BRACKET, reported as the min and max
      across admissible models, and the noise-dominated claim is NOT asserted.
  D3  Report the median levelcorr actually applied, so the size of the correction
      is visible next to the number it produced rather than buried in a script.

MY REGISTERED PREDICTION. The models will disagree and D2 will force a bracket:
M-none near +0.49, M-shot somewhere near +0.25, M-ptc +0.11. If that is what
happens then the honest headline is a bracket 0.11-0.49 whose LOWER half is
noise-dominated and whose upper half is not, and the correct report is that my
instrument cannot resolve the question -- which the orchestrator explicitly named
as an acceptable and valuable finding. My three previous predictions this session
were all scored wrong.
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
S_NOISE = 0.20
S_REAL = 0.50


def bucket(s):
    return "NOISE-DOMINATED" if s <= S_NOISE else "REAL SIGNAL" if s >= S_REAL else "PARTIAL"


def main():
    rng = np.random.default_rng(20260824)
    with open(os.path.join(OUT, "x12_bandsnr.json"), "r", encoding="utf-8") as fh:
        ptc = json.load(fh)
    a, b = ptc["fit_a"], ptc["fit_b"]

    print("=" * 78)
    print("M95 arm 13d -- does arm 13c's headline survive its own level correction?")
    print("=" * 78)

    A = load_luma(IMAGES["A"]["path"])
    pos = pick_tiles(A, n=NPOS)
    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))
    idx = np.unique(np.linspace(0, len(files) - 1, NFRAMES).astype(int))
    print(f"  {len(pos)} positions, {len(idx)} frames sampled from {len(files)}\n")

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
        print(f"    decoded {os.path.basename(files[k])}")
        del img

    order = np.argsort(P, axis=0)
    i_max, i_min, i_min2 = order[-1, :], order[0, :], order[1, :]
    ar = np.arange(npz)

    MODELS = {
        "M-none": lambda lf, ld: np.ones_like(lf),
        "M-shot": lambda lf, ld: lf / ld,
        "M-ptc": lambda lf, ld: (a + b * lf) / (a + b * ld),
    }

    ratio = P[i_max, ar] / P[i_min, ar]
    print(f"\n  focus/defocus band power ratio, median {float(np.median(ratio)):.4f}x")
    print(f"  levels: defocus median {float(np.median(L[i_min, ar])):.1f} DN, "
          f"focus median {float(np.median(L[i_max, ar])):.1f} DN")

    res = {}
    for name, fn in MODELS.items():
        lc = fn(L[i_max, ar], L[i_min, ar])
        S = 1.0 - P[i_min, ar] / P[i_max, ar] * lc
        lc_null = fn(L[i_min2, ar], L[i_min, ar])
        S_null = 1.0 - P[i_min, ar] / P[i_min2, ar] * lc_null
        n1 = bool(abs(float(np.median(S_null))) <= N1_MAX)

        n2 = {}
        for s_true in (0.50, 0.90):
            hat = []
            for j in range(npz):
                t = T[i_min[j], j].astype(np.float64)
                pn = P[i_min[j], j]
                f = band_limited_field(rng, TILE, *BAND)
                want = pn * s_true / (1.0 - s_true)
                planted = t + f * np.sqrt(want / band_power(f, *BAND))
                ptest = band_power(planted, *BAND)
                lcj = float(fn(np.array([L[i_min[j], j]]), np.array([L[i_min2[j], j]]))[0])
                hat.append(1.0 - P[i_min2[j], j] / ptest * lcj)
            got = float(np.median(hat))
            n2[f"{s_true:.2f}"] = {"S_hat": got, "pass": bool(abs(got - s_true) <= N2_TOL)}

        ok = bool(n1 and all(v["pass"] for v in n2.values()))
        med = float(np.median(S))
        res[name] = {"levelcorr_median": float(np.median(lc)), "S_median": med,
                     "bucket": bucket(med), "N1_median": float(np.median(S_null)),
                     "N1_pass": n1, "N2": n2, "admissible": ok}
        print(f"\n  {name:8s} levelcorr median {float(np.median(lc)):.4f}x  ->  "
              f"S_detail median {med:+.4f}  [{bucket(med)}]")
        print(f"           D1 controls: N1 {float(np.median(S_null)):+.4f} "
              f"{'PASS' if n1 else 'FAIL'}   "
              + "   ".join(f"N2@{k} {v['S_hat']:+.4f} {'PASS' if v['pass'] else 'FAIL'}"
                           for k, v in n2.items())
              + f"   -> {'ADMISSIBLE' if ok else 'INADMISSIBLE'}")

    adm = {k: v for k, v in res.items() if v["admissible"]}
    buckets = sorted({v["bucket"] for v in adm.values()})
    robust = bool(len(adm) > 0 and len(buckets) == 1)
    lo = min(v["S_median"] for v in adm.values()) if adm else float("nan")
    hi = max(v["S_median"] for v in adm.values()) if adm else float("nan")

    print("\n" + "-" * 78)
    print(f"  D1 admissible models: {sorted(adm)} of {sorted(res)}")
    print(f"  D2 verdict buckets among admissible models: {buckets}")
    if robust:
        print(f"  D2 HEADLINE ROBUST -- all admissible models agree: {buckets[0]}")
    else:
        print(f"  D2 HEADLINE NOT ROBUST -- downgraded to a BRACKET "
              f"S_detail in [{lo:+.4f}, {hi:+.4f}]")
        print("     arm 13c's noise-dominated claim is NOT asserted on this evidence")
    print(f"  D3 median level correction applied by arm 13c (M-ptc): "
          f"{res['M-ptc']['levelcorr_median']:.4f}x")

    J = {"bars": {"N1_max": N1_MAX, "N2_tol": N2_TOL, "S_noise": S_NOISE, "S_real": S_REAL},
         "frames": [os.path.basename(files[k]) for k in idx],
         "ptc_a": a, "ptc_b": b,
         "ratio_median": float(np.median(ratio)),
         "level_defocus_median": float(np.median(L[i_min, ar])),
         "level_focus_median": float(np.median(L[i_max, ar])),
         "models": res, "admissible": sorted(adm), "buckets": buckets,
         "robust": robust, "bracket_lo": lo, "bracket_hi": hi}
    with open(os.path.join(OUT, "x14_levelsens.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    print("wrote out/x14_levelsens.json")


if __name__ == "__main__":
    main()
