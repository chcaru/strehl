r"""LOOK AT THE PIXELS AT THE SITES THE INSTRUMENT ITSELF CONVICTED.

Two renders per subject, both at 1:1, both sRGB-encoded FOR LOOKING ONLY --
nothing here is measured, per the standing project rule.

  STRIP   the four edges with the LARGEST per-edge overshoot, plus two at the
          subject's median overshoot as a matched control. If a rim of the
          claimed amplitude is real, the worst four are where it is.

  STACK   every selected edge resampled onto a common (25 x 41) grid -- 25 px
          along the gradient normal, 41 px along the edge tangent -- rotated so
          bright is always to the right, then MEDIANED over all edges. Texture
          and noise are incoherent along the edge and average away; a rim is
          coherent and survives. Shown x8 nearest-neighbour so a few DN over
          5 px is not hidden by the display.

  The stack is shown twice: as it is, and with the LOCAL CONTRAST STRETCHED so
  that a band too faint to see in the first is unmissable in the second. A
  defect that only appears in the stretched panel is real and below visibility,
  which is a different verdict from both clean and defective.
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

import vr_lib as V
import rimaxis
import rimv6

PIC = os.path.join(V.SCRATCH, "pics")
CROP = 192
HALF = CROP // 2
TAN = np.arange(-20, 21)


def srgb(v):
    v = np.clip(v, 0.0, 1.0)
    v = np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1 / 2.4) - 0.055)
    return (v * 255.0 + 0.5).astype(np.uint8)


def stack_edges(g, sel, T, nmax=4000):
    """(25 x 41) median edge, bright always to the right."""
    acc = []
    for (y, x, yy, xx, dy, dx) in sel[:nmax]:
        t = g[y:y + T, x:x + T]
        # dy,dx is the unit gradient (points bright); tangent is (-dx, dy)
        py = yy + np.outer(TAN, -dx) + np.outer(np.ones_like(TAN), dy * rimv6.TT).T.T * 0
        # build explicitly: rows = tangent, cols = normal
        ry = yy + TAN[:, None] * (-dx) + rimv6.TT[None, :] * dy
        rx = xx + TAN[:, None] * (dy) + rimv6.TT[None, :] * dx
        ry = np.round(ry).astype(int)
        rx = np.round(rx).astype(int)
        if ry.min() < 0 or rx.min() < 0 or ry.max() >= T or rx.max() >= T:
            continue
        p = t[ry, rx].astype(np.float32)
        lo = p[:, :4].mean()
        hi = p[:, -4:].mean()
        if hi - lo <= 1e-6:
            continue
        acc.append((p - lo) / (hi - lo))
    if not acc:
        return None
    return np.median(np.stack(acc), axis=0)


def upn(a, k=8):
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def main():
    which = sys.argv[1]
    subs = sys.argv[2:]
    base = V.SHIP if which == "ship" else V.DELIV
    suf = "--SHIP-V4.tiff" if which == "ship" else ".tiff"
    os.makedirs(PIC, exist_ok=True)
    import tifffile
    for s in subs:
        a = tifffile.imread(os.path.join(base, s + suf))
        g = rimaxis.lum_of(a)
        clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
        rois = rimaxis.pick_rois(g, clip)
        ref, sel, n_all, cut, fl = rimaxis.select_for(g, clip, rois)
        e = rimv6.measure(g, sel, rimaxis.T)
        if e is None:
            print("%s: no measurement" % s)
            continue
        ov = e["ov"]
        gain = 1.0 / max(1e-6, np.percentile(a[::8, ::8].astype(np.float32),
                                             99.9) / 65535.0)
        order = np.argsort(-ov)
        picks = list(order[:4]) + list(order[len(order) // 2:len(order) // 2 + 2])
        tiles, labels = [], []
        for i in picks:
            y, x, yy, xx, dy, dx = sel[i]
            cy, cx = y + yy, x + xx
            y0 = min(max(0, cy - HALF), a.shape[0] - CROP)
            x0 = min(max(0, cx - HALF), a.shape[1] - CROP)
            c = a[y0:y0 + CROP, x0:x0 + CROP].astype(np.float32) / 65535.0
            tiles.append(srgb(c * gain))
            labels.append("ov %+.1f%% @(%d,%d)" % (100 * ov[i], cy, cx))
        sep = np.full((CROP, 6, 3), 40, np.uint8)
        strip = tiles[0]
        for t in tiles[1:]:
            strip = np.concatenate([strip, sep, t], axis=1)
        Image.fromarray(strip).save(os.path.join(PIC, "%s-%s-strip.png" % (which, s)))

        st = stack_edges(g, sel, rimaxis.T)
        prof = np.median(st, axis=0)
        # panel 1: absolute, using the subject's own lo..hi mapped through the
        # subject's real DN range at the median step
        step = float(np.median(e["st"])) / 65535.0
        lo_abs = float(np.percentile(a[::8, ::8].astype(np.float32), 50)) / 65535.0
        p1 = srgb(np.dstack([(lo_abs + st * step) * gain] * 3))
        # panel 2: stretched about 1.0 so +/-6% of the step fills the panel
        p2 = srgb(np.dstack([np.clip(0.5 + (st - 1.0) / 0.12, 0, 1)] * 3))
        pan = np.concatenate([upn(p1), np.full((41 * 8, 12, 3), 40, np.uint8),
                              upn(p2)], axis=1)
        Image.fromarray(pan).save(os.path.join(PIC, "%s-%s-stack.png" % (which, s)))
        print("%-8s %-38s  gain %.2f  step %.4f  worst ov %+.1f%%  "
              "median ov %+.1f%%" % (which, s, gain, step, 100 * ov[order[0]],
                                     100 * np.median(ov)))
        print("   stacked median profile q(t) for t=-12..+12:")
        print("   " + " ".join("%.3f" % v for v in prof))
        print("   sites: " + " | ".join(labels))
        del a, g, clip, ref
    print("\nwrote %s" % PIC)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
