"""Append section 16 to docs/research/BUILD-BLEND.md (idempotent)."""

import io
import os

DOC = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "research", "BUILD-BLEND.md")
DOC = os.path.normpath(DOC)
MARK = "## 16. The blocks are not at HEAD, but the hull violation behind them is"

NOTE = """

## 16. The blocks are not at HEAD, but the hull violation behind them is real and large

### 16.1 merge_cmd.rs: never touched

ORCH withdrew the wiring mandate and asked whether I hold local edits to
`crates/strehl-cli/src/merge_cmd.rs`. `git status --porcelain` on that path is
**empty**, and no commit of mine (`blend:`) appears in its history. I have never
written to it. Nothing to discard.

### 16.2 The visible defect does not reproduce at HEAD, in either binary

ORCH reports solid black axis-aligned blocks 40-60 px across at
`(6136, 1360)` on `dry-erase-marker-head-cpl`, and instructs -- correctly --
that the picture is the instrument and the number is the annotation. So the
crop was taken, with **one tone mapping shared by both panels** taken from the
BEFORE arm only, since a per-panel normalisation could manufacture or hide a
black block.

At that site, HEAD `5dd9b649`:

| arm | linear min | exact zeros |
|---|---:|---:|
| estimator (BEFORE) | 408 DN | 0 |
| pyramid, `strehl stack` | **2970 DN** | **0** |
| pyramid, `blend-render` | **2970 DN** | **0** |

Whole frame, both binaries, identical to four decimals:

    ch      min       <=0       <=1      <=16      <=64     <=256    <=1024
    R       582   0.0000%   0.0000%   0.0000%   0.0000%   0.0000%   2.3891%
    G       292   0.0000%   0.0000%   0.0000%   0.0000%   0.0000%   3.1193%
    B        89   0.0000%   0.0000%   0.0000%   0.0000%   0.0000%   4.0350%

    pixels with ANY channel exactly 0 : 0 (0.0000%)

That the product binary and my example binary agree *exactly* is an independent
confirmation of the retraction in 15.3: their arithmetic really is the same, and
the `.max(0.0)` divergence I claimed does not exist.

What the crop does show is the opposite of the report. The **estimator** panel
carries the halo -- a pale ring around the ink, concentric contour banding, a
grey patch to the left and a pale blob upper-right, and ink that reads
washed-out blue-grey. The **pyramid** panel is clean: solid black ink, no ring,
no patches, paper fibre resolved.

### 16.3 But the mechanism ORCH proposes is confirmed, and it is worse than the count suggested

ORCH's hypothesis -- *a per-band convex combination is not convex overall, so the
reconstruction can leave `[min_k, max_k]`, and at black-ink-on-white-paper
contrast that excursion is thousands of DN* -- is **correct**. This module's own
`Hull` docstring already says so, citing ORCH's earlier 1-D construction. What
was missing was the magnitude on a real high-contrast frame.

`hull clamp` on `dry-erase-marker-head-cpl`: **11.498% 18.821% 18.881% 12.553%**
per CFA plane -- the highest out-of-hull fraction measured anywhere in this
project, against 8.6-11.0% on `flower-bud-alone-cpl`. ORCH's contrast argument is
right.

The rate alone decides nothing, so the *correction magnitude* was measured
directly as `clamped - unclamped` (`experiments/BUILD-BLEND/excursion.py`):

| ch | moved | median &#124;d&#124; | p99 | p99.9 | max | share of frame > 1000 DN |
|---|---:|---:|---:|---:|---:|---:|
| R | 16.588% | 194 | 1835 | 4461 | **42711** | 2.026% |
| G | 15.512% | 287 | 1972 | 5515 | **49500** | 2.015% |
| B | 16.853% | 226 | 1904 | 5285 | **49497** | 1.795% |

And the direction is ORCH's direction: the clamp **raises** 77.7% / 85.0% /
79.1% of the pixels it moves, meaning the reconstruction had fallen *below* the
hull, toward and past black. The unclamped arm carries **1.17% / 1.29% / 1.40%**
exact zeros, which is the signature ORCH measured at +1.86 / +1.96 / +2.36 pt.

So: **the artifact ORCH saw is what this merge does with the clamp removed**, and
the clamp is the only thing standing between the current output and those blocks.
A merge that requires a 49,500 DN correction -- 75% of full scale -- on 2% of a
frame is not sound at those sites, even when the correction lands.

### 16.4 The design this data indicates

ORCH asks for a fix that does not resolve by reflex into a hard hull projection,
because that would also forbid genuine super-resolution or deconvolution gain,
and proposes a margin tied to the calibrated noise. **The excursion distribution
argues for exactly that, and it sets the constant.**

The median excursion is **194-287 DN**, which is on the order of one sigma of the
calibrated noise at these levels -- i.e. the typical excursion is inside what the
noise model already says is plausible, and is a candidate for genuine recovered
detail of the kind ORCH's own `rho_add` analysis found. The tail is **20-200
sigma**. Those two populations are separated by more than two orders of
magnitude, which is what makes a noise-referenced bound feasible rather than
arbitrary:

    lo_k = min_k - lambda * sigma(pixel)
    hi_k = max_k + lambda * sigma(pixel)

with `lambda` around 2-3. That admits essentially all of the median-scale
excursion and rejects essentially all of the catastrophic tail, and -- unlike an
absolute epsilon -- it scales correctly with signal level, so it does not tighten
in the shadows where the current hull is nearest zero and does most of its
damage.

Two properties worth stating before implementing, because they are what makes
this safe rather than merely plausible:

* It **degenerates to the current behaviour as `lambda -> 0`**, so a rung-0
  byte-identity commissioning is available -- the same ladder discipline used for
  `mean_coarse`.
* It **cannot reintroduce a hard seam**, because `min(max(x, lo), hi)` stays
  continuous in all three arguments and `sigma` is a smooth function of the
  signal, so the widened bound is still continuous.

The real fix is upstream of all of this: the excursions are generated by the
per-band selection exponent (`2 3 4 5 8 8 8`, highest at the finest bands), and
this module's own docstring records 0 violations at exponent <= 1 against 511 at
16. A margin makes the clamp honest; lowering the exponent would make it
unnecessary. The margin is the safe first rung because it cannot cost acuity,
which an exponent reduction measurably does (18% by an earlier measurement).

### 16.5 Acceptance, as ORCH specified it

Scored on the **linear 16-bit TIFF**, AFTER minus BEFORE, per channel, on
`dry-erase-marker-head-cpl`, `foam` and `flower-bud-alone-cpl` within +0.05 pt,
with `couch-fibers-cpl` held at 0.0000 as the placebo, plus a re-crop of
`(6136, 1360)` inspected by eye. `experiments/BUILD-BLEND/zerocount.py` and
`cropsite.py` implement it; `zerocommission.py` must pass first, since a
zero-count that cannot see a planted zero reports a pass and a frozen probe
identically.

*Instruments: `cropsite.py`, `clipcensus.py`, `excursion.py`, `zerocount.py`,
`zerocommission.py`, `acceptance.ps1`. Not verified by their author.*
"""


def main():
    src = io.open(DOC, encoding="utf-8").read()
    if MARK in src:
        print("section 16 already present; nothing to do")
        return
    io.open(DOC, "w", encoding="utf-8", newline="").write(src.rstrip("\n") + "\n" + NOTE)
    print(f"appended section 16 to {DOC}")
    print(f"now {len(io.open(DOC, encoding='utf-8').read().splitlines())} lines")


if __name__ == "__main__":
    main()
