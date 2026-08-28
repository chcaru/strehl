"""Per-subject chroma-fringe signature: magenta/cyan at luma edges vs flat regions.

THE SIGNATURE BEING SCORED. A channel displacement produces colour that appears
ONLY where luma has a gradient: magenta on one side of an edge and cyan on the
other, and nothing at all in a flat region. A genuine colour, a white-balance
error or a channel gain error does the opposite -- it is present in flat regions
too. So the discriminating statistic is not "how much magenta" but the RATIO of
magenta at edges to magenta in flat areas. A subject whose magenta is spread
evenly over flat and edge pixels does not have this defect, whatever its mean
chroma.

Magenta requires R AND B both above G, and cyan requires both below. A
single-channel excess is a different defect and is deliberately not counted.

COMMISSIONING. --null sets R and B equal to G: there is then no displacement and
no colour at all, so every count must be exactly zero. --plant N rolls R and B
against G by N px in opposite directions, which is a displacement of known
magnitude: the edge counts must rise and the flat counts must stay near zero. If
the flat count rises too, the edge/flat partition is not separating what it
claims to separate and the instrument must not be used.

UNSCORED is a real verdict. A subject with too few edge pixels to measure is
reported UNSCORED and must never be counted as clean.

Usage:
    python chromaedge.py <image.tiff> [--thresh 0.25] [--edgepct 98]
                         [--null] [--plant N] [--label NAME]
"""

import argparse

import numpy as np
import tifffile

MIN_EDGE_PX = 20000       # below this the subject is UNSCORED


def measure(img, thresh, edgepct):
    g = img[:, :, 1].astype(np.float32)
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    # Percentiles from a 1-in-16 regular subsample. On a 33 MP plane that is
    # still 2M samples, which pins a percentile far tighter than the threshold
    # needs, and it avoids sorting the full plane 26 times over.
    sub = mag[::4, ::4]
    hi = np.percentile(sub, edgepct)
    lo = np.percentile(sub, 50.0)
    edge = mag >= hi
    flat = mag <= lo
    eps = np.float32(1.0)
    gg = g + eps
    rg = np.log2((img[:, :, 0].astype(np.float32) + eps) / gg)
    bg = np.log2((img[:, :, 2].astype(np.float32) + eps) / gg)
    mgt = (rg > thresh) & (bg > thresh)
    cyn = (rg < -thresh) & (bg < -thresh)
    out = {
        "edge_px": int(edge.sum()),
        "flat_px": int(flat.sum()),
        "mag_edge": float(mgt[edge].mean()) if edge.sum() else float("nan"),
        "mag_flat": float(mgt[flat].mean()) if flat.sum() else float("nan"),
        "cyn_edge": float(cyn[edge].mean()) if edge.sum() else float("nan"),
        "cyn_flat": float(cyn[flat].mean()) if flat.sum() else float("nan"),
        "mag_all": float(mgt.mean()),
        "cyn_all": float(cyn.mean()),
    }
    # The score: fringe pixels per edge pixel, minus the flat-region background
    # rate, so a subject with a genuine overall colour cast is not penalised.
    out["score"] = (out["mag_edge"] + out["cyn_edge"]) - (out["mag_flat"] + out["cyn_flat"])
    out["unscored"] = out["edge_px"] < MIN_EDGE_PX
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--thresh", type=float, default=0.25)
    ap.add_argument("--edgepct", type=float, default=98.0)
    ap.add_argument("--null", action="store_true")
    ap.add_argument("--plant", type=int, default=0)
    ap.add_argument("--label", default=None)
    args = ap.parse_args()

    img = np.asarray(tifffile.imread(args.image)).astype(np.float32)
    if img.ndim == 2:
        img = np.dstack([img] * 3)
    img = img[:, :, :3]
    label = args.label or args.image

    if args.null:
        img[:, :, 0] = img[:, :, 1]
        img[:, :, 2] = img[:, :, 1]
        label += " [NULL R=B=G]"
    if args.plant:
        n = args.plant
        img[:, :, 0] = np.roll(img[:, :, 1], n, axis=1)
        img[:, :, 2] = np.roll(img[:, :, 1], -n, axis=1)
        label += f" [PLANT +-{n}px]"

    m = measure(img, args.thresh, args.edgepct)
    tag = "UNSCORED" if m["unscored"] else f"{m['score']:.6f}"
    print(f"{label}")
    print(f"  edge px={m['edge_px']:>9}  flat px={m['flat_px']:>9}")
    print(f"  magenta  edge={100*m['mag_edge']:8.4f}%  flat={100*m['mag_flat']:8.4f}%  "
          f"all={100*m['mag_all']:8.4f}%")
    print(f"  cyan     edge={100*m['cyn_edge']:8.4f}%  flat={100*m['cyn_flat']:8.4f}%  "
          f"all={100*m['cyn_all']:8.4f}%")
    print(f"  SCORE (edge fringe rate minus flat background) = {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
