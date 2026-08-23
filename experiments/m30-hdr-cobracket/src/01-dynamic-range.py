"""
M30 / 01 -- R17. What does a macro focus stack lose to dynamic range, and what
            would a second exposure actually buy?

The review's claim: "the estimation framework handles per-frame gain natively; a
two-exposure stack pair gives true HDR focus stacks -- RAW-native, calibrated --
which no shipping tool does honestly." Three measured facts now make this
priceable rather than arguable:

  fact 202 (M26)  `coffee-bean` has 1.26% of pixels at or above the 15360 DN
                  per-channel white level; four of six stacks have none.
  fact 213 (M27)  a 105-frame f/8 bracket is 2-4x denser in the focus axis than
                  it needs to be, so frames are AVAILABLE to re-task.
  fact 225 (M28)  per-frame gain must be fitted as the mean over all pixels.

and the calibrated noise model makes the counterfactual exact. A frame at +2 EV
has 4x the signal and sigma^2 = g(4S) + (RN g)^2, so the SNR change is a closed
form in the measured per-pixel signal -- no scene simulation is required, and no
second capture. What such a frame COSTS is equally exact: every pixel above
white/4 clips.

THE STATISTIC THAT MATTERS IS NOT THE GLOBAL ONE. M26 measured clipping over the
whole stack. What a merge actually sees is the exposure of the frame it would
GATHER at each pixel, i.e. at that pixel's best-focus frame. Those are different
numbers and only the second one is about the output.

THE CONTROL THAT MAKES OR BREAKS THIS. A naive analysis credits HDR bracketing
with a gain that is really just "more photons". The placebo is a +0 EV
DUPLICATE: re-task the same frames to the same exposure. That buys sqrt(2) in
noise and exactly zero in dynamic range. **The HDR claim is only worth something
to the extent the +2 EV arm beats the +0 EV arm**, and everything below is
reported as that difference.

PRE-REGISTERED PREDICTIONS:

  Q1  Clipping at the best-focus frame is within 2x of the global figure. (If it
      is far lower, highlights are mostly out of focus and the highlight half of
      the HDR case collapses.)
  Q2  The shadow problem is larger than the highlight problem: more than 20% of
      pixels sit below SNR 10 at their best-focus frame in at least one stack.
  Q3  The +2 EV arm beats the +0 EV duplicate arm by less than the naive
      factor-of-2 shot-noise argument suggests, because most pixels are already
      shot-noise limited rather than read-noise limited, where the two arms
      converge. The honest deliverable is an exchange rate, not a free lunch.
"""
import glob, os, json
import numpy as np
import rawpy
from scipy.ndimage import uniform_filter, sobel

BLACK, WHITE_NM, CROP, RBOX = 512.0, 15360.0, 1500, 2
STACKS = [("coffee-bean", r"D:\personal\macro\coffee-bean", 50.0, 2),
          ("112MSDCF", r"D:\personal\macro\112MSDCF", 500.0, 1),
          ("109MSDCF", r"D:\personal\macro\109MSDCF", 160.0, 1)]
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")


def rn_e(iso):
    return 4.20 if iso < 400.0 else 1.47


def sigma_dn(S, iso):
    """M4 model, native per-channel raw DN. S is DN above black."""
    g = iso / 436.8
    return np.sqrt(np.maximum(g * S, 0.0) + (rn_e(iso) * g) ** 2)


def load(folder, step):
    """Green sublattice, centred crop, one frame per `step`."""
    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))[::step]
    out = []
    for f in files:
        with rawpy.imread(f) as r:
            g = r.raw_image_visible[0::2, 1::2].astype(np.float32)
        h, w = g.shape
        y, x = (h - CROP) // 2, (w - CROP) // 2
        out.append(g[y:y + CROP, x:x + CROP])
    return np.stack(out)


