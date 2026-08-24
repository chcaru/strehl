"""mottle.py measured the wrong thing. This measures noise locally, and proves
the instrument on synthetic data before touching a photograph.

WHAT WENT WRONG. mottle.py pooled `img[flat]` across the entire 7032x4688
frame, so its SD was dominated by the background's frame-wide brightness
gradient, not by local noise. The tell was that a 17x17 box blur left the SD
unchanged (mottle "17.02x" in all three channels, where 17.02 is just the box
size) -- a blur that removes nothing was removing nothing because there was no
pixel-scale content in the measurement at all.

THE FIX. Subtract a local mean first. Everything below is measured on
residuals, so no scene structure coarser than the window can enter.

THE PLACEBO. A synthetic flat field plus known iid Gaussian noise is pushed
through the identical code path. It MUST report mottle 1.0x and recover the
planted sigma. If it does not, no number from the photograph is believed.
"""
import os
import numpy as np
import tifffile
import cv2

SRC = r"C:\dev\strehl-out\M86-align\bee-3-ALIGNED.tif"
RAWDIR = r"D:\personal\macro\bee-3-cpl"
OUT = r"C:\dev\strehl-out\ORCH-mottle"
os.makedirs(OUT, exist_ok=True)

FINE, COARSE = 5, 33


def bands(a):
    """Return (fine residual, mid-frequency band)."""
    f = cv2.blur(a, (FINE, FINE))
    c = cv2.blur(a, (COARSE, COARSE))
    return a - f, f - c


def analyse(a, mask, label):
    fine, mid = bands(a)
    sd_f = float(fine[mask].std())
    sd_m = float(mid[mask].std())
    # iid noise of per-pixel sigma s gives fine-band sd s*sqrt(1-1/FINE^2)
    # and mid-band sd s*sqrt(1/FINE^2 - 1/COARSE^2).
    sigma = sd_f / np.sqrt(1.0 - 1.0 / FINE ** 2)
    pred_mid = sigma * np.sqrt(1.0 / FINE ** 2 - 1.0 / COARSE ** 2)
    return sigma, sd_m, sd_m / max(pred_mid, 1e-12), label


print("=" * 70)
print("PLACEBO -- synthetic flat field + planted iid noise")
print("=" * 70)
rng = np.random.default_rng(7)
for planted in (0.002, 0.010, 0.030):
    synth = np.full((1200, 1600), 0.55, np.float32)
    synth += rng.normal(0, planted, synth.shape).astype(np.float32)
    m = np.ones(synth.shape, bool)
    sig, sd_m, ratio, _ = analyse(synth, m, "synth")
    print("  planted sigma %.4f -> recovered %.4f (%.1f%% err), mottle %.3fx"
          % (planted, sig, 100 * abs(sig - planted) / planted, ratio))
    assert abs(sig - planted) / planted < 0.05, "sigma recovery failed"
    assert abs(ratio - 1.0) < 0.05, "mottle on pure iid noise is not 1.0"

print("  + a planted LOW-FREQUENCY blob must raise mottle above 1.0:")
synth = np.full((1200, 1600), 0.55, np.float32)
synth += rng.normal(0, 0.010, synth.shape).astype(np.float32)
blob = rng.normal(0, 1.0, (1200, 1600)).astype(np.float32)
blob = cv2.GaussianBlur(blob, (0, 0), 6.0)
blob *= 0.010 / blob.std()
sig, sd_m, ratio, _ = analyse(synth + blob, np.ones(synth.shape, bool), "s")
print("    with sigma-6 blob of equal power: mottle %.2fx" % ratio)
assert ratio > 2.0, "instrument cannot see planted low-frequency structure"
print("  PLACEBO PASSED -- the instrument is quiet on iid and loud on mottle")

print()
print("=" * 70)
print("THE PHOTOGRAPH -- merged bee-3-cpl")
print("=" * 70)
img = tifffile.imread(SRC).astype(np.float32) / 65535.0
lum = img.mean(axis=2)

sm = cv2.GaussianBlur(lum, (0, 0), 12.0)
struct = cv2.GaussianBlur(
    np.hypot(cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=5),
             cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=5)), (0, 0), 12.0)
flat = (struct < np.percentile(struct, 20)) & (lum > np.percentile(lum, 60))
textured = struct > np.percentile(struct, 97)
print("flat mask %.1f%%   textured control %.1f%%"
      % (100 * flat.mean(), 100 * textured.mean()))
assert flat.mean() > 0.03 and textured.mean() > 0.005

print()
print("%-8s %10s %10s %10s %10s" % ("chan", "mean", "sigma", "sigma/mean", "mottle"))
print("-" * 52)
rel = {}
for ci, name in enumerate("RGB"):
    sig, sd_m, ratio, _ = analyse(img[:, :, ci], flat, name)
    m = float(img[:, :, ci][flat].mean())
    rel[name] = (sig / m, ratio)
    print("%-8s %10.5f %10.5f %10.5f %9.2fx" % (name, m, sig, sig / m, ratio))

print()
print("relative noise  R/G %.2fx   B/G %.2fx"
      % (rel["R"][0] / rel["G"][0], rel["B"][0] / rel["G"][0]))
print("mottle          R %.2fx  G %.2fx  B %.2fx"
      % (rel["R"][1], rel["G"][1], rel["B"][1]))

print()
print("SINGLE FRAME for comparison (what one exposure looks like)")
import rawpy
import glob
f = sorted(glob.glob(os.path.join(RAWDIR, "*.ARW")))[150]
with rawpy.imread(f) as r:
    one = r.postprocess(output_bps=16, no_auto_bright=True,
                        gamma=(1, 1), use_camera_wb=True)
one = one.astype(np.float32) / 65535.0
if one.shape[:2] != img.shape[:2]:
    fl2 = cv2.resize(flat.astype(np.uint8), (one.shape[1], one.shape[0]),
                     interpolation=cv2.INTER_NEAREST).astype(bool)
else:
    fl2 = flat
print("%-8s %10s %10s %10s %10s" % ("chan", "mean", "sigma", "sigma/mean", "mottle"))
print("-" * 52)
one_rel = {}
for ci, name in enumerate("RGB"):
    sig, sd_m, ratio, _ = analyse(one[:, :, ci], fl2, name)
    m = float(one[:, :, ci][fl2].mean())
    one_rel[name] = sig / m
    print("%-8s %10.5f %10.5f %10.5f %9.2fx" % (name, m, sig, sig / m, ratio))

print()
print("NOISE REDUCTION merged vs single frame, per channel:")
for name in "RGB":
    print("  %s  %.3fx" % (name, rel[name][0] / one_rel[name]))
print()
print("299 frames perfectly averaged would give 1/sqrt(299) = %.4fx"
      % (1 / np.sqrt(299)))
