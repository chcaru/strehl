# M94 — pre-registration: how decisively does the focus election win?

**Written and committed before any M94 measurement ran.** Everything measured
under this milestone is scored against the bars below. Where a bar is added or
changed later it will say so, in place, with the reason and the commit.

---

## 0. Rule 40 — what already exists, found before designing anything

Grepped `docs/research/` (116+ files) for `runner-up`, `second-best`, `winner
margin`, `top-2`, `index map`, `speckle`, `coherence`. Five prior results bear on
this question and **three of them partly answer it**:

| where | what it already says | what it leaves open |
|---|---|---|
| `B-algorithms-sota.md` §2.3 | **External prior art.** Surh et al. CVPR 2017 define **Winner Margin** `WM = (c1 - c2m) / sum_l c(l)` — best minus **second-best-*mode***, normalised by the response sum — and measure it against added noise. Audited at primary source by M83 (`M83-survey-audit.md` P4). | Synthetic light fields, 30 quantised depth labels, not RAW, not this operator, not this corpus. The *metric shape* transfers; the numbers do not. |
| `M2-baseline-skeleton.md` §3.1 | **Index-map speckle already measured with its nulls**: real 34.381%, i.i.d.-from-observed-histogram null 53.496%, uniform null 66.174%, 17x17-regularised 0.868%. Stratified by 64x64 contrast decile: 38.6% flattest, 21.7% busiest. States in as many words that the map is *"full-range salt-and-pepper everywhere the surface is smooth"*. | **Retired operator.** That is the ring difference, unregularised. `merge.rs`'s own doc comment (the `Gate::admits` block, item 1) states: *"No corpus row publishes a regularised Tenengrad speckle, so it cannot simply be swapped for a matched one."* |
| `M7-gpu-focus-measured.md` §3.1/§3.4 | **The top-2 margin already exists as a concept here** and is used as a tolerance argument: *"a winner flip where the top two candidates are separated by 1e-8 is a tie, not an error."* Measured at the one GPU/CPU-disagreeing pixel: margin 0.000, 6.62e-8 of the median focus. | Conditioned on GPU/CPU disagreement — **one pixel**. No distribution over all pixels, no frame-index structure, no noise denomination. |
| `M65-election-gate-measured.md` | **56.70% of pixels change winner** between raw and regularised election while the acceptance set moves 0.44%. Index-map disagreement rises monotonically with ISO (24.16% -> 36.58%). | Measures churn *between two arms*; says nothing about how decisively either arm wins. |
| `M93-election-gate.md` §7.2, `P6`, `D-b` | **A milestone tonight tried a spatial-coherence bar and it failed in the wrong direction** (+201% to +429% where <= -20% was registered). Diagnosis: speckle-as-a-*differential* penalises any substitution regardless of correctness — *"the metric measures churn, not correctness."* `D-b`: a coherence bar must distinguish a correct substitution from an incorrect one. | M93's failure is specific to using speckle **as a bar on an intervention**. It says nothing about the **absolute** coherence of the shipped election measured against endpoints. This milestone must not repeat the error, and §4 below says how it avoids it. |

Also relevant and read: fact 1196 (gate exonerated), 1177 (232.7 px uncorrected
drift), 1186-1190 (motion wins the election), 1199/1200 (the pedestal defect and
that it is *not* M60's mechanism), 1204/1205 (fact 608's ordering; the bit-exact
surrogate). M85's `n_eff` ladder (1.000 -> 60.860 over gate 0..4) already measures
the **size** of the competitive set.

**The gap this milestone fills, stated precisely.** The corpus knows *how many*
frames are competitive with the winner (`n_eff`). It does not know **where they
are in frame index**. `n_eff = 61` is benign if those are 61 contiguous
neighbours — a wide depth-of-field plateau, where any of them is nearly the same
picture — and pathological if they are scattered across the bracket, because then
the elected frame is one draw from a set of scene points that fact 1177 says are
hundreds of pixels apart. **Nothing in the corpus separates those two.**