res = {}
for name, folder, iso, step in STACKS:
    os.makedirs(CACHE, exist_ok=True)
    cp = os.path.join(CACHE, f"cube-{name}.npy")
    if os.path.exists(cp):
        cube = np.load(cp)
    else:
        cube = load(folder, step)
        np.save(cp, cube)
    n = cube.shape[0]
    sig = cube - BLACK

    # focus volume, M27's recipe unmodified (discipline 34)
    bf = np.full((CROP, CROP), -1.0, np.float32)
    bi = np.zeros((CROP, CROP), np.int64)
    for k in range(n):
        a = sig[k]
        f = uniform_filter(np.hypot(sobel(a, 0), sobel(a, 1)),
                           2 * RBOX + 1).astype(np.float32)
        m = f > bf
        bf[m], bi[m] = f[m], k
    yy, xx = np.mgrid[0:CROP, 0:CROP]
    S = sig[bi, yy, xx]                      # signal at each pixel's best frame

    clip_best = float((cube[bi, yy, xx] >= WHITE_NM).mean())
    clip_glob = float((cube >= WHITE_NM).mean())
    snr = S / sigma_dn(S, iso)

    # counterfactual arms, exact from the calibrated model
    snr_p2 = (4 * S) / sigma_dn(4 * S, iso)          # +2 EV, ignoring clipping
    would_clip = S > (WHITE_NM - BLACK) / 4.0
    newclip = float(would_clip.mean())
    gain_p2 = np.where(would_clip, 1.0, snr_p2 / np.maximum(snr, 1e-9))
    gain_dup = np.sqrt(2.0)                           # +0 EV duplicate, averaged
    adv = gain_p2 / gain_dup                          # the number that matters

    def q(a, p):
        return float(np.percentile(a, p))

    r = dict(n=n, iso=iso, clip_best=clip_best, clip_global=clip_glob,
             snr_med=float(np.median(snr)), snr_p10=q(snr, 10),
             frac_snr10=float((snr < 10).mean()),
             frac_snr5=float((snr < 5).mean()),
             frac_snr2=float((snr < 2).mean()),
             new_clip_at_p2=newclip,
             gain_p2_med=float(np.median(gain_p2)),
             adv_med=float(np.median(adv)), adv_p10=q(adv, 10),
             adv_p90=q(adv, 90), adv_frac_gt1=float((adv > 1.0).mean()),
             read_limited=float((S < rn_e(iso) ** 2).mean()))
    res[name] = r
    print(f"\n=== {name}  n={n}  ISO {iso:.0f} ===")
    print(f"  clipping   at best-focus frame {100*clip_best:6.3f}%   "
          f"whole stack {100*clip_glob:6.3f}%   Q1 ratio "
          f"{clip_best/max(clip_glob,1e-12):.2f}x")
    print(f"  SNR at best focus: median {r['snr_med']:7.1f}   p10 "
          f"{r['snr_p10']:6.1f}   <10 {100*r['frac_snr10']:5.1f}%   "
          f"<5 {100*r['frac_snr5']:5.1f}%   <2 {100*r['frac_snr2']:5.1f}%")
    print(f"  read-noise limited (S < RN_e^2): {100*r['read_limited']:.2f}%")
    print(f"  +2 EV arm: median SNR gain {r['gain_p2_med']:.3f}x   "
          f"newly clipped {100*newclip:.2f}%")
    print(f"  vs +0 EV duplicate placebo (x{np.sqrt(2):.3f}): "
          f"advantage median {r['adv_med']:.3f}x   "
          f"p10 {r['adv_p10']:.3f}  p90 {r['adv_p90']:.3f}   "
          f"beats placebo on {100*r['adv_frac_gt1']:.1f}% of pixels")

print(f"\nQ1  clipping at best focus vs global: "
      + "  ".join(f"{k} {v['clip_best']/max(v['clip_global'],1e-12):.2f}x"
                  for k, v in res.items()))
print(f"Q2  fraction below SNR 10 at best focus: "
      + "  ".join(f"{k} {100*v['frac_snr10']:.1f}%" for k, v in res.items())
      + f"   {'HOLDS' if max(v['frac_snr10'] for v in res.values()) > 0.20 else 'FAILS'}")
print(f"Q3  median advantage of +2 EV over a same-exposure duplicate: "
      + "  ".join(f"{k} {v['adv_med']:.3f}x" for k, v in res.items())
      + f"   (naive shot-noise argument says 1.414x)")
with open(os.path.join(OUT, "01-dynamic-range.json"), "w") as fh:
    json.dump(res, fh, indent=1)
