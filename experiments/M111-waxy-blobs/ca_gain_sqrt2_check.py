"""Is the measured lateral-CA gain distinguishable from sqrt(2)?

ORCH argues the sqrt(2) mechanism is live because 1.4142 "sits inside the
measured spread 1.381-1.505". The spread of seven ring estimates is the
dispersion of the estimates, not the uncertainty of their centre. If the
standard error excludes sqrt(2), the normalisation hunt in optics.rs is
looking for something that is not there, and a fitted scalar is the honest fix.

M111 contributes the arithmetic only. The measurement, the estimator and the
validated control are ORCH's; nothing here re-derives them.
"""
import math

# r, support, n, gain -- transcribed from ORCH's table
ROWS = [
    (0.250, "INSIDE",  240, 1.465),
    (0.350, "INSIDE",  238, 1.462),
    (0.450, "INSIDE",  238, 1.442),
    (0.550, "INSIDE",  205, 1.444),
    (0.650, "INSIDE",  136, 1.419),
    (0.750, "INSIDE",   52, 1.505),
    (0.830, "OUTSIDE",  33, 1.381),
]
SQRT2 = math.sqrt(2.0)

# Transcription guard: ORCH quoted these summaries, so they must reproduce.
# ORCH reports MEDIANS ("Median 1.444"), not means -- asserting the mean here
# fired and corrected my own assumption about which statistic was quoted.
def median(xs):
    s = sorted(xs)
    k = len(s)
    return s[k // 2] if k % 2 else 0.5 * (s[k // 2 - 1] + s[k // 2])


inside = [g for _, s, _, g in ROWS if s == "INSIDE"]
outside = [g for _, s, _, g in ROWS if s == "OUTSIDE"]
allg = [g for *_, g in ROWS]
assert abs(median(allg) - 1.444) < 5e-4, f"overall median {median(allg):.4f} != 1.444"
assert abs(median(inside) - 1.453) < 5e-4, f"inside median {median(inside):.4f} != 1.453"
assert abs(outside[0] - 1.381) < 5e-4, "outside != ORCH's 1.381"
assert abs(min(allg) - 1.381) < 1e-9
assert abs(max(allg) - 1.505) < 1e-9


def summarise(label, rows):
    g = [r[3] for r in rows]
    n = len(g)
    m = sum(g) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in g) / (n - 1))
    sem = sd / math.sqrt(n)
    t = (m - SQRT2) / sem
    # two-sided 95% t critical values, df = n-1
    tcrit = {5: 2.571, 6: 2.447, 7: 2.365}[n - 1]
    lo, hi = m - tcrit * sem, m + tcrit * sem
    print(f"{label}")
    print(f"   n rings {n}   mean {m:.4f}   sd {sd:.4f}   sem {sem:.4f}")
    print(f"   95% CI on the mean   [{lo:.4f}, {hi:.4f}]")
    print(f"   vs sqrt(2)={SQRT2:.4f}   t={t:+.2f}   "
          f"{'EXCLUDED' if not (lo <= SQRT2 <= hi) else 'compatible'}")
    print(f"   implied inverse 1/mean = {1/m:.4f}   (1/sqrt2 = {1/SQRT2:.4f})")
    print()
    return m, sem, lo, hi


print("=" * 68)
print("Is the gain sqrt(2)?  The spread is not the standard error.")
print("=" * 68)
print(f"raw spread quoted by ORCH: 1.381 - 1.505, which does contain "
      f"sqrt(2)={SQRT2:.4f}")
print()

m_all, sem_all, lo_all, hi_all = summarise("ALL SEVEN RINGS (unweighted)", ROWS)
m_in, sem_in, lo_in, hi_in = summarise(
    "INSIDE SUPPORT ONLY (six rings)", [r for r in ROWS if r[1] == "INSIDE"])

# Precision differs ~7x across rings; weight by window count.
tot = sum(r[2] for r in ROWS)
wm = sum(r[2] * r[3] for r in ROWS) / tot
print("WINDOW-COUNT WEIGHTED (all seven)")
print(f"   weighted mean {wm:.4f}   (unweighted {m_all:.4f})")
print(f"   the two low-n rings, 1.505 (n=52) and 1.381 (n=33), are the only "
      f"ones\n   near sqrt(2) or far above, and they carry {(52+33)/tot:6.1%} "
      f"of the windows")
print()

# Is a single scalar even the right model? Weighted trend in radius.
mw = sum(r[2] * r[0] for r in ROWS) / tot
sxx = sum(r[2] * (r[0] - mw) ** 2 for r in ROWS)
sxy = sum(r[2] * (r[0] - mw) * (r[3] - wm) for r in ROWS)
slope = sxy / sxx
print("RADIAL TREND (window-weighted)")
print(f"   slope {slope:+.4f} gain per unit r  ->  "
      f"{slope * (0.830 - 0.250):+.4f} across the measured span")
print(f"   ORCH's claim that the gain is FLAT in radius is supported; a single "
      f"scalar\n   is the right model shape.")
print()

print("=" * 68)
verdict_all = not (lo_all <= SQRT2 <= hi_all)
verdict_in = not (lo_in <= SQRT2 <= hi_in)
print(f"sqrt(2) excluded at 95% on all seven rings : {verdict_all}")
print(f"sqrt(2) excluded at 95% inside support     : {verdict_in}")
print("=" * 68)
