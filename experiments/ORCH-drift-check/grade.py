"""ORCH presentation probe -- is part of "these look horrible" a GRADING problem?

NOT A MEASUREMENT TOOL. Everything here is a monotone tone curve plus a
saturation change, i.e. exactly the transformation this project forbids
measuring across. Nothing produced by this script may be fed to any gate,
acceptance test, or numeric comparison. It exists to answer one question that
is about perception, not physics:

    the shipped renders are faithful (linear -> sRGB, one gain, no curve).
    Does a photographer looking at them call them "horrible" because they are
    SOFT, or because they are FLAT?

Those two have completely different fixes and the project has been assuming the
first without testing the second.

Usage:
    python grade.py <in.jpg> <out_sidebyside.jpg> [--label NAME]
"""
import argparse
import sys

import numpy as np
from PIL import Image


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    a = 0.055
    return np.where(x <= 0.04045, x / 12.92, ((x + a) / (1 + a)) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    a = 0.055
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, (1 + a) * x ** (1 / 2.4) - a)


S_CURVE_STRENGTH = 0.42


def s_curve(x: np.ndarray) -> np.ndarray:
    """A monotone filmic S: darkens shadows, brightens highlights, holds 0 and 1.

    Sign matters and has been wrong here once. `(2x-1)` is negative below the
    midpoint and positive above it, so ADDING the term pushes each half away
    from the centre, which is contrast. Negating it pulls both halves toward
    the centre, which is the opposite. See `assert_is_an_s_curve`.
    """
    return x + S_CURVE_STRENGTH * x * (1.0 - x) * (2.0 * x - 1.0)


def assert_is_an_s_curve() -> None:
    """Refuse to run if the tone curve is not, in fact, an S.

    This is cheap and it runs on every invocation, because the failure it
    guards against is silent: an inverted curve still produces a plausible
    picture, still clips nothing, and still passes every structural check.
    The only thing that distinguishes it is the direction of the contrast,
    and nothing was checking the direction.
    """
    x = np.linspace(0.0, 1.0, 1001)
    y = s_curve(x)
    if not np.all(np.diff(y) > 0):
        raise SystemExit("grade.py: tone curve is not monotonic - refusing to run")
    if not (abs(y[0]) < 1e-9 and abs(y[-1] - 1.0) < 1e-9):
        raise SystemExit("grade.py: tone curve does not hold its endpoints")
    if y[250] >= 0.25:
        raise SystemExit(f"grade.py: curve LIFTS shadows (0.25 -> {y[250]:.4f}) - it is inverted")
    if y[750] <= 0.75:
        raise SystemExit(f"grade.py: curve PULLS DOWN highlights (0.75 -> {y[750]:.4f}) - it is inverted")
    mid = (x >= 0.25) & (x <= 0.75)
    slope = np.polyfit(x[mid], y[mid], 1)[0]
    if slope <= 1.0:
        raise SystemExit(f"grade.py: midtone slope {slope:.4f} <= 1 - this curve reduces contrast")


def midtone_contrast(rgb: np.ndarray) -> float:
    """p75-p25 of BT.709 luma. A blunt but honest proxy for "has contrast"."""
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    return float(np.percentile(lum, 75) - np.percentile(lum, 25))


def apply_s_curve_safely(out: np.ndarray) -> tuple[np.ndarray, float]:
    """Apply the S-curve only as hard as it actually helps this image.

    A fixed contrast curve is wrong for a high-key subject. Measured on
    `flower-bud-alone-cpl` -- a white bud on white, median luma 239/255 --
    full strength drove midtone contrast 13.0 -> 9.2, i.e. WORSE than the
    ungraded input, because an S-curve brightens highlights and this subject
    is already living in them. Five other subjects gained 11-32% from the
    same curve.

    So: back the strength off until the grade is not worse than no grade.
    This mirrors the merge's own "never worse than a single frame" invariant
    -- a presentation render that degrades the picture is not a presentation
    render. Returns the graded image and the strength actually used, so the
    caller can report a backed-off subject instead of silently shipping one.
    """
    global S_CURVE_STRENGTH
    before = midtone_contrast(out)
    full = S_CURVE_STRENGTH
    for factor in (1.0, 0.5, 0.25, 0.0):
        S_CURVE_STRENGTH = full * factor
        if factor == 0.0:
            S_CURVE_STRENGTH = full
            return out, 0.0
        cand = np.clip(s_curve(np.clip(out, 0.0, 1.0)), 0.0, 1.0)
        if midtone_contrast(cand) >= before:
            S_CURVE_STRENGTH = full
            return cand, full * factor
    S_CURVE_STRENGTH = full
    return out, 0.0


