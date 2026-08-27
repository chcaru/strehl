"""POSITIVE CONTROL, the number.

E_mid at an in-focus tile, divided by E_mid at THE SAME TILE in frames k-off
and k+off.  Reported two ways:
  LITERAL   -- identical pixel coordinates in every frame, exactly as the
               brief specifies.
  MY PATH   -- the registered coordinates my instrument actually uses.
If those differ materially the drift matters; if not, it does not.

Also reported over the top-32 tiles by E_lo (the focus-INSENSITIVE coarse
band), so the headline is not resting on one hand-picked tile.
"""
import os, sys, numpy as np, softcheck as S
from analyze import load
CN = 0.185088
subj = sys.argv[1]; K = int(sys.argv[2]); OFFS = [int(x) for x in sys.argv[3].split(",")]
T, MARGIN, GAU = 128, 176, "lin"
d = os.path.join(S.ROOT, GAU, subj)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff")); N = len(fl)
c = load(subj, GAU, T); oy=np.asarray(c["oy"]); ox=np.asarray(c["ox"]); lo=np.asarray(c["m_lo"])
M = S.load_luma(os.path.join(d,"master.tiff"), GAU); H,W = M.shape
cy0, cx0 = H/2, W/2
near = (np.abs(oy+T/2-cy0) < H*0.30) & (np.abs(ox+T/2-cx0) < W*0.30)
cand = np.where(near & (lo >= np.quantile(lo[near], 0.95)))[0]
t = cand[np.argmax(lo[cand])]
top = cand[np.argsort(lo[cand])[::-1][:32]]
need = sorted({K} | {K-o for o in OFFS} | {K+o for o in OFFS})
assert all(0 <= k < N for k in need), f"offsets leave the bracket: {need} vs N={N}"
print(f"{subj}: N={N}  in-focus frame k={K} (confirmed visually)  tile #{t} at (y={oy[t]},x={ox[t]})")
E = {}
for k in need:
    Fk = S.load_luma(os.path.join(d, fl[k]), GAU)
    dm = S.dog(Fk,S.S_MID)**2; dh = S.dog(Fk,S.S_HI)**2
    lit_m = S.tile_means(dm, oy[top], ox[top], T); lit_h = S.tile_means(dh, oy[top], ox[top], T)
    coef,rms,kp,tot = S.register(M, Fk)
    dd = S.disp_at(coef, oy[top]+T/2.0, ox[top]+T/2.0)
    ry = np.clip(np.round(oy[top]+dd[:,0]).astype(int),0,H-T); rx = np.clip(np.round(ox[top]+dd[:,1]).astype(int),0,W-T)
    reg_m = S.tile_means(dm, ry, rx, T); reg_h = S.tile_means(dh, ry, rx, T)
    E[k] = (lit_m, lit_h, reg_m, reg_h)
i0 = list(top).index(t)
print(f"\n  THE VISUALLY CONFIRMED TILE (#{t})")
print(f"  {'offset':>8s} {'E_mid(k)':>12s} {'E_mid(k-off)':>13s} {'E_mid(k+off)':>13s}"
      f" {'ratio -':>9s} {'ratio +':>9s} {'ratio SUB -':>12s} {'ratio SUB +':>12s}")
for o in OFFS:
    a=E[K]; b=E[K-o]; cc=E[K+o]
    f=lambda x: x[0][i0]
    g=lambda x: x[0][i0]-CN*x[1][i0]
    print(f"  {'+-'+str(o):>8s} {f(a):12.1f} {f(b):13.1f} {f(cc):13.1f}"
          f" {f(a)/f(b):9.2f} {f(a)/f(cc):9.2f} {g(a)/g(b):12.2f} {g(a)/g(cc):12.2f}")
print(f"\n  MEDIAN OVER THE TOP {len(top)} TILES BY E_lo (focus-insensitive selection)")
print(f"  {'offset':>8s} {'LITERAL same-coords':>21s} {'MY PATH registered':>20s} {'SUB, my path':>14s}")
for o in OFFS:
    a=E[K]; b=E[K-o]; cc=E[K+o]
    litr = np.concatenate([a[0]/b[0], a[0]/cc[0]])
    regr = np.concatenate([a[2]/b[2], a[2]/cc[2]])
    subr = np.concatenate([(a[2]-CN*a[3])/(b[2]-CN*b[3]), (a[2]-CN*a[3])/(cc[2]-CN*cc[3])])
    print(f"  {'+-'+str(o):>8s} {np.median(litr):21.2f} {np.median(regr):20.2f} {np.median(subr):14.2f}")
