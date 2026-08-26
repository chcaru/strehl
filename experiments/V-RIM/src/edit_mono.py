from pathlib import Path

P = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-RIM-verification.md")
t = P.read_text(encoding="utf-8")

OLD = """The shape statement is stronger than the level statement, because levels are
exposed to focus breathing changing what "t = 100 px" means in each frame.
**The merged profile is non-monotone and all ten single frames are monotone.**
The merge rises to 14922 DN at t = 20 px, falls to 14447 DN at t = 120 px, then
recovers to 17497 DN at t = 280 px. Every frame rises from the silhouette to the
far field without turning over, the largest reversal in any of them being 16 DN,
0.08% of far field, in frame 110. A dip-and-recover cannot be produced by focus
breathing.
"""

NEW = """The shape statement is stronger than the level statement, because levels are
exposed to focus breathing changing what "t = 100 px" means in each frame, and
to exposure drift through the bracket. Shape is not. Summing every downward step
in the median profile between t = 0 and t = 280 px, over all sixteen usable
single frames and both merges:

| image | reversals | total fall, DN | total fall, % of far |
| --- | --- | --- | --- |
| `coffee-bean` merge | 6 | −4820 | **−8.03%** |
| `flower-bud` merge | 7 | −596 | **−3.33%** |
| worst single frame (`flower-bud` frame 70) | 2 | −33 | −0.18% |
| every other single frame | 0 to 2 | −2 to −50 | −0.01% to −0.08% |

**Both merged profiles turn over; not one of the sixteen single frames does.**
The worst non-monotonicity in any photograph is 0.18% of far field, and the
merges are 18x and 45x that. A dip-and-recover cannot be produced by focus
breathing or by exposure drift, both of which are monotone in distance.
"""

assert OLD in t, "ANCHOR NOT FOUND"
t = t.replace(OLD, NEW)
P.write_text(t.rstrip("\n") + "\n", encoding="utf-8", newline="\n")
print("ok")