def grade(img: np.ndarray) -> np.ndarray:
    """A conservative, entirely conventional photographic rendering.

    Deliberately boring: a percentile black/white point, a mild filmic S-curve,
    and a modest saturation lift. Nothing here is clever or bespoke -- the point
    is to apply what ANY raw developer would apply by default, so that if the
    result transforms the impression, the deficit was never sharpness.
    """
    lin = srgb_to_linear(img)

    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    # Black point: the 0.1th percentile, so a genuinely black background lands
    # at black instead of at a washed-out dark grey.
    blk = np.percentile(lum, 0.1)
    wht = np.percentile(lum, 99.8)
    if not np.isfinite(blk) or not np.isfinite(wht) or wht <= blk:
        blk, wht = 0.0, 1.0
    lin = (lin - blk) / (wht - blk)
    lin = np.clip(lin, 0.0, None)

    out = linear_to_srgb(lin)

    # Filmic-ish S-curve in display space. Contrast where the midtones are,
    # shoulders that do not clip.
    #
    # The `* -1.0` that used to close this line INVERTED the curve. Measured on
    # the 1001-point ladder in curve_check.py: midtone slope 0.822 instead of
    # 1.178, shadows LIFTED 0.25 -> 0.2894, highlights PULLED DOWN 0.75 ->
    # 0.7106. It was a contrast-crushing curve wearing the name of an S-curve,
    # and across the 26-subject corpus it cost a median 0.939x of midtone
    # contrast -- so the script written to ask "do these look bad because they
    # are FLAT?" was flattening them before anyone looked.
    out = np.clip(out, 0.0, 1.0)
    out, used = apply_s_curve_safely(out)
    if used < S_CURVE_STRENGTH:
        print(f"  note: S-curve backed off to {used:.3f} of {S_CURVE_STRENGTH:.3f} "
              f"(full strength would have REDUCED midtone contrast on this subject)")
    out = np.clip(out, 0.0, 1.0)

    # Modest saturation. Macro subjects carry real colour that a faithful
    # render leaves on the table.
    g = out @ np.array([0.2126, 0.7152, 0.0722])
    out = np.clip(g[..., None] + (out - g[..., None]) * 1.18, 0.0, 1.0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--label", default="")
    ap.add_argument("--maxw", type=int, default=1400,
                    help="0 means full resolution, no resize")
    ap.add_argument(
        "--single",
        action="store_true",
        help="write the graded image alone, with no side-by-side and no caption",
    )
    args = ap.parse_args()

    assert_is_an_s_curve()

    im = Image.open(args.src).convert("RGB")
    # `and` is load-bearing: 0 is the "no resize" sentinel finalpass.ps1 now
    # passes, and `im.width > 0` is true for every image ever made, so without
    # the guard this resizes to zero width. viewable.py has always had it; this
    # file did not, and the two are called from the same variable.
    if args.maxw and im.width > args.maxw:
        h = round(im.height * args.maxw / im.width)
        im = im.resize((args.maxw, h), Image.LANCZOS)

    a = np.asarray(im).astype(np.float64) / 255.0
    b = grade(a)

    left = (a * 255.0 + 0.5).astype(np.uint8)
    right = (b * 255.0 + 0.5).astype(np.uint8)

    if args.single:
        Image.fromarray(right).save(args.dst, quality=93)
        print(f"  -> {args.dst}  (graded, {right.shape[1]}x{right.shape[0]})")
        return 0

    pad = 8
    h, w, _ = left.shape
    canvas = np.zeros((h + 26, w * 2 + pad, 3), dtype=np.uint8)
    canvas[26:, :w] = left
    canvas[26:, w + pad:] = right

    out = Image.fromarray(canvas)
    from PIL import ImageDraw

    d = ImageDraw.Draw(out)
    tag = f"  {args.label}" if args.label else ""
    d.text((6, 7), f"SHIPPED (faithful, no curve){tag}", fill=(255, 210, 90))
    d.text((w + pad + 6, 7), "SAME FILE, conventional grade  [PRESENTATION ONLY]", fill=(120, 235, 140))
    out.save(args.dst, quality=92)
    print(f"  -> {args.dst}  ({out.width}x{out.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
