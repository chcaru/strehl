"""M69 shared instrument. Constants parsed from the crate at run time, never retyped.

Independent re-implementation of the shipped operator chain:

    luma  = 0.5 * (max(G1-black,0) + max(G2-black,0))              plane.rs
    grad  = 0.125 * hypot(Sobel_x, Sobel_y), replicate border      focus.rs
    focus = box_clamped(grad, WINDOW_RADIUS) / max(sigma_L, EPS)   focus.rs + noise.rs
    reg   = box_clamped(focus, REGULARISER_RADIUS)                 merge.rs

The box filter here is a summed-area implementation in float64, deliberately a
different construction from M66's `scipy.ndimage.uniform_filter` route, so that
control K2 (against the shipped Rust binary) is a real cross-implementation
check rather than a shared-bug check.
"""

import pathlib
import re

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
CORE = ROOT / "crates" / "strehl-core" / "src"
EXP = pathlib.Path(__file__).resolve().parents[1]
OUT = EXP / "out"
DATA = EXP / "data"

CORPUS = r"D:\personal\macro"
DARKS = r"D:\macro-dark-frames"


def _grab(path, pattern, cast=float):
    text = (CORE / path).read_text(encoding="utf-8")
    m = re.search(pattern, text)
    if m is None:
        raise SystemExit(f"constant not found in {path}: {pattern}")
    return cast(m.group(1).replace("_", ""))


FOCUS_NOISE_SD = _grab("merge.rs", r"pub const FOCUS_NOISE_SD: f32 = ([0-9_.]+);")
FINE_FOCUS_NOISE_SD = _grab(
    "through_focus.rs", r"pub const FINE_FOCUS_NOISE_SD: f32 = ([0-9_.]+);"
)
REGULARISER_RADIUS = _grab("merge.rs", r"pub const REGULARISER_RADIUS: usize = (\d+);", int)
DEFAULT_GATE = _grab("merge.rs", r"pub const DEFAULT_GATE: f32 = ([0-9.]+);")
WINDOW_RADIUS = _grab("focus.rs", r"pub const WINDOW_RADIUS: usize = (\d+);", int)
SIGMA_EPS = _grab("focus.rs", r"const SIGMA_EPS: f32 = ([0-9e.\-]+);")
SOBEL_SCALE = 0.125

GAIN_DIVISOR = _grab("profile.rs", r"gain_divisor: ([0-9.]+),")
BASE_ISO = _grab("profile.rs", r"base_iso: ([0-9.]+),")
READ_NOISE_E_LOW = _grab("profile.rs", r"read_noise_e_low: ([0-9.]+),")
READ_NOISE_E_HIGH = _grab("profile.rs", r"read_noise_e_high: ([0-9.]+),")
SECOND_BASE_ISO = _grab("profile.rs", r"second_base_iso: ([0-9.]+),")
BLACK = _grab("profile.rs", r"black: ([0-9.]+),")
WHITE = _grab("profile.rs", r"white: ([0-9.]+),")

INSET = WINDOW_RADIUS + REGULARISER_RADIUS + 2  # 23, matching M66 K7


def banner(title):
    print("=" * 78)
    print(title)
    print("=" * 78, flush=True)


def dump_constants():
    print(f"  FOCUS_NOISE_SD      {FOCUS_NOISE_SD:.6f}     merge.rs")
    print(f"  DEFAULT_GATE        {DEFAULT_GATE}            merge.rs")
    print(f"  REGULARISER_RADIUS  {REGULARISER_RADIUS}              merge.rs")
    print(f"  WINDOW_RADIUS       {WINDOW_RADIUS}             focus.rs")
    print(f"  SIGMA_EPS           {SIGMA_EPS}          focus.rs")
    print(f"  gain_divisor        {GAIN_DIVISOR}          profile.rs")
    print(f"  base_iso            {BASE_ISO}          profile.rs")
    print(f"  read_noise_e_low    {READ_NOISE_E_LOW}            profile.rs")
    print(f"  read_noise_e_high   {READ_NOISE_E_HIGH}          profile.rs")
    print(f"  second_base_iso     {SECOND_BASE_ISO}          profile.rs")
    print(f"  black / white       {BLACK:.0f} / {WHITE:.0f}     profile.rs", flush=True)


# ---------------------------------------------------------------- operator ---


def box_clamped(a, r):
    """Mean over the (2r+1)^2 window intersected with the plane (boxfilter.rs).

    Summed-area construction in float64.
    """
    a = np.asarray(a, dtype=np.float64)
    h, w = a.shape
    s = np.zeros((h + 1, w + 1), dtype=np.float64)
    np.cumsum(a, axis=0, out=s[1:, 1:])
    np.cumsum(s[1:, 1:], axis=1, out=s[1:, 1:])
    y0 = np.clip(np.arange(h) - r, 0, h)
    y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w)
    x1 = np.clip(np.arange(w) + r + 1, 0, w)
    total = (
        s[np.ix_(y1, x1)] - s[np.ix_(y0, x1)] - s[np.ix_(y1, x0)] + s[np.ix_(y0, x0)]
    )
    cnt = (y1 - y0)[:, None] * (x1 - x0)[None, :]
    return total / cnt


