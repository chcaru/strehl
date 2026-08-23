import numpy as np, rawpy, glob, os
from scipy.ndimage import median_filter
S=r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
BLACK=512; count=np.load(os.path.join(S,"hotcount.npy")); darkmap=count>=6
print("=== R11 step 5: is the dark-derived map COMPLETE at working exposures? ===")
print("    The darks are 1/100 s; real stacks are 0.8-1.3 s. A pixel with moderate dark current")
print("    would show there and not in the darks. Cross-scene test, no new captures needed:")
print("    a pixel anomalous in TWO DIFFERENT SCENES is scene-independent, i.e. a sensor defect.\n")
def meanres(path, n=8, sub=1):
    fs=sorted(glob.glob(os.path.join(path,"*.ARW")))[::sub][:n]
    acc=None
    for f in fs:
        with rawpy.imread(f) as rr: a=rr.raw_image_visible.astype(np.float32)-BLACK
        e=np.zeros_like(a)
        for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):
            pl=a[dy::2,dx::2]; e[dy::2,dx::2]=pl-median_filter(pl,3)
        acc=e if acc is None else acc+e
    return acc/len(fs), len(fs)
A,na=meanres(r"C:\dev\macro\test\109MSDCF",8)          # 1.3 s, ISO 160
B,nb=meanres(r"C:\dev\macro\test\coffee-bean",8,13)    # 0.8 s, ISO 50, different scene
print(f"    scene A = 109MSDCF ({na} frames, 1.3 s)   scene B = coffee-bean ({nb} frames, 0.8 s)")
for THR in (10,20,40):
    fa=A>THR; fb=B>THR
    both=fa&fb; exp=fa.mean()*fb.mean()*A.size
    print(f"\n    threshold mean residual > {THR:>2} DN:")
    print(f"      flagged in A: {fa.sum():>8}   in B: {fb.sum():>8}   in BOTH: {both.sum():>7}"
          f"   expected if independent: {exp:>9.1f}   enrichment {both.sum()/max(exp,1e-9):>7.1f}x")
    ov=(both&darkmap).sum()
    print(f"      of the {both.sum()} scene-independent defects, {ov} ({ov/max(both.sum(),1)*100:.1f}%) are in the 1/100 s dark map")
    print(f"      => {both.sum()-ov} defects are MISSED by the delivered darks")
print("\n    NOTE: 'both' still includes any pixel where both scenes happen to have a local maximum.")
print("    The enrichment over independence is what shows the population is real.")
