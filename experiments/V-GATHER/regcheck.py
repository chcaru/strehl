r"""Is a single-frame render REGISTERED to the master's pixel grid?

The entire attribution ratio assumes the window pinned on the master covers the
same scene content in every source frame. If STREHL_ONLY_FRAME emits an
unwarped frame instead of one warped into the reference grid, the window samples
different content in each and every ratio in this lane is meaningless.

Dimensions matching is NOT evidence of this -- two images can share a lattice
and be shifted by a hundred pixels. Measured by integer-shift cross-correlation
over a TEXTURED window (a flat one has no peak to find), with a positive
control: the same comparison against a deliberately shifted copy, which must
recover the shift it was given. Without that control a reading of (0,0) is
equally consistent with a working probe and a dead one.
"""
import os
import subprocess
import sys

import numpy as np
import tifffile

EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
RAW = r"D:\personal\macro"
WORK = r"C:\dev\strehl-out\V-GATHER\reg"
SUBJ = "109MSDCF"
R = 24


def render(out, only=None):
    env = dict(os.environ)
    env["STREHL_CACHE_DIR"] = os.path.join(r"C:\dev\strehl-out\V-GATHER\cert", SUBJ, "cache")
    for v in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU",
              "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME"):
        env.pop(v, None)
    if only is not None:
        env["STREHL_ONLY_FRAME"] = str(only)
    p = subprocess.run([EXE, "stack", os.path.join(RAW, SUBJ), "--out", out,
                        "--linear-srgb", "--demosaic"], env=env,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("render failed: %s" % p.stderr[-300:])
    return out


def lum(path):
    a = tifffile.imread(path).astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def textured(l, win=512):
    """Pick the window with the MOST gradient energy -- a peak needs structure."""
    h, w = l.shape
    best, at = -1.0, (0, 0)
    for y in range(0, h - win, win):
        for x in range(0, w - win, win):
            b = l[y:y + win, x:x + win]
            e = float(np.abs(np.diff(b, axis=0)).mean() + np.abs(np.diff(b, axis=1)).mean())
            if e > best:
                best, at = e, (y, x)
    return at, best


def peak_shift(a, b, r=R):
    """Integer-only search. Sub-pixel resampling would blur what is measured."""
    a = (a - a.mean()) / (a.std() + 1e-9)
    best, at = -9e9, (0, 0)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            bb = b[r + dy:b.shape[0] - r + dy, r + dx:b.shape[1] - r + dx]
            aa = a[r:a.shape[0] - r, r:a.shape[1] - r]
            bb = (bb - bb.mean()) / (bb.std() + 1e-9)
            c = float((aa * bb).mean())
            if c > best:
                best, at = c, (dy, dx)
    return at, best


def main():
    os.makedirs(WORK, exist_ok=True)
    mp = render(os.path.join(WORK, "master.tiff"))
    ml = lum(mp)
    (y, x), e = textured(ml)
    print("textured window at (%d,%d), gradient energy %.2f" % (y, x, e))
    mw = ml[y:y + 512, x:x + 512]

    print("\n%-28s %-12s %-9s %s" % ("arm", "shift(dy,dx)", "corr", "meaning"))
    print("-" * 92)

    # POSITIVE CONTROL FIRST. If this cannot recover a known shift, a (0,0)
    # reading on the real arm proves nothing at all.
    for want in ((7, -11), (-3, 5), (0, 0)):
        shifted = np.roll(np.roll(ml, want[0], axis=0), want[1], axis=1)
        sw = shifted[y:y + 512, x:x + 512]
        got, c = peak_shift(mw, sw)
        # SIGN DERIVED, NOT GUESSED. np.roll(ml, dy) gives shifted[i,j] =
        # ml[i-dy, j-dx], so the window read at the same coordinates satisfies
        # sw[a,b] = mw[a-dy, b-dx] and the correlator's matching offset is +want.
        # The first version asserted -want and reported "probe is dead" on a
        # correlation of 0.9669 -- a perfect recovery scored as a failure.
        ok = (got[0] == want[0] and got[1] == want[1])
        print("%-28s %-12s %-9.4f %s"
              % ("CONTROL planted %s" % (want,), str(got), c,
                 "recovered" if ok else "FAILED TO RECOVER -- probe is dead"))
        if not ok:
            raise SystemExit("positive control failed; refusing to interpret the real arm")

    for k in (0, 5, 11, 21):
        sp = render(os.path.join(WORK, "src.tiff"), only=k)
        sl = lum(sp)
        if sl.shape != ml.shape:
            print("frame %d LATTICE MISMATCH %s vs %s" % (k, sl.shape, ml.shape))
            continue
        got, c = peak_shift(mw, sl[y:y + 512, x:x + 512])
        print("%-28s %-12s %-9.4f %s"
              % ("frame %d vs master" % k, str(got), c,
                 "registered" if got == (0, 0) else "SHIFTED BY %s" % (got,)))
        os.remove(sp)
    os.remove(mp)


if __name__ == "__main__":
    main()
