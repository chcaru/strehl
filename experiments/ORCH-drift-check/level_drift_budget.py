"""Can inter-frame level drift account for the amplitude of the mosaic?

The mechanism on offer: different regions of the merge gather different frames,
the frames differ slightly in brightness, and those differences become the steps
between regions. M24 measured 2.88-11.70% peak-to-peak drift across four stacks,
so the mechanism is at least available.

This checks whether it is available AT THE RIGHT AMPLITUDE on the one stack
where the mosaic has been measured. If the frames agree to a fraction of a
percent over the same background window where the merge's mosaic swings several
percent, level drift cannot be the explanation and the mechanism is dead.

The comparison is held constant deliberately: the SAME window coordinates in
every frame and in the merge, one stack, one background region.

Reads only. Writes nothing. Never touches D:\\.
"""
import glob
import os

import numpy as np
import tifffile

M93 = r"C:\dev\strehl-out\M93-out"
X, Y, S = 2832, 400, 256


def lum(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s is %s, expected uint16" % (p, a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


frames = sorted(glob.glob(os.path.join(M93, "armF-f*.tif")))
print("single input frames found: %d" % len(frames))

ref = lum(frames[0])
H, W = ref.shape
# Several widely separated background windows, so the answer is not a property
# of the one window that happened to be looked at first.
WINDOWS = [(2832, 400), (400, 528), (1552, 1680), (656, 1552), (2704, 400), (400, 1040)]
WINDOWS = [(x, y) for x, y in WINDOWS if x + S <= W and y + S <= H]

stack = []
names = []
for p in frames:
    L = lum(p)
    if L.shape != ref.shape:
        print("  skip %s (geometry %s)" % (os.path.basename(p), L.shape))
        continue
    names.append(os.path.basename(p))
    stack.append([float(L[y : y + S, x : x + S].mean()) for x, y in WINDOWS])
stack = np.array(stack)
print("frames usable: %d over %d windows\n" % (len(names), len(WINDOWS)))

print("%-10s %10s %10s %12s %12s %12s" % ("window", "drift p2p", "drift sd", "gate0 swing",
                                          "gate4 swing", "drift/gate4"))
supply0, supply4 = [], []
g0 = lum(os.path.join(M93, "armM-gate0-binlin.tif"))
g4 = lum(os.path.join(M93, "armM4-gate4-binlin.tif"))
for i, (x, y) in enumerate(WINDOWS):
    ms = stack[:, i]
    p2p = (ms.max() - ms.min()) / ms.mean() * 100.0
    sdp = ms.std() / ms.mean() * 100.0
    w0 = g0[y : y + S, x : x + S]
    w4 = g4[y : y + S, x : x + S]
    a0 = w0.std() / w0.mean() * 100.0
    a4 = w4.std() / w4.mean() * 100.0
    supply0.append(p2p / a0 if a0 else np.nan)
    supply4.append(p2p / a4 if a4 else np.nan)
    print("%-10s %9.3f%% %9.3f%% %11.3f%% %11.3f%% %11.2fx"
          % ("%d,%d" % (x, y), p2p, sdp, a0, a4, p2p / a4 if a4 else np.nan))

print()
print("MEDIAN across %d windows: drift supplies %.0f%% of the gate0 swing and %.0f%% of the gate4 swing"
      % (len(WINDOWS), 100 * np.median(supply0), 100 * np.median(supply4)))

# Is the drift a smooth trend or frame-to-frame scatter? A smooth global trend
# is exactly what a per-frame gain fit removes; scatter is not.
idx = np.arange(len(names), dtype=float)
m0 = stack[:, 0]
fit = np.polyfit(idx, m0, 1)
resid = m0 - np.polyval(fit, idx)
print("drift shape at window %s: linear trend removes %.1f%% of the variance "
      "(residual sd %.3f%% of level)"
      % (WINDOWS[0], 100 * (1 - resid.var() / m0.var()), resid.std() / m0.mean() * 100.0))
print("  -> a smooth global trend is precisely what a fitted per-frame gain removes;")
print("     frame-to-frame scatter would not be.")

levels = [(names[i], float(stack[i, 0]), 0.0) for i in range(len(names))]
ms = stack[:, 0]
p2p = (ms.max() - ms.min()) / ms.mean() * 100.0
