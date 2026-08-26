"""Prove the Part 3 crop path works before the sweep finishes.

Reads one delivered master, asserts its dtype and geometry, cuts a 1:1 crop and
writes it through the same PNG writer the real sheets use.  If the crop tool is
going to fail on a 198 MB uint16 TIFF or on the .tiff-not-.tif extension, it
should fail here and not after the sweep.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crops as X

name = "flat-on-ruler-cpl"
a, meta = X.load_master(name)
print("path      :", meta["path"])
print("shape     :", meta["shape"], meta["dtype"])
print("sha256    :", meta["sha256_first_1MiB"], "(first 1 MiB)")
print("descr     :", str(meta["description"])[:200])
assert a.dtype == np.uint16
h, w = a.shape[:2]
print(f"master {h}x{w}; plane is 2344x3514, so plane*2 = 4688x7028 "
      f"-> master is {w - 7028} columns wider than the visible RAW area")

img, y0, x0 = X.crop_at(a, h // 2, w // 2)
print("crop      :", img.shape, "at", (y0, x0), "dtype", img.dtype)
assert img.shape == (X.CROP, X.CROP, 3)
qy, qx = X.quiet_site(a)
print("quiet site:", (qy, qx))
p = os.path.join(X.OUT, "crops", "_smoke.png")
os.makedirs(os.path.dirname(p), exist_ok=True)
X._write_png(p, X.to8(img))
print("wrote     :", p, os.path.getsize(p), "bytes")

sh = X.sheet([(X.to8(img), "SMOKE PANEL 1 1.23PX"), (X.to8(img), "CONTROL")],
             f"{name} SMOKE 1:1 NO RESAMPLING")
p2 = os.path.join(X.OUT, "crops", "_smoke_sheet.png")
X._write_png(p2, sh)
print("wrote     :", p2, sh.shape, os.path.getsize(p2), "bytes")
print("OK")
