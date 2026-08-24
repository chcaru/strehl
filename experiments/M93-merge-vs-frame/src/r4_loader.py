"""R4 -- the loader control. Rule 32.

Arm F claims to be "one frame through the identical code path". That claim is
only worth anything if the file `strehl` writes for a one-frame stack really is
that frame. This decodes the same `.ARW` with `rawpy`, applies the arithmetic
`merge_cmd.rs`'s byte-frozen branch applies, and compares.

Also prints the sensor geometry and levels both decoders report, so a
disagreement about the active area shows up here rather than silently shifting
an ROI by a row.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402

ARW = os.path.join(L.FRAMES, "f150", "DSC00150.ARW")
TIF = os.path.join(L.OUT, "smoke-f150-binlin.tif")


def main() -> int:
    rf = L.decode_raw(ARW)
    print(f"rawpy  visible CFA : {rf.cfa.shape[1]} x {rf.cfa.shape[0]}  pattern {rf.pattern}")
    print(f"rawpy  levels      : black {rf.black:.1f}  white {rf.white:.1f}")

    tif = L.read_tif_green(TIF)
    print(f"strehl binned TIFF : {tif.shape[1]} x {tif.shape[0]}")

    # `merge_cmd.rs` byte-frozen branch:
    #   v = min(1, (green_mean - black) * g_green / (white - black))
    #   out = (v * 65535 + 0.5) as u16
    # We do not know g_green here, so fit it: it is a single scalar and the fit
    # is over-determined by 8.2 million pixels. If the pipeline applies a green
    # gain other than 1 this will show it rather than assume it.
    gm = L.green_mean_plane(rf.cfa)
    h = min(gm.shape[0], tif.shape[0])
    w = min(gm.shape[1], tif.shape[1])
    gm = gm[:h, :w]
    ref = tif[:h, :w]
    print(f"compared on        : {w} x {h}")

    # Levels: strehl reports its own; probe printed black 512 white 16383 for
    # the container, and the merge uses `levels.range()`. Rather than assume,
    # solve for (black, scale) by least squares on unclipped pixels.
    y = ref / 65535.0
    unclipped = (y > 0.001) & (y < 0.999)
    A = np.stack([gm[unclipped], np.ones(int(unclipped.sum()))], axis=1)
    coef, *_ = np.linalg.lstsq(A, y[unclipped], rcond=None)
    scale, offset = float(coef[0]), float(coef[1])
    implied_black = -offset / scale
    implied_range = 1.0 / scale
    print(f"fitted             : scale {scale:.10f}  offset {offset:.8f}")
    print(f"implied black      : {implied_black:.4f} DN")
    print(f"implied range      : {implied_range:.4f} DN   (white = {implied_black + implied_range:.4f})")

    pred = np.clip(gm * scale + offset, 0.0, 1.0)
    pred_u16 = np.floor(pred * 65535.0 + 0.5).astype(np.int64)
    d = pred_u16 - ref.astype(np.int64)
    print()
    print(f"max |diff|         : {np.abs(d).max()} DN of 65535")
    print(f"mean |diff|        : {np.abs(d).mean():.6f} DN")
    print(f"exact matches      : {100.0 * (d == 0).mean():.4f}% of pixels")
    print(f"within 1 DN        : {100.0 * (np.abs(d) <= 1).mean():.4f}% of pixels")

    # And the thing that actually matters for the spectrum: the correlation of
    # the two greens after removing the affine map, in a detailed region.
    res = (pred * 65535.0) - ref
    print(f"residual rms       : {res.std():.4f} DN of 65535")

    verdict = "PASS" if np.abs(d).max() <= 2 else "FAIL"
    print()
    print(f"R4 VERDICT         : {verdict}")

    out = {
        "arw": ARW,
        "tif": TIF,
        "rawpy_cfa_shape": list(rf.cfa.shape),
        "rawpy_pattern": rf.pattern,
        "rawpy_black": rf.black,
        "rawpy_white": rf.white,
        "tif_shape": list(tif.shape),
        "fit_scale": scale,
        "fit_offset": offset,
        "implied_black": implied_black,
        "implied_range": implied_range,
        "max_abs_diff_dn": int(np.abs(d).max()),
        "mean_abs_diff_dn": float(np.abs(d).mean()),
        "frac_exact": float((d == 0).mean()),
        "frac_within_1": float((np.abs(d) <= 1).mean()),
        "residual_rms_dn": float(res.std()),
        "verdict": verdict,
    }
    dst = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out", "r4_loader.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote              : {dst}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
