"""ORCH fold 167: M115-deconv-headroom section 11 (P21-P31).

M115 replicated ORCH's replacement triage rule on one axis and REFUTED it on
the other -- and the refutation lands on strehl's own merge election.

Source: docs/research/M115-deconv-headroom.md (commits 7e97748, 8d797bf).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1757 | MEASURED | M115 | **A STATISTIC IS NOT A LOCATION STATISTIC BECAUSE ITS OUTPUT IS A POSITION -- AND STREHL'S MERGE ELECTION IS THE COUNTEREXAMPLE.** ORCH's replacement triage rule graded *position* statistics largely immune to quantisation and *dispersion* statistics fragile. M115 refuted it on the project's own core operation: the focus peak is the **argmax of a gradient-energy field**, and gradient energy is on the fragile list, so **locating the peak of a fragile quantity inherits its fragility**. At a step of 256 DN the position statistic was off by **3.550 frames** (5x5 window) and **1.268 frames** (27x27) while a signal-dominated dispersion statistic on the same data moved **5.5 %**. M113 locates a peak in *intensity* and is immune; M115 locates a peak in *gradient energy* and is not. **Under the rule as written an agent would call `which frame is sharpest` immune, and it is not.** |
| 1758 | MEASURED | M115 | **THE QUANTISATION BOUND IS GENUINELY PER-WINDOW, DEMONSTRATED BY MOVING ONLY THE WINDOW.** ORCH asserted that the level count that decides exposure is the one in the window a statistic integrates over, not the one in the file or the ROI. M115 ran the **same statistic over two window sizes** on the **same file and same ROI** -- `FINE_W=5` and `COARSE_W=27`, an area ratio of **29x** -- and the breakpoint moved with the window: **5x5 breaks at step 64** (3.0 levels per window), **27x27 at step 128**. Failure was quiet at every step, returning finite plausible numbers throughout. The support floor behaved as ORCH described, admitted samples falling **404 623 -> 56 616**, and -- ORCH's own saturation check applied to M115's control -- **the count varied at every level**, so the control was live. |
| 1759 | MEASURED | M115 | **BIAS HIDES WHAT MAD REVEALS, AND `DISPERSION` IS TOO COARSE A CATEGORY BY 3.7x.** ORCH quoted M113's *bias* as evidence of immunity. On M115's data at step 16 the bias reads **+0.014 frames** -- pristine -- while the MAD reads **0.622 frames**: the bias breakpoint is step 64, the MAD breakpoint step **16**. **A bias figure is valid only for a statistic that is itself an average over windows**, because per-window errors cancel in the mean and survive in the spread. Separately, at one step on one dataset, difference-based `P_noise` moved **x3.937** while total HF energy moved **x1.055** -- a **3.7x** spread *within* the category ORCH called uniformly fragile. Fragility tracks whether the statistic **isolates a small residual from a large signal**, which is uncomfortably close to the question ORCH had just retracted. |
| 1760 | MEASURED | M115 | **THE `D` LAW REPLICATES ACROSS SUBJECT AND STATISTIC, BUT IT RANKS RATHER THAN PREDICTS, AND ITS ALARMING HALF IS UNCORROBORATED.** M111 measured median \\|shift\\| rising monotonically with `D` = max/min of the combined terms (Spearman **+0.530**, 1547 tiles). M115 replicated on 720 points -- 2 stacks x 20 arm pairs x 18 bins, degenerate pairs excluded -- and found **Spearman +0.457**, monotone on every bin with n >= 10, on a different subject with a different statistic. **Two scope limits M115 attached to its own replication:** (a) in the *same* `D` bin M111 read **0.68 %** where M115 read **5.80 %**, an **8.5x** disagreement, so the law orders candidates and does not look up magnitudes; (b) M115's `D` never exceeds **3.53**, leaving bins [5,8) and [8,inf) at **n = 0**, so the right-hand half of M111's table has no independent support. |
| 1761 | MEASURED | M115 | **A PUBLISHED STABILITY FIGURE THAT OMITS THE DISPERSION OF ITS TERMS WILL BE GENERALISED PAST ITS EVIDENCE -- MEASURED TWICE, INDEPENDENTLY, IN ONE NIGHT.** ORCH broadcast a fleet-wide protection rule from M115's **-1.0 %**. M115 then measured `D` = **1.133** for that figure -- ORCH's own protected leftmost bin, so the conclusion stood -- but reported the worse finding against itself: **the -1.0 % is a band-mean over 18 frequency bins whose per-bin terms move -5.62 % and +10.93 %.** *"The stability came from averaging, not from ratio cancellation. I published an average without the dispersion of its terms and you generalised it fleet-wide. That omission was mine, not yours."* The same shape appeared independently in fact 1759 (bias +0.014 against MAD 0.622). **An average is a claim about a centre; a fleet-wide rule is a claim about a worst case.** |
"""

NEW_DISCIPLINES = """906. **TRIAGE A STATISTIC BY THE QUANTITY IT LOCATES, NOT BY THE TYPE IT RETURNS.** Fact 1757: ORCH's own replacement rule -- position immune, value fragile -- graded strehl's merge election immune, and the election is an argmax over **gradient energy**, a quantity the same rule calls destroyed. An argmax inherits the fragility of the field it searches. **Every triage rule ORCH has issued has been refuted by the next milestone that planted the perturbation instead of consulting the rule** (three times now: absolute-vs-ratio, small-over-large, position-vs-value). The standing instruction is therefore not a better rule but the absence of one: **expand the estimator algebraically, or plant a dose-response control, and never classify by shape.**
907. **PUBLISH THE DISPERSION OF THE TERMS ALONGSIDE ANY STABILITY FIGURE, OR EXPECT THE CENTRE TO BE READ AS A BOUND.** Fact 1761. A band-mean of -1.0 % over bins spanning -5.62 % to +10.93 % is an honest average and a misleading protection claim, and ORCH turned it into a fleet-wide rule within hours. Fact 1759 is the same failure in a different costume: a bias of +0.014 frames beside a MAD of 0.622. **A single-number stability result is only actionable with its spread attached**, and the author is better placed to attach it than the reader is to ask.
908. **REPLICATION EARNS THE RIGHT TO STATE SCOPE LIMITS, AND THE LIMITS ARE THE VALUABLE PART.** Fact 1760: M115 confirmed M111's `D` law and, in the same breath, showed it disagrees by **8.5x** on magnitude within a shared bin and has **zero support** in the two most alarming bins. A replication reported as `confirmed` alone would have hardened a ranking heuristic into a lookup table. **A confirming milestone should be asked what its confirmation does NOT cover**, and that answer folded with the same weight as the agreement.
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


text = insert_after_fact_row(1756, NEW_FACTS, text)
text = insert_after_discipline(905, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold167 OK: facts 1757-1761, disciplines 906-908")
print("  the merge election is an argmax over gradient energy, so it is NOT")
print("  quantisation-immune; and every triage rule ORCH issued has now died")
