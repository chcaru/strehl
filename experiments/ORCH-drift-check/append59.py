"""Append section 59 to docs/research/ORCH-veiling.md, idempotently.

Same contract as append58.py: refuses unless the file ends on the exact
expected anchor, refuses if section 59 already exists, and refuses if the
result would not grow. Commissioned by commission59.py before use -- a guard
that has never been shown to refuse is not a guard.
"""
import pathlib
import sys

DOC = pathlib.Path("docs/research/ORCH-veiling.md")

ANCHOR = """The domain trap from section 57 governs the answer: the clamp bounds
four CFA quad planes before demosaic, any hull computed in demosaiced RGB is a
different and strictly weaker constraint, and a test run in the wrong domain
will answer a question nobody asked.
"""

BODY = """

## 59. Two instruments that measured the wrong thing, and the veil's mechanism

Section 58 reported that the pictures are good. This one reports three things
that were wrong while they were good. Two were found by looking rather than by
reasoning, one of those was mine and had already been sent to two agents as an
instruction, and the third is the mechanism behind the last visible artifact in
the output.

### 59.1 The flower finding, and its retraction

`detailgallery.py` produced the artifact nobody had produced: twenty-six true
1:1 tiles, one per subject, at full resolution. Ranking those subjects by mean
absolute Laplacian in DN put every flower in the corpus in the bottom seven.
Three flower subjects, three of the last seven places, out of twenty-six. That
is the shape of a real pattern, and it was routed to BUILD-TRIAGE as a merge
defect on a subject class and used to justify part of BUILD-SWITCH's brief.

Then the tiles themselves were opened. `flowers-cpl` resolves individual
papillate epidermal cells -- the microscopic domes that give a petal its
texture. `flower-inner-edge-cpl` resolves those *and* pollen grains. Neither is
soft. Both were being ranked last for a reason that has nothing to do with the
merge: they are cream on cream, and a detail statistic in absolute units
measures how much contrast the subject has as much as how much of it the tool
recovered.

`sharpvscontrast.py` divides the detail statistic by the local RMS contrast
actually present in the same window. The ranking moves:

| subject | rank, raw DN | rank, normalised | local contrast (DN) |
| --- | ---: | ---: | ---: |
| `flowers-cpl` | 25 | **5** | **1282** (corpus minimum) |
| `flower-inner-edge-cpl` | 26 | 17 | 1508 |
| `flower-bud-alone-cpl` | 24 | 18 | 2328 |

A normalisation is a claim about an instrument and gets the same treatment as
any other claim, so the script carries a blur-monotone control: progressively
blur each master and require the normalised statistic to fall. It fell on
**26 of 26**. The statistic responds to blur and is not merely dividing one
kind of noise by another, which is the only reason its ranking is allowed to
mean anything.

Retractions went to both agents. The rule:

> **A detail statistic in absolute units measures the subject as much as the
> tool.** Divide by the contrast actually present, and prove the normalisation
> is blur-monotone before believing the ranking it produces.

The genuine bottom is elsewhere, and smaller than the false one: `119MSDCF`
(26th on both statistics) and `109MSDCF` (22nd raw, 25th normalised) are the
only subjects that are under-resolved by both measures. `coffee-bubbles` and
`foam` form a third class -- high contrast, little detail per unit of it --
which is a property of soap films and not a defect.

Two corrections arrived from BUILD-RENDER in the same window, both overturning
descriptions written here. `foam` is not the dark, noisy, flat subject this
corpus called it; it is a soap film with resolved interference banding and the
**lowest** noise-to-gradient ratio in the corpus at 0.072 -- against
`flowers-cpl`'s 0.201, the highest. The v2 ranking defect it was cited for was
sparsity, the ratio falling as one over the square root of the detailed
fraction, not noise. And `highly-angled-ruler-mm-cpl`, which looks poor on every
contact sheet ever made here, is genuinely sharp at 1:1 and sits mid-pack at
1364 DN. Both errors are the same error as the flower error: a summary statistic
or a reduced image standing in for the picture.

### 59.2 The differentiator that does not reach the shipping backend

The README's comparison table against every other stacker had five rows. The
fourth read: *Output -- an image, versus an image plus a per-pixel confidence
map.* It is the row the project's thesis rests on, since a stacker that can
separate "retouch this" from "reshoot this" is an instrument and one that
cannot is a bug report.

Tracing it through the tree:

- `main.rs:787-814` declares a `wrong_backend` table. **Nine** flags are
  refused when `--merge pyramid` is active, and pyramid is the default:
  `--gate`, `--target-n-eff`, `--index-map`, `--n-eff-map`, `--photometric`,
  `--stats`, `--stats-placebo`, `--flat-roi`, `--detail-roi`.
- `--n-eff-map` is the only per-pixel trust artifact that exists. It is written
  by `write_n_eff_map` at `merge_cmd.rs:2636`, called once, at
  `merge_cmd.rs:3782`, from `est.n_eff()` -- the estimator.
- Every other occurrence of the string `confidence` in the CLI crate is inside
  `report_statistics` at `merge_cmd.rs:5257`: console text, not an artifact.
- V-REACH established earlier that `--merge estimator` exits rc=1 out of the
  box.

So the shipping default emits an image and nothing else, and the row was an
overclaim. The README now says so in the table itself rather than in a
footnote, names the nine refused flags, and states that closing the gap is the
top priority after the merge. Correcting the document is not the fix; it is the
precondition for the fix being honest about its own size.

This is the third finding tonight of the same species as section 57's, and the
species deserves its own statement:

> **A capability that exists in the codebase, is flagged, and is documented can
> still be unreachable on the path the product actually runs.** Reachability is
> a property of the default configuration, not of the source tree, and it is
> established by running the shipping command and looking at what it wrote.

BUILD-SWITCH contributed the complement, promoted here because it generalises
past the case that produced it:

> **A flag census enumerates the promises a tool makes and tests whether it
> keeps them. It is structurally blind to a stage that makes no promise.**

Twenty-seven flags were enumerated in an earlier audit. **Zero** of them match
`hull` or `clamp`, which is why an operation touching 24.6% of pixels was
invisible to a census that was otherwise complete and correct. The complement to
a census is not a longer census: it is tracing the default configuration and
asking what the `if let Some` overrides do *not* cover.

### 59.3 The veil is a pedestal error, and the base band is a plain mean

The flagship master has one visible defect left: a haze over the bee's tarsus
and claw. Section 58 recorded a failed attempt to diagnose it -- a probe window
that turned out to be sitting on blank background, caught by its own control.
V-VEILCLAW was given that failure in writing and re-ran it properly. The result
is the most actionable finding of the run.

Probe box `y 2640:2830 x 2080:2270`, all 299 frames, step 1, with the control
kept unchanged and a **null** window added on plain paper:

```
CONTROL: SINGLE-PEAK  floor=83.3  f244 prom=0.24
NULL   : FLAT (no peak with prominence >= 0.10 of floor)
PROBE  : TWO-PEAK     floor=84.2  f182 prom=0.45   f288 prom=0.29
```

The control responds, the null stays quiet, and the probe is **bimodal**: two
peaks on the same pixels, **108 frames apart**. A per-frame contact sheet says
what each peak is -- `f171-198` is sharp foreground hairs on blank paper,
`f285-291` is the claw with the hairs dissolved. This is the two-layer occlusion
case, directly observed rather than inferred.

Then the decisive measurement, each plane normalised by its own paper white:

| plane | base mean | base p5 | detail rms |
| --- | ---: | ---: | ---: |
| f288 (resolved the claw) | 0.581 | 0.206 | 0.177 |
| f180 (resolved the hairs) | 0.892 | 0.835 | 0.047 |
| **master** | **0.802** | **0.669** | **0.104** |

`corr(master_detail, f288_detail) = +0.852`; `corr(master_detail, f180_detail)
= -0.035`; `master_detail ~= 0.50 * f288_detail`.

**Selection is not the defect.** The merge picked the right frame, and the
claw's structure is present in the master at 0.85 correlation with the frame
that resolved it. What is wrong is the *pedestal*: the master's base sits at
0.802, near the foreground layer's 0.892 rather than the claw's 0.581. The claw
is rendered at half amplitude on the occluder's brightness. The veil is not lost
detail. It is lost base.

The mechanism was reported as an unconfirmed lead and was confirmed here by
reading the source rather than by accepting the report. `pyramid.rs:895` sets
`base: BaseBand::Mean` as the default; `pyramid.rs:673` sets
`DEFAULT_MEAN_COARSE = 0`; `pyramid.rs:608-612` defines `Mean` as a "plain mean
across frames" that "does not depend on position at all." So the base residual
is an unweighted mean over all 299 frames, roughly 290 of which show the
defocused bright foreground at that pixel. The mean drags 0.581 to 0.802, the
detail band is selected correctly, and the correct detail is added to the wrong
pedestal. Signature and mechanism agree.

The sharpest part is that **the file already names this failure mode.**
`pyramid.rs:622-627`, arguing the case *for* the rejected `WeightedFromCoarsest`
arm, says it buys "local tone: at a depth boundary the in-focus frame's low
frequencies win locally instead of being averaged with every defocused frame's
veil." The project wrote down the veil, measured the alternative, found it cost
-2.5% of global level plus about 4% of position-dependent wander on featureless
backdrops, and correctly shipped the arm that has the veil.

Both arms are wrong, and the reason the choice looked forced is that nobody
noticed the two defects live in **disjoint** regions. A featureless backdrop has
no focus signal and no bimodality; an occlusion boundary has both. The base band
does not have to choose between being position-independent everywhere and
position-dependent everywhere -- it needs to be position-independent *where
there is no evidence* and to respect layer structure *where there is*. That is a
third arm neither existing option explored, the detector for it is now built and
commissioned, and it has been routed to the owner of `pyramid.rs`.

> **When two arms of a measured trade-off are both wrong, check whether their
> defects share a domain before accepting the trade.** A trade-off between
> defects that never co-occur is not a trade-off; it is two separate problems
> being solved with one switch.

### 59.4 Two corrections that came with it

**Master-to-raw is not near-identity, and this corpus said it was.** The
recorded fact was that the master at 4688x7032 and the green lattice at
2344x3514 differ by about 4 px and map near-identically. That holds only at the
optical centre. There is roughly 13% magnification breathing across the bracket,
about 0.35 px/frame per axis at the claw, and *within a single frame* the
required registration shift differs by **more than 150 px** between regions,
growing with distance from centre: at f240, region (4000,3400) needs
dy=-186,dx=+20 while region (3285,2065) needs dy=-94,dx=+152. Any fixed box
carried between master and raw coordinates without per-frame drift correction is
measuring the wrong pixels. That is exactly how the first attempt at this
diagnosis failed, and the corrected fact has been sent to every agent whose work
crosses that boundary.

A useful corollary, unlooked for: the drift is smooth and monotonic across the
bracket, which makes it breathing rather than subject motion. That is evidence
*against* the urgency of the dormant outlier-rejection module, and it arrived
from a probe aimed at something else entirely.

**And my own probe was blind to the case it was built for.**
`throughfocus_probe.py` exists to distinguish merge defect from capture limit
from two-layer veiling, and its docstring names bimodality as the important
case. Its `verdict()` takes the argmax of the response curve and asks only
whether that peak is interior. On this window it returned `INTERIOR-PEAK
frame#182` -- the *foreground* peak -- and would have reported MERGE. It cannot
see a second peak at all. The instrument named the case in prose and then
implemented a statistic incapable of expressing it.

> **A statistic that reports the location of a maximum cannot report that there
> were two.** If the docstring names bimodality, the implementation owes a
> prominence test, not an argmax.

### 59.5 What the three findings have in common

The flower ranking was an instrument reporting confidently about the subject
while being asked about the tool. The confidence row was a document reporting
confidently about the product while describing the source tree. The veil probe
was an instrument whose prose named a case its arithmetic could not express. All
three survived because what they said was, in a narrow sense, true -- the
flowers really do have the lowest Laplacian, the map really is implemented,
frame 182 really is the argmax -- and none would have been caught by checking
the claim as stated. All three fell within minutes of opening the object
itself: the tile, the flag table, and the response curve.

That is now seven instrument failures in this run, four of them in this
orchestrator's own hands, and not one was caught by reasoning about a result.
Every one was caught by opening the intermediate. The pattern is stable enough
to state as a working rule rather than an observation:

> **Confidence in a result is not evidence about the instrument that produced
> it.** The only thing that has ever caught one of these is looking at what the
> instrument looked at.
"""


def main() -> int:
    if not DOC.exists():
        print(f"REFUSE: {DOC} does not exist")
        return 1
    text = DOC.read_text(encoding="utf-8")
    before = len(text)

    if "## 59." in text:
        print("REFUSE: section 59 already present")
        return 1
    if not text.endswith(ANCHOR):
        print("REFUSE: file does not end on the expected anchor")
        print("--- expected tail ---")
        print(repr(ANCHOR[-120:]))
        print("--- actual tail ---")
        print(repr(text[-120:]))
        return 1

    out = text + BODY
    if len(out) <= before:
        print("REFUSE: result would not grow")
        return 1

    DOC.write_text(out, encoding="utf-8")
    print(f"OK: {before} -> {len(out)} chars (+{len(out) - before})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
