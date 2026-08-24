"""M104 -- the ruler magnification / object-space detail instrument.

WHAT THIS MEASURES AND WHY IT IS THE RIGHT INSTRUMENT

M95 is removing `fit_to_cover`'s upsample, so the emitted image changes
DIMENSIONS.  That breaks two families of instrument at once:

  * anything that maps tiles by absolute pixel coordinate mis-registers
    silently after the fix and reads the mis-registration as blur;
  * anything measured per pixel improves for free, because the same object is
    now carried by fewer pixels (rule 18).  That bias runs TOWARD "the fix
    worked", and it is precisely the error behind facts 1235/1237 and their
    retraction in 1250.

A millimetre ruler defeats both.  The tick pitch is a physical constant, so:

  f0            comb frequency in cyc/px -- a measurement of the SAMPLING
  mag = f0_ref / f0_test        the magnification of test relative to ref
  Mn            modulation depth at the comb, normalised by ROI mean level

`mag` is dimension-agnostic by construction: cropping an image to different
output dimensions without resampling leaves every tick exactly where it was, so
f0 does not move.  That is not an argument, it is the DIM control.

`Mn` is object-space because the comb is the SAME PHYSICAL TICK PITCH in both
renders regardless of how many pixels carry it.  Probing each render at its own
f0 therefore probes both at the same object frequency.  Dividing by the ROI
mean converts comb amplitude into modulation depth, which removes the exposure
and gain difference between two renders -- the defect in M98's S8, where an
unnormalised M was compared across two renders at different scales and its sign
was correctly refused as a bar.

D_hi is the same idea applied to a band rather than a line: annulus power over
[1.5*f0, 2.5*f0] IN EACH RENDER'S OWN UNITS is the same object band in both,
contrast-normalised, reported as log10 ratio (dex) to be commensurable with the
orchestrator's independent spectral measurement (fact 1286/1287).

SUB-BIN REFINEMENT IS NOT OPTIONAL.  The bar is +/- 0.004 in `mag`, i.e. 0.4%.
On a 768-px ROI the FFT bin is 1/768 = 0.0013 cyc/px; against an f0 near 0.05
that is a 2.6% quantisation, six times coarser than the bar.  Reading the
integer peak would make every control pass by being blind.  The peak is
therefore refined to sub-bin by a floor-subtracted power-weighted centroid, and
the DOSE control exists to prove the refined readout actually resolves 1%.
"""

import numpy as np
import tifffile

RENDERS = r"C:\dev\strehl-out\M104\renders"
LOGS = r"C:\dev\strehl-out\M104\logs"

ROI = 768  # see module docstring: bin size vs the +/-0.004 bar
DISC = 2.0  # probe disc radius, bins
CENT = 2.5  # centroid refinement radius, bins
SIDE_LO, SIDE_HI = 0.82, 1.22
F_MIN, F_MAX = 0.03, 0.40
INERT_MIN = 3.0  # S/B on the reference render
HI_LO, HI_HI = 1.5, 2.5  # D_hi annulus, in units of f0


def green(path) -> np.ndarray:
    """Green plane, float64.  Handles both binned-Bayer and demosaiced TIFFs."""
    a = tifffile.imread(str(path))
    if a.ndim == 3:
        a = a[..., 1]
    return a.astype(np.float64)


def roi_grid(h: int, w: int, n: int = ROI, cols: int = 5, rows: int = 4):
    """ROI positions as a FRACTION of the emitted dimensions.

    This is the orchestrator's dimension trap handled by construction rather
    than by remembering: when M95's fix changes the output size, a fractional
    lattice follows the frame instead of walking off it or sampling a
    different part of the subject.
    """
    out = []
    for r in range(rows):
        for c in range(cols):
            fy = (r + 0.5) / rows
            fx = (c + 0.5) / cols
            y = int(round(fy * h - n / 2))
            x = int(round(fx * w - n / 2))
            y = max(0, min(h - n, y))
            x = max(0, min(w - n, x))
            out.append((x, y))
    return out


def crop(a: np.ndarray, xy, n: int = ROI) -> np.ndarray:
    x, y = xy
    return a[y : y + n, x : x + n]


