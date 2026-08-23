# M18 — the sufficient-statistics seam, implemented

Status: **MEASURED, NOT INDEPENDENTLY VERIFIED.** Every number here came from a
command run in this repository tonight; none of it has been checked by anyone
but its author, and project rule 12 says that is not enough.

Artifacts: `out/m18/stats-109.txt`, `out/m18/stats-119.txt`,
`out/m18/stats-coffee.txt`, `out/m18/baseline-109.txt`, `out/m18/baseline-119.txt`,
`out/m18/argmax-109.txt`, `out/m18/argmax-119.txt`. `out/` is gitignored; the
transcripts are local.

Code: `crates/strehl-core/src/through_focus.rs` (new),
`crates/strehl-core/src/focus.rs` (fine scale added, operator untouched),
`crates/strehl-cli/src/merge_cmd.rs`, `crates/strehl-cli/src/main.rs`.

---

## 0. The brief was stale, and saying so is part of the deliverable

The M18 brief asks for four things. Before writing any code I checked each
against the repository as it stands, because the milestone numbering is not the
order the work happened in.

| Brief item | State found | Evidence |
| --- | --- | --- |
| 1. Focus-field regulariser, width 17, parameterised, O(1) box | **already built** | `merge.rs::REGULARISER_RADIUS = 8`, facts 310-314 (M37) |
| 2. Noise-gated accumulation in calibrated sigma | **already built** | `merge.rs::Gate`, `--gate`/`--target-n-eff`, facts 320-324, 330-331 (M38) |
| 3. The architectural seam — per-pixel sufficient statistics | **NOT built** | M37 answered the seam in favour of two-pass and explicitly did *not* retain per-pixel state (fact 310); SYNTHESIS fact 152 and questions 90/95 reserve it for M18 |
| 4. Robustness / outlier mask | **not built** | declared below |

The brief also states the test baseline is 70. It is **107** (34 cli + 65 core +
8 raw), measured before I changed anything. The brief's acceptance targets are
likewise quoted against the pre-M37 shipped binary: it says argmax is 1.068x on
109MSDCF's flat ROI, and that is still exactly right, but it says the *merge*
must be brought under 1.0x when M38 already brings it to 0.890x at gate 2.

So M18's real content is item 3, plus re-measuring the acceptance invariants and
supplying the nulls that were missing. That is what this document reports.

---

## 1. The seam decision

**Decision: gather the sufficient statistics in PASS TWO, anchored on pass one's
regularised winner. Retain 60 bytes per pixel, constant in the frame count.**

### Why pass two, and why this is not a third pass

The merge is already two-pass (M37). At the *start* of pass two the regularised
winner `k*` is known for every pixel, because pass one computed it. That single
fact makes the through-focus neighbourhood gatherable in O(1) state:

- the parabola triple is `(f[k*-1], f[k*], f[k*+1])`. Each of those three slots
  is written by **exactly one** frame — the frame whose index equals `k*-1`,
  `k*` or `k*+1` — so a frame either writes a slot or does not, and never
  contends. The fold is therefore exactly commutative and associative, which is
  what a `par_chunks` reduce requires.
- top-k, the floor, and the far-peak maximum are order statistics and fold
  trivially.

This cannot be done in pass one. `par_chunks` gives each worker a *contiguous*
range of frames, and the neighbour of a chunk-first argmax may live in another
worker's range and was never folded by this one. The anchor has to be known
before the frames are walked, and pass one is the thing that computes it.

**Measured cost of the second pass on this machine** (109MSDCF, 22 frames, warm
cache, from `out/m18/stats-109.txt`): pass two decode **1.775 s summed across
workers, 80.7 ms/frame**; field + gate 7.564 s summed, 343.8 ms/frame; pass two
wall clock 6.429 s. The second pass over the frames is real but it is not the
dominant term, and it was already being paid before this milestone.

### What is retained, and why it suffices for a posterior

`ThroughFocus`, one entry per CFA plane pixel:

| field | type | bytes | what it is for |
| --- | --- | --- | --- |
| `anchor` | `u16` | 2 | pass one's regularised winner `k*` |
| `anchor_focus` | `f32` | 4 | posterior offset; also the `absorb` merge guard |
| `triple` | `[f32; 3]` | 12 | **(a)** parabola position, and the log-fit height |
| `floor` | `f32` | 4 | log-fit baseline (fact 272) |
| `top_val` | `[f32; 4]` | 16 | **(b)** |
| `top_idx` | `[u16; 4]` | 8 | **(b)** |
| `far_val`, `far_idx` | `f32`, `u16` | 6 | **(c)** bimodality |
| `z`, `w` | `f32`, `f32` | 8 | untruncated posterior sums |
| | | **60** | |

The brief's three requirements, each computable with **no further pass over the
frames**:

- **(a) sub-frame peak by parabola fit** — `subframe_offset` fits the vertex of
  the retained triple. Fact 273 says the parabola is good for *position* (4.03x
  over argmax) and disqualifying for *height*, so height is taken instead from a
  log-domain fit with baseline subtraction (`subframe_deficit`), which is facts
  272/302/304.
- **(b) top-k frame indices and values** — `top_val` / `top_idx`, k = 4.
- **(c) bimodality** — `far_val - floor`, the best response at least
  `PEAK_SEPARATION = 2` frames from the anchor, minus the stack floor.

