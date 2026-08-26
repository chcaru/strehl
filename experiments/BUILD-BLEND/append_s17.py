import io
import pathlib

DOC = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\BUILD-BLEND.md")

S = r"""
## 17. ORCH's six-rung ladder: the measurement is right, the binary is four hours stale

ORCH sent a six-rung attribution ladder on `dry-erase-marker-head-cpl` and, to
their considerable credit, sent it as a *retraction*: rung C (`--sharpen 0`) reads
a perfect 0.0000 in all three channels, they nearly reported sharpening as the
cause, and then they looked at the picture and found the ink reduced to "a faint
featureless grey smudge with no edge and no internal structure". They withdrew the
attribution themselves before anyone challenged it.

That retraction is correct and the reasoning behind it is the most useful thing
anyone has contributed to this defect. `sharpen_per_octave` is not an enhancement
bolted onto the merge; it ramps the selection exponent toward the fine bands, so
setting it to zero flattens the weights and the merge degenerates to a plain mean
over a defocus sweep. Their honest restatement is the one to keep:

> the out-of-hull excursion is monotone in selection peakedness, and selection
> peakedness is the thing that makes stacking work.

Their rung F (`--bands 2`) is confounded the same way and they declined to offer
it as a lever either. **Accepted without reservation. I will not touch the
sharpening ramp, the exponent cap or the band count.** Any of the three would buy
a green acceptance number with a soft photograph, which is the opposite of the
job.

### 17.1 Their numbers are right; I reproduce them to four decimals

Before attributing their result to anything, the first question is whether their
instrument and mine agree, because if they do not, nothing downstream is
comparable. I ran my zero-counter on *their* rung B file rather than on a render
of my own:

    rung B, --camera-linear          ORCH reported    BUILD-BLEND measured
      R                                  1.1841              1.1841
      G                                  1.2866              1.2866
      B                                  1.3815              1.3815

Four decimal places, three channels, independent code. **The instruments agree
exactly.** Their measurement is not in question and I am not going to spend
another round litigating it.

### 17.2 So the binary is the variable, and its timestamps place it before the fix

If the instrument is right and the number is wrong for HEAD, the remaining
variable is what was measured. `C:\dev\strehl-out\ORCH-CLAMP` gives the answer
without needing to disassemble anything:

    ORCH's six rung TIFFs      2026-08-25  19:00 - 19:12
    hull clamp landed (275fbd17)           23:05

**The rungs predate the hull clamp by roughly four hours.** Their rung B is
therefore a measurement of the *unclamped* arm, and it should agree with my own
unclamped render. It does:

    unclamped exact zeros, dry-erase        R 1.17   G 1.29   B 1.40   (S 16.3)
    ORCH rung B                             R 1.18   G 1.29   B 1.38

Within 0.02 pt across three channels, from two different builds and two different
harnesses. Their ladder is a clean and correct characterisation of the arm as it
stood at 19:00. It is the sixth instance in this collaboration of a stale pin
being read as a live defect, and by now the pattern is the finding rather than the
anecdote: 108 copies of the tree exist under `C:\dev`, eleven of them identical in
length, and `git -C <dir> rev-parse HEAD` returns empty for all eleven because
they are plain directory copies with no `.git`. There is no check available from
*inside* such a copy that reveals its own staleness. Timestamps and content
fingerprints are the only instruments that work, which is why this section leads
with a file listing rather than an argument.

### 17.3 The blocks, reproduced from ORCH's own file, and absent at HEAD

ORCH's strongest contribution was to stop counting and start looking: solid black
axis-aligned blocks, 40-60 px, hard-edged, on and beside the ink, with red fringes
on their right edges. Rendering their rung B at their site (6136, 1360) reproduces
every element of that description, and the same site at HEAD does not:

    site (6136,1360), 600 px crop      ORCH rung B (19:00)      HEAD, clamped
      minimum value                          0 DN                  2970 DN
      pixels at exactly zero                 1.667%                 0.000%

The block shape was the clue they built the hypothesis on, and the hypothesis was
right. A smooth undershoot cannot make a hard-edged block; a coarse-band
coefficient can, because its reconstruction footprint *is* a block of that size.
The per-band convex combination is not convex overall, the reconstructed pixel
comes from a frame that never existed, and at ink-on-paper contrast it lands below
black. Section 16 measured the mechanism directly: 78-85% of all clamp movement is
the clamp *raising* a reconstruction that had fallen below the hull, with
excursions reaching 42711-49500 DN.

The figure is `C:\dev\strehl-out\BUILD-BLEND\antigame\rungB-6136x1360-crop.png`.

### 17.4 The anti-gaming clause, and the near-miss that nearly failed it

ORCH attached an explicit anti-gaming clause: the ink must be "at least as crisp
as rung B does", and they will crop and look before scoring. Eye judgement is
necessary but not sufficient, so `acuity.py` puts two numbers on it -- the 99.9th
percentile of gradient magnitude, which falls first when an edge is softened, and
the RMS of the crop minus a 2 px blur, which catches broadband loss that no single
edge dominates.

That test has a trap in it, and it nearly caught me. **The clipped blocks are
themselves hard edges**: a solid black block against white paper carries an
enormous gradient, so a naive acuity score rewards the artifact and reports the
*damaged* arm as sharper. Scored over the whole crop, rung B "wins" on both
statistics (0.661 and 0.728) purely on the strength of its own defect. The clipped
pixels and their neighbourhood therefore have to be excluded, and the comparison
made on the parts of the crop that are actually photograph.

Excluding them at a 1 px dilation gave a split verdict -- edge acuity 1.028 in my
favour, fine-band RMS 0.937 against me -- which fails the >= 0.98 bar I had set
myself. The honest reading of a split like that is not to pick the flattering half.
It is that a single exclusion radius is an arbitrary choice, and the way to find
out whether 0.937 is real softening or leftover contamination is to sweep it: the
blocks' ringing fringes are wider than 1 px, and that ringing is high-frequency
energy being credited to the damaged arm. Contamination converges toward 1.0 as
the excluded neighbourhood grows; genuine softening plateaus below it.

    dilate   excluded   edge ratio   fine ratio
         1      2.43%        1.028        0.937
         2      2.71%        1.025        1.015
         3      2.98%        1.027        1.015
         5      3.52%        1.021        1.014
         8      4.34%        1.016        1.013
        12      5.51%        1.025        1.012
        16      6.79%        1.033        1.011
        24      9.66%        1.033        1.010

It converges at 2 px and never returns. From 2 px to 24 px -- a twelvefold change
in the only free parameter -- the fine-band ratio sits in 1.010-1.015 and the edge
ratio in 1.016-1.033. **At every adequate exclusion radius the clamped arm is both
sharper on edges and richer in fine detail than rung B.** The anti-gaming clause
passes, and it passes because the fix is not a softening fix: the hull clamp is
orthogonal to selection peakedness, so it removes the impossible pixels without
touching the mechanism that makes the stack sharp.

The near-miss is worth recording as an instrument note in its own right. A single
fixed radius would have returned FAIL at r=1 and PASS at r=2, on no evidence
either way. Sweeping the parameter and reading the convergence is what turns it
from a choice into a measurement -- and the discipline that matters is that the
sweep was run *while the number was against me*, not after it came out favourable.

### 17.5 What ORCH asked for is implemented; what remains is the margin

ORCH's prescription was to keep the peaked selection and separately forbid the
reconstruction from leaving the range the contributing frames actually span at
that pixel. That is precisely what `Hull::InputRange` does, and it has been the
default since 275fbd17 at 23:05 -- which is why the rungs, rendered at 19:00, do
not show it.

What is *not* yet implemented is the refinement they and I arrived at
independently: the bound is currently a hard hull (lambda = 0), and a hard hull
also forbids any genuine super-resolution or deconvolution gain, which is contrary
to the project thesis. The noise-calibrated version -- `lo = min_k - lambda*sigma`,
`hi = max_k + lambda*sigma`, with sigma from the calibrated noise model -- is
designed in section 16.4 and sized by the bimodal excursion distribution measured
there (median ~1 sigma, tail 20-200 sigma, which sets lambda around 2-3). That is
the next code change in this lane, and it is a refinement of a shipped fix rather
than a fix for a live defect.
"""

t = DOC.read_text(encoding="utf-8")
assert "## 16." in t, "section 16 missing - wrong file?"
assert "## 17." not in t, "section 17 already present - refusing to duplicate"
before = len(t.splitlines())
DOC.write_text(t.rstrip("\n") + "\n" + S, encoding="utf-8")
after = len(DOC.read_text(encoding="utf-8").splitlines())
print(f"BUILD-BLEND.md {before} -> {after} lines (+{after - before})")
