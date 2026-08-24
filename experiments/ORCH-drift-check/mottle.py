"""Is the mottled background red-channel noise?

HYPOTHESIS (ARGUED): the visible background mottle in bee-3-cpl is dominated
by the red channel. Red sits ~2.6x below green in raw counts (measured:
killexp.py, R p99.9 0.1104 vs G 0.2980) and then receives a white-balance
gain of 2631/1024 = 2.57x. Relative noise therefore scales by roughly
sqrt(2.6) * 2.57 / 1 ~ 4.1x green's, before demosaic.  If true, the mottle is
a CONSEQUENCE of the under-exposure, not a merge defect, and it predicts that
exposing to the right removes it.

MASK DISCIPLINE. This session produced three masks that each excluded the
artifact they were built to find (fact 1256).  The traps here:

  - Selecting flat regions by low SD would exclude mottle BY CONSTRUCTION,
    since mottle IS local variation.  So flatness is decided on the gradient
    of a HEAVILY SMOOTHED copy -- that measures scene structure, and smoothing
    has already removed the noise being measured.  Not circular.
  - A positive control is mandatory: a textured SUBJECT region must NOT come
    out red-dominated.  If red dominates everywhere, the mask is measuring
    something other than what I think.
  - Mask coverage is asserted before any number is believed.

MOTTLE vs GRAIN.  Mottle is low-frequency.  Pixel-iid noise falls as 1/r
under a box blur of radius r; mottle does not.  So each channel is measured
both raw and after a radius-8 box blur, and the ratio to the ideal 1/r
falloff is the mottle excess.

READ-ONLY.
"""
import os
import numpy as np
import tifffile
import cv2

SRC = r"C:\dev\strehl-out\M86-align\bee-3-ALIGNED.tif"
OUT = r"C:\dev\strehl-out\ORCH-mottle"
os.makedirs(OUT, exist_ok=True)

img = tifffile.imread(SRC)
if img.dtype == np.uint16:
    img = img.astype(np.float32) / 65535.0
print("image %s  range %.4f..%.4f  mean %.4f"
      % (img.shape, img.min(), img.max(), img.mean()))

lum = img.mean(axis=2)
print("luminance mean %.4f  -- %s"
      % (lum.mean(), "sRGB-encoded" if lum.mean() > 0.40 else "linear"))

# ---- flatness from the gradient of a smoothed copy, never from SD ----------
sm = cv2.GaussianBlur(lum, (0, 0), 12.0)
gx = cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=5)
gy = cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=5)
struct = cv2.GaussianBlur(np.hypot(gx, gy), (0, 0), 12.0)

bright = lum > np.percentile(lum, 60)          # background is the bright part
flat = (struct < np.percentile(struct, 20)) & bright
textured = struct > np.percentile(struct, 97)  # positive control

print()
print("flat-background mask: %.2f%% of frame" % (100 * flat.mean()))
print("textured control    : %.2f%% of frame" % (100 * textured.mean()))
assert flat.mean() > 0.03, "flat mask too small to trust: %.4f" % flat.mean()
assert textured.mean() > 0.005, "control mask too small: %.4f" % textured.mean()
print("flat mask mean lum %.4f   textured mask mean lum %.4f"
      % (lum[flat].mean(), lum[textured].mean()))

blur = [cv2.blur(img[:, :, c], (17, 17)) for c in range(3)]

print()
print("%-10s %9s %9s %9s %9s %9s" %
      ("channel", "mean", "sd", "sd/mean", "sd_blur8", "mottle"))
print("-" * 64)
res = {}
for ci, name in enumerate("RGB"):
    v = img[:, :, ci][flat]
    m = float(v.mean())
    sd = float(v.std())
    sdb = float(blur[ci][flat].std())
    ideal = sd / 17.0                      # iid noise under a 17x17 box mean
    mottle = sdb / max(ideal, 1e-9)
    res[name] = (m, sd, sd / m, sdb, mottle)
    print("%-10s %9.5f %9.5f %9.5f %9.5f %9.2fx"
          % (name, m, sd, sd / m, sdb, mottle))

print()
print("relative noise, red vs green: %.2fx" % (res["R"][2] / res["G"][2]))
print("relative noise, blue vs green: %.2fx" % (res["B"][2] / res["G"][2]))
print("mottle excess over iid, red   : %.2fx" % res["R"][4])
print("mottle excess over iid, green : %.2fx" % res["G"][4])

print()
print("POSITIVE CONTROL -- textured subject region")
print("%-10s %9s %9s %9s" % ("channel", "mean", "sd", "sd/mean"))
print("-" * 42)
ctl = {}
for ci, name in enumerate("RGB"):
    v = img[:, :, ci][textured]
    m, sd = float(v.mean()), float(v.std())
    ctl[name] = sd / m
    print("%-10s %9.5f %9.5f %9.5f" % (name, m, sd, sd / m))
print()
print("control red/green ratio: %.2fx  (flat-region ratio was %.2fx)"
      % (ctl["R"] / ctl["G"], res["R"][2] / res["G"][2]))
print("If the flat ratio is much larger than the control ratio, the")
print("red dominance is specific to the noise, not to the whole image.")

# ---- a picture of it ------------------------------------------------------
h, w = lum.shape
cy, cx = h // 2, w // 2
ys, xs = None, None
best = -1
for y in range(0, h - 400, 200):
    for x in range(0, w - 400, 200):
        sub = flat[y:y + 400, x:x + 400]
        if sub.mean() > best:
            best, ys, xs = sub.mean(), y, x
print()
print("most-flat 400px window at (%d,%d), %.0f%% masked" % (ys, xs, 100 * best))
crop = img[ys:ys + 400, xs:xs + 400].copy()
panels = []
for ci, name in enumerate("RGB"):
    ch = crop[:, :, ci]
    d = ch - cv2.blur(ch, (33, 33))
    d = np.clip(d * 12.0 + 0.5, 0, 1)
    panels.append((d * 255).astype(np.uint8))
strip = np.hstack([np.dstack([p] * 3) for p in panels])
cv2.imwrite(os.path.join(OUT, "mottle-per-channel.png"),
            cv2.cvtColor(strip, cv2.COLOR_RGB2BGR))
print("wrote mottle-per-channel.png  (R | G | B, high-pass, 12x gain)")
