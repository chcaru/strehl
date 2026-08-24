"""Fold 34 -- M92b, the blast radius of the ISO defect.

Two jobs:
  (a) apply M92b's six verbatim amendments to existing corpus entries, and the
      M82 ledger row;
  (b) fold M92b's new findings as facts and disciplines.

Every amendment asserts its BEFORE fragment occurs exactly once, so a silent
miss is impossible. All asserts run before any file is written.
"""
import io
import re

SYN = "docs/research/SYNTHESIS.md"
AG = "AGENTS.md"

syn = io.open(SYN, encoding="utf-8").read()
ag = io.open(AG, encoding="utf-8").read()

# ---------------------------------------------------------------- amendments
AMEND = [
    ("fact 811",
     "PR13/14 noise null reads **0.343 px where the truth is exactly 0**.",
     "PR13/14 noise null reads **0.343 px where the truth is exactly 0** -- "
     "**CONTAMINATED, see fact 1242: that figure is a single draw measured "
     "with 1.7587x too much injected noise; the corrected null is 0.089-0.094 "
     "px**."),
    ("fact 1140",
     "**maximum absolute magnitude 0.1754 px against M82's frozen 0.343 px "
     "bound** taken from M57's measured independent-noise null -- **51.1% of "
     "the bound**",
     "**maximum absolute magnitude 0.1754 px against M82's frozen 0.343 px "
     "bound** taken from M57's measured independent-noise null -- **51.1% of "
     "the bound** (**the bound is contaminated: facts 1241-1243 correct it to "
     "0.089-0.094 px, at which the 0.1754 px effect is readable at N = 1 and "
     "the 18 abstentions are not entitled**)"),
    ("fact 1186",
     "`dsig`, whose noise null had to be *measured* and then failed at 0.343 px",
     "`dsig`, whose noise null had to be *measured* and then failed at 0.343 "
     "px (**contaminated; corrected to 0.089-0.094 px by fact 1242 -- the "
     "contrast with an analytic null stands, the number does not**)"),
    ("fact 1207",
     "fails its own noise null at 0.343 px where truth is exactly zero",
     "fails its own noise null at 0.343 px where truth is exactly zero "
     "(**contaminated figure; see fact 1242**)"),
    ("discipline 590",
     "`dsig` -- whose null had to be measured and then **failed at 0.343 px**, "
     "abstaining 18 of 18 rows",
     "`dsig` -- whose null had to be measured and then **failed at 0.343 px**, "
     "abstaining 18 of 18 rows (**and the measured null was itself wrong by "
     "1.7587x, fact 1242 -- which strengthens this discipline rather than "
     "weakening it: a fitted null can be wrong in a way a theorem cannot**)"),
]

for name, before, after in AMEND:
    n = syn.count(before)
    assert n == 1, "%s: BEFORE fragment occurs %d times, need exactly 1" % (name, n)
    syn = syn.replace(before, after, 1)

# Fact 130 is quoted in the report with a smart-dash and a `g` backtick; locate
# it by its two invariant numbers instead of by a long literal.
i130 = syn.find("| 130 |")
assert i130 > 0, "fact 130 row not found"
j130 = syn.index("\n", i130)
row130 = syn[i130:j130]
assert "22.9 DN" in row130 and "43.2" in row130, row130[:200]
new130 = row130.replace(
    "temporal \u03c3 caps at **22.9 DN**",
    "temporal \u03c3 caps at **32.41 DN** (**corrected by M92b: the original "
    "22.9 DN used `g`=0.1145, the ISO-50 gain M25 later refuted; the corrected "
    "`g`=0.22894 raises the cap 1.41x**)", 1)
assert new130 != row130, "fact 130 cap fragment did not match:\n" + row130[:400]
new130 = new130.replace(
    "fact 88 reports 43.2-53.1 DN",
    "fact 88 reports 43.2-53.1 DN, still above the corrected cap by 1.33x-1.64x, "
    "**so the refutation stands unchanged**", 1)
syn = syn[:i130] + new130 + syn[j130:]

