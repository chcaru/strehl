"""V-bestframe probe 0: establish rawpy's decode contract before trusting it."""
import time, numpy as np, rawpy, tifffile
from pathlib import Path

D = Path(r"D:\personal\macro")
for subj in ("flowers-cpl", "bee-1-cpl"):
    fs = sorted((D / subj).glob("*.ARW"))
    print(f"\n=== {subj}: {len(fs)} ARW, first={fs[0].name} last={fs[-1].name}")
    t0 = time.time()
    with rawpy.imread(str(fs[len(fs) // 2])) as r:
        print(f"  raw sizes: raw {r.raw_image.shape} visible {r.raw_image_visible.shape} "
              f"pattern {r.color_desc} black {r.black_level_per_channel} white {r.white_level}")
        a = r.postprocess(output_bps=16, no_auto_bright=True, use_camera_wb=True)
    t1 = time.time()
    assert a.dtype == np.uint16, f"rawpy returned {a.dtype}, NOT uint16"
    m = tifffile.imread(rf"C:\dev\strehl-out\GALLERY-FIXED-SRGB\{subj}.tiff")
    assert m.dtype == np.uint16, f"merge returned {m.dtype}, NOT uint16"
    print(f"  rawpy postprocess: {a.shape} {a.dtype} in {t1-t0:.2f}s   "
          f"min {a.min()} max {a.max()} distinct(G) {len(np.unique(a[::7, ::7, 1]))}")
    print(f"  merge tiff       : {m.shape} {m.dtype}                 "
          f"min {m.min()} max {m.max()} distinct(G) {len(np.unique(m[::7, ::7, 1]))}")
    print(f"  shape match: {a.shape == m.shape}   ptp frame {np.ptp(a)} merge {np.ptp(m)}")

print("\n=== rawpy postprocess defaults actually in force ===")
p = rawpy.Params(output_bps=16, no_auto_bright=True, use_camera_wb=True)
for k in ("gamma", "output_color", "user_flip", "half_size", "four_color_rgb",
          "no_auto_scale", "user_black", "bright", "highlight_mode", "median_filter_passes"):
    print(f"  {k:22s} = {getattr(p, k, '<n/a>')}")
print(f"  demosaic_algorithm     = {getattr(p, 'user_qual', '<n/a>')}  (libraw user_qual; 3 = AHD)")
