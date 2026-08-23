"""V01 -- independent re-implementation of M28 sections 1 and 2.
Nothing imported from the m28 scripts; written from the stated spec.
"""
import glob, os, sys
import numpy as np
import rawpy

BLACK = 512.0
CROP = 3072
CACHE = r"C:\dev\blog\death-of-software\projects\strehl\experiments\m28-robustness-scale\out\cache"

def decode_green(path):
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        h, w = v.shape
        y0 = (h - CROP) // 2
        x0 = (w - CROP) // 2
        assert y0 % 2 == 0 and x0 % 2 == 0, (y0, x0)
        sub = v[y0:y0+CROP, x0:x0+CROP]
        return sub[0::2, 1::2].astype(np.float64) - BLACK, v.shape

files = sorted(glob.glob(r"D:\personal\macro\109MSDCF\*.ARW"))
print("frames found:", len(files))
cache = np.load(os.path.join(CACHE, "109MSDCF.npy"))
print("cache", cache.shape, cache.dtype)

# --- verify the cache is a faithful decode on 3 sampled frames ---------------
for i in (0, 11, 21):
    g, shp = decode_green(files[i])
    d = np.abs(g - cache[i].astype(np.float64))
    print(f"  frame {i:2d} visible={shp} mine={g.shape} maxabsdiff={d.max():.6g} "
          f"mean={g.mean():.3f}")

a_raw = cache.astype(np.float64)   # verified identical to my own decode
n = len(a_raw)

def area_mean(a, d):
    if d == 1: return a
    N, h, w = a.shape
    h2, w2 = (h//d)*d, (w//d)*d
    return a[:, :h2, :w2].reshape(N, h2//d, d, w2//d, d).mean(axis=(2,4))

ISO = 160.0
g_dn = ISO/436.8
rn2 = (4.20*g_dn)**2
print(f"\ng={g_dn:.6f} DN/e-, RN_DN={np.sqrt(rn2):.4f}")

# ------------- S1: pairwise |z| vs separation, median-gain normalisation -----
med = np.median(a_raw.reshape(n,-1), axis=1)
gain_med = med/np.median(med)
a8 = area_mean(a_raw/gain_med[:,None,None], 8)
ref = np.median(a8, axis=0)
sig = np.sqrt(np.maximum(g_dn*np.maximum(ref,0)+rn2, 1e-6))/8.0
print("\nS1 pairwise |z| (whole-stack-median sigma, /sqrt2), d=8, median over all:")
for dk in (1,2,4,8,16):
    v = np.median(np.abs(a8[dk:]-a8[:-dk])/(sig*np.sqrt(2.0)))
    print(f"   dk={dk:3d}  {v:8.4f}")

# ------------- S1b: radial profile, whole-stack reference --------------------
z_ws = np.abs(a8-ref)/sig
zmed = np.median(z_ws, axis=0)
h, w = ref.shape
yy, xx = np.mgrid[0:h,0:w]
r = np.sqrt((yy-(h-1)/2.)**2 + (xx-(w-1)/2.)**2)
edges = np.linspace(0, r.max(), 9)
prof_ws = [float(np.median(zmed[(r>=edges[i])&(r<edges[i+1])])) for i in range(8)]
print("\nS1b radial |z| whole-stack ref: " + " ".join(f"{v:6.2f}" for v in prof_ws))
print(f"     outer/inner = {prof_ws[-1]/prof_ws[0]:.4f}")

# ------------- S1c: radial profile, adjacent-frame (2nd-diff) reference ------
gain_mean = a_raw.reshape(n,-1).mean(axis=1); gain_mean /= np.median(gain_mean)
b8 = area_mean(a_raw/gain_mean[:,None,None], 8)
refn = (b8[:-2]+b8[2:])/2.0
sign = np.sqrt(np.maximum(g_dn*np.maximum(refn,0)+rn2,1e-6))/8.0
z_nb = np.abs(b8[1:-1]-refn)/(sign*np.sqrt(1.5))
z1 = np.median(z_nb, axis=0)
prof_nb = [float(np.median(z1[(r>=edges[i])&(r<edges[i+1])])) for i in range(8)]
print("\nS1c radial |z| adjacent-frame(2nd-diff) ref: " + " ".join(f"{v:6.2f}" for v in prof_nb))
print(f"     outer/inner = {prof_nb[-1]/prof_nb[0]:.4f}")

# ------------- S1d: radial profile, FIRST-difference adjacent-frame ref ------
sig1 = np.sqrt(np.maximum(g_dn*np.maximum((b8[:-1]+b8[1:])/2.,0)+rn2,1e-6))/8.0
z_fd = np.abs(b8[1:]-b8[:-1])/(sig1*np.sqrt(2.0))
zf = np.median(z_fd, axis=0)
prof_fd = [float(np.median(zf[(r>=edges[i])&(r<edges[i+1])])) for i in range(8)]
print("\nS1d radial |z| adjacent-frame FIRST-difference ref: " + " ".join(f"{v:6.2f}" for v in prof_fd))
print(f"     outer/inner = {prof_fd[-1]/prof_fd[0]:.4f}")

# ------------- S2: tile statistic --------------------------------------------
W, D = 128, 8
tb = W//D
def tile_med(z):
    ny = z.shape[1]//tb; nx = z.shape[2]//tb
    t = z[:, :ny*tb, :nx*tb].reshape(z.shape[0], ny, tb, nx, tb)
    return np.median(t, axis=(2,4)).ravel()
t_nb = tile_med(z_nb)
t_fd = tile_med(z_fd)
print(f"\nS2 tile median |z| (2nd-diff, the M28 statistic): {np.median(t_nb):.4f}"
      f"  = {np.median(t_nb)/0.6745:.4f}x half-normal   ntiles={len(t_nb)}")
print(f"   tile median |z| (1st-diff, adjacent pair)     : {np.median(t_fd):.4f}"
      f"  = {np.median(t_fd)/0.6745:.4f}x half-normal")
print(f"   pixelwise median |z| 2nd-diff {np.median(z_nb):.4f}  1st-diff {np.median(z_fd):.4f}")
