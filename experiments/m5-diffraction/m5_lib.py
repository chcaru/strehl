"""M5 — diffraction cutoff from the radially averaged power spectrum.

Shared library. Everything here works in **sensor** frequency units
(cycles per 5.12 um sensor pixel, and cycles/mm) no matter which CFA
sublattice the samples came from, so that the factor of 2 between the sensor
grid and a Bayer sublattice — Trap 1, the single most likely way to produce a
confidently wrong answer — can never hide inside an intermediate result.

Three sampling lattices of the *same* green photosites are supported:

  G1  raw[0::2, 1::2]  pitch 2*5.12 = 10.24 um    Nyquist 0.250 sensor cyc/px
  G2  raw[1::2, 0::2]  pitch 2*5.12 = 10.24 um    Nyquist 0.250 sensor cyc/px
  GQ  both greens on their true quincunx lattice, re-indexed onto a square
      grid rotated 45 deg, pitch sqrt(2)*5.12 = 7.2408 um.
      Isotropic (inscribed-circle) reach 0.354 sensor cyc/px; the full
      support is the diamond |fx| + |fy| <= 0.5 sensor cyc/px, so along the
      sensor H and V axes it reaches the full sensor Nyquist.

GQ is an extension, not part of the prescribed method. It uses exactly the
same photosites as G1 and G2 — no interpolation, no demosaic — arranged on the
lattice they actually occupy. It exists because every candidate cutoff for
this rig sits above the 0.250 cyc/px reach of a single sublattice.

No demosaicing anywhere. No frame averaging anywhere.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Sensor constants. MEASURED, from M1 / F-camera-lens-optics.md, re-confirmed
# against rawpy below in `load_active`.
# ---------------------------------------------------------------------------

BLACK_LEVEL = 512
WHITE_LEVEL = 15360  # SR2SubIFD usable ceiling, NOT the 16383 in SubIFD
PITCH_UM = 5.12

# rawler reports a 7032x4688 active area inside a 7168x5120 buffer; LibRaw
# (via rawpy) reports 7028x4688 visible. We take the intersection, which is a
# strict subset of both, so no statistic can touch the synthetic zero padding
# (project rule 7).
ACTIVE_W = 7028
ACTIVE_H = 4688

LAMBDA_UM = 0.550  # green band centre; see M5 doc for the +-50 nm systematic

# ---------------------------------------------------------------------------
# Lattices
# ---------------------------------------------------------------------------

LATTICES = ("G1", "G2", "GQ")

# Sample pitch of each lattice, in units of the sensor pitch.
LATTICE_PITCH_PX = {"G1": 2.0, "G2": 2.0, "GQ": float(np.sqrt(2.0))}


def lattice_pitch_um(lattice: str) -> float:
    return LATTICE_PITCH_PX[lattice] * PITCH_UM


def lattice_nyquist_sensor(lattice: str) -> float:
    """Isotropic reach of the radial average, in sensor cyc/px.

    For G1/G2 this is the lattice Nyquist, 0.5 / 2 = 0.25.
    For GQ it is 0.5 / sqrt(2) = 0.3536 — the inscribed circle of the diamond.
    """
    return 0.5 / LATTICE_PITCH_PX[lattice]


def sensor_cyc_px_to_cyc_mm(f: float | np.ndarray) -> float | np.ndarray:
    """cycles per sensor pixel -> cycles per mm at the sensor."""
    return np.asarray(f) / (PITCH_UM * 1e-3)


# ---------------------------------------------------------------------------
# Raw IO
# ---------------------------------------------------------------------------


def load_active(path: str) -> np.ndarray:
    """Decode one ARW and return the active area as raw uint16 DN.

    Black level is NOT subtracted here — callers subtract it per lattice so
    that the subtraction is visible at the call site.
    """
    import rawpy

    with rawpy.imread(path) as r:
        a = np.array(r.raw_image[:ACTIVE_H, :ACTIVE_W], dtype=np.uint16)
        # Confirm the sensor constants we assumed rather than trusting them.
        assert r.sizes.top_margin == 0 and r.sizes.left_margin == 0
        assert tuple(r.raw_pattern.ravel()) == (0, 1, 3, 2), r.raw_pattern
        assert set(r.black_level_per_channel) == {BLACK_LEVEL}
        assert set(r.camera_white_level_per_channel) == {WHITE_LEVEL}
    return a


def crop_lattice(active: np.ndarray, lattice: str, rc: int, cc: int, size: int,
                 bounds: tuple[int, int] | None = None) -> np.ndarray:
    """Extract a `size` x `size` patch of one green lattice, centred on sensor
    pixel (rc, cc). Returns float64 DN above black.

    `rc` and `cc` must be even, so that the CFA phase is unambiguous.
    Raises if the sensor bounding box leaves the active area. `bounds`
    overrides the active-area extent (used by the synthetic controls, which
    build small arrays).
    """
    h, w = bounds if bounds is not None else (ACTIVE_H, ACTIVE_W)
    assert rc % 2 == 0 and cc % 2 == 0, "ROI centre must be on an even sensor pixel"
    if lattice in ("G1", "G2"):
        # G1 sits at (even row, odd col); G2 at (odd row, even col).
        r_off, c_off = (0, 1) if lattice == "G1" else (1, 0)
        r0 = rc // 2 - size // 2
        c0 = cc // 2 - size // 2
        r_lo, r_hi = 2 * r0 + r_off, 2 * (r0 + size - 1) + r_off
        c_lo, c_hi = 2 * c0 + c_off, 2 * (c0 + size - 1) + c_off
        _assert_inside(r_lo, r_hi, c_lo, c_hi, h, w)
        patch = active[r_lo : r_hi + 1 : 2, c_lo : c_hi + 1 : 2]
    elif lattice == "GQ":
        # B[u, v] = A[u + v, u - v + 1].  u = (r + c - 1)/2, v = (r - c + 1)/2.
        u0 = (rc + cc) // 2
        v0 = (rc - cc) // 2
        k = np.arange(size) - size // 2
        U = (u0 + k)[:, None]
        V = (v0 + k)[None, :]
        R = U + V
        C = U - V + 1
        _assert_inside(int(R.min()), int(R.max()), int(C.min()), int(C.max()), h, w)
        patch = active[R, C]
    else:
        raise ValueError(lattice)
    patch = patch.astype(np.float64)
    assert patch.min() > 0.0, "ROI touched the zero padding"
    return patch - BLACK_LEVEL


def _assert_inside(r_lo: int, r_hi: int, c_lo: int, c_hi: int, h: int, w: int) -> None:
    if not (0 <= r_lo and r_hi < h and 0 <= c_lo and c_hi < w):
        raise ValueError(
            f"ROI bounding box rows {r_lo}..{r_hi} cols {c_lo}..{c_hi} "
            f"leaves the {h}x{w} active area"
        )


# ---------------------------------------------------------------------------
# Windows and periodograms
# ---------------------------------------------------------------------------

WINDOWS = ("hann", "none", "kaiser8")


def window_2d(n: int, kind: str) -> np.ndarray:
    if kind == "none":
        w = np.ones(n)
    elif kind == "hann":
        w = np.hanning(n + 1)[:n]
    elif kind == "kaiser8":
        w = np.kaiser(n, 8.0)
    else:
        raise ValueError(kind)
    return np.outer(w, w)


def welch_psd2(patch: np.ndarray, tile: int, window: str) -> np.ndarray:
    """Welch-averaged 2D periodogram over 50%-overlapped square tiles.

    Normalised so that white noise of variance s^2 gives E[P] = s^2 in every
    bin, independent of tile size and window.
    """
    n = patch.shape[0]
    assert patch.shape[0] == patch.shape[1]
    step = tile // 2
    starts = list(range(0, n - tile + 1, step))
    w = window_2d(tile, window)
    wnorm = float((w * w).sum())
    acc = np.zeros((tile, tile))
    count = 0
    for i in starts:
        for j in starts:
            t = patch[i : i + tile, j : j + tile]
            t = t - t.mean()
            F = np.fft.fft2(t * w)
            acc += (F.real**2 + F.imag**2) / wnorm
            count += 1
    return acc / count


def radial_psd(psd2: np.ndarray, lattice: str, sector: str = "iso"):
    """Radially average a 2D periodogram into sensor-frequency bins.

    Returns (f_sensor, power, counts) with f_sensor in cycles per *sensor*
    pixel. Bin 0 (which contains DC) is dropped.

    sector:
      "iso"  full azimuth, radius limited to the inscribed circle.
      "hv15" only frequencies within +-15 deg of the sensor H or V axis. Legal
             because the diffraction MTF is isotropic; on GQ it reaches
             further than the inscribed circle (up to 0.408 sensor cyc/px).
    """
    n = psd2.shape[0]
    fu = np.fft.fftfreq(n)[:, None] * np.ones((1, n))  # cyc per lattice sample
    fv = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    if lattice in ("G1", "G2"):
        fx = fv / LATTICE_PITCH_PX[lattice]  # sensor cyc/px
        fy = fu / LATTICE_PITCH_PX[lattice]
    else:  # GQ: B[u,v] = A[u+v, u-v+1] => fu = fx+fy, fv = fy-fx
        fx = (fu - fv) / 2.0
        fy = (fu + fv) / 2.0
    r = np.hypot(fx, fy)

    if sector == "iso":
        rmax = lattice_nyquist_sensor(lattice)
        mask = r <= rmax
    elif sector == "hv15":
        s = np.sin(np.deg2rad(15.0))
        with np.errstate(invalid="ignore", divide="ignore"):
            ang_ok = (np.abs(fy) <= s * r) | (np.abs(fx) <= s * r)
        # Support of GQ is the diamond |fx|+|fy| <= 0.5; of G1/G2 the square
        # |fx|,|fy| <= 0.25. Restrict to the largest radius fully covered by
        # the sector within that support.
        if lattice == "GQ":
            rmax = 0.5 / (np.cos(np.deg2rad(15.0)) + np.sin(np.deg2rad(15.0)))
        else:
            rmax = 0.25
        mask = ang_ok & (r <= rmax)
    else:
        raise ValueError(sector)

    nb = n // 2
    edges = np.linspace(0.0, rmax, nb + 1)
    idx = np.digitize(r[mask].ravel(), edges) - 1
    vals = psd2[mask].ravel()
    ok = (idx >= 0) & (idx < nb)
    counts = np.bincount(idx[ok], minlength=nb).astype(float)
    sums = np.bincount(idx[ok], weights=vals[ok], minlength=nb)
    f = 0.5 * (edges[:-1] + edges[1:])
    with np.errstate(invalid="ignore", divide="ignore"):
        p = sums / counts
    keep = counts > 0
    keep[0] = False  # bin 0 holds DC
    return f[keep], p[keep], counts[keep]


def spectrum(patch, lattice, tile=256, window="hann", sector="iso"):
    return radial_psd(welch_psd2(patch, tile, window), lattice, sector)


# ---------------------------------------------------------------------------
# Per-tile machinery: lets the sharpest *frame* be chosen independently for
# each tile of an ROI (Trap 4 taken to its logical conclusion).  Tile
# periodograms from different frames may be averaged: they are independent
# estimates of the same optical transfer function, and no pixel value is ever
# averaged across frames.
# ---------------------------------------------------------------------------


def tile_starts(n: int, tile: int):
    return list(range(0, n - tile + 1, tile // 2))


def tile_psd2_stack(patch: np.ndarray, tile: int, window: str) -> np.ndarray:
    """Per-tile 2D periodograms, shape (ntiles, tile, tile), same
    normalisation as welch_psd2 (white noise of variance s^2 -> s^2)."""
    n = patch.shape[0]
    st = tile_starts(n, tile)
    w = window_2d(tile, window)
    wnorm = float((w * w).sum())
    out = np.empty((len(st) * len(st), tile, tile))
    k = 0
    for i in st:
        for j in st:
            t = patch[i : i + tile, j : j + tile]
            F = np.fft.fft2((t - t.mean()) * w)
            out[k] = (F.real**2 + F.imag**2) / wnorm
            k += 1
    return out


_BAND_CACHE: dict = {}


def band_masks(tile: int, lattice: str, sector: str = "iso",
               mid=(0.05, 0.14), floor_frac=0.85):
    """Boolean masks over the 2D periodogram for a mid-band (used as a focus
    measure) and a high-frequency band (used as a floor estimate), both in
    *sensor* cycles/px so they mean the same thing on every lattice."""
    key = (tile, lattice, sector, mid, floor_frac)
    if key in _BAND_CACHE:
        return _BAND_CACHE[key]
    fu = np.fft.fftfreq(tile)[:, None] * np.ones((1, tile))
    fv = np.fft.fftfreq(tile)[None, :] * np.ones((tile, 1))
    if lattice in ("G1", "G2"):
        fx = fv / LATTICE_PITCH_PX[lattice]
        fy = fu / LATTICE_PITCH_PX[lattice]
    else:
        fx = (fu - fv) / 2.0
        fy = (fu + fv) / 2.0
    r = np.hypot(fx, fy)
    rmax = lattice_nyquist_sensor(lattice)
    m_mid = (r >= mid[0]) & (r <= mid[1])
    m_flr = (r >= floor_frac * rmax) & (r <= rmax)
    _BAND_CACHE[key] = (m_mid, m_flr)
    return m_mid, m_flr


def focus_score_2d(psd2: np.ndarray, masks) -> np.ndarray:
    """Mid-band power in excess of the high-frequency floor, per tile.

    Deliberately mid-band rather than high-pass: SYNTHESIS fact 7 records that
    an argmax over a purely high-frequency measure selects the noisiest frame,
    not the sharpest.  The floor subtraction removes the residual coupling.
    """
    m_mid, m_flr = masks
    if psd2.ndim == 2:
        psd2 = psd2[None]
    mid = psd2[:, m_mid].mean(axis=1)
    flr = np.median(psd2[:, m_flr], axis=1)
    return mid - flr


# ---------------------------------------------------------------------------
# Optics
# ---------------------------------------------------------------------------


def mtf_diffraction(f, f_c):
    """Incoherent diffraction MTF of a circular pupil. f, f_c same units."""
    s = np.clip(np.asarray(f, dtype=float) / float(f_c), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(s) - s * np.sqrt(np.maximum(0.0, 1.0 - s * s)))


def mtf_pixel(f_sensor):
    """Aperture MTF of a 100%-fill square photosite, f in sensor cyc/px."""
    x = np.pi * np.asarray(f_sensor, dtype=float)
    return np.where(np.abs(x) < 1e-12, 1.0, np.sin(x) / np.where(x == 0, 1.0, x))


def f_cutoff_sensor(n_eff, lambda_um=LAMBDA_UM):
    """Diffraction cutoff in sensor cyc/px for an effective f-number."""
    return PITCH_UM / (lambda_um * n_eff)


def bellows_from_fc(f_c_sensor, n_marked, lambda_um=LAMBDA_UM):
    """(1 + m/p) implied by a measured cutoff."""
    return PITCH_UM / (lambda_um * float(f_c_sensor) * float(n_marked))


def airy_fwhm_um(n_eff, lambda_um=LAMBDA_UM):
    """~1.03 * lambda * N_eff, the FWHM of the Airy PSF."""
    return 1.03 * lambda_um * n_eff


# ---------------------------------------------------------------------------
# Knee estimators
# ---------------------------------------------------------------------------

# The detection rule, fixed once and applied identically to synthetic data,
# dark frames and every real stack. Nothing below is tuned per stack.
Z_DETECT = 3.0  # sigma above the fitted floor
RUN_LEN = 3  # consecutive detected bins required
DYN_GATE = 10.0  # low-frequency power must exceed the floor by this factor
F_LO_ABS = 0.025  # sensor cyc/px; bins below this are ignored. Absolute, not a
# fraction of the lattice reach, so the three lattices are compared over the
# same physical band.
DYN_BAND = (0.025, 0.050)  # sensor cyc/px, where "is there signal" is judged


_REF_KAPPA: dict = {}


def reference_kappa(tile: int, roi_size: int, lattice: str, window: str = "hann",
                    sector: str = "iso", trials: int = 8, seed: int = 7) -> float:
    """Per-bin scatter this estimator produces on *pure white noise* for a
    given tiling geometry, measured by Monte Carlo and cached.

    The data-driven kappa (see _floor_scatter) can fall below this by chance on
    a short floor band, which would make the detection threshold too tight and
    manufacture a knee. Flooring kappa at the reference means measured
    structure can only ever make the test more conservative, never less.
    """
    key = (tile, roi_size, lattice, window, sector)
    if key in _REF_KAPPA:
        return _REF_KAPPA[key]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(trials):
        patch = rng.normal(0.0, 100.0, (roi_size, roi_size))
        f, p, c = radial_psd(welch_psd2(patch, tile, window), lattice, sector)
        top = f >= 0.8 * f[-1]
        fl = float(np.median(p[top]))
        x = (p[top] / fl - 1.0) * np.sqrt(c[top])
        vals.append(float(np.var(x)))
    k = float(np.median(vals))
    _REF_KAPPA[key] = k
    return k


def _floor_scatter(p, counts, floor, top):
    """Measured per-bin scatter of the floor, expressed as kappa in
    Var(p_i) = kappa * floor^2 / counts_i.

    kappa = 1 would hold for a single non-overlapping periodogram. Welch
    averaging over overlapping tiles reduces it; residual structure in the
    floor band inflates it. Measuring it from the data rather than assuming
    it keeps the detection threshold honest in both directions. Robust (MAD)
    so that a few contaminated bins cannot drive it.
    """
    if top.sum() < 6 or floor <= 0:
        return 1.0
    x = (p[top] / floor - 1.0) * np.sqrt(counts[top])
    mad = np.median(np.abs(x - np.median(x)))
    k = (1.4826 * mad) ** 2
    if not np.isfinite(k) or k <= 0:
        return 1.0
    return float(np.clip(k, 0.02, 50.0))


def knee_floor_crossing(f, p, counts, z=Z_DETECT, run_len=RUN_LEN,
                        dyn_gate=DYN_GATE, kappa_floor=None):
    """Assumption-light knee: the highest frequency carrying power that is
    statistically distinguishable from a flat noise floor.

    A bin is *detected* when p - N > z * sqrt(kappa) * N / sqrt(n), where n is
    the number of Fourier samples in the bin and kappa is the per-bin scatter
    measured from the floor band itself (see _floor_scatter). f_c is the upper
    edge of the highest run of `run_len` consecutive detected bins; the floor
    is then re-estimated from the bins above and the rule re-applied to
    convergence.

    C1 measures this estimator to be biased 5-23% LOW, always in the same
    direction: the diffraction MTF approaches zero as (1 - f/f_c)^1.5, so the
    last stretch below the cutoff is always buried in noise. It is therefore
    read as a **lower bound on f_c**, hence an **upper bound on (1 + m/p)**.

    Returns dict with f_c (sensor cyc/px) or None, the floor, and diagnostics.
    """
    fmax = f[-1]
    f_lo = F_LO_ABS
    top = f >= 0.8 * fmax
    floor = float(np.median(p[top])) if top.any() else float(np.median(p))
    kfl = 0.0 if kappa_floor is None else float(kappa_floor)
    kappa = max(_floor_scatter(p, counts, floor, top), kfl)
    fc = None
    for _ in range(30):
        thr = z * np.sqrt(kappa) * floor / np.sqrt(counts)
        det = ((p - floor) > thr) & (f >= f_lo)
        idx = _last_run_end(det, run_len)
        if idx is None:
            fc_new = None
        else:
            step = f[1] - f[0]
            fc_new = float(min(f[idx] + 0.5 * step, fmax))
        above = f > (fc_new if fc_new is not None else 0.0)
        if above.sum() >= 6:
            floor_new = float(np.median(p[above]))
            kappa = max(_floor_scatter(p, counts, floor_new, above), kfl)
        else:
            floor_new = floor
        if fc_new == fc and abs(floor_new - floor) < 1e-12 * max(1.0, abs(floor)):
            floor = floor_new
            break
        fc, floor = fc_new, floor_new

    lowband = (f >= DYN_BAND[0]) & (f <= DYN_BAND[1])
    dyn = float(np.median(p[lowband]) / floor) if (floor > 0 and lowband.any()) else np.inf
    slope, slope_se, ratio = floor_flatness(f, p, counts, fc, fmax)
    return {
        "f_c": fc,
        "floor": floor,
        "dynamic_range": dyn,
        "has_signal": dyn >= dyn_gate,
        "saturated": fc is not None and fc >= 0.90 * fmax,
        "floor_slope": slope,
        "floor_slope_se": slope_se,
        "floor_ratio": ratio,
        "f_max": fmax,
        "kappa": kappa,
    }


def band_excess(f, p, floor, bands=((0.10, 0.15), (0.15, 0.20),
                                    (0.20, 0.25), (0.25, 0.35))):
    """Median fractional excess over the floor in fixed sensor-frequency
    bands. Lets a light frame's excess be compared directly against a dark
    frame's, which is how FPN contamination of the knee is bounded."""
    out = []
    for lo, hi in bands:
        m = (f >= lo) & (f < hi)
        out.append(float(np.median(p[m] / floor - 1.0)) if m.any() else float("nan"))
    return out


