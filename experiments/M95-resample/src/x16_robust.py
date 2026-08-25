"""M95 arm 13f -- robustness annex for the headline, and a cache so this is the
last decode.

Arm 13e produced the number that will be the headline:

    p = 1.0751, 95% CI [1.0579, 1.0953], n = 300, from 25 never-focusing tiles
    E1 held-out null 0.0183 (arm 13b failed the same 0.25 bar at 0.2506)
    E2 plants 0.4884 / 0.8979
    S_detail = +0.1281, CI [+0.1216, +0.1336]  NOISE-DOMINATED throughout

Three things could still make it wrong and none of them were tested.

  1. EXTRAPOLATION. p was fitted on defocused BACKGROUND tiles. It is applied to
     detail tiles at a different exposure level. Arm 13b carried a Q4
     extrapolation guard and passed it; 13e does not carry one at all. If the
     detail tiles sit outside the calibration range, the law is extrapolated.
  2. CURVATURE. A straight line in log-log was assumed. If the true relation
     bends, a single p misestimates the correction at the ends of the range.
  3. HOW WRONG WOULD p HAVE TO BE. The verdict is only interesting if it takes an
     implausible p to overturn it. I have not stated what that p is. Without it,
     "the CI is tight" is a claim about my fit, not about the conclusion.

This arm also caches every per-tile band power and level to an .npz, so that any
further question about this dataset costs no decodes at all.

-------------------------------------------------------------------------------
PRE-REGISTERED, committed BEFORE running.

  F1  EXTRAPOLATION GUARD. Report the calibration level range and the detail-tile
      level range. PASS if the detail tiles' [min, max] lies inside the
      calibration [min, max]. If it FAILS the headline is reported as
      EXTRAPOLATED and that word appears next to it in the report.
  F2  CURVATURE. Fit log10(P) = c + p*log10(L) + q*log10(L)^2. PASS if adding q
      changes the predicted levelcorr on the detail tiles by less than 0.02
      absolute in S_detail. Report the change either way.
  F3  OVERTURN THRESHOLD. Solve for the p at which median S_detail = 0.20 and at
      which it = 0.50. Report both, and report how many multiples of the fitted
      standard error away they are. State the interpretation now: if reaching
      S = 0.50 requires a p that is negative or below 0.3, the "real signal"
      verdict requires a level law that has already been refuted at 95%, and the
      noise-dominated verdict is robust.
  F4  The E1 held-out null and both E2 plants are re-run here on the same split
      procedure, so this arm carries its own controls rather than inheriting 13e's.

MY REGISTERED PREDICTION. F1 FAILS -- the detail tiles are lit subject and the
never-focusing tiles are background, and I expect the detail tiles to run brighter
than the calibration set at the top end. F2 passes with a change under 0.01. F3
returns an overturn threshold for S=0.50 somewhere near p = 0, i.e. the only way
to get "real signal" is the model already refuted. Session scoring: arms 13, 13b,
13c predictions wrong; 13d structurally right, one of three values wrong; 13e
right (predicted p in 0.8-1.1, got 1.0751).
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
E1_MAX = 0.25
E2_TOL = 0.12
F2_MAX_DS = 0.02
S_NOISE = 0.20
S_REAL = 0.50
CACHE = os.path.join(OUT, "x16_tiles.npz")


def bucket(s):
    return "NOISE-DOMINATED" if s <= S_NOISE else "REAL SIGNAL" if s >= S_REAL else "PARTIAL"


def main():
    rng = np.random.default_rng(20260824)
    print("=" * 78)
    print("M95 arm 13f -- robustness annex for the S_detail headline")
    print("=" * 78)

    A = load_luma(IMAGES["A"]["path"])
    det = pick_tiles(A, n=NPOS)
    H, W = A.shape
    ys = np.linspace(TILE, H - 2 * TILE, GRID).astype(int)
    xs = np.linspace(TILE, W - 2 * TILE, GRID).astype(int)
    grid = [(int(y), int(x)) for y in ys for x in xs]
    pos = grid + det
    ng, nd = len(grid), len(det)

    files = sorted(glob.glob(os.path.join(STACK, "*.ARW")))
    idx = np.unique(np.linspace(0, len(files) - 1, NFRAMES).astype(int))
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
    np.savez_compressed(CACHE, P=P, L=L, ng=ng, pos=np.array(pos),
                        frames=np.array([os.path.basename(files[k]) for k in idx]))
    print(f"  cached per-tile band power and level to {os.path.basename(CACHE)}")

    swing = P[:, :ng].max(axis=0) / np.maximum(P[:, :ng].min(axis=0), 1e-12)
    flat = np.where(swing < FOCUS_FLAT)[0]
    cal_L = L[:, flat].ravel()
    fl, fp = np.log10(np.maximum(cal_L, 1.0)), np.log10(np.maximum(P[:, flat].ravel(), 1e-12))
    p_hat, c_hat = np.polyfit(fl, fp, 1)
    se = float(np.sqrt(np.sum((fp - (c_hat + p_hat * fl)) ** 2) / (len(fl) - 2)
                       / np.sum((fl - fl.mean()) ** 2)))
    print(f"\n  {len(flat)} never-focusing tiles, p = {p_hat:.4f}, se = {se:.5f}")

    Pd, Ld = P[:, ng:], L[:, ng:]
    order = np.argsort(Pd, axis=0)
    i_max, i_min = order[-1, :], order[0, :]
    ar = np.arange(nd)
    R = Pd[i_min, ar] / Pd[i_max, ar]
    ratL = Ld[i_max, ar] / Ld[i_min, ar]

    def S_at(p):
        return float(np.median(1.0 - R * ratL ** p))

    det_L = np.concatenate([Ld[i_min, ar], Ld[i_max, ar]])
    f1 = bool(det_L.min() >= cal_L.min() and det_L.max() <= cal_L.max())
    print(f"\n  F1 extrapolation guard:")
    print(f"     calibration levels {cal_L.min():.1f} - {cal_L.max():.1f} DN")
    print(f"     detail-tile levels {det_L.min():.1f} - {det_L.max():.1f} DN")
    print(f"     {'PASS -- interpolating' if f1 else 'FAIL -- headline is EXTRAPOLATED'}")

    q2, p2, c2 = np.polyfit(fl, fp, 2)
    lo_l, hi_l = np.log10(Ld[i_min, ar]), np.log10(Ld[i_max, ar])
    lc_q = 10 ** ((c2 + p2 * hi_l + q2 * hi_l ** 2) - (c2 + p2 * lo_l + q2 * lo_l ** 2))
    S_q = float(np.median(1.0 - R * lc_q))
    S_l = S_at(p_hat)
    f2 = bool(abs(S_q - S_l) <= F2_MAX_DS)
    print(f"\n  F2 curvature: quadratic term q = {q2:+.5f}")
    print(f"     S_detail linear {S_l:+.4f}   quadratic {S_q:+.4f}   "
          f"delta {abs(S_q - S_l):.4f} (bar <= {F2_MAX_DS}) {'PASS' if f2 else 'FAIL'}")

    def solve(target):
        g = np.linspace(-4.0, 6.0, 200001)
        v = np.array([np.median(1.0 - R * ratL ** x) for x in np.linspace(-4.0, 6.0, 401)])
        xs_ = np.linspace(-4.0, 6.0, 401)
        i = int(np.argmin(np.abs(v - target)))
        return float(xs_[i]), float(v[i])

    p20, v20 = solve(S_NOISE)
    p50, v50 = solve(S_REAL)
    print(f"\n  F3 overturn thresholds (fitted p = {p_hat:.4f}, se = {se:.5f}):")
    print(f"     S_detail reaches {S_NOISE:.2f} at p = {p20:+.4f}  "
          f"({abs(p20 - p_hat) / se:.1f} se from the fit)")
    print(f"     S_detail reaches {S_REAL:.2f} at p = {p50:+.4f}  "
          f"({abs(p50 - p_hat) / se:.1f} se from the fit)")
    print(f"     p = 0 (M-none, refuted at 95% by arm 13e) gives S = {S_at(0.0):+.4f}")
    print(f"     p = 1 (pure shot noise)                   gives S = {S_at(1.0):+.4f}")

    half = rng.permutation(len(flat))
    fit_i, held_i = flat[half[: len(flat) // 2]], flat[half[len(flat) // 2 :]]
    pa, ca = np.polyfit(np.log10(np.maximum(L[:, fit_i].ravel(), 1.0)),
                        np.log10(np.maximum(P[:, fit_i].ravel(), 1e-12)), 1)
    pred = 10 ** (ca + pa * np.log10(np.maximum(L[:, held_i], 1.0)))
    e1v = float(np.median(np.abs(1.0 - pred / P[:, held_i])))
    e1 = bool(e1v <= E1_MAX)
    print(f"\n  F4 own controls: held-out null {e1v:.4f} (bar <= {E1_MAX}) "
          f"{'PASS' if e1 else 'FAIL'}")
    e2 = {}
    for s_true in (0.50, 0.90):
        hat = []
        for j in held_i:
            i0 = int(np.argmin(P[:, j]))
            t = T[i0, j].astype(np.float64)
            f = band_limited_field(rng, TILE, *BAND)
            want = P[i0, j] * s_true / (1.0 - s_true)
            ptest = band_power(t + f * np.sqrt(want / band_power(f, *BAND)), *BAND)
            hat.append(1.0 - 10 ** (ca + pa * np.log10(max(L[i0, j], 1.0))) / ptest)
        got = float(np.median(hat))
        e2[f"{s_true:.2f}"] = {"S_hat": got, "pass": bool(abs(got - s_true) <= E2_TOL)}
        print(f"     plant {s_true:.2f} -> {got:+.4f} "
              f"{'PASS' if e2[f'{s_true:.2f}']['pass'] else 'FAIL'}")

    ctrl = bool(e1 and all(v["pass"] for v in e2.values()))
    print(f"\n  headline S_detail = {S_l:+.4f}  [{bucket(S_l)}]"
          f"{'' if f1 else '  (EXTRAPOLATED)'}")
    print(f"  controls all pass: {ctrl}")

    J = {"bars": {"E1_max": E1_MAX, "E2_tol": E2_TOL, "F2_max_dS": F2_MAX_DS},
         "p_hat": float(p_hat), "p_se": se, "n_flat": int(len(flat)),
         "cal_L_min": float(cal_L.min()), "cal_L_max": float(cal_L.max()),
         "det_L_min": float(det_L.min()), "det_L_max": float(det_L.max()),
         "F1_pass": f1, "F2_q": float(q2), "F2_S_linear": S_l, "F2_S_quad": S_q,
         "F2_delta": float(abs(S_q - S_l)), "F2_pass": f2,
         "F3_p_at_0.20": p20, "F3_p_at_0.50": p50,
         "F3_se_to_0.20": float(abs(p20 - p_hat) / se),
         "F3_se_to_0.50": float(abs(p50 - p_hat) / se),
         "F3_S_at_p0": S_at(0.0), "F3_S_at_p1": S_at(1.0),
         "F4_E1": e1v, "F4_E1_pass": e1, "F4_E2": e2,
         "S_detail": S_l, "verdict": bucket(S_l), "controls_all_pass": ctrl}
    with open(os.path.join(OUT, "x16_robust.json"), "w", encoding="utf-8") as fh:
        json.dump(J, fh, indent=1)
    print("wrote out/x16_robust.json")


if __name__ == "__main__":
    main()