And for the milestone after this one — the per-pixel posterior over
frame-of-best-focus — the retained `z` and `w` are the trick that makes it
honest. With `u_k = (f_k - anchor_focus) / T` and `T = sqrt(2) * FOCUS_NOISE_SD`
(fact 260's calibrated temperature, never `std_k(f_k)`), `u_k <= 0` **by
construction** because `anchor_focus` is the maximum over frames. So `exp(u_k)`
lies in `(0, 1]` and cannot overflow, and

```
Z = sum_k exp(u_k)      W = sum_k u_k exp(u_k)
H = ln Z - W/Z          perplexity = exp(H)
```

are exactly mergeable sums. This gives the posterior entropy over **all** frames,
not the top four. That matters: fact 283's p99 perplexity is 4.74, which sits
right at the TOP_K = 4 cap, so anything computed from the top-k list alone would
be truncated exactly where it is most interesting.

### The memory ratchet

| | bytes/px | 22 frames | 33 frames | 105 frames |
| --- | --- | --- | --- | --- |
| fine focus **volume** (forbidden, O(frames)) | `4N` | 725 MB | 1088 MB | 3461 MB |
| `ThroughFocus` (O(1) in frames) | **60** | **494 MB** | **494 MB** | **494 MB** |

MEASURED, printed by the binary: `60 B/px = 494 MB per gather, CONSTANT in the
frame count` on both stacks, and the volume line changes with the stack while
the statistics line does not. Break-even is 15 frames; the corpus starts at 22,
so the ratchet is a win everywhere it is used and the margin grows without
bound. The plane is 8,241,504 px.

The statistics are **opt-in** (`--stats`) and are **priced into the memory
plan**, so turning them on reduces the worker count the budget licenses rather
than silently exceeding it. `the_statistics_are_priced_into_the_plan_and_do_not_grow_with_the_stack`
asserts all of that, including at 400 frames, and asserts the object is cheaper
than a 22-frame volume — so if a future change makes it O(frames), the test says
so instead of the machine swapping.

### The gather is provably non-perturbing

MEASURED, and the strongest single check in this milestone. 109MSDCF at gate 2.0,
merged output written twice:

```
strehl merge C:\dev\macro\test\109MSDCF --gate 2 --out nostats.tif
strehl merge C:\dev\macro\test\109MSDCF --gate 2 --out withstats.tif --stats --stats-placebo
```

```
DF6C3DE2B0B0AE143B997854B2E1A820BB744BB4D902B13FF8B0AC1290C815EE  nostats.tif
DF6C3DE2B0B0AE143B997854B2E1A820BB744BB4D902B13FF8B0AC1290C815EE  withstats.tif
```

**Byte-identical SHA256 over 3516x2344x3 16-bit pixels.** Two gathers, a second
`box_mean` at radius 2, and a full permutation placebo, and not one output bit
moved. The statistics are an observer, not a participant.

### The one cost, stated plainly

The statistics are gathered at a **5x5** box on the focus field, not the 27x27
selection window. That is forced: fact 152 measured bimodality enrichment at
**4.38x** at radius 2 and **0.36x — depleted** — at radius 13. A bimodality
statistic read at the selection scale measures nothing.

The consequence is that the fine field is much noisier than the selection field.
MEASURED in-crate over 12 SplitMix64 seeds on a 512² plane:

| field | mean response | sd | ratio to selection |
| --- | --- | --- | --- |
| fine, r = 2 | 0.542903 | **0.090400 ± 1.70e-4** | 5.94x |
| coarse, r = 13 | 0.542753 | 0.018847 ± 6.53e-5 | 1.24x |
| regularised, r = 13 then 8 | 0.542693 | **0.015214** | 1.00x |

The last row reproduces the shipped `FOCUS_NOISE_SD = 0.015214` **exactly**,
which is the instrument check: the same harness that measures the new constant
recovers the old one.

So the fine argmax disagrees with the regularised winner at **78.081%** of pixels
on 109MSDCF and 79.237% on 119MSDCF. That is not a defect — it is a 5.94x noisier
field doing what a 5.94x noisier field does — and it is the reason the *screening*
form of the flag is `fine_peak_outside_triple` (off by >= 2, so the parabola
cannot reach it: 54.843% / 57.247%) and not raw disagreement. Off-by-one is
harmless because the triple still brackets the fine peak.

---

## 2. The acceptance invariants, both stacks, both axes

Rule 9: **every noise number is paired with a detail number.** Fact 24 is the
reason — a plain mean's sigma looks harmless (0.899x, 0.995x) while its mean
gradient collapses -58% / -53%. Sigma alone cannot see detail destruction.

The detail column judged is `corrected = sqrt(raw^2 - model^2)` (fact 322: mean
|grad| is confounded by noise **with the same sign as the effect**, so an
uncorrected reading charges the merge for removing noise). `m2` is reported in
fact 24's own convention so the comparison is legitimate.

### 109MSDCF — 22 frames, ISO 160, flat `2272,1344,256,256`, detail `1630,1044,256,256`

| selector | flat sigma ratio | corrected detail retention | index speckle |
| --- | --- | --- | --- |
| one frame (frame 11) | 1.000x (28.201 DN) | 1.000x (18.7332) | — |
| **shipped argmax** (`strehl stack`) | **1.068x** | — | **1.010%** |
| merge, gate 0 (regularised selector) | 1.074x | 1.257x | — |
| merge, gate 1.0 | 0.973x | 1.257x | — |
| **merge, gate 2.0** | **0.890x** | **1.254x** | — |

### 119MSDCF — 33 frames, ISO 50, flat `2896,1968,256,256`, detail `2016,1152,256,256`

| selector | flat sigma ratio | corrected detail retention | index speckle |
| --- | --- | --- | --- |
| one frame | 1.000x | 1.000x | — |
| **shipped argmax** (`strehl stack`) | **1.061x** | — | **1.183%** |
| merge, gate 0 | 1.060x | 1.027x | — |
| merge, gate 1.0 | 1.003x | 1.021x | — |
| **merge, gate 2.0** | **0.960x** | **1.021x** | — |

Both stacks pass the "never worse than one frame" bar at gate 2.0 while the
detail metric moves by less than 0.3% and 0.6% respectively. Fact 24's collapse
is -58%. **The gate is buying noise reduction without buying blur.**

### Two things in these tables that are not flattering, and are reported anyway

1. **The brief's flat ROI does not transfer between stacks.** `2272,1344` on
   119MSDCF gives a single-frame sigma of **61.4 DN against a model prediction of
   16.1 DN** — it is not a flat region on that stack at all, and using it would
   have produced a meaningless ratio. The ROIs above come from
   `experiments/m11-focus-bakeoff/data/rois-119MSDCF.txt`. This is fact 88 in
   action and it should be a standing rule.
2. **On 109MSDCF the unregularised argmax (1.068x) is very slightly quieter than
   the regularised gate-0 selector (1.074x).** The regulariser is not a noise win
   by itself at gate 0; the noise win is the gate. This is consistent with fact
   86's message and is the sort of number that disappears from reports that only
   quote the best row.

Retention above 1.0x is expected and is not a bug: the reference is **one frame
of a focus bracket**, so much of the detail ROI is out of focus in it. The
failure this test catches is corrected retention *falling* as the gate opens.
It does not fall.

---

## 3. Nulls and positive controls

### Null for the bimodality statistic — the frame-permutation placebo

`--stats-placebo` gathers a second `ThroughFocus` in which each pixel keeps
exactly the same multiset of responses and exactly the same winning value, and
only the mapping from response to focus position is destroyed. Fact 19's placebo
is the model.

The sign is the opposite of the naive expectation and is documented in the code:
the placebo reads **higher**, because "at least 2 frames from the anchor" becomes
a random subset that usually *contains* the true runner-up, whereas on an ordered
curve the runner-up is a neighbour and is excluded. So the placebo is the
maximum-bimodality reference and the quantity to read is the ratio.

| stack | frames | real (mean sigma) | placebo | ratio |
| --- | --- | --- | --- | --- |
| 109MSDCF | 22 | 8.112 | 8.451 | **0.9598x** |
| 119MSDCF | 33 | 20.341 | 20.810 | **0.9775x** |
| coffee-bean | 105 | 102.577 | 119.226 | **0.8604x** |

All three read below 1, so the statistic **is** using the frame ordering and is
not reading noise. The ratio is not monotone in stack depth (22 frames reads
lower than 33), so depth is not the explanation; it is subject-dependent, and I
have not established what drives it.

### The null was broken, and the failure was silent

The first implementation used a rotation, `k -> (k + n/3) mod n`, and the placebo
came back at **exactly 1.0000x** — means matching to three decimals, p99 differing
by 0.005 in 80. Read at face value that says "the statistic carries no ordering
information", which is precisely the conclusion the null exists to rule out.

The cause was not the statistic. **A rotation is an isometry of the index line**:
`|perm[a] - perm[b]| = |a - b|` everywhere except across one wrap point, so a
screen defined by "at least PEAK_SEPARATION frames away" sees an almost identical
set. The null had silently become a copy of its own subject.

The fix is `shuffled_indices` — seeded Fisher-Yates over SplitMix64 — and, more
importantly, the test
`shuffle_destroys_adjacency_which_a_rotation_does_not`, which measures the mean
step between images of adjacent frames (1.0 for a rotation, ~n/3 for a shuffle)
and asserts the rotation control fails the property the shuffle passes. **A null
has to be tested for actually being a null.**

### The flag threshold was circular, and that was also silent

The C4 bimodality flag first took its cut from the *real* distribution's own p99.
It duly reported `82417 px` on both stacks — **exactly 1.0000%** of 8,241,504 —
which is the definition of the quantile being reported back as though it were a
measurement.

The cut is now the **placebo's** p99, which makes the flagged fraction a real
number: 1% is the no-effect reading, below 1% means fewer prominent far peaks
than chance. MEASURED: **0.9102%** on 109MSDCF, consistent in sign and roughly in
magnitude with the 0.9598x mean ratio.

### Positive control — and it did not come out positive

The positive control for the bimodality *flag* is `coffee-bean`, 105 frames,
the stack where M21 found the occlusion effect. It is also the positive control
for the memory ratchet, because it is the deepest stack in the corpus.

**The ratchet control passed, decisively.** MEASURED at 105 frames: `60 B/px =
494 MB per gather, CONSTANT in the frame count. A fine focus VOLUME for these
105 frames would be 420 B/px = 3461 MB`. Same 494 MB as at 22 frames, against a
volume that grew 4.8x. Plan: `4 chunks of <= 27 frames (4 allowed by the 6144 MB
budget, 32 by CPU)` — the budget, not the CPU, is the binding constraint, which
is the ratchet doing its job. In-flight frames 4, bound 4.

**The bimodality control did not move in the direction I wanted, and I am
reporting it rather than dropping it.** Fraction of pixels clearing the placebo's
p99, where 1% is the no-effect line:

| stack | frames | bimodal flag rate | reading |
| --- | --- | --- | --- |
| 109MSDCF | 22 | **0.9102%** | below chance |
| coffee-bean | 105 | **0.4741%** | further below chance |

So **no stack in the corpus shows a bimodality *enrichment* at this scale by this
statistic** — including the one M21 identified as the occlusion case. The
statistic is doing something real (the ratios above are all < 1, so it reads
ordering), but what it reads is that focus-ordered curves have *fewer* prominent
far peaks than a shuffle, which is the unimodal signal, not the occlusion one.

> **WITHDRAWN — see §4c.** The bolded conclusion above does not follow from this
> measurement. It is a **global** real-vs-permuted ratio; occlusion enrichment is
> a **conditional** quantity (depth step vs smooth depth). M21 measures 4.38x on
> `coffee-bean` conditioned properly, with its null at 1.01x. The global ratio is
> saturated by the fact that permutation manufactures multi-peakedness, so it
> could never have detected the effect. The retained per-pixel statistic is
> unaffected and still supports the conditional test; only this summary was wrong.

Two candidate explanations, neither tested:

1. `far_val - floor` is an **upper bound** on prominence — the true saddle is at
   least the global floor — so it is large for a merely *broad* unimodal curve.
   At 105 frames the curve is broad and the statistic is dominated by curve
   height, not by a second mode. Note `top1 - top4` is 27.74 fine sigma on
   coffee-bean against 1.91 on 109MSDCF: the whole response range is an order of
   magnitude bigger and the far-peak screen sits inside it.
2. M21 measured a multi-peak **rate** with its own prominence rule, not this
   quantity. The two may simply not be the same statistic, in which case this is
   not a contradiction of M21 and also not a confirmation.

Either way, the honest statement is: **(c) is retained and mergeable and its null
is sound, but it has not yet been shown to detect occlusion.** The next milestone
should not assume it does.

The merge's own positive control did move, on both axes: gate 0 -> 2.0 moves mean
n_eff 1.000 -> 2.891 and the flat-ROI ratio 1.074x -> 0.890x on 109MSDCF.

---

## 4. Predicted vs measured, and n_eff

From `out/m18/stats-109.txt`, gate ladder on 109MSDCF:

| gate | tol (DN-norm) | mean n_eff | n_eff = 1 % | predicted sigma gain |
| --- | --- | --- | --- | --- |
| 0.00 | 0.000000 | 1.000 | 100.00% | 1.0000x |
| 1.00 | 0.021516 | 1.884 | 41.66% | 0.7285x |
| 2.00 | 0.043032 | 2.891 | 15.45% | 0.5881x |

Measured flat-ROI ratios at those gates: 1.074x, 0.973x, 0.890x. **The model
over-predicts the gain**: `1/sqrt(n_eff)` says 0.5881x at gate 2 and the ROI
measures 0.890x. The gap is the same thing fact 19 is about — selection is
coupled to per-pixel noise, so averaging `n_eff` frames chosen *by their noise*
does not give `1/sqrt(n_eff)`. Ratio of measured to predicted at gate 2 is
0.890 / 0.588 = **1.51x**, which is remarkably close to fact 19's
structure-corrected argmax excess of ~1.48x. That may be a coincidence of two
small numbers and I have not tested it; it is flagged as a question below, not
claimed.

Soft and hard readings of the same acceptance set, at gate 0: mean posterior
perplexity **3.3206** (109MSDCF) and **2.4628** (119MSDCF) against mean n_eff
1.0000. The posterior thinks about three frames are plausible where the hard gate
admits one.

---

## 4b. The correction: mean|grad| is a ONE-SIDED test

The orchestrator sent a correction mid-milestone, and it changes an acceptance
invariant. Folded in here.

I had been told to guard fact 24 with "mean gradient on a detail ROI must not
collapse". That guard is right and stays. But mean|grad| has a blind spot in the
**other** direction: a merge can *raise* it by manufacturing detail that is not
in the scene. MEASURED by the orchestrator in a 1-D optics simulation of this
rig, calibrated to reproduce facts 12/27/28 to 3-4 digits, on a 25-frame stack
with oracle depth (latent mean|grad| = 0.0392):

| noise sigma | mean\|grad\| sel | mean\|grad\| wiener | grad CORR w/ truth, sel | grad CORR, wiener |
| --- | --- | --- | --- | --- |
| 0.002 | 0.0285 | 0.0384 | 0.8750 | 0.8504 |
| 0.010 | 0.0296 | 0.0367 | 0.8595 | 0.7538 |
| 0.030 | 0.0350 | 0.0327 | 0.7340 | 0.6903 |
| 0.050 | 0.0455 | 0.0293 | 0.5592 | 0.6629 |

At sigma 0.010 the Wiener merge carries **24% more gradient magnitude** than
selection (0.0367 vs 0.0296; 94% of latent vs 76%) while being **12% less
correlated with the truth** (0.7538 vs 0.8595). The surplus is ringing and
amplified noise sitting where no edge is. At sigma 0.050 argmax selection reads
0.0455, **above the ground truth's 0.0392** — noise alone inflates the metric
past the true value. A mean-gradient test scores both as wins.

That simulation independently reproduces fact 24 from a model not tuned to it:
plain mean loses 49-51% of gradient there, 58%/53% measured here.

### What changed in the code

1. The collapse guard is unchanged and still required.
2. The invariant is now **explicitly one-sided**, in the banner and in a comment
   on `detail_verdict`. The verdict column emits `COLLAPSE` / `ok` /
   `INVESTIG.` and **never `PASS` for a rise**. `DETAIL_COLLAPSE_FLOOR = 0.90`
   (fact 24's collapse is 0.42x/0.47x, the simulation's plain mean 0.49-0.51x,
   and tonight's gate-to-gate drift is 0.2%/0.6%, so 0.90 sits clear of both).
   `DETAIL_RISE_FLAG = 1.50` (the reference is one bracket frame, so retention
   above 1 is expected; measured 1.25x/1.02x). Both relationships are pinned by
   `const _: () = assert!(...)`, so a build that violates them does not link.
3. A **two-sided companion** is now reported: winner-index speckle, via the same
   `speckle_fraction` and the same tolerance `strehl stack` uses for argmax. The
   tolerance moved into `strehl-core` as `DEFAULT_SPECKLE_TOLERANCE` so the two
   numbers are comparable by construction rather than by coincidence.

I used **index speckle, not gradient correlation**. Gradient correlation is
strictly the better metric and the orchestrator said so, but it needs a
reference, and this repo has no ground-truth plant harness. Building one was out
of scope for tonight. Index speckle already existed, was already tested, and
shares a cause with manufactured detail. Stated plainly so nobody mistakes it
for the stronger check.

### MEASURED with the companion, both stacks

| stack | flat ratio @ gate 2 | detail retention @ gate 2 | verdict | index speckle | argmax speckle |
| --- | --- | --- | --- | --- | --- |
| 109MSDCF (22f) | **0.890x** | 1.251x | ok | **0.022%** | 1.010% |
| 119MSDCF (33f) | **0.960x** | 1.021x | ok | **0.024%** | 1.183% |

The regularised winner field is ~46x smoother than argmax's on 109 and ~49x on
119. The merge is not manufacturing detail; it is removing the selector's
speckle, which is what a regularised reference is for.

Note the retention figures for 109 moved from the 1.257x/1.254x recorded in §2
to 1.230x/1.251x. That is not my change. Another agent landed a
`selection_inflation` factor into `merge::predicted_sigma` while this milestone
was in flight, which raises the model-noise column at tight gates and therefore
lowers `corrected = sqrt(raw^2 - model^2)` there. The **flat-ROI ratios are
untouched** by it, because they do not consult the model. Flagged rather than
quietly restated.

### Negative control

Regressed `detail_verdict` to a two-sided `retention >= floor => "ok"` and
`a_gradient_increase_is_never_scored_as_a_pass` went **RED** at
`merge_cmd.rs:1949`. Restored from a copy, mtime touched forward (Windows
`Copy-Item` preserves the *source* mtime, so a restore can move mtime backwards
and cargo will skip the rebuild), suite green again.

## 4c. The seam scale, and a correction to my own bimodality claim

M21 (`1a70a80`) landed mid-milestone with two findings that bind the fold seam.
Both are answered here, and the second forces me to withdraw a claim I made in
§3.

### The scale decision: form (a)

**Statistics are carried at radius 2, not at the focus scale.** `FINE_WINDOW_RADIUS
= 2` (`focus.rs:105`) — a 5x5 box on the gradient-magnitude plane. This is
the same R=2 at which M21 measures 4.38x enrichment, arrived at independently
before M21 reported, for the same reason: a 27x27 window averages both layers of
a two-layer occluding edge together and the structure does not survive it.

`compute_with_fine` (`focus.rs:238-258`) builds both fields from **one** shared
gradient plane, with the fine field a second `box_mean` at `fine_radius`
(`focus.rs:255`). The box filter is the O(1) separable running sum, so the fine
field's cost is independent of its radius, and the gradient — the expensive part
— is computed once and used twice.

**Cost, MEASURED on `coffee-bean` (105 frames, 4 workers):**

- **Memory: one extra f32 plane per worker, 3516 x 2344 x 4 B = 32.97 MB.** It
  is a `Scratch` plane, so it is O(workers) and constant in the frame count. It
  does not appear in the 60 B/px gather figure because it is scratch, not state.
- **Time: bounded above by the 81.8 ms/frame** the whole pass-one focus stage
  costs (gradient + R=13 box + R=2 box + two normalisations). The fine field is
  one of those four sub-steps and the two box passes are the same O(1) cost, so
  the increment is roughly a quarter of that, but I did not isolate it with an
  alternating sweep and per-setting minima, so **I quote it as a bound, not a
  value** (project rule 16).

The alternative — form (b), carrying statistics at R=13 and paying a third pass
later — would have cost the measured warm decode of **74.4 ms/frame** plus the
focus stage again. On the 105-frame stack that is ~7.8 s of decode alone. Not
catastrophic, but entirely avoidable, and it is the rewrite the external review
warned about. It was not taken.

### The noise-normalisation requirement: already satisfied, by construction

M21's second finding is that a curve-shape threshold is worthless without the
noise model, because noise alone flags 60-98% of pixels as multi-peaked. The
retained state satisfies this and did so before M21 reported:

- **The retained values are already in units of the calibrated sigma.** Both
  fields are divided per pixel by `noise.green_luma_sigma(luma)` in
  `normalise_by_luma_sigma` (`focus.rs:257`, `focus.rs:272-277`). So
  `top_val`, `triple`, `floor` and `anchor_focus` are noise-normalised at the
  point of capture. There is no need to retain the signal level `S` in order to
  reconstruct `sigma(S)` later — the division has already happened, which is
  strictly better than retaining `S`, because it happens at the pixel's *own*
  luma rather than at the merged output's.
- **The thresholdable form is the only one exposed.** `bimodality_sigma` divides
  by `sqrt(2) * FINE_FOCUS_NOISE_SD`, the SD of a *difference* of two fine
  responses, and its doc comment already states that this is the only form that
  may be thresholded.
- `FINE_FOCUS_NOISE_SD = 0.090400` is re-measured from seeded noise by a test,
  and the same test re-derives the shipped `FOCUS_NOISE_SD = 0.015214` exactly,
  which is what validates the instrument.

### CORRECTION: my §3 bimodality claim was the wrong estimand

In §3 I reported placebo ratios of 0.9598x / 0.9775x / 0.8604x and concluded
that **"no stack shows bimodality enrichment, including M21's occlusion case."**

**That conclusion is withdrawn. It does not follow from what I measured.**

I measured a **global** ratio: the whole plane's bimodality against a
frame-permutation null. M21 measures a **conditional** one: the multi-peak rate
at depth steps against the rate on smooth depth, binned on an *independent* R=13
depth-step map. These are different estimands and mine cannot see the effect.

The reason is visible in my own transcript, which already noted the placebo
"reads HIGH by construction": permuting frames destroys the smooth unimodal
through-focus curve and manufactures multi-peakedness, so a global real-vs-null
ratio is dominated by "real curves are smooth" and saturates. M21's own numbers
show the same thing far more starkly — on `coffee-bean`, 4.8% real against an
86.2% permuted rate, a ratio of 0.056. Both of us measure a global ratio well
below 1; that is the null misbehaving as a global reference, not evidence about
occlusion.

Conditioned properly, M21 finds **4.38x** on `coffee-bean`, with the permutation
null at 1.01x and ~2.7x surviving stratification within intensity-gradient
quintiles. My global number is not in conflict with it and never tested it.

**This is a reporting defect, not a design defect**, and the distinction matters
for the seam: the retained `bimodality_sigma` is *per-pixel* and
*noise-normalised*, so a consumer can bin it against any depth-step map it
likes. Nothing about the fold forecloses M21's conditional test. What was wrong
was the summary statistic I chose to print, not the state I chose to keep. The
right global summary to print is a conditional enrichment, and I have not built
one — see §6.

## 4d. Photometric drift: the omission, stated and priced

M24 (`ce5ad73`) measured that this corpus really does drift photometrically. This
merge has **no per-frame gain term**, so rather than leave that implicit, this
section states where it would go and measures how big the assumption is.

### The scaling law, MEASURED in-crate

The focus response is `box_mean(|grad L|) / sigma(L)`. Scaling a frame's signal
by `g` scales the numerator by exactly `g`; in the shot-noise-limited regime
`sigma ~ sqrt(S)` scales the denominator by `sqrt(g)`. So the normalised
response moves by **`sqrt(g)`**, and a fractional level drift `d` moves it by
`d/2` of itself.

That is not asserted, it is tested:
`a_per_frame_gain_scales_the_normalised_response_by_its_square_root`
(`focus.rs`) applies `g = 1.44` to a synthetic plane deep in the shot-limited
regime and requires the normalised response to move by `1.2000`. It carries a
**positive control that discriminates the two hypotheses**: the *unnormalised*
response in the same test must move by the full `1.44`, so the test cannot pass
by accepting both. **Negative control:** replacing the sigma divisor with a
constant makes the normalised response move by `1.4400` and the test goes RED —
so this is evidence, not arithmetic (rule 20).

Stated failure direction (rule 18): `sqrt(g)` is the **shot-limited** answer and
therefore a *lower* bound on sensitivity. Where read noise dominates, sigma is
flat in signal and the response moves by the full `g` — **twice** as sensitive.
Deep shadow is the worse case, not the better one.

### The response scale, MEASURED on real RAW

| stack | median | p10 | p90 | gate units per **1%** drift (median / p90) |
| --- | ---: | ---: | ---: | ---: |
| 109MSDCF | 0.8119 | 0.7431 | 3.8662 | 0.189 / 0.898 |
| 119MSDCF | 1.5168 | 1.3311 | 10.1007 | 0.352 / 2.347 |

One gate unit is `sqrt(2) * FOCUS_NOISE_SD = 0.021516`, the SD of a *difference*
of two regularised responses — the only scale on which "does this matter" has an
answer.

### The consequence, DERIVED from those two MEASURED inputs

Combining M24's measured drift with each stack's own measured response scale:

| stack | drift (M24) | gate units, median px | gate units, p90 px |
| --- | ---: | ---: | ---: |
| `109MSDCF` | 0.91% | 0.17 | 0.82 |
| `119MSDCF` | 2.88% | **1.02** | **6.76** |
| `coffee-bean` | 11.70% | **2.21** | 10.5 |
| `coffee-bubbles` | 8.93% | **1.68** | 8.0 |

(109 and 119 rows use each stack's own scale; the coffee rows use 109's scale as
the conservative one, since I did not merge those stacks tonight.)

**The default gate ladder tops out at `t = 4`, and `t = 2` is the reference.** On
`119MSDCF` — the *second quietest* stack — photometric drift alone displaces the
response by a **full gate unit** at the median pixel and **~6.8** at textured
pixels, where selection actually happens. On `coffee-bean` it is 2.2 and ~10.5.
Drift of that size is not distinguishable from focus by this gate.

This raises R9 from ARGUED to DERIVED-with-measured-inputs. It is **not**
MEASURED: I did not fit a gain, and I did not measure any change in merge
output. The honest claim is that the assumption is large enough to matter, not
that a specific image is wrong.

**Why 109 never showed this:** at 0.91% it is 0.17 gate units — genuinely
negligible. 109 is the quietest stack in the corpus and carries most of this
project's numbers, including this milestone's headline. A clean 109 result is
not evidence that photometry is handled, and the report now says so in the
binary.

### The ordering decision, and why

**Gate in native raw DN. Do not pre-scale frames.** `Estimator`'s module note
already fixes this: no white balance, no colour transform and no black
subtraction happens before the gate, because the noise model is calibrated in
raw DN and any of those would put the gate and the model in different spaces. A
per-frame gain is the same class of operation and must obey the same rule.

The reason is the one M24 flags: `sigma^2(S)` is signal-dependent, so scaling
frame `k` by `g_k` scales its noise too. Applying `g_k` to the pixels while
gating against an unscaled sigma miscalibrates the gate by exactly `g_k` — it
would *manufacture* the error it was added to remove. So when the gain term is
built, the correct shape is to **apply `g_k` to the noise model as well as to
the signal**, i.e. gate on `(L_k / g_k)` against `sigma(L_k) / g_k`, which is
identical to gating in native units with `sigma` evaluated at the frame's own
observed level. Native-units gating is therefore not merely convenient, it is
the form that is automatically correct under an unknown gain, and it is what
ships.

### Where the gain term would go

Three lines in the existing two-pass structure, none of which require a new pass:

1. **Fit** in pass one, alongside the focus field, which already touches every
   pixel of every frame. A robust per-frame level ratio against a running
   reference — the same shape as the robustness mask of brief item 4 — costs one
   scalar per frame and no extra decode. **Fit it, do not read it:** M24 measured
   two stacks drifting 6.84% and 8.93% with *constant* EXIF, and `coffee-bean`
   moving only 16% of what its EXIF change predicts (1.0443 against 1.2800).
2. **Carry** it as a `Vec<f32>` of length `frames` on the `Plan` — O(frames)
   scalars, not O(frames) planes, so the memory ratchet is untouched.
3. **Apply** it inside `Estimator::fold`, to the signal and to the sigma
   together, per the ordering above.

Not built tonight. Stated so it is a decision, not an oversight.

## 4e. Colour ordering and the clipped-sample mask (M26)

Two asks, one confirmation and one build.

### 1. Gate in native raw DN before white balance: CONFIRMED, and it was already so

The design already gates in native per-channel raw DN, and `merge.rs:298-300`
already says so as a standing constraint on the `Estimator`. Recording it here so
it is on the record as a **decision** rather than an accident.

The argument the orchestrator gives is the one that makes it load-bearing, and it
is worth restating in the terms of this crate. The calibrated model
`sigma^2(S) = g*S + (RN_e*g)^2` is valid in native DN only. Scale a channel by an
as-shot multiplier `m` and the *true* noise scales as `m^2 * (g*S + (RN*g)^2)`,
while applying the model to the scaled value yields `g*(m*S) + (RN*g)^2`. The
ratio of believed to actual tends to `m` in the read-limited limit and `sqrt(m)`
in the shot-limited limit. With `R` spanning 2.13-2.86 across this corpus, a gate
that white-balanced first would believe red up to **2.86x quieter than it is**,
most strongly in the shadows — which is exactly where M2 measured the argmax
defect. The failure is silent: nothing crashes, the gate simply selects too
eagerly and the output drifts back toward the selector this project exists to
replace.

Concretely, in this crate: `Ctx::field_for` takes the CFA plane straight from
`strehl-raw`, forms the green luma with no multiplier, and hands it to the focus
operator; `Estimator::fold` consults `NoiseModel` at that same native level. No
WB, no colour matrix, and no black subtraction happens before the gate. VERIFIED
by reading the path; the module note at `merge.rs:298-300` pins the intent.

This also means the crate never needs to read `as_shot_whitebalance`, and so
cannot hard-code it. When WB is eventually applied it belongs strictly after the
merge, read per stack.

### 2. The clipped-sample mask: BUILT

`crates/strehl-core/src/clip.rs` (new module) owns `CONTAINER_MAX_DN = 16383` and
`ClipCensus`. `plane.rs` gains `green_luma_with_clip`, which is
`green_luma` plus **one comparison per sample** — the cost the orchestrator
priced it at.

Three design choices worth stating:

**Report, do not repair.** The mask flags; it does not substitute a value. A
substituted value is itself an edge, and it would land in the gradient operator
one stage later — trading a known-bad sample for a manufactured one. Under rule
18 that is the worst possible trade, because the manufactured edge *raises*
`mean|grad|` and reads as an improvement. `green_luma_with_clip` is therefore
proven **bit-identical** in its luma output to `green_luma`, by test
(`the_clip_mask_reports_clipping_without_altering_the_luma`).

**Either green flags the quad.** The plane is a green-average of the 2x2 CFA
quad. If either green sample is pinned, the average is not a measurement of the
scene and the quad is flagged. Requiring both would let a half-pinned average
through as if it were real.

**2 bytes per pixel, constant in frames.** `ClipCensus` carries a `u16` count per
pixel and the number of frames folded. That is 16.5 MB on this plane at every
depth — O(workers), never O(frames), so the ratchet is untouched. It is exactly
mergeable: `absorb` is tested against folding the same frames into one census.

The two white levels are kept distinct and the module doc says why: **15360**
bounds the noise model's calibrated range, **16383** is what "this sample is
pinned" means. `noise.rs` is correct as it stands and was not touched.

### The census, MEASURED on three stacks

Reported unconditionally, not behind `--stats` and not behind an ROI flag — it is
a correctness statement about the stack, not a diagnostic about a rectangle.

| stack | n | ever clipped | always clipped | index speckle |
| --- | ---: | ---: | ---: | ---: |
| `109MSDCF` | 22 | 0.0000% (0) | 0.0000% (0) | 0.022% |
| `119MSDCF` | 33 | 0.0000% (0) | 0.0000% (0) | 0.024% |
| `coffee-bubbles` | 19 | 0.5052% (41,632) | **0.0088% (724)** | — |

This is a null control and a positive control in one measurement. The two stacks
M26 reports as unsaturated read **exactly zero** — not "small", zero — and the
stack M26 reports as pinned at the container maximum fires. A mask that fired on
109 or 119 would be wrong, and a mask that stayed silent on `coffee-bubbles`
would be inert.

**I do not claim to reproduce M26's 616.** I measure **724** always-clipped
pixels, on a different estimand: my census lives on the green-luma plane with the
either-green rule above, and M26 counted on its own plane definition. Same
mechanism, same order, different denominator — stating it as agreement would be a
reporting defect. What is MEASURED here is 724 by this rule.

Both acceptance invariants are unchanged by the mask on 109 and 119 (flat 0.890x
and 0.960x, retention 1.251x and 1.021x, speckle 0.022% and 0.024%) — which is
the expected result, since the mask alters no luma and neither stack has a
clipped sample to flag.

### The caveat I am obliged to carry

M26's closing point applies directly to this milestone's headline: `109` and
`119` are the two stacks with **no saturation at all**, and M24 found `109` is
also the quietest photometrically at 0.91%. Every acceptance number in §2 was
measured on those two. **A clean result on 109/119 is systematically weaker
evidence than it looks**, and the corpus's hard cases — `coffee-bean` at 1.26%
saturated and 11.70% photometric drift, `coffee-bubbles` at 8.93% — are not
exercised by the acceptance tests. That is a stated limitation, not a defect I
have fixed.

### What the mask does NOT yet do

The census is computed and reported; it is **not yet consumed by the gate**. The
consumer is one line in `Estimator::fold` — treat a flagged sample as carrying no
focus information, i.e. force it to the averaging branch rather than letting its
maximal apparent focus contrast win the selection. I did not wire that tonight
because it changes merge output and I would rather ship the measurement, the
mask and the proof it fires than an unmeasured behaviour change at the end of a
run. The hole M26 identifies is real but its measured incidence on the acceptance
stacks is exactly zero, so wiring it cannot be validated there.

## 5. Tests


**107 -> 146, delta +39.** No test was removed, weakened, or marked `#[ignore]`.

- `strehl-cli` 34 -> 37 (+3)
- `strehl-core` 65 -> 101 (+36)
- `strehl-raw` 8 -> 8 (unchanged)

The suite currently *runs* 147. The extra one is
`the_selection_inflation_constant_is_the_measured_one` in `merge.rs`, which is
another agent's work in the shared tree, not mine. My commits account for +39
and no more.

The last seven are §4e's: six in `clip.rs` and one in `plane.rs`. They pin the
two white levels apart
(`the_container_maximum_is_not_the_usable_white_level`), the always-clipped
definition, the empty-census abstention, `absorb` against folding the same frames
into one census, the 2 B/px O(1)-in-frames footprint at 1/22/33/105/400 frames,
a dimension mismatch returning an error rather than panicking, and — the
load-bearing one — that the clip mask leaves the luma **byte-identical**
(`the_clip_mask_reports_clipping_without_altering_the_luma`).

The 29th core test is
`a_per_frame_gain_scales_the_normalised_response_by_its_square_root` (§4d): the
`sqrt(g)` law the photometric sensitivity report rests on, with a positive
control discriminating `sqrt(g)` from `g` and a negative control that turns it
red.

Two of the three CLI tests are the correction's:
`a_gradient_increase_is_never_scored_as_a_pass` (every retention at and above
the rise flag returns `INVESTIG.`, never `ok`, and the collapse floor still
returns `COLLAPSE`) and
`the_speckle_companion_uses_the_same_tolerance_as_the_argmax_baseline` (pins the
merge's tolerance to the identical core constant `strehl stack` reads, so the
two percentages cannot silently diverge).

The third CLI test is
`the_statistics_are_priced_into_the_plan_and_do_not_grow_with_the_stack`: the
memory ratchet, extended honestly rather than weakened. It asserts the gather is
priced into pass two, that it cannot license more workers, that the placebo costs
extra, that the footprint is **identical at 22, 33, 105 and 400 frames**, and
that it is cheaper than a 22-frame fine focus volume.

The 28 core tests cover the fold's commutativity and associativity under reduce,
`absorb` idempotence, the parabola vertex against a closed form, the log-fit
deficit, the top-k insert's idempotence on repeated indices, the bracket-boundary
condition, the untruncated posterior sums, the confidence vector's
non-collapsibility, the placebo's preservation properties and its sign, and the
two tests written in response to defects found during the run
(`shuffle_destroys_adjacency_which_a_rotation_does_not`,
`the_scale_disagreement_screen_ignores_off_by_one_and_catches_off_by_two`).

`FINE_FOCUS_NOISE_SD` is guarded by a test that re-measures it from seeded noise
and also re-measures `FOCUS_NOISE_SD`, so the constant cannot drift from the
operator without the suite saying so.

### Negative controls on the two load-bearing new tests

Rule: a test that has never been seen to fail is not evidence. Both were
regressed by copy-to-backup, run red, and restored from the copy — never
`git checkout --`, because three other agents had uncommitted work in this tree.

| test | regression applied | result |
| --- | --- | --- |
| `shuffle_destroys_adjacency_which_a_rotation_does_not` | `shuffled_indices` replaced by `k -> (k + n/3) mod n` | **RED**: `n=22: shuffle left adjacency largely intact, mean step 1.952` |
| `the_statistics_are_priced_into_the_plan_and_do_not_grow_with_the_stack` | `stats_bytes` made `4 * frames * px` | **RED**: `22 frames changed the statistics footprint; it is supposed to be O(1) in the stack depth` |

Both restored, full suite green at 136.

**A gotcha worth recording**: on Windows, `Copy-Item` preserves the *source*
file's `LastWriteTime`, so restoring from a backup moves the mtime **backwards**
and cargo's fingerprint does not rebuild — the restored tree kept reporting the
regression as still failing. `(Get-Item path).LastWriteTime = Get-Date` after a
restore, or the negative control will look like it did not restore.

---

## 6. What I did NOT build

**Brief item 4, the robustness / outlier mask, is NOT BUILT.** No per-tile
per-frame noise-normalised disagreement, no Wronski-shaped robustness model, no
defence against the moving `foam` stack or the twitching antenna. The brief says
a solid 1-3 beats a shaky 1-4 and I took it at its word: the seam is the thing
the next milestone is blocked on, and two of the three defects found tonight were
in the *nulls* rather than the statistics, which is where the remaining time
went.

The statistics built here are the input that mask would need — per-pixel
bimodality and a top-k list are exactly the disagreement evidence — so this is a
foundation for it, not a detour around it.

**Also not built, deliberately:** the per-pixel posterior itself. The brief says
"do not build that posterior now — but do not foreclose it either", and §1 above
is the argument that it is not foreclosed.

**Not built: the per-frame photometric gain term.** Stated and priced in §4d
rather than left implicit — the `sqrt(g)` law is tested, the response scale is
measured on both stacks, and the fit/carry/apply location is named. On
`119MSDCF` the unmodelled drift is worth a full gate unit at the median pixel.
This is the largest *stated* gap in the merge tonight.

**Not built, and newly identified in §4c: a conditional bimodality summary.** The
per-pixel `bimodality_sigma` supports M21's depth-step-vs-smooth-depth
enrichment, but `--stats` prints only a global real-vs-placebo ratio, which §4c
shows is the wrong estimand and cannot detect occlusion. Printing the right one
needs a depth-step map, which M21 owns and which lives under `experiments/` —
a directory I am forbidden to write to tonight. I did not reach into it. The
honest state is: the statistic is right, the retained state is right, the
printed summary is wrong, and fixing the print is a small job for whoever owns
the occlusion milestone next.

**Not built: the clip mask's consumption by the gate.** §4e builds, tests and
measures the mask; it does not yet let it change a merge decision. The consumer
is one line in `Estimator::fold`. Not wired tonight because it changes merge
output and its measured incidence on both acceptance stacks is **exactly zero**,
so the change could not be validated where the acceptance tests run.

**Not changed:** the focus operator. `WINDOW_RADIUS = 13`, `SUPPORT_RADIUS = 14`,
Sobel magnitude not squared, 27x27 running-sum box. `compute()` is byte-identical;
the fine scale is a second `box_mean` over the *same* gradient pass, and the
normalisation is factored into one function that both paths call so they cannot
drift.
