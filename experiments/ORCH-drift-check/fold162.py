"""ORCH fold 162: a stale claim caught in the owner brief, and the gate audit.

Not a milestone fold. Two ORCH-owned results from re-checking the brief against
the code at dawn:

  1. The brief asserted `robust.rs` was unreachable. It was true when written
     and became false at 20:00 the same night. Nothing flagged it.
  2. The render path's defaults: five of six measured improvements are off.
"""
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1740 | MEASURED | ORCH | **A CLAIM IN THE OWNER BRIEF WAS TRUE WHEN WRITTEN AND SILENTLY BECAME FALSE THE SAME NIGHT; ONLY RE-READING THE CODE FOUND IT.** The brief stated that `outlier.rs` and `robust.rs` are *unreachable from the binary*. Re-checked at dawn against `crates/`: `robust.rs` is now reachable -- `merge.rs:75` reads `use crate::robust::{AffineVar, Arm, ResidualOp, RobustElection, Z_HALF};`, wired with the `STREHL_ROBUST_ELECTION` gate at commit `e028113` (2026-08-24 **20:00:49**), i.e. **after** the brief sentence was written. `outlier.rs` is **still not reachable from the render path**: `lib.rs:23 pub mod outlier;` is its only reference from library or CLI sources. **ORCH's first draft of this row said `still orphaned: nothing outside itself refers to it`, and that was false** -- a recursive search found **33 matches across 9 files**, including four measurement binaries that import it directly (`strehl-cli/examples/m97-outlier.rs:24`, `m123-outlier-real.rs:51`, `m123-null-radius.rs:53`, `m123-trap-decompose.rs:57`). The error came from grepping `src\\*.rs` non-recursively and writing the conclusion as `anywhere`, and it was caught by `fold_check`'s qualifier bucket flagging the word `only` -- **not** by any label check. Second scope inflation inside this one fold; the rate fact 1721 predicts. **The defect is not the original sentence, which was correct, but that nothing in the pipeline re-examines a code-state claim once it is written** -- no test, no lint and no fold covers prose about code. Corrected in the brief at commit `a841232`. This is the live instance of the currency hazard that dissolved V-FOLD's two candidate counterexamples (fact 1725), and it landed in the one document the owner actually reads. |
| 1741 | MEASURED | ORCH | **FIVE OF THE SIX MEASURED IMPROVEMENTS THIS PROJECT HAS BUILT ARE OFF WHEN THE OWNER RUNS THE TOOL.** Read directly from the sources: `optics.rs:476` and `merge.rs:525` both resolve their switches through `env::var(...).ok()`, for which **unset means off**. On the default render path `STREHL_ALIGN` is the only improvement enabled; `STREHL_FIX_CA`, `STREHL_ROBUST_ELECTION`, `STREHL_SMOOTH`, `STREHL_SOFT_GATE` and `STREHL_PHOTOMETRIC` are all present, all tested, and all **inactive**. **So every render the owner has judged is very nearly the unimproved one, and the project's measured wins have never been measured together.** Two hazards were identified before dispatching that measurement, both of which would corrupt it: turning everything on is not obviously right -- on a drifted stack the merge measurably loses to a single frame -- and `STREHL_FIX_CA` under `STREHL_ALIGN=0` is a **byte-identical no-op**, so the arm matrix is nested rather than factorial. M126 dispatched with both pre-registered. |
"""

NEW_DISCIPLINES = """892. **PROSE ABOUT CODE IS THE ONLY ARTEFACT IN THIS PROJECT WITH NO STALENESS CHECK, AND IT IS THE ARTEFACT THE OWNER READS.** Fact 1740: a correct sentence about which modules were reachable decayed into a false one within hours of being written, and every automated gate stayed green because none of them reads prose. Facts get folded, code gets tested, numbers get `fold_check`ed; **a claim of the form `X is not wired up` has no owner and no expiry.** Treat every code-state assertion in an owner-facing document as perishable: re-derive it from `crates/` before each delivery, and prefer claims that are dated (`as of <commit>`) over claims that are timeless, because a dated claim that goes stale is still true and an undated one is simply wrong.
893. **`BUILT AND MEASURED` IS NOT `ON`, AND THE GAP IS INVISIBLE FROM EVERY GREEN SIGNAL THE PROJECT PRODUCES.** Fact 1741: five measured improvements sit behind unset environment variables, so the test suite, the byte-freezes and the milestone reports were all truthfully green about a render that contains none of them. **A default is a decision, and an unset `env::var` is a decision nobody wrote down.** Any project that gates work behind flags must audit the resolved default set as its own deliverable -- and must distinguish a gate that is *structurally inert* (no-op unless a second gate is on) from one that is *measurably useless*, because the two produce the identical number and mean opposite things. Only reading the code separates them.
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    j = txt.index("\n", i) + 1
    return txt[:j] + block + txt[j:]


def insert_after_discipline(n, block, txt):
    """Insert immediately after discipline n's own line.

    The earlier walk-forward version of this helper stepped past the end of
    section 5 and landed the block under the section 6 heading; corpus_lint
    caught it as N5 x2. A discipline is exactly one line, so anchoring on the
    end of that line is both simpler and correct.
    """
    anchor = f"\n{n}. **"
    i = txt.index(anchor)
    j = txt.index("\n", i + 1) + 1
    return txt[:j] + block + txt[j:]


text = insert_after_fact_row(1739, NEW_FACTS, text)
text = insert_after_discipline(891, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold162 OK: facts 1740-1741, disciplines 892-893")
print("  a code-state claim in the owner brief went stale within hours; five of six gates are off by default")
