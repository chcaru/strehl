"""M87 / 64 -- a baseline-free halo instrument, and what the bee rim is made of.

WHY THIS EXISTS.  Step 63 ran this milestone's frozen band-profile instrument on
`bee3-full.tif`, the image the owner actually judged, and it FAILED TO READ AN
ARTIFACT THAT IS OBVIOUS TO THE EYE.  Measured there, at ROI_LEG:

    P(d) rises monotonically outward -- 31672 DN at the peak inside d<=30,
    32384 at d in [48,96], ~35600 at d in [150,200].  lift_local = +0.280%.

On `flower-bud-alone-cpl` the same statistic returned +18.97% against a +0.42%
bias floor.  So the instrument is not merely quieter here, it is reading the
wrong quantity.  Three causes, all disclosed in section 25:

  (a) ROI_LEG's "background" is a tangle -- open card, cast shadow, the bee's
      own defocused body seen between limbs, and pale hair brighter than tau.
      A median over all background pixels at radius d mixes populations whose
      levels differ by more than the artifact does.
  (b) There is a broad depression around the subject that is still deepening at
      d = 200, so EVERY baseline window available inside the ROI sits inside it.
      `local_base` and `far` are both contaminated; the statistic compares rim
      to rim.
  (c) The registered C-BROKEN control is INVALID on this stack.
      `L.shifted_mask` translates the true mask by (512,512) to make an invented
      boundary "in open background" -- but the bee covers 37.18% of this frame
      and 35.87% of ROI_LEG, so the translated mask lands ON THE BEE.  Its
      "background" set then contains real dark subject pixels and the arm
      returned lift_local = -14.502%, larger in magnitude than the real arm.
      That is not a bias floor, it is a contaminated measurement, and the N2
      ratio computed from it (0.0x, "FAIL") is meaningless rather than negative.
      Same defect class as the planted discs of step 58: a control whose
      required geometry does not exist where I put it.

So this step replaces the instrument with one that needs NO BASELINE AT ALL.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

THE STATISTIC.  For pixel p with through-focus samples v_0..v_{n-1} and elected
frame a(p), define the ELECTION BRIGHTNESS RANK

    R(p) = ( #{k : v_k < v_a} + 0.5 * #{k : v_k = v_a, k != a} ) / (n - 1)

the mid-rank percentile of the ELECTED value within that pixel's OWN through-
focus samples.  R is invariant to any per-pixel monotone transform: shading,
vignetting, the broad depression, the cast shadow, the local mix of card and
hair -- all cancel, because every pixel is scored only against itself.

Its null is analytic.  If selection is uncorrelated with brightness, R = 0.5.

THE MECHANISM IT TESTS.  At a background pixel beside a dark defocused limb, the
frames differ in how much of the limb's blur disc covers that pixel.  Frames
where the limb is sharp are frames where its disc has shrunk off the pixel, so
the pixel is BRIGHT there; frames where the background is sharp are frames where
the limb is maximally defocused and its dark disc covers the pixel, so the pixel
is DARK there.  The focus response at that pixel is dominated by the limb's
edge, so the election picks the limb-sharp frame -- the bright one.  Selection
is therefore a max-like operator on brightness in the veiled band, and

    R1 (REGISTERED):  R(d) > 0.5 for small d, returning to 0.5 far away.

    R2 (REGISTERED):  the reach.  I predict R(d) crosses back below 0.55 at
    d* somewhere in 10..40 binned px, i.e. the same order as the ~20 px band
    measured on the bud in section 24.4, not 1-2 px and not 150 px.

    R3 (REGISTERED):  gate 2 (noise-gated average, n_eff mean 23.04) does not
    remove it.  |R_gate2(d) - R_gate0(d)| < 0.02 for all d <= 40.

CONTROLS -- registered, and all run regardless of outcome.

  C-RANDK (deliberately broken arm).  R recomputed with a UNIFORMLY RANDOM frame
      index per pixel instead of the elected one.  Its expectation is exactly
      0.5 at every d.  This is the bias floor and it is analytic, so unlike step
      63's C-BROKEN it cannot be invalidated by where the subject happens to be.
  C-SHUF (second broken arm).  R recomputed with the elected-index FIELD rolled
      by (317, 511) px, preserving its marginal distribution and destroying its
      registration with the boundary.  Expectation 0.5.
  C-FARNULL.  R at d >= 80 must sit at 0.5 within the C-RANDK scatter.
  C-PARAM (varies MY parameter, per fact P64).  The whole R(d) curve recomputed
      at mask tau x0.9, x1.0, x1.1.  R2's d* must not move by more than 50%.
  C-LINEAR.  Arm X below assumes the judged TIFF is linear in scene radiance.
      Tested, not assumed: `bee3-g0.tif` is regressed against the cache's
      `bee3-leg-sel.npy`, which is raw green DN and linear by construction.
      Reported as R^2 and slope; if R^2 < 0.99 the chromaticity arm is caveated.

ARM X -- CHROMATICITY CONVEXITY, and M107's demosaic hypothesis.
  Commit bdfd12c (facts 1377-1378) names Malvar-He-Cutler demosaic fringing at
  high-contrast diagonal edges as M107's candidate (c) for bright bee-edge
  artifacts.  It is a competing explanation for what I am measuring and it
  belongs to another milestone, so I test for it rather than assume it away.
  A two-layer composite a*F + (1-a)*B is convex IN EVERY CHANNEL SIMULTANEOUSLY,
  so in the chromaticity plane (r, b) = (R, B)/(R+G+B) the veil must lie ON the
  segment joining deep subject to far background.  Demosaic fringing displaces
  colour PERPENDICULAR to that segment.
    X1 (REGISTERED): the halo band's perpendicular offset from the segment, as a
    fraction of segment length, is below 0.05 -- and below the C-CHROMA-NULL
    floor obtained by splitting far background into two halves and measuring the
    same offset between them.
  If X1 fails, a share of the bee rim is chromatic, it is not a pure two-layer
  veil, and I hand that share to M107 instead of claiming it.

READ-ONLY: D:\\personal\\macro.  Writes only to experiments/M87-occlusion/data
and C:\\dev\\strehl-out\\M87-bee.
"""
import json
import pathlib
import sys
import time

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

