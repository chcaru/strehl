"""Fold M103 (PIL exposure re-run + the gauge) and M119 (gear identity).

Facts 1688-1698, disciplines 859-863.

M103's contribution is not that it was exposed -- I predicted that -- but that it
found the GAUGE that predicts the damage, and that its negative control read
CLEANER than the truth, which is the failure mode I warned the fleet about
arriving as a headline control number.

M119's contribution is a bound on the CA feature I recommended to the owner
tonight: the shipped profile key names four elements and the file evidences two.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    lines = fh.read().split("\n")


def section_bounds(pattern):
    hits = [i for i, l in enumerate(lines) if _re.match(pattern, l)]
    assert hits, "no section heading matching %r" % pattern
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
    return "fact table"


def insert_after_entry(number, section_pattern, block):
    start, end = section_bounds(section_pattern)
    hits = [i for i in range(start, end) if lines[i].startswith("%d. " % number)]
    assert len(hits) == 1, "entry %d appears %d times" % (number, len(hits))
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)
    return lines[start].strip()


NEW_FACTS = [
    (
        1688,
        "MEASURED",
        "M103",
        "**THE PIL EXPOSURE WAS REAL, THE RE-RUN MOVED EVERY ABSOLUTE, AND THE "
        "CONCLUSION SURVIVED.** M103's section 17 decider chain ran downstream of the "
        "8-bit narrowing (`waxy.py` read PNG crops written by `crop2.py`). Re-run "
        "with `tifffile`: bright shipped flatness **3.7324 -> 4.8411**, bright "
        "corrected **3.0837 -> 3.9515** -- both published values wrong -- while the "
        "**corrected/shipped ratio moved only 0.8262 -> 0.8162, 1.2%**, and the "
        "conclusion (the shipped render is more piecewise-flat than the corrected "
        "one; the blobs are not created by the correction) **stands and is "
        "marginally stronger**. The repair is controlled: PIL's conversion is "
        "exactly `>>8`, so all four preview PNGs stayed **SHA-256 identical** and "
        "geometry was unchanged (lock NCC **0.8243 vs 0.8242**).",
    ),
    (
        1689,
        "MEASURED",
        "M103",
        "**THE NEGATIVE CONTROL READ CLEANER THAN THE TRUTH -- THE PREDICTED WORST "
        "CASE, ARRIVING AS A HEADLINE NUMBER.** M103's natural-blurred plant read "
        "**+0.0006 at 8 bits and +0.0114 at 16 bits**: the blur's effect on "
        "`sigma(5)` was **smaller than the quantisation step and was rounded away**. "
        "The published separations were therefore in large part a measurement of the "
        "truncation rather than of the instrument -- **97.4x -> 24.2x** whole crop "
        "(inflated **4.0x**) and **959.5x -> 90.4x** on the bright subset (inflated "
        "**10.6x**). ORCH's broadcast warned that a narrowed reader makes a real "
        "effect 'read as zero, as noise, or -- worst -- as a clean null'; this is "
        "that prediction landing on the control that was supposed to catch it.",
    ),
    (
        1690,
        "MEASURED",
        "M103",
        "**THE GAUGE THAT PREDICTS QUANTISATION DAMAGE IS THE OCCUPIED RANGE OF THE "
        "LOCAL WINDOW THE STATISTIC INTEGRATES OVER -- NOT OF THE FILE, AND NOT OF "
        "THE ROI.** M103's ROI lost **11 542 -> 93 distinct levels**, a 124.1x loss "
        "that *'looks survivable and is the wrong gauge'*. The decisive number is "
        "one level down: `sigma(5)` in the flattest quartile (blob interiors) is "
        "**322.834 DN = 1.2611 DN in 8-bit units**, against a quantisation step of "
        "**1.0** and the instrument's own `FLOOR` of 0.5. **The decider's "
        "denominator was 1.26 quantisation steps** -- not 'inside the quantisation "
        "error' as a figure of speech but literally. **The ROI held 93 levels and "
        "the 5x5 windows the denominator was computed from held 1.26**; it is the "
        "second number that decides.",
    ),
    (
        1691,
        "MEASURED",
        "M103",
        "**UNDER A QUANTISATION FLOOR, A RATIO OF UNEQUAL QUANTITIES COMPRESSES "
        "TOWARD 1 IN BOTH DIRECTIONS.** ORCH measured that **small-over-large** "
        "ratios compress toward 1, failing toward a clean null. M103 measured the "
        "mirror: `sigma(31)/sigma(5)` is **large-over-small**, the floor lands on "
        "the denominator, and it compresses the same way (**3.7324 published vs "
        "4.8411 true**). The single gauge in fact 1690 predicts all three "
        "distortions at once -- the compressed ratio, the inflated separations, and "
        "the protection of the two-arm ratio, which moved **-1.2% against ORCH's "
        "independently planted -1.0%**: two independent estimates of the same "
        "cancellation.",
    ),
    (
        1692,
        "MEASURED",
        "M119",
        "**THE SHIPPED PROFILE KEY NAMES FOUR ELEMENTS AND THE FILE SUPPLIES "
        "EVIDENCE FOR TWO.** `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl` denotes body, "
        "lens, teleconverter and CPL. Measured across all 24 corpus macro stacks: "
        "`Make`=`SONY`, `Model`=`ILCE-7CM2`, `LensModel`=`FE 100mm F2.8 Macro GM OSS "
        "+ 2X Teleconverter` -- so body and lens+TC are extractable, **the substring "
        "`a7c2` occurs in no field at all** (it is a human label, not a datum), and "
        "**the CPL is invisible**: the `-cpl` stacks and the bare stacks are "
        "**byte-identical in every identity field**. A filter in front of the lens "
        "cannot be seen by the body.",
    ),
    (
        1693,
        "UNDETERMINED",
        "M119",
        "**THE LOAD-BEARING UNKNOWN FOR THE CA FEATURE: MAY LATERAL CA MEASURED "
        "*WITH* THE X4 CPL BE APPLIED TO A CAPTURE *WITHOUT* IT?** Unknown, and by "
        "fact 1692 **unknowable from the file** -- the software cannot detect which "
        "case it is in. Every CA number in this corpus was measured on `-cpl` "
        "captures. This bounds the recommendation ORCH gave the owner: the "
        "correction is evidenced for the frames it was measured on, and its "
        "transfer to bare-lens frames is neither measured nor detectable.",
    ),
    (
        1694,
        "MEASURED",
        "M119",
        "**A CENSUS OF 8920 ARW FILES YIELDS EXACTLY TWO LENS STRINGS, AND NEITHER "
        "IS A BARE FE-100.** 4484 TC-rig and 4436 `24-70mm F2.8 DG DN` under "
        "`D:\\personal`. The teleconverter is encoded **twice** -- named in the "
        "`LensModel` text and distinguished by `LensType3` (**32893** bare vs the "
        "TC value) -- so the discriminator has demonstrated power. But **no "
        "bare-FE-100 capture exists anywhere in the owner's library**, so that a "
        "genuine bare capture would report 32893 is `ARGUED`: **the decoder is "
        "measured and the encoder is inferred.** `LensType` reads 65535 (uniformly "
        "useless) and `LensType2` reads 0 on 22 of 24.",
    ),
    (
        1695,
        "MEASURED",
        "M119",
        "**THE PARSER IS VERIFIED AGAINST AN INDEPENDENT IMPLEMENTATION, COSTS "
        "NOTHING, AND CHANGES NO OUTPUT BYTE.** A Rust-vs-`exiftool` cross-check over "
        "**56 real files x 8 fields = 448 field comparisons**; extraction costs "
        "**0.418 ms/frame** over 299 frames by seeking a few hundred bytes rather "
        "than decoding; and rendering `wrapped-text-1 --limit 12 --gate 4.0` with the "
        "parser present is **byte-identical**. **No dependency was added -- the "
        "parser is `std` only**, which matters because fact 26's licence hygiene "
        "forbids pulling a GPL EXIF crate onto the default path.",
    ),
    (
        1696,
        "MEASURED",
        "M119",
        "**THE TEST BASELINE IN ORCH'S BRIEF WAS WRONG.** At `8a46b47` the suite is "
        "**454 passed / 0 failed / 1 ignored**, not the 449 ORCH quoted. Folded "
        "because a stale baseline is how a regression hides: five tests could be "
        "deleted and the count would still 'match'.",
    ),
    (
        1697,
        "ARGUED",
        "M119",
        "**THAT OFFSET `0x0009` OF TAG `0x940c` DENOTES `LensType3` ON SONY BODIES "
        "GENERALLY.** Verified on **one** body (ILCE-7CM2). The derivation is "
        "implemented as a `const fn` **with a stated derivation and a test** rather "
        "than a copied lookup table -- which is both the licence-clean route and the "
        "falsifiable one, since a formula can be wrong in a way a table cannot be "
        "checked for. **On another body this may be a different tag.**",
    ),
]

NEW_DISCIPLINES = [
    (
        859,
        "**When a reader may have narrowed your data, the number that predicts the "
        "damage is the occupied range of the LOCAL WINDOW your statistic integrates "
        "over -- not the file's, and not the ROI's.** M103's ROI kept 93 of 11 542 "
        "levels, which reads as survivable; the 5x5 windows its denominator actually "
        "came from held **1.26 levels against a quantisation step of 1.0**. Compute "
        "the ratio *your smallest integration window's spread : the quantisation "
        "step*. Below about 10 the statistic is measuring the truncation.",
    ),
    (
        860,
        "**A quantisation floor compresses ANY ratio of unequal quantities toward 1, "
        "whichever way up it is written.** Small-over-large fails toward a clean "
        "null; large-over-small understates the effect (M103: 3.7324 published "
        "against 4.8411 true). **So 'my statistic is a ratio, so it cancels' is only "
        "true when the two terms are comparable in size** -- a two-arm ratio on the "
        "same data is protected (-1.2% measured against a -1.0% plant), a ratio "
        "across scales is not. Ask which two numbers are being divided before "
        "claiming cancellation.",
    ),
    (
        861,
        "**A hardware-keyed profile must ship its identification alongside its data, "
        "and the identifier must denote the composed system, not the lens.** M119's "
        "`a7c2-fe100gm-2xtc-x4cpl` is four claims in a string, of which the file "
        "evidences two and one (`a7c2`) appears nowhere in any field. **An "
        "identifier that cannot be checked against the file is a label, and a label "
        "that looks like a key invites the software to assert what it cannot "
        "verify.**",
    ),
    (
        862,
        "**A gear-match predicate must be three-valued, and `unknown` must be "
        "un-collapsible at the type level.** Matching wrongly applies a correction "
        "measured on other glass; failing to match silently declines a correction "
        "the user asked for. Both are bad and they are different, so `bool` is the "
        "wrong return type. This is the same class as `STREHL_FIX_CA`'s silent "
        "no-op under `STREHL_ALIGN=0` -- **byte-identical output with no warning is "
        "`unknown` collapsed into `no`.**",
    ),
    (
        863,
        "**Derive a vendor's obfuscation as a formula with a test, not as a copied "
        "table.** Five lines of `const fn` with a stated derivation is licence-clean "
        "where a transcribed lookup table is not, and -- the part that matters for "
        "correctness -- **a formula is falsifiable**: it can be shown wrong on a new "
        "body, whereas a table can only be found to be missing a row. M119 flagged "
        "its own single-body verification as `ARGUED` because of exactly this.",
    ),
]

log = []
for number, status, source, text in NEW_FACTS:
    row = "| %d | %s | %s | %s |" % (number, status, source, text)
    assert row.count("|") == 5, "fact %d: pipe count %d" % (number, row.count("|"))
    assert _re.sub(r"`[^`]*`", "", row).count("**") % 2 == 0, "fact %d: bold" % number
    for ch in row:
        assert ch == "\t" or ord(ch) >= 32, "fact %d: control char" % number
    log.append((number, row))

dlog = []
for number, text in NEW_DISCIPLINES:
    entry = "%d. %s" % (number, text)
    assert _re.sub(r"`[^`]*`", "", entry).count("**") % 2 == 0, "disc %d: bold" % number
    for ch in entry:
        assert ch == "\t" or ord(ch) >= 32, "disc %d: control char" % number
    dlog.append((number, entry))

prev = 1687
for number, row in log:
    where = insert_after_fact_row(prev, [row])
    prev = number
    print("fact %d -> %s" % (number, where))

dprev = 858
for number, entry in dlog:
    where = insert_after_entry(dprev, r"^## 5\. ", [entry])
    dprev = number
    print("discipline %d -> %s" % (number, where))

out = "\n".join(lines)
for number, _ in log:
    assert len([l for l in lines if l.startswith("| %d |" % number)]) == 1, number
for number, _ in dlog:
    assert out.count("\n%d. " % number) == 1, number

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(out)
print("wrote %s" % PATH)
