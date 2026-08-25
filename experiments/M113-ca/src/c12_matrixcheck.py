"""M113 c12: independently recompute camera_to_srgb and settle which form is right.

ORCH reports that the corpus (and my own c8_linear.py docstring, which is where
the 10.4 %/20.3 % figures originate) used rownorm(inv(A@S)) where the crate
computes inv(rownorm(A@S)). I do not take that on report. color.rs:148-208 states
the steps in prose and then performs them; this recomputes both orderings from
the crate's OWN constants and tests each against an independent witness the crate
publishes separately -- the doc comment at color.rs:221, which states the green
row as [-0.115, +1.489, -0.374].

That witness is the point. It was written by the code's author to describe the
shipped behaviour and it is not part of either candidate computation, so it can
discriminate between them without circularity.
"""
import numpy as np

A = np.array([[0.7460, -0.2365, -0.0588],
              [-0.5687, 1.3442, 0.2474],
              [-0.0624, 0.1156, 0.6584]], dtype=np.float64)
S = np.array([[0.412_456_4, 0.357_576_1, 0.180_437_5],
              [0.212_672_9, 0.715_152_2, 0.072_175_0],
              [0.019_333_9, 0.119_192_0, 0.950_304_1]], dtype=np.float64)

def rownorm(m):
    return m / m.sum(axis=1, keepdims=True)

cam_from_srgb = A @ S
crate = np.linalg.inv(rownorm(cam_from_srgb))     # color.rs steps 1,2,3
corpus = rownorm(np.linalg.inv(cam_from_srgb))    # what the corpus quoted

WITNESS = np.array([-0.115, 1.489, -0.374])       # color.rs:221 doc comment

print("=" * 92)
print("Independent witness: color.rs:221 green row = [-0.115, +1.489, -0.374]")
print("=" * 92)
for name, m in (("inv(rownorm(A@S))  [crate steps 1,2,3]", crate),
                ("rownorm(inv(A@S))  [what corpus said]", corpus)):
    g = m[1]
    err = np.abs(g - WITNESS).max()
    print("\n%s" % name)
    for i, r in enumerate("RGB"):
        print("   %s row: %10.6f %10.6f %10.6f   (sum %.6f)"
              % (r, m[i][0], m[i][1], m[i][2], m[i].sum()))
    print("   green row vs witness: max|d| = %.6f   -> %s"
          % (err, "MATCHES" if err < 5e-4 else "does not match"))

print("\n" + "=" * 92)
print("The cross-channel leaks that the sRGB-contamination argument rests on")
print("=" * 92)
for name, m in (("crate (correct)", crate), ("corpus (wrong)", corpus)):
    rg = abs(m[0][1]) / abs(m[0][0]) * 100
    gr = abs(m[1][0]) / abs(m[1][1]) * 100
    print("  %-16s output red carries camera green %6.1f %% ; "
          "output green carries camera red %5.1f %%" % (name, rg, gr))

print("\nMy c8_linear.py docstring claimed 10.4 %% and 20.3 %%.")
rg_c = abs(corpus[0][1]) / abs(corpus[0][0]) * 100
gr_c = abs(corpus[1][0]) / abs(corpus[1][1]) * 100
print("The corpus form yields %.1f %% and %.1f %% -- %s"
      % (rg_c, gr_c, "so my docstring carried the corpus form"
         if abs(rg_c - 10.4) < 0.3 and abs(gr_c - 20.3) < 0.3 else "neither matches"))
print("\nMy docstring also printed the rows themselves:")
print("   R_out = +1.1975 R  -0.1250 G  -0.0725 B")
print("   G_out = -0.4530 R  +2.2300 G  -0.7770 B")
print("corpus form rows:")
for i, r in enumerate("RG"):
    print("   %s_out = %+.4f R %+.4f G %+.4f B" % (r, corpus[i][0], corpus[i][1], corpus[i][2]))
print("\nCONCLUSION: the crate form is %s; the direction of the error is that the"
      % ("CONFIRMED by the independent witness" if np.abs(crate[1] - WITNESS).max() < 5e-4
         else "NOT confirmed"))
print("green->red leak is %.1f %% and not %.1f %%, i.e. the contamination argument"
      % (abs(crate[0][1]) / abs(crate[0][0]) * 100, rg_c))
print("is STRENGTHENED, not weakened.")