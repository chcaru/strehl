"""Run the warp fit over every pair section 12 reports, and write it as an artifact.

The verifier must re-derive the table from measurements, not from numbers typed
into itself. So the measurement writes JSON and the verifier reads both that and
the document, and compares them. A checker that carries its own copy of the
answer verifies nothing: another lane passed 37/37 that way and then caught only
5 of 13 planted defects.
"""
import json
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402
import diag_warp  # noqa: E402
import nscene  # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\ladder2\out"
PAIRS = [("n18a", "n18b"), ("n37a", "n37b"), ("n74a", "n74b"),
         ("n149a", "n149b"), ("n18a", "n149a"), ("n37a", "n74a")]
SITE, PAD, MARGIN = diag_warp.SITE, diag_warp.PAD, diag_warp.MARGIN


def green(name, expo):
    return bandlib.display(tifffile.imread(os.path.join(OUT, name + ".tiff"))[..., 1]
                           .astype(np.float64), expo)


def main():
    r16 = tifffile.imread(os.path.join(OUT, "n149a.tiff"))
    expo = 0.90 / max(float(np.percentile(r16.astype(np.float64) / 65535.0, 99.9)), 1e-9)
    del r16
    out = {"expo": expo, "site": SITE, "pad": PAD, "grid": [diag_warp.GRID_Y,
                                                            diag_warp.GRID_X], "pairs": {}}
    cache = {}
    for a, b in PAIRS:
        for nm in (a, b):
            if nm not in cache:
                cache[nm] = green(nm, expo)
        ga, gb = cache[a], cache[b]
        h, w = ga.shape
        ys = np.linspace(MARGIN, h - MARGIN - SITE, diag_warp.GRID_Y).astype(int)
        xs = np.linspace(MARGIN, w - MARGIN - SITE, diag_warp.GRID_X).astype(int)
        pts, offs, sat = [], [], 0
        for y in ys:
            for x in xs:
                o, e, edge = nscene.integer_align(
                    ga[y:y + SITE, x:x + SITE],
                    gb[y - PAD:y + SITE + PAD, x - PAD:x + SITE + PAD], PAD)
                if edge:
                    sat += 1
                    continue
                pts.append((y + SITE / 2, x + SITE / 2))
                offs.append(o)
        k, t, r, M, t_aff, r_aff = diag_warp.fit(pts, offs)
        o = np.array(offs, dtype=np.float64)
        rms_raw = float(np.sqrt(np.mean((o - o.mean(axis=0)) ** 2)))
        rms_iso = float(np.sqrt(np.mean(r ** 2)))
        rms_aff = float(np.sqrt(np.mean(r_aff ** 2)))
        key = "%s|%s" % (a, b)
        out["pairs"][key] = {
            "sites": len(offs), "saturated": sat, "rms_raw": rms_raw,
            "iso_scale": k, "rms_iso": rms_iso, "rms_aff": rms_aff,
            "absorb_iso": 1 - rms_iso / rms_raw, "absorb_aff": 1 - rms_aff / rms_raw,
        }
        print("  %-14s rms %6.2f px  iso %+.5f  absorb iso %2.0f%% aff %2.0f%%  "
              "(%d sites, %d saturated)"
              % (key, rms_raw, k, 100 * (1 - rms_iso / rms_raw),
                 100 * (1 - rms_aff / rms_raw), len(offs), sat))
    p = os.path.join(OUT, "warp.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote %s" % p)


if __name__ == "__main__":
    main()
