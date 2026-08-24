"""Reconcile ORCH's by-eye fringe width (fact 1500) with the measured lateral
displacement (fact 1512), and record the by-eye read of the corrected arm plus the
placebo gap that read exposes.

Facts 1518-1519, disciplines 778-779.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1517 |")
disc_line = full_line(raw, "777. ")

NEW_FACTS = [
    (
        1518,
        "ARGUED",
        "ORCH",
        "**A colour fringe's WIDTH measures the edge's blur, not the channel "
        "misregistration; only its AMPLITUDE measures the misregistration.** Fact 1500 "
        "reported fringes **2-4 px wide** by eye; fact 1512 measures the lateral "
        "displacement at **0.155 px** peak. These are **not in conflict**, and the "
        "apparent conflict is instructive. A displacement `d` against a local gradient "
        "`g` produces a chroma error of amplitude `~d*g` spread across **the whole edge "
        "transition**, so on an edge blurred over 4 px -- which these diffraction- and "
        "defocus-limited renders are -- a 0.155 px misregistration yields a 4 px-wide "
        "fringe. **The naive inference `wide fringe therefore large displacement` is "
        "wrong by a factor of ~25 here**, and acting on it would call for a correction "
        "coefficient 25x too large. ORCH made exactly that inference and caught it only "
        "by having measured the displacement first.",
    ),
    (
        1519,
        "MEASURED",
        "ORCH",
        "**The lateral-CA correction is visibly effective by eye, but the arm set cannot "
        "yet separate the correction from its own resampler.** On ORCH's paired "
        "identically-tone-mapped crops of M114's `off.tif` vs `on.tif` (r=0.50 hairs and "
        "r=0.83 wing membrane, 3x nearest upscale), the **red/cyan speckle on fine "
        "high-contrast micro-texture is substantially reduced** in the corrected arm and "
        "the residual reads as neutral grey rather than opposed colour -- consistent with "
        "the 55 % reduction in displacement magnitude (0.155 -> 0.069 px) of fact 1512. "
        "**However:** applying the correction necessarily **resamples** R and B, which "
        "low-passes them, and single-sensel chroma speckle is exactly what a mild "
        "low-pass suppresses. M114's `zero` arm **cannot** isolate this, because it is "
        "byte-identical to `off` (fact 1517) -- the code short-circuits rather than "
        "resampling by zero. **The missing placebo is a tangentially-rotated correction "
        "of equal magnitude**, which incurs the identical interpolation blur while "
        "correcting nothing radial.",
    ),
]

NEW_DISCS = [
    (
        778,
        "**Do not read a defect's magnitude off its apparent extent.** A fringe, a halo "
        "and a seam all have a width set by the local blur and an amplitude set by the "
        "underlying error; the eye reports width and the fix needs amplitude (fact 1518). "
        "The failure mode is not mis-seeing -- ORCH's 2-4 px observation was accurate -- "
        "it is the silent inference from extent to magnitude, which here would have been "
        "wrong by 25x. Measure the quantity the fix is parameterised in, in the units the "
        "fix is parameterised in.",
    ),
    (
        779,
        "**A strength-zero arm is not a placebo for a correction that resamples.** If the "
        "implementation short-circuits at zero strength -- which is good engineering and "
        "is provable here, since `zero` is byte-identical to `off` (fact 1517) -- then the "
        "zero arm omits the resampling too, and any improvement attributable to "
        "interpolation blur rather than to the correction itself remains **completely "
        "invisible to the arm set**. The placebo must preserve the operation and destroy "
        "only the hypothesis: apply the same magnitude in a direction the physics forbids "
        "(here, tangentially), so the blur is identical and the correction is nil.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block):
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "fold text contains 0x%02X" % o

raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"
raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

# Cross-reference fact 1500 so the width figure cannot be read as a displacement.
f1500 = full_line(raw3, "| 1500 |")
assert f1500.endswith(" |"), "fact 1500 line does not end as a table row"
marked = f1500[:-1] + "**See fact 1518: the 2-4 px figure is the fringe's WIDTH, which " \
                      "is set by the edge blur. The lateral displacement is 0.155 px " \
                      "(fact 1512). Do not read this width as a misregistration.** |"
raw4 = raw3.replace(f1500, marked, 1)
assert raw4 != raw3, "fact 1500 cross-reference did not land"
assert raw4.count("the 2-4 px figure is the fringe's WIDTH") == 1, "marker not unique"

for fid, _, _, _ in NEW_FACTS:
    assert raw4.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw4.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw4)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("cross-referenced fact 1500")