ROI_LEG = L.ROIS["ROI_LEG"]
MARGIN = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
CUBE_ROI = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)
D_MAX = 96
MIN_BIN = 200
ROLL = (317, 511)
SEED = 8702


def rank_field(cube, argbest, rows=48):
    """R(p): mid-rank percentile of the elected sample within the pixel's own
    through-focus samples.  Streams the cube in row bands."""
    n, h, w = cube.shape
    out = np.empty((h, w), np.float32)
    for r0 in range(0, h, rows):
        r1 = min(r0 + rows, h)
        blk = np.asarray(cube[:, r0:r1, :], dtype=np.float32)
        sel = np.take_along_axis(blk, argbest[None, r0:r1, :].astype(np.intp), axis=0)[0]
        less = (blk < sel[None]).sum(axis=0)
        eq = (blk == sel[None]).sum(axis=0) - 1
        out[r0:r1] = (less + 0.5 * eq) / (n - 1)
    return out


def profile_of(field, mask, roi, d_max=D_MAX, min_bin=MIN_BIN):
    dist = distance_transform_edt(~mask)
    y0, y1, x0, x1 = roi
    dr = np.rint(dist[y0:y1, x0:x1]).astype(np.int32)
    bg = ~mask[y0:y1, x0:x1]
    v = field[y0:y1, x0:x1]
    prof = np.full(d_max + 1, np.nan)
    cnt = np.zeros(d_max + 1, np.int64)
    for d in range(1, d_max + 1):
        s = bg & (dr == d)
        cnt[d] = int(s.sum())
        if cnt[d] >= min_bin:
            prof[d] = float(np.median(v[s]))
    return prof, cnt


def crossing(prof, level=0.55):
    """First d at which the profile falls below `level` and stays there."""
    for d in range(1, len(prof)):
        if np.isfinite(prof[d]) and prof[d] < level:
            rest = prof[d:][np.isfinite(prof[d:])]
            if rest.size and float(np.nanmax(rest)) < level:
                return d
    return None


