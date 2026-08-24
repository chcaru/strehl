"""M77 shared instrument. Constants parsed from the crate at run time, never retyped.

Self-contained on purpose: M77 must reproduce without another milestone's
experiment directory on the path.

Re-implements two shipped statistics, each cited at its source:

    contam = hp_sd / (HP_NOISE_GAIN * model_sigma)     strehl-core/src/flat_ratio.rs
    cg     = sqrt(max(0, raw_rms^2 - noise_rms^2))     strehl-cli/src/merge_cmd.rs:305

The plane convention is the CLI's: one output pixel per sensor quad, green luma
= 0.5 * ((G1 - black) + (G2 - black)) clamped at zero, at half the sensor's
linear resolution (plane.rs; `strehl stack` help, "BINNED, NOT DEMOSAICED").
"""

import pathlib
import re

import numpy as np
from scipy.ndimage import uniform_filter

ROOT = pathlib.Path(__file__).resolve().parents[3]
CORE = ROOT / "crates" / "strehl-core" / "src"
CLI = ROOT / "crates" / "strehl-cli" / "src"
EXP = pathlib.Path(__file__).resolve().parents[1]
OUT = EXP / "out"

CORPUS = r"D:\personal\macro"

# Registered in PREREGISTRATION.md section 5, before any result existed.
STACKS = ["wrapped-text-1", "109MSDCF", "coffee-bean", "foam", "bee-1"]
GATES = [0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]


def _grab(base, path, pattern, cast=float):
    text = (base / path).read_text(encoding="utf-8")
    m = re.search(pattern, text)
    if m is None:
        raise SystemExit(f"constant not found in {path}: {pattern}")
    return cast(m.group(1).replace("_", ""))


DEFAULT_GATE = _grab(CORE, "merge.rs", r"pub const DEFAULT_GATE: f32 = ([0-9.]+);")
FOCUS_NOISE_SD = _grab(CORE, "merge.rs", r"pub const FOCUS_NOISE_SD: f32 = ([0-9_.]+);")
HP_BOX_SIDE = _grab(CORE, "flat_ratio.rs", r"pub const HP_BOX_SIDE: usize = (\d+);", int)
HP_BOX_RADIUS = HP_BOX_SIDE // 2
HP_NOISE_GAIN = float(np.sqrt(1.0 - 1.0 / (HP_BOX_SIDE * HP_BOX_SIDE)))

DETAIL_COLLAPSE_FLOOR = _grab(
    CLI, "merge_cmd.rs", r"const DETAIL_COLLAPSE_FLOOR: f64 = ([0-9.]+);"
)
DETAIL_RISE_FLAG = _grab(CLI, "merge_cmd.rs", r"const DETAIL_RISE_FLAG: f64 = ([0-9.]+);")

GAIN_DIVISOR = _grab(CORE, "profile.rs", r"gain_divisor: ([0-9.]+),")
BASE_ISO = _grab(CORE, "profile.rs", r"base_iso: ([0-9.]+),")
READ_NOISE_E_LOW = _grab(CORE, "profile.rs", r"read_noise_e_low: ([0-9.]+),")
READ_NOISE_E_HIGH = _grab(CORE, "profile.rs", r"read_noise_e_high: ([0-9.]+),")
SECOND_BASE_ISO = _grab(CORE, "profile.rs", r"second_base_iso: ([0-9.]+),")
BLACK = _grab(CORE, "profile.rs", r"black: ([0-9.]+),")


def banner(title):
    print("=" * 78)
    print(title)
    print("=" * 78)


def dump_constants():
    print(f"  DEFAULT_GATE          {DEFAULT_GATE:<12g} merge.rs")
    print(f"  FOCUS_NOISE_SD        {FOCUS_NOISE_SD:<12g} merge.rs")
    print(f"  HP_BOX_SIDE           {HP_BOX_SIDE:<12d} flat_ratio.rs")
    print(f"  HP_NOISE_GAIN         {HP_NOISE_GAIN:<12.6f} derived sqrt(1-1/w^2)")
    print(f"  DETAIL_COLLAPSE_FLOOR {DETAIL_COLLAPSE_FLOOR:<12g} merge_cmd.rs")
    print(f"  DETAIL_RISE_FLAG      {DETAIL_RISE_FLAG:<12g} merge_cmd.rs")
    print(f"  black                 {BLACK:<12g} profile.rs")


# ------------------------------------------------------------------- noise ---


def gain_dn_per_e(iso):
    """profile.rs:205 -- iso.max(base_iso) / gain_divisor."""
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def read_noise_e(iso):
    return READ_NOISE_E_HIGH if iso >= SECOND_BASE_ISO else READ_NOISE_E_LOW


def plane_variance(signal_dn, iso):
    """sigma^2(S) = g*S + (RN_e*g)^2, in DN."""
    g = gain_dn_per_e(iso)
    rn = read_noise_e(iso) * g
    return g * np.maximum(signal_dn, 0.0) + rn * rn


def green_luma_sigma(luma_dn, iso):
    """noise.rs::green_luma_sigma -- sqrt(0.25*(var_G1 + var_G2))."""
    v = plane_variance(luma_dn, iso)
    return np.sqrt(0.25 * (v + v))


def green_luma_sigma_map(a, iso):
    return green_luma_sigma(a, iso)


# --------------------------------------------------------------------- I/O ---


def raw_visible(path):
    import rawpy

    with rawpy.imread(path) as rr:
        return np.array(rr.raw_image_visible, dtype=np.float64)


def green_luma_plane(path):
    """0.5 * ((G1-black)+ + (G2-black)+), half linear resolution."""
    v = raw_visible(path)
    h = (v.shape[0] // 2) * 2
    w = (v.shape[1] // 2) * 2
    g1 = v[0:h:2, 1:w:2]
    g2 = v[1:h:2, 0:w:2]
    return 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))


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


def box_mean(a, radius):
    """Uniform mean over a (2r+1)^2 box. Only the valid interior is ever read."""
    return uniform_filter(a, size=2 * radius + 1, mode="nearest")
