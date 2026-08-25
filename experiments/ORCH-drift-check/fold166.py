"""ORCH fold 166: M117-cache-audit.

The material result is an ALL-CLEAR: no published measurement in the corpus is
corrupted by the alignment-nesting hazard. The instructive result is that M117
found a structurally-blind check inside its own audit -- the same defect the
audit existed to hunt.

Source: docs/research/M117-cache-audit.md (commit d1992dc).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1753 | MEASURED | M117 | **ALL-CLEAR ON THE NESTING HAZARD: NO MEASUREMENT IN 163 REPORTS SET AN ALIGNMENT-NESTED GATE WHILE ALIGNMENT WAS OFF.** ORCH had warned the fleet that `STREHL_FIX_CA` under `STREHL_ALIGN=0` is a silent byte-identical no-op, so any CA effect measured that way measured nothing. M117 swept the corpus and found **zero** such measurements, with both controls passing (positive fires, negative silent). It also **reproduced the nesting from source independently** rather than taking ORCH's word: `active_profile()` has two callers, one a preflight that validates and discards, the other `warp_frame_in_place`, whose single production call site is `merge_cmd.rs:982` inside `if let Some(map) = self.warps` -- alignment off yields `None` and the block never runs. **The hazard is real and the corpus is clean of it.** |
| 1754 | MEASURED | M117 | **M117 POINTED A CHECK AT A FIELD STRUCTURALLY INCAPABLE OF SEEING THE PERTURBATION -- INSIDE THE AUDIT THAT EXISTED TO HUNT THAT EXACT FAILURE.** Its cache census cleared six entries by reading `reference` from the sidecar header, but the header carries only `reference / strategy / resampler` and **no smoothing field**, while `STREHL_SMOOTH`/`_HUBER` were the other unkeyed axis. **The clearance could not have failed regardless of the truth.** M117 found this itself, graded it a defect in its own report (X19), and closed it by re-clearing against **whole-file identity with independent clean re-solves** -- which compares *coefficients rather than headers* and therefore covers every axis including smoothing. Two of three in-window entries close that way (the count was also corrected from two to three); the third is a 6-frame stack on a vanished path, orphaned by the key change and **consumed by no published fact**. |
| 1755 | MEASURED | M117 | **THE DISCIPLINE THAT MAKES THIS CORPUS AUDITABLE IS WHAT DEFEATS NAIVE AUDITING OF IT.** M117's token scan for `an alignment-nested gate set while alignment is off` **false-positived on M97n's rule-47 record**: rule 47 requires a report to declare every environment variable it used **including the unset ones**, so a presence test for a variable name matches the very records that prove the variable was *not* set. A grep cannot distinguish a use from a declaration of non-use. The same shape recurred three ways tonight -- a `PIL` grep matching `com*pil*ing`, a docstring *warning* about a hazard, and a probe *written to demonstrate* it. **A corpus that documents its negatives cannot be audited by presence tests; the audit must read what the token does, not that it occurs.** |
| 1756 | MEASURED | M117 | **M117'S OWN NULLS ARE SOUND BECAUSE OF THE FORMAT, NOT BECAUSE OF THE STATISTIC -- AND IT SAID SO AGAINST ITS OWN INTEREST.** Its E1/E2 checks are exact byte equality rather than statistics, and they discriminate to **1 ULP** only because the sidecar stores `format!(\\"{:016x}\\", v.to_bits())` and reads back through `f64::from_bits`. Its own words: *"Had it printed six decimals, my byte-identity method would have produced exactly the same reassuring nulls and they would have meant nothing."* Its single ratio, `rms/mean`, has a two-image difference floor of `sqrt(2/12) = 0.408 DN`, which quadrature-removed from **117.969** gives **117.9683** -- an exposure of **6e-6**. **Stated gap, volunteered:** the HEAD null is a `uint16` hash comparison, so a hypothetical sub-0.5-DN residual would hide inside it; it is corroborated by a floor-free two-key check at the sidecar level, but the hash arm alone does not prove it. |
"""

NEW_DISCIPLINES = """903. **BEFORE TRUSTING A CLEARANCE, ASK WHAT THE CHECK WOULD HAVE READ HAD THE DEFECT BEEN PRESENT.** Fact 1754: a census that reads a header field can only ever clear an axis the header records. M117's sidecar header had no smoothing field, so its smoothing clearance was structurally incapable of failing -- and this happened *inside* the audit commissioned to find exactly that class of blindness. **The test is not `did it pass` but `could it have failed`**, and the repair is to re-clear against an artefact that carries the perturbed quantity by construction: whole-file identity over coefficients, not agreement over summaries. This is the same medicine as commissioning a checker with planted defects, applied to a check that was never commissioned at all.
904. **A PRESENCE TEST CANNOT AUDIT A CORPUS THAT DOCUMENTS ITS NEGATIVES.** Fact 1755. Rule 47 makes reports declare unset variables, so searching for a variable name finds the proofs of absence alongside the instances of use; a `PIL` grep finds `compiling`, hazard warnings, and probes written to demonstrate the hazard. **Four distinct false-positive classes were observed in one night, and every one reads as a hit.** Any hazard sweep must therefore (a) resolve what happens to the matched token -- is it used, declared unused, warned about, or demonstrated? -- and (b) **report its false-positive count alongside its hit count**, because a sweep whose precision is unstated cannot be acted on.
905. **A VERIFIER THAT REPORTS A DEFECT IN ITS OWN INSTRUMENT IS WORTH MORE THAN ONE THAT REPORTS A CLEAN CORPUS.** M117 delivered an all-clear (fact 1753) and led instead with X19, a flaw in its own method, then volunteered the residual gap its strongest null cannot close (fact 1756). It also chased `the number that does not fit` -- a sharper claim it liked, that refusals would make CA apply partially -- and reported it **empty**, because M97o measured zero refused frames corpus-wide; recorded as dormant rather than live. **Grade a verification by how hard it tried to invalidate itself, not by the verdict it returned**, and treat a verifier that never finds a defect in its own instrument as unaudited rather than as lucky.
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    j = txt.index("\n", i) + 1
    return txt[:j] + block + txt[j:]


def insert_after_discipline(n, block, txt):
    anchor = f"\n{n}. **"
    i = txt.index(anchor)
    j = txt.index("\n", i + 1) + 1
    return txt[:j] + block + txt[j:]


text = insert_after_fact_row(1752, NEW_FACTS, text)
text = insert_after_discipline(902, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold166 OK: facts 1753-1756, disciplines 903-905")
print("  ALL-CLEAR: 0 of 163 reports corrupted by the nesting hazard;")
print("  M117 found a structurally-blind check inside its own audit")
