"""Print the per-ROI table from a saved JSON, and render the figures.

Discipline: never interpret a spatial statistic without rendering it as a map.
"""
import json, sys, os
import numpy as np

OUT = r"C:\dev\strehl-out\M107-chroma"


def load(name):
    with open(os.path.join(OUT, "json", name + ".json")) as f:
        return json.load(f)


def table(rows, stack=None):
    rs = [r for r in rows if stack is None or r["stack"] == stack]
    rs.sort(key=lambda r: r["radius"])
    hdr = ("    x0    y0     r  cos  frm       dR       dB     null    wG"
           "    wR    wB   contrast")
    print(hdr)
    for r in rs:
        print("%6d%6d%6.0f%5.2f%5d%9.3f%9.3f%9.3f%6.2f%6.2f%6.2f%11.0f" % (
            r["x0"], r["y0"], r["radius"], r["cos_radial"], r["frame"],
            r["dR"], r["dB"], r["null_dG"], r["wG"], r["wR"], r["wB"],
            r["contrast"]))


if __name__ == "__main__":
    d = load(sys.argv[1] if len(sys.argv) > 1 else "e1_raw_edges")
    stacks = sorted({r["stack"] for r in d["rows"]})
    for s in stacks:
        print("\n===", s, "===")
        table(d["rows"], s)
