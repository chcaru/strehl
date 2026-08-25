"""Self-measured lateral chromatic aberration: the estimator.

This is the instrument, kept separate from the scripts that drive it so that the
commissioning suite (`c0_lateral.py`) exercises *exactly* the code path that
produces the headline number in `c1_lateral.py`. An instrument commissioned on a
different code path is not commissioned.

MODEL. Identical in form to the one `crates/strehl-core/src/optics.rs` ships, so
the two numbers are directly comparable rather than merely similar:

    d_c(u) = eps_c * u + T_c

`u` is position measured from the image centre and `d_c` is the displacement of
channel `c` relative to green. `eps_c` is dimensionless (scale minus one,
matching `SimilarityParams::g`); `u`, `d_c` and `T_c` are in **plane px** (one
plane px = one 2x2 CFA quad = 2 sensels), which is the unit `optics.rs` uses for
its `translation` field.

Three parameters per channel, not one. `optics.rs` records that forcing the
translation to zero costs 5.37x in residual rms and biases eps by 14%, so the
translation is fitted here and reported, exactly as M107 did. Whether it should
be *applied* is a separate question that `optics.rs` already answers (no).

WHY NO REGISTRATION. Phase 1 estimated inter-frame drift and applied
integer-only shifts, because drift was a contaminant. Here every comparison is
between two channels **inside a single frame**, so drift cancels identically and
no registration is performed at all. The one place sub-pixel resampling appears
is in `plant_scale`, which manufactures a synthetic dose; it never touches a
measured quantity. Project rule 6 is about not blurring the thing you measure,
and it is respected.

WHY THE CFA LATTICE MATTERS. R, G1, G2 and B sample the scene on four lattices
offset from one another by half a plane px. Correlating two planes therefore
returns the optical displacement *plus* a known constant lattice offset. The
constant lands entirely in `T` and cannot affect `eps`, which is why `eps` is
safe. `T` is only meaningful after the lattice term is removed, and the G1-vs-G2
arm -- two lattices, one wavelength, zero optical displacement by construction --
provides an absolute on-sky calibration of both the sign convention and the
scale.
"""

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from skimage.registration import phase_cross_correlation

import common

# Channels measured against G1. G2 is the null arm: same wavelength as the
# reference, so its only displacement is the lattice offset.
ARMS = ("R", "G2", "B")


def lattice_offset(ch, ref="G1"):
    """Site offset of `ch` relative to `ref`, in plane px, as (dy, dx).

    `common.SITE` stores (x, y) inside the 2x2 quad in sensel units; one plane px
    is two sensels, so a one-sensel site offset is half a plane px.
    """
    ox, oy = common.SITE[ch]
    rx, ry = common.SITE[ref]
    return ((oy - ry) / 2.0, (ox - rx) / 2.0)


def _hann2d(shape):
    return np.outer(np.hanning(shape[0]), np.hanning(shape[1]))


def subpix(ref, mov, up=100, lowpass=0.0, norm=None):
    """Sub-pixel displacement of `mov` relative to `ref`, in plane px, (dy, dx).

    Upsampled cross-correlation after mean removal and a Hann window.

    `norm` selects skimage's spectrum normalisation. It defaults to `None`
    (plain normalised cross-correlation) rather than the more usual `"phase"`,
    and that choice was measured, not assumed. Whitening the cross-power
    spectrum divides by an amplitude that is nearly zero at the top of the band
    for any well-sampled subject, which fills the high frequencies with numerical
    noise and drags the interpolated peak toward the origin. On a band-limited
    plant the measured transfer functions are:

        planted      0.05   0.10   0.25   0.50   0.75   1.00   1.30  px
        "phase"      0.60   0.60   0.60   0.94   1.09   0.99   0.92
        None         1.00   1.00   1.00   1.00   1.00   1.00   0.99

    A transfer function that depends on the magnitude of the thing being
    measured is disqualifying here specifically, because red's coefficient is an
    order of magnitude larger than blue's: whitening would read the two arms on
    two different scales and the R-vs-B comparison would be an artefact. The
    shrinkage is independent of tile size (0.588 at 128 px, 0.623 at 448 px), so
    it is intrinsic to the whitening and not a windowing effect.

    Mean removal survives from the whitened version and still does the work that
    matters cross-channel: it removes the per-channel DC, which differs between R
    and G both because the scene is coloured and because white balance is not
    applied.

    `lowpass` is a Gaussian sigma in plane px applied identically to both inputs.
    Each CFA plane samples at half the sensel rate and is therefore aliased, and
    aliased energy violates the shift theorem that sub-pixel correlation rests
    on. A symmetric filter applied identically to both windows cannot move the
    correlation peak, so this can only trade precision for bias.

    The sign convention is not asserted here. It is pinned empirically by the
    planted dose ladder in `c0_lateral.py`, which requires recovery slope 1.000.
    """
    ref = np.asarray(ref, np.float64)
    mov = np.asarray(mov, np.float64)
    if lowpass > 0:
        ref = gaussian_filter(ref, lowpass, mode="nearest")
        mov = gaussian_filter(mov, lowpass, mode="nearest")
    w = _hann2d(ref.shape)
    a = (ref - ref.mean()) * w
    b = (mov - mov.mean()) * w
    sh, _err, _ph = phase_cross_correlation(
        a, b, upsample_factor=up, normalization=norm
    )
    return float(sh[0]), float(sh[1])


