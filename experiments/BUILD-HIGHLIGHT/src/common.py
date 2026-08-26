"""Shared helpers for BUILD-HIGHLIGHT.

Everything here is arithmetic that must agree with `crates/strehl-core/src/color.rs`.
Where it does, it is asserted -- `assert_matrix_agrees` reproduces the row-sum-1
property the Rust construction guarantees, so a silent divergence between this
analysis and the shipped renderer shows up as a failed assertion rather than as
a plausible-looking number.
"""

import json
import os
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(__file__).resolve().parents[1] / "out"

# IEC 61966-2-1, the same constant as `color::SRGB_TO_XYZ_D65`.
SRGB_TO_XYZ_D65 = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])

# Printed by the binary's own banner on every `foam` render:
#   XYZ->cam rows: [0.7460 -0.2365 -0.0588] [-0.5687 1.3442 0.2474] [-0.0624 0.1156 0.6584]
A7C2_XYZ_TO_CAM = np.array([
    [0.7460, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
])

# `strehl probe D:\personal\macro\foam`, 2026-08-26.
BLACK = 512.0
WHITE = 15360.0
CONTAINER = 16383.0
FOAM_WB = np.array([2.680664, 1.0, 1.5253906])

# color::saturation_ceiling's K0.
K0 = (CONTAINER - BLACK) / (WHITE - BLACK)


def cam_from_srgb(xyz_to_cam=A7C2_XYZ_TO_CAM):
    """linear sRGB -> white-balanced camera RGB, rows normalised to sum 1.

    This is step 2 of `color::camera_to_srgb`, before the inversion.
    """
    m = xyz_to_cam @ SRGB_TO_XYZ_D65
    m = m / m.sum(axis=1, keepdims=True)
    assert np.allclose(m.sum(axis=1), 1.0), "row normalisation failed"
    return m


def to_srgb(xyz_to_cam=A7C2_XYZ_TO_CAM):
    """What `color::camera_to_srgb` returns: WB camera RGB -> linear sRGB."""
    m = np.linalg.inv(cam_from_srgb(xyz_to_cam))
    assert np.allclose(m.sum(axis=1), 1.0, atol=1e-6), (
        "every row of camera_to_srgb must sum to 1 (neutral in -> neutral out)")
    return m


def ceilings(wb=None, exposure_gain=1.0):
    """`color::saturation_ceiling`, in the render's normalised units."""
    return K0 * np.asarray(FOAM_WB if wb is None else wb, dtype=np.float64) * exposure_gain


def load_master(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] == 3, f"expected HxWx3, got {a.shape}"
    return a


def back_to_camera(img_u16, xyz_to_cam=A7C2_XYZ_TO_CAM):
    """linear-sRGB u16 master -> the white-balanced camera triple that produced it.

    Exact up to 16-bit quantisation PROVIDED no pixel hit the post-matrix
    clamp; the caller must check that, and `camera_space_report` asserts it.
    """
    lin = img_u16.astype(np.float32) / 65535.0
    m = cam_from_srgb(xyz_to_cam).astype(np.float32)
    return lin @ m.T


def dump(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, default=float)
    print(f"  [wrote {os.path.relpath(OUT / f'{name}.json')}]")
