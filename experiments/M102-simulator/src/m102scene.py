"""M102 scene, optics and render -- the simulator proper.

Everything physical here is driven by a constant this project MEASURED, and
every such constant is cited by SYNTHESIS fact number at its definition in
m102lib.py. Free parameters -- the ones the owner's rail sets, not the
sensor -- are collected in `SimSpec` and named as free, so that no reader
mistakes a choice for a measurement.

Layer model. The scene is a back-to-front list of (rgb, alpha, depth) layers.
Rendering a frame warps every layer by that frame's magnification, blurs each
by its own defocus-composed-with-diffraction OTF, then composites with `over`.
Compositing AFTER per-layer blur is what produces genuine occlusion bleed: a
defocused foreground spreads its alpha over the background behind it, which a
single spatially-varying blur of a flat image cannot reproduce. M87 and M96
both need this and neither has ground truth for it.
"""
import numpy as np

import m102lib as M


class SimSpec:
    """Free parameters. NOT measured -- these are the rail and the framing.

    Held in one place so the report can list exactly what was chosen rather
    than derived. `blur_px_per_frame` in particular sets the through-focus
    width, which is why PREREGISTRATION N2 is a factor-of-2 bar and not a
    tight one: a tight bar there would be a bar on this number.
    """

    def __init__(self, h=512, w=512, frames=32, blur_px_per_frame=0.9,
                 iso=100, level=0.28, seed=7):
        self.h, self.w = h, w
        self.frames = frames
        self.blur_px_per_frame = blur_px_per_frame
        self.iso = iso
        # Mean signal as a fraction of usable range. 0.28 is chosen to sit
        # near bee-3-cpl's measured 0.296 background (M100 exposure help
        # text) so the shot-noise regime is comparable.
        self.level = level
        self.seed = seed


def _texture(h, w, rng, beta=1.1, amp=0.30):
    """Broadband 1/f^beta texture. Focus measures need real spectral content;
    white noise would be unrealistically Nyquist-heavy and a pure sinusoid
    would make every focus measure a single-frequency oracle, which facts
    617/708 already proved says nothing."""
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    r = np.hypot(fy, fx)
    r[0, 0] = 1.0
    spec = np.fft.rfft2(rng.standard_normal((h, w))) / r ** beta
    spec[0, 0] = 0.0
    t = np.fft.irfft2(spec, s=(h, w))
    t /= np.std(t)
    return 1.0 + amp * t


def _slanted_edge(h, w, y0, y1, angle_deg=5.7):
    """Classic slanted edge, for a free MTF measurement on the output."""
    yy, xx = np.mgrid[0:h, 0:w]
    t = np.tan(np.deg2rad(angle_deg))
    e = xx - (w * 0.5 + (yy - (y0 + y1) * 0.5) * t)
    m = np.clip(e * 0.5 + 0.5, 0.0, 1.0)          # 2 px analytic ramp
    band = (yy >= y0) & (yy < y1)
    return np.where(band, 0.18 + 0.72 * m, np.nan)


