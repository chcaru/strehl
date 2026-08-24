"""Fold M109's merge-dilution diagnosis, M111's soft gate + probe results,
M113's exit-code scope boundary, and ORCH's own audit findings.

Facts 1502-1510, disciplines 768-771.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1501 |")
disc_line = full_line(raw, "767. ")

NEW_FACTS = [
    (
        1502,
        "MEASURED",
        "M109",
        "**The residual magenta is a design limit of a post-merge equality guard, not a "
        "tuning gap.** On `dry-erase-marker-head-cpl`, 75 of 299 frames, green sensels: "
        "**21.02 %** of ever-pinned sensels are pinned in **every** frame, **78.98 %** in "
        "only **some**. **10.31 %** of the whole green plane is pinned in at least one "
        "frame. The pinned population grows **4.6x** across the sweep (178,987 -> "
        "816,158), so clip state is a property of the **frame**, not of the scene point. A "
        "sensel pinned in some frames but not others merges **strictly below** the "
        "ceiling, so `v_c >= ceil_c` never fires while green stays suppressed. `e9ad010` "
        "therefore removes the always-clipped subpopulation and **structurally cannot** "
        "remove the partially-clipped one. This also retires 'lower the trigger' on "
        "principle rather than caution: 10.31 % of the plane is pinned somewhere, so a low "
        "trigger reaches far beyond the defect.",
    ),
    (
        1503,
        "MEASURED",
        "M109",
        "**M109's registered bar B15 failed and was reported, not rewritten.** It predicted "
        "the always-pinned share would be comparable to the ~74.7 % the clip cleared; "
        "measured **21.02 %** -- wrong direction, not a near miss. M109 diagnosed the "
        "likely cause as its own denominator error (pinned fraction computed over all "
        "sampled frames, while the merge averages ~55 **focus-gated contributors**) and "
        "then **declined to assert the corrected figure because it had not measured it**. "
        "By the criterion registered before looking, merge-dilution is therefore **a "
        "mechanism, not the only one**.",
    ),
    (
        1504,
        "MEASURED",
        "M111",
        "**The soft admission gate is opt-in, proven by construction rather than by "
        "assertion.** `softgate.rs`: `w = exp(-0.5*((best-focus)/tol)^2)`, `tolerance()` "
        "**bit-identical** to `Gate::tolerance()` (preserving `FOCUS_NOISE_SD`'s unit -- "
        "the constraint M81's rejected route broke), Kish `n_eff` exact on 0/1 weights, "
        "tail truncated at `sqrt(32 ln 2) = 4.7096` (derived, not chosen). **18 tests, 5/5 "
        "mutations caught.** Control **NC8**: a module-present tree and a module-**deleted** "
        "tree both render `DB7BAAD2...`. No byte-freeze breaks, `DEFAULT_GATE` is not "
        "re-solved, and fact 19's 0.534x keeps its scope.",
    ),
    (
        1505,
        "MEASURED",
        "M111",
        "**The soft gate's falsifiable pre-render prediction HELD.** Soft `n_eff` in seam "
        "regions **1.59-2.14** versus texture **1.07-1.29** -- **disjoint**, which is the "
        "whole argument for why a soft weight repairs seams without softening texture. "
        "Both populations have boolean `n_eff` = 1.0, so the entire separation is in the "
        "numerator. Masks taken from the single-frame control alone, per discipline 752.",
    ),
    (
        1506,
        "MEASURED",
        "M111",
        "**A boolean `n_eff` map at gate `g` *is* the response-gap CDF at `g`.** So an "
        "existing gate ladder prices **any** monotone kernel by Stieltjes summation, with "
        "no new instrument. This is a general-purpose result: it makes future "
        "weighting-scheme proposals cheap to evaluate against data already on disk, and it "
        "is the instrument that should decide the Gaussian-versus-exponential question "
        "left open by fact 1498.",
    ),
    (
        1507,
        "MEASURED",
        "M113",
        "**Scope boundary on fact 1490, and it shrinks the remediation from a fleet-wide "
        "re-run to one shape.** The stale-`$LASTEXITCODE` defect requires an "
        "**early-terminating** pipeline element. Under adversarial priming on pwsh 7.6.5, "
        "`Select-Object -First` reproduces **both** directions (primed 0 + failing(3) reads "
        "**0**; primed 7 + succeeding(0) reads **7**), while `Select-String`, `Out-String "
        "-Stream`, and `Select-String \\| ForEach-Object` **all read the true code** -- they "
        "drain the stream, so the process is reaped. The correct fleet instruction is "
        "*re-run any gate whose pipeline contained `Select-Object -First`*, not *any "
        "truncated pipeline*.",
    ),
    (
        1508,
        "MEASURED",
        "M111",
        "**Two sharpenings of fact 1490, both consequential.** (a) The stale value is "
        "retained **verbatim**, not coerced to 1 -- 'reads 1' was an artefact of priming "
        "with 1; M111 measured a primed-5 shell returning **5** for a command that exited "
        "0. **Therefore no observed value signals a stale read**, and a plausible exit code "
        "is not evidence the read was live. (b) **`-Last` is safe where `-First` is not**: "
        "`-Last` cannot emit until the stream ends, so the process is always reaped. The "
        "rule agents need is `-First` versus `-Last`, not 'avoid truncation'.",
    ),
    (
        1509,
        "MEASURED",
        "ORCH",
        "**The owner's originals are intact, but agents have been writing to his drive.** "
        "`D:\\personal\\macro` and `D:\\macro-dark-frames`: **0 files written today**, "
        "verified by recursive mtime scan. However `D:\\m106-scratch` (**466 files, 16.9 "
        "GB**, created 09:21) and `D:\\strehl-scratch-m98` (empty, 04:53) were created by "
        "agents. Not a rule breach as the rule was written -- ORCH scoped 'strictly "
        "read-only' to the two named trees -- which is the defect. Nothing deleted: "
        "removing data from the owner's disk without asking is not ORCH's call.",
    ),
    (
        1510,
        "MEASURED",
        "ORCH",
        "**`HEAD` = `9c279d8` builds clean** -- `cargo check --workspace --all-targets`, "
        "exit 0, zero errors, zero warnings, isolated worktree, exit code captured on the "
        "line immediately after the process (the drain-safe shape of fact 1507). This is "
        "the second cold verification tonight and it now covers M97's `outlier.rs`. **The "
        "fact-1475 trap was armed and disarmed itself**: M111 twice reported `+pub mod "
        "outlier;` uncommitted against an untracked `outlier.rs`; by the time ORCH checked, "
        "M97 had committed **both**, and `git ls-tree HEAD` confirms the module is tracked.",
    ),
]

NEW_DISCS = [
    (
        768,
        "**Anchor an edit on a complete line, never on a sentence prefix.** A "
        "prefix-anchored replacement silently grafts the unmatched remainder of the line "
        "onto the end of the new text: **no error, no failed match, no lint violation**, "
        "and the result reads as plausible prose. M111 did it three times in one file -- "
        "twice grafting a bullet's tail onto a new bullet, once deleting four words -- and "
        "found all three only by reading the joined lines afterwards. Its repair commit "
        "showing **0 deletions** is what proved the fixes byte-exact. Same family as the "
        "rule against building `old_str` from truncated output, and it bites even when the "
        "text you can see is complete.",
    ),
    (
        769,
        "**A rate measured against the wrong denominator is not a weaker result, it is a "
        "different quantity.** M109's B15 predicted ~74.7 % and measured 21.02 % because "
        "it divided by all sampled frames while the merge averages ~55 focus-gated "
        "contributors. The temptation is to treat the gap as noise or as a partially "
        "confirmed hypothesis; it is neither, and the honest move -- which M109 made -- is "
        "to report the bar as failed, name the suspected denominator error, and **refuse to "
        "assert the corrected figure until it is measured** (fact 1503).",
    ),
    (
        770,
        "**When issuing a fleet-wide remediation order, measure its boundary before you "
        "send it.** ORCH told seven agents to re-run any gate built through a truncated "
        "pipeline. M113 spent two minutes on a positive control (reproducing the defect) "
        "plus a negative control on its own construct, and converted that into *re-run any "
        "gate that used `Select-Object -First`* -- provably excluding `Select-String` and "
        "`Out-String -Stream`, which the original order would have sent every agent to "
        "re-check for nothing. **An over-broad correction costs the fleet more than the "
        "defect did** (fact 1507).",
    ),
    (
        771,
        "**Scope a read-only constraint to the whole volume, not to named subtrees.** ORCH "
        "wrote '`D:\\personal\\macro` and `D:\\macro-dark-frames` are STRICTLY "
        "READ-ONLY'. Agents obeyed it exactly and then wrote **16.9 GB** of scratch "
        "elsewhere on the same personal drive, which no one had forbidden and no one had "
        "intended to permit. A constraint enumerated as a list of protected paths grants "
        "everything not enumerated. State the permitted **write** location instead -- "
        "outputs go to `C:\\dev\\strehl-out\\` -- because an allowlist cannot be "
        "under-enumerated in the dangerous direction (fact 1509).",
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

for fid, _, _, _ in NEW_FACTS:
    assert raw3.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw3.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw3)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
