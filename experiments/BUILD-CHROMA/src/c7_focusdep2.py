"""Is red's focus dependence real, or is it field radius wearing a disguise?

THE PROBLEM c6 LEFT. c6 found eps_R drifts with frame index, same sign on five of
six stacks, t = 2.2-4.3, worth 0.26 px at the corner across a bracket -- which is
3.6x the residual a good fixed coefficient leaves, so if it is real it is the
dominant remaining error and no per-stack scalar can remove it.

But c6's control was the green null, and by this project's own rule 4 that is not
a control on this axis. Tiles do not elect frames at random: near subject matter
sits at one end of the bracket and far at the other, and in these scenes that
correlates with field radius. So a purely RADIAL mis-fit -- eps not quite linear
in r -- would print as focus dependence. The green null cannot reveal that,
because the null's eps is ~0, so there is no radial term there to mis-fit. A
control that cannot exhibit the failure mode is not a control for it.

THE FIX: FIT BOTH TERMS AT ONCE. Let the coefficient vary in frame index and in
radius simultaneously,

    d_i = (eps0 + k * fc_i + m * rc_i) * u_i + T

with fc and rc the centred frame index and centred radius of tile i. This is
linear in (eps0, k, m, Tx, Ty), 5 parameters over 2n equations, so it is an
ordinary least-squares problem and the two terms compete on equal footing. If k
survives with m in the model, frame index carries information that radius does
not, and the focus dependence is real.

THE SECOND, NON-PARAMETRIC CHECK. Inside a narrow annulus, tiles at essentially
the same radius still elect different frames, because at one radius there is
still near and far subject matter. Regressing eps on frame within an annulus is
a contrast radius cannot produce. If the slope survives there too, it is real.

THE COMMISSIONING, WHICH IS THE POINT. A new parameter needs the same treatment
the estimator itself got, and neither arm is optional:

  PLANTED ZERO   synthesise displacements from a CONSTANT eps on the REAL tile
                 geometry and the REAL elected frames, so the frame/radius
                 confound is present in full, and require k to come back zero.
                 If the confound alone can manufacture a k, the whole finding is
                 the confound and this file says so.
  PLANTED LADDER synthesise a KNOWN k and require it back. A parameter that
                 cannot be recovered when it is really there cannot be trusted
                 when it appears.

Both are run on each stack's own geometry rather than a convenient one, because
the confound is a property of the geometry and differs between stacks.
"""

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import lateral

PPM = 1e6
R_CORNER = 2112.0
RNG = np.random.default_rng(20240607)


def design(u, fc, rc):
    """Stack the x and y rows of d = (eps0 + k*fc + m*rc) * u + T."""
    n = len(u)
    A = np.zeros((2 * n, 5))
    A[0::2, 0] = u[:, 1]              # eps0 * u_x
    A[0::2, 1] = fc * u[:, 1]         # k    * fc * u_x
    A[0::2, 2] = rc * u[:, 1]         # m    * rc * u_x
    A[0::2, 3] = 1.0                  # Tx
    A[1::2, 0] = u[:, 0]              # eps0 * u_y
    A[1::2, 1] = fc * u[:, 0]
    A[1::2, 2] = rc * u[:, 0]
    A[1::2, 4] = 1.0                  # Ty
    return A


def fit(u, d, fc, rc, cols=(0, 1, 2, 3, 4)):
    """OLS with standard errors, optionally dropping columns from the model."""
    A = design(u, fc, rc)[:, list(cols)]
    b = np.empty(2 * len(u))
    b[0::2] = d[:, 1]
    b[1::2] = d[:, 0]
    p, *_ = np.linalg.lstsq(A, b, rcond=None)
    res = b - A @ p
    dof = len(b) - A.shape[1]
    s2 = res @ res / dof
    cov = s2 * np.linalg.pinv(A.T @ A)
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    full = dict(zip(cols, p))
    fse = dict(zip(cols, se))
    return {
        "eps0": full.get(0, 0.0), "k": full.get(1, 0.0), "m": full.get(2, 0.0),
        "k_se": fse.get(1, np.nan), "m_se": fse.get(2, np.nan),
        "rms": float(np.sqrt(res @ res / len(b))),
    }


def load(stack, ch):
    p = os.path.join(common.OUT, "json", f"c1_{stack}_{ch}.npz")
    z = np.load(p)
    u, d, f = z["u"], z["d"], z["best_frame"].astype(float)
    r = np.hypot(u[:, 0], u[:, 1])
    # Centre the modulators so eps0 stays interpretable as the coefficient at
    # the mean frame and mean radius rather than at frame 0 / the optical axis.
    return u, d, f - f.mean(), r - r.mean(), f, r


