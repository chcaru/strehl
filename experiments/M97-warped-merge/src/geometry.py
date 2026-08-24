"""M97 geometry metrics on a rendered ruler.

Two ground-truthed invariants, chosen because they survive the reason M86c's
gradient-energy metric could not see this defect (M86 15.4): the defect is
geometric, so the metric is geometric.

S -- BASELINE STRAIGHTNESS.
    A straight line in the world projects to a straight line under *any*
    homography. So the fit has only 2 DOF and there is no freedom for a smooth
    misregistration to hide inside the model. It is also invariant to a uniform
    zoom about any centre, which matters here because `fit_to_cover` gives each
    arm a slightly different scale k -- so all arms are directly comparable on S
    without any scale normalisation.

G -- GRADUATION SPACING REGULARITY.
    Equal world spacing projects to spacing varying as a 3-DOF projective
    function of index. Residual about that exact ground-truth model is
    geometric error. Reported as a secondary, because a projective fit has more
    freedom than a line fit.

Both are reported raw and block-median-filtered. The engraving is pitted, and
that roughness is a per-column noise floor common to every arm; block medians
suppress it and leave the low-frequency bow that misregistration produces.

Usage: geometry.py <label> <render.tif> [--json out.json]
"""

import json
import sys

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import uniform_filter1d

Image.MAX_IMAGE_PIXELS = None

BLOCK = 64  # columns per block for the robust block-median edge
RUN = 24  # rows of sustained darkness that distinguish engraving from scratch
HALF_BAND = 150  # rows either side of the detected baseline centre


def read(path: str) -> np.ndarray:
    """Read a render at its true bit depth.

    NOT `PIL.Image.open`. Pillow reports `mode='RGB'` for a 16-bit RGB TIFF and
    hands back 8-bit data, silently, with no warning and no error. Measured on
    this render: Pillow max 255, tifffile max 65535 on the same file. Every
    number below would have been computed on 8-bit-quantised data.
    """
    return tifffile.imread(path)


def luma(path: str) -> np.ndarray:
    a = read(path)
    if a.ndim == 3:
        return a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def find_baseline_band(img: np.ndarray) -> tuple[int, int]:
    """Locate the thick horizontal engraved line.

    Detected as the row where the *fraction of columns that are dark* peaks.
    That is far more discriminative than row-mean darkness: the baseline runs
    the whole width, so nearly every column is dark on it, whereas a row
    crossing the graduations is dark in only a minority of columns and a row in
    the shadowed upper region is uniformly dim but not dark.

    An earlier version of this function used `np.convolve(..., "same")` on the
    row means. That zero-pads, so the smoothed sequence collapses at both ends
    and `argmin` reliably returned the first row of the search window. It
    reported a "baseline" 1900 px away from the real one. Fixed, and the
    detected band is asserted against the tick geometry by the caller.
    """
    lo, hi = int(0.15 * img.shape[0]), int(0.95 * img.shape[0])
    seg = img[lo:hi]
    # "Dark" relative to this render's own metal tone.
    bright = np.percentile(seg, 75)
    dark = np.percentile(seg, 2)
    thr = dark + 0.45 * (bright - dark)
    frac = (seg < thr).mean(axis=1)
    frac = uniform_filter1d(frac, size=25, mode="nearest")
    centre = lo + int(np.argmax(frac))
    return centre - HALF_BAND, centre + HALF_BAND


def subpixel_top_edge(img: np.ndarray, y0: int, y1: int) -> tuple[np.ndarray, np.ndarray]:
    """Sub-pixel y of the baseline's TOP edge, per column.

    Found as the entry into the first *sustained* dark run, refined by linear
    interpolation of the threshold crossing.

    An earlier version took the strongest negative vertical gradient. That
    failed, visibly, and the overlay is kept as evidence: the rule is brushed
    metal, and its horizontal brush scratches are thin but high-contrast, so
    they beat the baseline's own soft pitted edge on gradient magnitude. The
    tracker sat in the metal ~100 px above the true line and reported a 62.9 px
    RMS 'straightness'. Requiring the dark to *persist* for RUN rows is what
    separates a scratch from an engraving, because the scratches are a few
    pixels thick and the engraving is ~90.
    """
    band = img[y0:y1, :]
    h, w = band.shape
    bright = np.percentile(band, 80)
    dark = np.percentile(band, 3)
    thr = dark + 0.50 * (bright - dark)
    is_dark = band < thr
    # A run of RUN dark rows starting at r means is_dark[r:r+RUN] is all true.
    run_ok = uniform_filter1d(is_dark.astype(np.float32), size=RUN, axis=0, mode="constant") > 0.98
    # Shift so index r marks the START of the run rather than its centre.
    start_ok = np.zeros_like(run_ok)
    off = RUN // 2
    start_ok[: h - off] = run_ok[off:]

    ys = np.full(w, np.nan)
    strength = np.zeros(w)
    for x in range(w):
        idx = np.flatnonzero(start_ok[:, x])
        if idx.size == 0:
            continue
        s = int(idx[0])
        if s < 2:
            # The column is already dark at the top of the band: a tall
            # graduation, not the baseline. Left as NaN for the caller.
            continue
        a, b = float(band[s - 1, x]), float(band[s, x])
        if a <= b:
            ys[x] = s
        else:
            ys[x] = (s - 1) + (a - thr) / (a - b)
        strength[x] = a - b
    return ys + y0, strength


