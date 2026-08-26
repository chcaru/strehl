"""Render the ladder ONCE and keep crops, so any focus measure can be tried offline.

The first ladder threw the frames away and kept only two scalars, and both scalars
disagreed with what the contact sheet plainly showed. Keeping the pixels is cheap
(26 frames x 500x500 RGB = 39 MB) and lets the operator be chosen after looking.
"""
import argparse
import os
import pathlib
import subprocess
import time

import numpy as np
import tifffile

BIN = r"C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
SUBJECT = r"D:\personal\macro\flower-bud-alone-cpl"
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")

# name: (cy, cx) on the 4688x7040 grid. HALF is the crop half-width.
ROIS = {
    "pale-wash":     (2012, 2400),   # the defect: flat creamy wash, elected ~134
    "leaf-infocus":  (2050, 2700),   # across the seam, sharp; elected ~37
    "dark-patch":    (3148, 4002),   # the lower-lobe "polygon"; elected ~22
    "subject-sharp": (3400, 4300),   # visibly detailed subject; elected ~37
}
HALF = 250


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="0:205:8")
    ap.add_argument("--tag", default="crops")
    args = ap.parse_args()

    a, b, s = (int(x) for x in args.frames.split(":"))
    frames = list(range(a, b, s))

    dst_dir = OUT / f"ladder-{args.tag}"
    dst_dir.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f"_l2_{args.tag}.tif"

    env = dict(os.environ)
    env["STREHL_ALIGN"] = "0"
    for stale in ("STREHL_DUMP_ELECTION", "STREHL_DUMP_NEFF"):
        env.pop(stale, None)

    t0 = time.time()
    for k in frames:
        f = dst_dir / f"f{k:03d}.npz"
        if f.exists():
            print(f"  frame {k:>3}  cached")
            continue
        env["STREHL_ONLY_FRAME"] = str(k)
        r = subprocess.run([BIN, "stack", SUBJECT, "--out", str(tmp), "--demosaic"],
                           env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"frame {k} rc={r.returncode}\n{r.stderr[-2000:]}")
        img = tifffile.imread(str(tmp))
        assert img.dtype == np.uint16, img.dtype
        np.savez_compressed(f, **{
            n: img[cy - HALF:cy + HALF, cx - HALF:cx + HALF] for n, (cy, cx) in ROIS.items()})
        del img
        tmp.unlink(missing_ok=True)
        print(f"  frame {k:>3}  saved  [{time.time() - t0:.0f}s]")
    print(f"done, {len(frames)} frames in {dst_dir}")


if __name__ == "__main__":
    main()
