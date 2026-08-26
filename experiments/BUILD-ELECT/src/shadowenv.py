"""Is the merge lifting a real shadow? Measured against the frames themselves.

The owner's task 2. The finding to be tested came from a radial profile:
`coffee-bean`, backdrop at d=120-250 px, focus-INVARIANT across the bracket at
-5.70% to -7.03%, truth about -6.4%, control -4.35%, blend -3.80%. Roughly 40%
of a real shadow's depth lost by both arms.

That number rests on one estimator: a brightness mask, a distance transform, a
radial median and a far-field reference. If any of those is soft, everything
downstream is soft. **This is a second, independent estimator for the same
quantity**, sharing none of those four:

  * no radial median -- per-pixel;
  * no far-field reference -- each image is normalised by its OWN unshadowed
    reference patch, which is also the only way to compare a rawpy decode with
    a strehl render at all, since their DN scales differ;
  * no distance transform in the estimator (it is used only to propose the
    regions, and the picture shows what it proposed so the reader can reject it);
  * and one test the radial version cannot do at all -- the ENVELOPE test below.

**The envelope test.** A merge that selects a frame per pixel, or averages
frames, is bounded per pixel by the min and max over the frames it merged. It
cannot produce a value outside that range. So per pixel:

    merge > max over frames   =>  light was manufactured, not selected
    merge < min over frames   =>  light was destroyed

Frames are unregistered here, and that only ever WIDENS the envelope, so it
makes both violations harder to trigger. A positive result is therefore
conservative. (A negative result is not: a wide envelope can hide a real lift.)

Commissioning, because a detector that has never returned a known answer is not
an instrument:

  * PLANT -- a synthetic merge built by darkening the reference render's shadow
    region by a known factor. The measurement must return that factor.
  * NULL -- the same measurement on a region with no shadow. It must return
    approximately zero.

Both run every time, above the result, and the verdict is never the only output.

    python shadowenv.py <raw-dir> <merge.tif> [<merge2.tif> ...]
        [--shadow LO,HI] [--ref LO,HI] [--limit N] [--out <png>]
"""

import pathlib
import sys

import numpy as np
import rawpy
import tifffile
from scipy import ndimage

import ringprofile as rp

SHADOW = (120, 250)      # signed distance band the finding lives in, px
REF = (600, 1400)        # unshadowed reference, px
PLANT = 0.90             # known darkening for the commissioning plant
ORDERS = (1, 2, 3, 4, 5)  # backdrop surface orders, all reported, none chosen
NULL_FIT = (1000, 1800)  # null mirrors the real fit/predict geometry exactly
NULL_PRED = (520, 650)


