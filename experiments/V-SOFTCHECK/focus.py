"""POSITIVE CONTROL: does my statistic respond to focus at all?

Tile choice must not be circular, so the tile is picked by E_lo -- the COARSE
band (peak 0.053 c/opx), which is focus-insensitive -- never by E_mid, the
statistic under test.  Among high-E_lo tiles near the frame centre, take the
one with the most coarse structure and enough room in the bracket for the
requested offsets.  The in-focus frame k is then confirmed BY EYE from 1:1
crops before any ratio is quoted.

Crops are genuine 1:1 (no resampling), <=400 px, and share ONE display gauge
taken from frame k, so the three panels are photometrically comparable.
"""
import os, sys, numpy as np, softcheck as S
from PIL import Image
from analyze import load

subj = sys.argv[1]; CROP = 320; T, STEP, MARGIN, GAU = 128, 64, 176, "lin"
d = os.path.join(S.ROOT, GAU, subj)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff")); N = len(fl)
c = load(subj, GAU, T); oy = np.asarray(c["oy"]); ox = np.asarray(c["ox"])
lo = np.asarray(c["m_lo"]); F = np.asarray(c["f_mid_none"])
M = S.load_luma(os.path.join(d, "master.tiff"), GAU); H, W = M.shape

cy0, cx0 = H/2, W/2
near = (np.abs(oy+T/2-cy0) < H*0.30) & (np.abs(ox+T/2-cx0) < W*0.30)
cand = np.where(near & (lo >= np.quantile(lo[near], 0.95)))[0]
t = cand[np.argmax(lo[cand])]
print(f"{subj}: N={N}  tile #{t} at (y={oy[t]}, x={ox[t]})  chosen by E_lo (coarse band) = {lo[t]:.1f}")
print(f"  E_lo rank of this tile: {(lo < lo[t]).sum()}/{len(lo)}  (selection is focus-insensitive by construction)")

ks = np.unique(np.linspace(0, N-1, 9).astype(int))
print(f"  scanning frames {list(ks)} -- crops written for visual confirmation")
outd = os.path.join(S.ROOT, "crops", f"focus-{subj}"); os.makedirs(outd, exist_ok=True)
y0 = int(np.clip(oy[t]+T//2-CROP//2, 0, H-CROP)); x0 = int(np.clip(ox[t]+T//2-CROP//2, 0, W-CROP))
gauge = None
rows = []
for k in ks:
    Fk = S.load_luma(os.path.join(d, fl[k]), GAU)
    coef, rms, kp, tot = S.register(M, Fk)
    dy, dx = S.disp_at(coef, np.array([oy[t]+T/2.0]), np.array([ox[t]+T/2.0]))[0]
    ry = int(np.clip(round(y0+dy), 0, H-CROP)); rx = int(np.clip(round(x0+dx), 0, W-CROP))
    crop = Fk[ry:ry+CROP, rx:rx+CROP]
    if gauge is None: gauge = (np.percentile(crop, 0.5), np.percentile(crop, 99.5))
    v = np.clip((crop-gauge[0])/(gauge[1]-gauge[0]), 0, 1)
    Image.fromarray((v**(1/2.2)*255).astype(np.uint8)).save(os.path.join(outd, f"k{k:03d}.png"))
    rows.append((k, F[k, t], rms))
    print(f"    frame {k:3d}  E_mid={F[k,t]:12.2f}  (reg rms {rms:.2f}px)")
print(f"  crops -> {outd}")
