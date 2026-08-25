"""M95 arm 13e -- measure the level-scaling law instead of arguing about it.

WHERE THIS SITS. Arm 13d downgraded arm 13c's headline to a bracket:

    M-none  levelcorr 1.0000x  ->  S_detail +0.4910  PARTIAL          admissible
    M-shot  levelcorr 1.6129x  ->  S_detail +0.1573  NOISE-DOMINATED  admissible
    M-ptc   levelcorr 1.6778x  ->  S_detail +0.1138  NOISE-DOMINATED  admissible

All three passed their own null and both power plants, so all three are
admissible and the bracket is [+0.1138, +0.4910] -- straddling the boundary
between "the band is noise" and "the band is real detail". That bracket is the
honest state of my evidence and it does not answer the owner's question.

The three models differ in exactly one physical claim: how in-band noise power
scales with exposure level. M-none says p = 0, M-shot says p = 1, M-ptc's fitted
line implies a local log-log slope of b*L/(a+b*L) = L/(L-670), about 1.14 at the
measured defocus level of 5562 DN. THAT IS A MEASURABLE QUANTITY AND I HAVE BEEN
ARGUING ABOUT IT INSTEAD OF MEASURING IT.

THE CALIBRATION SET, CHOSEN BY PHYSICS. Arm 13b's root cause was named in its own
post-mortem: "flattest by gradient variance" is a spatial-domain criterion that
says nothing about power at 0.30-0.48 cyc/px. This arm replaces it with a
criterion that is about the band by construction. In a focus stack, a tile
position that NEVER comes into focus in any frame is defocused in all of them;
its in-band power is sensor noise plus the demosaic's response to sensor noise,
and the defocus disc guarantees it, with no fit and no assumption. Concretely:
sweep the 12 sampled frames and keep positions whose band power varies by less
than FOCUS_FLAT across the whole stack -- a position that focuses somewhere shows
a peak, and one that never focuses does not. Those positions span a wide range of
exposure level naturally, because the defocused background is unevenly lit, which
is precisely the lever needed to fit the scaling law.

-------------------------------------------------------------------------------
PRE-REGISTERED, committed BEFORE running.

Fit log10(P_band) = c + p*log10(L) over never-focusing tiles. Report p and a
bootstrap 95% CI. The three models predict p = 0 (M-none), p = 1 (M-shot),
p = L/(L-670) ~ 1.14 (M-ptc). Then recompute S_detail with levelcorr = (Lf/Ld)^p.

BARS
  E1  HELD-OUT NULL. Fit on a random half of the never-focusing tiles, then
      predict the other half. Median |1 - predicted/actual| <= 0.25. This is
      arm 13b's Q3 rebuilt on a physics-chosen calibration set; 13b read +0.2506
      against this same 0.25 bar and failed it.
  E2  POWER. Plant a real band-limited field into the ACTUAL PIXELS of held-out
      never-focusing tiles at S_true = 0.50 and 0.90 and recover within +/-0.12.
  E3  NON-DEGENERACY OF THE FIT. The never-focusing tiles must span at least a
      2.0x range in level, or the fit has no lever and p is unidentified. If this
      fails, p is NOT reported and the arm returns VOID.
  E4  DISCRIMINATION. State before looking: if the CI on p excludes 0, M-none is
      refuted and the bracket loses its upper end. If the CI excludes 1, M-shot
      is refuted. If the CI contains more than one model's prediction, the arm
      does NOT discriminate and the bracket stands as arm 13d left it.

HEADLINE. S_detail recomputed at the measured p, in the same three buckets:
<=0.20 noise-dominated, >=0.50 real signal, else PARTIAL.

MY REGISTERED PREDICTION. p in 0.8-1.1, refuting M-none, leaving S_detail near
+0.15 and the verdict NOISE-DOMINATED. Scoring so far this session: arm 13's
prediction wrong, arm 13b's wrong, arm 13c's wrong, arm 13d's structurally right
and one of three point values wrong.
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
GRID = 8
FOCUS_FLAT = 1.35
MIN_FLAT_TILES = 12
E1_MAX = 0.25
E2_TOL = 0.12
E3_MIN_SPAN = 2.0
S_NOISE = 0.20
S_REAL = 0.50


def bucket(s):
    return "NOISE-DOMINATED" if s <= S_NOISE else "REAL SIGNAL" if s >= S_REAL else "PARTIAL"


def main():
    rng = np.random.default_rng(20260824)

    print("=" * 78)
    print("M95 arm 13e -- the level-scaling law, measured on physics-chosen tiles")
    print("=" * 78)

    A = load_luma(IMAGES["A"]["path"])
    det = pick_tiles(A, n=NPOS)
    H, W = A.shape
    ys = np.linspace(TILE, H - 2 * TILE, GRID).astype(int)
    xs = np.linspace(TILE, W - 2 * TILE, GRID).astype(int)
    grid = [(int(y), int(x)) for y in ys for x in xs]
    pos = grid + det
    ng, nd = len(grid), len(det)
    print(f"  {ng} grid positions (candidate never-focusing) + {nd} detail positions")

    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))
    idx = np.unique(np.linspace(0, len(files) - 1, NFRAMES).astype(int))
    nf, npz = len(idx), len(pos)
    print(f"  {len(files)} frames, sampling {nf}\n")

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

    swing = P[:, :ng].max(axis=0) / np.maximum(P[:, :ng].min(axis=0), 1e-12)
    flat = np.where(swing < FOCUS_FLAT)[0]
    print(f"\n  never-focusing tiles: {len(flat)} of {ng} grid positions "
          f"(band power swing < {FOCUS_FLAT}x across the stack)")
    if len(flat) < MIN_FLAT_TILES:
        print(f"  *** only {len(flat)} < {MIN_FLAT_TILES} -- VOID, no calibration set ***")
        return

    fl = np.log10(np.maximum(L[:, flat].ravel(), 1.0))
    fp = np.log10(np.maximum(P[:, flat].ravel(), 1e-12))
    span = float(10 ** (fl.max() - fl.min()))
    e3 = bool(span >= E3_MIN_SPAN)
    print(f"  E3 level span across calibration set: {span:.3f}x "
          f"(bar >= {E3_MIN_SPAN}) {'PASS' if e3 else 'FAIL'}")
    if not e3:
        print("  *** E3 FAIL -- p is unidentified and is NOT reported. Arm VOID. ***")
        return

    p_hat, c_hat = np.polyfit(fl, fp, 1)
    boot = []
    n = len(fl)
    for _ in range(2000):
        s = rng.integers(0, n, n)
        boot.append(np.polyfit(fl[s], fp[s], 1)[0])
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    print(f"  fitted law: log10(P) = {c_hat:+.4f} + {p_hat:.4f}*log10(L)"
          f"   p = {p_hat:.4f}  95% CI [{lo:.4f}, {hi:.4f}]  n={n}")

    half = rng.permutation(len(flat))
    fit_i, held_i = flat[half[: len(flat) // 2]], flat[half[len(flat) // 2 :]]
    fl2 = np.log10(np.maximum(L[:, fit_i].ravel(), 1.0))
    fp2 = np.log10(np.maximum(P[:, fit_i].ravel(), 1e-12))
    p2, c2 = np.polyfit(fl2, fp2, 1)
    pred = 10 ** (c2 + p2 * np.log10(np.maximum(L[:, held_i], 1.0)))
    e1v = float(np.median(np.abs(1.0 - pred / P[:, held_i])))
    e1 = bool(e1v <= E1_MAX)
    print(f"  E1 held-out null: median |1 - pred/actual| = {e1v:.4f} "
          f"(bar <= {E1_MAX}) {'PASS' if e1 else 'FAIL'}   "
          f"[arm 13b read +0.2506 against this same bar and FAILED]")

    e2 = {}
    for s_true in (0.50, 0.90):
        hat = []
        for j in held_i:
            i0 = int(np.argmin(P[:, j]))
            t = T[i0, j].astype(np.float64)
            pn = P[i0, j]
            f = band_limited_field(rng, TILE, *BAND)
            want = pn * s_true / (1.0 - s_true)
            planted = t + f * np.sqrt(want / band_power(f, *BAND))
            ptest = band_power(planted, *BAND)
            ref = 10 ** (c2 + p2 * np.log10(max(L[i0, j], 1.0)))
            hat.append(1.0 - ref / ptest)
        got = float(np.median(hat))
        e2[f"{s_true:.2f}"] = {"S_hat": got, "pass": bool(abs(got - s_true) <= E2_TOL)}
        print(f"  E2 power: plant S_true={s_true:.2f} -> S_hat={got:+.4f} "
              f"{'PASS' if e2[f'{s_true:.2f}']['pass'] else 'FAIL'}")

    excl0 = bool(lo > 0.0 or hi < 0.0)
    excl1 = bool(lo > 1.0 or hi < 1.0)
    p_ptc = float(np.median(L[:, flat]) / (np.median(L[:, flat]) - 670.2))
    exclptc = bool(lo > p_ptc or hi < p_ptc)
    print(f"\n  E4 discrimination: CI excludes p=0 (M-none)? {excl0}   "
          f"p=1 (M-shot)? {excl1}   p={p_ptc:.3f} (M-ptc)? {exclptc}")

    Pd, Ld = P[:, ng:], L[:, ng:]
    order = np.argsort(Pd, axis=0)
    i_max, i_min = order[-1, :], order[0, :]
    ar = np.arange(nd)
    lc = (Ld[i_max, ar] / Ld[i_min, ar]) ** p_hat
    S = 1.0 - Pd[i_min, ar] / Pd[i_max, ar] * lc
    med = float(np.median(S))
    S_lo = float(np.median(1.0 - Pd[i_min, ar] / Pd[i_max, ar] * (Ld[i_max, ar] / Ld[i_min, ar]) ** hi))
    S_hi = float(np.median(1.0 - Pd[i_min, ar] / Pd[i_max, ar] * (Ld[i_max, ar] / Ld[i_min, ar]) ** lo))
    ctrl = bool(e1 and e3 and all(v["pass"] for v in e2.values()))

    print(f"\n  levelcorr at measured p: median {float(np.median(lc)):.4f}x")
    print(f"  S_detail median {med:+.4f}   [{bucket(med)}]")
    print(f"  propagating the CI on p: S_detail in [{S_lo:+.4f}, {S_hi:+.4f}]  "
          f"-> [{bucket(S_lo)} .. {bucket(S_hi)}]")
    print(f"  controls all pass: {ctrl}")
    if not ctrl:
        print("  *** a control FAILED -- headline VOID by pre-registration ***")

    J = {"bars": {"E1_max": E1_MAX, "E2_tol": E2_TOL, "E3_min_span": E3_MIN_SPAN,
                  "focus_flat": FOCUS_FLAT, "S_noise": S_NOISE, "S_real": S_REAL},
         "frames": [os.path.basename(files[k]) for k in idx],
         "n_flat_tiles": int(len(flat)), "n_grid": ng, "level_span": span,
         "p_hat": float(p_hat), "c_hat": float(c_hat), "p_ci": [lo, hi], "n_fit": int(n),
         "E1_value": e1v, "E1_pass": e1, "E2": e2, "E3_pass": e3,
         "E4_excludes_0": excl0, "E4_excludes_1": excl1,
         "E4_p_ptc": p_ptc, "E4_excludes_ptc": exclptc,
         "levelcorr_median": float(np.median(lc)),
         "S_detail_median": med, "S_detail_ci": [S_lo, S_hi],
         "verdict": bucket(med), "controls_all_pass": ctrl}
    with open(os.path.join(OUT, "x15_defocusptc.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    print("wrote out/x15_defocusptc.json")


if __name__ == "__main__":
    main()
