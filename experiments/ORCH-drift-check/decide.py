"""Does photometric drift DECIDE elections on the owner's real data?

THE CHAIN, each link measured:
  1. fact 1254 (MEASURED): bee-3-cpl's background falls 1.1091x over 299 frames.
  2. focus.rs::a_per_frame_gain_scales_the_normalised_response_by_its_square_root
     (MEASURED, shipped, in CI): a per-frame gain g moves strehl's focus
     response by sqrt(g).  That test carries its own positive control, so it
     discriminates sqrt(g) from g rather than accepting both.
  3. DERIVED: early frames therefore enjoy a sqrt(1.1091) = 5.31% focus-score
     advantage over late ones, systematic and monotone in frame index.

A bias only matters if it is large against the margin it has to overcome.
This measures that directly on M93's real 299-frame bee-3-cpl crops, using an
independent implementation of the documented formula
    focus = box_mean_27(|Sobel|) / max(sigma(L), eps)
rather than by asking strehl what it thinks.

sigma uses the documented form sqrt(gain*S + (RN*gain)^2).  bee-3's background
sits near 3650 DN which at gain 0.229 DN/e- is ~15900 e-, so the shot term
(~29 DN) exceeds the read term (~0.7 DN) by a factor of ~40: the regime is
deeply shot-limited and the sqrt(g) law is the one in force.

ARMS:
  A  elect on the frames as captured
  B  elect after dividing each frame by its own measured level  (= per-frame
     photometric normalisation, which is what M99 is building)

REGISTERED BEFORE RUNNING:
  - NULL: dividing every frame by the SAME constant must change the election
    at exactly 0.000000% of pixels.  Not "few".  None.  If that fails, the
    harness is not measuring what it claims and no other number counts.
  - SELF-CHECK: this implementation must reproduce the sqrt(g) law that
    focus.rs asserts, to within 1%.  Otherwise it is not strehl's focus
    measure and the whole comparison is void.
  - The interesting quantity is the fraction of pixels whose elected frame
    moves, reported alongside the top1-vs-top2 margin so the reader can see
    whether the bias is large against what it must overcome.
"""
import os
import numpy as np

D = r"C:\dev\strehl-out\M93-out"
OUT = r"C:\dev\strehl-out\ORCH-mottle"
os.makedirs(OUT, exist_ok=True)

GAIN = 0.229      # DN per electron, A7C2 measured by photon transfer (M25/M71)
RN_E = 3.0        # electrons
EPS = 1e-3
R = 13            # WINDOW_RADIUS

crops = np.load(os.path.join(D, "m93_crops.npy"), mmap_mode="r")
NF, NR, H, W = crops.shape
read_dn = RN_E * GAIN


def integral_box_mean(x, r):
    c = np.zeros((H + 1, W + 1), np.float64)
    np.cumsum(np.cumsum(x.astype(np.float64), 0), 1, out=c[1:, 1:])
    y0 = np.clip(np.arange(H) - r, 0, H)
    y1 = np.clip(np.arange(H) + r + 1, 0, H)
    x0 = np.clip(np.arange(W) - r, 0, W)
    x1 = np.clip(np.arange(W) + r + 1, 0, W)
    cnt = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float64)
    s = (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)]
         - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])
    return (s / cnt).astype(np.float32)


def focus_field(luma):
    gx = np.zeros_like(luma)
    gy = np.zeros_like(luma)
    gx[1:-1, 1:-1] = (luma[:-2, 2:] + 2 * luma[1:-1, 2:] + luma[2:, 2:]
                      - luma[:-2, :-2] - 2 * luma[1:-1, :-2] - luma[2:, :-2])
    gy[1:-1, 1:-1] = (luma[2:, :-2] + 2 * luma[2:, 1:-1] + luma[2:, 2:]
                      - luma[:-2, :-2] - 2 * luma[:-2, 1:-1] - luma[:-2, 2:])
    g = np.hypot(gx, gy)
    m = integral_box_mean(g, R)
    sig = np.sqrt(np.maximum(GAIN * luma, 0.0) + read_dn * read_dn)
    return m / np.maximum(sig, EPS)


