"""Does per-frame brightness variation print mottle into a selection merge?

This does NOT try to reproduce strehl's election.  It tests the MECHANISM on
real pixel data: if frames differ in brightness and pixels select among them,
does the selected image carry a low-frequency brightness artifact, and does
per-frame normalisation remove it?

That question is answerable with any reasonable focus measure, because the
mechanism is about the brightness of the winning frame, not about which frame
in particular wins.

ARMS (identical code path, one difference):
  A. select on raw frames, merge by selection
  B. divide every frame by its own ROI mean first, then select and merge

REGISTERED BEFORE RUNNING:
  - If the mechanism is real, arm B's mid-band SD in the FLAT ROI must be
    materially lower than arm A's.  I register "materially" as >= 20%.
  - CONTROL 1 (null): if instead I normalise every frame by the SAME constant
    (the grand mean), nothing about relative brightness changes, so the
    mid-band SD must be unchanged to within 1%.  This proves the effect comes
    from the per-frame variation and not from the act of dividing.
  - CONTROL 2 (specificity): in a TEXTURED ROI the election tracks real
    signal, so normalisation should change the result far less.  If it helps
    equally everywhere, the mechanism as stated is wrong.
  - CONTROL 3 (positive): planting an exaggerated brightness ramp across the
    frames must INCREASE arm A's mid-band SD.  If it does not, the instrument
    cannot see the effect it is looking for and no verdict is valid.
"""
import os
import numpy as np

D = r"C:\dev\strehl-out\M93-out"
OUT = r"C:\dev\strehl-out\ORCH-mottle"
os.makedirs(OUT, exist_ok=True)

crops = np.load(os.path.join(D, "m93_crops.npy"), mmap_mode="r")
NF, NR, H, W = crops.shape

print("=" * 72)
print("Is the crop data CFA-mosaiced?")
print("=" * 72)
a = np.asarray(crops[150, 0], np.float64)
for lbl, sub in (("(0,0)", a[0::2, 0::2]), ("(0,1)", a[0::2, 1::2]),
                 ("(1,0)", a[1::2, 0::2]), ("(1,1)", a[1::2, 1::2])):
    print("  parity %s mean %9.2f" % (lbl, sub.mean()))
sp = [a[0::2, 0::2].mean(), a[0::2, 1::2].mean(),
      a[1::2, 0::2].mean(), a[1::2, 1::2].mean()]
spread = (max(sp) - min(sp)) / np.mean(sp)
CFA = spread > 0.10
print("  parity spread %.1f%%  ->  %s"
      % (100 * spread, "CFA-MOSAICED" if CFA else "not mosaiced"))
print("  (a mosaiced crop must be handled per-parity or the Bayer pattern")
print("   dominates every gradient measurement)")


def prep(k, plane):
    """One frame of one ROI, reduced to a single non-mosaiced plane."""
    x = np.asarray(crops[k, plane], np.float32)
    if CFA:
        x = 0.5 * (x[0::2, 0::2] + x[1::2, 1::2])   # the two green sites
    return x


h2, w2 = prep(0, 0).shape
print("  working plane is %dx%d" % (h2, w2))


def focus(x):
    gx = np.zeros_like(x)
    gy = np.zeros_like(x)
    gx[:, 1:-1] = x[:, 2:] - x[:, :-2]
    gy[1:-1, :] = x[2:, :] - x[:-2, :]
    e = gx * gx + gy * gy
    c = np.cumsum(np.cumsum(e.astype(np.float64), 0), 1)
    pad = np.zeros((h2 + 1, w2 + 1))
    pad[1:, 1:] = c
    r = 8
    y0 = np.clip(np.arange(h2) - r, 0, h2)
    y1 = np.clip(np.arange(h2) + r + 1, 0, h2)
    x0 = np.clip(np.arange(w2) - r, 0, w2)
    x1 = np.clip(np.arange(w2) + r + 1, 0, w2)
    return (pad[np.ix_(y1, x1)] - pad[np.ix_(y0, x1)]
            - pad[np.ix_(y1, x0)] + pad[np.ix_(y0, x0)]).astype(np.float32)


