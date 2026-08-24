"""M84b step 17 - the two-dimensional plane law and the ground-truth depth map.

Step 13 fitted the graduation law along ONE row band. A depth map needs the
plane in two dimensions, so this step measures the second image axis.

For a plane under perspective, INVERSE depth is affine in image coordinates:

    1/Z = alpha + beta*xi + gamma*eta

(the dispatch's "depth is affine in image coordinates" is the paraxial
limit; with 4.5x foreshortening here the distinction is material). A tick is
an iso-depth line if and only if the tick image lines are PARALLEL in the
image - a vanishing point at infinity. That is a falsifiable test, and it is
the test this step runs:

  1. one streaming decode pass over the angled stack, building a column-wise
     best-focus dark profile in FIVE separate row bands;
  2. band-to-band x offsets by cross-correlation, then per-tick offsets;
  3. if per-tick offsets do NOT drift with graduation index, the ticks are
     parallel, depth is constant along each tick, and the depth field reduces
     to a one-dimensional law in the sheared coordinate
         x_ref = x - s*(y - y_ref);
  4. the depth map is then ANALYTIC:
         k(x_ref) = (x_ref - A) / (B - C*x_ref)
         depth_um = k * dZ_per_grad
     and is shipped as a small parameter file plus this builder, not as a
     30 MB binary blob. The .npz is written locally for inspection.

Uncertainty is propagated from the step-13 bootstrap on (A, B, C), the tick
residual scatter, the shear uncertainty, and the closure uncertainty on
dZ_per_grad. The validity mask is built from focus-index consistency against
the plane model, which rejects the granular supporting surface and the
background without hand-drawn polygons.

Reads READ-ONLY from D:\\personal\\macro.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np
import rawpy
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")
STACK = "highly-angled-ruler-mm-cpl"

X0, X1 = 1100, 3100  # widened by 100 px over step 12 so sheared ticks stay inside
# Five row bands. All lie inside registered A-RULE (y 900..1800) and inside the
# region measured clear of the datum line (y > 1263 at the leftmost tick) and of
# the granular supporting surface (y < 1948 at the rightmost tick).
BANDS = [(1350, 1410), (1450, 1510), (1550, 1610), (1650, 1710), (1740, 1800)]
REF_BAND = 3  # centre 1680, closest to the step-12/13 comb band centre 1710

BG_MEDIAN_QUAD = 601
LOCALMAX_HALFWIN = 200
MIN_RUN = 3
FRAC = 0.35

Q4 = 4  # the q4 maps are decimated 4x from the quad grid
TOL_FRAMES = (10.0, 25.0, 50.0)  # mask sensitivity sweep; 25 is the headline


def quad_green(path: pathlib.Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black


def peak_frame(curve: np.ndarray) -> float:
    base = float(np.median(curve))
    c = curve - base
    j = int(np.argmax(c))
    if c[j] <= 0:
        return float("nan")
    half = 0.5 * c[j]
    lo = j
    while lo > 0 and c[lo - 1] >= half:
        lo -= 1
    hi = j
    while hi < len(c) - 1 and c[hi + 1] >= half:
        hi += 1
    seg = c[lo : hi + 1]
    idx = np.arange(lo, hi + 1, dtype=np.float64)
    if seg.sum() <= 0:
        return float(j)
    return float((idx * seg).sum() / seg.sum())


def dark_profile(prof: np.ndarray) -> np.ndarray:
    bg = ndimage.median_filter(prof, size=BG_MEDIAN_QUAD, mode="nearest")
    return np.maximum(bg - prof, 0.0)


def find_ticks(dark: np.ndarray) -> list[dict]:
    locmax = ndimage.maximum_filter1d(
        dark, size=2 * LOCALMAX_HALFWIN + 1, mode="nearest"
    )
    mask = dark > FRAC * locmax
    lab, _ = ndimage.label(mask)
    ticks = []
    for s in ndimage.find_objects(lab):
        a, b = s[0].start, s[0].stop
        if b - a < MIN_RUN or a == 0 or b == len(dark):
            continue
        pk = a + int(np.argmax(dark[a:b]))
        hm = 0.5 * dark[pk]
        lo = pk
        while lo > 0 and dark[lo - 1] >= hm:
            lo -= 1
        hi = pk
        while hi < len(dark) - 1 and dark[hi + 1] >= hm:
            hi += 1
        seg = dark[lo : hi + 1]
        if seg.sum() <= 0:
            continue
        idx = np.arange(lo, hi + 1, dtype=np.float64)
        ticks.append(
            {
                "x": float((idx * seg).sum() / seg.sum()),
                "fwhm": float(hi - lo + 1),
                "depth": float(dark[pk]),
            }
        )
    return ticks


def two_pass_bands(frames: list[pathlib.Path]):
    """One decode pass building a focus profile per band, a second building the
    column-wise best-focus intensity profile per band."""
    n = len(frames)
    w = X1 - X0
    nb = len(BANDS)
    colprof = np.zeros((nb, n, w), np.float32)
    t0 = time.time()
    for i, fp in enumerate(frames):
        plane = quad_green(fp)
        for j, (y0, y1) in enumerate(BANDS):
            sub = np.ascontiguousarray(plane[y0:y1, X0:X1])
            np.clip(sub, 1.0, None, out=sub)
            gx = ndimage.sobel(sub, axis=1)
            gy = ndimage.sobel(sub, axis=0)
            e = gx * gx + gy * gy
            lvl = ndimage.uniform_filter(sub, 33)
            colprof[j, i] = (ndimage.uniform_filter(e, 33) / (lvl * lvl)).mean(axis=0)
        del plane
        if i % 60 == 0:
            print(f"    pass1 frame {i:3d}  {time.time() - t0:5.1f}s", flush=True)

    nstar = np.zeros((nb, w))
    for j in range(nb):
        for x in range(w):
            nstar[j, x] = peak_frame(colprof[j, :, x].astype(np.float64))
        nstar[j] = ndimage.median_filter(
            np.nan_to_num(nstar[j], nan=0.0), size=101, mode="nearest"
        )

    comps = np.zeros((nb, w), np.float32)
    counts = np.zeros((nb, w), np.float32)
    want = np.clip(np.rint(nstar).astype(int), 0, n - 1)
    t0 = time.time()
    for i in range(n):
        if not np.any(want == i):
            continue
        plane = quad_green(frames[i])
        for j, (y0, y1) in enumerate(BANDS):
            cols = np.flatnonzero(want[j] == i)
            if cols.size == 0:
                continue
            comps[j, cols] = plane[y0:y1, X0:X1][:, cols].mean(axis=0)
            counts[j, cols] = 1.0
        del plane
    print(f"    pass2 {time.time() - t0:5.1f}s", flush=True)
    assert np.all(counts > 0), "some columns never got a source frame"
    return nstar, comps


def xcorr_shift(a: np.ndarray, b: np.ndarray, max_shift: int = 200) -> float:
    """Sub-pixel shift that best maps b onto a, by parabolic refinement of the
    integer cross-correlation peak."""
    shifts = np.arange(-max_shift, max_shift + 1)
    scores = np.empty(len(shifts))
    for i, s in enumerate(shifts):
        bb = np.roll(b, s)
        if s > 0:
            bb[:s] = 0
        elif s < 0:
            bb[s:] = 0
        scores[i] = float(np.dot(a, bb))
    j = int(np.argmax(scores))
    if 0 < j < len(shifts) - 1:
        y0, y1, y2 = scores[j - 1], scores[j], scores[j + 1]
        denom = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / denom if denom != 0 else 0.0
    else:
        d = 0.0
    return float(shifts[j] + d)


def fit_projective(k: np.ndarray, x: np.ndarray, seed_c: float = 0.0) -> dict:
    A = B = 0.0
    C = seed_c
    prev = np.array([np.inf, np.inf, np.inf])
    w = np.ones_like(x)
    it = 0
    for it in range(1, 201):
        v = 1.0 / np.maximum(1.0 + C * k, 1e-6)
        M = np.column_stack([np.ones_like(k), k, -x * k])
        ww = w * v
        sw = np.sqrt(ww)
        sol, *_ = np.linalg.lstsq(M * sw[:, None], x * sw, rcond=None)
        A, B, C = sol
        r = x - (A + B * k) / (1.0 + C * k)
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-12
        c = 1.345 * s
        w = np.where(np.abs(r) <= c, 1.0, c / np.maximum(np.abs(r), 1e-12))
        cur = np.array([A, B, C])
        if np.all(np.abs(cur - prev) <= 1e-10 * np.maximum(np.abs(cur), 1e-12)):
            break
        prev = cur
    r = x - (A + B * k) / (1.0 + C * k)
    return {
        "A": float(A),
        "B": float(B),
        "C": float(C),
        "resid_rms": float(np.sqrt(np.mean(r**2))),
        "resid_max": float(np.max(np.abs(r))),
        "n": int(len(k)),
        "converged": bool(it < 200),
    }


def main(argv: list[str]) -> int:
    OUT.mkdir(exist_ok=True)
    frames = sorted((CORPUS / STACK).glob("*.ARW"))
    print(f"{STACK}: {len(frames)} frames, {len(BANDS)} bands")

    cache = OUT / "17-bands.npz"
    if cache.exists() and "--refit" in argv:
        z = np.load(cache)
        nstar, comps = z["nstar"], z["comps"]
        print("  reusing cached band profiles")
    else:
        nstar, comps = two_pass_bands(frames)
        np.savez_compressed(cache, nstar=nstar, comps=comps)

    darks = np.array([dark_profile(comps[j].astype(np.float64)) for j in range(len(BANDS))])
    band_y = np.array([0.5 * (a + b) for a, b in BANDS])
    y_ref = band_y[REF_BAND]

    # ---- band-to-band shear ----
    # xcorr_shift(a,b) returns s with a ~ roll(b, s), i.e. a feature at x in the
    # reference sits at x - s in band j. Negate so `shifts[j]` is the offset
    # ADDED to a reference x to predict band j's x.
    shifts = np.array(
        [-xcorr_shift(darks[REF_BAND], darks[j]) for j in range(len(BANDS))]
    )
    dy = band_y - y_ref
    s_hat, s_int = np.polyfit(dy, shifts, 1)
    s_resid = shifts - (s_hat * dy + s_int)
    # A straight-line fit through 5 points: sigma on the slope from the residual.
    s_sigma = float(
        np.sqrt(np.sum(s_resid**2) / max(len(dy) - 2, 1) / np.sum((dy - dy.mean()) ** 2))
    )
    print(f"  band shifts (px, vs ref band y={y_ref:.0f}): {np.round(shifts, 2).tolist()}")
    print(f"  shear s = dx/dy = {s_hat:+.5f} +/- {s_sigma:.5f}  "
          f"(tick tilt from image-vertical {np.degrees(np.arctan(s_hat)):+.2f} deg), "
          f"line resid rms {np.sqrt(np.mean(s_resid**2)):.3f} px")

    # ---- per-tick offsets: the parallelism (iso-depth) test ----
    per_band_ticks = [find_ticks(darks[j]) for j in range(len(BANDS))]
    ref_x = np.array([t["x"] for t in per_band_ticks[REF_BAND]])
    tick_off = {}
    for j in range(len(BANDS)):
        xs = np.array([t["x"] for t in per_band_ticks[j]])
        if len(xs) == 0:
            continue
        pairs = []
        for xr in ref_x:
            d = xs - (xr + shifts[j])
            i = int(np.argmin(np.abs(d)))
            if abs(d[i]) < 12.0:
                pairs.append((float(xr), float(xs[i] - xr)))
        tick_off[j] = pairs

    par = {}
    for j, pairs in tick_off.items():
        print(f"    band {j} raw detections {len(per_band_ticks[j])}, "
              f"matched to ref {len(pairs)}")
        if j == REF_BAND or len(pairs) < 5:
            continue
        xr = np.array([p[0] for p in pairs])
        off = np.array([p[1] for p in pairs])
        sl, ic = np.polyfit(xr, off, 1)
        pr = off - (sl * xr + ic)
        par[str(j)] = {
            "n_pairs": len(pairs),
            "mean_offset_px": float(np.mean(off)),
            "offset_spread_px": float(np.std(off)),
            "drift_per_1000px": float(sl * 1000.0),
            "resid_rms_px": float(np.sqrt(np.mean(pr**2))),
            "dy": float(dy[j]),
        }
        print(f"  band {j} (dy {dy[j]:+.0f}): {len(pairs)} matched ticks, "
              f"offset {np.mean(off):+.2f} px, spread {np.std(off):.2f} px, "
              f"drift {sl * 1000.0:+.2f} px per 1000 px of x")

    spreads = [v["offset_spread_px"] for v in par.values()]
    drifts = [abs(v["drift_per_1000px"]) for v in par.values()]
    iso_depth = bool(max(spreads) < 3.0 and max(drifts) < 15.0)
    print(f"  ISO-DEPTH TICKS: {iso_depth}  (max spread {max(spreads):.2f} px "
          f"< 3.0, max drift {max(drifts):.2f} < 15 px/1000px)")

    # ---- inherit the step-15 law (the one the closure used) ----
    f13 = json.loads((OUT / "13-ang.json").read_text())
    clos = json.loads((OUT / "15-closure.json").read_text())
    A13, B13, C13 = (clos["fits_absolute"]["ang"][q] for q in "ABC")
    boot13 = f13["bootstrap"]
    dZ = clos["solution"]["dZ_per_grad_ang_um"]
    dZ_sig = clos["bootstrap"]["dZ_per_grad_ang_um"]["sd"]

    # Step 15 now lifts its fits to ABSOLUTE quad coordinates itself (its ROI
    # bug fix), so no further offset is applied here. The raw step-13 tick
    # positions are still ROI-relative and are lifted.
    assert A13 > X0, (
        f"step-15 ang fit A={A13:.1f} looks ROI-relative, not absolute; "
        "the coordinate frames have drifted apart again"
    )
    rejected = f13["quality"]["rejected"]
    all_k = np.array(f13["k"], float)
    all_x = np.array(f13["tick_x"], float) + X0
    # The Huber fit down-weighted one far-end graduation; apply step 15's
    # disclosed 5-sigma hard rejection here so the depth law and its residual
    # scatter are built on exactly the same graduations the closure used.
    r_all = all_x - (A13 + B13 * all_k) / (1.0 + C13 * all_k)
    sig_r = 1.4826 * np.median(np.abs(r_all - np.median(r_all)))
    keep = np.abs(r_all - np.median(r_all)) <= 5.0 * sig_r
    kept_k, kept_x = all_k[keep], all_x[keep]
    print(f"  step-13: {len(all_k)} ticks after the quality filter "
          f"({len(rejected)} wide blobs dropped pre-fit); 5-sigma rejection "
          f"drops {int((~keep).sum())} -> {int(keep.sum())} kept "
          f"(k rejected: {all_k[~keep].astype(int).tolist()})")

    # The step-13 comb band was y in [1620,1800], centre 1710; map its law into
    # the step-17 reference row so both live in one coordinate system.
    x_shift_13 = s_hat * (1710.0 - y_ref)
    A_ref = A13 - x_shift_13
    B_ref = B13 - C13 * x_shift_13
    C_ref = C13
    print(f"  step-13 law re-referenced by {-x_shift_13:+.3f} px "
          f"-> A {A_ref:.3f} B {B_ref:.4f} C {C_ref:.6e}")

    # ---- L3 coverage and P1 after outlier rejection ----
    span_lo, span_hi = float(kept_x.min()), float(kept_x.max())
    arule_w = 1900.0  # registered A-RULE width
    L3 = (span_hi - span_lo) / arule_w
    pred = (A13 + B13 * kept_k) / (1.0 + C13 * kept_k)
    resid = kept_x - pred
    half = len(resid) // 2
    P1 = float(
        np.std(resid[:half]) / max(np.std(resid[half:]), 1e-12)
    )
    P1 = max(P1, 1.0 / P1)
    print(f"  L3 coverage {L3 * 100:.1f}% of A-RULE (bar >= 50%)  "
          f"span x [{span_lo:.1f}, {span_hi:.1f}]")
    print(f"  P1 planarity ratio after rejection {P1:.3f} (bar < 3.0), "
          f"resid rms {np.sqrt(np.mean(resid**2)):.3f} px")

    # ---- build the depth map at q4 resolution ----
    idx = np.load(OUT / f"10-aifidx-{STACK}.npy").astype(np.float64)
    conf = np.load(OUT / f"10-aifconf-{STACK}.npy").astype(np.float64)
    H4, W4 = idx.shape
    yy4, xx4 = np.mgrid[0:H4, 0:W4]
    xq = xx4 * Q4 + (Q4 - 1) * 0.5
    yq = yy4 * Q4 + (Q4 - 1) * 0.5
    x_ref = xq - s_hat * (yq - y_ref)
    denom = B_ref - C_ref * x_ref
    k_map = (x_ref - A_ref) / denom
    depth_um = k_map * dZ

    # frame index predicted by the plane, from the step-16 per-graduation n*(k)
    f16 = json.loads((OUT / "16-focusaxis.json").read_text())
    kk = np.array([g["k"] for g in f16["per_graduation"]], float)
    nn = np.array([g["n_centroid"] for g in f16["per_graduation"]], float)
    good = np.isfinite(nn)
    ncoef = np.polyfit(kk[good], nn[good], 2)
    n_model = np.polyval(ncoef, k_map)
    n_resid_fit = nn[good] - np.polyval(ncoef, kk[good])
    print(f"  n(k) quadratic resid rms {np.sqrt(np.mean(n_resid_fit**2)):.2f} frames")

    # ---- uncertainty propagation ----
    # A, B and C are strongly correlated: the fitted CURVE is far better
    # determined than any single coefficient. Propagating their marginal
    # standard deviations as if independent overstates the depth uncertainty by
    # about an order of magnitude. So bootstrap the curve itself: resample the
    # graduations, refit, and take the spread of k(x_ref) across replicates.
    rng = np.random.default_rng(0x4D84B017)
    x_grid = np.linspace(span_lo - 80.0, span_hi + 80.0, 400)
    k_reps = []
    ab_reps = []
    for _ in range(1000):
        j = rng.integers(0, len(kept_k), len(kept_k))
        if len(np.unique(kept_k[j])) < 5:
            continue
        fb = fit_projective(kept_k[j], kept_x[j])
        Ab = fb["A"] - x_shift_13
        Bb = fb["B"] - fb["C"] * x_shift_13
        Cb = fb["C"]
        db = Bb - Cb * x_grid
        with np.errstate(divide="ignore", invalid="ignore"):
            k_reps.append((x_grid - Ab) / db)
        ab_reps.append((Ab, Bb, Cb))
    k_reps = np.array(k_reps)
    sig_k_grid = np.nanstd(k_reps, axis=0)
    print(f"  curve bootstrap: {len(k_reps)} replicates, sigma_k over the "
          f"graduation span {np.nanmin(sig_k_grid):.5f} .. {np.nanmax(sig_k_grid):.5f} grad")

    sA, sB, sC = (boot13[q][1] for q in "ABC")
    sA_c = float(np.std([r[0] for r in ab_reps]))
    sB_c = float(np.std([r[1] for r in ab_reps]))
    sC_c = float(np.std([r[2] for r in ab_reps]))
    dk_dx = 1.0 / denom
    resid_rms = float(np.sqrt(np.mean(resid**2)))

    sig_k_fit = np.interp(x_ref, x_grid, sig_k_grid,
                          left=sig_k_grid[0], right=sig_k_grid[-1])
    sig_k = np.sqrt(
        sig_k_fit**2
        + (dk_dx * resid_rms) ** 2
        + (dk_dx * s_sigma * (yq - y_ref)) ** 2
    )
    sig_depth = np.sqrt((sig_k * dZ) ** 2 + (k_map * dZ_sig) ** 2)

    # ---- validity mask ----
    k_lo = (span_lo - A_ref) / (B_ref - C_ref * span_lo)
    k_hi = (span_hi - A_ref) / (B_ref - C_ref * span_hi)
    in_span = (k_map >= min(k_lo, k_hi) - 0.5) & (k_map <= max(k_lo, k_hi) + 0.5)
    conf_floor = float(np.percentile(conf[in_span], 20)) if in_span.any() else 0.0
    masks = {}
    for tol in TOL_FRAMES:
        m = in_span & (conf >= conf_floor) & (np.abs(idx - n_model) <= tol)
        masks[tol] = m
        med_sig = float(np.median(sig_depth[m])) if m.any() else float("nan")
        print(f"  mask tol {tol:4.0f} frames: {m.sum()} q4 px "
              f"({100.0 * m.sum() / m.size:.2f}% of frame), "
              f"median sigma_depth {med_sig:.2f} um")

    valid = masks[25.0]
    med_sig = float(np.median(sig_depth[valid]))
    D2_pass = bool(med_sig < 25.0)

    # ---- independent 2-D check: does the plane predict focus off the tick row? ----
    # n_model comes from the GEOMETRIC plane law composed with the step-16 focus
    # calibration, both fitted on one row band. idx is the q4 best-focus index,
    # measured independently at every pixel. Their agreement over a
    # two-dimensional region is a check the one-dimensional fits cannot give
    # themselves. The tolerance gate is deliberately NOT applied here.
    probe = in_span & (conf >= conf_floor)
    dres = (idx - n_model)[probe]
    core = np.abs(dres - np.median(dres)) <= 25.0
    print(f"  2-D plane-vs-focus check over {probe.sum()} q4 px "
          f"(no tolerance gate): median {np.median(dres):+.2f} frames, "
          f"core fraction {core.mean():.3f}, core rms {np.sqrt(np.mean(dres[core]**2)):.2f} "
          f"frames = {np.sqrt(np.mean(dres[core]**2)) * f16['um_per_frame']:.1f} um")
    # D1 was registered as "relative depth u_k/u_0 uncertainty". Taken
    # literally as sigma_k/|k| it diverges at k -> 0, which is a property of
    # the chosen depth ORIGIN and not of the measurement; both readings are
    # reported and the divergence is disclosed rather than defined away.
    k_span_len = abs(k_hi - k_lo)
    D1_literal = float(np.median(sig_k[valid] / np.maximum(np.abs(k_map[valid]), 1e-9)))
    D1_span = float(np.median(sig_k[valid]) / k_span_len)
    print(f"  D2 median sigma_depth {med_sig:.3f} um (bar < 25) -> "
          f"{'PASS' if D2_pass else 'FAIL'}   "
          f"[p10 {np.percentile(sig_depth[valid], 10):.2f}, "
          f"p90 {np.percentile(sig_depth[valid], 90):.2f}]")
    print(f"  D1 literal sigma_k/|k| median {D1_literal * 100:.4f}% "
          f"(diverges at the k=0 origin); span-relative "
          f"sigma_k/k_span {D1_span * 100:.4f}% (bar < 0.5%)")
    dr = depth_um[valid]
    print(f"  depth range over valid mask: {dr.min():.1f} .. {dr.max():.1f} um "
          f"({(dr.max() - dr.min()) / 1000.0:.3f} mm)")

    try:
        import imageio.v2 as imageio

        def norm8(a, m, lo=None, hi=None):
            v = np.array(a, float)
            sel = v[m] if m.any() else v.ravel()
            lo = np.percentile(sel, 1) if lo is None else lo
            hi = np.percentile(sel, 99) if hi is None else hi
            g = np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)
            rgb = np.zeros(v.shape + (3,), np.uint8)
            rgb[..., 0] = (255 * g).astype(np.uint8)
            rgb[..., 1] = (255 * (1 - np.abs(2 * g - 1))).astype(np.uint8)
            rgb[..., 2] = (255 * (1 - g)).astype(np.uint8)
            rgb[~m] = 30
            return rgb

        imageio.imwrite(OUT / "17-depth.png", norm8(depth_um, valid))
        imageio.imwrite(OUT / "17-sigma.png", norm8(sig_depth, valid))
        imageio.imwrite(
            OUT / "17-valid.png", (valid.astype(np.uint8) * 255)
        )
        print("  wrote 17-depth.png, 17-sigma.png, 17-valid.png "
              "(navigation only, not evidence)")
    except Exception as exc:  # pragma: no cover
        print(f"  preview PNGs skipped: {exc}")

    np.savez_compressed(
        OUT / "depth-truth-highly-angled-ruler-mm-cpl.npz",
        depth_um=depth_um.astype(np.float32),
        depth_sigma_um=sig_depth.astype(np.float32),
        valid=valid,
        k_index=k_map.astype(np.float32),
        n_model=n_model.astype(np.float32),
    )

    params = {
        "stack": STACK,
        "grid": "q4 (quad-grid green plane decimated 4x); "
                "quad px = 2 sensor px = 10.24 um at the sensor",
        "q4_shape": [int(H4), int(W4)],
        "quad_from_q4": {"scale": Q4, "offset": (Q4 - 1) * 0.5},
        "model": (
            "x_ref = x_quad - s*(y_quad - y_ref); "
            "k = (x_ref - A)/(B - C*x_ref); depth_um = k*dZ_per_grad. "
            "Depth origin is graduation k=0; the map is RELATIVE depth on an "
            "ABSOLUTE metric scale."
        ),
        "s": float(s_hat),
        "s_sigma": float(s_sigma),
        "y_ref": float(y_ref),
        "A": float(A_ref),
        "B": float(B_ref),
        "C": float(C_ref),
        "A_sigma": float(sA),
        "B_sigma": float(sB),
        "C_sigma": float(sC),
        "tick_resid_rms_px": resid_rms,
        "sigma_k_grid_x": x_grid.tolist(),
        "sigma_k_grid": sig_k_grid.tolist(),
        "curve_bootstrap_reps": int(len(k_reps)),
        "coef_sd_marginal_step13": {"A": sA, "B": sB, "C": sC},
        "coef_sd_marginal_step17": {"A": sA_c, "B": sB_c, "C": sC_c},
        "dZ_per_grad_um": dZ,
        "dZ_per_grad_um_sd": dZ_sig,
        "n_model_poly_k2k1k0": ncoef.tolist(),
        "mask": {
            "k_span": [float(min(k_lo, k_hi)), float(max(k_lo, k_hi))],
            "k_margin": 0.5,
            "conf_floor": conf_floor,
            "tol_frames": 25.0,
            "rule": "in_span AND conf >= conf_floor AND |idx_q4 - n_model| <= tol",
        },
        "results": {
            "iso_depth_ticks": iso_depth,
            "band_shifts_px": shifts.tolist(),
            "band_y": band_y.tolist(),
            "parallelism": par,
            "L3_coverage": float(L3),
            "P1_after_rejection": P1,
            "D1_literal_median_relative": D1_literal,
            "D1_span_relative": D1_span,
            "D2_median_sigma_um": med_sig,
            "D2_p10_sigma_um": float(np.percentile(sig_depth[valid], 10)),
            "D2_p90_sigma_um": float(np.percentile(sig_depth[valid], 90)),
            "D2_pass": D2_pass,
            "shear_s": float(s_hat),
            "shear_s_sigma": float(s_sigma),
            "plane_vs_focus_2d": {
                "probe_q4_px": int(probe.sum()),
                "median_frames": float(np.median(dres)),
                "core_fraction": float(core.mean()),
                "core_rms_frames": float(np.sqrt(np.mean(dres[core] ** 2))),
                "core_rms_um": float(
                    np.sqrt(np.mean(dres[core] ** 2)) * f16["um_per_frame"]
                ),
            },
            "tick_tilt_deg_from_vertical": float(np.degrees(np.arctan(s_hat))),
            "valid_q4_px": int(valid.sum()),
            "valid_fraction_of_frame": float(valid.sum() / valid.size),
            "depth_span_um": [float(dr.min()), float(dr.max())],
            "mask_sensitivity": {
                str(int(t)): int(masks[t].sum()) for t in TOL_FRAMES
            },
        },
    }
    (OUT / "17-depthmap.json").write_text(json.dumps(params, indent=1))
    (OUT / "depth-truth-params.json").write_text(json.dumps(params, indent=1))
    print("  wrote depth-truth-params.json and the .npz expansion")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
