r"""Dust / hot-pixel TRAIL axis: does the shipped master still carry them?

This is a DETECTOR, not a corrector. It answers one question: is there excess
localised structure in the master at the sensor coordinates where the darks say
a defect lives, compared with matched coordinates where they say there is none.

WHY A MATCHED CONTROL AND NOT A THRESHOLD. A master is full of real localised
structure -- that is what a photograph is. No absolute amount of local excess
means anything. What means something is a DIFFERENCE between defect sites and
sites drawn from the same image by the same procedure, because scene content is
independent of where this sensor's bad photosites happen to be.

WHY A SEARCH BOX. A sensor defect is fixed in sensor coordinates and the frames
are warped before merging, so a defect lands at a different output coordinate in
each frame and smears into a short trail. The master's lattice is also 4 px wider
than the raw visible area, so the sensor-to-master mapping carries an unknown
small offset. Both are absorbed by taking the maximum over a +-RAD box -- and the
control takes the maximum over the same box, so the upward bias of a max over a
window is present in both arms and cancels in the comparison.

THE AXIS REPORTS ITS OWN POWER. With a clean sensor there may be nothing to
find, and "no trails detected" from an instrument that could not have detected
them is not a pass. Arm POWER plants defects of decreasing amplitude and reports
the smallest the axis can see; if that is above what the darks say is present,
the subject is REFUSED rather than passed.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rimaxis                                                     # noqa: E402

MAP = os.path.join(HERE, "defectmap.json")
OUT = os.path.join(HERE, "dust.json")
RAD = 12
HALF = 40
NCTRL = 8
DUST_MAX = 1.05


def excess(win):
    """Local excess against a median background -- the shape a hot pixel or a
    mote makes, and one a smooth scene gradient does not."""
    return win - ndimage.median_filter(win, size=5, mode="nearest")


def response(g, y, x):
    y0, x0 = y - HALF, x - HALF
    if y0 < 0 or x0 < 0 or y0 + 2 * HALF > g.shape[0] or x0 + 2 * HALF > g.shape[1]:
        return None
    e = np.abs(excess(g[y0:y0 + 2 * HALF, x0:x0 + 2 * HALF]))
    c = HALF
    return float(e[c - RAD:c + RAD + 1, c - RAD:c + RAD + 1].max())


def arm(g, sites, ctrl):
    d = [v for v in (response(g, y, x) for y, x in sites) if v is not None]
    c = [v for v in (response(g, y, x) for y, x in ctrl) if v is not None]
    if len(d) < 30 or len(c) < 30:
        return None
    return {"n_defect": len(d), "n_control": len(c),
            "defect_med": float(np.median(d)), "control_med": float(np.median(c)),
            "ratio": float(np.median(d) / np.median(c))}


def controls(shape, sites, n_per=NCTRL, seed=13):
    rng = np.random.default_rng(seed)
    h, w = shape
    out = []
    for _ in range(n_per * len(sites) // max(1, len(sites)) * len(sites)):
        if len(out) >= n_per * len(sites):
            break
        out.append((int(rng.integers(HALF, h - HALF)), int(rng.integers(HALF, w - HALF))))
    return out


def load_sites(shape):
    m = json.load(io.open(MAP, encoding="utf-8"))
    ys, xs, amp = m["y"], m["x"], m["amp"]
    sites = [(y, x) for y, x in zip(ys, xs)
             if HALF <= y < shape[0] - HALF and HALF <= x < shape[1] - HALF]
    return sites, m, amp


def plant(g, sites, amp_dn):
    out = g.copy()
    for y, x in sites:
        out[y, x] += amp_dn
    return out


def run_subject(sub, commission=False):
    path = os.path.join(rimaxis.SEAL_DIR, sub + "--SHIP-V4.tiff")
    a = tifffile.imread(path)
    g = rimaxis.lum_of(a)
    del a
    sites, meta, amp = load_sites(g.shape)
    ctrl = controls(g.shape, sites)
    rec = {"n_map_sites": len(meta["y"]), "n_sites_used": len(sites),
           "n_control": len(ctrl), "rad": RAD,
           "map_cut_dn": meta["cut_dn"], "n_darks": meta["n_darks"]}
    base = arm(g, sites, ctrl)
    if base is None:
        rec["refused"] = "too few sites inside the frame"
        return rec
    rec.update(base)
    if commission:
        rec["power"] = []
        for a_dn in (4000.0, 2000.0, 1000.0, 500.0, 250.0, 120.0):
            r = arm(plant(g, sites, a_dn), sites, ctrl)
            rec["power"].append({"amp_dn": a_dn, "ratio": r["ratio"]})
        rec["improved"] = arm(
            ndimage.median_filter(plant(g, sites, 4000.0), size=3), sites, ctrl)["ratio"]
    return rec


def main():
    subs = sorted(f[:-len("--SHIP-V4.tiff")] for f in os.listdir(rimaxis.SEAL_DIR)
                  if f.endswith("--SHIP-V4.tiff"))
    doc = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    only = sys.argv[1:] or subs
    for i, s in enumerate(subs, 1):
        if s in doc or s not in only:
            continue
        rec = run_subject(s)
        doc[s] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        if "refused" in rec:
            print("[%2d/%d] %-38s REFUSED %s" % (i, len(subs), s, rec["refused"]))
        else:
            print("[%2d/%d] %-38s defect %8.1f  control %8.1f  ratio %6.4f"
                  % (i, len(subs), s, rec["defect_med"], rec["control_med"],
                     rec["ratio"]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
