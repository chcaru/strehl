"""Why the Zerene shape ratio is NOT a sharpness measure, and whether it can be
rescued.

THE LOOK CONTRADICTED THE NUMBER.  zercmp.py reported strehl at 0.38 of Zerene
in the 0.20-0.30 band, i.e. "much softer".  The 1:1 crops show the opposite:
Zerene's frame is a few bright filaments on CRUSHED BLACK and strehl resolves a
whole dendritic web that Zerene has lost.

Mechanism: the shape statistic normalises each arm by its own 0.02-0.05 band.
That is valid only while a tone difference acts as a LOCAL SCALAR inside the
ROI.  It does not act as a scalar when one arm is clipped at black: there the
local contrast is destroyed, not scaled.  Zerene's inputs were developed with
crs:Contrast2012="+100"; strehl came from raw pushed +2.34 stops.

So: (1) measure the black crush, (2) retry the comparison ONLY on ROIs where
NEITHER arm is near its black point, which is the region where the local-scalar
assumption is actually true, (3) if too few such ROIs survive, abandon.
"""
import numpy as np, tifffile, json, spec, shapecmp
from arms import Arm
from scipy import ndimage
Z = r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"
S = r"C:\dev\strehl-out\SHIP-V2\113MSDCF--SHIP-V2.tiff"
A, B, TX, TY = 1.0017487, 0.00032, 10.86, 5.75
def load(p):
    a = tifffile.memmap(p, mode="r")
    g = np.empty(a.shape[:2], np.float32); clip = np.zeros(a.shape[:2], bool)
    for y0 in range(0, a.shape[0], 256):
        y1 = min(y0+256, a.shape[0]); blk = np.asarray(a[y0:y1], np.uint16)
        g[y0:y1] = blk[:, :, 1].astype(np.float32)/65535.0
        clip[y0:y1] = blk.max(axis=2) >= 65535
    del a; return g, clip
if __name__ == "__main__":
    gz, cz = load(Z); gs, cs = load(S)
    print("=== BLACK CRUSH (green channel, fraction of pixels at or below) ===")
    print(f"{'level':>10}{'zerene':>12}{'strehl':>12}")
    for lv in (0.0, 1/65535, 2/65535, 0.001, 0.002, 0.005, 0.01, 0.02):
        print(f"{lv:>10.5f}{(gz<=lv).mean():>12.5f}{(gs<=lv).mean():>12.5f}")
    print(f"\nmedian  zerene {np.median(gz):.5f}   strehl {np.median(gs):.5f}")
    print(f"p01/p50/p99 zerene {np.percentile(gz,[1,50,99]).round(5)}")
    print(f"p01/p50/p99 strehl {np.percentile(gs,[1,50,99]).round(5)}")

    def mapper(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        return (A*x - B*y + TX, B*x + A*y + TY)
    Az = Arm("zerene", gz, lambda x, y: (x, y), 1.0, cz)
    As = Arm("strehl", gs, mapper, A, cs)
    T = 256; Ts = int(round(T*A))
    FLOOR = 0.01                       # "near black" for a 16-bit display encoding
    rois, dropped_black, dropped_flat = [], 0, 0
    for y in range(300, gz.shape[0]-T-300, T//2):
        for x in range(300, gz.shape[1]-T-300, T//2):
            tz = gz[y:y+T, x:x+T]
            if cz[y:y+T, x:x+T].any(): continue
            if (tz - ndimage.uniform_filter(tz, 9)).std() < 0.012: dropped_flat += 1; continue
            sx, sy = mapper(x+T/2.0, y+T/2.0)
            y0, x0 = int(round(sy-Ts/2)), int(round(sx-Ts/2))
            if y0 < 0 or x0 < 0 or y0+Ts > gs.shape[0] or x0+Ts > gs.shape[1]: continue
            ts = gs[y0:y0+Ts, x0:x0+Ts]
            if cs[y0:y0+Ts, x0:x0+Ts].any(): continue
            if (tz <= FLOOR).mean() > 0.01 or (ts <= FLOOR).mean() > 0.01:
                dropped_black += 1; continue
            rois.append((y, x))
    print(f"\nROIs: kept {len(rois)}   dropped for black crush {dropped_black}   "
          f"dropped as flat {dropped_flat}")
    if len(rois) < 40:
        print("TOO FEW UNCRUSHED ROIs -- the comparison is ABANDONED, not massaged."); raise SystemExit
    out = {}
    out["null"] = shapecmp.shape_ratio(Az, Arm("clone", gz, lambda x, y: (x, y), 1.0, cz),
                                       rois, "NULL CONTROL (uncrushed ROIs)", "zerene", "clone", T)
    bl = ndimage.gaussian_filter(gz, 0.5)
    out["pos"] = shapecmp.shape_ratio(Az, Arm("blur", bl, lambda x, y: (x, y), 1.0, cz),
                                      rois, "POSITIVE CONTROL sigma=0.5 px", "zerene", "blur", T)
    del bl
    out["real"] = shapecmp.shape_ratio(Az, As, rois,
        "REAL, UNCRUSHED ROIs ONLY: Zerene PMax vs strehl SHIP-V2", "zerene", "strehl", T)
    json.dump(out, open("zer_shape_uncrushed.json", "w"), indent=1)
