"""How much did true11.py's unclipped 16->8 conversion actually corrupt?

The defect (found by V-H2H2, not by me, in my own file):

    c8 = ((c.astype(np.uint32) + 128) >> 8).astype(np.uint8)

For c >= 65408 the shift yields 256, and the uint8 cast wraps it to 0.
Pure white renders BLACK. Every visual verdict made on a crop containing
blown highlights was made on an image with black speckle the stacker
did not produce.

This does not fix anything. It prices the damage, per site, so the
correction is a measurement and not an apology. A fix whose blast radius
is unmeasured is indistinguishable from a fix that was not needed.
"""
import os
import sys

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
CROP = 380

# Every site true11.py has ever cut, with the name AS WRITTEN in SITES.
# wrapped-text-1-cpl is deliberately left wrong here: this script must
# reproduce what the old code did, including the site it never cut.
HISTORICAL = ["tweezers-cpl", "lavendar-cpl", "bee-3-cpl", "wrapped-text-1-cpl"]


def old_convert(c):
    """Byte-for-byte the shipped conversion, wrap included."""
    return ((c.astype(np.uint32) + 128) >> 8).astype(np.uint8)


def new_convert(c):
    return np.clip((c.astype(np.uint32) + 128) >> 8, 0, 255).astype(np.uint8)


def best_site(y):
    h, w = y.shape
    lap = np.abs(np.diff(y, 2, axis=0)[:, :-2]) + np.abs(np.diff(y, 2, axis=1)[:-2, :])
    s = 64
    hh, ww = lap.shape[0] // s, lap.shape[1] // s
    blk = lap[:hh * s, :ww * s].reshape(hh, s, ww, s).mean(axis=(1, 3))
    m = CROP // s + 1
    blk[:m, :] = 0
    blk[-m:, :] = 0
    blk[:, :m] = 0
    blk[:, -m:] = 0
    i = int(np.argmax(blk))
    return (i % ww) * s + s // 2, (i // ww) * s + s // 2


def commission():
    """The probe must fire on a known wrap and stay silent on a known safe input.

    Without this the '0 corrupted pixels' rows below are unreadable: they
    would look identical whether the crop was clean or the probe was dead.
    """
    fired = []
    # arm 1: a value that MUST wrap
    a = np.full((4, 4), 65535, np.uint16)
    fired.append(("wrap-65535", int((old_convert(a) != new_convert(a)).sum()), 16))
    # arm 2: the exact threshold
    a = np.full((4, 4), 65408, np.uint16)
    fired.append(("wrap-65408-threshold", int((old_convert(a) != new_convert(a)).sum()), 16))
    # arm 3: one below threshold MUST NOT wrap
    a = np.full((4, 4), 65407, np.uint16)
    fired.append(("safe-65407", int((old_convert(a) != new_convert(a)).sum()), 0))
    # arm 4: mid grey must not wrap
    a = np.full((4, 4), 32768, np.uint16)
    fired.append(("safe-midgrey", int((old_convert(a) != new_convert(a)).sum()), 0))
    # arm 5: the wrap must be to BLACK specifically, not to some other value
    a = np.full((2, 2), 65535, np.uint16)
    fired.append(("wraps-to-zero", int((old_convert(a) == 0).sum()), 4))

    ok = 0
    for name, got, want in fired:
        good = got == want
        ok += good
        print("  %-24s got %3d want %3d  %s" % (name, got, want, "OK" if good else "FAIL"))
    print("  commissioning: %d pass + %d fail = %d of %d"
          % (ok, len(fired) - ok, len(fired), len(fired)))
    return ok == len(fired)


def main():
    print("=== commissioning the corruption probe (both directions) ===")
    if not commission():
        print("PROBE IS NOT TRUSTWORTHY - refusing to report damage figures")
        return 2

    print("\n=== per-site damage, historical SITES list ===")
    rendered = missing = 0
    for name in HISTORICAL:
        p = None
        for cand in sorted(os.listdir(SRC)):
            if cand.startswith(name) and cand.endswith(".tiff"):
                p = os.path.join(SRC, cand)
                break
        if p is None:
            missing += 1
            print("  %-22s NEVER CUT - no master matches this prefix" % name)
            continue
        rendered += 1
        a = tifffile.imread(p)
        y = a[..., 1].astype(np.float32) if a.ndim == 3 else a.astype(np.float32)
        cx, cy = best_site(y)
        x0 = max(0, min(a.shape[1] - CROP, cx - CROP // 2))
        y0 = max(0, min(a.shape[0] - CROP, cy - CROP // 2))
        c = a[y0:y0 + CROP, x0:x0 + CROP]
        o, n = old_convert(c), new_convert(c)
        bad = int((o != n).sum())
        tot = c.size
        # what did the viewer actually see there?
        where = np.argwhere(o != n)
        print("  %-22s corrupted %6d / %7d px (%7.4f%%)  white->black"
              % (name, bad, tot, 100.0 * bad / tot))
        if bad:
            ys, xs = where[:, 0], where[:, 1]
            print("      %d distinct rows, %d distinct cols; true value there: %d..%d DN16"
                  % (len(set(ys.tolist())), len(set(xs.tolist())),
                     int(c[o != n].min()), int(c[o != n].max())))

    print("\n  partition: rendered %d + never-cut %d = %d of %d sites"
          % (rendered, missing, rendered + missing, len(HISTORICAL)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
