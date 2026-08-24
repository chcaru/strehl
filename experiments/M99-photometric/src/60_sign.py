"""M99 Phase G -- settle the sign of the per-frame photometric bias.

Answers PR-13/14/15: signed-ramp recovery, the statistic-identity question,
and the EXIF arbiter. Reads Phase A's committed ladders; decodes nothing.
"""

import json
import math

DECK = "bee-3-cpl"
D = json.load(open("experiments/M99-photometric/data/phaseA.json"))[DECK]

lev = D["g_scene"]          # scene-coordinate background level, per frame
exp = D["g_exp"]            # EXIF-predicted exposure, per frame
ref = D["ref"]
n = len(lev)
dec = max(1, n // 10)


def bias(vals, lo, hi, r):
    """Mean level over [lo,hi) against frame r, in both conventions."""
    m = sum(vals[lo:hi]) / (hi - lo)
    return m / vals[r] - 1.0, vals[r] / m - 1.0


print(f"deck {DECK}   n={n}   reference={ref}   decile={dec} frames")
print(f"level[0]={lev[0]:.6f}  level[{ref}]={lev[ref]:.6f}  "
      f"level[{n-1}]={lev[n-1]:.6f}")
print(f"endpoint ratio level[0]/level[-1] = {lev[0]/lev[-1]:.4f}")

print("\n-- PR-14: the early-decile bias, M87's statistic, on M87's deck --")
b_bright, b_gain = bias(lev, 0, dec, ref)
print(f"  M99 scene-coord early decile: brightness {b_bright*100:+.2f}%   "
      f"gain {b_gain*100:+.2f}%")
print(f"  M87 far background reported : brightness -3.13%   gain +3.23%")
print(f"  the 5.31% figure re-derived : sqrt({lev[0]/lev[-1]:.4f})-1 = "
      f"{math.sqrt(lev[0]/lev[-1])-1:+.2%}  <- a FOCUS advantage, not a level bias")

print("\n-- PR-15: the EXIF arbiter (Program AE, independent of all pixels) --")
e_bright, e_gain = bias(exp, 0, dec, ref)
print(f"  EXIF early decile: brightness {e_bright*100:+.2f}%   "
      f"gain {e_gain*100:+.2f}%")
print(f"  EXIF endpoint ratio exp[0]/exp[-1] = {exp[0]/exp[-1]:.4f}")
agree = (b_bright > 0) == (e_bright > 0)
print(f"  scene and EXIF agree in sign: {agree}")

print("\n-- PR-13: signed-ramp recovery through the shipped estimator rule --")
print("  estimator: g_k = flux_ref / flux_k   (photometric.rs:390)")
print(f"  {'planted':>9} {'recovered':>11} {'err pp':>8}   verdict")
ok = True
for p in (0.0, 0.02, -0.02, 0.04, -0.04, 0.08, -0.08):
    # Plant a monotone ramp: frame 0 is (1+p) times the reference, falling
    # linearly to (1-p) at the last frame. Positive p == early frames brighter.
    planted = [lev[k] * (1.0 + p * (1.0 - 2.0 * k / (n - 1))) for k in range(n)]
    gains = [planted[ref] / planted[k] for k in range(n)]
    # Recover the planted early-decile gain bias, with the deck's own bias
    # removed so we measure what the plant added and nothing else.
    base = [lev[ref] / lev[k] for k in range(n)]
    rec = (sum(gains[0:dec]) / dec) / (sum(base[0:dec]) / dec) - 1.0
    # Expected: planting +p brightness on early frames lowers their gain.
    want = 1.0 / (1.0 + p * (1.0 - 2.0 * (dec - 1) / 2.0 / (n - 1))) - 1.0
    err = abs(rec - want) * 100
    good = err < 0.5 if p != 0 else abs(rec) < 0.0005
    ok &= good
    print(f"  {p*100:+8.1f}% {rec*100:+10.2f}% {err:8.3f}   "
          f"{'ok' if good else 'FAIL'}")
print(f"\n  PR-13 verdict: {'SIGN SOUND' if ok else 'SIGN FLIPPED / FAIL'}")
