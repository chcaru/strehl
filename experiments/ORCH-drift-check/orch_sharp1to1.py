"""At 1:1, is the master sharper than the best frame that went into it?

This is the question a macro photographer actually asks, and no instrument in
this tree has answered it. The halo, blotch, chroma and banding detectors all
ask "is there an artifact"; every one now says no. None of them asks "is it
SHARP", which is the entire point of a focus stacker and the thing the owner
called horrible.

It is also the measurement that prices V-NYQUIST's finding on real data. The
alignment gather runs on half-resolution CFA planes and was measured to lose 51%
of true contrast at 0.20-0.30 cyc/output-px and 88% at 0.30-0.40 on a synthetic
broadband scene. If that carries to real captures, it shows up here: the master
should be sharper than any single frame at coarse scales (it selects the focused
one everywhere) but may be SOFTER at the finest scales, because the gather
filtered them before the election ever ran.

THE BASELINE IS THE FRAME THE SELECTOR WOULD HAVE CHOSEN (section 96). Comparing
a stack against the median input is a strawman that flatters it whenever
selection is working -- that error produced a published halo target that had to
be withdrawn. So: search every sampled source frame for the one sharpest AT THIS
SITE, and compare against that.

Alignment: the master is warped and cropped relative to any frame, so the crops
are registered by integer-shift search over a small range. Integer only -- a
sub-pixel resample would add blur to the very quantity being measured, which is
the one thing this must not do.
"""
import os
import sys
import glob

import numpy as np
import tifffile

from orch_contact import png_rgb, draw_text, LABEL_H

OUT_ROOT = r"C:\dev\strehl-out"
SRC_ROOT = r"D:\personal\macro"

CROP = 560          # rendered at 1:1
SEARCH = 48         # integer registration half-range, px


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1]
            + 0.114 * rgb[..., 2]).astype(np.float64)


def detail(y):
    """Gradient energy at two scales, reported separately.

    Reporting one number would hide the whole point: a stacker can win at
    coarse scale (it picked the focused frame) and lose at fine scale (the
    gather filtered it) in the SAME crop, and a single figure averages that
    interesting disagreement away.
    """
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def best_site(my, n=3):
    """Pick high-detail windows from the MASTER, spread apart."""
    h, w = my.shape
    step = CROP
    scores = []
    for y in range(step, h - CROP - step, step * 2):
        for x in range(step, w - CROP - step, step * 2):
            blk = my[y:y + CROP:4, x:x + CROP:4]
            scores.append((detail(blk)[0], y, x))
    scores.sort(reverse=True)
    picked = []
    for s, y, x in scores:
        if all(abs(y - py) > CROP * 2 or abs(x - px) > CROP * 2
               for _, py, px in picked):
            picked.append((s, y, x))
        if len(picked) == n:
            break
    return picked


