"""M114 r25 -- independent re-derivation of camera_to_srgb, and its grounding.

ORCH reported that the corpus quoted `rownorm(inv(A@S))` where the crate
computes `inv(rownorm(A@S))`. This does not adopt that correction; it re-derives
both orderings from the crate's own constants and checks them against two
independent references.

Reference 1: color.rs:221's doc comment states the green row directly.
Reference 2: A7C2_XYZ_TO_CAM at color.rs:812 lives inside `#[cfg(test)]`
             (mod tests opens at line 799), so it is a TEST FIXTURE. Whether it
             describes the actual captures is a separate question, and this
             answers it by reading rgb_xyz_matrix out of a real ARW via rawpy.

Registered bars:
  E1  the two orderings differ (else there is nothing to correct)
  E2  the crate ordering matches color.rs:221's doc comment to 3 d.p.
  E3  the corpus ordering does NOT match that doc comment
  E4  the corpus ordering reproduces the previously-quoted 10.44% / 20.32%,
      which identifies the mechanism rather than merely the discrepancy
  E5  the test fixture equals the real capture's metadata
"""
import json

import numpy as np
import rawpy

ARW = r"D:\personal\macro\bee-3-cpl\DSC00001.ARW"
OUT = r"C:\dev\strehl-out\M114-ca-verify\r25.json"

S = np.array([[0.4124564, 0.3575761, 0.1804375],       # SRGB_TO_XYZ_D65, color.rs:79
              [0.2126729, 0.7151522, 0.0721750],
              [0.0193339, 0.1191920, 0.9503041]])
FIXTURE = np.array([[0.7460, -0.2365, -0.0588],        # color.rs:812, inside cfg(test)
                    [-0.5687, 1.3442, 0.2474],
                    [-0.0624, 0.1156, 0.6584]])
DOC_GREEN = np.array([-0.115, 1.489, -0.374])          # color.rs:221 doc comment


def rownorm(M):
    return M / M.sum(axis=1, keepdims=True)


def leaks(X):
    return {"green->red": 100 * abs(X[0, 1] / X[0, 0]),
            "blue->red": 100 * abs(X[0, 2] / X[0, 0]),
            "red->green": 100 * abs(X[1, 0] / X[1, 1]),
            "blue->green": 100 * abs(X[1, 2] / X[1, 1]),
            "red->blue": 100 * abs(X[2, 0] / X[2, 2]),
            "green->blue": 100 * abs(X[2, 1] / X[2, 2])}


with rawpy.imread(ARW) as raw:
    real = np.array(raw.rgb_xyz_matrix, dtype=np.float64)[:3, :3]

e5 = bool(np.abs(real - FIXTURE).max() < 5e-5)
print("E5  color.rs:812 fixture vs the real capture's rgb_xyz_matrix: max|d|=%.8f  %s"
      % (np.abs(real - FIXTURE).max(), "PASS" if e5 else "FAIL"))

M = real @ S
crate = np.linalg.inv(rownorm(M))        # color.rs steps 1,2,3
corpus = rownorm(np.linalg.inv(M))       # what the corpus quoted

e1 = not np.allclose(crate, corpus)
e2 = bool(np.abs(crate[1] - DOC_GREEN).max() < 5e-4)
e3 = bool(np.abs(corpus[1] - DOC_GREEN).max() > 5e-4)
cl = leaks(corpus)
e4 = bool(abs(cl["green->red"] - 10.44) < 0.01 and abs(cl["red->green"] - 20.32) < 0.01)

for lbl, X in (("CRATE  inv(rownorm(A@S))", crate), ("CORPUS rownorm(inv(A@S))", corpus)):
    print()
    print(lbl)
    for nm, row in zip("RGB", X):
        print("   %s row: %9.6f %9.6f %9.6f" % (nm, row[0], row[1], row[2]))
    for k, v in leaks(X).items():
        print("      %-12s %6.2f%%" % (k, v))

print()
for nm, v in (("E1 orderings differ", e1),
              ("E2 crate matches color.rs:221 doc", e2),
              ("E3 corpus does NOT match it", e3),
              ("E4 corpus reproduces 10.44/20.32", e4),
              ("E5 fixture == real capture", e5)):
    print("   %-36s %s" % (nm, "PASS" if v else "FAIL"))

allok = e1 and e2 and e3 and e4 and e5
print()
print("VERDICT: ORCH's correction is %s by independent re-derivation."
      % ("CONFIRMED" if allok else "NOT CONFIRMED"))
json.dump(dict(crate=crate.tolist(), corpus=corpus.tolist(),
               crate_leaks=leaks(crate), corpus_leaks=cl,
               E1=e1, E2=e2, E3=e3, E4=e4, E5=e5, confirmed=bool(allok)),
          open(OUT, "w"), indent=1)
print("wrote", OUT)
