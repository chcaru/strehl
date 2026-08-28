"""Does the rogue frame reach the IMAGE, or is it only a weight-space fact?

Merge bee-2-cpl with and without frame 46, everything else identical, and
report the difference in image space. A weight share is a property of the
estimator; a DN difference in delivered pixels is a property of the picture.
ORCH requires at least one statistic that coherence alone cannot move, and a
per-pixel DN difference between two renders is that statistic.

Reconstruction is the shipping rule from pyramid.rs: weighted mean of each
band where anything was admitted, unweighted mean where nothing was, base
band always the unweighted mean, then collapse.
"""
import sys, json, io, os; sys.path.insert(0, ".")
import numpy as np, vn_subgate as SG, vn_pyr as VP, vn_gbundle as GB

frames, kept, meta = GB.load("bee-2-cpl", rule="registered")
n = len(frames)
j46 = [j for j in range(n) if int(kept[j]) == 46][0]
var0 = VP.fit_variance(frames[0])[0]
varp = VP.gauss_pyr(var0, SG.NB)
NB = SG.NB


def build(skip):
    wl = [None] * NB; sw = [None] * NB; sl = [None] * NB; base = None; m = 0
    for j, f in enumerate(frames):
        if j == skip:
            continue
        m += 1
        lap, b = VP.lap_pyr(f, NB)
        base = b if base is None else base + b
        for k in range(NB):
            floor = np.maximum(SG.GATE * SG.BETA[k]
                               * np.maximum(varp[k], 0.0), 1.0)
            ex = VP.smooth5(lap[k] ** 2) - floor
            r = np.where(ex > 0.0, ex / floor / VP.SNR_REF, 0.0)
            w = np.where(ex > 0.0, r ** SG.EXPO[k], 0.0)
            wl[k] = w * lap[k] if wl[k] is None else wl[k] + w * lap[k]
            sw[k] = w.copy() if sw[k] is None else sw[k] + w
            sl[k] = lap[k].copy() if sl[k] is None else sl[k] + lap[k]
    out = base / m
    for k in range(NB - 1, -1, -1):
        g = np.where(sw[k] > 0.0, wl[k] / np.where(sw[k] > 0.0, sw[k], 1.0),
                     sl[k] / m)
        out = VP.expand(out, g.shape) + g
    return out, [np.sqrt((np.where(sw[k] > 0.0,
                                   wl[k] / np.where(sw[k] > 0.0, sw[k], 1.0),
                                   sl[k] / m) ** 2).mean())
                 for k in range(NB)]


a, ba = build(None)
b, bb = build(j46)
d = a - b
res = dict(n_with=n, n_without=n - 1, dropped_source_index=46,
           rms_diff_dn=float(np.sqrt((d ** 2).mean())),
           max_abs_diff_dn=float(np.abs(d).max()),
           p99_abs_diff_dn=float(np.percentile(np.abs(d), 99)),
           median_abs_diff_dn=float(np.median(np.abs(d))),
           mean_dn_with=float(a.mean()), mean_dn_without=float(b.mean()),
           frac_px_over_10dn=float((np.abs(d) > 10.0).mean()),
           frac_px_over_100dn=float((np.abs(d) > 100.0).mean()),
           band_rms=[dict(band=k, with_46=float(ba[k]), without=float(bb[k]),
                          ratio=float(ba[k] / bb[k]) if bb[k] else None)
                     for k in range(NB)])
p = os.path.join(SG.OUT, "rogue46.json")
json.dump(res, io.open(p, "w", encoding="utf-8"), default=float, indent=1)
for k, v in res.items():
    if k != "band_rms":
        print("%-22s %s" % (k, v))
print(" band   merged band RMS with 46   without 46    ratio")
for x in res["band_rms"]:
    print("  L%d %22.4f %13.4f %9.4f"
          % (x["band"], x["with_46"], x["without"], x["ratio"]))
print("wrote", p)
