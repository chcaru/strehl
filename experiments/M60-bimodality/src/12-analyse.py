"""M60 — the analysis. Reads curves + nulls, produces every number in the report.

Order of operations matters and is fixed by the pre-registration:
  B1  the fact-73 blindness check, run FIRST -- if the operator cannot see the
      thing being measured, nothing downstream means anything
  N1  per-cell noise-only null -> z* at 1% false-positive rate
  power assertions printed BEFORE any hit rate is read (fact 779)
  H1  hit rates by class at matched FPR
  H2  separation |k2-k1| against the measured through-focus peak width
  H4  posterior entropy
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
from cells import CELLS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CUR = os.path.join(DATA, "curves")
NUL = os.path.join(DATA, "null")
FPR = 0.01
CLASSNAMES = ("band", "fg", "bg")


def detect(F, S):
    """Run the frozen detector on an (n, P) curve set. Returns a dict of (P,) arrays."""
    V = F[:, :, None]
    res = L.second_peak(V)
    z, prom, denom, kd = L.prominence_z(V, S[:, :, None], res)
    out = {k: np.asarray(v).ravel() for k, v in res.items()}
    out["z"] = z.ravel()
    out["denom"] = denom.ravel()
    out["kd"] = kd.ravel()
    return out


def peak_width(F, k1):
    """Full width of the primary peak at half its height above the curve minimum."""
    n, P = F.shape
    idx = np.arange(P)
    lo = F.min(axis=0)
    half = lo + 0.5 * (F[k1, idx] - lo)
    w = np.zeros(P, np.int32)
    for sgn in (+1, -1):
        alive = np.ones(P, bool)
        for d in range(1, n):
            k = k1 + sgn * d
            ok = (k >= 0) & (k < n) & alive
            if not ok.any():
                break
            kk = np.clip(k, 0, n - 1)
            above = F[kk, idx] >= half
            w += (ok & above).astype(np.int32)
            alive &= ~(ok & ~above)
    return w + 1


def entropy_and_boundary(F, T, edge_frac=0.05):
    n = F.shape[0]
    a = (F - F.max(axis=0, keepdims=True)) / np.maximum(T, 1e-12)[None, :]
    np.clip(a, -700, 0, out=a)
    w = np.exp(a)
    w /= w.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        h = -(w * np.log(np.where(w > 0, w, 1.0))).sum(axis=0) / np.log(n)
    e = max(1, int(round(n * edge_frac)))
    bm = w[:e].sum(axis=0) + w[n - e:].sum(axis=0)
    return h, bm


def load(stack, name, where=CUR):
    p = os.path.join(where, "%s__%s.npz" % (stack, name))
    return np.load(p) if os.path.exists(p) else None


if __name__ == "__main__":
    rows = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = load(stack, name)
        if d is None:
            continue
        F, S, lab = d["F"], d["S"], d["lab"]
        n, P = F.shape
        nd = load(stack, name, NUL)
        real = detect(F, S)
        w = peak_width(F, real["k1"])
        T = np.median(S, axis=0)
        H, BM = entropy_and_boundary(F, T)
        rec = dict(stack=stack, cell=name, cls=cls, n=int(n), P=int(P))
        if nd is not None:
            nul = detect(nd["F"], nd["S"])
        for j, cn in enumerate(CLASSNAMES):
            m = lab == j
            if m.sum() == 0:
                continue
            zr = real["z"][m]
            pre = "%s_" % cn
            rec[pre + "npx"] = int(m.sum())
            rec[pre + "prom_med"] = float(np.median(real["prom"][m]))
            rec[pre + "denom_med"] = float(np.median(real["denom"][m]))
            rec[pre + "z_med"] = float(np.median(zr))
            rec[pre + "z_p90"] = float(np.percentile(zr, 90))
            rec[pre + "z_p99"] = float(np.percentile(zr, 99))
            rec[pre + "sep_med"] = float(np.median(np.abs(
                real["k2"][m].astype(float) - real["k1"][m])))
            rec[pre + "width_med"] = float(np.median(w[m]))
            rec[pre + "H_med"] = float(np.median(H[m]))
            rec[pre + "bmass_med"] = float(np.median(BM[m]))
            rec[pre + "k1_med"] = float(np.median(real["k1"][m]))
            rec[pre + "f1_med"] = float(np.median(real["f1"][m]))
            if nd is not None:
                zs = nul["z"][m]
                zstar = float(np.percentile(zs, 100 * (1 - FPR)))
                rec[pre + "zstar"] = zstar
                rec[pre + "null_z_med"] = float(np.median(zs))
                rec[pre + "hit"] = float(np.mean(zr > zstar))
                rec[pre + "null_hit"] = float(np.mean(zs > zstar))
                rec[pre + "null_sep_med"] = float(np.median(np.abs(
                    nul["k2"][m].astype(float) - nul["k1"][m])))
        rows.append(rec)
        print("%-16s %-18s %-8s n=%3d  band: prom %8.3f / den %6.3f = z %6.2f | "
              "z*%6.2f hit %5.1f%% sep %5.1f w %5.1f H %.3f"
              % (stack, name, cls, n, rec.get("band_prom_med", 0),
                 rec.get("band_denom_med", 0), rec.get("band_z_med", 0),
                 rec.get("band_zstar", float("nan")),
                 100 * rec.get("band_hit", float("nan")),
                 rec.get("band_sep_med", 0), rec.get("band_width_med", 0),
                 rec.get("band_H_med", 0)), flush=True)
    with open(os.path.join(DATA, "12-percell.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print("\nwrote data/12-percell.json  (%d cells)" % len(rows))
