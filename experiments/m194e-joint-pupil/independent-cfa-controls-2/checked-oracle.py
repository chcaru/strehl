"""Independent scalar conversion reader; not a model or emission authority.

Uses Python scalar arithmetic, an explicit even-tie decision and struct's u16
reader. White-rail admission is reported separately until the emitter's exact
endpoint contract is pinned. No receipt is accepted or published here.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct

import numpy as np

SHAPE = (48, 64)
FACTORS = (0.75, 1.0, 0.6)
BLACK = 512.0
GAIN = 0.25
WHITE = 15360.0


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def channel(x, y):
    if type(x) is not int or type(y) is not int or x < 0 or y < 0:
        raise ValueError("native indices must be nonnegative integers")
    return (0 if x % 2 == 0 else 1) if y % 2 == 0 else (1 if x % 2 == 0 else 2)


def even_integer(value):
    """Round a finite real scalar without numpy.rint or Python round."""
    if isinstance(value, (bool, complex, str)):
        raise ValueError("DN must be a real scalar")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("nonfinite DN")
    lower = math.floor(value)
    fraction = value - lower
    return lower + int(fraction > 0.5 or (fraction == 0.5 and lower % 2 != 0))


def validate_float_plane(array):
    if not isinstance(array, np.ndarray) or array.shape != SHAPE:
        raise ValueError("expected one 48 by 64 array")
    if array.dtype.str != "<f8":
        raise ValueError("expected little-endian f64")
    if not np.isfinite(array).all():
        raise ValueError("nonfinite electron values")
    if (array < 0).any():
        raise ValueError("negative electron values")


def read_float(path):
    with Path(path).open("rb") as handle:
        array = np.load(handle, allow_pickle=False)
        if handle.read(1):
            raise ValueError("trailing data after the NPY array")
    validate_float_plane(array)
    return array


def read_raw(path):
    payload = Path(path).read_bytes()
    size = SHAPE[0] * SHAPE[1]
    if len(payload) != 2 * size:
        raise ValueError("CFA must contain exactly 6144 bytes")
    return np.array(struct.unpack("<" + str(size) + "H", payload), dtype="<u2").reshape(SHAPE)


def convert(scalar):
    """Exact conversion of supplied f64 values, not approximate optical truth.

    Operation order: Python float(e)*factor, then *gain, then +black.
    Counts white-endpoint/over-white cases without deciding pending rail policy.
    """
    validate_float_plane(scalar)
    expected = np.empty(SHAPE, dtype="<f8")
    codes = np.empty(SHAPE, dtype="<u2")
    margins = [math.inf] * 3
    uncertain = [0] * 3
    quantization = [0.0] * 3
    at_white = 0
    over_white = 0
    for y in range(SHAPE[0]):
        for x in range(SHAPE[1]):
            c = channel(x, y)
            e = float(scalar[y, x]) * FACTORS[c]
            dn = BLACK + GAIN * e
            if not math.isfinite(e) or not math.isfinite(dn):
                raise ValueError("overflow in conversion")
            code = even_integer(dn)
            if not 0 <= code <= 65535:
                raise ValueError("conversion outside u16 storage")
            expected[y, x] = e
            codes[y, x] = code
            margin = abs(dn - math.floor(dn) - 0.5)
            margins[c] = min(margins[c], margin)
            uncertain[c] += int(margin <= 0.004 * GAIN * FACTORS[c])
            quantization[c] = max(quantization[c], abs(code - dn))
            at_white += int(dn == WHITE)
            over_white += int(dn > WHITE)
    return expected, codes, {
        "minimum_half_integer_margin_dn_rgb": margins,
        "within_optical_discrepancy_allowance_rgb": uncertain,
        "maximum_quantization_error_dn_rgb": quantization,
        "at_white_unquantized": at_white,
        "over_white_unquantized": over_white,
        "rail_endpoint_admission": "deferred to pinned emitter contract",
    }


def compare_files(scalar_path, expected_path, raw_path):
    scalar = read_float(scalar_path)
    observed_expected = read_float(expected_path)
    observed_raw = read_raw(raw_path)
    expected, codes, summary = convert(scalar)
    different_float = observed_expected.view("<u8") != expected.view("<u8")
    different_code = observed_raw != codes
    if different_float.any() or different_code.any():
        raise ValueError(
            f"actual conversion mismatch: expected-electron samples={int(different_float.sum())}, "
            f"CFA samples={int(different_code.sum())}"
        )
    return {
        "sample_count": SHAPE[0] * SHAPE[1],
        "scalar_sha256": sha256(scalar_path),
        "expected_cfa_sha256": sha256(expected_path),
        "cfa_sha256": sha256(raw_path),
        **summary,
    }
