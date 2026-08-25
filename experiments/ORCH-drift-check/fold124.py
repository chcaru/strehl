"""Fold M97m (election map) and M97n (warp cache key) -- both had 0 citations.

Facts 1561-1566, disciplines 807-808.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1560 |")
disc_line = full_line(raw, "806. ")

NEW_FACTS = [
    (
        1561,
        "MEASURED",
        "M97n",
        "**THE WARP CACHE KEY DID NOT COVER ITS OWN INPUTS: IDENTICAL COMMAND LINES "
        "PRODUCED DIFFERENT RENDERS DEPENDING ON WHAT HAD RUN BEFORE.** The shared warp-map "
        "cache was keyed on the **capture path alone**, so two solves of one bracket under "
        "different configurations occupied a single entry and a differently-configured "
        "solve of the *same frames* passed `check_stack` and was served silently. "
        "Identical `stack` command lines gave **`DB43E708...` or `ADF81E01...`** according "
        "to whether an `align --reference 40` had run first. Post-fix the same poisoning "
        "sequence leaves the render at `07C067E438F74D77` and the poisoning solve occupies "
        "a **second** entry.",
    ),
    (
        1562,
        "DERIVED",
        "ORCH",
        "**Fact 1561 is a corpus-validity hazard and the audit HAS NOT BEEN DONE.** Any "
        "A/B measurement taken **before** M97n's fix, in which two arms differed by an "
        "alignment configuration while sharing a capture path, could have been served a "
        "poisoned cache entry -- and the symptom is that the arms agree when they should "
        "differ, or differ when they should agree, with **no error and no warning**. M97n "
        "establishes only that the fix moves no frozen render (S5); it makes no claim "
        "about historical measurements. **Treat any pre-fix cross-configuration comparison "
        "on a shared capture path as unverified until re-run**, and prefer private cache "
        "paths per arm from here on.",
    ),
    (
        1563,
        "MEASURED",
        "M97n",
        "**A knob added an hour earlier was already poisoning the cache, which is the "
        "general shape of this defect.** `STREHL_SMOOTH` and `STREHL_SMOOTH_HUBER` changed "
        "the solved warps while **keying nothing**. The fix binds them to a named constant "
        "with a comment tying future knobs to it. The fix also preserves the cache "
        "**hit** (`alignment: ON (sidecar)`), so removing the silent substitution did not "
        "buy a re-solve on every run.",
    ),
    (
        1564,
        "MEASURED",
        "M97m",
        "**The election map is spatially structured at 23.2x a value-preserving shuffle of "
        "itself, which is what licenses reading its boundary statistics as a property of "
        "the merge.** On 12 frames of `109MSDCF` with alignment off, **3.33 %** of "
        "horizontal and **3.34 %** of vertical adjacent pixel pairs elect different frames, "
        "against **77.41 %** for a shuffle of the same values; **71.4 %** of boundaries are "
        "single-frame steps with median jump 1 frame. The export moves no pixel "
        "(`F240C1933CF08A4C` with the flag, without it, and via the env var), planted "
        "against a 13-frame arm that does move it.",
    ),
    (
        1565,
        "MEASURED",
        "M97n",
        "**A pre-registered bar that fails may indict the PREDICTION rather than the "
        "subject -- and this one failed because its premise came from a STALE BINARY'S "
        "`--help`.** Bar C4 predicted behaviour for `align`'s unspecified reference; the "
        "source resolves it to the middle frame. The bar was reported failed and the "
        "premise corrected, rather than the bar being quietly restated.",
    ),
    (
        1566,
        "MEASURED",
        "ORCH",
        "**UNCITED-REPORT SWEEP COMPLETE: seven milestone reports were sitting in "
        "`docs/research/` with zero citations in this file** -- `M107b`, `M97r`, `M97q`, "
        "`M97p`, `M97o`, `M97m`, `M97n` -- and folding them produced facts 1534-1565 and "
        "disciplines 793-808, including the reachability finding (1553-1555), the "
        "dead-code mechanism (1547), the retraction of M99's +6.88 % headline (1551) and "
        "the cache-poisoning hazard (1561-1562). **A written report is not a folded "
        "finding.** The sweep is one command and had the highest yield of the night.",
    ),
]

NEW_DISCS = [
    (
        807,
        "**A cache key must cover every input that can change the cached artefact, and the "
        "only honest test is adversarial poisoning: run the identical command after "
        "different histories and compare hashes.** Keying on the capture path alone let "
        "one bracket's two configurations share an entry and produced two different "
        "renders from one command line (fact 1561). A knob added an hour before was "
        "already poisoning it (fact 1563). **Every new tuning knob is a cache-key change "
        "until proven otherwise** -- bind it to the key in the same commit that adds it, "
        "and when running measurement arms, give each arm a private cache path.",
    ),
    (
        808,
        "**Derive a bar's premise from the SOURCE, never from a binary's `--help` -- the "
        "binary may be stale.** M97n's C4 failed for exactly this reason (fact 1565). The "
        "companion rule is the response: **when a pre-registered bar fails, first ask "
        "whether the prediction was wrong**, and if it was, report the bar as failed and "
        "correct the premise in the open. Silently restating the bar to match the observed "
        "behaviour destroys the entire value of pre-registration.",
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
