"""Decisive scale check: sweep the scale, warp argmax->merge, score correlation.

Independent of anchors and of ECC. If the peak sits at the logged FOV scale the
log is right; if it sits elsewhere the log describes the intent, not the file.
"""
import pathlib
import numpy as np, cv2, tifffile
R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
DS = 4
def prep(p):
    g = tifffile.imread(str(p))[:, :, 1].astype(np.float32)
    s = cv2.resize(g, None, fx=1.0/DS, fy=1.0/DS, interpolation=cv2.INTER_AREA)
    s = s - cv2.blur(s, (25,25))
    return s/(s.std()+1e-9)
for subj, logged in (("flowers-cpl",0.9367),("leaf-2-cpl",0.9342),("bee-3-cpl",0.9321),
                     ("flat-on-ruler-cpl",0.9707),("tweezers-cpl",0.9728),("bee-1-cpl",0.9236)):
    m, a = prep(R/subj/"merge.tif"), prep(R/subj/"argmax.tif")
    H, W = m.shape
    best = []
    for s in np.arange(0.900, 1.0101, 0.0025):
        # resample merge to argmax density, then find best shift by phase correlation
        n2 = (int(round(W*s)), int(round(H*s)))
        ms = cv2.resize(m, n2, interpolation=cv2.INTER_AREA)
        h = min(ms.shape[0], a.shape[0]); w = min(ms.shape[1], a.shape[1])
        A = ms[:h,:w].astype(np.float32); B = a[:h,:w].astype(np.float32)
        win = cv2.createHanningWindow((w,h), cv2.CV_32F)
        (dx,dy), resp = cv2.phaseCorrelate(A*win, B*win)
        M = np.float32([[1,0,dx],[0,1,dy]])
        Aw = cv2.warpAffine(A, M, (w,h))
        v = float(np.corrcoef(Aw[40:-40,40:-40].ravel(), B[40:-40,40:-40].ravel())[0,1])
        best.append((v, s, resp))
    best.sort(reverse=True)
    top = best[:4]
    print(f"{subj:20s} logged {logged:.4f}   peak corr scale " +
          "  ".join(f"{s:.4f}(r={v:.3f})" for v,s,_ in top))
