"""Does the merge's own reported 'averaged' fraction predict where it loses to a
single frame? 'averaged' is the fraction of finest-band coefficients where NO
frame cleared the --gate 4 noise gate, so the merge averaged instead of
selecting. Averaging a scene that focus breathing displaces must blur fine
detail, so a high averaged fraction predicts fine-band loss. Test it."""
import re, numpy as np, warnings
from pathlib import Path
from scipy.stats import spearmanr
from curve import arms
warnings.filterwarnings("ignore")
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB"); RAW = Path(r"D:\personal\macro")
AVG = re.compile(r"averaged\s*:\s*([0-9. %]+)")
rows = []
for p in sorted(GAL.glob("*.tiff")):
    s = p.stem
    lg = GAL / f"{s}.log"
    if not lg.exists() or not (RAW / s).is_dir():
        continue
    m = AVG.search(lg.read_text(errors="ignore"))
    if not m:
        continue
    av = float(m.group(1).split()[0].replace("%", ""))
    try:
        a = arms(s, peak_min=0.80)
    except Exception:
        continue
    fl = np.sqrt(np.nanmedian(a["F"]))
    if not np.isfinite(fl) or not (5.0 <= fl <= 60.0):
        continue
    real = np.isfinite(a["snr"]) & (a["snr"] >= 3.0)
    if real.sum() < 20:
        continue
    Smt = np.maximum(a["Em"] - np.minimum(a["Fm"], a["F"]), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        rc = np.sqrt(Smt) / np.sqrt(np.maximum(a["Sft"], 1e-12))
    rows.append((s, av, float(np.mean(rc[real] >= 1.0) * 100), int(real.sum())))
rows.sort(key=lambda t: -t[1])
print(f"{'subject':36s} {'avgFinest':>9} {'capped>=frm':>11} {'detail':>7}")
print("-" * 68)
for s, av, w, nd in rows:
    print(f"{s:36s} {av:8.1f}% {w:10.1f}% {nd:3d}/352")
av = np.array([r[1] for r in rows]); w = np.array([r[2] for r in rows])
nd = np.array([r[3] for r in rows])
r1, p1 = spearmanr(av, w)
print(f"\nn = {len(rows)} subjects")
print(f"Spearman(averaged_finest, merge>=frame)  rho = {r1:+.3f}  p = {p1:.4f}")
r2, p2 = spearmanr(av, nd)
print(f"Spearman(averaged_finest, detail tiles)  rho = {r2:+.3f}  p = {p2:.4f}")
hi = av >= 80.0
print(f"\nsubjects with averaged >= 80%: n={int(hi.sum())}, "
      f"median merge>=frame {np.median(w[hi]):.1f}%")
print(f"subjects with averaged <  80%: n={int((~hi).sum())}, "
      f"median merge>=frame {np.median(w[~hi]):.1f}%")
