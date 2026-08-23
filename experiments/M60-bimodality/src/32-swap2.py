"""32 -- S1 repaired, plus the real-data arm (T4) and frame density (T5).

31-swap.py's S1 was disqualified by its own pre-registered placebo (1.25,
outside M25's 1.00 +/- 0.15 band).  The cause is an implementation defect, not a
result: S1 used a single frame-INDEPENDENT sigma map derived from the temporal
mean, so permuting the frame order left the threshold behind.  At veiled pixels
the curve swings over 108 DN, so a permutation manufactures large frame-to-frame
jumps that a fixed absolute bar accepts.

The repair is the construction the noise model actually specifies: sigma is
predicted at EACH FRAME's own signal level, and the placebo permutes the
threshold together with the frames it belongs to.  The disqualified number is
reported alongside the repaired one; the pre-registered placebo is re-run and
must pass on its own terms.

Also runs, as registered in PREREGISTRATION-B.md section 4:
    T4  real data, M60's 25 hand-drawn cells (question 138)
    T5  frame density / the neighbour-adjacency defect (H-B)

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/M60-bimodality/src/32-swap2.py
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np
from scipy.ndimage import median_filter, sobel, uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import m60lib as L                                               # noqa: E402

DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
PLANT = os.path.join(DATA, "30-m25-plant.npz")
OUT = os.path.join(DATA, "32-swap2.txt")
OUTJ = os.path.join(DATA, "32-swap2.json")

MC_REPS = 16
FPR = 0.01
MIN_BIN = 500
POWER_BIN = 5000
SEED = 20260824

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def ff(g, R):
    """M21's focus field, verbatim."""
    gx = sobel(g, axis=1, mode='reflect') / 8.0
    gy = sobel(g, axis=0, mode='reflect') / 8.0
    return uniform_filter(np.sqrt(gx * gx + gy * gy), 2 * R + 1)


def multipeak(V, thr=0.04):
    """M21's detector, verbatim."""
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    mx = Vs.max(0)
    mn = Vs.min(0)
    rng = np.maximum(mx - mn, 1e-6)
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = (Vs[1:-1] > Vs[:-2] + thr * rng) & (Vs[1:-1] > Vs[2:] + thr * rng)
    return ispk.sum(0) >= 2, (mx - mn) / np.maximum(mx, 1e-6), np.argmax(Vs, 0)


def multipeak_abs(V, T):
    """The SAME function with `thr*rng` replaced by T, which may be per-frame.

    T broadcast-compatible with V.  Every other line is identical.
    """
    Vs = np.copy(V)
    Vs[1:-1] = (V[:-2] + 2 * V[1:-1] + V[2:]) / 4.0
    Tm = T[1:-1] if (np.ndim(T) == np.ndim(V) and np.shape(T)[0] == np.shape(V)[0]) else T
    ispk = np.zeros_like(Vs, bool)
    ispk[1:-1] = (Vs[1:-1] > Vs[:-2] + Tm) & (Vs[1:-1] > Vs[2:] + Tm)
    return ispk.sum(0) >= 2


def sigma_f_perframe(G, R, iso, reps, rng):
    """MC sd of the focus response, at EACH frame's own signal level."""
    out = np.empty(G.shape, np.float32)
    for k in range(G.shape[0]):
        out[k] = L.focus_sigma_mc(G[k], R, iso, reps, rng)
    return out


def solve_z(Vnull, Snull, target):
    lo, hi = 0.02, 80.0
    for _ in range(44):
        mid = 0.5 * (lo + hi)
        if multipeak_abs(Vnull, mid * Snull).mean() > target:
            lo = mid
        else:
            hi = mid
    return hi


def enrich(mp, hi, lo):
    if hi.sum() < MIN_BIN or lo.sum() < MIN_BIN:
        return float("nan"), float("nan"), float("nan")
    a = mp[hi].mean() * 100.0
    b = mp[lo].mean() * 100.0
    return a, b, a / max(b, 1e-9)


