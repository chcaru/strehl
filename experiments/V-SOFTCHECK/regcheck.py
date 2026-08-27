import os, sys, numpy as np, softcheck as S
subj = sys.argv[1]; gauge = sys.argv[2] if len(sys.argv) > 2 else "lin"
d = os.path.join(S.ROOT, gauge, subj)
M = S.load_luma(os.path.join(d, "master.tiff"), gauge)
print("master", M.shape, "mean", M.mean())
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff"))
print("frames", len(fl))
for fn in fl:
    F = S.load_luma(os.path.join(d, fn), gauge)
    coef, rms, kp, tot = S.register(M, F)
    cy = np.array([M.shape[0]/2]); cx = np.array([M.shape[1]/2])
    dd = S.disp_at(coef, cy, cx)[0]
    # corner displacements
    corners = np.array([[0,0],[0,M.shape[1]],[M.shape[0],0],[M.shape[0],M.shape[1]]], float)
    cd = S.disp_at(coef, corners[:,0], corners[:,1])
    span = np.linalg.norm(cd - dd, axis=1).max()
    print(f"{fn} rms={rms:5.2f} kept={kp}/{tot} centre=({dd[0]:+7.2f},{dd[1]:+7.2f}) "
          f"maxcorner_dev={span:6.2f} sy={1+coef[1,0]:.5f} sx={1+coef[2,1]:.5f} "
          f"shear=({coef[2,0]:+.2e},{coef[1,1]:+.2e}) level={F.mean():.1f}", flush=True)
