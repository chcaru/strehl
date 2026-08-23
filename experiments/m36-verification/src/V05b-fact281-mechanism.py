"""M36 V05b: is the SIGN FLIP in V05 real, or resampling noise?  And what is the
mechanism -- does the report's stated mechanism for fact 281 survive?

Report's mechanism (M34 s3): "dim, photon-starved pixels have FLAT through-focus
curves, so missing the peak costs them little."  That predicts inverse-SNR of the
frame-averaged image -- an unambiguous dimness measure -- must ALSO be
anti-informative.  V05 measured its worst-5% lift at 1.111x.  Test it properly.
"""
import numpy as np, os, json
from scipy.stats import spearmanr

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
CACHE34 = os.path.join(ROOT, "m34-confidence-vector", "out", "cache")
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E = 50/436.8, 4.20
res = {}

dense = np.asarray(np.load(os.path.join(ROOT, "m33-subframe-offset", "out", "cache",
                                        "dense_focus.npy"), mmap_mode="r"), np.float32)
raw = np.asarray(np.load(os.path.join(ROOT, "m32-posterior", "out", "cache", "raw.npy"),
                         mmap_mode="r"), np.float32)
foc = np.ascontiguousarray(dense[::2])
n, HH, WW = foc.shape
yy, xx = np.mgrid[0:HH, 0:WW]
base_d = dense.min(0)
tp = np.maximum(dense.max(0)-base_d, 1e-6)
td2 = np.clip(1.0 - np.maximum(foc.max(0)-base_d, 1e-6)/tp, 0, 1)
td = td2.ravel(); gm = float(td.mean())

tail = np.concatenate([foc[:6], foc[-6:]], 0)
d2 = tail[2:]-2*tail[1:-1]+tail[:-2]
sf = np.sqrt(np.maximum(d2.var(0), 1e-12)/6.0).astype(np.float32)
fmax, kmx = foc.max(0), foc.argmax(0)
vk = G*np.clip(raw, 0, None) + (RN_E*G)**2
def sos(acc):
    na = acc.sum(0).astype(np.float32)
    return ((np.sqrt((vk*acc).sum(0))/np.maximum(na, 1)) /
            np.maximum((raw*acc).sum(0)/np.maximum(na, 1), 1e-3))
acc1 = (fmax[None]-foc) <= sf[None]
nacc = acc1.sum(0).astype(np.float32)
one = np.zeros(foc.shape, bool); one[kmx, yy, xx] = True
mimg = raw.mean(0)
V = {"C1_gate1sig": sos(acc1), "C1_argmax_only": sos(one),
     "C1_inv_snr_meanimg": np.sqrt(G*np.clip(mimg, 0, None)+(RN_E*G)**2)/np.maximum(mimg, 1e-3),
     "acceptance_set_size": nacc, "peak_minus_base": tp, "mean_signal": mimg}

B = 64; nb = HH//B
tdb = td2.reshape(nb, B, nb, B).transpose(0, 2, 1, 3).reshape(nb*nb, B*B)
rb = np.random.default_rng(3660)

def boot_lift(v2d, nboot=300, sign=1):
    vb = (sign*v2d.astype(np.float64)).reshape(nb, B, nb, B).transpose(0, 2, 1, 3).reshape(nb*nb, B*B)
    out = []
    for _ in range(nboot):
        s = rb.integers(0, nb*nb, nb*nb)
        c = vb[s].ravel(); t = tdb[s].ravel()
        k = int(round(0.05*c.size))
        i = np.argpartition(c + rb.uniform(0, 1e-12, c.size)*(np.ptp(c)+1e-12), -k)[-k:]
        out.append(t[i].mean()/t.mean())
    return np.array(out)

print("channel                  worst-5% lift   bootstrap 95% CI        P(lift<1)")
for nm in ("C1_gate1sig", "C1_argmax_only", "C1_inv_snr_meanimg"):
    v = V[nm]
    k = int(round(0.05*v.size))
    i = np.argpartition(v.ravel().astype(np.float64), -k)[-k:]
    pt = float(td[i].mean()/gm)
    b = boot_lift(v)
    res[nm] = dict(lift=pt, ci=[float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))],
                   p_below_1=float((b < 1).mean()))
    print(f"{nm:24s} {pt:.4f}         [{np.percentile(b,2.5):.4f}, {np.percentile(b,97.5):.4f}]"
          f"      {(b<1).mean():.4f}")

print("\nmechanism: decile tables (10 = worst / dimmest)")
sub = np.random.default_rng(3661).choice(td.size, 300_000, replace=False)
mech = {}
for nm in ("C1_inv_snr_meanimg", "acceptance_set_size", "peak_minus_base", "mean_signal"):
    v = V[nm].ravel().astype(np.float64)
    q = np.quantile(v, np.linspace(0, 1, 11))
    rows = []
    for i in range(10):
        m = (v >= q[i]) & ((v <= q[i+1]) if i == 9 else (v < q[i+1]))
        rows.append(float(td[m].mean()))
    rho = float(spearmanr(v[sub], td[sub]).statistic)
    mech[nm] = dict(deciles=rows, spearman=rho)
    print(f"  {nm:22s} rho {rho:+.4f}  deciles " + " ".join(f"{x:.4f}" for x in rows))
res["mechanism"] = mech

json.dump(res, open(os.path.join(OUT, "V05b-fact281-mechanism.json"), "w"), indent=1)
print("wrote V05b-fact281-mechanism.json")
