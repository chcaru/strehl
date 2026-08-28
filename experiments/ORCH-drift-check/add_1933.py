"""Bank facts 1933-1940 from BUILD-SOFTGATE, including ORCH's own bad instruction."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1932

ROWS = [
    ("MEASURED", "BUILD-SOFTGATE",
     "**THE PYRAMID'S SHIPPED PER-FRAME WEIGHT ALREADY IS A SOFT KERNEL: IT IS ALGEBRAICALLY AN "
     "EXPONENTIAL OVER LOG-SNR DEFICIT AT TEMPERATURE ONE OVER p.** Normalising the shipped "
     "weight against the band winner, the ratio of frame weight to winner weight equals exp of "
     "minus p times the frame's log-SNR deficit, and the winner's own factor cancels exactly. "
     "The consequence reframes a whole design axis: **the sharpening ramp is not a separate "
     "mechanism, it is a temperature schedule over scale.** Nobody set out to build a soft gate; "
     "one was already shipping under a different name, and the project spent effort proposing to "
     "add what it already had. **Derive the closed form of what ships before designing its "
     "replacement.**"),

    ("MEASURED", "BUILD-SOFTGATE",
     "**A PLACEBO THAT IS ALGEBRAICALLY IDENTICAL TO THE SHIPPED PATH CONTROLS FOR WIRING BUT "
     "PROVIDES ZERO WIDTH CONTROL, WHICH IS THE ONE THING THE EXPERIMENT NEEDED.** Because the "
     "shipped weight is already exponential, `SoftKernel::Exponential` on the pyramid moves "
     "**0.029 percent of pixels at mean 0.001 DN** - a placebo by construction - while Gaussian "
     "moves **96.286 percent**. So the placebo shares shipping's effective width, and **the only "
     "arm whose width actually moved is the one arm the placebo is not matched to.** The lane "
     "reported this against its own interest rather than letting the placebo imply a rigour it "
     "did not have. **A placebo proves only what it is matched on; state the axis it does not "
     "control.**"),

    ("CORRECTED", "BUILD-SOFTGATE",
     "**A HEADLINE RESULT WAS WITHDRAWN BY ITS OWN AUTHOR BECAUSE A LATE FACT FROM ANOTHER LANE "
     "SHOWED THE INFERENCE, NOT THE MEASUREMENT, WAS UNSOUND.** The 3.0 percent depth-softening "
     "improvement is measured and reproducible; the claim that the kernel is 3.0 percent BETTER "
     "is not, because arms matched on threshold rather than on mean effective count confound "
     "kernel shape with admission width. **The mechanism transfers even though the code path "
     "does not:** fact 1918 was measured on the estimator's `Gate::tolerance()` while this lane "
     "wired the pyramid's `select_weight`, but a Gaussian is flatter near zero deficit on both, "
     "so it admits more frames on both, and admitting more frames trivially reduces noise and "
     "trivially increases blur. **No arm in the experiment ever measured n_eff**, so shape and "
     "width cannot be separated after the fact. The sign result survives explicitly weakened: a "
     "width confound plausibly explains a small positive number but not a **-44.6 percent sign "
     "reversal**."),

    ("MEASURED", "BUILD-SOFTGATE",
     "**THE GAUSSIAN SOFT KERNEL IS NOT ONE-PASS STREAMABLE, AND THAT IS WHY THE EXPONENTIAL "
     "SHIPS.** Expanding the Gaussian exponent leaves a cross term coupling winner and frame, "
     "which cannot be folded into a running accumulator and therefore forces a second decode "
     "pass: **measured 56.3 s to 124.7 s at N=79**, a 2.2x cost. The exponential's exponent "
     "separates, so it folds. **This is a real architectural constraint discovered by algebra "
     "rather than by profiling, and it prices the merge-architecture question the project had "
     "left open**: any per-pixel statistic requiring the through-focus neighbourhood pays a "
     "second pass, and the decision to carry sufficient statistics or to re-decode should be "
     "made against this measured number rather than argued."),

    ("MEASURED", "BUILD-SOFTGATE",
     "**A CRATE-WIDE CALL-SITE COUNT IS MEANINGLESS UNLESS IT STATES WHETHER IT COUNTS SHIPPING "
     "CODE, EXAMPLES, OR TESTS.** `compose` has **two shipping call sites** in `align_cmd.rs`, "
     "**one in an example binary that ships nothing**, and **twelve in tests**. A count of "
     "fifteen, two, or three are all defensible answers to carelessly different questions, and "
     "the project has already lost an entire investigation to a claim that no call sites existed "
     "when two did. **Report call-site counts partitioned by kind, never as a single integer.**"),

    ("MEASURED", "BUILD-SOFTGATE",
     "**THE RED BYTE-FREEZE ROW IS NOW PREDICTED BY ANCESTRY RATHER THAN MERELY EXPLAINED AFTER "
     "THE FACT, WHICH IS THE STRONGER CLAIM AND CLOSES IT.** The `eps_r` re-fit `393d7ca3` is an "
     "**ancestor** of `ec96973d`, therefore **any** pristine tree at or after `ec96973d` is "
     "necessarily RED on `coffee-bean-20-gate2-sidecar` and green on its `-unaligned` pair, "
     "because the re-fit reaches only the alignment path. The distinction matters: an "
     "explanation accommodates the observation it was built for, while this **forbids** the "
     "alternative outcome in advance and can be falsified by any tree that violates it. A third "
     "distinct hash would still be a real finding."),

    ("MEASURED", "BUILD-SOFTGATE",
     "**VALIDATING AN ENVIRONMENT VARIABLE WITHOUT APPLYING IT LEAVES A NO-CHANGE GATE TRUE FOR "
     "EVERY VALID VALUE AND FALSE ONLY FOR INVALID ONES - A STATE THAT LOOKS LIKE PROGRESS AND "
     "IS NOT.** After the committed change, `gaussian`, `exponential` and `off` all still render "
     "the identical hash `C9A93201...` on the pyramid, while `zzznope` newly fails at rc=1 in "
     "0.0 s. **`enable_soft` greps to zero occurrences: the change validates without applying.** "
     "The correct handling is to gate any polarity flip of such a assertion on the call-site "
     "count of the apply symbol reading non-zero, **not** on the belief that the wiring landed."),

    ("CORRECTED", "ORCH",
     "**THE ORCHESTRATOR ISSUED AN INSTRUCTION PREMISED ON AN UNVERIFIED ASSUMPTION, AND ONLY THE "
     "SUBORDINATE LANE'S REFUSAL PREVENTED A GREEN-LOOKING LIE FROM BEING PLANTED IN ANOTHER "
     "LANE'S COMMISSIONED HARNESS.** I told BUILD-SOFTGATE that flipping V-DILUTE's gate G2 to "
     "FAIL was its success signal. That was **wrong**, because I assumed its wiring had landed "
     "and never checked: `enable_soft` greps to zero, so the soft gate changes pyramid output "
     "for **no** valid kernel name, and flipping G2 would have asserted the opposite in a file "
     "the lane does not own. The lane refused, gave the falsifying command, and said so plainly. "
     "**Two lessons, and the second is the load-bearing one. (1) An orchestrator's instruction "
     "is not exempt from the evidence standard it imposes on its lanes; I asserted a state of "
     "the tree without running the one grep that decides it. (2) The project's rule that no "
     "author verifies their own work has an unstated dual: a lane must be able to refuse the "
     "orchestrator on evidence, or the orchestrator's unverified beliefs propagate into the "
     "corpus with a subordinate's name on them.**"),
]


def build_row(num, kind, lane, body):
    if "|" in body:
        raise SystemExit(f"fact {num}: raw pipe in body")
    if body.count("*") % 2 != 0:
        raise SystemExit(f"fact {num}: odd asterisk count")
    return f"| {num} | {kind} | {lane} | {body} |\n"


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()

    ids = [int(m.group(1)) for m in
           (re.match(r"^\|\s*(\d+)\s*\|", ln) for ln in lines) if m]
    tail = max(ids)
    if tail != EXPECTED_TAIL:
        raise SystemExit(f"tail is {tail}, expected {EXPECTED_TAIL} — re-read before banking")

    hits = [i for i, ln in enumerate(lines) if ln.startswith(f"| {tail} |")]
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} lines, expected exactly 1")
    at = hits[0]

    new = []
    for offset, (kind, lane, body) in enumerate(ROWS, start=1):
        num = tail + offset
        if any(ln.startswith(f"| {num} |") for ln in lines):
            raise SystemExit(f"fact {num} already present")
        new.append(build_row(num, kind, lane, body))

    lines[at + 1:at + 1] = new
    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)
    print(f"inserted {len(new)} rows ({tail + 1}-{tail + len(new)}) after fact {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