def reject_tall_ticks(img: np.ndarray, ys: np.ndarray, y0: int) -> np.ndarray:
    """Mask columns where a tall graduation rises ABOVE the baseline.

    Those columns have dark metal above the edge, which both moves the true
    edge and breaks the 'bright above' assumption. Detected as columns whose
    mean intensity well above the baseline is unusually dark.
    """
    w = len(ys)
    above = np.full(w, np.nan)
    for x in range(w):
        if np.isnan(ys[x]):
            continue
        top = int(ys[x]) - 160
        bot = int(ys[x]) - 40
        if top < 0:
            continue
        above[x] = img[top:bot, x].mean()
    med = np.nanmedian(above)
    mad = np.nanmedian(np.abs(above - med)) + 1e-9
    return (above > med - 4.0 * mad) & ~np.isnan(ys)


def straightness(img: np.ndarray) -> dict:
    y0, y1 = find_baseline_band(img)
    ys, strength = subpixel_top_edge(img, y0, y1)
    ok = reject_tall_ticks(img, ys, y0)
    ok &= strength > np.nanmedian(strength[ok]) * 0.25
    x = np.arange(len(ys), dtype=np.float64)

    # --- per-column straight-line fit, robust to the remaining outliers ---
    xs, yy = x[ok], ys[ok]
    keep = np.ones(len(xs), dtype=bool)
    for _ in range(5):
        c = np.polyfit(xs[keep], yy[keep], 1)
        r = yy - np.polyval(c, xs)
        s = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep]))) + 1e-9
        keep = np.abs(r - np.median(r[keep])) < 4.0 * s
    c = np.polyfit(xs[keep], yy[keep], 1)
    resid = yy[keep] - np.polyval(c, xs[keep])
    rms_raw = float(np.sqrt(np.mean(resid**2)))

    # --- block medians: suppress engraving roughness, keep the bow ---
    bx, by = [], []
    for start in range(0, len(ys), BLOCK):
        sl = slice(start, start + BLOCK)
        m = ok[sl]
        if m.sum() < BLOCK // 3:
            continue
        bx.append(x[sl][m].mean())
        by.append(np.median(ys[sl][m]))
    bx, by = np.asarray(bx), np.asarray(by)
    cb = np.polyfit(bx, by, 1)
    rb = by - np.polyval(cb, bx)
    rms_block = float(np.sqrt(np.mean(rb**2)))
    # The quadratic term is the bow itself: a scale error that varies across
    # the field displaces the line by an amount that varies with x.
    q = np.polyfit(bx, by, 2)
    bow = float(q[0] * (bx.max() - bx.min()) ** 2)

    return {
        "band": [int(y0), int(y1)],
        "columns_used": int(keep.sum()),
        "blocks": int(len(bx)),
        "S_rms_raw_px": rms_raw,
        "S_rms_block_px": rms_block,
        "S_bow_px": bow,
        "S_block_ptp_px": float(rb.max() - rb.min()),
    }


def spacing(img: np.ndarray) -> dict:
    """Graduation spacing regularity, from the strip just BELOW the baseline."""
    y0, y1 = find_baseline_band(img)
    ys, _ = subpixel_top_edge(img, y0, y1)
    base = float(np.nanmedian(ys))
    strip = img[int(base + 90) : int(base + 260), :]
    prof = strip.mean(axis=0)
    prof = np.convolve(prof, np.ones(5) / 5, mode="same")
    bright = np.percentile(prof, 90)
    depth = bright - prof
    thr = 0.35 * depth.max()
    # Contiguous runs below threshold are ticks.
    on = depth > thr
    edges = np.diff(on.astype(int))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0] + 1)
    if on[0]:
        starts.insert(0, 0)
    if on[-1]:
        ends.append(len(on))
    cents = []
    for a, b in zip(starts, ends):
        if b - a < 6:
            continue
        wgt = depth[a:b]
        cents.append(float((wgt * np.arange(a, b)).sum() / wgt.sum()))
    cents = np.asarray(cents)
    if len(cents) < 12:
        return {"G_ticks": int(len(cents)), "G_rms_px": float("nan")}

    i = np.arange(len(cents), dtype=np.float64)
    # Exact ground-truth model: equal world spacing under a homography maps to
    # a 3-DOF projective function of index.
    def proj_resid(p):
        a, b, c = p
        return cents - (a * i + b) / (c * i + 1.0)

    from scipy.optimize import least_squares

    p0 = [float(np.polyfit(i, cents, 1)[0]), float(cents[0]), 0.0]
    sol = least_squares(proj_resid, p0, method="lm", max_nfev=20000)
    r = proj_resid(sol.x)
    d = np.diff(cents)
    return {
        "G_ticks": int(len(cents)),
        "G_median_spacing_px": float(np.median(d)),
        "G_rms_px": float(np.sqrt(np.mean(r**2))),
        "G_rms_frac_of_spacing": float(np.sqrt(np.mean(r**2)) / np.median(d)),
    }


def main() -> None:
    label, path = sys.argv[1], sys.argv[2]
    img = luma(path)
    out = {"label": label, "path": path, "shape": list(img.shape)}
    out.update(straightness(img))
    out.update(spacing(img))
    print(json.dumps(out, indent=2))
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)


if __name__ == "__main__":
    main()
