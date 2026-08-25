"""Fold M118: lanczos3 wins the metric, but the metric is 88% a datasheet.

Facts 1670-1674, disciplines 852-853.
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
    assert len(hits) == 1, "entry %d appears %d times in %s" % (
        number, len(hits), lines[start].strip())
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)
    return lines[start].strip()


NEW_FACTS = [
    (
        1670,
        "MEASURED",
        "M118",
        "**LANCZOS-3 BEATS THE SHIPPED KERNEL END-TO-END -- AND 88 % OF THAT WIN CAN BE "
        "PREDICTED WITH NO IMAGE AT ALL.** The gain replicates: **+0.0868 dex** on "
        "`bee-3-cpl` (against M113's +0.083-0.099) and **+0.0859 to +0.1125** across three "
        "subjects. But a **closed form derived from `align.rs`'s own filter weights, "
        "given no photograph whatsoever**, predicts the per-cell result to a mean of "
        "**0.0155 dex** over 12 cells against a mean effect of **0.1300 dex**. **The "
        "photographs move the answer by 11.9 %.** The band metric is therefore reading the "
        "kernel's frequency response -- its datasheet -- rather than a property of the "
        "owner's captures.",
    ),
    (
        1671,
        "MEASURED",
        "M118",
        "**THE SHARPER KERNEL'S GAIN IS NOT CONCENTRATED WHERE THE DETAIL IS, ON ANY "
        "SUBJECT.** Rule 9's flat-decile control **fails for lanczos3 every time** -- the "
        "flat-region score meets or exceeds the detail-region score on all three subjects "
        "(**-0.0129 / -0.0002 / -0.0162 dex**). Corroborating this from the other "
        "direction, **`nearest` TOPS the band metric** (+0.1889 predicted and measured), "
        "**exactly as pre-registered**, which is precisely why the metric cannot be allowed "
        "to name a winner. ORCH's `N4` election-stratification probe was additionally "
        "measured to be **reading noise**: it reverses on one of three subjects, by 2.5 % "
        "of the effect, with the correlation's *sign* unstable at +0.382 / +0.059 / -0.293.",
    ),
    (
        1672,
        "MEASURED",
        "M118",
        "**BY EYE, THOUGH, LANCZOS-3 REALLY IS CRISPER -- AND IT MAKES THE COLOUR FRINGING "
        "WORSE.** A non-author read at 1:1 and x3 found it **visibly crisper** on ink grain "
        "and on the bee's ommatidia **with no dark rim on silhouettes**, while `lanczos2` "
        "is indistinguishable from the default and `bilinear` is clearly softest. The same "
        "read found it makes **lateral-CA fringes more conspicuous** -- **a second, "
        "independent sighting** of the interaction M110 reported and fact 1452 predicted, "
        "namely that the shipped `catmull-rom` has been suppressing that fringing **with "
        "blur**. Cost is **2.91x-3.92x** the default, as a bound. **So the CA correction is "
        "a prerequisite for the sharper kernel, not an independent tidy-up.**",
    ),
    (
        1673,
        "MEASURED",
        "M118",
        "**THE PIL HAZARD WOULD HAVE INVERTED THIS MILESTONE'S CENTRAL FINDING.** M118 was "
        "**not exposed** -- every read via `tifffile`, hashes taken on raw bytes -- but it "
        "re-ran the question anyway and reports that **had it used PIL, rule 9's flat-decile "
        "control would have SIGN-REVERSED**, turning fact 1671's *the gain is not where the "
        "detail is* into its opposite. This is the strongest single instance of fact 1648's "
        "directional bias: the 8-bit quantisation floor does not merely add noise, it "
        "**reverses the sign of a small difference between two nearly-equal quantities**, "
        "which is the exact shape of every control that compares a treatment region against "
        "a flat one.",
    ),
    (
        1674,
        "MEASURED",
        "M118",
        "**THE MERGE'S RESAMPLER IS NOT SELECTABLE FROM ANY COMMAND LINE.** `strehl stack "
        "--help` has **no `--resampler` flag**; the kernel is fixed by a literal in "
        "`align_cmd.rs::merge_config`, so the shipped `lanczos2` enum variant is "
        "**unreachable except through a sidecar**. This blocks promotion on ORCH's own G3: "
        "a **2.91x-3.92x** cost increase must be declinable before it can be imposed. M118 "
        "therefore **declined to move the default**, recommending the flag land first -- "
        "and handed over the `align_cmd.rs` diff **rather than applying it**, because that "
        "file belongs to another milestone.",
    ),
]

NEW_DISCS = [
    (
        852,
        "**BEFORE A METRIC IS ALLOWED TO JUSTIFY A DEFAULT, ASK WHAT IT READS WITH NO DATA "
        "IN IT.** M118 derived a closed form from `align.rs`'s filter weights alone and "
        "predicted its own headline to within **12 %** of the effect, **with no photograph "
        "involved** (fact 1670). A metric that can be computed from the algorithm's "
        "coefficients is measuring **the algorithm's datasheet**, not the images -- and it "
        "will rank kernels in the order their frequency responses predict no matter what "
        "the subject is, which is why `nearest` tops it. **The test is cheap and general: "
        "compute the metric analytically, or on a blank/random field, and subtract. What "
        "remains is the part that is about the photographs.** Same family as fact 1444's "
        "circular mask and M115's scene-free SNR of 84.9: **an instrument that cannot tell "
        "you it has no data will happily report a result.**",
    ),
    (
        853,
        "**WHEN A CHANGE IS BLOCKED ON A MISSING FLAG, LAND THE FLAG BEFORE THE CHANGE, AND "
        "HAND OVER THE DIFF RATHER THAN APPLYING IT ACROSS AN OWNERSHIP BOUNDARY.** M118 "
        "measured a real by-eye improvement and still **declined to promote it**, because "
        "the cost is **2.91x-3.92x** and there is no way for an operator to say no (fact "
        "1674). It then wrote the enabling `align_cmd.rs` diff and **handed it to the "
        "milestone that owns that file instead of applying it**, in a tree where several "
        "agents edit concurrently. **A quality change that cannot be declined is not a "
        "default, it is a tax**; and a correct patch applied across an ownership boundary "
        "is still a clobber.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = [fact_row(*f) for f in NEW_FACTS]
disc_block = ["%d. %s" % d for d in NEW_DISCS]

for line in fact_block:
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])
for line in fact_block + disc_block:
    stripped = _re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in line:
        o = ord(ch)
        assert not (o < 0x20 or o == 0x7F), "control char 0x%02X in %s" % (o, line[:60])

s1 = insert_after_fact_row(1669, fact_block)
s2 = insert_after_entry(851, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))
