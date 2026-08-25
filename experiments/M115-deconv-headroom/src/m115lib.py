"""M115 -- multi-frame deconvolution headroom on the focus axis.

The one limb M41 explicitly could not measure: a RESOLUTION metric with
demonstrated power on real data, and the per-frequency headroom read off it.

Rules honoured, by construction:
  4   no arm's reference is a raw per-band argmax; FRAME* elects on the
      REGULARISED coarse field, tile-wise, and is labelled a selector
  7   raw_image_visible only
  9   every statistic is computed on a flat ROI in the same pass as the detail
      ROI, and the flat run is READ FIRST
 10   every sigma here is either a temporal/model sigma (labelled sigma_t) or a
      spatial sd (labelled sd_s); the two are never compared
 18   fooling direction is stated next to each metric in the report
 23   sobel is only ever called on an already-extracted 2-D plane
 32   raw_image_visible is copied inside the `with` block
D:\ is opened read-only and never written.  Outputs go to C:\dev\strehl-out.
"""
import os, glob
import numpy as np
import rawpy, exifread
from scipy.ndimage import uniform_filter, sobel
from scipy.special import j1

BLACK = 512
F_SIG = 0.2762           # fact 27, MEASURED optical cutoff, cyc/quad px
MIDBAND = (0.10, F_SIG)  # M70's mid band, closed at fact 27's cutoff
FINE_W = 5
COARSE_W = 27
REG_W = 17
GATE_FRAC = 0.5
TILE = 128
STEP = 64
PAD = 64

OUT = r"C:\dev\strehl-out\M115-deconv-headroom\out"
os.makedirs(OUT, exist_ok=True)


# ------------------------------------------------------------------ loading
def stack_files(d):
    return sorted(glob.glob(os.path.join(d, "*.ARW")))


