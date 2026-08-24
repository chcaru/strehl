"""M97 -- tick straightness and tick spacing on the angled ruler render.

WHY THIS TARGET. M86 15.4 named the straightness of a physically straight edge
as the test that would settle whether alignment improves the render. This stack
is a millimetre ruler at a steep angle to the optical axis. Two properties are
known a priori and owe nothing to any metric this project invented:

  S -- each engraved graduation is STRAIGHT. A straight world line projects to
       a straight image line under any homography, so the model has 2 DOF and a
       smooth misregistration has nowhere to hide inside it. It is also
       invariant to the uniform zoom that differs between arms.
  G -- the graduations are EQUALLY SPACED in the world. Equal world spacing
       projects to spacing that is an exact 3-DOF projective function of index.

Why ticks rather than the ruler's outer edge: there are ~25 of them, so the
result is a distribution over independent straight lines rather than one
number; they are high-contrast; and because the ruler is steeply tilted they
span a large depth range, so adjacent parts of one tick are elected from very
different frames. That is exactly the condition under which inter-frame
misregistration becomes a visible kink in a line that must be straight.

WHAT IS NOT CLAIMED. The ruler's own manufacturing straightness and the lens's
distortion both enter the absolute residual. Neither differs between arms, so
only the PAIRED DIFFERENCE is quoted as registration error. The occlusion halo
(fact 1236) runs along every tick in BOTH arms for the same reason.

Usage:
  angstraight.py measure <label> <render.tif> [--json out.json] [--overlay p.png]
  angstraight.py plant   <render.tif> --bend PX   [--json out.json]
"""

import argparse
import json
import sys

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.optimize import least_squares

Image.MAX_IMAGE_PIXELS = None

# Region of the render in which the graduations are unambiguous, read off the
# 1/8 thumbnail: below the engraved baseline everywhere, above the bottom crop,
# and inside the ruler's two long edges. Deliberately generous in x; columns
# with no tick simply yield no detection.
ROI_Y0, ROI_Y1 = 3000, 4600
ROI_X0, ROI_X1 = 3250, 4900

HALF_WIN = 33  # +/- px searched around a tick's centre; AUTO-SIZED from pitch
BG_MED = 301  # px of running median used as the bright background; AUTO-SIZED
PROBE_MED = 401  # first-pass background width, used only to measure the pitch
MIN_ROWS = 900  # a tick must be trackable over at least this many rows
BLOCK = 64  # rows per block for the step statistic

# Both window constants were first set by hand to 9 and 61, sized for a thin
# scribed line, and both were wrong. angprobe.py MEASURED the angled ruler's
# graduations: 30 px wide at half depth, 101 px pitch, duty cycle 0.297.
# Consequences of the first sizing, and why the bend plant caught them:
#   * a 19 px window is NARROWER than a 30 px tick, so the depth-weighted
#     centroid was pinned by where the window fell rather than by where the
#     tick was. The tracker recovered only 18% of a planted 2.0 px bend.
#   * a 61 px median centred inside a 30 px tick is 49% dark, so the "bright
#     background" was itself dragged dark: measured depth p99 7534 at 61 px
#     against 10383 at 301 px, a third of the contrast thrown away.
# They are now DERIVED from the measured pitch rather than typed in, because
# the flat-on ruler has a 4x larger pitch and hand-tuning a second set of
# constants would be the same defect a second time. `autosize` reproduces the
# hand-tuned angled values to within a pixel.


def autosize(pitch: float) -> tuple[int, int]:
    """Window and background widths derived from the measured tick pitch.

    HALF_WIN spans the tick plus a bright margin either side and must stay well
    inside half a pitch or the window swallows the neighbouring tick; 0.33 of
    the pitch does both at the duty cycles this target has.
    BG_MED spans three pitches, so a running median is taken over at least two
    whole ticks plus their gaps and stays bright wherever it is centred for any
    duty cycle below 1/2.
    """
    hw = max(int(round(0.33 * pitch)), 6)
    bg = int(round(3.0 * pitch)) | 1
    return hw, bg


