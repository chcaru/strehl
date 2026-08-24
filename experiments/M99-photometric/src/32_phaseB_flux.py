"""Phase B, final -- model the WHOLE-FRAME flux, which blur cannot move.

The patch medians of `30_phaseB.py` mix two things: real photometric change and
defocus redistribution. The whole-frame mean above black is blind to the second
(blur conserves flux) and so is the honest dependent variable for a per-frame
photometric term.

Also checks the one confound the whole-frame mean does have: a magnification
change alters the field of view, so content enters and leaves at the border. If
a central crop -- which sees much less border traffic -- gives the same answer,
the border is not driving it.
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNG = np.random.default_rng(99)
N_SHUFFLE = 500
TILES = 24
CORE = 8   # keep tiles [CORE : TILES-CORE) -> central third, linear


def load(stack):
    fz = np.load(os.path.join(HERE, "data", "flux-%s.npz" % stack),
                 allow_pickle=True)
    lz = np.load(os.path.join(HERE, "data", "levels-%s.npz" % stack),
                 allow_pickle=True)
    files = [str(x) for x in fz["files"]]
    m = {}
    with open(os.path.join(HERE, "data", "exifn-%s.csv" % stack), newline="",
              encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            m[r["FileName"]] = r
    t = np.array([float(m[f]["SonyExposureTime"]) for f in files])
    tr = np.array([float(m[f]["ExposureTime"]) for f in files])
    nef = np.array([float(m[f]["SonyFNumber2"]) for f in files])
    return fz, lz, t, tr, nef, files


def rms(v):
    return float(np.sqrt(np.mean(np.square(v))))


def ols(y, regs):
    X = np.column_stack([np.ones_like(y)] + list(regs))
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return rms(y - X @ beta), beta


def analyse(stack):
    fz, lz, t, tr, nef, files = load(stack)
    gmean = fz["gmean"]
    tiles = fz["tiles"]
    core = tiles[:, CORE:TILES - CORE, CORE:TILES - CORE].mean(axis=(1, 2))
    a = lz["a"]
    ref = int(lz["ref"])
    n = len(gmean)

    y = np.log(gmean / gmean[ref])
    yc = np.log(core / core[ref])
    T = np.log(t / t[ref])
    Tr = np.log(tr / tr[ref])
    F = -2.0 * np.log(nef / nef[ref])
    Asc = -2.0 * np.log(a / a[ref])
    K = (np.arange(n) - ref) / n

    print("=" * 78)
    print("%s  n=%d  ref=%d" % (stack, n, ref))
    print("  whole-frame flux ratio  max/min = %.4f (%.4f stops)"
          % (gmean.max() / gmean.min(), np.log2(gmean.max() / gmean.min())))
    print("  central-third   ratio   max/min = %.4f (%.4f stops)"
          % (core.max() / core.min(), np.log2(core.max() / core.min())))
    print("  agreement whole vs core: corr(log) = %.5f, RMS gap = %.5f"
          % (np.corrcoef(y, yc)[0, 1], rms(y - yc)))

    s0 = rms(y)
    print()
    print("  residual RMS of log(whole-frame flux), natural log units")
    print("  %-48s %8s %8s" % ("model", "RMS", "vs null"))
    print("  %-48s %8.5f %8.3f" % ("M0  null", s0, 1.0))
    tbl = {"M0": s0}

    def show(name, resid):
        r = rms(resid)
        tbl[name.split()[0]] = r
        print("  %-48s %8.5f %8.3f" % (name, r, r / s0))

    show("M1  -2*log(a_k)              [brief's 1/m^2]", y - Asc)
    show("Me  log SonyExposureTime     [true shutter]", y - T)
    show("Mer log ExposureTime         [rounded EXIF]", y - Tr)
    show("Mf  -2*log SonyFNumber2      [effective f/#]", y - F)
    show("Mef T + F  [no free parameters, metadata only]", y - T - F)
    show("Mea T + (-2 log a_k)", y - T - Asc)

    s_q, b_q = ols(y - T, [np.log(a / a[ref])])
    print("  %-48s %8.5f %8.3f  q=%+.3f"
          % ("M2  T + q*log a_k, q free", s_q, s_q / s0, b_q[1]))
    s_p, b_p = ols(y - T, [np.log(nef / nef[ref])])
    print("  %-48s %8.5f %8.3f  p=%+.3f"
          % ("M2f T + p*log N_eff, p free", s_p, s_p / s0, b_p[1]))
    s_k, b_k = ols(y - T, [K])
    print("  %-48s %8.5f %8.3f  slope=%+.4f"
          % ("M4  T + c*time", s_k, s_k / s0, b_k[1]))

    print()
    print("  PR-4 negative control (%d shuffles):" % N_SHUFFLE)
    ctrl = {}
    for nm, reg in (("M1  -2 log a_k", Asc), ("Mf  -2 log N_eff", F),
                    ("Mef T + F", T + F)):
        true_r = rms(y - reg)
        sh = np.array([rms(y - reg[RNG.permutation(n)])
                       for _ in range(N_SHUFFLE)])
        p1 = float(np.percentile(sh, 1.0))
        ctrl[nm] = (true_r, p1)
        print("    %-20s true %.5f | shuffled 1st pct %.5f | %s"
              % (nm, true_r, p1, "HAS POWER" if true_r < p1 else "NO POWER"))

    # The per-frame gain the merge would apply if it normalised to the
    # reference frame using the whole-frame flux, and using metadata only.
    g_meas = gmean[ref] / gmean
    g_meta = np.exp(-(T + F))
    print()
    print("  per-frame gain to normalise to the reference frame:")
    print("    measured (flux)   : %.4f .. %.4f" % (g_meas.min(), g_meas.max()))
    print("    metadata (T+F)    : %.4f .. %.4f" % (g_meta.min(), g_meta.max()))
    print("    metadata error    : max |g_meta/g_meas - 1| = %.4f"
          % np.abs(g_meta / g_meas - 1).max())

    return {"stack": stack, "n": n, "ref": ref, "s0": s0, "tbl": tbl,
            "q": float(b_q[1]), "p": float(b_p[1]),
            "gmean": gmean.tolist(), "core": core.tolist(),
            "t": t.tolist(), "nef": nef.tolist(), "a": a.tolist(),
            "g_meas": g_meas.tolist(), "g_meta": g_meta.tolist(),
            "files": files}


if __name__ == "__main__":
    out = {}
    for s in sys.argv[1:] or ["bee-3-cpl", "lavendar-cpl", "leaf-2-cpl",
                              "bee-2-cpl"]:
        out[s] = analyse(s)
        print()
    with open(os.path.join(HERE, "data", "phaseB-flux.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f)
    print("wrote data/phaseB-flux.json")
