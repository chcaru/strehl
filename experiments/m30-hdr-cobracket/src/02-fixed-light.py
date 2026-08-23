"""
M30 / 02 -- Fixed LIGHT, not fixed frames. Script 01's control had a hole.

Script 01 compared one +2 EV frame against one +0 EV duplicate and reported a
1.415x advantage. That is not a result, it is an accounting error of mine: a
+2 EV frame by shutter costs 4x the exposure TIME, so the comparison put four
units of light against one and discovered that more light is better. The placebo
controlled for frame count, which is not the scarce resource. Exposure time is.

Redone at fixed total light, the question has a closed-form answer, and the
answer is that exposure allocation is EXACTLY NEUTRAL in the shot-noise regime.
For scene radiance L, a base frame measures S = L with variance
`g L + (RN g)^2`; a +2 EV frame measures 4L, and expressed back in radiance
units its variance is `[4 g L + (RN g)^2] / 16 = g L / 4 + (RN g)^2 / 16`. Take
`m` frames of each and combine by inverse variance against `5m` base frames --
the same 5m units of time, since each +2 EV frame costs 4 --

    HDR split      Var = 1 / (m/V_base + m/V_p2)  =  V_base / (5m)   [shot-noise]
    all base       Var = V_base / (5m)

Identical. Photons are photons. Every asymmetry that could break the tie is
measurable, and all three are measured here:

  READ NOISE   favours fewer, longer exposures. Binds only where `g S < (RN g)^2`,
               i.e. `S < RN_e^2 * g` DN above black.
  CLIPPING     favours more, shorter exposures. Binds at the top.
  FRAME COUNT  favours more, shorter exposures for reasons outside the noise
               model entirely -- focus coverage (fact 213) and outlier
               rejection (fact 222).

So the review's HDR co-bracketing item does not turn on the estimator's ability
to handle per-frame gain, which it has (M24, M28). It turns on whether this
sensor and these scenes have a dynamic-range problem at all.

STATUS OF THE PREDICTIONS BELOW. Weaker than usual and labelled as such: script
01 has already been run and its numbers informed these. They are stated to be
falsifiable, not to claim foresight.

  Q4  the fixed-light identity holds per pixel on real data to within a few
      parts in a thousand, with residual deviation attributable to read noise
      and traceable to signal level.
  Q5  the read-noise-limited fraction is negligible -- the boundary sits at a
      few DN above black, far below anything a real exposure contains.
  Q6  the highlight asymmetry is small and, at the pixels a merge actually
      gathers, smaller than the whole-stack figure -- because highlights are
      disproportionately out of focus.
"""
import os, json
import numpy as np

BLACK, WHITE_NM = 512.0, 15360.0
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
STACKS = [("coffee-bean", 50.0), ("112MSDCF", 500.0), ("109MSDCF", 160.0)]


def rn_e(iso):
    return 4.20 if iso < 400.0 else 1.47


def var_dn(S, iso):
    g = iso / 436.8
    return g * np.maximum(S, 0.0) + (rn_e(iso) * g) ** 2


prev = json.load(open(os.path.join(OUT, "01-dynamic-range.json")))
out = {}
print(f"Q5  read-noise regime boundary, S < RN_e^2 * g DN above black")
print(f"{'stack':>14s} {'ISO':>5s} {'g DN/e-':>9s} {'RN e-':>7s} "
      f"{'boundary DN':>12s} {'% of full scale':>16s} {'measured % below':>18s}")
for name, iso in STACKS:
    g = iso / 436.8
    b = rn_e(iso) ** 2 * g
    out[name] = dict(iso=iso, g=g, boundary_dn=float(b),
                     boundary_frac=float(b / (WHITE_NM - BLACK)),
                     read_limited=prev[name]["read_limited"])
    print(f"{name:>14s} {iso:5.0f} {g:9.4f} {rn_e(iso):7.2f} {b:12.3f} "
          f"{100*b/(WHITE_NM-BLACK):15.4f}% {100*prev[name]['read_limited']:17.2f}%")

print(f"\nQ4  fixed-light identity, evaluated per pixel on the real signal")
print(f"     all-base 5m frames   vs   m base + m at +2 EV   (both 5m time units)")
print(f"{'stack':>14s} {'median ratio':>13s} {'p1':>9s} {'p99':>9s} "
      f"{'max dev':>9s} {'clipped at +2EV':>16s}")
for name, iso in STACKS:
    cube = np.load(os.path.join(CACHE, f"cube-{name}.npy"), mmap_mode="r")
    S = np.asarray(cube[cube.shape[0] // 2], np.float32) - BLACK
    S = np.maximum(S, 0.0)
    m = 1.0
    v_base = var_dn(S, iso)
    v_p2 = var_dn(4.0 * S, iso) / 16.0                 # in radiance units
    var_all = v_base / (5.0 * m)
    var_hdr = 1.0 / (m / v_base + m / v_p2)
    ratio = np.sqrt(var_all / var_hdr)                 # >1 means HDR wins
    clip = float((S > (WHITE_NM - BLACK) / 4.0).mean())
    out[name].update(ratio_med=float(np.median(ratio)),
                     ratio_p1=float(np.percentile(ratio, 1)),
                     ratio_p99=float(np.percentile(ratio, 99)),
                     clip_at_p2=clip)
    print(f"{name:>14s} {np.median(ratio):13.5f} {np.percentile(ratio,1):9.5f} "
          f"{np.percentile(ratio,99):9.5f} "
          f"{np.max(np.abs(ratio-1.0)):9.5f} {100*clip:15.2f}%")

print(f"\nQ6  the three asymmetries, measured, per stack")
print(f"{'stack':>14s} {'read-limited':>13s} {'clipped @ best focus':>21s} "
      f"{'clipped whole stack':>20s} {'SNR<10 @ best focus':>20s}")
for name, iso in STACKS:
    p = prev[name]
    print(f"{name:>14s} {100*p['read_limited']:12.2f}% "
          f"{100*p['clip_best']:20.3f}% {100*p['clip_global']:19.3f}% "
          f"{100*p['frac_snr10']:19.1f}%")
    out[name].update(clip_best=p["clip_best"], clip_global=p["clip_global"],
                     frac_snr10=p["frac_snr10"])

mx = max(abs(out[n]["ratio_med"] - 1.0) for n, _ in STACKS)
rl = max(out[n]["read_limited"] for n, _ in STACKS)
cb = max(out[n]["clip_best"] for n, _ in STACKS)
print(f"\nQ4  max median deviation from neutrality {mx:.5f}   "
      f"{'HOLDS' if mx < 0.01 else 'FAILS'}")
print(f"Q5  max read-noise-limited fraction {100*rl:.4f}%   "
      f"{'HOLDS' if rl < 0.001 else 'FAILS'}")
print(f"Q6  max clipping at best focus {100*cb:.3f}%   "
      f"vs whole-stack {100*max(out[n]['clip_global'] for n,_ in STACKS):.3f}%")
with open(os.path.join(OUT, "02-fixed-light.json"), "w") as fh:
    json.dump(out, fh, indent=1)
