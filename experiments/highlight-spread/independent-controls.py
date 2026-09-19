"""Independent coordinate/bin controls. Root executes; no photographs or RAW.

The artificial rectangles establish operator sensitivity, not a physical PSF.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("highlight_spread_measure", HERE / "measure.py")
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)
PIVOT = complex(3516, 2344)
CROP = complex(56, 38)


def bits(a: complex, b: complex) -> list[str]:
    return [struct.pack(">d", v).hex() for v in (a.real, a.imag, b.real, b.imag)]


def forward(z: complex, a: complex, b: complex) -> complex:
    return PIVOT + a * (z + CROP - PIVOT) + 2 * b


def inverse(z: complex, a: complex, b: complex) -> complex:
    return (z - PIVOT - 2 * b) / a + PIVOT - CROP


def reference(rgb, origin, a, b, core, direction):
    """Scalar enumeration; explicit physical intervals and complex inverse."""
    totals = np.zeros((3, 48, 3), np.float64)
    counts = np.zeros((3, 48), np.int64)
    unit = complex(*direction) / abs(complex(*direction))
    for y in range(rgb.shape[0]):
        for x in range(rgb.shape[1]):
            z = inverse(complex(origin[0] + x, origin[1] + y), a, b) - complex(*core)
            relative = z / unit
            s, t = relative.real, relative.imag
            if not (-24 <= s < 72 and -12 <= t < 12):
                continue
            strip = 0 if t < -4 else 1 if t < 4 else 2
            index = math.floor((s + 24) / 2)
            counts[strip, index] += 1
            totals[strip, index] += rgb[y, x]
    means = np.full_like(totals, np.nan)
    np.divide(totals, counts[..., None], out=means, where=counts[..., None] != 0)
    return means, counts


def coordinate_and_linear_bins():
    a, b = complex(1.007, -0.021), complex(3.125, -2.375)
    encoded = bits(a, b)
    error = 0.0
    for point in [complex(0.25, -3.75), complex(120.4, 85.7), complex(3400.75, 2200.25)]:
        source = forward(point, a, b)
        actual = complex(*M.map_source_to_output(source.real, source.imag, encoded))
        actual_source = complex(*M.map_output_to_source(point.real, point.imag, encoded))
        error = max(error, abs(actual - point), abs(actual_source - source))
    assert error < 2e-12, error
    # Literal identity checks independently expose crop offset and pixel-centre
    # conventions. A hidden +0.5 or factor-two translation cannot pass these.
    identity = bits(1 + 0j, 0j)
    assert tuple(M.map_source_to_output(56, 38, identity)) == (0.0, 0.0)
    translated = bits(1 + 0j, complex(2, -3))
    assert tuple(M.map_output_to_source(0, 0, translated)) == (60.0, 32.0)
    core, direction = (120.4, 85.7), (3.0, 4.0)
    centre = forward(complex(*core), a, b)
    origin = [math.floor(centre.real) - 112, math.floor(centre.imag) - 112]
    yy, xx = np.indices((224, 224))
    x, y = xx + origin[0], yy + origin[1]
    rgb = np.stack([14000 + 3*x + 7*y, 22000 - 5*x + 2*y, 30000 + 2*x - 3*y], axis=-1)
    assert rgb.min() >= 0 and rgb.max() < 65536
    rgb = rgb.astype(np.uint16)
    expected, counts = reference(rgb, origin, a, b, core, direction)
    actual, actual_counts = M.bin_profile(rgb, origin, encoded, core, direction)
    assert np.all(counts > 0)
    np.testing.assert_array_equal(actual_counts, counts)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=0.008, equal_nan=True)
    # This wrong native-translation convention must disagree materially.
    wrong = inverse(forward(complex(*core), a, b), a, b/2)
    assert abs(wrong - complex(*core)) > 3.0
    return {"maximum_coordinate_error": error, "checked_colour_means": int(actual.size),
            "all_144_bins_populated": True, "wrong_translation_rejected": True}


def cardinal_fixture():
    origin = [112, 104]
    core = (80.25, 90.25)
    yy, xx = np.indices((120, 120))
    ox, oy = xx + origin[0] - 56, yy + origin[1] - 38
    rgb = np.stack([1000 + 3*ox + 7*oy, 7000 + 2*ox - oy, 9000 - ox + 3*oy], axis=-1).astype(np.uint16)
    return rgb, origin, core, ox-core[0], oy-core[1]


def signed_axes_and_empty_bins():
    rgb, origin, core, _, _ = cardinal_fixture()
    encoded = bits(1+0j, 0j)
    means, counts = M.bin_profile(rgb, origin, encoded, core, (1, 0))
    reversed_means, reversed_counts = M.bin_profile(rgb, origin, encoded, core, (-1, 0))
    # Only the shared signed interval [-24,24) is reciprocal. Quarter-pixel
    # origin keeps every sample off the half-open bin and strip boundaries.
    np.testing.assert_array_equal(reversed_counts[:, :24], counts[::-1, :24][:, ::-1])
    np.testing.assert_array_equal(reversed_means[:, :24], means[::-1, :24][:, ::-1])
    moved, moved_counts = M.bin_profile(rgb, origin, encoded, (core[0], core[1]+8), (1, 0))
    np.testing.assert_array_equal(moved_counts[1], counts[2])
    np.testing.assert_array_equal(moved[1], means[2])
    empty, empty_counts = M.bin_profile(np.ones((2, 3, 3), np.uint16), [600, 700], encoded, core, (1, 0))
    assert np.all(empty_counts == 0) and np.isnan(empty).all()
    constant, constant_counts = M.bin_profile(np.full_like(rgb, 3210), origin, encoded, core, (1, 0))
    assert np.all(constant_counts > 0) and np.all(constant == 3210)
    # Full bin population does not establish the separately required source
    # margin. Test the exact inclusive support boundary and one outside point.
    M.support_inside([110, 102], (124, 124, 3), encoded, (80, 90), (1, 0))
    refused = False
    try:
        M.support_inside([110, 102], (124, 124, 3), encoded, (79.999999, 90), (1, 0))
    except ValueError:
        refused = True
    assert refused, "incomplete two-pixel source margin accepted"
    return {"reversed_overlap_bins": 72, "side_strip_displacement_bins": 48,
            "empty_bins_nan_with_zero_count": True, "constant_field_unchanged": True,
            "inclusive_source_margin_and_outside_refusal": True}


def stationary_and_spreading_profiles():
    rgb, origin, core, s, t = cardinal_fixture()
    rgb.fill(0)
    compact = (np.abs(s) < 4) & (np.abs(t) < 4)
    wide = (np.abs(s) < 16) & (np.abs(t) < 4)
    rgb[compact] = [12000, 8000, 4000]
    expanded = np.zeros_like(rgb)
    expanded[wide] = [3000, 2000, 1000]
    encoded = bits(1+0j, 0j)
    p, n = M.bin_profile(rgb, origin, encoded, core, (1, 0))
    bright, n2 = M.bin_profile(rgb*2, origin, encoded, core, (1, 0))
    spread, n3 = M.bin_profile(expanded, origin, encoded, core, (1, 0))
    np.testing.assert_array_equal(n2, n)
    np.testing.assert_array_equal(n3, n)
    np.testing.assert_array_equal(bright, 2*p)
    compact_support = np.flatnonzero(p[1, :, 0] > 0)
    spread_support = np.flatnonzero(spread[1, :, 0] > 0)
    assert len(compact_support) == 4 and len(spread_support) == 16
    np.testing.assert_array_equal(p[1].sum(axis=0), spread[1].sum(axis=0))
    # An unrelated fixed side-strip object enters its own profile. The bins
    # cannot identify it as part of a point's PSF merely because it is nearby.
    mixed = rgb.copy()
    mixed[(s >= 20) & (s < 28) & (t >= 4) & (t < 12)] = [0, 0, 16000]
    mixed_p, mixed_n = M.bin_profile(mixed, origin, encoded, core, (1, 0))
    np.testing.assert_array_equal(mixed_n, n)
    np.testing.assert_array_equal(mixed_p[1], p[1])
    assert np.count_nonzero(mixed_p[2, :, 2]) == 4 and np.count_nonzero(p[2]) == 0
    return {"stationary_amplitude_change_preserves_support": True,
            "compact_nonzero_bins": 4, "spread_nonzero_bins": 16,
            "equal_profile_integral": True, "unrelated_side_object_is_visible": True,
            "scope": "Rectangular operator examples; no physical PSF or quality inference."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"status": "INDEPENDENT_COORDINATE_BIN_CONTROLS_PASS",
              "coordinate_and_linear_bins": coordinate_and_linear_bins(),
              "signed_axes_and_empty_bins": signed_axes_and_empty_bins(),
              "stationary_and_spreading_profiles": stationary_and_spreading_profiles(),
              "reads_originals": False}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
