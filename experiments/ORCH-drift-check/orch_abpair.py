"""A/B two rendered masters at 1:1 on the site that most separates them.

Built to decide one thing: whether to flip the full-resolution gather on by
default. BUILD-RESAMP measured it FASTER (-40 to -97 ms/frame against a predicted
+549) and visibly sharper, but also measured the full-res arm reading ABOVE 1.0
at 0.10-0.15 cyc/px -- Malvar gradient overshoot, which is sharpening, not
recovered detail. My orch_halo.py then scored wrapped-text-1 at 0.1793 ON versus
0.1281/0.1403 OFF, i.e. MORE edge overshoot on the arm that is otherwise better.

The owner's loudest complaint about this product was halos. A number cannot
settle whether 0.05 step units of extra overshoot is visible ringing or a
sharper edge. Only the picture can.

SITE SELECTION IS THE TRAP AND IT IS HANDLED EXPLICITLY.

Choosing the site where the two arms differ most is choosing the site that
flatters whichever arm you already believe. So this renders THREE site classes
and labels them, and the verdict must hold on all three:

  MAXDIFF   where |A-B| is largest -- the adversarial site for both arms
  MAXEDGE   the strongest edge -- where ringing lives if it exists anywhere
  MEDIAN    a mid-detail site -- what the image mostly looks like

Display: ONE window per column, taken from the UNION of both arms, so the
contrast ratio between rows is preserved exactly. Clipped fraction is printed
per row and CONDITIONED ON -- a printed number that nothing tests is decoration,
which a verifier proved in one of my own tools tonight.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orch_contact import LABEL_H, draw_text, png_rgb   # noqa: E402

CROP = 480
GRID = 24
CLIP_MAX = 0.15
OUT = r"C:\dev\strehl-out\ORCH-CONTACT"


def luma(rgb):
    return (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
            + 0.0722 * rgb[:, :, 2])


def edge_energy(y):
    gy = np.abs(np.diff(y, axis=0)[:, :-1])
    gx = np.abs(np.diff(y, axis=1)[:-1, :])
    return float((gy + gx).mean())


def overshoot_frac(y):
    """REFUTED -- NOT A RINGING METRIC. Do not use it as one. See below.

    V-GATHER commissioned this statistic against planted defects and it fails
    in the worst possible way: it moves in the WRONG DIRECTION. Measured:

      - amplitude-invariant to SIX significant figures;
      - reads a planted 2 px ring at 40% of step as an IMPROVEMENT;
      - reads an unsharp mask as an IMPROVEMENT;
      - rises MONOTONICALLY with blur;
      - read the gather flip's own claimed de-aliasing as a REGRESSION.

    The mechanism is visible in the last two lines of the body. `d` is a
    high-pass, and the threshold is `3.0 * s` where `s = d.std()` -- derived
    from the same data. Scaling `y` by any constant scales `d` and `s`
    identically, so the ratio, and therefore the returned fraction, cannot
    move. **This measures the TAIL SHAPE of the high-pass distribution, not
    the amplitude of any excursion.** Sharpening lifts `s` faster than it
    lifts the tail, so the fraction falls; blur collapses `s` around a few
    surviving edges, so it rises.

    **Any conclusion resting on this number is unsupported**, including one of
    mine. `740e7056` cited "did not move (1.086%->1.053%, 1.744%->1.744%)" as
    evidence of no added ringing. On this statistic's own commissioning a
    1.086 -> 1.053 move is the signature of ADDED SHARPENING, so the commit
    read its most reassuring number backwards -- and read it that way BECAUSE
    it was reassuring.

    > A statistic that is amplitude-invariant to six significant figures is
    > not measuring an amplitude, and the comfort it gave was the tell.

    Retained, not deleted, so the numbers in the prior commit remain
    reproducible. For an actual ringing reading use V-GATHER's statistic C,
    which passes narrow-ring, unsharp, clean-edge and planted-improvement
    commissioning. Note also that statistic A (`orch_halo.py`) does not
    substitute: its BAND=(8,90) at DS=2 is 16-180 full-res px, while a
    Catmull-Rom / Malvar lobe lives at 1-4 px.
    """
    k = 5
    c = np.cumsum(np.pad(y, ((0, 0), (k, k)), mode="edge"), axis=1)
    h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
    b = (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)
    d = y - b
    s = d.std()
    return float((np.abs(d) > 3.0 * s).mean()) if s > 0 else 0.0


def sites(ya, yb):
    h, w = ya.shape
    cand = []
    for gy in range(GRID):
        for gx in range(GRID):
            y = int((h - CROP) * gy / max(1, GRID - 1))
            x = int((w - CROP) * gx / max(1, GRID - 1))
            a = ya[y:y + CROP, x:x + CROP]
            b = yb[y:y + CROP, x:x + CROP]
            if a.shape != (CROP, CROP) or b.shape != (CROP, CROP):
                continue
            cand.append((y, x, float(np.abs(a - b).mean()), edge_energy(a)))
    if not cand:
        raise SystemExit("no candidate sites")
    by_diff = sorted(cand, key=lambda t: -t[2])
    by_edge = sorted(cand, key=lambda t: -t[3])
    med = by_edge[len(by_edge) // 2]
    return [("MAXDIFF", by_diff[0]), ("MAXEDGE", by_edge[0]), ("MEDIAN", med)]


def main():
    if len(sys.argv) < 4:
        raise SystemExit("usage: orch_abpair.py A.tiff B.tiff tag [labelA labelB]")
    pa, pb, tag = sys.argv[1], sys.argv[2], sys.argv[3]
    la = sys.argv[4] if len(sys.argv) > 4 else "A"
    lb = sys.argv[5] if len(sys.argv) > 5 else "B"

    a = tifffile.imread(pa)[:, :, :3].astype(np.float32)
    b = tifffile.imread(pb)[:, :, :3].astype(np.float32)
    hh = min(a.shape[0], b.shape[0])
    ww = min(a.shape[1], b.shape[1])
    # Crop to a common size. NEVER resample to match: resampling adds blur to
    # the exact quantity being compared.
    a, b = a[:hh, :ww], b[:hh, :ww]
    ya, yb = luma(a), luma(b)
    print("%s  vs  %s   at %dx%d" % (la, lb, ww, hh))

    chosen = sites(ya, yb)
    th = CROP + LABEL_H
    canvas = np.zeros((2 * th, len(chosen) * CROP, 3), dtype=np.uint8)
    print("\n%-9s %14s %10s %10s   %10s %10s" %
          ("site", "(x,y)", la + " edge", lb + " edge", "REFUTED", "REFUTED"))
    rep = []
    for cx, (kind, (y, x, _d, _e)) in enumerate(chosen):
        ca, cb = a[y:y + CROP, x:x + CROP], b[y:y + CROP, x:x + CROP]
        wa, wb = ya[y:y + CROP, x:x + CROP], yb[y:y + CROP, x:x + CROP]
        both = np.concatenate([wa.ravel(), wb.ravel()])
        lo, hi = float(np.percentile(both, 1)), float(np.percentile(both, 99))
        ea, eb = edge_energy(wa), edge_energy(wb)
        ra, rb = overshoot_frac(wa), overshoot_frac(wb)
        print("%-9s %14s %10.2f %10.2f   %9.3f%% %9.3f%%"
              % (kind, "(%d,%d)" % (x, y), ea, eb, ra * 100, rb * 100))
        for ry, (img, lab) in enumerate(((ca, "%s  %s edge %.1f" % (kind, la, ea)),
                                         (cb, "%s  %s edge %.1f" % (kind, lb, eb)))):
            raw = (luma(img) - lo) / max(hi - lo, 1e-9)
            cf = float(((raw < 0) | (raw > 1)).mean())
            t = np.clip((img.astype(np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)
            y0, x0 = ry * th, cx * CROP
            canvas[y0:y0 + CROP, x0:x0 + CROP] = (t * 255).astype(np.uint8)
            draw_text(canvas, lab, y0 + CROP + 4, x0 + 4)
            rep.append((kind, lab.split()[1], cf))
        rep.append((kind, "_ratio", eb / ea if ea else 0.0))

    out = os.path.join(OUT, "abpair-%s.png" % tag)
    png_rgb(canvas, out)
    print("\nwrote %s  %dx%d" % (out, canvas.shape[1], canvas.shape[0]))

    bad = [r for r in rep if r[1] != "_ratio" and r[2] > CLIP_MAX]
    for kind, which, cf in rep:
        if which == "_ratio":
            continue
        print("  clip %-9s %-8s %6.2f%%%s"
              % (kind, which, cf * 100, "  <== SATURATED" if cf > CLIP_MAX else ""))
    if bad:
        print("*** %d row(s) saturated above %.0f%%: the pair is not fair there. ***"
              % (len(bad), CLIP_MAX * 100))
    else:
        print("No row saturates above %.0f%%; all three columns are fair pairs."
              % (CLIP_MAX * 100))
    print("\nedge = mean |grad|, higher is sharper OR ringier -- it cannot tell you")
    print("which. Read the PICTURE: real detail gains texture inside flat areas;")
    print("ringing gains a bright line hugging the dark side of every edge and")
    print("nothing elsewhere.")
    print("\n*** The two REFUTED columns are overshoot_frac and ARE NOT A RINGING")
    print("*** METRIC. V-GATHER commissioned them: amplitude-invariant to six")
    print("*** significant figures, rising with blur, scoring a planted 2px ring")
    print("*** AND an unsharp mask as IMPROVEMENTS. They move the wrong way. The")
    print("*** threshold is 3*sigma of the same high-pass it thresholds, so the")
    print("*** amplitude cancels and only tail SHAPE survives. Printed solely so")
    print("*** the numbers quoted in 740e7056 stay reproducible. Do not read them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
