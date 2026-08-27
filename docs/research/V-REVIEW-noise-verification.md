# V-REVIEW: independent verification of the noise head-to-head

Adjudicating `docs/research/M127-noise-head-to-head.md`, the claim the project's
state-of-the-art case now rests on. Written under this project's rule that an
author never verifies their own work. No module of the original was imported;
the estimator was re-implemented from the written method in
`experiments/V-NOISE/PREREGISTRATION.md` and re-derived on the same images.

Every number below is labelled MEASURED, DERIVED or ARGUED.

## 1. Verdict

**The noise claim is CONFIRMED. The argument offered in its support is not.**

The measured half of M127 survives independent re-implementation without
qualification. All six of its shift-corrected ratios fall inside 95% intervals
computed by code that shares no line with it. strehl is quieter than `enfuse`
and than `focus-stack` in luma and in both chroma channels, and the direction is
bounded away from parity in every channel.

The *reasoning* M127 attaches to that result in its section 5 does not survive.
The "lowest noise and highest scene content in the same tiles" pairing is not
two findings. It is one measurement and an algebraic rearrangement of it, and
the ordering it reports reverses under a gauge choice M127 leaves open.

Partition of the five items assigned, summing to five:

| item | outcome |
|---|---|
| 1. re-derive the estimate independently | **confirmed**, within 2.0% on two arms and 5.0% on the third |
| 2. attack the pairing | **refuted**, the scene column is an identity |
| 3. check the survivor for cancellation | **no cancellation**, but a blind spot confirmed |
| 4. commission on my own arm and image | **passed** after I corrected my own prediction |
| 5. check comparator fairness | **fair**, with one mis-applied correction found |

## 2. Item 1, independent re-derivation

Implemented from the method, not the code: per tile, per channel, normalised by
that tile's own mean luma, on linear Rec.709 opponent channels.

    flat-ROI   sigma = std(x - uniform_filter(x, 9)) / mean_luma
    half-diff  sigma = sqrt(0.5 * var(A - B)) / mean_luma

The tile census was read as data only. MEASURED, medians over 110 flat tiles:

| arm | M127 raw luma | mine | agreement |
|---|---:|---:|---:|
| strehl | 0.07859 | 0.08017 | 1.020 |
| `enfuse` | 0.08394 | 0.08570 | 1.021 |
| `focus-stack` | 0.09953 | 0.10141 | 1.019 |

Three independent implementations of a normalised standard deviation landing
within 2.1% of each other is a confirmation. The residual is accounted for by
`enfuse` writing **RGBA**, where the fourth plane is 1.0 everywhere: a loader
that averages over the last axis reads 0.26051 instead of 0.01401, an 18.6x
corruption. My loader drops it. So does theirs.

## 3. Item 4, commissioning, including a defect of my own

The pre-registration fixes NULL at 1.000 +/- 0.005 and POTENCY within 10%.
MEASURED on the arm and image actually used, not carried across from
`coffee-bubbles`:

| control | measured | predicted | error | outcome |
|---|---:|---:|---:|---|
| NULL, image against itself | 0.00000000 | 0 | exact | pass |
| POTENCY 0.5x | 0.08476 | 0.08469 | 0.08% | pass |
| POTENCY 2.0x | 0.13914 | 0.13830 | 0.61% | pass |
| POTENCY 4.0x | 0.24251 | 0.23955 | 1.24% | pass |

**My first potency run failed at 2.0x with 21.78% error, and the defect was
mine.** I predicted `sqrt(s0^2 + sadd^2)`. Noise planted into one half of a
half-difference contributes only half its variance, so the target is
`sqrt(s0^2 + 0.5*sadd^2)`. DERIVED, and confirmed by three levels agreeing to
within 1.24% once corrected.

The instructive part is the 0.5x arm. Against the wrong formula it read 5.01%
error and **passed**, because the missing factor is small when the plant is
small. A single-level commissioning would have certified a wrong prediction.
Two levels were pre-registered and the second level is what caught it.

## 4. Item 5, is the comparison fair

MEASURED. Both comparators load from one shared 63-frame aligned tree,
`C:\dev\strehl-out\V-LINEAR2\aligned`, named directly in
`logs/coh-fs15-A.log`. Range fairness, with the arithmetic corrected as noted in
section 7:

| arm | dtype | planes | max | of range | mean |
|---|---|---:|---:|---:|---:|
| strehl | uint16 | 3 | 65535 | 100.0% | 0.0252 |
| `enfuse` | uint16 | 4 | 65535 | 100.0% | 0.0270 |
| `focus-stack` | uint8 | 3 | 255 | 100.0% | 0.0266 |

