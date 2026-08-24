"""M88b — paired merge-sharpness instrument.

Measures whether one merge is sharper than another, on the SAME stack, by the
ESF 10-90% rise distance in micrometres.

WHY THIS IS NOT A FIFTH METRIC HUNT.  The four dead hunts (facts 468, 476,
612-613, 617/708, 809) all tried to order ARBITRARY images by ABSOLUTE
sharpness with no ground truth.  This does something different: it measures a
DIFFERENCE in one physical quantity between two merges that share subject,
optics, frames, sensor, session and gate.  M88's own negative result was that
`rise^2 = d^2 + c^2` is unidentifiable because the subject term `c` is three
times the diffraction term `d` and cannot be separated.  In a paired
comparison on one stack, `c` is held fixed by construction and cancels:

    rise_off^2 - rise_on^2 = a_off^2 - a_on^2

with `a` the merge-induced blur.  The confound that defeated M88 is the thing
this design controls.

WHY FACT 617's PROOF DOES NOT REACH IT.  Ring FRC is `C/(C+U)`; a linear
post-filter scales `C` and `U` by the same `|H|^2` so the ratio cannot move.
That proof is about a RATIO OF POWERS.  The 10-90 rise distance is a distance
on the edge-spread function, and a low-pass strictly widens it.  The statistic
is maximally sensitive to exactly the transformation FRC is blind to.  This is
asserted here and MEASURED in b02_graveyard.py, which runs both statistics on
the same planted post-filter.

Everything in M88's frozen instrument (`m88lib.py`) is reused UNCHANGED.  This
module adds only a merge-TIFF adapter and the paired statistic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_M88_SRC = Path(__file__).resolve().parents[2] / "M88-optical-ceiling" / "src"
if str(_M88_SRC) not in sys.path:
    sys.path.insert(0, str(_M88_SRC))

import m88lib as L  # noqa: E402

# The merge writes one output pixel per 2x2 sensor quad, so the output grid
# has exactly the pitch of one Bayer sublattice: 2 * 5.12 = 10.24 um.  That is
# the geometry M88's instrument was validated on, which is why it transfers
# without retuning.
MERGE_PITCH_UM = 2.0 * L.PITCH_UM
MERGE_PLANE_NYQUIST_CYMM = 1.0e3 / (2.0 * MERGE_PITCH_UM)   # 48.828125

# Frozen instrument settings, taken verbatim from M88's s12_closing.py, which
# is the configuration validated at +1.19% +/- 1.50% on planted 60-140 cy/mm
# cutoffs and shown model-free to reach 114.6 cy/mm from this same pitch.
BIN_UM = 0.64
TAPER = 0.10
CORE_UM = 24.0
HALF_WIDTH_UM = 96.0


def read_merge_plane(path, channel="G"):
    """Read a strehl merge TIFF and return one linear plane as float64.

    The merge output is 16-bit RGB, LINEAR, binned from one quad per pixel.
    No demosaicing is involved at any point: R, G and B are each already one
    real sensor measurement per output pixel (G being the mean of the quad's
    two green sites), so trap 2 of the M88 dispatch does not arise here.
    """
    import tifffile

    arr = tifffile.imread(str(path))
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(f"expected an HxWx3 TIFF, got {arr.shape}")
    idx = {"R": 0, "G": 1, "B": 2}[channel]
    return np.asarray(arr[:, :, idx], dtype=np.float64)


def merge_sites(plane, r0, c0, h, w):
    """Extract a patch and give it SENSOR pixel coordinates.

    m88lib works in sensor pixels and converts to micrometres with PITCH_UM,
    so mapping merge column j to sensor x = 2j and merge row i to sensor
    y = 2i reproduces the true 10.24 um site spacing and lets every downstream
    function be reused with no change and no rescaling.
    """
    sub = plane[r0:r0 + h, c0:c0 + w]
    xs = 2.0 * (c0 + np.arange(w, dtype=np.float64))
    ys = 2.0 * (r0 + np.arange(h, dtype=np.float64))
    return sub, xs, ys


def rise_1090(centres, esf):
    """Model-free 10-90 percent rise distance, in micrometres.

    Byte-for-byte the definition used in M88's s12_closing.py.  No fit, no
    model, no sigma/f_c trade -- which matters because M88 measured that the
    two-parameter fit pins its amplitude at a bound on 6 of 11 real ROIs.
    """
    e = np.asarray(esf, float)
    c = np.asarray(centres, float)
    k = max(3, len(e) // 40)
    lo = np.median(e[:k])
    hi = np.median(e[-k:])
    if hi < lo:
        e, lo, hi = -e, -lo, -hi
    span = hi - lo
    if span <= 0:
        return np.nan
    t10, t90 = lo + 0.1 * span, lo + 0.9 * span
    em = np.maximum.accumulate(e)
    x10 = np.interp(t10, em, c)
    x90 = np.interp(t90, em, c)
    return float(x90 - x10)


def measure_roi(plane, roi, axis, half_width_um=HALF_WIDTH_UM, line=None):
    """Fit the edge inside one ROI of a merge plane and measure its rise.

    `line=None` refits the edge in this arm.  THIS IS DELIBERATE AND IS THE
    LESSON OF M88's OWN BAR 3: alignment moves the image, so a fixed pixel
    window is not a fixed EDGE.  M88 compared two stacks at identical window
    coordinates and found afterwards that their edges differed by 2.15 degrees
    and 1.91x in contrast.  Refitting per arm makes the comparison follow the
    edge rather than the coordinates.  Pass an explicit `line` only to hold
    geometry fixed on purpose, as the nuisance controls do.
    """
    r0, c0, h, w = roi
    sub, xs, ys = merge_sites(plane, r0, c0, h, w)
    if line is None:
        line = L.fit_edge_line(sub, xs, ys, axis=axis)
    xx, yy = np.meshgrid(xs, ys)
    res = L.sfr_from_sites2(sub.ravel(), xx.ravel(), yy.ravel(), line,
                            BIN_UM, half_width_um, TAPER, core_um=CORE_UM)
    return {
        "rise_um": rise_1090(res["centres_um"], res["esf"]),
        "angle_deg": float(line["angle_deg"]),
        "contrast": float(line["contrast"]),
        "resid_sd_px": float(line["resid_sd_px"]),
        "n_empty_bins": int(np.sum(res["count"] == 0)),
        "line": line,
        "centres_um": res["centres_um"],
        "esf": res["esf"],
    }


def rise_bootstrap(plane, roi, axis, n_boot=64, seed=0,
                   half_width_um=HALF_WIDTH_UM):
    """Uncertainty on one ROI's rise, by resampling strips along the edge.

    Resamples rows (for a vertical edge) with replacement.  This captures the
    finite along-edge sample and the noise together without assuming a noise
    model, which matters because M88 measured the real per-bin scatter at
    3.5-4.2x photon-only -- a photon-model error bar would be far too small.
    """
    r0, c0, h, w = roi
    sub, xs, ys = merge_sites(plane, r0, c0, h, w)
    line = L.fit_edge_line(sub, xs, ys, axis=axis)
    xx, yy = np.meshgrid(xs, ys)
    rng = np.random.default_rng(seed)
    n_along = h if axis == "vertical" else w
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, n_along, n_along)
        if axis == "vertical":
            v, X, Y = sub[pick, :], xx[pick, :], yy[pick, :]
        else:
            v, X, Y = sub[:, pick], xx[:, pick], yy[:, pick]
        res = L.sfr_from_sites2(v.ravel(), X.ravel(), Y.ravel(), line,
                                BIN_UM, half_width_um, TAPER, core_um=CORE_UM)
        vals.append(rise_1090(res["centres_um"], res["esf"]))
    vals = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
    return float(np.std(vals, ddof=1)), vals


def estimate_shift(a, b, max_shift=64):
    """Integer (dy, dx) that best aligns b onto a, by phase correlation.

    Used to make the paired comparison follow the EDGE rather than the window
    coordinates.  M88's Bar 3 failed precisely because it compared two images
    at identical window coordinates without checking that the same edge was in
    both windows; measured here, an uncorrected 3 px displacement produces a
    spurious 5.7 um difference, 8.5x the instrument floor.

    Deliberately returns an INTEGER shift.  Applying a sub-pixel correction
    would resample the ON arm and add interpolation blur to the very quantity
    being measured; the residual sub-pixel offset is instead absorbed by
    refitting the edge separately in each arm.
    """
    a = np.asarray(a, float) - float(np.mean(a))
    b = np.asarray(b, float) - float(np.mean(b))
    A = np.fft.rfft2(a)
    Bf = np.fft.rfft2(b)
    cross = A * np.conj(Bf)
    mag = np.abs(cross)
    cc = np.fft.irfft2(cross / np.maximum(mag, 1e-12), s=a.shape)
    h, w = a.shape
    idx = int(np.argmax(cc))
    dy, dx = divmod(idx, w)
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w
    if abs(dy) > max_shift or abs(dx) > max_shift:
        return 0, 0
    return int(dy), int(dx)


def paired_delta_registered(plane_off, plane_on, roi, axis,
                            half_width_um=HALF_WIDTH_UM, pad=64):
    """Paired delta with the ON window re-located onto the same physical edge.

    Estimates the offset on a padded neighbourhood of the ROI, moves the ON
    window by the integer part, and only then measures.  Returns the applied
    shift so the correction is auditable rather than invisible.
    """
    r0, c0, h, w = roi
    H, W = plane_off.shape
    pr0, pc0 = max(0, r0 - pad), max(0, c0 - pad)
    pr1, pc1 = min(H, r0 + h + pad), min(W, c0 + w + pad)
    dy, dx = estimate_shift(plane_off[pr0:pr1, pc0:pc1],
                            plane_on[pr0:pr1, pc0:pc1])
    r0b, c0b = r0 - dy, c0 - dx
    if not (0 <= r0b and r0b + h <= H and 0 <= c0b and c0b + w <= W):
        dy = dx = 0
        r0b, c0b = r0, c0
    out = paired_delta_at(plane_off, plane_on, roi, (r0b, c0b, h, w), axis,
                          half_width_um)
    out["shift_dy"] = dy
    out["shift_dx"] = dx
    return out


def paired_delta_at(plane_off, plane_on, roi_off, roi_on, axis,
                    half_width_um=HALF_WIDTH_UM):
    """Paired delta measuring each arm in its own, explicitly given window."""
    try:
        off = measure_roi(plane_off, roi_off, axis, half_width_um)
        on = measure_roi(plane_on, roi_on, axis, half_width_um)
    except Exception as exc:
        return {"rise_off_um": float("nan"), "rise_on_um": float("nan"),
                "delta_um": float("nan"), "error": repr(exc)}
    d = off["rise_um"] - on["rise_um"]
    quad = off["rise_um"] ** 2 - on["rise_um"] ** 2
    return {
        "rise_off_um": off["rise_um"],
        "rise_on_um": on["rise_um"],
        "delta_um": float(d),
        "delta_frac": float(d / off["rise_um"]) if off["rise_um"] else np.nan,
        "excess_blur_um": float(np.sqrt(quad)) if quad > 0 else float("nan"),
        "angle_off_deg": off["angle_deg"],
        "angle_on_deg": on["angle_deg"],
        "contrast_off": off["contrast"],
        "contrast_on": on["contrast"],
        "error": None,
    }


def paired_delta(plane_off, plane_on, roi, axis,
                 half_width_um=HALF_WIDTH_UM):
    """The statistic: how much narrower is the ON edge than the OFF edge?

    Returns both forms.  `delta_um` is the plain difference of rise.
    `a_off/a_on` decompose it under rise^2 = (shared)^2 + a^2 by taking the
    ON arm as the reference, which is only meaningful when ON is the sharper.

    A failure to fit either arm is reported as NaN with an `error` field
    rather than raised.  The instrument must be able to say "this ROI is not
    measurable under this perturbation" -- that is a result about the ROI, and
    silently crashing on it would let a fragile ROI go unnoticed.
    """
    try:
        off = measure_roi(plane_off, roi, axis, half_width_um)
        on = measure_roi(plane_on, roi, axis, half_width_um)
    except Exception as exc:
        return {"rise_off_um": float("nan"), "rise_on_um": float("nan"),
                "delta_um": float("nan"), "delta_frac": float("nan"),
                "excess_blur_um": float("nan"), "error": repr(exc)}
    d = off["rise_um"] - on["rise_um"]
    quad = off["rise_um"] ** 2 - on["rise_um"] ** 2
    return {
        "rise_off_um": off["rise_um"],
        "rise_on_um": on["rise_um"],
        "delta_um": float(d),
        "delta_frac": float(d / off["rise_um"]) if off["rise_um"] else np.nan,
        "excess_blur_um": float(np.sqrt(quad)) if quad > 0 else float("nan"),
        "angle_off_deg": off["angle_deg"],
        "angle_on_deg": on["angle_deg"],
        "contrast_off": off["contrast"],
        "contrast_on": on["contrast"],
        "n_empty_off": off["n_empty_bins"],
        "n_empty_on": on["n_empty_bins"],
        "error": None,
    }


def ring_frc(a, b, n_rings=32):
    """Split-half ring FRC, the statistic facts 617/708 proved blind.

    Implemented here only so the blindness can be demonstrated rather than
    cited.  Returns (freq_cyc_per_px, frc).
    """
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a - a.mean()
    b = b - b.mean()
    n = min(a.shape)
    a, b = a[:n, :n], b[:n, :n]
    win = np.outer(np.hanning(n), np.hanning(n))
    A = np.fft.fftshift(np.fft.fft2(a * win))
    B = np.fft.fftshift(np.fft.fft2(b * win))
    fy, fx = np.meshgrid(np.fft.fftshift(np.fft.fftfreq(n)),
                         np.fft.fftshift(np.fft.fftfreq(n)), indexing="ij")
    r = np.sqrt(fx ** 2 + fy ** 2)
    edges = np.linspace(0.0, 0.5, n_rings + 1)
    idx = np.clip(np.digitize(r.ravel(), edges) - 1, 0, n_rings - 1)
    num = np.bincount(idx, weights=np.real(A * np.conj(B)).ravel(),
                      minlength=n_rings)
    da = np.bincount(idx, weights=(np.abs(A) ** 2).ravel(), minlength=n_rings)
    db = np.bincount(idx, weights=(np.abs(B) ** 2).ravel(), minlength=n_rings)
    with np.errstate(invalid="ignore", divide="ignore"):
        frc = num / np.sqrt(np.maximum(da * db, 1e-30))
    return 0.5 * (edges[:-1] + edges[1:]), frc


def gauss_blur(img, sigma_px):
    """Separable Gaussian low-pass -- the 'linear post-filter' of fact 617."""
    from scipy.ndimage import gaussian_filter
    if sigma_px <= 0:
        return img.copy()
    return gaussian_filter(img, sigma_px, mode="nearest")


def shift_subpixel(img, dy_px, dx_px, order=3):
    """Sub-pixel translation by spline interpolation.

    Used to PLANT known misregistration and, with zero shift, to measure the
    interpolation penalty an alignment pass pays merely by resampling.
    """
    from scipy.ndimage import shift as ndshift
    return ndshift(img, (dy_px, dx_px), order=order, mode="nearest")


def linear_offsets(spread_px, n, angle_deg=30.0):
    """n offsets evenly spaced along a line of total length spread_px.

    M86 measured the owner's drift as SMOOTH and MONOTONIC, not as random
    jitter, so the frames winning the gate in one region carry offsets drawn
    from a contiguous run of that track.  A line is therefore the faithful
    model and isotropic noise would not be.  Offsets are centred on zero so
    the simulated merge has no net displacement, which keeps the ladder a
    test of BLUR rather than of the registration step in front of it.
    """
    if n < 2 or spread_px <= 0:
        return [(0.0, 0.0)]
    t = np.linspace(-0.5, 0.5, n) * float(spread_px)
    th = np.deg2rad(angle_deg)
    return [(float(v * np.sin(th)), float(v * np.cos(th))) for v in t]


def simulate_misregistered_merge(plane, offsets_px, order=3):
    """Average a plane over a set of translations.

    Stands in for what an unaligned merge does to a region: the frames that
    contribute to one output pixel are drawn at different sub-pixel positions,
    so their content is averaged over the spread of offsets.  This is a MODEL
    of misregistration blur, used only for the positive-control ladder, never
    for a claim about a real merge.
    """
    acc = np.zeros_like(plane, dtype=np.float64)
    for dy, dx in offsets_px:
        acc += shift_subpixel(plane, dy, dx, order=order)
    return acc / len(offsets_px)
