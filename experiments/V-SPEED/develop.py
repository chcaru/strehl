"""RAW -> 16-bit TIFF develop, process-parallel.

This is the conversion stage that arms 2 (enfuse) and 3 (focus-stack) require
and that arm 1 (strehl) does internally. It is deliberately a *standard*
converter -- LibRaw via rawpy -- not strehl's own decoder, because a real
enfuse user does not have strehl.

Two modes, because the choice is a fairness question and V-SPEED measures
whether the answer changes any arm's runtime (docs/research/V-SPEED.md sec 5):

  srgb    (default) rawpy defaults + output_bps=16 + use_camera_wb=True:
          BT.709 gamma (2.222, 4.5), auto-bright ON, sRGB primaries. This is
          what a standard converter gives with no thought, and it is the
          closest analogue of `strehl --srgb --auto-exposure`, which is arm 1's
          shipping command. Feed align_image_stack WITHOUT -l.

  linear  gamma=(1,1), no_auto_bright=True: V-LINEAR2's setup, on which the
          0.977 sharpness result was measured. Feed align_image_stack WITH -l.

Compression is off in both. Compressing trades CPU for I/O and would change
the arm being measured.

Usage: python develop.py <src_dir> <dst_dir> <workers> [srgb|linear]
Prints one JSON line to stdout.
"""

import json
import os
import sys
import time
from multiprocessing import Pool

import rawpy
import tifffile

MODES = {
    "srgb": dict(output_bps=16, use_camera_wb=True),
    "linear": dict(
        output_bps=16,
        use_camera_wb=True,
        gamma=(1, 1),
        no_auto_bright=True,
        output_color=rawpy.ColorSpace.sRGB,
    ),
}


def dev_one(job):
    src, dst, mode = job
    t0 = time.perf_counter()
    with rawpy.imread(src) as raw:
        rgb = raw.postprocess(**MODES[mode])
    tifffile.imwrite(dst, rgb, photometric="rgb", compression=None)
    return (os.path.basename(dst), rgb.shape, time.perf_counter() - t0)


def main():
    src_dir, dst_dir, workers = sys.argv[1], sys.argv[2], int(sys.argv[3])
    mode = sys.argv[4] if len(sys.argv) > 4 else "srgb"
    if mode not in MODES:
        raise SystemExit(f"unknown develop mode {mode!r}")
    os.makedirs(dst_dir, exist_ok=True)
    names = sorted(n for n in os.listdir(src_dir) if n.lower().endswith(".arw"))
    jobs = [
        (os.path.join(src_dir, n), os.path.join(dst_dir, os.path.splitext(n)[0] + ".tif"), mode)
        for n in names
    ]
    t0 = time.perf_counter()
    with Pool(workers) as pool:
        results = pool.map(dev_one, jobs, chunksize=1)
    wall = time.perf_counter() - t0
    shapes = sorted({r[1] for r in results})
    print(
        json.dumps(
            {
                "stage": "develop",
                "mode": mode,
                "src": src_dir,
                "dst": dst_dir,
                "frames": len(jobs),
                "workers": workers,
                "wall_s": wall,
                "s_per_frame": wall / len(jobs),
                "cpu_s_sum": sum(r[2] for r in results),
                "shapes": [list(s) for s in shapes],
            }
        )
    )


if __name__ == "__main__":
    main()
