"""One frame against the stack, at the same scene location, both unresampled.

This is the demonstration that answers "is the stacking doing anything", and it
is the one comparison a photographer can adjudicate without any instrument.

THE REGISTRATION PROBLEM. strehl aligns by default, and focus breathing means
alignment shrinks the field about 7-10%, so pixel (x,y) in the 299-frame master
is NOT the same scene point as (x,y) in a single-frame render. A naive crop at
matching coordinates would compare two different parts of the bee and prove
nothing.

So the scale and shift are estimated first, by normalised cross-correlation over
a coarse scale ladder on 8x-downscaled copies.

DISCIPLINE: THE SEARCH MAY RESAMPLE. THE OUTPUT MAY NOT. The scale estimate is
computed on downscaled copies; the delivered crops are integer slices out of the
full-resolution files, so what is shown is what is in the file. The only
transform applied to either crop is a 16-to-8 bit shift, applied identically to
both.

The single-frame arm is a real middle frame of the bracket, DSC00151 of 299 --
not the first, which sits at one end of the sweep and would flatter the stack by
being out of focus everywhere.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

MASTER_DIR = r"C:\dev\strehl-out\acceptance\SHIP-V4"
ONE = r"C:\dev\strehl-out\ORCH-ONEFRAME\oneframe.tiff"
DST = r"C:\dev\strehl-out\ORCH-ONEFRAME"
CROP = 380
DS = 8


def small(y, f):
    im = Image.fromarray(y.astype(np.float32), mode="F")
    return np.asarray(im.resize((int(y.shape[1] * f), int(y.shape[0] * f)),
                                Image.BILINEAR), dtype=np.float32)


def ncc_peak(a, b):
    """Peak normalised cross-correlation of b inside a, via FFT."""
    a = a - a.mean()
    b = b - b.mean()
    h, w = a.shape
    bb = np.zeros_like(a)
    bb[:b.shape[0], :b.shape[1]] = b
    c = np.fft.irfft2(np.fft.rfft2(a) * np.conj(np.fft.rfft2(bb)), s=(h, w))
    i = int(np.argmax(c))
    dy, dx = i // w, i % w
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    return float(c.flat[i] / denom if denom > 0 else 0.0), dx, dy


def main():
    mp = None
    for c in sorted(os.listdir(MASTER_DIR)):
        if c.startswith("bee-3") and c.endswith(".tiff"):
            mp = os.path.join(MASTER_DIR, c)
    if mp is None:
        print("master not found")
        return 1
    print("master : %s" % os.path.basename(mp))
    print("frame  : %s" % os.path.basename(ONE))

    m = tifffile.imread(mp)
    o = tifffile.imread(ONE)
    print("master %s   oneframe %s" % (m.shape, o.shape))
    my = m[..., 1].astype(np.float32)
    oy = o[..., 1].astype(np.float32)

    ms = small(my, 1.0 / DS)
    best = (None, -2.0, 0, 0)
    for s in np.arange(0.88, 1.16, 0.01):
        os_ = small(oy, s / DS)
        hh = min(ms.shape[0], os_.shape[0])
        ww = min(ms.shape[1], os_.shape[1])
        r, dx, dy = ncc_peak(ms[:hh, :ww], os_[:hh, :ww])
        if r > best[1]:
            best = (s, r, dx, dy)
    s, r, dx, dy = best
    print("\nbest scale %.3f  ncc %.4f  shift (%d,%d) at 1/%d" % (s, r, dx, dy, DS))
    if r < 0.30:
        print("*** REGISTRATION FAILED (ncc %.4f). Refusing to emit a comparison"
              " that may show two different places. ***" % r)
        return 2

    # a site with real detail in the MASTER, then mapped into the frame
    lap = np.abs(np.diff(my, 2, axis=0)[:, :-2]) + np.abs(np.diff(my, 2, axis=1)[:-2, :])
    b = 64
    hh, ww = lap.shape[0] // b, lap.shape[1] // b
    blk = lap[:hh * b, :ww * b].reshape(hh, b, ww, b).mean(axis=(1, 3))
    pad = CROP // b + 2
    blk[:pad, :] = 0
    blk[-pad:, :] = 0
    blk[:, :pad] = 0
    blk[:, -pad:] = 0
    i = int(np.argmax(blk))
    cx, cy = (i % ww) * b + b // 2, (i // ww) * b + b // 2

    # master pixel -> oneframe pixel, from the fitted scale and shift
    ox = int(round((cx / DS - dx) / s * DS))
    oy_ = int(round((cy / DS - dy) / s * DS))
    print("master site (%d,%d)  ->  frame site (%d,%d)" % (cx, cy, ox, oy_))

    def cut(a, x, y, tag):
        x0 = max(0, min(a.shape[1] - CROP, x - CROP // 2))
        y0 = max(0, min(a.shape[0] - CROP, y - CROP // 2))
        c = a[y0:y0 + CROP, x0:x0 + CROP]
        c8 = ((c.astype(np.uint32) + 128) >> 8).astype(np.uint8)
        p = os.path.join(DST, "%s.png" % tag)
        Image.fromarray(c8).save(p)
        g = c[..., 1].astype(np.float32)
        acu = float((np.abs(np.diff(g, 2, axis=0)[:, :-2])
                     + np.abs(np.diff(g, 2, axis=1)[:-2, :])).mean())
        print("  %-28s (%d,%d) %dx%d   mean |laplacian| %8.1f DN"
              % (tag, x0, y0, CROP, CROP, acu))
        return acu

    print("\nboth crops are integer slices, no resampling, same 16->8 bit shift:")
    a_stack = cut(m, cx, cy, "STACK-299-frames")
    a_one = cut(o, ox, oy_, "ONE-frame-DSC00151")
    print("\n  stack / single frame acuity ratio: %.2fx" % (a_stack / max(a_one, 1e-9)))
    print("  (a ratio near 1 at a site chosen FOR detail in the master would mean")
    print("   the stack is adding nothing there; it is not a quality score.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
