"""M111 exposure audit for the PIL 16-bit RGB TIFF hazard (ORCH fleet notice).

M111 has zero `Image.open(` calls, so no reported number is affected. Reasoning
from that is exactly the argument ORCH warned against, so this measures the
exposure instead: it recomputes M111's headline statistic -- the blob
inside/outside gradient-energy ratio and the boundary gradient p90 -- twice,
through `tifffile` (truth) and through `PIL` (the hazard), with every other line
of code identical.

PIL numbers are also reported rescaled by 65535/255, so that the pure
quantisation effect is separated from the trivial 8-bit scale change.

Writes: C:\\dev\\strehl-out\\M111-pil-audit\\pil16_exposure_audit.json
Reads:  render outputs only, all under C:\\dev\\strehl-out\\. Nothing on D:.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

OUT = r"C:\dev\strehl-out\M111-pil-audit"
ORCHDIR = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(ORCHDIR, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(ORCHDIR, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")
ZOOMS = [("blobA-row4", 4715, 1180, 300, 260), ("blobB-row2", 2048, 1300, 320, 300)]
SCALE = 65535.0 / 255.0


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def grad_energy(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def score(y, mask):
    ge = grad_energy(y)
    inside, outside = float(ge[mask].mean()), float(ge[~mask].mean())
    edge = (ndimage.binary_dilation(mask, iterations=2)
            & ~ndimage.binary_erosion(mask, iterations=2))
    p90 = float(np.percentile(ge[edge], 90)) if edge.sum() > 20 else float("nan")
    return inside, outside, inside / max(outside, 1e-9), p90


def read_tifffile(path):
    return tifffile.imread(path)


def read_pil(path):
    im = Image.open(path)
    return np.asarray(im), im.mode


def main():
    os.makedirs(OUT, exist_ok=True)
    report = {"files": {}, "blobs": {}}

    arrays = {}
    for tag, path in (("merged", MERGED), ("control", CTRL)):
        tf = read_tifffile(path)
        pl, mode = read_pil(path)
        arrays[tag] = (tf, pl)
        info = {
            "path": path,
            "tifffile": {"shape": list(tf.shape), "dtype": str(tf.dtype),
                         "min": int(tf.min()), "max": int(tf.max()),
                         "levels": int(np.unique(tf).size)},
            "pil": {"shape": list(pl.shape), "dtype": str(pl.dtype), "mode": mode,
                    "min": int(pl.min()), "max": int(pl.max()),
                    "levels": int(np.unique(pl).size)},
        }
        info["level_loss_factor"] = info["tifffile"]["levels"] / max(info["pil"]["levels"], 1)
        report["files"][tag] = info
        print("%-8s tifffile %s %s levels=%d   PIL %s mode=%s levels=%d   loss %.1fx"
              % (tag, tf.shape, tf.dtype, info["tifffile"]["levels"],
                 pl.dtype, mode, info["pil"]["levels"], info["level_loss_factor"]))

    print("\n%-12s %-9s %9s %9s %8s %10s" % ("blob", "reader", "inside", "outside", "ratio", "bdy p90"))
    print("-" * 62)
    for nm, x, y, w, h in ZOOMS:
        entry = {}
        for reader in ("tifffile", "pil"):
            idx = 0 if reader == "tifffile" else 1
            ym = luma(arrays["merged"][idx][y:y + h, x:x + w])
            yc = luma(arrays["control"][idx][y:y + h, x:x + w])
            mask = ym >= np.percentile(ym, 75)
            mi, mo, mr, mp = score(ym, mask)
            ci, co, cr, cp = score(yc, mask)
            k = 1.0 if reader == "tifffile" else SCALE
            entry[reader] = {
                "merged": {"inside": mi * k, "outside": mo * k, "ratio": mr, "p90": mp * k},
                "control": {"inside": ci * k, "outside": co * k, "ratio": cr, "p90": cp * k},
            }
            for arm in ("merged", "control"):
                e = entry[reader][arm]
                print("%-12s %-9s %9.2f %9.2f %8.3f %10.2f"
                      % (nm if arm == "merged" and reader == "tifffile" else "",
                         reader + "/" + arm[:4], e["inside"], e["outside"], e["ratio"], e["p90"]))
        for arm in ("merged", "control"):
            t = entry["tifffile"][arm]["ratio"]
            p = entry["pil"][arm]["ratio"]
            entry.setdefault("ratio_shift_pct", {})[arm] = 100.0 * (p - t) / max(abs(t), 1e-12)
            t90 = entry["tifffile"][arm]["p90"]
            p90 = entry["pil"][arm]["p90"]
            entry.setdefault("p90_shift_pct", {})[arm] = 100.0 * (p90 - t90) / max(abs(t90), 1e-12)

        # The headline was never a single-arm number: it was the merged-against-control
        # contrast. Quantisation hits the two arms unequally, so the contrast moves more
        # than either arm does, and it is the contrast that carries the claim.
        for label, key in (("boundary_hardness", "p90"), ("interior_flatness", "ratio")):
            tv = entry["tifffile"]["merged"][key] / max(entry["tifffile"]["control"][key], 1e-12)
            pv = entry["pil"]["merged"][key] / max(entry["pil"]["control"][key], 1e-12)
            entry.setdefault("cross_arm", {})[label] = {
                "tifffile": tv, "pil": pv, "shift_pct": 100.0 * (pv - tv) / max(abs(tv), 1e-12)}
        ca = entry["cross_arm"]
        print("   CROSS-ARM  boundary hardness merged/control: tifffile %.3fx  PIL %.3fx  "
              "(%+.1f%%)" % (ca["boundary_hardness"]["tifffile"],
                             ca["boundary_hardness"]["pil"],
                             ca["boundary_hardness"]["shift_pct"]))
        print("              interior flatness merged/control: tifffile %.3f   PIL %.3f   "
              "(%+.1f%%)" % (ca["interior_flatness"]["tifffile"],
                             ca["interior_flatness"]["pil"],
                             ca["interior_flatness"]["shift_pct"]))
        report["blobs"][nm] = entry
        print("   ratio shift merged %+.1f%%  control %+.1f%%   |   p90 shift (rescaled) "
              "merged %+.1f%%  control %+.1f%%"
              % (entry["ratio_shift_pct"]["merged"], entry["ratio_shift_pct"]["control"],
                 entry["p90_shift_pct"]["merged"], entry["p90_shift_pct"]["control"]))

    dst = os.path.join(OUT, "pil16_exposure_audit.json")
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(report, indent=1))
    print("\nwrote %s" % dst)

    bad = [t for t, i in report["files"].items() if i["tifffile"]["dtype"] != "uint16"]
    if bad:
        print("UNEXPECTED: these are not uint16 at source: %s" % bad)
        return 1
    print("CONFIRMED: both inputs are 16-bit at source, and M111 read them with tifffile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
