"""Append section 58 to docs/research/ORCH-veiling.md, idempotently.

Same contract as append57.py: refuses unless the file ends on the exact
expected anchor, refuses if section 58 already exists, and refuses if the
result would not grow. Commissioned by commission58.py before use -- a guard
that has never been shown to refuse is not a guard.
"""
import pathlib
import sys

DOC = pathlib.Path("docs/research/ORCH-veiling.md")

ANCHOR = """Reporting it as dead on the strength of the
accessors would have been exactly the error this section is about, in reverse.
"""

BODY = """

## 58. The output is print-worthy, and the clamp costs 3% not 15%

Section 57 closed on capability that is missing. This one opens on capability
that is present, because for the first time tonight the question "is this good
enough" has an answer taken from pixels rather than from a report.

### 58.1 Three subjects at 1:1, judged by eye

The owner's standing instruction is to work until the stacker produces
award-quality, print-worthy output. That is a judgement about a picture, and no
scalar in this corpus can stand in for it. So it was made the only way it can
be: by pulling true 1:1 tiles out of the delivered masters and looking at them.

`pixelpeep.py` selects the highest-detail tiles in a master by mean absolute
Laplacian on a coarse grid, spaces them so they do not all land on one feature,
and grades them through a single display curve derived once per master from the
whole frame. The single shared curve is not a detail. Deriving a curve per tile
would make two tiles from the same image mutually incomparable, and a
brightness difference between two regions of the subject would read as a
grading difference. That is the same defect that made a matched pair look
geometrically shifted in section 56, and the docstring in `hullcrop.py` now
forbids it by name.

| subject | rank | what is resolved at 1:1 | halo |
| --- | ---: | --- | --- |
| `bee-3-cpl` | 10 | individual plumose hair barbules, incl. the branched side-structure of bee hair | none |
| `leaf-2-cpl` | 6 | vein structure at three scales, cell-level texture, chloroplast speckle | none |
| `112MSDCF` | 4 | crystal dendrites to near single-pixel branch width | none |

All three are print-worthy. The verdict is mine, it is visual, and it is
recorded here as a judgement rather than a measurement so that a later reader
can disagree with it on the same evidence.

**The halo is gone at the place it was worst.** The hardest tile in the whole
delivered set is `bee-3-cpl` at y=964 x=4564: fine pale hairs crossing in front
of the dark, defocused compound eye. That geometry -- a bright thin foreground
over a dark defocused background -- is where every focus stacker in existence
produces a bright rim, and it is where this project's own output was unusable
earlier tonight. There is no rim. The hairs hold their edges across the
boundary and the eye's facet texture reads through behind them.

`leaf-2-cpl` is the more searching test of the two and was chosen for that
reason. Leaf veins are long, high-contrast, and locally straight, which is the
geometry that a Laplacian pyramid rings against most readily. They are clean.

### 58.2 One visible defect remains in the flagship

In `bee-3-cpl` a tarsus and claw around y=2723 x=1998 read soft, low-contrast
and veiled, while hairs a few hundred pixels away stay crisp. It is the only
thing left in that frame that a print would show.

Whether it is fixable is a single question with three possible answers, and the
answer determines the entire response:

- some frame saw it sharply and the merge lost it -- a **merge defect**,
  fixable, and important because the mechanism would be damaging every stack;
- no frame ever saw it sharply -- a **capture limit**, and the honest product
  response is to report it rather than fake it;
- the through-focus response is **bimodal** -- a background element seen through
  defocused foreground, which is the two-layer veiling case and has its own fix.

`throughfocus_probe.py` answers it by reading the CFA green lattice straight
from the raws with no demosaic, no alignment and no tone curve, and reporting
mean absolute Laplacian in a fixed window per frame. Only the shape of the
resulting curve is interpreted, never its height, which makes the measure
independent of scene brightness and of the merge entirely.

### 58.3 The control caught the author, again

The probe requires a control window on structure known to be sharp mid-bracket,
and refuses to interpret the probe at all unless the control produces a clear
interior peak.

On the first run the control commissioned cleanly at a peak-to-floor ratio of
**2.45**, and the probe returned **1.16** -- barely above the flat threshold,
and a number I was one step away from reading as "capture-limited, nothing to
be done."

Dumping the probe window to a PNG and looking at it showed it was sitting on
blank white background with a few stray hairs in one corner. The claw was not
in it. **The reading was correct and the window was wrong.**

> **A window that is not on the subject reads flat no matter what the subject
> does.** Confirm the window contains the thing by dumping it and looking at it,
> at several points along whatever axis the instrument sweeps. Arithmetic that
> maps coordinates between two grids is not confirmation; it is the assumption
> under test.

This is the sixth instrument-across-a-transformation failure recorded tonight
and the third in my own hands. The pattern is now stable enough to state
plainly: every one of them was an instrument reporting confidently about
something it was not actually measuring, and every one was caught by looking at
the intermediate rather than by reasoning about the result.

The claw diagnosis is therefore **unresolved**, and is with a dedicated agent
that has the instrument, the commissioning result, and a written account of how
its author misused it.

### 58.4 The clamp: two instruments, five-fold disagreement, one signature

Section 57 routed a claim that the default hull clamp costs 15.5-18.9%
microcontrast on `coffee-bean`. I measured the same matched pair and get about
**3%**.

First, the pair is sound, because the alternative explanation had to be
eliminated before the number could be doubted. Integer cross-correlation over
+/-40 px gives `dy=0 dx=0`; a planted +17 px roll is reported as -17, so the
search can see a shift when there is one; the silhouette's 50% crossing moves a
mean of +0.20 px across five rows.

| band | period | clamped | unclamped | retained | share of change |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 2 px | 537.83 | 553.02 | 97.25% | 60.4% |
| 1 | 4 px | 889.89 | 919.64 | 96.76% | 28.4% |
| 2 | 8 px | 1181.13 | 1224.61 | 96.45% | 8.9% |
| 3 | 16 px | 1319.67 | 1364.39 | 96.72% | 1.8% |
| residual | >128 px | 36650.07 | 36635.78 | 100.04% | 0.1% |

A global 3x3 Laplacian RMS agrees: 98.80% retained frame-wide, 95.72% at the
worst 700 px tile.

**Both numbers can be honest.** A global RMS is dominated by the strongest
edges in a frame, and a large fractional loss confined to low-amplitude texture
hides inside it almost completely. A local, texture-restricted measure would
report that same loss at full size. The disagreement is therefore probably not
an error by either party but a difference in what is being averaged over, and
the useful question is which of the two quantities corresponds to what a person
sees when they call a print soft. That is with an independent verifier, given
both methods and both numbers and told to define the quantity itself rather
than reuse either.

Two findings survive the disagreement, because both instruments show them:

- **88.8% of the change lives in the 2 px and 4 px bands.** The first hypothesis
  on seeing the percentile table was that the clamp merely shifts tone. The band
  split refutes it. The clamp acts on fine detail.
- **It is not rare.** 24.6% of pixels change, 17.1% by more than 100 DN, 1.9% by
  more than 1000 DN. The source comment at `pyramid.rs:666-674` describing this
  as binding constantly while changing nothing is wrong.

### 58.5 The percentile signature, which may close the workstream

| percentile | clamped | unclamped | delta |
| --- | ---: | ---: | ---: |
| p1 | 1726 | 1589 | **+137 DN** |
| p25 | 6928 | 6720 | **+208 DN** |
| p50 | 22107 | 22105 | +2 DN |
| p75 | 53326 | 53343 | -17 DN |
| p99 | 65535 | 65535 | 0 DN |

The clamp lifts the dark end and leaves midtones and highlights alone. That is
the signature of removing **undershoot**: a Laplacian reconstruction ringing
downward at edges, driven below the hull of every contributing frame.

If that is what it is, the argument inverts completely. Content below the hull
of every contributing frame was seen by no frame. It cannot be detail. Removing
it is correct, the 3% is the price of removing ringing rather than a loss, and
the recommendation changes from "do not ship this unconditionally" to "keep it."

> **Before pricing the removal of an operation, establish what the operation
> removes.** A cost measured without that is a number attached to an unknown
> quantity, and optimising it can as easily restore an artifact as recover
> detail.

The decisive test is not another magnitude. For the pixels the clamp moves,
does the unclamped value lie outside the hull of the contributing frames or
inside it? Outside is ringing, correctly removed. Inside is detail, wrongly
removed. The domain trap from section 57 governs the answer: the clamp bounds
four CFA quad planes before demosaic, any hull computed in demosaiced RGB is a
different and strictly weaker constraint, and a test run in the wrong domain
will answer a question nobody asked.
"""


def main() -> int:
    if not DOC.exists():
        print(f"FAIL: {DOC} not found (run from repo root)")
        return 1
    text = DOC.read_text(encoding="utf-8")
    before = len(text)

    if "## 58. The output is print-worthy" in text:
        print("SKIP: section 58 already present; nothing to do")
        return 0
    if not text.endswith(ANCHOR):
        print("FAIL: file does not end on the expected section 57 anchor.")
        print("      Refusing to append -- another writer has touched the tail.")
        print(f"      tail seen: {text[-160:]!r}")
        return 1

    out = text + BODY
    if len(out) <= before:
        print("FAIL: result would not grow")
        return 1
    DOC.write_text(out, encoding="utf-8")
    print(f"OK: {before} -> {len(out)} chars (+{len(out) - before})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
