"""fardep.py -- does defocus DISTANCE explain my disagreement with V-LINEAR on bee?

In V-SOFTCHECK-bandqual.md sec.3c.1 I published a hypothesis: that the gap between
V-LINEAR's bee readings and mine lives in defocus distance, because their `far = 20`
real frames is a weak defocus on a 299-frame stack. ORCH's correction #5 now routes the
depth scoring of the confidence exponent onto bee ON THE STRENGTH OF ITS QUALIFICATION,
so the hypothesis stopped being academic and has to be tested.

My ratio() takes the GLOBALLY most-defocused probe (argmin over the selection band).
V-LINEAR takes a FIXED distance. This re-derives R at a fixed distance k and sweeps k,
entirely from the cached per-tile band powers -- no re-render, no TIFF on disk.

PRE-REGISTERED READING, written before running:
  If defocus distance explains the gap, R must RISE steeply with k and approach
  V-LINEAR's magnitude near their far. If R is flat in k, or rises and plateaus far
  below, the hypothesis is dead and I withdraw it.
"""
import os, sys, numpy as np
import dmeasure as DM

E = DM.E; NB = DM.NB
D_ = r"C:\dev\strehl-out\V-SOFTCHECK\dilut"
SEL = [1, 2]
# subject -> (npz, real frames per probe step, V-LINEAR far in real frames)
SUB = {"113MSDCF":  (D_ + r"\113MSDCF\bandqual.npz", 2, 20),
       "bee-1-cpl": (D_ + r"\bee-1-cpl\bandqual-bee-1-cpl.npz", 10, 20)}

def bname(b): return "%.2f-%.2f" % (E[b], E[b+1])

def r_fixed(P, idx, meas, k):
    """R using a partner exactly k probe-steps from the in-focus probe (the farther side)."""
    Sb = P[:, idx, :][:, :, SEL].sum(axis=2)
    Mb = P[:, idx, meas]
    n = P.shape[0]; ti = np.arange(Sb.shape[1])
    pk = np.argmax(Sb, axis=0)
    lo = pk - k; hi = pk + k
    part = np.where(hi <= n - 1, hi, lo)          # prefer +k, fall back to -k
    ok = (part >= 0) & (part <= n - 1)
    if ok.sum() < 10: return np.nan, 0
    b = Mb[pk[ok], ti[ok]]; w = Mb[part[ok], ti[ok]]
    g = np.isfinite(b) & np.isfinite(w) & (b > 0) & (w > 0)
    if g.sum() < 10: return np.nan, int(g.sum())
    return float(10 ** np.median(np.log10(b[g] / w[g]))), int(g.sum())

def r_global(P, idx, meas):
    Sb = P[:, idx, :][:, :, SEL].sum(axis=2); Mb = P[:, idx, meas]
    ti = np.arange(Sb.shape[1])
    b = Mb[np.argmax(Sb, axis=0), ti]; w = Mb[np.argmin(Sb, axis=0), ti]
    g = np.isfinite(b) & np.isfinite(w) & (b > 0) & (w > 0)
    return float(10 ** np.median(np.log10(b[g] / w[g])))

for subj, (npz, step, vlfar) in SUB.items():
    if not os.path.exists(npz): print("%s: npz absent" % subj); continue
    z = np.load(npz); P = z["P"]; TOP = z["TOP"]
    n = P.shape[0]
    kfar = max(1, int(round(vlfar / step)))
    print("=== %s : %d probes, %d real frames per probe step ===" % (subj, n, step))
    print("    V-LINEAR far=%d real frames  ==  k=%d probe steps here" % (vlfar, kfar))
    ks = [k for k in [1, 2, 3, 5, 8, 10, 15, 20, 30] if k <= n - 1]
    hdr = "  %-11s" % "band" + "".join("%9s" % ("k=%d" % k) for k in ks) + "%10s" % "global"
    print(hdr)
    for b in [2, 3, 4, 5, 6]:
        row = "  %-11s" % bname(b)
        for k in ks:
            r, _ = r_fixed(P, TOP, b, k)
            row += "%9s" % ("%.3f" % r if np.isfinite(r) else "--")
        row += "%10.3f" % r_global(P, TOP, b)
        mark = "   <-- my operating band" if b == 5 else ""
        print(row + mark)
    rk, nk = r_fixed(P, TOP, 5, kfar)
    print("    at V-LINEAR's far equivalent (k=%d): 0.30-0.35 R = %.4f  (%d tiles)" % (kfar, rk, nk))
    print("    global-argmin (what I published)   : 0.30-0.35 R = %.4f" % r_global(P, TOP, 5))
    print()
print("READING: if R is roughly flat in k, defocus distance does NOT explain the gap")
print("         and the sec.3c.1 hypothesis is refuted BY MY OWN DATA.")
