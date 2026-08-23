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
  ->  focus volume (multi-scale ring-difference, per CFA plane, vs calibrated noise floor)
  ->  merge (band-selective noise-gated accumulation; select above the floor,
             average below it; reference from a REGULARISED focus field, never argmax;
             anisotropic structure-tensor kernels; emits RGB)
  ->  confidence (peak-vs-floor, modality, out-of-range, index-map coherence, residuals,
                  coverage/occlusion)
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
| 25 | Argmax's noise excess is **spatially correlated over 3-7 px, not white** — and 3-7 px is exactly `focus.rs`'s own `INNER_RADIUS: 1` / `OUTER_RADIUS: 3` support | **The focus measure and the merge are coupled.** The 17x17 regulariser behind facts 20 and 23 is tuned to *one measure's support*. A contributor pairing a wider measure with the default merge gets a silently wrong stack. Put the support on the interface (§3.4.1 B3). Also why high-pass views understate argmax damage while raw spatial sd overstates the ratio — ~1.48x is the honest figure between them | M2-verification (MEASURED) |
| 26 | **Every existing test stack was shot with a 2x teleconverter**, disclosed only after M1-M4 were complete. `LensModel = "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"`, `LensSpec = "FE 200mm F5.6 Macro OSS"`, `FocalLength = 200 mm`, `MaxApertureValue = 5.6`. The body composes the TC into reported focal length and aperture; **the maker-note lens ID does not** — it still reads as the bare lens | Two consequences. **(a)** Anything reading `FocalLength`/`FNumber` from EXIF is already TC-correct, so there is no hidden 2x error in the advisor. **(b)** **Keying a lens profile on the lens ID is a bug**: it would apply bare-lens constants to a composed path with a different `p`, twice the focal length and two more stops. The profile key must be the *composed optical path*, and every profiled constant must be measured for the combination actually in use | MEASURED-LOCALLY (exiftool, all three stacks, every frame) |
| 27 | **The bellows factor of the composed path is `B = (1 + m/p) ∈ [2.41, 3.06]`**, point estimate 2.6-2.9, measured from the diffraction cutoff in the raw CFA. At f/11 the green-quincunx spectrum has a genuine knee at **f_sig = 0.2762 cyc/px**, above which the floor matches the photon-transfer noise model to **0.950x** — so it is a real optical cutoff, not a fitted plateau. **`B = 5` (p = 0.5) is REFUTED 5/5 by a model-free test** at two apertures: there is optical signal at 0.3508 cyc/px, where p=0.5 permits none. **`B = 1` is refuted by ~3x** | **The corpus's "dominant uncertainty in the whole advisor" (±38%) is retired to −20%/+2%, from data the owner already had, with no bench work.** With m ≈ 2.0, **p ≈ 1.0-1.4** — the working assumption of p=1 was right. It does **not** vanish: M5 measures the product `(1 + m/p)` and cannot separate `p` from `m`, so `B` is known at *one* magnification only. A bench measurement of `p` alone would give `B` at any magnification | M5 (MEASURED → DERIVED; independently reproduced) |
| 28 | **EXIF `FNumber` is the *marked* aperture and is NOT bellows-corrected.** The body composes the teleconverter into `FocalLength` and `FNumber` (fact 26) but applies no correction for working at 2:1. **Marked f/11 is optically f/33** | **The most directly actionable finding in the corpus.** Every advisor formula that reads `FNumber` and treats it as `N_eff` **under-predicts diffraction blur by ~3x** and will recommend f/11 as "safe". Apply `N_eff = FNumber_exif * B`. Consequences at B=3: f/8 discards **40%** of the sensor's 2-D Nyquist area (46% of contrast at 4-px detail), f/11 discards **68%** (90%) — a 33 MP sensor used as ~10.5 MP. Critical sampling is at **N_marked = f/6.21** | M5 §7 (DERIVED, factor-of-3 margin) |
| 29 | **The project's noise model is independently confirmed to ±10% by a method sharing none of its assumptions.** The spectral floor above the cutoff is a structure-free sigma estimate: floor/model = **0.950-1.093x** across 15 f/11 cases spanning a **4.8x signal range** (422-2027 DN), so it tests the *slope* of the photon-transfer relation, not one point. Immerkaer on the same ROIs agrees to 0.896-1.020x | Three structurally independent routes now concur. **Where they disagree the disagreement is diagnostic**: at f/8 the ratio is 4.58-20.19x because the "floor" still contains subject signal, which is exactly how M5 detected that f/8 has no reachable floor. Uses no darks, no flats, no Immerkaer kernel, no fitted gain | M5 §8 (MEASURED, n=15) |
| 30 | **The fusion prize is 0.14% of the pipeline.** Ring-difference focus + merge, fused into one `wgpu` kernel, runs the 22-frame stack in **4.117 ms** — bandwidth-bound at **84%** of the measured DRAM read ceiling, predicted to **1.05x by a zero-free-parameter model**. Unfused (focus written to memory, merge reads it back — i.e. *a plugin that merely emits a focus field*) costs 5.566 ms. **Prize = 1.449 ms = 0.14% cold / 0.20% warm.** Keeping the entire focus volume resident, the most permissive plugin model there is, costs only 1.683 ms more than fusing. GPU vs best parallel CPU: **~165x** | **This kills the case for constraining contributors to spliceable WGSL** (§3.4.1 B2), which was the stated justification for the whole spliced-kernel contribution format. Splicing would make a contributor inherit our tile size, halo, shared-memory layout, register budget and single-pass restriction, make their measure untestable in isolation, and harden fact 25's coupling into the ABI — to buy back 0.14%. **The rule becomes "run on the GPU, emit an `f32` focus field."** That keeps the 165x, which is the part that matters. Fusion survives as an internal optimisation: fused and unfused are **bit-identical** (self-test group 6), so it is an implementation detail, not a different answer | M7 (MEASURED; independently reproduced to 0.1%) |

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

