r"""Look at the blocky texture in the master band-pass at NATIVE resolution.

The 460-px contact sheets are downsampled 900->460; a texture seen there could
be aliasing.  This crops 300x300 at 1:1, applies the gate's own band-pass, and
prints it at 3x NEAREST so no interpolation can invent or hide a grid.  A
planted 32-px block field of a stated amplitude is shown beside it as a ruler.

  python vr_zoom.py SUBJECT [--cell=32] [--amp=0.004] [--off=0,0]
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_blotch import boxblur, LO_R, HI_R                   # noqa: E402

C = 300


def band_rel(blk):
    return (boxblur(blk, LO_R // 2) - boxblur(blk, HI_R // 2)) / max(float(np.mean(blk)), 1e-9)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    cell = int(opts.get("cell", 32))
    amp = float(opts.get("amp", 0.004))
    oy, ox = [int(v) for v in opts.get("off", "0,0").split(",")]
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    wy, wx = S["master"]["blotch"]["y"], S["master"]["blotch"]["x"]
    W = V.BWIN
    m = V.lum_of(V.read_rgb(V.master_path(subj)))
    # band-pass on the FULL 900 window (so the 400-px high radius is honest),
    # then crop the middle 300 for display.
    win = m[wy:wy + W, wx:wx + W]
    B = band_rel(win)
    y0 = W // 2 - C // 2 + oy
    x0 = W // 2 - C // 2 + ox
    b = B[y0:y0 + C, x0:x0 + C]

    mm = float(np.mean(win))
    rng = np.random.default_rng(11)
    cellf = rng.normal(0, 1, (W // cell + 2, W // cell + 2)).astype(np.float32)
    grid = np.repeat(np.repeat(cellf, cell, 0), cell, 1)[:W, :W]
    planted = win + amp * mm * grid
    bp = band_rel(planted)[y0:y0 + C, x0:x0 + C]

    g = 2.5 / max(float(np.percentile(np.abs(B), 99)), 1e-12)
    lo, hi = np.percentile(win, [1, 99])
    panels = [((np.clip((win[y0:y0 + C, x0:x0 + C] - lo) / max(hi - lo, 1e-9), 0, 1)),
               "master 1:1 (as seen)"),
              (np.clip(0.5 + g * b, 0, 1), "master band x%.0f" % g),
              (np.clip(0.5 + g * bp, 0, 1),
               "+ planted %d px blocks, %.3f*mean = %.0f DN" % (cell, amp, amp * mm))]
    out = np.zeros((C * 3 + 18, C * 3 * len(panels), 3), np.uint8)
    for i, (img, lab) in enumerate(panels):
        t = cv2.resize((np.clip(img, 0, 1) * 255).astype(np.uint8), (C * 3, C * 3),
                       interpolation=cv2.INTER_NEAREST)
        out[:C * 3, i * C * 3:(i + 1) * C * 3] = np.dstack([t] * 3) if t.ndim == 2 else t
        cv2.putText(out, lab, (i * C * 3 + 4, C * 3 + 13), cv2.FONT_HERSHEY_PLAIN,
                    1.0, (255, 255, 255), 1)
    p = os.path.join(V.OUT, "zoom-%s.png" % subj)
    cv2.imwrite(p, out[:, :, ::-1])
    print("window (%d,%d) crop at (%d,%d) size %d, band gain x%.0f, band sd %.5f"
          % (wy, wx, wy + y0, wx + x0, C, g, float(np.std(B))))
    print("wrote %s" % p)


if __name__ == "__main__":
    main()
