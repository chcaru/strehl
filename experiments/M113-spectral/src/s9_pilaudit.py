"""M113 audit: did the fleet-wide PIL 16-bit-RGB defect touch any number I reported?

Every lateral-CA number I have published went through cs.load_tiff_u16(), which
DOES call PIL.Image.open(). Reading the source suggests PIL is used only for the
TIFF tags and the pixels come from a numpy memmap, but that is exactly the
argument ORCH warned against. Measure it instead: read the same files through
load_tiff_u16 and through tifffile and compare dtype, range and EXACT equality.
"""
import os, sys
import numpy as np
import tifffile

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
from c4_globalfit import cs                      # noqa: E402

FILES = [
    r"C:\dev\strehl-out\M113-ca\lin\bee-3-cpl-binned-off.tif",
    r"C:\dev\strehl-out\M113-ca\lin\bee-3-cpl-binned-on.tif",
    r"C:\dev\strehl-out\M113-spectral\arms\flat-on-ruler-cpl-binned-off.tif",
    r"C:\dev\strehl-out\M113-spectral\arms\leaf-2-cpl-binned-off.tif",
    r"C:\dev\strehl-out\M113-spectral\arms\bee-3-cpl-ref1frame.tif",
]

print("=" * 100)
print("A -- reproduce ORCH's defect on this machine, so the probe is known to be sensitive")
print("=" * 100)
from PIL import Image
tmp = r"C:\dev\strehl-out\M113-spectral\pilprobe.tif"
rng = np.random.default_rng(7)
truth = (rng.integers(0, 65536, size=(64, 96, 3))).astype(np.uint16)
tifffile.imwrite(tmp, truth)
via_pil = np.asarray(Image.open(tmp))
via_tf = tifffile.imread(tmp)
print("source        : %-8s levels=%d" % (truth.dtype, len(np.unique(truth))))
print("tifffile      : %-8s levels=%d  exact=%s" % (via_tf.dtype, len(np.unique(via_tf)),
                                                    np.array_equal(via_tf, truth)))
print("PIL.Image.open: %-8s levels=%d  mode=%s" % (via_pil.dtype, len(np.unique(via_pil)),
                                                   Image.open(tmp).mode))
sensitive = (via_pil.dtype == np.uint8)
print("PROBE IS SENSITIVE: %s  <- if False, the audit below proves nothing" % sensitive)
if not sensitive:
    sys.exit("probe could not reproduce the defect; audit aborted")

print("\n" + "=" * 100)
print("B -- the reader my numbers actually used, on the files my numbers actually used")
print("=" * 100)
bad = 0
for f in FILES:
    if not os.path.exists(f):
        print("  MISSING %s" % f); continue
    a, W, H = cs.load_tiff_u16(f)
    a = np.asarray(a)
    t = tifffile.imread(f)
    same = (a.dtype == t.dtype) and np.array_equal(a, t)
    lv_a, lv_t = len(np.unique(a[::16, ::16, :])), len(np.unique(t[::16, ::16, :]))
    print("  %-52s" % os.path.basename(f))
    print("      load_tiff_u16 : %-8s shape=%s min=%d max=%d levels(sub)=%d"
          % (a.dtype, a.shape, a.min(), a.max(), lv_a))
    print("      tifffile      : %-8s shape=%s min=%d max=%d levels(sub)=%d"
          % (t.dtype, t.shape, t.min(), t.max(), lv_t))
    print("      BYTE-IDENTICAL: %s" % same)
    if not same:
        bad += 1
    del a, t

print("\n" + "=" * 100)
print("VERDICT: %s" % ("ALL FILES IDENTICAL -- load_tiff_u16 is not affected; my numbers stand"
                       if bad == 0 else "%d FILE(S) DIFFER -- numbers are compromised" % bad))
print("=" * 100)
os.remove(tmp)