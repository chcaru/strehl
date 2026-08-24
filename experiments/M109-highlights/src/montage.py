"""B6: the owner judges images, not numbers.

A 100 % (1:1) crop montage of the affected region, before and after, with
LibRaw's independent render of the same region beside them.

The crop is placed by the PREDICATE, not by hand (discipline 713): it is centred
on the centroid of the largest connected run of pixels that the magenta
predicate fired on in the BEFORE render. Nobody types in an ROI, so nobody can
be accused of aiming at a flattering one -- fact 1434 is what happens when they
do.

Both strehl panels come from the SAME binary, SAME algorithm, SAME frames and
the SAME exposure (-0.24 stops). The only difference between them is whether
`color::saturation_ceiling` returns a ceiling or +inf. That is discipline 708's
exposure-matched control: the change cannot be mistaken for a brightness change.
"""

import argparse

import numpy as np
import tifffile
import cv2

OUT = r"C:\dev\strehl-out\M109"
BEFORE = rf"{OUT}\marker-argmax-e024-before.tif"
AFTER = rf"{OUT}\marker-argmax-e024-after.tif"
FRAME = r"D:\personal\macro\dry-erase-marker-head-cpl\DSC00150.ARW"

CROP = 520  # side of the 1:1 crop, in output pixels


def parse_args() -> argparse.Namespace:
    """Defaults reproduce the committed argmax montage byte-for-byte.

    The `stack` arm reuses this script rather than getting its own, so that both
    montages place their crop by the SAME predicate-driven rule. A second script
    would be a second chance to aim at a flattering ROI.
    """
    p = argparse.ArgumentParser()
    p.add_argument("--before", default=BEFORE)
    p.add_argument("--after", default=AFTER)
    p.add_argument("--tag", default="", help="suffix for the output filenames")
    p.add_argument("--cmd", default="argmax-baseline --srgb --exposure=-0.24",
                   help="invocation shown in the panel subtitle")
    return p.parse_args()


def magenta(x: np.ndarray) -> np.ndarray:
    return ((x[..., 0] - x[..., 1]) > 0.06) & ((x[..., 2] - x[..., 1]) > 0.06)


def label(img: np.ndarray, text: str, sub: str) -> np.ndarray:
    bar = np.zeros((58, img.shape[1], 3), np.uint8)
    cv2.putText(bar, text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(bar, sub, (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (170, 170, 170), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def to8(x: np.ndarray) -> np.ndarray:
    return np.clip(x * 255.0 + 0.5, 0, 255).astype(np.uint8)


def main() -> None:
    args = parse_args()
    b = tifffile.imread(args.before).astype(np.float32) / 65535.0
    a = tifffile.imread(args.after).astype(np.float32) / 65535.0

    # Let the predicate place the crop: largest connected magenta component in
    # the before render, restricted to the pixels the fix actually cleared, so
    # the crop lands on the defect this milestone is about rather than on the
    # unrelated fringing it does not claim to fix.
    cleared = (magenta(b) & ~magenta(a)).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(cleared, 8)
    if n < 2:
        raise SystemExit("the predicate found no cleared region to crop")
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    cx, cy = (int(round(v)) for v in cent[big])
    print(f"largest cleared component: {stats[big, cv2.CC_STAT_AREA]} px, centroid ({cx}, {cy})")

    h, w = b.shape[:2]
    x0 = int(np.clip(cx - CROP // 2, 0, w - CROP))
    y0 = int(np.clip(cy - CROP // 2, 0, h - CROP))
    print(f"crop: x {x0}..{x0 + CROP}  y {y0}..{y0 + CROP}  (100 %, no resampling)")

    cb = to8(b[y0:y0 + CROP, x0:x0 + CROP])
    ca = to8(a[y0:y0 + CROP, x0:x0 + CROP])

    import rawpy
    with rawpy.imread(FRAME) as raw:
        lr = raw.postprocess(use_camera_wb=True, output_bps=16, no_auto_bright=True,
                             gamma=(2.4, 12.92)).astype(np.float32) / 65535.0
    lh, lw = lr.shape[:2]
    lx = int(np.clip(x0, 0, max(0, lw - CROP)))
    ly = int(np.clip(y0, 0, max(0, lh - CROP)))
    cl = to8(lr[ly:ly + CROP, lx:lx + CROP])

    mb = magenta(b[y0:y0 + CROP, x0:x0 + CROP])
    ma = magenta(a[y0:y0 + CROP, x0:x0 + CROP])
    print(f"crop magenta fraction: before {100 * mb.mean():.2f} %   after {100 * ma.mean():.2f} %")

    panels = [
        label(cb[..., ::-1], "BEFORE  ceiling disabled (negative control)",
              f"magenta {100 * mb.mean():.2f}% of crop   {args.cmd}"),
        label(ca[..., ::-1], "AFTER  highlight ceiling on",
              f"magenta {100 * ma.mean():.2f}% of crop   same binary, same frames, same exposure"),
        label(cl[..., ::-1], "LibRaw (rawpy), single frame DSC00150.ARW",
              "independent decoder -- registration approximate, +-12 px"),
    ]
    gap = np.full((panels[0].shape[0], 8, 3), 40, np.uint8)
    montage = np.hstack([panels[0], gap, panels[1], gap, panels[2]])
    path = rf"{OUT}\M109-highlights-montage-100pct{args.tag}.png"
    cv2.imwrite(path, montage)
    print(f"wrote {path}  {montage.shape[1]}x{montage.shape[0]}")

    # Whole-frame overview so the blob's size and place in the picture is
    # visible, not just the crop.
    def small(x):
        return to8(cv2.resize(x, (w // 6, h // 6), interpolation=cv2.INTER_AREA))
    ov = np.hstack([
        label(small(b)[..., ::-1], "BEFORE  whole frame (1/6 scale)", "the magenta blob, in context"),
        np.full((small(b).shape[0] + 58, 8, 3), 40, np.uint8),
        label(small(a)[..., ::-1], "AFTER  whole frame (1/6 scale)", "same everything but the ceiling"),
    ])
    path2 = rf"{OUT}\M109-highlights-wholeframe{args.tag}.png"
    cv2.imwrite(path2, ov)
    print(f"wrote {path2}  {ov.shape[1]}x{ov.shape[0]}")


if __name__ == "__main__":
    main()
