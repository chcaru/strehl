"""One pass over a subject: register every frame to the master and cache the
per-tile band statistics for the master, for every frame, under several
planted disturbances and several deliberate reference-offset errors.

Every arm of the commissioning table and every real ratio is then computed
from this cache, so no arm can differ from another by anything except the
disturbance it names.
"""
import os, sys, time, numpy as np, softcheck as S

SUBJ  = sys.argv[1]
GAUGE = sys.argv[2] if len(sys.argv) > 2 else "lin"
T     = int(sys.argv[3]) if len(sys.argv) > 3 else 128
STEP  = int(sys.argv[4]) if len(sys.argv) > 4 else 64
MARGIN= 176

PLANTS = {
    "none":      None,
    "blur040":   ("blur", 0.40),
    "blur070":   ("blur", 0.70),
    "blur100":   ("blur", 1.00),
    "sharp030":  ("sharpen", 0.30, 1.0),
    "sharp060":  ("sharpen", 0.60, 1.0),
    "gain170":   ("gain", 1.70),
}
REF_PLANTS = ["none", "blur040", "blur070", "sharp030", "gain170"]
OFFSETS = [(0,0), (2,0), (4,0), (8,0), (16,0), (-4,0), (-8,0), (0,8), (0,-8), (24,24)]

d = os.path.join(S.ROOT, GAUGE, SUBJ)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff"))
N = len(fl)
n_arw = len([f for f in os.listdir(rf"D:\personal\macro\{SUBJ}") if f.lower().endswith(".arw")])
assert N == n_arw, f"COMPLETE-BRACKET CHECK FAILED: {N} renders vs {n_arw} RAW frames"
print(f"{SUBJ}/{GAUGE}: {N} frames == {n_arw} RAW files (complete bracket, no subsampling)")
print(f"first={fl[0]} last={fl[-1]}  indices 0..{N-1} all present: "
      f"{[int(f[1:4]) for f in fl] == list(range(N))}")

M = S.load_luma(os.path.join(d, "master.tiff"), GAUGE)
H, W = M.shape
oy, ox, shape = S.build_grid(H, W, T, STEP, MARGIN)
cy = oy + T/2.0; cx = ox + T/2.0
nt = len(oy)
print("tiles", nt, shape, "image", M.shape)

out = dict(subject=SUBJ, gauge=GAUGE, T=T, step=STEP, margin=MARGIN, N=N,
           oy=oy, ox=ox, shape=np.array(shape), c_noise=S.C_NOISE,
           frames=np.array(fl))

for pname, spec in PLANTS.items():
    Mp = S.apply_plant(M, spec)
    out[f"m_mid_{pname}"] = S.tile_means(S.dog(Mp, S.S_MID)**2, oy, ox, T)
    out[f"m_hi_{pname}"]  = S.tile_means(S.dog(Mp, S.S_HI)**2,  oy, ox, T)
out["m_lo"] = S.tile_means(S.dog(M, S.S_LOW)**2, oy, ox, T)
out["m_lv"] = S.tile_means(M, oy, ox, T)
print("master stats done", flush=True)

coefs = np.zeros((N, 3, 2)); rms = np.zeros(N); kept = np.zeros(N, int)
for pn in REF_PLANTS:
    out[f"f_mid_{pn}"] = np.zeros((N, nt), np.float64)
    out[f"f_hi_{pn}"]  = np.zeros((N, nt), np.float64)
for off in OFFSETS:
    out[f"f_mid_off_{off[0]}_{off[1]}"] = np.zeros((N, nt), np.float64)
    out[f"f_hi_off_{off[0]}_{off[1]}"]  = np.zeros((N, nt), np.float64)
out["f_lv"] = np.zeros((N, nt), np.float64)

t0 = time.time()
for k, fn in enumerate(fl):
    F = S.load_luma(os.path.join(d, fn), GAUGE)
    coef, r, kp, tot = S.register(M, F)
    coefs[k] = coef; rms[k] = r; kept[k] = kp
    dd = S.disp_at(coef, cy, cx)
    base_y = np.round(oy + dd[:,0]).astype(int); base_x = np.round(ox + dd[:,1]).astype(int)
    for pn in REF_PLANTS:
        Fp = S.apply_plant(F, PLANTS[pn])
        dm = S.dog(Fp, S.S_MID)**2; dh = S.dog(Fp, S.S_HI)**2
        ry = np.clip(base_y, 0, H-T); rx = np.clip(base_x, 0, W-T)
        out[f"f_mid_{pn}"][k] = S.tile_means(dm, ry, rx, T)
        out[f"f_hi_{pn}"][k]  = S.tile_means(dh, ry, rx, T)
        if pn == "none":
            out["f_lv"][k] = S.tile_means(Fp, ry, rx, T)
            for off in OFFSETS:
                ry2 = np.clip(base_y+off[0], 0, H-T); rx2 = np.clip(base_x+off[1], 0, W-T)
                out[f"f_mid_off_{off[0]}_{off[1]}"][k] = S.tile_means(dm, ry2, rx2, T)
                out[f"f_hi_off_{off[0]}_{off[1]}"][k]  = S.tile_means(dh, ry2, rx2, T)
    print(f"  {fn} rms={r:.2f} kept={kp}/{tot} ({time.time()-t0:.0f}s)", flush=True)

out["coefs"] = coefs; out["reg_rms"] = rms; out["reg_kept"] = kept
os.makedirs(os.path.join(S.ROOT, "cache"), exist_ok=True)
np.savez_compressed(os.path.join(S.ROOT, "cache", f"{SUBJ}--{GAUGE}--T{T}.npz"), **out)
print("saved", f"{SUBJ}--{GAUGE}--T{T}.npz", f"{time.time()-t0:.0f}s")
