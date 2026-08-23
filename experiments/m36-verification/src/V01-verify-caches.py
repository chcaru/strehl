"""M36 V01: verify the two big caches are what they claim to be.

Rule: cached .npy under experiments/*/out/cache/ are gitignored and unverified.
Before I reuse M32's raw.npy or M33's dense_focus.npy I rebuild spot frames
straight from the ARW files and compare bit-for-bit.
"""
import numpy as np, rawpy, glob, os, json, time
from scipy.ndimage import sobel, uniform_filter

SRC = r"C:\dev\macro\test\coffee-bean"
BLACK, R = 512, 2
CY, CX, H = 1172, 1757, 512
ys, xs = slice(0, 4688, 2), slice(1, 7028, 2)

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
M32 = os.path.join(ROOT, "m32-posterior", "out", "cache", "raw.npy")
M33 = os.path.join(ROOT, "m33-subframe-offset", "out", "cache", "dense_focus.npy")
OUT = os.path.join(ROOT, "m36-verification", "out")

files = sorted(glob.glob(os.path.join(SRC, "*.ARW")))
print(f"{len(files)} ARW in {SRC}")

raw = np.load(M32, mmap_mode="r")
dense = np.load(M33, mmap_mode="r")
print("raw.npy   ", raw.shape, raw.dtype)
print("dense.npy ", dense.shape, dense.dtype)

res = {"n_files": len(files), "raw_shape": list(raw.shape), "dense_shape": list(dense.shape)}

def load(f):
    with rawpy.imread(f) as r:
        return r.raw_image_visible[ys, xs][CY-H:CY+H, CX-H:CX+H].astype(np.float32) - BLACK

def focus(v):
    gx = sobel(v, axis=1, mode="nearest"); gy = sobel(v, axis=0, mode="nearest")
    return uniform_filter(np.hypot(gx, gy), size=2*R+1, mode="nearest")

# --- raw.npy: does frame i equal ARW file 2*i ? -----------------------------
raw_checks = {}
for i in (0, 1, 26, 52):
    v = load(files[2*i])
    c = np.asarray(raw[i])
    raw_checks[f"raw[{i}]<-file[{2*i}]"] = dict(
        max_abs_diff=float(np.abs(v-c).max()), identical=bool(np.array_equal(v, c)))
    print(f"  raw[{i}] vs ARW #{2*i}: max|d| = {np.abs(v-c).max():.6g}  identical={np.array_equal(v,c)}")
res["raw_checks"] = raw_checks

# a deliberate MISMATCH control: raw[0] against the wrong file
v = load(files[1]); c = np.asarray(raw[0])
res["raw_mismatch_control"] = float(np.abs(v-c).max())
print(f"  CONTROL raw[0] vs ARW #1 (wrong file): max|d| = {np.abs(v-c).max():.6g}  (must be large)")

# --- dense_focus.npy: does frame j equal focus(ARW file j) ? ----------------
d_checks = {}
for j in (0, 1, 2, 52, 104):
    fv = focus(load(files[j]))
    c = np.asarray(dense[j])
    rel = float(np.abs(fv-c).max()/max(c.max(),1e-9))
    d_checks[f"dense[{j}]<-file[{j}]"] = dict(max_abs_diff=float(np.abs(fv-c).max()),
                                              max_rel=rel, identical=bool(np.array_equal(fv, c)))
    print(f"  dense[{j}] vs focus(ARW #{j}): max|d| = {np.abs(fv-c).max():.6g}"
          f"  rel {rel:.3g}  identical={np.array_equal(fv,c)}")
res["dense_checks"] = d_checks

# --- the identity M34 script 01 ASSERTS: dense[::2] is the focus of raw -----
ident = {}
for i in (0, 13, 52):
    fv = focus(np.asarray(raw[i]))
    c = np.asarray(dense[2*i])
    ident[f"focus(raw[{i}]) vs dense[{2*i}]"] = dict(
        max_abs_diff=float(np.abs(fv-c).max()), identical=bool(np.array_equal(fv, c)))
    print(f"  focus(raw[{i}]) vs dense[{2*i}]: max|d| = {np.abs(fv-c).max():.6g}"
          f"  identical={np.array_equal(fv,c)}")
res["cache_identity"] = ident

json.dump(res, open(os.path.join(OUT, "V01-cache.json"), "w"), indent=1)
print("wrote V01-cache.json")
