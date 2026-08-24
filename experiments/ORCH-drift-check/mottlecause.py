"""Is the background mottle the photometric drift, printed through the
election map?

CHAIN OF REASONING (each link measured, cited):
  - fact 1254: background level falls 0.2284 -> 0.2059 across bee-3-cpl's 299
    frames, a ratio of 1.1091.  The frames are not the same brightness.
  - mottle2.py: the merged background's fine noise is 0.097-0.134x a single
    frame's, but its low-frequency excess is 8.5-10.6x versus 2.4-2.9x in a
    single frame.  Averaging killed the grain and left something behind.
  - If different background pixels elect different frames, and the frames
    differ in brightness, then the merged background inherits a picture of
    WHICH FRAME WON.  That is a low-frequency, blotchy field.  It is exactly
    what mottle looks like.

PREDICTION, registered before looking: the mid-frequency residual of the
merged background is correlated with the elected-frame index map.  Under the
null (mottle is sensor fixed-pattern, or demosaic, or anything not tied to
the election) there is no reason for any correlation at all.

FALSIFIERS, also registered first:
  - |r| < 0.15 in the flat background kills the hypothesis outright.
  - The sign must be NEGATIVE: later frames are dimmer (fact 1254), so a
    pixel electing a later frame should be darker.  A positive correlation
    of similar size would mean I have the mechanism backwards and would also
    count as a refutation of the stated model.
  - CONTROL: correlate the same residual against a SHUFFLED index map.  It
    must read ~0.  This catches a spurious correlation arising from the
    masks or from any shared spatial support.
  - CONTROL: the correlation must be far weaker in the TEXTURED region,
    where the election is driven by real focus signal rather than by noise.
"""
import os
import glob
import numpy as np
import tifffile
import cv2

MERGED = r"C:\dev\strehl-out\M86-align\bee-3-ALIGNED.tif"
IDXDIR = r"C:\dev\strehl-out\M94-election-margin\bee-3-cpl"
OUT = r"C:\dev\strehl-out\ORCH-mottle"
os.makedirs(OUT, exist_ok=True)

for f in sorted(glob.glob(os.path.join(IDXDIR, "*.tif"))):
    a = tifffile.imread(f)
    print("%-42s %-14s %s  %s..%s"
          % (os.path.basename(f), str(a.shape), a.dtype, a.min(), a.max()))

idx = tifffile.imread(os.path.join(IDXDIR, "elected-index.tif")).astype(np.float32)
img = tifffile.imread(MERGED).astype(np.float32) / 65535.0
print()
print("merged %s   index %s" % (str(img.shape), str(idx.shape)))

lum = img.mean(axis=2)
if idx.shape != lum.shape:
    print("resampling index map %s -> %s (nearest)" % (str(idx.shape), str(lum.shape)))
    idx = cv2.resize(idx, (lum.shape[1], lum.shape[0]),
                     interpolation=cv2.INTER_NEAREST)

FINE, COARSE = 5, 33
mid = cv2.blur(lum, (FINE, FINE)) - cv2.blur(lum, (COARSE, COARSE))
idx_mid = cv2.blur(idx, (FINE, FINE)) - cv2.blur(idx, (COARSE, COARSE))

sm = cv2.GaussianBlur(lum, (0, 0), 12.0)
struct = cv2.GaussianBlur(
    np.hypot(cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=5),
             cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=5)), (0, 0), 12.0)
flat = (struct < np.percentile(struct, 20)) & (lum > np.percentile(lum, 60))
textured = struct > np.percentile(struct, 97)
print("flat %.1f%%   textured %.1f%%" % (100 * flat.mean(), 100 * textured.mean()))
assert flat.mean() > 0.03 and textured.mean() > 0.005


def r(a, b, m):
    x, y = a[m].astype(np.float64), b[m].astype(np.float64)
    x -= x.mean()
    y -= y.mean()
    d = float(np.sqrt((x * x).sum() * (y * y).sum()))
    return float((x * y).sum() / d) if d > 0 else 0.0


print()
print("index map in flat background: mean %.1f  sd %.1f  range %.0f..%.0f"
      % (idx[flat].mean(), idx[flat].std(), idx[flat].min(), idx[flat].max()))

r_flat = r(mid, idx_mid, flat)
r_tex = r(mid, idx_mid, textured)

rng = np.random.default_rng(11)
sh = idx.copy().ravel()
rng.shuffle(sh)
sh = sh.reshape(idx.shape)
sh_mid = cv2.blur(sh, (FINE, FINE)) - cv2.blur(sh, (COARSE, COARSE))
r_shuf = r(mid, sh_mid, flat)

roll = np.roll(idx, (1500, 2500), axis=(0, 1))
roll_mid = cv2.blur(roll, (FINE, FINE)) - cv2.blur(roll, (COARSE, COARSE))
r_roll = r(mid, roll_mid, flat)

print()
print("=" * 66)
print("%-46s %8s" % ("correlation of mid-band luminance with...", "r"))
print("=" * 66)
print("%-46s %+8.4f   <- the test" % ("elected index, FLAT background", r_flat))
print("%-46s %+8.4f" % ("elected index, TEXTURED region", r_tex))
print("%-46s %+8.4f   <- must be ~0" % ("SHUFFLED index, flat background", r_shuf))
print("%-46s %+8.4f   <- must be ~0" % ("TRANSLATED index, flat background", r_roll))
print("=" * 66)
print()
if abs(r_flat) < 0.15:
    print("VERDICT: REFUTED. |r| = %.4f < 0.15." % abs(r_flat))
elif r_flat > 0:
    print("VERDICT: correlation is POSITIVE (r = %+.4f)." % r_flat)
    print("The registered model predicted NEGATIVE (later frames are dimmer).")
    print("The model as stated is WRONG even though something is correlated.")
else:
    print("VERDICT: SUPPORTED. r = %+.4f, negative as predicted." % r_flat)
    print("controls: shuffled %+.4f, translated %+.4f" % (r_shuf, r_roll))
    print("The background mottle carries a picture of which frame won.")
    print("Per-frame photometric normalisation (M99) should remove it.")

lo, hi = np.percentile(idx[flat], [1, 99])
print()
print("elected index spans %.0f..%.0f frames across the flat background"
      % (lo, hi))
print("fact 1254 measured a %.4fx brightness ratio end to end over 299 frames"
      % 1.1091)
span_pred = (hi - lo) / 299.0 * 0.1091
print("so an index spread of %.0f frames predicts a brightness spread of"
      % (hi - lo))
print("about %.4f, i.e. %.5f in absolute level at mean %.4f"
      % (span_pred, span_pred * lum[flat].mean(), lum[flat].mean()))
print("measured mid-band sd in flat background: %.5f" % mid[flat].std())

h, w = lum.shape
ys, xs, best = 0, 0, -1
for y in range(0, h - 500, 250):
    for x in range(0, w - 500, 250):
        s = flat[y:y + 500, x:x + 500].mean()
        if s > best:
            best, ys, xs = s, y, x
a = mid[ys:ys + 500, xs:xs + 500]
b = idx[ys:ys + 500, xs:xs + 500]
a = np.clip((a - a.mean()) * 60 + 0.5, 0, 1)
b = (b - b.min()) / max(b.max() - b.min(), 1e-9)
strip = np.hstack([(a * 255).astype(np.uint8), (b * 255).astype(np.uint8)])
cv2.imwrite(os.path.join(OUT, "mottle-vs-election.png"), strip)
print()
print("wrote mottle-vs-election.png (mid-band residual | elected index) at (%d,%d)"
      % (ys, xs))
