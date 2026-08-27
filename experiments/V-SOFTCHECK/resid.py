"""Is my +-8px search window big enough to rescue flower-bud?

For a sample of tiles and frames, brute-force the displacement that maximises
normalised cross-correlation between the master tile and the frame, over a
+-40px range, and compare it to what my affine fit predicted.  If the true
per-tile residual routinely exceeds 8px, then searchmax.py's window does not
cover the error and the subject is unmeasurable by my instrument.
"""
import os, sys, numpy as np, softcheck as S
from scipy import ndimage
subj = sys.argv[1]; T, GAU, RNG = 128, "lin", 40
d = os.path.join(S.ROOT, GAU, subj)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff")); N=len(fl)
M = S.load_luma(os.path.join(d,"master.tiff"), GAU); H,W = M.shape
rng = np.random.default_rng(3)
ks = sorted(rng.choice(N, size=min(6,N), replace=False).tolist())
ys = np.linspace(400, H-400-T, 5).astype(int); xs = np.linspace(400, W-400-T, 6).astype(int)
print(f"{subj}: probing frames {ks}, {len(ys)*len(xs)} tiles each, brute force +-{RNG}px")
allr = []
for k in ks:
    F = S.load_luma(os.path.join(d, fl[k]), GAU)
    coef, rms, kp, tot = S.register(M, F)
    res = []
    for y in ys:
        for x in xs:
            a = M[y:y+T, x:x+T]
            if a.std() < 1e-3: continue
            a = (a - a.mean())/ (a.std()+1e-9)
            dy0, dx0 = S.disp_at(coef, np.array([y+T/2.0]), np.array([x+T/2.0]))[0]
            y0 = int(round(y+dy0)); x0 = int(round(x+dx0))
            ylo=max(0,y0-RNG); xlo=max(0,x0-RNG)
            b = F[ylo:min(H,y0+T+RNG), xlo:min(W,x0+T+RNG)]
            if b.shape[0]<T or b.shape[1]<T: continue
            # NCC by FFT
            bb = b - b.mean()
            num = ndimage.correlate(bb, a, mode="constant")[T//2:T//2+b.shape[0]-T+1, T//2:T//2+b.shape[1]-T+1]
            j = np.unravel_index(np.argmax(num), num.shape)
            res.append(np.hypot(ylo+j[0]-y0, xlo+j[1]-x0))
    res = np.array(res); allr.append(res)
    print(f"  {fl[k]} affine rms={rms:5.2f}px | per-tile residual vs my fit: "
          f"median {np.median(res):5.1f} p90 {np.quantile(res,.9):5.1f} max {res.max():5.1f} | "
          f">8px {100*(res>8).mean():3.0f}%  >40px(pegged) {100*(res>=RNG-1).mean():3.0f}%")
a = np.concatenate(allr)
print(f"  ALL: median {np.median(a):.1f}px  frac>8px {100*(a>8).mean():.0f}%  frac pegged {100*(a>=RNG-1).mean():.0f}%")
