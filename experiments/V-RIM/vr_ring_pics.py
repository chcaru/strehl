r"""Pixels for the MID-SCALE axis, so the owner can falsify the mid-scale
verdict the same way he can falsify the tight-scale one.

Two artefacts per subject.

  PROFILE STRIP -- the ray-averaged backdrop profile from the silhouette edge
      out to t=+200 px, drawn as an image and stretched so that +/-2% of the
      far field fills the panel from black to white. A ring is a VERTICAL
      BRIGHT BAND somewhere in the left third. The published run claimed
      +3% to +10% bands at t=21..34 px; at this stretch those would be pure
      white and unmissable. A tick row marks t=0,20,...,200.

  BOUNDARY CROP -- a real 1:1 crop straddling the silhouette, subject on the
      left, backdrop on the right, shown twice: as it looks, and with the
      backdrop stretched about its own far level by the same +/-2%. What to
      look for is a bright fringe hugging the silhouette in the right-hand
      panel that is not present in the left.

Nothing here is measured. These are sRGB-encoded for looking at.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
from vrimlib import load_lum, segment                              # noqa: E402

PIC = r"D:\strehl-out\V-RIM\pics"
ARMS = {"deliv": r"D:\strehl-out\V-RIM\ring",
        "ship": r"D:\strehl-out\V-RIM\ring-ship",
        "lin": r"D:\strehl-out\V-RIM\ring-lin"}
DELIV = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
FIVE = ["bee-3-cpl", "flower-bud-alone-cpl",
        "flower-bud-with-background-fern-cpl", "lavendar-cpl", "coffee-bean"]
SPAN = 0.02          # +/- 2% of far fills the panel


def strip(lab):
    rows, labels = [], []
    for arm, d in ARMS.items():
        f = Path(d) / (lab + "-rays.json")
        if not f.exists():
            continue
        j = json.loads(f.read_text())
        if not j.get("straight"):
            continue
        s = j["straight"]
        g = np.asarray(s["grid"], float)
        m = np.asarray(s["med"], float)
        far = float(s["far"])
        k = (g >= 0) & (g <= 200)
        v = np.clip(0.5 + (m[k] / far - 1.0) / (2 * SPAN), 0, 1)
        rows.append(np.repeat(v[None, :], 46, axis=0))
        labels.append(arm)
    if not rows:
        return None
    tick = np.zeros((6, rows[0].shape[1]))
    for t in range(0, 201, 20):
        tick[:, t] = 1.0
    out = []
    for r in rows:
        out.append(r)
        out.append(tick)
    img = (np.concatenate(out, axis=0) * 255).astype(np.uint8)
    img = np.repeat(np.repeat(img, 3, axis=0), 3, axis=1)
    Image.fromarray(img).save(os.path.join(PIC, "midscale-%s-profile.png" % lab))
    return labels


def boundary(lab):
    p = Path(DELIV) / (lab + ".tiff")
    a = tifffile.imread(str(p))
    lum = a[:, :, 1].astype(np.float32)
    subject, backdrop, diag = segment(lum)
    d = ndimage.distance_transform_edt(~subject).astype(np.float32)
    h, w = lum.shape
    # a boundary point with at least 220 px of clear backdrop to its right
    cand = np.zeros_like(subject)
    cand[300:h - 300, 300:w - 400] = True
    band = subject & ~ndimage.binary_erosion(subject, iterations=1) & cand
    ys, xs = np.nonzero(band)
    best = None
    for i in range(0, len(ys), max(1, len(ys) // 4000)):
        y, x = int(ys[i]), int(xs[i])
        seg = d[y, x:x + 240]
        if seg.size == 240 and seg[-1] > 200 and np.all(np.diff(seg) >= 0):
            if backdrop[y, x + 40:x + 240].all():
                best = (y, x)
                break
    if best is None:
        print("  %s: no clean rightward boundary run found" % lab)
        del a
        return
    y, x = best
    y0 = max(0, y - 90)
    crop = a[y0:y0 + 180, x - 60:x + 240, :].astype(np.float32) / 65535.0
    far = float(np.median(crop[:, -60:, 1]))
    norm = np.clip(crop / max(far, 1e-6), 0, 4)
    left = (np.clip(crop / max(np.percentile(crop, 99.5), 1e-6), 0, 1)
            * 255).astype(np.uint8)
    right = (np.clip(0.5 + (norm - 1.0) / (2 * SPAN), 0, 1) * 255).astype(np.uint8)
    sep = np.full((left.shape[0], 8, 3), 60, np.uint8)
    Image.fromarray(np.concatenate([left, sep, right], axis=1)).save(
        os.path.join(PIC, "midscale-%s-boundary.png" % lab))
    print("  %s: boundary at (%d,%d), far=%.4f" % (lab, y, x, far))
    del a, lum, subject, backdrop, d


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(PIC, exist_ok=True)
    for lab in FIVE:
        print(lab, strip(lab))
        boundary(lab)
    print("wrote %s" % PIC)
