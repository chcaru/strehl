#!/usr/bin/env python3
"""BUILD-TRIAGE shared instrument.

The one question this whole build exists to answer is:

    is this region soft because the MERGE lost detail the source frames hold,
    or because NO source frame ever held it?

Those demand opposite responses -- "retouch" versus "reshoot" -- so the
instrument has to be able to tell them apart without being fooled by the
transformations that sit between a merge and a frame.

THE TRANSFORMATIONS, AND WHAT THIS MODULE DOES ABOUT EACH
---------------------------------------------------------
1. TONE CURVE.  The SHIP-V1 masters are `--srgb`: tone-curved.  Nothing numeric
   is ever taken from them here.  Both arms are re-rendered `--linear-srgb`
   with the SAME pinned binary, so every number below is camera-linear DN.
   Ranking sites inside one image is still fine on a curved render -- that is
   all printqa.py ever claimed -- but a cross-arm ratio is not.

2. RESOLUTION.  `--demosaic` is implied by `--srgb` and NOT by `--linear-srgb`.
   Omitting it returns a 3516x2344 binned render against a 7032x4688 master and
   every ratio is then taken across a 2x resample.  Both arms pass --demosaic.

3. THE ALIGNMENT GATHER.  A merge crops the field of view to `k` so every frame
   covers every pixel, then upsamples back; and it gathers each non-reference
   frame through a CatmullRom warp.  A STREHL_ONLY_FRAME render re-solves
   alignment on a stack of one, so its warp is identity and its `k` is the 3 px
   floor, 0.9974.  The two arms are therefore NOT on the same side of the
   gather and a naive ratio hands the merge a handicap it did not earn.
   This module does not assume a correction factor.  It brackets:

       upper bound on source sharpness = arm B as rendered   (merge handicapped)
       lower bound on source sharpness = arm B + the matched residual gather

   A verdict is only called when it survives BOTH ends of the bracket.  The
   bracket width is reported so a reader can see how much of a verdict is
   instrument rather than subject.

4. MISREGISTRATION.  The two arms differ in coverage scale by ~0.9%, which is
   ~30 px at the frame edge.  Crops at equal coordinates do NOT show equal
   content.  Every comparison here locates its partner window by normalised
   cross-correlation first, and the detail metric itself is the magnitude of a
   windowed Fourier transform, which is shift-invariant -- so residual sub-pixel
   registration error cannot move the answer.

WHAT IT REPORTS.  Amplitude in DN at a stated spatial frequency band, AND the
absolute mean level in DN.  A ratio alone hides an additive bias; this project
has already had one headline effect turn out to be 39% additive.
"""
from __future__ import annotations

import os

import numpy as np

# Spatial-frequency bands, in cycles per sample.  0.5 is Nyquist.
# HIGH is centred on 0.35 c/s, the frequency the project's gather cost is
# quoted at, so the two are directly commensurable.
BANDS = {
    "low": (0.02, 0.08),
    "mid": (0.15, 0.25),
    "high": (0.30, 0.45),
}
DN = 65535.0  # 16-bit full scale; every "DN" below is on this scale.


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------
def load16(path: str) -> np.ndarray:
    """A 16-bit TIFF as float32 DN.  tifffile only -- PIL mangles 16-bit."""
    import tifffile

    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return a.astype(np.float32)


def luma(rgb: np.ndarray) -> np.ndarray:
    """Scene luminance in DN.  Linear-sRGB primaries, so BT.709 weights are
    the colorimetrically correct ones -- and both arms get the identical
    weights, so any error here is common-mode and cancels in a ratio."""
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])


# --------------------------------------------------------------------------
# The detail metric
# --------------------------------------------------------------------------
def _radial_bins(n: int) -> np.ndarray:
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    return np.sqrt(fy * fy + fx * fx)


_HANN: dict[int, np.ndarray] = {}


def _hann(n: int) -> np.ndarray:
    if n not in _HANN:
        w = np.hanning(n + 2)[1:-1].astype(np.float32)
        _HANN[n] = np.outer(w, w)
    return _HANN[n]


