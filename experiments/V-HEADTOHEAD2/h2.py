"""V-H2H2 core: load a strehl viewing render in LINEAR light, and compute
band-resolved power / cross-power over integer-aligned ROIs.

WHY THIS FILE EXISTS
--------------------
The prior pass's fine-scale statistic was BAND POWER, and it was retracted
because band power counts noise as if it were detail: a nearest-neighbour
gather scored +29%/+42%, a 0.5x downscale scored 4.35x better, and flat
featureless ROIs gained MORE than detail ROIs.

The primitive here is deliberately a PAIR statistic.  Given two images built
from DISJOINT halves of the same bracket -- same scene, independent photons --

    P_A(f) = <|A|^2>              total band power of half A
    P_B(f) = <|B|^2>              total band power of half B
    C (f) = <Re A B*>             COHERENT power, common to both halves
    N_A(f) = P_A(f) - C(f)        INCOHERENT power of half A

is an exact partition of P_A into a part that is common to two independent
observations of the same scene and a part that is not.  Independent noise
contributes ZERO to C in expectation, so C cannot be inflated by adding noise.
That is the single defect that killed every prior instrument, and it is the
one thing this decomposition is built to be immune to.

WHAT IT CANNOT DO -- stated here, next to where it is used (rule 18).
  * C is an MTF-like quantity: it measures COHERENT CONTRAST at a frequency.
    A filter that AMPLIFIES a band -- a sharpen, a halo -- raises C, because
    the amplification is applied to both halves and is therefore coherent.
    C is admissible as evidence about how much real structure survives to a
    frequency, and INADMISSIBLE on its own as evidence that the rendering is
    faithful.  Every arm here is therefore run against an over-sharpen control
    whose measured magnitude is reported, not argued.
  * C credits any structure common to both halves, including structure that is
    not scene detail: sensor PRNU, dust, and hot pixels are the same silicon in
    both halves.  Measured bound: kappa = 0.3096% (SYNTHESIS/M71) against
    20-26% high-pass contrast on detail ROIs, i.e. ~1.4e-4 in power.  On FLAT
    ROIs it is not negligible and the flat-ROI arm is where it shows up.
  * The two halves are aligned by separate solves, so their rasters can differ
    by a small residual.  That DEPRESSES C at high f.  It is identical for the
    two gather arms of a subject (they share a warpmap per half), so it cancels
    in a pre/post ratio and does NOT cancel in an absolute comparison against a
    third-party render.  `coherence_report` prints it so it cannot be ignored.

TONE.  The shipped master is a viewing render.  Everything here inverts the
exact chain in crates/strehl-cli/src/image_out.rs::develop_pixel

    linear sRGB -> tone gain g(luma709) -> gamut_map -> srgb_encode
                -> s_curve(contrast) -> u16

using the black / white / contrast values THE RENDER ITSELF PRINTED, parsed out
of its log -- not hard-coded, because they are chosen per image from its own
luminance histogram.  gamut_map is the identity on in-gamut pixels, so any ROI
containing a clipped or out-of-gamut sample is DROPPED and COUNTED, never
silently included.
"""
import os
import re

import numpy as np
import tifffile

import physics

TONE_TOE = 0.004          # image_out.rs const TONE_TOE
U16 = 65535.0


# --------------------------------------------------------------------------
# tone
# --------------------------------------------------------------------------
class Tone:
    """The three numbers a strehl --srgb render prints, plus the fixed toe."""

    def __init__(self, black, white, contrast):
        self.black = float(black)
        self.white = float(white)
        self.contrast = float(contrast)
        self._lut = None

    def __repr__(self):
        return f"Tone(black={self.black:.6f}, white={self.white:.6f}, contrast={self.contrast})"

    @staticmethod
    def from_log(path):
        """Parse `tone            : black 0.02509, white 0.99229 (linear), contrast 0.55`."""
        txt = open(path, "r", encoding="utf-8", errors="replace").read()
        m = re.search(r"^tone\s*:\s*black\s+([0-9.eE+-]+),\s*white\s+([0-9.eE+-]+)"
                      r"\s*\(linear\),\s*contrast\s+([0-9.eE+-]+)", txt, re.M)
        if not m:
            raise RuntimeError(f"no tone line in {path}")
        return Tone(m.group(1), m.group(2), m.group(3))

    def gain(self, lum):
        lum = np.maximum(np.asarray(lum, np.float64), 0.0)
        s = 1.0 / (self.white - self.black)
        y = (lum - self.black) * s
        soft = 0.5 * (y + np.sqrt(y * y + TONE_TOE * TONE_TOE))
        with np.errstate(divide="ignore", invalid="ignore"):
            g = np.where(lum > 0, soft / np.where(lum > 0, lum, 1.0), 0.0)
        return np.minimum(g, s)

    def inv_luma(self, lp):
        """Invert L' = L * gain(L).  Monotone by construction (gain' > 0)."""
        if self._lut is None:
            lo = np.linspace(0.0, 0.05, 200001)
            hi = np.linspace(0.05, 4.0, 200001)[1:]
            L = np.concatenate([lo, hi])
            self._lut = (L * self.gain(L), L)
        return np.interp(np.clip(lp, 0, None), self._lut[0], self._lut[1])