def sobel_components(a):
    """Replicate-clamped 3x3 Sobel, scaled by 1/8, exactly as focus.rs does.

    focus.rs indexes its closure as `at(dx, dy)`; this uses `at(dy, dx)`, so the
    two argument orders are transposed relative to each other and the bodies
    below are written out in this file's own convention.
    """
    p = np.pad(np.asarray(a, dtype=np.float64), 1, mode="edge")
    h, w = a.shape

    def at(dy, dx):
        return p[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]

    gx = at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1)
    gy = at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1)
    return SOBEL_SCALE * gx, SOBEL_SCALE * gy


def sobel_mag(a):
    """|grad| exactly as focus.rs::gradient_magnitude computes it."""
    gx, gy = sobel_components(a)
    return np.hypot(gx, gy)


def gain(iso):
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def read_noise_e(iso):
    return READ_NOISE_E_HIGH if iso >= SECOND_BASE_ISO else READ_NOISE_E_LOW


def plane_variance(signal_dn, iso):
    """noise.rs: var = gain*max(S,0) + (read_noise_e*gain)^2, per CFA plane."""
    g = gain(iso)
    rd = read_noise_e(iso) * g
    return g * np.maximum(signal_dn, 0.0) + rd * rd


def green_luma_sigma(luma_dn, iso):
    """noise.rs::green_luma_sigma -- sqrt(0.25*(var_G1 + var_G2))."""
    v = plane_variance(luma_dn, iso)
    return np.sqrt(0.25 * (v + v))


def focus_field(luma, iso=None, sigma=None):
    """Windowed Tenengrad normalised by the per-pixel luma sigma (focus.rs)."""
    if sigma is None:
        sigma = green_luma_sigma(luma, iso)
    f = box_clamped(sobel_mag(luma), WINDOW_RADIUS)
    return f / np.maximum(sigma, SIGMA_EPS)


def regularised(luma, iso=None, sigma=None):
    return box_clamped(focus_field(luma, iso, sigma), REGULARISER_RADIUS)


def interior(a, inset=INSET):
    return a[inset:-inset, inset:-inset]


# -------------------------------------------------------------------- I/O ---


def raw_visible(path):
    import rawpy

    with rawpy.imread(path) as rr:
        return np.array(rr.raw_image_visible, dtype=np.float64)


def luma_from_raw(v):
    h = (v.shape[0] // 2) * 2
    w = (v.shape[1] // 2) * 2
    g1 = v[0:h:2, 1:w:2]
    g2 = v[1:h:2, 0:w:2]
    return 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))


def luma_of(path):
    return luma_from_raw(raw_visible(path))


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        tags = exifread.process_file(fh, stop_tag="EXIF ISOSpeedRatings", details=False)
    for key in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if key in tags:
            v = tags[key].values
            return float(v[0] if isinstance(v, list) else v)
    raise SystemExit(f"no ISO in EXIF: {path}")


def stack_files(stack):
    d = pathlib.Path(CORPUS) / stack
    return sorted(str(p) for p in d.iterdir() if p.suffix.upper() == ".ARW")


# ------------------------------------------------------------- statistics ---


class Welford:
    """Streaming per-pixel mean/variance, so no arm has to hold a cube."""

    def __init__(self, shape):
        self.n = 0
        self.mean = np.zeros(shape, dtype=np.float64)
        self.m2 = np.zeros(shape, dtype=np.float64)

    def push(self, x):
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self.m2 += d * (x - self.mean)

    def sd(self):
        if self.n < 2:
            raise ValueError("need >= 2 samples")
        return np.sqrt(self.m2 / (self.n - 1))


def summarise(sd, label, crate=None):
    crate = FOCUS_NOISE_SD if crate is None else crate
    flat = np.asarray(sd, dtype=np.float64).ravel()
    q1, q2, q3 = np.percentile(flat, [25, 50, 75])
    return {
        "label": label,
        "n_px": int(flat.size),
        "mean": float(flat.mean()),
        "median": float(q2),
        "p05": float(np.percentile(flat, 5)),
        "p95": float(np.percentile(flat, 95)),
        "iqr_rel": float((q3 - q1) / q2),
        "rho": float(flat.mean() / crate),
        "rho_median": float(q2 / crate),
    }


def print_row(s):
    print(
        f"  {s['label']:<22} {s['mean']:>10.6f} {s['median']:>10.6f}"
        f" {s['p05']:>9.6f} {s['p95']:>9.6f} {s['iqr_rel']:>8.4f} {s['rho']:>8.4f}",
        flush=True,
    )


def print_header():
    print(
        f"  {'arm':<22} {'SD mean':>10} {'SD med':>10} {'p05':>9} {'p95':>9}"
        f" {'IQR/med':>8} {'rho':>8}"
    )
    print("  " + "-" * 76)
