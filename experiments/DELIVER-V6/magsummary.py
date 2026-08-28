"""DELIVER-V6: one honest line per subject, old master vs new master.

WHAT THIS IS FOR
----------------
The eye is the verdict on this job -- the owner has rejected two rounds on
visual grounds and metrics twice failed to predict him. But "I looked at 26
subjects and it seemed better" is not something anyone can check, and it is not
something I can check myself a week later. So each visual claim gets one number
standing next to it, computed the same way for every subject.

This is NOT the acceptance metric. `experiments/V-REVIEW/PREREG-v6ca.md`
pre-registered the scoring of this render before it existed, and that lane owns
the verdict: signed radial displacement per channel, magenta and cyan lobes kept
apart, an `agree` fraction. Deliberately not reimplemented here -- a second,
differently-shaped metric computed by the lane that produced the render is how a
comparison gets talked into the answer its author wanted.

WHAT IT MEASURES
----------------
The magenta axis `m = ((R-G) + (B-G)) / 2`: positive is magenta, negative is
green. Lateral CA puts colour on EDGES, so the statistic is taken only on edge
pixels -- the top 2 % of luma gradient -- and the edge set is chosen on the OLD
master and reused for the new one, so both arms are scored on the same pixels
and a change in edge structure cannot move the sample.

Two summaries, because they answer different questions and can disagree:

  mean |m|   how much colour error sits on edges, regardless of hue. This is
             the fringing the eye objects to. Down is better.
  mean  m    the signed bias. A global tint shows here and NOT in mean |m|.

They can move in opposite directions and on this corpus they do: the magnitude
falls while the signed mean rises. Reporting only one of them would have made
the result look cleaner than it is.

RADIUS
------
Lateral CA scales with distance from the optical axis, so it is near-zero in the
centre by construction. `r > 0.5` (normalised half-diagonal) keeps the statistic
in the region where the correction is actually doing something; the all-radii
row is printed too so the dilution is visible rather than hidden.

Usage:
    python magsummary.py <old-dir> <new-dir> [--json <path>] [--subject S]...
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile

EDGE_PCTL = 98.0
RADIUS_MIN = 0.5


def magenta(a: np.ndarray) -> np.ndarray:
    return ((a[:, :, 0] - a[:, :, 1]) + (a[:, :, 2] - a[:, :, 1])) * 0.5


def edge_and_radius(luma: np.ndarray):
    gy, gx = np.gradient(luma)
    g = np.hypot(gy, gx)
    h, w = luma.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((yy - h / 2) / (h / 2), (xx - w / 2) / (w / 2)) / np.sqrt(2.0)
    return g >= np.percentile(g, EDGE_PCTL), r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old_dir")
    ap.add_argument("new_dir")
    ap.add_argument("--json", default=None)
    ap.add_argument("--subject", action="append", default=None)
    args = ap.parse_args()

    old_dir, new_dir = Path(args.old_dir), Path(args.new_dir)
    names = sorted(p.stem for p in old_dir.glob("*.tiff"))
    if args.subject:
        names = [n for n in names if n in set(args.subject)]

    hdr = (f"{'subject':<38}{'px moved':>12}{'max':>7}{'mnR':>7}{'mnG':>7}{'mnB':>7}"
           f"{'|m|old':>9}{'|m|new':>9}{'d%':>7}{'m old':>9}{'m new':>9}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for n in names:
        pn = new_dir / f"{n}.tiff"
        if not pn.exists():
            print(f"{n:<38}  (no new master)")
            continue
        O = tifffile.imread(str(old_dir / f"{n}.tiff"))[:, :, :3]
        N = tifffile.imread(str(pn))[:, :, :3]
        if O.shape != N.shape:
            print(f"{n:<38}  GEOMETRY {O.shape} -> {N.shape}")
            continue
        identical = np.array_equal(O, N)
        Of, Nf = O.astype(np.float32), N.astype(np.float32)
        d = np.abs(Of - Nf)
        luma = 0.2126 * Of[:, :, 0] + 0.7152 * Of[:, :, 1] + 0.0722 * Of[:, :, 2]
        edge, r = edge_and_radius(luma)
        m = edge & (r > RADIUS_MIN)
        mo, mn = magenta(Of)[m], magenta(Nf)[m]
        ao, an = float(np.abs(mo).mean()), float(np.abs(mn).mean())
        pct = 100.0 * (an - ao) / ao if ao > 0 else 0.0
        rows.append(dict(subject=n, identical=bool(identical),
                         px_moved=int((d.max(axis=2) > 0).sum()),
                         max_dn=float(d.max()),
                         mean_r=float(d[:, :, 0].mean()), mean_g=float(d[:, :, 1].mean()),
                         mean_b=float(d[:, :, 2].mean()), n_edge=int(m.sum()),
                         absmag_old=ao, absmag_new=an, absmag_pct=pct,
                         mag_old=float(mo.mean()), mag_new=float(mn.mean())))
        tag = "  IDENTICAL" if identical else ""
        print(f"{n:<38}{rows[-1]['px_moved']:>12,}{d.max():>7.0f}"
              f"{d[:, :, 0].mean():>7.1f}{d[:, :, 1].mean():>7.1f}{d[:, :, 2].mean():>7.1f}"
              f"{ao:>9.1f}{an:>9.1f}{pct:>+7.1f}{mo.mean():>+9.1f}{mn.mean():>+9.1f}{tag}")

    if rows:
        scored = [r for r in rows if not r["identical"]]
        print("-" * len(hdr))
        print(f"{len(rows)} subjects; {len(scored)} changed, {len(rows) - len(scored)} bit-identical")
        if scored:
            imp = [r for r in scored if r["absmag_pct"] < 0]
            print(f"edge |m| fell on {len(imp)}/{len(scored)} changed subjects; "
                  f"median change {np.median([r['absmag_pct'] for r in scored]):+.1f}%")
    if args.json:
        Path(args.json).write_text(json.dumps(
            dict(edge_pctl=EDGE_PCTL, radius_min=RADIUS_MIN, rows=rows), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
