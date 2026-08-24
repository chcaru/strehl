"""M87 / 68 -- the drift disagreement is not a disagreement, and the halo is not
an overshoot.

TWO SURPRISES FROM STEP 67, BOTH OF WHICH CHANGE A CONCLUSION.

SURPRISE 1 -- MY PHASE CORRELATION IS NOT BLIND.
    G1 registered: estimate frame 0 against frame 298, then again with a known
    (13, -21) planted on frame 298, and require the difference to be exactly the
    plant.  It was: as-is (0,0), planted (-13,+21), difference (-13,+21).  The
    estimator solves a translation across the entire focus sweep to the pixel.
    So its zero is a MEASUREMENT, not a failure, and the reading I was preparing
    to give -- "my instrument is the outlier, trust the warpmap" -- is wrong.

    Which leaves three instruments that cannot all be describing the same thing:
        translation, frame 0 vs frame 298 .......  0.00 px   (measured, verified)
        warpmap sidecar at the ROI centre ....... 70.97 px   (M87 step 66)
        mask centroid, step 35 .................. 63.04 px
    There is a motion model that makes all three true at once, and it is the one
    macro stacking is famous for: FOCUS BREATHING.  Racking focus changes
    magnification.  A pure scale about the optical axis has NO translational
    component -- phase correlation of a scaled image pair peaks at zero -- while
    the displacement it induces at a point grows linearly with that point's
    distance from the centre, which is what a warpmap evaluated at an off-centre
    ROI and an off-centre subject's centroid both report.
    That hypothesis is testable and I test it here rather than assert it.

SURPRISE 2 -- G2 FAILED ITS OWN POSITIVE CONTROL, so its 188.56 px is void.
    Planting a 40 px ramp changed the measured excursion by -0.19 px.  An
    instrument that does not move when the thing it measures moves by 40 px is
    not measuring that thing.  I register the diagnosis before testing it: the
    dark class spans the fixed window, so rolling the image merely exchanges
    dark pixels across the window border and the windowed centroid is pinned by
    the WINDOW rather than by the subject.  Fourth instance this milestone of a
    control whose required geometry was absent where I put it.

SURPRISE 3 -- THE HALO IS NOT A BRIGHT OVERSHOOT.
    In linear light: subject G = 1457, halo band G = 12975, far background
    G = 16646.  The band is 22.05% DARKER than the far background, and the
    profile is monotone outward.  There is NO local bright bump for a band
    profile to find -- which is exactly why the frozen instrument read +0.280%
    on this image while the rank statistic read +0.376 above its null.
    If that is right the artifact must be restated: the merge is not adding
    light above the background level, it is electing a near-maximal sample at
    every veiled pixel, so the band is bright RELATIVE TO WHAT THAT PIXEL SHOULD
    BE and dark relative to unveiled background.  Both at once.  That would make
    every difference-from-baseline halo metric structurally unable to see it.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

H1 -- FOCUS BREATHING.  Tile ROI_LEG into a grid and phase-correlate frame 0
    against frame 298 tile by tile.  Fit shift(p) = s * (p - c).
    REGISTERED PREDICTION: if breathing is the reconciliation, the per-tile
    shifts are NOT all zero, they are radial about a common centre, the fit
    explains > 60% of the shift variance, and the implied displacement at the
    ROI centre's distance from the frame centre is of order the 63-71 px the
    other two instruments report.
    REGISTERED FALSIFIER: if every tile returns (0,0), there is no motion of any
    kind between the two frames, the warpmap and the centroid are both measuring
    something that is not image motion, and I say so.
    C-SCALE: positive control -- rescale frame 0 by a known 1.010 about its
    centre and re-estimate.  The recovered s must be 0.010 +/- 0.002, else the
    tile instrument cannot see scale and H1 is undecidable either way.

H2 -- THE G2 DIAGNOSIS.  Measure the fraction of the analysis window's border
    that is dark class.  REGISTERED: if > 20% of the border ring is dark, the
    windowed centroid is pinned and G2's failure is explained; a redone centroid
    on a CONNECTED-COMPONENT that does not touch the border should then respond
    to the planted ramp.

H3 -- THE PROFILE, IN LINEAR LIGHT, AT FINE RESOLUTION.  Median linear G over
    background pixels at each integer distance out to 200 px.
    REGISTERED: I predict it is monotone increasing with no local maximum, i.e.
    max over d in [1,40] is attained at d = 40 and not in the interior.
    If instead there is an interior local maximum, the overshoot IS there, my
    reading of the frozen instrument's failure is wrong, and step 63's
    +0.280% needs another explanation.

READ-ONLY: D:\\personal\\macro.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import (distance_transform_edt, label, uniform_filter, zoom)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

ROI_LEG = L.ROIS["ROI_LEG"]
FULL_H, FULL_W = 4688, 7032
GRID = (4, 6)
SCALE_PLANT = 1.010
RAMP = 40


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def est(a, b):
    h, w = a.shape
    aa = a - uniform_filter(a, 31)
    bb = b - uniform_filter(b, 31)
    cps = np.fft.rfft2(aa) * np.conj(np.fft.rfft2(bb))
    mag = np.abs(cps)
    cps = cps / np.maximum(mag, 1e-9)
    c = np.fft.irfft2(cps, s=(h, w))
    p = np.unravel_index(int(np.argmax(c)), c.shape)
    pk = float(c[p])
    return (float(p[0] if p[0] <= h // 2 else p[0] - h),
            float(p[1] if p[1] <= w // 2 else p[1] - w), pk)


def tile_shifts(a, b, grid=GRID):
    h, w = a.shape
    th, tw = h // grid[0], w // grid[1]
    rows = []
    for i in range(grid[0]):
        for j in range(grid[1]):
            ys, xs = i * th, j * tw
            dy, dx, pk = est(a[ys:ys + th, xs:xs + tw].astype(np.float32),
                             b[ys:ys + th, xs:xs + tw].astype(np.float32))
            rows.append((ys + th / 2.0, xs + tw / 2.0, dy, dx, pk))
    return np.array(rows)


def fit_scale(rows):
    """shift = s * (p - c).  Linear in (s, s*cy, s*cx); solve per axis then
    combine.  Returns s, centre, and the fraction of shift variance explained."""
    py, px_, dy, dx = rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3]
    A = np.zeros((2 * len(rows), 3))
    rhs = np.concatenate([dy, dx])
    A[:len(rows), 0] = py
    A[:len(rows), 1] = -1.0
    A[len(rows):, 0] = px_
    A[len(rows):, 2] = -1.0
    sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    s = float(sol[0])
    cy = float(sol[1] / s) if abs(s) > 1e-12 else np.nan
    cx = float(sol[2] / s) if abs(s) > 1e-12 else np.nan
    pred = A @ sol
    ss_res = float(((rhs - pred) ** 2).sum())
    ss_tot = float(((rhs - rhs.mean()) ** 2).sum())
    return s, cy, cx, (1 - ss_res / ss_tot if ss_tot > 1e-9 else np.nan), ss_res


def main():
    t0 = time.time()
    rep = {}
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    n, h, w = cube.shape
    f0 = np.asarray(cube[0], dtype=np.float32)
    fl = np.asarray(cube[n - 1], dtype=np.float32)

    # ------------------------------------------------------------------ C-SCALE
    print("=== C-SCALE: can the tile instrument see a scale at all? ===", flush=True)
    big = zoom(f0, SCALE_PLANT, order=1)
    oy = (big.shape[0] - h) // 2
    ox = (big.shape[1] - w) // 2
    f0s = big[oy:oy + h, ox:ox + w]
    rows_c = tile_shifts(f0, f0s)
    s_c, cy_c, cx_c, r2_c, _ = fit_scale(rows_c)
    print(f"  planted scale {SCALE_PLANT:.4f}  ->  recovered s = {s_c:+.5f}  "
          f"centre=({cy_c:.0f},{cx_c:.0f})  R^2={r2_c:.4f}", flush=True)
    cok = abs(abs(s_c) - (SCALE_PLANT - 1)) <= 0.002
    print(f"  C-SCALE -> {'OK, the instrument sees scale' if cok else 'FAILED, H1 undecidable'}",
          flush=True)
    rep["C_SCALE"] = {"planted": SCALE_PLANT - 1, "recovered": s_c, "r2": r2_c,
                      "centre": [cy_c, cx_c], "ok": bool(cok)}

    # ---------------------------------------------------------------------- H1
    print("\n=== H1: focus breathing, frame 0 vs frame 298 ===", flush=True)
    rows = tile_shifts(f0, fl)
    nz = int((np.abs(rows[:, 2]) + np.abs(rows[:, 3]) > 0).sum())
    print(f"  {GRID[0]}x{GRID[1]} tiles of {h // GRID[0]}x{w // GRID[1]} px; "
          f"{nz}/{len(rows)} returned a non-zero shift", flush=True)
    for r_ in rows:
        print(f"    tile @ ({r_[0]:6.0f},{r_[1]:6.0f})  shift=({r_[2]:+6.1f},{r_[3]:+6.1f})"
              f"  peak={r_[4]:.4f}", flush=True)
    s, cy, cx, r2, _ = fit_scale(rows)
    print(f"  similarity fit: s = {s:+.6f}   centre = ({cy:.0f}, {cx:.0f})   "
          f"R^2 = {r2:.4f}", flush=True)
    roi_cy = ROI_LEG[0] + (ROI_LEG[1] - ROI_LEG[0]) / 2
    roi_cx = ROI_LEG[2] + (ROI_LEG[3] - ROI_LEG[2]) / 2
    rr = np.hypot(roi_cy - FULL_H / 4, roi_cx - FULL_W / 4)
    print(f"  ROI centre is {rr:.0f} px from the binned frame centre; a scale of "
          f"{abs(s):.6f} there = {abs(s) * rr:.2f} px", flush=True)
    h1 = bool(nz > 0 and r2 > 0.60)
    print(f"  H1 -> {'radial motion present' if h1 else 'FALSIFIED as registered'}",
          flush=True)
    if nz == 0:
        print("  REGISTERED FALSIFIER FIRED: every tile returns (0,0).  There is no",
              flush=True)
        print("  image motion of any kind between the first and last frame of this",
              flush=True)
        print("  crop -- not translation, not scale.  The warpmap's 70.97 px and the",
              flush=True)
        print("  centroid's 63.04 px are therefore NOT measurements of image motion.",
              flush=True)
    rep["H1"] = {"n_nonzero": nz, "n_tiles": len(rows), "s": s, "centre": [cy, cx],
                 "r2": r2, "roi_radius_px": float(rr), "disp_at_roi": abs(s) * float(rr),
                 "tiles": rows.tolist(), "radial": h1}

    # ---------------------------------------------------------------------- H2
    print("\n=== H2: why the windowed centroid could not move ===", flush=True)
    _, tau = L.foreground_mask(sel0)
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
    y0, y1, x0, x1 = M, M + 700, M, M + 1100
    win = f0[y0:y1, x0:x1] < tau
    ring = np.concatenate([win[0], win[-1], win[:, 0], win[:, -1]])
    frac = float(ring.mean())
    print(f"  dark-class fraction on the window border = {100 * frac:.2f}%", flush=True)
    print(f"  dark-class fraction inside the window    = {100 * win.mean():.2f}%", flush=True)
    h2 = frac > 0.20
    print(f"  H2 -> {'window-pinned, G2 explained' if h2 else 'NOT explained by border contact'}",
          flush=True)
    lab, nlab = label(win)
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    touch = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    free = [i for i in range(1, nlab + 1) if i not in touch and sizes[i] > 2000]
    print(f"  {nlab} dark components; {len(free)} are >2000 px and touch no border",
          flush=True)
    if free:
        best = max(free, key=lambda i: sizes[i])
        yy, xx = np.nonzero(lab == best)
        c0 = (yy.mean(), xx.mean())
        rolled = np.roll(f0, (RAMP, 0), axis=(0, 1))[y0:y1, x0:x1] < tau
        lab2, n2 = label(rolled)
        ov = np.bincount(lab2[lab == best], minlength=n2 + 1)
        ov[0] = 0
        b2 = int(np.argmax(ov))
        yy2, xx2 = np.nonzero(lab2 == b2)
        moved = float(np.hypot(yy2.mean() - c0[0], xx2.mean() - c0[1]))
        print(f"  border-free component {best} ({sizes[best]} px): planted a {RAMP} px "
              f"roll -> its centroid moved {moved:.2f} px", flush=True)
        rep["H2_free_component"] = {"size": int(sizes[best]), "moved_px": moved,
                                    "planted": RAMP,
                                    "responds": bool(abs(moved - RAMP) < 8)}
    rep["H2"] = {"border_dark_frac": frac, "window_dark_frac": float(win.mean()),
                 "n_components": int(nlab), "n_border_free": len(free),
                 "explained": bool(h2)}

    # ---------------------------------------------------------------------- H3
    print("\n=== H3: the linear radial profile, integer bins ===", flush=True)
    import tifffile
    img = tifffile.imread(CACHE / "ship-before-linear.tif").astype(np.float64)
    gg = img[..., 1]
    fmask, _ = L.foreground_mask(gg)
    do = distance_transform_edt(~fmask)[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]]
    gl = gg[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]]
    dd = np.rint(do).astype(np.int32)
    prof, cnt = [], []
    for d in range(0, 201):
        s = dd == d
        c = int(s.sum())
        cnt.append(c)
        prof.append(float(np.median(gl[s])) if c >= 200 else np.nan)
    prof = np.array(prof)
    seg = prof[1:41]
    ok = np.isfinite(seg)
    imax = int(np.nanargmax(seg)) + 1
    print("  d :  median linear G   (n)", flush=True)
    for d in [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 60, 80, 120, 160, 200]:
        v = prof[d]
        print(f"  {d:4d}: {v:12.1f}   ({cnt[d]})" if np.isfinite(v)
              else f"  {d:4d}:        n/a   ({cnt[d]})", flush=True)
    interior = imax not in (1, 40)
    print(f"  max over d in [1,40] is at d = {imax}  -> "
          f"{'INTERIOR local maximum: an overshoot IS present' if interior else 'no interior maximum, monotone as predicted'}",
          flush=True)
    dif = np.diff(prof[1:41][ok])
    print(f"  monotone increasing over [1,40]: {bool((dif >= 0).all())}  "
          f"({int((dif < 0).sum())} descents)", flush=True)
    rep["H3"] = {"profile": [None if not np.isfinite(v) else round(float(v), 1) for v in prof],
                 "counts": cnt, "argmax_1_40": imax, "interior_max": bool(interior),
                 "monotone": bool((dif >= 0).all())}

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "68-breathing.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '68-breathing.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