def main():
    t0 = time.time()
    rep = {}
    rng = np.random.default_rng(SEED)

    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    arg0 = np.load(CACHE / "bee3-leg-argbest.npy").astype(np.int32)
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    n, h, w = cube.shape
    print(f"cube {cube.shape}  mask fg={mask.mean():.4f}  ROI {CUBE_ROI}", flush=True)
    rep["inputs"] = {"cube": list(cube.shape), "mask_fg": float(mask.mean())}

    # ---------------------------------------------------------------- arm R
    print("\n=== ARM R: election brightness rank ===", flush=True)
    R = rank_field(cube, arg0)
    print(f"  R field done [{time.time() - t0:.0f}s]  mean={R.mean():.4f}", flush=True)

    kr = rng.integers(0, n, size=(h, w)).astype(np.int32)
    R_rand = rank_field(cube, kr)
    R_shuf = rank_field(cube, np.roll(arg0, ROLL, axis=(0, 1)))
    print(f"  C-RANDK mean={R_rand.mean():.4f}   C-SHUF mean={R_shuf.mean():.4f}  "
          f"[{time.time() - t0:.0f}s]", flush=True)

    p_true, cnt = profile_of(R, mask, CUBE_ROI)
    p_rand, _ = profile_of(R_rand, mask, CUBE_ROI)
    p_shuf, _ = profile_of(R_shuf, mask, CUBE_ROI)

    print("\n   d    n_px    R(true)   C-RANDK   C-SHUF", flush=True)
    for d in [1, 2, 3, 5, 8, 12, 16, 20, 25, 30, 40, 50, 60, 80, 96]:
        if np.isfinite(p_true[d]):
            print(f"  {d:3d} {cnt[d]:7d}   {p_true[d]:7.4f}   {p_rand[d]:7.4f}  "
                  f"{p_shuf[d]:7.4f}", flush=True)

    d_star = crossing(p_true, 0.55)
    far = np.nanmedian(p_true[80:97])
    far_rand = np.nanmedian(p_rand[80:97])
    print(f"\n  R1  R(1..5) = {np.nanmedian(p_true[1:6]):.4f}   "
          f"far d>=80 = {far:.4f}   C-RANDK far = {far_rand:.4f}", flush=True)
    r1 = bool(np.nanmedian(p_true[1:6]) > 0.55 and abs(far - 0.5) < 0.05)
    print(f"  R1 -> {'PASS' if r1 else 'FAIL'}", flush=True)
    r2 = bool(d_star is not None and 10 <= d_star <= 40)
    print(f"  R2  reach d*(R<0.55) = {d_star}  (registered 10..40) -> "
          f"{'PASS' if r2 else 'FAIL'}", flush=True)
    cr = float(np.nanmax(np.abs(p_rand[1:41] - 0.5)))
    cs = float(np.nanmax(np.abs(p_shuf[1:41] - 0.5)))
    print(f"  C-RANDK max|dev from 0.5| over d<=40 = {cr:.4f}", flush=True)
    print(f"  C-SHUF  max|dev from 0.5| over d<=40 = {cs:.4f}", flush=True)

    rep["armR"] = {
        "d": list(range(D_MAX + 1)),
        "R_true": [None if not np.isfinite(x) else round(float(x), 5) for x in p_true],
        "R_randk": [None if not np.isfinite(x) else round(float(x), 5) for x in p_rand],
        "R_shuf": [None if not np.isfinite(x) else round(float(x), 5) for x in p_shuf],
        "counts": [int(c) for c in cnt],
        "R_near_1_5": float(np.nanmedian(p_true[1:6])),
        "R_far_80_96": float(far), "R_randk_far": float(far_rand),
        "d_star_0p55": d_star, "R1": "PASS" if r1 else "FAIL",
        "R2": "PASS" if r2 else "FAIL",
        "C_RANDK_maxdev": cr, "C_SHUF_maxdev": cs,
    }

    # ---------------------------------------------------------------- R3
    print("\n=== R3: does the gate 2 average remove it? ===", flush=True)
    argg = CACHE / "bee3-leg-g2.npy"
    if argg.exists():
        g2 = np.load(argg)
        # rank of the gate-2 OUTPUT value within the pixel's own samples
        Rg2 = np.empty((h, w), np.float32)
        for r0 in range(0, h, 48):
            r1 = min(r0 + 48, h)
            blk = np.asarray(cube[:, r0:r1, :], dtype=np.float32)
            v = g2[None, r0:r1, :]
            Rg2[r0:r1] = ((blk < v).sum(axis=0) + 0.5 * (blk == v).sum(axis=0)) / (n - 1)
        p_g2, _ = profile_of(Rg2, mask, CUBE_ROI)
        dmax_dev = float(np.nanmax(np.abs(p_g2[1:41] - p_true[1:41])))
        print(f"  max|R_gate2 - R_gate0| over d<=40 = {dmax_dev:.4f}  "
              f"(registered < 0.02) -> {'PASS' if dmax_dev < 0.02 else 'FAIL'}", flush=True)
        for d in [1, 3, 8, 16, 30, 40]:
            print(f"    d={d:3d}  gate0={p_true[d]:.4f}  gate2={p_g2[d]:.4f}", flush=True)
        rep["R3"] = {"max_dev_d_le_40": dmax_dev,
                     "R_gate2": [None if not np.isfinite(x) else round(float(x), 5)
                                 for x in p_g2],
                     "verdict": "PASS" if dmax_dev < 0.02 else "FAIL"}

    # ---------------------------------------------------------------- C-PARAM
    print("\n=== C-PARAM: R2 under my own mask threshold, x0.9 / x1.0 / x1.1 ===",
          flush=True)
    _, tau0 = L.foreground_mask(sel0)
    cp = []
    for tm in (0.9, 1.0, 1.1):
        m2, _ = L.foreground_mask(sel0, tau=tau0 * tm)
        p2, _ = profile_of(R, m2, CUBE_ROI)
        d2 = crossing(p2, 0.55)
        cp.append({"tau_mul": tm, "fg": float(m2.mean()), "d_star": d2,
                   "R_near": float(np.nanmedian(p2[1:6]))})
        print(f"  tau x{tm:.1f}  fg={m2.mean():.4f}  R(1..5)={np.nanmedian(p2[1:6]):.4f}  "
              f"d*={d2}", flush=True)
    ds = [c["d_star"] for c in cp if c["d_star"]]
    ok = bool(ds and (max(ds) - min(ds)) <= 0.5 * np.mean(ds))
    print(f"  d* spread {min(ds) if ds else None}..{max(ds) if ds else None}  "
          f"(registered: within 50%) -> {'PASS' if ok else 'FAIL'}", flush=True)
    rep["C_PARAM"] = {"grid": cp, "tau0": float(tau0), "verdict": "PASS" if ok else "FAIL"}

    # ---------------------------------------------------------------- picture
    print("\n=== rendering the statistic next to the artifact ===", flush=True)
    y0, y1, x0, x1 = CUBE_ROI
    vis = np.clip((R[y0:y1, x0:x1] - 0.5) / 0.45, 0, 1)
    Image.fromarray((vis * 255).astype(np.uint8)).save(OUT / "64-rank-map.png")
    s = sel0[y0:y1, x0:x1].astype(np.float32)
    lo, hi = np.percentile(s, [0.5, 99.7])
    sv = np.clip((s - lo) / max(hi - lo, 1e-9), 0, 1) ** (1 / 2.2)
    Image.fromarray((sv * 255).astype(np.uint8)).save(OUT / "64-merge.png")
    rgbv = np.stack([vis, sv, np.zeros_like(vis)], axis=-1)
    Image.fromarray((rgbv * 255).astype(np.uint8)).save(OUT / "64-overlay.png")
    print(f"  wrote 64-rank-map.png / 64-merge.png / 64-overlay.png", flush=True)

    # ---------------------------------------------------------------- C-LINEAR
    print("\n=== C-LINEAR: is the judged TIFF linear in scene radiance? ===", flush=True)
    g0 = tifffile.imread(r"C:\dev\strehl-out\bee3-g0.tif")[..., 1].astype(np.float64)
    a = g0[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]].ravel()
    b = sel0[y0:y1, x0:x1].astype(np.float64).ravel()
    idx = rng.choice(a.size, size=min(400000, a.size), replace=False)
    aa, bb = a[idx], b[idx]
    sl, ic = np.polyfit(bb, aa, 1)
    pred = sl * bb + ic
    ss = 1.0 - float(((aa - pred) ** 2).sum() / ((aa - aa.mean()) ** 2).sum())
    print(f"  bee3-g0.tif[G] = {sl:.4f} * raw_green_DN + {ic:.1f}   R^2 = {ss:.6f}",
          flush=True)
    print(f"  -> {'LINEAR, chromaticity arm is sound' if ss > 0.99 else 'NOT LINEAR, arm X caveated'}",
          flush=True)
    rep["C_LINEAR"] = {"slope": float(sl), "intercept": float(ic), "r2": ss,
                       "linear": bool(ss > 0.99)}

    # ---------------------------------------------------------------- arm X
    print("\n=== ARM X: chromaticity convexity on the judged merge ===", flush=True)
    img = tifffile.imread(r"C:\dev\strehl-out\bee3-full.tif").astype(np.float64)
    gg = img[..., 1]
    fmask, ftau = L.foreground_mask(gg)
    dist_out = distance_transform_edt(~fmask)
    dist_in = distance_transform_edt(fmask)
    yy0, yy1, xx0, xx1 = ROI_LEG
    sub = (slice(yy0, yy1), slice(xx0, xx1))
    do, di = dist_out[sub], dist_in[sub]
    px = img[sub]
    band_r = d_star if d_star else 20

    def chroma(selmask, label):
        v = px[selmask]
        if v.shape[0] < 500:
            print(f"  {label}: only {v.shape[0]} px -- skipped", flush=True)
            return None
        s = v.sum(axis=1)
        good = s > 0
        r_ = np.median(v[good, 0] / s[good])
        b_ = np.median(v[good, 2] / s[good])
        print(f"  {label:22s} n={v.shape[0]:8d}  r={r_:.6f}  b={b_:.6f}  "
              f"mean DN={v.mean():.0f}", flush=True)
        return np.array([r_, b_])

    c_sub = chroma((di > 40), "deep subject")
    c_far = chroma((do >= 120), "far background")
    c_band = chroma((do >= 1) & (do <= band_r), f"halo band d<={band_r}")
    half = np.zeros_like(do, bool)
    half[::2] = True
    c_f1 = chroma((do >= 120) & half, "far bg half A")
    c_f2 = chroma((do >= 120) & ~half, "far bg half B")

    if c_sub is not None and c_far is not None and c_band is not None:
        seg = c_far - c_sub
        seglen = float(np.hypot(*seg))
        u = seg / max(seglen, 1e-12)
        rel = c_band - c_sub
        along = float(rel @ u)
        perp = float(abs(rel[0] * u[1] - rel[1] * u[0]))
        frac = perp / max(seglen, 1e-12)
        nul = None
        if c_f1 is not None and c_f2 is not None:
            nul = float(np.hypot(*(c_f2 - c_f1)) / max(seglen, 1e-12))
        print(f"\n  segment length |far - subject| = {seglen:.6f}", flush=True)
        print(f"  band position along segment    = {along / max(seglen, 1e-12):.4f} "
              f"(0 = subject, 1 = background)", flush=True)
        print(f"  band PERPENDICULAR offset      = {frac:.5f} of segment length", flush=True)
        if nul is not None:
            print(f"  C-CHROMA-NULL (far bg A vs B)  = {nul:.5f}", flush=True)
        x1 = bool(frac < 0.05 and (nul is None or frac < max(nul * 3, 0.05)))
        print(f"  X1 (registered: < 0.05 and near the null) -> "
              f"{'PASS -- convex in colour, a two-layer veil' if x1 else 'FAIL -- chromatic, share to M107'}",
              flush=True)
        rep["armX"] = {"tau": float(ftau), "band_r": int(band_r),
                       "c_subject": c_sub.tolist(), "c_far": c_far.tolist(),
                       "c_band": c_band.tolist(), "seg_len": seglen,
                       "along_frac": along / max(seglen, 1e-12), "perp_frac": frac,
                       "null_frac": nul, "X1": "PASS" if x1 else "FAIL"}

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "64-rank.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nwrote {DATA / '64-rank.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()
