"""Measure the correction in the DELIVERED PIXELS, not in the residual.

Everything so far measured a residual in a Python pipeline.  This measures the
16-bit sRGB TIFF the tool actually writes, from two `strehl argmax-baseline`
renders of D:\\personal\\macro\\bee-3-cpl that differ in exactly one thing --
whether STREHL_DEFECT_MAP was set.  Both were rendered at a FIXED --exposure=1.47
so the auto-exposure chooser cannot silently move the comparison.

What is required of the result, and each of these can fail:

  1. At the mote, the corrected render must be BRIGHTER, by roughly the gain the
     map carries (median 1.0608, max 1.0994 at (3434,2305)).
  2. Away from the mote, the two renders must be BIT-IDENTICAL.  A correction
     that touches pixels it was not asked to touch is a worse defect than the
     dust.
  3. The count of differing pixels must match the map: 1135 quads, so at most
     1135 * 4 = 4540 CFA samples per frame, and after demosaic a bounded
     neighbourhood of those.
  4. An UNCORRECTED CONTROL LOCATION with no mote must show zero change --
     otherwise the difference is not the correction, it is the renderer.

tifffile, never PIL: PIL mis-reads this project's TIFFs (a trap this project has
paid for before).
"""

import json
import pathlib
import time

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


# Quad coordinates from the map -> sensor pixel = 2 * quad.
MOTES = [(3202, 121), (3434, 2305)]
CONTROL = (1600, 1000)
R = 24  # quads either way


def region(img, cx, cy, r=R):
    """Mean over the three channels of a 2r-quad box, in sensor pixels."""
    y0, x0 = 2 * (cy - r), 2 * (cx - r)
    return img[y0 : y0 + 4 * r, x0 : x0 + 4 * r].astype(np.float64).mean(axis=2)


def main():
    off = tifffile.imread(OUT / "renders" / "bee3-dust-off.tiff")
    on = tifffile.imread(OUT / "renders" / "bee3-dust-on.tiff")
    log(f"off {off.shape} {off.dtype}, on {on.shape} {on.dtype}")
    assert off.shape == on.shape and off.dtype == on.dtype == np.uint16

    d = on.astype(np.int32) - off.astype(np.int32)
    changed = np.any(d != 0, axis=2)
    n_changed = int(changed.sum())
    log(
        f"pixels differing: {n_changed} of {changed.size} "
        f"({100 * n_changed / changed.size:.6f}%)"
    )

    ys, xs = np.nonzero(changed)
    log(
        f"changed bounding box: x {xs.min()}..{xs.max()}, y {ys.min()}..{ys.max()}"
    )
    log(f"max |delta| = {int(np.abs(d).max())} DN of 65535")

    rows = []
    for cx, cy in MOTES:
        a, b = region(off, cx, cy), region(on, cx, cy)
        # The mote core, and an annulus of the same box that is outside it.
        yy, xx = np.ogrid[: a.shape[0], : a.shape[1]]
        cc = ((yy - a.shape[0] / 2) ** 2 + (xx - a.shape[1] / 2) ** 2) <= (2 * 12) ** 2
        rows.append(
            dict(
                quad=[cx, cy],
                off_core=float(a[cc].mean()),
                on_core=float(b[cc].mean()),
                ratio_core=float(b[cc].mean() / a[cc].mean()),
                off_ring=float(a[~cc].mean()),
                on_ring=float(b[~cc].mean()),
                ratio_ring=float(b[~cc].mean() / a[~cc].mean()),
            )
        )
        log(
            f"  mote ({cx},{cy}): core {a[cc].mean():9.1f} -> {b[cc].mean():9.1f} "
            f"= x{b[cc].mean() / a[cc].mean():.5f}   surround "
            f"{a[~cc].mean():9.1f} -> {b[~cc].mean():9.1f} "
            f"= x{b[~cc].mean() / a[~cc].mean():.5f}"
        )

    ca, cb = region(off, *CONTROL), region(on, *CONTROL)
    identical = bool(np.array_equal(ca, cb))
    log(
        f"  CONTROL ({CONTROL[0]},{CONTROL[1]}): {ca.mean():9.1f} -> {cb.mean():9.1f}, "
        f"bit-identical: {identical}"
    )

    # How much of the frame is untouched?
    frac = 100 * (1 - n_changed / changed.size)
    log(f"untouched: {frac:.4f}% of the frame")

    ok = (
        identical
        and all(r["ratio_core"] > 1.0 for r in rows)
        and all(abs(r["ratio_ring"] - 1.0) < abs(r["ratio_core"] - 1.0) for r in rows)
    )
    log(f"VERDICT: {'PASS' if ok else 'FAIL'}")

    (DATA / "17-pixels.json").write_text(
        json.dumps(
            dict(
                pixels_changed=n_changed,
                pixels_total=int(changed.size),
                max_abs_delta=int(np.abs(d).max()),
                bbox=[int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
                motes=rows,
                control_identical=identical,
                verdict="PASS" if ok else "FAIL",
            ),
            indent=1,
        ),
        encoding="utf-8",
    )
    log("wrote data/17-pixels.json")


if __name__ == "__main__":
    main()
