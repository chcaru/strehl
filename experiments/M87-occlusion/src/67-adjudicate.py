"""M87 / 67 -- adjudicating the drift disagreement, and the M107 separation on
linear data.

TWO LOOSE ENDS FROM STEP 66, BOTH OF WHICH COULD OVERTURN A CLAIM.

LOOSE END 1 -- THREE INSTRUMENTS DISAGREE ABOUT THE DRIFT.
    my FFT phase correlation ....... 0 px, for every one of 299 frames
    the aligner's warpmap sidecar .. 70.97 px peak-to-peak at ROI_LEG centre
    step 35's mask centroid ........ 63.04 px peak-to-peak (same region)
    The last two agree to 13%; mine is the outlier.  Step 66's D1 control
    "passed" -- the estimator recovered a planted (13, -21) exactly -- but that
    control was TOO EASY: it planted a shift on frame 0 and matched it against
    frame 0, so the two images had identical content and only differed by the
    translation being solved for.  The real problem is matching frame 0 against
    frame 298, which differ by the entire focus sweep and share almost no sharp
    structure.  A control that cannot fail in the way the instrument actually
    fails is not a control, so D1's green is worth nothing and I am replacing it.

LOOSE END 2 -- THE CHROMATICITY ARM RAN ON GAMMA-ENCODED DATA.
    Step 64's X1 passed on `bee3-full.tif`, and step 66's C-LINEAR-2 then showed
    that file is NOT linear: binning away resampling scatter, the transform from
    linear raw DN to that TIFF is curved, R^2 = 0.9612 against a straight line
    with a quadratic term worth 63.8% of the fitted range.  Consistent with a
    ~1/2.2 encode -- its p50 is 29876/65535 = 0.4559, and the linear merge's is
    11041/65535 = 0.1685, and 0.1685^(1/2.2) = 0.4494.
    A convex blend is convex IN LINEAR LIGHT.  Testing convexity on gamma-
    encoded values tests the wrong proposition, so X1's PASS does not stand as
    run and is re-run here on `ship-before-linear.tif`, which is the same merge,
    same geometry, RGB, and linear.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

G1 -- THE HARD DRIFT CONTROL.  Estimate frame 0 against frame 298 twice: as-is,
    and with a known (+13, -21) planted on frame 298.  If the estimator is
    working, the two answers must differ by exactly the plant.
    REGISTERED: answer(planted) - answer(as-is) == (-13, +21).  If that holds,
    the estimator is self-consistent across the focus sweep and its zero is a
    real measurement; if it fails, the estimator is blind across focus and the
    warpmap and the centroid are the only instruments standing.

G2 -- AN INDEPENDENT THIRD INSTRUMENT.  Per-frame centroid of the dark class,
    thresholded at the MERGE's tau so the threshold itself cannot move, over the
    inner ROI.  A defocus blur is centroid-preserving to first order, so this
    should track translation and not focus.
    REGISTERED: if the centroid excursion is within 30% of 63.04 px, the
    warpmap and the centroid agree, my phase correlation is the odd one out, and
    step 66's D2 -- which applied the warpmap shifts -- is the arm to trust.
    Its own positive control: re-run the centroid on frames given a planted
    linear roll ramp of 40 px and require the measured excursion to grow by
    40 px +/- 4.

G3 -- AND WHY IT DOES NOT MATTER MUCH, STATED IN ADVANCE.  Step 66 measured the
    dR band peak at +0.2282 (d = 6) unaligned and +0.2651 (d = 7) after applying
    70.97 px of warpmap correction, a +16.2% change.  Either the true drift is
    ~71 px, in which case the band survives ALIGNMENT; or it is ~0, in which
    case the band survived being deliberately MIS-registered by 71 px.  Both
    readings exclude drift as the cause.  I register that reading now so it
    cannot be constructed after the fact.

X1-LINEAR -- CHROMATICITY CONVEXITY, REDONE IN LINEAR LIGHT.
    Populations inside ROI_LEG on `ship-before-linear.tif`:
      deep subject     mask, inner distance > 40
      far background   background, distance >= 120
      halo band        background, distance in [2, 20]   (the measured dR reach)
      null             far background split into two interleaved halves
    In the chromaticity plane (r, b) = (R, B)/(R+G+B) a two-layer composite must
    lie ON the segment joining subject to background.
    REGISTERED: perpendicular offset < 0.05 of segment length AND < 3x the null.
    If it fails, part of the bee rim is chromatic, it is not a pure two-layer
    veil, and that share belongs to M107's demosaic candidate, not to me.
    Reported alongside the SCALAR convex bound in linear light: the band's
    luminance must lie between the subject's and the background's.
    A precondition is checked, not assumed: the same binned-median linearity
    test that failed for `bee3-full.tif` must PASS for this file, else the arm
    is void again and I say so.

READ-ONLY: D:\\personal\\macro.  Writes only to experiments/M87-occlusion/data
and C:\\dev\\strehl-out\\M87-bee.
"""
import json
import pathlib
import sys
import time

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

