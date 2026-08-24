"""Phase B -- what actually predicts the per-frame level?

Four candidate regressors, all measured or metadata, none fitted to the pixels:

  T   log SonyExposureTime      -- the true stepless exposure the camera used.
                                   ExposureTime in the standard EXIF block is
                                   rounded to the 1/3-stop ladder and is wrong
                                   by up to 9%; SonyExposureTime is not.
  F   -2 log SonyFNumber2       -- the camera's own EFFECTIVE f-number, which
                                   already contains the lens-extension term
                                   N_eff = N(1+m). Irradiance ~ 1/N_eff^2.
  A   -2 log a_k                -- the alignment solve's fitted scale ladder.
                                   This is the brief's 1/m^2 hypothesis.
  K   frame index (time)        -- a lamp warming or cooling.

Models are compared on the RMS of the residual of log(level), in natural log
units. A negative control shuffles the frame order.
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module  # noqa: E402

A = import_module("21_phaseA")

RNG = np.random.default_rng(99)
N_SHUFFLE = 500


def exifn(stack, files):
    path = os.path.join(HERE, "data", "exifn-%s.csv" % stack)
    m = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            m[r["FileName"]] = r
    t = np.array([float(m[f]["SonyExposureTime"]) for f in files])
    tr = np.array([float(m[f]["ExposureTime"]) for f in files])
    nef = np.array([float(m[f]["SonyFNumber2"]) for f in files])
    nn = np.array([float(m[f]["SonyFNumber"]) for f in files])
    fd = np.array([float(m[f]["FocusDistance2"]) if m[f]["FocusDistance2"]
                   else np.nan for f in files])
    return t, tr, nef, nn, fd


def rms(v):
    return float(np.sqrt(np.mean(np.square(v))))


def fit_report(y, regs, names):
    """OLS of y on [1] + regs, reporting residual RMS and coefficients."""
    X = np.column_stack([np.ones_like(y)] + list(regs))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return rms(r), beta


def analyse(stack):
    z = A.load(stack)
    scene, smad, sensor = z["scene"], z["scene_mad"], z["sensor"]
    centres, a = z["centres"], z["a"]
    files = [str(x) for x in z["files"]]
    ok = (np.isfinite(scene).all(axis=0) & np.isfinite(smad).all(axis=0)
          & (scene > A.LEVEL_MIN).all(axis=0) & (scene < A.LEVEL_MAX).all(axis=0)
          & (smad < A.SMOOTH_MAX).all(axis=0))
    chosen = A.farthest_point(centres, ok, A.N_PATCH)
    S = scene[:, chosen]
    n = S.shape[0]
    lvl = np.median(S, axis=1)
    t, tr, nef, nn, fd = exifn(stack, files)
    ref = int(z["ref"])

    y = np.log(lvl / lvl[ref])
    T = np.log(t / t[ref])
    Tr = np.log(tr / tr[ref])
    F = -2.0 * np.log(nef / nef[ref])
    Ascale = -2.0 * np.log(a / a[ref])
    K = (np.arange(n) - ref) / n

    print("=" * 74)
    print("%s  n=%d  ref=%d  patches=%d" % (stack, n, ref, len(chosen)))
    print("  SonyExposureTime : %.6f .. %.6f  (%d distinct, ratio %.4f)"
          % (t.min(), t.max(), len(set(t.round(9))), t.max() / t.min()))
    print("  ExposureTime(EXIF, rounded): %.6f .. %.6f  ratio %.4f"
          % (tr.min(), tr.max(), tr.max() / tr.min()))
    print("  SonyFNumber2     : %.4f .. %.4f  ratio %.4f  -> 1/N^2 span %.4f"
          % (nef.min(), nef.max(), nef.max() / nef.min(),
             (nef.max() / nef.min()) ** 2))
    print("  SonyFNumber      : %.4f .. %.4f" % (nn.min(), nn.max()))
    print("  align scale a_k  : %.5f .. %.5f  ratio %.4f"
          % (a.min(), a.max(), a.max() / a.min()))
    print("  measured level   : %.5f .. %.5f  ratio %.4f (%.4f stops)"
          % (lvl.min(), lvl.max(), lvl.max() / lvl.min(),
             np.log2(lvl.max() / lvl.min())))
    if np.isfinite(fd).any():
        print("  FocusDistance2   : %.4f .. %.4f m" % (np.nanmin(fd), np.nanmax(fd)))

    s0 = rms(y)
    print()
    print("  residual RMS of log(level), natural log units. lower is better.")
    print("  %-46s %8s %8s" % ("model", "RMS", "vs null"))
    print("  %-46s %8.5f %8s" % ("M0  null (constant)", s0, "1.000"))

    rows = {}

    def show(name, resid):
        r = rms(resid)
        rows[name] = r
        print("  %-46s %8.5f %8.3f" % (name, r, r / s0))
        return r

    show("M1  -2*log(a_k)            [brief's 1/m^2]", y - Ascale)
    show("M1r +2*log(a_k)            [opposite sign]", y + Ascale)
    show("Me  log SonyExposureTime   [true shutter]", y - T)
    show("Mer log ExposureTime       [rounded EXIF]", y - Tr)
    show("Mf  -2*log SonyFNumber2    [effective f/#]", y - F)
    show("Mef T + F                  [shutter x f/#]", y - T - F)
    show("Mea T + (-2 log a_k)       [shutter x scale]", y - T - Ascale)

    # Free-parameter fits, for the exponent and the floor.
    s_q, b_q = fit_report(y - T, [np.log(a / a[ref])], ["log a"])
    print("  %-46s %8.5f %8.3f   q_hat=%+.3f"
          % ("M2  T + q*log(a_k), q free", s_q, s_q / s0, b_q[1]))
    s_p, b_p = fit_report(y - T, [np.log(nef / nef[ref])], ["log N"])
    print("  %-46s %8.5f %8.3f   p_hat=%+.3f"
          % ("M2f T + p*log(N_eff), p free", s_p, s_p / s0, b_p[1]))
    s_k, b_k = fit_report(y - T, [K], ["k"])
    print("  %-46s %8.5f %8.3f   slope=%+.4f/stack"
          % ("M4  T + c*time  [lamp drift]", s_k, s_k / s0, b_k[1]))
    s_tk, b_tk = fit_report(y, [T, F, K], ["T", "F", "k"])
    print("  %-46s %8.5f %8.3f   bT=%+.3f bF=%+.3f bK=%+.4f"
          % ("M5  free T + F + time", s_tk, s_tk / s0, b_tk[1], b_tk[2], b_tk[3]))

    # Collinearity of the candidate regressors.
    def corr(u, v):
        u = u - u.mean()
        v = v - v.mean()
        d = np.linalg.norm(u) * np.linalg.norm(v)
        return float(u @ v / d) if d > 0 else np.nan
    print()
    print("  regressor collinearity: corr(F,A)=%+.4f  corr(F,k)=%+.4f  "
          "corr(A,k)=%+.4f  corr(T,k)=%+.4f"
          % (corr(F, Ascale), corr(F, K), corr(Ascale, K), corr(T, K)))

    # ---- PR-4 negative control ---------------------------------------------
    best_name = min(rows, key=lambda k2: rows[k2])
    print()
    print("  PR-4 negative control (%d shuffles of frame order):" % N_SHUFFLE)
    for nm, reg in (("M1  -2*log(a_k)", Ascale), ("Mf  -2*log SonyFNumber2", F),
                    ("Mef T + F", T + F)):
        true_r = rms(y - reg)
        sh = np.empty(N_SHUFFLE)
        for i in range(N_SHUFFLE):
            p = RNG.permutation(n)
            sh[i] = rms(y - reg[p])
        p1 = np.percentile(sh, 1.0)
        frac = float(np.mean(sh <= true_r))
        print("    %-24s true %.5f | shuffled 1st pct %.5f, median %.5f "
              "| P(shuffle<=true)=%.4f -> %s"
              % (nm, true_r, p1, np.median(sh), frac,
                 "HAS POWER" if true_r < p1 else "NO POWER"))

    return {"stack": stack, "n": n, "ref": ref, "rows": rows,
            "s0": s0, "q_hat": float(b_q[1]), "p_hat": float(b_p[1]),
            "lvl": lvl.tolist(), "t": t.tolist(), "nef": nef.tolist(),
            "a": a.tolist(), "best": best_name}


if __name__ == "__main__":
    out = {}
    for s in sys.argv[1:] or ["bee-3-cpl", "lavendar-cpl", "leaf-2-cpl",
                              "bee-2-cpl"]:
        out[s] = analyse(s)
        print()
    with open(os.path.join(HERE, "data", "phaseB.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f)
