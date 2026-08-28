"""Bind the two halo reports to the measurements they claim. Shipped entry point.

Six lanes have now found their own verifier blind to a reversed conclusion, so
this checks CONCLUSIONS, not just numbers: each check is pinned to the specific
claim it certifies and re-derived from the saved measurement JSON, never from
the document's internal coherence.

Exit 0 = GREEN. Non-zero = the report disagrees with the measurements.
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_REPO = _os.path.join(_HERE, "halo-data")
_SCRATCH = r"D:\strehl-out\V-REVIEW\halo"
# prefer the banked in-repo inputs; fall back to scratch if it still exists
D = _REPO if _os.path.isdir(_REPO) else _SCRATCH
FP = os.path.join(HERE, "HALO-falsepositive.md")
RS = os.path.join(HERE, "HALO-residual.md")

def norm(t): return re.sub(r"\s+", " ", t)

fails, checks = [], 0
def ck(cond, msg):
    global checks
    checks += 1
    if not cond: fails.append(msg)

fp = norm(io.open(FP, encoding="utf-8").read())
rs = norm(io.open(RS, encoding="utf-8").read())
tr = json.load(open(os.path.join(D, "trunc2.json")))
h3 = json.load(open(os.path.join(D, "halo3.json")))
bl = json.load(open(os.path.join(D, "blind.json")))

# --- CONCLUSION checks. Each names the subject AND the verdict word, so a
# --- flipped verdict cannot be satisfied by the number appearing elsewhere.
for s in ("flat-on-ruler-cpl", "tweezers-cpl", "lavendar-cpl", "119MSDCF"):
    ck(re.search(re.escape(s) + r"[^|]{0,40}-- FALSE POSITIVE", fp) is not None,
       "FP report no longer calls %s a FALSE POSITIVE" % s)
ck("Answer: yes. All four." in fp, "FP report headline conclusion changed")
ck(re.search(r"leaf-2-cpl` is \*\*acquitted of halo", rs) is not None,
   "residual report no longer acquits leaf-2-cpl")
ck("COMMISSION FAILED" in rs, "residual report no longer states its commission failed")
ck(re.search(r"no halo is demonstrated anywhere", rs, re.I) is not None,
   "residual report headline changed")
ck(re.search(r"NOT ENTITLED", rs) is not None,
   "residual report dropped its NOT ENTITLED section")
ck(re.search(r"STREHL_HULL.{0,12} nothing here puts the fix back on the table", rs, re.I) is not None,
   "residual report changed its STREHL_HULL disposition")

# --- NUMERIC checks re-derived from the JSON, each anchored to its subject.
ck(sum(1 for v in tr.values() if v["verdict"] == "UNMEASURABLE") == 7,
   "halo_profile UNMEASURABLE count is no longer 7")
ck(sum(1 for v in tr.values() if v["verdict"] != "UNMEASURABLE" and v.get("used", 0) < 7) == 4,
   "halo_profile partial-walk count is no longer 4")
ck(sum(1 for v in h3.values() if v["verdict"] == "UNSCORED") == 8,
   "halo3 UNSCORED count is no longer 8")
ck(len(tr) == 26 and len(h3) == 26, "a corpus JSON no longer holds 26 subjects")

b = {x["lo"]: x for x in bl["leaf-2-cpl"]}[50]
ck(abs(b["med"] - 5721.4) < 1.0, "leaf-2-cpl 50-80 median moved from +5721.4")
ck(abs(b["cov"] * 100 - 43.75) < 1.0, "leaf-2-cpl 50-80 azimuthal coverage moved from 44%")
ck(b["cov"] < 0.60, "leaf-2-cpl coverage no longer below the qualification bar")
c = {x["lo"]: x for x in bl["bee-1-cpl"]}[50]
ck(abs(c["cov"] - 1.0) < 1e-9,
   "bee-1-cpl control coverage moved from 100% -- the discriminator is void")
ck(c["spread"] > 15000,
   "bee-1-cpl control spread fell; the 'spread does not discriminate' claim is void")
ck(abs(tr["leaf-2-cpl"]["overshoot"] + 1808.6) < 1.0,
   "leaf-2-cpl reported overshoot moved from its 20-32 px value")
ck(tr["leaf-2-cpl"]["used"] == 4, "leaf-2-cpl no longer walks 4/7 bands")
ck(h3["lavendar-cpl"]["verdict"] == "HALO", "halo3 lavendar-cpl verdict changed")
ck(h3["lavendar-cpl"]["overshoot"] < 1600.0,
   "lavendar-cpl no longer sits BELOW the 1600 DN demonstrated floor")
ck(h3["tweezers-cpl"]["overshoot"] == 0.0, "halo3 tweezers-cpl no longer reads 0.0")

# PRESENCE TESTS ARE SATISFIED BY DUPLICATES. Commissioning caught this:
# deleting the 1600 DN floor from the bee-1 row read GREEN because "1600 DN"
# also appears in the bee-2 row and in prose. Each number is now pinned to its
# own canonical site, so a deletion at that site cannot be masked elsewhere.
for anchor, n in (
    ("| **leaf-2-cpl** | **+5721** | **44%** (7/16) | **18845 DN** | walk artifact |",
     "leaf-2 azimuthal spread row"),
    ("| bee-1-cpl | **1600 DN** | 400 DN | 1 of 4 (at 3000 DN) |",
     "bee-1 detection floor row"),
    ("| bee-2-cpl | **1600 DN** | 1600 DN* | 0 of 4 |",
     "bee-2 detection floor row"),
    ("| 4 | 2613 DN | 1323 | 3305 | 0.51x / **1.26x** |",
     "best trend separation row"),
    ("read \"profile is monotone; no local rim\"", "the 3200 DN monotone refutation"),
    ("**HALO 7745 DN on known-clean `bee-1-cpl`**", "max-of-noise defect"),
):
    ck(norm(anchor) in rs, "residual report dropped or altered: %s" % n)

# --- SECTION 6 partition. It previously read "clean 14 / UNSCORED 8", which
# --- credited halo3's rescues; halo3 FAILED its commission, so it cannot move a
# --- subject out of UNSCORED. Every row below is RE-DERIVED from trunc2.json,
# --- and the withdrawn split carries a negative pin so it cannot drift back.
FLAGGED = ("flat-on-ruler-cpl", "tweezers-cpl", "lavendar-cpl", "119MSDCF")
_full = [k for k, v in tr.items()
         if v["verdict"] != "UNMEASURABLE" and v.get("used", 0) == 7]
ck(len([k for k in _full if k not in FLAGGED]) == 11,
   "clean full-7-band-walk count is no longer 11")
ck(sorted(k for k in _full if k in FLAGGED) == sorted(FLAGGED),
   "the four false positives no longer all walk a full 7 bands")
ck(len([k for k, v in tr.items()
        if v["verdict"] != "UNMEASURABLE" and v.get("used", 0) < 7]) +
   sum(1 for v in tr.values() if v["verdict"] == "UNMEASURABLE") == 11,
   "residual risk re-derived from trunc2.json is no longer 11 subjects")
for anchor, n in (
    ("| clean, full 7-band walk | **11** |", "section 6 clean row"),
    ("| clean but BLIND beyond 32-50 px, not a pass | **4** |", "section 6 blind row"),
    ("| UNMEASURABLE, per-subject reason in section 2 | **7** |", "section 6 unmeasurable row"),
    ("**Residual risk is 11 subjects UNSCORED**", "section 6 residual-risk statement"),
    ("**`halo3` failed its own commission (section 4), so it cannot move any subject\nout of UNSCORED**",
     "section 6 retraction rationale"),
):
    ck(norm(anchor) in rs, "residual report dropped or altered: %s" % n)
ck(norm("| clean | **14** |") not in rs,
   "the withdrawn 'clean 14' partition row has reappeared")
ck(norm("| UNSCORED, per-subject reason in section 2 | **8** |") not in rs,
   "the withdrawn 'UNSCORED 8' partition row has reappeared")

print("checks run : %d" % checks)
print("failed     : %d" % len(fails))
for f in fails: print("   FAIL: %s" % f)
print("VERDICT    : %s" % ("GREEN" if not fails else "RED"))
sys.exit(0 if not fails else 1)

