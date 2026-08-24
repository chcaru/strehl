"""Check the "~2.5x" claim I folded into fact 1258.

mottle2.py reported per-channel sigma and a mottle RATIO, and I converted
those to an absolute mid-band change in my head while writing the fact. Hand
arithmetic on ratios of ratios is exactly where a corpus acquires a wrong
number that nothing later contradicts, so this recomputes it from the
reported quantities and prints the mid-band SD directly.

The two arms also have different mean levels (a single frame sits at 0.2454
in green, the merged render at 0.5452), so any absolute comparison between
them is meaningless unless it is normalised by the mean. That normalisation
is the step most likely to have gone missing.
"""
import numpy as np

FINE, COARSE = 5, 33
K = np.sqrt(1.0 / FINE ** 2 - 1.0 / COARSE ** 2)
print("mid-band coefficient for iid noise: sqrt(1/%d^2 - 1/%d^2) = %.6f"
      % (FINE, COARSE, K))

# straight from mottle2.py's output
single = {"R": (0.22507, 0.00313, 2.77),
          "G": (0.24537, 0.00197, 2.42),
          "B": (0.26200, 0.00230, 2.90)}
merged = {"R": (0.52538, 0.00071, 8.46),
          "G": (0.54523, 0.00059, 10.12),
          "B": (0.56129, 0.00059, 10.63)}

print()
print("%-6s %26s %26s %10s" % ("", "SINGLE FRAME", "MERGED", ""))
print("%-6s %12s %12s %12s %12s %10s"
      % ("chan", "mid abs", "mid/mean", "mid abs", "mid/mean", "ratio"))
print("-" * 70)
rows = []
for c in "RGB":
    m1, s1, r1 = single[c]
    m2, s2, r2 = merged[c]
    a1 = s1 * K * r1
    a2 = s2 * K * r2
    n1, n2 = a1 / m1, a2 / m2
    rows.append(n2 / n1)
    print("%-6s %12.6f %12.6f %12.6f %12.6f %9.3fx"
          % (c, a1, n1, a2, n2, n2 / n1))

med = float(np.median(rows))
print()
print("normalised mid-band change, merged vs single: %.3fx (median %.3fx)"
      % (float(np.mean(rows)), med))
print("i.e. the mottle fell by a factor of %.2f" % (1.0 / med))
print()
print("fact 1258 as folded says the mid-band 'fell ~2.5x'.")
if abs(1.0 / med - 2.5) > 0.3:
    print("*** THAT IS WRONG. The correct factor is %.2fx. ***" % (1.0 / med))
    print("Fold a correction.")
else:
    print("claim stands")

print()
print("For contrast, the FINE noise ratio (normalised), merged vs single:")
for c in "RGB":
    m1, s1, _ = single[c]
    m2, s2, _ = merged[c]
    print("  %s  %.4fx" % (c, (s2 / m2) / (s1 / m1)))
print()
print("So the honest statement is: fine noise falls ~10x, mid-band falls")
print("only ~%.1fx, and the mottle dominates the residual because of the" % (1.0 / med))
print("GAP between those two numbers, not because it grew.")