def tile_structure(plane, y, x, tile):
    """Mean Sobel gradient energy of one tile of the reference (green) plane.

    This is the gate. It is computed on **green only** -- the reference channel --
    so it carries no information about any chromatic displacement and cannot
    select for or against the effect being measured. Selection on an input, not
    on an outcome.
    """
    return float(np.mean(common.grad_energy(plane[y:y + tile, x:x + tile])))


def tile_corners(shape, tile, margin):
    """Non-overlapping tile origins covering the plane.

    Non-overlapping matters: Phase 1 established that the independent statistical
    unit is the tile, and overlapping tiles would share structure and make the
    bootstrap understate the uncertainty.
    """
    h, w = shape
    ys = list(range(margin, h - margin - tile + 1, tile))
    xs = list(range(margin, w - margin - tile + 1, tile))
    return [(y, x) for y in ys for x in xs]


def field_position(y, x, tile, ch, sensel_shape):
    """Tile-centre position from the image centre, in plane px, as (uy, ux).

    Worked in sensel coordinates and halved, because the four planes' sample
    sites sit at different sensel offsets and the resulting quarter-plane-px
    differences are the same order as the translation term being fitted.
    """
    hs, ws = sensel_shape
    ox, oy = common.SITE[ch]
    cy = (hs - 1) / 2.0
    cx = (ws - 1) / 2.0
    py = 2.0 * (y + (tile - 1) / 2.0) + oy
    px = 2.0 * (x + (tile - 1) / 2.0) + ox
    return ((py - cy) / 2.0, (px - cx) / 2.0)


def fit_model(u, d, radial_only=False, robust=False, n_irls=12):
    """Least-squares fit of d = eps*u + T over N tiles.

    Both components of every tile enter as separate rows, so the y and x
    equations share one `eps` -- which is what makes it a *radial* scale rather
    than two independent axis gains.

    `robust=True` runs IRLS with Tukey's biweight (c = 4.685 * MAD-sigma), which
    is a second line of defence behind the structure gate rather than a
    substitute for it: a phase-correlation failure can land tens of px away, and
    no amount of downweighting rescues a fit whose majority is garbage. Both
    forms are reported side by side wherever this is used (rule 3).
    """
    u = np.asarray(u, float)
    d = np.asarray(d, float)
    n = len(u)
    b = np.concatenate([d[:, 0], d[:, 1]])
    if radial_only:
        A = np.concatenate([u[:, 0], u[:, 1]])[:, None]
    else:
        A = np.zeros((2 * n, 3))
        A[:n, 0] = u[:, 0]
        A[:n, 1] = 1.0
        A[n:, 0] = u[:, 1]
        A[n:, 2] = 1.0
    w = np.ones(2 * n)
    for _ in range(n_irls if robust else 1):
        sw = np.sqrt(w)[:, None]
        sol, *_ = np.linalg.lstsq(A * sw, b * np.sqrt(w), rcond=None)
        resid = b - A @ sol
        if not robust:
            break
        sigma = 1.4826 * np.median(np.abs(resid - np.median(resid)))
        if sigma <= 0:
            break
        t = resid / (4.685 * sigma)
        w = np.where(np.abs(t) < 1.0, (1.0 - t * t) ** 2, 0.0)
        if w.sum() < 6:
            break
    resid = b - A @ sol
    keep = w > 0
    ss_res = float((resid[keep] ** 2).sum())
    bb = b[keep]
    ss_tot = float(((bb - bb.mean()) ** 2).sum())
    out = {
        "eps": float(sol[0]),
        "ty": 0.0 if radial_only else float(sol[1]),
        "tx": 0.0 if radial_only else float(sol[2]),
        "r2": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
        "rms": float(np.sqrt(ss_res / max(int(keep.sum()), 1))),
        "n_tiles": int(n),
        "n_kept_rows": int(keep.sum()),
    }
    return out


