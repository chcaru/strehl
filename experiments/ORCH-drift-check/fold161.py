"""ORCH fold 161: M85 (reports filed under M95-*).

Three results and one indictment of ORCH:

  1. The combination stage is ELIMINATED. The merge emits the elected frame
     byte-exactly, so nothing is lost there.
  2. M85 RETRACTED its own kernel headline, which removes the measured basis
     for ever promoting a sharper resampler by default.
  3. Election QUALITY is now the last surviving sharpness suspect.
  4. ORCH's broadcasts consumed hours of a top agent's time.
"""
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1735 | MEASURED | M85 | **THE COMBINATION STAGE IS ELIMINATED: THE MERGE EMITS THE FRAME IT ELECTED, BYTE-EXACTLY.** Over **180,697 px** across 47 frame/ROI combinations, the merged output equals the elected source frame **100.0000 %** exactly, max deviation **0 DN of 65535**; per-ROI ratios all `1.000000` on 12/57,977, 16/59,648 and 19/63,072. Coverage **99.9413 / 99.9409 / 99.9676 / 99.9176 %** over 288/292/195/298 distinct frames, residual median **1 DN**, and the election behaves as a depth map (median deviation **0.00** frames; outliers **0.81/0.52/0.44 %** on detail against **2.04 %** on flat). The discriminating control is decisive: elected pixels match at **100.0000 %** while unelected match at **0.0519 %**, and degrading the election drops coverage **99.9413 -> 10.1360 %**. Verifier caught **18/18** planted errors. Source: `M95-merge-vs-frame-sharpness.md`. **With the gate and halo results, every part of the combination stage is now ruled out as a place detail could be lost.** |
| 1736 | MEASURED | M85 | **M85 RETRACTED ITS OWN KERNEL HEADLINE, AND THE RETRACTION REMOVES THE MEASURED BASIS FOR EVER PROMOTING A SHARPER RESAMPLER BY DEFAULT.** The band its `+0.1160 dex` resampler result was scored in -- 0.30-0.48 cyc/px -- is **12.8 % subject detail (CI 12.2-13.4) and 87.2 % noise**. The placebo that proves it: a **dark frame, with no photograph in it at all**, read essentially the same gain (**1.0006**), and the defocus null read **+0.0033**. **`+0.1160 dex` is WITHDRAWN.** Consequence for a live decision: M124 noted that `ORCH-kernel-decision.md`'s **G3 is now met**, which makes a default kernel change *cheaper* -- **this retraction makes it unjustified**. `G3 met` must not be read as `go`. Source: `M95-kernel.md`. |
| 1737 | MEASURED | M85 | **ELECTION QUALITY IS THE LAST SURVIVING SHARPNESS SUSPECT, AND IT IS UNRUN.** M85 proved the merge faithfully emits *the frame it elected* (fact 1735); it did **not** prove the pipeline elects the *best* frame. Every other candidate is now closed: deconvolution headroom is a commissioned null (fact 1731), the combination stage is byte-exact (fact 1735), and the halo is a **selection** artefact rather than an averaging one -- established twice from opposite directions (M121's gate 0 = gate 4, **+0.0658 vs +0.0634**; M87's removal at **`n_eff` = 1.000**). **So if the render is less sharp than the sharpest captured frame, the focus measure is choosing a slightly-defocused frame, or there is nothing left to find.** ORCH authorised the oracle test on this basis; ground truth must not derive from the statistic under test, or the result is circular by construction. |
| 1738 | MEASURED | M85 | **M85 REPORTED ITS FAILURES AND RETIRED A RESULT THAT FLATTERED IT.** Reported as failures rather than omitted: **R1b 41.0 % at 1.50 px** against a +/-25 % bar; **F1**, an ROI rule that aliased past a focus peak at 61.8x contrast; **F3**, a geometry control that failed 2 of 3 ROIs with offsets (0,+37), (+147,-46), (-1,+2). Retired as confounded rather than published: sigma_eq **-0.7504 / -0.4846 / -0.5587 px**, which read **"the merge is sharper"** and was seam energy from an unaligned collage. **That reading was in the direction M85 wanted and it killed it anyway** -- the discipline ORCH's own fold was measured failing (fact 1721, 8 of 8 errors in the flattering direction). |
| 1739 | ARGUED | ORCH | **ORCH'S BROADCASTS CONVERTED A MEASUREMENT AGENT INTO A CORRESPONDENCE CLERK FOR HOURS, AND THE AGENT HAD TO SAY SO.** M85: *"My milestone work finished hours ago; both reports were filed (04:49 and 19:26). Since then the time went to six orchestrator broadcasts, each of which I audited against my own files rather than assert immunity ... I was not stuck; I was answering mail."* Compounding it, **three of those rounds propagated ORCH's triage rule, which is now withdrawn as refuted three times over** (discipline 885) -- so a share of the mail was not merely costly but **wrong**. The agent's behaviour was exactly what ORCH had asked for, which means the cost is entirely orchestration's. Remedy applied: M85 exempted from any broadcast that does not name it, addressees made explicit, corrections batched. Labelled ARGUED because the hours lost are attested, not instrumented. |
"""

NEW_DISCIPLINES = """889. **A FLEET BROADCAST IS A WRITE TO EVERY AGENT'S CRITICAL PATH; PRICE IT THAT WAY.** Fact 1739 measures the bill: six broadcasts, hours of a top agent's time, and the agent could not opt out because auditing rather than asserting immunity is exactly what it had been told to do. **Address broadcasts explicitly, exempt agents that have filed, and batch corrections.** And note the multiplier -- a broadcast that is *wrong* costs the fleet the audit AND the rework, so the bar for sending one must be higher than the bar for believing one.
890. **`CHEAPER TO DO` AND `JUSTIFIED TO DO` ARE DIFFERENT GATES, AND A REPORT SHOULD SAY WHICH ONE IT MOVED.** M124 lowered the cost of changing the resampler default (a flag now exists, the default is pinned to a committed fixture) and correctly said only that. M85 then withdrew the evidence that a change would help (fact 1736). **A decision record that tracks only feasibility will read `G3 met` and go.** When you retract a measurement that supports a pending decision, name the decision document in the retraction -- the retraction is the thing that must travel, and it does not travel by itself.
891. **A PLACEBO THAT CONTAINS NO SUBJECT AT ALL IS THE STRONGEST FORM OF THIS CONTROL.** M85 killed its own headline by scoring a **dark frame** -- no photograph in it -- through the identical channel and reading essentially the same gain (1.0006 against the claimed effect). No argument about scene content, ROI choice or tuning survives that. **When a metric's band may be noise-dominated, run the metric on data with no signal in it before you run it on a rival method.**
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    eol = txt.index("\n", i)
    return txt[: eol + 1] + block + txt[eol + 1 :]