def bin2(a):
    """2x2 box-bin, to bring a full-res render onto the half_size frame grid."""
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    return a[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


MARGIN = 16


def _zn(a):
    a = a - a.mean()
    return a / max(float(np.sqrt((a * a).sum())), 1e-9)


def best_shift(ref, mov, search=MARGIN, patch=1200):
    """Integer-only shift aligning the merge grid onto the frame grid.

    rawpy half_size and a 2x2-binned strehl render do not have the same shape:
    the renders are cropped differently. The offset is MEASURED here, not
    assumed, and it is integer-only on purpose -- sub-pixel resampling would
    add blur to the very quantity this file measures.

    Returns (dy, dx, best, zero, second) where the three scores are normalised
    cross-correlations, so the caller can see whether the peak is sharp.
    """
    h = min(ref.shape[0], mov.shape[0]) - 2 * search
    w = min(ref.shape[1], mov.shape[1]) - 2 * search
    ph, pw = min(patch, h), min(patch, w)
    y0, x0 = search + (h - ph) // 2, search + (w - pw) // 2
    r = _zn(ref[y0:y0 + ph, x0:x0 + pw].astype(np.float64))
    scores = {}
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            m = mov[y0 + dy:y0 + dy + ph, x0 + dx:x0 + dx + pw]
            if m.shape != r.shape:
                continue
            scores[(dy, dx)] = float((r * _zn(m.astype(np.float64))).sum())
    order = sorted(scores.items(), key=lambda kv: -kv[1])
    (dy, dx), best = order[0]
    second = next((v for (k, v) in order[1:] if max(abs(k[0] - dy),
                                                    abs(k[1] - dx)) > 1), 0.0)
    return dy, dx, best, scores.get((0, 0), 0.0), second


def frame_luma(path):
    with rawpy.imread(str(path)) as r:
        rgb = r.postprocess(half_size=True, no_auto_bright=True,
                            output_bps=16, gamma=(1, 1), user_flip=0)
    return rgb.astype(np.float32).mean(axis=2)


def norm_by(a, sel):
    """Scale so the reference region has mean 1. Removes every DN-scale
    difference between a rawpy decode and a strehl render, which is the only
    way the two can be compared at all."""
    m = float(a[sel].mean())
    return a / max(m, 1e-9), m


def depth(a, shadow_sel, ref_sel):
    """Shadow depth as a within-image fraction. Instrument-free by construction."""
    s = float(a[shadow_sel].mean())
    r = float(a[ref_sel].mean())
    return 100.0 * (s / max(r, 1e-9) - 1.0), s, r


def depth_med(a, shadow_sel, ref_sel):
    """Same quantity, median instead of mean.

    Not cosmetic. The original finding was produced by a RADIAL MEDIAN profile;
    this file's primary estimator is a band MEAN. On an annulus that is 22%
    non-uniform across itself -- measured, see the NULL -- those two are not
    the same number, and the difference is a candidate explanation for any
    disagreement between the two instruments.
    """
    s = float(np.median(a[shadow_sel]))
    r = float(np.median(a[ref_sel]))
    return 100.0 * (s / max(r, 1e-9) - 1.0), s, r


def _terms(x, y, order):
    """Bivariate polynomial terms for 1-D coordinate vectors."""
    return np.stack([(x ** i) * (y ** j)
                     for i in range(order + 1)
                     for j in range(order + 1 - i)], axis=1)


def _coords(shape):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    return (xx / (w - 1.0)) * 2.0 - 1.0, (yy / (h - 1.0)) * 2.0 - 1.0


def fit_backdrop(img, xx, yy, fit_sel, order=3, cap=300000, seed=0):
    """Least-squares low-order surface through the UNSHADOWED backdrop only.

    Why this exists: the ratio estimator above divides the shadow band by a
    distant reference band, which is only valid if the backdrop is flat between
    them. On `coffee-bean` it is not -- two halves of the reference differ by
    22%, measured. A shadow measured against a sloping backdrop is a shadow plus
    a slope, and the two cannot be told apart afterwards.

    The shadow band is an annulus ENCLOSED by the reference band, so predicting
    it from the fit is interpolation, not extrapolation.

    Returns the coefficients. Fit pixels are subsampled to `cap` with a fixed
    seed -- a smooth surface does not need a million points and the memory does.
    """
    idx = np.flatnonzero(fit_sel.ravel())
    if len(idx) > cap:
        idx = np.random.default_rng(seed).choice(idx, cap, replace=False)
    A = _terms(xx.ravel()[idx], yy.ravel()[idx], order)
    coef, *_ = np.linalg.lstsq(A, img.ravel()[idx].astype(np.float64),
                               rcond=None)
    return coef


def predict(coef, xx, yy, sel, order):
    return _terms(xx[sel], yy[sel], order) @ coef


def main():
    argv = sys.argv[1:]
    out, limit, mask_from = "shadowenv.png", None, None
    for flag in ("--out", "--limit", "--mask-from"):
        if flag in argv:
            i = argv.index(flag)
            if flag == "--out":
                out = argv[i + 1]
            elif flag == "--mask-from":
                mask_from = argv[i + 1]
            else:
                limit = int(argv[i + 1])
            del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 2

    raw_dir, merges = pathlib.Path(args[0]), args[1:]
    frames = sorted(raw_dir.glob("*.ARW"))
    if limit:
        frames = frames[::max(1, len(frames) // limit)][:limit]
    if not frames:
        print(f"  no ARW under {raw_dir}")
        return 2

    ref_img = rp.load_luma(merges[0])
    mask_src = mask_from or merges[0]
    mask, thr, kept, found = rp.subject_mask(
        ref_img if mask_src == merges[0] else rp.load_luma(mask_src))
    signed = rp.signed_distance(mask)
    sh_full = (signed >= SHADOW[0]) & (signed <= SHADOW[1])
    rf_full = (signed >= REF[0]) & (signed <= REF[1])

    probe = frame_luma(frames[len(frames) // 2])
    mref = bin2(ref_img)
    dy, dx, best, zero, second = best_shift(probe, mref)
    H = min(probe.shape[0], mref.shape[0]) - 2 * MARGIN
    W = min(probe.shape[1], mref.shape[1]) - 2 * MARGIN
    crop_f = lambda a: a[MARGIN:MARGIN + H, MARGIN:MARGIN + W]
    crop_m = lambda a: a[MARGIN + dy:MARGIN + dy + H, MARGIN + dx:MARGIN + dx + W]

    sh = crop_m(bin2(sh_full.astype(np.float32))) > 0.5
    rf = crop_m(bin2(rf_full.astype(np.float32))) > 0.5

    print(f"raw dir : {raw_dir}   {len(frames)} frames used")
    print(f"  GRID: frame {probe.shape} vs binned merge {mref.shape} -- they "
          f"do not match, so the offset is measured, not assumed.")
    print(f"    integer shift (dy,dx) = ({dy:+d},{dx:+d})   ncc {best:.5f}   "
          f"at zero shift {zero:.5f}   best non-adjacent rival {second:.5f}")
    print(f"    common window {H} x {W}. Integer-only on purpose: sub-pixel "
          f"resampling would blur the quantity being measured.")
    print(f"regions proposed from : {pathlib.Path(mask_src).name}")
    print(f"  mask {mask.mean() * 100:.2f}% of frame, {kept} component kept "
          f"of {found} found; POSITIVE d IS OUTWARD")
    print(f"  shadow band d={SHADOW[0]}-{SHADOW[1]} px : {int(sh.sum())} px "
          f"on the half-res grid")
    print(f"  reference   d={REF[0]}-{REF[1]} px : {int(rf.sum())} px")
    print()

    xx, yy = _coords(sh.shape)

    # ---------------- COMMISSIONING, before any result -----------------------
    print(f"  COMMISSIONING")
    base = crop_m(bin2(ref_img))
    d0, s0, r0 = depth(base, sh, rf)
    planted = base.copy()
    planted[sh] *= PLANT
    d1, s1, r1 = depth(planted, sh, rf)
    want = 100.0 * (PLANT * (1.0 + d0 / 100.0) - 1.0)
    print(f"    PLANT: darken the shadow band by x{PLANT:.2f} and re-measure.")
    print(f"      before {d0:+.3f}%  ({s0:.1f} DN vs {r0:.1f} DN)")
    print(f"      after  {d1:+.3f}%  ({s1:.1f} DN vs {r1:.1f} DN)")
    print(f"      expected {want:+.3f}%   error {d1 - want:+.4f} points   "
          f"{'PASS' if abs(d1 - want) < 0.05 else 'FAIL'}")
    half = np.zeros_like(sh)
    idx = np.argwhere(rf)
    if len(idx):
        cut = idx[len(idx) // 2][0]
        half[rf & (np.arange(sh.shape[0])[:, None] < cut)] = True
    other = rf & ~half
    if half.sum() > 1000 and other.sum() > 1000:
        dn = 100.0 * (base[half].mean() / base[other].mean() - 1.0)
        print(f"    NULL: two halves of the unshadowed reference against each "
              f"other.")
        print(f"      {dn:+.3f}%  ({base[half].mean():.1f} DN vs "
              f"{base[other].mean():.1f} DN)   "
              f"{'PASS' if abs(dn) < 2.0 else 'FAIL -- the reference is not flat'}")
    print()

    # ---- the gradient-removing estimator, and its own commissioning ---------
    # The order is NOT chosen after seeing the answer. Every order is reported,
    # for the frames and for both merges. If the conclusion is the same at every
    # order, the choice does not matter; if it is not, it was never a result.
    #
    # The null MIRRORS THE REAL GEOMETRY. The real use fits an 800 px-wide
    # reference band (d=600-1400) and predicts a 130 px band (d=120-250) that
    # sits 350 px inside it -- an inward extrapolation across a gap. So the null
    # fits an 800 px band (d=1000-1800) and predicts a 130 px band (d=520-650)
    # sitting 350 px inside it, on backdrop that carries no cast shadow.
    #
    # A first attempt split the reference into top and bottom halves. That put
    # the held-out set outside the fitted domain in y, and the polynomials
    # diverged to 1e15. A null that tests the wrong extrapolation is not a null.
    nf_full = (signed >= NULL_FIT[0]) & (signed <= NULL_FIT[1])
    np_full = (signed >= NULL_PRED[0]) & (signed <= NULL_PRED[1])
    nf = crop_m(bin2(nf_full.astype(np.float32))) > 0.5
    npr = crop_m(bin2(np_full.astype(np.float32))) > 0.5

    def _sub(sel, cap, seed):
        i = np.flatnonzero(sel.ravel())
        return (np.random.default_rng(seed).choice(i, cap, replace=False)
                if len(i) > cap else i)

    idx_fit = _sub(rf, 150000, 0)
    idx_nf = _sub(nf, 150000, 1)
    idx_np = _sub(npr, 100000, 2)
    xr, yr = xx.ravel(), yy.ravel()
    RC = 1e-8   # pinv default rcond is 1e-15: it lets a rank-deficient thin
                # annulus produce coefficients of 1e15. Regularise.
    P = {o: np.linalg.pinv(_terms(xr[idx_fit], yr[idx_fit], o), rcond=RC)
         for o in ORDERS}
    A_sh = {o: _terms(xx[sh], yy[sh], o) for o in ORDERS}
    Pn = {o: np.linalg.pinv(_terms(xr[idx_nf], yr[idx_nf], o), rcond=RC)
          for o in ORDERS}
    A_np = {o: _terms(xr[idx_np], yr[idx_np], o) for o in ORDERS}

    def fitdepth(img, o):
        coef = P[o] @ img.ravel()[idx_fit].astype(np.float64)
        p = float((A_sh[o] @ coef).mean())
        s = float(img[sh].mean())
        return 100.0 * (s / max(p, 1e-9) - 1.0), s, p

    def fitnull(img, o):
        coef = Pn[o] @ img.ravel()[idx_nf].astype(np.float64)
        p = float((A_np[o] @ coef).mean())
        s = float(img.ravel()[idx_np].mean())
        return 100.0 * (s / max(p, 1e-9) - 1.0)

    print(f"    FIT NULL: same geometry as the real measurement, on backdrop "
          f"with no cast shadow.")
    print(f"      fit d={NULL_FIT[0]}-{NULL_FIT[1]} ({int(nf.sum())} px), "
          f"predict d={NULL_PRED[0]}-{NULL_PRED[1]} ({int(npr.sum())} px). "
          f"A shadow-free band must come back at zero.")
    print(f"      {'order':>6} {'terms':>6} {'held-out null':>14} "
          f"{'planted depth':>14} {'expected':>10} {'error':>8}")
    for o in ORDERS:
        nul = fitnull(base, o)
        d_b, _, _ = fitdepth(base, o)
        d_p, _, _ = fitdepth(planted, o)
        want_f = 100.0 * (PLANT * (1.0 + d_b / 100.0) - 1.0)
        ok = abs(nul) < 0.5 and abs(d_p - want_f) < 0.05
        print(f"      {o:>6} {A_sh[o].shape[1]:>6} {nul:>+13.3f}% "
              f"{d_p:>+13.3f}% {want_f:>+9.3f}% {d_p - want_f:>+7.3f}"
              f"  {'PASS' if ok else 'FAIL'}")
    print(f"      A high held-out null means the surface cannot represent this "
          f"backdrop and no depth taken against it is trustworthy.")
    print()

    # ---------------- the frames ---------------------------------------------
    print(f"  reading {len(frames)} frames (rawpy, half_size, linear, "
          f"no auto-bright)")
    fmin = fmax = fsum = None
    depths = []
    dmed = []
    fitd = []
    sharp = []
    for i, f in enumerate(frames):
        L = crop_f(frame_luma(f))
        if fmin is None:
            if L.shape != sh.shape:
                print(f"    grid mismatch: frame {L.shape} vs merge/2 {sh.shape}")
                return 2
            fmin, fmax, fsum = L.copy(), L.copy(), L.astype(np.float64)
        else:
            np.minimum(fmin, L, out=fmin)
            np.maximum(fmax, L, out=fmax)
            fsum += L
        d, s, r = depth(L, sh, rf)
        depths.append((f.stem, d, s, r))
        dmed.append(depth_med(L, sh, rf)[0])
        fitd.append([fitdepth(L, o)[0] for o in ORDERS])
        gy, gx = np.gradient(L)
        sharp.append(float(np.hypot(gx, gy)[sh].mean()))
        if i % 20 == 0:
            print(f"    {i + 1}/{len(frames)} {f.stem}  ratio {d:+.2f}%  "
                  f"fit(o=3) {fitd[-1][ORDERS.index(3)]:+.2f}%  "
                  f"sharp {sharp[-1]:.1f}")
    fmean = (fsum / len(frames)).astype(np.float32)
    fitd = np.array(fitd)
    print()

    dv = np.array([d for _, d, _, _ in depths])
    print(f"  SHADOW DEPTH PER FRAME, within-image, no far-field reference")
    print(f"    n={len(dv)}  min {dv.min():+.2f}%  max {dv.max():+.2f}%  "
          f"mean {dv.mean():+.2f}%  median {np.median(dv):+.2f}%  "
          f"sd {dv.std():.2f}")
    print(f"    spread {dv.max() - dv.min():.2f} points. A focus-INVARIANT "
          f"deficit is real shadow; a focus-dependent one is defocus bleed.")
    lo = min(depths, key=lambda t: t[1])
    hi = max(depths, key=lambda t: t[1])
    print(f"    deepest  {lo[0]} {lo[1]:+.2f}%   shallowest {hi[0]} {hi[1]:+.2f}%")
    print()
    sv = np.array(sharp)
    rk = np.argsort(-sv)
    cc = float(np.corrcoef(sv, dv)[0, 1]) if len(sv) > 2 else float("nan")
    print(f"  IS THE DEFICIT FOCUS-INVARIANT? The original finding said yes, "
          f"and that is what licenses averaging every frame into a 'truth'.")
    print(f"    corr(sharpness in band, depth) = {cc:+.3f} over {len(sv)} "
          f"frames.  |r| near 0 is focus-invariant; large |r| is not.")
    k = max(1, len(rk) // 10)
    top, bot = dv[rk[:k]], dv[rk[-k:]]
    print(f"    sharpest {k} frames: depth {top.mean():+.2f}%   "
          f"softest {k}: {bot.mean():+.2f}%   difference "
          f"{top.mean() - bot.mean():+.2f} points")
    print(f"    TRUTH AT PEAK BACKDROP SHARPNESS = {top.mean():+.2f}% -- the "
          f"frames that actually resolved the shadow edge. The all-frame mean "
          f"{dv.mean():+.2f}% mixes them with frames in which the backdrop is "
          f"defocused and the edge is smeared.")
    print()
    mv = np.array(dmed)
    print(f"  MEAN vs MEDIAN over the same band, same frames. The original "
          f"finding used a radial MEDIAN; this file's primary estimator is a "
          f"band MEAN.")
    print(f"    mean-based   truth {dv.mean():+.2f}%  (min {dv.min():+.2f}, "
          f"max {dv.max():+.2f})")
    print(f"    median-based truth {mv.mean():+.2f}%  (min {mv.min():+.2f}, "
          f"max {mv.max():+.2f})   difference "
          f"{mv.mean() - dv.mean():+.2f} points")
    print()
    print(f"  SAME FRAMES, GRADIENT REMOVED (depth against the fitted backdrop)")
    print(f"    {'order':>6} {'mean':>9} {'median':>9} {'min':>9} {'max':>9} "
          f"{'spread':>8} {'sd':>7}")
    for k, o in enumerate(ORDERS):
        c = fitd[:, k]
        print(f"    {o:>6} {c.mean():>+8.2f}% {np.median(c):>+8.2f}% "
              f"{c.min():>+8.2f}% {c.max():>+8.2f}% "
              f"{c.max() - c.min():>7.2f} {c.std():>7.2f}")
    print()

    # ---------------- each merge against the frames --------------------------
    print(f"  {'merge':<34} {'depth':>9} {'vs truth':>9} {'lost':>7} "
          f"{'median':>9} {'vs med':>8} "
          f"{'>max %':>8} {'<min %':>8} {'>max ref%':>10}")
    results = []
    for m in merges:
        img = crop_m(bin2(rp.load_luma(m)))
        d, s, r = depth(img, sh, rf)
        dm = depth_med(img, sh, rf)[0]
        lost = 100.0 * (1.0 - d / dv.mean()) if dv.mean() else float("nan")
        n_img, _ = norm_by(img, rf)
        n_max, _ = norm_by(fmax, rf)
        n_min, _ = norm_by(fmin, rf)
        over = float((n_img[sh] > n_max[sh]).mean()) * 100.0
        under = float((n_img[sh] < n_min[sh]).mean()) * 100.0
        over_ref = float((n_img[rf] > n_max[rf]).mean()) * 100.0
        print(f"  {pathlib.Path(m).name:<34} {d:>+8.2f}% "
              f"{d - dv.mean():>+8.2f} {lost:>6.1f}% "
              f"{dm:>+8.2f}% {dm - mv.mean():>+7.2f} "
              f"{over:>7.2f}% {under:>7.2f}% {over_ref:>9.2f}%")
        results.append((m, img, n_img, n_max, d, over, under, over_ref))
    print(f"  'vs truth' and 'vs med' are (merge - frames) in points. POSITIVE "
          f"means the merge renders the shadow SHALLOWER than the frames -- "
          f"shadow lift. NEGATIVE means deeper.")
    print()
    print(f"  SAME COMPARISON, GRADIENT REMOVED. Every order shown. If the "
          f"sign of 'vs truth' is not the same at every order it was never a "
          f"result.")
    hdr = "".join(f"{'o=' + str(o):>19}" for o in ORDERS)
    print(f"    {'arm':<30}{hdr}")
    print(f"    {'frames (truth)':<30}" +
          "".join(f"{fitd[:, k].mean():>+13.2f}%{'':>5}"
                  for k in range(len(ORDERS))))
    for m in merges:
        img = crop_m(bin2(rp.load_luma(m)))
        cells = []
        for k, o in enumerate(ORDERS):
            dm = fitdepth(img, o)[0]
            cells.append(f"{dm:>+13.2f}% {dm - fitd[:, k].mean():>+5.2f}")
        print(f"    {pathlib.Path(m).name:<30}" + "".join(cells))
    print(f"    each cell is: merge depth, then (merge - truth) in points. "
          f"A POSITIVE difference means the merge renders the shadow SHALLOWER "
          f"than the frames do -- shadow lift.")
    print()
    print(f"  '>max %' is the share of shadow-band pixels where the merge "
          f"exceeds the per-pixel MAXIMUM over all {len(frames)} frames -- "
          f"light that was manufactured, not selected.")
    print(f"  '>max ref%' is the same test in the UNSHADOWED reference band. "
          f"It is the null for the envelope test: if it is as high as '>max %' "
          f"then the envelope test is firing everywhere and means nothing.")
    print(f"  Frames are unregistered, which only WIDENS the envelope, so a "
          f"positive '>max %' is conservative and a zero is not informative.")
    print()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:                                # pragma: no cover
        print(f"  no picture: {exc}")
        return 0

    n = len(results)
    fig, ax = plt.subplots(2, max(n + 1, 2), figsize=(4.6 * max(n + 1, 2), 9.0),
                           squeeze=False)
    band = np.zeros(sh.shape, np.uint8)
    band[rf] = 1
    band[sh] = 2
    ax[0, 0].imshow(band[::3, ::3], cmap="viridis")
    ax[0, 0].set_title(f"regions: shadow d={SHADOW[0]}-{SHADOW[1]} (bright)\n"
                       f"reference d={REF[0]}-{REF[1]} (mid)", fontsize=9)
    v0, v1 = np.percentile(fmean, [1, 99])
    ax[1, 0].imshow(fmean[::3, ::3], cmap="gray", vmin=v0, vmax=v1)
    ax[1, 0].set_title(f"mean of {len(frames)} source frames\n"
                       f"shadow depth {dv.mean():+.2f}%", fontsize=9)
    for j, (m, img, n_img, n_max, d, over, under, over_ref) in enumerate(results):
        c0, c1 = np.percentile(img, [1, 99])
        ax[0, j + 1].imshow(img[::3, ::3], cmap="gray", vmin=c0, vmax=c1)
        ax[0, j + 1].set_title(f"{pathlib.Path(m).name}\n"
                               f"depth {d:+.2f}% vs truth {dv.mean():+.2f}%",
                               fontsize=9)
        viol = np.zeros(sh.shape, np.float32)
        viol[sh] = (n_img[sh] - n_max[sh])
        lim = float(np.percentile(np.abs(viol[sh]), 99)) or 1.0
        ax[1, j + 1].imshow(np.where(band[::3, ::3] > 0, viol[::3, ::3], np.nan),
                            cmap="coolwarm", vmin=-lim, vmax=lim)
        ax[1, j + 1].set_title(f"merge - per-pixel frame MAX\n"
                               f"red = manufactured light, {over:.2f}% of band",
                               fontsize=9)
    for row in ax:
        for a_ in row:
            a_.set_xticks([])
            a_.set_yticks([])
    fig.suptitle("Shadow depth against the source frames themselves. "
                 "Normalisation is each image's own unshadowed reference, "
                 "the only way a rawpy decode and a strehl render compare.",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