def synth_bandlimited(shape, sigma=2.0, seed=7):
    """A genuinely band-limited random field, for testing the estimator alone.

    A CFA plane is aliased, so cubic-spline resampling of one does not produce an
    exact sub-pixel translation -- the *plant* is then inaccurate, and a failed
    recovery cannot be attributed to the estimator. Blurring white noise to
    sigma >= 2 px puts essentially no energy near Nyquist, so the spline
    interpolant is the band-limited interpolant to well under the tolerance here
    and the planted value is genuine ground truth.
    """
    rng = np.random.default_rng(seed)
    f = gaussian_filter(rng.standard_normal(shape), sigma, mode="wrap")
    return (f / f.std() * 500.0 + 2000.0)


def boot_fit(u, d, radial_only=False, robust=False, n_boot=2000, seed=20260607):
    """Bootstrap over tiles. Returns the point fit plus percentile CIs."""
    rng = np.random.default_rng(seed)
    u = np.asarray(u, float)
    d = np.asarray(d, float)
    n = len(u)
    point = fit_model(u, d, radial_only, robust)
    eps = np.empty(n_boot)
    ty = np.empty(n_boot)
    tx = np.empty(n_boot)
    for k in range(n_boot):
        idx = rng.integers(0, n, n)
        f = fit_model(u[idx], d[idx], radial_only, robust)
        eps[k] = f["eps"]
        ty[k] = f["ty"]
        tx[k] = f["tx"]
    point["eps_lo"], point["eps_hi"] = (
        float(np.percentile(eps, 2.5)),
        float(np.percentile(eps, 97.5)),
    )
    point["eps_se"] = float(np.std(eps, ddof=1))
    point["ty_se"] = float(np.std(ty, ddof=1))
    point["tx_se"] = float(np.std(tx, ddof=1))
    return point


def perm_p(u, d, radial_only=False, robust=False, n_perm=2000, seed=99):
    """Permutation p for eps: shuffle which displacement belongs to which radius.

    Destroys the radius-displacement pairing while preserving both marginals, so
    a scene whose displacements are merely large cannot fake a radial trend.
    """
    rng = np.random.default_rng(seed)
    u = np.asarray(u, float)
    d = np.asarray(d, float)
    obs = abs(fit_model(u, d, radial_only, robust)["eps"])
    hits = 0
    for _ in range(n_perm):
        idx = rng.permutation(len(u))
        if abs(fit_model(u, d[idx], radial_only, robust)["eps"]) >= obs:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def plant_scale(plane, eps, ty=0.0, tx=0.0, centre=None):
    """Magnify `plane` by (1 + eps) about `centre`, then translate by (ty, tx).

    Used only to manufacture a synthetic dose for commissioning. Cubic spline
    resampling; the blur it adds is symmetric and so cannot move a correlation
    peak, and the dose ladder's required recovery slope of 1.000 is what actually
    proves that.
    """
    h, w = plane.shape
    if centre is None:
        centre = ((h - 1) / 2.0, (w - 1) / 2.0)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    sy = centre[0] + (yy - centre[0] - ty) / (1.0 + eps)
    sx = centre[1] + (xx - centre[1] - tx) / (1.0 + eps)
    return map_coordinates(
        np.asarray(plane, np.float64), [sy, sx], order=3, mode="reflect"
    )


def measure_frame(planes, tiles, tile, arms=ARMS, ref="G1", lowpass=0.0,
                  norm=None):
    """Raw correlation displacements for one frame. Lattice NOT yet removed.

    Also returns the green structure metric per tile, which is the gate.
    """
    out = {}
    struct = {}
    g = planes[ref]
    for (y, x) in tiles:
        struct[(y, x)] = tile_structure(g, y, x, tile)
        r = g[y:y + tile, x:x + tile]
        for ch in arms:
            m = planes[ch][y:y + tile, x:x + tile]
            out[(y, x, ch)] = subpix(r, m, lowpass=lowpass, norm=norm)
    return out, struct


def rows_for(arm, disp, tiles, tile, sensel_shape, ref="G1", struct=None,
             gate=0.0):
    """Assemble (u, d) fit rows for one arm, with the lattice offset removed.

    `disp[(y, x, arm)]` is the raw correlation output. The optical displacement
    is that minus the constant lattice term; the constant is degenerate with `T`
    and so affects only `T`, never `eps`.

    `gate` drops tiles whose green gradient energy is below the threshold. The
    threshold is never chosen by a rule of thumb -- project rule 5 forbids that
    and five such rules have already been killed here -- it is swept as a ladder
    and the answer is required to be flat across it.
    """
    ly, lx = lattice_offset(arm, ref)
    u, d, s = [], [], []
    for (y, x) in tiles:
        key = (y, x, arm)
        if key not in disp:
            continue
        if struct is not None and struct[(y, x)] < gate:
            continue
        dy, dx = disp[key]
        u.append(field_position(y, x, tile, ref, sensel_shape))
        d.append((dy - ly, dx - lx))
        s.append(0.0 if struct is None else struct[(y, x)])
    return np.array(u, float), np.array(d, float), np.array(s, float)