# --------------------------------------------------------------- M82 ledger
m82 = ag.find("| `M82` |")
assert m82 > 0, "M82 ledger row not found"
e82 = ag.index("\n", m82)
row82 = ag[m82:e82]
assert row82.rstrip().endswith("|"), row82[-80:]
add82 = (" **M92b: the 0.343 px bound this milestone froze is contaminated "
         "(facts 1241-1243). M82's own 0.1754 px effect clears the corrected "
         "null at N = 1; its 18 abstentions were caused by the bound, not by "
         "the instrument.** |")
ag = ag[:m82] + row82.rstrip()[:-1].rstrip() + add82 + ag[e82:]

# ------------------------------------------------------------- disciplines
DISC = [
    "**An audit of a defect class must classify its hits by *role*, not count "
    "them.** M92b found 31 sensor constants disagreeing with their stack's "
    "EXIF, of which **exactly 3** were defects: 20 fed the deliberately frozen "
    "detail operator, where disagreement with EXIF is rule 15 working as "
    "designed, and 4 defined synthetic plants, where there is no truth to "
    "disagree with. The unclassified headline -- \"31 defects\" -- would have "
    "invited someone to correct 20 frozen constants and silently break every "
    "cross-milestone comparison in the corpus. **The classification is the "
    "audit; the count is not.**",
    "**Control a guard against planted *non*-defects as well as planted "
    "defects, because a guard that over-fires gets disabled.** M92b's "
    "`check_tree()` scored 10 of 10 only because two of those cases were "
    "correct constants it was required to **ignore** -- one right-by-EXIF, one "
    "operator-only. A guard proven solely against true positives has an "
    "unmeasured false-positive rate, and the first time it blocks legitimate "
    "work someone turns it off, which costs more than never having written it.",
    "**A bare stack name is not an identifier.** `119MSDCF` exists under two "
    "different roots at **ISO 50 and ISO 400** -- a 4x gain difference -- so "
    "resolving a stack by directory name alone silently selects the wrong "
    "sensor constants. This defeated M92b's own ground-truth table on its "
    "first run. Key a stack by root **and** name, and read the constant from "
    "EXIF rather than from a lookup keyed on the name.",
    "**Point a new scanner at the defect you already know about before you "
    "trust what it says about the ones you do not.** M92b's first revision "
    "reported **0 instances tree-wide** (wrong root) and its second missed "
    "**tuple unpacking** -- which is precisely how `s7_bias_or_variance.py:44` "
    "concealed its `ISO = 500`. Fixing that one blind spot moved the count "
    "from **121 to 254**. A scanner that cannot find the known instance is "
    "reporting its own coverage, not the tree's contents.",
]