# ---------------------------------------------------------------------------
def plant_arm(rng0, res):
    d = np.load(PLANT)
    G = d["frames"]
    vf, af = d["visible_focus"], d["alpha_front"]
    iso = float(d["iso"])
    n = G.shape[0]

    V2 = np.stack([ff(G[k], 2) for k in range(n)])
    V13 = np.stack([ff(G[k], 13) for k in range(n)])
    _, c13, am13 = multipeak(V13)
    strong = c13 > 0.10
    tstep = (np.abs(np.gradient(vf)[0]) + np.abs(np.gradient(vf)[1])) >= 1.0
    tpartial = (af > 0.02) & (af < 0.98)
    veiled, smooth = strong & tpartial, strong & ~tstep & ~tpartial

    say("T1r  S1 REPAIRED -- per-frame sigma, placebo permutes the threshold")
    say(f"  power: veiled {int(veiled.sum())}, smooth {int(smooth.sum())}, "
        f"smaller {min(int(veiled.sum()), int(smooth.sum()))} "
        f"{'>= ' + str(POWER_BIN) + ' POWERED' if min(veiled.sum(), smooth.sum()) >= POWER_BIN else '< floor UNDERPOWERED'}")

    t0 = time.time()
    Sreal = sigma_f_perframe(G, 2, iso, MC_REPS, rng0)
    Ibar = G.mean(0)
    sdk = np.stack([L.sigma_dn(G[k], iso) for k in range(n)])
    Vnull = np.stack([ff(Ibar + rng0.normal(0, 1, Ibar.shape).astype(np.float32) * sdk[k], 2)
                      for k in range(n)])
    Snull = np.stack([L.focus_sigma_mc(Ibar, 2, iso, MC_REPS, rng0)
                      for _ in range(1)] * n)
    say(f"  sigma_f per frame: median {np.median(Sreal):.3f} DN "
        f"(min-frame {np.median(Sreal, axis=(1,2)).min():.3f}, "
        f"max-frame {np.median(Sreal, axis=(1,2)).max():.3f}); "
        f"MC {MC_REPS} reps, {time.time()-t0:.0f}s")

    z1 = solve_z(Vnull, Snull, FPR)
    say(f"  z* = {z1:.3f} at {FPR*100:.0f}% FPR "
        f"(null rate {multipeak_abs(Vnull, z1*Snull).mean()*100:.2f}%)")

    perm = rng0.permutation(n)
    mp = multipeak_abs(V2, z1 * Sreal)
    mpp = multipeak_abs(V2[perm], z1 * Sreal[perm])     # threshold travels with the frame
    a, b, e = enrich(mp, veiled, smooth)
    _, _, pe = enrich(mpp, veiled, smooth)
    base = mp[strong].mean() * 100.0
    say(f"  S1r: veiled {a:.2f}%  smooth {b:.2f}%  enrich {e:.2f}x  "
        f"placebo {pe:.2f}  base {base:.1f}%")
    ok = abs(pe - 1.0) <= 0.15 and base <= 90.0
    say(f"  invalidating conditions: placebo "
        f"{'OK' if abs(pe-1.0)<=0.15 else 'OUT OF BAND -> S1r DISQUALIFIED'}, "
        f"base {'OK' if base <= 90 else 'SATURATED'}")
    res["plant_S1r"] = dict(veiled=a, smooth=b, enrich=e, placebo=pe,
                            base=base, z=z1, admissible=bool(ok))
    say()
    return res


