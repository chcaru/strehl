"""M88 shared library: RAW loading, green sublattices, slanted-edge SFR.

Rule 32: `raw_image_visible` is a LibRaw view. Every read here copies inside
the `with` block on the same line as the slice.

Rule 7: only the 7032x4688 active area is ever touched.

Geometry conventions used throughout
------------------------------------
* Sensor pixel pitch `PITCH_UM` = 5.12 um, RGGB.
* `raw[r, c]` for r,c in the ACTIVE area. Colour of (r,c) is
  R at (even, even), G1 at (even, odd), G2 at (odd, even), B at (odd, odd).
* A green sublattice is a set of scattered sample POSITIONS in sensor pixel
  units. We never resample it onto its own grid; the slanted-edge estimator
  consumes (x, y, value) triples in SENSOR pixel coordinates, so the
  10.24 um sublattice pitch never enters the frequency axis.
* Frequency axis is cycles/mm at the SENSOR.
"""

from __future__ import annotations

import numpy as np

PITCH_UM = 5.12
PITCH_MM = PITCH_UM * 1e-3
ACTIVE_H = 4688
ACTIVE_W = 7032
BLACK_LEVEL = 512
SENSOR_NYQUIST_CYMM = 1.0 / (2.0 * PITCH_MM)  # 97.65625
CFA_PLANE_NYQUIST_CYMM = SENSOR_NYQUIST_CYMM / 2.0  # 48.828125


# ---------------------------------------------------------------- RAW loading

def load_active(path):
    """Return the black-subtracted active area as float32, shape (4688, 7032)."""
    import rawpy

    with rawpy.imread(str(path)) as raw:
        # Rule 32: copy inside the with, on the same line as the slice.
        vis = raw.raw_image_visible[:ACTIVE_H, :ACTIVE_W].astype(np.float32)
    return vis - BLACK_LEVEL


def green_sites(active, which="G1"):
    """Return (values, x_px, y_px) for one green sublattice, in SENSOR px units.

    G1 = (even row, odd col); G2 = (odd row, even col).  Coordinates are the
    sensor-pixel indices of the sites, so the caller works in a single global
    coordinate system regardless of which sublattice is used.
    """
    if which == "G1":
        r0, c0 = 0, 1
    elif which == "G2":
        r0, c0 = 1, 0
    else:
        raise ValueError(which)
    sub = active[r0::2, c0::2]
    ny, nx = sub.shape
    ys = (np.arange(ny) * 2 + r0).astype(np.float64)
    xs = (np.arange(nx) * 2 + c0).astype(np.float64)
    return sub, xs, ys


# ------------------------------------------------------- diffraction MTF model

def mtf_diffraction(f_cymm, fc_cymm):
    """Incoherent circular-aperture MTF.  Exactly zero for f >= fc."""
    s = np.asarray(f_cymm, dtype=np.float64) / float(fc_cymm)
    out = np.zeros_like(s)
    m = s < 1.0
    sm = s[m]
    out[m] = (2.0 / np.pi) * (np.arccos(sm) - sm * np.sqrt(1.0 - sm * sm))
    return out


def mtf_pixel(f_cymm, aperture_um=PITCH_UM):
    """Square photosite aperture MTF = |sinc(f * a)| with a in mm."""
    a_mm = aperture_um * 1e-3
    x = np.pi * np.asarray(f_cymm, dtype=np.float64) * a_mm
    return np.where(np.abs(x) < 1e-12, 1.0, np.sin(x) / np.where(x == 0, 1.0, x))


def mtf_gauss(f_cymm, sigma_um):
    """Gaussian blur of sd sigma (um) -> exp(-2 pi^2 sigma^2 f^2)."""
    s_mm = sigma_um * 1e-3
    f = np.asarray(f_cymm, dtype=np.float64)
    return np.exp(-2.0 * np.pi**2 * s_mm**2 * f**2)


# -------------------------------------------------------------- slanted edge

class EdgeFitError(RuntimeError):
    pass


