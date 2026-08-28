"""V-KILLB0 verdict.py -- bind my VERDICT to my NUMBERS, and try to flip it.

ORCH's postscript: a presence test cannot detect a reversed conclusion.  My
harness had a worse version of that defect than V-LINEAR's -- not a weak check
binding verdict to evidence, but NO check at all.  My verdict lived only in
prose, so no mutation could ever have been caught.  This is that check.

It re-derives the verdict mechanically from the stored measurements and then
runs CONCLUSION-FLIP arms: each one leaves the document internally consistent
and changes what the report CONCLUDES.  A check that survives all of these is
worthless.  Arm A2 is deliberately the shape V-LINEAR found in itself -- move a
subject's qualification boundary so that a band which carried a withdrawn claim
becomes re-licensed, with every measured number left correct.
"""
import copy
import sys

# ---- the evidence, exactly as measured -------------------------------------
FACTS = {
    # subject: boundary from V-LINEAR (None = unqualified)
    "boundary": {"leaf-2-cpl": 0.20, "bee-1-cpl": 0.48, "113MSDCF": 0.25},
    # subject -> band -> R at STRUCTURED sites (flatanalyze.py, V-LINEAR rule)
    "R_struct": {"leaf-2-cpl": {(0.05, 0.08): 48.088, (0.08, 0.11): 19.115,
                                (0.11, 0.14): 9.772, (0.14, 0.17): 5.935,
                                (0.17, 0.20): 3.719, (0.20, 0.25): 2.202}},
    # subject -> band -> b0x4/default amplitude at STRUCTURED sites (spectrum.py)
    "obs_struct": {"leaf-2-cpl": {(0.05, 0.08): 0.6913, (0.08, 0.11): 0.5789,
                                  (0.11, 0.14): 0.5520, (0.14, 0.17): 0.5559,
                                  (0.17, 0.20): 0.5526, (0.20, 0.25): 0.5482}},
    # bee flat-site band 0: R, and the PERMUTED selection-bias floor
    "bee_flat": {(0.25, 0.30): (1.075, 1.021, 1.037), (0.30, 0.40): (1.035, 1.006, 1.023),
                 (0.40, 0.48): (1.026, 0.998, 1.033)},
}
PASS_R, PASS_CI = 2.0, 1.5


def derive(f):
    """Re-derive every conclusion from the numbers.  No prose is consulted."""
    out = {}
    # C1: is there a QUALIFIED band where loss exceeds the max-legal-denoise floor?
    convicted = []
    for subj, bands in f["obs_struct"].items():
        b = f["boundary"].get(subj)
        for band, obs in bands.items():
            R = f["R_struct"][subj][band]
            if b is None or band[1] > b:          # band not qualified signal here
                continue
            if R < PASS_R:                        # band does not PASS: no claim
                continue
            floor = (1.0 - 1.0 / R) ** 0.5
            if obs < floor:
                convicted.append((subj, band, obs, floor))
    out["C1_damage"] = convicted
    # C2: does ORCH's flat-site defence hold?  flat band 0 must FAIL and must not
    #     stand clear of the selection-bias floor.
    holds = True
    for band, (R, ci, null) in f["bee_flat"].items():
        if R >= PASS_R and ci >= PASS_CI:
            holds = False                          # flat band 0 is SIGNAL -> defence fails
        if R - null > 0.20:
            holds = False                          # stands clear of the null -> unexplained
    out["C2_defence_holds"] = holds
    out["VERDICT"] = "REFUTED" if convicted else "NOT REFUTED"
    return out


def show(tag, r):
    n = len(r["C1_damage"])
    return (f"{tag:<46} verdict={r['VERDICT']:<11} qualified-damaged bands={n}  "
            f"ORCH defence holds={r['C2_defence_holds']}")


base = derive(FACTS)
print("== BASELINE (unmutated)")
print("  " + show("as measured", base))
for s, band, obs, fl in base["C1_damage"]:
    print(f"     {s} {band[0]:.2f}-{band[1]:.2f}  observed {obs:.4f} < denoise floor {fl:.4f}")

ARMS = []
def arm(name, fn):
    ARMS.append((name, fn))

def a1(f):   # loss shrinks above the bound: damage should vanish
    for b in f["obs_struct"]["leaf-2-cpl"]:
        f["obs_struct"]["leaf-2-cpl"][b] = 0.995
arm("A1 loss reduced above the denoise floor", a1)

