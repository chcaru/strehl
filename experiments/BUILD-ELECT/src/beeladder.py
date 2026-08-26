"""Ladder on bee-1-cpl: render single frames and keep crops for offline analysis.

Same instrument as ladder2.py, pointed at the bee. ladder2.py is left untouched
because it is the cited provenance of the flower-bud numbers in the report.

Every frame is rendered with STREHL_ALIGN=0, and the reference election it is
compared against (E-noalign-elect.tif) is also align-off. STREHL_ONLY_FRAME
re-solves alignment against the single frame it is handed, so a ladder rendered
with alignment on does not sit in the same coordinates as the merge it explains.

The bracket end is appended explicitly: one ROI elects f298, the very last frame,
and a ladder that stops at f288 could not tell a peak from a boundary.
"""
import argparse
import json
import os
import pathlib
import subprocess
import time

import numpy as np
import tifffile

BIN = r"C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe"
SUBJECT = r"D:\personal\macro\bee-1-cpl"
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
HALF = 250
NFRAMES = 299


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="0:299:12")
    ap.add_argument("--tag", default="crops")
    args = ap.parse_args()

    rois = {k: (v["cy"], v["cx"])
            for k, v in json.loads((OUT / "bee-rois.json").read_text()).items()}
    print("ROIs:", {k: v for k, v in rois.items()})

    a, b, s = (int(x) for x in args.frames.split(":"))
    frames = sorted(set(list(range(a, b, s)) + [NFRAMES - 1]))

    dst_dir = OUT / f"ladder-{args.tag}"
    dst_dir.mkdir(parents=True, exist_ok=True)
    (dst_dir / "rois.json").write_text(json.dumps(rois, indent=1))
    tmp = OUT / f"_bl_{args.tag}.tif"

    env = dict(os.environ)
    env["STREHL_ALIGN"] = "0"
    for stale in ("STREHL_DUMP_ELECTION", "STREHL_DUMP_NEFF"):
        env.pop(stale, None)

    t0 = time.time()
    for k in frames:
        f = dst_dir / f"f{k:03d}.npz"
        if f.exists():
            print(f"  frame {k:>3}  cached", flush=True)
            continue
        env["STREHL_ONLY_FRAME"] = str(k)
        r = subprocess.run([BIN, "stack", SUBJECT, "--out", str(tmp), "--demosaic"],
                           env=env, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  frame {k:>3}  FAILED rc={r.returncode}: {r.stderr.strip()[-300:]}",
                  flush=True)
            tmp.unlink(missing_ok=True)
            continue
        img = tifffile.imread(str(tmp))
        assert img.dtype == np.uint16, img.dtype
        np.savez_compressed(f, **{
            n: img[cy - HALF:cy + HALF, cx - HALF:cx + HALF]
            for n, (cy, cx) in rois.items()})
        del img
        tmp.unlink(missing_ok=True)
        print(f"  frame {k:>3}  saved  [{time.time() - t0:.0f}s]", flush=True)

    got = sorted(int(p.stem[1:]) for p in dst_dir.glob("f*.npz"))
    print(f"done: {len(got)}/{len(frames)} frames in {dst_dir}")
    missing = [k for k in frames if k not in got]
    if missing:
        print(f"MISSING (re-run to fill): {missing}")


if __name__ == "__main__":
    main()
