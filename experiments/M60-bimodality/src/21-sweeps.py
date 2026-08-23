"""M60 — the remaining pre-registered arms.

  MC convergence   the rep count used for sigma_f was promised to be fixed by a
                   convergence check reported before use. It is reported here,
                   after the fact, and labelled as such.
  N2 permutation   M21's placebo. Permute the frame order per pixel; the
                   marginal is preserved exactly and only the ordering dies.
  R sweep          fact 152 says bimodality is depleted 0.36x at the shipped
                   R = 13. R = 2 is the registered primary; {1, 4, 8} are swept.
  H2 correlation   Spearman of |k2-k1| against the reference depth step.
"""

import os
import sys
import json
import time
import numpy as np
from scipy.ndimage import uniform_filter
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
from cells import CELLS, STACK_ISO  # noqa: E402
import importlib
A = importlib.import_module("12-analyse")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
SUBSET = ["occ3-wing-thorax", "occ3-limb-abdomen", "occ3-antenna-head",
          "occ3-leg-card-2", "ctl3-eye"]
RS = (1, 2, 4, 8)


def foc(a, r):
    return uniform_filter(L.sobel_mag(a), 2 * r + 1, mode="reflect")


def mc_convergence():
    print("=" * 78)
    print("MC convergence of sigma_f -- rep count used throughout is 12")
    print("=" * 78)
    stack, name = "bee-3", "occ3-limb-abdomen"
    rect = [c for c in CELLS if c[1] == name][0][3:]
    d = A.load(stack, name)
    sel = d["sel"]
    fs = L.frames(stack)
    a = L.load_green(fs[len(fs) // 2], tuple(rect))
    iso = STACK_ISO[stack]
    sd = L.sigma_dn(a, iso)
    ref = None
    out = []
    for reps in (6, 12, 24, 96):
        rng = np.random.default_rng(77)
        s1 = np.zeros(len(sel)); s2 = np.zeros(len(sel))
        for _ in range(reps):
            v = foc(a + rng.normal(0, 1, a.shape).astype(np.float32) * sd, 2).ravel()[sel]
            s1 += v; s2 += v.astype(np.float64) ** 2
        s = np.sqrt(np.maximum(s2 / reps - (s1 / reps) ** 2, 0) * reps / (reps - 1))
        if ref is None:
            ref0 = s
        ref = s
        out.append((reps, float(np.median(s))))
        print("   reps=%3d  median sigma_f = %8.5f DN" % (reps, np.median(s)))
    base = out[-1][1]
    for reps, v in out:
        print("   reps=%3d  deviation from reps=96: %+6.2f%%" % (reps, 100 * (v / base - 1)))
    return out


def n2_permutation():
    print()
    print("=" * 78)
    print("N2  frame-permutation placebo (M21's control), on the real curves")
    print("=" * 78)
    rows = []
    rng = np.random.default_rng(202)
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = A.load(stack, name)
        nd = A.load(stack, name, A.NUL)
        if d is None or nd is None:
            continue
        F, S, lab = d["F"], d["S"], d["lab"]
        band = lab == 0
        Fb, Sb = np.ascontiguousarray(F[:, band]), np.ascontiguousarray(S[:, band])
        n, P = Fb.shape
        idx = np.argsort(rng.random((n, P)), axis=0)
        Fp = np.take_along_axis(Fb, idx, 0)
        Sp = np.take_along_axis(Sb, idx, 0)
        real = A.detect(Fb, Sb)
        perm = A.detect(Fp, Sp)
        nul = A.detect(nd["F"][:, band], nd["S"][:, band])
        zst = float(np.percentile(nul["z"], 99))
        rows.append(dict(cell=name, cls=cls, hit=float(np.mean(real["z"] > zst)),
                         hit_perm=float(np.mean(perm["z"] > zst)),
                         sep=float(np.median(np.abs(real["k2"].astype(float) - real["k1"]))),
                         sep_perm=float(np.median(np.abs(perm["k2"].astype(float) - perm["k1"])))))
        print("   %-18s %-8s  real hit %5.1f%% sep %5.1f | permuted hit %5.1f%% sep %5.1f"
              % (name, cls, 100 * rows[-1]["hit"], rows[-1]["sep"],
                 100 * rows[-1]["hit_perm"], rows[-1]["sep_perm"]), flush=True)
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r for r in rows if r["cls"] == cls]
        print("   %-9s real %5.1f%%  permuted %5.1f%%" % (
            cls, 100 * np.median([r["hit"] for r in v]),
            100 * np.median([r["hit_perm"] for r in v])))
    return rows


def r_sweep():
    print()
    print("=" * 78)
    print("R sweep -- registered primary is R=2 (fact 152)")
    print("=" * 78)
    rows = []
    by_stack = {}
    for c in CELLS:
        if c[1] in SUBSET:
            by_stack.setdefault(c[0], []).append(c)
    for stack, cs in by_stack.items():
        iso = STACK_ISO[stack]
        fs = L.frames(stack)
        n = len(fs)
        sels = {c[1]: A.load(stack, c[1])["sel"] for c in cs}
        F = {(c[1], r): np.zeros((n, len(sels[c[1]])), np.float32) for c in cs for r in RS}
        S = {(c[1], r): np.zeros((n, len(sels[c[1]])), np.float32) for c in cs for r in RS}
        Fn = {(c[1], r): np.zeros((n, len(sels[c[1]])), np.float32) for c in cs for r in RS}
        base = L.load_green(fs[n // 2]).astype(np.float32)
        rng = np.random.default_rng(515)
        t0 = time.time()
        for k, f in enumerate(fs):
            P = L.load_green(f).astype(np.float32)
            for (_, name, _, y0, y1, x0, x1) in cs:
                a = P[y0:y1, x0:x1]
                ii = sels[name]
                sd = L.sigma_dn(a, iso)
                nz = rng.normal(0, 1, a.shape).astype(np.float32) * sd
                ab = base[y0:y1, x0:x1]
                nb = ab + rng.normal(0, 1, ab.shape).astype(np.float32) * L.sigma_dn(ab, iso)
                for r in RS:
                    F[(name, r)][k] = foc(a, r).ravel()[ii]
                    S[(name, r)][k] = np.abs(foc(a + nz, r).ravel()[ii]
                                             - F[(name, r)][k]) / 0.7979
                    Fn[(name, r)][k] = foc(nb, r).ravel()[ii]
            if k % 80 == 0:
                print("   %s frame %d/%d %.0fs" % (stack, k, n, time.time() - t0), flush=True)
        for (_, name, cls, y0, y1, x0, x1) in cs:
            for r in RS:
                re = A.detect(F[(name, r)], np.maximum(S[(name, r)], 1e-6))
                nu = A.detect(Fn[(name, r)], np.maximum(S[(name, r)], 1e-6))
                lab = A.load(stack, name)["lab"]
                band = lab == 0
                zst = float(np.percentile(nu["z"][band], 99))
                rows.append(dict(cell=name, cls=cls, R=r,
                                 hit=float(np.mean(re["z"][band] > zst)),
                                 sep=float(np.median(np.abs(re["k2"][band].astype(float)
                                                            - re["k1"][band])))))
                print("   %-18s %-8s R=%d  hit %5.1f%%  sep %5.1f"
                      % (name, cls, r, 100 * rows[-1]["hit"], rows[-1]["sep"]), flush=True)
    return rows


if __name__ == "__main__":
    out = {}
    out["mc"] = mc_convergence()
    out["n2"] = n2_permutation()

    print()
    print("=" * 78)
    print("H2  does |k2-k1| track the reference depth step?")
    print("=" * 78)
    with open(os.path.join(DATA, "20-audit.json"), encoding="utf-8") as fh:
        geo = json.load(fh)["geometry"]
    for cls in ("occ", "occ_flat", "ctl", None):
        v = [g for g in geo if cls is None or g["cls"] == cls]
        s = np.array([g["sep"] for g in v]); st = np.array([g["step"] for g in v])
        rho, p = spearmanr(s, st)
        print("   %-9s n=%2d  Spearman(|k2-k1|, |k_fg-k_bg|) = %+.3f  p=%.3g"
              % (cls or "ALL", len(v), rho, p))
        out.setdefault("h2", []).append(dict(cls=cls or "ALL", n=len(v),
                                             rho=float(rho), p=float(p)))
    out["r"] = r_sweep()
    with open(os.path.join(DATA, "21-sweeps.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote data/21-sweeps.json")
