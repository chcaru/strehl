"""Append AMENDMENT 3 to ORCH-kernel-decision.md.

Written as a script rather than by hand because the text contains backticks and
PowerShell here-strings eat them (a hazard this project has already paid for).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/ORCH-kernel-decision.md"

AMENDMENT = """
## 9. AMENDMENT 3, 2026-08-25 — NO-GO. The last gate opened and the reason to walk through it closed on the same night.

**Decision: NO-GO. This pre-registration is SUSPENDED and must not be resolved
on its current evidence.**

### What changed, in the order it happened

1. **G3 was met.** M124 landed `--resampler` on `strehl stack` with five kernels,
   the default unmoved and pinned byte-for-byte to a committed freeze fixture
   (`crates/strehl-cli/tests/byte-freezes.tsv`). That was the last outstanding
   GO gate, and it is genuine work: it makes the change **cheap and reversible**.
2. **On the same night, the benefit was withdrawn.** M85 retracted its own
   `+0.1160 dex` sharpness headline — the number this entire document was
   written to act on. Its band, **0.30-0.48 cyc/px**, was measured to be
   **12.8 % subject detail (CI 12.2-13.4 %) and 87.2 % noise**. The retraction
   is not a doubt, it is a placebo result: **a dark frame containing no
   photograph at all** was scored through the identical channel and read
   essentially the same gain, **1.0006**. The defocus null read **+0.0033**.

### Why this is a NO-GO rather than a "wait"

The two terms of the trade have become asymmetric in the worst possible way:

| Term | Status |
| --- | --- |
| **Cost** of Lanczos-3 by default | **Still measured**, 2.5x-3.5x warp time |
| **Benefit** of Lanczos-3 by default | **No longer measured** — the supporting statistic was withdrawn by its author |

§5 was explicit that "cost as a veto" was *not* a criterion, on the reasoning
that a measured sharpness gain justified a measured time cost. **That reasoning
required the gain.** With the gain withdrawn, the document's own logic inverts:
what remains is a real cost purchased with an unmeasured benefit. Proceeding
would not be a close call made carefully, it would be a trade whose favourable
side no longer exists.

### The failure mode this document came within one night of demonstrating

A decision record that tracks **feasibility** gates converges on GO as
engineering lands, because every gate it tracks is a piece of work someone is
being paid to complete. Nothing in the original §5 would have gone red when the
motivating measurement was retracted — **G1-G4 are all still met.** The gate
that should have failed was never written, because the possibility that the
premise would be withdrawn was not on the list of ways to be wrong (§6).

**Generalisation, recorded as discipline 890:** `cheaper to do` and `justified
to do` are different gates, and a decision record must say which one moved. A
retraction does not travel to the decisions that depend on it by itself; the
retracting party must name the decision document, and the decision owner must
carry a live pointer back to the measurement the decision rests on.

### What would reopen this

A sharpness comparison scored in a band **demonstrated in advance** to carry
subject detail, with the dark-frame placebo run first and required to read null.
Not the previous band, and not by-eye alone: G2's non-author eye check was
designed as a *guard* on a quantitative result, and it cannot be promoted to
the evidence itself. Until then the default stays where it is, which is the
outcome the freeze fixture now protects for free.

**Sources:** `M95-kernel.md` (retraction, band composition, dark-frame placebo);
M124's report (flag, freeze fixture, G3); SYNTHESIS facts 1726-1730 (M124),
1736 (retraction), disciplines 884, 890.
"""

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

if "## 9. AMENDMENT 3" in text:
    print("already applied; no change")
    sys.exit(0)

text = text.rstrip("\n") + "\n" + AMENDMENT

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("AMENDMENT 3 appended: NO-GO recorded on ORCH-kernel-decision.md")
