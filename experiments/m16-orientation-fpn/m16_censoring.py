"""Ladder-endpoint censoring per arm and geometry.

Discipline 25: an argmin that lands on the last rung of the sweep is
"no turnover found within the sweep", not an optimum. Any median taken over a
set that contains such cells is censored and must not be read as a shift.

Reads the committed per-arm CSVs and writes data/censoring.csv.
Run:  python m16_censoring.py
"""

import collections
import csv
import pathlib
import re

DATA = pathlib.Path(__file__).resolve().parent / "data"
LADDER_MAX = 40


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def arm_names():
    names = set()
    for p in DATA.glob("*.csv"):
        stem = p.stem
        if "-" not in stem:
            continue
        arm = stem.split("-")[0]
        if re.fullmatch(r"A\d+[a-z0-9]*", arm):
            names.add(arm)
    return sorted(names, key=lambda s: (len(s), s))


def main():
    rows = []
    for arm in arm_names():
        counts = collections.Counter()
        totals = collections.Counter()
        for path in sorted(DATA.glob(f"{arm}-*.csv")):
            best = {}
            for r in load(path):
                key = (r["shape"], int(r["step"]), int(r["seed"]), int(r["width"]))
                window = int(r["window"])
                excess = float(r["excess_dn"])
                if key not in best or excess < best[key][1]:
                    best[key] = (window, excess)
            for (shape, _step, _seed, width), (window, _e) in best.items():
                geom = shape.split("@")[0]
                totals[(geom, width)] += 1
                if window >= LADDER_MAX:
                    counts[(geom, width)] += 1
        for geom, width in sorted(totals):
            n = totals[(geom, width)]
            k = counts[(geom, width)]
            rows.append(
                {
                    "arm": arm,
                    "geometry": geom,
                    "width": width,
                    "cells": n,
                    "endpoint_cells": k,
                    "endpoint_frac": f"{k / n:.4f}",
                }
            )

    out = DATA / "censoring.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["arm", "geometry", "width", "cells", "endpoint_cells", "endpoint_frac"],
        )
        w.writeheader()
        w.writerows(rows)

    hdr = f"{'arm':<8} {'geometry':<11} {'w1 endpoint':>12} {'w17 endpoint':>13}"
    print(hdr)
    print("-" * len(hdr))
    by_arm = collections.defaultdict(dict)
    for r in rows:
        by_arm[(r["arm"], r["geometry"])][int(r["width"])] = (
            int(r["endpoint_cells"]),
            int(r["cells"]),
        )
    for (arm, geom), d in by_arm.items():
        a = d.get(1, (0, 0))
        b = d.get(17, (0, 0))
        print(f"{arm:<8} {geom:<11} {a[0]:>6}/{a[1]:<5} {b[0]:>7}/{b[1]:<5}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