text = insert_after_fact_row(1734, NEW_FACTS, text)

m = re.search(r"^888\. .*?(?=\n\d+\. |\n## )", text, re.S | re.M)
assert m, "discipline 888 not found"
text = text[: m.end()] + "\n" + NEW_DISCIPLINES.rstrip() + text[m.end() :]

# ---------------------------------------------------------------- assertions

assert text != orig, "no change"
for n in (1735, 1736, 1737, 1738):
    assert text.count(f"| {n} | MEASURED | M85 |") == 1, f"fact {n}"
assert text.count("| 1739 | ARGUED | ORCH |") == 1, "fact 1739 must be ARGUED and owned by ORCH"
for n in (889, 890, 891):
    assert re.search(rf"^{n}\. \*\*", text, re.M), f"discipline {n}"

for line in NEW_FACTS.strip().split("\n"):
    assert line.count("|") == 5, f"pipe count {line.count('|')}: {line[:80]}"
    stripped = re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, f"bold imbalance: {line[:80]}"

# The retraction is load-bearing on a live decision. It must name it.
i1736 = text.index("| 1736 |")
row1736 = text[i1736 : text.index("\n", i1736)]
assert "ORCH-kernel-decision.md" in row1736, "1736 must name the decision it blocks"
assert "WITHDRAWN" in row1736, "1736 must state the withdrawal"

# Fact 1735 must carry the discriminating control, else byte-identity is vacuous
# (a merge that copied ANY frame would also be 'byte-exact' against itself).
i1735 = text.index("| 1735 |")
row1735 = text[i1735 : text.index("\n", i1735)]
assert "0.0519" in row1735, "1735 must carry the unelected-pixel control"

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold161 OK: facts 1735-1739, disciplines 889-891")
print("  combination stage ELIMINATED; kernel headline WITHDRAWN; election quality is the last suspect")
