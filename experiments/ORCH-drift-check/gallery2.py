"""Gallery v2: the tool does the exposure, so this shows what strehl EMITS.

v1 (gallery.py) applied its own numpy gain at target 0.92 on top of a render
that had no exposure at all. That was defensible when the tool could not expose
-- but it meant the owner was judging a Python post-process, not the program.
M100's exposure shipped at 925d03d, so the honest gallery now invokes

    strehl stack <dir> --out <tif> --srgb --auto-exposure

and post-processes NOTHING. Every pixel here comes out of the binary. The gain
printed below is the tool's own choice (linear-sRGB luma p99.9 -> 0.90), not
this script's.

Two deliberate differences from v1:

1.  NO numpy exposure. Applying 0.92 here on top of the tool's 0.90 would
    double-expose, and worse, would show an image the tool cannot produce.
2.  TWO crops per stack, not one. v1 cropped at the maximum of gradient
    energy, which on flowers-cpl selected sharp background fabric beside
    mushy petals -- the crop selector was measuring the thing it was supposed
    to be reporting on (discipline 666). A fixed centre crop is emitted
    alongside it so the detail crop cannot quietly flatter the result.

READ-ONLY on D:\\. All output goes to C:\\dev\\strehl-out\\ORCH-gallery2.
"""
import os
import re
import subprocess
import time
import glob
import numpy as np
import tifffile
from PIL import Image

ROOT = r"D:\personal\macro"
OLD = r"C:\dev\strehl-out\ORCH-gallery"
OUT = r"C:\dev\strehl-out\ORCH-gallery2"
EXE = r".cargo-target-orch\release\strehl.exe"
os.makedirs(OUT, exist_ok=True)

STACKS = [
    "bee-3-cpl",
    "lavendar-cpl",
    "flowers-cpl",
    "leaf-2-cpl",
    "flower-bud-alone-cpl",
    "tweezers-cpl",
    "coffee-bean",
]

EXP_RE = re.compile(r"exposure\s*:\s*([+-][\d.]+)\s*stops\s*\(gain\s*([\d.]+)x\)")


def stack_one(name):
    """Render with the tool's own auto-exposure. Returns (path, stops, gain)."""
    src = os.path.join(ROOT, name)
    dst = os.path.join(OUT, "%s-auto.tif" % name)
    n = len(glob.glob(os.path.join(src, "*.ARW")))
    if os.path.exists(dst):
        print("  [skip] %s already rendered" % name, flush=True)
        return dst, None, None
    print("  [stack] %s (%d frames) ..." % (name, n), flush=True)
    t0 = time.time()
    r = subprocess.run(
        [EXE, "stack", src, "--out", dst, "--srgb", "--auto-exposure"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print("  [FAIL] %s rc=%d" % (name, r.returncode))
        print((r.stderr or "")[-2000:])
        return None, None, None
    log = (r.stderr or "") + (r.stdout or "")
    m = EXP_RE.search(log)
    stops = float(m.group(1)) if m else None
    gain = float(m.group(2)) if m else None
    print("  [ok] %s in %.1f s, tool chose %s stops"
          % (name, time.time() - t0, stops), flush=True)
    return dst, stops, gain


def detail_peak(gray, box=900):
    """Coordinates of the most-detailed box. BIASED -- see module docstring."""
    s = 8
    g = gray[::s, ::s].astype(np.float32)
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    e = gx * gx + gy * gy
    r = max(box // (2 * s), 1)
    c = np.zeros((e.shape[0] + 1, e.shape[1] + 1))
    np.cumsum(np.cumsum(e.astype(np.float64), 0), 1, out=c[1:, 1:])
    H, W = e.shape
    y0 = np.clip(np.arange(H) - r, 0, H)
    y1 = np.clip(np.arange(H) + r, 0, H)
    x0 = np.clip(np.arange(W) - r, 0, W)
    x1 = np.clip(np.arange(W) + r, 0, W)
    tot = (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)]
           - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])
    iy, ix = np.unravel_index(int(np.argmax(tot)), tot.shape)
    return iy * s, ix * s


def crop(img, cy, cx, N=900):
    y = int(np.clip(cy - N // 2, 0, img.shape[0] - N))
    x = int(np.clip(cx - N // 2, 0, img.shape[1] - N))
    return img[y:y + N, x:x + N]


print("=" * 78)
print("RENDERING -- the tool exposes itself; this script applies no gain")
print("=" * 78)
rows = []
for n in STACKS:
    p, stops, gain = stack_one(n)
    if p:
        rows.append((n, p, stops, gain))

print()
print("=" * 78)
print("WHAT THE TOOL CHOSE")
print("=" * 78)
print("%-26s %9s %9s %10s %12s" % ("stack", "stops", "gain", "clipped", "MP"))
print("-" * 78)
thumbs = []
for n, p, stops, gain in rows:
    a = tifffile.imread(p)
    f = a.astype(np.float32) / 65535.0
    clipped = float((f.max(axis=2) >= 1.0).mean())
    mp = a.shape[0] * a.shape[1] / 1e6
    print("%-26s %9s %9s %9.4f%% %9.2f MP"
          % (n,
             ("%+.2f" % stops) if stops is not None else "(cached)",
             ("%.3fx" % gain) if gain is not None else "-",
             100 * clipped, mp), flush=True)

    prev = (f[::6, ::6] * 255).astype(np.uint8)
    Image.fromarray(prev).save(os.path.join(OUT, "%s-preview.png" % n))
    thumbs.append((n, prev))

    gray = f.mean(axis=2)
    cy, cx = detail_peak(gray)
    Image.fromarray((crop(f, cy, cx) * 255).astype(np.uint8)).save(
        os.path.join(OUT, "%s-100pct-detail.png" % n))
    Image.fromarray(
        (crop(f, f.shape[0] // 2, f.shape[1] // 2) * 255).astype(np.uint8)).save(
        os.path.join(OUT, "%s-100pct-centre.png" % n))

    # Before/after against v1's un-exposed render, when one exists. Labelled
    # honestly: that file was written by an EARLIER binary, so this shows the
    # combined effect of exposure and everything else that landed since.
    old = os.path.join(OLD, "%s-srgb.tif" % n)
    if os.path.exists(old):
        b = tifffile.imread(old).astype(np.float32) / 65535.0
        if b.shape[:2] == f.shape[:2]:
            sbs = np.concatenate(
                [(b[::6, ::6] * 255).astype(np.uint8), prev], axis=1)
            Image.fromarray(sbs).save(
                os.path.join(OUT, "%s-before-after.png" % n))

if thumbs:
    tw = min(t.shape[1] for _, t in thumbs)
    th = min(t.shape[0] for _, t in thumbs)
    cols = 3
    nrow = (len(thumbs) + cols - 1) // cols
    sheet = np.full((nrow * th + (nrow + 1) * 8, cols * tw + (cols + 1) * 8, 3),
                    18, np.uint8)
    for i, (n, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        y = 8 + r * (th + 8)
        x = 8 + c * (tw + 8)
        sheet[y:y + th, x:x + tw] = t[:th, :tw]
    Image.fromarray(sheet).save(os.path.join(OUT, "CONTACT-SHEET.png"))
    print()
    print("wrote CONTACT-SHEET.png (%d stacks)" % len(thumbs))
print("gallery in %s" % OUT)
