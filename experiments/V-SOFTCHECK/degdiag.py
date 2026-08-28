"""Is the DEGRADE non-monotonicity caused by the sub-pixel shift estimator?
Same ladder, correction ON and OFF.  If OFF is monotone and ON is not, the
estimator is locking onto noise-driven shifts and the statistic is not trustworthy."""
import numpy as np, softcheck as S, hcoh as HC
d=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh\113MSDCF"
A=S.load_luma(rf"{d}\N062-A.tiff","srgb"); B=S.load_luma(rf"{d}\N062-B.tiff","srgb")
oy,ox=HC.pick_tiles(A); y,x=oy[:120],ox[:120]
sd=float(A.std()); rng=np.random.default_rng(23)
print(f"113MSDCF  image std {sd:.1f}   120 tiles   band 0.20-0.25")
print(f"{'amp':>7s} {'noise DN':>9s} {'subpix ON':>10s} {'subpix OFF':>11s}")
for amp in (0.0,0.005,0.01,0.02,0.03,0.05,0.10,0.20):
    Ad=A+rng.standard_normal(A.shape).astype(np.float32)*sd*amp if amp else A
    Bd=B+rng.standard_normal(B.shape).astype(np.float32)*sd*amp if amp else B
    on,_=HC.pair_stats(Ad,Bd,y,x,y,x,subpix=True)
    off,_=HC.pair_stats(Ad,Bd,y,x,y,x,subpix=False)
    print(f"{amp:7.3f} {sd*amp:9.1f} {np.median(on[:,3]):10.4f} {np.median(off[:,3]):11.4f}")
