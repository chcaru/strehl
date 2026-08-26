"""Collect every subject's classify.json into one table.

Headline is the drift-tracked arm at one block size with the topographic
prominence, alongside the uncorrected arm and the plant's artefact floor, so
the number is never read without the thing that would invalidate it.
"""
import argparse
import json
import pathlib

import numpy as np


def get(rec, block, arm, det, norm="plain"):
    for g in rec["grids"]:
        if (g["block"] == block and g["arm"] == arm and g["det"] == det
                and g["norm"] == norm):
            return g
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--blocks", default="48,96,192,384")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    outd = pathlib.Path(a.out)
    blocks = [int(v) for v in a.blocks.split(",")]
    recs = []
    for p in sorted((outd / "classify").glob("*.json")):
        recs.append(json.loads(p.read_text(encoding="utf-8")))

    bh = "".join(f"{('b%d' % b):>16}" for b in blocks)
    print("MULTI-PEAK fraction of all in-bounds blocks, topographic "
          "prominence, plain response.")
    print("Each cell is  tracked/uncorrected.  n = frames in the bracket.\n")
    print(f"{'subject':<30}{'n':>5}  {bh}")
    rows = []
    for r in sorted(recs, key=lambda r: (r["subject"].startswith("PLANT"),
                                         r["subject"])):
        cells = ""
        for b in blocks:
            gr = get(r, b, "resp", "topo")
            gf = get(r, b, "fixed", "topo")
            cells += (f"{gr['multi']:7.3f}/{gf['multi']:<8.3f}" if gr and gf
                      else f"{'--':>16}")
        print(f"{r['subject']:<30}{r['nframes']:>5}  {cells}")
        for b in blocks:
            gr, gf = get(r, b, "resp", "topo"), get(r, b, "fixed", "topo")
            gg = get(r, b, "resp", "global")
            if gr:
                rows.append(dict(subject=r["subject"], nframes=r["nframes"],
                                 block=b, tracked=gr["multi"],
                                 uncorrected=gf["multi"] if gf else None,
                                 tracked_globalprom=gg["multi"] if gg else None,
                                 flat=gr["flat"], single=gr["single"],
                                 nblocks=gr["n"], med_sep=gr["med_sep"]))

    real = [r for r in recs if not r["subject"].startswith("PLANT")]
    print(f"\n{len(real)} real subjects.  Median tracked MULTI fraction:")
    for b in blocks:
        v = [get(r, b, "resp", "topo")["multi"] for r in real
             if get(r, b, "resp", "topo")]
        f = [get(r, b, "fixed", "topo")["multi"] for r in real
             if get(r, b, "fixed", "topo")]
        if v:
            print(f"  b={b:<4} tracked median {np.median(v):.3f} "
                  f"[{min(v):.3f}, {max(v):.3f}]   uncorrected median "
                  f"{np.median(f):.3f} [{min(f):.3f}, {max(f):.3f}]")
    if a.csv:
        import csv as _csv
        p = pathlib.Path(a.csv)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
