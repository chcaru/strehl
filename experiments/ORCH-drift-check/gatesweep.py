"""The gate continuum, on the owner's own photographs.

The owner's verdict was that the stacks look soft.  strehl has exactly one
knob -- `--gate` -- and its documented trade is that low is sharper and
noisier, high is cleaner and softer.  M92 measured the near-selector end as
sharper by 0.318-0.618 px on 66 of 70 ROIs; M85 measured facet sharpness
moving only 0.985x across a 61x change in frames averaged.  Those two
disagree, M98 is adjudicating, and DEFAULT_GATE does not move until it
reports.

This script does not adjudicate anything.  It renders the owner's own frames
at five points along the continuum so he can look at the trade himself, on
his own subject, at 100%.

Exposure-only correction, exactly as in gallery.py: a single global gain in
linear light, then the sRGB transfer curve.  No contrast curve, no
saturation, no sharpening, no noise reduction, no local adjustment -- any of
them would flatter the output and none of them is strehl's work.

READ-ONLY on D:\\.  All output goes to C:\\dev\\strehl-out\\ORCH-gate.
"""
import glob
import os
import re
import subprocess
import sys
import time

import numpy as np
import tifffile
from PIL import Image, ImageDraw

ROOT = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\ORCH-gate"
EXE = r".cargo-target-orch\release\strehl.exe"
GATES = [0.0, 1.0, 2.0, 4.0, 8.0]
STACKS = ["bee-3-cpl", "tweezers-cpl"]

TARGET = 0.92
CLIP_BUDGET = 0.005
os.makedirs(OUT, exist_ok=True)


def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def render(name, gate):
    """One render at one gate. Returns (path, mean_n_eff, seconds)."""
    dst = os.path.join(OUT, "%s-g%g.tif" % (name, gate))
    meta = dst + ".txt"
    if os.path.exists(dst) and os.path.exists(meta):
        return dst, open(meta).read().strip(), 0.0
    src = os.path.join(ROOT, name)
    t0 = time.time()
    r = subprocess.run(
        [EXE, "stack", src, "--out", dst, "--srgb", "--demosaic",
         "--gate", str(gate)],
        capture_output=True, text=True)
    dt = time.time() - t0
    if r.returncode != 0:
        print("  [FAIL] %s gate=%g rc=%d" % (name, gate, r.returncode))
        print((r.stdout or "")[-1500:])
        print((r.stderr or "")[-1500:])
        return None, None, dt
    blob = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"n_eff[^\n]*?([0-9]+\.[0-9]+)", blob)
    neff = m.group(1) if m else "?"
    with open(meta, "w") as fh:
        fh.write(neff)
    print("  [ok] %-14s gate=%-4g n_eff=%-8s %.1f s" % (name, gate, neff, dt),
          flush=True)
    return dst, neff, dt


def expose(img16):
    """Exposure only: one global gain in linear light. Returns (u8, gain)."""
    x = img16.astype(np.float32) / 65535.0
    lin = srgb_to_linear(x)
    p = np.percentile(lin, 99.9)
    gain = 1.0 if p <= 0 else TARGET / p
    while gain > 1.0:
        clipped = float(np.mean(lin * gain > 1.0))
        if clipped <= CLIP_BUDGET:
            break
        gain *= 0.95
    return (linear_to_srgb(lin * gain) * 255.0 + 0.5).astype(np.uint8), gain


def main():
    print("RENDERING %d stacks x %d gates" % (len(STACKS), len(GATES)))
    rows = []
    for name in STACKS:
        n = len(glob.glob(os.path.join(ROOT, name, "*.ARW")))
        print("%s (%d frames)" % (name, n), flush=True)
        for g in GATES:
            path, neff, dt = render(name, g)
            if path:
                rows.append((name, g, path, neff))

    # Build a 100% crop strip per stack, same crop across every gate.
    for name in STACKS:
        mine = [r for r in rows if r[0] == name]
        if not mine:
            continue
        tiles, labels = [], []
        cy = cx = None
        for _, g, path, neff in mine:
            a = tifffile.imread(path)
            if cy is None:
                # Pick the crop once, on the busiest 512x512 region of the
                # FIRST gate, then reuse those exact coordinates for every
                # other gate so the comparison is of the same pixels.
                lum = a[..., 1].astype(np.float32)
                h, w = lum.shape
                gy, gx = np.gradient(lum)
                e = np.abs(gy) + np.abs(gx)
                bs = 512
                best, cy, cx = -1.0, h // 2, w // 2
                for yy in range(bs, h - 2 * bs, bs):
                    for xx in range(bs, w - 2 * bs, bs):
                        s = float(e[yy:yy + bs, xx:xx + bs].mean())
                        if s > best:
                            best, cy, cx = s, yy, xx
                print("%s: crop at (%d,%d)" % (name, cy, cx))
            crop = a[cy:cy + 512, cx:cx + 512]
            u8, gain = expose(crop)
            tiles.append(u8)
            labels.append("gate %g   n_eff %s   gain %.2fx" % (g, neff, gain))

        pad = 28
        W = 512 * len(tiles) + 4 * (len(tiles) - 1)
        sheet = Image.new("RGB", (W, 512 + pad), (16, 16, 16))
        for i, (t, lab) in enumerate(zip(tiles, labels)):
            sheet.paste(Image.fromarray(t), (i * 516, pad))
            ImageDraw.Draw(sheet).text((i * 516 + 6, 8), lab, (235, 235, 235))
        p = os.path.join(OUT, "%s-GATE-STRIP.png" % name)
        sheet.save(p)
        print("wrote %s" % p)

    print("\n%-16s %-6s %-10s" % ("stack", "gate", "mean n_eff"))
    for name, g, _, neff in rows:
        print("%-16s %-6g %-10s" % (name, g, neff))


if __name__ == "__main__":
    sys.exit(main())
