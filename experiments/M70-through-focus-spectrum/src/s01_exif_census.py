"""M70 s01 - EXIF census of the twelve corpus stacks.

Reads the TSVs dumped by exiftool (see README). No RAW decode.

Purpose: establish per stack the marked aperture, ISO and frame count. The
diffraction cutoff `f_sig` is a function of the *marked* aperture (fact 27:
f/11 -> 0.2762 cyc/px; M5 also measured f/5.6 -> 0.2431 and f/8 -> 0.2817), so
a single cutoff must NOT be carried across stacks.
"""

from __future__ import annotations

import collections
import glob
import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")


def main() -> None:
    rows_out = []
    for f in sorted(glob.glob(os.path.join(OUT, "exif-*.tsv"))):
        stack = os.path.basename(f)[5:-4]
        rows = [l.rstrip("\n").split("\t") for l in open(f, encoding="utf-8") if l.strip()]
        iso = collections.Counter(r[1] for r in rows)
        fnum = collections.Counter(r[2] for r in rows)
        expt = collections.Counter(r[3] for r in rows)
        flen = collections.Counter(r[4] for r in rows)
        lens = collections.Counter(r[5] for r in rows)
        rec = {
            "stack": stack,
            "n": len(rows),
            "iso": dict(iso),
            "fnumber": dict(fnum),
            "focal_length": dict(flen),
            "lens_type3": dict(lens),
            "exposure_top4": dict(expt.most_common(4)),
        }
        rows_out.append(rec)
        print(
            "{:16s} n={:4d} ISO={} F={} FL={} lens={}".format(
                stack, len(rows), dict(iso), dict(fnum), dict(flen), dict(lens)
            )
        )
        print("{:16s} exp(top4)={}".format("", dict(expt.most_common(4))))
    with open(os.path.join(OUT, "exif-census.json"), "w", encoding="utf-8") as fh:
        json.dump(rows_out, fh, indent=1)


if __name__ == "__main__":
    main()
