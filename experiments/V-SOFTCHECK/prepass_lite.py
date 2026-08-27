"""Same instrument, reduced arm set, for large brackets."""
import os, sys, time, numpy as np, softcheck as S
SUBJ = sys.argv[1]; GAUGE = "lin"; T, STEP, MARGIN = 128, 64, 176
PLANTS = {"none": None, "blur070": ("blur", 0.70), "sharp030": ("sharpen", 0.30, 1.0),
          "gain170": ("gain", 1.70)}
REF_PLANTS = ["none", "blur070", "gain170"]
OFFSETS = [(0,0), (8,0), (24,24)]
d = os.path.join(S.ROOT, GAUGE, SUBJ)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff"))
N = len(fl)
n_arw = len([f for f in os.listdir(rf"D:\personal\macro\{SUBJ}") if f.lower().endswith(".arw")])
assert N == n_arw, f"COMPLETE-BRACKET CHECK FAILED: {N} vs {n_arw}"
assert [int(f[1:4]) for f in fl] == list(range(N)), "MISSING FRAME INDEX"
print(f"{SUBJ}: {N} == {n_arw} RAW (complete bracket, first={fl[0]} last={fl[-1]})", flush=True)
M = S.load_luma(os.path.join(d, "master.tiff"), GAUGE); H, W = M.shape
oy, ox, shape = S.build_grid(H, W, T, STEP, MARGIN); cy = oy+T/2.0; cx = ox+T/2.0; nt = len(oy)
out = dict(subject=SUBJ, gauge=GAUGE, T=T, step=STEP, margin=MARGIN, N=N, oy=oy, ox=ox,
           shape=np.array(shape), c_noise=S.C_NOISE, frames=np.array(fl))
for pn, spec in PLANTS.items():
    Mp = S.apply_plant(M, spec)
    out[f"m_mid_{pn}"] = S.tile_means(S.dog(Mp, S.S_MID)**2, oy, ox, T)
    out[f"m_hi_{pn}"]  = S.tile_means(S.dog(Mp, S.S_HI)**2,  oy, ox, T)
out["m_lo"] = S.tile_means(S.dog(M, S.S_LOW)**2, oy, ox, T)
out["m_lv"] = S.tile_means(M, oy, ox, T)
for pn in REF_PLANTS + [f"off_{o[0]}_{o[1]}" for o in OFFSETS]:
    out[f"f_mid_{pn}"] = np.zeros((N, nt), np.float32); out[f"f_hi_{pn}"] = np.zeros((N, nt), np.float32)
out["f_lv"] = np.zeros((N, nt), np.float32)
coefs = np.zeros((N,3,2)); rms = np.zeros(N); kept = np.zeros(N, int); t0 = time.time()
for k, fn in enumerate(fl):
    F = S.load_luma(os.path.join(d, fn), GAUGE)
    coef, r, kp, tot = S.register(M, F); coefs[k]=coef; rms[k]=r; kept[k]=kp
    dd = S.disp_at(coef, cy, cx)
    by = np.round(oy+dd[:,0]).astype(int); bx = np.round(ox+dd[:,1]).astype(int)
    for pn in REF_PLANTS:
        Fp = S.apply_plant(F, PLANTS[pn])
        dm = S.dog(Fp, S.S_MID)**2; dh = S.dog(Fp, S.S_HI)**2
        ry = np.clip(by,0,H-T); rx = np.clip(bx,0,W-T)
        out[f"f_mid_{pn}"][k] = S.tile_means(dm, ry, rx, T); out[f"f_hi_{pn}"][k] = S.tile_means(dh, ry, rx, T)
        if pn == "none":
            out["f_lv"][k] = S.tile_means(Fp, ry, rx, T)
            for o in OFFSETS:
                ry2 = np.clip(by+o[0],0,H-T); rx2 = np.clip(bx+o[1],0,W-T)
                out[f"f_mid_off_{o[0]}_{o[1]}"][k] = S.tile_means(dm, ry2, rx2, T)
                out[f"f_hi_off_{o[0]}_{o[1]}"][k]  = S.tile_means(dh, ry2, rx2, T)
    if k % 10 == 0: print(f"  {fn} rms={r:.2f} ({time.time()-t0:.0f}s)", flush=True)
out["coefs"]=coefs; out["reg_rms"]=rms; out["reg_kept"]=kept
np.savez_compressed(os.path.join(S.ROOT,"cache",f"{SUBJ}--lin--T{T}.npz"), **out)
print("saved", f"{time.time()-t0:.0f}s")