def _robust_line_fit(t, d, n_iter=5):
    """Huber-ish IRLS fit d = a*t + b.  Returns (a, b, resid_sd)."""
    t = np.asarray(t, float)
    d = np.asarray(d, float)
    w = np.ones_like(d)
    a = b = 0.0
    for _ in range(n_iter):
        W = np.diag(w) if False else w
        S0 = W.sum()
        S1 = (W * t).sum()
        S2 = (W * t * t).sum()
        T0 = (W * d).sum()
        T1 = (W * d * t).sum()
        det = S0 * S2 - S1 * S1
        if abs(det) < 1e-12:
            raise EdgeFitError("degenerate line fit")
        a = (S0 * T1 - S1 * T0) / det
        b = (S2 * T0 - S1 * T1) / det
        r = d - (a * t + b)
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-9
        k = 1.5 * s
        w = np.where(np.abs(r) <= k, 1.0, k / np.abs(r))
    r = d - (a * t + b)
    s = 1.4826 * np.median(np.abs(r - np.median(r)))
    return a, b, s


def fit_edge_line(sub, xs, ys, axis="vertical", smooth=5, half_win=6,
                  n_refine=3):
    """Locate a near-straight edge in a sublattice patch.

    axis='vertical'  : edge runs roughly along +y, crossing varies with row.
    axis='horizontal': edge runs roughly along +x, crossing varies with column.

    Two stages, because a centroid taken over a whole line is dominated by
    far-field noise and biases the slope toward zero (measured: 1.21 deg
    recovered from a planted 1.98 deg at realistic SNR).  Stage 1 uses the
    argmax of a smoothed gradient; stage 2 re-centroids inside +/-half_win
    samples of the current line and re-fits.

    Returns dict with the unit normal (nx, ny) and a point (x0, y0) on the
    line, all in SENSOR pixel coordinates, plus the fit residual sd.
    """
    if axis == "horizontal":
        res = fit_edge_line(sub.T, ys, xs, axis="vertical", smooth=smooth,
                            half_win=half_win, n_refine=n_refine)
        return {
            "nx": res["ny"],
            "ny": res["nx"],
            "x0": res["y0"],
            "y0": res["x0"],
            "resid_sd_px": res["resid_sd_px"],
            "angle_deg": res["angle_deg"],
            "n_rows_used": res["n_rows_used"],
            "contrast": res["contrast"],
            "lo_dn": res["lo_dn"],
            "hi_dn": res["hi_dn"],
        }

    ny, nx = sub.shape
    if nx < 8 or ny < 8:
        raise EdgeFitError("patch too small")
    a2 = sub.astype(np.float64)
    if smooth > 1:
        k = np.ones(smooth) / smooth
        a2 = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"),
                                 1, a2)
    g = np.abs(np.diff(a2, axis=1))
    xm = 0.5 * (xs[:-1] + xs[1:])
    # stage 1: argmax of the smoothed gradient, robust to far-field noise
    guard = max(smooth, 2)
    gi = g[:, guard:g.shape[1] - guard]
    if gi.shape[1] < 4:
        raise EdgeFitError("patch too narrow")
    cen = xm[guard + np.argmax(gi, axis=1)]
    a, b, sd = _robust_line_fit(ys, cen)
    # stage 2: centroid inside a window around the current line
    for _ in range(n_refine):
        pred = a * ys + b
        j = np.searchsorted(xm, pred)
        lo = np.clip(j - half_win, 0, len(xm) - 1)
        hi = np.clip(j + half_win + 1, 1, len(xm))
        cen2 = np.full(ny, np.nan)
        for i in range(ny):
            if hi[i] - lo[i] < 3:
                continue
            wv = g[i, lo[i]:hi[i]]
            s = wv.sum()
            if s <= 0:
                continue
            cen2[i] = float((wv * xm[lo[i]:hi[i]]).sum() / s)
        ok = np.isfinite(cen2)
        if ok.sum() < 8:
            raise EdgeFitError("refine lost the edge")
        a, b, sd = _robust_line_fit(ys[ok], cen2[ok])
    nrm = np.hypot(1.0, a)
    nxu, nyu = 1.0 / nrm, -a / nrm
    ymid = float(np.median(ys))
    # contrast: robust levels well clear of the transition on each side
    pred = a * ys + b
    gap = 8.0 * float(np.median(np.diff(xs)))
    left, right = [], []
    for i in range(ny):
        ml = xs < (pred[i] - gap)
        mr = xs > (pred[i] + gap)
        if ml.sum() > 3:
            left.append(np.median(sub[i, ml]))
        if mr.sum() > 3:
            right.append(np.median(sub[i, mr]))
    lo_dn = float(np.median(left)) if left else np.nan
    hi_dn = float(np.median(right)) if right else np.nan
    return {
        "nx": nxu,
        "ny": nyu,
        "x0": a * ymid + b,
        "y0": ymid,
        "resid_sd_px": float(sd),
        "angle_deg": float(np.degrees(np.arctan(a))),
        "n_rows_used": int(ok.sum()),
        "contrast": float(abs(hi_dn - lo_dn)),
        "lo_dn": min(lo_dn, hi_dn),
        "hi_dn": max(lo_dn, hi_dn),
    }