---

## 1. The question, in the form I will answer it

> Per pixel, how far in **frame index** can the election move before the focus
> response drops below the winner's by more than the response noise?

Three quantities, all per pixel, all computed against the shipped operator
(`FocusField` + `regularise`) on the shipped election (`FocusStats::beats`):

1. **Confusion radius** `rho(t) = max{ |k - k_win| : R_k >= R_win - t }` — the
   furthest frame that is still within `t` of the winner.
2. **Confusion gap** `gap(t) = (hi(t) - lo(t) + 1) - n(t)` — how many frames
   inside the competitive index range are *excluded* from it. `gap > 0` means the
   competitive set is **disconnected**: a distant frame beats the winner's own
   neighbours. This is the direct signature of an arbitrary election.
3. **Distance-d margin** `m_d = R_win - max_{|k - k_win| >= d} R_k`, for
   `d in {1, 2, 4, 8, 16, 32}`. `m_1` is the naive top-2 margin.

`n(t)`, `lo(t)`, `hi(t)` are over the same admission rule the merge uses,
`Gate::admits`, so `n(t)` **is** `Estimator::n_eff` at threshold `t/(sqrt(2)*
FOCUS_NOISE_SD)` and is checkable against it exactly (§3, F2).

### 1.1 Units — and why the headline will not rest on `FOCUS_NOISE_SD`

`FOCUS_NOISE_SD = 0.015214` is a shipped constant that **two milestones failed to
calibrate** (M69, M81), and M69 established that the quantity is **not measurable
from a focus sweep at all** (`docs/captures-needed.md` §12). I therefore report
three denominators and the headline is the one that needs no constant:

- **(a) Unit-free, the headline.** `q_d = m_d / (R_win - R_min)`, the margin as a
  fraction of that pixel's **own** through-focus dynamic range. Scale-free in the
  operator's units, needs no noise model, and is the closest thing to Surh's WM
  that this pipeline can produce. A pixel with `q_32 = 0.001` is decided by 0.1%
  of its own focus contrast against a rival 32 frames away.
- **(b) A sweep, never a single number.** `rho(t)` reported over a ladder
  `t = c * sqrt(2) * FOCUS_NOISE_SD` for `c in {0.5, 1, 2, 4, 8}`, which brackets
  the shipped gate (4.0) and M69's measured 0.9285x-1.1009x value range with room
  to spare. If the conclusion is the same at `c = 0.5` and at `c = 8`, the
  constant is not load-bearing and I will say so; if it flips inside the ladder I
  will report the crossing point and claim nothing beyond it.
- **(c) A directly measured scale, for context only.** `sigma_R_hat`, the
  frame-axis fourth-difference SD of `R_k` using M89's `[1,-4,6,-4,1]/6` kernel,
  whose variance under white noise is `sigma^2 * 70/36` **by algebra, with no
  fitted constant**. Registered caveat, before the run: this annihilates any
  cubic in `k`, so it measures response noise **plus** motion and under-sampling,
  which makes it an **upper bound** on the noise and therefore a **lower bound**
  on the margin in noise units. That direction **flatters this milestone's
  hypothesis**, so (c) is reported as context and **must not carry a headline**.

---

## 2. Pre-registered bars — what "the election is fine" looks like

These are written before any result exists. **If the numbers land on the
"decisive" side, the answer to the milestone is "the election is fine, look
elsewhere", and that is a successful outcome.**

| bar | "the election is DECISIVE" | "the election is NEARLY ARBITRARY" |
|---|---|---|
| **B1 — headline.** Median `rho(t)` at the shipped gate `c = 4`, as a fraction of the stack's frame count `N` | `<= 0.05 N` — the competitive set is a local plateau | `>= 0.20 N` — a fifth of the bracket is competitive |
| **B2 — disconnection.** Fraction of pixels with `gap(t) > 0` at `c = 4` | `<= 5%` | `>= 25%` |
| **B3 — unit-free margin.** Median `q_8` (winner vs. best rival >= 8 frames away, as a fraction of own dynamic range) | `>= 0.10` | `<= 0.02` |
| **B4 — the smooth/sharp split.** Ratio of median `q_8` in the top detail decile to the bottom, binned on an **independent** axis (§4.3) | the *ratio* is what is reported; **no bar**, because I have no prior for its size. Registered prediction: `>= 3x`, smooth regions worse. |
| **B5 — coherence.** Elected-index speckle of the **real** election as a fraction of the i.i.d.-from-observed-histogram null, `S_real / S_iid` | `<= 0.20` | `>= 0.80` |

Anything between the two columns is **INTERMEDIATE** and will be reported as
such, with no verdict claimed.

**Registered prediction (rule 30 — I expect to be able to falsify this).** I
predict B1, B2, B3 and B5 all land in the "nearly arbitrary" column on the
owner's deep stacks and in the "decisive" column on the synthetic ramp plant. If
the real stacks come out decisive, the softness is not here and I will say so in
the verdict line, unhedged.

**What this milestone cannot conclude either way.** Even a fully arbitrary
election does not by itself prove it *causes* softness; fact 1196 shows the gate
does not, and the standing alternative (fact 1177's 232.7 px uncorrected drift)
would produce an arbitrary-looking election *as a symptom*. I will not claim
causation. See §6.

---

## 3. Faithfulness controls — my surrogate must be the shipped election

Per fact 1205's precedent and M93's `P9`/`P10`. `merge.rs` is contended and I do
not touch it; the whole instrument is written against the public API.

- **F1.** My `k_win` must equal `FocusStats::best_index()` at **exactly
  100.000000%** of plane pixels, on every stack measured. Not ">99.99%" — M93's
  `P10` recorded a planted tie-break inversion that moved 2.5 ppm and would have
  passed any looser phrasing.
- **F2.** My `n(t)` must equal `Estimator::n_eff()` at **exactly 100.000000%** of
  pixels at the shipped gate, on every stack measured.
- **F3 (power for F1/F2, mandatory).** Plant a tie-break inversion — `index <
  cur_index` becomes `index > cur_index` in my own comparator — and show F1
  **fails**. A faithfulness bar that has never been seen to fail is arithmetic,
  not evidence (rule 20). The plant is restored from a SHA256-verified copy in
  `$env:TEMP`, never `git checkout --`, and the file's `LastWriteTime` is touched
  after restore (M93 `P12`, AGENTS rule 33).

---

## 4. Controls on the answer

### 4.1 Positive control — discipline 594, mandatory

**A null is a claim only if the instrument could have said otherwise, and I must
show it saying otherwise.** Plant a stack whose election is *known* to be
well-determined: a synthetic bracket built by blurring one real, sharp corpus
frame with a Gaussian whose radius is `|k - k*(x)| * delta`, where `k*(x)` is a
smooth left-to-right ramp across the plane, plus sensor noise drawn from the real
`NoiseModel`. Truth is known by construction.

**Registered:** on this plant the instrument must report `rho` small, `q_8`
large, `gap` near zero and `S_real/S_iid` small. If it does not, **the instrument
is broken and no real-stack number in this milestone means anything.**

Rule 13 check — can the stimulus express the failure? Yes: `delta` sets the peak
width, so sweeping `delta` down must walk the plant continuously from decisive to
arbitrary. I will run at least two `delta` values and show the metric moving.

### 4.2 Nulls — the scale M93 lacked

M93's `D-b` says a coherence bar must distinguish correct from incorrect
substitution. **I avoid that failure by not using coherence as a bar on an
intervention at all.** I use it descriptively, against two measured endpoints on
the same stack:

- **N1 — i.i.d. null.** Elected indices redrawn i.i.d. from that stack's own
  observed winner histogram. Preserves the marginal, destroys all spatial
  correspondence. (M2's null, so the number is comparable to 53.496%.)
- **N2 — uniform null.** Indices uniform on `[0, N)`. Maximum disorder.
- **N3 — placebo on the same scale (discipline 596).** Permute the **frame axis**
  before folding. The per-pixel *multiset* of responses is unchanged, so:
  - `m_1` (naive top-2 margin) and `R_win`, `R_min` are **exactly invariant** —
    to the bit;
  - `rho`, `gap`, `q_8` and speckle must jump to their maximum-disorder values.

  **A wiring error shows up as the invariant quantity moving**, which is a
  recognisable failure rather than a merely wrong number. Registered:
  `m_1` identical to the bit under N3, or the instrument is mis-wired.
- **N4 — the trivial placebo.** `d = 0` must return `m_0 = 0` and `rho(0) = 0`
  exactly, at every pixel, on every stack.

### 4.3 Rule 17 — the binning axis, and its circularity, stated up front

Binning `q_d` against `R_win` is **circular**: a pixel with a tall focus peak has
a large margin *by construction*, and a noise fluctuation that raises `R_win`
raises both the bin and the statistic. Named mechanism, so the result is
circular until the shared path is broken.

**Break:** the detail axis is the local standard deviation of green luma over a
33x33 window of **one single frame** (the stack's middle frame), computed by an
operator that is not the focus measure and does not involve the argmax at all.
Both axes are reported; the `R_win` axis is reported **labelled circular** and is
not used to support any claim.

---

## 5. Scope, fixed before running

Stacks: `109MSDCF` (22), `119MSDCF` (33), `112MSDCF` (79), `coffee-bean` (105),
`foam` (100), and at least one of the owner's 299-frame deep stacks
(`bee-3-cpl`, the stack M85 rendered fact 1196 on). Reduced ladders are
permitted on the deep stacks for cost; any reduction is stated in the report.

Renders (deliverable 3) go to `C:\dev\strehl-out\M94-election-margin\` only.
`C:\dev\macro`, `D:\macro-dark-frames` and `D:\personal\macro` are read-only.

Files owned: `crates/strehl-cli/examples/m94-election-margin.rs`,
`crates/strehl-cli/examples/m60-disagreement.rs` (task 1 only),
`crates/strehl-cli/examples/m91-photometry.rs`, `docs/research/M94-*.md`,
`experiments/M94-election-margin/`. `merge.rs`, `align.rs`, `image_out.rs`,
`color.rs`, `demosaic.rs`, `m86-align.rs`, `SYNTHESIS.md`, `AGENTS.md` and
`docs/captures-needed.md` are **not** mine; any change to them is delivered as a
verbatim patch in the report.

---

## 6. What would falsify the result — registered now, not after

- **If B1/B2/B3 land arbitrary but the positive-control plant also reads
  arbitrary**, the instrument cannot discriminate and every real number is void.
- **If `m_1` moves at all under the N3 frame-permutation placebo**, the fold is
  order-dependent somewhere it must not be, and the whole run is void.
- **If F1 or F2 is below 100.000000%**, I am not measuring the shipped election
  and nothing here transfers to the product.
- **If the smooth/sharp split (B4) shows margins are small in *sharp* regions
  too**, the "smooth regions are near-random and harmless" reading is gone and the
  finding is stronger, not weaker — registered so I cannot claim it as expected
  either way.
- **The causal claim is out of scope.** An arbitrary election is *consistent
  with* fact 1177's uncorrected drift being the cause, and does not distinguish
  "the election is arbitrary because the operator is noisy" from "the election is
  arbitrary because frame `k` and frame `j` no longer describe the same scene
  point". Distinguishing those needs the aligner M86 is wiring, and this
  milestone must not pre-empt it.
