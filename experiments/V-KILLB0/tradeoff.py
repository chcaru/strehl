"""V-KILLB0 tradeoff.py -- is 4 justified over 2, and does duty predict damage?

BENEFIT = 1 - (flat-site amplitude ratio)     grain removed at flat sites
COST    = 1 - (structured-site amplitude ratio)   real detail removed
both in 0.05-0.14 cyc/px, which is below every boundary V-LINEAR measured
(minimum 0.17 across a 2.8x spread) and is therefore qualified SIGNAL on all
five measured subjects.  For the fourteen unmeasured subjects that is an
assumption, flagged below; it is the most conservative band available.

Numbers are pasted from the breadth.py runs above so the arithmetic is checkable.
"""
import numpy as np
from scipy.stats import spearmanr

# subject: (default duty %, b0x4 SIG STRUCT, b0x4 SIG FLAT, qual)
X4 = {
 "109MSDCF": (72.5, 0.9899, 0.8572, "UNQUAL"), "leaf-2-cpl": (54.4, 0.6549, 0.5631, "0.20"),
 "flower-bud-alone-cpl": (37.3, 0.9874, 0.6278, "0.17"), "coffee-bubbles": (36.4, 1.0006, 0.7178, "UNQUAL"),
 "119MSDCF": (34.4, 0.9986, 0.7127, "0.25"), "lavendar-cpl": (33.5, 1.0031, 0.5960, "UNQUAL"),
 "pencil-steep-angle-cpl": (32.2, 1.0025, 0.5701, "UNQUAL"), "112MSDCF": (32.1, 0.9689, 0.6862, "UNQUAL"),
 "tweezers-cpl": (29.7, 1.0039, 0.9391, "UNQUAL"), "113MSDCF": (28.6, 1.0003, 0.7732, "0.25"),
 "flower-inner-edge-cpl": (26.4, 0.9939, 0.7271, "UNQUAL"), "couch-fibers-cpl": (19.7, 0.9696, 0.6763, "UNQUAL"),
 "bee-1-cpl": (10.6, 1.0023, 0.8167, "0.48"), "dry-erase-marker-head-cpl": (10.0, 1.0003, 0.8184, "UNQUAL"),
 "coffee-bean": (7.5, 1.0012, 0.8746, "UNQUAL"), "foam": (5.5, 1.0018, 0.9552, "UNQUAL"),
 "wrapped-text-1": (1.1, 1.0006, 0.9332, "UNQUAL"), "paper-sweep-cpl": (0.0, 1.0011, 1.0011, "UNQUAL"),
 "flat-on-ruler-cpl": (0.0, 1.0004, 1.0014, "UNQUAL"),
}
# subjects rendered at BOTH 2x and 4x: (2x STRUCT, 2x FLAT)
X2 = {"109MSDCF": (0.9970, 0.8675), "112MSDCF": (1.0114, 0.7690), "119MSDCF": (1.0002, 0.7409),
      "coffee-bubbles": (1.0009, 0.7564), "couch-fibers-cpl": (0.9969, 0.8294),
      "flat-on-ruler-cpl": (1.0001, 1.0007), "foam": (1.0009, 0.9906), "leaf-2-cpl": (0.8575, 0.6891),
      "paper-sweep-cpl": (1.0004, 1.0007), "tweezers-cpl": (1.0037, 0.9392)}

print("== IS 4 JUSTIFIED OVER 2?   benefit = grain removed at FLAT, cost = detail removed at STRUCT")
print(f"{'subject':<24} {'ben 2x':>7} {'ben 4x':>7} {'d ben':>7} | "
      f"{'cost 2x':>8} {'cost 4x':>8} {'d cost':>7} | {'verdict':>22}")
db, dc = [], []
for s in sorted(X2, key=lambda k: -X4[k][0]):
    b2, b4 = 1 - X2[s][1], 1 - X4[s][2]
    c2, c4 = 1 - X2[s][0], 1 - X4[s][1]
    db.append(b4 - b2); dc.append(c4 - c2)
    v = "cost grows, no gain" if (c4 - c2) > max(b4 - b2, 0) else "4x buys more than it costs"
    print(f"{s:<24} {b2:7.3f} {b4:7.3f} {b4-b2:+7.3f} | {c2:8.3f} {c4:8.3f} "
          f"{c4-c2:+7.3f} | {v:>22}")
print(f"\n  going 2x -> 4x, summed over the 10 subjects rendered at both:")
print(f"    extra benefit {sum(db):+.3f}   extra cost {sum(dc):+.3f}   "
      f"cost per unit extra benefit = {sum(dc)/sum(db):.2f}")

print("\n== DOES DEFAULT DUTY CYCLE PREDICT DAMAGE?  (a pre-flight check ORCH could run)")
duty = np.array([X4[s][0] for s in X4]); cost = np.array([1 - X4[s][1] for s in X4])
r, p = spearmanr(duty, cost)
print(f"   spearman(default duty, 4x structured-site cost) over {len(duty)} subjects: "
      f"rho={r:.3f} p={p:.4f}")
hi = [s for s in X4 if X4[s][0] > 50]
print(f"   subjects with default duty > 50%: {hi}")
print(f"     their costs: " + ", ".join(f"{s} {1-X4[s][1]:+.4f}" for s in hi))
print(f"   worst 3 costs overall: " +
      ", ".join(f"{s} {1-X4[s][1]:+.4f} (duty {X4[s][0]}%)"
                for s in sorted(X4, key=lambda k: X4[k][1])[:3]))
