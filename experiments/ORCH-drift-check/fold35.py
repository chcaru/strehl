"""Fold 35 -- M97, the warped merge: correct wiring, half-strength solve."""
import io
import re

SYN = "docs/research/SYNTHESIS.md"

DISC = [
    "**A held-out or relative error score cannot detect a global shrinkage, so "
    "the acceptance bar for an *estimator* must be absolute and end-to-end.** "
    "M86's alignment solve passes its held-out reprojection check while "
    "applying only **50.2%** of the drift that is physically there, because "
    "shrinking every frame's warp by a common factor leaves the frames' "
    "agreement *with each other* almost untouched -- it is the agreement with "
    "the **scene** that collapses. M97's words: *\"any future acceptance bar "
    "for the solve needs an absolute, end-to-end check.\"* Whenever a fitted "
    "quantity is scored only against other fitted quantities, ask what "
    "multiplying the truth by a constant would do to the score; if the answer "
    "is \"nothing\", the score cannot validate the fit.",

    "**Resolve a disputed measurement by *gathering* rather than by reading, "
    "and write the extractor yourself.** Facing a contradiction between M86's "
    "prose and its own sidecar, M97 wrote an independent sub-lattice "
    "extractor, gather and NCC scale ladder *in the milestone* rather than "
    "importing the pipeline's -- explicitly *\"so that a shared bug cannot "
    "make two measurements agree with each other and with nothing else.\"* Its "
    "figure of **0.85714** reproduced the orchestrator's independently "
    "measured **0.85715** to five decimals, which is the strongest cross-check "
    "the corpus holds on any geometric quantity. Two implementations sharing a "
    "helper are one implementation.",

    "**Any cache or sidecar a concurrent process can read must be written "
    "through a temp file and renamed.** M97 measured -- by accident, while "
    "debugging something else -- a **torn read** of `bee-3-cpl/warpmap.txt`: "
    "a sibling milestone was rewriting it in place and the reader got a "
    "half-written file that parsed and merely lacked a key. With many agents "
    "live in one working tree this is not a theoretical race. Write-then-"
    "rename makes a reader see either the old file or the new one and never a "
    "partial one.",

    "**PowerShell's `[int]` rounds half to even, so `[int](3/2)` is `2`.** "
    "`$v[[int]($v.Count/2)]` on a sorted 3-element array returns the **max** "
    "and calls it the median; M97's timing harness reported **29.51 s** for a "
    "set whose median is **21.67 s**. Use `[math]::Floor` for an index. The "
    "general form: a language's default rounding mode is a silent participant "
    "in every index and every bin edge you compute.",
]

