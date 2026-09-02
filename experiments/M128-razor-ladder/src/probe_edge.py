"""M128 / probe_edge -- can this subject support an edge-based MTF measurement?

WHY THIS EXISTS

The razor lane spent its effort on estimators and never asked whether the
subject presents an edge at all. It does not. A single-bevel razor lit and
viewed from above shows its BEVEL, a ground facet hundreds of um wide that
shades continuously into the background, and the 50% level between the blade
body and the background falls in the middle of that facet. The reduction was
tracking an iso-brightness contour of a shading ramp.

That failure was invisible in every summary statistic the lane computed. It is
obvious in one full-resolution profile. So this tool prints the profile, and
applies the one acceptance test an SFR target has to pass.

THE TEST

A slanted-edge target must have a PLATEAU on both sides: a region where the
profile is flat to within a small fraction of the step contrast, reached within
a few multiples of the expected blur. Without plateaus the 10% and 90% levels
are undefined, the ESF wings carry subject structure into the transform, and
the resulting MTF is a Fourier transform of the subject rather than of the
lens. The razor's measured MTF fell to 0.02 by 30 cy/mm and then ROSE to 0.73
by 193 cy/mm, which no physical system can do.

DELIBERATELY OPTIMISTIC

Each column is registered on its own steepest gradient before averaging. That
correlates the registration with the noise in the very samples being averaged
and biases the result SHARPER than the truth, and it also absorbs all edge
raggedness for free. That bias is chosen on purpose: this is a screening tool,
and a subject that fails under the most flattering reduction available has
failed for real. A subject that passes here still has to be measured properly.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "M88-optical-ceiling" / "src"))
import m88lib as L  # noqa: E402

FLAT_FRAC_PER_UM = 0.001   # a plateau drifts by <0.1% of contrast per um


def column_shift_stack(band, smooth=3, tol_rows=6.0, min_frac=0.30):
    """Register every column on its own steepest gradient, then average.

    Returns (offsets_um, mean profile, n columns used, scatter about the fitted
    slant). Sub-sample position comes from a parabola through the three samples
    about the gradient peak, which is the standard estimator.

    Outliers are rejected about a FITTED LINE rather than about the median,
    because a slanted edge sweeps through many rows across the window by
    design; rejecting about the median would throw away the slant itself and
    the tool would only ever work on edges that are already horizontal. The
    residual about that line is the raggedness, and it is returned rather than
    hidden, because a large scatter means the subject offers more than one
    candidate edge.

    Columns contribute wherever they have data, and bins are kept when at least
    `min_frac` of the columns reach them. A common window bounded by the
    extreme columns would shrink to nothing on a steeply slanted edge.
    """
    n, m = band.shape
    k = np.ones(smooth) / smooth
    prof = np.empty_like(band, dtype=float)
    for j in range(m):
        prof[:, j] = np.convolve(band[:, j].astype(float), k, mode="same")
    g = np.abs(np.diff(prof, axis=0))
    pk = np.argmax(g[2:-2], axis=0) + 2
    pos = np.empty(m)
    for j in range(m):
        i = pk[j]
        a, b, c = g[i - 1, j], g[i, j], g[i + 1, j]
        den = a - 2 * b + c
        pos[j] = i + (0.5 * (a - c) / den if abs(den) > 1e-9 else 0.0)

    cols = np.arange(m, dtype=float)
    keep = np.ones(m, bool)
    coef = np.polyfit(cols, pos, 1)
    for _ in range(4):
        resid = pos - np.polyval(coef, cols)
        nk = np.abs(resid) <= tol_rows
        if nk.sum() < 24:
            break
        keep = nk
        coef = np.polyfit(cols[keep], pos[keep], 1)
    scatter = float(np.std(pos[keep] - np.polyval(coef, cols[keep])))
    if keep.sum() < 24:
        raise SystemExit(f"only {int(keep.sum())} columns agree on an edge "
                         f"(scatter {np.std(pos):.1f} rows)")

    half = int(min(n // 2, max(8, n // 2)))
    grid = np.arange(-half, half + 1, dtype=float)
    acc = np.zeros_like(grid)
    cnt = np.zeros_like(grid)
    idx = np.arange(n, dtype=float)
    for j in np.nonzero(keep)[0]:
        s = pos[j] + grid
        ok = (s >= 0.0) & (s <= n - 1.0)
        acc[ok] += np.interp(s[ok], idx, band[:, j].astype(float))
        cnt[ok] += 1.0
    good = cnt >= max(8.0, min_frac * keep.sum())
    if good.sum() < 12:
        raise SystemExit("too few well-populated bins; widen --band-half")
    return (grid[good] * 2.0 * L.PITCH_UM, acc[good] / cnt[good],
            int(keep.sum()), scatter)


def plateau_report(x_um, p, contrast):
    """Distance from the edge at which each side becomes flat, and by how much.

    `flat` is |dp/dx| / contrast in units of 1/um, so it is comparable across
    subjects and apertures regardless of exposure.
    """
    d = np.gradient(p, x_um)
    flat = np.abs(d) / max(contrast, 1e-9)
    rows = []
    for side, sel in (("bright", x_um < 0), ("dark", x_um > 0)):
        xs, fs = x_um[sel], flat[sel]
        order = np.argsort(np.abs(xs))
        xs, fs = xs[order], fs[order]
        reach = None
        for i in range(len(xs)):
            if np.all(fs[i:] < FLAT_FRAC_PER_UM):
                reach = abs(xs[i])
                break
        rows.append((side, reach, float(np.min(fs)), float(fs[-1])))
    return rows


def rise_1090(x_um, p, bright_first=True):
    hi = float(np.percentile(p, 98))
    lo = float(np.percentile(p, 2))
    span = hi - lo
    if span <= 0:
        return None, hi, lo
    q = p if bright_first else p[::-1]
    xx = x_um if bright_first else -x_um[::-1]

    def cross(frac):
        t = lo + frac * span
        for i in range(len(q) - 1):
            if q[i] >= t > q[i + 1]:
                u = (q[i] - t) / max(q[i] - q[i + 1], 1e-9)
                return float(xx[i] + u * (xx[i + 1] - xx[i]))
        return None

    a90, a10 = cross(0.9), cross(0.1)
    if a90 is None or a10 is None:
        return None, hi, lo
    return a10 - a90, hi, lo


def probe(path, which, orient, row0, nrow, col0, ncol, band_half, show, quiet,
          shape=0):
    active = L.load_active(path)
    sub, _xs, _ys = L.green_sites(active, which)
    if orient == "v":
        sub = np.ascontiguousarray(sub.T)
    roi = sub[row0:row0 + nrow, col0:col0 + ncol].astype(float)

    if shape:
        med = np.median(roi, axis=1)
        hi, lo = float(np.percentile(med, 99)), float(np.percentile(med, 1))
        print(f"\n{Path(path).parent.name} / {Path(path).name}  SHAPE of the "
              f"whole ROI, column median, no registration")
        print(f"  {roi.shape[0]} sublattice rows x {roi.shape[1]} columns, "
              f"{roi.shape[0] * 2 * L.PITCH_UM:.0f} um tall, "
              f"range {lo:.0f}..{hi:.0f} DN")
        print(f"  {'row':>5} {'um':>8} {'DN':>8}  profile")
        step = max(1, roi.shape[0] // shape)
        for i in range(0, roi.shape[0], step):
            frac = (med[i] - lo) / max(hi - lo, 1e-9)
            bar = "#" * int(round(56 * min(max(frac, 0.0), 1.0)))
            print(f"  {row0 + i:5d} {i * 2 * L.PITCH_UM:8.1f} {med[i]:8.1f}  {bar}")
        return dict(rise_um=None, hi=hi, lo=lo, contrast=hi - lo, plateau=[],
                    n_cols=roi.shape[1], scatter=0.0, grad_max=None,
                    grad_norm=None, edge_row=row0)

    med = np.median(roi, axis=1)
    kw = 9
    sm = np.convolve(med, np.ones(kw) / kw, mode="same")
    # `mode="same"` zero-pads, so the first and last kw/2 samples carry an
    # enormous artificial gradient. Searching the whole array finds that
    # artifact rather than the edge, and every downstream number is then a
    # measurement of the padding.
    g = np.abs(np.diff(sm))
    g[:kw] = 0.0
    g[-kw:] = 0.0
    row = int(np.argmax(g))
    b0 = max(row - band_half, 0)
    b1 = min(row + band_half, roi.shape[0])
    band = roi[b0:b1]
    if band.shape[0] < 2 * 6:
        raise SystemExit("band too small")

    x_um, p, used, scatter = column_shift_stack(band)
    bright_first = p[0] > p[-1]
    rise, hi, lo = rise_1090(x_um, p, bright_first)
    contrast = hi - lo
    rows = plateau_report(x_um, p, contrast)
    # Peak gradient is the sharpness metric that survives this subject. The
    # 10-90 rise needs two plateaus and there are none; the peak gradient needs
    # neither, and for a fixed subject imaged at fixed exposure it is monotone
    # in sharpness. It is quoted normalised by contrast so it can be compared
    # across apertures, where the exposure is constant but the brightness is not.
    grad = np.abs(np.gradient(p, x_um))
    gmax = float(np.max(grad))
    gnorm = gmax / max(contrast, 1e-9)

    if not quiet:
        print(f"\n{Path(path).parent.name} / {Path(path).name}  plane {which} "
              f"orient {orient}")
        print(f"  edge near row {row + row0}, band +/-{band_half} sublattice rows, "
              f"{used}/{roi.shape[1]} columns agree (scatter {scatter:.2f} rows), "
              f"{'bright first' if bright_first else 'dark first'}")
        print(f"  hi {hi:8.1f} DN   lo {lo:8.1f} DN   contrast {contrast:8.1f} DN")
        print(f"  10-90 rise {rise if rise is None else round(rise, 2)} um "
              f"(self-registered, so this is an OPTIMISTIC lower bound)")
        print(f"  peak gradient {gmax:8.2f} DN/um = {gnorm * 100:6.3f}%/um  "
              f"-> implied 10-90 rise if this were a clean edge: "
              f"{0.8 / max(gnorm, 1e-12):.1f} um")
        for side, reach, fmin, fend in rows:
            r = "never" if reach is None else f"{reach:.1f} um"
            print(f"  {side:>6} side flat at {r:>10}   best flatness "
                  f"{fmin * 100:7.4f}%/um   at window edge {fend * 100:7.4f}%/um")
        if show:
            print(f"\n  {'um':>8} {'DN':>9}  profile")
            step = max(1, len(x_um) // show)
            for i in range(0, len(x_um), step):
                frac = (p[i] - lo) / max(contrast, 1e-9)
                bar = "#" * int(round(48 * min(max(frac, 0.0), 1.0)))
                print(f"  {x_um[i]:8.1f} {p[i]:9.1f}  {bar}")
    return dict(rise_um=rise, hi=hi, lo=lo, contrast=contrast,
                plateau=rows, n_cols=used, scatter=scatter,
                grad_max=gmax, grad_norm=gnorm, edge_row=row + row0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--orient", default="h", choices=["h", "v"])
    ap.add_argument("--row0", type=int, default=0)
    ap.add_argument("--nrow", type=int, default=100000)
    ap.add_argument("--col0", type=int, default=0)
    ap.add_argument("--ncol", type=int, default=300)
    ap.add_argument("--band-half", type=int, default=40)
    ap.add_argument("--show", type=int, default=40,
                    help="print this many profile samples; 0 to suppress")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--shape", type=int, default=0,
                    help="print N samples of the unregistered ROI median")
    args = ap.parse_args()

    best = None
    for f in args.frames:
        try:
            r = probe(f, args.which, args.orient, args.row0, args.nrow,
                      args.col0, args.ncol, args.band_half, args.show,
                      args.quiet, args.shape)
        except SystemExit as e:
            print(f"  {Path(f).name}: {e}")
            continue
        if args.quiet:
            print(f"  {Path(f).name}  peak grad {r['grad_norm'] * 100:6.3f}%/um"
                  f"  -> equiv rise {0.8 / max(r['grad_norm'], 1e-12):7.1f} um"
                  f"  contrast {r['contrast']:7.1f} DN"
                  f"  scatter {r['scatter']:5.2f}")
        if r["grad_norm"] is not None and (best is None
                                           or r["grad_norm"] > best[0]):
            best = (r["grad_norm"], f)
    if best and len(args.frames) > 1:
        print(f"\nsharpest: {Path(best[1]).name}  peak grad "
              f"{best[0] * 100:.3f}%/um -> equiv rise {0.8 / best[0]:.1f} um")


if __name__ == "__main__":
    main()
