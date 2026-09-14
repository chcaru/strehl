"""Small diagnostic only: M95 CDIFF and fixed green-quincunx Lanczos3 + CDIFF.

Inputs are normalized, WB-applied RGGB f32 patches with an even sensor origin.
A keeps supplied current MHC green. B never reads R/B while estimating green.
B sacrifices genuine green frequencies outside |fx|+|fy| <= 0.5 cycles/native px;
finite Lanczos3 is an approximation even inside that diamond. No quality claim.
Trim at least 6 native pixels for a boundary-independent comparison of both arms.
"""
import json
from pathlib import Path
import numpy as np


def _mosaic(cfa):
    a = np.asarray(cfa, dtype=np.float32)
    assert a.ndim == 2 and min(a.shape) >= 2 and all(n % 2 == 0 for n in a.shape)
    assert np.isfinite(a).all()
    return a


def _reflect(i, n):
    """Whole-sample reflection: period 2(n-1), so CFA parity is unchanged."""
    j = np.asarray(i) % (2 * (n - 1))
    return np.minimum(j, 2 * (n - 1) - j)


def _masks(shape):
    y, x = np.indices(shape)
    return (y % 2 == 0) & (x % 2 == 0), (y + x) % 2 == 1, (y % 2 == 1) & (x % 2 == 1)


def _bilinear_difference(d):
    # M95 K_LATTICE = outer([1,2,1],[1,2,1])/4, sparse R or B input.
    h, w = d.shape
    y, x = np.indices(d.shape)
    result = np.zeros_like(d)
    for dy, wy in ((-1, 1), (0, 2), (1, 1)):
        for dx, wx in ((-1, 1), (0, 2), (1, 1)):
            weight = np.float32(wy * wx) * np.float32(0.25)
            result += d[_reflect(y + dy, h), _reflect(x + dx, w)] * weight
    return result


def cdiff(cfa, green):
    """M95 bilinear colour differences around supplied green; known sites exact."""
    a = _mosaic(cfa)
    g = np.array(green, dtype=np.float32, copy=True)
    assert g.shape == a.shape and np.isfinite(g).all()
    r, known_g, b = _masks(a.shape)
    g[known_g] = a[known_g]
    result = np.empty((*a.shape, 3), dtype=np.float32)
    result[..., 1] = g
    for channel, mask in ((0, r), (2, b)):
        difference = np.where(mask, a - g, np.float32(0))
        result[..., channel] = g + _bilinear_difference(difference)
        # Avoid subtraction/addition roundoff at measured sensor samples.
        result[..., channel][mask] = a[mask]
    return result


def mhc_cdiff(cfa, mhc_rgb):
    """Arm A: use the captured current MHC green, with no replacement MHC model."""
    a = _mosaic(cfa)
    rgb = np.asarray(mhc_rgb, dtype=np.float32)
    assert rgb.shape == (*a.shape, 3) and np.isfinite(rgb).all()
    _, known_g, _ = _masks(a.shape)
    assert np.array_equal(rgb[..., 1][known_g].view(np.uint32), a[known_g].view(np.uint32))
    return cdiff(a, rgb[..., 1])


def half_phase_weights():
    """Six normalized f32 Lanczos3 taps at +/-0.5, +/-1.5, +/-2.5."""
    t = np.array([-2.5, -1.5, -0.5, 0.5, 1.5, 2.5], dtype=np.float32)
    p = np.float32(np.pi) * t
    p3 = p / np.float32(3)
    weights = (np.sin(p) / p) * (np.sin(p3) / p3)
    return weights / np.sum(weights, dtype=np.float32)


def quincunx_green(cfa):
    """Arm B green: separable half-phase reconstruction in the rotated lattice.

    u=(x+y-1)/2, v=(x-y-1)/2; green sites have integral u,v. At an
    R/B site both coordinates are half-integral. Inverse x=u+v+1,y=u-v
    turns 36 green-only taps into integral native offsets below.
    """
    a = _mosaic(cfa)
    _, known_g, _ = _masks(a.shape)
    y, x = np.nonzero(~known_g)
    estimates = np.zeros(y.shape, dtype=np.float32)
    weights = half_phase_weights()
    offsets2 = (-5, -3, -1, 1, 3, 5)
    for i, du2 in enumerate(offsets2):
        for j, dv2 in enumerate(offsets2):
            sx = _reflect(x + (du2 + dv2) // 2, a.shape[1])
            sy = _reflect(y + (du2 - dv2) // 2, a.shape[0])
            estimates += a[sy, sx] * (weights[i] * weights[j])
    result = a.copy()
    result[y, x] = estimates
    return result


def quincunx_cdiff(cfa):
    return cdiff(cfa, quincunx_green(cfa))


def sample_equality(cfa, rgb):
    a = _mosaic(cfa)
    return {name: bool(np.array_equal(rgb[..., c][mask].view(np.uint32), a[mask].view(np.uint32)))
            for c, (name, mask) in enumerate(zip(("R", "G", "B"), _masks(a.shape)))}


def write_candidates(cfa_path, mhc_rgb_path, width, height, out_dir):
    """Save only candidate camera RGB f32 plus a literal known-sample receipt."""
    a = np.fromfile(cfa_path, dtype="<f4").reshape(height, width)
    mhc = np.fromfile(mhc_rgb_path, dtype="<f4").reshape(height, width, 3)
    out = Path(out_dir)
    out.mkdir(exist_ok=False)
    receipt = {"shape": [height, width, 3], "trim": 6, "dtype": "little-endian f32 camera RGB", "arms": {}}
    for name, rgb in (("mhc-cdiff", mhc_cdiff(a, mhc)), ("quincunx-cdiff", quincunx_cdiff(a))):
        equality = sample_equality(a, rgb)
        assert all(equality.values()) and rgb.dtype == np.float32 and np.isfinite(rgb).all()
        with (out / (name + "-camera-rgb.f32")).open("xb") as stream:
            stream.write(rgb.astype("<f4", copy=False).tobytes())
        receipt["arms"][name] = {"known_samples_bit_exact": equality}
    with (out / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt
