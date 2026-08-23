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

## 5. Tests

**107 -> 136, delta +29.** No test was removed, weakened, or marked `#[ignore]`.

- `strehl-cli` 34 -> 35 (+1)
- `strehl-core` 65 -> 93 (+28)
- `strehl-raw` 8 -> 8 (unchanged)

The one CLI test is
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

**Not changed:** the focus operator. `WINDOW_RADIUS = 13`, `SUPPORT_RADIUS = 14`,
Sobel magnitude not squared, 27x27 running-sum box. `compute()` is byte-identical;
the fine scale is a second `box_mean` over the *same* gradient pass, and the
normalisation is factored into one function that both paths call so they cannot
drift.