def esf_from_sites(values, X, Y, line, bin_um, half_width_um):
    """Project scattered samples onto the edge normal and bin the ESF.

    values, X, Y : 1-D arrays of sample value and SENSOR pixel coordinates.
    line         : dict from fit_edge_line.
    Returns (centres_um, mean, count).
    """
    d_px = (X - line["x0"]) * line["nx"] + (Y - line["y0"]) * line["ny"]
    d_um = d_px * PITCH_UM
    m = np.abs(d_um) <= half_width_um
    d_um = d_um[m]
    v = np.asarray(values, float)[m]
    nb = int(round(2 * half_width_um / bin_um))
    edges = np.linspace(-half_width_um, half_width_um, nb + 1)
    idx = np.clip(np.digitize(d_um, edges) - 1, 0, nb - 1)
    cnt = np.bincount(idx, minlength=nb).astype(np.float64)
    tot = np.bincount(idx, weights=v, minlength=nb)
    centres = 0.5 * (edges[:-1] + edges[1:])
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    return centres, mean, cnt


def sfr_from_esf(centres_um, esf, taper_frac=0.25):
    """ESF -> LSF -> MTF, with the finite-difference and bin-box transfer
    functions divided out analytically.

    Returns (freq_cymm, mtf) with mtf[0] == 1.
    """
    d = float(centres_um[1] - centres_um[0])
    e = np.asarray(esf, float)
    if not np.all(np.isfinite(e)):
        raise EdgeFitError("ESF has empty bins")
    # centred difference over one bin -> LSF at bin centres
    lsf = np.empty_like(e)
    lsf[1:-1] = 0.5 * (e[2:] - e[:-2])
    lsf[0] = e[1] - e[0]
    lsf[-1] = e[-1] - e[-2]
    # remove any DC pedestal from the wings, then centre on the LSF centroid
    lsf = lsf - 0.5 * (np.median(lsf[:8]) + np.median(lsf[-8:]))
    n = len(lsf)
    # Tukey taper suppresses truncation ringing without touching the core
    w = _tukey(n, taper_frac)
    lsfw = lsf * w
    F = np.fft.rfft(lsfw)
    f_cyc_per_um = np.fft.rfftfreq(n, d=d)
    f_cymm = f_cyc_per_um * 1000.0
    mag = np.abs(F)
    mag = mag / mag[0]
    # centred difference [1,0,-1]/2 over spacing d has |H| = |sin(2 pi f d)|/2... 
    # careful: our operator is (e[i+1]-e[i-1])/2 which is sin(2*pi*f*d) in
    # magnitude relative to the ideal derivative 2*pi*f*d.
    x = 2.0 * np.pi * f_cyc_per_um * d
    h_diff = np.where(np.abs(x) < 1e-12, 1.0, np.sin(x) / np.where(x == 0, 1.0, x))
    # bin box of width d
    xb = np.pi * f_cyc_per_um * d
    h_bin = np.where(np.abs(xb) < 1e-12, 1.0, np.sin(xb) / np.where(xb == 0, 1.0, xb))
    corr = h_diff * h_bin
    mtf = np.where(np.abs(corr) > 1e-3, mag / np.where(corr == 0, 1.0, corr), np.nan)
    return f_cymm, mtf