def spectrum(tile: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Radially averaged power spectrum of a square tile, in DN^2.

    The mean is removed before the window so the DC term does not leak into
    the low band; the absolute level is reported separately and never inferred
    from the spectrum.
    """
    n = tile.shape[0]
    assert tile.shape[0] == tile.shape[1], "spectrum wants a square tile"
    t = (tile - tile.mean()) * _hann(n)
    p = np.abs(np.fft.fft2(t)) ** 2
    # Normalise out the window's power so the value is an amplitude density
    # comparable between tile sizes.
    p /= (_hann(n) ** 2).sum()
    return _radial_bins(n), p


def band_amp(tile: np.ndarray, k: float = 1.0) -> dict[str, float]:
    """Amplitude in DN inside each named band, plus the absolute level.

    `k` IS THE POINT OF THIS SIGNATURE.  A merge crops the field of view to `k`
    and upsamples back to full size, so its content is magnified by 1/k and a
    feature of physical frequency f (cycles per SENSOR sample) lands at f*k
    cycles per OUTPUT sample.  Across this corpus k runs from 0.9046 to 0.9916,
    so "0.35 cycles per output sample" is a DIFFERENT PHYSICAL FREQUENCY in
    every render, and a merge at k=0.9236 compared against a one-frame render
    at k=0.9974 at equal OUTPUT frequency is being asked an easier question --
    0.323 c/sensor-sample against 0.349.  That is a ~1.08x handicap smuggled in
    as a band definition.

    BANDS ARE THEREFORE DEFINED IN SENSOR FREQUENCY and evaluated at f*k in
    each arm's own output grid.  Neither arm is resampled to achieve this, so
    each keeps exactly ONE Catmull-Rom gather and that loss stays common-mode.

    `mean`, `p50` and `sd` are ABSOLUTE levels in DN.  They are here because an
    additive bias is invisible in every ratio and in every error, and this
    project has already been bitten by exactly that.
    """
    r, p = spectrum(tile)
    out: dict[str, float] = {}
    for name, (lo, hi) in BANDS.items():
        m = (r >= lo * k) & (r < hi * k)
        out[name] = float(np.sqrt(p[m].mean())) if m.any() else float("nan")
    out["mean"] = float(tile.mean())
    out["p50"] = float(np.median(tile))
    out["sd"] = float(tile.std())
    out["k"] = float(k)
    return out


def edge_slope(tile: np.ndarray, pct: float = 99.5) -> float:
    """Sharpness as the strongest edge gradient, in DN per pixel.

    WHY THIS IS THE PRIMARY METRIC.  Band amplitude cannot tell detail from
    noise, and on this corpus that distinction is the whole question: a single
    source frame carries 1.4-2.5x the pixel noise of a pyramid merge of the
    same scene, and broadband noise alone manufactures a 2.05x false sharpness
    advantage for the noisier arm (commissioning C8c).  Measured that way,
    119MSDCF scored "merge/source = 0.549" on a site where the crop plainly
    shows the merge winning.  Measured by edge slope the same pair is 0.957 --
    and the merge's noise is 52 DN against the frame's 72 DN.

    The 3x3 median removes isolated noise excursions while leaving a step edge
    intact, so the statistic responds to BLUR and not to NOISE.  Commissioning
    E2 holds it to 1.5% across a 16x noise range; E3 recovers planted blurs.
    """
    from scipy import ndimage
    m = ndimage.median_filter(tile.astype(np.float32), 3).astype(np.float64)
    gy, gx = np.gradient(m)
    return float(np.percentile(np.hypot(gy, gx), pct))


def pixel_noise(tile: np.ndarray) -> float:
    """Pixel noise sd in DN: the residual after a 3x3 median removes structure."""
    from scipy import ndimage
    t = tile.astype(np.float32)
    return float((t - ndimage.median_filter(t, 3)).std())


def blur_equiv(tile: np.ndarray, ratio: float,
               grid=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.4, 2.0, 3.0)) -> float:
    """Convert a measured sharpness ratio into an equivalent blur, in pixels.

    A raw edge-slope ratio is COMPRESSED: commissioning E3 shows a planted 1.2 px
    Gaussian reads as 0.88, not 0.50, because the p99.5 statistic pools many
    edges rather than one ideal step.  Quoting 0.88 as "12% softer" would badly
    understate the defect, and quoting it as a blur without calibration would be
    an invented number.

    So the curve is measured ON THIS TILE, at this site, by planting known blurs
    and interpolating -- the same self-calibration principle used for the gather.
    The answer is then in a unit the owner can act on: "the merge is equivalent
    to 0.6 px of blur against the best source frame at this site."

    Returns 0.0 when the merge is at or above the source (nothing to explain).
    """
    from scipy import ndimage
    if not np.isfinite(ratio) or ratio >= 1.0:
        return 0.0
    e0 = edge_slope(tile)
    if e0 <= 0:
        return float("nan")
    xs, ys = [], []
    for sg in grid:
        b = tile if sg == 0.0 else ndimage.gaussian_filter(tile.astype(np.float32), sg)
        xs.append(sg)
        ys.append(edge_slope(b) / e0)
    xs, ys = np.array(xs), np.array(ys)
    if ratio <= ys[-1]:
        return float(xs[-1])  # beyond the calibrated range; report the floor
    # ys is monotonically decreasing; np.interp needs increasing x
    return float(np.interp(ratio, ys[::-1], xs[::-1]))


NYQ = (0.46, 0.50)  # where this rig's MTF is ~0, so power here is noise


def noise_template(tile: np.ndarray) -> tuple[np.ndarray, float]:
    """Radial noise PSD template from a tile known to carry no detail.

    WHY THIS EXISTS.  Band amplitude counts noise as if it were detail.  A
    pyramid merge averages many frames and so has FAR less noise than any
    single frame; measured broadband, the merge therefore scores lower than a
    source frame it is visibly sharper than.  On 119MSDCF that produced
    "merge/source = 0.549" on a site where the crop plainly shows the merge
    winning, and 0.256 on a site that is a featureless patch of teal paint
    where NEITHER arm carries detail.  Both are false MERGE-LIMITED verdicts
    and both were caught by opening the picture.

    A flat floor taken at Nyquist is not enough: demosaic interpolation
    low-passes the noise, so its PSD is still falling at Nyquist (measured:
    91 DN at 0.32 c/sample against 53 DN at 0.49 on this corpus, a factor of
    1.7).  Subtracting the Nyquist level would leave most of the noise in the
    band and still favour the noisier arm.  So the SHAPE is measured, per
    subject and per arm, from that subject's flattest block, and only its
    AMPLITUDE is rescaled per site.

    Returns (template_psd_by_radial_bin, its own Nyquist-band level in DN^2).
    """
    r, p = spectrum(tile)
    edges = np.arange(0.0, 0.5001, 0.01)
    prof = np.full(edges.size - 1, np.nan)
    for i in range(edges.size - 1):
        m = (r >= edges[i]) & (r < edges[i + 1])
        if m.any():
            prof[i] = float(p[m].mean())
    # fill any empty bin by nearest valid neighbour so the template is total
    idx = np.arange(prof.size)
    ok = np.isfinite(prof)
    assert ok.sum() >= 10, "noise template has too few populated bins"
    prof = np.interp(idx, idx[ok], prof[ok])
    m = (r >= NYQ[0]) & (r < NYQ[1])
    return prof, float(p[m].mean())


def band_amp_sig(tile: np.ndarray, k: float, tmpl: np.ndarray,
                 tmpl_nyq: float) -> dict[str, float]:
    """Band amplitude with the measured noise template subtracted IN POWER.

    Absolute DN levels for total, noise and signal are all returned, because a
    ratio hides an additive term and noise power IS an additive term.
    """
    r, p = spectrum(tile)
    mn = (r >= NYQ[0]) & (r < NYQ[1])
    site_nyq = float(p[mn].mean())
    gain = site_nyq / tmpl_nyq if tmpl_nyq > 0 else 0.0
    edges = np.arange(0.0, 0.5001, 0.01)
    out: dict[str, float] = {}
    for name, (lo, hi) in BANDS.items():
        m = (r >= lo * k) & (r < hi * k)
        if not m.any():
            out[name] = out[name + "_tot"] = out[name + "_noise"] = float("nan")
            continue
        tot = float(p[m].mean())
        # Average the template over the SAME radial range as the band, not at
        # its centre: the noise PSD falls by ~1.7x across [0.30,0.45], so a
        # centre sample misestimates the very term being subtracted.
        b0 = int(np.clip(lo * k / 0.01, 0, tmpl.size - 1))
        b1 = int(np.clip(np.ceil(hi * k / 0.01), b0 + 1, tmpl.size))
        nz = float(np.mean(tmpl[b0:b1])) * gain
        out[name + "_tot"] = float(np.sqrt(tot))
        out[name + "_noise"] = float(np.sqrt(max(nz, 0.0)))
        out[name] = float(np.sqrt(max(tot - nz, 0.0)))
    out["mean"] = float(tile.mean())
    out["p50"] = float(np.median(tile))
    out["sd"] = float(tile.std())
    out["k"] = float(k)
    out["nyq_dn"] = float(np.sqrt(site_nyq))
    return out


# --------------------------------------------------------------------------
# Registration between arms
# --------------------------------------------------------------------------
def find_match(ref: np.ndarray, hay: np.ndarray, cy: int, cx: int,
               size: int, search: int = 64) -> tuple[int, int, float]:
    """Locate `ref` (size x size) inside `hay` near (cy, cx).

    Returns (y, x, ncc) of the best normalised-cross-correlation match.  Plain
    FFT cross-correlation on mean-removed, variance-normalised windows.
    """
    h, w = hay.shape
    y0 = max(0, min(h - size - 2 * search, cy - search))
    x0 = max(0, min(w - size - 2 * search, cx - search))
    y0, x0 = max(0, y0), max(0, x0)
    win = hay[y0:y0 + size + 2 * search, x0:x0 + size + 2 * search]
    if win.shape[0] < size or win.shape[1] < size:
        return cy, cx, float("nan")

    a = ref - ref.mean()
    na = float(np.sqrt((a * a).sum()))
    if na == 0:
        return cy, cx, float("nan")

    # Sliding-window normalised cross-correlation via FFT + integral images.
    fh, fw = win.shape
    fa = np.zeros((fh, fw), np.float32)
    fa[:size, :size] = a[::-1, ::-1]
    num = np.real(np.fft.ifft2(np.fft.fft2(win) * np.fft.fft2(fa)))
    num = num[size - 1:, size - 1:]

    ii = np.cumsum(np.cumsum(np.pad(win.astype(np.float64), ((1, 0), (1, 0))), 0), 1)
    i2 = np.cumsum(np.cumsum(np.pad(win.astype(np.float64) ** 2, ((1, 0), (1, 0))), 0), 1)

    def boxsum(t):
        return (t[size:, size:] - t[:-size, size:] - t[size:, :-size] + t[:-size, :-size])

    s1, s2 = boxsum(ii), boxsum(i2)
    cnt = size * size
    var = np.maximum(s2 - s1 * s1 / cnt, 1e-6)
    ncc = num[:var.shape[0], :var.shape[1]] / (na * np.sqrt(var))

    j = int(np.argmax(ncc))
    dy, dx = divmod(j, ncc.shape[1])
    return y0 + dy, x0 + dx, float(ncc[dy, dx])


# --------------------------------------------------------------------------
# The matched residual gather (the lower bound on source sharpness)
# --------------------------------------------------------------------------
def catmull_rom_scale(img: np.ndarray, k: float,
                      win: tuple[int, int, int, int] | None = None) -> np.ndarray:
    """Crop the field of view to `k` about the centre and resample back to the
    original size with a Catmull-Rom kernel.

    This is the SAME operation, with the SAME kernel, that the merge applies to
    every frame when it scales the field of view so every frame covers every
    pixel ("coverage: field of view scaled to k ... then upsampled to keep the
    output dimensions").  Applying the residual `k` to one arm is what puts the
    two arms on the same side of the gather.

    `win` = (y0, x0, h, w) returns ONLY that destination window.  The geometry
    is unchanged -- the scale is still about the FULL frame's centre, so a
    windowed result is bit-identical to the corresponding slice of the full
    result.  It exists because the full frame is 33 Mpx and every site needs
    only ~0.5 Mpx of it; commissioning check C6 asserts the equivalence.
    """
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    if win is None:
        ys, xs, hh, ww = 0, 0, h, w
    else:
        ys, xs, hh, ww = win
    yy = (np.arange(ys, ys + hh, dtype=np.float32) - cy) * k + cy
    xx = (np.arange(xs, xs + ww, dtype=np.float32) - cx) * k + cx
    g = np.meshgrid(yy, xx, indexing="ij")
    return _cubic_conv(img, g[0], g[1], a=-0.5)


def _cubic_conv(img: np.ndarray, yy: np.ndarray, xx: np.ndarray,
                a: float = -0.5) -> np.ndarray:
    """Keys cubic convolution.  a = -0.5 IS Catmull-Rom."""
    h, w = img.shape
    y0 = np.floor(yy).astype(np.int32)
    x0 = np.floor(xx).astype(np.int32)
    fy = (yy - y0).astype(np.float32)
    fx = (xx - x0).astype(np.float32)

    def wts(t):
        # Keys cubic convolution, taps at t+1, t, 1-t, 2-t.  Derived, not
        # copied: for |s| in [1,2), W(s) = a s^3 - 5a s^2 + 8a s - 4a, which at
        # s = 1+t gives a(t^3 - 2t^2 + t) and at s = 2-t gives a(t^2 - t^3).
        # BOTH OUTER TAPS ARE NEGATIVE for a = -0.5.  An earlier revision of
        # this function had both signs flipped; the weights then summed to
        # 1 + 2a(t - t^2) = 1.25 at t = 0.5 instead of 1, and a constant image
        # came back 25% brighter per axis.  Commissioning caught it only
        # because a constant image has a closed-form answer.
        t2, t3 = t * t, t * t * t
        return (
            a * (t3 - 2 * t2 + t),
            (a + 2) * t3 - (a + 3) * t2 + 1,
            -(a + 2) * t3 + (2 * a + 3) * t2 - a * t,
            a * (t2 - t3),
        )

    wy, wx = wts(fy), wts(fx)
    # Partition of unity, asserted rather than assumed.  Any interpolator that
    # fails this rescales the signal, which shows up as a level shift in DN and
    # would be read as a merge defect.
    for nm, ws in (("y", wy), ("x", wx)):
        s = ws[0] + ws[1] + ws[2] + ws[3]
        assert np.abs(s - 1.0).max() < 1e-5, (
            f"cubic {nm} weights do not sum to 1 "
            f"(max deviation {np.abs(s - 1.0).max():.2e})")
    out = np.zeros(yy.shape, np.float32)
    for m in range(4):
        ys = np.clip(y0 - 1 + m, 0, h - 1)
        acc = np.zeros(yy.shape, np.float32)
        for n in range(4):
            xs = np.clip(x0 - 1 + n, 0, w - 1)
            acc += wx[n] * img[ys, xs]
        out += wy[m] * acc
    return out


def catmull_rom_shift(img: np.ndarray, dy: float, dx: float,
                      win: tuple[int, int, int, int] | None = None) -> np.ndarray:
    """Gather `img` through a pure sub-pixel TRANSLATION with the same kernel.

    This exists to measure what one Catmull-Rom gather COSTS, without the
    side-effect that makes a scale gather useless for the job: a scale by s
    also magnifies the content by 1/s, which is 8% on the bee stacks, and a
    translation match cannot absorb 8% of stretch -- the self-calibration then
    fails to register (ncc 0.43) and returns a gather "cost" of 1.32, i.e. a
    blur that amplifies, which is impossible.

    A translation gather leaves the content scale alone, so the before and
    after are trivially comparable, while exercising the kernel at exactly the
    sub-pixel phase that is where the loss actually comes from.
    """
    h, w = img.shape
    ys, xs, hh, ww = win if win is not None else (0, 0, h, w)
    yy = np.arange(ys, ys + hh, dtype=np.float32) + dy
    xx = np.arange(xs, xs + ww, dtype=np.float32) + dx
    g = np.meshgrid(yy, xx, indexing="ij")
    return _cubic_conv(img, g[0], g[1], a=-0.5)


# Sub-pixel phases used to average the gather cost.  A scale gather by s sweeps
# the fractional offset uniformly through [0,1) with period 1/(1-s) pixels --
# 13.5 px at s=0.926, so ~38 full cycles across a 512 px window.  Averaging the
# translation cost over these phases reproduces that uniform-phase average,
# instead of quoting the worst case at phase 0.5.
GATHER_PHASES = (0.125, 0.375, 0.625, 0.875)
def read_log(path: str, require: tuple[str, ...] = ()) -> dict:
    """Provenance lives in the log, not the filename.  Pull the facts a
    measurement is only valid against: coverage scale, reference frame, frame
    count, resampler, black/white points, colour space.

    ENCODING IS NOT A DETAIL.  PowerShell's `>` redirection writes UTF-16LE
    with a BOM.  Reading that as UTF-8 yields NUL-interleaved mojibake, every
    pattern misses, and the function returns an empty dict -- which a caller
    with a default silently turns into a wrong number.  That very nearly
    substituted k=0.9887 for bee-3-cpl's real k=0.9321, a 6% error in the one
    quantity the whole merge-versus-frame comparison rests on.  So: sniff the
    BOM, and let `require` make a missing key an ERROR rather than a default.
    """
    d: dict = {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"no provenance log at {path}")
    with open(path, "rb") as fh:
        raw = fh.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    elif raw[:3] == b"\xef\xbb\xbf":
        text = raw[3:].decode("utf-8", "replace")
    else:
        text = raw.decode("utf-8", "replace")

    for line in text.splitlines():
        s = line.strip()
        if "field of view scaled to" in s:
            d["coverage_k"] = float(s.split("scaled to")[1].split()[0])
        elif s.startswith("alignment") and "reference frame" in s:
            t = s.split("reference frame")[1].strip().split()[0].rstrip(",")
            d["ref_frame"] = int(t)
            d["placed"] = s
        elif s.startswith("frames") and " from " in s:
            d["n_frames"] = int(s.split(":")[1].strip().split()[0])
        elif "resampler:" in s:
            d["resampler"] = s.split("resampler:")[1].strip()
        elif s.startswith("levels"):
            d["levels"] = s.split(":", 1)[1].strip()
        elif s.startswith("wrote"):
            d["wrote"] = s.split(":", 1)[1].strip()
        elif s.startswith("colour"):
            d["colour"] = s.split(":", 1)[1].strip()
        elif s.startswith("iso"):
            d["iso"] = s.split(":", 1)[1].strip()
        elif s.startswith("alignment") and "OFF" in s:
            d["alignment"] = "OFF"
            d["alignment_note"] = s
    # Alignment OFF is a POSITIVE statement in the log, not a missing value.
    # highly-angled-ruler-mm-cpl is refused by the aligner as a tilted subject
    # ("a global similarity [transform is inappropriate]") and its frames are
    # combined unregistered, so no field of view is cropped and no resampler
    # runs: k is exactly 1 and there is no gather. Deriving that from the log
    # is evidence; defaulting it would be the error this check exists to stop.
    if d.get("alignment") == "OFF":
        d.setdefault("coverage_k", 1.0)
        d.setdefault("resampler", "none (frames combined unregistered)")
    missing = [k for k in require if k not in d]
    if missing:
        raise ValueError(
            f"{path}: provenance is missing {missing}. A measurement taken "
            "against a defaulted coverage scale is not a measurement.")
    return d


SUBJECTS = [
    "109MSDCF", "112MSDCF", "113MSDCF", "119MSDCF",
    "bee-1-cpl", "bee-2-cpl", "bee-3-cpl",
    "coffee-bean", "coffee-bubbles", "couch-fibers-cpl",
    "dry-erase-marker-head-cpl", "flat-on-ruler-cpl",
    "flower-bud-alone-cpl", "flower-bud-with-background-fern-cpl",
    "flower-inner-edge-cpl", "flowers-cpl", "foam",
    "highly-angled-ruler-mm-cpl", "lavendar-cpl", "lead-1-cpl", "leaf-2-cpl",
    "pencil-flatter-angle-cpl", "pencil-steep-angle-cpl", "tweezers-cpl",
    "wrapped-text-1", "wrapped-text-2",
]
RAW = r"D:\personal\macro"
LIN = r"C:\dev\strehl-out\BUILD-TRIAGE\lin"
SHIP = r"C:\dev\strehl-out\SHIP-V1"
OUT = r"C:\dev\strehl-out\BUILD-TRIAGE"
