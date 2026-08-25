"""Fold M97o (refused frames) and M97p (n_eff map) -- both had 0 citations.

Facts 1556-1560, disciplines 805-806.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1555 |")
disc_line = full_line(raw, "804. ")

NEW_FACTS = [
    (
        1556,
        "MEASURED",
        "M97o",
        "**A SINGLE UNPLACEABLE FRAME COULD DESTROY AN ENTIRE RENDER, AND NOW CANNOT.** "
        "Pre-fix, a sidecar carrying 8 refused frames aborted the run with **exit 1 and no "
        "file written**; post-fix the same input renders the remaining 71 and exits 0. On "
        "a 299-frame bracket that failure mode costs the whole capture. Frame-level "
        "refusal **does not occur on any capture in this corpus** (four sidecars, 0 refused "
        "lines each), so this ships **zero pixel change** on the owner's stacks -- its "
        "value is entirely in the failure mode it removes.",
    ),
    (
        1557,
        "MEASURED",
        "M97o",
        "**Dropping frames is byte-exact on refusal-free data, and the drop is visible to "
        "the merge's own statistics when it does happen.** The aligned byte-freeze row "
        "`coffee-bean-20-gate2-sidecar` reproduces `119936E6...` at 20 placed / 0 refused: "
        "zero refusals in, zero bytes changed, 5/5. When 8 of 79 are dropped, mean `n_eff` "
        "moves **1.154 -> 1.131** and the coverage scale **0.9708 -> 0.9710** -- so the "
        "drop reaches the merge estimator and the coverage solve, not merely a frame "
        "counter. The plant confirms the hash *can* move (`DE0825B7...` vs `9AB8BC3A...`).",
    ),
    (
        1558,
        "MEASURED",
        "M97p",
        "**An exported diagnostic map is proven CONNECTED, not merely present, by "
        "cross-checking it against an independently-computed scalar at TWO settings.** The "
        "`n_eff` map's mean reproduces the `mean n_eff` that `report()` computes by a "
        "**different code path** to **0.00026 at gate 4 and 0.00047 at gate 2** -- and the "
        "two means are **far apart (4.563 vs 2.829)**. A constant buffer, a stale buffer or "
        "an off-by-one field could match one printed scalar by luck; none can match two "
        "that differ by 1.7 frames. The export itself perturbs nothing: three invocations "
        "differing only in whether the map was requested all produce `09FA927898ABF314`, "
        "and the plant shows that null is not vacuous (gate 2 moves it to "
        "`360634D92341C3CA`).",
    ),
    (
        1559,
        "MEASURED",
        "M97p",
        "**The gate is genuinely intermediate on real data -- neither pure selection nor a "
        "flat mean.** On `flat-on-ruler-cpl --limit 20 --gate 4` the `n_eff` field spans "
        "the full `1..20` with **all 20 counts present**, mean 4.563. DERIVED: since the "
        "same stack at 79 frames reported mean `n_eff` **1.154**, `n_eff` is **not a fixed "
        "fraction of bracket length**, which is consistent with M52's refutation of fact "
        "324's stated mechanism.",
    ),
    (
        1560,
        "MEASURED",
        "M97o+M97p",
        "**TWO INDEPENDENT MILESTONES CONVERGED ON THE SAME REFUSAL: a guard that never "
        "fired is UNEXERCISED, not PASSED.** M97p's `n_eff` range guard (E4) never saw a "
        "value outside `1..=frames_folded`; M97q's region guard (F4) never fired because "
        "the ruler stack keeps 68.2 % of pixels after erosion. **Both were recorded as "
        "live paths with no real-data evidence rather than marked PASS** -- explicitly "
        "invoking the disconnected-probe error (fact 1548), where a bar and its own plant "
        "both read exactly 0 and the bar looked like a clean null.",
    ),
]

NEW_DISCS = [
    (
        805,
        "**To prove an instrument is connected, cross-check it against a quantity computed "
        "by a DIFFERENT code path, at TWO settings that give clearly different answers.** "
        "An 'export exists and looks plausible' check cannot distinguish a live probe from "
        "a constant, a stale buffer or an off-by-one field; agreement to ~3e-4 with an "
        "independently-computed scalar at **both** gate 4 (4.563) and gate 2 (2.829) can "
        "(fact 1558). This is the direct antidote to the dead-code failure of fact 1547: "
        "**one agreement is a coincidence budget, two that differ is a measurement.**",
    ),
    (
        806,
        "**Report a guard that never fired as UNEXERCISED, never as PASS.** Two milestones "
        "reached this independently on the same night (fact 1560). A guard reported PASS on "
        "the strength of never having been reached is the disconnected-probe error in its "
        "purest form -- the same error that made a bar and its own plant both read exactly "
        "0 px and nearly shipped as a headline null (fact 1548). **The honest status of an "
        "unfired guard is 'live path, no real-data evidence'.**",
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
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert out.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert out.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