def register(ref, mov):
    """Integer shift maximising normalised correlation. No resampling."""
    r = ref - ref.mean()
    best, at = -2.0, (0, 0)
    for dy in range(-SEARCH, SEARCH + 1, 2):
        for dx in range(-SEARCH, SEARCH + 1, 2):
            m = mov[SEARCH + dy:SEARCH + dy + r.shape[0],
                    SEARCH + dx:SEARCH + dx + r.shape[1]]
            if m.shape != r.shape:
                continue
            m = m - m.mean()
            d = np.sqrt(float(np.sum(r * r)) * float(np.sum(m * m)))
            if d <= 0:
                continue
            c = float(np.sum(r * m)) / d
            if c > best:
                best, at = c, (dy, dx)
    return at, best


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "bee-1-cpl"
    nsrc = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    import rawpy

    cand = [p for p in glob.glob(os.path.join(OUT_ROOT, "SHIP-V2", "*.tiff"))
            if os.path.basename(p).startswith(subject)]
    if not cand:
        raise SystemExit("no master for %s" % subject)
    m = tifffile.imread(cand[0])[..., :3].astype(np.float64)   # tifffile, not PIL
    my = luma(m)
    sites = best_site(my)
    print("master %s  sites %r" % (os.path.basename(cand[0]), [(y, x) for _, y, x in sites]))

    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    idx = np.linspace(0, len(arw) - 1, min(nsrc, len(arw))).astype(int)
    print("scanning %d of %d source frames for the sharpest AT EACH SITE\n"
          % (len(idx), len(arw)))

    srcs = []
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        srcs.append((os.path.basename(arw[i]), luma(s.astype(np.float64)), s))

    rows = []
    print("%-8s %-14s %10s %10s   %10s %10s   %s"
          % ("site", "best frame", "M_fine", "S_fine", "M_coarse", "S_coarse", "corr"))
    for si, (_, y, x) in enumerate(sites):
        ref = my[y:y + CROP, x:x + CROP]
        mf, mc = detail(ref)
        best = None
        for name, sy, s in srcs:
            if (y + CROP + SEARCH > sy.shape[0]) or (x + CROP + SEARCH > sy.shape[1]):
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape[0] < CROP + 2 * SEARCH or pad.shape[1] < CROP + 2 * SEARCH:
                continue
            (dy, dx), c = register(ref, pad)
            crop = sy[y + dy:y + dy + CROP, x + dx:x + dx + CROP]
            sf, sc = detail(crop)
            if best is None or sf > best[1]:
                best = (name, sf, sc, dy, dx, c, s)
        if best is None:
            print("site %d: no usable source crop" % si)
            continue
        name, sf, sc, dy, dx, c, s = best
        print("%-8d %-14s %10.2f %10.2f   %10.2f %10.2f   %.3f"
              % (si, name[:14], mf, sf, mc, sc, c))
        rows.append((si, y, x, m[y:y + CROP, x:x + CROP],
                     s[y + dy:y + dy + CROP, x + dx:x + dx + CROP],
                     name, mf, sf, mc, sc))

    if not rows:
        raise SystemExit("nothing to render")
    print("\nM_fine  = master gradient energy, 1 px scale")
    print("S_fine  = SHARPEST SOURCE FRAME at that site, 1 px scale")
    print("M/S at fine scale is the number V-NYQUIST's gather finding predicts")
    print("should be WEAK; at coarse scale the master should win outright.")
    for si, _, _, _, _, name, mf, sf, mc, sc in rows:
        print("  site %d   fine %.3fx   coarse %.3fx   (vs %s)"
              % (si, mf / sf if sf else 0, mc / sc if sc else 0, name))

    th = CROP + LABEL_H
    canvas = np.zeros((2 * th, len(rows) * CROP, 3), dtype=np.uint8)
    for cx, (si, _, _, mc_img, sc_img, name, mf, sf, _, _) in enumerate(rows):
        lo = float(np.percentile(luma(mc_img), 1))
        hi = float(np.percentile(luma(mc_img), 99))
        for ry, (img, tag) in enumerate((
                (mc_img, "MASTER  detail %.1f" % mf),
                (sc_img, "%s  %.1f" % (name[:11], sf)))):
            t = np.clip((img.astype(np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)
            y0, x0 = ry * th, cx * CROP
            canvas[y0:y0 + CROP, x0:x0 + CROP] = (t * 255).astype(np.uint8)
            draw_text(canvas, tag, y0 + CROP + 4, x0 + 4)

    out = os.path.join(OUT_ROOT, "ORCH-CONTACT", "sharp-1to1-%s.png" % subject)
    png_rgb(canvas, out)
    print("\nwrote %s  %dx%d" % (out, canvas.shape[1], canvas.shape[0]))
    print("ONE STATED WINDOW per column, taken from the master, applied to both")
    print("rows -- a per-tile stretch would make the pair incomparable (section 91).")


if __name__ == "__main__":
    main()