FACTS = [
    "| 1271 | **THE ALIGNMENT WIRING IS CORRECT AND THE SOLVE BEHIND IT "
    "APPLIES ONLY HALF THE DRIFT: 150.2 PLANE PX OF MISREGISTRATION SURVIVE "
    "ALIGNMENT ON `bee-3-cpl`.** M97 verified the wiring with controls -- "
    "correct sign, correct per-CFA-plane handling, an identity placebo, a "
    "wrong-stack control, and a whole-frame NaN sweep with an 18-px plant "
    "recovered at 0.00000% black. Then it measured the solve itself: **50.2% "
    "of the drift removed** end-to-end (**54.3%** of the span by the sidecar "
    "route). Truth, measured twice independently with no shared code, is that "
    "a feature at radius `r` in frame 0 sits at **0.85714**`r` (M97) / "
    "**0.85715**`r` (orchestrator) in frame 298; the sidecar spans only "
    "**1.0841** against a true **~1.167**. | This is the largest known defect "
    "in the pipeline and it explains the owner's complaint. Wiring alignment "
    "into the merge bought only **~3%** not because registration is the wrong "
    "lever but because **the registration being applied is half-strength**. It "
    "also retires the prior explanation: M97 had proposed a different "
    "mechanism an hour earlier and discarded it when this measurement "
    "arrived. | M97 (MEASURED, two independent implementations); "
    "`docs/research/M97-warped-merge.md` §7 |",

    "| 1272 | **M86 §4.2'S STATED SIGN IS WRONG: THE SUBJECT SHRINKS THROUGH "
    "THE STACK, IT DOES NOT GROW.** The sentence *\"Frame 0 is roughly 10-12% "
    "smaller than frame 298\"* is contradicted by M86's **own** sidecar, which "
    "places frame 0 at `\|a\|` = **1.0504** and frame 298 at **0.9689** about "
    "reference 149, and by two independent RAW gathers. The 10-12% magnitude "
    "in that sentence is just 232.7/2111.2, so only the direction is wrong. | "
    "A flipped sign would have doubled the drift silently, so this was worth "
    "settling before anything was built on it -- and M97 settled it by gather "
    "rather than by argument, with an inverted arm as the control (AS-IS moves "
    "toward 1.0 at 0.92887; INVERTED moves **away**, to 1.48x the raw drift). "
    "**The shipped sign is correct**; only the prose was wrong. Anything that "
    "cites M86 §4.2's direction must be re-checked. | M97 (MEASURED, with an "
    "inverted control); `docs/research/M97-warped-merge.md` §7.1 |",

    "| 1273 | **GRADIENT-ENERGY SHARPNESS HAS NOW FAILED ITS OWN CONTROLS A "
    "THIRD TIME, ON A DIFFERENT METRIC AND A DIFFERENT SUBJECT.** M97 built a "
    "tile-wise band-limited detail metric intending it as half of its verdict; "
    "the responsiveness control **disqualified it**, and the signs came out "
    "**inconsistent between subjects** -- on the bee the worse arm reads "
    "higher, on the ruler's `ZOOMNULL` the worse arm reads lower. | Sign "
    "inconsistency across subjects is independent evidence of confounding "
    "rather than of signal, and it corroborates M86c §15.4 by a different "
    "route. With discipline 605 and M82's eighteen abstentions this is the "
    "third independent death. **Treat \"whole-frame gradient-energy sharpness "
    "cannot adjudicate registration or the gate\" as settled corpus**, not as "
    "one milestone's opinion, and stop commissioning it. The instrument that "
    "replaces it must carry ground truth (M102) or an external anchor (M98). | "
    "M97 (MEASURED, negative, self-disqualified); "
    "`docs/research/M97-warped-merge.md` §6 |",

    "| 1274 | **COVERAGE AFTER ALIGNMENT IS ~13%, NOT THE 26% THE "
    "ORCHESTRATOR BRIEFED -- BECAUSE THE SOLVE APPLIES HALF THE SPAN -- AND "
    "`stack` ALREADY CROPS TO THE FULLY-COVERED REGION.** `fit_to_cover` "
    "reports `k` = **0.9315** on `bee-3-cpl`, so there is no low-`n_eff` "
    "margin in the output at all, at the price of a **7.35%** full-frame "
    "upsample. | Two corrections in one row. The orchestrator's coverage "
    "figure was derived from the *measured* drift rather than the *applied* "
    "drift, and the realised deficit is about half of it. And the NaN-margin "
    "hazard the brief warned about does not exist in the shipped path, because "
    "the crop precedes it -- but the 7.35% upsample is a real resample cost "
    "that is **confounded with the registration gain** and has not been "
    "isolated. | M97 (MEASURED); `docs/research/M97-warped-merge.md` §9a |",
]

syn = io.open(SYN, encoding="utf-8").read()
L = syn.split("\n")

d = max(i for i, l in enumerate(L) if re.match(r"^6\d\d\. ", l))
assert L[d].startswith("620. "), L[d][:60]
f = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[f].startswith("| 1270 |"), L[f][:60]

for k, row in enumerate(FACTS):
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == 5, "fact %d has %d pipes" % (k, n)
DROWS = ["%d. %s" % (621 + k, t) for k, t in enumerate(DISC)]

assert d != f
for idx, rows in sorted([(d, DROWS), (f, FACTS)], reverse=True):
    L[idx + 1:idx + 1] = rows

io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("SYNTHESIS: facts 1271-1274, disciplines 621-624")
