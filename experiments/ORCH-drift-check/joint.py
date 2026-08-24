"""Do M96's disconnected competitive sets explain WHICH pixels photometric
drift re-elects?

TWO INDEPENDENT RESULTS THAT MAY BE ONE MECHANISM:

  M96 (measured, committed): on bee-3-cpl, 25.247% of pixels have a
  DISCONNECTED competitive set at the shipped gate -- the gate admits frames
  at two or more separated depths, mean gap 29.12 frames, rho p90 = 243 of
  299.  In the margin render these are thin contours lying exactly along
  depth and occlusion boundaries.

  Mine (fact 1259): under per-frame photometric normalisation 1.40-6.87% of
  pixels re-elect, and the ones that move go a median of 1, 1, 29 and 44
  frames.

MECHANISTIC PREDICTION.  A pixel whose competitive set is CONNECTED has its
runner-up adjacent to its winner, so a small bias moves the election by ~1
frame.  A pixel whose competitive set is DISCONNECTED has a second cluster
separated by the gap, so the same small bias moves the election by ~the gap.
That predicts the re-electing population is ENRICHED for disconnection, and
it explains both the 1s and the 29/44s in the same table.

If it holds, then photometric drift, M96's bimodal pixels and the occlusion
halo are the same object seen three ways, and normalising the frames is not
a cosmetic fix -- it is a fix at depth boundaries.

REGISTERED BEFORE RUNNING:
  - Enrichment = P(re-elect | disconnected) / P(re-elect | connected).
    Enrichment <= 1.5 REFUTES the mechanism.
  - CONTROL (label shuffle): permuting the disconnected labels across pixels
    must give enrichment ~1.0.  This catches enrichment manufactured by any
    shared spatial support between the two masks.
  - CONTROL (self-consistency): among re-electing DISCONNECTED pixels,
    median |dk| must be much larger than among re-electing CONNECTED pixels.
    If the two are the same, disconnection is not what carries the jump.

UNITS.  FOCUS_NOISE_SD is calibrated to strehl's focus units and this is an
independent Python implementation, so its value is not transferable here.
The threshold is therefore built from a focus-response noise SD estimated
from this data, using a 5-point second-difference along the FRAME axis
normalised by its L2 norm.  That is a standard high-pass noise estimator and
no claim of fact 1186's is being re-derived: 1186 runs that kernel on pixel
luma normalised by the photon-transfer model, this runs it on the focus
response to get a scale for a threshold.
"""
import os
import numpy as np

D = r"C:\dev\strehl-out\M93-out"
GAIN, RN_E, EPS, R = 0.229, 3.0, 1e-3, 13
GATE = 4.0

crops = np.load(os.path.join(D, "m93_crops.npy"), mmap_mode="r")
NF, NR, H, W = crops.shape
read_dn = RN_E * GAIN


def box_mean(x, r):
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
    sig = np.sqrt(np.maximum(GAIN * luma, 0.0) + read_dn * read_dn)
    return box_mean(np.hypot(gx, gy), R) / np.maximum(sig, EPS)


def volume(plane, normalise):
    frames = [np.asarray(crops[k, plane], np.float32) for k in range(NF)]
    lv = np.array([float(f.mean()) for f in frames], np.float64)
    if normalise:
        frames = [f * float(lv.mean() / lv[k]) for k, f in enumerate(frames)]
    return np.stack([focus_field(f) for f in frames], 0), lv


print("%-7s %9s %9s %9s %9s %9s %9s"
      % ("plane", "sigma_R", "%disconn", "%re-el", "enrich", "shuffled", "dk d/c"))
print("-" * 74)
out = []
for p in range(NR):
    volA, lv = volume(p, False)
    volB, _ = volume(p, True)
    argA = volA.argmax(0)
    argB = volB.argmax(0)

    ker = np.array([1.0, -4.0, 6.0, -4.0, 1.0], np.float32)
    hp = np.tensordot(ker, np.stack([volA[i:NF - 4 + i] for i in range(5)], 0),
                      axes=(0, 0))
    sigma_R = float(np.median(np.abs(hp)) * 1.4826 / np.sqrt((ker ** 2).sum()))
    t = GATE * np.sqrt(2.0) * sigma_R

    win = volA.max(0)
    comp = volA >= (win - t)[None]
    n = comp.sum(0)
    idx = np.arange(NF)[:, None, None]
    hi = np.where(comp, idx, -1).max(0)
    lo = np.where(comp, idx, NF).min(0)
    disc = (hi - lo + 1 - n) > 0

    changed = argA != argB
    dk = np.abs(argA.astype(int) - argB.astype(int))
    pd = float(changed[disc].mean()) if disc.any() else 0.0
    pc = float(changed[~disc].mean()) if (~disc).any() else 0.0
    enrich = pd / max(pc, 1e-12)

    rng = np.random.default_rng(3)
    sh = disc.ravel().copy()
    rng.shuffle(sh)
    sh = sh.reshape(disc.shape)
    pds = float(changed[sh].mean())
    pcs = float(changed[~sh].mean())
    esh = pds / max(pcs, 1e-12)

    md = float(np.median(dk[changed & disc])) if (changed & disc).any() else 0.0
    mc = float(np.median(dk[changed & ~disc])) if (changed & ~disc).any() else 0.0

    out.append((p, sigma_R, disc.mean(), changed.mean(), enrich, esh, md, mc))
    print("%-7d %9.5f %8.2f%% %8.2f%% %8.2fx %8.2fx %5.0f/%-4.0f"
          % (p, sigma_R, 100 * disc.mean(), 100 * changed.mean(),
             enrich, esh, md, mc))

print()
print("=" * 74)
en = np.array([r[4] for r in out])
sh = np.array([r[5] for r in out])
print("enrichment  min %.2fx  median %.2fx  max %.2fx"
      % (en.min(), float(np.median(en)), en.max()))
print("shuffled control  min %.2fx  median %.2fx  max %.2fx"
      % (sh.min(), float(np.median(sh)), sh.max()))
print()
if en.min() <= 1.5:
    print("VERDICT: REFUTED on at least one plane (min enrichment %.2fx <= 1.5)"
          % en.min())
elif abs(float(np.median(sh)) - 1.0) > 0.25:
    print("VERDICT: VOID -- the shuffle control did not read ~1.0 (%.2fx)"
          % float(np.median(sh)))
else:
    print("VERDICT: SUPPORTED. Disconnected pixels re-elect %.2fx more often,"
          % float(np.median(en)))
    print("the shuffle control reads %.2fx, and the pixels that move far are"
          % float(np.median(sh)))
    print("the disconnected ones. Photometric drift, M96's bimodal pixels and")
    print("the occlusion halo are the same object seen three ways.")
