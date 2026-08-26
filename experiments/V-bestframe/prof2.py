import time, numpy as np
from pathlib import Path
from scipy import ndimage
import bestframe as B
RAW = Path(r"D:\personal\macro")
def T(lab, fn, n=1):
    t=time.time()
    for _ in range(n): r=fn()
    print(f"  {lab:38s} {(time.time()-t)/n:6.2f}s"); return r
rgb = B.decode(sorted((RAW/"bee-1-cpl").glob("*.ARW"))[120])
print("luma variants")
L = B.LUMA
a = T("current (3 strided mults)", lambda: B.luma(rgb))
b = T("einsum", lambda: np.einsum('ijk,k->ij', rgb, L, dtype=np.float32))
c = T("reshape @ matmul", lambda: (rgb.reshape(-1,3).astype(np.float32) @ L).reshape(rgb.shape[:2]))
d = T("green plane only", lambda: np.ascontiguousarray(rgb[:,:,1]).astype(np.float32))
print(f"  einsum==current max|d| {np.abs(a-b).max():.4f}   matmul==current {np.abs(a-c).max():.4f}")
f32 = a
print("band variants on 33M float32")
T("gaussian dog (1,2) truncate=4", lambda: B.dog(f32,1.0,2.0))
T("gaussian dog (1,2) truncate=3", lambda: (ndimage.gaussian_filter(f32,1.0,truncate=3.0)
                                            - ndimage.gaussian_filter(f32,2.0,truncate=3.0)))
T("uniform dog (3,9)", lambda: (ndimage.uniform_filter(f32,3) - ndimage.uniform_filter(f32,9)))
T("uniform dog (3,9) via output=", lambda: ndimage.uniform_filter(f32,3)-ndimage.uniform_filter(f32,9))
print("check the two bands see the same thing (corr over tiles)")
g = B.dog(f32,1.0,2.0); u = ndimage.uniform_filter(f32,3)-ndimage.uniform_filter(f32,9)
ye=B.tile_edges(f32.shape[0],B.NTY); xe=B.tile_edges(f32.shape[1],B.NTX)
G=B._tile_reduce(f32,(g*g),(g*g),ye,xe)[:,:,1]; U=B._tile_reduce(f32,(u*u),(u*u),ye,xe)[:,:,1]
print(f"  pearson(log G, log U) over 352 tiles = "
      f"{np.corrcoef(np.log(G.ravel()+1e-9), np.log(U.ravel()+1e-9))[0,1]:.5f}")
