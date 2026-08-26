import numpy as np, rawpy, os
D = r"D:\personal\macro\coffee-bean"
fs = sorted(f for f in os.listdir(D) if f.lower().endswith(".arw"))
print("frames", len(fs))
def load(fn):
    with rawpy.imread(os.path.join(D, fn)) as r:
        return r.postprocess(half_size=True, output_bps=16, no_auto_bright=True,
                             use_camera_wb=True, gamma=(1,1)).astype(np.float32).mean(axis=2)
ref = load(fs[len(fs)//2])
H, W = ref.shape
print("half-res grid", ref.shape)
def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a*b).sum() / (np.sqrt((a*a).sum()*(b*b).sum()) + 1e-9))
# two patches far apart horizontally, to expose magnification change
sites = {"far-left": (H//2 - 250, 300), "right-mid": (H//2 - 250, W - 800)}
R = 60   # search radius, half-res px
for name in ["far-left", "right-mid"]:
    y, x = sites[name]
    tgt = ref[y:y+500, x:x+500]
    for fn in [fs[0], fs[-1]]:
        mv = load(fn)
        best = None
        for dy in range(-R, R+1, 2):
            for dx in range(-R, R+1, 2):
                p = mv[y+dy:y+dy+500, x+dx:x+dx+500]
                if p.shape != tgt.shape: continue
                c = ncc(tgt, p)
                if best is None or c > best[0]: best = (c, dy, dx)
        z = ncc(tgt, mv[y:y+500, x:x+500])
        print(f"  {name:9s} {fn[:8]}  peak ({best[1]:+d},{best[2]:+d}) ncc {best[0]:.4f} | zero-shift ncc {z:.4f} | gain {best[0]-z:+.4f}")
