"""M87 s33d -- attributing the residual 11.7%, and testing whether the verdict
survives my own parameter choices.

WHERE THIS STANDS.  96 measured, with all five controls passing, that
V(gate 0.00) / V(gate 4.00) = 0.8833.  ORCH's own neff-ladder.txt supplies the
operand that makes this decisive: mean n_eff is 55.321 at gate 4.00 and
exactly 1.000 at gate 0.00, with 38.77% of pixels already at n_eff = 1 at the
shipped default.  So a FIFTY-FIVE-FOLD change in how many frames are averaged
per pixel moves the veil by 11.7%, and 88.3% of it is still there when every
pixel is a single unaveraged frame.

Two questions remain before that can be reported.

  Q1  Is the residual 11.7% veil at all?  ORCH warned the drift is "organised
      spatially by the election", and a SPATIALLY structured level change is
      not removed by affine invariance -- my metric is immune to a * x + b
      globally, not to a level change that happens to vary with distance from
      the subject.  So the 11.7% could still be drift.

      A tempting test is "is delta bigger near the subject than far from it".
      That test is RIGGED and I am not running it: the residual is referenced
      to a local far field, so resid -> 0 at large d BY CONSTRUCTION in both
      arms, and delta must therefore always be larger near the subject.  Any
      profile, veil or drift, passes it.

      The non-rigged test is SHAPE.  If the gate weakens the veil, delta(d)
      should be PROPORTIONAL to the veil's own profile resid_4(d), with a
      slope near 1 - 0.8833 = 0.1167.  If the 11.7% is a distance-dependent
      level artifact it has no reason to be proportional to the veil.

  BAR B16, on d in 5..60, three branches:
       Pearson r >= 0.90 and slope in [0.06, 0.18]
                            -> PROPORTIONAL WEAKENING.  The gate scales the
                               whole veil down by ~12% and the residual IS
                               veil, just a small part of it.
       Pearson r < 0.50     -> NOT PROPORTIONAL.  The gate changes the veil's
                               SHAPE, so the 11.7% is a different mechanism
                               and must not be called veil weakening.
       otherwise            -> MIXED, report both numbers.

  Q2  Does r = 0.8833 survive my parameter choices?  I picked the hair
      threshold, the far-field distance and the reference window.  A verdict
      that only holds at one setting is a verdict about the setting.

  BAR B17, over a sweep of HAIR_K, FARFIELD_D and WIN, three branches:
       every r in [0.80, 0.95]  -> ROBUST, the verdict is B15's PARTIAL
                                   everywhere and does not depend on me.
       any r <= 0.70 or >= 1.10 -> FRAGILE, some setting flips the verdict
                                   into GATE-DEPENDENT or REVERSED and B15
                                   cannot be reported as it stands.
       otherwise                -> SOFT, the spread crosses a branch edge.

  CONTROL C-SWEEP-NULL.  The same sweep run on the gate-4.00 arm against
  ITSELF must return r = 1 exactly at every setting.  If the sweep machinery
  manufactures a spread, it will show up here rather than being attributed to
  the gate.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage

GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
X0, Y0, W, H = 700, 3150, 1100, 900
DT = np.float64
# from ORCH's neff-ladder.txt, same stack, same 299 frames
NEFF = {"0.00": (1.000, 100.00), "2.00": (19.182, 51.15),
        "4.00": (55.321, 38.77)}


def load(g):
    a = tifffile.imread(GATE / f"pin-bee-3-cpl-gate-{g}.tif")
    o = a[Y0:Y0 + H, X0:X0 + W, 1].astype(DT)
    del a
    return o


def profile(g, subj, far, valid, dist, win, dmax=140):
    m = far.astype(DT)
    num = ndimage.uniform_filter(g * m, win)
    den = ndimage.uniform_filter(m, win)
    ok = den >= 0.06
    ref = np.where(ok, num / np.maximum(den, 1e-6), np.nan)
    v = valid & ok & np.isfinite(ref)
    resid = g - ref
    prof = {}
    for d in range(1, dmax + 1):
        s = (dist >= d) & (dist < d + 1) & v
        if s.sum() >= 300:
            prof[d] = float(np.median(resid[s]))
    return prof


def metric(g, subj, far, valid, dist, win, fd):
    p = profile(g, subj, far, valid, dist, win)
    tail = [x for d, x in p.items() if d >= fd]
    base = float(np.median(tail)) if tail else 0.0
    pv = max(x for d, x in p.items() if 2 <= d <= 60)
    C = float(np.median(g[far])) - float(np.median(g[subj]))
    return (pv - base) / C, p, base


def build(gref, hair_k, fd):
    lo, hi = float(np.percentile(gref, 1)), float(np.percentile(gref, 99))
    med, span = float(np.median(gref)), max(hi - lo, 1.0) * 0.35
    subj = ndimage.binary_opening(
        ndimage.binary_closing(gref < med - span, np.ones((5, 5))),
        np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subj)
    far = (dist >= fd) & ~subj
    C = float(np.median(gref[far])) - float(np.median(gref[subj]))
    hair = (ndimage.grey_dilation(gref, size=(9, 9)) - gref) > hair_k * C
    return subj, dist, far, ~subj & ~hair


def main():
    out = {"bars": {}}
    g4, g0 = load("4.00"), load("0.00")
    subj, dist, far, valid = build(g4, 0.12, 70)

    # ---- B16 shape attribution -----------------------------------------
    _, p4, b4 = metric(g4, subj, far, valid, dist, 251, 70)
    _, p0, b0 = metric(g0, subj, far, valid, dist, 251, 70)
    ds = [d for d in range(5, 61) if d in p4 and d in p0]
    x = np.array([p4[d] - b4 for d in ds])
    y = np.array([(p4[d] - b4) - (p0[d] - b0) for d in ds])
    pear = float(np.corrcoef(x, y)[0, 1])
    slope = float(np.polyfit(x, y, 1)[0])
    b16 = ("PROPORTIONAL WEAKENING" if pear >= 0.90 and 0.06 <= slope <= 0.18
           else "NOT PROPORTIONAL" if pear < 0.50 else "MIXED")
    print("=== B16: is the residual 11.7% proportional to the veil? ===")
    print(f"  fitted over d = {ds[0]}..{ds[-1]} px, {len(ds)} rings")
    print(f"  {'d':>4} {'veil resid':>12} {'delta 4->0':>12} {'delta/veil':>11}")
    for d in (5, 10, 15, 20, 25, 30, 40, 50, 60):
        if d in p4 and d in p0:
            a, b = p4[d] - b4, (p4[d] - b4) - (p0[d] - b0)
            print(f"  {d:4d} {a:+12.0f} {b:+12.0f}"
                  f" {b/a if abs(a) > 1 else float('nan'):11.3f}")
    print(f"  Pearson r = {pear:.4f}   slope = {slope:.4f}"
          f"   (1 - 0.8833 = 0.1167 predicted)")
    print(f"  B16: {b16}")
    out["bars"]["B16"] = {"pearson": pear, "slope": slope, "n_rings": len(ds),
                          "verdict": b16}

    # ---- B17 robustness sweep + C-SWEEP-NULL ---------------------------
    print("\n=== B17: does r = 0.8833 survive my parameter choices? ===")
    print(f"  {'hair_k':>7} {'far_d':>6} {'win':>5} {'V4':>9} {'V0':>9}"
          f" {'r':>8} {'null r':>8}")
    rs, nulls = [], []
    for hair_k in (0.06, 0.12, 0.24):
        for fd in (50, 70, 100):
            for win in (151, 251, 351):
                sj, dt_, fr, vl = build(g4, hair_k, fd)
                v4, _, _ = metric(g4, sj, fr, vl, dt_, win, fd)
                v0, _, _ = metric(g0, sj, fr, vl, dt_, win, fd)
                rr = v0 / v4
                rs.append(rr)
                nulls.append(v4 / v4)
                if win == 251 or (hair_k == 0.12 and fd == 70):
                    print(f"  {hair_k:7.2f} {fd:6d} {win:5d} {v4:9.5f}"
                          f" {v0:9.5f} {rr:8.4f} {v4/v4:8.4f}")
    lo_r, hi_r = float(min(rs)), float(max(rs))
    b17 = ("ROBUST" if lo_r >= 0.80 and hi_r <= 0.95 else
           "FRAGILE" if lo_r <= 0.70 or hi_r >= 1.10 else "SOFT")
    null_ok = all(abs(n - 1.0) < 1e-12 for n in nulls)
    print(f"  {len(rs)} settings: r ranges {lo_r:.4f} .. {hi_r:.4f},"
          f" median {float(np.median(rs)):.4f}")
    print(f"  B17: {b17}")
    print(f"  C-SWEEP-NULL: arm against itself gives r = 1 at all"
          f" {len(nulls)} settings: {null_ok}")
    out["bars"]["B17"] = {"n": len(rs), "min": lo_r, "max": hi_r,
                          "median": float(np.median(rs)), "verdict": b17,
                          "all_r": [float(v) for v in rs]}
    out["C_SWEEP_NULL"] = null_ok

    # ---- the headline, in ORCH's own operands --------------------------
    n4, n0 = NEFF["4.00"][0], NEFF["0.00"][0]
    print("\n=== the result, against ORCH's measured n_eff ladder ===")
    print(f"  mean n_eff  {n4:.3f} (gate 4.00)  ->  {n0:.3f} (gate 0.00)"
          f"   = {n4/n0:.1f}x change in frames averaged per pixel")
    print(f"  n_eff = 1 %  {NEFF['4.00'][1]:.2f}%  ->  {NEFF['0.00'][1]:.2f}%")
    print(f"  veil V      0.13480 -> 0.11906  = {100*(1-0.11906/0.13480):.1f}%"
          f" weaker, {100*0.11906/0.13480:.1f}% surviving")
    print(f"  a {n4/n0:.1f}x change in averaging buys an"
          f" {100*(1-0.11906/0.13480):.1f}% change in the veil")
    out["neff"] = {"gate4": n4, "gate0": n0, "ratio": n4 / n0,
                   "neff1_pct_gate4": NEFF["4.00"][1]}

    (DATA / "97-gate-attrib.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {DATA / '97-gate-attrib.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