def box(x, n):
    c = np.cumsum(np.cumsum(x.astype(np.float64), 0), 1)
    pad = np.zeros((h2 + 1, w2 + 1))
    pad[1:, 1:] = c
    r = n // 2
    y0 = np.clip(np.arange(h2) - r, 0, h2)
    y1 = np.clip(np.arange(h2) + r + 1, 0, h2)
    x0 = np.clip(np.arange(w2) - r, 0, w2)
    x1 = np.clip(np.arange(w2) + r + 1, 0, w2)
    cnt = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float64)
    s = (pad[np.ix_(y1, x1)] - pad[np.ix_(y0, x1)]
         - pad[np.ix_(y1, x0)] + pad[np.ix_(y0, x0)])
    return (s / cnt).astype(np.float32)


def run(plane, mode, ramp=0.0):
    """mode: 'raw' | 'perframe' | 'constant'"""
    frames = [prep(k, plane) for k in range(NF)]
    if ramp:
        frames = [f * (1.0 + ramp * (k / (NF - 1.0) - 0.5))
                  for k, f in enumerate(frames)]
    lv = np.array([float(f.mean()) for f in frames])
    if mode == "perframe":
        frames = [f / lv[k] for k, f in enumerate(frames)]
    elif mode == "constant":
        g = float(lv.mean())
        frames = [f / g for f in frames]
    best = np.full((h2, w2), -1e30, np.float32)
    arg = np.zeros((h2, w2), np.int32)
    for k, f in enumerate(frames):
        s = focus(f)
        m = s > best
        best[m] = s[m]
        arg[m] = k
    st = np.stack(frames, 0)
    merged = np.take_along_axis(st, arg[None], 0)[0]
    mid = box(merged, 5) - box(merged, 33)
    return lv, arg, merged, float(mid.std()) / float(merged.mean())


names = ["ROI-FLAT", "ROI-HIGHDRIFT", "ROI-LOWDRIFT", "ROI-MIDDRIFT"]
print()
print("=" * 72)
print("Per-frame brightness of each ROI, and the mid-band SD of a selection merge")
print("=" * 72)
print("%-8s %11s %11s %11s %11s %11s"
      % ("plane", "L drift", "A raw", "B perframe", "C constant", "B vs A"))
print("-" * 72)
results = {}
for p in range(NR):
    lvA, argA, mA, sA = run(p, "raw")
    _, _, _, sB = run(p, "perframe")
    _, _, _, sC = run(p, "constant")
    drift = lvA.max() / lvA.min()
    results[p] = (drift, sA, sB, sC, argA)
    print("%-8d %10.4fx %11.6f %11.6f %11.6f %10.1f%%"
          % (p, drift, sA, sB, sC, 100 * (sB / sA - 1)))

print()
print("CONTROL 1 (null): 'C constant' must equal 'A raw' to within 1%")
for p in range(NR):
    d, sA, sB, sC, _ = results[p]
    rel = abs(sC / sA - 1)
    flag = "OK" if rel < 0.01 else "**FAIL**"
    print("  plane %d: %.4f%% difference  %s" % (p, 100 * rel, flag))

print()
print("CONTROL 3 (positive): plant a 40% brightness ramp across the frames.")
print("Arm A's mid-band SD must RISE.")
for p in range(NR):
    _, _, _, s0 = run(p, "raw")
    _, _, _, s1 = run(p, "raw", ramp=0.40)
    print("  plane %d: %.6f -> %.6f  (%+.1f%%)  %s"
          % (p, s0, s1, 100 * (s1 / s0 - 1),
             "OK" if s1 > s0 * 1.02 else "**INSTRUMENT BLIND**"))
