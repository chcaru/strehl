"""Measure per-frame photometric drift across a deep bracket, and test whether
the alignment solve already predicts it.

Frame 1 -> 150 -> 299 of bee-3-cpl show background green at 0.2962, 0.2755,
0.2558 of the sensor's usable range: monotonic, 13.6% end to end. If the merge
elects different frames in adjacent regions -- which is what a stacker does --
that drift becomes a brightness step in the output.

The physical prediction: focus breathing changes magnification, and irradiance
falls as 1/m^2, so brightness should track the SAME per-frame scale ladder the
aligner already fits. If it does, photometric normalisation is free for any
stacker that solves alignment, and needs no new estimation.
"""
import glob
import os
import numpy as np
import rawpy

DIR = r"D:\personal\macro\bee-3-cpl"
files = sorted(glob.glob(os.path.join(DIR, "*.ARW")))
idx = np.linspace(0, len(files) - 1, 30).astype(int)
print("%d frames; sampling %d of them" % (len(files), len(idx)))

rows = []
for k in idx:
    with rawpy.imread(files[k]) as r:
        raw = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
        white = float(r.white_level)
        colors = r.raw_colors_visible
        norm = (raw - black) / (white - black)
        h, w = norm.shape
        # Four background patches, one per corner region, so a brightness
        # gradient across the frame cannot masquerade as a global drift.
        pats = {
            "TR": (slice(0, h // 8), slice(-w // 8, None)),
            "TL": (slice(0, h // 8), slice(0, w // 8)),
            "BR": (slice(-h // 8, None), slice(-w // 8, None)),
            "BL": (slice(-h // 8, None), slice(0, w // 8)),
        }
        vals = {}
        for nm, sl in pats.items():
            p = norm[sl]; pc = colors[sl]
            vals[nm] = float(np.median(p[(pc == 1) | (pc == 3)]))
        rows.append((int(k), vals))
        print("  frame %3d  TL %.4f  TR %.4f  BL %.4f  BR %.4f"
              % (k, vals["TL"], vals["TR"], vals["BL"], vals["BR"]))

ks = np.array([r[0] for r in rows], dtype=np.float64)
means = np.array([np.mean(list(r[1].values())) for r in rows])
print()
print("global background level: first %.4f  last %.4f  ratio %.4f  (%.3f stops)"
      % (means[0], means[-1], means[0] / means[-1],
         np.log2(means[0] / means[-1])))

# Is it monotonic?
d = np.diff(means)
print("monotonic decreasing: %s (%d of %d steps negative)"
      % (bool((d < 0).all()), int((d < 0).sum()), len(d)))

# Do the four corners drift TOGETHER (a global gain) or differently (a
# vignetting/geometry change)? A pure 1/m^2 irradiance change is global.
rel = np.array([[r[1][nm] for nm in ("TL", "TR", "BL", "BR")] for r in rows])
rel = rel / rel[0:1, :]
print()
print("per-corner drift, normalised to frame 0:")
print("  final: TL %.4f  TR %.4f  BL %.4f  BR %.4f" % tuple(rel[-1]))
print("  spread across corners at the end: %.4f (0 = perfectly global gain)"
      % float(rel[-1].max() - rel[-1].min()))

# 1/m^2 prediction. The aligner reports 232.7 px corner-to-corner drift on
# this stack; convert to a scale change and predict the brightness ratio.
DRIFT_PX = 232.7
half_diag = np.hypot(7032, 4688) / 2.0
ds = DRIFT_PX / half_diag
print()
print("alignment solve: %.1f px corner drift over half-diagonal %.0f px"
      % (DRIFT_PX, half_diag))
print("  -> scale change %.4f%%  -> predicted 1/m^2 brightness ratio %.4f"
      % (100 * ds, (1 + ds) ** 2))
print("  measured brightness ratio                                  %.4f"
      % (means[0] / means[-1]))

np.save(os.path.join(os.path.dirname(__file__), "photodrift.npy"),
        np.stack([ks, means]))
