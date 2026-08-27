import os, sys, numpy as np, softcheck as S
subj, gauge, ks = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(",")]
d = os.path.join(S.ROOT, gauge, subj)
M = S.load_luma(os.path.join(d, "master.tiff"), gauge)
H, W = M.shape; win = 512; margin = 64
ys = np.linspace(margin, H-win-margin, 4).astype(int)
xs = np.linspace(margin, W-win-margin, 6).astype(int)
for k in ks:
    F = S.load_luma(os.path.join(d, f"f{k:03d}.tiff"), gauge)
    coef, rms, kp, tot = S.register(M, F)
    print(f"--- frame {k}: fit rms={rms:.2f} kept={kp}/{tot}")
    pts, dsp, qs = [], [], []
    for y in ys:
        for x in xs:
            dy, dx, q = S.phase_shift(M[y:y+win, x:x+win], F[y:y+win, x:x+win])
            pts.append((y+win/2, x+win/2)); dsp.append((dy,dx)); qs.append(q)
    pts=np.array(pts,float); dsp=np.array(dsp,float); qs=np.array(qs)
    A = np.column_stack([np.ones(len(pts)), pts[:,0], pts[:,1]])
    res = dsp - A@coef
    for i in range(len(pts)):
        print(f"   anchor y={pts[i,0]:6.0f} x={pts[i,1]:6.0f}  d=({dsp[i,0]:+7.1f},{dsp[i,1]:+7.1f}) "
              f"resid={np.linalg.norm(res[i]):6.2f}  peakq={qs[i]:6.1f}")