def _tukey(n, alpha):
    if alpha <= 0:
        return np.ones(n)
    w = np.ones(n)
    m = int(np.floor(alpha * (n - 1) / 2.0)) + 1
    k = np.arange(m)
    ramp = 0.5 * (1 + np.cos(np.pi * (2 * k / (alpha * (n - 1)) - 1)))
    w[:m] = ramp
    w[n - m:] = ramp[::-1]
    return w


def sfr_from_sites(values, X, Y, line, bin_um, half_width_um, taper_frac=0.25,
                   detrend_iters=2):
    """Scattered samples -> ESF -> MTF, with an along-edge linear detrend.

    The detrend removes illumination gradients running ALONG the edge, which
    otherwise inflate the ESF bin variance and tilt the wings.  It cannot
    remove anything that varies with `d`, so it cannot manufacture an edge.
    """
    v = np.asarray(values, float).copy()
    d_px = (X - line["x0"]) * line["nx"] + (Y - line["y0"]) * line["ny"]
    t_px = -(X - line["x0"]) * line["ny"] + (Y - line["y0"]) * line["nx"]
    for _ in range(max(0, detrend_iters)):
        centres, esf, cnt = esf_from_sites(v, X, Y, line, bin_um, half_width_um)
        m = np.isfinite(esf)
        if m.sum() < 8:
            break
        pred = np.interp(d_px * PITCH_UM, centres[m], esf[m],
                         left=np.nan, right=np.nan)
        r = v - pred
        ok = np.isfinite(r) & (np.abs(d_px * PITCH_UM) <= half_width_um)
        if ok.sum() < 32:
            break
        A = np.column_stack([np.ones(ok.sum()), t_px[ok]])
        coef, *_ = np.linalg.lstsq(A, r[ok], rcond=None)
        v = v - coef[1] * t_px
    centres, esf, cnt = esf_from_sites(v, X, Y, line, bin_um, half_width_um)
    if np.any(cnt == 0):
        raise EdgeFitError(f"{int((cnt == 0).sum())} empty ESF bins")
    f, mtf = sfr_from_esf(centres, esf, taper_frac)
    return {
        "centres_um": centres,
        "esf": esf,
        "count": cnt,
        "freq_cymm": f,
        "mtf": mtf,
        "contrast": float(np.nanmax(esf) - np.nanmin(esf)),
        "d_px": d_px,
        "t_px": t_px,
        "values": v,
    }


def measure_sfr(active, roi, which_green, axis, bin_um, half_width_um,
                taper_frac=0.25, n_segments=1, detrend_iters=2):
    """Full pipeline on one ROI of one sublattice.

    roi = (r0, c0, h, w) in SENSOR pixel coordinates.
    If n_segments > 1 the edge is also measured on that many disjoint
    along-edge segments, giving an empirical between-segment spread.
    """
    r0, c0, h, w = roi
    patch = active[r0:r0 + h, c0:c0 + w]
    sub, xs, ys = green_sites(patch, which_green)
    xs = xs + c0
    ys = ys + r0
    line = fit_edge_line(sub, xs, ys, axis=axis)
    XX, YY = np.meshgrid(xs, ys)
    res = sfr_from_sites(sub.ravel(), XX.ravel(), YY.ravel(), line,
                         bin_um, half_width_um, taper_frac, detrend_iters)
    res["line"] = line
    if n_segments > 1:
        t = res["t_px"]
        qs = np.quantile(t, np.linspace(0, 1, n_segments + 1))
        segs = []
        for k in range(n_segments):
            m = (t >= qs[k]) & (t <= qs[k + 1])
            try:
                s = sfr_from_sites(sub.ravel()[m], XX.ravel()[m], YY.ravel()[m],
                                   line, bin_um, half_width_um, taper_frac,
                                   detrend_iters)
                segs.append(s["mtf"])
            except EdgeFitError:
                segs.append(None)
        res["segment_mtf"] = segs
    return res

# ------------------------------------------------------ analytic step response

