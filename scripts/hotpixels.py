"""Find the sensor's hot pixels from the dark-frame campaign, and say whether
they are bad enough to matter.

WHY THIS EXISTS
---------------
A hot pixel is a single photosite that reads high regardless of light. On a
single frame it is one bright dot and nobody cares. In a *focus stack* it is
much worse than that: alignment warps each frame by a different sub-pixel
amount, so the same defective photosite lands on a different output pixel in
every frame, and the stack turns one dot into a short bright trail. That is
exactly the kind of defect a reviewer finds in five minutes, and it is
invisible to every aggregate sharpness metric this project has.

The dark frames are short (1/100 s) and lens-capped, so what is left in them is
black level, read noise, and per-pixel dark current. Averaging N frames beats
the read noise down by sqrt(N) and leaves the fixed pattern -- which is the
thing we want to find.

METHOD
------
Per ISO folder, average frames 3..N (the first two are stabilisation shots and
are discarded, as instructed). Then, *within each CFA phase separately* --
because the four Bayer positions have different offsets and gains, and mixing
them would flag every red pixel as hot -- compare each photosite against a
local median of its own phase and flag the ones that stand far above it in
robust (MAD-scaled) units.

A pixel that is hot at one ISO could be noise. A pixel that is hot at many
ISOs is a defect. The persistence count is the real output here.

Usage:
    python scripts/hotpixels.py characterise --out C:\\dev\\strehl-out\\hotpixels
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np

# The first two frames of every dark folder are stabilisation shots: the
# shutter and IBIS are still settling and the frames are not representative.
# Instructed to discard them; doing it in one named constant so it cannot
# silently drift.
STABILISATION_FRAMES = 2

# How far above its local, same-phase background a photosite must sit before we
# call it hot, in robust sigma. 8 is deliberately conservative: at 8 sigma with
# ~8.3M samples per phase, pure Gaussian noise would produce well under one
# false positive per plane, so essentially everything flagged is real.
HOT_SIGMA = 8.0

# Radius of the local background estimate, in same-phase pixels. Must be small
# enough to track real shading and large enough that a cluster of adjacent hot
# pixels cannot drag its own background up and hide itself.
BG_RADIUS = 2


def _phase_planes(a: np.ndarray) -> dict[str, np.ndarray]:
    """Split a Bayer mosaic into its four phases.

    Keyed by (row parity, col parity) rather than by colour name, because the
    CFA pattern differs between bodies and we never need to know which phase is
    red -- only that we are comparing like with like.
    """
    return {
        f"{r}{c}": a[r::2, c::2] for r in (0, 1) for c in (0, 1)
    }


def _average_darks(folder: str, limit: int | None) -> tuple[np.ndarray, int, dict]:
    """Mean of the usable dark frames in one folder, as float32."""
    import rawpy

    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))
    files = files[STABILISATION_FRAMES:]
    if limit:
        files = files[:limit]
    if not files:
        raise SystemExit(f"no usable frames in {folder}")

    acc = None
    for f in files:
        with rawpy.imread(f) as raw:
            # raw_image_visible excludes the masked border, so coordinates line
            # up with what the renderer actually sees.
            v = raw.raw_image_visible
            if acc is None:
                acc = np.zeros(v.shape, dtype=np.float64)
                black = float(np.mean(raw.black_level_per_channel))
                white = float(raw.white_level)
            acc += v
    acc /= len(files)
    return acc.astype(np.float32), len(files), {"black": black, "white": white}


def _find_hot(mean: np.ndarray) -> tuple[np.ndarray, dict]:
    """Boolean mask of hot photosites, in full-mosaic coordinates."""
    from scipy.ndimage import median_filter

    mask = np.zeros(mean.shape, dtype=bool)
    per_phase = {}
    size = 2 * BG_RADIUS + 1
    for key, plane in _phase_planes(mean).items():
        bg = median_filter(plane, size=size, mode="nearest")
        dev = plane - bg
        # Robust scale from the MAD of the deviation. Using the MAD rather than
        # the standard deviation matters: the hot pixels we are hunting would
        # inflate an SD-based threshold enough to hide themselves.
        mad = np.median(np.abs(dev - np.median(dev)))
        sigma = float(1.4826 * mad) or 1e-6
        hot = dev > HOT_SIGMA * sigma
        r, c = int(key[0]), int(key[1])
        mask[r::2, c::2] = hot
        per_phase[key] = {
            "sigma_dn": round(sigma, 4),
            "hot": int(hot.sum()),
            "max_excess_dn": round(float(dev.max()), 2),
        }
    return mask, per_phase


def cmd_characterise(args: argparse.Namespace) -> None:
    os.makedirs(args.out, exist_ok=True)
    folders = sorted(glob.glob(os.path.join(args.root, "*")))
    folders = [f for f in folders if os.path.isdir(f)]
    if not folders:
        raise SystemExit(f"no ISO folders under {args.root}")

    import exifread

    report = []
    union = None
    tally = None
    shape = None

    for folder in folders:
        t0 = time.time()
        first = sorted(glob.glob(os.path.join(folder, "*.ARW")))[STABILISATION_FRAMES]
        with open(first, "rb") as fh:
            tags = exifread.process_file(fh, stop_tag="ISOSpeedRatings", details=False)
        iso = str(tags.get("EXIF ISOSpeedRatings", "?"))

        mean, n, levels = _average_darks(folder, args.limit)
        mask, per_phase = _find_hot(mean)

        if union is None:
            shape = mean.shape
            union = np.zeros(shape, dtype=bool)
            tally = np.zeros(shape, dtype=np.uint16)
        elif mean.shape != shape:
            raise SystemExit(f"{folder}: shape {mean.shape} != {shape}")

        union |= mask
        tally += mask.astype(np.uint16)

        row = {
            "folder": os.path.basename(folder),
            "iso": iso,
            "frames_used": n,
            "hot": int(mask.sum()),
            "hot_ppm": round(1e6 * mask.sum() / mask.size, 2),
            "black_dn": levels["black"],
            "white_dn": levels["white"],
            "phases": per_phase,
            "seconds": round(time.time() - t0, 1),
        }
        report.append(row)
        print(
            f"  ISO {iso:>5}  {n:2d} frames  hot={row['hot']:6d} "
            f"({row['hot_ppm']:8.2f} ppm)  {row['seconds']:5.1f}s",
            flush=True,
        )

    n_iso = len(report)
    persistent = tally >= max(2, (n_iso + 1) // 2)
    always = tally == n_iso

    ys, xs = np.nonzero(persistent)
    coords = np.stack([xs, ys], axis=1).astype(np.int32)

    np.save(os.path.join(args.out, "hot-tally.npy"), tally)
    np.save(os.path.join(args.out, "hot-persistent-xy.npy"), coords)

    summary = {
        "root": args.root,
        "stabilisation_frames_discarded": STABILISATION_FRAMES,
        "hot_sigma": HOT_SIGMA,
        "bg_radius": BG_RADIUS,
        "mosaic_shape": [int(shape[0]), int(shape[1])],
        "isos": n_iso,
        "union_hot": int(union.sum()),
        "persistent_hot": int(persistent.sum()),
        "hot_at_every_iso": int(always.sum()),
        "persistent_ppm": round(1e6 * persistent.sum() / persistent.size, 2),
        "per_iso": report,
    }
    with open(os.path.join(args.out, "hotpixels.json"), "w") as fh:
        json.dump(summary, fh, indent=2)

    print()
    print(f"  union over {n_iso} ISOs : {summary['union_hot']}")
    print(f"  persistent (>= half)  : {summary['persistent_hot']}"
          f"  ({summary['persistent_ppm']} ppm)")
    print(f"  hot at EVERY ISO      : {summary['hot_at_every_iso']}")
    print(f"  wrote {os.path.join(args.out, 'hotpixels.json')}")


def cmd_materiality(args: argparse.Namespace) -> None:
    """Ask whether the hot pixels are bad enough to see, on REAL frames.

    The dark campaign is shot at 1/100 s. The owner's stacks run from 1/40 s to
    2.5 s -- up to 250x longer -- and dark current accumulates with exposure
    time, so a count taken from the darks does not transfer to the library. The
    only honest way to settle it is to measure the defect amplitude in the
    actual frames at the actual exposure.

    Trick: within a focus bracket the scene is static and only focus changes,
    so a per-pixel MINIMUM across frames keeps whatever is constant (the fixed
    pattern, including hot pixels) while real detail, which is sharp in only a
    few frames, drops to its defocused floor. Comparing that minimum against a
    local same-phase median isolates photosites that are always high.

    The random sample is the control. Without it a large excess would be
    unreadable, because scene structure produces excursions too.
    """
    import rawpy
    from scipy.ndimage import median_filter

    coords = np.load(os.path.join(args.map, "hot-persistent-xy.npy"))
    rng = np.random.default_rng(7)
    out = []

    for folder in args.stacks:
        files = sorted(glob.glob(os.path.join(folder, "*.ARW")))[: args.frames]
        if not files:
            print(f"  {folder}: no frames, skipped")
            continue
        mn = None
        for f in files:
            with rawpy.imread(f) as raw:
                v = raw.raw_image_visible
                if mn is None:
                    mn = v.copy()
                    white = float(raw.white_level)
                    black = float(np.mean(raw.black_level_per_channel))
                else:
                    np.minimum(mn, v, out=mn)
        mn = mn.astype(np.float32)

        excess = np.zeros(mn.shape, dtype=np.float32)
        for key, plane in _phase_planes(mn).items():
            bg = median_filter(plane, size=2 * BG_RADIUS + 1, mode="nearest")
            r, c = int(key[0]), int(key[1])
            excess[r::2, c::2] = plane - bg

        hot = excess[coords[:, 1], coords[:, 0]]
        ry = rng.integers(0, excess.shape[0], 200_000)
        rx = rng.integers(0, excess.shape[1], 200_000)
        ctrl = excess[ry, rx]
        span = white - black

        row = {
            "stack": os.path.basename(folder),
            "frames": len(files),
            "range_dn": span,
            "hot_p99_dn": round(float(np.percentile(hot, 99)), 1),
            "hot_max_dn": round(float(hot.max()), 1),
            "control_p99_dn": round(float(np.percentile(ctrl, 99)), 1),
            "hot_over_0.5pct": int((hot > 0.005 * span).sum()),
            "hot_over_1pct": int((hot > 0.01 * span).sum()),
            "hot_over_2pct": int((hot > 0.02 * span).sum()),
        }
        out.append(row)
        print(
            f"  {row['stack']:<24} {row['frames']:3d} frames  "
            f"hot p99={row['hot_p99_dn']:8.1f} max={row['hot_max_dn']:8.1f} DN  "
            f"(control p99={row['control_p99_dn']:7.1f})  "
            f">1% of range: {row['hot_over_1pct']:5d}",
            flush=True,
        )

    os.makedirs(args.map, exist_ok=True)
    with open(os.path.join(args.map, "materiality.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    print(f"  wrote {os.path.join(args.map, 'materiality.json')}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("characterise", help="find hot pixels from the dark frames")
    c.add_argument("--root", default=r"D:\macro-dark-frames")
    c.add_argument("--out", default=r"C:\dev\strehl-out\hotpixels")
    c.add_argument("--limit", type=int, default=None,
                   help="use at most this many frames per ISO")
    c.set_defaults(func=cmd_characterise)

    m = sub.add_parser("materiality",
                       help="are those hot pixels visible in the real stacks?")
    m.add_argument("--map", default=r"C:\dev\strehl-out\hotpixels",
                   help="directory holding hot-persistent-xy.npy")
    m.add_argument("--frames", type=int, default=40,
                   help="frames per stack to take the minimum over")
    m.add_argument("stacks", nargs="+", help="stack folders to test")
    m.set_defaults(func=cmd_materiality)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
