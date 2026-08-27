"""Re-derive every noise-handled arm with the EMPIRICALLY MEASURED white-noise
gains, from the cache (f_mid and f_hi are stored separately, so no image is
re-read except for the nulls).  Supersedes every SUB number computed with the
analytic constant."""
import os, sys, numpy as np, softcheck as S
from analyze import load, ratio, line
from scipy import ndimage

GAUGE = sys.argv[2] if len(sys.argv) > 2 else "lin"
if GAUGE == "srgb":
    S.S_MID=(1.4,2.8); S.S_HI=(0.7,1.4); S.S_LOW=(6.0,12.0)
    G_MID, G_HI = 0.018282, 0.078028; T = 256
else:
    G_MID, G_HI = 0.078008, 0.421466; T = 128
CN = G_MID/G_HI
subj = sys.argv[1]; c = load(subj, GAUGE, T); N = int(c["N"]); nt = len(c["m_lo"])
sh = tuple(c["shape"]); lo = c["m_lo"]

def row(tag, m_mid, m_hi, f_mid, f_hi, sel, ci=True):
    a = ratio(m_mid, f_mid.max(0), sel, sh, nt, ci)
    b = ratio(m_mid-CN*m_hi, (f_mid-CN*f_hi).max(0), sel, sh, nt, ci)
    f = lambda z: f"{z['median']:.4f}" + (f" [{z['ci'][0]:.4f},{z['ci'][1]:.4f}]" if z["ci"] else "")
    print(f"  {tag:34s} NOSUB {f(a):24s} SUB(recal) {f(b):24s} n={a['n']} dropSUB={b['dropped']}")
    return a, b

print(f"=== {subj}/{GAUGE}  C_NOISE analytic {float(c['c_noise']):.5f} -> MEASURED {CN:.5f}")
sel = lo >= np.quantile(lo, 0.50)
row("BASELINE detail half", c["m_mid_none"], c["m_hi_none"], c["f_mid_none"], c["f_hi_none"], sel)
row("FLAT-ROI control", c["m_mid_none"], c["m_hi_none"], c["f_mid_none"], c["f_hi_none"], ~sel, False)
for q in (0.75, 0.90):
    s2 = lo >= np.quantile(lo, q)
    row(f"content quantile >= {q:.2f}", c["m_mid_none"], c["m_hi_none"], c["f_mid_none"], c["f_hi_none"], s2, False)
for pn in [k[6:] for k in c if k.startswith("m_mid_") and k != "m_mid_none"]:
    if pn.startswith("off"): continue
    row(f"MASTER plant {pn}", c[f"m_mid_{pn}"], c[f"m_hi_{pn}"], c["f_mid_none"], c["f_hi_none"], sel, False)
for pn in [k[6:] for k in c if k.startswith("f_mid_") and k != "f_mid_none" and not k.startswith("f_mid_off")]:
    row(f"REF plant {pn}", c["m_mid_none"], c["m_hi_none"], c[f"f_mid_{pn}"], c[f"f_hi_{pn}"], sel, False)
for n in sorted(set([3,5,9,17,33,65,129,N])):
    if n > N: continue
    idx = np.unique(np.round(np.linspace(0,N-1,n)).astype(int)); assert idx[0]==0 and idx[-1]==N-1
    row(f"n={len(idx):3d} idx {idx[0]}..{idx[-1]}", c["m_mid_none"], c["m_hi_none"],
        c["f_mid_none"][idx], c["f_hi_none"][idx], sel, False)

# nulls with the corrected sigma
d = os.path.join(S.ROOT, GAUGE, subj); M = S.load_luma(os.path.join(d,"master.tiff"), GAUGE)
oy, ox = c["oy"], c["ox"]
med = np.median(c["f_hi_none"], axis=0)
sig = np.sqrt(np.maximum(med,0)/G_HI).reshape(sh)
smap = ndimage.zoom(sig, (M.shape[0]/sh[0], M.shape[1]/sh[1]), order=1).astype(np.float32)
smap = np.pad(smap, [(0,max(0,M.shape[i]-smap.shape[i])) for i in range(2)], mode="edge")[:M.shape[0],:M.shape[1]]
rng = np.random.default_rng(11)
fm = np.zeros((N+1, nt)); fh = np.zeros((N+1, nt))
for k in range(N+1):
    F = M + smap*rng.standard_normal(M.shape).astype(np.float32)
    fm[k] = S.tile_means(S.dog(F,S.S_MID)**2, oy, ox, T); fh[k] = S.tile_means(S.dog(F,S.S_HI)**2, oy, ox, T)
print(f"  NULL noise level: median sigma {np.median(smap):.1f} DN (matched to the real frames' top band)")
row("NULL B: N+1 iid noised masters", fm[0], fh[0], fm[1:], fh[1:], sel)
