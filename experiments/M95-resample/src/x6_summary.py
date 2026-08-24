"""M95 arm 4 - single source of truth for every number in the report.

Rule: a number recalled from earlier notes is not a measurement. Everything the report
quotes is printed here, from the recorded JSON of the run that produced it, including the
derived quantities (blur equivalents, shares of the total) which are computed here rather
than by hand.
"""

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def load(n):
    return json.load(open(os.path.join(OUT, n)))


x2, x3, x4, x5 = load("x2_pairs.json"), load("x3_kernel.json"), load("x4_endtoend.json"), load("x5_ringing.json")

print("=" * 78)
print("A. THE DECOMPOSITION  (x2_pairs.py, 40 in-focus tiles, 0.30-0.48 vs 0.02-0.10 cyc/px)")
print("=" * 78)
for k, v in x2["per_image"].items():
    print(f"  {k:6s} mean {v['mean']:+.4f}  sd {v['sd']:.4f}  n={v['n']:2d}  cc {v['mean_cc']:.4f}  dropped {v['dropped']}")
print()
for k, v in x2["deltas"].items():
    print(f"  {k:8s} {v:+.4f} dex   {10**abs(v):.3f}x power   {10**(abs(v)/2):.3f}x amplitude")

print()
print("=" * 78)
print("B. CONTROLS")
print("=" * 78)
print(f"  K7 null (B0 vs B0)            : {x2['null']:+.6f} dex")
print("  K6/K13 planted Fourier-exact Gaussian blur on B0:")
for s, v in sorted(x2["planted"].items(), key=lambda kv: float(kv[0])):
    print(f"      sigma = {float(s):4.2f} px -> {v:+.4f} dex")
print(f"  K8 anchor separation          : {x2['anchor_sep']:.4f} dex   gate>=0.30 {'PASS' if x2['anchor_gate_pass'] else 'FAIL'}")
print(f"  x3 identity-phase, catmullrom : {x3['results']['catmullrom']['identity']:+.6f} dex")
print(f"  x3 identity-phase, lanczos3   : {x3['results']['lanczos3']['identity']:+.6f} dex")
print(f"  x3 identity-phase, bspline    : {x3['results']['bspline']['identity']:+.6f} dex")
print(f"  x3 identity-phase, mitchell   : {x3['results']['mitchell']['identity']:+.6f} dex  (approximating, NOT interpolating)")
print(f"  x3 ordering mitchell<catmull  : {'PASS' if x3['ordering_ok'] else 'FAIL'}")
for k, v in x4["checks"].items():
    print(f"  x4 {k:26s} : {'PASS' if v else 'FAIL'}")
for k, v in x5["checks"].items():
    print(f"  x5 {k:26s} : {'PASS' if v else 'FAIL'}")

print()
print("=" * 78)
print("C. END TO END THROUGH THE SHIPPED BINARY  (x4, sidecar resampler is the ONLY change)")
print("=" * 78)
for k in ("nearest", "catmull-rom", "bilinear"):
    v = x4["results"][k]
    print(f"  {k:12s} {v['delta']:+.4f} dex  {10**abs(v['delta']):.3f}x power  {10**(abs(v['delta'])/2):.3f}x amplitude  n={v['n']}")
kern = x4["results"]["catmull-rom"]["delta"] - x4["results"]["nearest"]["delta"]
print(f"\n  INTERPOLATION KERNEL ALONE : {kern:+.4f} dex  {10**abs(kern):.3f}x power  {10**(abs(kern)/2):.3f}x amplitude")

print()
print("=" * 78)
print("D. BLUR EQUIVALENT, from the K6 anchors")
print("=" * 78)
p25, p50 = x2["planted"]["0.25"], x2["planted"]["0.5"]
slope = np.log(p50 / p25) / np.log(2.0)
print(f"  response is proportional to sigma^{slope:.3f} between 0.25 and 0.50 px")


def sigma_of(dex):
    return 0.25 * (abs(dex) / abs(p25)) ** (1.0 / slope)


for lab, d in (
    ("one strehl gather, total (B0->B1)", x2["deltas"]["B0->B1"]),
    ("the interpolation kernel alone", kern),
    ("B0 -> C, single frame to shipped merge", x2["deltas"]["B0->C"]),
):
    print(f"  {lab:40s} {d:+.4f} dex  ==  a Gaussian blur of sigma = {sigma_of(d):.3f} px")

print()
print("=" * 78)
print("E. WHAT A KERNEL CHANGE WOULD BUY  (x3, independently written kernels)")
print("=" * 78)
cr = x3["results"]["catmullrom"]["phase_avg"]
print(f"  independent Catmull-Rom, phase-averaged : {cr:+.4f} dex")
print(f"  independent Catmull-Rom, worst phase    : {x3['results']['catmullrom']['worst']:+.4f} dex")
print(f"  strehl's own gather, measured (B0->B1)  : {x3['strehl_b0_b1']:+.4f} dex")
print(f"  gap (strehl vs independent, phase-avg)  : {x3['strehl_b0_b1'] - cr:+.4f} dex")
print()
for n in ("lanczos3", "bspline"):
    g = x3["results"][n]["phase_avg"] - cr
    r = x5["results"][n]["mean_overshoot"] / x5["results"]["catmullrom"]["mean_overshoot"]
    print(
        f"  {n:10s} recovers {g:+.4f} dex ({10**abs(g):.3f}x power, {10**(abs(g)/2):.3f}x amplitude)"
        f"   and rings {r:.3f}x as much"
    )

print()
print("=" * 78)
print("F. RINGING  (x5, mean overshoot as a fraction of the local range, half-pixel phase)")
print("=" * 78)
for k, v in x5["results"].items():
    print(f"  {k:12s} mean {v['mean_overshoot']:.6f}   p99.9 {v['p999']:.6f}   negatives {v['pct_negative']:.4f}%")

print()
print("=" * 78)
print("G. SHARE OF THE TOTAL LOSS")
print("=" * 78)
tot = abs(x2["deltas"]["B0->C"])
parts = [
    ("interpolation kernel", abs(kern)),
    ("gather that is not the kernel (nearest baseline)", abs(x4["results"]["nearest"]["delta"])),
    ("election + coverage zoom (remainder)", tot - abs(kern) - abs(x4["results"]["nearest"]["delta"])),
]
for lab, v in parts:
    print(f"  {lab:52s} {v:+.4f} dex  {100*v/tot:5.1f}%")
print(f"  {'TOTAL B0 -> C':52s} {tot:+.4f} dex  100.0%")
print()
print(f"  demosaic-algorithm difference (A -> B0), NOT part of the above: {x2['deltas']['A->B0']:+.4f} dex")
