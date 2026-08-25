"""Fold M111's halo-claim audit -- which refutes ORCH's blur hypothesis and the
halo recommendation ORCH built on it.

Facts 1595-1602, disciplines 821-823.

Every one of the four load-bearing findings was already in M87's report before
ORCH sent two messages of confident direction about it.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1594 |")
disc_line = full_line(raw, "820. ")

NEW_FACTS = [
    (
        1595,
        "MEASURED",
        "M111",
        "**ORCH'S BLUR CONFOUND FOR THE HALO CORRECTION IS REFUTED, AND M87 HAD ALREADY "
        "RUN ORCH'S EXPERIMENT -- BETTER -- BEFORE ORCH PROPOSED IT.** M87 bisected a "
        "Gaussian until its **coarse**-band suppression matched the correction's to "
        "**4e-12** (`0.9145749511849404` against `0.9145749511806655`), then raced the two "
        "on the **fine** band. Pure blur needs **sigma = 5.108 px** and retains only "
        "**20.46 %** of the fine band against the correction's **90.58 %** -- a "
        "**blur-match factor of 4.428**. **M87 pre-registered BMF <= 1.05 in the script "
        "docstring, in ORCH's direction, then measured 4.43 and recorded the refutation "
        "against itself.** Independently, a Catmull-Rom gather destroying ~49 % of "
        "gradient energy moves the halo metric by **+0.6 %, positive**: the metric is a "
        "median **level** profile against distance and is not a sharpness proxy at all.",
    ),
    (
        1596,
        "MEASURED",
        "M111",
        "**THE 87.9 % / 84.6 % HEADLINE IS FROM A PIPELINE THE PROJECT DOES NOT SHIP.** "
        "M87 section 16.9 records those figures as **ROI crops of an UNALIGNED, GATE-0 "
        "merge**. On the shipped path -- full frame, aligned, gate 2 -- the figure is "
        "**72.9 %**. ORCH promoted the headline to the fleet and to the owner's morning "
        "brief **fifteen points high**, in two successive messages, without reading the "
        "section that qualifies it.",
    ),
    (
        1597,
        "MEASURED",
        "M111",
        "**AND THE REPORT'S OWN AUTHOR RECOMMENDS AGAINST ENABLING IT.** M87 section 16.9 "
        "is *titled* **'why I am telling you not to enable it'**. Its finding: the fringe "
        "is replaced by a **'smooth, milky, scalloped band'** and **'it looks worse'**. A "
        "later withdrawal softens the proposed *mechanism* only, and explicitly records "
        "that **'the conclusion -- do not enable this by default -- stands'**; sections "
        "24.5, 25.9 and 28.7 cite it standing and 25.9 makes it binding on the successor. "
        "**ORCH spent two messages promoting a feature whose own author had already "
        "concluded the opposite.**",
    ),
    (
        1598,
        "MEASURED",
        "M111",
        "**THE CORRECTION FIRES HARDEST WHERE THERE IS NOTHING TO FIX.** On a "
        "**non-occluding** control the treated-pixel fraction is **1.000 at every dose**, "
        "against **0.394** on the real occluding scene -- **2.5x more aggressive on a "
        "scene containing no occlusion**. Worse, on that control the apparent improvement "
        "is **non-monotone in dose** (**-186.6 % / -142.0 % / +63.9 %** at d10/d20/d40) "
        "while the error against ground truth rises **monotonically** (**+215.9 % / "
        "+354.4 % / +558.4 %**). **It makes a region with no halo 2.9x worse before it "
        "appears to improve it**, and the apparent +63.9 % is a band rewritten into "
        "flatness. The dose ladder ORCH asked M116 to build already existed, on ground "
        "truth, and is pathological.",
    ),
    (
        1599,
        "MEASURED",
        "M111",
        "**ORCH DESIGNED A SECOND BIASED CONTROL ONE MESSAGE AFTER BEING TAUGHT THE "
        "LESSON, BIASED THE SAME WAY.** ORCH proposed forbidding the **far** frames "
        "instead of the near ones as a blur-matched placebo. **The count is wrong**: the "
        "treatment forbids `\\|k - k_F\\| < 40`, which is **79 of 299** frames, so the "
        "complement excludes **220** -- **2.8x** as many. **And it is aimed wrong**: "
        "near-silhouette background pixels **inherit the foreground's election**, so the "
        "near band targets the frames those pixels actually elect, while a displaced band "
        "mostly **misses** -- it under-treats, under-blurs, and scores near zero **by "
        "construction**. Same bias structure as the tangential placebo (fact 1584), "
        "pointing the same way: **toward vindicating the treatment**.",
    ),
    (
        1600,
        "MEASURED",
        "M111",
        "**THE REAL CONFOUND IS SILHOUETTE-KEYING, NOT BLUR -- the correction cannot "
        "distinguish thin bright structure ATTACHED to the subject from background VEILED "
        "by it.** That control already exists and the correction already failed it: at a "
        "planted **non-occluding** disc, **85.4 %** of treated pixels moved, against "
        "**82.1 %** at a real occluding edge. And the metric cannot police it -- it "
        "returns indistinguishable verdicts on reconstructions whose true error differs by "
        "**six orders of magnitude** (RMSE **33117** against **0.0171**). M87's binding "
        "rule follows: **no halo-removal arm may be certified on that metric alone.**",
    ),
    (
        1601,
        "MEASURED",
        "M111",
        "**`DELTA = 40` IS NOT BELOW THE BLUR THRESHOLD -- it is merely below the "
        "threshold that was visible on the crops inspected.** It destroys **9.4 % of the "
        "fine band at the damage site** on the shipped frame. M87's own summary: **'none "
        "of these three is good; d40 is the least-bad point on a ladder every rung of "
        "which raises error against truth.'** ORCH's question of whether `40` was safe or "
        "merely untested has the answer **neither**: it is measured, and measured to cost "
        "detail.",
    ),
    (
        1602,
        "MEASURED",
        "M111",
        "**A NEGATIVE CONTROL CAUGHT A DEFECT IN THE VERIFIER ITSELF: seven of seven "
        "planted defects were caught, ALL of them by one arm, while the only arm that "
        "opens the source file had never once fired.** M111's guard checks a claim by "
        "literal presence **and** by numeric comparison; the presence arm short-circuits "
        "first, so **7/7 GREEN was reported by an instrument half of which was inert**. "
        "Three further plants placed into a *copy* of the source were required to prove "
        "the second arm live. **An arm that never fires is indistinguishable from one that "
        "cannot.** The same guard also caught its owner writing **-141.9 %** where "
        "141.95215 rounds to **-142.0 %**.",
    ),
]

NEW_DISCS = [
    (
        821,
        "**Read the source section, not the headline -- and read the report's own "
        "conclusion before promoting its number.** ORCH twice directed the fleet on the "
        "halo correction using a figure that the report qualifies as an unshipped "
        "pipeline (fact 1596), from a section *titled* with the opposite recommendation "
        "(fact 1597). Nothing was hidden; ORCH did not look. **A headline is written to "
        "be quotable and a conclusion is written to be acted on**, and when a corpus "
        "grows past the point where any one reader holds it, quoting the first without "
        "checking the second becomes the default failure rather than an unusual one.",
    ),
    (
        822,
        "**Prove that every arm of a multi-arm check fires, individually, or you do not "
        "know which arm produced your green.** M111's guard reported 7/7 caught with half "
        "of itself inert, because the cheap arm short-circuited ahead of the expensive one "
        "(fact 1602). **An arm that never fires is indistinguishable from one that "
        "cannot.** The commissioning test is per-arm, not per-suite: plant a defect that "
        "**only** arm N can see, and require arm N to be the one that reports it.",
    ),
    (
        823,
        "**Before commissioning an experiment, search the corpus for whether it has "
        "already been run.** ORCH designed a blur control for the halo correction that "
        "M87 had already built, matched **1000x more precisely** than ORCH specified, and "
        "**pre-registered against its own author's expectation** before measuring the "
        "opposite (fact 1595). The cost was two misdirected messages and nearly a wasted "
        "measurement campaign. **In a corpus this size the prior-art search is cheaper "
        "than the experiment**, and the search that matters is for the *question*, not "
        "for the milestone that happened to ask it.",
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
    for line in block.split("\n"):
        stripped = _re.sub(r"`[^`]*`", "", line)
        assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
