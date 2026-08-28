"""V-KILLB0 verdictaudit.py -- polarity/deletion audit of verdict.py through its
SHIPPED ENTRY POINT (subprocess), per ORCH's three arms.

Reports TWO channels separately, because they can disagree and the difference is
the whole finding:
  * EXIT  -- what a CI or a caller sees (the shipped pass/fail channel)
  * TEXT  -- what the printed conclusion says (whether the LOGIC noticed)
An instrument whose logic is sound but whose channel is dead reads green to every
automated consumer while still being right on paper.  Those are different repairs
and different risks, so they are scored apart.

Every mutation is anchored on a UNIQUE full-line string and hard-errors if it
does not land exactly once.
"""
import subprocess, sys, os, re

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verdict.py")
OUT = r"D:\strehl-out\V-KILLB0\vaudit"
os.makedirs(OUT, exist_ok=True)
BASE = open(SRC, encoding="utf-8").read()

A_BOUND = '    "boundary": {"leaf-2-cpl": 0.20, "bee-1-cpl": 0.48, "113MSDCF": 0.25},'
A_PASS  = "PASS_R, PASS_CI = 2.0, 1.5"
A_ARM7  = 'arm("A7 bee flat R stands clear of the permuted null", a7)'
A_DOC   = '"""V-KILLB0 verdict.py -- bind my VERDICT to my NUMBERS, and try to flip it.'
A_BAND  = "                                (0.17, 0.20): 3.719, (0.20, 0.25): 2.202}},"

def mutate(old, new, tag):
    n = BASE.count(old)
    if n != 1:
        raise SystemExit("FATAL anchor for %s matched %d times, not 1:\n  %r" % (tag, n, old))
    return BASE.replace(old, new)

def run(text, tag):
    path = os.path.join(OUT, "v_%s.py" % tag)
    open(path, "w", encoding="utf-8").write(text)
    r = subprocess.run([sys.executable, path], capture_output=True, text=True)
    o = (r.stdout or "") + (r.stderr or "")
    verdict = (re.search(r"verdict=(\S+)", o) or [None, "?"])[1]
    m = re.search(r"(\d+)/(\d+) conclusion-flip arms caught", o)
    ratio = "%s/%s" % (m.group(1), m.group(2)) if m else "?"
    nbands = (re.search(r"qualified-damaged bands=(\d+)", o) or [None, "?"])[1]
    tail = "PASS" if "PASS" in o.split("conclusion-flip arms caught")[-1] else "FAIL"
    return r.returncode, verdict, ratio, nbands, tail

# tag, mutation, class, what the CONCLUSION should do
ARMS = [
 ("null",  None, "NULL",
  "unmutated: must exit 0 and read REFUTED 7/7"),
 ("rev_obs",
  (A_PASS, A_PASS + '\nFACTS["obs_struct"]["leaf-2-cpl"] = {b: 0.995 for b in FACTS["obs_struct"]["leaf-2-cpl"]}'),
  "REVERSAL", "loss removed -> verdict must become NOT REFUTED"),
 ("rev_boundary",
  (A_BOUND, '    "boundary": {"leaf-2-cpl": 0.05, "bee-1-cpl": 0.48, "113MSDCF": 0.25},'),
  "REVERSAL", "V-LINEAR defect shape: de-license the damaged bands"),
 ("rev_defence",
  (A_PASS, A_PASS + '\nFACTS["bee_flat"][(0.30, 0.40)] = (4.10, 3.05, 1.023)'),
  "REVERSAL", "bee flat band 0 -> SIGNAL: ORCH defence must fail"),
 ("del_arm",
  (A_ARM7, ""),
  "DELETION", "remove arm A7: must not stay green at 6/6"),
 ("del_band",
  (A_BAND, "                                (0.17, 0.20): 3.719}},"),
  "DELETION", "delete a measured band row: damaged-band count must move"),
 ("spec_prose",
  (A_DOC, '"""V-KILLB0 verdict.py -- INNOCUOUS PROSE EDIT, no number touched.'),
  "SPECIFICITY", "prose only: conclusion must NOT move"),
 ("spec_unused",
  (A_BOUND, '    "boundary": {"leaf-2-cpl": 0.20, "bee-1-cpl": 0.48, "113MSDCF": 0.31},'),
  "SPECIFICITY", "perturb an unused subject: conclusion must NOT move"),
]

print("%-14s %-12s %-5s %-12s %-6s %-7s %s" % ("arm","class","EXIT","verdict","bands","arms","expectation"))
print("-"*118)
rows=[]
for tag, mut, cls, why in ARMS:
    text = BASE if mut is None else mutate(mut[0], mut[1], tag)
    code, verdict, ratio, nbands, tail = run(text, tag)
    rows.append((tag, cls, code, verdict, nbands, ratio, tail))
    print("%-14s %-12s %-5d %-12s %-6s %-7s %s" % (tag, cls, code, verdict, nbands, ratio, why))

print("-"*118)
base = rows[0]
print("\nCHANNEL ANALYSIS")
exits = {r[2] for r in rows}
print("  EXIT codes observed across ALL arms: %s" % sorted(exits))
if len(exits) == 1:
    print("  *** verdict.py's PASS/FAIL CHANNEL IS DEAD: every arm -- reversal, deletion,")
    print("      specificity and null alike -- returns the same exit code %d." % rows[0][2])
    print("      No caller, CI step or wrapper can distinguish a flipped conclusion from a clean run.")
moved = [r for r in rows[1:] if r[1] in ("REVERSAL","DELETION") and (r[3]!=base[3] or r[4]!=base[4] or r[5]!=base[5])]
held  = [r for r in rows[1:] if r[1]=="SPECIFICITY" and (r[3]==base[3] and r[4]==base[4] and r[5]==base[5])]
print("\n  TEXT channel: %d/%d reversal+deletion arms visibly moved the printed conclusion"
      % (len(moved), len([r for r in rows[1:] if r[1] in ("REVERSAL","DELETION")])))
print("  TEXT channel: %d/%d specificity arms correctly held the conclusion still" % (len(held), 2))
print("\n  baseline as shipped: verdict=%s bands=%s arms=%s" % (base[3], base[4], base[5]))
