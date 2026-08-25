import numpy as np, tifffile, itertools, os
base = r"C:\dev\strehl-out\M117\pc"
def load(p): return tifffile.imread(p).astype(np.float64)
for tag in ["prefix-ref3","pre2-plain","head-ref3"]:
    A  = load(os.path.join(base,tag,"A.tiff"))
    A2 = load(os.path.join(base,tag,"A2.tiff"))
    B  = load(os.path.join(base,tag,"B.tiff"))
    print(f"--- {tag}  shape={A.shape} dtype=uint16 ---")
    for name, X in (("A2-A", A2-A), ("B-A", B-A)):
        d = np.abs(X)
        nz = float((d>0).mean())*100
        # mean level for a relative figure
        mean = A.mean()
        print(f"  {name:5s}  changed px {nz:8.4f}%   maxabs {d.max():8.1f} DN   "
              f"rms {np.sqrt((X**2).mean()):8.3f} DN   rms/mean {100*np.sqrt((X**2).mean())/mean:7.4f}%")
    # where does B differ? interior vs border
    d = np.abs(B-A).sum(axis=2) if B.ndim==3 else np.abs(B-A)
    h,w = d.shape
    m = h//10, w//10
    interior = d[m[0]:h-m[0], m[1]:w-m[1]]
    print(f"  B-A central 80%: changed px {100*float((interior>0).mean()):.4f}%  maxabs {interior.max():.1f}")