No arm is clipped, floored or exposure-penalised; the three means agree within
7%. `focus-stack` emits 8-bit because the tool emits 8-bit, which is why a
quantisation penalty has to be removed before its ratios read as an algorithm
comparison. The 8-to-8-bit identity control passes exactly in all three
channels, so my requantiser adds nothing of its own.

**But M127 does not apply the penalty it measured.** MEASURED, by dividing its
own published columns:

| channel | penalty M127 states | factor M127's table actually divides by |
|---|---:|---:|
| luma | 1.124 | 1.093 |
| R-Y | 1.333 | 1.090 |
| B-Y | 1.548 | 1.131 |

My own requantisation measures 1.167, 1.390 and 1.596, close to what M127
*states*. On chroma its correction is applied at roughly a quarter of the
measured size. Applying the measured penalty to my raw ratios gives 1.088,
1.623 and 1.627 against M127's published 1.161, 2.028 and 2.237. **The error
runs in strehl's favour and the published chroma advantage over `focus-stack`
is overstated by about 0.4 to 0.6x.** The direction of the finding is unchanged;
its size is not.

## 5. Item 2, the pairing, refuted

M127 section 5 argues strehl cannot merely be blurrier because it reads lowest
noise **and** highest scene content, calling the scene column a different
statistic. MEASURED, by recomputing `sqrt(flat^2 - noise^2)` from its own two
published columns:

| arm | scene as published | `sqrt(flat^2 - noise^2)` |
|---|---:|---:|
| strehl | 0.12151 | 0.12151 |
| `enfuse` | 0.10682 | 0.10681 |
| `focus-stack` | 0.09247 | 0.09247 |

The scene column is an algebraic rearrangement of the other two to five
significant figures. At a fixed total it is a strictly decreasing function of
the noise term, so "lowest noise" and "highest scene" are **one finding stated
twice**. It cannot corroborate itself.

A second separation with different failure modes, holding the total fixed and
varying only how the noise term is gauged. MEASURED:

| treatment | strehl | `enfuse` | `focus-stack` | highest |
|---|---:|---:|---:|---|
| raw noise | 0.11522 | 0.11272 | 0.12024 | `focus-stack` |
| shift-corrected noise | 0.12979 | 0.11272 | 0.12024 | strehl |
| corrected, depth-scaled | 0.13509 | 0.12798 | 0.14000 | `focus-stack` |

strehl reads highest under one treatment of three. The third assumes noise falls
as one over root N between the 31-frame half the noise term is measured on and
the 63-frame full stack the total is measured on; M127 section 6 states that
scaling is unmeasured, so this row is a sensitivity test rather than a result.
That is the point: **an unmeasured choice moves the conclusion.**

**This does not damage the noise claim.** The ratios in section 6 are direct and
carry no scene term. It removes one of the two legs section 5 stands on. The
other leg, the level sharpness result of 0.977 with interval 0.810 to 1.181 in
`docs/research/V-LINEAR2.md`, is an independent measurement of detail and is
untouched by this. **The anti-blur defence should rest on that leg alone.**

## 6. Item 3, cancellation, and one gauge question resolved

M127 withdrew its pre-registered primary after it read two arms differing 19% in
noise as 0.13585008 against 0.13585464. I looked for the same disease in the
survivor and did not find it: the half-difference has no numerator and
denominator that can cancel, and the potency series above shows it tracking a
known plant across an 8x range to within 1.24%.

It does have a **blind spot**, which M127 states as a virtue. MEASURED, by
planting a fixed deterministic pattern identically into both halves and into the
full stack:

| term | before | after | change |
|---|---:|---:|---:|
| half-diff noise | 0.08017 | 0.08017 | 0.00% |
| flat-ROI total | 0.14018 | 0.22119 | +57.79% |
| derived scene | 0.11500 | 0.20615 | +79.26% |

A reproducible artifact is invisible to the noise term and lands **entirely** in
the derived scene term, where nothing distinguishes it from detail. This is the
mechanism behind section 5's refutation: a high scene term is equally consistent
with "it stamps something into every frame".

**One criticism I formed and then withdrew on measurement.** M127's section 2
table pairs strehl's shift-corrected figure with the comparators' raw ones, and
I recorded that as cross-gauge. It is asymmetric, but MEASURED it is not unfair:
the median best integer offset is 1.41 px for strehl and **0.00 px for both
comparators**, and correcting them moves their numbers by +0.0%. The mechanism
is in the logs: both comparators draw their halves from one pre-aligned raster,
while strehl aligns internally on each run, so only strehl's halves sit on
different rasters. That offset is an artifact of the half-split design and does
not exist in the shipping product, which aligns all 63 frames once. The
corrected figure is the right one to quote. **The defect that remains is
presentational**: section 2 does not tell the reader one column is corrected,
and the fact that makes this harmless is not stated there.