---

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
2. **Every focus-measure noise analysis in the literature is synthetic.** Nothing measures focus
   measures on real 33 MP RAW. Build that benchmark *before* choosing the operator.
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
   must be ordered relative to the noise model); dust and hot pixels, which are fixed in *sensor*
   coordinates and therefore smear into trails once the subject is stabilised — made harder to
   inspect by "never materialise aligned frames"; a single bad frame (motion, wind, clipping)
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
3. **Focus-measure bake-off on real RAW**, against the noise model: ring-difference vs SML vs
   Tenengrad vs wavelet, scored by winner-margin versus sigma. Closes risk 2. *Run on the skeleton.*
   ~~This — not the rail requirement — is what justifies build-time WGSL splicing.~~ **That last
   sentence is dead (fact 30).** M7 measured the fusion prize at 0.14%, so nothing justifies
   splicing and this experiment is no longer load-bearing for the contribution format. **The
   bake-off is still worth running** — it closes risk 2 and it feeds question 9's support-coupling
   sweep — but it now decides *which measure ships as the default*, not *how contributors are
   allowed to write one*.
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
9. **Is the focus-measure/merge coupling (fact 25) severe enough to belong on the interface?**
   Re-run the skeleton's winner map with measures of differing support (3x3/7x7 ring, 5x5/13x13
   ring, 3x3 Tenengrad) and sweep the regulariser width against the flat-ROI ratio for each. **If
   the noise-optimal width tracks the measure's outer radius, §3.4.1 B3 is confirmed and
   `support_px()` is mandatory.** The skeleton already emits `--index-map` and `--flat-roi`, so
   this is nearly free. **Now the most valuable open item in this section**, since M6 and M7 closed
   the other two interface questions and B3 is the one still standing on an unmeasured claim.
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

**Licensing, for the record.** MIT OR Apache-2.0 on our own code is standard and fine. The
practical obligation comes from linking LGPL-2.1 `rawler`: **anyone we distribute a binary to must
be able to relink it against a modified `rawler`.** Ship it dynamically linked, or publish object
files / a reproducible build. Statically linking it into a monolithic binary and shipping only that
binary is the trap. Separately, the "link but do not read" constraint on GPL sources (enfuse,
`align_image_stack`, Hugin, darktable, RawTherapee) is a constraint on *how the project works* and
is a written project rule in `AGENTS.md`.