def read_luma(path: str) -> np.ndarray:
    """Read at true bit depth. Pillow silently 8-bits a 16-bit TIFF."""
    a = tifffile.imread(path)
    if a.ndim == 3:
        return a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def deshade(roi: np.ndarray) -> np.ndarray:
    """Depth below a local bright background, per row.

    The ruler face is unevenly lit and the tilt makes it darker with depth, so
    a global threshold would find ticks at one end of the frame and nothing at
    the other. A running median along x is a background that follows the
    shading but steps over a tick, because a tick is far narrower than BG_MED.
    """
    bg = median_filter(roi, size=(1, BG_MED), mode="nearest")
    return np.maximum(bg - roi, 0.0)


def find_shear(depth: np.ndarray) -> float:
    """Slope dx/dy of the graduations, by a Radon-style search.

    Summing rows straight down smears the comb if the ticks lean; summing along
    their true direction sharpens it. The correct slope is the one that
    maximises the variance of the collapsed profile.
    """
    h = depth.shape[0]
    y = np.arange(h) - h / 2.0
    best, best_s = -1.0, 0.0
    for s in np.arange(-0.40, 0.401, 0.005):
        shifted = np.empty_like(depth)
        for i in range(h):
            shifted[i] = np.roll(depth[i], -int(round(s * y[i])))
        v = float(shifted.mean(axis=0).var())
        if v > best:
            best, best_s = v, float(s)
    return best_s


def collapse(depth: np.ndarray, shear: float) -> np.ndarray:
    h = depth.shape[0]
    y = np.arange(h) - h / 2.0
    acc = np.zeros(depth.shape[1])
    for i in range(h):
        acc += np.roll(depth[i], -int(round(shear * y[i])))
    return acc / h


def comb_peaks(prof: np.ndarray) -> np.ndarray:
    """Tick centres in the collapsed profile, as run centroids."""
    sm = uniform_filter1d(prof, size=5, mode="nearest")
    thr = 0.30 * float(sm.max())
    on = sm > thr
    starts = list(np.flatnonzero(np.diff(on.astype(int)) == 1) + 1)
    ends = list(np.flatnonzero(np.diff(on.astype(int)) == -1) + 1)
    if on[0]:
        starts.insert(0, 0)
    if on[-1]:
        ends.append(len(on))
    cents = []
    for a, b in zip(starts, ends):
        if b - a < 5:
            continue
        w = sm[a:b]
        cents.append(float((w * np.arange(a, b)).sum() / w.sum()))
    return np.asarray(cents)


def track(depth: np.ndarray, x0: float, shear: float) -> np.ndarray:
    """Sub-pixel x of one tick's centre, per row. NaN where it is not found.

    The centre is the depth-weighted centroid inside a narrow window that
    follows the shear model. A centroid, not an argmin: the engraving is pitted
    and the argmin hops between pits, which manufactures residual that has
    nothing to do with registration.
    """
    h, w = depth.shape
    y = np.arange(h) - h / 2.0
    xs = np.full(h, np.nan)
    peak = np.full(h, 0.0)
    for i in range(h):
        c = x0 + shear * y[i]
        a, b = int(round(c)) - HALF_WIN, int(round(c)) + HALF_WIN + 1
        if a < 0 or b > w:
            continue
        seg = depth[i, a:b]
        tot = float(seg.sum())
        if tot <= 0:
            continue
        xs[i] = a + float((seg * np.arange(len(seg))).sum() / tot)
        peak[i] = float(seg.max())

    # The ruler does not fill the ROI: its bottom-right corner gives way to
    # bright out-of-focus foam, and the first overlay showed the tracker
    # happily following texture there for the four rightmost ticks. A tick is
    # only present on a row if that row's window actually contains an
    # engraving-strength darkening, so gate on the tick's OWN typical depth
    # rather than on a frame-wide threshold.
    live = peak > 0
    if live.sum() < MIN_ROWS:
        return np.full(h, np.nan)
    xs[peak < 0.40 * float(np.median(peak[live]))] = np.nan
    return xs