def esf_diffraction(x_um, fc_cymm, sigma_um=0.0, n_quad=20001):
    """Exact step response of (diffraction at fc) x (Gaussian sigma).

    ESF(x) = 1/2 + (1/pi) * int_0^inf H(f) sin(2 pi f x) / f df
    """
    x_mm = np.asarray(x_um, float) * 1e-3
    f = np.linspace(0.0, float(fc_cymm), n_quad)[1:]
    H = mtf_diffraction(f, fc_cymm)
    if sigma_um > 0:
        H = H * mtf_gauss(f, sigma_um)
    integ = H / f
    out = np.empty_like(x_mm)
    for i, xv in enumerate(np.ravel(x_mm)):
        out.flat[i] = np.trapezoid(integ * np.sin(2 * np.pi * f * xv), f)
    return 0.5 + out / np.pi


def synth_edge_frame(h_px, w_px, fc_cymm, angle_deg, lo_dn, hi_dn,
                     sigma_um=0.0, sub=4, x0_px=None, y0_px=None,
                     axis="horizontal"):
    """Pixel-integrated synthetic slanted edge on the SENSOR grid.

    axis='horizontal' -> edge runs roughly along +x, normal roughly along +y.
    Returns a (h_px, w_px) float array in DN, before noise.
    """
    a = np.radians(angle_deg)
    if axis == "horizontal":
        nx, ny = -np.sin(a), np.cos(a)
    else:
        nx, ny = np.cos(a), np.sin(a)
    x0 = 0.5 * w_px if x0_px is None else x0_px
    y0 = 0.5 * h_px if y0_px is None else y0_px
    off = (np.arange(sub) + 0.5) / sub - 0.5
    ys = np.arange(h_px)[:, None, None, None] + off[None, None, :, None]
    xs = np.arange(w_px)[None, :, None, None] + off[None, None, None, :]
    d_px = (xs - x0) * nx + (ys - y0) * ny
    d_um = d_px * PITCH_UM
    lut_x = np.linspace(d_um.min() - 1, d_um.max() + 1, 4001)
    lut_y = esf_diffraction(lut_x, fc_cymm, sigma_um)
    e = np.interp(d_um, lut_x, lut_y)
    img = e.mean(axis=(2, 3))
    return lo_dn + (hi_dn - lo_dn) * img


def add_sensor_noise(img_dn, gain_dn_per_e, read_noise_e, rng):
    """Poisson photon noise + Gaussian read noise, in DN above black."""
    e = np.maximum(img_dn, 0.0) / gain_dn_per_e
    out = rng.poisson(e).astype(np.float64) * gain_dn_per_e
    out += rng.normal(0.0, read_noise_e * gain_dn_per_e, size=out.shape)
    return out


# --------------------------------------------------------------- fc estimators

def fit_fc(freq_cymm, mtf, f_lo, f_hi, fc_init=90.0, sigma_init=1.0,
           pixel_aperture_um=PITCH_UM, weights=None, free_amp=True):
    """E1: least-squares fit of A x diffraction x pixel x Gaussian.

    `A` absorbs the residual ESF-truncation scale error, which the positive
    control measures at ~1.6% and nearly flat in f.  Returns dict.
    """
    from scipy.optimize import least_squares

    m = (freq_cymm >= f_lo) & (freq_cymm <= f_hi) & np.isfinite(mtf)
    f = freq_cymm[m]
    y = mtf[m]
    w = np.ones_like(y) if weights is None else np.asarray(weights)[m]

    def model(p):
        fc, sig = p[0], p[1]
        amp = p[2] if free_amp else 1.0
        return (amp * mtf_diffraction(f, fc) * mtf_pixel(f, pixel_aperture_um)
                * mtf_gauss(f, sig))

    def resid(p):
        return (model(p) - y) * w

    p0 = [fc_init, sigma_init] + ([1.0] if free_amp else [])
    lo = [20.0, 0.0] + ([0.5] if free_amp else [])
    hi = [400.0, 30.0] + ([2.0] if free_amp else [])
    r = least_squares(resid, p0, bounds=(lo, hi), method="trf")
    out = {"fc_cymm": float(r.x[0]), "sigma_um": float(r.x[1]),
           "amp": float(r.x[2]) if free_amp else 1.0,
           "cost": float(r.cost), "n_pts": int(m.sum()),
           "rms_resid": float(np.sqrt(np.mean(resid(r.x) ** 2))),
           "success": bool(r.success)}
    return out


