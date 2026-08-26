"""Is the master's pedestal under the claw just the across-frame mean?

The merge's base residual is a plain mean across frames by default
(strehl-core pyramid.rs, BaseBand::Mean). If that is what veils the claw, then
the master's low-frequency level in the claw box should sit near the average of
all frames there, not near the frame that resolved it. Measure both.

Each frame is normalised by its own paper white so the numbers are fractions of
paper luminance and are comparable across frames and with the master.
"""
import argparse
import pathlib

import cv2
import numpy as np
import rawpy
import tifffile

RAWDIR = pathlib.Path(r"D:\personal\macro\bee-3-cpl")
MASTER = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", nargs=4, type=int, required=True)
    ap.add_argument("--step", type=int, default=3)
    ap.add_argument("--paperwin", nargs=4, type=int, required=True,
                    help="a box that is plain paper in EVERY frame, for the white anchor")
    a = ap.parse_args()
    y0, y1, x0, x1 = a.win
    py0, py1, px0, px1 = a.paperwin

    files = sorted(RAWDIR.glob("*.ARW"))
    idxs = list(range(0, len(files), a.step))
    vals = []
    for i in idxs:
        with rawpy.imread(str(files[i])) as r:
            g = r.raw_image_visible[0::2, 1::2].astype(np.float32)
            black = float(np.mean(r.black_level_per_channel))
        g -= black
        paper = float(np.percentile(g[py0 // 2:py1 // 2, px0 // 2:px1 // 2], 99.0))
        c = g[y0 // 2:y1 // 2, x0 // 2:x1 // 2] / max(paper, 1e-6)
        vals.append(float(c.mean()))
    v = np.array(vals)

    M = tifffile.imread(str(MASTER))[:, :, 1].astype(np.float32)
    mpaper = float(np.percentile(M[py0:py1, px0:px1], 99.0))
    mc = M[y0:y1, x0:x1] / max(mpaper, 1e-6)
    base = cv2.GaussianBlur(mc, (0, 0), 32.0)

    print(f"frames sampled: {len(idxs)} (step {a.step})")
    print(f"across-frame MEAN of claw box            = {v.mean():.3f} of paper white")
    print(f"minimum over frames (best-resolved frame)= {v.min():.3f} at frame {idxs[int(v.argmin())]}")
    print(f"MASTER claw box mean                     = {mc.mean():.3f}")
    print(f"MASTER claw box low-frequency base mean  = {base.mean():.3f}")
    print()
    print("if the master's pedestal tracks the across-frame mean rather than the")
    print("frame that resolved the claw, the base band is where the veil enters.")


if __name__ == "__main__":
    main()