def _hann2(n: int) -> np.ndarray:
    w = np.hanning(n)
    return np.outer(w, w)


def power(img: np.ndarray, normalise: bool = True):
    """Contrast-normalised 2-D power spectrum.

    Dividing by the mean level squared makes the spectrum a measure of
    modulation rather than of exposure, so two renders with different gain are
    commensurable.  Returns (P, mean).
    """
    a = np.asarray(img, dtype=np.float64)
    mu = float(a.mean())
    a = a - mu
    if normalise and abs(mu) > 1e-9:
        a = a / mu
    a = a * _hann2(a.shape[0])
    F = np.fft.fftshift(np.fft.fft2(a))
    return (F.real**2 + F.imag**2) / a.size, mu


def freq_grid(n: int):
    f = np.fft.fftshift(np.fft.fftfreq(n))
    fy, fx = np.meshgrid(f, f, indexing="ij")
    return fy, fx


def find_comb(P: np.ndarray):
    """Dominant non-DC peak, refined to sub-bin.  Returns (fy, fx, f0)."""
    n = P.shape[0]
    fy, fx = freq_grid(n)
    r = np.hypot(fy, fx)
    half = (fy > 0) | ((np.abs(fy) < 1e-12) & (fx > 0))
    m = (r >= F_MIN) & (r <= F_MAX) & half
    if not m.any():
        return None
    iy, ix = np.unravel_index(int(np.argmax(np.where(m, P, -np.inf))), P.shape)
    return refine(P, float(fy[iy, ix]), float(fx[iy, ix]))


ANG_TOL = 0.15  # rad; a pure scale change does not rotate the comb
RAD_TOL = 0.15  # fractional search window around the seeded frequency


def find_comb_near(P: np.ndarray, fy_s: float, fx_s: float):
    """Locate the comb in a window around a SEEDED frequency and direction.

    The first version of this instrument searched the test arm globally and
    then only checked the angle.  A comb and its own 2nd harmonic lie at the
    SAME angle, so an ROI whose harmonic outran its fundamental returned
    mag ~ 2 or ~ 0.5, and the resulting scatter blew the DOSE and DIM controls
    (SE 0.13 and 0.20 against a 0.004 bar).  The controls caught it; the
    docstring had described the correct algorithm all along and the code did
    not implement it.

    The window is +/- 15%, which is twice the largest effect this milestone
    measures (bee-3-cpl's 1/k = 1.0735, i.e. 7.4%), so it admits both the
    "resample removed" and "resample still there" hypotheses with room to
    spare.  A window narrow enough to force 1.000 would be circular; this one
    is not, and the DOSE control at 1.075 is what proves it.
    """
    n = P.shape[0]
    fy, fx = freq_grid(n)
    f_s = float(np.hypot(fy_s, fx_s))
    r = np.hypot(fy, fx)
    half = (fy > 0) | ((np.abs(fy) < 1e-12) & (fx > 0))
    ang = np.arctan2(fy, fx)
    da = np.abs(np.arctan2(np.sin(ang - np.arctan2(fy_s, fx_s)),
                           np.cos(ang - np.arctan2(fy_s, fx_s))))
    m = half & (r >= f_s * (1 - RAD_TOL)) & (r <= f_s * (1 + RAD_TOL)) & (da <= ANG_TOL)
    if m.sum() < 4:
        return None
    iy, ix = np.unravel_index(int(np.argmax(np.where(m, P, -np.inf))), P.shape)
    return refine(P, float(fy[iy, ix]), float(fx[iy, ix]))


def refine(P: np.ndarray, fy0: float, fx0: float):
    """Floor-subtracted power-weighted centroid around a peak.

    The floor subtraction matters: without it the broadband pedestal pulls the
    centroid toward the disc centre and compresses every measured ratio toward
    1.000, which would make the fix look successful by making the instrument
    insensitive.  The floor is the disc's own minimum.
    """
    n = P.shape[0]
    fy, fx = freq_grid(n)
    bw = 1.0 / n
    d = np.hypot(fy - fy0, fx - fx0) / bw
    m = d <= CENT
    w = P[m] - P[m].min()
    if w.sum() <= 0:
        return fy0, fx0, float(np.hypot(fy0, fx0))
    cy = float((fy[m] * w).sum() / w.sum())
    cx = float((fx[m] * w).sum() / w.sum())
    return cy, cx, float(np.hypot(cy, cx))


