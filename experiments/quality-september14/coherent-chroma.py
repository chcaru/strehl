"""Diagnostic C: spatially averaged soft H/V green, then the prior M95 CDIFF.

The H/V estimates and raw costs are from this project's green_directional.
BUILD-SHARP's hard per-pixel directional choice lost on flat noise. Here costs
are averaged over a fixed 5x5 same-CFA-phase neighbourhood before soft mixing.
No hard winner, threshold, neutral-colour assumption or production route.
Normalized WB RGGB f32 input, even native origin. Trim >=8 native pixels.
"""
import importlib.util
from pathlib import Path
import numpy as np

_spec = importlib.util.spec_from_file_location("coherent_chroma_shared",
    Path(__file__).with_name("quincunx-chroma.py"))
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)


def _shift(a, dx, dy):
    y, x = np.indices(a.shape)
    return a[_shared._reflect(y + dy, a.shape[0]), _shared._reflect(x + dx, a.shape[1])]


def _phase_mean(a):
    result = np.zeros_like(a)
    for dy in (-4, -2, 0, 2, 4):
        for dx in (-4, -2, 0, 2, 4):
            result += _shift(a, dx, dy)
    return result * (np.float32(1) / np.float32(25))


def coherent_green(cfa):
    a = _shared._mosaic(cfa)
    gl, gr = _shift(a, -1, 0), _shift(a, 1, 0)
    gu, gd = _shift(a, 0, -1), _shift(a, 0, 1)
    lh = np.float32(2) * a - _shift(a, -2, 0) - _shift(a, 2, 0)
    lv = np.float32(2) * a - _shift(a, 0, -2) - _shift(a, 0, 2)
    dh = _phase_mean(np.abs(gl - gr) + np.abs(lh))
    dv = _phase_mean(np.abs(gu - gd) + np.abs(lv))
    horizontal = np.float32(0.5) * (gl + gr) + np.float32(0.25) * lh
    vertical = np.float32(0.5) * (gu + gd) + np.float32(0.25) * lv
    total = dh + dv
    weight = np.full_like(a, np.float32(0.5))
    np.divide(dv, total, out=weight, where=total > np.float32(0))
    green = weight * horizontal + (np.float32(1) - weight) * vertical
    _, known_g, _ = _shared._masks(a.shape)
    green[known_g] = a[known_g]
    return green


def coherent_cdiff(cfa):
    """Return f32 camera RGB with every measured R/G/B sample bit-exact."""
    return _shared.cdiff(cfa, coherent_green(cfa))


def sample_equality(cfa, rgb):
    return _shared.sample_equality(cfa, rgb)