def s_curve(x, k):
    s = x * x * (3.0 - 2.0 * x)
    return x + (s - x) * k


_INV_S = {}


def inv_s_curve(y, k):
    key = round(float(k), 6)
    if key not in _INV_S:
        x = np.linspace(0.0, 1.0, 65536, dtype=np.float64)
        _INV_S[key] = (s_curve(x, k), x)
    ys, xs = _INV_S[key]
    return np.interp(np.clip(y, 0, 1), ys, xs)


def srgb_decode(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))


def luma709(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def to_linear(u16_rgb, tone):
    """u16 viewing render -> linear sRGB, tone and transfer removed exactly."""
    d = np.asarray(u16_rgb, np.float64) / U16
    d = inv_s_curve(d, tone.contrast)
    v = srgb_decode(d)
    lp = luma709(v)
    lin = tone.inv_luma(lp)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(lin > 0, lp / np.maximum(lin, 1e-12), 1.0)
    g = np.where(g > 1e-9, g, 1.0)
    return v / g[..., None]


# --------------------------------------------------------------------------
# renders
# --------------------------------------------------------------------------
class Render:
    """A u16 RGB TIFF plus the tone that produced it.  Crops are inverted to
    linear on demand: the full float image is never materialised (7032x4688x3
    float64 is 790 MB, and several arms are open at once)."""

    def __init__(self, path, tone=None, log=None, name=None, linear=False,
                 chan="luma"):
        self.path = path
        self.name = name or os.path.splitext(os.path.basename(path))[0]
        self.a = tifffile.memmap(path, mode="r")
        self.h, self.w = self.a.shape[0], self.a.shape[1]
        self.linear = linear
        self.chan = chan
        if linear:
            self.tone = None
        else:
            self.tone = tone or Tone.from_log(
                log or os.path.splitext(path)[0] + ".log")

    def __repr__(self):
        return f"Render({self.name}, {self.w}x{self.h}, {self.tone})"

    def raw_crop(self, y0, x0, t):
        return np.asarray(self.a[y0:y0 + t, x0:x0 + t, :3], np.uint16)

    def crop(self, y0, x0, t, chan=None):
        """Linear-light crop of one channel, plus the count of clipped samples.

        chan defaults to `self.chan`.  'luma' is BT.709 luminance, which is the
        right default on a --linear-srgb render: the demosaic estimates every
        CFA site, and the real measurement at each site lands mostly in
        luminance, whereas the green channel after the colour matrix is a
        difference of three interpolated numbers and carries the demosaic's
        chroma error at full weight."""
        chan = self.chan if chan is None else chan
        blk = self.raw_crop(y0, x0, t)
        nclip = int((blk >= 65535).sum() + (blk == 0).sum())
        if self.linear:
            v = np.asarray(blk, np.float64)
        else:
            v = to_linear(blk, self.tone) * U16
        if chan == "luma":
            return luma709(v), nclip
        return v[:, :, chan], nclip

    def coarse(self, step=16, chan=1):
        """Strided view of one channel, u16, for ROI scouting only."""
        return np.asarray(self.a[::step, ::step, chan], np.float64)


# --------------------------------------------------------------------------
# spectra
# --------------------------------------------------------------------------
BANDS = [(0.02, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.25),
         (0.25, 0.30), (0.30, 0.40), (0.40, 0.48)]


def _window(t):
    w = np.hanning(t)
    return w[:, None] * w[None, :]


_WCACHE = {}


def window(t):
    if t not in _WCACHE:
        _WCACHE[t] = _window(t)
    return _WCACHE[t]


_RCACHE = {}


def radial(t):
    if t not in _RCACHE:
        fy = np.fft.fftfreq(t)[:, None]
        fx = np.fft.fftfreq(t)[None, :]
        _RCACHE[t] = np.hypot(fy, fx)
    return _RCACHE[t]


def contrast_fft(crop):
    """DC-removed, mean-normalised, Hann-windowed FFT.  Every scalar gain --
    exposure, white point, a global grade -- cancels in the mean division, so
    the result is in CONTRAST units."""
    t = crop.shape[0]
    m = crop.mean()
    if not np.isfinite(m) or m <= 1e-9:
        return None
    c = (crop / m - 1.0) * window(t)
    return np.fft.fft2(c)


def band_masks(t, bands=BANDS):
    r = radial(t)
    return [(r >= a) & (r < b) for (a, b) in bands]


def pair_bands(fa, fb, masks, t, tag=""):
    """Per-band (P_A, P_B, C) for one ROI.  Parseval-normalised so the numbers
    are the variance carried by that band, comparable across ROI sizes.

    Every triple leaving this function is checked against the physics that
    constrains it -- |C| <= sqrt(P_A P_B), powers non-negative -- and an
    ImpossibleMeasurement is RAISED, not returned as a flag.  The reason is a
    reading elsewhere in this project of an aura depression of 16557.7 DN on an
    image whose median was 8171.1 DN: a quantity deeper than the thing it is
    measured against.  That class of defect passes every range check and every
    plausibility glance, and is caught instantly by asking whether the number
    is physically possible.  See physics.py and commission_physics.py.
    """
    norm = (t * t) ** 2 * (window(t) ** 2).mean()
    pa = (np.abs(fa) ** 2) / norm
    pb = (np.abs(fb) ** 2) / norm
    cc = np.real(fa * np.conj(fb)) / norm
    PA = np.array([pa[m].sum() for m in masks])
    PB = np.array([pb[m].sum() for m in masks])
    C = np.array([cc[m].sum() for m in masks])
    physics.coherence_ok(PA, PB, C, tag or "pair_bands")
    physics.band_partition_ok(PA, PB, C, tag or "pair_bands")
    return PA, PB, C


def bootstrap_ratio(num, den, reps=4000, seed=5):
    """95% CI of sum(num)/sum(den) by ROI resampling.  ROIs are the unit of
    replication because they are what varies between runs of this instrument;
    Fourier bins inside one ROI are not independent."""
    num = np.asarray(num, float)
    den = np.asarray(den, float)
    n = len(num)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    point = num.sum() / den.sum() if den.sum() != 0 else float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, (reps, n))
    ns = num[idx].sum(1)
    ds = den[idx].sum(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        bs = np.where(ds != 0, ns / ds, np.nan)
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    return float(point), float(lo), float(hi)


# --------------------------------------------------------------------------
# integer registration
# --------------------------------------------------------------------------
def integer_shift(ref, mov, maxshift=8):
    """Integer (dy, dx) such that mov sampled at (y+dy, x+dx) aligns to ref.

    INTEGER ONLY -- sub-pixel resampling would add blur to the very quantity
    being measured, so no sub-pixel option exists here at all.

    NOT phase correlation.  The first version of this function whitened the
    cross-spectrum, and on a pair of images with INDEPENDENT noise -- which is
    the entire point of the half-stack primitive -- whitening promotes the
    noise-dominated high frequencies to equal weight with the signal.  It
    returned shifts of +/-1 and +/-2 px on a pair whose true offset is 0, and
    applying them DROVE COHERENCE DOWN at every frequency (gamma at f=0.005
    fell from 1.0000 to 0.9971, which is impossible for a correct alignment).
    Plain cross-correlation weights each frequency by its own power, so the
    scene decides the peak and the noise does not.  `commission_shift` below
    is the test that this version actually recovers a planted shift.

    SIGN.  The cross-correlation peak is the DISPLACEMENT of mov relative to
    ref; what every caller wants is the CORRECTION, which is its negative, and
    that is what this returns -- as the first line of this docstring has always
    said.  It did not, until measured: commission_shift scored `planted (2,3)
    got (2,3)` as a MISS because it (correctly) required -(dy,dx), while every
    consumer added the returned value to its crop origin.  signconv.py settles
    it by measurement rather than by reading -- re-cropping at +g scores 0.6186
    mean residual correlation against 1.0000 at -g, and on a 1 px plant the
    wrong sign takes gamma at 0.25-0.30 cyc/px from +1.0000 to -0.4234.
    """
    a = ref - ref.mean()
    b = mov - mov.mean()
    w = window(ref.shape[0])
    A = np.fft.fft2(a * w)
    B = np.fft.fft2(b * w)
    c = np.real(np.fft.ifft2(A * np.conj(B)))
    n = np.sqrt(((a * w) ** 2).sum() * ((b * w) ** 2).sum()) + 1e-30
    t = ref.shape[0]
    off = np.arange(-maxshift, maxshift + 1)
    sub = c[np.ix_(off % t, off % t)] / n
    i = np.unravel_index(np.argmax(sub), sub.shape)
    return -int(off[i[0]]), -int(off[i[1]]), float(sub[i])


def commission_shift(render, y, x, t=256, pad=32, plants=((0, 0), (1, 0),
                                                          (0, -1), (2, 3),
                                                          (-3, 2), (5, -5))):
    """Plant a known integer offset and check integer_shift recovers it.

    A registration routine that has only ever been run on data whose true
    answer is unknown is not a registration routine.  Returns (n_ok, n_total,
    failures)."""
    ref = render.crop(y, x, t)[0]
    ok, fails = 0, []
    for (dy, dx) in plants:
        mov = render.crop(y + dy, x + dx, t)[0]
        gy, gx, pk = integer_shift(ref, mov)
        # mov was taken at +(dy,dx); to realign we must sample at -(dy,dx)
        if (gy, gx) == (-dy, -dx):
            ok += 1
        else:
            fails.append(((dy, dx), (gy, gx), pk))
    return ok, len(plants), fails
