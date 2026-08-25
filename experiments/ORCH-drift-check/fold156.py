"""Fold V-M113: the triage rule ORCH broadcast is wrong, and the better one.

Facts 1710-1715, disciplines 871-873. Amends fact 1488 (PowerShell backticks).

ORCH's two triage questions -- is the statistic absolute, does it divide small
by large -- both answer YES for M113's estimator, which predicted maximal
vulnerability. It moved -0.4%. The rule is not merely imprecise, it points the
wrong way for an entire class, and it is ORCH's rule.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()

lines = raw.split("\n")


def section_bounds(pattern):
    hits = [i for i, l in enumerate(lines) if _re.match(pattern, l)]
    assert hits
    start = hits[-1]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if _re.match(r"^#{1,3} ", lines[i]):
            end = i
            break
    return start, end


def insert_after_fact_row(number, block):
    hits = [i for i, l in enumerate(lines) if l.startswith("| %d |" % number)]
    assert len(hits) == 1, "fact row %d appears %d times" % (number, len(hits))
    for k, text in enumerate(block):
        lines.insert(hits[0] + 1 + k, text)


def insert_after_entry(number, section_pattern, block):
    start, end = section_bounds(section_pattern)
    hits = [i for i in range(start, end) if lines[i].startswith("%d. " % number)]
    assert len(hits) == 1, "entry %d appears %d times" % (number, len(hits))
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)


NEW_FACTS = [
    (
        1710,
        "REFUTED",
        "V-M113",
        "**ORCH'S BROADCAST TRIAGE RULE FALSE-POSITIVES, AND IT IS ORCH'S RULE.** "
        "The two questions ORCH sent the fleet -- *is my statistic absolute?* and "
        "*does it divide a small quantity by a large one?* -- **both answer YES** "
        "for M113's `eps`, a ~0.1 px displacement over a ~2000 px radius. Predicted "
        "maximally vulnerable. **Measured under a 118x narrowing (6522 -> 55 levels "
        "per window): `needed_R` moved -0.4% / +0.1% and the headline "
        "between-scene difference retained 102.2%.** Had the milestone answered "
        "from the rule instead of planting the defect, **it would have re-run "
        "correct work** -- the same cost, and the same direction of error, as the "
        "`ca_radial.py` false positive.",
    ),
    (
        1711,
        "DERIVED",
        "V-M113",
        "**THE CORRECT DISCRIMINATOR IS WHETHER THE STATISTIC READS PIXEL *VALUE* "
        "OR FEATURE *POSITION*, NOT WHETHER IT IS ABSOLUTE OR A RATIO.** A "
        "displacement estimator is a **location** statistic: quantisation error is "
        "zero-mean and uncorrelated with sub-pixel position, texture dithers it, "
        "and ~600 windows average it away. Noise power and band SNR are "
        "**dispersion** statistics and absorb quantisation variance **directly**. "
        "That is why they behave oppositely under the same narrowing, and it "
        "subsumes both of ORCH's questions: the bias holds to **+2.1% at a step of "
        "8192 DN** while `rms` on the same data degrades **2.8x**.",
    ),
    (
        1712,
        "MEASURED",
        "V-M113",
        "**THE IMMUNITY IS BOUNDED AND THE BOUNDARY WAS MEASURED: IT ENDS NEAR 12 "
        "DISTINCT LEVELS PER FITTED WINDOW.** Below that the location statistic "
        "fails, and fails quietly: **-43.0% at 4 levels** and a full **sign "
        "inversion at 2 levels (-155.4%, -203%)**. At 4 levels it returns a "
        "**confident, plausible, 43%-low number** -- the dangerous failure rather "
        "than a loud one. **M121's nine-level low-contrast case sits inside this "
        "failing regime**, so fact 1711's immunity must never be quoted without "
        "this bound attached.",
    ),
    (
        1713,
        "MEASURED",
        "V-M113",
        "**A SUPPORT FLOOR ALREADY IN THE SHIPPED CODE CONVERTS THE SILENT FAILURE "
        "INTO A REFUSAL TO FIT.** All three cases where the unfloored estimator "
        "returned a confident wrong number either **refuse to fit or stay accurate** "
        "at the shipped `MIN_EDGE_ENERGY = 60.0` (K=60 and K=150 produce *no fit*, "
        "on 5 and 16 windows). The protection is **graded rather than binary**: at "
        "K=20 the estimate is still 17% low, but the window count collapsing "
        "**605 -> 144** is the visible warning. **A threshold that refuses is worth "
        "more than a threshold that corrects**, because the refusal is legible and "
        "the correction is not.",
    ),
    (
        1714,
        "MEASURED",
        "V-M113",
        "**A CONTROL WHOSE SAMPLING SATURATES HAS TESTED NOTHING, AND IT PRINTED "
        "'NOT CONFIRMED'.** `s12`'s floor sweep saturated at **693 windows -- the "
        "entire 21x33 grid** -- so **no smooth window was ever excluded** and the "
        "control could not fire; it then reported a clean negative. `bee-3-cpl` has "
        "no smooth content to exclude, so the condition had to be manufactured by a "
        "separate script. **The giveaway was visible from the first run: a count "
        "that stops changing while the parameter keeps moving.**",
    ),
    (
        1715,
        "MEASURED",
        "V-M113",
        "**FACT 1488 IS TOO NARROW: A BACKTICK ESCAPES IN *ANY* DOUBLE-QUOTED "
        "POWERSHELL STRING, NOT ONLY IN A HERE-STRING.** An anchor written as "
        "`\"its \\`bits == {16}\\` ...\"` became a **backspace byte** followed by "
        "`its `; the guarded edit then refused, correctly. **Agents across this "
        "fleet have been guarding `@\"...\"@` and leaving ordinary double-quoted "
        "strings open**, which is the same defect with no guard in front of it.",
    ),
]

NEW_DISCIPLINES = [
    (
        871,
        "**To triage a statistic against a narrowed reader, ask whether it reads "
        "pixel *value* or feature *position* -- not whether it is absolute or a "
        "ratio.** Location statistics (displacements, centroids, peak positions) "
        "dither and average out; dispersion statistics (noise power, sd, SNR, "
        "band energy) absorb the quantisation variance directly. This **replaces** "
        "ORCH's absolute/ratio rule, which false-positived on a location estimator "
        "and would have caused correct work to be re-run.",
    ),
    (
        872,
        "**Immunity claims must carry the level count at which they expire.** "
        "M113's location estimator is immune down to roughly **12 distinct levels "
        "per fitted window** and then fails hard -- **-43% at 4 levels, sign "
        "inverted at 2** -- while still returning confident, plausible numbers. "
        "An unqualified 'location statistics are safe' is a licence to trust the "
        "regime where it is most wrong. **State the boundary or do not state the "
        "immunity.**",
    ),
    (
        873,
        "**Watch for a control whose sampling saturates: a count that stops changing "
        "while its parameter keeps moving means the control is testing nothing, and "
        "it will report a clean negative.** M113's floor sweep admitted the whole "
        "693-window grid at every setting and printed 'NOT CONFIRMED'. **Log the "
        "sample count of every control at every level and require it to vary** -- "
        "this is the same class as a plant the harness cannot express, and it is "
        "cheaper to detect.",
    ),
]

log = []
for number, status, source, text in NEW_FACTS:
    row = "| %d | %s | %s | %s |" % (number, status, source, text)
    assert row.count("|") == 5, "fact %d: pipe count %d" % (number, row.count("|"))
    assert _re.sub(r"`[^`]*`", "", row).count("**") % 2 == 0, "fact %d: bold" % number
    log.append((number, row))

dlog = []
for number, text in NEW_DISCIPLINES:
    entry = "%d. %s" % (number, text)
    assert _re.sub(r"`[^`]*`", "", entry).count("**") % 2 == 0, "disc %d: bold" % number
    dlog.append((number, entry))

prev = 1709
for number, row in log:
    insert_after_fact_row(prev, [row])
    prev = number
    print("fact %d" % number)

dprev = 870
for number, entry in dlog:
    insert_after_entry(dprev, r"^## 5\. ", [entry])
    dprev = number
    print("discipline %d" % number)

out = "\n".join(lines)
for number, _ in log:
    assert len([l for l in lines if l.startswith("| %d |" % number)]) == 1, number
for number, _ in dlog:
    assert out.count("\n%d. " % number) == 1, number

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(out)
print("wrote %s" % PATH)
