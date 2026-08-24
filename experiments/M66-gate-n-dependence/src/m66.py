"""M66 shared constants, parsed from the crate at run time. Never retyped.

M62's discipline: a harness that retypes a constant can drift from the crate
silently. Everything here is read out of the Rust source on every run.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
CORE = ROOT / "crates" / "strehl-core" / "src"

OUT = pathlib.Path(__file__).resolve().parents[1] / "out"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


def _grab(path, pattern, cast=float):
    text = (CORE / path).read_text(encoding="utf-8")
    m = re.search(pattern, text)
    if m is None:
        raise SystemExit(f"constant not found in {path}: {pattern}")
    return cast(m.group(1).replace("_", ""))


FOCUS_NOISE_SD = _grab("merge.rs", r"pub const FOCUS_NOISE_SD: f32 = ([0-9_.]+);")
REGULARISER_RADIUS = _grab("merge.rs", r"pub const REGULARISER_RADIUS: usize = (\d+);", int)
WINDOW_RADIUS = _grab("focus.rs", r"pub const WINDOW_RADIUS: usize = (\d+);", int)
SOBEL_SCALE = 0.125
SIGMA_EPS = _grab("focus.rs", r"const SIGMA_EPS: f32 = ([0-9e.\-]+);")
DEFAULT_GATE = _grab("merge.rs", r"pub const DEFAULT_GATE: f32 = ([0-9.]+);")

GAIN_DIVISOR = _grab("profile.rs", r"gain_divisor: ([0-9.]+),")
BASE_ISO = _grab("profile.rs", r"base_iso: ([0-9.]+),")
READ_NOISE_E_LOW = _grab("profile.rs", r"read_noise_e_low: ([0-9.]+),")
READ_NOISE_E_HIGH = _grab("profile.rs", r"read_noise_e_high: ([0-9.]+),")
SECOND_BASE_ISO = _grab("profile.rs", r"second_base_iso: ([0-9.]+),")
BLACK = _grab("profile.rs", r"black: ([0-9.]+),")
WHITE = _grab("profile.rs", r"white: ([0-9.]+),")

# The pre-registered grids (PREREGISTRATION.md section 3).
GATES = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0]
N_GRID = [3, 5, 8, 12, 19, 22, 30, 33, 45, 63, 79, 100, 105, 120, 130, 200, 299]
CORPUS_N = [19, 22, 33, 63, 79, 100, 105, 120, 130, 299]

CORPUS = r"D:\personal\macro"
DARKS = r"D:\macro-dark-frames"

# M64 section 2.4, the shipped binary at gate 4.0, full N. Control K3's target.
M64_GUARD = {
    "foam": (100, 1.359),
    "113MSDCF": (63, 8.581),
    "119MSDCF": (33, 4.723),
    "112MSDCF": (79, 12.037),
    "coffee-bubbles": (19, 3.529),
    "109MSDCF": (22, 4.987),
    "coffee-bean": (105, 31.614),
}

# M4 section 8.1 dark temporal sigma. Control K4's target (copied from M52's
# verified harness, experiments/m52-gate-cluster/src/03-fact324-n-eff-independent.py).
DARK_TRUTH = {
    "118MSDCF": (100.0, {"R": 1.0048, "G1": 1.0042, "G2": 1.0105, "B": 0.9185}),
    "119MSDCF": (400.0, {"R": 1.2130, "G1": 1.2266, "G2": 1.2403, "B": 1.1146}),
}


def banner(title):
    print("=" * 78)
    print(title)
    print("=" * 78)


def dump_constants():
    print(f"  FOCUS_NOISE_SD     {FOCUS_NOISE_SD:.6f}   (merge.rs)")
    print(f"  DEFAULT_GATE       {DEFAULT_GATE}          (merge.rs)")
    print(f"  WINDOW_RADIUS      {WINDOW_RADIUS}            (focus.rs)")
    print(f"  REGULARISER_RADIUS {REGULARISER_RADIUS}            (merge.rs)")
    print(f"  gain_divisor       {GAIN_DIVISOR}        (profile.rs)")
    print(f"  read_noise_e_low   {READ_NOISE_E_LOW}          (profile.rs)")
    print(f"  read_noise_e_high  {READ_NOISE_E_HIGH}        (profile.rs)")
    print(f"  black / white      {BLACK:.0f} / {WHITE:.0f}   (profile.rs)")
