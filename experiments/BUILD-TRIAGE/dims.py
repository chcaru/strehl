"""BUILD-TRIAGE: does the master width variation track anything real?

The delivered masters are not all the same width -- 7032 or 7040 px against a
common height of 4688.  A gallery whose members differ in pixel dimensions is
at best a packaging wart for anyone printing a set, and at worst a sign that
the alignment solve consumed more margin on some subjects than on others.

This tests the second reading.  If width tracks `coverage_k` (the fraction of
the output the alignment gather could fill), or frame count, or the measured
drift, it is a useful diagnostic.  If it does not track any of them it is
arbitrary and belongs in the report as one line.

Shapes come from the TIFF HEADER only -- tifffile reads the IFD without
touching the 188 MB of pixel data, so this is a header scan, not 26 decodes.
"""

from __future__ import annotations

import json
import os

import numpy as np
import tifffile

import tri


def master_shape(subject: str) -> tuple[int, int] | None:
    p = os.path.join(tri.SHIP, f"{subject}.tiff")
    if not os.path.exists(p):
        return None
    with tifffile.TiffFile(p) as tf:
        s = tf.pages[0].shape
    return int(s[0]), int(s[1])


def main() -> None:
    rows = []
    for s in tri.SUBJECTS:
        shp = master_shape(s)
        if shp is None:
            print(f"{s:<38} NO MASTER")
            continue
        cp = os.path.join(tri.OUT, "compare", f"{s}.json")
        n = k = None
        if os.path.exists(cp):
            j = json.load(open(cp))
            n = j.get("n_frames")
            k = j.get("coverage_k_merge")
        rows.append({"subject": s, "h": shp[0], "w": shp[1],
                     "n_frames": n, "coverage_k": k})

    hdr = f"{'subject':<38} {'HxW':>12} {'N':>5} {'coverage_k':>11}"
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda r: (r["w"], r["subject"])):
        k = "n/a" if r["coverage_k"] is None else f"{r['coverage_k']:.4f}"
        n = "n/a" if r["n_frames"] is None else str(r["n_frames"])
        print(f"{r['subject']:<38} {r['h']:>5}x{r['w']:<6} {n:>5} {k:>11}")

    ws = sorted({r["w"] for r in rows})
    print(f"\ndistinct widths: {ws}")
    print(f"heights        : {sorted({r['h'] for r in rows})}")
    for w in ws:
        g = [r for r in rows if r["w"] == w]
        ks = [r["coverage_k"] for r in g if r["coverage_k"] is not None]
        ns = [r["n_frames"] for r in g if r["n_frames"] is not None]
        print(f"  w={w}  n={len(g):>2}  "
              f"coverage_k median={np.median(ks):.4f} "
              f"range={min(ks):.4f}-{max(ks):.4f}  "
              f"frames median={np.median(ns):.0f} range={min(ns)}-{max(ns)}"
              if ks and ns else f"  w={w}  n={len(g)}")

    # Does width separate the coverage_k distributions at all?
    a = [r["coverage_k"] for r in rows
         if r["w"] == ws[0] and r["coverage_k"] is not None]
    b = [r["coverage_k"] for r in rows
         if r["w"] == ws[-1] and r["coverage_k"] is not None]
    if a and b and len(ws) > 1:
        import scipy.stats as st
        u = st.mannwhitneyu(a, b, alternative="two-sided")
        print(f"\ncoverage_k by width: Mann-Whitney U p = {u.pvalue:.4f} "
              f"(n={len(a)} vs {len(b)})")
        print("  -> width TRACKS coverage_k" if u.pvalue < 0.05
              else "  -> width does NOT track coverage_k; the split is arbitrary")

    json.dump(rows, open(os.path.join(tri.OUT, "dims.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(tri.OUT, 'dims.json')}  ({len(rows)} subjects)")


if __name__ == "__main__":
    main()