def disc_sum(P: np.ndarray, fy0: float, fx0: float, rad: float = DISC) -> float:
    n = P.shape[0]
    fy, fx = freq_grid(n)
    bw = 1.0 / n
    tot = 0.0
    for sy, sx in ((fy0, fx0), (-fy0, -fx0)):
        d = np.hypot(fy - sy, fx - sx) / bw
        tot += float(P[d <= rad].sum())
    return tot


def probe(P: np.ndarray, fy0: float, fx0: float):
    """Sideband-subtracted comb power, floor and modulation depth."""
    S = disc_sum(P, fy0, fx0)
    B = 0.5 * (
        disc_sum(P, fy0 * SIDE_LO, fx0 * SIDE_LO)
        + disc_sum(P, fy0 * SIDE_HI, fx0 * SIDE_HI)
    )
    return S, B, float(np.sqrt(max(S - B, 0.0)))


def band_power(P: np.ndarray, f0: float, lo: float = HI_LO, hi: float = HI_HI):
    """Contrast-normalised annulus power over [lo*f0, hi*f0].

    Expressed in units of f0, so the SAME OBJECT BAND is integrated in both
    renders however they are sampled.  Returns mean power per bin.
    """
    n = P.shape[0]
    fy, fx = freq_grid(n)
    r = np.hypot(fy, fx)
    m = (r >= lo * f0) & (r <= hi * f0) & (r < 0.5)
    if m.sum() < 8:
        return None
    return float(P[m].mean())


def band_power_abs(P: np.ndarray, lo: float, hi: float):
    """Contrast-normalised annulus power over an ABSOLUTE pixel band.

    Used with the band pre-divided by the measured magnification on the
    enlarged arm, so that both arms are integrated over the same OBJECT
    frequencies while the band itself is quoted in the reference arm's pixel
    units.  This is what makes the result commensurable with a spectral
    measurement made elsewhere at a stated cyc/px band.
    """
    n = P.shape[0]
    fy, fx = freq_grid(n)
    r = np.hypot(fy, fx)
    m = (r >= lo) & (r <= hi) & (r < 0.5)
    if m.sum() < 8:
        return None
    return float(P[m].mean())


def stats(v):
    """Mean and standard error across repetitions."""
    v = np.asarray([x for x in v if np.isfinite(x)], dtype=np.float64)
    if v.size == 0:
        return float("nan"), float("nan"), 0
    if v.size == 1:
        return float(v[0]), float("nan"), 1
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(v.size)), int(v.size)


def resample(a: np.ndarray, scale: float) -> np.ndarray:
    """Geometric rescale about the image centre, keeping dimensions.

    Used ONLY by the controls, to plant a magnification of known size.  The
    kernel is a cubic spline (scipy order=3), which is not the same amplitude
    response as the aligner's Catmull-Rom -- that is irrelevant here because
    the controls test where the comb LANDS, not how tall it is.
    """
    from scipy.ndimage import map_coordinates

    h, w = a.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    src_y = cy + (yy - cy) / scale
    src_x = cx + (xx - cx) / scale
    return map_coordinates(a, [src_y, src_x], order=3, mode="reflect")


def gmean_se(v):
    """Geometric mean and its SE, for quantities that are RATIOS.

    A magnification is a ratio, so its natural average is geometric: the
    geometric mean of x is exactly the reciprocal of the geometric mean of
    1/x, whereas the arithmetic mean is not.  The placebo control (swap
    reference and test, require inversion to 1e-6) is only satisfiable with a
    reciprocal-invariant estimator, and the first version of this instrument
    failed PL at 1.3e-3 for exactly that reason.  The SE is computed in log
    space and mapped back, so it is asymmetric-correct to first order.
    """
    v = np.asarray([x for x in v if np.isfinite(x) and x > 0], dtype=np.float64)
    if v.size == 0:
        return float("nan"), float("nan"), 0
    lg = np.log(v)
    m = float(np.exp(lg.mean()))
    if v.size == 1:
        return m, float("nan"), 1
    se = float(lg.std(ddof=1) / np.sqrt(lg.size)) * m
    return m, se, int(v.size)