def knee(f, p, counts, tile, roi_size, lattice, window="hann", sector="iso",
         **kw):
    """knee_floor_crossing with the per-bin scatter floored at the value this
    exact tiling geometry produces on pure white noise. This is the entry
    point every driver should use."""
    return knee_floor_crossing(
        f, p, counts,
        kappa_floor=reference_kappa(tile, roi_size, lattice, window, sector),
        **kw)


def floor_flatness(f, p, counts, fc, fmax):
    """Is the claimed noise floor actually flat?

    Reported as a description, not as a guard. C1 measured that it does *not*
    work as an out-of-band detector: when the cutoff sits above the lattice
    reach the band above the reported knee is too narrow to fit, the fallback
    band still contains falling optical signal, and the slope comes out
    strongly *negative* rather than positive. The out-of-band guard that C1
    validated at 36/36 with no false alarms is `knee_model_fit`'s own
    `above_reach` flag. Returns (slope of log p vs log f over the floor band,
    its standard error, top-half / bottom-half ratio).
    """
    band = f > (fc if fc is not None else 0.75 * fmax)
    if band.sum() < 6:
        band = f >= 0.75 * fmax
    if band.sum() < 6:
        return None, None, None
    x = np.log(f[band])
    y = np.log(p[band])
    w = counts[band]  # var(log periodogram mean) ~ 1/n
    X = np.vstack([np.ones_like(x), x]).T
    W = np.diag(w)
    try:
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
    except np.linalg.LinAlgError:
        return None, None, None
    resid = y - X @ beta
    dof = max(1, len(x) - 2)
    s2 = float((w * resid**2).sum() / dof)
    cov = s2 * np.linalg.inv(X.T @ W @ X)
    half = len(x) // 2
    ratio = float(np.median(p[band][half:]) / np.median(p[band][:half]))
    return float(beta[1]), float(np.sqrt(max(cov[1, 1], 0.0))), ratio