FACTS = [
    "| 1267 | **THE ISO DEFECT'S BLAST RADIUS IS BOUNDED AND SMALLER THAN "
    "FACT 1242 IMPLIED: OF 254 SENSOR-CONSTANT ASSIGNMENTS ACROSS 165 FILES, "
    "31 DISAGREE WITH THEIR STACK'S EXIF AND ONLY 3 ARE DEFECTS.** All three "
    "are the already-known M57 S5/S6/S7 instances. Of the remaining 28, **20 "
    "feed the frozen detail operator**, where disagreement with EXIF is rule "
    "15 behaving correctly, and **4 define synthetic plants**, where there is "
    "no truth to disagree with. Of every contaminated number, **none changes a "
    "conclusion** beyond the three already retracted. | Fact 1242 left the "
    "sentence *\"any future use of M57's S5/S6/S7 numbers ... inherits this\"* "
    "sitting in the corpus as an unpriced liability, and the honest resolution "
    "was as likely to be *worse* as better. It is better, but the "
    "classification matters more than the number: an audit that reported "
    "\"31 defects\" would have invited a correction pass over 20 deliberately "
    "frozen constants. | M92b (MEASURED, whole experiment tree); "
    "`docs/research/M92b-iso-blast-radius.md` |",

    "| 1268 | **A SECOND, OLDER INSTANCE OF THE ISO DEFECT EXISTS AND WAS "
    "NEVER RECORDED: `m41-r3-kill/src/a11_metric_power.py:66` APPLIES M25'S "
    "*REFUTED* ISO-50 GAIN TO REAL `119MSDCF` PLANES, UNDERSTATING INJECTED "
    "NOISE BY 1.4199x.** The direction is conservative for a11's own "
    "failure-to-detect claims -- too little noise makes detection easier, so a "
    "reported failure to detect survives the correction. | It predates M57, "
    "which means the class was never a single author's slip. It also uses a "
    "gain the corpus had already refuted, so the defect is not merely "
    "hard-coding but hard-coding a *retracted* value -- exactly what an "
    "EXIF-reading assertion makes impossible. **Open and explicitly not "
    "smoothed:** whether fact 477's absolute recovery ratios move under the "
    "correction. M92b derived that fact 478's `(1 - rho)` law is invariant "
    "and did not re-run m41. | M92b (MEASURED; one open consequence); "
    "`docs/research/M92b-iso-blast-radius.md` §5.1, §10 |",

    "| 1269 | **ONE CONSTANT CAN SERVE TWO INCOMPATIBLE CONTRACTS AT ONCE, AND "
    "THEN IT CANNOT BE CORRECTED IN PLACE.** `M55 e2` assigns a single "
    "`G, RN_E` pair that feeds **both a physical sensor model** (which must "
    "track EXIF) **and the frozen detail operator** (which must not). As a "
    "number it is inert -- 1.0014x from correct -- but as a structure it is "
    "live: fixing it for one contract breaks the other. | This is the shape of "
    "defect an audit finds only by tracing *use sites* rather than "
    "assignments, and M92b's own first revision hid it behind role precedence "
    "before the author caught it. The corpus-level lesson is that rule 15's "
    "frozen operator and the calibrated noise model must not read from a "
    "shared symbol, however convenient. | M92b (MEASURED, structural); "
    "`docs/research/M92b-iso-blast-radius.md` §5.2 |",

    "| 1270 | **A REGISTRATION-TIME GUARD MAKES THE ISO DEFECT CLASS "
    "IMPOSSIBLE, AND IT IS ADOPTABLE TODAY.** `sensor_for()` / "
    "`assert_sensor()` read the constant from EXIF rather than accepting a "
    "literal; `check_tree()` fails **SENSOR-role** mismatches only. With the "
    "allowlist off it goes **RED on exactly the 3 known M57 assignments** and "
    "nothing else; with them carried it is green, so it can be turned on "
    "without a cleanup pass first. Controls **6/6 (S11) and 10/10 (S14)**, "
    "including **two planted defects on the live tree that it caught** and "
    "**two planted non-defects it correctly ignored**. | This is the "
    "M78b-shaped remedy the orchestrator asked for -- make the class "
    "impossible at registration time rather than add a review habit -- and it "
    "is proven by a falsifying control in both directions rather than "
    "asserted. | M92b (MEASURED, 16 control cases); "
    "`docs/research/M92b-iso-blast-radius.md` §7, §8 |",
]

# ------------------------------------------------------------------- splice
L = syn.split("\n")
d = max(i for i, l in enumerate(L) if re.match(r"^6\d\d\. ", l))
assert L[d].startswith("616. "), L[d][:60]
f = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[f].startswith("| 1266 |"), L[f][:60]
assert d < f or d > f, "discipline and fact anchors collided"

for k, row in enumerate(FACTS):
    assert len(re.findall(r"(?<!\\)\|", row)) == 5, "fact %d pipes" % k
DROWS = ["%d. %s" % (617 + k, t) for k, t in enumerate(DISC)]

# Splice the HIGHER line index first, or the earlier insert invalidates the
# later one. In this document §5's disciplines sit below the fact table.
assert d != f
for idx, rows in sorted([(d, DROWS), (f, FACTS)], reverse=True):
    L[idx + 1:idx + 1] = rows

io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
io.open(AG, "w", encoding="utf-8", newline="\n").write(ag)
print("SYNTHESIS: 5 amendments + fact 130 + facts 1267-1270 + disciplines 617-620")
print("AGENTS.md: M82 ledger row annotated")
