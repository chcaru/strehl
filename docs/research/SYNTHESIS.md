# Synthesis — a new macro focus stacker

Status: **Proposal, revised after adversarial review.** Nothing here is built.

> **REVISION — after independent adversarial review (`claude-opus-5`) and measurement M1.**
> The review found four design-changing errors in the first draft of this document. They are
> corrected inline below and summarised here so they are not inherited:
>
> 1. **The chained aligner is deleted.** §3.3 originally specified *both* iterative ECC chained
>    frame-to-previous *and* HDR+ tile refinement, while §4 fact #11 budgeted only the second.
>    Reports C and D were never in conflict — they priced different algorithms. Because drift is
>    linear in frame index (fact #1), each frame can be seeded from a **global model** rather than
>    from its predecessor, which makes all N alignments **independent and parallel**, removes the
>    serial Amdahl chain, and is *more* accurate (a 59-step chain is a random walk, and fact #5
>    says scale-centre error amplifies 1541x per pair; F validated composition over 16 steps, not
>    59). Corrected budget: **~0.5 s**, not 0.1 and not 5.0.
> 2. **The noise-gain headline was wrong by ~3x.** Corrected in §1.1 below.
> 3. **The merge reference must not be a raw per-band argmax**, or it reimports the 1.95–2.61x
>    argmax noise defect (fact #7) that this project exists to remove. Corrected in §1.1.
> 4. **Most "constants" in §4 are per-stack artifacts, not architecture.** They must be *fitted at
>    runtime*. See §4.1. The owner's instruction — *"don't overfit to anything specific to my
>    setup"* — is binding, and the empirical corpus is n=1 (one stack, one subject, one body).
>
> Measurement `M1-decode-measured.md` supersedes fact #11's decode term with real numbers.

Source: six parallel `claude-opus-5` research workstreams (A prior-corpus, B algorithms,
C landscape, D Rust/hardware, E plugin architecture, F camera/lens optics), plus follow-ups,
two adversarial reviews, and five measurements (M1 decode, M2 baseline + independent
re-derivation, M3 alignment, M4 dark-frame FPN, M5 diffraction).
Reports: `A-prior-corpus.md`, `B-algorithms-sota.md`, `C-landscape.md`,
`D-rust-and-hardware.md`, `E-plugin-architecture.md`, `F-camera-lens-optics.md`,
`M1-decode-measured.md`.

Every claim below is labelled. **MEASURED** = someone ran something. **VERIFIED** = a primary
source was read. **DERIVED** = computed, formula in the source report. **ARGUED** = reasoned,
not measured. **UNVERIFIED** = not established.

---

## 1. The thesis

Focus stacking has a stable, well-documented set of defects that *every* shipping tool has,
and they share one root cause: **existing stackers are selectors.** They pick, per pixel or
per subband, which frame is sharpest, and copy it. That single decision produces all of it:

- **Selection amplifies noise.** Argmax over N noise-only coefficients returns
  1.95x single-frame noise at N=10 and 2.61x at N=60 (MEASURED, B, own simulation), against
  1/sqrt(N) for averaging. Low-temperature softmax is indistinguishable from hardmax.
  **This is now measured on our own sensor and our own files, and independently verified**
  (MEASURED, M2 + M2-verification): a plain argmax stack of 22 frames is **1.253x noisier than
  one unstacked frame** on a flat region, **~1.48x** once shared scene structure is removed.
  **The cause is proven, not inferred.** On the same frames and the same region, a plain mean
  gives **0.534x** and a *placebo* selector with argmax's identical winner histogram but no
  coupling to the pixel's own noise gives **0.981x** — so neither drift nor scene structure can
  produce the effect. It is already present at **N=3** with 1.5 px of total drift, and grows
  monotonically in N. The prior project's 1.82x in flat highlights (A §1) is the same sign and
  the same order, and is no longer the claim this rests on.
- **Selection needs a sharpness metric, and the standard metric inverts under noise.** The
  Laplacian's winner-margin goes *negative* at sigma >= 0.01 — it actively prefers the wrong
  frame — while ring-difference filtering stays highest at every noise level
  (MEASURED, B, Surh CVPR 2017 Table 1).
- **Selection cannot represent "several frames are equally right"**, so it dithers, and the
  dithering is the halo. Halos are structural in every algorithm family, each fails differently,
  and expert practice is to run two tools and hand-blend (VERIFIED, C).
- **Selection discards its own evidence**, so no tool can say where it is unsure. No stacker
  emits confidence (VERIFIED, C). Retouching is therefore a manual hunt across 33 MP.

So the thesis is not "a faster stacker" and not "a better focus measure". It is:

> **Treat stacking as noise-aware estimation with a calibrated sensor model, in the camera's
> native colour-filter-array domain, and emit per-pixel confidence as a first-class output.**

Three consequences follow, and each is a differentiator that is *verified absent* from the
field:

1. **Estimate, don't select.** Select only where the inter-frame difference exceeds the
   calibrated noise floor; **average all N frames everywhere else**. This is HDR+'s Wiener gate
   `A(w) = |D|^2 / (|D|^2 + c*sigma^2)` (B). It is provably non-amplifying — Wiener shrinkage
   never exceeds 1.0 at any threshold and tends to 1/sqrt(N) (MEASURED, B).

   **§1.1 — Two corrections the review forced here. Both are load-bearing.**

   *(a) The reference must be regularised, never a raw argmax.* HDR+'s non-amplifying guarantee
   is **relative to its reference frame**, and HDR+ uses a single fixed frame. Generalising the
   reference to a per-band **argmax over frames** breaks the guarantee, because fact #7 says
   argmax over N returns **1.95–2.61x** single-frame noise. The bound would then be preserved
   but worthless: wherever the gate *rejects* (i.e. on resolved detail), the output would be the
   argmax reference, reproducing the prior project's measured defect exactly. **The reference is
   therefore selected from a regularised focus field** — spatially smoothed, parabola-fitted
   across frame index, and averaged over the top-k frames whose focus measure lies within the
   noise floor of the peak. The peak-vs-floor quantity is already computed for §1.3.

   **This is now measured, and it also sets a limit** (fact 23). Regularising the focus field with
   a 17x17 smooth drops winner speckle **34.4% -> 0.868%** and noise **1.253x -> 1.075x**. So the
   correction works — **but 1.075x is still above 1.0.** A regularised selector is still a
   selector. Only averaging goes below a single frame (0.534x). **Both halves are required and
   neither alone is sufficient**, which is the difference between this design and "a stacker with
   a better focus measure".

   *(b) The honest gain is ~sqrt(N) in flat regions, ~1.2–1.8x on detail — not 3–5.5x
   everywhere.* At the recommended step (`step = DoF/k`, `k ~ 1.3–1.5`, F), the number of frames
   whose depth of field covers a given depth is **k ~ 1.3–1.5**, not N. So in the depth-overlap
   region the gain is only **1.14–1.22x** (2.4x-oversampled stacks reach ~1.8x). Reaching 5.5x
   would need ~20x oversampling, i.e. ~660 frames. The gate is per-frequency, and defocus is a
   low-pass, so `|D|` is small at low frequency (averages correctly) and large on resolved
   texture (rejects, reverting to selection).

   **The real win is elsewhere, and it is bigger than it looks.** In flat, low-detail regions all
   N frames are identical up to noise, `|D|^2 << c*sigma^2`, and all N average — a genuine
   **~5.7x at N=33**. Flat regions are *precisely* where report A measured the prior tool at
   **1.82x worse than a single unstacked frame**. So the claim to defend, and to test, is:

   > ~sqrt(N) in flat and smooth regions, where current tools are worse than not stacking at
   > all; ~1.2–1.8x on resolved detail; never worse than a single frame anywhere.

   That is narrower than the first draft, still verified absent from the field, and unlike
   "3–5.5x" it is a claim the §5 discipline will not later convict us of. (ARGUED; experiment 1
   is the test.)
2. **Work in the CFA domain and never demosaic.** CFA-domain merging beats SOTA demosaicers by
   >3 dB *and* beats merge-then-demosaic (VERIFIED, B, Wronski et al.). The merge emits RGB
   directly. **Nothing in the field is RAW-native** — Zerene states plainly *"no stacking
   software really works directly with raw files"*, and Helicon's RAW-in/DNG-out demosaics via
   Adobe DNG Converter before aligning (VERIFIED, C).
3. **Emit confidence.** Everything a human currently retouches is predictable from four signals
   the stacker already computes and throws away (C follow-up): the focus-measure-vs-frame curve
   per pixel (its peak versus the noise floor, and its *modality*), output falling outside
   `[min,max]` of the sources, the winning frame differing from the locally-best frame, and
   retained alignment residuals plus coverage counts. **The last one costs zero pixel
   processing.**

A fourth, sharper product idea fell out of the artifact taxonomy and is worth stating
separately: **separate "retouch this" from "reshoot this."** Contamination haze, wind streaks
and never-in-focus gaps are physically unrecoverable. Telling the user while they are still at
the rig beats any amount of fusion cleverness.

---

## 2. Name

Recommendation: **`strehl`**.

The Strehl ratio is the standard measure of how close a real optical system comes to the
diffraction-limited ideal. It names precisely what the tool optimises, it is short,
pronounceable, unclaimed on crates.io (VERIFIED), and free of significant GitHub collision
(largest is a 4-star adaptive-optics repo). It also gives the project a natural identity: a
stacker whose distinguishing output is a *quality figure per pixel*.

Alternates, all verified free on crates.io: `petzval` (photographic-optics heritage),
`eclose` (entomological — the imago emerging), `abbe` (diffraction limit),
`ommatidia` (compound-eye facets; also literally "pluggable units").

Taken, avoid: `z-stackr`, `stackaroni`, `focus-stack`, `focusstack`, `ChimpStackr`,
`shinestacker`, `millefeuille`, `deptheos`, `Picolay` (VERIFIED, C).

---

## 3. Architecture

### 3.1 Decisions, and what lost

| Decision | Chosen | Runner-up and why it lost |
|---|---|---|
| Language | Rust | Given |
| Plugin mechanism | Statically-linked trait-object `Stage`s in a Cordis-shaped context; pipeline composed by declarative RON | **WASM Component Model lost on three verified facts**: the Canonical ABI is a copy boundary by its own explainer's admission, `shared-everything-threads`/`memory-control` are unimplemented in Wasmtime, and `wasi-webgpu` is Phase 2 so a wasm plugin cannot drive the GPU. Our unit of work is ~528 MB/frame (E) |
| GPU kernel contribution | **A compute kernel that emits an `f32` focus field.** Contributors are not required to be spliceable; the framework may compose and fuse **its own** kernels from named WGSL functions | `naga_oil` `virtual`/`override` lost: it is *total replacement* resolved by DFS import order, which makes algorithm choice a property of import order and makes A/B impossible (E follow-up). **The "kills fusion" half of that argument is now nearly worthless — fact 30 measured fusion at 0.14% of the pipeline — but the A/B objection stands and is sufficient on its own** |
| Compute backend | **`wgpu` only for v1.** Keep the CUDA seam, build no CUDA | CUDA fast path estimated at **~1.1x** end-to-end, on a stage that is 15-25% of the budget. Tensor cores irrelevant (every kernel below ~20 FLOP/byte, merge below 0.5). 99 KiB shared memory worth 2-5%, TMA 1-3%, persisting-L2 **0.2%** (D follow-up) |
| RAW decode | `rawler` (LGPL-2.1), behind a feature flag | Writing an ARW decoder lost: 2-4 months, because no permissive LJPEG implementation exists in any language. LGPL is satisfied by publishing our own source; 11 permissive crates already do this (C follow-up) |
| Alignment transform | **Affine** | MEASURED on the reference stack: translation 4.32e-3, euclidean 4.29e-3, **affine 1.45e-3**, homography 1.45e-3. Homography adds *literally nothing* — there is no perspective signal (F follow-up) |
| Aligned-frame storage | **Never materialise.** Gather at consumption time inside each kernel | Demosaic-then-align rejected: recreates a 24 GB working set, triples merge bandwidth, demosaics 60x instead of once. Materialising 4 CFA planes costs 4 GB for a wash on time (D follow-up) |
| Demosaic | **None.** The merge emits RGB | A separate demosaic stage loses >3 dB (B) |

### 3.2 Working set — the problem dissolves

The prior project's 23 GB was not bad luck. `60 x 33 MP x 3ch x f32 = 23.8 GB` — it had
materialised the entire stack as demosaiced float RGB (MEASURED, C follow-up). Its wall clock
regressed 81 s -> 456 s *because* its memory did (MEASURED, A).

Staying in u16 CFA: **66 MB/frame, 3.96 GB for 60 frames** — the whole stack fits in VRAM with
8x headroom (DERIVED, D). Storage u16, arithmetic f32. **f16 is wrong for CFA data**: a 10-bit
mantissa gives ~8 LSB steps on linear 14-bit values, worse than u16. f16 is fine for bounded
quantities — focus maps, weights, displacement fields.

Constraint to ratchet in CI from commit one: **peak RSS <= 8 GB, independent of frame count.**

**Measured against that ratchet, and it is closer than this section implied (`M2-rss-resolved.md`).**
The 3.96 GB above is *frame storage*; real peak also carries per-worker focus/selection buffers and
decoder scratch. At default thread count the skeleton measures **~4.0 GB at N=22** and **7.16 decimal
GB at N=105 real frames** — **89% of the ratchet**, with a synthetic N=220 run at 7.99 decimal GB.
The *shape* of the claim survives — peak is O(workers), not O(frames), and it saturates once the
pool hits 20 — but the constant is ~379 MB per worker, and **the planner under-counts it by
13-24%**, so it licenses more workers than the budget can pay for.

#### 3.2.1 The ratchet, restated — and the bug in how it was specified

**DECIDED (owner deferred to the implementer on units; owner chose "measure first" on the planner).**

**The unit is GiB.** `8 GB` now means **8 GiB = 8,589,934,592 bytes**, written as a byte constant and
never as a prose "8 GB" again. The deciding argument is internal coherence, not preference:
`MEMORY_BUDGET_BYTES` is literally `6 << 30`, i.e. **6 GiB**. A decimal-GB ratchet sitting next to a
GiB budget in the same binary is incoherent, and the 7% margin means the incoherence is not academic
— it flips the verdict. So the N=220 run at 7,616 MiB **passes, at 7.44 GiB, with 576 MiB of margin.**

**But pinning the unit exposes a larger bug in the ratchet's specification, and the unit question was
the less important half.** Fact 22 measured that peak RSS is a function of **live concurrency**:
the *same binary on the same 22 frames* peaks at **833 MB at 1 thread, ~1.6 GB at 3, and ~4.0 GB at
32**. Peak RSS is therefore **a property of the machine's core count as much as of the code**. An
absolute peak-RSS ceiling asserted in CI is consequently **not a regression test — it is a flake**:
it passes vacuously on a small runner and fails on a large one, and either outcome tells you nothing
about whether the code regressed. As specified, the ratchet could have gone green through the exact
regression it exists to catch, simply by running on fewer cores.

**So the ratchet is specified as three assertions, not one, and the first two are the ones that
actually carry the intent:**

1. **Shape (the real test).** With `RAYON_NUM_THREADS` **pinned**, peak RSS at `N = 4 x pool` must
   not exceed peak RSS at `N = 2 x pool` by more than a small tolerance. This is a direct test of
   "O(workers), not O(frames)" — the property §3.2 exists to defend — and it is
   **machine-independent**, because both sides move together with core count.
2. **Per-worker cost.** `peak_rss / live_workers` at a pinned thread count, ratcheted as its own
   number. This is the constant that actually regresses when someone adds a buffer, and it is the
   quantity the planner needs to model correctly. It is the honest target of M8.
3. **Absolute ceiling: 8 GiB**, at a **pinned thread count and a pinned N**, recorded with both.
   Kept as a backstop, but demoted — an unpinned absolute ceiling is the flake described above.

> **ASSERTIONS 1 AND 2 ARE BOTH WRONG AS WRITTEN. M8 measured them, at the exact pair assertion 1
> named, and both fail on unregressed code.** Reproduced from the raw CSVs independently.
> **This is my own specification being refuted, and the intent survives while both formulas die.**
>
> **Assertion 1 fails: ratio 1.196 at pool=4 and 1.163 at pool=8** — that is +16% to +20% of growth
> on clean code, on a gate whose entire job is to notice a regression. Giving it a 20% tolerance to
> make it green would leave it unable to detect anything worth detecting. **Two measured mechanisms,
> neither of them a leak:**
> - **`chunks` grows with N until it saturates at `workers`, and the reduce tree costs 110.04 MiB
>   per level** (fact 33). That is O(log N) growth the assertion did not know about.
> - **`chunk_len` 1 → 2 fills the concurrency window.** Same `chunks` (16), same pool (4), N=16 vs
>   N=32: **1912 → 2393 MiB, +25%.** A worker that decodes a single frame is at its high-water mark
>   only briefly, so the pool never actually fills. My formula compared two points that differ in
>   *both* confounds at once.
>
> **The intent does hold.** Once `chunks` has saturated *and* `chunk_len ≥ 2`, growth in N is nearly
> flat — the system really is O(workers), not O(N). That is the property; assertion 1 just was not
> measuring it.
>
> **Assertion 2's estimator is wrong.** `peak_rss / live_workers` silently absorbs the process floor
> *and* the whole reduce tree, so at one pinned condition it ranges over **355.5–384.0 MiB** driven
> only by how many reduce levels the plan happens to have. Ratcheting it ratchets `chunks`. **The
> quantity it wants is the fitted slope, 342.8 ± 5.4 MiB per live worker**, which moves when someone
> adds a buffer and does not move when `chunks` changes.

**Restatement (this replaces assertions 1 and 2 above).**

1. **Shape.** With `RAYON_NUM_THREADS` pinned, compare two `N` that produce the **same `chunks`** and
   **both have `chunk_len ≥ 2`**. Record `chunks`, `chunk_len`, `threads` and `N` beside the result;
   **if the two sides differ in `chunks` or `chunk_len`, the gate must fail loudly rather than
   pass** — a comparison across a confound is not a weaker test, it is a different one.
   **Take the median of at least 3 repeats per side, and set the tolerance at 12%.** *(That
   tolerance is not a matter of taste and it is where I part company with M8's own proposal: M8
   suggests N=40 vs N=60 at 32 threads on a measured 1.049, but 1.049 is a mean of 5, and the N=40
   condition's own run-to-run spread is **11.7%** — 6861.4 to 7665.1 MiB across 5 runs. Worst case
   the pair lands at **1.119**. A 5% tolerance on that pair is a flake with extra steps.)*
2. **Per-worker cost — ratchet the fitted slope, not a ratio.** `342.8 ± 5.4 MiB` per live worker,
   fitted across a sweep, not divided out of a single run.
3. **Absolute ceiling: 8 GiB**, unchanged, and still a demoted backstop. **M8 supplied the real-file
   evidence the GiB-vs-decimal decision previously lacked**: `coffee-bean` at N=60 peaks at
   **7681 MiB**, which passes 8 GiB with 511 MiB of margin and *fails* 8 decimal GB (7629 MiB). The
   unit choice flips the verdict on a 60-frame stack of the owner's own files, not merely on the
   synthetic N=220 run it was decided from.

**A general lesson, and it is why this whole subsection got rewritten twice.** Assertion 1 was
derived by *reasoning* about what peak RSS should depend on, and it was wrong because two real
mechanisms — a reduce tree and a concurrency-window filling effect — were not in the mental model.
**A gate written from a model of the system tests the model, not the system.** Measure the gate's
own behaviour on known-good code before trusting it to judge unknown code.

**Any peak-RSS figure quoted anywhere in this corpus without its thread count is uninterpretable**,
and several already published figures were exactly that (see fact 22: two agents measured honestly,
disagreed 2.2x, and were both right about different thread counts). Quote the thread count or do
not quote the number.

See §10 questions 12-13.

### 3.3 Pipeline

```
decode (CPU, rayon ACROSS files -- 2.5x over one-at-a-time, MEASURED M1)
  ->  calibrate (black/white/FPN, per CFA plane)
  ->  detect capture mode (breathing | rail) from EXIF + fitted residual signature
  ->  align  coarse-to-fine tiled NCC against a FIXED reference frame.
             Every frame independent, all N in parallel. 4-parameter similarity,
             scale centre regularised toward the principal point.
             No chaining. No global model of transform vs frame index.
             (MEASURED M3: 13-16 ms/frame, 0.78-0.96 s for a 60-frame stack)
             SUPERSEDED FOR DEEP STACKS by M10: a fixed reference places only 76/105 frames.
             Use a sparse multiscale graph of DIRECT pairwise fits (discard spans 1-2), then
             one global Huber-IRLS least squares for per-frame (log a, theta, tx, ty),
             restricted to the anchor's connected component. 105/105 at 6.76 plane px
             held-out; 0.58-0.67 px on shallow stacks. The scale centre is fitted PER STACK
             (fact 48), not per rig. NOT YET IMPLEMENTED in crates/.
  ->  focus volume (Tenengrad = Sobel gradient MAGNITUDE under a 27x27 BOX WINDOW, radius 13,
             support radius 14, per CFA plane, vs calibrated noise floor. MEASURED M11:
             replaces the multi-scale ring-difference, which ranked 26-27th of 36 operators
             and cannot be rescued by re-tuning its radii. Tenengrad PARETO-DOMINATES
             ring(1,3) on BOTH axes -- noise 1.1324x vs 1.3475x, selectivity ~0.85 vs ~0.41
             -- so the swap is not a trade-off. WINDOW MEASURED M13, superseding M11's 11x11,
             which is DOMINATED (fact 65): radius 13 is the regret argmin over 36 occluding-
             edge cells and stable in all 3 seeds; basin w11-w15 is defensible. The box MUST
             be the running-sum form -- cost is then O(1) in the radius and the widening is
             free (fact 66); a naive convolution at radius 13 is ~841x the work.
             SHIPPED M14 in crates/strehl-core/src/focus.rs. "Magnitude", NOT "energy":
             M11's measured `tenengrad-w{N}` is `squared: false` (fact 70), so squaring it
             would ship an operator nobody benchmarked. BLIND SPOT (fact 73): on an
             UNTEXTURED monotone edge this operator has EXACTLY ZERO focus discrimination
             at radius 13. Confidence must therefore come from cross-frame spread in the
             focus volume, never from focus magnitude -- see discipline 29)
  ->  merge (band-selective noise-gated accumulation; select above the floor,
             average below it; reference from a REGULARISED focus field, never argmax;
             anisotropic structure-tensor kernels; emits RGB.
             THE REGULARISER IS NOT BUILT YET AND IS THE LARGEST MEASURED QUALITY WIN
             OUTSTANDING: at width 17 it cuts absolute reconstruction error 35% (fact 84),
             more than the entire window axis provides. It does NOT reopen the window
             choice -- w13 holds at every width 1-33 (fact 80). Width 3 is WORSE than no
             regulariser at all (fact 86); do not ship a narrow one)
  ->  confidence (peak-vs-floor, modality, out-of-range, index-map coherence, residuals,
                  coverage/occlusion. peak-vs-floor is load-bearing and must be measured
                  ACROSS FRAMES: fact 73 shows focus magnitude can be large where the
                  discriminating information is exactly zero)
  ->  colour + output (tiled float BigTIFF / DNG)
```

**Alignment is coarse-to-fine per frame against a fixed reference. Superseded by M3 —
measured, not argued.** The original design said "fit one global model of transform vs frame
index, then seed per-frame refinement from it." Killing the chain was right; the global model
was not. Measured on the reference stack:

- **Chaining fails by 25 px at the sensor corner.** Composing 21 adjacent-pair fits recovers
  -1.244% total scale against a directly measured -1.835% — a **32% underestimate**, while every
  individual adjacent fit *looks excellent* (0.446 px residual, better than the direct fits).
  The mechanism is **pixel locking**, not a random walk: sub-pixel refinement is biased toward
  integer displacements by a roughly fixed absolute amount, so at the ~1.9 px drift of an
  adjacent pair it is a ~5% error with a consistent sign that compounds over 21 steps, whereas
  at the 39 px drift of a direct fit it is ~0.25% and vanishes. Systematic error gets *worse*
  with more frames, not better.
- **A global model in frame index is worse than just measuring each frame.** A straight line
  leaves 0.57 px RMS of scale error at the plane corner, a quadratic 0.50 px, against a per-frame
  direct-fit precision of 0.16 px. The global model was to be the *seed* for something 3.6x more
  accurate than itself, and an 8x-decimated coarse pass supplies capture range on its own.
- **Similarity is the whole model.** 4 parameters. Going to affine (6) or quadratic (12) reduces
  the residual by at most 6%, on both the filtered and unfiltered tile sets. Rotation is
  unmeasurable (<=0.21 px at the corner) — keep the parameter as a guard against tripod flex,
  expect it to stay zero.

All N alignments are therefore independent, which is both the accurate option and the parallel
one. The remaining 0.6-1.3 px residual is neither estimator noise (floor 0.19 px) nor global
model error (richer geometry does not touch it). **M3 named two candidate causes and could not
separate them; M6 did** — see below.

> **The residual's cause is now measured (M6, facts 18 and 31), and it changes this stage.** It is
> **blur-induced correlation bias**: a tile far from its own best-focus frame correlates worse, and
> the estimator reads that as displacement. In-focus tiles already align at **0.144-0.172 px**, at
> or below the estimator floor. **So the aligner is not broken — it is being fed tiles that cannot
> answer.**
>
> **The fix is a weight, not a model:** weight each tile in the similarity fit by its defocus
> mismatch `|c − w|` (pair midpoint vs the tile's own best-focus frame), down-weighting tiles far
> from focus. `w` is the winner-index map the pipeline already computes, so this costs nothing new.
> It needs **no lens identity and no PSF model**, which is why the lens plugin died with it
> (§3.4.2). Expected effect is bounded by the measured gap: γ = **+0.0597 / +0.0452 px per frame**
> of mismatch, contributing 69% and 105% of the mean residual on two of the three stacks.
>
> **Two things this does not fix, and they are separate.** (i) The `coffee-bean` stack shows the
> gap *inverted* at small baselines (−0.077, −0.083 px at Δ=1,2) before turning positive — the
> weight is not unconditionally safe, and should be validated per stack rather than assumed.
> (ii) Deep stacks have a prior problem: **the fixed reference itself fails past ~100 frames**
> (risk 11), and no weighting scheme rescues a pair that shares no correlatable content.

**Both capture modes share this structure**, which is why rail support — when it lands — does not
force a second pipeline. A rail produces genuine *parallax*: point scale depends on depth, so
**no global 2D transform can be correct** — but the residual is locally near-constant, which is
what a per-tile refinement stage absorbs. Rail would promote per-tile refinement from optional to
**mandatory**, and make D's tile-search budget the floor rather than the optimistic case.
Occlusion at depth discontinuities is a real, separate problem (different frames see *different
surfaces*, which the Wiener gate would otherwise misread as "sharp vs blurred").

The measured similarity result (M3 §2) is **specific to in-camera bracketing**, and the mechanism
says so: the camera does not move, so the image-space effect of refocusing is magnification about
a fixed point, which is exactly a similarity. That argument does not survive a rail. Rail data
must never be run through the similarity model.

> **Rail is deferred from v1** — no rail hardware is available, so every rail claim above is
> *derived and untested*. See §9. `CaptureMode` and mode detection stay; occlusion handling does
> not. For breathing alone, per-tile refinement beyond the global similarity is polish rather than
> a requirement, and must justify itself by measurement — M3 puts the unmodelled residual at
> 0.6-1.3 px, which is the size of the prize.

**The noise model is injected, not per-stage.** Six of eight stages consume the same calibrated
per-CFA-plane noise model (B, escalated). If it is not first-class from v1, each stage grows a
private inconsistent estimate — which is precisely the mechanism behind the prior project's
2-5x defect. Form: `sigma^2(S, ISO) = g*S + (RN_e*g)^2`, `g = ISO/436.8` DN/e-, which reproduces
the camera's own white level to 0.23% (MEASURED, F). Both greens modelled separately.

**A runtime noise estimator is on the v1 path, not v2** (review, first-tier). Every gating
decision depends on the noise floor. A user on an unprofiled body would otherwise get a *wrong*
floor and the gate would silently mis-gate — no error, just bad output. Estimate per stack from
temporal sigma across frames plus a flat-region photon-transfer fit, and use it to **validate**
the baked A7C II profile. If estimator and profile disagree on the reference body, one of them is
wrong and we want to know on day one.

### 3.4 The plugin model

- A plugin is a **`Stage`**: object-safe, `Send + Sync`, with a `resources()` declaration, and
  `gpu() -> Option<&dyn GpuStage>` so GPU support is genuinely optional with CPU fallback.
- Large buffers cross the boundary as a **`TileView` descriptor**, never a bare slice, so
  CPU/GPU residency and ownership stay explicit and zero-copy.
- **The framework owns the warp, the scale centre and the sampler. A plugin never sees a warp.**
  Rule 2 forbids materialising aligned frames, so a contributed function receives *already-gathered
  samples at reference coordinates*. See §3.4.1 (B1) — this is not a detail; the naive interface
  cannot express rule 2 at all.
- GPU plugins contribute **a compute kernel that emits an `f32` focus field** — that is the whole
  contract (fact 30). They are *not* required to be spliceable into a fused kernel: M7 measured the
  fusion prize at **1.449 ms = 0.14% of the pipeline**, which does not pay for making a contributor
  inherit our tile size, halo, shared-memory layout and register budget. What the contract *does*
  require is running on the GPU, which is worth **~165x**. The framework may still compose **its
  own** kernels from WGSL source at run time (`naga_oil`, SPIR-V cached by content hash) and fuse
  its own built-in measures — fused and unfused are bit-identical, so that is an internal
  optimisation and never a semantic difference. **Not `build.rs`, and not a spliced contributor
  ABI** — see §3.4.1 (B2).
- **A focus measure declares its own spatial support**, and the merge derives its regulariser width
  from that declaration rather than reading a constant. See §3.4.1 (B3).
- **A focus measure returns sigma-multiples, not raw response**, so the framework owns the division
  by the noise floor and rule 3 is enforced by the type rather than by documentation. See
  §3.4.1 (B4).
- **Names for the algorithm, constants for the schedule.** This is Halide's algorithm/schedule
  split falling out of the mechanism rather than being imposed on it.
- **Camera and lens knowledge is a *profile*, which is data, not a plugin.** See §3.4.2. What data
  there is supplies **priors, never capability**: every accessor returns `Option`, and a geometric
  correction returns `None` to *disable* rather than approximate, because a wrong distortion
  coefficient is worse than none.
- **Unresolved dependencies are settled once at plan time and reported in the output's provenance**
  — the `Provenance::Fallback` shape already implemented in `noise.rs`/`profile.rs`, whose test
  asserts that an unknown body falls back *visibly*. This is a **stronger** guarantee than the
  Cordis `try_activate -> Inactive{unmet}` shape it replaces, and it is the right one for a batch
  run that decides everything before touching a pixel. Cordis's shape is reactive — it exists so a
  component can activate later when a provider appears at run time, which cannot happen here.

What we deliberately refuse to make pluggable: the pixel data model, the noise model interface,
the colour pipeline, the interpolation kernel, and stage ordering semantics. Registries commute;
the pixel chain does not.

### 3.4.1 What measurement did to the plugin model

**The internal justification for plugin machinery is gone. The external one is the whole point,
and it is the owner's stated requirement.**

`E-plugin-architecture.md` §4.12 sets the test: *"The strongest argument for the whole architecture
is not extensibility at all — it is that §4.5's declared capabilities and §4.9's caching are what
let 24 GB of frames be scheduled and re-run cheaply... **If the plugin system is ever justified on
extensibility alone, it is over-engineered.**"*

Both internal legs have since been cut by our own measurements:

- **§4.5's tiling/capability apparatus solved a 24 GB problem that no longer exists.** §3.2 is
  titled "the problem dissolves" — u16 CFA fits 60 frames in VRAM with 8x headroom — and fact 22
  **measured** peak RSS at 1.81-1.94 GB. Nothing needs to be tiled.
- **§4.9's caching wanted to cache aligned frames.** Rule 2 forbids materialising them, so the
  artifact does not exist; and fact 15 measured alignment at **0.78-0.96 s for 60 frames, ~6% of
  budget**, so caching it would save under a second.

**The ruling is not "cut the plugin system".** E's test was written to catch machinery built for
nobody. The owner asked for this explicitly and in these words: *"the stacking techniques, algos,
etc. should all be plugins too — recomposable and **easily contributable by others**."* So
extensibility is not a failed justification here; it is the **only** one that was ever load-bearing,
and the design must now be judged **solely on contributor experience**. That cuts both ways:

- **Cut everything that existed to serve internal engineering:** `Resources`/`negotiate`/`Access`,
  the derivation cache, two-pass ROI negotiation, tiling machinery. They were priced for a problem
  measurement dissolved.
- **Strengthen everything that serves a contributor**, because that is now the entire return.

Four blocking items follow, and all four are cheap **today** and expensive after the first stage is
written against the wrong signature.

**B1 — `TileView`/`Stage` as specified cannot express rule 2.** E's
`Stage::run(ctx, inputs: &[TileView], outputs: &mut [TileViewMut])` is a materialised-buffer-in,
buffer-out interface with an axis-aligned integer ROI and no warp; the strings `gather` and
`materialis` appear **nowhere** in E. E and the hardware workstream ran in parallel and rule 2 came
out of the latter; nobody reconciled them. Worse, a scalar `fn halo(&self) -> u32` **cannot express
a warp-dependent source ROI** — under a radial similarity the offset is proportional to radius from
the scale centre, ~0 at the centre and **39 plane px at the corner** on a 22-frame stack (M3 §0), so
a scalar halo must be sized for the corner and paid everywhere (~2.6x tile area for a 128 px tile).
And if one kernel gathers bilinear while another gathers bicubic they disagree about what "the same
pixel" is, at the same 0.6-1.3 px scale as M3's unmodelled residual.
**Fix:** the framework owns `Warp`, the scale centre and the sampler, and hands contributed
functions already-gathered samples at reference coordinates; replace `halo() -> u32` with
`source_roi(&self, out: Roi, warp: &Warp) -> Roi` (default impl `out.expand(halo)`); add the
interpolation kernel to the rigid-seam list.

> **B1 CONFIRMED BY M6 — but two of its three numbers were wrong, and the surviving argument is a
> different one.** M6 did the arithmetic on M3's fitted similarities across all three stacks
> (`M6-residual-halo-measured.md`). Independently reproduced.
>
> - **"39 plane px at the corner" is not a halo.** 39 px is the *Euclidean displacement magnitude*;
>   a halo is a **rectangle** expansion, so the quantity wanted is `max(|dx|,|dy|)`. Measured:
>   **32.39 px** on 109MSDCF. B1 overstated by **1.20x**. *(Confirmed by hand: at the fitted scale
>   centre the corner sits 4,307 px out, giving 39.9 px of displacement but only 32.8 px of halo.)*
> - **"~2.6x tile area" is also wrong.** The real within-frame waste at 128 px is **1.34x**
>   (1.17x at 256 px, 1.56x at 64 px). **On its own this would NOT have killed a scalar `halo()`** —
>   a 1.34x gather overhead is a price an interface could reasonably charge.
> - **What actually kills it is stack dependence, which B1 never mentioned.** The halo is a property
>   of *the stack*, not of the lens: corner halo runs **19.42 px / 32.39 px / 89.23 px** across the
>   three stacks, tracking total drift (−1.029% / −1.835% / −4.575%), and on one stack it grows
>   0.87 → 18.6 → 89.2 px as N goes 5 → 20 → 100. A `halo() -> usize` is answered **once, without
>   seeing the stack**, so it must be sized for the worst case (89.23 px) and then costs **4.25x**
>   and **3.48x** on the other two. Correlation with radius from the scale centre is
>   **Spearman ρ = 0.963–0.975**, i.e. the radial structure B1 asserted is real.
>
> **So the fix stands unchanged and is now better justified:** `source_roi(out, &Warp)` gets both
> the radial *and* the stack dependence for free, because the `Warp` it is handed is the one that
> was actually fitted to the stack in hand. **The lesson is that B1 reached the right interface
> through a mis-stated number** — the kind of thing that survives review and dies to arithmetic.

**B2 — "build-time WGSL splicing" is a mistranslation of E, and it destroys the headline
requirement.** E §F2.2 says *"selected by name at **pipeline-build time**"* — and in `wgpu`,
pipeline creation is a **runtime** call. E §4.2 is explicit: contributed kernels are
*"hot-reloadable for free (**re-read a file, recompose the shader, rebuild the pipeline**)"*, and
§F2.2 already specifies *"cache emitted SPIR-V by content hash of (module set, entry point,
constants) and it is amortised to zero across runs."* "pipeline-build time" became "build time"
became "`build.rs`", and §7 then logged the resulting contributor cost as a *risk* rather than as a
*bug*. **The runtime cost of the two is identical** — both end at one `set_pipeline` and one
dispatch — and both keep the decisive fusion advantage. The only difference is when SPIR-V is
emitted, and E already amortises that to zero.

| | `build.rs` splicing (as §3.4 wrongly said) | runtime composition (as E actually says) |
| --- | --- | --- |
| To contribute | Rust toolchain, full workspace, `cargo build --release` | drop a `.wgsl` in a directory |
| Iterate | full rebuild per edit | re-run; hot reload for free |
| Shader error | a `build.rs` failure at a spliced line offset, in generated source the author never sees | a runtime error naming the author's own file and line |
| A/B two measures | two builds | two config values, one binary |
| Distribute | fork the repo | ship a file |

**Fix: never write the `build.rs`.** Compose at run time, cache by content hash. This is the single
highest-value item in this section, because it *is* "easily contributable by others".

> **B2 SUPERSEDED BY MEASUREMENT — M7 priced the thing both options were competing to preserve, and
> it is worth 0.14% of the pipeline.** The table above argues about *when* to splice WGSL. M7 asked
> whether to splice at all, by porting ring-difference to one `wgpu` kernel and timing the fused and
> unfused paths side by side (`M7-gpu-focus-measured.md`). Results, independently reproduced:
>
> | Quantity | Measured |
> | --- | --- |
> | Focus + merge, fused, 22 frames on the 5090 | **4.117 ms** (0.187 ms/frame), bandwidth-bound at **84%** of measured DRAM read |
> | Same, unfused — focus written to memory, merge reads it back (**i.e. a plugin that just emits a focus field**) | 5.566 ms |
> | **The fusion prize** | **1.449 ms = 0.14% of a cold pipeline, 0.20% warm** |
> | Full focus volume resident — the *most permissive* plugin model there is | only 1.683 ms worse than fused |
> | GPU vs best parallel CPU | **~165x** |
>
> **So the fusion prize does not pay for the contribution format, and it is not close.** Splicing
> would make a contributor inherit our tile size, halo, shared-memory layout, register budget and
> single-pass restriction, make their measure untestable in isolation, and — worst — **harden fact
> 25's radius/regulariser coupling into the ABI**. All to buy back 0.14%.
>
> **The rule is therefore "run on the GPU, emit an `f32` focus field", not "be spliceable".** That
> keeps the 165x, which is the part that actually matters, and costs the plugin model nothing.
> Fusion survives as an **internal** optimisation the framework may apply to its own built-in
> measures: M7's self-test group 6 proves fused and unfused produce **bit-identical** focus fields
> and winner maps, so fusion is an implementation detail and not a different answer.
>
> **This retires the B2 debate rather than settling it.** Both columns of the table above assumed
> the fusion advantage was "decisive"; it was never measured until now. Runtime composition remains
> right for the framework's *own* kernels, so the `build.rs` verdict stands — but no contributor is
> required to be spliceable, so the contributor-experience column is moot.

**B3 — the focus measure and the merge are coupled, and the coupling is currently invisible.**
`M2-verification.md` §6 records that argmax's noise excess is *spatially correlated over 3-7 px
because the ring-difference measure correlates winners* — and 3-7 px is exactly `focus.rs`'s own
`INNER_RADIUS: 1` / `OUTER_RADIUS: 3` support. **So the 17x17 regulariser that facts 20 and 23 rest
on is a constant tuned to one measure's support.** §3.3 lists focus volume and merge as separate
pluggable stages, so a contributor who supplies a 9x9 DCT-energy or multi-scale wavelet measure and
leaves the merge at its default gets a **silently wrong stack**: no error, plausible output, wrong
regularisation. §5's property tests cannot catch it — *sensitivity* only requires that
distinguishable configs produce distinguishable output, and wrong-but-distinguishable passes.
**Fix:** `fn support_px(&self) -> u32` on the measure; the merge derives its regulariser width from
it; a property test asserts the derivation.

> **B3 IS REJECTED — MEASURED by M9, and independently reproduced. `support_px()` comes off the
> interface.** B3 was the last Blocking verdict resting on an unmeasured claim, and the claim was
> half right in a way that made the wrong fix look obvious.
>
> **The coupling is real; it is just not to support.** Argmax's noise excess tracks the operator's
> **centre-tap sensitivity fraction φ** — the share of the operator's total response that comes from
> the pixel being selected. **ρ(φ, excess) = +0.918 / +0.894** across two stacks (p < 0.0001);
> **ρ(support radius, excess) = −0.170 / −0.243, not significant** (p = 0.53 / 0.37). A 3x3 Sobel,
> which has a **zero centre tap**, shows **no excess at all: 0.9952x**. The mechanism is that a
> pixel's own noise votes for its own selection; how far the operator reaches is irrelevant.
>
> **Why `support_px()` specifically cannot work, algebraically.** For a ring difference the
> linearised kernel is `1/n_i − 1/n_o` at centre and `−1/n_o` in the annulus, so
> **φ = (1/n_i − 1/n_o) / (2(1 − n_i/n_o)) = 1/(2·n_i) = 1/(2·(2·inner+1)²)** —
> **the outer radius cancels exactly.** *(Derived by hand in exact rational arithmetic, independent
> of M9's harness; `ring(1,3)`, `ring(1,12)` and `ring(1,2)` all give φ = 1/18 identically.)*
> **`support_px()` reports the outer radius. It reports precisely the term that cancels.**
>
> **The empirical form of the same point, which needs no model at all:** among operators declaring
> **the same** `support_px()`, φ still spans **12.7x to 321x** and the noise excess spans up to
> **0.74 ratio units** — 37x the pre-registered 0.02 severity floor. The interface field has almost
> no predictive power inside its own equivalence class.
>
> **Decision-theoretic form, which is what actually rules.** A merge told only `support_px()`
> achieves worst-case regret **0.0646 / 0.0037** ratio units against a per-measure oracle; a merge
> told **nothing** achieves **0.0646 / 0.0045**. **Value of the interface = +0.0000 / +0.0009**,
> against a 0.02 floor, and below the statistic's own placebo floor of **+0.0326**.
>
> **Fix, replacing the one above: nothing goes on the interface.** φ is *framework-measurable* — the
> framework can finite-difference any contributed measure itself, which is exactly how M9 measured
> it. Contributors declare nothing; the framework learns what it needs by probing. **This is the
> better outcome for a plugin system: it cannot be got wrong by a contributor, and it works for
> measures nobody anticipated.**

**B4 — rule 3 is documented, not enforced.** §3.4's enforcement is a refusal to make the noise-model
*interface* pluggable, which closes the interface but not the behaviour: a plugin handed raw pixels
can always compute its own local sigma, reintroducing the exact 2-5x defect this project exists to
remove. **Fix:** (i) contributed measures return a `SigmaMultiples` newtype so the framework owns
the division — `focus.rs` already does this internally; (ii) add a **fifth** property test,
*noise-model sensitivity*: perturb the injected model and assert every downstream stage moves as
predicted. It must be a **non-uniform** perturbation (the read-noise term alone, not a global
scale), because a global scale cancels out of a ranking and the test would be a tautology — which
is itself the §5 metric-validity failure mode.

### 3.4.2 Camera and lens: profiles, not plugins

**Stated plainly, because the requirement changed shape under measurement and the docs had not said
so.** The owner asked for pluggable camera and lens specifics. What survives is:

- **Camera: four numbers** — `gain_divisor`, `read_noise_e_low`, `read_noise_e_high`,
  `second_base_iso`. White level, black level and the CFA pattern are **decoder output, per frame**,
  because they are firmware- and compression-dependent (M1 §2). `g` is DERIVED, not measured, and
  §3.3 puts a runtime estimator on the v1 path whose job is to *validate the profile from the
  stack*.
- **Lens: one measured float plus an EXIF parser.** `F-camera-lens-optics.md` §7 rules out by name
  the PDAF map, PDAF depth, field curvature, `FocusPosition2` as depth, LensFun/LCP (neither
  database contains the SEL100M28GM), and vignetting (coefficients are all zeros). Distortion and
  TCA come from Sony's own maker notes, which is decoder work. **The breathing scale prior is dead
  too** — see §4.1. What remains is the **bellows factor `(1 + m/p)`**, where `p` is pupil
  magnification: unpublished by every manufacturer, **now measured rather than assumed — `p ≈ 1.0-1.4`
  for the composed path (fact 27)**, and previously worth ±38% on every capture-advisor number at
  m=1.4 (F1.7b).

  **Correction, and it is mine.** This section previously called `p` "the only gear constant that
  can be neither read from EXIF nor fitted from a stack". That is **wrong**. A diffraction-limited
  system has a hard OTF zero at `f_c = 1/(lambda * N_eff)`, so the frequency at which a well-focused
  frame's power spectrum flattens into its own noise floor **recovers `N_eff`, and hence
  `(1 + m/p)`, directly from pixels**. The three existing stacks happen to be an aperture sweep at
  near-constant magnification — f/5.6, f/8, f/11 with `FocusPosition2` 56-59 — so this is measurable
  on files that already exist, with no bench and no new captures. That is M5. Note also that what
  the formulas need is the **bellows factor**, not `p`; separating the two requires knowing `m`,
  which needs a ruler in frame, and matters only for *extrapolating* to a different magnification.

  **M5 ran, and it answered.** `(1 + m/p) ∈ [2.41, 3.06]`, `p ≈ 1.0-1.4`, `p = 0.5` refuted
  model-free (fact 27). The ±38% advisory collapses to **−20%/+2%**. **So the lens profile's one
  float now has measured content rather than an assumption in it** — and the profile must store `p`,
  not `B`, because `B` depends on the shot's magnification while `p` is the property of the optical
  path. Storing `B` would silently apply one magnification's bellows factor to every other.

  **And the float earns its place, because EXIF actively misleads here.** `FNumber` is the *marked*
  aperture with no bellows correction (fact 28), so a tool that reads EXIF and stops is wrong by ~3x
  at 2:1 and will recommend f/11 as safe when it is optically f/33. The lens profile is small, but
  it is the difference between a correct advisor and a confidently wrong one.

So: **camera profiles are a TOML table; lens profiles are one float and a maker-note parser.**
Measurement dissolved the rest, mostly by showing that runtime fitting is both cheaper and more
accurate than any profile could be (§4.1). This does not weaken the tool — a runtime fit
generalises to gear nobody has profiled, which is what "generally SOTA" requires — but it must be
called what it is.

**One candidate could still make gear knowledge into genuine code, and it is unresolved.** The lens
is not telecentric, so the defocus PSF is **field-dependent** and a single global PSF model is wrong
toward the corners (F §5.3). One of the two candidate causes of M3's unexplained 0.6-1.3 px residual
is *blur-induced correlation bias*. **If that is the cause, a field-dependent defocus PSF is biasing
the aligner, and modelling it per lens is real per-lens computation.** Do not close the lens-plugin
question before running §10 question 6.

> **RESOLVED, and the answer is no (M6, facts 18 and 31).** The conditional above has a true
> antecedent and a false consequent, and its two halves come apart. **The cause *is* blur-induced
> correlation bias** — in-focus tiles align at 0.144-0.172 px, at the estimator floor, while
> far-from-focus tiles in the same pairs sit at 0.25-0.69 px, and the gap survives within-pair and
> within-tile. **But the mechanism is symmetric peak degradation, not directed peak displacement.**
> M6's S6 statistic, which recovers a planted directional bias cleanly and is null on
> variance-only perturbations, is **null on all three real stacks**. A field-dependent *asymmetric*
> PSF is what would have made per-lens modelling pay, and there is no evidence of one.
>
> **So the last candidate is gone and the lens profile stays a data file: one measured float (`p`,
> fact 27) plus an EXIF parser.** The fix for the residual belongs in the aligner and needs no lens
> identity whatsoever — weight tiles by `|c − w|`, down-weighting tiles far from their own best
> focus. That generalises to every lens, including ones nobody has profiled, which is what
> "generally SOTA" requires (§4.1).
>
> **Two caveats M6 raised against itself, and they are the honest limits of this conclusion.**
> (i) A *signed-linear* field-dependent PSF is mathematically indistinguishable from a per-pair
> scale change and is undetectable by **any** residual-based method, including this one — so
> field-dependence is bounded, not excluded. (ii) This is one camera and one lens: the conclusion
> is inferred from *absent* field-dependence on this rig, not from a cross-lens comparison.

**Over-engineering guard.** v1 is one binary, all stages in-tree, no dynamic loading, no WASM,
no DI container. What must not be foreclosed: the object-safe `Stage` signature, `TileView`
descriptors everywhere, `source_roi(out, warp)` rather than `halo()`, `support_px()`,
`SigmaMultiples`, a framework-owned sampler, `ctx.provide/require` from day one, and **runtime**
source-level kernel composition — the last now scoped by fact 30 to the framework's **own** kernels,
since contributors are not required to be spliceable and only have to emit an `f32` focus field.

---

## 4. Measured facts that constrain the design

> **Numbering note.** The table is **not** in numeric order — facts 43-54 and
> 60-69 precede fact 26, because each milestone's block was appended where it
> was folded. Anchor any edit on row *content*, never on position. **Numbers
> 55-59 are unallocated**: M12 and M13 ran concurrently and were told to number
> from 50 and 60 respectively so their facts could not collide, and M12 needed
> only five. Nothing was deleted. **74-79 are unallocated for the same reason**:
> M14 took 70-73 and M15 was reserved from 80.
>
> **The convention now covers questions and discipline items too, because that
> is where it first failed.** M14 and M15 ran concurrently; facts were reserved
> (70+ and 80+) and did not collide, but **both proposed "question 19" and both
> proposed discipline items starting at 30**, because only the fact table had a
> reservation rule. M15's were renumbered to question 20 and discipline 31-34 on
> fold. **Give every concurrent milestone a reserved block in all three
> sequences**, and reconcile at the fold, never in the agent's own report.
>
> **Blocks currently reserved for work in flight** (89-139 will stay sparse):
> M16 facts 90+/discipline 40+, M17 facts 100+/discipline 50+, M18 facts
> 110+/discipline 60+, M19 facts 120+, M20's verifier facts 130+, **M23 facts
> 170+/discipline 80+/question 25+**, **M25 facts 190+/discipline 100+/question
> 30+**. Facts **140-145 (M20)**, **150-152 (M21)**,
> **160-162 (M22)**, **180-182 (M24)**, **200-203 (M26)**, **210-213 (M27)**, **220-225 (M28)**, **230-234 (M29)**, **240-243 (M30)**, **260-264 (M32)**, **270-274 (M33)**, **280-284 (M34)**, **300-304 (M35)**, **310-314 (M37)** and **320-324 (M38)** are folded below and are all
> **NOT INDEPENDENTLY VERIFIED** — they were measured by the
> orchestrator, and rule 12 binds their author exactly as it binds any milestone.
> **Facts 330-331 are M38's follow-on block** — the gate solve built on top of fact 324 —
> leaving **325-329 unallocated** so the milestone's original block stays contiguous.
> **Facts 285-297, disciplines 200-207 and questions 80-84 are M36-V**, the independent
> verification of M32-M34. The verifier proposed facts 290-302; 300-302 were taken, so the
> block shifted by −5 on fold and its internal cross-references shifted with it. It marks
> facts 261, 270, 280, 281 and 282 in place. **298-299 are unallocated.**
> **Facts 122-139 are M20-V** — the independent verification of the deconvolution-ceiling
> report. The verifier proposed 130-147; that collided with M20's own 140-145 because the
> orchestrator's brief named a start number without checking it, so the block was shifted
> by −8 on fold. **Disciplines 250-252 are the cross-milestone findings** M20-V, M31-V,
> M36-V and M39 share; they live in §5 with the other disciplines, are numbered outside
> every milestone block because none owns them, and are the most important things in this
> document. Note the two namespaces: **facts are `| N |` table rows in §4, disciplines are
> `N. **` list items in §5**, and the two numbering series are independent — facts 240-243
> (M30) and disciplines 240-242 (M39) coexist deliberately.
> **Facts 340-345, disciplines 240-242 and question 100 are M39**, the first independent
> verification since M2 — and the first block in the corpus whose author is *not* the
> orchestrator. It supersedes parts of 320 and 322 and opens question 100 against fact 19.
> **335-339 are unallocated.**
> The same reservation rule governs the other two sequences: **discipline 110-111
> (M26), 120-121 (M27), 130-131 (M28), 140-142 (M29), 150 (M30), 170 (M32), 180-181 (M33), 190-191 (M34), 210-211 (M35), 220-221 (M37), 230-231 (M38)** and **question 45 (M28),
> 50 (M29), 55 (M30), 65 (M32), 70 (M33), 75 (M34), 85 (M35), 90 (M37), 95 (M38)** are folded. M23's blocks (discipline 80+, question 25+) and
> M25's (discipline 100+, question 30+) remain unclaimed pending their reports;
> **facts 250+, discipline 160+ and question 60+ are reserved for M31**, the
> independent verification of M27-M30; **facts 290+, discipline 200+ and question
> 80+ are reserved for M36**, the independent verification of M32-M34; and
> **discipline 30-34 are already taken**
> by M15's renumbered items, so a new block must not start there.

| # | Fact | Consequence | Source |
|---|---|---|---|
| 1 | Inter-frame scale drift **-1.012%** over 33 frames, linear, ~42 px corner displacement | Translation-only alignment is dead on arrival | F (MEASURED) — **"linear" SUPERSEDED by M3**: a second stack gives -1.835%, and no low-order polynomial in frame index matches a direct per-frame fit |
| 2 | Reference stack is **in-camera focus bracketing, not a rail** (~85% conf.): `FocusPosition2` 56->57 matches the 0-1 ticks predicted from 2.03 mm travel; interval 0.6492 s +/- 0.0208 s | Frame-to-frame relation is **breathing (magnification)**, not parallax | F (MEASURED) |
| 3 | Homography residual identical to affine (1.45e-3) | No perspective signal. Use affine | F (MEASURED) — **SUPERSEDED by M3**: even affine is more than needed; a 4-parameter similarity is sufficient |
| 4 | Per-block correlation tracks the **migrating in-focus band**, not geometry — response collapses 0.68 -> 0.13 while ECC composes correctly over 16 chained steps | A block-matching aligner would be **silently wrong** | F (MEASURED) |
| 5 | Scale-centre amplification **1541x** per frame pair, 98x at full baseline. Corrected estimate x = -176 +/- 127 px, y = -338 +/- 61 px | Solve **one** centre per stack at full baseline, regularised toward image centre. Never profile it — the max-shrink axis sits 4-10 deg from the subject's depth-gradient axis, so it is subject-dependent | F (MEASURED) — **the centre estimate is REFUTED by M3**: (-22, -113) px. The "never profile it" conclusion stands |
| 6 | Laplacian winner-margin goes **negative** at sigma >= 0.01; ring-difference stays highest at every sigma | Do not use a Laplacian focus measure | B (MEASURED) |
| 7 | Argmax over N noise coefficients: 1.95x (N=10) -> 2.61x (N=60) | Selection is the defect. Gate on the noise floor | B (MEASURED) |
| 8 | PDAF: **0** candidate pixels over 5 frames; anomaly density at the noise floor | No PDAF mask, no PDAF depth cue | A + F (MEASURED, independently) |
| 9 | Sub-pixel *random* jitter **0.075 px** vs Wronski's >= 0.3 px gate | Classical multi-frame SR is off the table — **but see §6, breathing supplies structured diversity instead** | A (MEASURED) |
| 10 | H2D **56.9 GB/s**, D2D **1503 GB/s** measured locally; 66 MB frame transfers in 1.2 ms | PCIe is a non-issue. Do not build decode/compute overlap in v1 | D (MEASURED-LOCALLY) |
| 11 | Full budget 60x33 MP: **2.7-6.1 s**, decode-dominated | 15 s target has 2.5-5.5x margin | D (DERIVED) |
| 12 | A 2x teleconverter at m=2.8: **MTF@Nyquist = 0.000 at every aperture** — wide open is already N_eff 21.3, past the **N_eff 18.6** extinction point, where the diffraction cutoff `pitch/(lambda*N_eff)` falls to Nyquist | The tool should warn, and offer reduced-resolution output. **No longer hypothetical — see fact 26.** But the verdict turns on a magnification nobody has measured: at m=2.0 the same rig is at N_eff 16.8, just *inside* extinction. **M5 settled it (fact 27), and confirmed this row by direct measurement**: the `N_eff = 18.6` extinction point is reproduced to three digits from the measured cutoff, and the MTF@Nyquist row for m=2.00 (0.036 / 0.000 / 0.000 at f/5.6, f/8, f/11) is reproduced exactly. The warning stands | F (DERIVED) → **confirmed by M5 (MEASURED)** |
| 13 | The reference 33-frame stack is **2.4x oversampled**; 14 frames sufficed | A capture advisor is a real feature | F (DERIVED) |
| 14 | ISO 400 is a **second base ISO** (read noise 4.20 -> 1.47 e-); DR is higher than ISO 320. Usable white level **15360**, not 16383 | Camera plugin must expose `dominated_isos()` and the true white level | F (MEASURED) |
| 15 | Alignment costs **13-16 ms/frame**; 0.78-0.96 s for 60 frames, scalar CPU, all frames independent | Alignment is ~6% of a 15 s budget. The last unpinned budget term is pinned | M3 (MEASURED) |
| 16 | Composing 21 adjacent-pair fits underestimates total drift by **32%** — **25 px error at the sensor corner** — while each individual fit looks excellent (0.446 px residual) | **Never chain.** Always align to a fixed reference. The cause is pixel locking, a *systematic* bias that compounds, not a random walk | M3 (MEASURED) |
| 17 | Going from 4 to 12 motion parameters reduces the residual by **≤6%**, on filtered and unfiltered tile sets alike. Rotation ≤0.21 px at the corner | A **4-parameter similarity** is the whole model for in-camera bracketing. Keep rotation as a tripod-flex guard | M3 (MEASURED) |
| 18 | Residual after any global model is **0.6-1.3 px**, against a 0.19 px estimator floor, and richer geometry does not touch it | ~~Neither noise nor global model error. Candidates: depth-dependent magnification, or blur-induced correlation bias.~~ **RESOLVED by M6: it is blur-induced correlation bias (cause b).** In-focus tiles align at **0.144-0.172 px — at or below the estimator floor** — while far-from-focus tiles in *the same frame pairs* sit at 0.25-0.69 px. The gap survives within the same pair (**+0.667 px, p=0.010**) and within the same tile (**+0.460 to +0.599 px**), so it is not texture, contrast or field position. γ = **+0.0597 / +0.0452 px per frame of defocus mismatch**, against a real-data null of +0.000003 ± 0.000032. Cause (a)'s own signature (S2) is null on all three stacks (all p > 0.22) on a statistic that fires at ρ = −0.83 when (a) is planted | M3 (MEASURED fact), **cause MEASURED by M6** |
| 31 | **The defocus bias is symmetric peak *degradation*, not directed peak *displacement*.** M6's S6 asks whether the correlation peak is pushed in a preferred direction — the signature of a field-dependent asymmetric PSF. It is **null on all three stacks** (119MSDCF: **+0.0007 ± 0.0109**) against planted signals of ±0.039 to +0.077 that it recovers cleanly, and all three stacks match the *symmetric*-blur control column on S1, S2 and S6 while matching no other column | **This kills the last candidate for a lens plugin that is real code (§3.4.2).** The standing conditional was: *if* the residual is blur-induced, *then* a field-dependent defocus PSF is biasing the aligner and modelling it per lens is genuine per-lens computation. **The antecedent is true and the consequent is false** — the two halves come apart. **The lens profile stays a data file.** The fix belongs in the aligner and needs no lens identity at all: weight tiles by `\|c − w\|`, i.e. down-weight tiles far from their own best focus | M6 (MEASURED, with positive and null controls on the statistic itself) |
| 32 | **The halo is a property of the stack, not of the lens.** Corner halo runs **19.42 / 32.39 / 89.23 plane px** across the three stacks, tracking total drift (−1.029% / −1.835% / −4.575%), and grows **0.87 → 18.6 → 89.2 px** as N goes 5 → 20 → 100 on one stack. Correlation with radius from the scale centre is **Spearman ρ = 0.963-0.975** | **Kills a scalar `halo()`, but not for the reason §3.4.1 B1 gave.** Within-frame waste is only **1.34x** at 128 px — survivable. What is not survivable is that `halo() -> usize` is answered *once, without seeing the stack*, so it must be sized for the worst case and then costs **4.25x** and **3.48x** on the other two stacks. **B1's "39 px corner halo" was also wrong**: 39 px is the Euclidean *displacement*; a halo is a rectangle expansion, so `max(\|dx\|,\|dy\|)` = **32.39 px**, a 1.20x overstatement. The fix (`source_roi(out, &Warp)`) is unchanged and better justified | M6 (MEASURED; hand-checked independently) |
| 19 | A naive argmax stack of 22 frames is **1.253x noisier than one unstacked frame** on a flat ROI; **~1.48x** structure-corrected. On the same frames and ROI, a plain **mean gives 0.534x** and a placebo selector with the identical winner histogram gives **0.981x**. Present already at **N=3** (1.5 px drift), monotone in N | **The defect the project exists to remove is measured on our own files, and its cause is proven.** Drift and scene structure push the ratio *below* 1.0; only selection coupled to per-pixel noise pushes it above. The corpus's borrowed 1.82x is no longer load-bearing | M2 + M2-verification (MEASURED) |
| 20 | Winner-index speckle **34.4%**, against a no-information null of **53.5%** (i.i.d. draws from the observed winner histogram) and **0.868%** for a 17x17-regularised focus field. Still 21.7% in the busiest contrast decile | The winner map carries *some* spatial information but is nowhere near a depth map. **A fair upper bound on selector instability and nothing more** — it cannot separate "argmax elected noise" from "no frame is in focus here, so the error is harmless". Never quote it without the null | M2-verification (MEASURED) |
| 21 | Ring-difference focus + fold costs **~74% of decode** (196.8 vs 267.6 ms/frame), i.e. **42% of total CPU**, for the cheapest focus measure anyone would consider | Any budget treating focus measurement as negligible beside decode is wrong on this hardware. Fact 11's decode-dominated framing is too generous. *(M2 published "41% of decode" — a conflation of "% of decode" with "% of total"; corrected)* **The ratio survives M7; the inference drawn from it does not.** 196.8 ms/frame is per-frame **CPU time under 32-way concurrency**, not wall clock — the same work is 677 ms of wall for the whole 22-frame stack, and **4.1 ms on the GPU**. So fact 21 may not be used to size a GPU design or to justify a contribution format (fact 30) | M2-verification (MEASURED), scope corrected by M7 |
| 22 | Peak RSS is a function of **live concurrency, not of the plan**: `min(chunks, rayon pool) x per-worker`. At N=22 it is **833 MB at 1 thread, ~1.6 GB at 3, ~4.0 GB at default (32)**. On **105 real frames** it is **7.16 decimal GB**, against the planner's own 5.77 GB prediction. In-flight frames = `min(20, 32, N)` — O(workers), never O(N). Output byte-identical (SHA-256) across reduction trees and thread counts | **The architecture is right and the constant is not small.** O(workers) holds, but the planner licenses more workers than the 6 GiB budget can pay for, and **N=105 already sits at 89% of the 8 GB ratchet**. *(Both prior figures were configuration-specific and each was published as "the" peak: 4.12-4.20 GB and 1.81-1.94 GB. The latter is the `RAYON_NUM_THREADS=3` run. The earlier "far more headroom than published" reading is **inverted** — there is less.)* **This fact is also why the CI ratchet was respecified (§3.2.1).** **Two corrections from M8:** (i) the "**379 MB measured vs 321 MB modelled**" gap was **a unit mismatch** — 321 was decimal MB from `describe()`, 379 was MiB from PowerShell; the buffer model is 305.79 MiB = 320.6 decimal MB, so the real per-worker excess is **37.0 ± 5.4 MiB working set and 7.7 ± 6.6 MiB private commit, the latter consistent with zero**. M2's *ratios* survive because both sides were divided consistently. (ii) `peak_live` **exceeds** `min(chunks, pool)` in 8 of 108 runs, so the formula is a close model, not an identity | M2-rss-resolved (MEASURED, n=6 at N=22 + n=1 at N=105); **corrected by M8 (MEASURED)** |
| 33 | **Most of the planner's error was never decoder scratch — it is the reduce tree.** Peak resolves into **14.4 MiB floor + `live` x 342.8 ± 5.4 MiB + `⌈log₂ chunks⌉` x 110.04 MiB**. That third term is one whole `Selection` per level of rayon's `reduce_with` tree, and **110.04 MiB is exactly `px x 14`** — 8,241,504 plane px x (f32 focus + 5 x u16) — matching the struct to 0.1%. **550 MiB at 18 chunks, larger than all the decoder scratch put together.** Out-of-sample on a never-fitted stack: **8.4% mean, 17.5% max, +0.6% bias**, against run-to-run spread of up to 11.7%; the shipped `a + b·live` model gives 12.0% / 25.2% | **The gap was misattributed for two milestones.** A divide-and-conquer reduction keeps one accumulator alive per level of the tree, which is O(log N) memory nobody had costed. *(Verified independently from the struct definition and the plane geometry — 8,241,504 x 14 = 115,381,056 B = 110.036 MiB — without using M8's fit.)* **Consequence: the honest worker cap at the unchanged 6 GiB budget is 16, not 20** — N=22 → 11 chunks (unchanged), N=105 → 15 (was 18), N=220 → 16 (was 20); measured end-to-end **6909 → 5762 MiB**. **Adopted as the default** (question 13); `Buffers` stays reachable via `--memory-model buffers`, and output is byte-identical either way | M8 (MEASURED, k swept 0-32, R² = 0.99998) |
| 34 | **Decoder scratch is 39.36 ± 0.11 MiB private commit per concurrent decode** on 37.8 MiB ARWs and **32.34 ± 0.06 MiB** on 31.6 MiB ARWs. It is **file-size proportional** (slope 1.009 ± 0.015, intercept 0.685 ± 0.530 MiB, consistent with zero; a constant model has R² = 0), plus **1.51 ± 0.04 MiB per doubling of `RAYON_NUM_THREADS`** because the decoder is itself rayon-parallel (240.4 ms at 1 thread, 53.6 ms at 32). **Allocator retention is separate and bounded**: ≈2 MiB resting, ≤4.15 MiB added to peak, and **exactly flat (0.000 MiB) over decodes 40-104** | Scratch scales with concurrency; retention does not and does not leak. **Fitted over 17 points with all intercepts positive — M2's two-point negative-intercept trap explicitly avoided.** **Pixel-proportional vs constant remains UNVERIFIED**: `active_px` is 32,966,016 on every file available, so one body and one geometry cannot separate them | M8 (MEASURED) |
| 23 | Regularising the focus field (17x17 smooth) before argmax drops speckle **34.4% -> 0.868%** and noise **1.253x -> 1.075x** — **but 1.075x is still above 1.0.** Only averaging goes below one frame | **Direct measured support for §1.1(a), and a warning.** The architecture needs *both* halves: a regularised reference to stop the selector electing noise, **and** a noise-gated estimator that averages where frames agree. A better selector is not enough | M2-verification (MEASURED) |
| 24 | On high-detail ROIs a mean's sigma looks harmless (0.899x, 0.995x) while its mean gradient **collapses -58% and -53%**; argmax *raises* gradient | **Sigma alone cannot see detail destruction.** This is rule 9 working: the flat-ROI metric is valid precisely because its paired control fails as it should | M2-verification (MEASURED) |
| 25 | Argmax's noise excess is **spatially correlated over 3-7 px, not white** — and 3-7 px is exactly `focus.rs`'s own `INNER_RADIUS: 1` / `OUTER_RADIUS: 3` support | **The focus measure and the merge are coupled** — this stands. Also why high-pass views understate argmax damage while raw spatial sd overstates the ratio — ~1.48x is the honest figure between them. **But the inference drawn from it was wrong (M9).** The observation pairs the *inner* radius, which drives the effect, with the *outer* radius, which does not, and the coincidence made "put the support on the interface" look obvious. `ring(1,3)`'s focus-field autocorrelation length is **L(1/e) = 2 px**, shorter than its own 7 px outer box. **Not retracted — reinterpreted: the coupling is to φ (fact 35), and §3.4.1 B3 is rejected** | M2-verification (MEASURED); **interpretation corrected by M9** |
| 35 | **Argmax's noise excess tracks the focus operator's centre-tap sensitivity fraction φ, not its support.** ρ(φ, excess) = **+0.918 / +0.894** on two stacks (p < 0.0001); ρ(support radius, excess) = **−0.170 / −0.243**, not significant (p = 0.53 / 0.37). A 3x3 Sobel has a **zero centre tap** and shows **no excess: 0.9952x**. For a ring difference, **φ = 1/(2·(2·inner+1)²)** and **the outer radius cancels exactly** | **The mechanism is that a pixel's own noise votes for its own selection.** How far the operator reaches is irrelevant; how much of its answer comes from the pixel under test is everything. **This kills `support_px()` (§3.4.1 B3) and needs no replacement on the interface** — φ is framework-measurable by finite-differencing any contributed measure. *(The φ formula was re-derived by hand in exact rational arithmetic, independently of M9's harness.)* Among operators declaring **the same** `support_px()`, φ still spans **12.7x-321x** and excess spans **0.74 ratio units**, 37x the severity floor | M9 (MEASURED, 4 families x 4 support radii, two stacks) |
| 36 | **The flat-ROI noise ratio is monotone-decreasing then flat in regulariser width — there is no interior optimum.** 9 of 16 argmins sit at the sweep edge even after the sweep was extended to width 257. **And regularising can actively harm**: `ring(1,3)` scores **1.3625x at width 3** against **1.2527x unregularised** | **Any procedure that "tunes the regulariser width to minimise noise" is optimising a function with no minimum**, and will run to the widest width offered — which destroys focus selectivity. Width must be chosen against a *combined* objective, not against noise alone. **This also means B3's proposed property test — "assert the merge derives its width from the measure" — would have asserted a derivation with no well-defined target.** *Constructively repaired by fact 42: the objective is not broken, it was under-specified* | M9 (MEASURED) |
| 37 | **Operator choice alone cannot remove argmax's noise excess.** Across a 47-operator bake-off spanning φ from 0.0000 to 0.4778 and support radius 1 to 12, **no operator reaches the pre-registered noise-free bar of N ≤ 1.02x** on real data — the qualifying set was empty, **0 of 36** | Choosing well moves the excess from **1.35x to 1.05x**; it does not reach 1.00x. **This is the strongest direct evidence yet for §1's thesis:** the escape from selection's noise penalty is *estimation*, not a better selector. A project that only swapped in a better focus measure would capture most of the available gain and still be a selector | M11 (MEASURED, pre-registered outcome O4) |
| 38 | **A zero-centre-tap operator is noise-free and under-selective.** `tenengrad-w0-nonorm` and `brenner-sym-s2-w0-nonorm` measure **φ = 0.0000 exactly** and score Ncorr **0.9888x / 0.9966x** — no measurable excess, confirming fact 35's mechanism — but recover a planted focus surface at only **34-40% of the best operator's rate** | **Viable as a noise reference; not viable as a default.** M11 registered this as hypothesis H1 and refuted it with its own data. *(The 40.4% is M11's single-stack figure; pooling both stacks gives 33.7%, so the refutation is if anything stronger than published — verified independently)* | M11 (MEASURED, H1 refuted) |
| 39 | **Windowing and pointwise normalisation each re-introduce a centre tap, and roughly additively.** Against **φ = 0.000000** for a bare Sobel at `window = 0` and `Norm::None`: windowing alone (`tenengrad-w2-nonorm`) gives **0.0235**, normalisation alone (`tenengrad-w0`) gives **0.0321**, both together (`tenengrad-w2`) give **0.0568 ≈ their sum**. φ then grows monotonically with window: 0.032 → 0.057 → 0.066 → 0.084 → 0.105 across w0…w11 | **Zero centre tap is a property of the whole configured stage, not of the kernel.** *(Additivity and the monotone window series are my independent extensions.)* **Direct consequence for the plugin framework, easy to get wrong:** §3.4.1's replacement for B3 has the framework measure φ by finite-differencing a contributed measure. It must finite-difference the **complete configured stage, after windowing and normalisation** — probing the contributed kernel alone would report φ = 0 for Tenengrad and be wrong by construction | M11 amendment A1 (MEASURED); extensions VERIFIED independently |
| 40 | **The two axes are governed by different structural variables.** Over 36 operators: **φ predicts noise excess (ρ = +0.583) and not selectivity (ρ = −0.088); support radius predicts selectivity (ρ = +0.553) and not noise (ρ = −0.009)** | **This separation is why a Pareto front exists at all** — selectivity can be bought with support without paying in noise, provided centre-tap sensitivity is not bought along with it. **Fact 35 is scoped, not weakened.** M11 read its ρ = +0.583 as weakening M9's +0.918 / +0.894, but the two are measured over different populations and Spearman's ρ is not population-free. Restricting M11's set to the ring and `dsml` families M9 actually sampled gives **ρ = +0.783**, and the sequence is monotone in heterogeneity: **+0.918/+0.894** (designed crossed grid) → **+0.783** (comparable subset) → **+0.583** (heterogeneous 36). Fact 39 explains why: φ is not the same construct across M11's set. **What replicates unconditionally is the direction and the support null (−0.009, exact)** | M11 (MEASURED); **scoping correction VERIFIED independently** |
| 41 | **The ring difference is a poor focus measure and the shipped constants are among its worse settings.** `ring(1,3)` ranks **26-27th of 36**: N = **1.3475x**, selectivity **41-49%** of best. The best ring in a 7-configuration sweep, `ring(3,8)`, reaches only **58-60%**. **Tenengrad under an 11x11 box window** reaches **85-99%** at N = **1.1324x** for 7% more cost | **Re-tuning the ring radii cannot close the gap; the operator should be replaced.** Cost is near-irrelevant — M7 measured the whole fused focus+merge at 4.117 ms/22 frames, bandwidth-bound, so this stage is not the bottleneck. *(Ranges span M11's single-stack normalisation and my two-stack pooling; the **ordering is identical under both**, which is what the ruling rests on)* | M11 (MEASURED); ordering VERIFIED independently |
| 42 | **A joint selectivity/noise objective has an interior optimum in regulariser width; a noise-only objective does not.** Fact 36's boundary-running replicates for noise alone, but on a planted **tilted** depth surface (16-32 frames of depth across 256 px) selectivity peaks near **width 17** and declines by width 33. On a fronto-parallel surface it never turns over | **Tuning a regulariser on fronto-parallel test data will run to the sweep edge and destroy real depth structure.** This is the constructive repair of fact 36 — the objective was under-specified, not broken. **It also means any focus-stacking benchmark built on flat test targets is measuring the wrong thing:** the tilt is what makes the optimum exist | M11 (MEASURED) |
| 43 | **Short-baseline alignment edges under-report magnification change by ~3.2-3.5x.** On `coffee-bean`, telescoping span-1 edges total **−1.6876%** while span-16 edges total **−5.8891%**, and the ramp is monotone across 14 spans: −1.69, −2.08, −2.30, −2.41, −2.53, −2.83, −3.49, −4.35, −5.14, −5.89, then a plateau near −5.2 to −5.8. The identity `Σ log a` over any span must give the same total; it does not. 2.19x on 119MSDCF, 1.43x on 109MSDCF | **This is why chaining fails, and it is not what anyone assumed.** The failure is not accumulated *random* error — it is a **coherent** shrinkage, which is why composing 104 edges gives 40.3 px of corner error with **36.4 px of it in scale alone**. *(Reproduced independently from the raw edge CSV: span 1 = −1.6875%, span 16 = −5.8754% endpoint-normalised. The "3.33x" in M10's report is not derived from a stated rule — span16/span1 gives 3.49x, plateau-mean/span1 gives 3.25x; **quote the range, not the point**)* **— M12 RESCOPES THIS: the magnitude is not a constant of the optics.** "~3.2-3.5x" is `coffee-bean` **alone**. The corpus range is **1.03x to 3.26x**, and `112MSDCF`/`113MSDCF` show essentially **none** (1.048x / 1.027x) at a per-frame displacement matched to 0.3% and a window drift matched to 0.3%. The phenomenon is real, replicated on three of five stacks, and confirmed by an independent non-telescoping probe — but **its size is a per-stack artifact, not a calibration constant**. Same lesson as fact 48 and §4.1: measure it, never bake it | M10 (MEASURED); rescoped by M12 (MEASURED); both VERIFIED independently |
| 44 | **Long edges are the correct ones.** Where a trustworthy long anchor exists it agrees with the long-span ladder: 119MSDCF's ladder climbs −0.464 → −0.581 → −0.805 → −0.927 → **−1.022%** across spans 1→16 against a direct 0→32 edge of **−1.0185%** (78 tiles, rms 1.24); 109MSDCF's span-1 ladder reads −1.296% against a direct 0→21 edge of **−1.8544%** (61 tiles, rms 1.11) | **This fixes the *direction* of fact 43** — short edges are shrunk, long edges are right — which the conservation identity alone cannot do. *(Direct-anchor figures reproduced exactly. **But M10's "agrees to five significant figures" is circular and must not be quoted:** on a 33-frame stack the span-32 ladder **is** the single direct 0→32 edge, the same measurement reported twice. The real evidence is the **monotone convergence** across spans 1→16, which is genuine and which I reproduced)* | M10 (MEASURED); **corrected on verification** |
| 45 | **The shrinkage requires a real inter-frame content change and lives below ~0.5 px of differential displacement.** A resampler-free band-limited field recovers a planted magnification increment at ratio **1.008 / 0.991** at 0.12 / 0.24 px; the same increment planted on a *real defocus pair* recovers at **0.559 / 0.664**, IQRs disjoint. Above 0.48 px both are unbiased | **So it is neither the resampler nor the estimator's response to geometry** — the two explanations that would have made it an artifact. It needs real defocus change between the frames. Calling it "pixel locking amplified by the defocus step" stays **ARGUED**: a marginal-response model does not account for the ladder at spans 4-8. **Consequence: short baselines look *best* by tile residual while being *worst* by truth — never judge an edge by its residual** | M10 (MEASURED; mechanism ARGUED) — **CAUSAL READING WITHDRAWN by M23 (fact 174):** the numbers reproduce, the attribution to *defocus* does not — a zero-defocus self-pair on the same code reads **0.372**, *further* from unity than the real defocus pair (0.526), and a resampler-free field reads **0.965**. The mechanism is the plant's own bilinear resampler |
| 46 | **A global solve over direct edges covers a deep stack; a fixed reference does not.** On 105 frames a fixed reference places **76/105** (first failure at frame 73); a global least-squares solve over a sparse multiscale graph places **105/105 at 6.76 plane px** held-out, against the chain's **40.3 px**. On shallow stacks the same method reaches **0.58-0.67 px** and agrees with the known-good fixed reference to median 0.305 px (109) / 0.582 px (119) | **Risk 11 moves from open to bounded.** *(Every row of the ruling table reproduced to 3 decimals from the committed CSVs — 5.875 / 6.591 / 6.822 / 6.997 / 9.037 / 14.549 / 24.011 / 40.342 — and the 76/105 coverage and frame-73 first failure are exact)* | M10 (MEASURED); VERIFIED independently |
| 47 | **Deep-stack alignment error is set by the pairwise measurements, not the solver.** An in-sample solve that has *seen* the test edges reaches only **5.875 px** against the best out-of-sample **6.591 px**, and the raw edges' own cycle consistency is **6.83 px** at leg 8-15 and **13.03 px** at leg 32-104 | **Better solvers cannot help; better *edges* can.** This is what makes 6.76 px a floor rather than a tuning target, and it points all remaining effort at fact 43's shrinkage. It also means the parametric-model win is small — a degree-6 polynomial captures 96.7% of the 116 px corner motion and a straight line 93.9%, a ~6% gain that sits inside the noise | M10 (MEASURED) — **BOUNDED FROM A SECOND SIDE by M23:** the short edges cannot be rescued by per-edge response calibration either — held-out is **6.758 px unchanged**, and the winning training set still contains no corrected edge |
| 48 | **The scale centre is not a constant of the optics.** Fitted per stack: 109MSDCF **(−27, −131)** sensor px — independently corroborating M3's **(−22, −113)** from a different estimator path — but coffee-bean **(+425, −449)** and 119MSDCF **(−106, −378)** | **One centre per stack survives the falsifier; one centre per rig does not.** So the scale centre must be **fitted at runtime and never baked** — which is what project rule 5 already says, now with a measured reason rather than a cautious one. Another instance of §4.1: this is an *artifact of the capture*, not a calibration constant of the lens | M10 (MEASURED) |
| 49 | **The corpus doubled, and the obvious prize in it is the wrong one.** `D:\personal\macro` holds seven stacks; three (`109MSDCF`, `119MSDCF`, `coffee-bean`) are **byte-identical duplicates** of the existing corpus, verified by count, total size and MD5. The four new ones, all on the same rig (`LensType3` 33094): **`112MSDCF` 79 frames** and **`113MSDCF` 63 frames**, both sweeping **0.3189 → 0.3297 m** at 0.51 s/frame — **but see fact 50: that reading decodes `FocusPosition2`, which takes only 3 distinct values across both stacks, and it is WRONG**; **`foam` 100 frames**, 0.2707 → 0.2841 m but at **2.52 s/frame over 249 s**; **`coffee-bubbles` 19 frames at *constant* focus** (0.2841 → 0.2841 m) over 60 s. Preview-NCC on 128×96 normalised luma: **112 vs 113 = +0.9961** (same subject, same framing), while **`foam` decorrelates *within itself* to 0.087 / 0.122 / 0.243** first-vs-mid-vs-last | **`foam` is not a second deep stack, and the control is what proves it.** Deep sweeping alone does not decorrelate a preview: `coffee-bean`, also ~100 frames and a genuine deep sweep, holds **0.979 / 0.941 / 0.970** on the identical statistic, and `119MSDCF` holds 0.999. `foam` is an order of magnitude below its own control, so **the scene changed** — foam drains and coalesces over four minutes — and it violates the rigid-scene assumption every alignment result depends on. **The real prize is the `112`/`113` pair**: two independent captures of one static subject over an identical focus range, which is exactly the out-of-sample structure M10 said it lacked when it declined to fit the span-dependent shrinkage correction (fact 43). `coffee-bubbles`, at fixed focus, is a *near*-null for the aligner — any transform it reports is drift or bias, not parallax — but it is contaminated by real bubble motion (0.947 first-to-last), so it is a soft null, not a clean one | MEASURED-LOCALLY (exiftool + preview NCC, with `coffee-bean`/`119MSDCF` as the deep-sweep control) **— PARTIALLY CORRECTED by M12 (fact 50): the "same focus range, two densities" reading is false.** Measured two independent ways. *By magnification:* `rate(112)/rate(113) = 1.0044` where that reading requires 0.7949, and `total(112)/total(113) = 1.2442` where it requires 1.0000. *From the focus band in the pixels*, with no metadata and no distance-map assumption: the tile-wise focus-index slope is **0.9867 ± 0.0078**, **1.7 σ** from a shared step and **34.7 σ** from a shared interval, and 113 covers only 112's frames **5.5 → 66.6 of 0 → 78**. They share a per-frame step; 112 simply runs 16 frames further. **The pair is still a genuine same-subject replicate — it is not the index-vs-baseline discriminator it was recruited as** |
| 50 | **`112MSDCF` and `113MSDCF` share a per-frame focus step, not a focus interval — measured two independent ways.** *(a) By magnification:* per-frame rates **−0.4846e-3** and **−0.4825e-3** (ratio **1.0044**), totals **−3.7448%** and **−3.0210%** (ratio **1.2442**); the `wide64` config agrees (1.0225 / 1.2584). *(b) From the focus band itself,* via a per-tile sharpness peak over 693 tiles with no metadata and no distance-map assumption: `p_112 = α + β·p_113` gives **β = 0.9867 ± 0.0078**, α = **+5.461** frames. A shared interval at two densities requires β = 1.2581; a shared step with 112 running 16 frames further requires 1.0000. β is **1.7 σ from the latter and 34.7 σ from the former**. Corroborated by disjoint observables: α from the focus regression (5.461) against α from a direct 112↔113 frame-0 similarity fit (5.552) agree to **0.09 frames** | **Corrects fact 49 and removes the discriminator it promised.** Span `s` is the same physical baseline in both stacks, so index-span and physical-baseline parameterisations make identical predictions here and cannot be separated by this pair. It remains a valid same-subject *replicate*, which is what made fact 52's stability result possible. **General lesson: `FocusPosition2` is a coarse encoder — never infer a fine sweep from it; measure the sweep from the pixels** | M12 (MEASURED) |
| 51 | **The shrinkage does not replicate on the new stacks, and it is not a function of baseline in any parameterisation.** `1/S_W(1)` = **3.260** (`coffee-bean`), 2.199 (`119`), 1.318 (`109`), **1.048** (`112`), **1.027** (`113`). The decisive pair: `coffee-bean` at d = 1.081 px/frame gives S = 0.3067; `112MSDCF` at d = 1.077 px/frame gives S = 0.9541 — **displacement matched to 0.3%, shrinkage differing 3.11×**, at matched per-frame rate and matched window drift. Chaining all 78 adjacent edges on 112 recovers **99.0%** of the direct `(0,78)` edge, and 113 recovers 97.5% over 62, where `coffee-bean` recovers ~30% | **Both candidate parameterisations are refuted** — not frame-index span (S at s=1 ranges 0.307→0.974), not physical baseline or differential displacement (matched d, 3.11× different S). Across stacks the shrinkage is a function of the **scene**. **VERIFIED independently, and more strongly than published:** recomputing `1/S` over *every* width-48 window at every offset gives **completely disjoint** ranges — coffee-bean **[2.573, 3.222]** over 48 windows against 112MSDCF **[0.960, 1.038]** over 31. No choice of window could reverse the conclusion, and a rival "displacement threshold" explanation dies here: at a matched 1.06 px/frame, coffee-bean still shrinks 2.79× and 112 does not shrink at all | M12 (MEASURED); VERIFIED independently |
| 52 | **The shrinkage is stable within a scene and does not transfer between scenes.** Two independent captures of the same subject agree to **0.15 σ_w** (0.9734 vs 0.9659, σ_w = 0.0510 from disjoint within-capture windows) — even a full stop apart in exposure. But a correction `k = 1/S_W(1)` fitted on one stack and tested on another's disjoint edges passes both registered conditions on **0 of 18** cross-scene ordered pairs; `coffee-bean → 113MSDCF` makes the error **83.4× worse**. On a real chain an **oracle in-sample** correction takes `coffee-bean` from 36.99 px to **13.92 px** — still 2.06× worse than the 6.76 px global solve — and on `112MSDCF` a self-fitted correction makes the worst case *worse* (5.27 → 5.66 px) | **This closes fact 43's open question: no.** Measurable and stable is not the same as transferable, and **the case the project would actually ship — fit on the deep stack you have, apply to the next capture — is the catastrophic one.** The stability result is what makes this damning rather than merely inconclusive: the quantity is real, reproducible, and still useless as a correction. **The useful residue is diagnostic**, separating chainable stacks from unchainable ones | M12 (MEASURED) — **BROADENED by M23 (fact 175):** a *per-edge* correction reduces in measurement to that same scalar — shuffled `R` reproduces 93.3% of its movement and a constant median `R` 93.5% — so M12's refutation is not merely a transfer failure |
| 53 | **Nothing measurable in the edge sets predicts which stacks shrink.** Ten candidate predictors over five stacks, best Spearman \|ρ\| = 0.600 at n = 5. The two natural stories each die on a single row: *"noisier ⇒ more shrinkage"* is killed by `119MSDCF`, which has the corpus's **lowest** span-1 rms (0.172) and still shrinks 2.20×; *"less inter-frame correlation ⇒ more shrinkage"* has the **wrong sign**, since `113MSDCF` has the **highest** span-1 NCC peak (0.9737) and the least shrinkage. An independent non-telescoping probe — a known increment planted on one real defocus pair, no anchor and no chain — orders all four tested stacks **identically** to the ladder | **The mechanism stays UNVERIFIED, and the corroboration is real because the probes are independent.** Fact 45's "requires a real inter-frame content change" survives, but its *quantitative* signature is `coffee-bean`-specific exactly as fact 43's magnitude is. Naming the responsible scene property needs a corpus larger than five stacks with deliberate variation in subject depth and texture — **that is a capture request, not an analysis** | M12 (MEASURED; mechanism UNVERIFIED) |
| 54 | **Per-frame focus position is not in EXIF, but it is measurable from the pixels to ~0.01 frames of slope.** `FocusPosition2` is 8-bit and takes **3 values across a 79-frame sweep**; `FocusPosition` is absent; `FocusLocation` is an AF rectangle. The substitute is a **focus index**: per scene tile, the parabola-interpolated frame at which a mean-normalised sharpness measure peaks. Mean normalisation is mandatory (112 and 113 differ by a full stop). Tile centres round to integer pixels, so **no resampler is involved**. Because the depth→focus map belongs to the *subject*, it **cancels** in a tile-wise regression between two captures of the same scene — including a nonlinear motor-unit-to-distance map. Measured: 93.1% tile acceptance on real data against **0%** on a synthetic stack with planted magnification and no focus change, split-half σ_β = 0.0078, agreement across two independent sharpness measures to 0.0028, and known-answer recovery of 2.0061 and 0.9877 against truths of 2.0 and 1.0 | **The project can measure focus geometry directly instead of trusting metadata**, which it needs for depth-map work, step validation, and any comparison of two sweeps. Also a standing caution: **any figure computed as `span/(n−1)` is DERIVED-UNDER-ASSUMPTION** — it presupposes uniform stepping, and its ratio between two stacks is then an arithmetic identity equal to the inverse frame-count ratio, not evidence. *(The orchestrator made exactly this error in briefing M12 and retracted it mid-run.)* | M12 (MEASURED) |
| 60 | **The focus-measure window optimum is at radius 13 — a 27x27 box — for Tenengrad.** Measured by regret against the per-cell best over **36 cells** (2 stacks x 3 occluding-edge geometries x 6 depth steps x 20 windows x 3 noise seeds; 7,200 measurements), `regret(w,cell) = E_excess(w,cell) − min_w' E_excess(w',cell)`. Argmin of **both** mean regret (3.171 DN) and worst-case regret (12.111 DN), and argmin **independently in each of the three noise seeds** on both objectives. The basin **w11–w15** (23x23 to 31x31) is flat to 0.87 DN against a seed noise floor of 0.193 DN. Getting it wrong is expensive: w40 costs 12x the mean regret, M11's w5 costs 5.5x | **Use a 27x27 box.** Read it as a basin, not a point: the sampled ladder omits w14 and w16, so w13 is not distinguishable from its immediate neighbours, and §3.4 shows a few window steps of genuine scene dependence. **Scope: every one of the 7,200 measurements is at regulariser `width=1`** — see question 17 | M13 (MEASURED) — **VERIFIED**: orchestrator reproduced the argmin structure, both regret aggregates and the full 20-point ladder exactly from the committed CSVs with independently written code |
| 61 | **The optimum exists only because of depth *discontinuity*.** On the same 36-cell grid the **6 cells with zero depth step** put their argmin at the sweep **endpoint** (w40, an 81x81 box) at regret 0.000 DN — no interior optimum at all. The **30 cells with a non-zero step** all have interior argmins. This is the null/positive pair for the whole question, and it holds under three independent objectives (`E_excess` → w13, `mis_width` → w23, `dmae_band` → w15). A **2-frame** step is already enough to move the argmin off the endpoint | **Sharpens fact 42**: depth *structure* is not sufficient — it must be discontinuous. Any future sweep of a spatial-support parameter must plant a discontinuity or it will return the endpoint by construction | M13 (MEASURED) — **VERIFIED** independently by the orchestrator, both aggregates |
| 62 | **A fronto-parallel plant cannot turn over.** Exact-hit accuracy and mean frame error both improve monotonically w0→w40 (0.3128→0.9946 and 6.04→0.064 frames). A symmetric box mean of a *constant* is unbiased, so every extra tap is pure variance reduction and there is nothing to smear | **M11's A4 amendment was measured on exactly this configuration.** Its "still improving at 23x23" is therefore not weak evidence of an optimum past 23x23 — it is **no** evidence, because that plant could not have produced any other result | M13 (MEASURED + ARGUED) — **VERIFIED**: all 16 published values reproduce exactly (mean over ROIs, then over stacks) |
| 63 | **A linear depth ramp is nearly as uninformative.** Under tilt, exact-hit accuracy turns over (argmax w33/w18/w11/w8 at tilt 4/8/16/32 DN-frames/px) but mean frame error does **not** — its argmin is the w40 endpoint at *every* tilt. A symmetric box mean of a *linear* ramp is also unbiased | Reporting either axis alone would have produced a confident wrong answer in **either** direction. A ramp is the friendliest possible non-flat plant for a box window, which is why it cannot settle the question | M13 (MEASURED) |
| 64 | **M11's per-pixel selectivity metric is structurally blind to occlusion halo.** In **30 of 30** depth-step cells the window chosen by per-pixel exact-hit accuracy is **strictly wider** than the window chosen by reconstruction error; strictly narrower in **0 of 30**. Mean penalty for following accuracy **18.48 DN**, worst **101.35 DN**. On 109MSDCF/vertical/step 32, accuracy climbs monotonically to 0.967 at w40 while `E_excess` is **66% worse** than at its optimum. Restricting accuracy to the boundary band helps but does not fix it | **This is why M11 picked a window less than half the right size** — not an arithmetic slip but a metric that cannot see the failure. The damage concentrates in a band that is a small fraction of the ROI by area, so a per-pixel ROI average barely moves. Any future focus-measure metric must include an edge-referenced term | M13 (MEASURED) — **VERIFIED**: 30/30, 18.48 and 101.35 all reproduce exactly |
| 65 | **`tenengrad-w5` (11x11) is dominated, not merely a lower bound.** `tenengrad-w8` (17x17) beats it in **36 of 36** edge cells at lower merged noise (N 1.1019 vs 1.1324) and identical cost. It is not a near-tie anywhere: w8's **smallest margin of victory is 2.894 DN** (median 7.52, max 25.39). The recommended `tenengrad-w13` beats w5 in **33 of 36** — all three losses fall in the single 119MSDCF-horizontal cell — but its worst-case regret is 12.1 DN against w5's 64.5 DN | **M11's window ruling is superseded; its operator ruling stands untouched.** If a zero-risk upgrade is wanted over an argmin, w8 is strictly dominating; w13 is better on every aggregate and loses three head-to-heads in one anomalous cell | M13 (MEASURED) — **VERIFIED**; the margin distribution is an orchestrator strengthening M13 did not report (it published the loss as 0.00 DN, which is true but reads as a tie) |
| 66 | **Focus-operator cost is flat in the window radius.** Spread over w1–w40 is **2.53%** with no trend in radius — the extremes sit at w18 and w9, not at the ends — exactly as a running-sum box filter must behave: **O(1) per pixel independent of radius**. Widening w5→w13 costs **+0.00%** (3.3805→3.3806 ms/frame/Mpx). `w0` is cheaper (1.924) only because it skips the box entirely | **A wide window is free, so the window choice is a pure quality decision.** The box filter **must** be the running-sum form — a naive (2w+1)² convolution at radius 13 would be ~841x the work. Absolute ms/frame/Mpx here are **not** comparable to M11's table: the harnesses time different work, scales differ ~1.9x, unreconciled | M13 (MEASURED) — **VERIFIED**: 2.53%, the w18/w9 extremes, the +1.49% w5-vs-ring gap and the w5/w13 flatness all reproduce exactly. **Re-confirmed on the shipped path (M14)**: I ran it and read **0.11%** over w1→w13, the range the milestone actually moves through, and 3.3012 ms/frame/Mpx for `FocusField::compute`. The *spread* figure is not stable run to run (M14 reported 1.28%/argmin w30, I measured 0.69%/argmin w40) — which is itself the finding: the effect is smaller than the timing noise, so "flat" is the robust claim and any point value must be quoted as a range |
| 67 | **Spatial adaptivity has real headroom that no realisable rule reached.** A per-pixel oracle choosing between a narrow and a wide window gains **5.7–46.8%** of band RMS over the better fixed window across the 24 configurations containing a discontinuity. The realisable disagreement gate (narrow where the two windows disagree by more than τ frames, τ ∈ 1..8) gains at most **+5.4%**, is negative in **18 of 30**, and reaches **−153.6%**. Making the selection worse is its typical behaviour, not a rare failure | **Ship a single global window.** Adaptivity is *unrealised*, not rejected — the headroom is larger than the entire w5→w13 improvement, so it is worth more than further window tuning. Becomes question 16 | M13 (MEASURED) |
| 68 | **CORRECTION to M11 A1: φ does not rise monotonically with window.** Under pointwise normalisation on real texture φ peaks at **w15–w17** (0.1474) and declines to 0.1146 by w40 — argmax at w17 at all three probe amplitudes (δ = 1, 8, 32 DN). It is also non-monotone at *small* w: it spikes at w1 (0.0882), dips to a local minimum at w3 (0.0631), then rises. A1's five values are **correct** and reproduce to ±5e-5. Under `Norm::None`, φ falls monotonically toward the analytic dilution law **1/(2w+1)²**, ratio 0.62 (w1) → 0.978 (w40), and is **exactly 0** at w0 | The monotonicity claim was extrapolation past the data at one end and interpolation across an unsampled dip at the other — **the same error class as A4**. The rise M11 saw belongs to the *pointwise normaliser's* own 1-px centre tap, not to windowing. Consequence for the pinned test: **φ under normalisation is texture-dependent and must not be pinned to 4 dp**, unlike `ring(1,3)`'s 1/18 which is a property of the kernel alone | M13 (MEASURED) — **VERIFIED**: φ_nonorm(w0) = 0 is *derived* independently (Sobel's centre weight is 0 in both kernels, so a centre perturbation cannot change the response at that pixel), and the turnover, the dip and the ratio ladder all reproduce |
| 69 | **`C:\dev\macro\test\119MSDCF` and `D:\personal\macro\119MSDCF` are the same 33 frames.** A full edge sweep run against each produced a **byte-identical** CSV (sha256 `F076E402…D11798`) | The `D:` tree is a **mirror, not an independent sample**. Two stacks must mean two *different* stacks — use 109/119 or 112/113, never a directory and its mirror. Extends fact 49's duplicate audit from file hashes to measurement output | M13 (MEASURED) |
| 70 | **The operator M11 benchmarked as `tenengrad-w{N}` is the gradient MAGNITUDE, not the squared "energy" the literature name implies.** In `m11-focus-bakeoff/src/measures.rs` it registers as `Kind::Tenengrad { squared: false }`, `Norm::Pointwise`, `degree = 1`, and the CSV carries `norm=sigma, degree=1` on every row. The squared arm exists but is a **separate** measure, `tenengrad-sq-w2` | **Shipping the textbook "Tenengrad" would have shipped an operator nobody benchmarked**, inheriting M11's and M13's evidence under a name that did not earn it. Every `sqrt` in the shipped path is load-bearing. The pipeline spec in §3.3 said "gradient energy" and was **wrong**; it is corrected | M14 (MEASURED) — **VERIFIED**: I read `measures.rs:653-674` myself, and independently recomputed M11's published N from M11's own CSVs (median over flat ROIs, then mean over stacks): `ring-1-3` → **1.3475**, `tenengrad-w5` → **1.1324**, both exact to 4 dp |
| 71 | **The shipped CLI reproduces M13's separately-written harness to every printed digit.** On 109MSDCF at M2's flat ROI: stacked σ **30.114** DN vs M13's 30.1138, single-frame σ **28.201** vs 28.2007, ratio **1.068x** vs 1.067839, **6** distinct winners vs 6. Against the retired ring on the same ROI: ratio 1.253x → 1.068x, distinct winners 22 → 6, index speckle **34.381% → 1.010%** | **Two independently written implementations, in different crates, agree.** This is the cross-check that distinguishes "the operator is right" from "one harness is self-consistent". The 34x speckle collapse is the merge electing 34x less of its own noise | M14 (MEASURED) — **VERIFIED**: I ran `strehl stack` myself on 109MSDCF and read 30.114 / 28.201 / 1.068x / 6 / 1.010% off the shipped binary, then read 1.067839 / 30.1138 / 6 out of M13's committed CSV. Not circular — M13's CSV predates M14 and was produced by a different codebase |
| 72 | **φ under pointwise normalisation is a property of the SCENE, not the operator: it spans 47x (0.0085 → 0.3987) over a 64x texture-amplitude range while the operator does not change at all.** Landing inside M13 §6.4's proposed `0.10 < φ < 0.18` bracket requires a texture amplitude near 330 DN | **M13 §6.4's bracket was a plant in disguise** and asserting it would have pinned one ROI — the exact failure M13 itself warned against. What is pinned instead is what is analytic: **841 taps** (`(2·(1+13)+1)²`), `φ_nonorm(w0) = 0`, `φ_nonorm(w13)/(1/729) ∈ (0.88, 1.00)`, plus the two structural relations φ *does* obey (divisor dominates the centre tap; φ tracks contrast) | M14 (MEASURED) — **VERIFIED**: the rising trend is *derivable* — the gradient path's centre sensitivity is scale-free in contrast while the divisor path's scales with it, so φ → 1 as amplitude grows. Mechanism and measurement agree |
| 73 | **The shipped 27x27 operator has EXACTLY ZERO focus discrimination on an untextured monotone edge.** Sobel magnitude under a radius-13 box reads **37.037037** on a step blurred at σ = 0, 1, 2 **and** 3 — identical to 8 significant figures. Cause: mean \|∇\| over a window wider than the blur is total variation ÷ area, and blur **conserves** TV on a monotone edge. Radius 1 discriminates the same pair at **0.376**, radius 3 at 0.747, radius 13 at **1.0000**. Positive control on broadband texture: 45.13 → 28.88 → 13.64 → 6.90 → 2.24 across the same blur ladder | **A blind spot that no prior measurement covers, and the cost of the w13 decision that M13 could not see** — M13's edge plant is a *textured* occlusion boundary (`build_edge_textures` extracts real tiles), so the texture always carried the focus signal. Smooth gradients are common in macro: specular falloff on a carapace, a defocused background, a petal edge. **Design consequence: confidence must be derived from cross-frame spread in the focus volume, never from focus magnitude** — here the magnitude is *large* (37.04, comparable to sharp texture's 45.13) while the discriminating information is exactly zero. Opens question 19 | ORCHESTRATOR (MEASURED + DERIVED) — mine, not M14's. M14 found the mechanism while diagnosing why an old test was unpassable and reported it as a note about a test; it is a property of the operator it shipped. Reproduced independently in `tvcheck.py` with a null (step) and a positive control (texture) |
| 80 | **The focus-window optimum does not move under the merge regulariser.** Over 30 occluding-edge cells the window argmin is **13 or 14 — always `interior`, never an endpoint — at every regulariser width from 1 to 33** (and w8 only at the degenerate g=49, which is 4x worse overall) | **Question 17 is closed and M13's w13 stands unchanged.** My own hypothesis — that a 27x27 box and the regulariser are substitutes, so the true window might be ~1.5x too wide — is **REFUTED on the aggregate**. The last recommendation-moving caveat on the window is discharged | M15 (MEASURED) — **VERIFIED**: I recomputed the whole argmin sequence `13,14,13,13,14,14,13,14,8` from M15's committed CSVs with independently written code. Exact |
| 81 | **Shipping w13 rather than the per-width optimum costs 0.000–0.121 DN over regulariser widths 1–33**, and **0.050 DN** at the reference width 17, against M13's pre-registered 0.87 DN threshold and its w11–w15 basin flatness | w13 survives everywhere the project would actually operate. The cost never approaches the threshold at any width | M15 (MEASURED) — **VERIFIED**: all **9 of 9** values reproduce (0.0000/0.0330/0.0000/0.0000/0.0797/0.0504/0.0000/0.1205/0.5513). The quantity is `regret(w13) − regret(w*)`, *not* the absolute regret level, which is ~3.0–3.4 DN |
| 82 | **The window and the regulariser substitute only where the window's job is variance reduction.** On zero-step cells the optimal window narrows at **1.72 window-radius units per regulariser-radius unit (r² = 0.94)**; on cells carrying a depth discontinuity the rate is **−0.03 (r² = 0.10)** — no substitution at all | **This is what makes the null interpretable.** At an occluding boundary the window buys *contrast localisation*, which the regulariser cannot supply because it acts **after** the per-frame focus field is formed. The two are not redundant where the decision is actually made | M15 (MEASURED + ARGUED) — **VERIFIED**: I re-fitted both OLS slopes and got **−1.72 / r² 0.94** and **+0.03 / r² 0.10**. **Sign convention**: M15 quotes a *substitution rate* (positive = the regulariser replaces window), which is the negation of the raw slope of w\* on regulariser radius `(g−1)/2`. Both agree under that convention |
| 83 | **A flat aggregate optimum can be a cancellation, not an absence of movement.** Between regulariser width 1 and 17 the `horizontal` edge cells move narrower **10 of 10** (median −2.5) while `vertical` moves wider **6 of 10** (median +1.5) and `bar` moves wider **6 of 10** (median +1.0); the aggregate median shift is **0** | Reporting only the aggregate would have hidden a real, unanimous, orientation-dependent effect. It also doubles as the **positive control that the design can resolve a moving optimum** — which is what licenses reading fact 80's flatness as a null rather than as an insensitive instrument | M15 (MEASURED) — **VERIFIED**: 10/10, 6/10 and the medians all reproduce. **CORRECTION to M15's framing**: it presents this as horizontal-vs-vertical, but `bar` (a third of the cells) moves *with* vertical. The accurate statement is **`horizontal` is the outlier**, not that the two named geometries oppose each other |
| 84 | **The merge regulariser at width 17 cuts w13's absolute reconstruction error by 35%** (24.79 → 15.99 DN mean over the 30 occluding-edge cells) and the seed noise floor by 33% (0.228 → 0.153 DN) | **A larger gain than the entire window axis provides**, and `strehl stack` does **not** regularise yet — so this is the single largest measured quality win still unbuilt. Fact 80 is therefore a *forward* guarantee: the window will not need revisiting when the regulariser ships | M15 (MEASURED) — **VERIFIED**: 24.7914 → 15.9939, **35.5%**, over 30 cells |
| 85 | **Fact 61 survives the regulariser as a plateau, not a turnover.** Above regulariser width 9 the zero-step argmin is nominally `interior` (w33/w26/w20/w16/w10), but the w40 **endpoint's regret is 0.0000–0.0003 DN** — two orders of magnitude below a 3σ seed bar | The *label* broke, the *finding* did not: on a fronto-parallel plant, wider stops paying but never starts hurting. Reporting the label alone would have manufactured a turnover that is not there | M15 (MEASURED, self-corrected) — **VERIFIED**: my null-stratum table reproduces both the labels and the ≤0.0003 DN endpoint regret |
| 86 | **The merge regulariser at width 3 is worse than no regulariser at all on merged noise.** `ring-1-3` N *rises* 1.2773 → 1.3856 (109MSDCF) and 1.4177 → 1.4785 (119MSDCF) before falling monotonically to ~1.07/1.08 | **Independently reproduces fact 36 on a different measure and a different harness, unregistered.** A narrow regulariser correlates neighbouring selections without averaging enough of them to pay for it | M15 (MEASURED) — **VERIFIED**: both rises and the subsequent monotone fall reproduce exactly from M15's committed noise CSVs |
| 87 | **M13's w13 is an aggregate over cells whose own optima span w8–w33**, the `vertical` geometry's median sitting at w17 against w10.5 for `bar` and `horizontal`. M13's ladder also omits w14 and w16, which concealed a ≤0.121 DN one-rung movement | The recommendation is correct as published but is a *central tendency*, not a per-cell truth. This is the measurement behind question 16's adaptivity headroom, seen from a different direction | M15 (MEASURED, from M13's own committed bytes) |
| 88 | **The "flat ROI ≈ 28–30 DN `single_sigma`" discriminator is 109MSDCF-specific.** M11's committed data puts 119MSDCF's four flat ROIs at **43.2 / 49.0 / 50.8 / 53.1 DN**; applying 109's band to 119 rejects **all four correct ROIs** | **This was a live trap in `AGENTS.md`**, where it was written as general guidance for anyone reusing a harness; it is now corrected in place. Separate flat from detail *within* a stack; never carry an absolute threshold across stacks | M15 (MEASURED) — **ADVICE SURVIVES, MECHANISM REFUTED by M20-V** (fact 130): 43.2–53.1 DN is *impossible* as temporal σ at ISO 50, where the project's own model caps it at 22.9 DN. Those are spatial sds containing subject structure, so the ROIs were not flat — which strengthens the advice and destroys the stated reason. **119 is *less* relatively noisy than 109, not more** |
| 90 | The occluding-edge orientation asymmetry of fact 83 is a property of the corpus subjects, not of the merge, the focus operator or the `\|d\| ≤ 24` band. Transposing the plant's textures 90° while holding every piece of machinery fixed transposes the asymmetry exactly: median \|shift(rotated geometry) − shift(control)\| = **0.0 windows**, against **8.0** for the same geometry. | Fact 83 is not a defect and there is no code change that removes it. Question 20 is closed. | M16 (MEASURED — M16 §6.2, arms A6/A8, 30 cells, `data/A{6,8}-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 91 | Making the corpus texture exactly transpose-invariant (`T ← (T + Tᵀ)/2`, which forces `Σgx² = Σgy²` identically) removes the asymmetry completely: median `w*(1)` goes from 8.0 `horizontal` vs 20.0 `vertical` to **8.0 vs 8.0**, and `A_hv` from −7.5 to **+0.0** windows against a leave-one-seed-out floor of 1.0. | An isotropy intervention on the *scene*, with the machinery untouched, is sufficient to null the effect. Nothing is left for a machinery defect to explain. | M16 (MEASURED — M16 §6.3, arms A6/A11, `data/A11-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 92 | Mechanism: a horizontal edge is localised by `Gy` and a vertical edge by `Gx`, and the corpus's far-field texture carries **14–22× more vertical gradient energy than horizontal** (`gx²/gy²` = 0.046–0.073; near-field 0.198–0.294). | The horizontal edge is handed 14–22× more gradient signal, needs less spatial averaging and settles on a much smaller focus window — median `w*(1)` 9.0 against 17.0. Any future corpus with different lineation will move these window numbers. | M16 (MEASURED — M16 §3.2/§6.3, `data/fpnscan-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 93 | The sensor's fixed pattern is **isotropic at every measured ISO**: master-bias `gx²/gy²` = **0.968–0.999** across all 11 dark ISO groups (50–2000), 20 frames each, against a scaled split-half null. | Row-banded FPN is not a mechanism this sensor makes available. Any future proposal resting on row/column FPN asymmetry must first move this number. | M16 (MEASURED — M16 §3.1, `data/darkfpn.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 94 | The row-correlated component of the sensor's fixed pattern is **0.0036–0.0136 DN** at the corpus ISOs (50 and 160) — about **0.3 % of fixed-pattern variance** — against **11.8–51.4 DN** of row-marginal structure in the texture tiles the harness uses. A ratio of ~10³. | The row structure in the corpus tiles is scene, not sensor, by three orders of magnitude. | M16 (MEASURED — M16 §3.1/§3.2, `data/darkfpn.csv`, `data/fpnscan-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 95 | Per-frame row/column mean subtraction removes **44–99 % of a corpus tile's total variance** while moving `gx²` by only **3–17 %** and leaving `gx²/gy²` still 2–10× from isotropic. | Destriping cannot correct a Sobel-scale directional bias. The focus operator is a high-pass and never used the component the treatment removes. A destripe arm therefore tests almost nothing about a gradient-domain effect. | M16 (MEASURED — M16 §3.3, `data/anisoscan-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 96 | The reviewer's proposed fix — per-frame row and column mean subtraction before the focus operator — changes fact 83 by **nothing**: `A` = −3.5 → −3.5 windows. On the level statistic it is **worse**: `L_hv(1)` = −8.0 → −9.5. | The fix is inert on this corpus and is not worth shipping for this reason. It may still be worth having for others; M16 did not test any. | M16 (MEASURED — M16 §6.1, arms A0/A1, `data/A1-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 97 | `WINDOW_RADIUS = 13` survives every M16 arm. The mean-regret argmin stays inside M13's published w11–w15 basin under destriping, a squared ROI, a 90° scene rotation and a fully isotropised plant; the largest penalty at w13 anywhere is **0.6759 DN**, below M15's registered 0.87 DN threshold. Leave-one-seed-out floor 0.0000–0.0234 DN, argmin stable across all five subsets. | No window number M13 or M15 produced is biased by an orientation defect, because there is no orientation defect. 13 stands. | M16 (MEASURED — M16 §7, `data/A*-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 98 | The orientation effect is larger in the **level** than in the **shift**, and it is present with **no depth discontinuity at all**. At step 0 on the real corpus the `vertical` geometry's argmin runs to the ladder endpoint w40 — *no turnover found within the sweep* — while `horizontal` turns over at 12–20; symmetrising the texture brings `vertical` back to 16 beside `horizontal`'s 17. | Fact 83's ±2.5-window regulariser shift is a second-order consequence of an 8–12-window gap that is already there at width 1. Future work should measure the level, not the shift. | M16 (MEASURED — M16 §6.3, N3 stratum, `data/A{0,2,6,11}-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 99 | H3's mechanism **is** expressible in the harness, but only at absurd amplitude. Planting a row-correlated pattern on the isotropic synthetic plant moves the orientation statistic by **0.0 windows at 0.377 DN (28× the sensor), 0.0 at 3.016 DN (222×) and −2.0 at 24.128 DN (1774×)**, floor 0.5; applying the fix at 24.128 DN returns it to within +0.5 of the unplanted arm. | The positive and negative controls both pass, so the H3 arms carry information and the refutation is by the pre-registered rule rather than by argument. And even at 1774× the sensor's amplitude the mechanism reproduces only **half** of fact 83; at the real amplitude, ≈0.03 %. | M16 (MEASURED — M16 §6.1/§8, arms A3/A4x1/A4x8/A4x64/A5x64; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 26 | **Every existing test stack was shot with a 2x teleconverter**, disclosed only after M1-M4 were complete. `LensModel = "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"`, `LensSpec = "FE 200mm F5.6 Macro OSS"`, `FocalLength = 200 mm`, `MaxApertureValue = 5.6`. **CORRECTED 2026-08-22 — this row previously claimed the maker-note lens ID "still reads as the bare lens". That is false.** Sony enumerates the *composed path* as its own ID: `LensType3` = **32893** bare, **33093** +1.4x, **33094** +2x, and every corpus frame reports **33094**. The tags that are useless are `LensType` (65535) and `LensType2` (0) | Two consequences, one of them now inverted. **(a)** Anything reading `FocalLength`/`FNumber` from EXIF is already TC-correct, so there is no hidden 2x error in the advisor. **(b)** **Key a lens profile on `LensType3`, which already denotes the composed optical path.** The original conclusion — "keying on the lens ID is a bug" — was right about the *requirement* (the key must denote the composed path, since `p`, focal length and aperture all differ) and wrong about the *fact*, because it generalised from `LensType`/`LensType2` to all lens identity. The surviving rule is narrower and sharper: **key on `LensType3`; never on `LensType`, `LensType2`, or a parsed `LensModel` string** | MEASURED-LOCALLY (exiftool `-n`, all corpus stacks; ID table read from exiftool's own `Sony:LensType3` lookup) |
| 27 | **The bellows factor of the composed path is `B = (1 + m/p) ∈ [2.41, 3.06]`**, point estimate 2.6-2.9, measured from the diffraction cutoff in the raw CFA. At f/11 the green-quincunx spectrum has a genuine knee at **f_sig = 0.2762 cyc/px**, above which the floor matches the photon-transfer noise model to **0.950x** — so it is a real optical cutoff, not a fitted plateau. **`B = 5` (p = 0.5) is REFUTED 5/5 by a model-free test** at two apertures: there is optical signal at 0.3508 cyc/px, where p=0.5 permits none. **`B = 1` is refuted by ~3x** | **The corpus's "dominant uncertainty in the whole advisor" (±38%) is retired to −20%/+2%, from data the owner already had, with no bench work.** With m ≈ 2.0, **p ≈ 1.0-1.4** — the working assumption of p=1 was right. It does **not** vanish: M5 measures the product `(1 + m/p)` and cannot separate `p` from `m`, so `B` is known at *one* magnification only. A bench measurement of `p` alone would give `B` at any magnification | M5 (MEASURED → DERIVED; independently reproduced) |
| 28 | **EXIF `FNumber` is the *marked* aperture and is NOT bellows-corrected.** The body composes the teleconverter into `FocalLength` and `FNumber` (fact 26) but applies no correction for working at 2:1. **Marked f/11 is optically f/33** | **The most directly actionable finding in the corpus.** Every advisor formula that reads `FNumber` and treats it as `N_eff` **under-predicts diffraction blur by ~3x** and will recommend f/11 as "safe". Apply `N_eff = FNumber_exif * B`. Consequences at B=3: f/8 discards **40%** of the sensor's 2-D Nyquist area (46% of contrast at 4-px detail), f/11 discards **68%** (90%) — a 33 MP sensor used as ~10.5 MP. Critical sampling is at **N_marked = f/6.21** | M5 §7 (DERIVED, factor-of-3 margin) |
| 29 | **The project's noise model is independently confirmed to ±10% by a method sharing none of its assumptions.** The spectral floor above the cutoff is a structure-free sigma estimate: floor/model = **0.950-1.093x** across 15 f/11 cases spanning a **4.8x signal range** (422-2027 DN), so it tests the *slope* of the photon-transfer relation, not one point. Immerkaer on the same ROIs agrees to 0.896-1.020x | Three structurally independent routes now concur. **Where they disagree the disagreement is diagnostic**: at f/8 the ratio is 4.58-20.19x because the "floor" still contains subject signal, which is exactly how M5 detected that f/8 has no reachable floor. Uses no darks, no flats, no Immerkaer kernel, no fitted gain | M5 §8 (MEASURED, n=15) |
| 30 | **The fusion prize is 0.14% of the pipeline.** Ring-difference focus + merge, fused into one `wgpu` kernel, runs the 22-frame stack in **4.117 ms** — bandwidth-bound at **84%** of the measured DRAM read ceiling, predicted to **1.05x by a zero-free-parameter model**. Unfused (focus written to memory, merge reads it back — i.e. *a plugin that merely emits a focus field*) costs 5.566 ms. **Prize = 1.449 ms = 0.14% cold / 0.20% warm.** Keeping the entire focus volume resident, the most permissive plugin model there is, costs only 1.683 ms more than fusing. GPU vs best parallel CPU: **~165x** | **This kills the case for constraining contributors to spliceable WGSL** (§3.4.1 B2), which was the stated justification for the whole spliced-kernel contribution format. Splicing would make a contributor inherit our tile size, halo, shared-memory layout, register budget and single-pass restriction, make their measure untestable in isolation, and harden fact 25's coupling into the ABI — to buy back 0.14%. **The rule becomes "run on the GPU, emit an `f32` focus field."** That keeps the 165x, which is the part that matters. Fusion survives as an internal optimisation: fused and unfused are **bit-identical** (self-test group 6), so it is an implementation detail, not a different answer | M7 (MEASURED; independently reproduced to 0.1%) |
| 140 | **`L̂ = Σ H_k* Y_k / (Σ\|H_k\|² + σ²/S)` is exactly the MMSE linear estimator** across the focus axis — confirmed by three independent routes (proposed closed form; empirical normal equations `R_yy w = r_yL`; black-box Nelder-Mead minimisation) agreeing to **6 decimals** | The external review's reframe is *algebraically* correct: selection and averaging are both degenerate cases of it. Nothing below weakens this; what fails is the claim that it helps **on this rig** | M20 (MEASURED) — **VERIFIED and UPGRADED TO PROOF by M20-V** (fact 124, Sherman-Morrison, 2.043e-13). The gain magnitude holds; its stated *cause* is refuted (fact 125) |
| 141 | **The unguarded Wiener merge LOSES to plain argmax at realistic noise, even given oracle depth *and* an oracle prior** — up to **31% worse RMSE** (σ=0.03: 0.0825 vs 0.0628). The `Σ\|H\|²` fallback guard is **load-bearing**, not one of three optional safeguards | Inverts the review's framing. Deconvolution is not "safe here because the noise model makes it safe"; it is *unsafe by default* and the noise model is what rescues it. A first guard attempt was algebraically identical to the unguarded estimator and produced identical numbers — caught and replaced | M20 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 142 | **Only 15.1% of real pixels sit where the estimator wins.** On all 22 frames of 109MSDCF, taking each pixel's *best* frame, `σ_local/signal_local` has median **1.128** — for the median pixel, local noise exceeds local signal structure **in its own best frame**. The crossover is σ≈0.03; 15.1% of pixels beat it (21.2% under an oracle bound). Robust to a 2× calibration error; flips at 3.3× | The reframe's benefit is real but confined to a minority of the frame. This is why M20 declines to make deconvolution the merge's core, while keeping it as a plugin | M20 (MEASURED) — **REPRODUCED on 109MSDCF but REFUTED AS A CORPUS FIGURE by M20-V.** The true range is **3.5%–65.8%** across five stacks (fact 127); the selector is biased in deconvolution's favour (fact 126); the statistic is monotone in frame count (fact 128). **Never quote 15.1% bare** |
| 143 | **Hard ceiling: if `H_k(f) = 0` for all k then `L̂(f) = 0` exactly.** At marked f/8 and f/11, MTF@Nyquist is 0.000 (fact 12) | **Deconvolution cannot restore Nyquist detail on this rig at the apertures actually used.** No estimator recovers a frequency no frame observed. The review's "only path to actual sharpness" is closed at the aperture, not the algorithm | M20 (DERIVED from facts 12/27/28) |
| 144 | **Blur-per-focus-step, measured in pixels, is aperture-invariant** — step µm ∝ DOF ∝ `N_eff` while CoC growth ∝ 1/`N_eff`, so at fixed subject depth frames scale as 1/`N_eff` and nothing else changes. Best-frame MTF at 0.25 cyc/px: f/4 **0.598**, f/5.6 **0.447**, f/8 **0.242**, f/11 **0.046**, f/16 **0.000** | **The largest actionable quality win found so far, and it is a capture change, not a code change.** Marked f/11 → f/5.6 buys **9.6×** contrast at 4-px detail and **13.5×** matched-filter SNR at fixed time, for 2× the frames and *no* extra light. Written up as `captures-needed.md` §0; §7 would turn it from DERIVED into MEASURED. An earlier version of this scaled blur with aperture and was **wrong** — superseded | M20 (DERIVED) — **the circularity concern is CONFIRMED: the optics gate IS a tautology** (fact 122). This row survives only on the a-priori `B = 1+m/p` check (fact 123), and it is **definitional, not optical** (fact 134) |
| 122 | **M20's optics "gate" is a TAUTOLOGY.** `B = 3.064` was itself obtained by inverting `f_c = pitch/(λN)` on the very knee the gate re-derives (M5 line 26). Rows 2 and 6 contain no measured quantity. **No configuration of the model could have failed the table** | A gate that cannot fail is not evidence. **State the input that would break a check, before running it** (discipline 250). M20 §3's "the model is gated" must be struck | M20-V (VERIFIED, `v1_optics.py`) — the second consecutive verification to find a test in this corpus with no power to fail |
| 123 | **The non-circular gate was available, costs one line, and passes.** A-priori `B = 1 + m/p = 3.000` predicts a knee at **0.2821** cyc/px against M5's measured **0.2762** — **2.1% agreement**, with no spectral measurement in the chain | This is the real licence for the optics model, and the only reason §4.4 stands at all. Use it in place of M20's table | M20-V (VERIFIED, `v1_optics.py`) |
| 124 | **The MMSE identity is now proved, not just checked.** `L̂ = ΣH*Y/(Σ\|H\|²+σ²/S)` proved analytically via Sherman-Morrison; worst relative error **2.043e-13** against brute-force inversion over 200 random cases | Fact 140 is upgraded from three-route agreement to proof. The estimator algebra is settled and needs no further work | M20-V (VERIFIED, `v2_estimator.py`) |
| 125 | **The gain residual was misattributed.** The +1.18% excess over `√(Σ\|H\|²)/max\|H\|` is caused by the **finite prior `S`** (→ 0.0000% as `S`→∞), *not* by an inverse-filtered baseline as M20 §4.2 claims. Rebuilding the baseline as single-frame Wiener gives **−1.81%** — the sign flips | A residual explained by the wrong mechanism is an unfalsified guess. Fact 140's magnitude survives; its stated cause does not | M20-V (CORRECTED, `v2_estimator.py`) |
| 126 | **M20's selector is biased in deconvolution's favour.** 109MSDCF's crossover fraction is **15.1%** under the report's argmin-σ_rel selector but **12.7%** under a decoupled sharpness selector | The headline is *more* robust than published — the true fraction is lower still. Never select and score on the same statistic | M20-V (VERIFIED/CORRECTED, `v5`, `v9`) |
| 127 | **"15.1% of pixels" is a property of ONE capture, and the corpus spans 3.5%–65.8%.** Across 109/119/112/113/coffee-bean: 15.1 / 30.5 / 43.7 / 57.9 / **65.8%**. On the two deepest stacks the **majority** of pixels sit where the estimator wins | **REFUTES M20's point estimate as a corpus figure.** The gating *recommendation* is unaffected — a local gate is right at 4% and still right at 66% — but deconvolution is worth materially more than M20 concluded | M20-V (REFUTES, `v7_corpus.py`) |
| 128 | **The statistic is monotone in frame count, and that was never disclosed.** `113MSDCF` goes **13.0% → 47.8%** from 22 to 63 frames under a bias-free selector | The central number of M20 is an argmin over K. Comparing it across stacks of different depth compares frame counts, not subjects | M20-V (VERIFIED, `v9_framecount.py`) |
| 129 | **The 0.3440 crossover is a units mismatch.** It is `0.03/0.0872` where 0.0872 is the median local σ of the noise-free **latent** — pairing unblurred noise-free contrast against blurred noise-subtracted observed contrast. Direct calibration at matched CFA scale: **0.2996** (implementable) / **0.6703** (oracle) | M20 correctly named this its softest number and was right for the wrong reason. Measure the crossover directly; do not unit-convert into it | M20-V (CORRECTED, `v6`, `v8`) |
| 130 | **Fact 88's 119MSDCF numbers are impossible under this project's own noise model.** At ISO 50 (`g`=0.1145) with ROI means ≤4585 DN, temporal σ caps at **22.9 DN**; fact 88 reports 43.2–53.1 DN. Those are spatial sds containing subject structure. **119 is *less* relatively noisy than 109** | **REFUTES fact 88's mechanism** (its advice survives and is strengthened). An internal consistency check against the noise model would have caught this at write time — run it on every σ this corpus publishes | M20-V (REFUTES fact 88, `v5_realdata.py`) |
| 131 | **`σ_local/signal_local` is the correct scale-invariant for sim→real transfer.** Scaling plant amplitude ×3 / ×0.3 with σ matched leaves gua/sel at **0.9945** and median σ_rel at **0.3707** identically | The one mapping constant in the deconvolution work that is dimensionally sound. Use it, not absolute DN, whenever a simulation result is carried to a capture | M20-V (VERIFIED, `v6_mapping.py`) |
| 132 | **The 9.6× aperture ratio is a point estimate masquerading as a result.** It holds only at `B`=3.0 and λ=550 nm; it spans **3.09×–12.58×** over `B`'s own published bracket [2.41, 3.064] and **3.26×–∞** over 450–650 nm — because f/11's cutoff (0.2821) sits just *above* the 0.25 cyc/px evaluation point | M5's "do not quote" list already banned a two-sided point `B`; M20 quoted one anyway. Never evaluate a ratio at a frequency adjacent to a cutoff without publishing the band | M20-V (CORRECTED, `v3`, `v10`) |
| 133 | **The robust form of the aperture result.** At 4-px detail, marked f/11 at m=2 gives modulation **0.00–0.17**; marked f/5.6 gives **0.35–0.54**. True at every `B` in [2.4, 3.1] and every λ in [450, 650] nm | This is what §4.4 should say. The *direction* of the advice is robust; the multiplier is not | M20-V (VERIFIED, `v10_aperture_robust.py`) |
| 134 | **M20 §4.4's blur-per-step invariance is definitional, not optical.** `c = m²δ/N_eff` means a fixed-CoC-increment policy has constant CoC/step **by construction**. The physical content is `frames ∝ 1/N_eff` | Fact 144 is not an optical discovery. State it as the capture-policy identity it is | M20-V (CORRECTED, `v3_aperture.py`) |
| 135 | **The CFA phase is CORRECT.** `raw_image_visible[0::2, 1::2]` is green for `raw_pattern [[0,1],[3,2]]` / `RGBG`; the G2 control `[1::2,0::2]` agrees to 3 decimals (15.2% vs 15.1%) | A suspected defect, checked and cleared with a positive control. Recorded so it is not re-litigated | M20-V (VERIFIED, `v5_realdata.py`) |
| 136 | **`mean \|∇\|` is one-sided, independently confirmed.** At σ=0.010 the unguarded Wiener has **+23.7%** gradient magnitude but **−12.1%** gradient *correlation* with truth; at σ=0.050 argmax selection reads mean\|∇\| **above the latent's own value** | Second independent confirmation of the M38/M39 metric defect, from a different milestone and a different author. `mean \|∇\|` alone can never be a quality metric | M20-V (VERIFIED, `v4_sim.py`) |
| 137 | **Cross-slab ringing does NOT drive M20's refutation.** The unguarded Wiener is *worst* under a **single-plane** depth model (1.088× RMSE) and mildest under a continuous ramp (1.039×); spread is 6.2%, not the "within 3%" M20 claims | Removing the mechanism M20 blamed makes the Wiener look **worse**, not better. The refutation is stronger than its stated reason | M20-V (CORRECTED, `v4_sim.py`) |
| 138 | **M20 §4.4 and §7 point in OPPOSITE directions.** Wider apertures raise local SNR and therefore raise the deconvolution-wins fraction (119MSDCF at f/5.6 → 30.5%). M20 treats the two as independent | Taking M20's own aperture advice invalidates M20's own "few pixels want deconvolution" figure. **The capture recommendation and the merge recommendation are coupled and must be designed together** | M20-V (VERIFIED, `v7_corpus.py`) |
| 139 | **The aperture recommendation is a two-stop extrapolation from the only calibrated aperture**, using a diffraction-only model with **no aberration term** — systematically optimistic in exactly the direction it recommends. M5's own f/5.6 knee (0.2431) is texture-limited and explicitly not quotable | **Largest unflagged risk in the deconvolution corpus.** Do not put "shoot at f/5.6" in front of the user until an aberration term or an f/5.6 calibration exists | M20-V (UNFLAGGED RISK, `v3_aperture.py`; M5 §11) |
| 145 | **`mean \|∇\|` is a ONE-SIDED metric.** At σ=0.010 the Wiener output carries **24% more** gradient magnitude than truth but **12% less** gradient *correlation* with truth; at σ=0.050 plain argmax reads mean\|∇\| **above** ground truth | A merge can raise mean\|∇\| by manufacturing detail. Valid only as a test against **collapse** (fact 24), never as evidence of quality. Dispatched to M18 mid-build | M20 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 150 | **The occlusion-bimodality mechanism is real and measured.** Multi-peaked through-focus curves are enriched **4.38×** at depth steps on `coffee-bean` (19.4% vs 4.4%), against a scene-matched **frame-permutation placebo that reads 1.01×**. Stable at 4.43× from a different subsample offset. Survives stratification within *every* intensity-gradient quintile (pooled **~2.7×**, rising to **9.5–14.3×** in the most textured quintile), and binning on intensity edges alone gives **0.00×** — so it is not an edge artifact | Confirms the review's second proposal at the level of mechanism, and identifies the signal that question 16's oracle headroom was exploiting. A first version of this measurement reported **29.47×** and was **circular** — bimodality was binned against an argmax field from the same volume, and a bimodal pixel manufactures its own depth step. 85% of that number was the tautology | M21 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 151 | **But the detector is unusable without the noise model.** On 109MSDCF and 119MSDCF at fine scale, the permutation null shows **noise alone flags 60–98% of pixels as multi-peaked** (real 60.7% vs permuted 92.5% on 109). On `coffee-bean` the same detector reads 4.8% against an 86.2% ceiling | The dip between peaks must be tested against **predicted** σ at that pixel's signal level, not against curve shape. Independently reaches the same conclusion as fact 141 by a different route: the calibrated noise model is what makes these stages possible at all — which is precisely what no competitor has | M21 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 152 | **Bimodality is invisible at the focus measure's own scale.** At `WINDOW_RADIUS = 13` (27 CFA px = **54 sensor px**) enrichment is **0.36×** — *depleted*. It appears only at radius 2 | **An architectural constraint on the fold seam** (review item R14) that was not previously on the list: per-pixel sufficient statistics must be carried at a materially finer scale than the focus window, or a second finer pass must be budgeted. Dispatched to M18 mid-build. Generalises: a detector inherited from another stage is not a neutral instrument | M21 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 160 | **Recurrence, not a σ threshold, is the correct hot-pixel discriminator.** The 242 darks arrive as 11 ISO groups, which supplies a free replication test. Against a Binomial independence baseline, pixels recurring in ≥6 groups number **3,947 (expected 2e-08)** and in all 11 **352 (expected 6e-26)**, while single-group flags (108,776) are *fewer* than chance — they are the threshold's false positives. Defensible map: **11,393 px = 0.0346%**, 346 per Mpx | Removes the threshold as a tuning knob entirely. A reusable pattern: data delivered in independently captured groups for one purpose (M4's read noise) supplies a built-in replicate test for another | M22 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 161 | **And it barely matters.** In real 1.3 s frames the excess attributable to the map is **+3.0 DN mean, 0.0 DN median** (always-hot 352: +3.7 DN). Against the calibrated noise floor the excess is **flat at ~3 DN across three signal decades** — the signature of a fixed additive offset — worth **0.39σ / 0.22σ / 0.13σ** from shadow to upper midtone. Only **3 pixels** sensor-wide are both always-hot and >100 DN | **Refutes the urgency of review item R11.** This sensor is clean; hot pixels displace a pixel by at most ~0.4 of its own noise. Build the map (it is cheap and correct) but do not let it preempt the merge. ARGUED: an additive constant belongs in the calibration/noise model as an offset, not in a detect-and-inpaint stage that invents pixel values | M22 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; deep shadow (<50 DN) had only 78 samples and is untested |
| 162 | **All 242 delivered darks are 1/100 s; the real stacks run 1/60 s to 2.5 s — up to 250× longer.** Dark current scales with time, so the map is complete *for the wrong exposure*. A cross-scene test with a **shift control** (even offset: preserves CFA phase, destroys per-pixel correspondence) finds **~839 scene-independent defects** at a 4σ bar of which the dark map contains **5** | Requested as `captures-needed.md` §6 — cheap, low urgency. **M4's read-noise and FPN work is exposure-independent and unaffected.** The first version of this test scored overlap against an *independence* baseline and reported >1M "defects", because both subjects sit centre-frame and the flag maps share large-scale structure; the known-real dark map is the positive control at 1.91/2.36/16.00× | M22 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 180 | **Per-frame photometric drift is present across most of the corpus**: peak-to-peak mean level varies **2.88%** (119MSDCF), **6.84%** (112MSDCF), **8.93%** (coffee-bubbles) and **11.70%** (coffee-bean). **`109MSDCF` is the quietest stack at 0.91%** | Establishes the premise of review item R9 as fact rather than speculation. **The stack that shaped most of this project's measurements is the least representative one in the corpus for this defect** — a clean result on 109 says nothing about photometric handling | M24 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; probe only, stacks subsampled so jitter figures are lower bounds |
| 181 | **EXIF does not predict the drift, in either direction.** `coffee-bubbles` and `112MSDCF` vary 6.84–8.93% with a **single** distinct `(ExposureTime, ISO, FNumber)` across the whole stack. `coffee-bean` *does* change exposure mid-capture (`4/5 s` → `5/8 s`, 0.356 EV) — but its measured level ratio is **1.0443 against an EXIF-predicted 1.2800**, i.e. the level moved **16% of what EXIF predicts** | **The per-frame gain must be FITTED from the data, never read from metadata.** A model trusting `ExposureTime × ISO` is blind to ~7–9% on two stacks and overcorrects by ~6× on a third. Sharper than R9 as the review stated it. ARGUED: the shortened exposure at near-constant level is the signature of auto-exposure compensating a drifting light; the two exposure groups are also different focus ranges, and that is not separable here | M24 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 182 | **The drift is not a framing artifact.** Focus breathing changes magnification and could move the mean without any exposure change — but a central 600 px ROI moves **at least as much** as the full frame on all three stacks tested (ratios 1.50 / 2.05 / 0.92, correlations **+0.911 / +0.971 / +0.848**), the opposite of what the framing hypothesis predicts | Discharges the rule-17 confound that would otherwise have made fact 180 unreadable. Honest limit: a centred subject blurring in and out moves light across the ROI boundary, so this **bounds** the framing explanation rather than eliminating it | M24 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 200 | **As-shot white balance is a large per-channel gain that varies per stack.** R spans **2.13–2.86**, B spans **1.41–1.88** across the six stacks; both greens are exactly equal on every stack. `daylight_whitebalance` is identical everywhere, so it is the **as-shot** value that varies — the body was on auto WB. `rgb_xyz_matrix` is constant, as a camera-model property should be | **Read WB per stack; never put it in a profile.** No G1/G2 imbalance term is needed for these captures | M26 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 201 | **The noise model is only valid in native per-channel raw DN, and white-balancing first breaks it by up to 2.86×.** Scaling a channel by `m` gives true `σ² = m²(gS + (RN·g)²)`, while applying the model to WB'd values gives `g(mS) + (RN·g)²`. The ratio → **`m`** in the read-limited (shadow) limit, **`√m`** in the shot-limited limit — so red is believed **2.86× quieter than it is, most strongly in the shadows** | **Ordering rule: gate in native raw DN; apply WB and the colour matrix after the merge.** The failure is silent — the gate simply rejects too aggressively, reverting toward the selector the project exists to replace, and it does so hardest exactly where M2 measured the argmax defect. A plugin needing earlier WB must transform the noise model with it, as part of the contract | M26 (DERIVED from fact 200 + the calibrated model) — **NOT INDEPENDENTLY VERIFIED** |
| 202 | **Saturation is real, per-stack, and absent from four of six stacks.** `coffee-bean` has **1.26%** of pixels ≥ 15360 and `coffee-bubbles` has 62,054 pinned at the 14-bit container max — while `109`, `119`, `112`, `113` contain **zero**, topping out at **39–61%** of the white level. Separately, `rawpy` exposes **two** white levels: `white_level` = **16383** (container) and `camera_white_level_per_channel` = **15360** | Detect saturation; never assume it either way. **The two white levels are both right and are used for different purposes** — the clip mask wants the container max, the noise model's range wants 15360. **Checked and clean:** `noise.rs` already documents and tests this (`usable_white_level_is_not_the_container_maximum`). Second respect (after fact 180) in which **`109`/`119` are the gentlest stacks in the corpus** — a clean result on them is systematically weaker evidence than it looks | M26 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 203 | **Clipping defeats discipline 29, and both confidence candidates fail in the same direction.** Cross-frame focus contrast reads **1.0000 — its maximum — on always-clipped pixels** (median; n=616) against 0.5398 never-clipped, at pixels pinned in every frame that carry zero information. Mechanism: **85.9%** of them have `f_min` **exactly 0** (uniformly clipped blob interior in ≥1 frame) vs **0.0000%** of never-clipped, while median `f_max` is **7,598 vs 145.6** — 52× typical — as the blob's edge crosses in another frame | **Mask samples at/above the container max before the focus volume and propagate the mask** — one comparison per sample, closing a maximum-severity hole. Discipline 29 was chosen *because* magnitude fails on fact 73; this is the same class of failure arriving through the quantity picked to prevent it. **The partially-clipped population is a weak effect**: a raw 1.67× elevation collapsed to **1.06–1.09×** under brightness matching, so ~90% was brightness (discipline 70, applied to the orchestrator's own first framing). No brightness-matched control is constructible for the always-clipped group — no unclipped pixel reaches that level by definition | M26 (MEASURED mechanism, DERIVED consequence) — **NOT INDEPENDENTLY VERIFIED**; frames unaligned, 616 px = 0.0075%, green sublattice and R=2 only |
| 210 | **A hole in the focus bracket is blindly detectable from a single missing frame.** Removing a contiguous block from `coffee-bean` (53 frames, f/8), peak-curvature ratio against a **fixed** control band runs **1.88 → 2.81** for gaps of 1→6 frames, against a null (same frame count removed from a region no group peaks in) **stable at 1.40–1.43**; excess **+0.45 to +1.39**. Parabola vertex offset \|δ\| moves in parallel, excess **−0.10 to −0.48** against a null stable at 0.83–0.87 | Ground truth is **by construction** — no plant, no simulation: remove frames and the pixels whose best frame was among them have provably lost coverage. Both detectors use **only the reduced stack**, so both are deployable at inference time | M27 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; one stack, one 1500×1500 crop, R=2, frames unaligned |
| 211 | **The gap disguises itself as a *better* peak.** A missing best frame makes the through-focus curve **sharper** (curvature ratio to 2.81) and **better centred** (\|δ\| falls 0.23 → 0.088). The predicted direction was the opposite — the surviving frames flank the true peak at **near-equal focus distance**, so the sampled curve reads symmetric and δ → 0 | **Third independent instance of one pattern**, and the reason it is promoted to discipline 120: fact 73 (monotone edge → magnitude high, information zero), fact 203 (clipped pixel → contrast maximal, information zero), fact 211 (best frame absent → peak looks textbook). Three failure modes, three metrics, all reading **confident where there is nothing to be confident about**. Degenerate inputs make clean-looking outputs | M27 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 212 | **Uniform under-sampling needs no optics model to detect.** Where a *hole* leaves an internal control, uniformly-too-coarse steps affect every pixel equally and §1's comparative method cannot work at all. But `nwide` — retained frames within 50% of peak height — falls **3 → 2 → 1 → 1 → 1** under ×1/×2/×3/×4/×6 decimation and is **absolute**: `nwide = 1` means the peak is resolved by one sample and its location is unrecoverable | Refutes the prediction that the reshoot advisor would need the optical model to supply a predicted peak width. **Confound closed (rule 17):** decimation estimates `min` from fewer samples, which would shrink `nwide` for free — holding the threshold at the full-stack minimum gives an **identical** column, and the median minimum drifts only 1.000 → 1.195 | M27 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 213 | **The deployable reshoot criterion, and a verdict on real capture practice.** Fraction of reliable pixels resolved by ≤1 sample: **0.01%** at 53 frames, **37.46%** at 27, 59.91% at 18, 69.06% at 14, 75.76% at 9. So `coffee-bean`'s 105-frame bracket is **~2–4× denser than it needed to be** at f/8 — comfortably too fine, not too coarse | Per-pixel, absolute, blind, and directly phrasable as R19's recipe: *"38% of the subject is resolved by a single frame; halve the step."* **DERIVED and contingent: the two capture findings cancel** — M20 wants f/11→f/5.6 for 9.6× contrast at ~2× the frames, and this measures ~2–4× surplus density, so **the aperture change is roughly free in frame count**. Chains to a DOF scaling from the optics model **M20's verifier is checking for circularity**; if that gate is tautological this inherits it | M27 (MEASURED + DERIVED) — **NOT INDEPENDENTLY VERIFIED**; decimation assumes optical but not photometric equivalence to a genuinely coarse bracket |
| 220 | **R10's robustness mask needs one correction: compare against the immediate neighbours, not a running estimate over the stack.** On the **clean** stack the noise-normalised pairwise residual grows **1.13 → 12.30** as frame separation goes 1 → 16 — **10.9× over 16×**, near-linear, the signature of an accumulating geometric warp (noise would be flat, defocus would saturate). Radial profile centre-to-corner: **1.82× with a whole-stack reference, 0.98× with an adjacent-frame one** | A whole-stack reference buys ~10× more geometric residual for no gain. **The architectural consequence is the opposite of the prediction: the mask CAN run before alignment**, so alignment can be protected from outliers rather than having to precede their detection. Frames adjacent in a clean stack differ by *noise*; frames 16 apart differ by *breathing* | M28 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; three stacks, unaligned, one crop size — **MECHANISM REFUTED by M31-V:** the residual is **photometric, not geometric**. Swapping script 02's median-gain estimator for the mean estimator M28 §6 itself recommends takes dk=16 from **12.301 → 4.094**, and a single least-squares *scalar* per pair removes **73.3%** of it — a scalar cannot express a displacement. The residual is non-monotone in `\|∇\|` and a constant 3.5–4.5% of signal. The half-normal assumption is **not** the problem (simulated Gaussian and Poisson both return 0.6744/0.6745 through the same pipeline) |
| 221 | **The M4 noise model predicts the clean adjacent-frame tile residual to 9.9%, with no free parameters.** Median tile \|z\| is **0.7416** against the **0.6745** half-normal expectation for pure noise (= **1.099×**); `coffee-bubbles` 1.645×, `foam` 2.097× | `σ²(S) = g·S + (RN_e·g)²` was calibrated on flat patches; this is an **independent validation on a real subject at 256-sensor-pixel tiles**, a scale and a statistic it was never fitted to. Arrived at incidentally while measuring something else | M28 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; assumes the residual is Gaussian, and the tails are what facts 222/224 measure — **QUALIFIED by M31-V:** "9.9% with no free parameters" is **1.005 / 1.099 / 1.449** across tile scale and **1.505** without the 22 fitted gains — so there are free parameters, and the number moves 1.5× with them |
| 222 | **Measured sensitivity of the mask, with a plant built from the frame's own content and a shift-zero placebo.** A 128-px tile replaced by the same tile taken `s` px away in the same frame (noise, defocus, illumination and sensor position all correct by construction). At FPR 1%: `s`=1 → **15.2%**, 2 → 31.1%, **4 → 53.8%**, 8 → **77.3%**, 16 → 96.2%. **Placebo `s`=0 → 0.0%** at FPR ≤ 1% | 4 green px = 8 sensor px = **41 µm on the sensor ≈ 20 µm at the subject** at m≈2.0, caught **89%** at FPR 5%. The placebo is mildly inflated at FPR 5% (8.3–10.6% vs nominal) because the null frame sits near peak focus — **calibrate the threshold per frame, not per stack**. Lower bound for *translation* only; deformation, occlusion and illumination change are unmeasured | M28 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** — **OPERATING POINT UNKNOWN (M31-V):** the placebo reads **9.85 / 8.33 / 10.61%** at a nominal 5% and **0.00%** at 1% (0/132, CI [0, 2.8%]). "@FPR 1%" therefore names a threshold the calibration cannot resolve. Conclusions survive recalibration |
| 223 | **The tile scale is not a sensitivity knob.** Detection at FPR 1% across a 4× range of scale is near-flat: `s`=4 gives **58.3 / 53.8 / 49.2%** at d=4/8/16; `s`=16 gives 97.7 / 96.2 / 85.6%. Planted \|z\| rises with `d` (3.06 → 4.36) but the threshold rises with it too (2.62 → 4.39) | **Choose the tile scale for compute cost, not detection power** — cutting against the usual reasoning about burst-denoising tile sizes. Refutes the predicted `s ≈ d` switch-on. Mechanism: the baseline *tail* is dominated by deterministic defocus structure rather than by noise, so signal and threshold average down together | M28 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 224 | **The detector transfers: a threshold calibrated entirely on the clean stack flags 1.01% / 8.33% / 17.88%** of tiles at FPR 1% on `109MSDCF` / `coffee-bubbles` / `foam` — clean, bubbles-move, scene-evolves. Ordering **pre-registered** from what the stacks are | Converts "it detects plants" into "it detects the real thing", and the two disturbed stacks separate by 2.1× from each other. **Confound stated:** the stacks differ in subject and contrast as well as stability, so this cannot separate *more disturbance* from *more contrast*; \|z\| being noise-normalised handles ISO by construction | M28 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 225 | **M24 said gain must be FITTED; M28 measures HOW, after the wrong choice bit its own script.** Peak-to-peak on `109MSDCF`: median-over-subject-crop **4.28%**, mean-all-px **1.02%**, median-low-gradient 0.94%, mean-low-gradient 0.99% — against M24's independent **0.91%** | **Use the mean over all pixels; never a median over a subject-centred region** — as focus sweeps, subject contrast changes and that median absorbs *focus* signal into what it calls gain. The low-gradient restriction is **not** the safe choice it looks: on `foam` it is the worst estimator (84.98%), because "low gradient in the median reference" selects nothing meaningful when the scene evolves. Estimator **disagreement** is itself a scene-instability signal (5.6× on `foam` vs 1.09× clean) — an observation from three stacks, not a calibrated detector | M28 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 230 | **The merge does NOT dilute dust. The estimator's supposed free lunch is worth `D = 0.999`.** Sensor-fixed defect suppression requires the averaged frames to be *displaced relative to one another*; measured adjacent-frame warp is **sub-pixel — 0.07–0.22 green px** across two stacks, four radii, sixteen tiles each | **A focus merge averages ADJACENT frames precisely because they agree.** M27 put `n_eff ≈ 3` at full sampling density and M28 showed disagreement grows near-linearly with separation, so the merge gathers exactly the frames whose dust positions coincide. A 0.2 px shift does not move a shadow 10–40 px across. **Dust must be handled explicitly — flat-field division or a defect map — it is not a by-product of estimation.** Independently corroborates fact 221 (adjacent residual at 1.099× the noise floor) | M29 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; rests on the `sep 1` column only, the `sep ≥ 8` columns lost phase-correlation lock and are disclosed as unusable — **SPEC INCOMPLETE (M31-V): the flat-field map floor IS PRNU** (`g/blur(g) ≈ 1+p`), and PRNU does not fall with `n`. Bounded at **≲0.26%** from M29's own script-01 data. Consequence: **42–51σ becomes 17–19σ, and flats stop helping at n≈4–5, not 16.** M4 declines to measure PRNU, so `captures-needed.md`'s flat-field campaign is load-bearing for this fact |
| 231 | **A self-ratio static map responds to defect depth × LOCAL SCENE BRIGHTNESS relative to its neighbourhood: `R ≈ 0.92·(g/blur(g))` at the defect.** Response is dead linear in depth (0.342 / 0.342 / 0.342 at 1 / 4 / 16%) and tracks `g/blur` across six stacks × three locations: `g/blur` 0.29 → `R` 0.274; 1.16 → 1.065; ≈1.00 → 0.89–0.95 | **This is why a flat field is the right instrument and a subject frame is not** — a flat has `g/blur(g) ≡ 1` everywhere by construction. Any multiplicative defect map built from subject frames (dust, PRNU, anything) **must divide by the local relative brightness** or it reports a defect field shaped like the scene. The pipeline algebra predicts 0.885 and was right; the empirical 0.274 first measured was **one pixel's `g/blur`**, promoted to a global constant by its author | M29 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** — **CONFIRMED and SHARPENED by M31-V:** the exact pipeline algebra is **0.9148**, not the 0.885 the report derives — its gap was a linearisation error, so **the lesson is stronger than stated**. Measured/pure-algebra agrees to 0.3499/0.3542/0.3557 across σ |
| 232 | **Dust is undetectable from subject stacks: the limit is a 32–50% shadow, against real dust of 1–15%.** Six-stack per-location conjunction; the 50% positive control fires at all three planted locations, 32% at none. **Q9: no excess over the shift null** anywhere in the tail (raw −0.0001, standardised +0.0006 at p0.001) | A null result **with a bound attached**, which is the only kind worth recording. Also: a `min`-conjunction across heterogeneous instruments is bounded by its worst member — the raw variant never fires at any depth because `coffee-bubbles`' map rms is 6.5× `coffee-bean`'s and alone sets the tail | M29 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; sweep is too coarse to separate the three locations — **QUALIFIED by M31-V:** the `sep 1` column is **peak-locked at ~0.5× truth** (Fourier-shift plant: true 0.05/0.10/0.20/0.30 → 0.0251/0.0510/0.1086/0.1827), and the disclosure calls it "clean". `sep 4` is also broken (3.381 px vs 0.103 at sep 8) and undisclosed. **Pre-registered Q12 fails and is unreported** |
| 233 | **The static-map floor is scene texture, not noise, so it cannot be bought with frames.** Map rms vs frame count over a 16× sweep: 0.14412 → 0.15447, **exponent +0.025** — dead flat, against −0.5 for shot noise. The stochastic part alone (adjacent-frame difference) is **1.6%**, a ~10× separation | **The scene is common to every frame of a stack, so averaging within a stack cannot remove it.** A flat field reaches a **0.120%** floor at n=20 (ISO 100, 8,000 DN) from the calibrated model with no free parameters — a **158× improvement**, at which a 5% shadow is a **42σ** detection. Yields a *specification*: **≥16 flats per working aperture, ISO 100, mid-tone 8,000–12,000 DN** | M29 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; one stack for the n-sweep — **THE DISCRIMINATOR HAD NO POWER (M31-V).** "+0.0250 against −0.5 for shot noise" names the wrong alternative: under pure shot noise this map's exponent is **−0.0045**, not −0.5, because the map is PRNU-dominated (fact 230). The measured and null exponents are indistinguishable, so the test could not have rejected. Discipline 250 |
| 234 | **Two stacks shot in the same session of the same subject share 94% of their "static" map.** `112MSDCF` × `113MSDCF` **r = 0.9370** against a shift null of 0.0845, while different-subject pairs give **0.002–0.016**. Same-ish median 0.4685 vs different-subject 0.0017 — a **271.92×** ratio | The pre-registered control that killed the first version of the instrument: the map is measuring **residual scene structure**, not sensor. Kept because it is also the cleanest available demonstration that "static across the frames of one stack" and "static in sensor coordinates" are different properties, and that only cross-*subject* evidence can distinguish them | M29 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** — **M31-V:** the detection limit is quoted from the arm the milestone itself declares defective — `04-limit.json` has `raw.limit = [null,null,null]`. **Pre-registered Q7 fails for the primary statistic by the milestone's own criterion** |
| 240 | **Exposure allocation is neutral at fixed light. Splitting a budget across exposures neither gains nor loses anything in the shot-noise regime.** `m` base frames + `m` at +2 EV cost the same `5m` time units as `5m` base frames and reach the same variance; measured per pixel, the median ratio is **1.00041 / 1.00470 / 1.00192** across three stacks, residual attributable to read noise in the predicted direction | **This constrains R15, R16 and R17 together, and is the most reusable thing in the capture-design workstream.** How a light budget is *divided across frames* does not affect noise — only the total does. Every capture-design decision therefore reduces to the **non-noise** asymmetries: read noise (fact 241), clipping (fact 242), focus coverage (fact 213), outlier rejection (fact 222), and **aperture (M20's 9.6×)**. Only the last is large, and it is the only one that changes the *optics* rather than the allocation | M30 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; assumes shutter-based EV change and ignores motion blur, which a real long exposure would incur — **M31-V: CONFIRMED**, re-derived by hand before reading the script (`precision_HDR − precision_base = m·12R²/[(4gL+R²)(gL+R²)] > 0`; ratio `= (1/5)[1+16(1+x)/(4+x)]`, exactly 1 at x=0) and by Monte Carlo. **Wording defect: the row says variance and measures sd** |
| 241 | **This sensor is shot-noise limited across its entire usable range.** Read noise binds where `S < RN_e²·g`: **2.02 / 2.47 / 6.46 DN** above black at ISO 50 / 500 / 160 = **0.014–0.044% of full scale**. Measured fraction of pixels below the boundary, three stacks: **0.0000%** | The dual-gain design does this deliberately — the high-ISO branch drops read noise to 1.47 e⁻ exactly where `g` rises. **Keep the read-noise term in `σ²(S)` — it is what makes the model correct near black, and masked or clipped regions do reach there — but make no design decision *because of* it.** Any argument that depends on read noise for its justification depends, on this rig, on 0.0000% of the frame | M30 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; the boundary is exact given M4's model, the 0.0000% is corpus-specific — **M31-V: conclusion CONFIRMED, implementation DEFECTIVE.** The boundary `S < RN_e²·g` is algebraically right but the script implements `S < RN_e²` — off by 8.7× / 0.87× / 2.7×. The 0.000000% survives at the documented boundary, checked on the full green plane, but **the script never tested the quantity the fact states** |
| 242 | **The clipping a merge sees is not the clipping in the stack: 0.075% at gathered frames against 0.177% whole-stack, a 2.3× reduction.** Two of three stacks have exactly zero of both. `112MSDCF` has **30.7% below SNR 10** at best focus but **0.0% below SNR 5** | **Highlights are disproportionately out of focus** — speculars sit on curved surfaces near the depth extremes — so the highlight case for exposure bracketing is roughly half what a whole-stack figure suggests. `112MSDCF` is not a dynamic-range problem but a *dim frame*, which more light fixes and which fact 240 says more frames supply as well as longer ones. **General instruction: any statistic used to justify a capture change must be evaluated at the frames the merge would gather, not over the stack** | M30 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; best-frame index from an unregularised argmax over M27's focus volume, which rule 4 forbids for output but is adequate for locating signal — **REFUTED by M31-V — THIS IS A RULE-4 VIOLATION AND THE ROW IS WITHDRAWN.** The 2.3× is an artefact of a **raw argmax**: at the shipped 31×31 regularisation it is **1.4×**, and heavier still **1.0×** — against a uniform-random-frame null of 0.1710%. Mechanism: the argmax *flees* clipped frames because clipping flattens the gradient (median focus 262.26 clipped vs 311.11 unclipped). **Do not cite this row. Fact 243's HDR verdict rests partly on it and must be re-derived** |
| 243 | **Verdict on HDR co-bracketing: support it, do not default it, trigger it per stack.** The machinery is already paid for (M24 gain in the forward model), the default path should not spend frames on exposure, and clipping-at-gathered-frames is a computable per-stack trigger | **The review's direction is backwards for highlights:** rescuing clipped pixels needs a **−2 EV** pass; +2 EV clips *more* (**1.89%** newly clipped on `coffee-bean`). Shadow lifting and highlight rescue are opposite operations. The advisory form — "2.4% of gathered pixels are clipped; a −2 EV pass would recover them" — is the same instrument R19 asked for | M30 (DERIVED from facts 240-242) — **NOT INDEPENDENTLY VERIFIED** — **RE-DERIVED by the orchestrator after fact 242's withdrawal; the verdict STANDS and its own evidence was understated 3.7x.** See facts 432-435. The recommendation (support, do not default, trigger per stack) survives intact, but **the argument for it inverts**: M30 reached it partly by reasoning that selection already dodges half the clipping, and that dodge is now measured at 1.32x rather than 2.3x, so **the highlight case is stronger than M30 thought, not weaker**. The `−2 EV, not +2 EV` direction is unaffected and is reinforced. **The 1.89% in this row should read 7.05%** |
| 260 | **A self-normalised posterior temperature is blind to the evidence, and non-monotone in it.** Across a **6.1× range of focus evidence** (peak-over-noise 119 → 728) the self-normalised arm reports **0.6480 → 0.6482** — a 0.03% change — falling to 0.6085 in between. Under a 16× SNR degradation it moves **9%** while the calibrated arm moves **22 orders of magnitude**. It reports "≈12 candidate frames" on every bin at every SNR tested | **The sharpest available form of discipline 120**, which M27 could only argue from three instances. Dividing by `std_k(f_k)` divides out the peak height, which *is* the evidence; what survives is the curve's **shape**, a property of the subject and the optics rather than of the measurement. A statistic non-monotone in the quantity it purports to report admits no order-preserving rescue | M32 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 261 | **Focus evidence on this rig is overwhelming: the through-focus peak stands 142–991 σ above its own curve**, across every texture bin including the least textured in the crop. Re-estimated model-free from the focus curve's along-`k` roughness (no noise model, no Monte Carlo, no added noise); the two estimates agree to **1.24×**, the Monte Carlo conservative as predicted | **A calibrated posterior over frame index is a delta function on real data** — perplexity 1.0000, rising only to 1.206 after a 16× SNR degradation that puts the data below the dimmest stack in the corpus, against a no-information null of 33.97. The falsification threshold was pre-registered at ~100×; the conclusion is insensitive to the noise model being wrong by two orders of magnitude | M32 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; measured on `coffee-bean`, the cleanest stack, with degradation applied synthetically rather than captured — **NUMBER CORRECTED by M36-V (facts 286, 285): the focus measure was `scipy.ndimage.sobel` on the whole CUBE, silently smoothing along the FRAME axis, and `rough_sigma` reads 21–28% low on such a volume. On the per-frame measure the range is 84–512σ, not 142–991σ. The conclusion is untouched — 84σ is still a delta — and the report's "Monte Carlo is conservative" reads exactly backwards: the MC estimate is the correct one** |
| 262 | **The no-information fixed point of a softmax posterior is not `H/log n = 1`, and it drifts with `n`: 0.888 → 0.850 for n = 53 → 9**, perplexity **64–72% of `n`**. Simulated null (200k trials) reproduces the scene-free placebo to **0.0137**, inside the pre-registered 0.02 | **The statistic is built from a maximum, and the maximum of `n` noise draws is not typical of them**, so even a perfectly calibrated softmax concentrates on pure noise. Any entropy threshold must be referenced to this `n`-dependent null, not to `log n` — a tool shipping "entropy > 0.9 is unreliable" would call every pixel of a 9-frame stack reliable, by construction. The null is a pure function of `n`, so tabulate it once. **General form: any statistic defined relative to an extremum has a sample-size-dependent null that must be simulated, not reasoned about** | M32 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 263 | **The defect in selection is not a noise problem.** A 142 σ peak is not signal-to-noise limited, so M2's argmax defect in lit low-contrast regions and M27's under-resolved pixels cannot be SNR failures — **they are sampling and model failures: the true peak lies between frames and the estimator has no term for it** | **Relocates confidence.** The uncertain quantity is not *which frame is best* (nearly certain) but **which frames are equivalent** — M27's `n_eff ≈ 3` — and **how far the true peak sits from the nearest sample**. Neither is a function of the focus curve's shape, which is exactly why discipline 120 disqualified shape statistics. Confidence must be built from the predicted σ of the merged estimate, the acceptance-set width, and the sub-frame peak offset | M32 (DERIVED from facts 261, 24, 211) — **NOT INDEPENDENTLY VERIFIED** |
| 264 | **M20 and M32 explain each other.** M20: the unguarded Wiener estimator *loses* to argmax by up to 31% even with oracle depth, and only **15.1%** of real pixels beat the crossover. M32: when one frame stands 10²–10³ σ above the rest, **the minimum-variance estimator *is* nearly a selector** and the matched filter has nothing to harvest from neighbours | **The thesis survives and gets sharper.** "Estimation, not selection" is a claim about estimating the **pixel value**, and it is untouched. It was never a claim about being unsure which frame won, and it must not become one. The estimation content lives in **averaging among frames that genuinely agree** (M14's 0.534×), in the **sub-frame peak location**, and in the noise model that identifies both | M32 (DERIVED, reconciling M20 + M32) — **NOT INDEPENDENTLY VERIFIED** |
| 270 | **At operational sampling, ~~48.7%~~ **51.3%** of pixels miss their focus peak entirely and give up a median 4.64% of their focus response** — **10.74%** at p90, **17.34%** at p99. Deficit grows to 9.74% (×4) and 19.60% (×6) mean. Replication across the two ×2 phases agrees to **0.05%** | Question 65's candidate (c), and the **only** one of the three with a measured magnitude. Nothing at the median, a great deal in a large minority — **the exact profile of something a per-pixel confidence map exists to report and a global quality number cannot**. **The all-pixel median is meaningless here**: half the population sits at exactly 1.0, so the median reports which side of 50% the point mass fell on (0.234% vs 0.000% for the two phases — not a difference between them) | M33 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; ground truth is the 105-frame grid, which misses its own peaks by 0.711% against the ×2 grid's 2.753% — adequate at **3.87×**, but a ×4 grid would not have been — **DIRECTION INVERTED and MARGIN CORRECTED by M36-V (facts 288, 289): 48.7% of pixels HIT their peak at ×2; 51.3% miss. The "replication" cited cannot exist — the two ×2 phases' hit fractions sum to 1.0000 by construction, so they are complements, not independent arms (discipline 204). Adequacy is 3.10× (3.24× like-for-like, ~2.7–2.8× calibration-corrected) against a pre-registered bar of 3×, because 0.711% came from the parabolic fit fact 271 disqualifies** |
| 271 | **Three-point parabolic peak interpolation gives a HEIGHT estimate that is anti-correlated with the quantity it reports.** On a synthetic Gaussian its predicted deficit **falls 21×** (1.55% → 0.07%) while the true deficit **rises 8×** (3.08% → 24.57%). On real data it is pinned near **1.5%** while the truth runs 2.75% → 19.60%; calibration ratio 0.457 / 0.115 / 0.042 at ×2/×4/×6 | **Discipline 120's failure mode in a third independent guise, this time inside the most standard piece of sub-pixel machinery in the field.** The parabola's *relative* deficit depends only on the **shape** of three samples, which is scale-free, so it barely moves with the spacing that determines the answer. **Never use the parabola's peak height for anything** — gate thresholds, quality reporting, or confidence | M33 (MEASURED, synthetic + real) — **NOT INDEPENDENTLY VERIFIED** |
| 272 | **The log-domain (Gaussian) three-point fit with baseline subtraction is the fix, and it settles `B` §4.4's UNVERIFIED marker.** Exact on a Gaussian response (ratio **1.0000** at every spacing, error ~10⁻¹⁷). On real data at ×2 it reaches calibration ratio **0.710** and **51.2%** of pixels within 2×, against the parabola's 0.457 / 37.5% — **the first estimator in the milestone to clear the pre-registered calibration bar** | Baseline subtraction matters because `log` is not shift-invariant and the focus measure does not reach zero when defocused. **The placebo confirms it is not universally better:** on a curve that genuinely *is* a parabola the parabola fit is exact and the log fit is **3.02× wrong**. Honest scope: the fix works at operational density and degrades under sparse sampling (ratio 0.368 at ×4, 0.223 at ×6). **One-line change wherever interpolation happens** | M33 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**. **UPDATED by M35 (fact 304): this comparison changed two things at once — it scored a RAW parabola against a BASELINE-SUBTRACTED log fit. The missing cell has now been measured: 9% of the margin is the baseline, 91% is the log domain (3% / 97% at ×4). The fact stands and is better supported. M35 also reproduced 0.457 / 0.710 / 51.2% exactly from independent code** |
| 273 | **The same fit is adequate for peak POSITION and disqualifying for peak HEIGHT.** Position at ×2: parabola 0.128 dense frames vs the trivial argmax's 0.517 — a **4.03×** gain, only **9.4%** worse than the log fit. Synthetic shrinkage 0.403 (h=4) and 0.110 (h=6) for the parabola; **1.000** for the log fit | **Position is set by the *asymmetry* of three samples — a first-order property any smooth fit captures. Height is *curvature extrapolated beyond* them — entirely a consequence of the assumed functional form, about which three points carry no information.** The parabola is not estimating the peak height from the data; it is reporting its own assumption, evaluated at the data. **This scope limit is what keeps fact 271 from overclaiming against the field**, which mostly uses interpolation for position | M33 (MEASURED + DERIVED mechanism) — **NOT INDEPENDENTLY VERIFIED** |
| 274 | **The through-focus response has heavier shoulders than a Gaussian.** Fitting a Gaussian width to the decimation ladder gives σ = **1.68 / 2.04 / 2.45 dense frames** from the ×2 / ×4 / ×6 arms; a true Gaussian would give one number | Explains why the log fit is *exact* on synthetic and only *better* on real data, and why both estimators degrade under sparse sampling: the wider the spacing, the more the fit is extrapolating into shoulders neither functional form describes. **Any future sub-frame estimator should be validated on the decimation ladder rather than at one spacing**, since a single-spacing test cannot see this | M33 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; one stack, one aperture, one magnification |
| 280 | **The confidence output must be a VECTOR; a scalar cannot represent it.** The three real-valued channels' worst-5% sets union to **14.278%** of pixels against a **15.0%** perfectly-disjoint ceiling — **95.19% of the way to complete disjointness** (5.0% if they were the same channel). Every pairwise overlap sits at **0.53×–1.35× of analytic chance**; the label-shuffle null returns **0.0256** against an analytic **0.0256** | Settles M18's output contract. **The controls are what make it readable:** each channel is **70–76% self-reproducible** under an independent noise re-realisation, so this is disagreement between real measurements, not between noise. Three orthogonal noise sources would have produced the overlap table exactly — the reliability ceiling is the control that separates the two cases, and it is a conservative lower bound (both arms carry √2× the real noise) | M34 (MEASURED) — **"AT CHANCE" IS FALSE, and the error understates M34 (fact 287): against the milestone's own shuffle null (sd 0.00048) C1 vs C3 sits at z = −25.0 and C1 vs C2 at z = +18.6. The channels are significantly MORE disjoint than chance. The lower bound holds but by −0.0074…−0.0090, not the √2 margin (fact 294)** |
| 281 | **One channel is NEGATIVELY informative about another's target.** C1 (predicted σ) has a worst-5% lift of **0.89×** on C3's true sub-frame deficit — the pixels it calls least trustworthy have **less** true deficit than average (Spearman −0.0726 against truth, −0.1240 against C3) | **This, not the orthogonality, is the decisive argument for the vector.** Mechanism: photon-starved pixels have **flat** through-focus curves, so missing the peak costs them little — the channel that finds the noisiest pixels is systematically looking *away* from the worst-sampled ones. **No monotone scalar combination of these channels is faithful**, so a "quality score" is not merely lossy, it is wrong | M34 (MEASURED + DERIVED mechanism) — **NUMBER SURVIVES, MECHANISM REFUTED, SIGN IS GATE-DEPENDENT (M36-V facts 290, 291, 292).** The stated cause is dead on direct measurement: Spearman(signal, deficit) = +0.0000. The real channel is **acceptance-set size** (fact 291), which generalises across all three stacks. And three of six reasonable definitions of "predicted σ" **flip the sign** (fact 292), so this is safe as "C1 carries no useful sub-frame information" and **not** as "predicted σ is anti-informative". **M18's output contract must not rest on the sign** — see question 80 |
| 282 | **The honest "do not trust this pixel" mask is the UNION, and it is 14.3% of pixels — 3× what any single channel reports.** C3 alone predicts true deficit at Spearman **+0.5560** against a random-channel floor of **+0.0014**; C2 at **+0.3349**; C1 at −0.0726 | **A tool shipping one confidence channel understates its own uncertainty by about 3×.** This is the concrete, checkable form of the product claim: 14.3% of this stack is pixels some channel says not to trust, and the selectors we are competing with report none of them | M34 (MEASURED, ground truth = M33's dense 105-frame grid) — **NOT INDEPENDENTLY VERIFIED**; ground truth honest by 3.87× and no more — **CORRECTED to 3.10× (fact 289), and C3's specificity is ONE-STACK (fact 293): Spearman +0.5569 on coffee-bean falls to +0.048 on 119MSDCF and +0.053 on 112MSDCF; worst-5% lift 2.91× → 1.28× → 1.37×. Confounded with sampling density and signal level, so a warning rather than a refutation — but the confound is the kind that would also cause a real collapse (question 82)** |
| 283 | **Fact 261 is right about the typical pixel and silent about the minority — and confidence lives in the minority.** Per pixel, the calibrated posterior's perplexity is within 1% of a delta for only **76.5%** of pixels; p99 = **4.74**, max = **39.05**, and the informative 23.5% correlates with true sub-frame deficit at **+0.3349** | **Answers question 65(b): `n_eff` is degenerate for the typical pixel and genuinely informative in the tail — so it ships.** My own falsified prediction (P2 predicted >95% degenerate). **The general error: fact 261 was measured on binned populations, and a median over a population cannot falsify a claim about that population's tail.** Recheck any fact whose evidence is a median but whose claim is about extremes | M34 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; qualifies but does not overturn fact 261 |
| 284 | **Explicit flags are nearly free and nearly redundant.** C4 (clip ∪ stack-boundary peak) fires on **0.053%** of pixels and adds only **0.0145%** of genuinely new pixels to the union — **73% of what it flags is already caught** by the three real-valued channels | **Keep the flags, but as an explanation rather than a dimension**: they are the only channel that says *why* instead of *how much*, which is what the reshoot advisor needs. Separately, C4's degenerate row became **a free second null**: a binary flag on 0.053% of pixels has a "worst 5%" that is 99% random tie-breaks, so its overlaps must land at chance by construction — and they measured 0.0250 / 0.0297 / 0.0268 against 0.0256 | M34 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 285 | **`scipy.ndimage.sobel` on an N-D cube smooths along every axis except the derivative axis** — so M32's focus response is `[1,2,1]`-blended across adjacent frames and scaled 4x, while M27/M33/M34 use the unsmoothed per-frame measure. Median `focus3d/focus2d` = 3.587; median deviation from a pure 4x scaling 10.4% | M32 is the only milestone affected (I grepped every `sobel(` call under `experiments/*/src/`), but three of its scripts are, and its report claims the opposite at line 42. Any future cube-wise filter call inherits this | M36 (MEASURED, `V10`) |
| 286 | **On the project's actual focus measure the through-focus peak stands 84–512 sigma above its own curve, not 142–991.** Two compounding causes: the frame smoothing of fact 285, and `rough_sigma` being biased **21–28% low** on a frame-smoothed volume (it is unbiased, 1.06–1.13x, on an unsmoothed one) | Fact 261's conclusion is untouched — 84 sigma is still a delta — but the number that "makes M32 and M20 cohere" is 1.7–1.9x smaller than reported, and the report's claim that the Monte Carlo estimate is "conservative" is backwards: the MC estimate is the correct one | M36 (MEASURED, `V11`) |
| 287 | **M34's pairwise overlaps are not at chance.** The milestone's own label-shuffle null has sd 0.00048 over 100 repeats; C1 vs C3 sits at **z = −25.0** and C1 vs C2 at **z = +18.6** | The channels are *more* disjoint than chance in the C1/C3 direction, which is fact 281 appearing in the overlap table. "At chance" understates M34's own result while being technically false | M36 (MEASURED, `V02`) |
| 288 | **48.7% of pixels HIT their focus peak at x2; 51.3% miss it.** The two x2 phases' hit fractions are 0.4869095 and 0.5131283 and sum to 1.0000 — complementary by construction, not an independent replication | Fact 270 states the direction backwards and cites a replication that cannot exist for that statistic. The conditional deficit statistics do replicate (4.6405 vs 4.5957) | M36 (MEASURED, `V07`) |
| 289 | **The dense 105-frame grid's own residual deficit is 0.8875%, not 0.711%**, when measured with the log+baseline fit M33 itself prefers; adequacy is **3.10x** (3.24x like-for-like), not 3.87x, and ~2.7–2.8x after the log fit's own 0.854 calibration | The 0.711% was produced by the parabolic height fit that fact 271 disqualifies. The pre-registered adequacy bar was 3x, so this sits on the edge rather than comfortably above it | M36 (MEASURED, `V07`) |
| 290 | **Fact 281's mechanism is wrong and its number is right.** Spearman(mean signal, true deficit) = **+0.0000**; Spearman(peak − baseline, true deficit) = **+0.0147**; both decile tables flat | The stated causal story ("photon-starved pixels have flat curves so missing the peak costs them little") is refuted by direct measurement, while the 0.89x it was invented to explain survives a block bootstrap, three shift controls and two other stacks | M36 (MEASURED, `V05b`) |
| 291 | **The acceptance-set size is itself a sub-frame-offset detector, and it is the real mechanism behind fact 281.** Spearman(size, true deficit) = +0.198; size 1 (91.94% of pixels) lift 0.91x, size 2 (6.82%) lift **2.10x**; worst-5%-by-size lift **1.94x** on coffee-bean, **2.67x** on 119MSDCF, **2.36x** on 112MSDCF | C1 decreases with acceptance-set size, so its worst-5% is nearly all size-1 pixels whose lift is 0.91x — which *is* the observed 0.889x. And the acceptance-set size is the only channel-like quantity in this study that generalises across all three stacks: **it is a candidate channel in its own right** | M36 (MEASURED, `V05c`, `V06`) |
| 292 | **C1's anti-informativeness is a property of the gate, not of "predicted sigma".** Worst-5% lift: gated 1-sigma **0.889x**, 2-sigma 0.762x, 3-sigma 0.680x; but sigma at the argmax frame alone **1.118x**, fixed top-3 **1.125x**, inverse SNR of the mean image **1.111x**. Block-bootstrap CIs [0.828, 0.945] and [1.035, 1.184] — both signs are solid | Fact 281 is safe as "C1 carries no useful information about sub-frame deficit"; it is **not** safe as "predicted sigma is anti-informative", because a reasonable reimplementation of the same channel flips the sign. M18's output contract should not rest on the sign | M36 (MEASURED, `V05`) |
| 293 | **C3's specificity does not reproduce off coffee-bean.** Spearman vs true deficit: **+0.5569** (coffee-bean, 105 frames, ISO 50) -> **+0.048** (119MSDCF, 33, ISO 50) -> **+0.053** (112MSDCF, 79, ISO 500); worst-5% lift 2.91x -> 1.28x -> 1.37x | Fact 282's +0.5560 is a one-stack number. Confounded with sampling density (119MSDCF has 10.9% boundary-argmax pixels) and signal level (112MSDCF median 179 DN), so this is a warning rather than a refutation — but the confound is exactly the kind that would also *cause* a real collapse | M36 (MEASURED, `V06`, `V06b`) |
| 294 | **M34's reliability protocol has two opposing biases that nearly cancel.** On a synthetic stack with known truth: R_true(1x) = 0.742 / 0.744 / 0.815, R under the author's protocol = 0.735 / 0.735 / 0.811 — **net bias −0.0074 / −0.0090 / −0.0037**, from a sharing gain of +0.041…+0.060 against a noise penalty of −0.050…−0.064 | The "conservative lower bound" conclusion is correct but for a reason the report does not give, and the margin is <0.01 rather than the ~0.05 the sqrt(2) argument implies. The ceiling is also a strong function of an arbitrary knob (C1: 0.926 at x0.25 -> 0.635 at x2) | M36 (MEASURED, `V04`, `V03`) |
| 295 | **The M33/M34 ground-truth gap decomposes exactly: the mean gap is 100% baseline subtraction, the fraction gap is 0%.** 2.75274% (no baseline) -> 2.87642% (baseline) -> 2.87578% (all pixels) -> 2.87559% (M34's form); `frac_exact` is 48.6897% with **and** without baseline subtraction | Baseline subtraction cannot move an argmax, so it cannot change the fraction. M34's explanation of the mean is exactly right and of the fraction is wrong; the apparent 2.4 pp fraction gap was manufactured by fact 288's inversion and is really 0.23 pp of pixel-population difference | M36 (MEASURED, `V07`) |
| 296 | **M34's tie-break perturbation is provably inert for the three real-valued channels and provably dominant for C4.** `1e-12 * ptp` is 1.9e-5 / 3.2e-4 / 1.2e-4 of the float32 spacing at each channel's p95 threshold, with **zero** non-tied pixels inside it; union and all Jaccards are bit-identical across eps in {1e-18, 1e-12} and with no tie-break. Removing it moves C4's Jaccards from 0.0251/0.0281/0.0260 to 0.0036/0.0181/0.0375 | Refutes the tie-break hazard for C1/C2/C3 and independently **confirms** fact 284's claim that C4's overlaps are 99% tie-break by construction | M36 (MEASURED, `V02`) |
| 297 | **M32's roughness temperature is confirmed independent of the noise model.** An analytic delta-method sigma_f (Sobel Jacobian propagated through the box filter, validated against finite differences to 1.4e-6 against typical values 7.8e-2) agrees with `rough_sigma` to **0.967–1.044x** across all six texture bins | The model-free temperature really is model-free, which is the load-bearing part of fact 261's robustness argument — even though the *magnitude* it is used to compute is wrong (fact 286) | M36 (MEASURED, `V09`) |
| 300 | **Question 70 cannot be answered from existing captures, and the gate that says so is M33's own.** Adequacy headroom is **2.18×** for `119MSDCF` (33 fr, f/5.6) and **2.10×** for `112MSDCF` (79 fr, f/11), against **3.62×** for `coffee-bean` (105 fr, f/8) recomputed by the same code | Both candidate stacks are **too coarsely sampled to serve as their own ground truth** — decimating them measures the grid, not the estimator. The shortfall is **frames, not light**: `119MSDCF` also has **7.38%** of pixels peaking at the very edge of its bracket, so 33 frames did not cover the subject's depth. `captures-needed.md` §7 extended — the already-requested aperture pair now needs **2.5× the normal frame count** | M35 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 301 | **The deficit ladder's log–log slope is a second adequacy diagnostic, and a cheaper one.** Deficit should grow as **h²** near a smooth peak. `coffee-bean` measures **1.818**; both failing stacks sit at **1.129 / 1.094** | **A sub-quadratic slope is the signature of a reference that is itself under-sampled** — if the reference already misses the peak, decimating adds less than `h²` because much of the deficit was present at `h=1`. It agrees with the headroom test on all three stacks while being computed differently, and **it needs no extrapolation, so it should be the front-line check** | M35 (MEASURED + DERIVED mechanism) — **NOT INDEPENDENTLY VERIFIED** |
| 302 | **The log fit beats the parabola on every stack — 2.05× / 1.53× / 1.79× — across a 2× range of marked aperture and a 10× range of ISO**, and in all twelve cells measured across two factorials | **This survives the failed adequacy gate, and the reason is general: a ratio between two estimators scored against the SAME reference is robust to a multiplicative error in that reference, because it cancels. An absolute calibration against the same reference is not.** So the part of M33 that M18 actually needs — *which* estimator — generalises, while the part that does not generalise is the part nothing depends on | M35 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; the absolute calibrations for `119`/`112` are **not reportable** |
| 303 | **M33's published calibration reproduces exactly from independently written code: 0.457 / 0.710 / 51.2%**, to three decimals on all three | Confirms M33's arithmetic (its *design* is fact 304). Also resolves an apparent 20% disagreement with M35 script 02 that looked like one of the two milestones being wrong: they compute **different statistics** — median-of-per-pixel-ratios versus ratio-of-means, on different baselines and pixel sets. **When quoting a calibration number, quote M33's cell**, which is the one that reproduces | M35 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 304 | **Fact 272 had a real confound, now priced, and it survives: 9% of its margin is the baseline and 91% is the log domain** (3% / 97% at ×4). M33 script 04 ran `parabola-raw`, `log-raw` and `log-baseline` but **never `parabola-baseline`**, so its headline changed two things at once. The missing cell reads **0.479** against the raw parabola's 0.457 and the log fit's 0.710 | **Fact 272 is better supported than when published**, because the alternative explanation has been measured instead of dismissed. The relative deficit `1 − a0/peak` is not shift-invariant for the parabola either, so this was not a nitpick — it could have gone the other way. **My pre-registered guess (⅓ of the margin) was falsified in the fact's favour**, and was registered before running precisely because fact 272 was already folded | M35 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 310 | **The estimation merge is built** (`crates/strehl-core/src/merge.rs`, 21 tests, 91 passing workspace-wide, clippy clean). Two-pass: pass one folds each frame's **17×17-regularised** focus field into a winner map, pass two admits every frame within the gate of the winner and averages them in native raw DN. Both passes are commutative and associative, pinned by test rather than assumed | Facts 84 and 19 stop being priced-but-unbuilt. **"Never noisier than one frame" is now a proof rather than a measurement**: the winning frame is admitted unconditionally at its own pixels, so `n_eff ≥ 1` structurally, and averaging `n` independent frames scales σ by exactly `1/√n` — the test asserts the exact factor, not an inequality. Two passes because the gate needs each frame's response relative to a winner not known until all frames are seen; this answers the review's §6 architectural seam in favour of **two-pass**, not sufficient statistics | M37 (BUILT + MEASURED) — **NOT INDEPENDENTLY VERIFIED**; no real-data run yet, see question 90 |
| 311 | **`FOCUS_NOISE_SD = 0.015214 ± 0.000075`** — the SD of the σ-normalised regularised focus response under pure noise, measured in-crate over 12 seeds on a 512² plane. It implies **~348 effective independent samples** against a nominal `43×43 = 1849` combined support | The gate threshold can be **a single pure number** rather than a per-pixel field, because `FocusField::compute` already divides by the model's σ — which is what makes one threshold valid across the frame and across ISOs. **Assuming independence would have made the gate 2.3× too tight**: stencil overlap and the box-of-box weighting cost a factor of 5.3, and no closed form could have supplied it. The response mean also matches the closed-form Rayleigh value `0.5427` to <3%, which is the structural check that the operator chain is what the measurement assumes | M37 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 312 | **A plain LCG in the test harness made the constant vary 1.30× across seeds** (0.01172 / 0.01371 / 0.01522); SplitMix64 cut it to 1.05×, which is itself consistent with the effective sample count | Consecutive LCG outputs lie on lattice planes, Box-Muller consumes them **in pairs**, and filling a raster grid lays that lattice out *spatially* — where a 27-box followed by a 17-box aliases against it differently per seed. **A single-seed measurement would have baked a 30% error into the gate and looked completely stable.** The multi-seed check is what caught it; nothing about the number looked wrong | M37 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 313 | **A sample SD over a region a few supports across is biased low: 192² reads 0.01366, 10% under.** 384² gives `0.015277 ± 0.000223` and 512² `0.015214 ± 0.000075` — **0.27 σ apart, so the bias is spent by 384²** | The mean a sample SD subtracts is itself correlated with the samples when the field has a 43×43 correlation length. The drift with plane size is a *falsifiable signature*, not a mystery, and it was diagnosed by predicting the next point rather than by inspection — **the prediction's direction was wrong (I expected a further rise) and its magnitude right**, which is what identified convergence rather than confirmed a story | M37 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 314 | **The regulariser is dilution by `W²` and nothing more.** A `W×W` box divides a spike's excess by `W²`, so against a response deficit `d` the break-even spike is `d·W² + baseline`: at `d = 0.1`, `W = 17` that is **29.8**. A 20× spike is killed; a 50× spike survives | Bounds fact 23's speckle win rather than mythologising it. The test asserts **both** outcomes deliberately: a test that only showed the spike dying would not distinguish this regulariser from an arbitrarily strong one, and would pass just as well if the width were wrong. It also says plainly that the regulariser is **not** a robust estimator — outlier rejection (M28's mask) is a separate mechanism and is still unbuilt | M37 (MEASURED + DERIVED) — **NOT INDEPENDENTLY VERIFIED** |

| 320 | **The estimation merge runs on real frames and passes invariant 1.** `109MSDCF`, 22 frames, six-gate sweep including two full decode passes in **2.9 s**. Flat-ROI noise ratio **1.074x** at gate 0 (pure regularised selection), **0.973x** at gate 1.0, **0.890x** at gate 2.0. Two independently-chosen ROIs agree to within **0.6%** at every gate | **The thesis is measured on our own photographs.** **QUALIFIED BY FACT 343:** this row originally read the win against fact 19's 1.253×, which M39 could not reproduce on the shipped operator. The defensible same-operator comparison is **0.890× against 1.0739×**, a 17% improvement. The ROIs were chosen by M2 on structural grounds long before this code existed, so neither was selected by this outcome | M38 (MEASURED) — **verified by M39**; baseline claim superseded by fact 343 |
| 321 | **Gate 0 reproduces an independently measured number to 0.1%.** Pure regularised selection with no averaging measures **1.074x** where M2-verification measured **1.075x** for the same operation (fact 23) — different language, different author, different harness, a year of intervening design | **Worth more than the pass it accompanies.** It says the whole pass-one chain — decode, black subtraction, green luma, Tenengrad against the injected noise model, 17×17 regularisation, argmax — reproduces end to end. The merge is not trusted because it looks right | M38 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 322 | **Mean \|∇\| is confounded by noise, and the confound has the same sign as the effect.** Uncorrected, detail fell **−45%** across the gate sweep on both ROIs — fact 24's collapse, apparently on schedule. Removing the model-predicted noise contribution (`corrected = sqrt(raw² − model²)`, exact for forward differences) leaves **−4.6%** and **−3.6%**. **~90% of the apparent detail loss was noise removal scored as blur** | **The verdict inverted.** An uncorrected reading charges the merge for doing the one thing it exists to do, so the metric could not distinguish success from failure. The same confound runs backwards through fact 24 itself: argmax "raises" gradient there and also raises noise 1.253x, so part of that flattering number is the defect. Model term validated against hand calculation: 17.1412 DN predicted vs `2σ = 17.14` | M38 (MEASURED) — **verified by M39, and SUPERSEDED IN THREE PLACES.** Direction and conclusion hold and were reproduced cell-for-cell (fact 340), but: **−4.6% is pessimistic, not an upper bound** — the model under-subtracts at gate 0, so the true loss is −4.6% … −0.5% (fact 341); **"~90%" is 77.5% / 81.4%** within one statistic (fact 345a); and **the FPN caveat originally named here is ~40× smaller than the unnamed noise-model-scale sensitivity of ±2 pp** (fact 342). Read this row only with 340-345 |
| 323 | **Fact 24's gradient convention, identified by measurement rather than assumed.** M2's harness is not preserved, so seven candidate definitions were computed with an **independent numpy implementation**: `mean(0.5(\|dx\|+\|dy\|))` reproduces the published 11.89 and 18.58 to **0.01% and 0.02%**. The pre-registered guess — single-axis `\|dx\|`, from the exact `π/2` ratio the observed 1.552 and 1.600 appeared to bracket — matched one ROI and **missed the other by 17.5%**, because that ROI is **1.43× anisotropic** | **A single-ROI check would have confirmed a wrong answer.** Same shape as facts 73, 203 and 211: a quantity reading confidently while its assumption is absent. Two consequences — there is **no constant conversion** between the harnesses, so comparison against fact 24 must be made in fact 24's convention (now a reported column); and the same script cross-validates the new Rust metric against numpy at ratio **1.0000** | M38 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 324 | **The gate does not transfer, and a fixed threshold is not a calibration.** At gate 2.0, `mean n_eff` runs **2.258, 2.891, 4.774, 6.226, 7.422** across `119MSDCF`/`109MSDCF`/`113MSDCF`/`112MSDCF`/`coffee-bean` — a **3.3× range**. But `n_eff/N` clusters at **0.068–0.079** for four of five, so the acceptance set is roughly **a fixed fraction of the bracket, not a fixed count**. Solving each stack for `n_eff = 3` needs thresholds spanning **1.1 to 2.9** | **Answers question 90 by refusing its premise, and would have shipped wrong**: gate 2.0 is the honest reading of `109MSDCF` and a **2.6× error** on `coffee-bean`. The threshold must be **solved per stack against a target `n_eff`**, which pass two can do in one sweep since many accumulators cost one decode. §4.1's "profiles as data, not constants" arriving in a new place. Consistent with fact 213 (`coffee-bean` 2–4× over-dense). `109MSDCF` at 0.131 is unexplained | M38 (MEASURED) — **NOT INDEPENDENTLY VERIFIED**; whole-image statistic, so no ROI was selected by outcome |

| 330 | **The gate is now solved, not chosen, and the solve is confirmed end to end.** `--target-n-eff` interpolates the measured ladder in log-log and returns a gate. On `109MSDCF` it returned **2.0964** for a target of 3; re-running at that gate measured **2.989**, an error of **0.37%**. On `coffee-bean` the same target returns **1.1063** — **1.9× apart for the same statistic** | **Fact 324's conclusion, in working code.** Interpolation is not a measurement, so the confirmation run is the result and the solve is only the hypothesis; the CLI says so in its own output and tells the user to re-run. Log-log is exact on a power law and near-exact here (a linear ladder interpolation would have been 11% low on the same rungs, biased the same way on every stack). Pass two folds every rung for one decode, so the ladder *is* the solve and no bisection pass is needed | M38 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |
| 331 | **`coffee-bean`'s acceptance set is strongly bimodal, and its boundary fraction is gate-invariant.** At gates 0.5/1.0/2.0 the mean `n_eff` is 1.52/2.57/7.42 while the share of pixels admitting **only** the winner stays at **77.5%/68.3%/62.6%** — so a large minority averages dozens of frames while most of the image averages one. `boundary %` is **7.60% at every gate**, exactly as it must be | The bimodality means **mean `n_eff` is a poor summary for this stack** and a target expressed through it will under-serve the majority of pixels; a percentile or the `n_eff = 1` share is the better control variable, which is a live design question rather than a defect. The invariant boundary fraction is a **free internal consistency check that passed**: boundary depends only on the winner field, which the gate cannot move, so any gate dependence there would have been a bug | M38 (MEASURED) — **NOT INDEPENDENTLY VERIFIED** |

| 340 | **M39 independently reproduced M38 cell-for-cell, and confirmed claims A, B and C.** A numpy re-implementation of the merge, written from `merge.rs` by a different author, matched **every cell of both six-gate tables to 4 dp** (ROI A −45.49%/−4.58%, ROI B −44.66%/−3.57%). The `2σ_i² + σ_{i+1}² + σ_{i+w}²` structure was re-derived before reading M38's version and confirmed by 4×10⁶-trial Monte Carlo under non-uniform σ, which separates it from all sum-preserving rivals by 24–39 against its own 0.096 error | **The first independent verification in the project since M2.** It is an independent *implementation* but explicitly **not an independent specification** — it was written from `merge.rs`, so a shared misreading of intent would survive both. Reproduction to 4 dp across two languages does exclude arithmetic and indexing error | M39 (MEASURED, INDEPENDENT of M38's author) |
| 341 | **DEFECT, confirmed by re-run: the corrected metric leaves selection noise in.** `predicted_sigma` returns exactly **1.000×** the single-frame σ at gate 0, where the measured ratio is **1.074×** — the model does not know that selection *adds* noise. Consequence, on a **flat** ROI where no detail can exist, the shipped metric credits regularised argmax with **+35.47% "detail"** (and +32.37% unregularised) | **A falsification test M38 never ran, and it fails.** A flat ROI has no detail, so any gain is pure artifact. Because gate 0 is the denominator of M38's retention figure, **−4.6% is pessimistic**: the true loss lies in **−4.6% … −0.5%**, so fact 322's conclusion survives and strengthens while its number is wrong. The repair is to carry the measured selection inflation, not `σ/√n`, at n = 1 | M39 (MEASURED) — re-run and confirmed by M38's author |
| 342 | **The error budget was inverted: M38 flagged the small caveat and missed the large ones.** Fixed-pattern noise, which M38 disclosed as its one bound, is worth **0.01–0.05 pp** at M4's measured 0.377 DN DSNU. Noise-model **scale**, which M38 did not flag, is worth **±2 pp** (`k ∈ [0.96, 1.05]` moves the result across −6.3% … −2.2%) — and the run's own banner already calls that model DERIVED rather than measured | **The disclosed uncertainty was ~40× smaller than two undisclosed ones.** Disclosing a caveat is not the same as ranking them, and an unranked budget flatters whichever term the author happened to think of. Any sensitivity claim must sweep the inputs the pipeline itself marks as underived | M39 (MEASURED) |
| 343 | **Fact 19's 1.253× does not reproduce on the shipped operator; fact 23's 1.075× does, exactly.** On the same 22 frames and flat ROI, the shipped normalised Tenengrad gives **1.0678× unregularised** and **1.0739× regularised**. The regularised value matches M2-verification's 1.075× to 0.1%; the unregularised value misses 1.253× by a factor the regulariser cannot explain, because here regularising *raises* the ratio slightly instead of dropping it | **The baseline the project quotes is operator-dependent, and the merge's headline win was stated against the half that does not reproduce.** The defensible comparison is same-operator, same-frames: merge **0.890×** against regularised argmax **1.0739×**, a **17%** improvement rather than the 29% implied by 1.253×. Fact 19 is not thereby refuted — it is a different focus operator — but it may not be quoted as this pipeline's baseline. See question 100 | M39 (MEASURED) — **the strongest open discrepancy in the corpus** |
| 344 | **The positive control M38 never ran is the strongest evidence for its own claim.** A plain mean of all 22 frames reads **−48.43%** corrected on ROI A against the merge's −4.6%: the corrected metric discriminates a real detail-destroyer from the merge by a factor of **10.6**, where the uncorrected `m2` separates them by only **1.3**. The same run reproduces fact 24's published −58%/−53% to **0.2 pp** | **Invariant 2 genuinely separates success from failure, which no measurement in M38 established.** M38 showed the metric was confounded and corrected it, but never demonstrated the corrected version still *fires* — a correction that removed the confound and the signal together would have looked identical. The free replication of fact 24 also confirms the convention identification in fact 323 from a second direction | M39 (MEASURED) |
| 345 | **Three smaller defects, none fatal.** (a) M38's "~90% of the loss was noise" compares `m2` against a corrected RMS — **within one statistic it is 77.5% / 81.4%**. (b) The metric is an RMS over a top-heavy distribution: the top 10% of pairs carry **73.5% / 78.2%** of the energy, so deleting **all** low-contrast texture costs only **−0.66%** corrected — it measures strong edges, not texture. (c) The `(2,1,1)` coefficient structure **ships untested**: all seven `detail_metrics` tests use uniform σ, which cannot distinguish any coefficient set summing to 4 | (b) is the one that matters for scope: the invariant is a strong-edge metric and must be described as one, since a merge could destroy fine texture and pass it. (c) is a real test-coverage hole in code that passed review — the Monte Carlo that *can* separate the coefficients exists now in M39 and should be ported into the crate | M39 (MEASURED) |
| 170 | **MEASURED.** The per-edge metacalibration response on `coffee-bean` span-1 edges is **0.5264 at δ=1e-4 and 0.9928 at δ=8e-4** — a swing of **0.4664**, 3.1× the pre-registered refutation threshold of 0.15. **Metacalibration's local-linearity premise is refuted on this data**: there is no single `R` that characterises an edge, so the identity `L' = L/R` holds at no `δ`. This alone is sufficient to reject R4, before any gate is scored. | **R4 is rejected on its premise, before any gate is scored.** The review's #4-ranked proposal has no valid identity to apply. Any future response calibration on this project must first publish `R(δ)` over at least a 4× δ range and show it flat | M23 §5.1 |
| 171 | **MEASURED.** A single edge's response carries **23.7% fractional noise** at `δ=1e-4` and 11.9% at `2e-4` on `coffee-bean` span-1. Because `E[1/R] > 1/E[R]`, dividing by a per-edge `R` inflates on average even when `R` is pure noise. At the primary δ the total inflation is `mean(1/R) = 1.629` (+62.9%), of which the noise-driven Jensen part is a factor **1.0134** (+1.3 percentage points) and the rest, `1/mean(R) = 1.608`, is the response's **central tendency** — that is, the correction is overwhelmingly a scalar wearing a per-edge costume. | **Every per-edge division must be Jensen-audited.** Report `mean(1/R)` and `1/mean(R)` separately: their gap is the noise-driven inflation, and it is *not* the bias being corrected. A correction whose average effect survives shuffling is magnitude inflation | M23 §5.4 |
| 172 | **MEASURED.** The small-δ metacalibration response deficit is caused by the **plant's own bilinear resampler**, not by the defocus asymmetry it was meant to calibrate. Measuring a `coffee-bean` frame **against itself** — zero defocus difference, identical content, identical plant — gives `R = 0.372` at `δ=1e-4`, *further* from unity than any real defocus pair (0.526). Running the identical probe against a synthetic band-limited field rendered as point samples at the composed transforms, with **no interpolator anywhere in the path**, gives `R = 0.965` (12 independent noise realisations, sd 0.0071, range [0.953, 0.976]). Removing the defocus makes the response worse; removing the resampler fixes it. **The response is not a response to the defect.** | **A plant's own resampler is a first-class confound, with a size-dependent signature.** The self-pair arm — real content, real plant, zero defect — is now mandatory for any planted-increment probe here. Discipline 81 | M23 §6 |
| 173 | **MEASURED.** The deficit is a **sub-pixel locking artefact**, not a resampler bandwidth artefact. Composing the same single bilinear warp off a `4e-3` scale pedestal — a ≈4.8 plane px differential displacement, so no tile sits near zero fractional offset — moves real `coffee-bean` pairs from `R = 0.5465` to `R = 0.9533` and self-pairs from `0.3719` to `0.9346` at `δ=1e-4`, **with the defocus completely unchanged**. *Confound, stated: the pedestal moves the operating point as well as leaving the locking zone, so this arm changes two things at once; it is corroboration of fact 172, not an independent proof.* | **The fix for span dependence is a phase dither or an upsampled correlation peak, not a calibration.** Opens question 25, which is the live thread M23 leaves behind | M23 §6 |
| 174 | **MEASURED, correction to the corpus.** Fact 45's attribution of the planted-increment under-response to *defocus* is not supported. The control that would have decided it — real content, bilinear plant, zero defocus — was measured here (`cb-self`) and reads **0.372 at δ=1e-4**, *below* the real-pair value fact 45 attributes to defocus. Fact 45's numbers reproduce; its causal reading does not. **This does not disturb fact 43 or the M12 ruling**, which rest on the conservation identity `1/S_W(1)` computed from *unplanted* edge measurements and involve no resampler at all. | **Fact 45's causal reading is withdrawn; its numbers stand.** Fact 43 and the M12 ruling are unaffected — they rest on the correlation, not the attribution | M23 §6 |
| 175 | **MEASURED.** Per-edge response calibration moves `coffee-bean`'s conservation ratio from **3.2604** to **1.9095** at δ=2e-4 (**PARTIAL**, never reaching the 1.0 the identity requires), and a **shuffled** `R` carrying zero per-edge information reproduces **93.3%** of that movement (2.0005), while a **constant** median `R` reproduces **93.5%** (1.9974). The per-edge content of R4 is worth **6.7%** of an already-insufficient correction. **R4 reduces, in measurement, to the scalar correction M12 refuted.** | **The per-edge content of R4 is worth 6.7% of an insufficient correction.** Discipline 83: register the null's arithmetic. Without the shuffled arm, 3.26 → 1.91 reads as a large win | M23 §7(a) |
| 176 | **MEASURED.** The response is **almost span-independent** where the defect is **strongly span-dependent**: `median R` at δ=2e-4 is 0.6126 (span 1) and 0.6621 (span 2), an 8% difference, while the local telescoping ratio `l(k,k+2) / [l(k,k+1)+l(k+1,k+2)]` reads **1.1816** uncorrected over 103 triples — the span-2 edge sees 18% more than the span-1 pair beneath it. Correcting both by their own responses moves that ratio only to **1.1205**. A correction whose magnitude does not track the defect's span structure cannot restore a telescoping identity. | **Structural, not statistical: a span-independent correction cannot fix a span-dependent defect.** This is the deepest of the nine — no amount of noise reduction in `R` would change it, so R4 could not have worked even measured perfectly | M23 §5.3/§7 |
| 177 | **MEASURED.** Re-admitting metacalibrated span-1–2 edges does **not** beat the 6.758 px held-out baseline on `coffee-bean`. Best corrected `E*` = **6.758 px** (unchanged; the winning training set contains no corrected edge), and on the best short-edge-inclusive training set the correction makes it **worse**: 7.241 → 7.252 px. **Gate (c) FAILS, so R4 ships nothing.** | **Gate (c) FAILS on the pre-registered criterion. R4 ships nothing.** Fact 47 is now bounded from a second side: the short edges are not recoverable by response calibration | M23 §7(c) |
| 178 | **MEASURED.** On the one arm where the correction helps substantially — training on `span ≤ 2` alone, 43.679 → **32.426 px** — both nulls help **more**: shuffled `R` gives **30.931 px** and a constant median `R` gives **31.245 px**. The improvement is undirected magnitude inflation of an under-reporting chain, not per-edge calibration, and a **random** assignment of responses does it better than the measured ones. | **A treatment that random assignment performs better is not the treatment working.** This is the arm that would have been reported as R4's success had the nulls not been run | M23 §7(c) |
| 100 | The box **max** of \|∇L\| does fix fact 73's monotone-edge blind spot: on a 1000 DN hard step, blur σ0→σ3, D goes from **1.0000** (mean, blind) to **0.2592**, matching the analytic prediction 0.2660 to 2.6%. | The reviewer's core claim is correct and is now VERIFIED twice from disjoint code. | M17 §2.1, §2.2; `experiments/m17-dual-response/data/blindspot-nonorm.csv` |
| 101 | The box max **costs +18.91 DN mean `excess_dn`** on M13's 30 occluding-edge cells — **21.7×** the pre-registered +0.87 DN bar — and loses **28 of 30** cells (sign test p = 1.2e-6). | The dual (mean, max) is rejected. Question 19's proposed fix fails the guard question 19 itself made mandatory. | M17 §3, §3.2; `data/edge-{109,119}MSDCF.csv` |
| 102 | The max's cost is **not** noise. Its flat-ROI merged-noise ratio *improves*: ΔN = **−0.0081** (N 1.08637 → 1.07826). Pre-registered prediction 2 (ΔN > +0.05) is falsified. | The premise the dual was designed around does not hold on real data. A response-level CoV does not predict merged-output noise; only the merged statistic decides. | M17 §4; `data/noise-{109,119}MSDCF.csv` |
| 103 | **`tenengrad-sq-w13`** (question 19 candidate (c), `box_mean₂₇(gx²+gy²)/σ²`) is the only arm clearing all four pre-registered gates: D **0.1860**, ΔE **−2.14 DN**, ΔN **−0.0015**, radius-flat cost, and **0.96×** the shipped operator's wall clock. | Recommended replacement for `tenengrad-w13`. The blind-spot fix is available for free — cheaper, in fact, since it drops a per-pixel `sqrt`. | M17 §6, §5.2; `data/m17-analysis.txt` |
| 104 | Candidate (c)'s quality gain is **not robust**: 15/30 cells, median paired Δ **−0.27 DN**, sign test **p = 1.00**. The −2.14 DN mean is one shape in one stack (`vertical@274`/119MSDCF, −16.56); it loses **0/10** on `horizontal@210`. | Sell candidate (c) as **quality-neutral**, never as a quality win. A mean over 30 cells must always be paired with its sign test. | M17 §3.2 |
| 105 | `tenengrad-sq` and `√(box_mean(g²))` (degree-1 normalisation) produce **bit-identical** `excess_dn` and `acc` on all 18 cells — the squared response and degree-2 normalisation are a monotone pair, so candidate (c) carries **no ÷σ² vs ÷σ confound**. | Any future "squared vs magnitude" comparison must apply the matching normalisation degree, or it measures the normalisation, not the operator. | M17 §1; `data/rms-consistency-109MSDCF.csv` |
| 106 | Question 19 candidate (b), dual-radius, is dead on two axes: ΔN = **+0.193** (geo) and **+0.237** (larger), ~10–12× the threshold, and ΔE = +15.4 / +25.5 DN (0/30 cells). `tgrad-larger-w1-w13` reads *exactly* `tenengrad-w1`'s D on every plant — near structure the pointwise max of radius 1 and radius 13 **is** radius 1. | Do not revisit dual-radius. It is a radius-1 operator with extra cost, and M13 already measured radius-1's noise at N ≈ 1.34. | M17 §4, §2.1 |
| 107 | On a **9-px ramp** — the realistic monotone gradient — the max's advantage largely evaporates (D 0.8587 vs the mean's 0.9999) while `tenengrad-sq` holds **0.6802**. A hard step is the easiest case for an extremum statistic. | Fact 73's hard-step plant *overstates* what a max buys. Any future blind-spot claim must include a ramp plant. | M17 §2.3(ii); `data/blindspot-nonorm.csv` |
| 108 | The shipped operator's monotone-edge reading is **±15% of normalisation artefact straddling 1.0**: D = **1.1299** at the bright-side boundary column and **0.8353** one column to the dark side. The **un-normalised** operator reads 1.0000001 on **both** sides. | Extends fact 73: the shipped focus field on a monotone edge is not merely constant, it carries pixel-side-dependent junk of the same magnitude as a real focus signal. Confidence derived from it is worse than uninformative. | M17 §2.3(i); `data/blindspot-norm.csv`, `data/blindspot-nonorm.csv` |
| 109 | On an untextured edge, `max`, `p95`, `p99` and `w0` all read **identically** (D = 0.2483 on the realistic B2 plant): the gradient ridge spans the window, so any percentile above the ridge's area fraction **is** the max. They separate only on texture (p95 0.164 vs max 0.124). | Percentile variants are not a distinct family on the case they were proposed for. Register a textured plant or the comparison is vacuous. | M17 §2.3(iii); `data/blindspot-edge.csv` |
| 110 | Van Herk / Gil-Werman is O(1) in **comparisons** (≈3/element, DERIVED) but this implementation is **not O(1) in wall clock**: **4.90×** over r = 1…40 and **2.69×** `box_mean` at r = 13, against `box_mean`'s ≤ **1.02×** bound. Hoisting all allocation and removing the inner-loop modulo changed nothing; ≈2.9× of the growth is unexplained. | Fact 66's "widening the window is free" does **not** generalise to a running max. Any max-based operator must be re-timed, not assumed. | M17 §5.1; `data/boxcost.csv` |
| 111 | At the shipped radius, whole-measure cost is **0.96×** for `tenengrad-sq-w13`, **1.71×** for `max`, and **≥2.26×** for every dual (a dual pays for both windows). `tenengrad-sq` is cheaper than the shipped operator because it never computes a per-pixel `sqrt`. | The dual's rejection is robust even to a hypothetical flat vHGW. | M17 §5.2; `data/cost-measures.csv` |
| 112 | Exact windowed percentile is **352×** over the radius ladder (818 ms/frame/Mpx at r = 13). | A percentile focus measure is unshippable without a sliding histogram; none was built. | M17 §5.1; `data/boxcost-pct.csv` |
| 400 | **The multi-frame Wiener merge across a focal stack is published, with its error law.** Levin et al., MIT-CSAIL-TR-2009-019 (2009), Appendix B, Eq. (52) is the estimator verbatim; Eq. (53) gives `E[error] = (σ⁻²Σ_j\|φ̂_j\|² + σ_ω⁻²)⁻¹`. **The project's fact 140 re-derived a published result and `SYNTHESIS.md` §6 must not claim it as novel.** | **The novelty claim is withdrawn before it was made.** The review's "complete the thought" framing describes 2009 prior art. strehl may implement this estimator and must cite it; it may not claim it | M19 §9 — VERIFIED (full text)  *(proposed as fact 120; shifted +280, M20-V holds 122–139)* |
| 401 | **Levin's Eqs. (54)–(57) evaluate that estimator for a focal stack and conclude *against* it** — focus sweep is better, by a factor `\|ω\|/Ω` — **but only under a fixed-total-exposure assumption (each of N frames gets 1/N of the light) that a static macro subject does not impose.** Removing it inverts the ordering by `N²`; at N = 22 that is 484×. | **The one crack in the published negative, and the only place a real gain could hide.** Levin's verdict assumes fixed total exposure — each of N frames gets 1/N of the light. A static subject on a tripod does not pay that. Pair with M20's own refutation before acting on either | M19 §9 — VERIFIED (their result) + DERIVED (the inversion, my algebra) |
| 402 | **Unregularised inversion is catastrophic by an externally measured 79 dB.** DeconvolutionLab2 synthetic microtubules: NIF **−75.45 dB**, RIF **+3.47 dB**, same data and PSF. Independent external corroboration of fact 141. | External corroboration of fact 141 from a different modality and a different team. Any inverse filter here must be **regularised by construction, not by option** | M19 §9 — MEASURED (Sage et al. 2017 Table 2) |
| 403 | **Deconvolution measurably degrades the axis where the OTF is weakest.** Real 2.5 µm bead: acquisition axial FWHM **3979 nm**; all six deconvolution settings tested gave **4449–5909 nm**, while lateral improved ≤ **3.3%**. | **Deconvolution degrades the axis where the OTF is weakest, and for a focal stack that axis is depth.** Whatever ships must never sharpen along `k` | M19 §9 — MEASURED (Sage et al. 2017 Table 3) |
| 404 | **A 7-second regularised inverse filter is within 0.19 dB of Richardson–Lucy at 1661 s (237×), and beats commercial Huygens CMLE.** Do not build iterative deconvolution on the strength of this literature. | **Do not build iterative deconvolution.** One regularised inverse filter buys within 0.19 dB of Richardson–Lucy at 1/237 the cost. This is the whole design of the opt-in plugin | M19 §9 — MEASURED (Sage et al. 2017 Table 2) |
| 405 | **Total variation is not a safe default: it MEASURED *worse* than plain RL (3.36 vs 3.66 dB) on a non-piecewise-constant object.** The authors state the ranking is not transferable between object types. | No prior may be shipped as a default on literature strength alone. TV measured *worse* than plain RL, and the authors state the ranking does not transfer between object types | M19 §9 — MEASURED (Sage et al. 2017 Table 2) |
| 406 | **A 30% error in the PSF σ costs no significant topography accuracy, but the in-focus PSF must be precise**; an over-wide PSF causes "out-of-focus information [to be] falsely reallocated to the texture". The accuracy budget along k is asymmetric and peaked. | **The PSF accuracy budget is asymmetric**: in-focus precision matters, defocus width tolerates 30%. That is exactly the direction that makes self-calibration from the through-focus curve cheap enough to attempt | M19 §9 — MEASURED (Aguet et al. 2008) |
| 407 | **Max-absolute-value wavelet fusion puts ≈30% of pixels outside the dynamic range of every input frame**, boosting energy, noise and saturation. Measured by the authors of the method in 2004 — external corroboration of the selection-injects-energy thesis behind fact 19. | **External corroboration of the selection-injects-energy thesis — measured in 2004 by the authors of the method it condemns.** ≈30% of pixels outside the range of every input frame is the defect strehl exists to remove | M19 §9 — MEASURED (Forster et al. 2004) |
| 408 | **A merge expressed as a normalised weighted sum over frames is structurally range-safe; a merge containing a `1/Σ\|H\|²` division is not.** Aguet 2008 gets range safety for free because its texture update is an interpolation among slices. Forster 2004's "reassignment" clamp is the retrofit, MEASURED to reduce ringing (+0.37 to +0.64 dB). | **A structural argument for the normalised-weighted-sum merge strehl already ships, and against the `1/Σ\|H\|²` form the review proposed.** Range safety is free in one and absent in the other | M19 §9 — DERIVED / MEASURED |
| 409 | **Transform-domain fusion's advantage over a plain focus measure is content-dependent and can invert sign on real data**: +2.49 to +4.70 dB on synthetic Brodatz textures, but **−0.58 dB vs the variance method** on real histological tissue without post-processing. | A fusion method's advantage can **invert sign** between synthetic and real content. Never accept a transform-domain win measured on synthetic textures — which is how most of them are measured | M19 §9 — MEASURED (Forster et al. 2004 Tables 1–2) |
| 410 | **The three most relevant papers in three different fields each state that the depth-discontinuity case lies outside their forward model** — Levin et al. 2009 ("a general problem for all computational extended-DOF systems … most artifacts can be eliminated with simple manual layer refinement"), Nagahara et al. 2008 ("we have not explicitly modeled occlusions"), Aguet et al. 2008 ("ignores potential out-of-focus contributions from beneath the surface"). | **The depth-discontinuity case is outside all three forward models, stated by their own authors.** The occlusion work is genuinely open ground — subject to fact 411 | M19 §9 — VERIFIED (all three, full text) |
| 411 | **"First to model the occlusion halo" is FALSE and must not be claimed.** Prior art: Asada et al. 1995/1998 (RPB; explicitly predicts the **non-monotonic** brightness transition that fact 150 measured, 28 years earlier), Bhasin & Chaudhuri 2001, Favaro & Soatto 2003, McGuire et al. 2005, Hasinoff & Kutulakos 2007, McCloskey et al. 2011, Wang et al. 2015. **The defensible claim is "first shipping focus-stacking tool to model it", and even that is `could not confirm`.** | **Withdraw this claim before making it.** The halo has 28 years of prior art, including a paper predicting the exact non-monotonic transition fact 150 measured. The defensible claim is narrower and must be stated that way in any write-up | M19 §9 — VERIFIED |
| 412 | **Wang et al. 2015 give a cheap published remedy for exactly fact 150's bimodality**: at an occlusion boundary the angular patch is bimodal, and splitting it by local edge orientation restores unimodality in each half. The focus-axis analogue is to partition frames by through-focus mode and merge within the mode — **no `α`, `F`, `B` unmixing required.** | A cheap published remedy for fact 150's bimodality already exists. **Try the focus-axis analogue of Wang 2015 before anything bespoke** — it is a strictly smaller change than the two-layer unmixing the review proposed | M19 §9 — VERIFIED |
| 413 | **Ringing has two distinct causes needing different fixes**: FFT circular periodicity ⇒ ghosts (fix: zero-padding or apodization) and band-limiting ⇒ Gibbs/Runge (intrinsic). Sage et al.: *"Fourier-related artifacts frequently appear, particularly in the axial direction since this direction is often sampled to a lesser extent"* — **for this project the under-sampled axis is the focus axis.** | Two causes, two fixes, only one intrinsic. **Zero-padding or apodisation is mandatory, not optional**, and a ringing report that does not say which cause it saw is uninterpretable | M19 §9 — MEASURED (Sage et al. 2017 §4.3.1) |
| 414 | **Blind PSF estimation is scale-degenerate**: `(a·h)*(x/a) = h*x`, and "setting a meaningful value to ‖h‖ is highly nontrivial". Both Forster 2004 and Aguet 2008 pin it by Köhler-style unit-sum-per-slice normalisation. Any self-calibrated OTF must do the same. | Any self-calibrated OTF needs an **explicit normalisation to break the scale degeneracy**, or the estimate is unidentifiable. Both reference implementations pin it the same way | M19 §9 — MEASURED (Sage et al. 2017 §6.1) |
| 415 | **MAP over image and kernel favours the no-blur explanation** (Levin et al. CVPR 2009). Levin et al.'s own tech report notes their depth search works *"because a delta explanation is absent from the search space"*. **Design rule: exclude the zero-blur hypothesis from any per-pixel OTF search.** | **Design rule: exclude the zero-blur explanation from the search space.** MAP over image and kernel otherwise selects it, and the failure is silent | M19 §9 — VERIFIED |
| 416 | **A calibrated physical EDOF simulator with withheld ground truth already exists**: the EPFL 3-D Deconvolution Grand Challenge (ISBI 2013/2014) — advanced PSF model plus a noise generator covering **shot noise, electronic noise and quantisation**, four structure classes, ground truth never disclosed. **Its design is transplantable; its microscopy data is not.** The one element M25's pre-registration does not appear to carry is **per-structure-class scoring** (point / filament / edge / dense texture), which is precisely what exposed the content-dependent sign inversions in facts 125 and 129. | A calibrated physical simulator with **withheld** ground truth already exists. Constrains M25's design — learn the spec, and do not read the GPL code | M19 §9 — VERIFIED (challenge page) |
| 417 | **Fourier Ring Correlation and image decorrelation analysis measure resolution with no ground truth** — FRC from two independent noisy realisations, decorrelation analysis from a single image. **FRC cannot be fooled upward by noise amplification**, which is precisely the defect fact 145 found in `mean \|∇\|`. The corpus already contains an independent pair (fact 52: `112MSDCF`/`113MSDCF`). | **FRC cannot be fooled upward by noise amplification**, which is precisely how a deconvolution metric fails. This is the ground-truth-free instrument strehl needs to score any sharpening honestly | M19 §9 — VERIFIED |
| 418 | **The reference implementation of *both* Forster 2004 CWT-EDF and Aguet 2008 2.5-D EDOF is the same GPL-3.0 ImageJ plugin** (`bigwww.epfl.ch/demo/edf/`). DeconvolutionLab2 and PSFGenerator are also GPL-3.0. All four papers are readable and complete enough to reimplement from; **none of the code may be read.** | All four reference implementations are GPL-3.0. **Papers readable, code untouchable.** The licence hygiene rule holds with no exception available | M19 §9 — VERIFIED (repo metadata) |
| 419 | **In astronomy the same select-vs-reconstruct choice has been live for 30+ years and both still ship** — lucky imaging (Fried 1978; Law et al. 2006) selects; MFBD/MOMFBD (Schulz 1993; van Noort et al. 2005) reconstructs. **The disanalogy: astronomy's PSFs vary randomly and are unknown, with no occlusion; a focus stack's vary systematically and are modellable, but the object occludes itself.** | After 30+ years in a field with harder physics, **both select and reconstruct still ship**. Evidence for strehl's plugin stance over picking a winner in the core | M19 §9 — VERIFIED / ARGUED |
| 420 | **MEASURED. The through-focus statistics are provably non-perturbing.** 109MSDCF merged twice at gate 2.0, once with `--stats --stats-placebo` and once without: SHA256 `DF6C3DE2…C815EE` **both times**, byte-identical over 3516×2344×3 16-bit pixels. Two gathers, a second `box_mean` at radius 2 and a full permutation placebo moved **not one output bit**. | **This is the strongest single check in the corpus, and it is the right shape for all future observers.** A statistic that claims not to affect the merge should prove it by hash, not by argument. Adopt this as the standard for every diagnostic channel strehl adds | M18 §1 + `nostats.tif`/`withstats.tif` |
| 421 | **MEASURED/DERIVED. The seam is two-pass, and the per-pixel state is 60 bytes, constant in the frame count.** Anchored on pass one's regularised winner `k*`, the parabola triple `(f[k*−1], f[k*], f[k*+1])` has each slot written by **exactly one** frame, so the fold is exactly commutative and associative — what `par_chunks` requires. The fine focus **volume** would be `4N` B/px: 725 MB at 22 frames, 1088 MB at 33, **3461 MB at 105**. `ThroughFocus` is **494 MB at every stack depth**. | **Resolves the review's item 6, the architectural seam it said must be decided before the merge is written — and the answer is two-pass, not a fatter fold.** Break-even is 15 frames and the corpus starts at 22, so the ratchet wins everywhere it is used and the margin grows without bound | M18 §1 |
| 422 | **DERIVED. The posterior entropy is computed over *all* frames, not the top-k, and cannot overflow.** With `u_k = (f_k − anchor_focus)/T`, `u_k ≤ 0` **by construction** because `anchor_focus` is the max over frames, so `exp(u_k) ∈ (0,1]`. `Z = Σexp(u_k)` and `W = Σu_k·exp(u_k)` are exactly mergeable, giving `H = ln Z − W/Z`. | **Necessary, not merely elegant: fact 283's p99 perplexity is 4.74, sitting exactly at the `TOP_K = 4` cap.** Anything computed from the top-k list alone is truncated precisely where it is most interesting. The temperature is fact 260's calibrated `T = √2·FOCUS_NOISE_SD`, never `std_k(f_k)` | M18 §1 |
| 423 | **MEASURED. The fine (r=2) focus field is 5.94× noisier than the selection field.** Over 12 SplitMix64 seeds on a 512² plane: fine r=2 sd **0.090400 ± 1.70e-4**; coarse r=13 **0.018847**; regularised r=13-then-8 **0.015214**. | **The last row reproduces the shipped `FOCUS_NOISE_SD = 0.015214` exactly — the instrument check.** The same harness that measures the new constant recovers the old one, which is what licenses believing the new one | M18 §1 |
| 424 | **MEASURED. The fine argmax disagrees with the regularised winner at 78.081% (109MSDCF) and 79.237% (119MSDCF) of pixels — and this is not a defect.** It is a 5.94× noisier field behaving as one. The screening flag is therefore `fine_peak_outside_triple` (off by ≥2, so the parabola cannot reach it): **54.843% / 57.247%**. | **Off-by-one disagreement is harmless because the triple still brackets the fine peak.** A raw-disagreement flag would have fired on four-fifths of the image and been discarded as noise; the bracketing form is the one that carries information | M18 §1 |
| 425 | **MEASURED/FORCED. The statistics must be gathered at 5×5, not at the 27×27 selection window.** Fact 152 measured bimodality enrichment at **4.38× at radius 2** and **0.36× — depleted — at radius 13**. | **A bimodality statistic read at the selection scale measures nothing.** The cost is the noisier fine field of fact 423, and it is not optional — the two scales cannot be shared, so the merge pays for two fields | M18 §1 + fact 152 |
| 426 | **DERIVED. The parabola is used for position and explicitly not for height.** Fact 273 gives the parabola 4.03× over argmax for *position* and disqualifies it for *height*, so height comes from a log-domain fit with baseline subtraction (`subframe_deficit`, facts 272/302/304) using the retained `floor`. | **One estimator, two uses, only one of them valid — and the split is honoured in the retained state rather than in a comment.** `triple` serves position; `floor` exists solely so height never reads off the parabola | M18 §1 + facts 272/273/302/304 |
| 427 | **PROCESS. M18's brief was stale in three of four items and saying so was the deliverable.** Items 1 and 2 were already built; the stated test baseline of 70 was actually **107**; and the acceptance target "bring the merge under 1.0×" was quoted against the pre-M37 binary when M38 already reached **0.890× at gate 2**. | **Milestone numbering is not the order the work happened in, and a brief written before a reordering will silently ask for work already done.** Every implementation brief from here must be checked against the tree before code is written, and the check reported. Discipline 254 | M18 §0 |
| 428 | **MEASURED. Fact 341's defect is repaired, and the repair is worth 3.1× in the artifact it was raised against.** `predicted_sigma` now carries `SELECTION_INFLATION = 1.074` at `n = 1`. On `109MSDCF` with the **flat** ROI `2272,1344,256,256` passed as the *detail* ROI — the negative control M38 never ran — corrected gate-0 detail moves from **+35.47%** (fact 341) to **0.885× = −11.5%**. The measured flat-ROI noise ratios are **unchanged** at 1.074× / 0.973× / 0.890×. | **The spurious credit is gone, and the unchanged noise column proves the merge output did not move — only the prediction did.** The constant is the measured one twice over (1.074× fact 320, 1.075× fact 23), not a fitted knob, and a test pins it there | orchestrator, post-M39 — **MEASURED, NOT INDEPENDENTLY VERIFIED** |
| 429 | **A shipped acceptance invariant was false, and its test could not have failed.** `the_merged_estimate_is_never_noisier_than_a_single_frame` asserted `merged ≤ single` at every gate, reasoning that averaging scales σ by `1/√n` and `n ≥ 1` is structural. **That reasoning is wrong at `n = 1`**: one admitted frame is not averaging, it is *selection*, and fact 320 measured selection at **1.074× a single frame**. The test passed only because `predicted_sigma` was blind in exactly the same place — **it was proving an invariant against a model that could not express its violation.** | **Fifth no-power check found in this corpus, and the first inside shipped Rust rather than an analysis script.** The invariant now has two branches: `n ≥ 2` strictly beats one frame, `n = 1` is measurably worse. That is *why the gate exists* — it is the mechanism that moves pixels off `n = 1` — and why **gate 0 is a diagnostic, not a shipping configuration**. Rule 20 and discipline 253 now both have a code-side instance | orchestrator — **DERIVED from facts 320/341**, test rewritten to the two-branch contract |
| 430 | **OPEN. The repair overshoots on the flat ROI: −11.5% where a no-detail region should read ≈1.0×.** The artifact fell 3.1× in magnitude and **flipped sign**, from crediting detail that cannot exist to charging a penalty that also cannot exist. Confounded by the ROI not being strictly detail-free — the single-frame corrected reading is 14.7270, not 0, and much of the region is out of focus in the reference frame. | **Do not report −4.6% … −0.5% (fact 341's revised band) as settled.** The gate-0 denominator moved again, so M38's retention figure needs re-deriving a third time. Question 101 | orchestrator — **MEASURED, NOT INDEPENDENTLY VERIFIED** |
| 431 | **The `n > 1` selection penalty is unmeasured and deliberately set to 1.0.** The acceptance set at any gate is still chosen by a noise-dependent criterion, so some selection bias survives averaging. `selection_inflation(n) = 1.0` for `n ≥ 2` makes `predicted_sigma` a **floor** there, not an estimate. | **Stated in the code, not just here** — the doc comment on `selection_inflation` says which branch is measured and which is assumed, so the next reader cannot mistake the assumption for a measurement. Feeds question 80 | orchestrator — **ASSUMED, flagged as such** |
| 432 | **M31-V's "31x31, the shipped scale" is correct, and the shipped constants do not say 31.** `WINDOW_RADIUS = 13` gives a 27x27 focus box; `REGULARISER_RADIUS = 8` gives a 17x17 regulariser. `merge::regularise` box-means the focus field that `focus::compute` has **already** box-meaned, so the kernels compose, and boxes compose additively in variance: `60.667 + 24.000 = 84.667`, whose variance-equivalent single box is **31.89 taps** | **Recorded to protect a correct number from a plausible-looking correction.** A reader checking M31-V against the code finds 27 and 17, sees 31 in neither, and has every reason to think the verification swept the wrong scale — the orchestrator did think exactly that, and spent a pass proving itself wrong. The general form: **when two smoothing stages are applied in series, the scale that matters downstream is neither of their widths**, and a milestone that names the composed scale is more right than one that names a shipped constant. Cite this row alongside any future reading of the 1.4x | orchestrator (DERIVED, arithmetic verified; kernel composition verified against `merge.rs:137` and `focus.rs:212`) — **NOT INDEPENDENTLY VERIFIED** |
| 433 | **Fact 243 quotes the weaker of two numbers M30's own script wrote.** The row states **1.89%** newly clipped at +2 EV on `coffee-bean`. That is `clip_at_p2` from script 02, measured at the **middle** frame. `01-dynamic-range.json` — the same milestone, the same stack, the same run — records `new_clip_at_p2 = 0.07049`, i.e. **7.05%**, measured at the **best-focus** frame, which is the frame the merge actually gathers. **3.7x** | **The milestone understated its own conclusion.** Fact 243's point is that +2 EV is the wrong direction for highlights, and the number that makes that point hardest was sitting in its own output file, unquoted. This is not an arithmetic error and no recomputation would have found it — **it is a choice of which frame to report**, which is exactly the defect class rule 24 names. New discipline 255: **before quoting a milestone's number, grep its own artifacts for the same quantity**; where two exist, the row must say which condition each belongs to and why the quoted one was chosen | orchestrator (MEASURED — read directly from `experiments/m30-hdr-cobracket/out/01-dynamic-range.json` and `02-fixed-light.json`, not from M30's prose; independently corroborates M31-V correction 3) — **NOT INDEPENDENTLY VERIFIED** |
| 434 | **Re-derived verdict on HDR co-bracketing: unchanged in what it recommends, inverted in why.** The three supports of fact 243 fare differently under M31-V. *Allocation neutrality* (fact 240) is **CONFIRMED** — re-derived by hand and by Monte Carlo — so "do not default it" stands. *The clipping dodge* (fact 242) is **WITHDRAWN**: gathered frames clip at **0.1293%** against a random-frame null of **0.1710%**, a **1.32x** advantage, not 2.3x. *The direction* (−2 EV, not +2 EV) is **STRENGTHENED** by fact 433 | **Support it, do not default it, trigger it per stack — but the trigger fires roughly twice as often as M30 implied.** M30's reasoning was that highlights are disproportionately out of focus, so a selector already avoids much of the clipping and the highlight case is "roughly half what a whole-stack figure suggests". At the scale the pipeline actually ships, that halving is 1.32x and mostly gone. **The conclusion survives on a weaker premise, which means it is now better supported than when it was written**: less of it rests on the selector being clever. R19's advisory must compute its trigger at the **regularised** gathered frames | orchestrator (DERIVED from facts 240/242-as-corrected/433; inputs MEASURED by M30 and M31-V) — **NOT INDEPENDENTLY VERIFIED** |
| 435 | **And 7.05% is a lower bound, by the same mechanism that killed fact 242.** `new_clip_at_p2` is evaluated at a **raw-argmax** best frame. Fact 242's measured mechanism is that the argmax *flees* clipped frames, because clipping flattens the local gradient (median focus 262.26 clipped vs 311.11 unclipped). So the frames it evaluates are systematically **dimmer at clip-prone pixels** than the regularised winner the merge actually gathers, and a dimmer pixel newly clips less at +2 EV | **The same rule-4 violation biases two numbers in opposite directions, and only one of them was caught.** It made fact 242's clipping advantage look 1.7x too good and it makes fact 433's +2 EV penalty look too small. **A defect in a shared upstream estimator does not have a single sign downstream** — it must be re-propagated through every consumer rather than corrected once at the source. Worth a measurement: re-run `new_clip_at_p2` at R=15 and read the true penalty | orchestrator (ARGUED from fact 242's measured mechanism; **the sign is derived, the magnitude is not measured**) — **NOT INDEPENDENTLY VERIFIED** |
| 436 | **The merge gate's tolerance is exactly linear in a constant that belongs to the operator, not to the host.** `tol = t * sqrt(2) * FOCUS_NOISE_SD`, verified against the shipped binary at five gates spanning **35x**: `tol/t` is constant to **2.0e-6** and equals `sqrt(2) * 0.015214 = 0.021516`. Therefore **an operator whose true noise SD is `k` times the declared constant behaves exactly like the declared gate divided by `k`** | **This is the substitution that makes the plugin seam's calibration hole measurable without building a plugin system first.** It also means the gate has no units of its own: `--gate 1.0` is a statement about a specific operator at a specific window, and it silently means something else for any other. Linearity is the check with power to fail here, and it did not fail | M43 (MEASURED — `strehl merge` on 109MSDCF, 22 frames; see [`M43-plugin-calibration-seam.md`](M43-plugin-calibration-seam.md) section 1) — **NOT INDEPENDENTLY VERIFIED** |
| 437 | **A wrong operator constant silently degrades the estimator into the selector.** `FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD = 0.090400 / 0.015214 = 5.94x` — two real operators already in this codebase, differing only in window radius. At the intended `--gate 1.0`: correct constant gives mean `n_eff` **1.884** with **41.66%** of pixels at `n_eff` = 1; an operator 5.94x noisier than declared gives **1.131** and **87.76%**; 5.94x quieter gives **7.267** and **2.40%** | **The same declared gate produces anything from 87.76%-selection to a 7.3-frame average, and the three runs are indistinguishable from the log, the exit code and the CLI's own calibration block.** In the noisy direction the tool becomes the defect it exists to remove; in the quiet direction it averages frames the noise model can tell apart, which is blur. **`--gate` is therefore not a portable number and must never appear in a contributed profile** — a second, independent argument for fact 324's `--target-n-eff`, this time from portability rather than from calibration | M43 (MEASURED — same run; see [`M43-plugin-calibration-seam.md`](M43-plugin-calibration-seam.md) section 2) — **NOT INDEPENDENTLY VERIFIED**; one stack, and `k` = 5.94 is illustrative rather than a surveyed distribution — **`k` = 5.94 CORRECTED by fact 500**: it divides an unregularised SD by a regularised one, and the honest value for that pair is **1.815**. The cost table is unaffected (it was run at effective gates) and fact 439 supplies a larger real `k` |
| 438 | **Neither capability negotiation nor the confluence property test can catch it.** A focus-measure plugin with a wrong noise constant is capability-compatible (same domain, tiling and layout), **confluent** (the constant is not an ordering property, so it commutes exactly as well as the correct one does), and **sensitive** in the sense workstream E section F4.3 requires (its output does change when the input changes). It passes every gate the plugin design has and produces a quietly worse image | **A missing contract, not a missing test** — and the correction is cheap, because the measurement already exists twice in-crate (`the_focus_noise_constant_is_the_measured_one`, `the_fine_focus_noise_constant_is_the_measured_one`). **The plugin boundary must make that test mandatory rather than customary, must refuse to load a plugin that omits the constant rather than defaulting it, and must require the operator and its window to be declared as a pair.** The third follows independently from M42's quality-side question and from fact 152's scale finding. Amends workstream E sections F3.3/F4, which predate the constant's measurement | M43 (DERIVED from facts 436-437 and a reading of `E-plugin-architecture.md` sections F3.3/F4; see [`M43-plugin-calibration-seam.md`](M43-plugin-calibration-seam.md) sections 3-4) — **NOT INDEPENDENTLY VERIFIED** |
| 439 | **Across seven textbook focus operators, the noise constant the gate is calibrated in spans 10.4x.** Measured in the shipped configuration (operator -> 27x27 box -> 17x17 regulariser), as `k` = SD / `FOCUS_NOISE_SD`: ring(1,3) **0.644**, tenengrad **1.008** (the shipped operator, so 1.000 by definition — the 0.8% is the instrument's own noise floor), tenengrad-squared **1.367**, Brenner **1.962**, local variance **2.475**, Laplacian **6.590**, sum-modified-Laplacian **6.680** | **Answers question 102, and answers it against fact 438.** The two operators at the top are the canonical shape-from-focus measures — Nayar & Nakagawa's SML is *the* SFF operator — so they are the most likely third-party contribution there is, not a strawman. At the intended `--gate 1.0` an SML plugin inheriting the host constant runs at an effective **0.150**. And ring(1,3), which is **this project's own first shipped operator**, errs the other way at 0.644, so both failure directions are populated by operators that actually exist. **The load-time refusal in fact 438 is therefore mandatory, not tidy** | M43 step 2b (MEASURED — `experiments/m43-plugin-seam/02b-operator-noise-spread.py`, 8 seeds x 2048^2 unit-variance Gaussian planes; the instrument is calibrated against **both** in-crate constants in **both** of their configurations and refuses to report if either misses) — **NOT INDEPENDENTLY VERIFIED** |
| 500 | **Fact 437's `k` = 5.94 was wrong, and the error was a units conflation in this project's own two published constants.** `FOCUS_NOISE_SD` = 0.015214 is the SD of the **regularised** response; `FINE_FOCUS_NOISE_SD` = 0.090400 is the SD of the **unregularised** fine field. Dividing them mixes a window-radius change with the presence of a 17x17 box. The honest quantity — that operator as the host would actually run it, `SD(regularise(box_mean(\|grad\|, 2)))` — is **0.027613**, giving **k = 1.815**. Fact 437 overstated that pair by **3.27x** | **The conclusion survives and is now better supported than the illustration ever made it.** M43's cost table was computed by running the binary at effective gates, not from the pair, so every number in it stands; what fails is only the sentence claiming 5.94 came from two real operators. Fact 439 then supplies a *larger* real `k` — 6.68, from SML — so the corrected record prices the seam higher than the mistake did. **Recorded rather than quietly patched because the failure mode is general**: a ratio of two constants is only meaningful if both were measured in the same configuration, and nothing in this repository said they were not | M43 step 3 (MEASURED — `experiments/m43-plugin-seam/03-fine-in-gate-path.py`; the direction was **pre-registered in the script's docstring** before the number was computed, and held) — **NOT INDEPENDENTLY VERIFIED** |
| 501 | **A two-target calibration caught it; a one-target calibration would have shipped it.** The first instrument (`02-...py`) modelled the coarse field without the regulariser. Against `FINE_FOCUS_NOISE_SD` it matched to **+0.20%**; against `FOCUS_NOISE_SD` it read **+24.26%** high. One target passing and one failing localises the fault to exactly what the two configurations differ in — which was the regulariser, and was the bug | **The pattern of pass and fail carried the diagnosis, not the magnitude of the miss.** A single target would have been matched by tuning, and the survey built on it would have been wrong by 24% with nothing to say so. The script was written to refuse to print its own results when calibration fails, and that refusal is what forced the investigation instead of a plausible-looking table. Generalised as discipline 257 | M43 steps 2/2b (MEASURED — the failing run is preserved at `experiments/m43-plugin-seam/02-operator-noise-spread.py`, which is kept precisely because its failure is the useful part) — **NOT INDEPENDENTLY VERIFIED** |
| 502 | **The host should measure the plugin's noise constant, not ask it for one.** Fact 438 called for a mandatory declaration in `Caps`. That is the weaker design. The host already owns a noise plane, the window, the regulariser and the sigma normalisation, so it can run any candidate operator through its own configuration at registration and read the SD off directly — **a few milliseconds, once per stage** | **Better on four counts, and the fourth is structural.** (1) No trust: a declaration can be wrong, a measurement cannot be wrong the same way, so fault 5 becomes *unrepresentable* rather than merely detectable. (2) **A plugin-declared constant is under-determined in principle** — fact 500 showed the constant depends on the host's regulariser, which the plugin cannot know. (3) Changing `REGULARISER_RADIUS` silently stales every declared constant in the ecosystem; a measured one re-derives. (4) It removes the parameter from the contract entirely, which is the Cordis-shaped answer — the host stops requesting a coeffect the plugin cannot reliably supply and computes one it already has the means to. **Under this design `--gate` becomes genuinely dimensionless**, which is the only version in which a number in a shared preset means the same thing on two operators | M43 step 4 (DERIVED — reasoning from facts 436, 438, 500-501 and `focus.rs`'s documented scale invariance; see [`E-plugin-architecture.md`](E-plugin-architecture.md) section F5.3) — **the load-time cost is asserted, not timed**, and that is the cheapest open item in the section |
| 503 | **Pre-normalising the focus response is behaviour-preserving, by derivation and not yet by test.** If the field is divided by its own noise SD and the tolerance multiplied by the same factor, the admission set should be **bit-for-bit unchanged**: `focus.rs` states that both the argmax and any positive-scaled regulariser are invariant to a constant rescale, and fact 436 established that `tol` is exactly linear in the constant | **This is the load-bearing step of fact 502 and it is the one that is not measured.** If it holds, the whole calibration seam closes with a one-line change and the gate becomes unitless. If it fails — most plausibly through f32 rounding, since normalising scales the field by about **65.7x** — then the host-measures-it design still works but is no longer free. **Check it with a byte-identical-output test against the shipped binary before relying on it**; the merge is the wrong place to be confidently wrong, and fact 341 is the standing reminder of what a structural argument about the merge is worth | M43 step 4 (DERIVED — from `crates/strehl-core/src/focus.rs`'s `gradient_magnitude` doc comment and fact 436; see [`E-plugin-architecture.md`](E-plugin-architecture.md) section F5.5) — **NOT MEASURED, and deliberately recorded as a falsifiable prediction rather than folded into fact 502** — **SHARPENED by fact 504**: bit-identity is provable in exact arithmetic but should be expected to fail in f32 at a rate of order 1e-6 to 1e-5 of pixels, so the test must assert a bounded flip count |
| 504 | **Fact 503's bit-identity should be expected to fail, at an estimable and tiny rate — and the test must be written for that.** Pre-normalisation changes the divisor from `sigma` to `sigma * SD`, so the field is rounded differently, not merely scaled: relative error ~`2^-24` on field values of order 0.5, i.e. ~`6e-8` absolute, against a gate-1.0 tolerance of `0.0215`. That perturbation is **~3e-6 of the tolerance width**, so for a smooth distribution of `\|Δfield\|` near the boundary the expected flip rate is of order **1e-6 to 1e-5 of pixels — tens, not zero, out of 8.2 M** | **The correct assertion is a bounded flip count, not byte-identity.** An equality test would go red, and the natural reading of a red merge test is that the transformation is unsound rather than that the test was mis-specified. **A flip rate above ~1e-4 would be the real refutation**, because that would mean the admission boundary is far denser in near-ties than smoothness predicts — which would itself be a finding about the gate worth having. Recorded before the test is written rather than after it fails, which is the only time this kind of note is worth anything | M43 step 5 (DERIVED — f32 ULP arithmetic against fact 436's measured `tol = t * sqrt(2) * 0.015214` and the field scale in `focus.rs`) — **the flip rate is an order-of-magnitude estimate from an assumed-smooth boundary density, and that assumption is untested** |
| 505 | **The load-time calibration of fact 502 is bounded at ~1.7 ms per stage, from measurements already taken.** Merge pass one is **1.153 s for 22 frames** at 3516x2344 = 8.241 MP, so **52.4 ms** per full-resolution plane for decode plus gradient plus window plus regulariser plus the winner fold. A 512x512 calibration plane is **3.18%** of that area, giving **~1.67 ms** — and that figure **includes ARW decode**, which a synthetic noise plane does not pay, so the true cost is strictly lower | **Settles F5.5's cheapest open item without a new benchmark, and it settles it in favour of option A.** The reason to prefer a bound derived this way over a fresh timing is that it needs no decomposition of pass one into decode and compute — the inequality holds however that split falls, so it cannot be wrong in the direction that matters. At under 2 ms per stage per configuration, host-side calibration is not a cost worth trading a correctness property for. **What this does not bound is a `WholeStack` operator or one with expensive setup**, which is the case option B still exists to serve | M43 step 6 (DERIVED — arithmetic on the merge timings measured this session on 109MSDCF, 22 frames: pass 1 1.153 s, pass 2 2.036 s, total 3.189 s at 262.3 MB/s over 836.4 MB) — **an upper bound, not a timing**; no calibration pass has been run |
| 506 | M13's `edge_mode` derives `baseline_lo`, `baseline_hi` and `max_d` from `roi.width` **regardless of the distance axis**. On a 384×256 ROI a `horizontal` edge's far baseline band `[160, 188]` is **empty**, `dmae_far` falls back to `0.0`, and `equivalent_width`'s baseline is `median(∅)`. | Any published `dmae_far`, `bleed_*` or `mis_*` number for a horizontal edge on a non-square ROI is unsound. `E_excess` reads none of these and is unaffected — which is why it was M15's and M16's primary statistic. | M16 (MEASURED — M16 §11, `experiments/m13-window-depth/src/edge.rs`, VERIFIED by reading; predicted in M16's preregistration §6 before measurement; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 507 | **Turnover censoring is orientation-asymmetric and follows the scene exactly.** Counting cells whose mean-regret argmin lands on the last rung of the sweep: on the corpus `vertical` is censored 10–15/60 and `horizontal` **0/60 in 480 cells**; transposing the scene 90° swaps this to `horizontal` 16/60 and `vertical` 0/60; symmetrising the texture gives **0/60 in every column**. | A categorical, non-parametric confirmation of fact 90 that is independent of every median, noise floor and pooling choice. It also means M15's and M16's `vertical` medians are **censored from below**, so the true orientation gap is wider than measured, not narrower. | M16 (MEASURED — M16 §6.4, `data/censoring.csv`, arms A6/A8/A11; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |
| 508 | A **rectangular** scoring region is an orientation-non-neutral gain on the regulariser-shift statistic. Holding the plant, band, seeds and code identical and scoring a centred 256×256 square instead of the full 384×256 ROI takes `A_hv` from −4.0 to **−7.0 windows** (1.75×) while leaving the level gap `L_hv(1)` at −8.0 → −8.5, inside the 1.5-window floor. | M13 and M15 measured roughly **half** the orientation shift that was present. The rectangle does not *create* bias — symmetrising the texture under the identical square geometry still nulls it to +0.0 — but it under-reports it. Prefer the level statistic, or a square region, for any future orientation claim. | M16 (MEASURED — M16 §6.2, arms A0/A10/A6, `data/A10-*.csv`; see [`M16-orientation-fpn-measured.md`](M16-orientation-fpn-measured.md)) — **NOT INDEPENDENTLY VERIFIED** |

### 4.1 Which of these are architecture, and which are artifacts of one stack

The empirical corpus is **n=1**: one stack, one subject, one body, one lens. The owner's
instruction is binding — *"don't overfit to anything specific to my setup."* Ruling:

| "Constant" | What it actually is | Verdict |
| --- | --- | --- |
| −1.012% scale drift | Per-**stack** by construction: depends on travel, magnification, focal length, and on a rail also on working distance | **Artifact. Fit at runtime, always.** Confirmed by M3: a second stack measures −1.835%. And the fallback claim *"drift is smooth and low-order in frame index"* is **also wrong** — no low-order polynomial in `k` reaches the accuracy of a direct per-frame fit. Do not model drift against frame index at all. |
| affine ≈ homography (1.45e-3) | An artifact of the *breathing* case, where there is no perspective signal | **Resolved by M3, and the true answer is stronger: even affine is more than is needed.** A 4-parameter similarity is sufficient; affine (6) and quadratic (12) reduce the residual by ≤6%. The *mechanism* — fixed camera, magnification about a fixed point — generalises to all in-camera bracketing, so this is no longer n=1. It still does not survive a rail. |
| Scale centre (−176±127, −338±61 px) | Physically the principal point — within a few px of image centre. 176–338 px is **not physical**; x has 72% relative error | **Artifact — confirmed refuted by M3**, which measures **(−22, −113) px** at sensor resolution on a second stack: 8x closer in x, 3x closer in y. Solve per stack, regularised toward the principal point with a **tight** prior. |
| `g = ISO/436.8`, ISO 400 second base, white level 15360 | Genuine **per-body-model sensor calibration** — the most legitimate constants here. White level and black level independently **confirmed by M1**. | **Keep — but in a camera-profile data file, never in pipeline code.** Read white level from file tags where present (firmware/compression dependent). `g` was validated by reproducing white level to 0.23%, which is a consistency check on one relation, *not* a photon-transfer measurement — extend experiment 1 to a real PTC. Dual-gain behaviour is per body *and* per firmware. |
| 0.075 px jitter ⇒ MFSR off the table | An artifact of the **capture mode** — in-camera bracketing on a tripod has no camera motion by design | **Do not bake anywhere.** A mechanical rail has 1–10 µm repeatability plus lateral runout; 5 µm at m=1 on a 5.12 µm pitch is ~**1 px**, far above Wronski's ≥0.3 px gate. **MFSR is back on the table for rail users.** |
| `LensModel::breathing_scale_prior` — F ranked it payoff #2 at 5 stars and F1.13 says it *"is justified and should be built"* | A per-lens prior whose **only job** was to seed and constrain the aligner's scale search | **RETRACTED — M3 removed its job.** A direct per-frame fit is already 3.6x more accurate than any low-order model of drift against frame index, costs 13–16 ms/frame, and an 8x-decimated coarse pass supplies capture range on its own. **A prior cannot beat a free, more-accurate direct measurement, and nothing needs seeding.** This was the second-highest-ranked lens-profile item; with it gone, §3.4.2 is what remains. |
| Bellows factor `B = (1 + m/p) ≈ 2.6–2.9` (fact 27) | **Not a constant at all** — `m` is per shot, `p` is per composed optical path. M5 measures the *product*, at one magnification | **Store `p`, never `B`.** `p ≈ 1.0–1.4` is the genuinely profileable half and it is a property of the lens+TC path, not of the body or the subject. `B` must be recomputed per shot from the profile's `p` and the shot's `m`. A profile that caches `B` applies 2:1's bellows factor to a 1:4 shot and is wrong by 2x in the safe direction — i.e. silently. **This is the strongest surviving case for a lens profile**, because fact 28 shows EXIF alone gives the wrong answer by ~3x. |

**A live contradiction to resolve before either claim reaches a design decision:** fact #9
(0.075 px, "MFSR off the table") and novelty bet #1 ("breathing supplies structured, radially
growing sub-pixel diversity") cannot both be true as stated. If breathing offsets grow with
radius, 0.075 px is a centre or whole-frame-average number and the corner value is much larger.
This is exactly the §5 metric-validity failure mode. **Resolution: measure the sub-pixel jitter
distribution per stack from alignment residuals** — which the pipeline already computes and §1.3
already retains — and gate super-resolution on the measurement at runtime. Zero pixel cost, no
baked constant, generalises to capture modes we have not seen.



- **"Bracket frames have correlated noise" (1.10x at N=5) — RETRACTED.** Measured on LR TIFFs,
  4x downsampled, uint8-quantised, and fatally it computed **spatial** sigma within a patch, not
  **temporal** sigma across frames. Averaging frames does not reduce scene structure, so the
  ratio was structure-floored by construction. The sigma-vs-N curve was never measured on any
  data (A follow-up).
- **"The ARW path is 30-44% softer" — CORRECTED to less-*sharpened*, not less-*detailed*.** The
  corpus's own control shows flat foam substrate with 2.4x more top-5% gradient in the TIFF
  stack, annotated *"no real signal there — it's noise being boosted by the sharpening passes."*
  LinearRaw got one sharpening pass, the TIFF *"two-and-a-half"*. Only ~1.4-1.6x was real
  demosaic difference (A follow-up).
- Three fabricated citations, and a fourth (**Lee & Tai 2016**) that was wrong in initial, title
  and availability and reached scheduled work item #7 — *"it passed review because the author was
  real"* (A follow-up).
- Pixel pitch wrong in four places in the corpus; true value **5.12 um**.

---

## 5. Engineering discipline

The prior corpus's two worst errors were **metric-validity failures, not measurement failures**:
*"the arithmetic was right, the column headings were wrong."* And its best-measured win (NLM-Multi,
1.38x at ship) silently inverted to a **+35-48% regression** when an unrelated default flipped and
the baseline got 2.6-3.0x cleaner — noticed only in retrospect, by a manual audit. No automated
signal fired.

In a project whose whole premise is third-party contributable algorithms, that is the default
failure mode, not an edge case.

**And it has already recurred inside this project.** M2's report compared a *temporal per-sample*
sigma (19.267 DN, from the noise model) against a *spatial* sd of noise **plus scene structure**
(28.201 DN, from the image) and presented the 1.46x gap as an unexplained model failure. Matched
properly — high-pass the ROI first — they agree to **1.01x**. That is the same spatial-vs-temporal
confusion that got the prior corpus's 1.10x claim retracted, committed by an agent that had read
the retraction, in a document written to the labelling discipline. It was caught only because a
second agent was told to re-derive rather than review. **Rule 8 is not paranoia, and self-verification
does not work.** In the same pass, four other supporting numbers in the same document were refuted
(`M2-verification.md` §3) — while the headline itself survived and was strengthened.

So the A/B harness is a **first-class component from commit one**, not a later addition:

1. Every quality claim stored with a **named baseline artifact hash**.
2. **Pair every sharpness metric with a no-signal flat-ROI control**, and every noise metric with a
   genuinely *temporal* estimator. **Never compare a spatial sd to a temporal sigma** — high-pass
   first, or compare like with like.
3. **Every headline number needs a regression test on its own code path.** M2's 1.253x had 52
   passing tests behind the library and **zero** covering `report_flat_roi` / `roi_green` /
   `speckle_fraction`, the code that actually produced it.
4. **Every claimed defect needs a placebo.** The control that proved argmax was the cause was not a
   better measurement of argmax — it was a *different merge rule* on identical data (mean 0.534x)
   and a selector with the same winner statistics but no noise coupling (0.981x). Quote the
   placebo alongside the effect or the effect is only correlational.
5. Re-measure **non-default flag combinations** — the NLM inversion lived entirely inside an opt-in
   flag, and default-only CI is blind to it.
6. Ratchet **wall clock and peak RSS** together — and **pin the thread count when you do**, or you
   are ratcheting the runner rather than the code (§3.2.1). Ratchet the *shape* (peak flat in N at
   fixed pool) and the *per-worker constant* alongside the absolute ceiling; the ceiling alone can
   go green through the very regression it exists to catch, just by running on fewer cores.
7. **Resolve every citation to a retrievable artifact before it reaches a design decision.**
8. Property-test the plugin graph on four properties, not just confluence: invariance,
   **sensitivity** (distinguishable configs must produce distinguishable output), no-residue
   across runs, and a calibrated fixture recovering a known synthetic warp. Confluence
   alone is passed by a function that returns a constant.
9. **A synthetic null is not a null.** M5's cutoff estimator false-alarms on **0.4% of white-noise
   tiles (3/240) and on 34.2% of real dark frames (113/330)** — an 85x gap, because real darks carry
   M4's row/column FPN and synthetic noise does not. The estimator is only safe because a second,
   independent gate (`dyn ≥ 10`) suppresses all 113. **Run every null on real sensor data, and when
   a guard is what makes a result valid, publish the guard with the result** — anyone reusing the
   estimator without it inherits a 1-in-3 false-alarm rate.
10. **A measurement design can be structurally incapable of answering the question it is pointed
    at, and it will not tell you.** M3 aligned every frame to frame 0, so for a tile whose best
    focus is frame `w`, the defocus mismatch of pair `(0, k)` is `|w − k| − |w − 0| = k − 2w`
    — **an exact linear identity in the very quantity that was supposed to discriminate the two
    hypotheses.** Every M3 pair would have produced the same residual pattern under either cause.
    M6 broke the degeneracy with a **sliding baseline** — align `(j, j+Δ)` for every `j` at fixed Δ,
    so each tile is seen at many defocus levels with its depth fixed, and each defocus level across
    many depths. **Before running a discriminating experiment, write the identity relating the
    treatment to the design and check it is not degenerate.** M6 reports its own residual identity
    collinearity (0.14-0.67) alongside every γ for exactly this reason.
11. **Resampling is not a neutral operation in an alignment benchmark.** Bilinear interpolation's
    transfer function depends on the sub-pixel phase, so a synthetic shift plants a
    sharpness modulation that a correlation-based estimator reads **the same way it reads defocus**.
    Any benchmark that manufactures ground-truth shifts by resampling has this baked in and will
    partly measure its own resampler. M6 handled it by using resampled data only for
    positive-control *recovery* checks, never as evidence about real defocus, and by running its
    null on the torus rather than on shifted copies. **State the resampler's contribution whenever
    resampled data supports a claim about sharpness.**
12. **State the unit on every memory figure, and never set two figures side by side without
    checking they share one.** `WorkerPlan::describe()` printed decimal MB; PowerShell's
    `PeakWorkingSet64 / 1MB` is MiB. Those two numbers were published together as "379 measured vs
    321 modelled" and read as a 18% modelling error. **The real working-set excess is 37.0 ± 5.4 MiB
    and the private-commit excess is 7.7 ± 6.6 MiB — consistent with zero.** The error survived two
    milestones and a respecification of the CI ratchet because ratios were unaffected, so nothing
    looked wrong. Percentages hide unit bugs; absolute differences expose them.
13. **A gate written from a model of the system tests the model, not the system.** §3.2.1's
    assertion 1 was derived by reasoning about what peak RSS ought to depend on. It failed on clean
    code by 16-20% because two real mechanisms were absent from the reasoning: rayon's reduce tree
    holds one accumulator per level, and `chunk_len` 1 → 2 fills a concurrency window that
    `chunk_len = 1` leaves half empty. **Run every new gate against known-good code, at the exact
    pair it specifies, before trusting it to judge unknown code** — and set its tolerance above the
    measured run-to-run spread of its own two sides, not above a mean of them.

14. **Pre-register the full outcome grid, not the outcome you expect.** M9's registered rule had a
    confirm branch and a reject branch and the observed result landed in **neither** — the
    load-bearing clause of confirm failed, but the reject branch had its own unmet condition. The
    ruling then had to lean on **S7, a post-hoc statistic**, which is a strictly weaker position than
    if the grid had been enumerated up front. **Before running, write down what you will conclude
    for every cell of the outcome space, including "both conditions fail".** *(M9 disclosed this
    against itself, which is why it is here and not a defect.)*

15. **When re-analysing someone else's data, reproduce one of their published numbers first.** My
    first independent pass at M9 produced the *opposite* correlations — ρ(support) = +0.813,
    ρ(φ) = +0.105 — because the sweep CSV is stratified by ROI and my reader silently kept the last
    row per measure, collapsing four flat ROIs and four detail ROIs into one. **The tell was that
    the same script failed to reproduce M2's published 1.253x**, returning 0.9992x. With the strata
    filtered correctly, every M9 headline reproduced. **A cross-check against a known published
    figure is the cheapest guard against misreading a schema, and it should be the first thing any
    re-analysis prints** — without it I would have "refuted" a correct result on my own bug.

16. **A control can fail because the *control* is wrong, and that must be published as loudly as a
     treatment failure.** M11 registered a rule-9 pairing — the same planted run on a flat ROI must
     collapse to within 3x of chance — and it failed at **13.8x and 31.7x**. The cause was the
     control: a *relatively* flat ROI of a real frame still carries broadband texture and its own
     inherited read and shot noise, and a planted blur ladder blurs those too. With the base replaced
     by its own mean — nothing left to blur — the same run sits at **1.12x**. **The rule: when a
     registered control fails, diagnose it before believing it, and publish the original failure next
     to the repair. Deleting a failed control and substituting a passing one is indistinguishable,
     from the outside, from fabrication.**

17. **A correlation coefficient is a property of the population sampled, not of the mechanism.**
     M11 measured ρ(φ, noise) = +0.583 over 36 heterogeneous operators and read it as *weakening*
     M9's +0.918 / +0.894. It does not: restricting to the families M9 actually sampled gives
     **+0.783**, and the sequence is monotone in how heterogeneous the operator set is. **Before
     reporting that a replication weakens a prior ρ, re-run the prior statistic on the comparable
     subset.** Otherwise range extension is indistinguishable from a real effect-size reduction —
     and the direction and the null, which are the parts that carry the mechanism, replicated exactly
     (support null −0.009).

18. **Reach for a conservation identity before reaching for a better estimator.** M10's span ladder
     was first suspected to be a median-vs-mean weighting artifact. A pure telescoping sum — no
     median, no weighting, no solver, just `Σ log a` over a fixed span, which *must* give the same
     total for every span — settled it in one calculation and left nothing to argue with. **When a
     quantity is subject to a conservation law, check the law first.** It is cheaper than any
     estimator comparison and immune to every objection about weighting.

19. **Zero failures is not zero error.** M10's `wide64` config produced **0 no-fit pairs out of
     1601** where the default produced 140, which looked like the win. Its cycle consistency was
     **35.2 px against 13.0 px**, and it was the only config with a significantly positive
     error-vs-span slope. **It was not fitting harder; it was failing silently.** A robustness
     variant that converts failures into wrong answers is strictly worse than one that reports
     failure. **Always score a "more robust" variant on an independent metric, never on its own
     failure count.**

20. **Do not corroborate a measurement with itself.** M10 reported that 119MSDCF's span ladder
     "agrees to five significant figures" with its direct long anchor. On a 33-frame stack the
     **span-32 ladder *is* the single direct 0→32 edge** — the same number reported twice, so the
     agreement is exact by construction and carries no information. The genuine evidence was sitting
     next to it: the **monotone convergence** of spans 1→16 toward the anchor. **Before quoting an
     agreement, check that the two quantities were computed from disjoint measurements** — and treat
     any agreement to five significant figures between two noisy estimates as a bug report, not a
     result.

21. **A control may not presuppose the treatment's answer.** M12 registered its positive control
     with two clauses, one of which — *"a small planted increment must recover at < 0.9"*, lifted
     from fact 45 — was **a prediction of the treatment wearing a control's clothes**. It failed,
     correctly, on precisely the stacks that turned out not to shrink. Ask of every registered gate:
     *would this still be a valid instrument check if my hypothesis were false?* If not, it is a
     hypothesis and it belongs in the results, where it can be refuted, rather than in the controls,
     where its failure looks like a broken harness.

22. **State the audit method, not merely the audit result.** M12's read-only tree audit matched
     byte for byte — and a recount that included hidden files differed by **1081 files**, purely
     because the original enumeration omitted `-Force`. Same tree, different method, different
     number. **An unchanged count proves nothing unless the enumeration itself is identical and
     stated.**

23. **Reproducible is not transferable.** The shrinkage reproduces between two captures of the same
     scene to **0.15 σ** and transfers to **0 of 18** cross-scene pairs. Stability within a condition
     is evidence that a quantity is *real*; it is no evidence whatsoever that it is a *constant*.
     **Before calibrating anything, test it across the axis you intend to generalise over, not the
     axis you happen to have replicates on.** The two are rarely the same axis, and the replicate
     axis is always the one that is cheap to measure.

24. **A plant that cannot express the failure mode is not evidence about it.** M11's A4 swept the
     window on a fronto-parallel plant and reported "still improving at the edge of the sweep". That
     plant is mathematically incapable of producing an interior optimum for a symmetric window
     (fact 62), so the observation carried **no** information — it was not weak evidence, it was
     none. Before sweeping a parameter, ask **what the plant would have to contain for the answer to
     be anything other than the endpoint**; if the answer is "nothing it contains", fix the plant,
     not the sweep range. This is item 10 with a sharper edge: item 10 says a design can be
     structurally incapable of answering; this says **check that property before you spend the
     compute, and check it on the stimulus rather than the analysis.**

25. **Report an endpoint argmin as "no turnover found within the sweep", never as an optimum.** A
     mechanical rule, and the cheapest guard in this file. M13's analysis script labels every argmin
     `interior` or `ENDPOINT` automatically so the distinction cannot be lost in prose.

26. **Where a metric has a known blind spot, control for it rather than disclosing it in prose.**
     M13's `W_bleed` cannot see a selector that elects a compromise frame *between* two layers, so
     that blind spot was asserted as a **test** — a planted compromise of radius R must read bleed
     0.0 and mis R−1 — and not as a caveat. The blind spot then appeared in real data (`bleed_fg`
     collapsing 18.75 px → 1.19 px while excess error *rose*), and was recognised on sight because
     the control existed. A caveat in prose would have been read as "the halo went away".

27. **When a pre-registered threshold turns out to be on the wrong quantity, say so and override it
     explicitly.** M13 registered a 5% threshold on an **oracle** gain it had already documented as
     "a strict upper bound, never a proposal". The threshold fired and would have mandated an
     adaptive rule; the decision-relevant quantity was the *realisable* rule, which said the
     opposite. The correct move — taken — is to **report that the registered test fires, state that
     it was registered on the wrong quantity, and override on stated grounds.** Quietly re-cutting
     the threshold is the failure mode this discipline exists to prevent.

28. **Verify a corpus audit with `Get-ChildItem -Force`, never without it.** Without `-Force`,
     `Get-ChildItem -Recurse -File C:\dev\macro` reports 17,449 files / 286,581,830,721 bytes; with
     `-Force` it reports **18,530** / **286,893,514,060**, matching the harness audit exactly. The
     1,081-file gap is hidden and system files, not deletion. **An agent spot-checking the read-only
     guarantee this way will conclude it was violated when it was not** — the checking tool was
     wrong, not the thing being checked.

29. **Derive confidence from cross-frame spread in the focus volume, never from focus magnitude.**
     Fact 73 is the counterexample that forces this: on an untextured monotone edge the shipped
     operator returns a *large* response (37.04, comparable to sharp texture's 45.13) that is
     **identical in every frame**. Magnitude-derived confidence would report high confidence at
     exactly the pixels where the discriminating information is exactly zero — the worst possible
     failure mode for a stacker whose thesis is calibrated per-pixel confidence. The quantity that
     carries the information is the *contrast of the peak across the stack*, which correctly reads
     zero there.

     > **QUALIFIED by fact 203 (M26) — this quantity has its own blind spot, and it is the same
     > shape.** On pixels clipped in every frame the peak contrast reads **1.0000, its maximum**,
     > because the pixel sits inside a uniformly clipped blob in one frame (`f_min` exactly 0, in
     > 85.9% of cases) and under the blob's moving edge in another (`f_max` 52× typical). Focus
     > magnitude fails there too, so **switching between the two candidates does not help; the
     > input has to be masked.** The item stands as written — it is still right about fact 73 — but
     > it is not sufficient on its own.

     > **SUPERSEDED IN SCOPE by discipline 120 (M27).** A *third* instance — a bracket missing its
     > best frame reads as a **sharper, better-centred** peak (fact 211) — shows the problem is not
     > confined to metrics with degenerate denominators. **No self-normalised shape statistic may
     > be shipped as confidence at all**, cross-frame spread included. This item survives as the
     > right instruction for choosing a *focus measure*; the confidence output itself must be built
     > from externally-referenced quantities (predicted σ, effective sample count, flags).

30. **Time a parameter sweep with alternating direction and take the per-setting minimum.** M14
     found a single forward sweep reading **−0.7%** and a reverse sweep **+19%** on the same binary
     and the same settings, and `FocusField::compute` reading **21% slow** purely because it was
     timed after the sweeps rather than before. A one-directional sweep silently attributes thermal
     drift, cache warming and clock ramp to whichever parameter was measured last. Confirmed from
     the other side by my own re-run: the residual spread it reports (0.69%) disagrees with M14's
     (1.28%) by more than either differs from zero, so **quote flatness as a bound, not a value**.

31. **An `interior` argmin label is only meaningful when the argmin is separated from its
     neighbours — especially from the endpoints — by more than the noise floor.** Item 25 refuses
     to call an *endpoint* argmin an optimum; this is the mirror error, calling a **plateau** a
     turnover. Publish the separation next to the label. M15 §3: the zero-step argmin reads
     `interior` at w33/w26/w20/w16/w10 while the w40 endpoint sits within **0.0003 DN** of the
     minimum — nominally a turnover, actually a plateau, and fact 61 survives because M15 checked
     the separation instead of the label.

32. **A max-over-cells regret statistic is not comparable across a treatment that changes the
     dispersion of per-cell optima.** Mean regret is, because the cell set is fixed; the max is
     not. Register decision thresholds on mean regret, and always check **absolute** error before
     believing a worst-case regression. M15 §5.1: worst-case regret at w13 *doubled* while w13's
     absolute error *fell 35%* — the statistic moved the wrong way against a treatment that was
     helping. M15 registered this arm itself and disclosed it as invalid rather than dropping it.

33. **When a null result is the finding, publish the stratum on which the effect IS present, as
     the positive control that the design could have resolved it.** A null is only evidence if the
     same ladder, seeds, objective and aggregation rule are shown moving somewhere. M15 §4:
     substitution rate **1.72 (r² 0.94)** on the zero-step stratum against **≈0 (r² 0.10)** on the
     decision stratum, from one harness invocation. Fact 83's orientation split is a second such
     control — the aggregate is flat *because two unanimous effects cancel*, not because nothing
     moves.

34. **Prefer re-running a prior milestone's harness unmodified to reimplementing it.** The
     experiment binaries are deterministic, so byte-identity of the replication CSV is the
     strongest available form of item 15's reproduction gate, and it simultaneously proves the
     binary *and* its inputs are unchanged. M15 §0.2 reproduced M13's committed CSVs by SHA-256 on
     both stacks. **State explicitly that this is a consistency check, not independent evidence**
     (item 20) — it cannot detect an error that was already in the harness.

> **Items 70-73 were added by the orchestrator while M16-M19 were in flight**, and are numbered
> from 70 to keep clear of the reserved blocks (M16 40+, M17 50+, M18 60+). Every one of them
> comes from an error found in the orchestrator's *own* work, not an agent's.

40. **A treatment that removes a defect also removes whatever scene content shares its geometry.** When the scene component is orders of magnitude larger than the defect — here ~10³ — the treatment arm cannot separate them, and a null result from it means nothing on its own. Only a planted positive control at a measured amplitude, plus a direct measurement of the defect's amplitude, can decide. M16's H3 arms were nulls for exactly this reason and the verdict had to come from elsewhere.

41. **Before blaming the machinery, make the scene symmetric under the transformation the machinery is accused of breaking, and re-measure.** For a 90° orientation claim that is `T ← (T + Tᵀ)/2` on a square tile: one line, exact, and it keeps the corpus's own contrast and spectrum, so there is no synthetic-regime objection to answer. Transposing the scene (`T ← Tᵀ`) is the complementary test and is even cheaper.

42. **Pooling two conditions because they share one property imports every property they do not share.** M16 pre-registered `vertical ∪ bar` because both have vertical boundaries. `bar` also differs in *shape*, and on the decisive arm the entire residual statistic came from `bar` alone while `horizontal` and `vertical` agreed exactly. Report the unpooled contrast beside the registered one; never silently replace it.

43. **A synthetic control that lands in a different regime from the real data cannot carry a verdict about the real data.** Check the control's mean-regret argmin against the published basin first. M16's registered isotropic arm sat at w4/w8 against the corpus's w12–w15 and had to be replaced by a symmetrised *real-texture* arm before it could decide anything.

44. **Count the censored cells before quoting a median of argmins, and report the count.** Discipline 25 forbids reading an endpoint argmin as an optimum, but a *median over a set containing endpoint cells* smuggles the same error back in one level up. In M16 the censoring rate was 0/60 for one orientation and 15/60 for the other on the same data, so the medians being compared were not the same kind of quantity. The censoring count is also the most robust statistic in the milestone — binary per cell, immune to floors, ties and pooling — and it should be computed first, not last.

70. **Never bin a statistic against a map derived from the same data as the statistic.** This is
     the single most productive error of the M20-M22 block and it was made twice. M21 measured
     occlusion bimodality against a depth-step map built from the same focus volume — but a bimodal
     pixel makes its own argmax flip, *manufacturing* the depth step it is then credited with
     landing on. Breaking the circularity cut **29.47× to 4.38×**, so 85% of the headline was the
     statistic measuring itself. M20 §2 carries an unresolved version of the same worry (fact 27's
     `B` may have been derived from the very formula the optics gate uses to "check" it).
     **The test: name the mechanism that could drive both quantities. If you can, the design is
     circular until you break the shared path** — cross-scale binning, an independent instrument,
     or a control that removes the shared mechanism.

71. **Say which direction a metric can be fooled in, and only use it in the direction it cannot.**
     `mean |∇|` rises when a merge *manufactures* detail as readily as when it preserves it — fact
     145 measured argmax reading **above ground truth**. It is therefore admissible as a test
     against collapse (fact 24) and inadmissible as evidence of quality. Every acceptance metric
     needs this sentence written next to it before it is used to accept anything.

72. **When data arrives in independently captured groups, use agreement across groups as the
     discriminator — not a threshold within one.** M22's 242 darks were delivered as 11 ISO groups
     for M4's read-noise work; that grouping turned out to be a free replication test, and against
     a Binomial baseline it separated 11,393 real defects from 108,776 threshold false positives
     (which were *fewer* than chance). This deleted a tuning knob rather than tuning it. **Look for
     the replicate structure already present in delivered data before inventing a threshold.**

73. **Any claim that two per-pixel maps agree needs a shift control, not an independence
     baseline.** M22's first cross-scene test scored overlap against independence and reported over
     a million defects — because both subjects sit centre-frame, so the maps share large-scale
     structure having nothing to do with per-pixel defects. Rolling one map by an even offset
     preserves CFA phase and every spatial statistic while destroying per-pixel correspondence.
     **Pair it with a known-real population as the positive control** (M22 used the dark-derived
     map: 1.91/2.36/16.00×), or the collapse ratio has no scale to be read against.

110. **Write down which domain each calibrated model is valid in, and treat leaving that domain as
     a breaking operation.** `σ²(S) = g·S + (RN_e·g)²` is valid in *native per-channel raw DN*.
     White balance is a per-channel gain of up to **2.86×** on this corpus, and applying the model
     after it understates σ by a factor tending to **m** in the shadows and **√m** in the
     highlights (fact 201). Nothing errors — the gate simply rejects too aggressively, and hardest
     in the shadows, which is precisely where the defect being fixed lives. **Every calibrated
     quantity in this project should carry its domain in its type or its doc comment**, and any
     plugin that wants to move a value out of that domain must transform the model with it as part
     of the contract.

111. **A metric that saturates has a second failure mode at its own ceiling, and it is usually the
     opposite of the one you designed against.** Discipline 29 exists because focus *magnitude*
     reports high confidence where information is zero (fact 73); the replacement, cross-frame peak
     contrast, does exactly the same thing on clipped pixels (fact 203), because a ratio
     `(max−min)/max` attains 1.0 whenever the minimum is degenerate rather than whenever the signal
     is strong. **Before adopting a normalised metric, ask what makes its denominator large and its
     numerator's floor zero, and check whether any real input can do both.** In this case the fix
     was not a better metric but masking the input — three bad pixels' worth of work for a
     maximum-severity hole.

120. **A self-normalised shape statistic measures goodness of fit, never presence of evidence — so
     none of them may be shipped as confidence.** Three independent failure modes now read
     *maximum* confidence where information is *absent*: an untextured monotone edge (fact 73,
     focus magnitude high), a pixel clipped in every frame (fact 203, peak contrast exactly 1.0),
     and a bracket missing the best frame (fact 211, peak *sharper* and *better centred* than a
     well-sampled one). Discipline 111 diagnosed the first two as a denominator problem; the third
     has no degenerate denominator at all — the curve really is sharp and really is symmetric,
     because the two surviving frames flank the true peak at equal distance. **The common cause is
     more general than saturation: any statistic computed over a neighbourhood describes the data
     it was given, and a neighbourhood containing no evidence is a well-behaved input.** The
     consequence is a hard design constraint on strehl's headline output: curvature ratios, peak
     contrast and vertex offsets are all disqualified as confidence. Confidence must be built from
     quantities with an **external, absolute referent** — predicted σ from the calibrated noise
     model, effective sample count, and explicit flags — which is what discipline 29's semantics
     were reaching for and is now *derived* rather than asserted.
     **M31-V: partially retracted.** The specific worry that fact 73 is a self-normalised shape statistic does **not** hold — **fact 211 is a genuine third mechanism**. The discipline itself stands on facts 260 and 211.

121. **A detector that divides by a quantity unavailable at inference time is an effect-size
     measurement wearing a detector's clothes.** M27's first pass scored `f_reduced / f_full` and
     produced a beautiful monotone table (16/26/49/62/73% peak loss for gaps of 1/2/4/6/8 frames)
     with a control pinned at exactly 1.0000 — and it was worthless as a detector, because the
     full-stack peak does not exist when you need it. The tell is the perfect control: a control
     that cannot move is usually an identity, not evidence. **Before running a detector experiment,
     write down the exact inputs the shipped code will have, and delete every term not on that
     list.** Keep the oracle version if you want the effect size — M27 does — but label it, and
     never cite it as detectability.

130. **A disagreement statistic is only as good as its reference, and the reference should be
     chosen to minimise the nuisance term rather than to maximise the sample count.** R10 imported
     the burst-photography shape — disagreement against a running estimate over all frames —
     which is correct when the frames are nominally identical. In a focus stack it is not: the
     residual against a whole-stack reference is **10.9× larger** than against the immediate
     neighbours (fact 220), and every bit of that excess is breathing, which the statistic cannot
     tell from an outlier. The general instruction: **before averaging more data into a reference,
     ask what systematically differs between the frames you are adding and the frame you are
     testing.** Here the answer flipped an architectural ordering — a mask referenced to neighbours
     runs *before* alignment, so alignment can be protected by it instead of being a prerequisite
     for it.

131. **When a statistic's baseline is deterministic rather than stochastic, changing the
     aggregation scale buys nothing — check which regime you are in before tuning it.** Averaging
     `d²` samples divides the *noise* by `d` and leaves any *deterministic* residual in place, so
     a scale sweep separates the two: M28's clean-stack residual *rose* 1.01 → 25.07 under lowpass
     (fact 220's mechanism) rather than collapsing, and detection rate was flat to within 10%
     across a 4× range of tile size because signal and threshold both scale (fact 223). The
     corollary is a useful instrument, not just a warning: **sweep the aggregation scale and read
     the exponent** — flat means noise-dominated, ∝ `d` means fully deterministic, and anything in
     between measures the spatial structure of the deterministic part. The corollary for design is
     that a scale chosen "for accuracy" in the deterministic regime is a scale chosen for nothing,
     and should be picked on compute cost instead.

140. **When a measured constant disagrees with your algebra, the algebra usually has a hidden
     factor that varies. Find it before adopting the empirical number.** M29 measured a
     map-domain attenuation of **0.274** where the pipeline algebra predicted **0.885**, and the
     empirical figure was adopted and carried into a second script without the disagreement being
     resolved. The algebra was right: the missing factor was `g/blur(g)` at the plant location,
     which happened to be **0.29** at the one pixel it was measured at (fact 231). A local
     accident was promoted to a global constant, and every downstream number silently inherited a
     3.4× error. The tell is available for free — **a constant that disagrees with a derivation is
     either a bug or a variable, and both are worth an hour.** Note this is the *converse* of the
     usual advice to trust measurement over argument: measurement wins on *values*, but a
     measurement that contradicts a derivation has not yet told you *what* it measured.

141. **A conjunction across heterogeneous instruments is bounded by its worst member; either
     equalise them or accept the worst one's floor.** M29's raw six-stack `min` conjunction never
     fires at any planted depth, because `coffee-bubbles`' map rms is 6.5× `coffee-bean`'s and
     alone sets the null tail, while the per-stack drop under a common plant is bounded below by
     `min_i(R_i)` — the *least* responsive stack (fact 232). The standardised variant fires but
     pays for it by dividing a common physical quantity by a per-stack scene number. There is no
     free version of this: **an AND across detectors of unequal quality is an AND with the weakest
     one**, so the design choice is which members to admit, not how to combine them.

142. **Compute the statistic's expected value before running it.** M29's first script spent a
     full pass over six stacks on a global correlation whose expected signal, `r ≈ f·A²/σ²`, is an
     order of magnitude *below its own null* for any plausible defect — one line of algebra,
     available before any data was touched. A null result from an instrument that could not have
     produced a positive is not evidence; it is a wasted pass. **Pair every pre-registered
     prediction with a pre-registered effect size**, and if the predicted effect does not clear
     the predicted null, redesign rather than run.

150. **A control must hold constant the resource that is actually scarce — and the scarce
     resource is a property of the domain, not of the data structure.** M30's first script
     compared a +2 EV frame against a +0 EV duplicate and called the duplicate a placebo. It
     held **frame count** fixed, because frames are what the array is indexed by. Frame count is
     not scarce; **exposure time** is, and a +2 EV frame costs four units of it. The comparison
     put four units of light against one and recovered `√4/√2 = 1.414` to four significant
     figures. **The tell is available for free: a result that reproduces a constant that exactly,
     across three stacks with different ISOs, signals and scenes that should all perturb it, is
     the arithmetic of the comparison rather than a property of the world.** Before running a
     two-arm comparison, name the budget the arms are supposed to be spending, and check that the
     arms actually spend the same amount of it.

170. **A population selected by thresholding a statistic computed on averaged data is not
     selected on the property you think it is.** M32 split pixels into "flat" and "textured" by
     local contrast measured on the **frame-averaged** image, whose noise floor is `σ/√53 ≈ 1.1`
     DN — so a 5.9 DN "flat" pixel is real scene structure at 5.4× that floor, and the
     least-textured bin in the entire crop still carried **119 σ** of focus evidence. There was no
     information-free real population in the data at all, and every flat-vs-textured comparison
     was *more evidence against slightly less*. The mechanism is that **averaging moves the noise
     floor the threshold is implicitly referenced to**, and a percentile threshold hides this
     perfectly because it always returns a population. A near-relative of discipline 130: picking
     a threshold that guarantees a sample exists is not the same as picking one that guarantees
     the sample has the property. **Check that the selected population has the property the
     experiment needs, using a reference the selection did not use.

180. **When a statistic can be exactly zero for a large fraction of the population, the median
     reports the size of that fraction, not the size of the effect.** M33's retention is exactly
     1.0 for every pixel whose focus peak happens to land on a sampled frame — about half of them
     at ×2 sampling — so the median sat on the boundary of that point mass and returned 0.234% for
     one phase and *exactly* 0.000% for the other. That difference is not a difference between the
     two stacks; it is which side of 50% the mass fell on. The quantity with meaning was the
     deficit **conditional on missing**, which is **4.64% — twenty times larger**. Check for point
     masses before choosing a quantile, and when one exists, report the mixture: the mass fraction
     and the conditional distribution, never a quantile that straddles them.

181. **A pre-registered effect size protects only the estimator you named.** M33's P1 predicted
     ~7% median deficit from a Gaussian argument. The conditional median came out at 4.64%, so the
     *physics* was close — but the statistic actually named, the all-pixel median, came out at
     0.234%, wrong by 30×. Discipline 142 requires the effect size; it does not by itself stop you
     getting the magnitude right for the wrong estimator. **Pre-register the effect size *and* the
     shape of the distribution it will be read off.****

190. **A rank correlation and an extreme-set overlap answer different questions, and a
     confidence channel has to be judged on both.** M34's C2 correlates with the true
     sub-frame deficit at **+0.3349 — 60% of C3's +0.5560** — while their worst-5% sets
     overlap at **chance**. Neither number alone is true: reporting only the correlation
     says C2 is a weak C3; reporting only the overlap says C2 is unrelated to C3. What is
     actually the case is that C2 carries real information across the bulk of the
     distribution while the specific pixels it calls worst are different pixels. Any claim
     that two diagnostics are redundant must state which of the two questions it answered.

191. **A defensive clamp that is unreachable in correct operation conceals the bug it was
     written to guard against. Use an assert.** M34 script 01 computed
     `1 − exp(min(a0 − peak, 0))`, where `min(·, 0)` existed so a numerically impossible
     positive value could not produce a negative deficit. A sign error made `a0 − peak`
     positive for **every** pixel, the clamp fired everywhere, and the channel came out
     **exactly 0.00000 at the median, the mean *and* p95 — 100.0000% of pixels**. The guard
     did its job, which is exactly the problem: an assert would have failed on the first
     pixel instead of producing a plausible-looking all-zeros array. **Corollary, from the
     same incident: a formula that has already been got wrong once must exist in exactly one
     place in the repository.** The sign error was character-for-character the one M33 script
     02 already contained, found and corrected; I reproduced it by retyping the expression
     instead of importing the corrected one. Retyping a correction discards it.

210. **When an estimator changes in two ways at once, the comparison prices the pair, not
     the part you are claiming.** M33's headline scored a raw parabola against a
     baseline-subtracted log fit, and attributed the whole margin to the log domain. It
     happened to be right — M35 measured the split at 9% baseline, 91% log domain — but the
     experiment as run could not have told the difference, and the relative deficit is not
     shift-invariant for either estimator, so it could easily have gone the other way.
     **Run the full factorial, not the diagonal.** The missing cell cost one script.

211. **A ratio between two estimators scored against a shared reference survives errors in
     that reference; an absolute calibration against it does not.** A multiplicative error
     in the ground truth cancels in the ratio. M35's two failed stacks therefore still
     support "the log fit beats the parabola" (2.05× and 1.79×) while their absolute
     calibrations are unreportable. **When a ground truth fails its adequacy gate, do not
     discard the experiment — work out which of its statistics were invariant to the
     failure, and report only those, saying which.

220. **A test's random number generator is part of the measurement apparatus, not
     scaffolding.** An LCG feeding Box-Muller and written into a raster grid puts the
     generator's lattice structure into *space*, where any box filter will alias against
     it — 1.30× across seeds on a constant that looked perfectly stable at one seed.
     **Use SplitMix64 or better for anything whose spread is the measurement**, and always
     run more than one seed. The single-seed version of this measurement was not noisy;
     it was confidently wrong.

221. **Derive a test's tolerance from its effective sample count; never choose it.** Two
     failures in one afternoon came from choosing: a 5% stability bound that no honest
     version of the measurement could have met (~118 independent samples per seed put the
     floor at 6.5%), and a 1.25× band wide enough to admit a value that was later found to
     be 30% wrong. The repair is to compute the standard error inside the test, assert the
     constant sits within four of them, **and separately assert that the standard error is
     small** — otherwise the band admits anything and the test silently has no power.
     Correlated samples make this mandatory rather than pedantic: 219,000 pixels were 118
     measurements.**

230. **A metric whose confound shares the sign of the effect will confirm whatever you already
     believe.** Mean |∇| falls when a merge blurs and falls when a merge denoises, so read
     uncorrected it charges the estimator for its own purpose — and read the other way it
     credited argmax for raising noise (fact 24 against fact 19). The repair is **not a caveat
     in the report**: subtract the confound with the calibrated model, in whatever algebraic
     form makes it separable. The absolute gradient does not decompose but the squared one
     does, so the metric became `sqrt(raw² − model²)` and the apparent −45% became −4.6%.
     **Audit every paired control for this.** Confounds that share a sign are invisible — they
     never produce a surprising number, only a wrong one.

231. **When the harness behind a published number is not preserved, identify its convention by
     enumeration and measurement, not by reasoning.** A reasoned guess got the family right and
     the member wrong, and would have passed on the single ROI it was checked against.
     Enumerating seven candidates hit **0.01%** on both ROIs. This is cheap — one script, one
     independent implementation. **And keep the harness**: this cost an afternoon only because
     M2's code was not kept, which is a preventable class of debt.

240. **A correction is not verified until you show it still fires.** M38 proved its detail
     metric was confounded and removed the confound, but never demonstrated the corrected
     version could still detect real destruction — and a correction that removed the confound
     *and the signal together* would have produced identical evidence. The missing measurement
     was one line: run a **plain mean**, which is known to destroy detail, and confirm the
     corrected metric fires. It does, at −48.4% against the merge's −4.6% (fact 344). **Every
     debiasing needs a positive control**, and it belongs in the same run as the debiasing.

241. **Rank the error budget; do not merely disclose it.** M38 named fixed-pattern noise as its
     one caveat. FPN was worth 0.01–0.05 pp; the noise-model *scale* it did not name was worth
     ±2 pp, and the pipeline's own banner already marked that model DERIVED rather than
     measured. **An unranked budget flatters whichever term the author thought of**, and reads
     as rigour while omitting the dominant sensitivity. Sweep every input the pipeline itself
     labels underived, then report the terms in size order.

242. **Test a coefficient structure with data that can distinguish it.** All seven tests of the
     noise-correction term passed under uniform σ, which cannot separate `(2,1,1)` from any
     other coefficients summing to 4 — the exact structure the correction depends on was
     unconstrained by its own test suite. Non-uniform σ plus Monte Carlo separates the true
     structure from its rivals by 24–39 against a 0.096 error. **A test whose inputs are
     symmetric in the thing under test has no power over it**, and uniform-σ noise is the most
     natural and most inert choice available.
250. **A check that cannot fail is not evidence, and this corpus has now shipped three of
     them.** M20's optics "gate" re-derives `B` from the very knee `B` was obtained by
     inverting, and two of its six rows contain no measured quantity at all — no configuration
     of the model could have failed it, and the report concluded "the model is gated". M38's
     detail metric credits regularised argmax with **+35.47% "detail" on a FLAT ROI**. M33's
     two half-step phases, quoted as replicating each other to 0.05%, have hit rates summing
     to **1.0000 by construction** — complements cannot corroborate each other. All three were
     written by the orchestrator, published as confirmation, and caught only by independent
     authors. **This is the failure mode the project's entire measure-first discipline exists
     to prevent, and measuring instead of arguing did not prevent it**, because a measurement
     with no power to reject is arithmetic wearing evidence's clothes. **Standing requirement:
     before running any gate, control or metric, write down the input that would make it fail
     and confirm such an input exists.** Prefer the cheap adversarial one — a flat ROI for a
     detail metric, an a-priori value for a fitted constant, a known destroyer for a quality
     score, an arithmetic check that two "independent" arms are not the same number twice.
     Disciplines 13, 24 and 242 are special cases; this is the general form.
251. **Retire unnormalised `mean |∇|` as a scoring statistic.** It has now failed in three
     independent measurements by three authors: it rises **+35.47%** on a flat ROI under
     selection (fact 341); it rises **+23.7%** on Wiener output whose gradient *correlation*
     with truth **falls 12.1%**; and at σ=0.050 it reads plain argmax selection **above the
     noise-free latent itself** (fact 136). It is monotone in noise, so on any comparison whose
     arms differ in noise it measures the noise and calls it detail. The noise-subtracted form
     (M38 §2) is the minimum admissible replacement and still under-subtracts at `n_eff`→1.
     **Gradient correlation against a reference survived all three tests; prefer it wherever a
     reference exists.**
252. **The rules are an executable checklist, not a creed.** `AGENTS.md` rules 4, 9 and 10 were
     each written down, published, and then violated by a later milestone *by the author who
     wrote them*: M30's fact 242 is a raw argmax (rule 4), M38's detail metric shipped with no
     flat-ROI control (rule 9), and fact 88 compared a spatial sd to a temporal σ (rule 10).
     All three were caught by independent verifiers; none by the author. **Agreeing with a rule
     does not execute it.** Before publishing a milestone, walk the list and name, per rule,
     the line of code or the command that discharges it.
200. **Never quote an extreme-set overlap as "at chance" without the null's standard deviation.**
     A ratio of 0.53x to an analytic chance level sounds like agreement; it was 25 sigma from the
     milestone's own empirical null. Report the null's sd alongside its mean, always
201. **A reliability protocol built by adding noise to already-noisy data has two opposing
     biases, and neither may be assumed to dominate.** Extra noise pushes reliability down; the
     shared original noise realisation pushes it up. The only way to know the net is to build a
     stack whose truth you know and measure it. My own algebraic prediction of which dominates
     was wrong by measurement
202. **Never estimate your ground truth's adequacy with an estimator your own milestone
     disqualifies.** M33 measured the dense grid's residual deficit with the parabolic height fit
     it had just shown to be anti-correlated with truth, and thereby overstated its own safety
     margin by 22%
203. **Filters from `scipy.ndimage` are N-D filters. Calling one on a stacked cube silently
     filters along the stack axis.** `sobel(cube, axis=2)` smooths with `[1,2,1]` along frames.
     Either loop per frame or assert the cube result equals the per-frame computation. A one-line
     assertion in M32's build would have caught this
204. **Two decimation phases of the same grid are complementary, not independent.** Their
     agreement is a replication only for statistics not determined by the parity of the
     underlying argmax; for the "did I sample the peak" fraction it is arithmetically forced
205. **When a fact bundles a MEASURED number with a DERIVED mechanism, the mechanism needs its
     own falsification test.** Fact 281's number survived a block bootstrap, three shift
     controls, six channel redefinitions and two other stacks; its mechanism died to a single
     two-line Spearman. They were shipped as one fact under one label
206. **A confidence channel's sign can be an artifact of its gate.** Before shipping "channel X
     is anti-informative about Y", reimplement X two other reasonable ways. Three of six
     reasonable definitions of "predicted sigma" flip fact 281's sign
207. **A noise estimator that assumes independence along an axis is invalidated by any smoothing
     along that axis, including smoothing you did not intend.** `rough_sigma` divides the
     second-difference sd by sqrt(6) on the assumption of iid noise along k; the accidental frame
     smoothing made it read 21–28% low, and the report then interpreted the resulting
     disagreement with Monte Carlo in exactly the wrong direction
253. **Arithmetic is not where this project's errors live — choices are.** Across four
     independent verifications covering fourteen milestones, **every published number that was
     attempted reproduced exactly**. Not one defect was a miscalculation. All of them were
     choices: of nuisance estimator (M28's median gain, worth 3×), of reference (M38's gate-0
     denominator; M20's fact-24 baseline), of arm (M29 quoting a limit from the arm it declares
     defective), of null (M29's −0.5 shot-noise alternative where the real one is −0.0045;
     M34's "at chance" against an unmeasured sd), and of library default (M32's `sobel` on a
     cube). **So checking the arithmetic is nearly worthless here and re-deciding the choices
     is nearly everything.** A verifier that recomputes the author's formula on the author's
     inputs will confirm every one of these defects. **Verification must re-choose, not
     re-compute** — that is why the brief for an independent pass must name the choice points
     and require a different defensible setting at each, not merely an independent
     implementation.
80. **When a probe's response approaches unity as the probe gets *larger*, suspect the probe,
     not the scene.** A scene property does not know the plant size. On this project that pattern
     (0.526 at δ=1e-4 → 0.993 at δ=8e-4) was the first visible sign that the measured response was
     a sub-pixel locking artefact of the plant's own resampler rather than the defocus asymmetry it
     was built to calibrate.
81. **A control that removes the *cause* is worth more than a control that removes the *content*.**
     M10's mechanism table compared a real-pair arm against a synthetic-field arm and concluded
     "defocus", but it omitted the arm with real content and no defocus. **Two of the three cells of
     a 2×2 are not a mechanism.** Enumerate the full 2×2 — defect present/absent × instrument
     artefact present/absent — and fill all four.
82. **Before reporting "all arms are identical, so the treatment is inert", check that the winning
     row *could* have differed.** A comparison whose optimum is set by a row the treatment cannot
     touch has zero power: that is a broken instrument, not a null result. M23 caught this in its
     own first held-out script and preserved the broken version in the record (`§9.1`), which is
     the behaviour rule 20 asks for.
83. **Register the null's arithmetic, not just its existence.** `1/S` moving from 3.26 to 1.91 reads
     as a large effect until the shuffled null lands at 2.00. The informative number is the
     **fraction of the movement the null reproduces** (93.3%), and it should be computed and printed
     by the same script, not left for the reader to divide.
50. **A mean over cells is not a result until its sign test is next to it.** M17's candidate (c)
     shows a −2.14 DN mean improvement and a 15/30 win rate with p = 1.00 — the mean is a heavy tail,
     the operator is neutral. Report mean, median paired delta, win count and worst single-cell
     regression together, or the mean will be quoted as a win it is not.
51. **Before claiming two operators differ, check they are not a monotone reparameterisation of each
     other.** At regulariser width 1 the winner map depends only on the per-pixel *ordering* across
     frames, so any strictly increasing map of the response is the *same operator*. M17 verified
     `tenengrad-sq` ≡ `√box_mean(g²)` bit-for-bit on 18 cells; without that check its degree-2
     normalisation would have looked like a confound.
52. **A planted-scene harness whose tile margin depends on the measure set will silently move the
     scene when you change the measure set.** M17's edge probe rendered `vertical@261` instead of
     M13's `vertical@274` purely because a wide measure was dropped from the list; every number
     changed and nothing warned. Pin the margin, or pin the full measure list and step ladder, and
     gate on digit-for-digit reproduction of the prior milestone's rows before believing any new row.
53. **When a timing profile is not flat, report which hypotheses you falsified, not just the
     number.** M17 tested allocation (hoisted scratch) and the inner-loop modulo (block iteration) on
     `box_max`; both changed nothing, ≈2.9× remains unexplained. Recording the *failed* explanations
     is what stops the next milestone re-running them.
54. **An algorithmic complexity claim and a wall-clock claim are different claims and need different
     labels.** vHGW is O(1) in comparisons (DERIVED) and 4.90× in wall clock (MEASURED). Quoting the
     first as if it settled the second would have shipped a 2.7× regression.
254. **Check the brief against the tree before writing code, and report the check.** M18's brief
     asked for four things; two were already built, its stated test baseline was 70 when the tree
     had 107, and its acceptance target was quoted against a binary two milestones out of date.
     Milestone numbering is not the order the work happened in. **An agent that silently implements
     a stale brief produces a duplicate, and one that silently skips it produces an unexplained
     gap** — the deliverable is the reconciliation, in writing, before the first edit.

---
255. **Grep a milestone's own artifacts before quoting its number.** Fact 243
     quoted 1.89% for a penalty its own `01-dynamic-range.json` recorded at
     7.05%, understating the milestone's own conclusion by 3.7x. The two figures
     were the same quantity at different frames, and the prose named neither
     condition. No recomputation finds this, because both numbers are correct —
     it is a **choice of reporting condition**, the defect class of rule 24.
     Where a milestone's outputs hold two values for one quantity, the fact row
     must state which condition each belongs to and why the quoted one was
     chosen. See facts 433 and 435.
256. **A tunable is only portable if its units are.** `--gate` reads as a
     dimensionless number and is not one: it is scaled by a constant belonging
     to the focus operator, so the same value means different things for
     different operators - measured span at one declared gate is `n_eff` 1.131
     to 7.267 (fact 437). Before exposing a parameter in a profile, a preset, a
     plugin manifest or a README, **name the quantity it is measured in and say
     who owns that quantity**. If the owner is a component the user can replace,
     the parameter is not portable, and the portable form is the achieved
     outcome instead - here `--target-n-eff`, per fact 324.
257. **Calibrate an instrument against at least two targets that differ in a
     known way, and make it refuse to report when calibration fails.** One
     target can be matched by a compensating error; two cannot, and the
     *pattern* of which passed and which failed points at the fault. Fact 501
     is the worked example - a Python model of the focus operator matched the
     fine constant to 0.20% and missed the coarse one by 24.26%, and the one
     thing those two configurations differ in was the bug. This is the cheap
     structural answer to M31-V's standing objection that the Python proxies
     were never checked against the crate: a proxy that reproduces two in-crate
     constants measured in two different configurations has earned a narrow
     licence, and one that reproduces none has earned nothing.



## 6. Novelty — verified gaps, labelled as bets

Recorded with their queries; **all are UNVERIFIED as wins, and none is on the v1 default path.**

- **SR from focus-breathing sub-pixel diversity.** 4 arXiv queries, 0 relevant results. Breathing
  is a *scale* change, so it induces radially-varying sub-pixel resampling — free, *structured*
  diversity where handheld MFSR depends on hand tremor. Resolves the apparent contradiction with
  fact #9: random jitter is too small, but breathing offsets are deterministic and grow with radius.
- **Per-channel focus stacking exploiting longitudinal CA.** R/G/B focus at different z, so one
  bracket is three z-offset sweeps: redundant depth, per-pixel LCA measurement, and a structurally
  fringe-free output. `all:"depth from chromatic aberration"` -> 0 results.
- **Monocular depth prior as an ordinal regulariser** for macro shape-from-focus.
- **Diffraction+defocus PSF modelling at macro magnification** — `N_eff` flattens the focus peak,
  degrading sub-frame interpolation.

---

## 7. Risks

1. ~~**Alignment is a serial chain of length N**~~ — **RESOLVED by review, and it was self-inflicted.**
   C and D never disagreed on fact; they priced different algorithms. C's 5.0 s prices iterative
   chained ECC (latency-bound, ~150 GPU→CPU round-trips per pair, serial × N-1). D's 0.10 s prices
   the HDR+ tile search alone (bandwidth-bound roofline). §3.3 originally specified **both** and
   budgeted **one**. Deleting the chain in favour of a global frame-index model plus parallel
   per-frame refinement (§3.3) removes the Amdahl wall entirely and is *more* accurate.
   **Residual risk is now only that the global model is inadequate for some capture mode**, which
   phase 2 absorbs and the residual measures. Corrected estimate ~0.5 s. Still needs measuring.
2. ~~**Every focus-measure noise analysis in the literature is synthetic.**~~ — **CLOSED by M11.**
   The benchmark was built and run on real 33 MP RAW before choosing the operator, exactly as this
   risk demanded: 47 operators, pre-registered, two stacks, scored on a measured Pareto front of
   selectivity against noise excess. **The incumbent `ring(1,3)` ranks 26-27th of 36; the
   recommendation is Tenengrad under an 11x11 box window.** Facts 37-42.
   **Both residuals carried forward as q15 are now CLOSED by M13, and both went against M11.**
   The window is **27x27 (radius 13), not 11x11** — M11's choice is dominated 36/36 by w8 alone
   (fact 65) — and the missing depth discontinuity was not a gap in coverage but the *whole
   mechanism*: without one there is no interior optimum at all (fact 61). M11's per-pixel
   selectivity metric is confirmed blind to the damage in **30 of 30** cells (fact 64), which is
   why it chose a window less than half the right size. The operator ruling is untouched.
   **Doing this synthetically would have chosen wrong:** M11 measured `sml-w5` as best at zero
   noise (0.996) and *worse than the incumbent* at 4x noise.
3. **All deep MFIF/DfD SOTA is trained outside our regime** — MFIFB is 105 image *pairs*, Lytro has
   no ground truth, FOSSA trains at stack size 5 and 0.8-8.1 m. Keep learned components off the
   default path.
4. **Alignment residual silently poisons everything downstream** — sub-pixel misalignment looks like
   a focus difference to a focus measure, and like signal to a Wiener gate.
5. ~~**Additive dark/offset FPN** is the one live threat to the multi-frame averaging pillar~~ —
   **MEASURED and conditionally resolved (M4).** Raw averaging of darks follows a slope of
   **-0.2888**, not -0.5, departing from ideal at **N = 2**, and asymptotes at a fixed-pattern floor
   of **0.377 DN** reached by **N ≈ 7**. Subtracting a master bias built from *disjoint* frames
   removes 90-100% of that floor's variance and restores the slope to **-0.497 … -0.502 across all
   eleven ISOs** (-0.5019 at base ISO). So the pillar holds, conditionally: either the merge subtracts a bias frame, or it
   must not claim more than **2.6x** in the darkest regions at any N. Above roughly **12 DN** of
   signal it never binds. **The live threat has moved**: darks measure *offset* FPN (DSNU) only.
   **PRNU — multiplicative, signal-proportional — is invisible in this data and does not average
   away**, and it would bite in exactly the lit, low-contrast regions where M2 found the argmax
   defect. UNVERIFIED, and it needs flat fields (§10 question 3).
6. `rawler` is **link-freely but do-not-read**; `wgpu` 30 raw-memory export for a future CUDA path
   is architecturally possible but **not runtime-tested**.
7. **Occlusion on a rail** — **deferred with rail support (§9).** At depth discontinuities different
   frames see different surfaces; the Wiener gate misreads that as sharp-vs-blurred, and halos live
   at exactly those boundaries. Does not arise for in-camera bracketing, where occlusion is fixed.
8. **Gaps with no coverage in v1 planning at all** (review §7): colour management and the CFA→RGB
   transform (and the hard ordering constraint that white balance scales noise *per channel*, so WB
   must be ordered relative to the noise model); ~~dust and hot pixels, which are fixed in *sensor*
   coordinates and therefore smear into trails once the subject is stabilised — made harder to
   inspect by "never materialise aligned frames"~~ — **now MEASURED, and worse than stated.** M22
   located hot pixels (0.0346% of the sensor) and M29 settled dust: the estimator does **not**
   dilute it (`D = 0.999` at `n_eff ≈ 3`, fact 230), it cannot be detected from subject stacks at
   all (limit 32–50% shadow against real dust of 1–15%, fact 232), and the floor is scene texture
   that does not fall with frame count (fact 233). **Explicit handling — flat-field division or a
   defect map — is now a requirement rather than a gap**, and it is blocked on the flats specified
   in `captures-needed.md` §4. The trail-smearing half of the original risk stands unmeasured; a single bad frame (motion, wind, clipping)
   poisoning both reference and average, with no outlier rejection anywhere; **no way to act on the
   confidence map** (a confidence map you cannot act on is a bug report, not a feature); and the
   contributor loop — ~~build-time WGSL splicing means a plugin author recompiles the whole binary~~
   — **RESOLVED as a bug, not a risk (§3.4.1 B2).** It was a mistranslation of E's *"pipeline-build
   time"*, which in `wgpu` is a runtime call. Composing at run time costs nothing at dispatch and
   removes the recompile entirely.

9. **Out-of-tree plugins inherit an open research problem.** The Cordis paper's §6.6 surveys three
   approaches to dependency typing — nominal linking, interface drift, key collision — and
   **completes none of them**. It is stated in the paper as unsolved. In-tree stages never meet it,
   because the compiler resolves everything; the moment `strehl` ships third-party plugins that
   declare and discover each other's capabilities, it is ours. This is a further argument for
   keeping the *shape* and not the *machinery*, and for the contributed surface being data plus
   WGSL — a shader cannot drift an interface it does not have.

10. ~~**The GPU contribution format is being constrained by a CPU measurement.**~~ — **CONFIRMED as a
    real defect, then CLOSED by M7 (fact 30).** The suspicion was right and the consequence was
    larger than stated. Fact 21's "focus is 74% of decode" is scalar CPU; fact 10 measured D2D at
    1503 GB/s and suggested the focus volume might be single-digit milliseconds. **It is 4.117 ms**,
    bandwidth-bound at 84% of the measured read ceiling. **The fusion prize that justified
    constraining contributors to spliceable WGSL is 1.449 ms — 0.14% of the pipeline.** Ruling: the
    contribution rule is *"run on the GPU, emit an `f32` focus field"*, not *"be spliceable"*.
    Fusion stays as an internal optimisation, and is provably bit-identical either way. **General
    lesson, and it is the reason this risk was worth writing down: a measurement taken on one
    execution substrate was about to fix a public interface on another.** Check the substrate before
    a number is allowed to constrain an interface.
11. **NEW, opened by M6 — there is no working alignment strategy for deep stacks.** Project rule 6
    says *never chain, always align to a fixed reference*, and it was measured on 22 frames.
    **On 105 frames it breaks.** Direct-to-frame-0 alignment degrades badly and in places fails
    outright: **3 of 104 pairs produced no fit at all**, and those that did used a median of
    **18 of 96 tiles at 4.61 px rms**, because frames 0 and ~90 share almost no correlatable
    in-focus content (fact 4 — the winner map is a partition, so a deep stack's endpoints have
    nearly disjoint sharp regions). The two known options are now **both** refuted at scale:
    chaining is dead by pixel locking (rule 6, 25 px corner error), and a single fixed reference is
    dead by content overlap. M6 worked around it with a smoothed anchor model fitted across the
    stack, which is evidence that *something* in that family works, **not** a specification.
    **Mitigation: treat deep-stack alignment as an open design problem, not a solved one.** It is
    plausibly the single largest remaining unknown in §3.3, and 100+ frame stacks are the normal
    case for macro, not the exotic one. Do not let the skeleton's 22-frame success imply otherwise.

    > **STATUS: PARTIALLY SOLVED by M10 — usable, not solved.** A global least-squares solve over a
    > sparse multiscale graph of **direct** pairwise fits (never composing anything) places **all
    > 105 frames at 6.76 plane px** held-out corner error, against **76/105 coverage** for a fixed
    > reference and **40.3 px** for a chain. On shallow stacks it reaches **0.58-0.67 px**, at the
    > estimator floor. That is usable for a working pipeline and **not good enough for a final
    > render** — M10's pre-registered `T_usable` was 4.0 px and it missed.
    >
    > **The cause is now named, and it is not what this risk assumed.** Chaining does not fail from
    > accumulated *random* error. **Short-baseline edges under-report magnification change by
    > ~3.2-3.5x** (fact 43), coherently, so 36.4 px of the chain's 40.3 px is scale alone. The bias
    > needs a real inter-frame content change and lives below ~0.5 px of differential displacement
    > (fact 45) — it is not the resampler and not the estimator's response to geometry.
    > **Operationally: discard spans 1-2 from the solve, and never judge an edge by its residual**,
    > because short baselines look best by residual while being worst by truth.
    >
    > **The residual risk is bounded below by the measurements, not the solver** (fact 47): an
    > in-sample solve reaches only 5.875 px, and the edges' own cycle consistency is 6.8-13.0 px at
    > long spans. Better solvers cannot help; better *edges* can.
    >
    > **What remains open is no longer the shrinkage.** M12 answered it: **the short-baseline
    > shrinkage cannot be calibrated away** (facts 50–53). It is not a function of baseline in any
    > parameterisation, it varies **3.11× between scenes at matched displacement**, a fitted
    > correction transfers to **0 of 18** cross-scene pairs and makes the worst case **83.4× worse**,
    > and even an *oracle in-sample* correction leaves `coffee-bean`'s chain at **13.92 px** — twice
    > the 6.76 px the global solve already achieves with no correction at all. **Do not fit a
    > shrinkage correction.** The remaining open question is the narrower one: **does 6.76 px still
    > matter once the depth map is applied?**
    >
    > **What is now known about the shrinkage** is that it is a **per-scene** property: reproducible
    > within a scene to 0.15 σ, but ranging **1.03× to 3.26×** across the five-stack corpus. Its
    > mechanism is **UNVERIFIED** — no measurable property of the edge sets predicts it (fact 53).
    > The useful residue is diagnostic, not corrective: `1/S_W(1)` is cheap and cleanly separates
    > stacks that can be chained (112MSDCF recovers **99.0%** of its direct long edge over 78 chained
    > edges) from stacks that cannot (`coffee-bean`, ~30%).
    >
    > **The `112`/`113` pair did not do the job it was recruited for, and fact 49 is corrected
    > accordingly.** They do not sample one focus interval at two densities; they share a per-frame
    > step, with 112 simply running 16 frames further (fact 50). They remain a valid same-subject
    > *replicate* — which is what made the stability result possible — but they cannot discriminate
    > index span from physical baseline, because on this pair the two parameterisations make
    > identical predictions.

---

## 8. Sequencing — walking skeleton first, then experiments

The review's ruling, which the owner independently agreed with (*"probably measure before
building"*): experiments 1 and 2 are genuine go/no-go and cheap. Experiments 3 and 4 are **research
procrastination as standalone tasks**, because each needs decoded frames, a calibration, a focus
volume and an output path — i.e. you build most of the skeleton to run them anyway, in throwaway
form. So build the skeleton *as* the harness.

~~**Step 0 — the walking skeleton.**~~ — **DONE. See `M2-baseline-skeleton.md`.**
`decode 22 ARW -> calibrate -> NO alignment -> ring-difference focus volume -> plain argmax select
-> TIFF out`, in **1.03 s** for the whole stack. It delivered what it was built to deliver: a real
stacked image, the **named baseline artifact** §5 mandates, the harness experiments 3 and 4 need,
and above all *the measured argmax-noise defect on our own data* — **1.253x noisier than a single
unstacked frame**, ~1.48x structure-corrected, with 34.4% index speckle (facts 19-24). It was then
**independently re-derived by a second agent** (`M2-verification.md`), which confirmed the headline,
*proved its cause* with a mean/placebo control the author never ran, and refuted five supporting
numbers. The thesis number is no longer borrowed, and no longer merely correlational. Everything
after this is measured as a delta against a baseline that exists.

1. ~~**`rawler` decode throughput**~~ — **DONE. See `M1-decode-measured.md`.** 122/122 files
   decoded across two corpora, 0 failures. **60-frame stack: 1.78 s cold, 0.91 s warm** (rayon
   across files; 2.5x over one-at-a-time, because concurrent reads double effective disk
   bandwidth). Sensor constants independently confirmed. Decode is **6–12% of a 15 s budget, not
   the wall** — the dependency risk is cleared and the budget term is pinned.
2. **The sigma-vs-N curve.** Plot the *spatial* sd of an N-frame average, log-log. Slope -0.5 means
   independent; any asymptote **is** the fixed-pattern floor; re-run after disjoint-half master-bias
   subtraction to get the calibratable fraction. Go/no-go on the central pillar.
   **UNBLOCKED — running.** The owner delivered `D:\macro-dark-frames`: **11 ISO settings x 22
   frames** (first 2 of each discarded for stabilisation), well beyond the 2 ISOs requested. The
   extra ISOs additionally permit a model-free test of fact 14's **ISO 400 second base ISO** via a
   discontinuity in read noise vs ISO. **A photon-transfer measurement of `g` is still not possible
   from darks** — no signal, no signal-variance — so `g` stays DERIVED and **question 8** stays open,
   now needing flat fields rather than darks.
3. ~~**Focus-measure bake-off on real RAW**~~ — **DONE. See `M11-focus-bakeoff-measured.md`.**
   47 operators, pre-registered, two stacks, scored on a measured Pareto front of selectivity
   against noise excess. **`ring(1,3)` — the shipped default — ranks 26-27th of 36. The winner is
   Tenengrad (Sobel gradient MAGNITUDE — fact 70, not the squared "energy" the name implies) under
   an 11x11 box window.** Re-tuning the ring cannot close
   the gap; the best ring reaches only ~60% of the leader's selectivity. **Risk 2 closed; facts
   37-42.** The headline result is fact 37: **no operator anywhere on the front is noise-free**, so
   operator choice alone cannot rescue a selector — which is the strongest direct evidence yet for
   §1's thesis. **The window was subsequently superseded by M13 — 27x27, not 11x11 (facts 60, 65);
   the operator was not. SHIPPED M14** (facts 70-71), with one blind spot found on verification
   (fact 73, question 19).
4. ~~**Alignment cost and accuracy at scale.**~~ — **DONE. See `M3-alignment-measured.md`.**
   **13-16 ms/frame; 0.78-0.96 s for a 60-frame stack**, scalar CPU, unoptimised, all frames
   independent. Chaining measured at **25 px error at the sensor corner** — dead by measurement,
   not argument. A 4-parameter similarity is sufficient (affine and quadratic buy ≤6%); rotation
   is unmeasurable; the scale centre is **(−22, −113) px**, refuting the corpus's (−176, −338).
   No global model of drift against frame index — it is less accurate than the per-frame fit it
   was supposed to seed. **Open:** the 0.6-1.3 px residual is neither estimator noise nor global
   model error; the discriminating experiment needs the skeleton's winner-index map.

Test data exists: `C:\dev\macro\test\109MSDCF\*.ARW` (36 MB lossless-compressed) plus `D:\personal\`
(2310 files, verified decodable).

---

## 9. Scope

**v1** — CLI. ARW in, tiled float TIFF + DNG out. Calibrate, coarse-to-fine per-frame alignment
against a fixed reference (4-parameter similarity, no chaining) for **in-camera focus bracketing**,
ring-difference focus volume,
noise-gated merge with a regularised reference emitting RGB, confidence map, capture advisor.
`wgpu` compute. Stages in-tree behind a **minimal** stage interface. A/B harness and the
RSS/wall-clock ratchet. Sony A7C II + SEL100M28GM profiles **plus a runtime noise estimator** for
unprofiled bodies.

**Rail capture is deferred (owner decision).** No rail is available, so every rail claim here would
be *derived and untested* — shipping it would violate §5. What survives, and why the detour was not
wasted:

- **The two-phase aligner stays**, because the review showed it is correct for breathing on its own
  merits: it deletes the serial chain of length N regardless of capture mode. Rail was
  corroborating evidence, not the reason.
- **Tile refinement reverts from mandatory to polish.** Rail was what made it mandatory. For
  breathing, a global model plus refinement is belt-and-braces, and the refinement can be measured
  and dropped if it earns nothing.
- **`CaptureMode` stays as a two-variant enum**, and mode detection stays on the roadmap. That is
  the one narrow seam the rail case genuinely exerted pressure on (§9, review §3), and it costs
  almost nothing to leave in place.
- **Occlusion handling (risk 7) is deferred with it.** Breathing does not change occlusion.
- **MFSR stays out of v1.** Rail was what put it back on the table.

Do not silently apply the breathing model to rail data. Detect and warn.

**Cut from v1 by the review — abstractions not earned by any second implementation:**
darktable-style two-pass ROI negotiation (replaced by `fn source_roi(&self, out, warp) -> Roi`,
**not** the scalar `halo()` the review first proposed — see §3.4.1 B1); the RON pipeline
graph (a graph language that can express exactly one topology; replaced by a `serde` struct with an
algorithm *name* per slot); Cordis-style `ctx.provide/require` DI (a `HashMap<TypeId>` replacing
eight explicit arguments, converting compile-time errors into runtime ones); `try_activate ->
Inactive{unmet}` (nothing can be unmet when everything is in-tree; replaced by plan-time resolution
reported through `Provenance` — §3.4); and a universal per-stage CPU fallback (keep
`gpu() -> Option<..>` in the signature, but don't write every kernel twice).

**Also cut, by measurement rather than review (§3.4.1):** `Resources`/`negotiate`/`Access` and the
tiling apparatus (fact 22 measured 1.81-1.94 GB peak RSS — there is no 24 GB problem to tile), and
the derivation cache (rule 2 forbids materialising the aligned frames it wanted to cache, and fact
15 prices all alignment at 0.78-0.96 s). **Both were E §4.12's stated justification for the whole
architecture.** With them gone, the plugin system stands on contributor experience alone — which is
exactly what the owner asked for, and is now the only thing it should be designed against.

**Kept, and correctly credited:** **runtime** WGSL composition with a content-hashed SPIR-V cache
(earned by the four focus-measure candidates in experiment 3; the `build.rs` variant was a
mistranslation of E and is deleted — §3.4.1 B2); `TileView` (earned by gather-at-consumption, and
only if it carries the geometry that rule 2 actually needs); the injected noise model; u16 CFA
storage.

**The genuinely irreversible decisions are about data, not structure** — u16 CFA storage,
never-materialise/gather-at-consumption, and the injected noise model. Those are load-bearing and
must be defended now. `(id, semver, params_hash)` cache keys are no longer among them: they were
the keys of a cache that is no longer being built. The rest are cheap refactors of
eight known call sites, and the rail requirement demonstrated the principle: the first genuine
second implementation the project met exerted pressure on **exactly one narrow interface** and on
none of the framework. Let the second variant of each thing tell you where the seam goes.

**Two signatures stop being cheap the moment the first stage is written against them**
(§3.4.1 B1, B3): `source_roi(out, warp)` rather than `halo()`, and `support_px()` on the focus
measure. Fix both before writing a stage, not after.

**Deliberately not v1** — rail capture and occlusion handling, CUDA, dynamic/WASM plugins, GUI,
decode/compute overlap, learned components, super-resolution, per-channel LCA exploitation.

---

## 10. Open questions

**Needs the owner:**
1. ~~20 lens-cap dark frames at ISO 100 and ISO 400~~ — **DELIVERED at `D:\macro-dark-frames`:
   11 ISO settings x 22 frames, first 2 of each discarded.** Experiment 2 is unblocked and running;
   see `M4-fpn-measured.md` when it lands.
2. ~~A rail-captured stack~~ — **no rail available. Rail support deferred from v1 (§9).**
3. **Flat fields, if `g` is to be measured rather than inferred.** Darks cannot supply a
   photon-transfer curve. Spec to be added to [`../captures-needed.md`](../captures-needed.md) §4
   only if experiment 2 shows it would change a decision.
4. ~~Pupil magnification `p` for the SEL100M28GM — a one-hour bench measurement~~ —
   **CLOSED by M5 (fact 27), and the premise was wrong twice over.** (a) The rig is not the bare
   lens: **every stack carries a 2x teleconverter** (fact 26), so the quantity wanted is the bellows
   factor of the *composed* path, and a bare-lens figure would not apply even if one existed. (b) It
   did not need a bench: M5 measured `(1 + m/p) ∈ [2.41, 3.06]` from the diffraction cutoff in the
   existing stacks. **What the owner may still optionally supply is a ruler or stage micrometer in
   frame at the working magnification** — needed only to separate `m` from `p`, and hence to
   extrapolate `B` to *other* magnifications. Nothing is blocked on it.

**Needs a decision, not a measurement — both raised by `M2-rss-resolved.md` §4:**
12. ~~**What unit is the 8 GB ratchet in?**~~ — **DECIDED: GiB.** The owner deferred the call
    (*"i have no idea. do what you think is right"*), so it was taken on internal coherence:
    `MEMORY_BUDGET_BYTES` is `6 << 30`, i.e. 6 **GiB**, and a decimal-GB ratchet beside a GiB budget
    in one binary is incoherent. `8 GB` now means **8 GiB = 8,589,934,592 bytes**, as a byte
    constant. The N=220 run passes at 7.44 GiB with 576 MiB of margin. **The unit was the less
    important half of this question**: pinning it exposed that an absolute peak-RSS ceiling is
    machine-dependent (fact 22: 833 MB to 4.0 GB on identical input, purely from core count) and is
    therefore a flake rather than a regression test. **The ratchet is respecified as three
    assertions in §3.2.1**, of which the machine-independent *shape* test is the one that carries
    the original intent. Nothing is enforced in CI yet.
13. **Buy planner accuracy at the cost of parallelism?** `per_worker_bytes` omits decoder scratch
    and under-counts by 13-24%, so `by_memory = MEMORY_BUDGET_BYTES / per_worker_bytes` licenses
    more workers than 6 GiB can pay for. Modelling the scratch honestly would drop N=105 from 18
    workers to ~14 — a real speed cost on a project whose stated goal is SOTA speed. The
    alternatives are to raise the ratchet (the box has 64 GB), or to keep the pool and accept that
    the budget constant is nominal. **Do not fix it by lowering `MEMORY_BUDGET_BYTES`** — that
    treats the symptom and makes the model *less* truthful, not more.
    **Owner's answer: measure the decoder scratch properly first, then decide.** That was M8, now
    **landed and independently verified.**
    **M8's answer changed the premise: the scratch was never the main term.** Decoder scratch is
    39.36 MiB per concurrent decode (fact 34), but the reduce tree costs **110.04 MiB per level of
    `⌈log₂ chunks⌉`** — 550 MiB at 18 chunks, larger than all the scratch combined (fact 33). The
    question was pointed at the wrong term.
    **DECIDED — M8 is now the default model; the cap moves 20 → 16.** N=22 → 11 chunks
    (**unchanged**), N=105 → 15 (was 18), N=220 → 16 (was 20). Measured end-to-end
    **6909 → 5762 MiB**. **The reasoning, since this question framed it as a speed-vs-accuracy
    trade and it is not one:** the `Buffers` model licenses 20 workers where 6 GiB pays for 16, so
    this is a **planner error, not a tuning preference** — the plan was exceeding the budget it
    claims to respect. M8 is also measurably the better model out of sample (**8.4% mean / 17.5%
    max** vs 12.0% / 25.2%). The speed cost is smaller than this question assumed: the reference
    22-frame stack does not move at all, and the cap only binds above ~100 frames.
    **Raising `MEMORY_BUDGET_BYTES` was rejected** — the box having 64 GB is a fact about *this*
    rig, and tuning the planner to it contradicts the portability goal (§9) as squarely as the
    "lower the budget" trap this question already named. The constant stays 6 GiB.
    **Verified before adopting:** both models produce **byte-identical output** (SHA-256
    `3C9A08EA…` on 109MSDCF at 32 threads, unchanged across the default flip), `Buffers` stays
    reachable via `--memory-model buffers` and is pinned by its own test, and the new default has a
    negative control (reverting `#[default]` turns `the_default_memory_model_is_m8` red).
    **A prior attempt to fit this was abandoned deliberately and must not be repeated: two
    points (11 workers → 364 MB, 18 → 379 MB) fit a line with a negative intercept, which is
    unphysical.** *(M8 avoided it — 17 points, k swept 0-32, all intercepts positive. It also found
    that those two numbers were **in mismatched units**: 321 was decimal MB, 364/379 were MiB.)*

**Needs measurement, not argument:**
5. ~~Alignment cost for the two-phase design~~ — **closed by M3.** 13-16 ms/frame, 0.78-0.96 s for
   60 frames. The two-phase design itself was superseded: no global frame-index model, no chaining,
   per-frame coarse-to-fine against a fixed reference.
6. ~~**What the 0.6-1.3 px alignment residual is**~~ — **CLOSED by M6. It is blur-induced
   correlation bias (cause b), and the architectural consequence is the opposite of what this
   question assumed.** In-focus tiles align at **0.144-0.172 px**, at or below the 0.19 px estimator
   floor; far-from-focus tiles in the same pairs sit at 0.25-0.69 px; the gap survives within-pair
   (+0.667 px, p=0.010) and within-tile (+0.460 to +0.599 px). Cause (a)'s signature is null
   everywhere (p > 0.22) on a statistic that fires at ρ = −0.83 when (a) is planted. **But the bias
   is symmetric degradation, not directed displacement (fact 31), so the lens plugin dies anyway**
   and §3.4.2 is closed. The fix is in the aligner — weight tiles by `|c − w|` — and needs no lens
   identity. *(Method note worth keeping: M3's own design could not have answered this. Aligning
   everything to frame 0 makes `|w − k| − |w − 0| = k − 2w` an exact degeneracy between the two
   hypotheses. M6 broke it with a sliding baseline, aligning `(j, j+Δ)` for every `j`.)*
7. The radial dependence of sub-pixel jitter — resolves the fact #9 / novelty-bet-#1 contradiction
   (§4.1). Still live for breathing: bet #1 claims breathing itself supplies sub-pixel diversity.
   M3's per-frame alignment residuals are the raw material.
8. `g` by direct photon transfer rather than by white-level consistency (§4.1). Needs (3), not (1).
9. ~~**Is the focus-measure/merge coupling (fact 25) severe enough to belong on the interface?**~~ —
   **CLOSED by M9. The coupling is real, it is not to support, and it does not belong on the
   interface.** Excess tracks the **centre-tap sensitivity fraction φ** (ρ = +0.918 / +0.894), not
   support radius (ρ = −0.170 / −0.243, n.s.). A merge told only `support_px()` is worth
   **+0.0000 / +0.0009** ratio units over a merge told nothing, against a pre-registered 0.02 floor
   and a placebo floor of +0.0326. **`support_px()` comes off; nothing replaces it** — φ is
   framework-measurable by finite-differencing the contributed measure. §3.4.1 B3 rejected,
   facts 35 and 36 added, fact 25 reinterpreted. **With this, every question that gated the plugin
   interface is closed.**
10. ~~**How big is the halo actually?**~~ — **CLOSED by M6 (fact 32). A scalar `halo()` does not
    survive, but B1's stated reasons were wrong.** Corner halo is **32.39 px**, not 39 — B1 quoted
    the Euclidean *displacement*, and a halo is a rectangle expansion, so the right quantity is
    `max(|dx|,|dy|)` (1.20x overstatement). Within-frame waste is **1.34x** at 128 px, not 2.6x, and
    on its own would **not** have killed the interface. What kills it is **stack dependence**, which
    B1 never raised: 19.42 / 32.39 / 89.23 px across three stacks, and 0.87 → 89.2 px as N goes
    5 → 100. `source_roi(out, &Warp)` gets both the radial and the stack dependence for free.
11. ~~**Price the GPU fusion prize before it constrains the contribution format**~~ — **CLOSED by M7.
    The answer is no.** The fused focus+merge kernel runs 22 frames in **4.117 ms**, bandwidth-bound
    at 84% of the measured read ceiling; the fusion prize is **1.449 ms = 0.14% of the pipeline**;
    the most permissive plugin model imaginable (whole focus volume resident) costs 1.683 ms more
    than fusing. **Contributors will not be constrained to spliceable WGSL.** Fact 30, risk 10.
    Independently reproduced to within 0.1%. *(Note that this closes question 11 without running
    experiment 3 — the bake-off is still worth doing, but it is no longer load-bearing for the
    plugin interface, which is what §9 had staked on it.)*
14. **Does `B` hold away from 2:1, and how much does the λ assumption cost?** M5's two disclosed
    systematics. `B` is measured at **one** focus distance (`FocusDistance2` 0.274-0.277 m); at
    infinity `B → 1` trivially and the interpolation between is unmeasured. And `λ_eff = 550 nm` is
    **assumed** — it is M5's largest single error term at ±10%, and it moves the advisor's critical
    aperture from f/6.21 to f/5.69-f/6.83. Both are cheap to close: a second aperture sweep at a
    different magnification for the first, a CFA-green-weighted `λ_eff` for the second. Neither
    blocks anything today, and **both must be stated whenever `B` is quoted.**

15. **~~Where does the window optimum actually sit, and what does a depth discontinuity do to it?~~
    CLOSED by M13, and the answer superseded M11's recommendation.** The optimum is at **radius 13
    (a 27x27 box)**; it turns over **sharply**; and it turns over *only* because of depth
    discontinuity — remove the step and the argmin runs to the sweep endpoint (facts 60, 61). Both
    of the question's suspicions were right and both were understated. M11's 11x11 was not a lower
    bound but **dominated** (fact 65), and the hypothesis that its metric is "structurally incapable
    of seeing that damage" is confirmed at **30 of 30** cells with an 18.48 DN mean penalty
    (fact 64). The hypothesis that a fronto-parallel plant says nothing is confirmed and strengthened
    — such a plant *cannot* turn over (fact 62), so M11's extension carried no information rather
    than weak information. Adaptivity was measured and is **not** recommended (fact 67). The
    prediction that this needed no new capture held: everything was planted.
    See `docs/research/M13-window-depth-measured.md`.

16. **Can any realisable rule reach the adaptive headroom?** A per-pixel oracle choosing between a
    narrow and a wide focus window gains **5.7-46.8%** of band RMS at occluding edges (fact 67).
    Every gate M13 tried reached at most **+5.4%** and usually *lost*, down to −153.6%. That
    headroom is **larger than the entire w5→w13 window improvement**, so it is worth more than any
    further window tuning. Untried: gating on the focus curve's **peak sharpness** rather than on
    inter-window disagreement; a guided-filter or cross-bilateral regulariser on the selection map;
    explicit occlusion detection. This is also the natural home for the project's confidence output
    — an occlusion detector and a confidence map are close to the same object.

17. **~~Does the window optimum survive the merge regulariser?~~ — CLOSED by M15. Yes, and my
    hypothesis was refuted.** The argmin is **w13–w14, always `interior`, at every regulariser
    width from 1 to 33**; shipping w13 costs **0.050 DN** at the reference width 17 against a
    pre-registered 0.87 DN threshold (facts 80–81). The redundancy argument below was right about
    the *mechanism* and wrong about *where it applies*: the regulariser does substitute for the
    window at **1.72 : 1** — but only on cells with **no depth discontinuity** (r² 0.94). On the
    cells that actually decide the window, the substitution rate is **≈ 0** (fact 82), because a
    wide window buys contrast *localisation* at an occluding boundary and the regulariser cannot
    supply it — it acts after the per-frame focus field is formed. **M13's recommendation stands
    unchanged and its last recommendation-moving caveat is discharged.** The regulariser remains
    the largest unbuilt quality win in the project (fact 84: −35% absolute error), so fact 80 is
    best read as a *forward guarantee* that shipping it will not reopen the window.
    *(Original statement of the question, preserved:)* Every one of M13's 7,200 edge
    measurements is at regulariser `width = 1` — that is, with the regulariser switched off. M2
    measured that the regulariser alone cuts merged-noise excess from 1.2527 to 1.0737 at width 17,
    which is a *larger* noise reduction than the entire window axis provides (1.1324 → 1.0778 over
    w5→w40). The two mechanisms are plausibly redundant: if the regulariser is already buying the
    variance reduction, the wide window's benefit shrinks while its occlusion-halo cost does not,
    and **the optimum should move narrower than w13**. *(Raised by the orchestrator while verifying
    M13, which disclosed the gap but did not propose it as a question.)*

18. **Why does the 119MSDCF horizontal texture pair behave differently?** Its `E_excess` optimum
    sits at **w8 at all five depth steps** — the only cell with a constant argmin — while the other
    five scatter over w9-w33, and it is the source of **every** head-to-head loss w13 suffers
    against w5 (fact 65). One texture pair per stack cannot distinguish an occlusion-geometry effect
    from a texture effect. Note this is the *second* open question whose answer needs a corpus with
    deliberate variation in subject depth and texture — the first is fact 53's unexplained shrinkage
    mechanism. **One capture campaign would serve both, and it is specified in
    [`../captures-needed.md`](../captures-needed.md) §5.**

19. **Does the monotone-edge blind spot (fact 73) cost anything on real subjects, and what is the
    cheapest fix?** The blindness is exact and analytic — TV conservation — but its *incidence* is
    unmeasured: how much of a real macro frame is smooth-gradient content with no texture at any
    scale the operator can see? Three candidate fixes, none measured. **(a)** Keep the wide window
    and let confidence handle it — cross-frame spread reads zero, so those pixels are correctly
    marked unreliable and can fall back to a neighbourhood vote. Cheapest, and it needs no operator
    change. **(b)** A dual-radius response — take the max, or the spread, of radius-1 and radius-13
    fields; radius 1 discriminates the same edge at 0.376. Costs one extra plane and one extra pass.
    **(c)** Squared magnitude (`tenengrad-sq`), which is **not** TV-conserving and so does not have
    this null — but it is a different operator with different noise, and M11 benchmarked it only at
    w2. Measure (a) first: if the confidence channel already isolates these pixels, the operator does
    not need to change at all. **Guard against overfitting to the fix:** this must be scored on the
    same edge cells M13 used, so a repair cannot silently regress the textured-occlusion case that
    picked w13 in the first place.

20. **Why does edge orientation set the direction the window optimum moves?** Under regularisation,
    `horizontal` occluding edges move the optimum narrower **unanimously** (10/10, median −2.5)
    while `vertical` (6/10, +1.5) and `bar` (6/10, +1.0) move wider; they cancel in the aggregate
    (fact 83). Both the Sobel pair and the box window are 90°-symmetric, so the asymmetry is either
    **texture anisotropy** in these two stacks — harmless, and a corpus artefact — or a property of
    the `|d| ≤ 24` band geometry that `E_excess` uses, which would be a **defect M13 and M15
    share** and would put a directional bias in every window number either produced. Distinguishing
    them needs a synthetic isotropic texture and a rotated band; both are cheap. `UNVERIFIED`.
    *(Raised by M15 as its question 19; renumbered to 20 — 19 was taken by fact 73's blind spot in
    a concurrent milestone. This is exactly the collision the fact-number reservation under §4
    exists to prevent, arriving on the question list instead.)*

    **CLOSED by facts 90-92** (M16, after 6.0 h of measurement). The answer is
    that nothing is broken: the asymmetry is a property of the corpus subjects.
    Transposing the plant's textures 90° while holding every piece of machinery
    fixed transposes the asymmetry exactly (median shift difference **0.0**
    windows against **8.0** for the same geometry), and symmetrising the texture
    nulls it outright. The mechanism is that a horizontal edge is localised by
    `Gy` and a vertical edge by `Gx`, and this corpus carries **14-22x more
    vertical gradient energy**. **The review's proposed fix — per-frame row and
    column mean subtraction — changes the statistic by 0.0 windows** (fact 96),
    and the row-FPN mechanism it assumed is refuted at source: this sensor's
    fixed pattern is isotropic at all 11 measured ISOs (fact 93). **`WINDOW_RADIUS = 13` survives** (fact 97).

45. **Does masking actually improve the merge, and how does the mask interact with the estimator's
    own weights?** M28 measured a *detector* — that a ≈20 µm subject displacement is caught 53.8%
    of the time at a 1% false-positive rate, and that a clean-calibrated threshold flags 8.33% of
    `coffee-bubbles`' tiles and 17.88% of `foam`'s. **It measured no merged image at all.** Whether
    flagging 8–18% of tiles improves or harms the result is open, and the honest prior is that it
    could go either way: masking removes contaminated samples but also removes *focus coverage*,
    which fact 213 measures as the scarcer resource in most brackets. Two specific unknowns. (a)
    The mask and the merge weights are both down-weighting devices and may double-count — a frame
    that is off-peak already gets a low weight, so masking it again is not free. (b) M28's plant is
    a **rigid translation of a square tile**; real outliers deform and occlude, and an occluding
    edge produces exactly the bimodal through-focus signature M21 measured at 4.38× enrichment, so
    the mask and the occlusion detector may be firing on the same pixels for opposite reasons —
    one wanting to discard them, the other wanting to unmix them. Resolving (b) probably requires
    the M25 twin, since only a simulator knows which of the two a given pixel really is.
    `UNVERIFIED`. *(Raised by M28; numbered 45 to clear the reserved question blocks.)*

50. **Is there ever a reason to widen the gather deliberately, trading focus coverage for
    defect suppression?** M29 refuted the free-lunch version — `n_eff ≈ 3` adjacent frames give
    `D = 0.999`, no suppression at all (fact 230). But the mechanism it identified is a *dial*,
    not a dead end: suppression is bought by the **span** of frames averaged, not their count,
    because span is what buys relative displacement. The measured direction is right (dilution
    appears in the wide-span columns) but the numbers that would price it rest on
    `06-dilution.py`'s `sep ≥ 8` displacements, which lost phase-correlation lock and are
    disclosed as unusable. Three things are unknown. (a) The honest exchange rate: a wider gather
    costs resolved detail — fact 213 already prices focus coverage as the scarcer resource — and
    nobody has measured what a defect-suppressing span costs in sharpness. (b) Whether it matters
    at all once flats exist, since flat-field division removes dust outright and is strictly
    better than diluting it. (c) Whether the same dial helps for defects flats *cannot* fix —
    fixed-pattern noise that survives calibration, or the trails risk 8 predicts when dust smears
    under the warp. The likely answer is that (b) makes this moot for dust and (c) is the only
    live case, which would make it a low priority — but it is the sort of thing that is cheap to
    settle once the M25 twin can plant a defect with ground truth. `UNVERIFIED`. *(Raised by M29;
    numbered 50 to clear the reserved question blocks.)*

55. **Does a genuinely high-contrast subject overturn M30's verdict on exposure bracketing?**
    Fact 240 (allocation is neutral at fixed light) is a property of the *sensor* and does not
    depend on the subject. Facts 241-242 do: **0.0000% read-limited and 0.075% clipped are
    measurements of this corpus**, which is three stacks of a bean, a coin-like subject and a
    coffee surface, all under diffuse continuous light. A wet chitinous insect under flash — the
    canonical macro subject and the one the tool most wants to serve — could plausibly clip one
    to two orders of magnitude more, at which point the per-stack advisory in fact 243 starts
    firing routinely and the "support it, do not default it" ruling may need revisiting for
    specular subjects specifically. **The measurement is cheap and needs no new theory** — the
    clipping-at-gathered-frames statistic runs on any stack — but it needs a capture that does
    not exist yet, so it is a question rather than a request until a specular subject is shot.
    Note the asymmetry that makes this worth watching: neutrality means bracketing costs
    *nothing* at fixed light, so the decision threshold is not "is HDR worth it" but merely "is
    any pixel clipped", which is a much lower bar than the corpus currently clears.
    `UNVERIFIED`. *(Raised by M30; numbered 55 to clear the reserved question blocks.)*

65. **Where does confidence actually come from, now that the focus curve cannot supply it?**
    Fact 263 relocated the problem but did not solve it. Three candidates are named and none is
    measured: **(a)** the predicted σ of the merged estimate under the M4 noise model — cheap,
    externally referenced, and the one quantity the project already trusts everywhere else, but
    it reports only *photon* uncertainty and fact 263 says the live failure is not photon
    uncertainty; **(b)** the width of the acceptance set, i.e. M27's `n_eff` — available in one
    pass as the calibrated posterior's perplexity (fact 261), with fact 262 supplying the null it
    would have to be referenced against; **(c)** the sub-frame peak offset — the distance from
    the true through-focus peak to the nearest sampled frame, which fact 263 argues is the actual
    mechanism behind M2's argmax defect and which **nothing in the project currently estimates**.
    **UPDATE — (c) is now measured: M33 gives it a magnitude (fact 270: 48.7% of pixels miss, median
    deficit 4.64%, p99 17.34%) and an estimator that clears a calibration bar (fact 272). (a) and (b)
    remain unmeasured, and whether (c) *predicts M2's defect* is still open.**
    My guess is that (c) is load-bearing and (a) is merely easy, and that a shippable confidence
    output is a small vector rather than a scalar — a predicted σ, an `n_eff`, and a set of flags
    — which is what discipline 29 demanded before there was a mechanism to justify it. **The
    cheap falsifiable version:** M13's cells have known depth, so the sub-frame offset is
    available as ground truth there, and whether (c) predicts M2's defect can be answered on an
    existing harness. `UNVERIFIED`. *(Raised by M32; numbered 65 to clear the reserved question
    blocks.)*

70. **Does the log-domain sub-frame fit hold up away from this stack's optics?** Fact 272 settles
    `B` §4.4 on `coffee-bean` at one aperture and one magnification, and fact 274 already shows the
    response is **not** exactly Gaussian — the implied width drifts 1.68 → 2.45 dense frames across
    the decimation ladder. The Gaussian model is therefore an approximation that happens to be much
    better than the parabolic one *here*, and two things could change that. **(a) Aperture:** M5
    measured `N_eff = N_marked × (1 + m/p)`, so the defocus and diffraction contributions trade off
    with aperture, and the through-focus shape is their convolution — a wide-open frame is
    defocus-dominated and plausibly closer to Gaussian, a stopped-down one is diffraction-dominated
    and plausibly not. **(b) Focus-measure scale:** everything in M33 used radius 2, and M21 already
    found that scale changes what the curve reveals (bimodality present at R=2, invisible at R=13).
    A wider window averages over more depth and must broaden the response, possibly changing which
    functional form fits. **The cheap version needs no new capture** — `112MSDCF` and `119MSDCF` are
    different apertures and magnifications, and the radius sweep is free — so this is a question only
    because it has not been run, not because it is blocked. **If the shape turns out to be
    aperture-dependent, the fit's functional form becomes a candidate entry in the optical profile**,
    which would be the first thing to genuinely need the camera/lens plugin seam. `UNVERIFIED`.
    *(Raised by M33; numbered 70 to clear the reserved question blocks.)*

75. **Does C1 — the predicted σ of the merged estimate — predict anything real?** M34
    established that it is *orthogonal* to the other channels (fact 280) and *self-reproducible*
    at 0.7642 under an independent noise draw. It established nothing about whether it is
    **right**, because its target is the merged estimate's actual error and this project has no
    ground truth for that. Worse, the one target it could be scored against it gets **backwards**:
    fact 281's 0.89× lift. Two ways to obtain the missing truth. **(a) The simulator (M25):** a
    latent scene rendered through the measured forward model has a known answer at every pixel,
    so predicted-vs-actual error is directly scoreable — this is the cleanest route and it is
    already in flight. **(b) A repeat-capture pair:** two identical brackets of a static subject
    give an empirical per-pixel error from their difference, with no model in the loop at all;
    it costs one extra bracket and nothing else, and it is the only route that does not inherit
    the simulator's assumptions. **Until one of these lands, C1 must not appear in a product
    claim** — shipping a confidence number that has never been checked against a real error is
    precisely the defect this project exists to remove. Note also that M34's acceptance set has
    median size **1.0** at a 1σ_f gate, so C1 is currently measuring single-frame SNR rather than
    any merge benefit; it will change character once M18's gate is tuned, and these numbers must
    be re-measured against the real merge rather than carried forward. `UNVERIFIED`.
    *(Raised by M34; numbered 75 to clear the reserved question blocks.)*

85. **Where does the last ~0.07 of the M33↔M35 calibration gap live?** M35 §4 accounts for
    M33's published numbers exactly and §3's factorial accounts for most of the gap to M35
    script 02, but not all: the same estimator reads **0.479** on M33's cell and **0.549** on
    M35 script 02's. Three harness differences compound into it — baseline defined as
    min-of-dense versus 5th-percentile-of-decimated, all 1,048,576 pixels versus a 40,000
    sample, and interior judged by the dense versus the decimated argmax. **It is a harness
    difference and not an estimator one** — the ordering and sign of the margin are identical
    in all twelve cells measured — so nothing currently depends on it. It is recorded rather
    than rounded away because an unreconciled residual is how a real defect hides, and
    because M18 will implement exactly one of these conventions. **Flagged to the M36
    verifier.** Resolving it also fixes which convention `strehl-core` should use, which is a
    decision that has to be made anyway. `UNVERIFIED`.
    *(Raised by M35; numbered 85 to clear the reserved question blocks.)*

90. **What is the gate threshold, and does the built merge actually beat 1.0 on real
    frames?** `Gate::threshold` is the one free parameter in the merge and it is
    deliberately unmeasured and explicit at the API boundary rather than buried in a
    default. Its calibration target is already measured — **fact 212's `nwide = 3`** at full
    sampling density, the count of frames within 50% of peak height — and `Estimator::n_eff` is
    an output for exactly that purpose. The two acceptance sets are **not the same rule**
    (`nwide` thresholds on peak *height*, the gate on the calibrated *noise*), so 3 is a target
    to land near, not a number to reproduce. **Nothing here has touched a
    real frame yet.** The merge is proven never to be *noisier* than one frame, which is a
    statement about σ; fact 24 is the reason that is not sufficient, because a mean's σ
    can look harmless while its gradient collapses 58%. So the acceptance test is the
    **paired** one M2-verification established: flat-ROI noise ratio ≤ 1.0 *and* detail
    retained, measured with the same harness that produced 1.253×, on the same frames.
    Wiring the two-pass merge into `strehl-cli` as an additive subcommand — reusing the
    existing flat-ROI metric rather than reimplementing it, per discipline 210 — is the
    next build step. `UNVERIFIED`.
    *(Raised by M37; numbered 90 to clear the reserved question blocks.)*

    > **M38: half answered, half refused.** Both acceptance tests **pass on real frames**
    > (facts 320, 322) — flat-ROI 0.890x at gate 2.0 against argmax's 1.253x, detail retained
    > to −4.6% once the noise confound is removed. But the question's *premise* is wrong:
    > **there is no single threshold** (fact 324). At gate 2.0 `n_eff` spans 2.26–7.42 across
    > five stacks, and the threshold that lands on fact 212's target of 3 ranges 1.1–2.9. The
    > free parameter should be **the target `n_eff`, not the gate** — which is a better API
    > anyway, since it is the quantity with a measured calibration behind it and the one a
    > user can reason about. What remains open is how the solve is specified; see question 95.

95. **What is the right gate parameterisation, now that a fixed threshold is known not to
    transfer?** Fact 324 measured `n_eff/N` clustering at 0.068–0.079 on four of five stacks,
    which says the acceptance set is roughly a fixed *fraction* of the bracket — the signature
    of a through-focus peak of fixed optical width sampled at varying density. Three candidates,
    all cheap because pass two folds many accumulators for the price of one decode:
    **(a)** solve per stack for a target `n_eff` by bisection on the gate;
    **(b)** normalise the gate by the measured focus-step density, which makes it a statement
    about depth rather than about frame count;
    **(c)** normalise per pixel by the local through-focus curve width, which is the only one
    that adapts *within* an image and is the natural precursor to the posterior formulation.
    `109MSDCF`'s 0.131 outlier must be explained before any of them is trusted — it is the
    shallowest stack at 22 frames, so a boundary or under-sampling effect is the first
    hypothesis. **Also unresolved:** `at_bracket_boundary` reads 7.60% on `coffee-bean` and
    2.02% on `119MSDCF`, while fact 300 reports 7.38% for `119MSDCF`. The definitions differ
    (all-pixel regularised winner index against a parabola-fit peak on a reliable subset), so
    this is not yet a conflict — but the numbers are close enough, and attached to the wrong
    stacks, that one of the two should be re-derived before either is cited. `UNVERIFIED`.
    *(Raised by M38.)*

    > **Boundary discrepancy resolved by reading M35's harness, not by re-measuring.**
    > `experiments/m35-fit-generality/src/01-build.py:70` computes
    > `((am <= 1) | (am >= n - 2)).mean()` — **two frames deep at each end**, on a
    > **decimated** stack, from an **unregularised** argmax. `at_bracket_boundary` is **one**
    > frame deep, on the **full** stack, from the **regularised** winner. All three differences
    > push M35's number up, so 7.38% and 2.02% are the same reality read two ways.
    > **The confirmation is that both stacks scale by the same factor**: 7.38/2.02 = **3.65**
    > on `119MSDCF` against 2.08/0.61 = **3.41** on `112MSDCF`, agreeing to 7%. If either
    > number were simply wrong there would be no reason for the ratios to agree. `coffee-bean`
    > at 7.60% is genuinely the worst-covered stack in the corpus on the stricter definition —
    > the apparent match with 119MSDCF's 7.38% was coincidence. **`merge.rs`'s doc comment
    > invited exactly this false comparison and has been corrected.** The remaining part of
    > this question — the gate parameterisation and `109MSDCF`'s 0.131 outlier — stands.

    > **Candidate (a) is built and confirmed, and it exposes the next question.**
    > `--target-n-eff` solves the ladder by log-log interpolation: 2.0964 on `109MSDCF` for a
    > target of 3, which measures **2.989** when re-run — 0.37% (fact 330). `coffee-bean` needs
    > **1.1063** for the same target, so the parameterisation transfers where the gate does not.
    > **But fact 331 undercuts the control variable itself**: `coffee-bean` holds 62–77% of
    > pixels at `n_eff = 1` while its *mean* reaches 7.42, so a mean target buys a lot of
    > averaging for a minority of pixels and none for most of the image. **The open question is
    > therefore no longer "gate or n_eff" but which statistic of the `n_eff` distribution to
    > target** — the mean, a percentile, or the `n_eff = 1` share. Candidate (c), normalising
    > per pixel by the local through-focus width, is the one that dissolves the question rather
    > than answering it, and it is the same object the posterior formulation needs anyway.

    > **One weak lead, recorded so it is not re-derived.** If `n_eff` tracks the peak width in
    > frames, the natural normaliser is the bracket span *actually used* rather than the frame
    > count. M35's `01-build.json` has the argmax percentiles for two stacks: `119MSDCF` spans
    > p05–p95 = 4–30 (26 frames of 33), `112MSDCF` spans 11–66 (55 of 79). Normalising gate
    > 2.0's `n_eff` by that span gives **0.0868 and 0.1132** — a 1.30× spread, **worse** than
    > `n_eff/N`'s 0.0684 and 0.0788 (1.15×). So the obvious refinement makes the fit worse on
    > the only two stacks where the data already exists, which is evidence against it but is
    > **two points and does not include the `109MSDCF` outlier itself** — the stack that raised
    > the question is not in M35's build. Getting it needs argmax percentiles from the merge
    > command, roughly ten lines and five runs. Not started, so that the night ends on a
    > verified boundary rather than mid-measurement.

100. **Which argmax baseline is this pipeline's, given that fact 19's 1.253× does not
     reproduce on the shipped operator?** M39 measured **1.0678× unregularised** and
     **1.0739× regularised** on the same frames and ROI where M2 measured 1.253× and 1.075×.
     The regularised halves agree to 0.1%; the unregularised ones do not, and the gap cannot be
     the regulariser, because here regularisation moves the ratio the *wrong way* (up 0.6%,
     not down 14%). The likely cause is the focus operator — M2's was a ring difference, the
     shipped one is a normalised Tenengrad — which would mean **the two facts describe
     different selectors and only one of them is the product's**. Three things follow, in
     descending confidence: **(a)** the merge's win must be quoted same-operator, 0.890×
     against 1.0739×, a **17%** improvement (fact 343); **(b)** fact 19's "the defect the
     project exists to remove is measured on our own files" remains true but is measured on an
     operator the project does not ship, so its *magnitude* is not this pipeline's; **(c)** if
     the shipped Tenengrad is only 1.07× noisier under selection where the ring operator was
     1.25×, then **the operator swap already bought most of what fact 19 priced**, and the
     estimation merge's remaining margin over good selection is thinner than the corpus
     implies. **(c) is the one to test first, and it is cheap**: run both operators through the
     same harness on the same ROI. It moves the headline number the whole thesis is sold on,
     so nothing downstream should be re-argued until it is settled. `UNVERIFIED`.
     *(Raised by M39.)*
     **ANSWERED by M17.** The baseline is neither the ring nor plain Tenengrad: it is **`tenengrad-sq-w13`**, `box_mean₂₇(gx²+gy²)/σ²`. It takes the monotone-edge blind spot from **D = 1.0000 to 0.1860**, is quality-neutral on M13's occluding-edge cells (15/30, p = 1.00), noise-neutral (ΔN = −0.0015), and **cheaper than the shipped operator (0.96×)** because it drops a per-pixel `sqrt`. It is now the operator in `crates/strehl-core/src/focus.rs`, with the ring retained only as the comparison the tests assert against. **Caveat carried forward:** `w13` was chosen by M13 for the *mean* operator and candidate (c)'s per-shape sign is not uniform, which is consistent with a window mismatch — the ladder has not been re-run for `tenengrad-sq`. See owner question in `docs/research/OWNER-QUESTIONS.md`.
80. **Which definition of "predicted sigma" should M18 ship, given that the gated and ungated
    forms have opposite signs against sub-frame deficit?** The gated form carries acceptance-set
    information; the ungated form is what a user would expect from the name. They are different
    channels and should probably both exist, or the gated one should be renamed
81. **Should the acceptance-set size ship as a fourth real-valued channel?** It is the only
    quantity in this study with a consistent worst-5% lift across all three stacks (1.94x / 2.67x
    / 2.36x), and it is already computed as a by-product of C1
82. **Does C3's specificity collapse on 119MSDCF and 112MSDCF because those stacks are coarsely
    sampled and dim, or because +0.5560 is a coffee-bean artifact?** Separating the two needs a
    decimated coffee-bean arm matched to 119MSDCF's effective focus step
83. **Should M32's headline sigma count be restated at 84–512, and does fact 264's reconciliation
    with M20 survive at the lower figure?** It should — 84 sigma is still overwhelming — but fact
    264 quotes "10^2–10^3 sigma" and the honest range is now 10^2 at the low end and barely
    5x10^2 at the high end
84. **Is the dense 105-frame grid adequate?** The pre-registered bar was 3x; the like-for-like
25. **Does the sub-pixel locking artefact of fact 173 also bias the *unplanted* edge measurements
     the pipeline actually uses?** The `1/S` conservation defect is measured with no resampler in
     the path, so it is not the same artefact — but `coffee-bean`'s span-1 edges have a measured
     displacement of ~0.19 px, squarely in the locking zone, while its long edges do not. If locking
     contributes to fact 43's span dependence, the fix is a **phase dither or an upsampled
     correlation peak, not a calibration**. *Testable:* re-measure `coffee-bean` span-1 edges with
     the moving frame pre-shifted by a known integer-plus-half-pixel offset that is then removed
     analytically, and see whether `1/S_48(1)` moves off 3.26. **This is the live thread M23 leaves
     behind, and it is cheap.**
26. **Is R5 (blur-equalised edges) now the better candidate?** It attacks the same defect without
     planting anything, so it is immune to the mechanism that broke R4. Untested.
101. **What should a strictly detail-free region read under the corrected detail metric, and does
     the flat ROI qualify?** Fact 430 measures −11.5% where 1.0× is the naive expectation, but the
     ROI's single-frame corrected reading is 14.7270 rather than 0, so it is low-detail, not
     no-detail. Until this is settled the gate-0 denominator is not trustworthy and M38's retention
     band cannot be quoted. **Testable, and cheap:** synthesise a genuinely flat plane at the ROI's
     mean level with the calibrated noise model, run the same metric, and read the answer directly —
     the simulator (M25) exists to make exactly this kind of question decidable. Then re-derive the
     retention band against whichever denominator survives.
    measurement is 3.24x and the calibration-corrected one ~2.7–2.8x. If the ground truth is only
    ~3x better than the thing it judges, how much of the 2.876% "true deficit" is the ground
    truth's own error?

**Licensing, for the record.** MIT OR Apache-2.0 on our own code is standard and fine. The
practical obligation comes from linking LGPL-2.1 `rawler`: **anyone we distribute a binary to must
be able to relink it against a modified `rawler`.** Ship it dynamically linked, or publish object
files / a reproducible build. Statically linking it into a monolithic binary and shipping only that
binary is the trap. Separately, the "link but do not read" constraint on GPL sources (enfuse,
`align_image_stack`, Hugin, darktable, RawTherapee) is a constraint on *how the project works* and
is a written project rule in `AGENTS.md`.
102. **What is the realistic spread of `k` across focus measures anyone would
    actually contribute?** Fact 437 prices the damage using `k` = 5.94, taken
    from two operators already in this repository, but that is an illustration
    and not a distribution. If plausible contributed operators cluster near
    `k` = 1, the seam is a documentation problem; if they spread as widely as
    the two built-ins do, the load-time refusal in fact 438 is mandatory. Cheap
    to answer: measure the noise SD of the M11/M14/M17 bake-off arms, which are
    already implemented, and read the spread directly.

    **ANSWERED by fact 439** (M43 step 2b): `k` spans 0.644 to 6.680 across
    seven textbook operators, a 10.4x spread, with the two canonical
    shape-from-focus measures at the top. The spread is as wide as the
    built-ins', so the load-time refusal is mandatory. The same work found
    that fact 437's `k` = 5.94 was itself wrong — see fact 500.