def a2(f):   # V-LINEAR's own defect shape: move the boundary to re-license
    f["boundary"]["leaf-2-cpl"] = 0.05
arm("A2 boundary moved so damaged bands are 'noise'", a2)

def a3(f):   # bee flat band 0 becomes SIGNAL -> ORCH's defence must fail
    f["bee_flat"][(0.30, 0.40)] = (4.10, 3.05, 1.023)
arm("A3 bee flat band 0 reclassified as SIGNAL", a3)

def a4(f):   # flat numbers pasted into the structured slot
    f["obs_struct"]["leaf-2-cpl"] = {b: 0.99 for b in f["obs_struct"]["leaf-2-cpl"]}
    f["R_struct"]["leaf-2-cpl"] = {b: 1.05 for b in f["R_struct"]["leaf-2-cpl"]}
arm("A4 STRUCT/FLAT populations swapped", a4)

def a5(f):   # R inflated so the floor drops below what was observed
    f["R_struct"]["leaf-2-cpl"] = {b: 1.35 for b in f["R_struct"]["leaf-2-cpl"]}
arm("A5 R inflated until the floor sinks under the loss", a5)

def a6(f):   # subject silently de-qualified
    f["boundary"]["leaf-2-cpl"] = None
arm("A6 subject de-qualified (boundary removed)", a6)

def a7(f):   # bee flat R stands clear of the selection-bias null
    f["bee_flat"][(0.25, 0.30)] = (1.60, 1.40, 1.037)
arm("A7 bee flat R stands clear of the permuted null", a7)

print("\n== CONCLUSION-FLIP ARMS  (each must change a conclusion, and be CAUGHT)")
caught = 0
for name, fn in ARMS:
    f = copy.deepcopy(FACTS)
    fn(f)
    r = derive(f)
    flipped = (r["VERDICT"] != base["VERDICT"]
               or r["C2_defence_holds"] != base["C2_defence_holds"]
               or len(r["C1_damage"]) != len(base["C1_damage"]))
    caught += flipped
    print(f"  {'CAUGHT ' if flipped else 'MISSED '} {show(name, r)}")
print(f"\n  {caught}/{len(ARMS)} conclusion-flip arms caught  "
      f"{'PASS' if caught == len(ARMS) else 'FAIL - the check is decorative'}")

# --- pass/fail channel -------------------------------------------------------
# Added by ORCH, not by this file's author, after V-KILLB0's own `verdictaudit.py`
# proved every designed outcome here exited 0 -- including a run that printed the
# word FAIL.  Two separate defects were found and both are fixed below.
#
# 1. `caught == len(ARMS)` is satisfied by DELETING an arm: remove A7 and the
#    harness prints "6/6 ... PASS".  A count pins nothing on its own, so the arm
#    NAMES are pinned too.  This is the same hole `softaudit.py` found in the
#    sibling `softverdict.py`.
# 2. Nothing here ever exited non-zero, so any CI step or `if ($LASTEXITCODE)`
#    wrapper read this harness as green unconditionally.
#
# The verdict itself was re-audited under these mutations and did NOT move: the
# derivation is sound and correctly signed in both directions.  What was wrong
# was the assurance the printed number implied, not the number.
EXPECTED_ARMS = (
    "A1 loss reduced above the denoise floor",
    "A2 boundary moved so damaged bands are 'noise'",
    "A3 bee flat band 0 reclassified as SIGNAL",
    "A4 STRUCT/FLAT populations swapped",
    "A5 R inflated until the floor sinks under the loss",
    "A6 subject de-qualified (boundary removed)",
    "A7 bee flat R stands clear of the permuted null",
)

failures = []
names = tuple(n for n, _ in ARMS)
if names != EXPECTED_ARMS:
    failures.append(
        "ARM SET CHANGED: expected %d arms %r, found %d arms %r. An arm was added, "
        "removed or renamed; `caught == len(ARMS)` cannot see that."
        % (len(EXPECTED_ARMS), EXPECTED_ARMS, len(names), names))
if caught != len(ARMS):
    failures.append(
        "%d of %d conclusion-flip arms were MISSED: the verdict does not follow "
        "from the numbers." % (len(ARMS) - caught, len(ARMS)))

if failures:
    print("\n  VERDICT BINDING FAILED")
    for f in failures:
        print("    " + f)
    sys.exit(1)
print("\n  VERDICT BINDING PASSED  "
      f"({len(ARMS)} arms, all named as expected, all caught)")
sys.exit(0)
