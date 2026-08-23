"""M60 — the decisive discriminator: does the second peak's offset depend on
distance from the silhouette?

Two mechanisms produce a second through-focus peak near an edge.

  genuine second depth  the background's focus peak sits at ONE frame, the frame
                        where the background is sharp. Its offset from the
                        foreground peak is the depth step. It does NOT depend on
                        how far the pixel is from the silhouette.

  defocus side-lobe     a single depth. The blurred edge's skirt sweeps outward
                        as defocus grows, so a pixel x px from the edge sees its
                        gradient peak when sigma ~ x, i.e. at |k - k_focus| =
                        x / rate. The offset GROWS LINEARLY with x.
                        (measured in 15-sidelobe: ratio 1.87 when rate is halved)

So regress the measured offset |k2 - k1| on distance-to-silhouette, per cell.
Slope ~ 0 with a tight intercept => second depth. Slope > 0 => side-lobe.
The same regression is run on occlusion cells and on control cells that have no
depth discontinuity at all; if both give the same slope, the statistic is
measuring edge defocus, not occlusion.

Nothing here needs the defocus rate to be calibrated: the comparison is between
classes, using the same operator and the same distance definition.
"""

import os
import sys
import json
import numpy as np
from scipy.ndimage import distance_transform_edt, binary_erosion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
from cells import CELLS  # noqa: E402
import importlib
A = importlib.import_module("12-analyse")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
BINS = [(1, 3), (3, 6), (6, 10), (10, 16), (16, 26), (26, 40), (40, 64)]


def distance_map(Ibar):
    """Distance in px from the silhouette, where the silhouette is the boundary of
    the dark region of the through-focus mean image. Intensity only."""
    dark = Ibar < np.median(Ibar)
    inner = binary_erosion(dark, np.ones((3, 3), bool), border_value=1)
    edge = dark & ~inner
    if not edge.any():
        return None
    return distance_transform_edt(~edge)


def theil_sen(x, y):
    """Robust slope, no distributional assumption, no fitted denominator."""
    n = len(x)
    if n < 3:
        return float("nan"), float("nan")
    idx = np.arange(n)
    i, j = np.triu_indices(n, 1)
    dx = x[j] - x[i]
    ok = dx != 0
    s = (y[j] - y[i])[ok] / dx[ok]
    return float(np.median(s)), float(np.percentile(s, 84) - np.percentile(s, 16))


if __name__ == "__main__":
    out = []
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        d = A.load(stack, name)
        if d is None:
            continue
        nd = A.load(stack, name, A.NUL)
        F, S, lab, sel = d["F"], d["S"], d["lab"], d["sel"]
        Ibar = d["Ibar"]
        dm = distance_map(Ibar)
        if dm is None:
            continue
        dist = dm.ravel()[sel]
        real = A.detect(F, S)
        sep = np.abs(real["k2"].astype(float) - real["k1"])
        zstar = None
        if nd is not None:
            nul = A.detect(nd["F"], nd["S"])
        band = lab == 0
        # reference: where is the pale interior in focus, and the dark interior?
        kbg = float(np.median(real["k1"][lab == 2])) if (lab == 2).any() else float("nan")
        kfg = float(np.median(real["k1"][lab == 1])) if (lab == 1).any() else float("nan")
        rec = dict(stack=stack, cell=name, cls=cls, n=int(F.shape[0]),
                   k_fg_ref=kfg, k_bg_ref=kbg, bins=[])
        xs, ys, hs = [], [], []
        for lo, hi in BINS:
            m = band & (dist >= lo) & (dist < hi)
            if m.sum() < 200:
                continue
            if nd is not None:
                zst = float(np.percentile(nul["z"][m], 99))
                hit = float(np.mean(real["z"][m] > zst))
            else:
                zst, hit = float("nan"), float("nan")
            fired = m & (real["z"] > (zst if zst == zst else np.inf))
            b = dict(lo=lo, hi=hi, npx=int(m.sum()), zstar=zst, hit=hit,
                     sep_med=float(np.median(sep[m])),
                     sep_med_fired=float(np.median(sep[fired])) if fired.sum() > 20 else float("nan"),
                     k2_med=float(np.median(real["k2"][m].astype(float))),
                     k1_med=float(np.median(real["k1"][m].astype(float))),
                     z_med=float(np.median(real["z"][m])),
                     prom_med=float(np.median(real["prom"][m])),
                     den_med=float(np.median(real["denom"][m])))
            rec["bins"].append(b)
            xs.append(0.5 * (lo + hi)); ys.append(b["sep_med"]); hs.append(b["hit"])
        if len(xs) >= 3:
            sl, sp = theil_sen(np.array(xs, float), np.array(ys, float))
            rec["slope_frames_per_px"] = sl
            rec["slope_spread"] = sp
            rec["sep_range"] = float(max(ys) - min(ys))
            rec["hit_first"] = hs[0]
            rec["hit_last"] = hs[-1]
        out.append(rec)
        print("%-16s %-18s %-8s  k_fg=%6.1f k_bg=%6.1f  slope=%7.3f fr/px  "
              "sep %s" % (stack, name, cls, kfg, kbg,
                          rec.get("slope_frames_per_px", float("nan")),
                          " ".join("%5.1f" % b["sep_med"] for b in rec["bins"])),
              flush=True)
    with open(os.path.join(DATA, "16-distance.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote data/16-distance.json (%d cells)" % len(out))