def noise_floor_mtf(freq_cymm, mtf, f_band=(150.0, 190.0)):
    m = (freq_cymm >= f_band[0]) & (freq_cymm <= f_band[1]) & np.isfinite(mtf)
    if m.sum() < 3:
        return np.nan
    return float(np.sqrt(np.mean(mtf[m] ** 2)))


def signal_bound(freq_cymm, mtf, floor, z=3.0, run_len=3, f_min=20.0,
                 f_max=190.0):
    """E2: highest frequency with `run_len` consecutive bins above z*floor.

    A LOWER BOUND on the cutoff (trap 3): where the curve meets the noise.
    """
    m = (freq_cymm >= f_min) & (freq_cymm <= f_max) & np.isfinite(mtf)
    f = freq_cymm[m]
    y = mtf[m]
    thr = z * floor
    best = np.nan
    above = y > thr
    for i in range(len(f) - run_len + 1):
        if above[i:i + run_len].all():
            best = f[i + run_len - 1]
    return float(best)

def esf_defocus(x_um, fc_cymm, disc_diam_um=0.0, n_quad=20001):
    """Step response of (diffraction at fc) x (uniform disc of given diameter).

    A geometric defocus blur is a DISC, not a Gaussian; this is the realistic
    mis-specification for the fit, whose model carries a Gaussian.
    """
    from scipy.special import j1

    x_mm = np.asarray(x_um, float) * 1e-3
    f = np.linspace(0.0, float(fc_cymm), n_quad)[1:]
    H = mtf_diffraction(f, fc_cymm)
    if disc_diam_um > 0:
        a = np.pi * f * disc_diam_um * 1e-3
        H = H * np.where(a < 1e-9, 1.0, 2.0 * j1(np.where(a == 0, 1.0, a)) / np.where(a == 0, 1.0, a))
    integ = H / f
    out = np.empty(np.size(x_mm))
    for i, xv in enumerate(np.ravel(x_mm)):
        out[i] = np.trapezoid(integ * np.sin(2 * np.pi * f * xv), f)
    return (0.5 + out / np.pi).reshape(np.shape(x_mm))


def synth_edge_frame2(h_px, w_px, fc_cymm, angle_deg, lo_dn, hi_dn,
                      sigma_um=0.0, disc_um=0.0, sub=6, x0_px=None,
                      y0_px=None, axis="horizontal"):
    """As synth_edge_frame but supports a defocus DISC as the extra blur."""
    a = np.radians(angle_deg)
    if axis == "horizontal":
        nx, ny = -np.sin(a), np.cos(a)
    else:
        nx, ny = np.cos(a), np.sin(a)
    x0 = 0.5 * w_px if x0_px is None else x0_px
    y0 = 0.5 * h_px if y0_px is None else y0_px
    off = (np.arange(sub) + 0.5) / sub - 0.5
    ys = np.arange(h_px)[:, None, None, None] + off[None, None, :, None]
    xs = np.arange(w_px)[None, :, None, None] + off[None, None, None, :]
    d_um = ((xs - x0) * nx + (ys - y0) * ny) * PITCH_UM
    lut_x = np.linspace(d_um.min() - 1, d_um.max() + 1, 4001)
    if disc_um > 0:
        lut_y = esf_defocus(lut_x, fc_cymm, disc_um)
    else:
        lut_y = esf_diffraction(lut_x, fc_cymm, sigma_um)
    e = np.interp(d_um, lut_x, lut_y)
    return lo_dn + (hi_dn - lo_dn) * e.mean(axis=(2, 3))

def corr_curve(freq_cymm, bin_um):
    """The centred-difference x bin-box transfer function that sfr_from_esf
    divides out.  White noise in the ESF bins therefore appears in the MTF as
    a floor proportional to 1/corr, not as a constant."""
    f = np.asarray(freq_cymm, float) / 1000.0
    x = 2.0 * np.pi * f * bin_um
    h_diff = np.where(np.abs(x) < 1e-12, 1.0, np.sin(x) / np.where(x == 0, 1.0, x))
    xb = np.pi * f * bin_um
    h_bin = np.where(np.abs(xb) < 1e-12, 1.0, np.sin(xb) / np.where(xb == 0, 1.0, xb))
    return h_diff * h_bin


