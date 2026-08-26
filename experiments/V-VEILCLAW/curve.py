"""Read a probe CSV and classify the through-focus curve properly.

The original verdict() takes argmax and asks whether it is interior. That cannot
distinguish one layer from two, even though the two-layer case is the one the
probe's own docstring says matters most. This adds prominence-based peak
detection so a second layer is reported instead of silently losing to the first.
"""
import argparse
import pathlib

import numpy as np


def smooth(v, k=5):
    ker = np.ones(k) / k
    return np.convolve(np.pad(v, k // 2, mode="edge"), ker, mode="valid")[:len(v)]


def peaks(v, floor, min_prom=0.10, min_sep=15):
    out = []
    for i in range(1, len(v) - 1):
        if v[i] >= v[i - 1] and v[i] > v[i + 1]:
            l = v[:i].min() if i else v[i]
            r = v[i + 1:].min()
            prom = (v[i] - max(l, r)) / max(floor, 1e-9)
            out.append((i, v[i], prom))
    out.sort(key=lambda t: -t[2])
    kept = []
    for i, val, prom in out:
        if prom < min_prom:
            continue
        if any(abs(i - j) < min_sep for j, _, _ in kept):
            continue
        kept.append((i, val, prom))
    return sorted(kept)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--col", default="probe")
    ap.add_argument("--plot")
    a = ap.parse_args()
    lines = pathlib.Path(a.csv).read_text(encoding="utf-8").strip().splitlines()
    hdr = lines[0].split(",")
    rows = [l.split(",") for l in lines[1:]]
    idx = np.array([int(r[0]) for r in rows])

    for col in ("probe", "control", "null"):
        j = hdr.index(col)
        v = np.array([float(r[j]) for r in rows])
        s = smooth(v, 7)
        floor = float(np.percentile(s, 10))
        pk = peaks(s, floor)
        tag = {"probe": "PROBE  ", "control": "CONTROL", "null": "NULL   "}[col]
        if not pk:
            print(f"{tag}: FLAT (no peak with prominence >= 0.10 of floor) -> never resolved")
        else:
            desc = "  ".join(
                f"frame#{idx[i]} val={val:.1f} prom={prom:.2f}" for i, val, prom in pk)
            kind = {1: "SINGLE-PEAK", 2: "TWO-PEAK"}.get(len(pk), f"{len(pk)}-PEAK")
            print(f"{tag}: {kind}  floor={floor:.1f}  {desc}")

    if a.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(11, 4.2), dpi=130)
        for col, c in (("probe", "#d02020"), ("control", "#2060c0"), ("null", "#909090")):
            j = hdr.index(col)
            v = np.array([float(r[j]) for r in rows])
            ax.plot(idx, v, color=c, lw=0.7, alpha=0.35)
            ax.plot(idx, smooth(v, 7), color=c, lw=1.7, label=col)
        ax.set_xlabel("frame index (0..298, focus moving front to back)")
        ax.set_ylabel("mean |laplacian| of CFA green lattice")
        ax.set_title(pathlib.Path(a.csv).stem)
        ax.legend()
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(a.plot)
        print(f"wrote {a.plot}")


if __name__ == "__main__":
    main()