def build_scene(spec):
    """Return (layers, truth, masks).

    layers: back-to-front list of dicts {rgb (h,w,3), alpha (h,w), depth}
            where `depth` is expressed directly in FRAME INDEX units -- the
            frame at which that layer is in best focus. Depths are quantised
            onto the layer set and the quantised value IS the truth, so the
            round-trip carries no quantisation error it did not plant.
    truth:  (h,w) float, per-pixel index of the frontmost opaque layer.
    masks:  dict of boolean masks used by the pre-registered bars.
    """
    h, w, F = spec.h, spec.w, spec.frames
    rng = np.random.default_rng(spec.seed)
    yy, xx = np.mgrid[0:h, 0:w]
    layers = []

    # Colour: three fixed reflectances so the CFA carries real chromatic
    # structure. Not measured; declared as a choice.
    tint = np.array([1.00, 0.92, 0.78])

    # --- Layer 0: background plane, far, textured, with fact 73's blind spot.
    bg_depth = F - 4.0
    bg = _texture(h, w, rng)
    # Smooth low-texture disc: fact 73 MEASURED the 27x27 operator reading
    # 37.037037 at sigma = 0,1,2,3 identically on an untextured edge, i.e.
    # the focus measure is UNDEFINED here. The simulator must contain such a
    # region or it cannot express the project's known blind spot.
    smooth = np.hypot(xx - 0.78 * w, yy - 0.80 * h) < 0.11 * min(h, w)
    soft = np.cos(np.hypot(xx - 0.78 * w, yy - 0.80 * h)
                  / (0.11 * min(h, w)) * (np.pi / 2)) ** 2
    bg = np.where(smooth, 1.0 + 0.004 * soft, bg)
    layers.append({"rgb": bg[..., None] * tint,
                   "alpha": np.ones((h, w)), "depth": bg_depth,
                   "name": "background"})

    # --- Layers 1..K: slanted plane, analytic depth linear in x, top half.
    #     Continuous depth quantised into K slabs; the quantised value is
    #     what is both rendered and recorded as truth.
    K = 24
    plane_band = yy < int(0.46 * h)
    d_lo, d_hi = 3.0, F - 4.0
    d_cont = d_lo + (d_hi - d_lo) * (xx / (w - 1.0))
    edges = np.linspace(0.0, 1.0, K + 1)
    q = np.clip(np.digitize(xx / (w - 1.0), edges[1:-1]), 0, K - 1)
    d_q = d_lo + (d_hi - d_lo) * (edges[q] + edges[q + 1]) * 0.5
    ptex = _texture(h, w, np.random.default_rng(spec.seed + 1))
    # Slanted edge inside the plane, at one constant depth slab, for MTF.
    se = _slanted_edge(h, w, int(0.06 * h), int(0.16 * h))
    ptex = np.where(np.isnan(se), ptex, se)
    for k in range(K):
        a = (plane_band & (q == k)).astype(float)
        if a.sum() == 0:
            continue
        dk = float(d_lo + (d_hi - d_lo) * (edges[k] + edges[k + 1]) * 0.5)
        layers.append({"rgb": ptex[..., None] * tint, "alpha": a,
                       "depth": dk, "name": f"plane{k:02d}"})

    # --- Foreground slab: a genuine occluder. It is NEAR, and it extends
    #     over background that is FAR, so when it is defocused its alpha
    #     bleeds outward over pixels whose true depth is the background's.
    fg_depth = 5.0
    fg = (yy >= int(0.60 * h)) & (yy < int(0.90 * h)) & \
         (xx >= int(0.12 * w)) & (xx < int(0.46 * w))
    ftex = _texture(h, w, np.random.default_rng(spec.seed + 2), amp=0.34)
    layers.append({"rgb": ftex[..., None] * tint * 0.85,
                   "alpha": fg.astype(float), "depth": fg_depth,
                   "name": "occluder"})

    # --- Truth: frontmost layer covering each pixel. Layers are appended
    #     back-to-front only for the background; depth decides, not order.
    truth = np.full((h, w), bg_depth)
    truth = np.where(plane_band, d_q, truth)
    truth = np.where(fg, fg_depth, truth)

    # Occlusion band: outside the occluder but within its worst-case defocus
    # spread, where a layered renderer and a flat blur disagree.
    r_max = abs(fg_depth - bg_depth) * spec.blur_px_per_frame
    from scipy import ndimage
    grown = ndimage.binary_dilation(fg, iterations=int(max(1, r_max)))
    occ_band = grown & ~fg

    # Textured mask: where the focus measure is DEFINED. Computed on the
    # latent the simulator planted, not on the output, so it cannot be
    # tuned to flatter the result.
    lat = np.where(plane_band, ptex, bg)
    lat = np.where(fg, ftex * 0.85, lat)
    loc = ndimage.uniform_filter(lat.astype(float), 17)
    var = ndimage.uniform_filter(lat.astype(float) ** 2, 17) - loc ** 2
    textured = var > (0.25 * np.median(var[~smooth]))
    textured &= ~occ_band
    # 24 px margin: the breathing warp shrinks the field, so edge pixels do
    # not exist in every frame.
    marg = np.zeros((h, w), bool)
    marg[24:-24, 24:-24] = True
    textured &= marg

    masks = {"textured": textured, "smooth": smooth & marg,
             "occ": occ_band & marg, "plane": plane_band & marg,
             "fg": fg & marg}
    return layers, truth, masks