The shift search got its own control, an arm that cannot contain a real offset:
two independent noise fields, where the same 49-candidate search moved the
statistic by **-0.43%**. MEASURED. The search is not fitting noise.

## 7. Two defects in my own instrument, disclosed

Both were caught by me, both are corrected above, and neither changes a reported
number. They are recorded because this project treats an undisclosed self-error
as worse than a wrong result.

**A label asserting a statistic the code did not compute.** `vn_scene.py`
printed the header `BOOTSTRAP ... 2000 resamples` over a column headed
`[95% CI]`, above a body that built a five-element throwaway list and printed
the point value. No interval existed. This is the same defect class as a control
named in prose and implemented as a filename parse: the part everyone reads
described something the predicate did not do. The intervals in section 8 are
computed.

**An overflowed percentage presented as a measurement.** `vn_boot.py` computed
`100 * a.max() / full` on a numpy uint16 scalar. `100 * 65535` wraps, and the
line reported a full-range image as "1.0% of range". The conclusion I drew from
it was correct and the number supporting it was not, which makes it an argued
conclusion wearing a measured number's clothes. Recomputed in float in section 4.

## 8. The interval that decides it

MEASURED. Ratio of medians, comparator over strehl, 2000 tile resamples,
percentile interval, both arms shift-corrected on one gauge:

| comparator | channel | mine | 95% interval | M127 | inside |
|---|---|---:|---|---:|---|
| `enfuse` | luma | 1.618 | 1.510 to 1.708 | 1.540 | yes |
| `enfuse` | R-Y | 1.813 | 1.716 to 1.967 | 1.763 | yes |
| `enfuse` | B-Y | 1.606 | 1.527 to 1.703 | 1.538 | yes |
| `focus-stack` | luma | 1.915 | 1.811 to 2.003 | 1.898 | yes |
| `focus-stack` | R-Y | 2.408 | 2.314 to 2.596 | 2.371 | yes |
| `focus-stack` | B-Y | 2.586 | 2.475 to 2.758 | 2.532 | yes |

Every published value lands inside an interval from an independent
implementation, and every interval is bounded away from parity on the low side.

**What ORCH may say.** That strehl is measurably quieter than both open-source
comparators at equal detail, by roughly 1.5 to 1.8x against `enfuse` in all
three channels. **What ORCH should stop saying.** That strehl shows more scene
content as well; that is the same measurement counted twice. And the
`focus-stack` chroma figures should be restated at about 1.6x rather than 2.0 to
2.2x once the penalty M127 measured is applied at the size it was measured.

## 9. What is not verified

- The comparison is a **shadow-noise** comparison. The 110 tiles are the dark
  quartile, median tile mean luma 0.01304 linear. MEASURED. Nothing here
  measures midtone or highlight noise, and M127 says so.
- One subject, one stack. Six ratios from 110 tiles of one image are not a
  corpus result.
- All statistics here are purely spatial. **No frequency transform is taken**,
  so the formally withdrawn statistic above 0.30 cyc/px does not apply to any
  number in this document.
- I did not verify that the aligned tree is byte-identical to what strehl itself
  consumed, and it is not: strehl reads the linear frames and aligns internally,
  while the comparators read a Hugin-resampled copy at 7029 px against strehl's
  7032 px. That resampling correlates noise, which would flatter the
  comparators on this statistic rather than penalise them, so it does not
  threaten the direction of the result. Its size is unmeasured.

## 10. Scripts

All under `experiments/V-REVIEW/`, none importing anything from
`experiments/V-NOISE/`.

| script | what it does |
|---|---|
| `vn_probe.py` | shapes, dtypes, ranges, census contents; found the RGBA plane |
| `vn_half.py` | the independent re-derivation of the estimator |
| `vn_comm.py` | commissioning, quantisation penalty, alpha control |
| `vn_shift.py` | corrected potency, selection-bias null, one-gauge ratios |
| `vn_scene.py` | the three attacks on the pairing |
| `vn_boot.py` | bootstrap intervals |
| `vn_fair.py` | comparator input and range fairness |


## 11. The publishable table, on one named gauge

**The gauge is: container-matched, shift-corrected.** Every ratio is comparator
over strehl, where strehl has first been placed in **the comparator's own
container**, and both arms are registration-corrected by the same 49-candidate
integer search driven on luma. Against `enfuse` the requantisation is a no-op,
both being 16-bit. Against `focus-stack` strehl is requantised to 8 bits.