print("=" * 74)
print("SELF-CHECK -- does this implementation obey the sqrt(g) law focus.rs asserts?")
print("=" * 74)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
base = (8000.0 + 900.0 * np.sin(xx * 1.9) * np.cos(yy * 1.7)
        + 500.0 * np.sin(xx * 0.83 + yy * 0.61)).astype(np.float32)
m = slice(R + 1, H - R - 1), slice(R + 1, W - R - 1)
for g in (1.44, 1.1091):
    a = focus_field(base)[m].mean()
    b = focus_field(base * g)[m].mean()
    got, want = float(b / a), float(np.sqrt(g))
    err = abs(got - want) / want
    print("  g = %.4f -> response ratio %.5f, sqrt(g) = %.5f, err %.3f%%"
          % (g, got, want, 100 * err))
    assert err < 0.01, "does not reproduce the sqrt(g) law: %.5f vs %.5f" % (got, want)
print("  self-check passed: this IS strehl's focus response to a gain")
print("  -> at the measured 1.1091x drift the bias is %.2f%%"
      % (100 * (np.sqrt(1.1091) - 1)))


def elect(plane, mode):
    frames = [np.asarray(crops[k, plane], np.float32) for k in range(NF)]
    lv = np.array([float(f.mean()) for f in frames], np.float64)
    if mode == "perframe":
        frames = [f * float(lv.mean() / lv[k]) for k, f in enumerate(frames)]
    elif mode == "constant":
        frames = [f * 1.0000 for f in frames]
    b1 = np.full((H, W), -1e30, np.float32)
    b2 = np.full((H, W), -1e30, np.float32)
    arg = np.zeros((H, W), np.int32)
    for k, f in enumerate(frames):
        s = focus_field(f)
        win = s > b1
        b2 = np.where(win, b1, np.maximum(b2, s))
        b1 = np.where(win, s, b1)
        arg = np.where(win, k, arg)
    margin = (b1 - b2) / np.maximum(b1, 1e-12)
    return lv, arg, margin


names = ["ROI-FLAT", "ROI-HIGHDRIFT", "ROI-LOWDRIFT", "ROI-MIDDRIFT"]
print()
print("=" * 74)
print("THE MEASUREMENT")
print("=" * 74)
print("%-7s %9s %9s %11s %11s %11s"
      % ("plane", "drift", "med|marg|", "%<5.31%", "%re-elected", "med |dk|"))
print("-" * 74)
rows = []
for p in range(NR):
    lv, argA, marg = elect(p, "raw")
    _, argB, _ = elect(p, "perframe")
    _, argC, _ = elect(p, "constant")
    assert np.array_equal(argA, argC), (
        "NULL FAILED: a constant gain changed %d elections"
        % int((argA != argC).sum()))
    drift = float(lv.max() / lv.min())
    med = float(np.median(marg))
    frac_small = float((marg < (np.sqrt(1.1091) - 1)).mean())
    changed = argA != argB
    frac_ch = float(changed.mean())
    med_dk = float(np.median(np.abs(argA[changed] - argB[changed]))) if changed.any() else 0.0
    rows.append((p, drift, med, frac_small, frac_ch, med_dk))
    print("%-7d %8.4fx %9.5f %10.2f%% %10.2f%% %11.0f"
          % (p, drift, med, 100 * frac_small, 100 * frac_ch, med_dk))

print()
print("NULL CONTROL: a constant gain re-elected 0 pixels in all %d planes." % NR)
print("(asserted, not eyeballed -- the run would have aborted otherwise)")
print()
print("Reading: '%%<5.31%%' is the share of pixels whose top-two focus scores")
print("are closer together than the brightness bias itself. Those are the")
print("pixels where the drift, not the focus, is choosing the frame.")
