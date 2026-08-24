"""R2 + R4 -- measure edge WIDTH, because every gradient functional has failed.

THE ROAD HERE, so the choice is not mistaken for a lucky guess:

  mech1.py  doubling a step HALVES tenengrad (0.5000, synthetic, exact).
            So the orchestrator's "doubling manufactures gradient energy"
            cannot be the mechanism. Only noise raises it from a flat base.
  bands.py  every octave band and every structure stratum, placebo exact.
            The null wins at 1-4px (0.9836-0.9974) and in the FLATTEST
            quartile (0.6303), where there is no detail to sharpen at all.
  peaks.py  every percentile of |grad| up to the top 0.01%, all three
            controls passing, and the null wins them ALL (0.9446 at the top).

The null holding the STRONGEST gradients in the frame is the tell. An abrupt
switch between elected frames displaced by hundreds of pixels is a step
discontinuity larger than any real scene edge. Gradient energy cannot tell that
defect from detail at any percentile or any scale.

Edge width is a different kind of quantity. It is not an energy, so structure
displaced into the wrong place does not contribute; it is a distance, measured
where a real edge actually is. It is also exactly what the eye reported: in
crop-wing-venation.png the null's bristles are smeared and partly doubled while
the aligned render's are single crisp strokes.

METHOD, and the named risk from PREREG2 is handled explicitly. The two arms do
not share a true feature position -- the null is a composite of frames at
different scales, so its features sit at an average position matching nothing,
and a ~12 px apparent displacement is visible between the panels. So edges are
LOCATED on a common reference (the mean of the arms) to choose which edges to
examine and in what direction, but each arm's profile is then RE-CENTRED on its
own 50% crossing before its width is measured. Width is a shape property and is
compared as one.

Both arms are sampled with the same interpolator at the same offsets, so
neither pays a resampling the other does not.

PRE-REGISTERED BAR (PREREG2 R4): treatment > 1.00, placebo 1.000 +/- 0.005,
blur plant > 1.30, direction plant < 1.00.
"""

import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, map_coordinates

HALF = 8.0
STEP = 0.25
TS = np.arange(-HALF, HALF + STEP / 2, STEP)


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    g = a[:, :, 1] if a.ndim == 3 else a
    return g.astype(np.float32)


def pick_edges(ref, n_want, seed=97):
    """Choose strong, locally isolated edges on the common reference."""
    s = gaussian_filter(ref, 2.0)
    gy, gx = np.gradient(s)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 99.5)
    ys, xs = np.nonzero(mag > thr)
    keep = ((ys > HALF + 4) & (ys < ref.shape[0] - HALF - 4) &
            (xs > HALF + 4) & (xs < ref.shape[1] - HALF - 4))
    ys, xs = ys[keep], xs[keep]
    rng = np.random.default_rng(seed)
    if ys.size > n_want:
        i = rng.choice(ys.size, n_want, replace=False)
        ys, xs = ys[i], xs[i]
    d = mag[ys, xs]
    return ys, xs, gy[ys, xs] / d, gx[ys, xs] / d


def profiles(img, ys, xs, ny, nx):
    """Sample each edge perpendicular to its direction, one row per edge."""
    yy = ys[:, None] + ny[:, None] * TS[None, :]
    xx = xs[:, None] + nx[:, None] * TS[None, :]
    v = map_coordinates(img, [yy.ravel(), xx.ravel()], order=1, mode="nearest")
    return v.reshape(len(ys), len(TS))


def widths(p):
    """10-90% rise width of each profile, re-centred on its own 50% crossing.

    Returns NaN for any profile that is not a clean single transition, so a
    seam or a texture patch cannot masquerade as an infinitely sharp edge.
    """
    lo = p[:, :6].mean(axis=1)
    hi = p[:, -6:].mean(axis=1)
    amp = hi - lo
    out = np.full(p.shape[0], np.nan)
    ok = np.abs(amp) > 200.0
    if not ok.any():
        return out
    q = (p[ok] - lo[ok, None]) / amp[ok, None]
    # Reject anything that overshoots badly: not a single clean transition.
    clean = (q.min(axis=1) > -0.25) & (q.max(axis=1) < 1.25)
    idx = np.nonzero(ok)[0][clean]
    q = q[clean]
    if q.shape[0] == 0:
        return out

    def cross(level):
        ge = q >= level
        first = np.argmax(ge, axis=1)
        valid = ge.any(axis=1) & (first > 0)
        t = np.full(q.shape[0], np.nan)
        i = np.nonzero(valid)[0]
        f = first[i]
        y0 = q[i, f - 1]
        y1 = q[i, f]
        frac = np.where(y1 != y0, (level - y0) / (y1 - y0), 0.0)
        t[i] = TS[f - 1] + frac * STEP
        return t

    w = cross(0.9) - cross(0.1)
    w[~np.isfinite(w)] = np.nan
    w[w <= 0] = np.nan
    out[idx] = w
    return out


