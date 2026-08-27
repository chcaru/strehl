r"""Verify the two gauge facts this assignment rests on, rather than inherit them.

FACT 1 (claimed): --exposure reaches no pixel, because --srgb fits its black and
white points from the image's own luminance percentiles, so a gain applied before
the fit is divided straight back out. If true, the documented defence of "force a
common --exposure" is not a defence at all and every master/source ratio taken on
--srgb is a comparison across two different content-fitted curves.

FACT 2 (claimed): --linear-srgb does NOT imply --demosaic, while --srgb does. If
true, a linear render taken without --demosaic is half-resolution and every
spatial-frequency quantity silently changes meaning. VERIFY THE LATTICE FROM THE
FILE, never from the flags.
"""
import hashlib
import os
import numpy as np
import tifffile

D = r"C:\dev\strehl-out\V-GATHER\gauge"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest().upper()[:16]


print("FACT 1 -- does a commanded 64x exposure reach any pixel?")
a = tifffile.imread(os.path.join(D, "exp0.tiff"))
b = tifffile.imread(os.path.join(D, "exp6.tiff"))
print("  --exposure=0  %s  %s  sha %s" % (a.shape, a.dtype, sha(os.path.join(D, "exp0.tiff"))))
print("  --exposure=6  %s  %s  sha %s" % (b.shape, b.dtype, sha(os.path.join(D, "exp6.tiff"))))
if a.shape == b.shape:
    d = np.abs(a.astype(np.int64) - b.astype(np.int64))
    n = int((d > 0).sum())
    print("  differing samples %d of %d;  max |diff| %d DN" % (n, d.size, d.max()))
    am, bm = float(a.mean()), float(b.mean())
    print("  mean DN %.4f -> %.4f   delivered gain %.7f  (commanded %.1fx)"
          % (am, bm, (bm / am) if am else float("nan"), 2.0 ** 6))
    print("  VERDICT: %s" % ("the flag reaches NO pixel -- the documented defence "
                             "is inert" if n == 0 else
                             "the flag DOES change the file; claim refuted"))

print("\nFACT 2 -- lattice, read from the files themselves")
for tag in ("lin", "lindem", "exp0"):
    p = os.path.join(D, "%s.tiff" % tag)
    with tifffile.TiffFile(p) as t:
        pg = t.pages[0]
        w = pg.tags["ImageWidth"].value
        h = pg.tags["ImageLength"].value
        desc = pg.tags["ImageDescription"].value if "ImageDescription" in pg.tags else ""
    tone = "TONE FITTED" if "Tone rendering" in desc else "no tone stage"
    print("  %-8s %5d x %-5d  %s" % (tag, w, h, tone))

with tifffile.TiffFile(os.path.join(D, "lin.tiff")) as t:
    lw = t.pages[0].tags["ImageWidth"].value
with tifffile.TiffFile(os.path.join(D, "lindem.tiff")) as t:
    dw = t.pages[0].tags["ImageWidth"].value
print("  VERDICT: --linear-srgb alone is %s the demosaiced lattice (%d vs %d px wide)."
      % ("HALF" if dw == 2 * lw else "NOT half", lw, dw))
print("  A spatial statistic computed on the narrow one is on a different Nyquist.")