# ---------------------------------------------------------------------------
def real_arm(rng0, res):
    say("T4  REAL DATA -- M60's 25 hand-drawn cells (question 138)")
    say("    labels assigned from intensity and geometry only, never from the")
    say("    focus volume.  Band pixels only; unit of analysis is the CELL.")
    files = sorted(glob.glob(os.path.join(DATA, "curves", "*.npz")))
    rows = []
    for fp in files:
        d = np.load(fp)
        cls = str(d["cls"][0])
        if cls not in ("occ", "occ_flat", "ctl"):
            continue
        F, S, lab = d["F"], d["S"], d["lab"]
        band = lab == 1
        if band.sum() < 2000:
            continue
        Fb, Sb = F[:, band], S[:, band]
        name = os.path.basename(fp)[:-4]

        # noise-only null at this cell's own levels, for z*
        Ib = Fb.mean(0, keepdims=True)
        Vn = Ib + rng0.normal(0, 1, Fb.shape).astype(np.float32) * Sb
        z1 = solve_z(Vn, Sb, FPR)

        s0 = multipeak(Fb)[0]
        s1 = multipeak_abs(Fb, z1 * Sb)
        r = L.second_peak(Fb[:, :, None])
        zz, prom, den, _ = L.prominence_z(Fb[:, :, None], Sb[:, :, None], r)
        rn = L.second_peak(Vn[:, :, None])
        zn, _, _, _ = L.prominence_z(Vn[:, :, None], Sb[:, :, None], rn)
        z2 = float(np.quantile(zn, 1.0 - FPR))
        s2 = (zz > z2)[:, 0]

        rows.append(dict(cell=name, cls=cls, n=int(band.sum()),
                         s0=float(s0.mean() * 100), s1=float(s1.mean() * 100),
                         s2=float(s2.mean() * 100),
                         rng=float(np.median(Fb.max(0) - Fb.min(0)))))
    say()
    say(f"  {'cell':<34}{'class':<10}{'n':>7}{'S0%':>8}{'S1%':>8}{'S2%':>8}{'rng DN':>9}")
    for r in rows:
        say(f"  {r['cell']:<34}{r['cls']:<10}{r['n']:>7}{r['s0']:8.1f}"
            f"{r['s1']:8.1f}{r['s2']:8.1f}{r['rng']:9.1f}")
    say()
    say(f"  {'class':<10}{'cells':>7}{'S0%':>9}{'S1%':>9}{'S2%':>9}{'rng DN':>10}")
    med = {}
    for c in ("occ", "occ_flat", "ctl"):
        g = [r for r in rows if r["cls"] == c]
        if not g:
            continue
        med[c] = {k: float(np.median([r[k] for r in g]))
                  for k in ("s0", "s1", "s2", "rng")}
        say(f"  {c:<10}{len(g):>7}{med[c]['s0']:9.1f}{med[c]['s1']:9.1f}"
            f"{med[c]['s2']:9.1f}{med[c]['rng']:10.1f}")
    say()
    say("  occ:ctl ratio by statistic -- the registered sign test:")
    for k, nm in (("s0", "S0 (M21 verbatim)"), ("s1", "S1 (noise-thresholded)"),
                  ("s2", "S2 (M60 prominence)")):
        rr = med["occ"][k] / max(med["ctl"][k], 1e-9)
        say(f"    {nm:<28}{rr:6.2f}x")
    say(f"    median curve range occ {med['occ']['rng']:.1f} DN vs "
        f"ctl {med['ctl']['rng']:.1f} DN = "
        f"{med['occ']['rng']/max(med['ctl']['rng'],1e-9):.2f}x "
        f"(S0's denominator, on real data)")
    res["real"] = dict(rows=rows, med=med)
    say()
    return res


# ---------------------------------------------------------------------------
def density_arm(rng0, res):
    say("T5  FRAME DENSITY -- H-B, the neighbour-adjacency defect")
    say("    M21's peak test compares IMMEDIATE frame neighbours, so its")
    say("    sensitivity depends on the focus step.  Decimating a 299-frame")
    say("    stack holds the scene and the noise fixed and varies only n.")
    files = sorted(glob.glob(os.path.join(DATA, "curves", "bee-3__*.npz")))
    say()
    say(f"  {'cell':<28}{'class':<10}" + "".join(f"{('n='+str(n)):>9}"
                                                 for n in (299, 150, 75, 38, 23)))
    rows = []
    for fp in files:
        d = np.load(fp)
        cls = str(d["cls"][0])
        F, lab = d["F"], d["lab"]
        band = lab == 1
        if band.sum() < 2000:
            continue
        Fb = F[:, band]
        vals = []
        for nn in (299, 150, 75, 38, 23):
            idx = np.linspace(0, Fb.shape[0] - 1, nn).round().astype(int)
            vals.append(float(multipeak(Fb[idx])[0].mean() * 100))
        name = os.path.basename(fp)[:-4].split("__")[1]
        say(f"  {name:<28}{cls:<10}" + "".join(f"{v:9.1f}" for v in vals))
        rows.append(dict(cell=name, cls=cls, rates=vals))
    if rows:
        arr = np.array([r["rates"] for r in rows])
        say(f"  {'MEDIAN':<28}{'':<10}" + "".join(f"{v:9.1f}"
                                                  for v in np.median(arr, 0)))
        m = np.median(arr, 0)
        say()
        say(f"  S0 rate at n=299 is {m[0]:.1f}% and at n=23 is {m[-1]:.1f}% "
            f"-> {m[-1]/max(m[0],1e-9):.1f}x")
        say("  H-B predicts the rate FALLS as n rises. "
            + ("CONFIRMED." if m[0] < m[-1] else "NOT confirmed."))
    res["density"] = rows
    say()
    return res


def main() -> None:
    t0 = time.time()
    rng0 = np.random.default_rng(SEED)
    res = {}
    say("M60b/32 -- S1 repaired, real-data arm, frame density")
    say("PRE-REGISTERED PREREGISTRATION-B.md section 4, commit b28b2e3.")
    say()
    res = plant_arm(rng0, res)
    res = real_arm(rng0, res)
    res = density_arm(rng0, res)
    say(f"total {time.time()-t0:.0f}s")
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(OUTJ, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
