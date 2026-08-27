"""Genuine 1:1 crops, <=400 px, matched display gauge on both panels.
Picks the highest-content tiles where the measured deficit is largest."""
import os, sys, numpy as np, softcheck as S
from analyze import load
from PIL import Image

subj = sys.argv[1]; gauge = "lin"; T = 128
c = load(subj, gauge, T)
d = os.path.join(S.ROOT, gauge, subj)
M = S.load_luma(os.path.join(d, "master.tiff"), gauge)
oy, ox = c["oy"], c["ox"]; lo = c["m_lo"]
fm = c["f_mid_none"]; r = c["m_mid_none"]/fm.max(0)
top = lo >= np.quantile(lo, 0.90)
cand = np.where(top)[0]
cand = cand[np.argsort(r[cand])][:3]
outdir = os.path.join(S.ROOT, "crops"); os.makedirs(outdir, exist_ok=True)
CS = 320
for rank, t in enumerate(cand):
    k = int(fm[:, t].argmax())
    F = S.load_luma(os.path.join(d, f"f{k:03d}.tiff"), gauge)
    coef = c["coefs"][k]
    dd = S.disp_at(coef, np.array([oy[t]+T/2.0]), np.array([ox[t]+T/2.0]))[0]
    y0 = int(oy[t]+T//2-CS//2); x0 = int(ox[t]+T//2-CS//2)
    fy = int(round(y0+dd[0])); fx = int(round(x0+dd[1]))
    a = M[y0:y0+CS, x0:x0+CS]; b = F[fy:fy+CS, fx:fx+CS]
    lo_v = float(np.percentile(np.concatenate([a.ravel(), b.ravel()]), 1))
    hi_v = float(np.percentile(np.concatenate([a.ravel(), b.ravel()]), 99.5))
    def enc(x):
        y = np.clip((x-lo_v)/(hi_v-lo_v), 0, 1) ** (1/2.2)
        return Image.fromarray((y*255).astype(np.uint8))
    tag = f"{subj}-site{rank}-ratio{r[t]:.3f}"
    enc(a).save(os.path.join(outdir, f"{tag}-MASTER.png"))
    enc(b).save(os.path.join(outdir, f"{tag}-BESTFRAME{k}.png"))
    print(f"{tag}: master tile ({y0},{x0})  best frame {k} at ({fy},{fx})  "
          f"E_mid master {c['m_mid_none'][t]:.1f} best {fm[:,t].max():.1f}")