def _otf(h, w, r_px, neff):
    """Defocus disc OTF times the diffraction OTF, on the rfft2 grid.

    Defocus: a filled disc of radius r has MTF 2*J1(2*pi*r*f)/(2*pi*r*f).
    Diffraction: incoherent circular pupil, (2/pi)(acos s - s*sqrt(1-s^2)),
    s = f/f_c, with f_c from the MEASURED effective aperture (fact 12).
    """
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    f = np.hypot(fy, fx)
    from scipy.special import j1
    a = 2.0 * np.pi * max(r_px, 1e-9) * f
    dfc = np.ones_like(a)
    nz = a > 1e-9
    dfc[nz] = 2.0 * j1(a[nz]) / a[nz]
    return dfc * M.diffraction_mtf(f, neff)


def _warp_scale(img, s):
    """Bilinear resample about the image centre by scale factor s."""
    h, w = img.shape[:2]
    cy, cx = (h - 1) * 0.5, (w - 1) * 0.5
    yy, xx = np.mgrid[0:h, 0:w]
    sy = (yy - cy) / s + cy
    sx = (xx - cx) / s + cx
    y0 = np.clip(np.floor(sy).astype(int), 0, h - 2)
    x0 = np.clip(np.floor(sx).astype(int), 0, w - 2)
    fy = np.clip(sy - y0, 0, 1)[..., None] if img.ndim == 3 else \
        np.clip(sy - y0, 0, 1)
    fx = np.clip(sx - x0, 0, 1)[..., None] if img.ndim == 3 else \
        np.clip(sx - x0, 0, 1)
    a = img[y0, x0]
    b = img[y0, x0 + 1]
    c = img[y0 + 1, x0]
    d = img[y0 + 1, x0 + 1]
    return (a * (1 - fy) * (1 - fx) + b * (1 - fy) * fx +
            c * fy * (1 - fx) + d * fy * fx)


def render_frame(layers, spec, k, scale, neff, extra_scale=1.0):
    """Render one frame's latent RGB irradiance, before CFA and noise."""
    h, w = spec.h, spec.w
    s = scale * extra_scale
    out = np.zeros((h, w, 3))
    acc_a = np.zeros((h, w))
    for L in layers:
        r = abs(L["depth"] - k) * spec.blur_px_per_frame
        H = _otf(h, w, r, neff)
        a = _warp_scale(L["alpha"], s)
        rgb = _warp_scale(L["rgb"], s) * a[..., None]
        ab = np.fft.irfft2(np.fft.rfft2(a) * H, s=(h, w))
        cb = np.stack([np.fft.irfft2(np.fft.rfft2(rgb[..., c]) * H, s=(h, w))
                       for c in range(3)], -1)
        ab = np.clip(ab, 0.0, 1.0)
        out = cb + out * (1.0 - ab[..., None])
        acc_a = ab + acc_a * (1.0 - ab)
    return out


def mosaic(rgb):
    """RGGB Bayer sample. Requirement 4: the stack must be CFA, not RGB."""
    h, w = rgb.shape[:2]
    out = np.empty((h, w))
    out[0::2, 0::2] = rgb[0::2, 0::2, 0]
    out[0::2, 1::2] = rgb[0::2, 1::2, 1]
    out[1::2, 0::2] = rgb[1::2, 0::2, 1]
    out[1::2, 1::2] = rgb[1::2, 1::2, 2]
    return out


def add_noise(signal_dn, g, rn_e, rng):
    """Calibrated sensor noise: sigma^2 = g*S + (RN*g)^2, per-pixel,
    signal-dependent. `g` and `rn_e` MUST come from sensor_for(); M92's
    whole finding was a hard-coded ISO defeating a per-stack calibration."""
    var = np.maximum(g * np.maximum(signal_dn, 0.0), 0.0) + (rn_e * g) ** 2
    return signal_dn + rng.standard_normal(signal_dn.shape) * np.sqrt(var)
