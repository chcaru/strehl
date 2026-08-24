"""s05: GEOMETRIC edge candidate finder.  Computes no frequency quantity.

For a given frame it locates long, straight, high-contrast edges whose slant
against the pixel axes lies in a usable band, and reports position, angle,
contrast and straightness residual.  ROIs are chosen from this listing on
geometry alone, before any cutoff is computed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402

ROOT = Path("D:/personal/macro")
OUT = Path(__file__).resolve().parents[1] / "out"


def candidates(sub, xs, ys, axis, band=(0.4, 12.0), min_contrast=300.0,
               max_resid=0.60):
    """Slide a window over the green sublattice; in each, try the edge fit.

    Window aspect follows the edge: a 'vertical' edge (running along +y) needs
    many rows to fit the line and only enough columns to hold the transition
    plus the +/-192 um ESF wings (18.75 sublattice columns each side).
    """
    out = []
    H, W = sub.shape
    if axis == "vertical":
        nrow, ncol, sr, sc = 400, 160, 200, 80
    else:
        nrow, ncol, sr, sc = 160, 400, 80, 200
    for r0 in range(0, H - nrow + 1, sr):
        for c0 in range(0, W - ncol + 1, sc):
            s = sub[r0:r0 + nrow, c0:c0 + ncol]
            try:
                line = L.fit_edge_line(s, xs[c0:c0 + ncol], ys[r0:r0 + nrow],
                                       axis=axis)
            except L.EdgeFitError:
                continue
            if not (band[0] <= abs(line["angle_deg"]) <= band[1]):
                continue
            if line["contrast"] < min_contrast:
                continue
            if line["resid_sd_px"] > max_resid:
                continue
            out.append(dict(row0=int(r0), col0=int(c0), nrow=int(nrow),
                            ncol=int(ncol), axis=axis,
                            angle_deg=float(line["angle_deg"]),
                            contrast=float(line["contrast"]),
                            lo_dn=float(line["lo_dn"]),
                            hi_dn=float(line["hi_dn"]),
                            resid_sd_px=float(line["resid_sd_px"])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stack")
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--which", default="G1")
    args = ap.parse_args()

    files = sorted((ROOT / args.stack).glob("*.ARW"))
    path = files[args.frame]
    active = L.load_active(path)
    sub, xs, ys = L.green_sites(active, args.which)
    print(f"{path.name}  sublattice {sub.shape}")

    res = []
    for axis in ("horizontal", "vertical"):
        c = candidates(sub, xs, ys, axis)
        print(f"  {axis}: {len(c)} candidates")
        res += c
    res.sort(key=lambda d: -d["contrast"])
    for d in res[:25]:
        print(f"  {d['axis'][:4]} row0={d['row0']:5d} col0={d['col0']:5d} "
              f"ang={d['angle_deg']:+6.2f} contrast={d['contrast']:7.0f} "
              f"resid={d['resid_sd_px']:.3f}")
    OUT.mkdir(exist_ok=True)
    (OUT / f"s05_edges_{args.stack}.json").write_text(
        json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
