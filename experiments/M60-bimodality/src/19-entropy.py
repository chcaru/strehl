"""M60 — H4 (posterior entropy), the background-texture audit, and the replicate test.

Three things:

  texture audit   how much texture does each cell's background actually carry?
                  Measured as max_k median(f_k) over the PALE INTERIOR pixels --
                  the peak focus response the background can muster at its own
                  best frame. If the occ_flat cells' backgrounds are genuinely
                  featureless this number collapses, and their firing at the same
                  rate as textured occlusion cells cannot be a veiled background.

  H4 entropy      posterior over frame-of-best-focus, p_k prop exp((f_k-max)/T).
                  Reported at the noise temperature T = median_k sigma_f (the
                  reviewer's matched filter) and over a temperature sweep,
                  because the answer turns out to depend entirely on T.

  replicate       bee-2 and bee-3 are the same scene, independently captured.
                  |k1(bee-3) - k1(bee-2)| is the estimator's own error. Does
                  entropy predict it (AUC)? Does the bimodality flag reproduce?
                  Both need the frame offset between the stacks MEASURED first.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import CELLS  # noqa: E402
import importlib
A = importlib.import_module("12-analyse")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
TEMPS = (0.5, 1.0, 2.0, 5.0, 20.0, 100.0)


def auc(score, positive):
    """Rank AUC of `score` for separating positive from the rest."""
    p, q = score[positive], score[~positive]
    if len(p) < 10 or len(q) < 10:
        return float("nan")
    from scipy.stats import rankdata
    r = rankdata(np.concatenate([p, q]))
    return float((r[:len(p)].sum() - len(p) * (len(p) + 1) / 2.0) / (len(p) * len(q)))


if __name__ == "__main__":
    out = {"texture": [], "entropy": [], "replicate": []}

    print("=" * 78)
    print("TEXTURE AUDIT -- can each class's background be veiled at all?")
    print("=" * 78)
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = A.load(stack, name)
        if d is None:
            continue
        F, lab = d["F"], d["lab"]
        bg, fg, band = lab == 2, lab == 1, lab == 0
        rec = dict(stack=stack, cell=name, cls=cls)
        for key, m in (("bg", bg), ("fg", fg), ("band", band)):
            if m.sum() < 50:
                continue
            prof = np.median(F[:, m], axis=1)
            rec[key + "_peak"] = float(prof.max())
            rec[key + "_floor"] = float(np.median(prof))
            rec[key + "_contrast"] = float(prof.max() / max(np.median(prof), 1e-9))
        out["texture"].append(rec)
        print("  %-16s %-18s %-8s   bg peak f %8.2f (x%5.2f over its own floor)   "
              "fg peak f %8.2f   band peak f %8.2f"
              % (stack, name, cls, rec.get("bg_peak", float("nan")),
                 rec.get("bg_contrast", float("nan")),
                 rec.get("fg_peak", float("nan")), rec.get("band_peak", float("nan"))))
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        v = [r["bg_peak"] for r in out["texture"] if r["cls"] == cls and "bg_peak" in r]
        c = [r["bg_contrast"] for r in out["texture"] if r["cls"] == cls and "bg_contrast" in r]
        print("  %-9s  background peak focus response: median %8.2f   "
              "peak/floor ratio median %5.2f" % (cls, np.median(v), np.median(c)))

    print()
    print("=" * 78)
    print("H4  posterior entropy, over temperature")
    print("=" * 78)
    print("  %-18s %-8s " % ("cell", "class")
          + " ".join("T=%-6.1f" % t for t in TEMPS) + "   bnd-mass@T=20")
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = A.load(stack, name)
        if d is None:
            continue
        F, S, lab = d["F"], d["S"], d["lab"]
        band = lab == 0
        base = np.median(S, axis=0)
        line, bm20 = [], None
        for t in TEMPS:
            H, BM = A.entropy_and_boundary(F[:, band], base[band] * t)
            line.append(float(np.median(H)))
            if t == 20.0:
                bm20 = float(np.median(BM))
        out["entropy"].append(dict(stack=stack, cell=name, cls=cls, H=line, bmass20=bm20))
        print("  %-18s %-8s " % (name, cls) + " ".join("%8.4f" % h for h in line)
              + "   %8.4f" % bm20)
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        rs = [r["H"] for r in out["entropy"] if r["cls"] == cls]
        m = np.median(np.array(rs), axis=0)
        print("  %-9s median H  " % cls + " ".join("%8.4f" % h for h in m))

    print()
    print("=" * 78)
    print("REPLICATE -- bee-2 vs bee-3, same scene, independent capture")
    print("=" * 78)
    reps = [c for c in CELLS if c[0] == "bee-3"]
    offs = []
    for _, name, cls, y0, y1, x0, x1 in reps:
        a, b = A.load("bee-3", name), A.load("bee-2", name)
        if a is None or b is None:
            continue
        ra, rb = A.detect(a["F"], a["S"]), A.detect(b["F"], b["S"])
        band = a["lab"] == 0
        off = float(np.median(rb["k1"][band].astype(float) - ra["k1"][band]))
        offs.append(off)
        print("  %-18s %-8s  median k1 offset bee-2 - bee-3 = %6.1f frames" % (name, cls, off))
    OFF = float(np.median(offs))
    print("  -> global frame offset used: %.1f frames" % OFF)

    for _, name, cls, y0, y1, x0, x1 in reps:
        a, b = A.load("bee-3", name), A.load("bee-2", name)
        na = A.load("bee-3", name, A.NUL)
        if a is None or b is None or na is None:
            continue
        ra, rb = A.detect(a["F"], a["S"]), A.detect(b["F"], b["S"])
        nu = A.detect(na["F"], na["S"])
        band = a["lab"] == 0
        err = np.abs(ra["k1"][band].astype(float) - (rb["k1"][band] - OFF))
        T = np.median(a["S"], axis=0)
        H, BM = A.entropy_and_boundary(a["F"][:, band], T[band])
        H20, _ = A.entropy_and_boundary(a["F"][:, band], T[band] * 20.0)
        zst = float(np.percentile(nu["z"][band], 99))
        fa = ra["z"][band] > zst
        fb = rb["z"][band] > zst
        bad = err > 10
        rec = dict(cell=name, cls=cls, npx=int(band.sum()),
                   err_med=float(np.median(err)), err_p90=float(np.percentile(err, 90)),
                   frac_bad=float(bad.mean()),
                   auc_H=auc(H, bad), auc_H20=auc(H20, bad),
                   auc_prom=auc(-ra["prom"][band], bad),
                   auc_f1=auc(-np.asarray(ra["f1"])[band], bad),
                   flag_a=float(fa.mean()), flag_b=float(fb.mean()),
                   flag_both=float((fa & fb).mean()),
                   flag_expected=float(fa.mean() * fb.mean()))
        out["replicate"].append(rec)
        print("  %-18s %-8s |dk1| med %5.1f p90 %6.1f | frac>10fr %5.1f%% | "
              "AUC entropy %.3f (T=20: %.3f) peak-height %.3f | flag A %4.1f%% B %4.1f%% "
              "both %4.1f%% (chance %4.1f%%)"
              % (name, cls, rec["err_med"], rec["err_p90"], 100 * rec["frac_bad"],
                 rec["auc_H"], rec["auc_H20"], rec["auc_f1"],
                 100 * rec["flag_a"], 100 * rec["flag_b"], 100 * rec["flag_both"],
                 100 * rec["flag_expected"]), flush=True)

    with open(os.path.join(DATA, "19-entropy.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote data/19-entropy.json")
