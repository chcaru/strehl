"""M55b -- register the held-out substrate, and nothing else.

The six stacks named in spec_v1.HELD_OUT must never be scored by the author of
the spec. This file reads EXIF, frame counts, and RawPy header geometry. It does
not unpack a pixel, merge, or evaluate any metric.
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

import rawpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spec_v1 as S

ROOT = r"D:\personal\macro"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        type=Path,
        default=Path(HERE).parent / "out" / "heldout_geometry.json",
        help="registration record (default: out/heldout_geometry.json)",
    )
    return parser.parse_args()


def raw_visible_shape(path):
    """Read `(height, width)` from a raw header without unpacking pixels."""
    with rawpy.imread(str(path)) as raw:
        return int(raw.sizes.height), int(raw.sizes.width)


def main():
    import exifread

    args = parse_args()
    out = {}
    print("=" * 78)
    print("M55b -- held-out substrate registration (EXIF, counts, and geometry)")
    print("=" * 78)
    print(f"   {'stack':14s} {'ARW':>5s} {'raw visible':>16s} {'ROI':>5s} "
          f"{'ISO':>7s} {'exposure':>10s} {'f':>7s}  {'lens':30s}")
    ok = True
    checks_passed = 0
    for stack in S.HELD_OUT:
        files = sorted(glob.glob(os.path.join(ROOT, stack, "*.ARW")))
        if not files:
            print(f"   {stack:14s}  MISSING")
            out[stack] = dict(n=0, enough=False, error="stack missing")
            ok = False
            continue

        tags = {}
        for path in (files[0], files[-1]):
            with open(path, "rb") as fh:
                parsed = exifread.process_file(fh, details=False)
            tags[path] = {
                key: str(value) for key, value in parsed.items()
                if key in ("EXIF ISOSpeedRatings", "EXIF ExposureTime",
                           "EXIF FNumber", "EXIF LensModel", "Image Model")
            }
        first = tags[files[0]]
        enough = len(files) >= S.B6_FRAMES
        if not enough:
            ok = False

        shapes = [raw_visible_shape(path) for path in files]
        unique_shapes = sorted(set(shapes))
        checks = []
        error = None
        if len(unique_shapes) != 1:
            error = (
                f"B6 raw geometry violation: stack={stack} non-uniform "
                f"visible_raw_shapes={unique_shapes}")
        else:
            try:
                checks = S.validate_roi_registry(
                    S.roi_rule(), unique_shapes[0], stack=stack, pad=S.B6_ROI_PAD)
            except ValueError as exc:
                error = str(exc)
        if error is not None:
            ok = False

        checks_passed += len(checks)
        shape_text = str(unique_shapes[0]) if len(unique_shapes) == 1 else "NON-UNIFORM"
        print(
            f"   {stack:14s} {len(files):5d} {shape_text:>16s} "
            f"{len(checks):2d}/4 {first.get('EXIF ISOSpeedRatings', '?'):>7s} "
            f"{first.get('EXIF ExposureTime', '?'):>10s} "
            f"{first.get('EXIF FNumber', '?'):>7s}  "
            f"{first.get('EXIF LensModel', '?')[:30]:30s}"
            f"{'' if enough else '   <-- FEWER THAN 64 FRAMES'}")
        if error is not None:
            print(f"   ERROR: {error}")

        out[stack] = dict(
            n=len(files),
            first=first,
            last=tags[files[-1]],
            enough=bool(enough),
            visible_raw_shapes=[list(shape) for shape in unique_shapes],
            quad_shape=checks[0]["quad_shape"] if checks else None,
            roi_checks=checks,
            error=error,
        )

    expected_checks = len(S.HELD_OUT) * len(S.ROI_FRACTIONS)
    if checks_passed != expected_checks:
        ok = False
    print(f"\n   ROIs, by rule, identical for every stack: {S.roi_rule()}")
    print(f"   ROI bounds checks: {checks_passed}/{expected_checks}")
    print(f"   frames used per stack: first {S.B6_FRAMES}; split: {S.B6_SPLIT}")
    print(f"   -> substrate {'VALID' if ok else 'NOT VALID'}")
    print("   No pixel of any held-out stack was decoded by this file.")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(dict(
            stacks=out,
            rois=[list(roi) for roi in S.roi_rule()],
            roi_bounds_checks_passed=checks_passed,
            valid=ok,
        ), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"   Wrote {args.json}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
