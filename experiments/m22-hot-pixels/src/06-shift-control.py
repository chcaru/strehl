import numpy as np, rawpy, glob, os
from scipy.ndimage import median_filter
S=r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
BLACK=512; darkmap=np.load(os.path.join(S,"hotcount.npy"))>=6
def meanres(path,n=8,sub=1):
    fs=sorted(glob.glob(os.path.join(path,"*.ARW")))[::sub][:n]; acc=None
    for f in fs:
        with rawpy.imread(f) as rr: a=rr.raw_image_visible.astype(np.float32)-BLACK
        e=np.zeros_like(a)
        for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):
            pl=a[dy::2,dx::2]; e[dy::2,dx::2]=pl-median_filter(pl,3)
        acc=e if acc is None else acc+e
    return acc/len(fs)
A=meanres(r"C:\dev\macro\test\109MSDCF",8); B=meanres(r"C:\dev\macro\test\coffee-bean",8,13)
print("=== R11 step 5b: SHIFT CONTROL on the cross-scene test ===")
print("    Shifting scene B by an even offset preserves CFA phase and all spatial statistics,")
print("    but breaks per-pixel correspondence. A real defect population must COLLAPSE.")
print("    Anything that survives the shift was shared large-scale structure, not defects.\n")
print(f"    {'thr':>4} {'aligned both':>13} {'shifted both':>13} {'ratio':>7}   verdict")
for THR in (10,20,40):
    fa=A>THR; fb=B>THR
    al=(fa&fb).sum()
    sh=[]
    for (dy,dx) in ((50,50),(-50,50),(50,-50),(120,80)):
        sh.append((fa&np.roll(fb,(dy,dx),(0,1))).sum())
    shm=float(np.mean(sh))
    r=al/max(shm,1e-9)
    v = "REAL defect population" if r>2.0 else ("weak / inconclusive" if r>1.2 else "NO defect signal -- it was spatial structure")
    print(f"    {THR:>4} {al:>13} {shm:>13.0f} {r:>7.2f}   {v}")
    print(f"         (individual shifts: {sh})")
print("\n    And the same control applied to the DARK-DERIVED map, which is known-real:")
for THR in (10,20,40):
    fa=A>THR
    al=(fa&darkmap).sum()
    sh=float(np.mean([(fa&np.roll(darkmap,(dy,dx),(0,1))).sum() for (dy,dx) in ((50,50),(-50,50),(50,-50),(120,80))]))
    print(f"    thr {THR:>2}: dark-map pixels flagged in scene A = {al:>6}, shifted {sh:>8.0f}, ratio {al/max(sh,1e-9):>6.2f}x")