def _last_run_end(det: np.ndarray, run_len: int):
    """Index of the last element of the highest run of >= run_len True."""
    best = None
    run = 0
    for i, d in enumerate(det):
        if d:
            run += 1
            if run >= run_len:
                best = i
        else:
            run = 0
    return best


def knee_model_fit(f, p, counts, f_lo=F_LO_ABS, pixel_mtf=True, curvature=False):
    """Physical cross-check: fit P(f) = N + A f^-alpha MTF_d(f;f_c)^2 [MTF_pix^2].

    Uses the whole roll-off rather than only the last detectable bin, so it is
    not biased downward the way the crossing rule is. It does assume the
    diffraction MTF shape, which is the hypothesis under test — so it is a
    cross-check, never the headline.
    """
    from scipy.optimize import least_squares

    fmax = f[-1]
    m = f >= f_lo
    fx, px, cx = f[m], p[m], counts[m]
    if len(fx) < 8 or np.any(px <= 0):
        return {"f_c": None, "ok": False, "reason": "too few positive bins"}
    pix = mtf_pixel(fx) ** 2 if pixel_mtf else np.ones_like(fx)
    logf = np.log(fx / fmax)

    def model(theta):
        if curvature:
            lA, alpha, lN, fc, c2 = theta
        else:
            lA, alpha, lN, fc = theta
            c2 = 0.0
        s = np.exp(lA - alpha * logf + c2 * logf**2)
        return np.exp(lN) + s * mtf_diffraction(fx, fc) ** 2 * pix

    def resid(theta):
        mo = model(theta)
        mo = np.maximum(mo, 1e-30)
        return (np.log(mo) - np.log(px)) * np.sqrt(cx)

    p0_lA = float(np.log(px[0]))
    p0_lN = float(np.log(np.median(px[-max(4, len(px) // 10) :])))
    best = None
    for fc0 in (0.4 * fmax, 0.7 * fmax, 1.0 * fmax, 1.6 * fmax, 2.6 * fmax):
        for a0 in (1.5, 2.5, 3.5):
            th0 = [p0_lA, a0, p0_lN, fc0] + ([0.0] if curvature else [])
            lo = [p0_lA - 20, 0.0, p0_lN - 20, 0.3 * fx[0]] + ([-5.0] if curvature else [])
            hi = [p0_lA + 20, 8.0, p0_lN + 20, 6.0 * fmax] + ([5.0] if curvature else [])
            try:
                r = least_squares(resid, th0, bounds=(lo, hi), max_nfev=4000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return {"f_c": None, "ok": False, "reason": "fit failed"}
    fc = float(best.x[3])
    r = best.fun / np.sqrt(cx)  # back to unweighted log residuals
    return {
        "f_c": fc,
        "alpha": float(best.x[1]),
        "floor": float(np.exp(best.x[2])),
        "cost": float(best.cost),
        "resid_rms": float(np.sqrt(np.mean(r**2))),
        "above_reach": fc > fmax,
        "ok": True,
        "f_max": fmax,
    }


def focus_score(f, p, band=(0.05, 0.14)):
    """Mid-band excess power: a defocus-sensitive, noise-robust focus measure.

    Deliberately band-limited well below every candidate cutoff. A high-pass
    energy measure would select the *noisiest* frame (SYNTHESIS fact 7), which
    would inflate the floor and drag the knee down.
    """
    fmax = f[-1]
    top = f >= 0.8 * fmax
    floor = float(np.median(p[top])) if top.any() else 0.0
    sel = (f >= band[0]) & (f <= band[1])
    if not sel.any():
        return float("nan")
    return float(np.mean(p[sel]) - floor)


# ---------------------------------------------------------------------------
# Noise model (F-camera-lens-optics.md 2.3) — used by H4 only
# ---------------------------------------------------------------------------

_RN_E = {  # read noise in electrons, Claff photon-transfer fit
    50: 4.72, 100: 4.72, 125: 4.66, 160: 4.41, 200: 4.29, 250: 4.14,
    320: 4.20, 400: 1.47, 500: 1.41, 640: 1.39, 800: 1.39, 1000: 1.35,
    1600: 1.31, 2000: 1.33, 3200: 1.37,
}


def noise_model_var(signal_dn: float, iso: int) -> dict:
    """sigma^2(S, ISO) = g*S + (RN_e*g)^2 in DN^2.  DERIVED, not measured here."""
    g = iso / 436.8
    rn_e = _RN_E.get(iso, 4.5)
    b = (rn_e * g) ** 2
    return {"g": g, "rn_e": rn_e, "shot": g * signal_dn, "read": b,
            "var": g * signal_dn + b}


def immerkaer_sigma(patch: np.ndarray) -> float:
    """Immerkaer 3x3-Laplacian noise estimate. Structure-free upper bound.

    sigma = sqrt(pi/2) / 6 * mean|conv(I, K)| with K the 3x3 mask below, whose
    coefficients have sum-of-squares 36.
    """
    from scipy.signal import convolve2d

    k = np.array([[1.0, -2.0, 1.0], [-2.0, 4.0, -2.0], [1.0, -2.0, 1.0]])
    c = convolve2d(patch, k, mode="valid")
    return float(np.sqrt(np.pi / 2.0) * np.abs(c).mean() / 6.0)