def seed_combs(img: np.ndarray, cols=5, rows=4):
    """Per-ROI comb location on a designated seed image, found globally once.

    Both arms are then measured with this SAME seed, by the SAME procedure.
    That is what makes the estimator symmetric: swapping which arm is called
    "reference" cannot change either arm's frequency estimate, so the placebo
    inverts exactly rather than approximately.
    """
    out = {}
    for i, xy in enumerate(roi_grid(*img.shape, cols=cols, rows=rows)):
        P, _ = power(crop(img, xy))
        c = find_comb(P)
        if c is None:
            continue
        fy, fx, f0 = c
        S, B, _ = probe(P, fy, fx)
        if B <= 0 or S / B < INERT_MIN:
            continue  # INERT: no comb, no evidence
        out[i] = dict(fy=fy, fx=fx, f0=f0, sb=S / B)
    return out


def measure_arm(img: np.ndarray, seed: dict, cols=5, rows=4):
    """Measure every seeded ROI on one arm.  ROIs are placed by FRACTION of
    this image's own dimensions, so an arm with different pixel dimensions is
    read at the same place in the frame rather than at the same coordinate."""
    grid = roi_grid(*img.shape, cols=cols, rows=rows)
    out = {}
    for i, s in seed.items():
        if i >= len(grid):
            continue
        P, mu = power(crop(img, grid[i]))
        c = find_comb_near(P, s["fy"], s["fx"])
        if c is None:
            continue
        fy, fx, f0 = c
        S, B, M = probe(P, fy, fx)
        out[i] = dict(f0=f0, sb=(S / B if B > 0 else float("nan")), mod=M,
                      hi=band_power(P, f0), mean=mu, P=P)
    return out


NYQ_LO, NYQ_HI = 0.30, 0.48  # near-Nyquist band, reference arm's pixel units


def measure_pair(ref: np.ndarray, test: np.ndarray, seed: dict, cols=5, rows=4):
    """Paired magnification and object-space modulation, ref vs test.

    An ROI is admitted only if BOTH arms clear the sideband floor by
    INERT_MIN.  A symmetric admission rule keeps the ROI set unchanged when
    the arms are swapped, which the placebo requires; a rule applied to the
    reference arm alone silently changes the sample under swap and makes the
    placebo untestable.
    """
    A = measure_arm(ref, seed, cols, rows)
    B = measure_arm(test, seed, cols, rows)
    rows_out = []
    for i in sorted(set(A) & set(B)):
        a, b = A[i], B[i]
        if not (a["sb"] >= INERT_MIN and b["sb"] >= INERT_MIN):
            continue
        mg = a["f0"] / b["f0"] if b["f0"] > 0 else float("nan")
        # Near-Nyquist band, corrected to OBJECT space: content at object
        # frequency f (in the reference arm's pixel units) appears in an arm
        # enlarged by `mg` at f/mg.  Integrating both arms over the same
        # numeric pixel band would charge the enlarged arm for being enlarged
        # -- which is the rule-18 free win, not a detail loss.
        na = band_power_abs(a["P"], NYQ_LO, NYQ_HI)
        nb = band_power_abs(b["P"], NYQ_LO / mg, NYQ_HI / mg)
        rows_out.append(
            dict(
                roi=i,
                f0_ref=a["f0"],
                f0_test=b["f0"],
                mag=mg,
                sb_ref=a["sb"],
                sb_test=b["sb"],
                mod_ref=a["mod"],
                mod_test=b["mod"],
                mod_ratio=b["mod"] / a["mod"] if a["mod"] > 0 else float("nan"),
                hi_ref=a["hi"],
                hi_test=b["hi"],
                d_hi=(
                    float(np.log10(a["hi"] / b["hi"]))
                    if (a["hi"] and b["hi"] and a["hi"] > 0 and b["hi"] > 0)
                    else float("nan")
                ),
                d_nyq=(
                    float(np.log10(na / nb))
                    if (na and nb and na > 0 and nb > 0)
                    else float("nan")
                ),
            )
        )
    return rows_out


def summarise(rows, key):
    return stats([r[key] for r in rows])