def measure(a, z, label, rows, ys, xs, ny, nx, cy=None, cx=None):
    wa = widths(profiles(a, ys, xs, ny, nx))
    wz = widths(profiles(z, ys, xs, ny, nx))
    both = np.isfinite(wa) & np.isfinite(wz)
    n = int(both.sum())
    ma, mz = float(np.median(wa[both])), float(np.median(wz[both]))
    # Ratio of MEDIAN widths, and the median of the PER-EDGE ratio, which is
    # the paired version and is insensitive to the mix of edges retained.
    paired = float(np.median(wz[both] / wa[both]))
    r = mz / ma if ma else float("nan")
    rec = dict(label=label, n=n, width_a=ma, width_z=mz,
               ratio_of_medians=r, median_paired_ratio=paired)
    print(f"\n--- {label} ---")
    print(f"    edges used        {n}")
    print(f"    median width A    {ma:.4f} px")
    print(f"    median width B    {mz:.4f} px")
    print(f"    B/A widths        {r:.4f}   (>1 means A is sharper)")
    print(f"    median paired B/A {paired:.4f}")

    if cy is not None:
        # SPATIAL CONTROL, and it is the strongest one available: residual
        # misregistration is proportional to distance from the centre of the
        # similarity, so a registration effect MUST grow with radius and MUST
        # vanish at the centre. The image supplies its own placebo region.
        rad = np.hypot(ys[both] - cy, xs[both] - cx)
        pr = wz[both] / wa[both]
        qs = np.quantile(rad, np.linspace(0, 1, 5))
        bands = []
        print("    by radius (registration effect must GROW with radius):")
        for i in range(4):
            m = (rad >= qs[i]) & (rad <= qs[i + 1] if i == 3 else rad < qs[i + 1])
            if m.sum() < 50:
                continue
            v = float(np.median(pr[m]))
            bands.append(dict(r_lo=float(qs[i]), r_hi=float(qs[i + 1]),
                              n=int(m.sum()), paired=v))
            print(f"      r {qs[i]:7.0f}-{qs[i+1]:7.0f} px  n={int(m.sum()):>6}"
                  f"  paired B/A {v:.4f}")
        rec["radial"] = bands
    rows.append(rec)
    return paired


def main(argv):
    d = r"C:\dev\strehl-out\M86-align"
    a = load(rf"{d}\bee-3-ALIGNED.tif")
    z = load(rf"{d}\bee3-zoomnull.tif")
    assert a.shape == z.shape, "arms are not FOV-matched"
    print("dims", a.shape)

    ys, xs, ny, nx = pick_edges((a + z) * 0.5, 20000)
    print("candidate edges", ys.size)

    rows = []
    cy, cx = (a.shape[0] - 1) / 2.0, (a.shape[1] - 1) / 2.0
    print("=== CONTROLS ===")
    measure(z, z, "PLACEBO zoomnull vs itself (want 1.0000)", rows, ys, xs, ny, nx)

    # CALIBRATION LADDER. My pre-registered blur-plant bar of >1.30 was
    # specified for an ENERGY metric, where a sigma=1 blur removes a third of
    # the gradient energy. Widths do not behave that way: they add in
    # quadrature, so blurring an edge of effective sigma s by sigma b widens it
    # only to sqrt(s^2+b^2). The bar was mis-specified, and rather than quietly
    # restate it I measure the whole ladder and check it against that
    # prediction. If the measured ladder tracks quadrature, the metric is
    # calibrated and the bar was the wrong number; if it does not, the metric
    # is broken and nothing below it stands.
    base = None
    ladder = []
    for b in (0.5, 1.0, 2.0, 4.0):
        v = measure(z, gaussian_filter(z, b),
                    f"PLANT zoomnull vs blurred(zoomnull) sigma={b}",
                    rows, ys, xs, ny, nx)
        w0 = rows[-1]["width_a"]
        base = base if base is not None else w0 / 2.5631
        pred = float(np.hypot(base, b) / base)
        ladder.append(dict(sigma=b, measured=v, quadrature_prediction=pred))
        print(f"    quadrature prediction {pred:.4f}  measured {v:.4f}"
              f"  ratio {v/pred:.4f}")
    rows.append(dict(label="blur ladder vs quadrature", ladder=ladder,
                     base_sigma_px=base))

    dirp = measure(gaussian_filter(a, 1.0), z,
                   "DIRECTION PLANT blurred(aligned) vs zoomnull (want < 1.00)",
                   rows, ys, xs, ny, nx, cy, cx)

    print("\n=== TREATMENT (visual ground truth: aligned IS sharper) ===")
    tre = measure(a, z, "aligned vs zoomnull", rows, ys, xs, ny, nx, cy, cx)

    print("\n=== VERDICT against the pre-registered bar ===")
    print(f"  treatment       {tre:.4f}  {'PASS' if tre > 1.0 else 'FAIL'}"
          f"   (bar: > 1.00)")
    print(f"  direction plant {dirp:.4f}  {'PASS' if dirp < 1.0 else 'FAIL'}"
          f"   (bar: < 1.00)")
    print(f"  blur plant sigma=1.0 read {ladder[1]['measured']:.4f} against a"
          f" pre-registered bar of >1.30: FAIL AS WRITTEN.")
    print("  See the ladder above for whether the bar or the metric is wrong.")

    json.dump(rows, open(argv[1], "w"), indent=1)
    print("\nwrote", argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
