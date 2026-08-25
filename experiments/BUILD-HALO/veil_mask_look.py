"""Dump the frozen mask as a picture, because a mask you have not looked at is
an assumption, not a measurement.

This is the check that caught an Otsu failure earlier in this project.  Do not
skip it.  Writes a 3-panel PNG: the scene, the mask, and the mask's boundary
drawn on the scene.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from veil_test import FRAMES, OUT, luma, subject_mask  # noqa: E402


def norm8(a):
    lo, hi = np.percentile(a, [0.5, 99.5])
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)


for subject in (sys.argv[1:] or ["lavendar-cpl", "flower-bud-with-background-fern-cpl"]):
    mask, med = subject_mask(subject)
    g = norm8(med)

    rgb = np.stack([g, g, g], axis=-1)
    shown = rgb.copy()
    shown[mask] = shown[mask] * 0.45 + np.array([0.55, 0.0, 0.0])

    edge = ndimage.binary_dilation(mask, np.ones((3, 3))) & ~ndimage.binary_erosion(mask, np.ones((3, 3)))
    outline = rgb.copy()
    outline[edge] = np.array([1.0, 0.15, 0.0])

    panel = np.concatenate([rgb, shown, outline], axis=1)
    h, w = panel.shape[:2]
    scale = 2100 / w
    img = Image.fromarray((panel * 255).astype(np.uint8))
    img = img.resize((2100, int(h * scale)), Image.LANCZOS)
    p = OUT / f"MASK-{subject}.png"
    img.save(p)
    assert p.read_bytes()[:4] == b"\x89PNG"

    subj = float(np.median(med[mask]))
    d = ndimage.distance_transform_edt(~mask)
    far = float(np.median(med[d > 400]))
    print(f"{subject}: mask {mask.mean():.1%}  subject {subj:.4f}  far bg {far:.4f}  -> {p.name}")
