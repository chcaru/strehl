"""M114 R9 -- does the correction generalise off bee-3-cpl?

Everything M114 and M107 measured is one stack (bee-3-cpl, f/5.6), which is
also one of the two stacks the profile was FITTED on.  That is the weakest
possible generalisation evidence.  109MSDCF is 22 frames, shot at f/11 on the
same optical train, and was NOT in the fit.

Bars, registered before running:
  G1  the render must succeed in both arms (exit 0) and the two arms must
      DIFFER (a null here would mean the correction silently did nothing on a
      stack outside the fit set).
  G2  high-passed mean |R-Y| near edges must FALL.  Red-control: the same
      statistic computed with the arms SWAPPED must RISE by the mirror amount.
  G3  high-passed mean |B-Y| near edges must move less than |R-Y| does.
  G4  fringe area (M107's W1 instrument, verbatim) must not RISE.
"""
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

EXE = Path(r"C:\dev\strehl-out\M114-ca-verify\cargo-target\release\strehl.exe")
DIR = Path(r"D:\personal\macro\109MSDCF")
OUT = Path(r"C:\dev\strehl-out\M114-ca-verify\r9")
KEY = "a7c2-fe100gm-2xtc-x4cpl"
OUT.mkdir(parents=True, exist_ok=True)
SIDE = OUT / "side.txt"


def run(args, extra):
    env = dict(os.environ)
    env.pop("STREHL_FIX_CA", None)
    env.update(extra)
    t0 = time.time()
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    return p.returncode, time.time() - t0, p.stdout + p.stderr


n = len(list(DIR.glob("*.ARW")))
print("frames=%d" % n, flush=True)
if not SIDE.exists():
    c, s, o = run([str(EXE), "align", str(DIR), "--out", str(SIDE),
                   "--reference", str(n // 2)], {})
    print("align EXIT=%d %.1fs" % (c, s), flush=True)
    if c != 0:
        print(o[-3000:])
        sys.exit("ALIGN FAILED")

arms = {}
for name, val in (("off", "0"), ("on", KEY)):
    tif = OUT / ("%s.tif" % name)
    if not tif.exists():
        c, s, o = run([str(EXE), "stack", str(DIR), "--srgb", "--auto-exposure",
                       "-o", str(tif)],
                      {"STREHL_WARPMAP": str(SIDE), "STREHL_FIX_CA": val})
        print("stack %-3s EXIT=%d %.1fs" % (name, c, s), flush=True)
        if c != 0:
            print(o[-3000:])
            sys.exit("STACK FAILED")
    arms[name] = tif

h = {k: hashlib.sha256(v.read_bytes()).hexdigest().upper() for k, v in arms.items()}
print("off sha=%s" % h["off"])
print("on  sha=%s" % h["on"])
g1 = h["off"] != h["on"]
print("G1 arms differ: %s -> %s" % (g1, "PASS" if g1 else "FAIL"))

a0 = tifffile.imread(arms["off"]).astype(np.float32) / np.float32(65535.0)
a1 = tifffile.imread(arms["on"]).astype(np.float32) / np.float32(65535.0)
print("shape=%s" % (a0.shape,))


def yof(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def hp(x, box=31):
    return x - ndimage.uniform_filter(x, box, mode="nearest")


y0, y1 = yof(a0), yof(a1)
gy, gx = np.gradient(y0)
mag = np.hypot(gx, gy)
edge = mag >= np.quantile(mag, 0.99)
near = ndimage.distance_transform_edt(~edge) <= 3
print("near-edge px = %d (%.2f%% of frame)" % (near.sum(), 100 * near.mean()))


def stat(a, y):
    return (np.abs(hp(a[..., 0] - y))[near].mean(),
            np.abs(hp(a[..., 2] - y))[near].mean())


r0, b0 = stat(a0, y0)
r1_, b1 = stat(a1, y1)
dr = 100 * (r1_ - r0) / r0
db = 100 * (b1 - b0) / b0
print("hp|R-Y| off=%.6f (%.1f DN)  on=%.6f (%.1f DN)  %+.2f%%"
      % (r0, r0 * 65535, r1_, r1_ * 65535, dr))
print("hp|B-Y| off=%.6f (%.1f DN)  on=%.6f (%.1f DN)  %+.2f%%"
      % (b0, b0 * 65535, b1, b1 * 65535, db))
print("G2 hp|R-Y| falls: %+.2f%% -> %s" % (dr, "PASS" if dr < 0 else "FAIL"))
# red-control: swap the arms; the same code must report the mirror sign.
drs = 100 * (r0 - r1_) / r1_
print("G2 CONTROL arms swapped: %+.2f%% -> %s"
      % (drs, "PASS (goes red)" if drs > 0 else "FAIL (instrument stuck)"))
print("G3 |B-Y| moves less than |R-Y|: |%.2f| < |%.2f| -> %s"
      % (db, dr, "PASS" if abs(db) < abs(dr) else "FAIL"))

# M107's W1 fringe-area instrument, verbatim thresholds.
def area(a, y):
    return int(((np.abs(a[..., 0] - y) > 0.06) & near).sum())


f0, f1 = area(a0, y0), area(a1, y1)
print("fringe area off=%d on=%d  %+.2f%%" % (f0, f1, 100 * (f1 - f0) / f0))
print("G4 area does not rise: %s" % ("PASS" if f1 <= f0 else "FAIL"))
