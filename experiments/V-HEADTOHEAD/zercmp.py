"""SUBJECT 2, matched frames: strehl SHIP-V2 vs ZERENE STACKER PMax.

  zerene  D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif   uint16 4672x7008
  strehl  C:\dev\strehl-out\SHIP-V2\113MSDCF--SHIP-V2.tiff        uint16 4688x7032
  frames  the same 63 exposures, DSC00001..00063, 2026-05-07.
          Lightroom develop for Zerene's inputs: Sharpness=0, LuminanceSmoothing=0,
          ColorNoiseReduction=0, Contrast2012=+100.  NO capture sharpening.

CAVEAT, declared everywhere this is quoted: PMax is Zerene's maximum-detail
pyramid method.  Zerene's own documentation says PMax raises contrast and noise
relative to DMap.  No DMap render exists here, so this is a comparison against
Zerene's SHARPEST-and-NOISIEST mode, which flatters Zerene on sharpness and
handicaps it on noise.  Both directions are stated with the numbers.

Reference grid = Zerene.  NOTHING IS RESAMPLED: each arm reads its own integer
box and frequencies are expressed in cycles per ZERENE pixel.
"""
import numpy as np, tifffile, json, spec, shapecmp
from arms import Arm
from scipy import ndimage

Z = r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"
S = r"C:\dev\strehl-out\SHIP-V2\113MSDCF--SHIP-V2.tiff"

def load(p):
    a = tifffile.memmap(p, mode="r")
    g = np.empty(a.shape[:2], np.float32); clip = np.zeros(a.shape[:2], bool)
    for y0 in range(0, a.shape[0], 256):
        y1 = min(y0+256, a.shape[0]); blk = np.asarray(a[y0:y1], np.uint16)
        g[y0:y1] = blk[:, :, 1].astype(np.float32)/65535.0
        clip[y0:y1] = blk.max(axis=2) >= 65535
    del a
    return g, clip

def fit_similarity(gz, gs, T=512, step=900):
    pts = []
    for y in range(300, gz.shape[0]-T-300, step):
        for x in range(300, gz.shape[1]-T-300, step):
            a = gz[y:y+T, x:x+T]
            if a.std() < 0.01: continue
            b = gs[y:y+T, x:x+T]
            A = np.fft.rfft2(a - a.mean()); B = np.fft.rfft2(b - b.mean())
            R = A*np.conj(B); R /= np.abs(R)+1e-12
            c = np.fft.irfft2(R, s=a.shape)
            i = np.unravel_index(np.argmax(c), c.shape); pk = c[i]
            if pk < 0.02: continue
            dy = i[0]-(T if i[0] > T//2 else 0); dx = i[1]-(T if i[1] > T//2 else 0)
            if abs(dy) > 60 or abs(dx) > 60: continue
            pts.append((x+T/2.0, y+T/2.0, x+T/2.0-dx, y+T/2.0-dy, pk))
    P = np.array(pts)
    print(f"  tiles kept: {len(P)}  (median peak {np.median(P[:,4]):.3f})")
    xs, ys, xt, yt = P[:, 0], P[:, 1], P[:, 2], P[:, 3]
    M = np.zeros((2*len(P), 4)); v = np.zeros(2*len(P))
    M[0::2, 0] = xs; M[0::2, 1] = -ys; M[0::2, 2] = 1; v[0::2] = xt
    M[1::2, 0] = ys; M[1::2, 1] = xs;  M[1::2, 3] = 1; v[1::2] = yt
    sol, *_ = np.linalg.lstsq(M, v, rcond=None)
    a, b, tx, ty = sol
    res = (M@sol - v).reshape(-1, 2)
    print(f"  scale {np.hypot(a,b):.6f}  rot {np.degrees(np.arctan2(b,a)):+.4f} deg  "
          f"tx {tx:+.2f} ty {ty:+.2f}  residual rms {np.hypot(*res.T).std():.2f} px  "
          f"max {np.hypot(*res.T).max():.2f} px")
    return a, b, tx, ty

if __name__ == "__main__":
    print("loading..."); gz, cz = load(Z); gs, cs = load(S)
    print("zerene", gz.shape, "strehl", gs.shape, "  zerene clipped frac",
          f"{cz.mean():.4f}", " strehl clipped frac", f"{cs.mean():.4f}")
    print("similarity fit (zerene -> strehl):")
    a, b, tx, ty = fit_similarity(gz, gs)
    sc = float(np.hypot(a, b))
    def mapper(x, y, a=a, b=b, tx=tx, ty=ty):
        x = np.asarray(x, float); y = np.asarray(y, float)
        return (a*x - b*y + tx, b*x + a*y + ty)
    Az = Arm("zerene", gz, lambda x, y: (x, y), 1.0, cz)
    As = Arm("strehl", gs, mapper, sc, cs)
    T = 256
    import shapegrid
    rois = shapegrid.grid_rois(Az, T, thresh=0.012)
    print(f"\ndetail ROIs on the subject: {len(rois)}")
    out = {}
    out["null"]  = shapecmp.shape_ratio(Az, Arm("clone", gz, lambda x, y: (x, y), 1.0, cz),
                                        rois, "NULL CONTROL", "zerene", "clone", T)
    bl = ndimage.gaussian_filter(gz, 0.5)
    out["pos"]   = shapecmp.shape_ratio(Az, Arm("blur", bl, lambda x, y: (x, y), 1.0, cz),
                                        rois, "POSITIVE CONTROL sigma=0.5 px", "zerene", "blur", T)
    del bl
    out["real"]  = shapecmp.shape_ratio(Az, As, rois,
                    "REAL: Zerene PMax vs strehl SHIP-V2 -- SHARPNESS, grade removed",
                    "zerene", "strehl", T)
    json.dump(out, open("zer_shape.json", "w"), indent=1)
