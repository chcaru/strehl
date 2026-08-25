"""M115 s07 -- the numbers that go in the report, with the right error bars.

Per-block ratios first, THEN the mean and the standard error of that mean.
Never the spread of the blocks: the spread is roughly sqrt(nblocks) wider than
the SE and is not a confidence interval on a mean.  A previous milestone on
this project quoted a raw per-ring range as though it bounded a mean; the SE
was 4x narrower and excluded the hypothesis the range appeared to support.
"""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import banner

STACKS = ["109MSDCF", "119MSDCF"]
h4 = json.load(open(os.path.join(L.OUT, "s04_headroom.json")))
blocks = h4["blocks"]
meta = h4["meta"]
c = np.array(meta[STACKS[0]]["centres"])
mid = np.array(meta[STACKS[0]]["mid"], bool)
fs = c[mid]


def pool(arm, key):
    return np.concatenate([np.array(blocks[s][arm][key]) for s in STACKS])[:, mid]


def stat(v):
    n = v.shape[0]
    return v.mean(0), v.std(0, ddof=1) / np.sqrt(n)


def line(name, v):
    m, se = stat(v)
    i = int(np.argmax(m))
    return dict(f=fs.tolist(), mean=m.tolist(), se=se.tolist(),
                band_mean=float(m.mean()),
                band_se=float(np.sqrt((se ** 2).sum()) / len(se)),
                peak=float(m[i]), peak_se=float(se[i]), peak_f=float(fs[i]))


out = {}
banner("M115 headline numbers  (8 spatial blocks: 4 quadrants x 2 stacks)")

for ref in ["BEST1", "FRAME*"]:
    Ps_r, Pn_r = pool(ref, "Ps"), pool(ref, "Pn")
    print(f"\n  --- referenced to {ref} ---")
    print(f"  {'arm':11s} {'peak G_sig (contrast)':>28s} {'band-mean R_SNR':>24s}")
    for a in ["GATE", "MF", "WIENER", "WIENER_UNG"]:
        gs = np.sqrt(np.maximum(pool(a, "Ps"), 0) / np.maximum(Ps_r, 1e-30))
        gn = np.sqrt(np.maximum(pool(a, "Pn"), 0) / np.maximum(Pn_r, 1e-30))
        rs = gs / np.maximum(gn, 1e-30)
        g, r = line("gs", gs), line("rs", rs)
        out.setdefault(ref, {})[a] = dict(G_sig=g, G_noise=line("gn", gn), R_SNR=r)
        print(f"  {a:11s} {g['peak']:9.3f} +- {g['peak_se']:.3f} at f={g['peak_f']:.3f}"
              f"   {r['band_mean']:10.4f} +- {r['band_se']:.4f}")

banner("the decision-relevant ratio: deconvolution against the SHIPPED gate")
print("  C3 proved SNR is invariant to post-filtering, so this ratio IS the")
print("  matched-contrast comparison: >1 means the Wiener output is cleaner")
print("  than the gate sharpened to the same contrast; 1.00 means it delivered")
print("  nothing that sharpening the shipped merge does not already deliver.\n")
Ps_g, Pn_g = pool("GATE", "Ps"), pool("GATE", "Pn")
rs_g = np.sqrt(np.maximum(Ps_g, 0) / np.maximum(Pn_g, 1e-30))
for a in ["WIENER", "MF", "WIENER_UNG"]:
    rs_a = np.sqrt(np.maximum(pool(a, "Ps"), 0) / np.maximum(pool(a, "Pn"), 1e-30))
    r = rs_a / np.maximum(rs_g, 1e-30)
    d = line("r", r)
    out.setdefault("vs_GATE", {})[a] = d
    m, se = stat(r)
    print(f"  {a:11s} band-mean {d['band_mean']:.4f} +- {d['band_se']:.4f}   "
          f"per-bin range {m.min():.3f}..{m.max():.3f}")
    print(f"              " + "  ".join(f"{f:.2f}:{v:.3f}" for f, v in zip(fs, m)))

banner("what a PERFECT selector already gets over the single sharpest frame")
Ps_b, Pn_b = pool("BEST1", "Ps"), pool("BEST1", "Pn")
gs = np.sqrt(np.maximum(pool("FRAME*", "Ps"), 0) / np.maximum(Ps_b, 1e-30))
rs = gs / np.maximum(np.sqrt(np.maximum(pool("FRAME*", "Pn"), 0) /
                             np.maximum(Pn_b, 1e-30)), 1e-30)
d1, d2 = line("gs", gs), line("rs", rs)
out["FRAMEstar_vs_BEST1"] = dict(G_sig=d1, R_SNR=d2)
print(f"  FRAME* / BEST1 contrast band-mean {d1['band_mean']:.4f} +- {d1['band_se']:.4f}")
print(f"  FRAME* / BEST1 R_SNR    band-mean {d2['band_mean']:.4f} +- {d2['band_se']:.4f}")
print(f"  -> per-tile election buys {100*(d1['band_mean']-1):+.1f}% contrast over")
print(f"     simply taking the sharpest frame, on these detail ROIs.")

banner("the fixed-pattern floor, scaled to the detail ROIs")
s3 = json.load(open(os.path.join(L.OUT, "s03_instrument.json")))
fl, lv = s3["fpn_floor_psig_mid"], s3["fpn_floor_level_dn"]
for st in STACKS:
    lvl = meta[st]["level"]
    scaled = fl * (lvl / lv) ** 2
    sc = np.array(blocks[st]["FRAME*"]["Ps"])[:, mid].mean()
    print(f"  {st}: PRNU floor {scaled:.4g} vs scene P_sig {sc:.4g} "
          f"-> floor is {100*scaled/sc:.4f}% of the signal")
    out.setdefault("fpn", {})[st] = dict(floor=float(scaled), scene=float(sc),
                                         pct=float(100 * scaled / sc))

json.dump(out, open(os.path.join(L.OUT, "s07_summary.json"), "w"), indent=2)
print(f"\n-> s07_summary.json")
