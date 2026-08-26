"""Occluding-edge analysis at the bean silhouette: sharpness AND occlusion halo.

NO RESAMPLING of either arm.  Profiles are integer pixel picks along image rows
(near-vertical edges) or columns (near-horizontal edges) in each arm's OWN grid.
The only interpolation is 1-D root finding for the 10%/90% crossings on samples
already measured, which adds no blur.

LINEAR LIGHT.  strehl's tone rendering is inverted first (arms.strehl_arm);
prior is linear Rec.2020 as written.  Comparing shipped display values would
measure strehl's 0.55 display S-curve, not its edges.

PER-PROFILE NORMALISATION.  Each profile is mapped to [0,1] by its own two
asymptotes, so exposure, white point and channel gain cancel and only edge SHAPE
survives.

FOOLING DIRECTIONS (rule 18):
  rise10_90 falls with genuine sharpness AND with an unsharp rim -> always read
    it beside the overshoot columns.
  overshoot rises with a real occlusion halo AND with capture sharpening in the
    prior arm's develop step; it is attributable to the PIPELINE, not the merge.
    It is SUPPRESSED BY CLIPPING, so any profile touching a clipped pixel in
    either arm is discarded -- otherwise the prior arm wins by being blown out.
WHAT WOULD MAKE THIS FAIL (rule 20): two identical arms must return ratio 1.000
and zero halo difference (null control); a 0.8 px Gaussian on one arm must be
detected with the right sign (positive control).  Both are run below.
"""
import numpy as np, json, sys, arms

FAR0, FAR1 = 60, 110      # asymptote window, in SCENE (prior) px from the edge

def sample(arm, x, y, axis, sign, n):
    ax, ay = arm.px(float(x), float(y))
    xi, yi = int(round(ax)), int(round(ay))
    k = np.arange(-n, n + 1)
    if axis == 1:
        xs = xi + sign * k
        if xs.min() < 0 or xs.max() >= arm.g.shape[1] or not (0 <= yi < arm.g.shape[0]):
            return None, None
        return arm.g[yi, xs].astype(np.float64), arm.clip[yi, xs]
    ys = yi + sign * k
    if ys.min() < 0 or ys.max() >= arm.g.shape[0] or not (0 <= xi < arm.g.shape[1]):
        return None, None
    return arm.g[ys, xi].astype(np.float64), arm.clip[ys, xi]

def shape(prof, scale):
    n = (len(prof) - 1) // 2
    d = (np.arange(len(prof)) - n) / scale
    lo = np.median(prof[(d <= -FAR0) & (d >= -FAR1)])
    hi = np.median(prof[(d >= FAR0) & (d <= FAR1)])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-4:
        return None
    p = (prof - lo) / (hi - lo)
    def cross(level):
        s = p - level
        j = np.where(np.sign(s[:-1]) != np.sign(s[1:]))[0]
        if len(j) == 0: return None
        i = j[np.argmin(np.abs(j - n))]
        dd = s[i + 1] - s[i]
        return (i + (-s[i]) / dd if abs(dd) > 1e-12 else i) - n
    c10, c90 = cross(0.10), cross(0.90)
    if c10 is None or c90 is None: return None
    r = {"rise": abs(c90 - c10) / scale, "step": float(hi - lo), "hi": float(hi), "lo": float(lo)}
    for a, b, nm in ((2, 8, "03_08"), (8, 25, "08_25"), (25, 55, "25_55")):
        mo = (d > a) & (d <= b); mi = (d < -a) & (d >= -b)
        r["over_" + nm] = float(np.max(p[mo]) - 1.0)
        r["under_" + nm] = float(-np.min(p[mi]))
    r["p"] = p; r["d"] = d
    return r

def compare(A, B, sites, nprof=130, tag=""):
    ra, rb, prof_a, prof_b = [], [], [], []
    grid = np.linspace(-55, 55, 441)
    for (y, x, ny, nx) in sites:
        if abs(nx) > 0.9:
            axis, sign = 1, (1 if nx > 0 else -1)
        elif abs(ny) > 0.9:
            axis, sign = 0, (1 if ny > 0 else -1)
        else:
            continue
        pa, ca = sample(A, x, y, axis, sign, nprof)
        nb = int(round(nprof * B.scale / A.scale))
        pb, cb = sample(B, x, y, axis, sign, nb)
        if pa is None or pb is None: continue
        if ca.any() or cb.any(): continue
        sa = shape(pa, A.scale); sb = shape(pb, B.scale)
        if sa is None or sb is None: continue
        if not (0.02 < sa["lo"] and sa["hi"] < 0.98): continue
        ra.append(sa); rb.append(sb)
        prof_a.append(np.interp(grid, sa["d"], sa["p"]))
        prof_b.append(np.interp(grid, sb["d"], sb["p"]))
    return ra, rb, np.array(prof_a), np.array(prof_b), grid

KEYS = ["rise", "over_03_08", "over_08_25", "over_25_55",
        "under_03_08", "under_08_25", "under_25_55"]

def report(name, ra, rb, na, nb):
    print(f"\n===== {name}  ({len(ra)} paired profiles) =====")
    print(f"{'metric':<14}{na:>12}{nb:>12}{'B/A':>10}{'delta':>12}")
    out = {}
    for k in KEYS:
        a = np.array([r[k] for r in ra]); b = np.array([r[k] for r in rb])
        ma, mb = float(np.median(a)), float(np.median(b))
        # paired bootstrap on the median difference
        rng = np.random.default_rng(3)
        idx = rng.integers(0, len(a), (2000, len(a)))
        bs = np.median(b[idx], axis=1) - np.median(a[idx], axis=1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        rat = mb / ma if abs(ma) > 1e-9 else np.nan
        print(f"{k:<14}{ma:>12.4f}{mb:>12.4f}{rat:>10.3f}{mb-ma:>+9.4f} [{lo:+.4f},{hi:+.4f}]")
        out[k] = (ma, mb, rat, float(lo), float(hi))
    return out

if __name__ == "__main__":
    sites = np.load("edge_sites.npy")
    print("sites available:", len(sites))
    P = arms.prior_arm()
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = {}
    if which in ("all", "null"):
        ra, rb, pa, pb, grid = compare(P, arms.clone_arm(P), sites)
        res["null"] = report("NULL CONTROL: prior vs prior (identical bytes)", ra, rb, "prior", "prior-clone")
        print("  max |profile difference| over all sites:", float(np.abs(pa - pb).max()))
    if which in ("all", "pos"):
        ra, rb, pa, pb, grid = compare(P, arms.blur_arm(P, 0.8), sites)
        res["pos"] = report("POSITIVE CONTROL: prior vs prior blurred sigma=0.8 px", ra, rb, "prior", "blurred")
    if which in ("all", "scale"):
        ra, rb, pa, pb, grid = compare(P, arms.rescale_arm(P, 1.035063), sites)
        res["scale"] = report("SCALE CONFOUND CONTROL: prior vs prior crop-1/1.035 + upsample", ra, rb, "prior", "rescaled")
    if which in ("all", "real"):
        S = arms.strehl_arm()
        ra, rb, pa, pb, grid = compare(P, S)  if False else compare(P, S, sites)
        res["real"] = report("REAL: prior (focus-stack fork) vs strehl SHIP-V2", ra, rb, "prior", "strehl")
        np.save("edge_prof_prior.npy", pa); np.save("edge_prof_strehl.npy", pb); np.save("edge_grid.npy", grid)
    json.dump({k: {kk: list(vv) for kk, vv in v.items()} for k, v in res.items()},
              open("edge_results.json", "w"), indent=1)
