"""M36 V06: does fact 281 survive on a DIFFERENT STACK?

119MSDCF: 33 frames, ISO 50, same sensor, same crop.  x2 decimation gives 17
frames against a 33-frame dense grid -- the same experiment M34 ran on
coffee-bean's 105 -> 53.

Also carries the acceptance-set mechanism test across, and re-measures C3's own
lift so the comparison is on a scale.
"""
import numpy as np, rawpy, glob, os, json, time
from scipy.ndimage import sobel, uniform_filter
from scipy.stats import spearmanr

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT, "m36-verification", "out")
CACHE = os.path.join(OUT, "cache")
BLACK, R = 512, 2
CY, CX, H = 1172, 1757, 512
ys, xs = slice(0, 4688, 2), slice(1, 7028, 2)
res = {}

STACKS = {"119MSDCF": (r"D:\personal\macro\119MSDCF", 50, 4.20),
          "112MSDCF": (r"D:\personal\macro\112MSDCF", 500, 1.47)}

def build(src, tag):
    fr = os.path.join(CACHE, f"{tag}_raw.npy")
    ff = os.path.join(CACHE, f"{tag}_foc.npy")
    if os.path.exists(fr) and os.path.exists(ff):
        return np.load(fr, mmap_mode="r"), np.load(ff, mmap_mode="r")
    files = sorted(glob.glob(os.path.join(src, "*.ARW")))
    n = len(files); t0 = time.time()
    raw = np.empty((n, 2*H, 2*H), np.float32); foc = np.empty_like(raw)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            assert r.raw_image_visible.shape == (4688, 7028), r.raw_image_visible.shape
            v = r.raw_image_visible[ys, xs][CY-H:CY+H, CX-H:CX+H].astype(np.float32) - BLACK
        raw[i] = v
        gx = sobel(v, axis=1, mode="nearest"); gy = sobel(v, axis=0, mode="nearest")
        foc[i] = uniform_filter(np.hypot(gx, gy), size=2*R+1, mode="nearest")
    print(f"  {tag}: {n} frames decoded in {time.time()-t0:.0f}s")
    np.save(fr, raw); np.save(ff, foc)
    return raw, foc

for tag, (src, iso, rn) in STACKS.items():
    G = iso/436.8
    raw_all, foc_all = build(src, tag)
    raw_all = np.asarray(raw_all, np.float32); foc_all = np.asarray(foc_all, np.float32)
    nd = foc_all.shape[0]
    coarse_sel = np.arange(0, nd, 2)
    foc = foc_all[coarse_sel]; raw = raw_all[coarse_sel]
    n, HH, WW = foc.shape
    yy, xx = np.mgrid[0:HH, 0:WW]
    base_d = foc_all.min(0)
    tp = np.maximum(foc_all.max(0)-base_d, 1e-6)
    td = np.clip(1.0 - np.maximum(foc.max(0)-base_d, 1e-6)/tp, 0, 1).ravel()
    gm = float(td.mean())
    print(f"\n{tag}: dense {nd} frames -> coarse {n}; ISO {iso}, g {G:.5f}, RN {rn} e-")
    print(f"  true deficit (M34 defn): mean {gm:.5f}  exactly_zero {float((td==0).mean()):.4%}")

    tail = np.concatenate([foc[:6], foc[-6:]], 0)
    d2 = tail[2:]-2*tail[1:-1]+tail[:-2]
    sf = np.sqrt(np.maximum(d2.var(0), 1e-12)/6.0).astype(np.float32)
    fmax, kmx = foc.max(0), foc.argmax(0)
    vk = G*np.clip(raw, 0, None) + (rn*G)**2
    def sos(acc):
        na = acc.sum(0).astype(np.float32)
        return ((np.sqrt((vk*acc).sum(0))/np.maximum(na, 1)) /
                np.maximum((raw*acc).sum(0)/np.maximum(na, 1), 1e-3)).ravel()
    acc1 = (fmax[None]-foc) <= sf[None]
    nacc = acc1.sum(0).ravel()
    one = np.zeros(foc.shape, bool); one[kmx, yy, xx] = True
    mimg = raw.mean(0)
    # C3, M34's corrected log-baseline fit
    base = foc.min(0); km = np.clip(kmx, 1, n-2)
    a0 = np.log(np.maximum(foc[km, yy, xx]-base, 1e-6))
    am_ = np.log(np.maximum(foc[km-1, yy, xx]-base, 1e-6))
    ap = np.log(np.maximum(foc[km+1, yy, xx]-base, 1e-6))
    den = am_-2*a0+ap; ok = den < -1e-9
    xst = np.clip(np.where(ok, 0.5*(am_-ap)/np.where(ok, den, 1.0), 0.0), -1, 1)
    c3 = np.clip(1.0-np.exp(np.minimum(a0-(a0+0.25*(ap-am_)*xst), 0.0)), 0, 1)
    c3[~ok] = 0.0
    ch = {"C1_gate1sig": sos(acc1), "C1_argmax_only": sos(one),
          "C1_inv_snr_meanimg": (np.sqrt(G*np.clip(mimg, 0, None)+(rn*G)**2)/np.maximum(mimg, 1e-3)).ravel(),
          "acceptance_set_size": nacc.astype(np.float64), "C3_deficit": c3.ravel()}
    rng = np.random.default_rng(3670)
    sub = rng.choice(td.size, 300_000, replace=False)
    row = {}
    for nm, v in ch.items():
        v = v.astype(np.float64)
        k = int(round(0.05*v.size))
        i = np.argpartition(v + rng.uniform(0, 1e-12, v.size)*(np.ptp(v)+1e-12), -k)[-k:]
        row[nm] = dict(spearman=float(spearmanr(v[sub], td[sub]).statistic),
                       worst5_lift=float(td[i].mean()/gm))
        print(f"    {nm:22s} rho {row[nm]['spearman']:+.4f}   worst-5% lift {row[nm]['worst5_lift']:.3f}x")
    aa = {}
    for a in (1, 2, 3):
        m = nacc == a
        aa[f"A{a}"] = dict(frac=float(m.mean()), lift=float(td[m].mean()/gm))
        print(f"    |A|={a}: {m.mean():7.4%} of pixels, lift {td[m].mean()/gm:.2f}x")
    # what fraction of C1's worst-5% is |A|=1 ?
    v = ch["C1_gate1sig"].astype(np.float64); k = int(round(0.05*v.size))
    i = np.argpartition(v, -k)[-k:]
    fa1 = float((nacc[i] == 1).mean())
    print(f"    fraction of C1's worst-5% with |A|=1: {fa1:.4%}   (|A|=1 lift {td[nacc==1].mean()/gm:.3f}x)")
    res[tag] = dict(n_dense=int(nd), n_coarse=int(n), iso=iso, g=G, rn_e=rn,
                    true_deficit_mean=gm, true_deficit_exact_zero=float((td == 0).mean()),
                    channels=row, acceptance=aa, c1_worst5_frac_A1=fa1,
                    A1_lift=float(td[nacc == 1].mean()/gm))

json.dump(res, open(os.path.join(OUT, "V06-other-stacks.json"), "w"), indent=1)
print("\nwrote V06-other-stacks.json")
