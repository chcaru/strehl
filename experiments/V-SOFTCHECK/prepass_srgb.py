"""sRGB gauge: BOTH sides are the shipped output transform.

The numerator is byte-identical to the shipped SHIP-V4 master (verified by
sha256).  Every reference member is the SAME binary, the SAME --srgb, and the
SAME --exposure +1.53 that the master itself chose -- so the colour matrix,
the exposure multiply and the sRGB transfer curve are applied identically to
numerator and denominator.  That is the whole point of this arm.

The sRGB render is at 2x the linear resolution per axis, so the DoG sigmas and
the tile size are scaled by 2 to keep the SAME optical band and the SAME
physical sites as the linear gauge.
"""
import os, sys, time, numpy as np, softcheck as S

SUBJ = sys.argv[1]; GAUGE = "srgb"
S.S_MID = (1.4, 2.8); S.S_HI = (0.7, 1.4); S.S_LOW = (6.0, 12.0)
S.G_MID = S._white_gain(*S.S_MID); S.G_HI = S._white_gain(*S.S_HI)
S.C_NOISE = S.G_MID / S.G_HI
T, STEP, MARGIN = 256, 128, 352
PLANTS = {"none": None, "blur080": ("blur", 0.80), "blur140": ("blur", 1.40),
          "sharp030": ("sharpen", 0.30, 2.0), "gain170": ("gain", 1.70)}
REF_PLANTS = ["none", "blur080", "gain170"]
OFFSETS = [(0,0), (16,0), (48,48)]

d = os.path.join(S.ROOT, GAUGE, SUBJ)
fl = sorted(f for f in os.listdir(d) if f.startswith("f") and f.endswith(".tiff"))
N = len(fl)
n_arw = len([f for f in os.listdir(rf"D:\personal\macro\{SUBJ}") if f.lower().endswith(".arw")])
assert N == n_arw, f"COMPLETE-BRACKET CHECK FAILED: {N} vs {n_arw}"
print(f"{SUBJ}/srgb: {N} == {n_arw} RAW (complete bracket)  c_noise={S.C_NOISE:.5f}")
M = S.load_luma(os.path.join(d, "master.tiff"), GAUGE)
H, W = M.shape; print("image", M.shape)
oy, ox, shape = S.build_grid(H, W, T, STEP, MARGIN)
cy = oy + T/2.0; cx = ox + T/2.0; nt = len(oy)
print("tiles", nt, shape, flush=True)
out = dict(subject=SUBJ, gauge=GAUGE, T=T, step=STEP, margin=MARGIN, N=N,
           oy=oy, ox=ox, shape=np.array(shape), c_noise=S.C_NOISE, frames=np.array(fl))
for pn, spec in PLANTS.items():
    Mp = S.apply_plant(M, spec)
    out[f"m_mid_{pn}"] = S.tile_means(S.dog(Mp, S.S_MID)**2, oy, ox, T)
    out[f"m_hi_{pn}"]  = S.tile_means(S.dog(Mp, S.S_HI)**2,  oy, ox, T)
out["m_lo"] = S.tile_means(S.dog(M, S.S_LOW)**2, oy, ox, T)
out["m_lv"] = S.tile_means(M, oy, ox, T)
for pn in REF_PLANTS + [f"off_{o[0]}_{o[1]}" for o in OFFSETS]:
    out[f"f_mid_{pn}"] = np.zeros((N, nt)); out[f"f_hi_{pn}"] = np.zeros((N, nt))
out["f_lv"] = np.zeros((N, nt))
coefs = np.zeros((N,3,2)); rms = np.zeros(N); kept = np.zeros(N, int)
t0 = time.time()
for k, fn in enumerate(fl):
    F = S.load_luma(os.path.join(d, fn), GAUGE)
    coef, r, kp, tot = S.register(M, F, win=1024, ny=4, nx=6, margin=128)
    coefs[k] = coef; rms[k] = r; kept[k] = kp
    dd = S.disp_at(coef, cy, cx)
    by = np.round(oy + dd[:,0]).astype(int); bx = np.round(ox + dd[:,1]).astype(int)
    for pn in REF_PLANTS:
        Fp = S.apply_plant(F, PLANTS[pn])
        dm = S.dog(Fp, S.S_MID)**2; dh = S.dog(Fp, S.S_HI)**2
        ry = np.clip(by,0,H-T); rx = np.clip(bx,0,W-T)
        out[f"f_mid_{pn}"][k] = S.tile_means(dm, ry, rx, T)
        out[f"f_hi_{pn}"][k]  = S.tile_means(dh, ry, rx, T)
        if pn == "none":
            out["f_lv"][k] = S.tile_means(Fp, ry, rx, T)
            for o in OFFSETS:
                ry2 = np.clip(by+o[0],0,H-T); rx2 = np.clip(bx+o[1],0,W-T)
                out[f"f_mid_off_{o[0]}_{o[1]}"][k] = S.tile_means(dm, ry2, rx2, T)
                out[f"f_hi_off_{o[0]}_{o[1]}"][k]  = S.tile_means(dh, ry2, rx2, T)
    print(f"  {fn} rms={r:.2f} ({time.time()-t0:.0f}s)", flush=True)
out["coefs"]=coefs; out["reg_rms"]=rms; out["reg_kept"]=kept
np.savez_compressed(os.path.join(S.ROOT,"cache",f"{SUBJ}--srgb--T{T}.npz"), **out)
print("saved", f"{time.time()-t0:.0f}s")
