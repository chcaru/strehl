import time, numpy as np
from pathlib import Path
import bestframe as B
RAW = Path(r"D:\personal\macro"); GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
def T(lab, fn):
    t = time.time(); r = fn(); print(f"  {lab:34s} {time.time()-t:6.2f}s"); return r
m = T("read merge", lambda: B.luma(B.read_merge(GAL / "bee-1-cpl.tiff")).astype(np.float32))
ye = B.tile_edges(m.shape[0], B.NTY); xe = B.tile_edges(m.shape[1], B.NTX)
f = sorted((RAW / "bee-1-cpl").glob("*.ARW"))[120]
g = T("raw_green_half", lambda: B.raw_green_half(f))
T("register down=8  (97 scales)", lambda: B.register(B.boxdown(m, 8), B.boxdown(g, 4)))
T("register down=16 (97 scales)", lambda: B.register(B.boxdown(m,16), B.boxdown(g, 8), down=16))
T("register down=16 coarse+fine", lambda: B.register(B.boxdown(m,16), B.boxdown(g,8),
        scales=np.arange(0.82,1.061,0.01), down=16))
rgb = T("rawpy decode full", lambda: B.decode(f))
fL = T("luma", lambda: B.luma(rgb).astype(np.float32))
xs, ys, _ = T("fit_tone", lambda: B.fit_tone(B.boxdown(m,8), B.boxdown(fL,8), 0.9375, (217.5,135.0)))
T("apply_tone np.interp 33M", lambda: B.apply_tone(fL, xs, ys).astype(np.float32))
def lut_tone():
    lut = np.interp(np.arange(65536, dtype=np.float32), xs, ys).astype(np.float32)
    return lut[np.clip(fL, 0, 65535).astype(np.uint16)]
T("apply_tone LUT gather", lut_tone)
T("dog sigma=(1,2) f32", lambda: B.dog(fL, 1.0, 2.0))
T("dog sigma=(2.5,5) f32", lambda: B.dog(fL, 2.5, 5.0))
T("dog sigma=(1.25,2.5) on half", lambda: B.dog(B.boxdown(fL,2).astype(np.float32),1.25,2.5))
d = B.dog(fL, 1.0, 2.0)
T("square as float64 (33M)", lambda: d.astype(np.float64)**2)
T("square as float32 (33M)", lambda: d*d)
T("tile loop 352", lambda: B._tile_reduce(fL, d*d, d*d, ye, xe))
