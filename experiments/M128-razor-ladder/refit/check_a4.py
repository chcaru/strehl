"""
Checker for M128 Amendment A4.

Every number A4 states must come from a file on disk, not from my memory of the
conversation. This script re-reads refit.json and commission.json and requires
the amendment to agree with them.

TWO CLASSES OF NUMBER, AND THEY ARE NOT EQUALLY TRUSTWORTHY
-----------------------------------------------------------
  DERIVED   Produced by refit_width.py / commission_refit.py on this machine.
            Checked against the JSON those scripts wrote. If the amendment and
            the JSON disagree, the amendment is wrong.

  REPORTED  Measured by the razor-verifier, which wrote no files. There is no
            JSON to check these against. They are pinned to the constants block
            below so that the amendment cannot drift from what was actually
            reported, and so a later reader can see at a glance which numbers
            have provenance on disk and which do not.

  The distinction is the point. A checker that treated both alike would imply
  the reported numbers had been verified when they have not been.

DESIGN NOTES CARRIED FORWARD FROM EARLIER LANES
-----------------------------------------------
  * Prose wraps, so all matching happens against FLAT -- the text with runs of
    whitespace collapsed to single spaces. A plain substring search fails on any
    phrase that spans a line break.
  * check_phrase() builds the search string FROM the JSON value together with
    surrounding words, so the check carries its own context. An anchor that
    merely contains the value it is checking can never fail.
  * The summary partitions every check into pass / fail / unresolved, and those
    must sum to the total. A skipped check must not read as a passed one.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANE = os.path.dirname(HERE)
NOTE = os.environ.get("A4_PATH", os.path.join(LANE, "PREREGISTRATION.md"))

with open(NOTE, encoding="utf-8") as f:
    RAW = f.read()
# A4 is the last amendment; scope the checks to it so a number that happens to
# appear in A1-A3 cannot satisfy a check about A4.
idx = RAW.find("### Amendment A4")
if idx < 0:
    print("FATAL: Amendment A4 not found in %s" % NOTE)
    sys.exit(2)
FLAT = re.sub(r"\s+", " ", RAW[idx:])

with open(os.path.join(HERE, "refit.json"), encoding="utf-8") as f:
    R = json.load(f)
with open(os.path.join(HERE, "commission.json"), encoding="utf-8") as f:
    C = json.load(f)

# Verifier-reported constants. No on-disk provenance; see docstring.
REPORTED = {
    "rise_iso_f56_t0": 19.848, "rise_erf_f56_t0": 19.326,
    "plateau_hi": 3236.7, "plateau_lo": 718.0, "contrast": 2518.6,
    "rise_iso": [20.86, 19.91, 16.50], "rise_erf": [18.42, 16.29, 16.62],
    "sd_iso": [5.6, 5.3, 5.4], "sd_erf": [3.4, 4.7, 3.9],
    "corr_f8": 0.811, "corr_f11": 0.728,
    "plateau_ratios": [4.52, 4.60, 4.39],
    "frames": ["DSC00063", "DSC00061", "DSC00062", "DSC00047"],
    "rows": "[254:286)", "cols": "[2626:2666)",
    "ragged": -31.70,
}

npass = nfail = nunres = 0
fails = []


def record(ok, label, needle, kind):
    global npass, nfail, nunres
    if ok is None:
        nunres += 1
        fails.append((kind, label, "UNRESOLVED", needle))
        print("  UNRESOLVED  [%s] %s" % (kind, label))
    elif ok:
        npass += 1
    else:
        nfail += 1
        fails.append((kind, label, "FAIL", needle))
        print("  FAIL        [%s] %s   looked for: %r" % (kind, label, needle))


def check_phrase(label, template, kind, *values):
    """Build the needle FROM the values, so it carries its own context."""
    needle = template % values
    record(needle in FLAT, label, needle, kind)


def check_lit(label, needle, kind):
    record(needle in FLAT, label, needle, kind)


print("Checking Amendment A4 in %s" % NOTE)
print("=" * 74)

# ------------------------------------------------------------ DERIVED: the fit
check_phrase("refit w both estimators", "recovering **w = %.2f / %.2f um**", "DERIVED",
             R["t2"]["isotonic"]["w"], R["t2"]["erf"]["w"])
check_phrase("refit k both zero", "`k = %.3f`", "DERIVED", R["t2"]["isotonic"]["k"])
check_phrase("sigma isotonic", "excluded at **%.2f**", "DERIVED",
             R["t2"]["isotonic"]["sigma_equiv"])
check_phrase("sigma erf", "and **%.2f sigma**", "DERIVED", R["t2"]["erf"]["sigma_equiv"])
check_phrase("w95 interval", "runs %.1f-%.1f um", "DERIVED",
             R["t2"]["isotonic"]["w95"][0], R["t2"]["isotonic"]["w95"][1])

# ------------------------------------------------------- DERIVED: ratio test
check_phrase("sharp-edge prediction", "= %.3f`", "DERIVED", 11.0 / 5.6)
check_phrase("measured ratio isotonic", "are **%.2f** and", "DERIVED",
             R["t1"]["isotonic"]["ratio"])
check_phrase("measured ratio erf", "and **%.2f**. The rise", "DERIVED",
             R["t1"]["erf"]["ratio"])

# ------------------------------------------------------- DERIVED: floor budget
check_phrase("sensor pitch", "the %.2f um pixel aperture", "DERIVED", R["s1"]["pitch_um"])
check_phrase("sublattice pitch", "full** %.2f um green-sublattice", "DERIVED",
             R["s1"]["sublattice_um"])
check_phrase("pixel-aperture rise", "a %.2f um rise", "DERIVED", 0.8 * R["s1"]["pitch_um"])
check_phrase("sampling contribution", "contributes %.2f um", "DERIVED",
             0.8 * R["s1"]["sublattice_um"])
check_phrase("combined floor", "floor of **%.2f um**", "DERIVED", R["s1"]["floor_um"])
check_phrase("w_physical isotonic", "**w_physical = %.2f um**", "DERIVED",
             R["s1"]["isotonic"]["w_physical"])
check_phrase("w_physical erf", "and **%.2f um** (erf)", "DERIVED",
             R["s1"]["erf"]["w_physical"])

# ------------------------------------------------------- DERIVED: commissioning
check_phrase("commission tally", "commissioned, %d/%d.**", "DERIVED",
             C["caught"], C["total"])
check_phrase("flat-plant closed form", "**%.4f sigma**", "DERIVED", C["sigma_flat_plant"])
check_phrase("flat-plant grid", "returned %.2f sigma", "DERIVED", C["sigma_flat_plant"])
check_phrase("real decreasing sigma", "at %.2f sigma", "DERIVED", C["sigma_real"])

# ------------------------------------------------------------------- REPORTED
check_phrase("turn-0 isotonic rise", "**%.3f um** by isotonic", "REPORTED",
             REPORTED["rise_iso_t0"] if "rise_iso_t0" in REPORTED
             else REPORTED["rise_iso_f56_t0"])
check_phrase("turn-0 erf rise", "**%.3f um** by an erf", "REPORTED",
             REPORTED["rise_erf_f56_t0"])
check_phrase("plateaus", "%.1f and %.1f DN", "REPORTED",
             REPORTED["plateau_hi"], REPORTED["plateau_lo"])
check_phrase("contrast", "contrast %.1f DN", "REPORTED", REPORTED["contrast"])
check_phrase("locus rows/cols", "rows `%s`, cols `%s`", "REPORTED",
             REPORTED["rows"], REPORTED["cols"])
for i, n in enumerate(("5.6", "8", "11")):
    check_phrase("ladder row N=%s" % n,
                 "| %s | %.2f +/- %.1f | %.2f +/- %.1f | %s |", "REPORTED",
                 n, REPORTED["rise_iso"][i], REPORTED["sd_iso"][i],
                 REPORTED["rise_erf"][i], REPORTED["sd_erf"][i],
                 REPORTED["frames"][i + 1])
check_phrase("template correlations", "(%.3f and %.3f;", "REPORTED",
             REPORTED["corr_f8"], REPORTED["corr_f11"])
check_phrase("plateau ratios", "ratios %.2f / %.2f / %.2f)", "REPORTED",
             *REPORTED["plateau_ratios"])
check_lit("source frame", "`%s.ARW`" % REPORTED["frames"][0], "REPORTED")
check_phrase("raggedness", "`%.2f%%` on its raggedness", "REPORTED", REPORTED["ragged"])

# --------------------------------------------------------------- DISCIPLINE
for label, needle in [
    ("records the universal negative is refuted", "universal negative is refuted"),
    ("states nothing is being retracted", "nothing here is being retracted"),
    ("states the verifier had no access to my code",
     "**not** my reduction code"),
    ("discloses the C2 error", "the bar was mine, not the instrument"),
    ("states the bar was not relaxed", "was not relaxed to make the control pass"),
    ("states the inference not the measurement was rechecked",
     "checks the inference, not the measurement"),
    ("states the verifier wrote no files", "verifier reported no files"),
    ("keeps the verifier's own caveat", "only moderate discrimination"),
    ("refuses to upgrade the claim", "deliberately does not make one"),
    ("names the second disqualification", "two independent disqualifications"),
    ("separates exercising from calibrating", "not usable for"),
]:
    check_lit(label, needle, "DISCIPLINE")

total = npass + nfail + nunres
print("=" * 74)
print("checks: %d   pass: %d   fail: %d   unresolved: %d   (sum %d)"
      % (total, npass, nfail, nunres, total))
print("STATUS: %s" % ("GREEN" if nfail == 0 and nunres == 0 else "RED"))
sys.exit(0 if (nfail == 0 and nunres == 0) else 1)