**Why this convention and not a penalty divisor.** A quantisation penalty is not
a property of the container. MEASURED, the same 8-bit requantisation of the same
strehl arm costs **+16.4%** luma on the raw gauge and **+29.8%** luma on the
shift-corrected gauge. Both are correct. Quantisation adds an independent
variance floor, so the same absolute floor is a larger fraction of a smaller
baseline, and the shift correction lowers strehl's luma noise from 0.07985 to
0.05296. The floor recovered from one gauge predicts the other to within 3.5%,
0.2% and 0.4% in the three channels, which confirms one phenomenon rather than
two measurements.

A divisor therefore only means anything on the gauge it was measured on.
Container-matching never divides: the quantisation lives inside an arm, and the
bootstrap propagates its uncertainty for free. Commissioned before use:
requantising an already-8-bit arm changes the statistic by exactly **0.000e+00**,
and the identity ratio is exactly 1.000000000000.

**The four cells.** MEASURED, 110 shadow tiles, 4000 tile resamples, percentile
intervals.

| cell | channel | corrected value | 95% interval | clear of parity |
|---|---|---|---|---|
| vs `enfuse` | luma | **1.62x cleaner** | 1.51 to 1.71 | yes |
| vs `enfuse` | chroma | **1.61 to 1.81x cleaner** | 1.53 to 1.97 | yes |
| vs `focus-stack` | luma | **1.48x cleaner** | 1.40 to 1.51 | yes |
| vs `focus-stack` | chroma | **1.64 to 1.66x cleaner** | 1.55 to 1.76 | yes |

Per channel, so the chroma cells cannot be mis-mapped: `enfuse` B-Y 1.606, R-Y
1.813; `focus-stack` B-Y 1.640, R-Y 1.661. Every one of the six individual
channel intervals has a lower bound above 1.0.

One sentence per cell, quotable:

- **`enfuse`, luma.** Both arms sit in the same 16-bit container and both are
  registration-corrected, so this is an algorithm comparison on shadow
  luminance grain; it covers one 63-frame stack and says nothing about midtone
  or highlight noise.
- **`enfuse`, chroma.** The span is the two opponent chroma channels rather
  than an uncertainty, and each channel is separately bounded away from parity.
- **`focus-stack`, luma.** strehl is placed in `focus-stack`'s own 8-bit
  container before the ratio is taken, so the number is algorithm against
  algorithm and not 16-bit against 8-bit.
- **`focus-stack`, chroma.** This replaces the published 2.03 to 2.24x, which
  divided by a quantisation penalty measured on a different gauge from the
  ratio it was applied to.

**The sentence replacing the struck paragraph.**

> Sharpness is level with `enfuse` at 0.977, and at that matched detail strehl
> leaves measurably less shadow noise than either open-source comparator --
> about 1.6x less than `enfuse` and 1.5 to 1.7x less than `focus-stack` -- with
> every interval clear of parity on two independent implementations.

The matched-detail half of that sentence comes from the sharpness measurement in
`docs/research/V-LINEAR2.md`, **not** from the noise measurement. Keeping the two
sources visible in one sentence is what stops it becoming the circular claim it
replaces.

**Also worth labelling.** The README's existing luma cell, `[1.02, 1.54]`, is not
a confidence interval. DERIVED from M127's own section 4: 1.021 is its raw ratio
and 1.540 its shift-corrected one, so the bracket is the **distance between two
gauges** presented in the notation of an uncertainty. The chroma cell
`1.54-1.76x` is a channel span, which is legitimate but should say so. Both
replacements above carry real resampling intervals.

## 12. A correction to section 4 of this document

Section 4 reported that M127 under-applies its own 8-bit penalty and that **the
error runs in strehl's favour**. The first half stands. **The second half was
itself a cross-gauge comparison and is withdrawn.**

I compared corrected ratios I had computed on the **raw** gauge, 1.088, 1.623
and 1.627, against M127's published values, which are on the **shift-corrected**
gauge. That is the same fault I convicted its section 2 table of, committed by me
one section later. On the single container-matched gauge of section 11:

| channel | M127 published | mine, one gauge | direction of M127's error |
|---|---:|---:|---|
| luma | 1.161 | 1.475 | **understates** strehl's advantage |
| R-Y | 2.028 | 1.661 | overstates strehl's advantage |
| B-Y | 2.237 | 1.640 | overstates strehl's advantage |

So the error is **not uniformly in strehl's favour**. It flatters strehl on
chroma by roughly 0.4x and penalises it on luma by roughly 0.3x. ORCH was told
the favourable direction in my summary and should replace all three cells rather
than only the chroma ones.