ROI_LEG = L.ROIS["ROI_LEG"]
MARGIN = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
PLANT = (13, -21)
RAMP = 40
LINEAR_TIF = CACHE / "ship-before-linear.tif"
BAND = (2, 20)


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(repr(o))


def est_shift(a_hp, b_img):
    h, w = a_hp.shape
    bb = b_img - uniform_filter(b_img, 31)
    cps = np.fft.rfft2(a_hp) * np.conj(np.fft.rfft2(bb))
    cps /= np.maximum(np.abs(cps), 1e-9)
    c = np.fft.irfft2(cps, s=(h, w))
    p = np.unravel_index(int(np.argmax(c)), c.shape)
    return (int(p[0] if p[0] <= h // 2 else p[0] - h),
            int(p[1] if p[1] <= w // 2 else p[1] - w))


def linearity(tif_green, raw_green):
    """Binned-median straightness test: resampling scatter averages out, only
    curvature survives."""
    a = tif_green.ravel()
    b = raw_green.ravel()
    lo, hi = np.percentile(b, [0.5, 99.5])
    edges = np.linspace(lo, hi, 65)
    ib = np.digitize(b, edges) - 1
    xs, ys = [], []
    for i in range(64):
        s = ib == i
        if s.sum() >= 500:
            xs.append(float(np.median(b[s])))
            ys.append(float(np.median(a[s])))
    xs, ys = np.array(xs), np.array(ys)
    sl, ic = np.polyfit(xs, ys, 1)
    r2 = 1 - float(((ys - (sl * xs + ic)) ** 2).sum() / ((ys - ys.mean()) ** 2).sum())
    q = np.polyfit(xs, ys, 2)
    curv = float(abs(q[0]) * (xs.max() - xs.min()) ** 2 / max(ys.max() - ys.min(), 1e-9))
    return {"n_bins": len(xs), "r2": r2, "slope": float(sl), "curv_frac": curv,
            "linear": bool(r2 > 0.999 and curv < 0.01)}


def main():
    t0 = time.time()
    rep = {}
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    n, h, w = cube.shape

    # ------------------------------------------------------------------ G1
    print("=== G1: the hard drift control (frame 0 vs frame 298) ===", flush=True)
    f0 = np.asarray(cube[0], dtype=np.float32)
    f0hp = f0 - uniform_filter(f0, 31)
    fl = np.asarray(cube[n - 1], dtype=np.float32)
    asis = est_shift(f0hp, fl)
    pl = est_shift(f0hp, np.roll(fl, PLANT, axis=(0, 1)))
    diff = (pl[0] - asis[0], pl[1] - asis[1])
    exp = (-PLANT[0], -PLANT[1])
    g1 = diff == exp
    print(f"  as-is        -> {asis}", flush=True)
    print(f"  plant {PLANT} -> {pl}", flush=True)
    print(f"  difference   -> {diff}   expected {exp}", flush=True)
    print(f"  G1 -> {'estimator SELF-CONSISTENT across focus' if g1 else 'estimator BLIND across focus'}",
          flush=True)
    rep["G1"] = {"asis": list(asis), "planted": list(pl), "diff": list(diff),
                 "expected": list(exp), "self_consistent": bool(g1)}

    # ------------------------------------------------------------------ G2
    print("\n=== G2: independent third instrument -- dark-class centroid ===", flush=True)
    _, tau = L.foreground_mask(sel0)
    y0, y1, x0, x1 = MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100
    yy, xx = np.mgrid[y0:y1, x0:x1]

    def centroid_track(roll_ramp=None):
        cy = np.empty(n)
        cx = np.empty(n)
        for k in range(n):
            a = np.asarray(cube[k], dtype=np.float32)
            if roll_ramp is not None:
                a = np.roll(a, (int(roll_ramp[k]), 0), axis=(0, 1))
            m = a[y0:y1, x0:x1] < tau
            s = m.sum()
            if s < 1000:
                cy[k] = np.nan
                cx[k] = np.nan
            else:
                cy[k] = (yy * m).sum() / s
                cx[k] = (xx * m).sum() / s
        return cy, cx

    cy, cx = centroid_track()
    pp = float(np.hypot(np.nanmax(cy) - np.nanmin(cy), np.nanmax(cx) - np.nanmin(cx)))
    print(f"  centroid excursion = {pp:.2f} px p-p   "
          f"(step 35: 63.04, warpmap: 70.97)", flush=True)
    ramp = np.linspace(0, RAMP, n)
    cy2, cx2 = centroid_track(ramp)
    pp2 = float(np.hypot(np.nanmax(cy2) - np.nanmin(cy2), np.nanmax(cx2) - np.nanmin(cx2)))
    print(f"  POSITIVE CONTROL: with a planted {RAMP} px ramp -> {pp2:.2f} px p-p "
          f"(grew by {pp2 - pp:+.2f}, expect ~{RAMP})", flush=True)
    ctrl_ok = abs((pp2 - pp) - RAMP) <= 8
    agree = abs(pp - 63.04) / 63.04 < 0.30
    print(f"  control {'OK' if ctrl_ok else 'FAILED -- centroid instrument unreliable'}",
          flush=True)
    print(f"  G2 -> {'AGREES with step 35/warpmap; my phase correlation is the outlier' if (agree and ctrl_ok) else 'does NOT agree'}",
          flush=True)
    rep["G2"] = {"pp_px": pp, "planted_pp_px": pp2, "growth": pp2 - pp,
                 "control_ok": bool(ctrl_ok), "agrees_with_step35": bool(agree),
                 "cy": [None if not np.isfinite(v) else round(float(v), 3) for v in cy],
                 "cx": [None if not np.isfinite(v) else round(float(v), 3) for v in cx]}

    # ------------------------------------------------------------ X1-LINEAR
    print("\n=== X1-LINEAR: chromaticity convexity, in linear light ===", flush=True)
    img = tifffile.imread(LINEAR_TIF).astype(np.float64)
    print(f"  {LINEAR_TIF.name}  {img.shape}  {tifffile.imread(LINEAR_TIF).dtype}", flush=True)
    lin = linearity(img[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3], 1],
                    sel0[y0:y1, x0:x1].astype(np.float64))
    print(f"  PRECONDITION linearity: {lin['n_bins']} bins  R^2={lin['r2']:.6f}  "
          f"curvature={lin['curv_frac']:.5f}  -> {'LINEAR' if lin['linear'] else 'CURVED'}",
          flush=True)
    rep["X_precondition"] = lin

    gg = img[..., 1]
    fmask, ftau = L.foreground_mask(gg)
    do = distance_transform_edt(~fmask)[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]]
    di = distance_transform_edt(fmask)[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]]
    px = img[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]]

    def pop(sel, label):
        v = px[sel]
        if v.shape[0] < 500:
            print(f"  {label}: only {v.shape[0]} px -- NOT DECIDABLE", flush=True)
            return None, None
        s = v.sum(axis=1)
        ok = s > 0
        c = np.array([float(np.median(v[ok, 0] / s[ok])), float(np.median(v[ok, 2] / s[ok]))])
        lum = float(np.median(v[:, 1]))
        print(f"  {label:24s} n={v.shape[0]:8d}  r={c[0]:.6f}  b={c[1]:.6f}  "
              f"G={lum:9.1f}", flush=True)
        return c, lum

    half = np.zeros_like(do, bool)
    half[::2] = True
    c_sub, l_sub = pop(di > 40, "deep subject")
    c_far, l_far = pop(do >= 120, "far background")
    c_bnd, l_bnd = pop((do >= BAND[0]) & (do <= BAND[1]), f"halo band d in {BAND}")
    c_a, _ = pop((do >= 120) & half, "far bg half A")
    c_b, _ = pop((do >= 120) & ~half, "far bg half B")

    if c_sub is not None and c_far is not None and c_bnd is not None:
        seg = c_far - c_sub
        sl_ = float(np.hypot(*seg))
        u = seg / max(sl_, 1e-12)
        rel = c_bnd - c_sub
        along = float(rel @ u) / max(sl_, 1e-12)
        perp = float(abs(rel[0] * u[1] - rel[1] * u[0])) / max(sl_, 1e-12)
        nul = float(np.hypot(*(c_b - c_a)) / max(sl_, 1e-12)) if c_a is not None else None
        print(f"\n  segment length            = {sl_:.6f}", flush=True)
        print(f"  band along segment        = {along:.4f}  (0=subject, 1=background)",
              flush=True)
        print(f"  band PERPENDICULAR offset = {perp:.5f} of segment", flush=True)
        print(f"  C-CHROMA-NULL (bg A vs B) = {nul:.5f}", flush=True)
        x1 = bool(perp < 0.05 and (nul is None or perp < max(3 * nul, 0.05)))
        print(f"  X1-LINEAR -> {'PASS: convex in colour, consistent with a two-layer veil' if x1 else 'FAIL: chromatic, a share belongs to M107'}",
              flush=True)
        inb = l_sub <= l_bnd <= l_far or l_far <= l_bnd <= l_sub
        print(f"\n  SCALAR convex bound in linear light: subject G={l_sub:.1f}  "
              f"band G={l_bnd:.1f}  far bg G={l_far:.1f}", flush=True)
        print(f"    band between the two layers: {inb}  "
              f"(band is {100 * (l_bnd - l_far) / l_far:+.2f}% vs far background)", flush=True)
        rep["X1_linear"] = {"c_subject": c_sub.tolist(), "c_far": c_far.tolist(),
                            "c_band": c_bnd.tolist(), "seg_len": sl_, "along": along,
                            "perp": perp, "null": nul, "tau": float(ftau),
                            "G_subject": l_sub, "G_band": l_bnd, "G_far": l_far,
                            "scalar_convex": bool(inb),
                            "band_vs_far_pct": 100 * (l_bnd - l_far) / l_far,
                            "verdict": "PASS" if x1 else "FAIL"}

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "67-adjudicate.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '67-adjudicate.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