def noise_floor_curve(freq_cymm, mtf, bin_um, f_band=(250.0, 380.0)):
    """Frequency-dependent 1-sigma noise floor of the MTF estimate.

    White ESF-bin noise gives a flat |FFT| magnitude; the MTF divides that by
    corr(f), so the floor rises as 1/corr(f).  Estimate the flat pre-division
    level in a band chosen above any possible optical signal, then map it back
    to every frequency.  Returns (floor_array, flat_level).
    """
    f = np.asarray(freq_cymm, float)
    c = corr_curve(f, bin_um)
    m = (f >= f_band[0]) & (f <= f_band[1]) & np.isfinite(mtf) & np.isfinite(c)
    if m.sum() < 8:
        raise EdgeFitError("noise band too sparse")
    flat = float(np.sqrt(np.mean((np.asarray(mtf)[m] * c[m]) ** 2)))
    return flat / np.abs(c), flat


def signal_bound_curve(freq_cymm, mtf, floor_arr, z=3.0, run_len=3,
                       f_min=20.0):
    """Highest frequency with run_len consecutive bins above z*floor(f).

    This is a LOWER BOUND on the cutoff (trap 3): it is where signal power
    falls under the noise, which depends on exposure and averaging, not where
    the optics stop.
    """
    f = np.asarray(freq_cymm, float)
    m = np.asarray(mtf, float)
    ok = np.isfinite(m) & np.isfinite(floor_arr) & (f >= f_min)
    hit = ok & (m > z * floor_arr)
    best = np.nan
    for i in range(len(f) - run_len + 1):
        if hit[i:i + run_len].all():
            best = f[i + run_len - 1]
    return best

def deramp_esf(centres_um, esf, core_um=48.0):
    """Remove a DIFFERENT linear ramp from each ESF wing.

    Real subjects are not flat either side of a silhouette: measured on
    119MSDCF ROI A1, the dark wing falls 527 DN over 154 um while the bright
    wing climbs 910 DN over 169 um, 32% of the edge contrast.  A single
    constant pedestal, subtracted from both sides at once, leaves a
    step-shaped baseline in the LSF and dumps spurious low-frequency energy
    into mag[0], which deflates the entire normalised MTF.

    Subtracting slope_L*d for d<0 and slope_R*d for d>0 removes both ramps,
    preserves the step height, and is continuous at d=0 because both
    corrections vanish there.  It cannot create a transition: it is odd-free
    and linear on each side.
    """
    c = np.asarray(centres_um, float)
    e = np.asarray(esf, float).copy()
    out = {}
    for tag, m in (("L", c < -core_um), ("R", c > core_um)):
        if m.sum() < 8:
            out[tag] = 0.0
            continue
        A = np.column_stack([np.ones(m.sum()), c[m]])
        coef, *_ = np.linalg.lstsq(A, e[m], rcond=None)
        out[tag] = float(coef[1])
    e = e - np.where(c < 0, out["L"] * c, out["R"] * c)
    return e, out["L"], out["R"]


def sfr_from_sites2(values, X, Y, line, bin_um, half_width_um, taper_frac=0.25,
                    detrend_iters=2, core_um=48.0, deramp=True):
    """sfr_from_sites plus the per-wing ESF deramp of deramp_esf."""
    r = sfr_from_sites(values, X, Y, line, bin_um, half_width_um, taper_frac,
                       detrend_iters)
    if not deramp:
        r["slope_l"] = 0.0
        r["slope_r"] = 0.0
        return r
    e2, sl, sr = deramp_esf(r["centres_um"], r["esf"], core_um)
    f, mtf = sfr_from_esf(r["centres_um"], e2, taper_frac)
    r = dict(r)
    r["esf_raw"] = r["esf"]
    r["esf"] = e2
    r["freq_cymm"] = f
    r["mtf"] = mtf
    r["slope_l"] = sl
    r["slope_r"] = sr
    r["contrast"] = float(np.nanmax(e2) - np.nanmin(e2))
    return r