The mechanism is the gauge-dependence measured in section 11: M127 measured a
penalty on one gauge and divided a ratio computed on another by it. Because the
luma penalty is much larger on the corrected gauge than the raw one, dividing by
the raw-gauge figure removes too little, and because its applied chroma factors
were smaller still than either measurement, it removes far too little there. The
two errors happen to point in opposite directions once the ratio itself is
recomputed on a consistent gauge.

None of this touches section 8. Those ratios never involved a quantisation
divisor and all six remain inside their intervals.


## 13. Provenance of the four published cells

Asked whether any published cell depends on build `066A87AB`, which reproduces
neither shipping corpus.

**It does not.** Established three independent ways, none relying on the others.

**First, my code cannot have used any binary.** MEASURED, by scanning all
eleven `vn_*.py` scripts for `subprocess`, `Popen`, `os.system`, `.exe` and
`vr_lib`: **no binary invocation in any of them.** The only file matching is the
audit script itself, which contains those strings as search patterns. The
verification consumed existing renders and re-derived the estimator in Python.

**Second, the inputs are not in my lane.** The four cells were computed from six
files and one tile census, none under `C:\dev\strehl-out\V-REVIEW\`:

| role | file |
|---|---|
| strehl, denominator of all four cells | `V-H2H2\lin\113-A-g1.tiff`, `113-B-g1.tiff` |
| `enfuse`, cells one and two | `V-LINEAR2\out\coh-enfuse-A.tif`, `-B.tif` |
| `focus-stack`, cells three and four | `V-LINEAR2\out\coh-fs15-A.tif`, `-B.tif` |
| tile selection only | `V-NOISE\census.npz` |

**Third, the binary that made the strehl arm is named and its hash checks out.**
`experiments/V-HEADTOHEAD2/render_linear.ps1` carries a Rule 47 record naming
pin `740e7056` at
`C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe`.
MEASURED rather than believed:

| check | result |
|---|---|
| hash of the named binary | `15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0` |
| equals the hash the harness claims | yes |
| equals the SHIP-V3 corpus seal | **yes** |
| equals the SHIP-V4 corpus seal | no |
| equals `066A87AB` | **no** |

Flags recorded with it: `stack --merge pyramid --pyramid-gate 4.5 --linear-srgb
--demosaic`, with `STREHL_FULLRES_GATHER=1`, a pinned warpmap, and eleven
`STREHL_*` variables cleared by name. `experiments/V-LINEAR2/run_free.ps1`
carries the matching record for the comparator side, including
`align_image_stack.exe` version `2025.0.1.9609d5726ad8` and the linear input
frames both comparators were developed from.

### The scope statement that should be published beside the cells

`740e7056` is a **shipping** pin, but it is the **previous** one. It rendered
SHIP-V3; the 26 masters the owner is looking at are SHIP-V4, rendered by
`9b05d0b7`. So the four cells are a measurement of a build that shipped, on a
linear measurement render rather than a master render, and **not** of the exact
binary behind the current masters.

That is a much weaker caveat than the one that sank the aura entry, where the
build had shipped nothing at all. It is not nothing, and the honest wording is:
*measured on the SHIP-V3 pin.* Whether SHIP-V4 changed merge noise behaviour is
**unmeasured here**.

The `--linear-srgb` render is correct method rather than a defect: this
project's standing rule is that quality is never judged through a transfer
curve, and the harness quotes that rule as its reason. A master render would be
the wrong arm to measure noise on.

### A defect in my own first probe, disclosed

My opening provenance probe searched for `.ok` and `.provenance.txt` sidecars
beside each input and found **zero**, against a positive control proving the
pattern can match, which found 26 under SHIP-V4. I was one step from reporting
*the provenance is not recorded*.

**It is recorded. It is not shaped like a seal.** Both harnesses carry Rule 47
comment blocks naming the binary, its hash and the full switch state, and one
even names the resolved input paths of the other lane. A seal-shaped query
cannot see a comment-shaped record, and an empty result from it means only that
this project keeps provenance in more than one form.

This is the same lesson as the earlier missing-binary episode in
`docs/research/V-REVIEW-aura-ship.md`, in different clothes: **an empty search
is a statement about the query.** There it was a filename pattern too narrow by
one wildcard; here it was a provenance *format* assumed to be the only one. The
positive control proved my pattern worked and still did not save me, because a
control proves the query can match things of the kind it looks for -- it cannot
tell you that you are looking for the wrong kind.

### What `066A87AB` is

`C:\dev\strehl-out\V-REVIEW\bin\strehl-pinned.exe`, 9,716,736 bytes, hash
beginning `066A87AB`. MEASURED: it is the only copy on this machine and it
produced exactly eight images in my lane, four under `geom` and four under
`halo2`, carrying **no seals**. Those are the renders whose seals I declined to
backfill, and no number in this document or in the four published cells derives
from them. The aura measurement that ORCH acted on used `9b05d0b7`, derived from
the SHIP-V4 seal, and its pyramid arm was byte-identical to the shipped master.


## 14. Do the four cells hold on the SHIP-V4 pin?

**Verdict: HOLD.** All six per-channel ratios are unchanged and all six remain
clear of parity. The scope line can be struck. The reason is stronger than the
verdict: **the pin question turned out to be empty, and it took a measurement to
find that out.**

The decision rule was written and committed as `e358bd3c` before any SHIP-V4
render existed. Its threshold was the published interval, on the six
per-channel ratios rather than the four rounded cells, because a rounded cell
hides movement.

### What was rendered

Pin verified by hash before use, never by path or size, since four builds on
this machine share size 9,568,768:

    44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490

which equals the SHIP-V4 corpus seal. The strehl A/B half-stack pair for
subject 113 was re-rendered with the switch state copied verbatim from the Rule
47 block of `experiments/V-HEADTOHEAD2/render_linear.ps1` -- `stack --merge
pyramid --pyramid-gate 4.5 --linear-srgb --demosaic`, `STREHL_FULLRES_GATHER=1`,
the pinned per-half warpmap, eleven variables cleared by name, and a check that
no other `STREHL_*` was set in the calling process. Comparator outputs and the
tile census were held fixed. Both renders were sealed at render time.

### The commissioning gate fired

The pre-registration required the SHIP-V4 render to **differ** from the SHIP-V3
arm, because rendering with the wrong binary produces exactly the "no change"
answer a real null produces. MEASURED:

| half | SHIP-V3 pin | SHIP-V4 pin | differ |
|---|---|---|---|
| `113-A-g1` | `F6810573765972E9...` | `F6810573765972E9...` | **no** |
| `113-B-g1` | `41DA8F97C2BD7B0F...` | `41DA8F97C2BD7B0F...` | **no** |

Byte-identical. By the rule I had already committed, that is a red flag to
diagnose rather than a clean null, and it had to be established positively by a
route other than my own run. Two routes were used.

**Route one, is my harness inert?** A responsiveness control: same pin, same
command, one environment variable changed to `STREHL_FULLRES_GATHER=0`.
MEASURED, the output hash becomes `DACB36FB1141AD86...` -- completely different.
The harness genuinely invokes the binary and its output responds to input state.

**Route two, the source.** MEASURED, `git diff 740e7056 9b05d0b7` touches 99
files, of which seven are under `crates/`. Four are `examples/*.rs`, which
compile to separate binaries and cannot reach `strehl.exe`. The diffs to
`strehl-core/src/photometric.rs` and `strehl-core/src/highlight.rs` are **doc
comments and one test rename** with no executable change; `DEFAULT_KNEE` stays
`0.60`. That leaves `crates/strehl-cli/src/image_out.rs`, whose only behavioural
change is one match arm:

| condition | `740e7056` | `9b05d0b7` |
|---|---|---|
| matrix, `--srgb` | sRGB profile | sRGB profile |
| matrix, linear, **no tone** | linear-sRGB profile | linear-sRGB profile |
| matrix, linear, **with tone** | linear-sRGB profile | **none** |

The changed arm requires a linear render that also carries a tone curve. This
measurement path is `--linear-srgb` with no `--exposure` and no
`--auto-exposure`, so it has no tone and takes the unchanged arm. **The two
binaries are required to agree here, and they do.**

### The cells

MEASURED, same gauge, same code, same 2000-resample bootstrap:

| comparator | channel | SHIP-V3 published | SHIP-V4 | SHIP-V4 interval | clear |
|---|---|---:|---:|---|---|
| `enfuse` | luma | 1.618 | 1.618 | 1.511 to 1.709 | yes |
| `enfuse` | B-Y | 1.606 | 1.606 | 1.525 to 1.702 | yes |
| `enfuse` | R-Y | 1.813 | 1.813 | 1.717 to 1.966 | yes |
| `focus-stack` | luma | 1.475 | 1.475 | 1.400 to 1.514 | yes |
| `focus-stack` | B-Y | 1.640 | 1.640 | 1.550 to 1.710 | yes |
| `focus-stack` | R-Y | 1.661 | 1.661 | 1.592 to 1.755 | yes |

Six points inside their published intervals, six intervals clear of parity, six
rounded cells unchanged. **HOLD** on the pre-registered rule.

**These six numbers are not independent evidence and should not be read as
such.** The inputs are byte-identical, so identical statistics follow by
construction. Running the estimator confirms no file was mixed up; it confirms
nothing about the pipeline. The residual deltas, all below 0.0005, are the
rounding of the published three-decimal values and not movement.

### The finding that outranks the verdict

If the two pins agree on this path, do they agree on the delivered images?
MEASURED, hashing every master in both corpora:

**All 26 subjects are byte-identical between SHIP-V3 and SHIP-V4.** Identical
26, differing 0, missing 0, summing to the 26 subjects present. The seals name
different binaries -- `15EA7346...` against `44C2F2CD...` -- over the same
pixels.

So the two shipping corpora are **one set of images rendered by two builds that
agree**, not two generations of output. The distinction is a labelling
distinction on these files. That retires the scope concern completely rather
than narrowly: any measurement on either corpus applies to both, which also
means the print-readiness adjudication done on SHIP-V3 and the aura work done on
SHIP-V4 were always on the same pixels.

This does **not** say the binaries are equivalent in general. They provably
differ on linear-plus-tone renders. It says they agree on every path either
corpus exercises, and that was worth measuring rather than assuming in either
direction.

### Cleanup

The three renders made here are byte-identical duplicates of files already on
disk, or a control whose result is its hash, so the `.tiff` artifacts were
removed after measurement and their `.ok` and `.provenance.txt` records kept.
Nothing is lost: the exact bytes of the measurement arms remain at
`C:\dev\strehl-out\V-H2H2\lin\`, and each render reproduces in under 40
seconds from the sealed provenance.


## 15. Was the comparator input denoised? No — and the premise was inverted

Pre-registered in `experiments/V-REVIEW/PREREG-nr.md`, committed as `f5b0e2e0`
before any probe was run.

### 15.1 The converter, named

The RAW-to-TIFF step that feeds `enfuse` and `focus-stack` is not a third-party
converter. It is **strehl's own decoder**, pin `740e7056`, sha
`15EA7346...A7B0` — verified by `Get-FileHash -SHA256` and equal to the SHIP-V3
corpus seal. It is invoked by `experiments/V-LINEAR/develop_frames.ps1` as a
one-frame `stack ... --linear-srgb --demosaic` with `STREHL_ALIGN=0`, producing
63 frames of 197,798,923 bytes each at `C:\dev\strehl-out\V-LINEAR\lintiff\`.

**This is the same binary that rendered the strehl arm.** Both sides of the
head-to-head share the decoder bit for bit, so a decoder-level denoiser cannot
produce an asymmetry between them. That is structural and it already answers the
confound, but this project does not accept an argument from absence, so it was
measured anyway.

### 15.2 A defective search, caught by its own control

The first pass reported no denoise function anywhere in `crates/`. **That result
was an artifact of a broken query.** `Select-String -Path 'crates\**\*.rs'` does
not recurse in PowerShell. The positive control — search for a function that is
known to exist — returned `demosaic-ish fn definitions found: 0`, and a parallel
count found one `STREHL_*` environment variable where eleven were known. The
control caught it; the null was discarded and re-run under ripgrep, where the
same control returns eleven `demosaic` definitions.

Re-run correctly, three candidate forms were searched and all are empty: no NR
function in `crates/`, no config-file reader, and a complete dependency set —
`anyhow`, `thiserror`, `rayon`, `clap`, `tracing`, `rawler`, `tiff` — that
contains no image-processing library able to denoise.

### 15.3 The discriminator, and commissioning against a real denoiser

Chroma noise reduction works by averaging chroma over a neighbourhood, so its
unavoidable fingerprint is chroma noise correlated far beyond the demosaic
kernel's support. **D1** is the radius at which the normalised autocorrelation
of the high-passed chroma plane falls below 0.10, median over the 110 vetted
census tiles.

Commissioning did not use a synthetic blur. The identical `.ARW` was developed
twice through `rawpy`/LibRaw — once with all NR off, once with **FBDD full plus
two median passes** — so the probe was tested against a production denoiser
working on the same photons. All three pre-registered arms passed. MEASURED:

| commissioning arm | luma | R-Y | B-Y | required | result |
| --- | --- | --- | --- | --- | --- |
| C1 null, same frame twice | 1.64 | 2.19 | 2.23 | ratio exactly 1.000 | pass |
| C2 potency, FBDD full | 1.67 | 2.69 | 2.77 | chroma must separate | pass |
| C2 as a ratio to reference | 1.016x | 1.228x | 1.242x | greater than 1.15x | pass |
| C3 floor, white noise | 0.88 | 0.88 | 0.88 | shortest measured | pass |

The potency arm moved **chroma** by 23 to 24 percent and **luma** by 1.6
percent. FBDD is a chroma denoiser, so the probe responded in the correct
channel and not merely in the correct direction. That is the stronger result.

### 15.4 Result: no noise reduction was applied

MEASURED, D1 in pixels, 110 tiles, subject `113MSDCF`, frame `DSC00001`:

| development | luma | R-Y | B-Y |
| --- | --- | --- | --- |
| LibRaw, all NR off (reference) | 1.64 | 2.19 | 2.23 |
| **strehl `740e7056` (the comparator input)** | **1.48** | **2.27** | **2.24** |
| LibRaw, FBDD full (denoised) | 1.67 | 2.69 | 2.77 |

The comparator input sits **on the undenoised reference on both chroma
channels** — 2.27 against 2.19, and 2.24 against 2.23 — and nowhere near the
denoised arm at 2.69 and 2.77. On luma it reads *shorter* than the reference,
which is the signature of a sharper demosaic, the opposite of denoising.

**Verdict: NO NOISE REDUCTION. The confound is excluded.** The comparator inputs
were not denoised, so the six cells compare two merges.

### 15.5 The premise was inverted, and it matters more than the verdict

The task described the six cells as showing that "we are measurably noisier than
both comparators," with chroma "consistently worse for us." **Both statements
are backwards.** Every ratio in the published table is comparator-over-strehl,
printed as *cleaner*, and `vn_table.py` says so in its own docstring.

Stated as absolute sigma, where no orientation can be misread — MEASURED, same
gauge, same tiles, sigma times 1000, **lower is cleaner**:

| arm | Y | R-Y | B-Y |
| --- | --- | --- | --- |
| **strehl** | **52.96** | **60.70** | **56.01** |
| strehl in the 8-bit container | 68.75 | 88.02 | 88.29 |
| `enfuse` | 85.70 | 110.04 | 89.97 |
| `focus-stack` | 101.41 | 146.19 | 144.84 |

**strehl is the cleanest arm on all three channels.** These reproduce the
published cells exactly — 1.618, 1.813 and 1.606 against `enfuse` — which is an
internal control on the whole section.

Two consequences follow.

- **There is no noise deficit to close.** A build lane sent to fix it would be
  chasing a sign error.
- **The NR hypothesis was pointed the wrong way from the start.** A denoiser
  running on the comparator inputs would make the comparators *cleaner* and
  shrink strehl's lead. The observed pattern is that strehl's lead is **largest
  on chroma** — 1.813x on R-Y against `enfuse` versus 1.618x on luma. That is
  the opposite of the chroma-NR signature, so the stated motivation could have
  been ruled out on direction before any file was read.

### 15.6 A measurement I withdrew, with the mechanism

To attribute the difference to the merge, single-frame noise was measured on an
input frame and divided by the merged output — ideal `sqrt(31.5) = 5.61` for a
half stack. It returned **0.56x luma for all three arms**: every merge appeared
to *add* luma noise. An averaging merge cannot do that, so the number was
diagnosed rather than reported.

MEASURED, two estimators on the same images and tiles, sigma times 1000:

| arm | half-diff Y | high-pass Y | inflation |
| --- | --- | --- | --- |
| strehl | 52.96 | 136.61 | 2.58x |
| `enfuse` | 85.70 | 137.30 | 1.60x |
| `focus-stack` | 101.41 | 135.36 | 1.33x |

The high-pass estimator reads **136.6, 137.3 and 135.4** — nearly identical
across three arms whose true noise differs by a factor of two. It is measuring
the scene, which is the same scene, and the inflation is largest on the sharpest
arm. **The 9-pixel high-pass cannot separate detail from noise, and a merge adds
detail.** The reduction factors are withdrawn; they measured detail gained.

This is the same blind spot recorded in section 6, reached from the other
direction, and it is why the half-difference estimator exists.

A scene-blind reduction factor is **not measurable from this corpus**: it needs
two exposures at identical focus, and a focus stack contains none. Saying so is
the honest answer.

### 15.7 What is still open

The live alternative explanation is the one already flagged in section 9 and
still unquantified: each arm carries one registration resample, but **the
kernels differ** — Hugin's for the comparators, catmull-rom for strehl — and
resampling correlates and suppresses high-frequency noise. That would flatter
the comparators, meaning the measured strehl lead is if anything conservative.
It remains the most likely residual confound and it is not addressed here.
