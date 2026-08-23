"""
M29 / 06 -- The claim that started this milestone, priced.

The motivating argument was:

  A SELECTOR copies one frame's pixel into the output, so a dust shadow arrives
  at full contrast. An ESTIMATOR averages n_eff frames, and because the warp
  displaces the dust relative to the scene by a different amount in every frame,
  the shadow lands in n_eff different places and is diluted. If that is real,
  strehl suppresses dust without doing anything.

Scripts 01-05 established that dust cannot be DETECTED on this corpus: the floor
is scene texture at 15% fractional, it does not fall with frame count (exponent
+0.025), and the limit is a 32-50% shadow. But the dilution claim does not
actually require detecting any dust. It is a statement about geometry: given how
far the warp moves sensor coordinates relative to scene coordinates between the
frames a merge averages, a shadow of known radius is diluted by a computable
factor. Measure the displacements, and the claim is priced.

Two things make me doubt it before measuring, and both are worth stating up
front so the measurement can refute them:

  1. M27 measured n_eff for a focus merge as about 3 frames at full sampling
     density -- not the whole stack. Three frames is a weak averager.
  2. Those three frames are ADJACENT, and adjacent frames are exactly the ones
     with the least warp between them (M28: pairwise residual grows near
     linearly with separation, 1.13 -> 12.30 over 1 -> 16). The estimator
     averages precisely the frames whose dust positions agree most.

  3. Breathing is a SCALE change, so displacement vanishes at the optical
     centre and grows with radius. Any dilution is therefore radius dependent,
     and worst exactly where people put the subject.

METHOD. Per-frame displacement is measured directly by phase correlation of
256 px tiles against frame 0, on a ring of tiles at several radii, with a
parabolic subpixel peak. Defocus differs between the frames being correlated,
which biases SCALE estimates strongly (the whole subject of M23) but shifts only
weakly; 1 px accuracy is enough here and the numbers are labelled accordingly.

Dilution is then evaluated exactly, with no further measurement:

  D = max_x (1/n) * sum_k exp(-|x - d_k|^2 / (2 sigma_d^2))

the peak depth of a Gaussian shadow of radius sigma_d averaged over the n frames
a merge actually gathers at that pixel. D = 1 is no suppression at all, and a
selector is D = 1 by definition.

PRE-REGISTERED:
  Q12  displacement grows with radius from the optical centre and with frame
       separation.
  Q13  for n_eff = 3 adjacent frames, D is close to 1 -- the free lunch is not
       free. If D < 0.7 anywhere in the plausible parameter range the claim
       survives and the review was right.
  Q14  D falls with the SPAN of frames averaged rather than their count, so any
       real dust suppression has to be bought deliberately by widening the
       gather, not harvested from the merge as it stands.
"""
import glob, os, json
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter

BLACK, T = 512.0, 256
STACKS = [("109MSDCF", r"D:\personal\macro\109MSDCF", 22),
          ("coffee-bean", r"D:\personal\macro\coffee-bean", 24)]
SEPS = [1, 2, 4, 8, 16]
SIGMA_D = [5.0, 10.0, 20.0]        # green px; dust is ~10-40 sensor px across
OUT = os.path.join(os.path.dirname(__file__), "..", "out")


def green(path):
    with rawpy.imread(path) as r:
        return r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK


def shift(a, b):
    """Subpixel displacement of b relative to a by phase correlation."""
    a = a - a.mean()
    b = b - b.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    A, B = np.fft.rfft2(a * win), np.fft.rfft2(b * win)
    R = A * np.conj(B)
    R /= np.maximum(np.abs(R), 1e-12)
    c = np.fft.irfft2(R, s=a.shape)
    i, j = np.unravel_index(np.argmax(c), c.shape)

    def sub(v0, v1, v2):
        d = v0 - 2 * v1 + v2
        return 0.0 if abs(d) < 1e-12 else 0.5 * (v0 - v2) / d
    dy = i + sub(c[(i - 1) % c.shape[0], j], c[i, j], c[(i + 1) % c.shape[0], j])
    dx = j + sub(c[i, (j - 1) % c.shape[1]], c[i, j], c[i, (j + 1) % c.shape[1]])
    if dy > a.shape[0] / 2:
        dy -= a.shape[0]
    if dx > a.shape[1] / 2:
        dx -= a.shape[1]
    return dy, dx


res = {}
for name, folder, nmax in STACKS:
    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))[:nmax]
    gs = [green(f) for f in files]
    h, w = gs[0].shape
    cy, cx = h // 2, w // 2
    rad = [(0.15, 0), (0.35, 0), (0.55, 0), (0.75, 0)]
    tiles = []
    for fr, _ in rad:
        for ang in (0, 90, 180, 270):
            y = int(cy + fr * (h / 2 - T) * np.cos(np.radians(ang)))
            x = int(cx + fr * (w / 2 - T) * np.sin(np.radians(ang)))
            tiles.append((fr, y - T // 2, x - T // 2))
    print(f"\n{name}: {len(gs)} frames, {len(tiles)} tiles")
    print(f"{'radius':>7s}" + "".join(f"{'sep '+str(s):>10s}" for s in SEPS))
    byrad = {}
    for fr, _ in rad:
        row = []
        for sep in SEPS:
            mags = []
            for (f2, y, x) in tiles:
                if f2 != fr:
                    continue
                for k in range(0, len(gs) - sep, max(1, sep)):
                    dy, dx = shift(gs[k][y:y + T, x:x + T],
                                   gs[k + sep][y:y + T, x:x + T])
                    if abs(dy) < T / 4 and abs(dx) < T / 4:
                        mags.append(np.hypot(dy, dx))
            row.append(float(np.median(mags)) if mags else float("nan"))
        byrad[fr] = row
        print(f"{fr:7.2f}" + "".join(f"{v:10.2f}" for v in row))
    res[name] = byrad

print(f"\nQ13/Q14  dilution D of a Gaussian shadow averaged over the frames a "
      f"merge gathers")
print(f"          D = 1 is a selector; lower is suppression")
dil = []
for name, byrad in res.items():
    print(f"\n{name}")
    print(f"{'sigma_d':>8s} {'radius':>7s}" +
          "".join(f"{'n='+str(n)+' span'+str(s):>15s}"
                  for n, s in ((3, 1), (5, 1), (5, 4), (9, 8))))
    for sd in SIGMA_D:
        for fr in sorted(byrad):
            cells = ""
            for n, step in ((3, 1), (5, 1), (5, 4), (9, 8)):
                per = np.interp(step, SEPS, byrad[fr])
                offs = np.array([(k - (n - 1) / 2) * per for k in range(n)])
                D = float(np.mean(np.exp(-(offs - offs.mean()) ** 2
                                         / (2 * sd ** 2))))
                dil.append(dict(stack=name, sigma_d=sd, radius=fr, n=n,
                                span=step, per_step_px=float(per), D=D))
                cells += f"{D:15.3f}"
            print(f"{sd:8.0f} {fr:7.2f}" + cells)

worst = min(d["D"] for d in dil if d["n"] == 3)
print(f"\nQ13  best-case suppression at n_eff=3 adjacent: D = {worst:.3f}   "
      f"{'CLAIM SURVIVES' if worst < 0.7 else 'CLAIM DOES NOT SURVIVE'}")
with open(os.path.join(OUT, "06-dilution.json"), "w") as fh:
    json.dump(dict(displacement=res, dilution=dil, seps=SEPS), fh, indent=1)
