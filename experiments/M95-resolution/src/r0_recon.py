"""Reconnaissance: raw layout, CFA phase, black level, and where the subject is.

Nothing here is a result. It establishes the facts the measurement needs and
prints them so the measurement is not built on an assumption.
"""

import json
import os

import numpy as np
import rawpy

SRC = r"D:\personal\macro\bee-3-cpl"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def main():
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(SRC, "DSC00150.ARW")
    with rawpy.imread(path) as r:
        vis = r.raw_image_visible
        desc = r.color_desc.decode() if isinstance(r.color_desc, bytes) else r.color_desc
        pat = r.raw_pattern
        info = {
            "file": os.path.basename(path),
            "raw_image_visible_shape": list(vis.shape),
            "dtype": str(vis.dtype),
            "color_desc": desc,
            "raw_pattern": pat.tolist(),
            "black_level_per_channel": [int(v) for v in r.black_level_per_channel],
            "white_level": int(r.white_level),
            "sizes_raw": [int(r.sizes.raw_height), int(r.sizes.raw_width)],
            "sizes_visible": [int(r.sizes.height), int(r.sizes.width)],
        }
        # raw_pattern indexes into color_desc. RGGB means [[0,1],[1,2]] over "RGBG"
        # or "RGGB"; resolve it explicitly rather than trusting the name.
        letters = [[desc[pat[y][x]] for x in range(2)] for y in range(2)]
        info["cfa_letters"] = letters
        v = vis.astype(np.float64)
        info["percentiles"] = {str(p): float(np.percentile(v, p)) for p in (0.1, 1, 50, 99, 99.9)}
        print(json.dumps(info, indent=2))

    # Where is the subject? Use the binned green, which is what the shipped
    # render shows, so region choice is made on the same thing the eye sees and
    # is blind to the G1-G2 difference the measurement will look at.
    g1 = v[0::2, 1::2]
    g2 = v[1::2, 0::2]
    s = 0.5 * (g1 + g2)
    h, w = s.shape
    tile = 256
    rows = []
    for ty in range(0, h - tile, tile):
        for tx in range(0, w - tile, tile):
            t = s[ty:ty + tile, tx:tx + tile]
            gy, gx = np.gradient(t)
            rows.append({
                "y": ty, "x": tx,
                "mean": float(t.mean()),
                "grad": float(np.sqrt(gy ** 2 + gx ** 2).mean()),
            })
    rows.sort(key=lambda r: -r["grad"])
    print("\ntop 8 tiles by gradient on binned green (frame 150):")
    for r in rows[:8]:
        print("   y=%5d x=%5d  mean %8.1f  grad %8.2f" % (r["y"], r["x"], r["mean"], r["grad"]))
    print("\nbinned green plane: %d x %d" % (w, h))
    with open(os.path.join(OUT, "recon.json"), "w", encoding="utf-8") as f:
        json.dump({"info": info, "tiles": rows[:40]}, f, indent=1)


if __name__ == "__main__":
    main()
