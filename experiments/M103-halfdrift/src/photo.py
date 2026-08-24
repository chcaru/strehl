"""Look at the photograph.

The milestone's stated point is a sharper photograph, not a better number, so this
renders the before/after into something a human can inspect and simultaneously
tests a prediction that could falsify the whole story.

The prediction (DERIVED, written before the run): residual misregistration under a
scale error is `|s-1| * rho`, i.e. **proportional to distance from the image
centre**. So if the improvement comes from registration it must be

    * essentially zero at the centre, where even a 7.6% scale error displaces
      nothing, and
    * largest at the corners, where the baseline's residual reaches ~150 plane px.

A *uniform* improvement across the field would mean the change is doing something
else -- a global contrast or noise effect -- and would refute the attribution. That
makes this a control, not just a picture.

Acutance is measured per tile as mean squared gradient normalised by mean intensity
squared, on the green channel of the linear-ish sRGB render. Normalising by
intensity is what stops a brightness difference from masquerading as sharpness;
both renders share gate, colour path and frame set, so registration is the only
variable.

    python src/photo.py <before.tiff> <after.tiff> <outdir> <out.json>
"""

import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image


def acutance(g):
    """Mean squared gradient, normalised by mean intensity squared."""
    gy, gx = np.gradient(g.astype(np.float64))
    m = float(g.mean())
    if m <= 0:
        return 0.0
    return float((gx * gx + gy * gy).mean() / (m * m))


def main(argv):
    before_p, after_p, outdir, out_json = argv[1], argv[2], argv[3], argv[4]
    # Relative field of view of `after` against `before`. The merge shrinks the
    # field so every frame covers every output pixel, and a *larger* scale span
    # needs a larger shrink, so two solves of the same bracket can land on
    # different fields at the same pixel dimensions. Comparing acutance per pixel
    # across different fields compares different subject matter -- so when the
    # two coverages differ, pass the ratio and `before` is cropped and rescaled
    # onto `after`'s field first. Both renders print their coverage.
    fov = float(argv[5]) if len(argv) > 5 else 1.0
    os.makedirs(outdir, exist_ok=True)
    A = tifffile.imread(before_p)
    B = tifffile.imread(after_p)
    if A.shape != B.shape:
        raise SystemExit(f"shape mismatch {A.shape} vs {B.shape}")
    h, w = A.shape[:2]
    if abs(fov - 1.0) > 1e-6:
        kw, kh = int(round(w * fov)), int(round(h * fov))
        x0, y0 = (w - kw) // 2, (h - kh) // 2
        crop = Image.fromarray(A[y0:y0 + kh, x0:x0 + kw])
        A = np.asarray(crop.resize((w, h), Image.LANCZOS))
        print(f"FOV correction: cropped `before` to {kw}x{kh} (x{fov:.4f}) and "
              f"rescaled to {w}x{h} so both show the same field")
    print(f"{w}x{h}  before={os.path.basename(before_p)}  "
          f"after={os.path.basename(after_p)}")

    ga = A[..., 1].astype(np.float64)
    gb = B[..., 1].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = float(np.hypot(cx, cy))

    # Per-tile acutance, binned by radius.
    T = 256
    recs = []
    for y in range(0, h - T + 1, T):
        for x in range(0, w - T + 1, T):
            ta, tb = ga[y:y + T, x:x + T], gb[y:y + T, x:x + T]
            # Skip tiles with no structure: a flat background cannot report a
            # registration improvement and would only dilute the bins.
            if ta.std() < 1.0:
                continue
            r = float(np.hypot(x + T / 2 - cx, y + T / 2 - cy)) / rmax
            recs.append((r, acutance(ta), acutance(tb)))
    recs.sort()
    print(f"{len(recs)} textured tiles of {T}x{T}")
    print()
    print(f"{'r/rmax':>12} {'tiles':>6} {'before':>11} {'after':>11} "
          f"{'after/before':>13}")
    bins = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    out = {"before": before_p, "after": after_p, "bins": []}
    for lo, hi in bins:
        sel = [t for t in recs if lo <= t[0] < hi]
        if not sel:
            continue
        a = float(np.mean([t[1] for t in sel]))
        b = float(np.mean([t[2] for t in sel]))
        print(f"{lo:>5.2f}-{hi:<6.2f} {len(sel):>6} {a:>11.5f} {b:>11.5f} "
              f"{b / a:>12.4f}x")
        out["bins"].append(dict(lo=lo, hi=hi, n=len(sel), before=a, after=b,
                                ratio=b / a))
    ga_all, gb_all = acutance(ga), acutance(gb)
    out["global"] = dict(before=ga_all, after=gb_all, ratio=gb_all / ga_all)
    print()
    print(f"whole frame: {ga_all:.5f} -> {gb_all:.5f}  "
          f"({gb_all / ga_all:.4f}x)")

    inner = out["bins"][0]["ratio"]
    outer = out["bins"][-1]["ratio"]
    out["inner_ratio"], out["outer_ratio"] = inner, outer
    print(f"centre bin {inner:.4f}x vs outer bin {outer:.4f}x  "
          f"-> gradient {outer - inner:+.4f}")
    print("PREDICTION: outer > inner if the gain is registration. "
          f"{'HOLDS' if outer > inner else 'REFUTED'}")

    # Crops to actually look at. Fixed spots are useless on this subject: the
    # corners are defocused background where no registration change can show. So
    # the outer crops are placed on the most textured tiles the *baseline* has at
    # large radius -- chosen from the before image alone, so the choice cannot be
    # tuned to flatter the after image.
    C = 700
    spots = {"centre": (int(cx - C / 2), int(cy - C / 2))}
    tiles = []
    for y in range(0, h - T + 1, T):
        for x in range(0, w - T + 1, T):
            ta = ga[y:y + T, x:x + T]
            if ta.std() < 1.0:
                continue
            r = float(np.hypot(x + T / 2 - cx, y + T / 2 - cy)) / rmax
            tiles.append((r, acutance(ta), x, y))
    for label, (lo, hi) in {"mid": (0.45, 0.65), "outer": (0.65, 1.01)}.items():
        band = sorted([t for t in tiles if lo <= t[0] < hi], key=lambda t: -t[1])
        for i, (_, _, x, y) in enumerate(band[:2]):
            px = int(min(max(x + T // 2 - C // 2, 0), w - C))
            py = int(min(max(y + T // 2 - C // 2, 0), h - C))
            spots[f"{label}-{i + 1}"] = (px, py)
    for name, (x, y) in spots.items():
        pair = []
        for img in (A, B):
            c = img[y:y + C, x:x + C, :3].astype(np.float64) / 65535.0
            pair.append(np.clip(c, 0, 1))
        gap = np.ones((C, 12, 3))
        side = np.concatenate([pair[0], gap, pair[1]], axis=1)
        p = os.path.join(outdir, f"{name}.png")
        Image.fromarray((side * 255).astype(np.uint8)).save(p)
        print(f"wrote {p}  (left=before  right=after)")

    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
