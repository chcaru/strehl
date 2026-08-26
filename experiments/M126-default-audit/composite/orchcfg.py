"""M126: identify the render configuration of ORCH's ORCH-GATE artefacts.

`--demosaic` is opt-in and `conflicts_with = "binned"`; the help says to pass
it "explicitly to force full resolution WITHOUT --srgb", which implies --srgb
also emits full resolution. ORCH's own brief says an --srgb render is
"For looking at, NOT for measuring." So: is a-g45.tiff linear or sRGB?

Decided against my own gate-4.5 demosaic render (Bd.tif), same pinned binary.
"""
import numpy as np
import tifffile  # hard import -- no PIL fallback

ORCH = r"C:\dev\strehl-out\ORCH-GATE\a-g45.tiff"
MINE = r"C:\dev\strehl-out\M126-COMPOSITE\109MSDCF\lin\Bd.tif"

for p in (ORCH, MINE):
    with tifffile.TiffFile(p) as t:
        pg = t.pages[0]
        print(f"--- {p}")
        print(f"    shape={pg.shape} dtype={pg.dtype}")
        for tag in pg.tags.values():
            if tag.name in ("ImageDescription", "Software", "Make", "Model",
                            "PhotometricInterpretation", "BitsPerSample"):
                v = str(tag.value)
                print(f"    {tag.name}: {v[:600]}")
    print()

a = tifffile.imread(ORCH)
b = tifffile.imread(MINE)
assert a.dtype == np.uint16 and b.dtype == np.uint16
print(f"same shape: {a.shape == b.shape}")
if a.shape == b.shape:
    d = a.astype(np.int32) - b.astype(np.int32)
    print(f"identical pixels : {not d.any()}")
    print(f"%% differing      : {(d != 0).mean() * 100:.3f}")
    print(f"rms %% of FS      : {np.sqrt((d.astype(np.float64) ** 2).mean()) / 65535 * 100:.4f}")
    print(f"mean DN  ORCH={a.mean():.1f}  mine={b.mean():.1f}")
