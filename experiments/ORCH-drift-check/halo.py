"""Characterise the halo precisely: is it a soft glow or hard-edged plateaus?

The 100% grid shows angular, polygonal brightness terraces in the background
near the silhouette, and a flat grey patch pasted over the leg. That is a
different artifact from "a bright halo" and it implies a different fix.
"""
import os
import numpy as np
import tifffile
from PIL import Image, ImageDraw

SRC = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
OUT = r"C:\dev\strehl-out\ORCH-diagnose"
a = tifffile.imread(SRC)
H, W = a.shape[:2]

SITES = {
    "terrace-below-leg": (2407, 3676),
    "patch-on-leg":      (2407, 2114),
    "terrace-left":      (649, 3676),
    "background-far":    (5923, 551),
}
N = 460

for name, (x, y) in SITES.items():
    c = a[y:y + N, x:x + N].astype(np.float32).mean(axis=2)
    lo, hi = np.percentile(c, 2), np.percentile(c, 98)
    # Stretch hard: terraces are a few DN and invisible at normal contrast.
    s = np.clip((c - lo) / max(hi - lo, 1e-6), 0, 1)
    norm = Image.fromarray((s * 255).astype(np.uint8)).convert("RGB")

    # Local contrast enhancement: subtract a heavy box blur so only the
    # step structure survives.
    k = 41
    pad = np.pad(c, k // 2, mode="edge")
    ii = np.cumsum(np.cumsum(pad, axis=0), axis=1)
    ii = np.pad(ii, ((1, 0), (1, 0)))
    box = (ii[k:, k:] - ii[:-k, k:] - ii[k:, :-k] + ii[:-k, :-k]) / (k * k)
    hp = c - box[:N, :N]
    v = np.percentile(np.abs(hp), 99.5)
    hpi = Image.fromarray(
        (np.clip(hp / max(v, 1e-6) * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)
    ).convert("RGB")

    canvas = Image.new("RGB", (N * 2 + 12, N + 22), (16, 16, 16))
    canvas.paste(norm, (0, 22))
    canvas.paste(hpi, (N + 12, 22))
    dr = ImageDraw.Draw(canvas)
    dr.text((4, 6), "%s  contrast-stretched  [%.0f..%.0f DN]" % (name, lo, hi),
            fill=(210, 210, 120))
    dr.text((N + 16, 6), "high-pass (box41 removed)", fill=(210, 210, 120))
    canvas.save(os.path.join(OUT, "halo-%s.png" % name))

    # How step-like is it? Count how much of the crop sits on a small number
    # of discrete levels.
    q = np.round(c).astype(np.int64)
    vals, counts = np.unique(q, return_counts=True)
    top = np.sort(counts)[::-1][:8].sum() / q.size
    print("%-20s range %6.0f DN  sd %7.2f  top-8 DN levels hold %5.1f%% of px"
          % (name, hi - lo, float(c.std()), top * 100))
