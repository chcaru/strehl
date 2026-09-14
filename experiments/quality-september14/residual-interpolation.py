"""Fixed published RI, with explicit f32 and unclipped RAW-headroom adaptation.

BSD-2-Clause upstream: https://www.ipol.im/pub/art/2021/358/
See residual-interpolation-reference/source/LICENSE.txt and float32-adaptation.diff.
Input: normalized WB RGGB f32 at even native origin. No RAW decoding or writer.
sigma=1 is spatial Gaussian width, not sensor noise. Guided eps=0 and all other
published RI settings remain fixed. Conservative boundary-independent trim:32.
Reflect-padding32/cropping32 keeps returned sites away from the reference's
phase-breaking replicated residual boundary; the full-output guard is unchanged.
"""
from pathlib import Path
import sys
import numpy as np

SOURCE = Path(__file__).with_name("residual-interpolation-reference") / "float32-ri"
_names = ("demosaic_RI", "mosaic_bayer", "RIgreen_interpolation", "RIGuidefilterResidual",
          "RIguidedfilter3gf", "RIred_interpolation", "RIblue_interpolation", "RIHaResidual", "filtertools")
for _name in _names:
    if _name in sys.modules:
        assert Path(sys.modules[_name].__file__).resolve().parent == SOURCE.resolve(), "RI module collision"
sys.path.insert(0, str(SOURCE))
try:
    from demosaic_RI import demosaic_RI
finally:
    sys.path.pop(0)

LAST_DIAGNOSTIC = None


def ri(cfa):
    """Return camera RGB f32; measured samples restored only after roundoff guard."""
    global LAST_DIAGNOSTIC
    a = np.asarray(cfa)
    assert a.dtype == np.float32 and a.ndim == 2 and min(a.shape) >= 2
    assert all(n % 2 == 0 for n in a.shape) and np.isfinite(a).all()
    # Whole-sample reflection preserves parity; even pad32 preserves RGGB origin.
    work = np.pad(a, ((32, 32), (32, 32)), mode="reflect")
    scaled = work * np.float32(255)
    source = np.zeros((*work.shape, 3), dtype=np.float32)
    y, x = np.indices(work.shape)
    masks = ((y % 2 == 0) & (x % 2 == 0), (y + x) % 2 == 1,
             (y % 2 == 1) & (x % 2 == 1))
    for c, mask in enumerate(masks):
        source[..., c][mask] = scaled[mask]
    rgb = demosaic_RI(source, "rggb", np.float32(1), "RI")
    assert rgb.dtype == np.float32 and rgb.shape == source.shape and np.isfinite(rgb).all()
    rgb = rgb[32:-32, 32:-32].copy()
    scaled = scaled[32:-32, 32:-32]
    masks = tuple(mask[32:-32, 32:-32] for mask in masks)
    # RI adds each known residual to its tentative value: algebraic identity.
    # Bound cancellation roundoff before restoring the original normalized bits.
    scale = max(np.float32(1), np.max(np.abs(rgb)), np.max(np.abs(scaled)))
    bound = np.float32(16) * np.float32(np.finfo(np.float32).eps) * scale
    errors = [np.max(np.abs(rgb[..., c][mask] - scaled[mask])) for c, mask in enumerate(masks)]
    assert all(error <= bound for error in errors), "RI changed a measured sample beyond roundoff"
    rgb /= np.float32(255)
    changed = [int(np.count_nonzero(rgb[..., c][mask].view(np.uint32) != a[mask].view(np.uint32)))
               for c, mask in enumerate(masks)]
    for c, mask in enumerate(masks):
        rgb[..., c][mask] = a[mask]
        assert np.array_equal(rgb[..., c][mask].view(np.uint32), a[mask].view(np.uint32))
    LAST_DIAGNOSTIC = {"algorithm": "RI", "sigma_spatial": 1, "guided_eps": 0,
        "reference_scale": 255, "clip_adaptation": "all reference [0,255] clips disabled",
        "boundary_adaptation": "parity-preserving reflect-pad32 before RI, crop32 after; every returned site guarded",
        "pre_restore_max_error_reference_units_rgb": [float(e) for e in errors],
        "roundoff_bound_reference_units": float(bound), "restored_sample_count_rgb": changed,
        "known_samples_bit_exact": True, "dtype": str(rgb.dtype), "trim": 32}
    return rgb