def grouped_k(u, d, f, min_tiles=15):
    """Replicate c6's estimator exactly: fit eps per elected frame, then regress.

    This matters, twice over.

    First, c7's original draft commissioned the per-tile joint fit instead, found
    k unidentifiable, and nearly retracted c6 on the strength of it -- but they
    are not the same instrument. A single tile's displacement scatters by
    0.11-0.56 px while the focus modulation k*fc*u is ~0.08 px, so per-tile k is
    buried; grouping ~30 tiles per frame before regressing buys sqrt(30) and is
    why c6 saw t = 3-4.

    Second, the per-group fit has to be the ROBUST one. c1 fits every group with
    IRLS/Tukey and c7's second draft used plain OLS, which on groups of 15-50
    tiles containing the occasional phase-correlation failure scatters ~30x
    worse -- it read the real data at 45 ppm/frame where c6 reads 1.6. That is
    not a disagreement about the data, it is a different instrument. An estimator
    must be commissioned as it is actually used, down to the loss function.
    """
    rows = []
    for fr in np.unique(f):
        s = f == fr
        if s.sum() < min_tiles:
            continue
        g = lateral.fit_model(u[s], d[s], robust=True)
        rows.append((fr, g["eps"], s.sum()))
    if len(rows) < 4:
        return None
    x = np.array([r[0] for r in rows], float)
    y = np.array([r[1] for r in rows])
    w = np.array([r[2] for r in rows], float)
    W = w / w.sum()
    xm, ym = (W * x).sum(), (W * y).sum()
    sxx = (W * (x - xm) ** 2).sum()
    b = (W * (x - xm) * (y - ym)).sum() / sxx
    res = y - (ym + b * (x - xm))
    dof = len(x) - 2
    se = np.sqrt((W * res ** 2).sum() * len(x) / dof / (sxx * len(x)))
    return {"k": float(b), "se": float(se), "t": float(b / se),
            "n_groups": len(x), "span": float(x.max() - x.min())}


def main():
    stacks = sorted(os.path.basename(p)[len("c1_lateral_"):-len(".json")]
                    for p in glob.glob(os.path.join(common.OUT, "json",
                                                    "c1_lateral_*.json")))
    out = {"joint": [], "annulus": [], "commission": []}

    print("=" * 112)
    print("JOINT FIT: does the focus slope k survive with a radial slope m in "
          "the model?")
    print("  k is in ppm per frame; 'drift' is k x bracket span, in corner "
          "plane px.")
    print("=" * 112)
    print(f"{'stack':>18} {'ch':>3} {'n':>4} {'corr(f,r)':>10} "
          f"{'k alone':>9} {'t':>6} {'k with m':>9} {'t':>6} "
          f"{'m':>10} {'t':>6} {'drift px':>9}")
    for st in stacks:
        for ch in ("R", "B", "G2"):
            u, d, fc, rc, f, r = load(st, ch)
            cfr = float(np.corrcoef(f, r)[0, 1])
            a = fit(u, d, fc, rc, cols=(0, 1, 3, 4))      # no radial term
            b = fit(u, d, fc, rc, cols=(0, 1, 2, 3, 4))   # both
            span = f.max() - f.min()
            drift = abs(b["k"]) * span * R_CORNER
            rec = {"stack": st, "ch": ch, "n": len(u), "corr_fr": cfr,
                   "k_alone_ppm": a["k"] * PPM, "t_alone": a["k"] / a["k_se"],
                   "k_joint_ppm": b["k"] * PPM, "t_joint": b["k"] / b["k_se"],
                   "m_joint_ppm_per_px": b["m"] * PPM,
                   "t_m": b["m"] / b["m_se"],
                   "eps0_ppm": b["eps0"] * PPM, "span": float(span),
                   "drift_corner_px": float(drift)}
            out["joint"].append(rec)
            print(f"{st:>18} {ch:>3} {len(u):4d} {cfr:10.2f} "
                  f"{a['k']*PPM:9.3f} {a['k']/a['k_se']:6.1f} "
                  f"{b['k']*PPM:9.3f} {b['k']/b['k_se']:6.1f} "
                  f"{b['m']*PPM:10.5f} {b['m']/b['m_se']:6.1f} {drift:9.3f}")
        print()

    print("=" * 112)
    print("WITHIN-ANNULUS CONTRAST: middle 50% of tiles by radius, so radius is "
          "nearly constant")
    print("=" * 112)
    print(f"{'stack':>18} {'ch':>3} {'n':>4} {'r range':>14} "
          f"{'corr(f,r)':>10} {'k':>9} {'t':>6}")
    for st in stacks:
        for ch in ("R", "B", "G2"):
            u, d, fc, rc, f, r = load(st, ch)
            lo, hi = np.quantile(r, [0.25, 0.75])
            s = (r >= lo) & (r <= hi)
            if s.sum() < 30:
                continue
            fs = f[s] - f[s].mean()
            rs = r[s] - r[s].mean()
            g = fit(u[s], d[s], fs, rs, cols=(0, 1, 3, 4))
            rec = {"stack": st, "ch": ch, "n": int(s.sum()),
                   "r_lo": float(lo), "r_hi": float(hi),
                   "corr_fr": float(np.corrcoef(f[s], r[s])[0, 1]),
                   "k_ppm": g["k"] * PPM, "t": g["k"] / g["k_se"]}
            out["annulus"].append(rec)
            print(f"{st:>18} {ch:>3} {s.sum():4d} "
                  f"{lo:6.0f}-{hi:<7.0f} {rec['corr_fr']:10.2f} "
                  f"{g['k']*PPM:9.3f} {rec['t']:6.1f}")
        print()

    print("=" * 112)
    print("COMMISSIONING c6's GROUPED k ON EACH STACK'S OWN GEOMETRY")
    print("  Displacements are SYNTHESISED on the real u and the real elected")
    print("  frames, so the frame/radius confound is present in full, then")
    print("  c6's own grouped estimator is asked to read k back.")
    print()
    print("  ARMS.  zero      constant eps. k must be 0.")
    print("         radial    eps varies with RADIUS, not with focus. This is")
    print("                   the confound in its pure form: if grouped k reads")
    print("                   nonzero here, c6's slope is radius in disguise")
    print("                   and the finding is dead.")
    print("         k=...     a real planted focus slope, which must come back.")
    print("=" * 112)
    print(f"{'stack':>18} {'arm':>10} {'noise px':>9} {'planted':>8} "
          f"{'read k':>9} {'recovery':>9} {'t':>6}")
    for st in stacks:
        u, d, fc, rc, f, r = load(st, "R")
        base = fit(u, d, fc, rc, cols=(0, 1, 2, 3, 4))
        sd = base["rms"]
        # Size the radial-nonlinearity plant from what the data actually shows,
        # so the confound arm is dosed at a realistic strength rather than a
        # flattering one: the joint fit's own m, doubled.
        m_real = abs(base["m"]) * 2.0
        arms = [("zero", 0.0, 0.0), ("zero", 0.0, 0.0),
                ("radial", 0.0, m_real), ("radial", 0.0, 2 * m_real),
                ("k=0.5", 0.5e-6, 0.0), ("k=1.0", 1.0e-6, 0.0),
                ("k=2.0", 2.0e-6, 0.0), ("k=4.0", 4.0e-6, 0.0)]
        for name, k_true, m_true in arms:
            eps = -650e-6 + k_true * fc + m_true * rc
            ds = u * eps[:, None] + RNG.normal(0, sd, u.shape)
            g = grouped_k(u, ds, f)
            if g is None:
                continue
            rec = {"stack": st, "arm": name, "planted_k_ppm": k_true * PPM,
                   "planted_m_ppm_per_px": m_true * PPM, "noise_px": sd,
                   "read_k_ppm": g["k"] * PPM, "t": g["t"],
                   "recovery": (g["k"] / k_true) if k_true else None}
            out["commission"].append(rec)
            recs = f"{rec['recovery']:9.3f}" if k_true else f"{'--':>9}"
            pl = (f"{k_true*PPM:8.2f}" if k_true
                  else f"{m_true*PPM:8.4f}")
            print(f"{st:>18} {name:>10} {sd:9.4f} {pl} "
                  f"{g['k']*PPM:9.3f} {recs} {g['t']:6.1f}")
        print()

    z = [abs(c["read_k_ppm"]) for c in out["commission"]
         if c["arm"] == "zero"]
    rad = [abs(c["read_k_ppm"]) for c in out["commission"]
           if c["arm"] == "radial"]
    lad = [c for c in out["commission"] if c["planted_k_ppm"] > 0]
    xs = np.array([c["planted_k_ppm"] for c in lad])
    ys = np.array([c["read_k_ppm"] for c in lad])
    slope = float(np.polyfit(xs, ys, 1)[0])
    # c6's measured red slopes, from the same grouped path on real data.
    meas = []
    for st in stacks:
        u, d, fc, rc, f, r = load(st, "R")
        g = grouped_k(u, d, f)
        if g:
            meas.append(abs(g["k"]) * PPM)
    print("=" * 112)
    print("VERDICT")
    print("=" * 112)
    print(f"  planted ZERO   worst |k| {max(z):.3f} ppm/frame over {len(z)} runs")
    print(f"  planted RADIAL worst |k| {max(rad):.3f} ppm/frame over "
          f"{len(rad)} runs  <- the confound, dosed at 1x and 2x what the data "
          f"shows")
    print(f"  planted LADDER slope {slope:.3f} over {len(lad)} runs "
          f"(1.000 = unbiased)")
    print(f"  MEASURED red   mean |k| {np.mean(meas):.3f} ppm/frame "
          f"(per stack: {', '.join(f'{v:.2f}' for v in meas)})")
    ceil = max(max(z), max(rad))
    print(f"\n  measured / worst false positive = "
          f"{np.mean(meas)/ceil:.2f}x")
    print("  Above ~3x the finding stands. Near or below 1x it is the")
    print("  instrument, and c6's focus dependence must be withdrawn.")

    out["verdict"] = {"zero_worst_ppm": max(z), "radial_worst_ppm": max(rad),
                      "ladder_slope": slope,
                      "measured_mean_ppm": float(np.mean(meas)),
                      "ratio": float(np.mean(meas) / ceil)}

    common.dump("c7_focusdep2", out)
    print("\nwrote c7_focusdep2.json")


if __name__ == "__main__":
    main()