def robust_line(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    keep = np.ones(len(y), dtype=bool)
    c = np.polyfit(y, x, 1)
    for _ in range(6):
        r = x - np.polyval(c, y)
        m = np.median(r[keep])
        s = 1.4826 * np.median(np.abs(r[keep] - m)) + 1e-9
        keep = np.abs(r - m) < 4.0 * s
        if keep.sum() < 50:
            break
        c = np.polyfit(y[keep], x[keep], 1)
    return c, keep


def step_stat(y: np.ndarray, r: np.ndarray) -> float:
    """Largest jump between adjacent block medians of the residual.

    A global similarity maps a straight line to a straight line, so it cannot
    bend a tick at all. Any bend in the render must come from the per-pixel
    election of DIFFERENT frames along the tick, which produces a piecewise
    displacement -- a step, not a bow. This statistic is chosen to be sensitive
    to that specific shape.
    """
    if len(y) < 3 * BLOCK:
        return float("nan")
    order = np.argsort(y)
    y, r = y[order], r[order]
    meds = []
    for s in range(0, len(y) - BLOCK + 1, BLOCK):
        meds.append(np.median(r[s : s + BLOCK]))
    meds = np.asarray(meds)
    return float(np.abs(np.diff(meds)).max()) if len(meds) > 1 else float("nan")


def measure(img: np.ndarray) -> dict:
    global HALF_WIN, BG_MED
    roi = img[ROI_Y0:ROI_Y1, ROI_X0:ROI_X1]

    # Pass 1: a generous fixed background just to MEASURE the pitch.
    BG_MED = PROBE_MED
    depth = deshade(roi)
    shear = find_shear(depth)
    peaks0 = comb_peaks(collapse(depth, shear))
    if len(peaks0) < 4:
        return {"n_ticks": 0, "reason": "fewer than 4 graduations found in pass 1"}
    pitch0 = float(np.median(np.diff(peaks0)))

    # Pass 2: re-derive both windows from that pitch and redo everything.
    HALF_WIN, BG_MED = autosize(pitch0)
    depth = deshade(roi)
    shear = find_shear(depth)
    prof = collapse(depth, shear)
    peaks = comb_peaks(prof)

    ticks, rmss, steps, slopes, rows = [], [], [], [], []
    mids = []
    all_resid = []
    ymid = (ROI_Y1 - ROI_Y0) / 2.0
    for p in peaks:
        xs = track(depth, float(p), shear)
        ok = ~np.isnan(xs)
        if ok.sum() < MIN_ROWS:
            continue
        yy = np.flatnonzero(ok).astype(np.float64)
        xx = xs[ok]
        c, keep = robust_line(yy, xx)
        if keep.sum() < MIN_ROWS // 2:
            continue
        r = xx[keep] - np.polyval(c, yy[keep])
        ticks.append(float(p) + ROI_X0)
        rmss.append(float(np.sqrt(np.mean(r**2))))
        steps.append(step_stat(yy[keep], r))
        slopes.append(float(c[0]))
        rows.append(int(keep.sum()))
        mids.append(float(np.polyval(c, ymid)) + ROI_X0)
        all_resid.append(r)

    if not ticks:
        return {"n_ticks": 0}

    allr = np.concatenate(all_resid)
    rmss = np.asarray(rmss)
    steps = np.asarray(steps, dtype=np.float64)

    # --- G: equal world spacing is an exact projective function of index ---
    t = np.asarray(ticks)
    i = np.arange(len(t), dtype=np.float64)
    g = {"G_ticks": int(len(t))}
    if len(t) >= 8:
        def resid(p):
            a, b, cc = p
            return t - (a * i + b) / (cc * i + 1.0)

        p0 = [float(np.polyfit(i, t, 1)[0]), float(t[0]), 0.0]
        sol = least_squares(resid, p0, method="lm", max_nfev=20000)
        rg = resid(sol.x)
        d = np.diff(t)
        g.update(
            {
                "G_median_spacing_px": float(np.median(d)),
                "G_rms_px": float(np.sqrt(np.mean(rg**2))),
                "G_rms_frac": float(np.sqrt(np.mean(rg**2)) / np.median(d)),
                "G_spacing_first": float(d[: max(len(d) // 4, 1)].mean()),
                "G_spacing_last": float(d[-max(len(d) // 4, 1) :].mean()),
            }
        )

    return {
        "n_ticks": len(ticks),
        "shear": shear,
        "pitch_probe_px": pitch0,
        "half_win": HALF_WIN,
        "bg_med": BG_MED,
        "tick_x": [float(v) for v in ticks],
        "fit_mid_x": mids,
        "rows_per_tick": rows,
        "rows_total": int(sum(rows)),
        "S_rms_median_px": float(np.median(rmss)),
        "S_rms_mean_px": float(rmss.mean()),
        "S_rms_p90_px": float(np.percentile(rmss, 90)),
        "S_rms_per_tick": [float(v) for v in rmss],
        "S_resid_p50_abs": float(np.percentile(np.abs(allr), 50)),
        "S_resid_p90_abs": float(np.percentile(np.abs(allr), 90)),
        "S_resid_p99_abs": float(np.percentile(np.abs(allr), 99)),
        "S_resid_max_abs": float(np.abs(allr).max()),
        "S_resid_n": int(len(allr)),
        "S2_step_median_px": float(np.nanmedian(steps)),
        "S2_step_p90_px": float(np.nanpercentile(steps, 90)),
        "slope_median": float(np.median(slopes)),
        **g,
    }


def bend(img: np.ndarray, amp: float) -> np.ndarray:
    """Plant a known bend: displace x by amp*sin(pi*(y-y0)/(y1-y0)).

    Applied to the WHOLE image so the instrument's ROI logic is exercised
    unchanged, which is the point of a plant.

    NOTE ON THE EXPECTED RESIDUAL. A half-sine is mostly DC: its mean over the
    support is 2/pi of its amplitude, and a straight-line fit's intercept
    absorbs that mean entirely and legitimately. So the residual RMS this plant
    can possibly produce is NOT amp/sqrt(2) but amp*sqrt(1/2 - 4/pi^2) =
    0.3078*amp -- and less again over the sub-range of rows a given tick is
    actually tracked on. Comparing the measured rise against amp/sqrt(2) makes
    an honest instrument look 44% blind. `expected_bend_rms` below computes the
    correct expectation over the exact rows used instead of assuming one.
    """
    h, w = img.shape
    y = np.arange(h, dtype=np.float64)
    dx = amp * np.sin(np.pi * np.clip((y - ROI_Y0) / (ROI_Y1 - ROI_Y0), 0, 1))
    out = np.empty_like(img)
    xi = np.arange(w, dtype=np.float64)
    for r in range(h):
        out[r] = np.interp(xi + dx[r], xi, img[r])
    return out


def shift(img: np.ndarray, px: float) -> np.ndarray:
    """Plant a pure sub-pixel translation in x.

    The unambiguous test of whether the tracker can see a displacement at all.
    A translation is absorbed *entirely* by the line fit's intercept, so it
    leaves the residual untouched -- which is exactly why it is the right
    probe: the response appears in the fitted tick POSITIONS, where the
    expected gain is exactly 1.0 with no orthogonality argument required.
    """
    h, w = img.shape
    out = np.empty_like(img)
    xi = np.arange(w, dtype=np.float64)
    for r in range(h):
        out[r] = np.interp(xi + px, xi, img[r])
    return out


def expected_bend_rms(amp: float, rows_per_tick: list[int]) -> float:
    """RMS the planted bend can leave AFTER a straight-line fit.

    Computed over a contiguous row block of the same length as each tick's
    tracked run, centred in the ROI, then averaged over ticks. This is an
    approximation in the placement of each run, and is reported as such.
    """
    n = ROI_Y1 - ROI_Y0
    y = np.arange(n, dtype=np.float64)
    d = amp * np.sin(np.pi * y / n)
    vals = []
    for k in rows_per_tick:
        k = min(int(k), n)
        s = (n - k) // 2
        yy, dd = y[s : s + k], d[s : s + k]
        c = np.polyfit(yy, dd, 1)
        vals.append(float(np.sqrt(np.mean((dd - np.polyval(c, yy)) ** 2))))
    return float(np.mean(vals)) if vals else float("nan")


def overlay(img: np.ndarray, res: dict, path: str) -> None:
    """Draw the tracked centre only on the rows the gate actually accepted.

    Drawing the whole search corridor would hide exactly the failure the first
    overlay revealed -- a tick "tracked" across bright foam where no tick
    exists. The overlay must show what was measured, not what was searched.
    """
    roi = img[ROI_Y0:ROI_Y1, ROI_X0:ROI_X1]
    depth = deshade(roi)
    lo, hi = np.percentile(roi, 1), np.percentile(roi, 99)
    v = np.clip((roi - lo) / max(hi - lo, 1e-9), 0, 1)
    rgb = np.repeat((v * 255).astype(np.uint8)[:, :, None], 3, axis=2)
    for tx in res.get("tick_x", []):
        xs = track(depth, tx - ROI_X0, res["shear"])
        for i, xv in enumerate(xs):
            if np.isnan(xv):
                continue
            xx = int(round(xv))
            if 0 <= xx < rgb.shape[1]:
                rgb[i, xx] = (255, 40, 40)
    Image.fromarray(rgb).save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["measure", "plant"])
    ap.add_argument("a")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--bend", type=float, default=0.0)
    ap.add_argument("--shift", type=float, default=0.0)
    ap.add_argument("--roi", help="x0,y0,x1,y1 -- overrides the angled-ruler default")
    ap.add_argument("--json")
    ap.add_argument("--overlay")
    args = ap.parse_args()

    if args.roi:
        global ROI_X0, ROI_Y0, ROI_X1, ROI_Y1
        ROI_X0, ROI_Y0, ROI_X1, ROI_Y1 = (int(v) for v in args.roi.split(","))

    if args.mode == "measure":
        label, path = args.a, args.b
        img = read_luma(path)
    elif args.shift:
        label, path = f"shift{args.shift}", args.a
        img = shift(read_luma(path), args.shift)
    else:
        label, path = f"bend{args.bend}", args.a
        img = bend(read_luma(path), args.bend)

    res = measure(img)
    res["label"] = label
    res["path"] = path
    res["roi"] = [ROI_X0, ROI_Y0, ROI_X1, ROI_Y1]
    if args.mode == "plant" and args.bend:
        res["planted_bend_px"] = args.bend
        res["expected_added_rms_px"] = expected_bend_rms(
            args.bend, res.get("rows_per_tick", [])
        )
    if args.mode == "plant" and args.shift:
        res["planted_shift_px"] = args.shift
    if args.overlay and res.get("n_ticks"):
        overlay(img, res, args.overlay)
    keys = [
        "n_ticks", "rows_total", "shear", "pitch_probe_px", "half_win", "bg_med",
        "S_rms_median_px", "S_rms_p90_px",
        "S_resid_p50_abs", "S_resid_p90_abs", "S_resid_p99_abs",
        "S2_step_median_px", "S2_step_p90_px",
        "G_ticks", "G_median_spacing_px", "G_rms_px", "G_rms_frac",
        "G_spacing_first", "G_spacing_last",
        "planted_bend_px", "expected_added_rms_px", "planted_shift_px",
    ]
    print(f"--- {label} ---")
    for k in keys:
        if k in res:
            val = res[k]
            print(f"  {k:24s} {val:.4f}" if isinstance(val, float) else f"  {k:24s} {val}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