def iso_of(p):
    with open(p, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in t:
            return int(str(t[k]).split(",")[0].strip("[] "))
    return None


def fnumber_of(p):
    with open(p, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    for k in ("EXIF FNumber", "Image FNumber"):
        if k in t:
            v = t[k].values[0]
            return float(v.num) / float(v.den)
    return None


def noise_params(iso):
    """The project's own photon-transfer model.  Returns g DN/e- and RN in e-."""
    g = iso / 436.8
    rn_e = 1.47 if iso >= 400 else 4.20
    return g, rn_e


def quad_var(level_dn, g, rn_e):
    """Temporal variance of one QUAD-plane sample, DN^2.  Halved because
    G = (G1+G2)/2 averages two independent CFA sites."""
    return 0.5 * (g * np.maximum(level_dn, 0.0) + (rn_e * g) ** 2)


def load_cube(files, roi, pad=PAD):
    """(n, h, w) float32 quad-green, black-subtracted, over roi expanded by pad.
    Rule 32: the view is sliced AND cast inside the `with`."""
    x, y, w, h = roi
    x0, y0 = x - pad, y - pad
    x1, y1 = x + w + pad, y + h + pad
    out = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
            g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - BLACK
    return out


def quad_green_full(path):
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[0::2, 1::2].astype(np.float32)
        g2 = v[1::2, 0::2].astype(np.float32)
    return 0.5 * (g1 + g2) - BLACK


# ------------------------------------------------------------- focus fields
def focus_fields(cube, g, rn_e):
    """Noise-normalised Tenengrad, shipped shape.  Rule 23: sobel per 2-D plane."""
    n = cube.shape[0]
    fine = np.empty_like(cube)
    coarse = np.empty_like(cube)
    reg = np.empty_like(cube)
    for k in range(n):
        p = cube[k]
        gx = sobel(p, axis=1)
        gy = sobel(p, axis=0)
        e = gx * gx + gy * gy
        m = uniform_filter(p, COARSE_W)
        nvar = quad_var(m, g, rn_e)
        fine[k] = uniform_filter(e, FINE_W) - 24.0 * nvar
        coarse[k] = uniform_filter(e, COARSE_W) - 24.0 * nvar
        reg[k] = uniform_filter(coarse[k], REG_W)
    np.maximum(fine, 0.0, out=fine)
    np.maximum(coarse, 0.0, out=coarse)
    np.maximum(reg, 0.0, out=reg)
    return fine, coarse, reg


# -------------------------------------------------------------------- OTFs
def otf_defocus(r, f):
    """Geometric pillbox of radius r quad px: H = 2 J1(2 pi r f)/(2 pi r f).
    Kept signed -- the contrast reversals are real."""
    if r <= 1e-6:
        return np.ones_like(f)
    a = 2.0 * np.pi * r * f
    out = np.ones_like(f)
    nz = a > 1e-8
    out[nz] = 2.0 * j1(a[nz]) / a[nz]
    return out


def otf_diffraction(f, fc=F_SIG):
    """Incoherent circular-aperture OTF at the MEASURED cutoff fc (fact 27)."""
    nu = np.clip(f / fc, 0.0, 1.0)
    h = (2.0 / np.pi) * (np.arccos(nu) - nu * np.sqrt(np.maximum(1.0 - nu * nu, 0.0)))
    h = np.where(f >= fc, 0.0, h)
    return h


# ------------------------------------------------------- spectra / binning
def hann2(n):
    w = np.hanning(n)
    return np.outer(w, w).astype(np.float64)


class RadialBins:
    """Radial bins over a square N x N rfft2 grid, in cyc/px."""

    def __init__(self, n, df=0.01):
        fy = np.fft.fftfreq(n)[:, None]
        fx = np.fft.rfftfreq(n)[None, :]
        self.f2d = np.sqrt(fy * fy + fx * fx)
        self.n = n
        # rfft2 double-counts nothing at columns 0 and n/2; weight the rest by 2
        wt = np.full(self.f2d.shape, 2.0)
        wt[:, 0] = 1.0
        if n % 2 == 0:
            wt[:, -1] = 1.0
        self.wt = wt
        edges = np.arange(0.0, 0.5 + df, df)
        self.edges = edges
        self.centres = 0.5 * (edges[:-1] + edges[1:])
        idx = np.digitize(self.f2d.ravel(), edges) - 1
        idx[(idx < 0) | (idx >= len(self.centres))] = -1
        self.idx = idx
        self.valid = idx >= 0
        wv = wt.ravel()[self.valid]
        self.wv = wv
        self.iv = idx[self.valid]
        self.count = np.bincount(self.iv, weights=wv, minlength=len(self.centres))
        self.win = hann2(n)
        self.nrm = float((self.win ** 2).sum())

    def power(self, img):
        """Mean power per mode, per radial bin.  White noise of variance v
        contributes exactly v * self.nrm to every bin."""
        a = img.astype(np.float64)
        a = (a - a.mean()) * self.win
        P = np.abs(np.fft.rfft2(a)) ** 2
        s = np.bincount(self.iv, weights=P.ravel()[self.valid] * self.wv,
                        minlength=len(self.centres))
        return s / np.maximum(self.count, 1e-12)

    def cross(self, ia, ib):
        """Re<A conj(B)> per mode, per radial bin.  For two observations of one
        latent with INDEPENDENT noise this is the signal power in expectation,
        and the noise contributes zero -- no noise model is involved at all."""
        a = ia.astype(np.float64)
        b = ib.astype(np.float64)
        A = np.fft.rfft2((a - a.mean()) * self.win)
        B = np.fft.rfft2((b - b.mean()) * self.win)
        P = np.real(A * np.conj(B))
        s = np.bincount(self.iv, weights=P.ravel()[self.valid] * self.wv,
                        minlength=len(self.centres))
        return s / np.maximum(self.count, 1e-12)

    def band_mask(self, lo, hi):
        return (self.centres >= lo) & (self.centres < hi)


# --------------------------------------------------------------- the arms
def _tile_grid(H, W):
    ys = list(range(0, H - TILE + 1, STEP))
    xs = list(range(0, W - TILE + 1, STEP))
    if ys[-1] != H - TILE:
        ys.append(H - TILE)
    if xs[-1] != W - TILE:
        xs.append(W - TILE)
    return ys, xs


def arm_frame_tile(cube, reg):
    """FRAME* -- the ceiling a perfect selector reaches.  Per TILE, the single
    best frame, elected on the REGULARISED coarse field averaged over the tile
    (rule 4: not a raw per-band argmax).  Hann overlap-add, so the seams are
    blended exactly as the Wiener arms' are and the comparison is like for
    like."""
    n, H, W = cube.shape
    acc = np.zeros((H, W))
    wacc = np.zeros((H, W))
    win = hann2(TILE)
    ys, xs = _tile_grid(H, W)
    picks = {}
    for y in ys:
        for x in xs:
            r = reg[:, y:y + TILE, x:x + TILE].reshape(n, -1).mean(1)
            k = int(np.argmax(r))
            picks[(y, x)] = k
            acc[y:y + TILE, x:x + TILE] += cube[k, y:y + TILE, x:x + TILE] * win
            wacc[y:y + TILE, x:x + TILE] += win
    return (acc / np.maximum(wacc, 1e-9)).astype(np.float32), picks


def arm_frame_pixel(cube, reg):
    """Per-pixel election on the regularised field, no averaging.  Labelled
    baseline only; never a reference for another arm's score (rule 4)."""
    w = np.argmax(reg, axis=0)
    return np.take_along_axis(cube, w[None], 0)[0].astype(np.float32), w


def arm_gate(cube, coarse, reg):
    """Shipped-equivalent noise-gated average (M41 arm A)."""
    n, H, W = cube.shape
    w = np.argmax(reg, axis=0)
    peak = np.take_along_axis(coarse, w[None], 0)[0]
    acc = coarse >= (GATE_FRAC * peak)[None]
    acc[w, np.arange(H)[:, None], np.arange(W)[None, :]] = True
    cnt = acc.sum(0).astype(np.float32)
    s = (cube * acc).sum(0)
    return (s / np.maximum(cnt, 1.0)).astype(np.float32), cnt


def arm_mean(cube):
    return cube.mean(0).astype(np.float32)


def arm_wiener(cube, reg, g, rn_e, s, use_diff, guarded=True, tau=3.0,
               gate_img=None, otf_scale=1.0):
    """The R3 estimator, tile-wise.

        L_hat(f) = SUM_k H_k(f) Y_k(f) / ( SUM_k |H_k(f)|^2 + sigma^2/S(f) )

    S(f) is DATA-ESTIMATED per tile from the sharpest frame's noise-subtracted
    radial spectrum (M20 measured that parametric power-law priors fail
    everywhere and data-estimated ones track the oracle to ~1%).

    guarded: blend toward gate_img with weight SUM|H|^2/(SUM|H|^2 + tau sigma^2/S)
    so the estimator can never do worse than the gated average where the OTFs
    carry nothing (the floor the brief requires).
    """
    n, H, W = cube.shape
    acc = np.zeros((H, W))
    wacc = np.zeros((H, W))
    win = hann2(TILE)
    nrm = float((win ** 2).sum())        # E|FFT(noise*win)|^2 = sig2 * nrm, per mode
    fy = np.fft.fftfreq(TILE)[:, None]
    fx = np.fft.rfftfreq(TILE)[None, :]
    F = np.sqrt(fy * fy + fx * fx)
    hd = otf_diffraction(F) if use_diff else np.ones_like(F)
    rb = RadialBins(TILE, df=1.0 / TILE)
    ys, xs = _tile_grid(H, W)
    for y in ys:
        for x in xs:
            tile = cube[:, y:y + TILE, x:x + TILE]
            rt = reg[:, y:y + TILE, x:x + TILE].reshape(n, -1).mean(1)
            kstar = int(np.argmax(rt))
            mean = float(tile[kstar].mean())
            sig2 = float(quad_var(max(mean, 0.0), g, rn_e))
            # data-estimated prior: the sharpest frame's noise-subtracted radial
            # spectrum, forced non-increasing.  M20 measured that parametric
            # power-law priors lose everywhere and this one tracks the oracle.
            Pk = rb.power(tile[kstar])                       # per-mode power
            floor = 1e-6 * max(float(Pk[1]), 1e-9)
            Ps = np.maximum(Pk - sig2 * nrm, floor)          # per-mode SIGNAL power
            Ps = np.maximum.accumulate(Ps[::-1])[::-1]
            Sf = np.maximum(np.interp(F.ravel(), rb.centres, Ps).reshape(F.shape), 1e-12)
            # both terms are per-mode powers of the SAME windowed transform
            reg_term = (sig2 * nrm) / Sf
            numc = np.zeros(F.shape, np.complex128)
            den = np.zeros(F.shape)
            for k in range(n):
                Hk = otf_defocus(abs(k - kstar) * s * otf_scale, F) * hd
                numc += Hk * np.fft.rfft2((tile[k] - mean) * win)
                den += Hk * Hk
            Lf = numc / (den + reg_term)
            if guarded and gate_img is not None:
                # the floor the brief requires: where SUM|H|^2 is small the
                # estimator falls back to the gated average and so can never do
                # worse than it.
                a = den / (den + tau * reg_term)
                Gt = np.fft.rfft2((gate_img[y:y + TILE, x:x + TILE] - mean) * win)
                Lf = a * Lf + (1.0 - a) * Gt
            L = np.fft.irfft2(Lf, s=(TILE, TILE)) + mean
            acc[y:y + TILE, x:x + TILE] += L * win
            wacc[y:y + TILE, x:x + TILE] += win
    return (acc / np.maximum(wacc, 1e-9)).astype(np.float32)


def arm_best1(cube, coarse):
    """The single globally sharpest frame -- the brief's literal reference:
    'contrast that NO single frame in the stack contains'.  FRAME* (per-tile
    election) is strictly stronger than this, so both are reported."""
    k = int(np.argmax(coarse.reshape(cube.shape[0], -1).mean(1)))
    return cube[k].astype(np.float32), k


def run_all_arms(cube, g, rn_e, s, want=None):
    """One pass over a cube producing every arm.  Every data-derived weight
    (election, gate set, prior, kstar) is re-derived from the cube it is given,
    so a split half elects on its OWN noise -- which is what makes the split
    channel able to see selection-induced noise structure."""
    w = set(ARMS) if want is None else set(want)
    fine, coarse, reg = focus_fields(cube, g, rn_e)
    out = {}
    picks = neff = None
    if "FRAME*" in w:
        out["FRAME*"], picks = arm_frame_tile(cube, reg)
    if "FRAME_PIX" in w:
        out["FRAME_PIX"], _ = arm_frame_pixel(cube, reg)
    if "BEST1" in w:
        out["BEST1"], _ = arm_best1(cube, coarse)
    gimg = None
    if w & {"GATE", "MF", "WIENER"}:
        gate, neff = arm_gate(cube, coarse, reg)
        gimg = gate.astype(np.float64)
        if "GATE" in w:
            out["GATE"] = gate
    if "MEAN" in w:
        out["MEAN"] = arm_mean(cube)
    if "MF" in w:
        out["MF"] = arm_wiener(cube, reg, g, rn_e, s, use_diff=False, gate_img=gimg)
    if "WIENER" in w:
        out["WIENER"] = arm_wiener(cube, reg, g, rn_e, s, use_diff=True, gate_img=gimg)
    if "WIENER_UNG" in w:
        out["WIENER_UNG"] = arm_wiener(cube, reg, g, rn_e, s, use_diff=True,
                                       guarded=False, gate_img=None)
    out["_neff"] = neff
    out["_picks"] = picks
    return out


ARMS = ["BEST1", "FRAME*", "FRAME_PIX", "GATE", "MEAN", "MF", "WIENER", "WIENER_UNG"]


# ------------------------------------------------------- the noise channel
def make_noise(cube, g, rn_e, rng, scale=1.0):
    """An iid realisation with EXACTLY the modelled per-pixel variance of the
    real noise, per frame.  Rule 34 applies: this plant supplies its own noise
    constant and cannot validate it -- control C5 validates it against the data
    (frame-to-frame differences on a flat patch)."""
    lvl = uniform_filter(cube, size=(1, COARSE_W, COARSE_W))
    sd = np.sqrt(quad_var(lvl, g, rn_e) * scale)
    return (rng.standard_normal(cube.shape).astype(np.float32) * sd).astype(np.float32)


def noise_channel(cube, g, rn_e, s, reps, seed, crop, scale=1.0, want=None):
    """Antithetic noise injection.  D = (pipeline(Y+n) - pipeline(Y-n))/2 is,
    for any pipeline linear in its input given fixed weights, exactly W n --
    the arm's noise transfer applied to a noise field of the real amplitude.
    Returns {arm: [D_1..D_reps]} cropped to the measurement window."""
    rng = np.random.default_rng(seed)
    acc = {}
    for _ in range(reps):
        nz = make_noise(cube, g, rn_e, rng, scale)
        op = run_all_arms(cube + nz, g, rn_e, s, want)
        om = run_all_arms(cube - nz, g, rn_e, s, want)
        for k in op:
            if k.startswith("_"):
                continue
            d = 0.5 * (op[k].astype(np.float64) - om[k].astype(np.float64))
            acc.setdefault(k, []).append(crop(d))
    return acc


def crop_fn(pad, b):
    def f(a):
        return a[pad:pad + b, pad:pad + b]
    return f


# ------------------------------------------------- the split-stack channel
def split_channel(cube, g, rn_e, s, crop, mode="oddeven", want=None):
    """Two INDEPENDENT observations of one latent, each pushed through the whole
    pipeline with every data-dependent weight re-derived inside its own half.

    Unlike noise injection, this sees noise that a data-dependent election has
    converted into STRUCTURE, because half A's election is driven by half A's
    noise and half B's by B's, independently.  Measured: the injection channel
    reports mid-band SNR 84.9 for a per-pixel selector on a scene-free capture;
    this one reports the truth.

    Returns {arm: (O_A, O_B)}.  The halves have N/2 frames each and therefore
    twice the focus step, so `s` is doubled for the arms that use it.
    """
    if mode == "oddeven":
        ia, ib = np.arange(0, cube.shape[0], 2), np.arange(1, cube.shape[0], 2)
    elif mode == "halves":                       # latent-mismatch control
        h = cube.shape[0] // 2
        ia, ib = np.arange(0, h), np.arange(h, 2 * h)
    else:
        raise ValueError(mode)
    n = min(len(ia), len(ib))
    ia, ib = ia[:n], ib[:n]
    sa = s * 2.0 if mode == "oddeven" else s
    A = run_all_arms(cube[ia], g, rn_e, sa, want)
    B = run_all_arms(cube[ib], g, rn_e, sa, want)
    out = {}
    for k in A:
        if k.startswith("_"):
            continue
        out[k] = (crop(A[k]), crop(B[k]))
    return out


def split_stats(rb, oa, ob):
    """P_sig, P_noise, SNR from a split pair.

        P_sig   = Re<A conj(B)>            noise is independent -> 0 in expectation
        P_noise = P(A - B) / 2             signal cancels exactly
        check   : (P(A)+P(B))/2 ~= P_sig + P_noise

    Fooling directions (rule 18).  P_sig is fooled UP by anything COMMON to both
    halves that is not scene -- fixed-pattern non-uniformity above all; that
    floor is measured on a scene-free capture and quoted.  It is fooled DOWN by
    the two halves' latents differing, which is why the halves are interleaved
    and why a first-half/second-half split is run as a control.  P_noise cannot
    be fooled down by amplified noise: amplified noise is independent between
    halves and lands in P_noise by construction.
    """
    Ps = rb.cross(oa, ob)
    Pn = 0.5 * rb.power(oa - ob)
    Pa = 0.5 * (rb.power(oa) + rb.power(ob))
    return Ps, Pn, Ps / np.maximum(Pn, 1e-30), Pa


# ------------------------------------------------------------ the plant
def fourier_gauss_blur(img, sb):
    """EXACT Gaussian blur in the Fourier domain: MTF = exp(-2 pi^2 sb^2 f^2).
    No kernel truncation, no resampling -- the brief forbids a plant that
    perturbs the quantity being measured, and a resampling plant blurs."""
    if sb <= 0:
        return img.astype(np.float64).copy()
    n0, n1 = img.shape
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.rfftfreq(n1)[None, :]
    f2 = fy * fy + fx * fx
    H = np.exp(-2.0 * np.pi ** 2 * sb ** 2 * f2)
    m = img.mean()
    return np.fft.irfft2(np.fft.rfft2(img - m) * H, s=img.shape) + m


def blur_cube(cube, sb):
    if sb <= 0:
        return cube.astype(np.float32).copy()
    out = np.empty_like(cube)
    for k in range(cube.shape[0]):
        out[k] = fourier_gauss_blur(cube[k], sb).astype(np.float32)
    return out


def freq_gain(img, a_of_f):
    """Apply a known frequency-dependent gain a(f) -- control C3's plant."""
    n0, n1 = img.shape
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.rfftfreq(n1)[None, :]
    f = np.sqrt(fy * fy + fx * fx)
    m = img.mean()
    return np.fft.irfft2(np.fft.rfft2(img - m) * a_of_f(f), s=img.shape) + m


# ------------------------------------------------------------- OTF self-cal
def calibrate_s(cube, coarse, use_diff=True, kstar=None):
    """The reviewer's route: the WIDTH of the through-focus response curve IS
    the local PSF scale sampled by the operator.  Measure the FWHM of the
    measured curve in frames, then solve for the blur growth per frame s that
    reproduces that FWHM under the forward model.
    Returns (s, fwhm_measured, fwhm_modelled)."""
    n = cube.shape[0]
    curve = coarse.reshape(n, -1).mean(1)
    ks = int(np.argmax(curve)) if kstar is None else kstar
    c = curve - curve.min()
    half = 0.5 * c.max()
    above = np.where(c >= half)[0]
    fwhm_meas = float(above[-1] - above[0] + 1)

    p = cube[ks] - cube[ks].mean()
    h, w = p.shape
    win = hann2(min(h, w))
    p = p[:win.shape[0], :win.shape[1]]
    P = np.abs(np.fft.rfft2(p * win)) ** 2
    P /= P.sum()
    fy = np.fft.fftfreq(p.shape[0])[:, None]
    fx = np.fft.rfftfreq(p.shape[1])[None, :]
    F = np.sqrt(fy * fy + fx * fx)
    grad2 = (2.0 * np.pi) ** 2 * F * F
    hd = otf_diffraction(F) if use_diff else np.ones_like(F)

    def modelled_fwhm(sv):
        resp = np.array([float((P * grad2 * (otf_defocus(dk * sv, F) * hd) ** 2).sum())
                         for dk in range(n)])
        r = resp - resp.min()
        idx = np.where(r >= 0.5 * r.max())[0]
        return 2.0 * (idx[-1] + 1) - 1.0

    lo, hi = 0.02, 8.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if modelled_fwhm(mid) > fwhm_meas:
            lo = mid
        else:
            hi = mid
    sv = 0.5 * (lo + hi)
    return sv, fwhm_meas, modelled_fwhm(sv)


# --------------------------------------------------------------- reporting
def fmt_band(rb, arr, lo=MIDBAND[0], hi=MIDBAND[1]):
    m = rb.band_mask(lo, hi)
    return arr[m], rb.centres[m]
