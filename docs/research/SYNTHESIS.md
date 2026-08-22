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
one adversarial review, and one measurement.
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
  1/sqrt(N) for averaging. Low-temperature softmax is indistinguishable from hardmax. The prior
  project measured exactly this in the wild: output sigma 2.3-4.6x the source cross-frame sigma,
  and 1.82x worse than a *single frame* in flat highlights (MEASURED, A §1).
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
| GPU kernel contribution | Distinct **named** functions + framework-generated entry points, selected from config | `naga_oil` `virtual`/`override` lost: it is *total replacement* resolved by DFS import order, which makes algorithm choice a property of import order, kills fusion, and makes A/B impossible (E follow-up) |
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

### 3.3 Pipeline

```
decode (CPU, rayon ACROSS files -- 2.5x over one-at-a-time, MEASURED M1)
  ->  calibrate (black/white/FPN, per CFA plane)
  ->  detect capture mode (breathing | rail) from EXIF + fitted residual signature
  ->  align  PHASE 1: fit ONE global low-order (quadratic) model of transform vs frame index
                      at full baseline, regularised toward the principal point
             PHASE 2: seed every frame from that model and refine per-frame IN PARALLEL
                      (HDR+ 32px tile search). No frame-to-previous chaining.
  ->  focus volume (multi-scale ring-difference, per CFA plane, vs calibrated noise floor)
  ->  merge (band-selective noise-gated accumulation; select above the floor,
             average below it; reference from a REGULARISED focus field, never argmax;
             anisotropic structure-tensor kernels; emits RGB)
  ->  confidence (peak-vs-floor, modality, out-of-range, index-map coherence, residuals,
                  coverage/occlusion)
  ->  colour + output (tiled float BigTIFF / DNG)
```

**Why alignment is two phases and not a chain (review finding #1).** Chaining frame-to-previous
is what every existing tool does *because it has no optical prior*. We have one: drift is smooth
and low-order in frame index (fact #1). Fitting the global model once and seeding from it makes
the N refinements **embarrassingly parallel** instead of a serial chain of length N, and avoids
compounding a 59-step random walk through a parameter whose error amplifies 1541x per pair
(fact #5). Fit **quadratic, not linear** — rail scale goes as `1/(u-d-f)`, which is hyperbolic,
and the second-order term is ~0.4 px over the reference baseline: detectable, and free to fit.

**Both capture modes use this same two-phase structure**, which is why rail support — when it
lands — does not force a second pipeline. A rail produces genuine *parallax*: point scale depends
on depth, so **no global 2D transform can be correct** — but the residual is locally near-constant,
which is exactly what phase 2's tile search absorbs. Rail would therefore promote tile refinement
from optional polish to **mandatory**, and make D's tile-search budget the floor rather than the
optimistic case. Occlusion at depth discontinuities is a real, separate problem (different frames
see *different surfaces*, which the Wiener gate would otherwise misread as "sharp vs blurred").

> **Rail is deferred from v1** — no rail hardware is available, so every rail claim above is
> *derived and untested*. See §9. `CaptureMode` and mode detection stay; occlusion handling does
> not. For breathing alone, phase 2 is polish rather than a requirement, and must justify itself by
> measurement.

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

- A plugin is a **`Stage`**: object-safe, `Send + Sync`, with darktable-style two-pass ROI
  negotiation, a `resources()` declaration, and `gpu() -> Option<&dyn GpuStage>` so GPU support
  is genuinely optional with CPU fallback.
- Large buffers cross the boundary as a **`TileView` descriptor**, never a bare slice, so
  CPU/GPU residency and ownership stay explicit and zero-copy.
- GPU plugins contribute **WGSL source**, spliced at build time into framework-generated entry
  points. One dispatch, zero indirect calls, **zero runtime plugin cost**, and two focus measures
  can fuse into a single dispatch — saving a whole pass over the stack.
- **Names for the algorithm, constants for the schedule.** This is Halide's algorithm/schedule
  split falling out of the mechanism rather than being imposed on it.
- Camera and lens models are plugins that **supply priors, never capability**. Every accessor
  returns `Option`; a geometric correction returns `None` to *disable* rather than approximate,
  because a wrong distortion coefficient is worse than none. `ScalePrior` has no constructor
  that omits `sigma`, and the aligner weights the prior by `1/sigma^2` so degradation is
  continuous rather than a branch.
- Unsatisfied optional dependencies leave a stage **inactive**, not errored (the Cordis
  `try_activate -> Inactive{unmet}` shape).

What we deliberately refuse to make pluggable: the pixel data model, the noise model interface,
the colour pipeline, and stage ordering semantics. Registries commute; the pixel chain does not.

**Over-engineering guard.** v1 is one binary, all stages in-tree, no dynamic loading, no WASM,
no DI container. What must not be foreclosed: the object-safe `Stage` signature, `TileView`
descriptors everywhere, `ctx.provide/require` from day one, `(id, semver, params_hash)` in cache
keys from day one, source-level kernel composition, and manifest-first stage declaration.

---

## 4. Measured facts that constrain the design

| # | Fact | Consequence | Source |
|---|---|---|---|
| 1 | Inter-frame scale drift **-1.012%** over 33 frames, linear, ~42 px corner displacement | Translation-only alignment is dead on arrival | F (MEASURED) |
| 2 | Reference stack is **in-camera focus bracketing, not a rail** (~85% conf.): `FocusPosition2` 56->57 matches the 0-1 ticks predicted from 2.03 mm travel; interval 0.6492 s +/- 0.0208 s | Frame-to-frame relation is **breathing (magnification)**, not parallax | F (MEASURED) |
| 3 | Homography residual identical to affine (1.45e-3) | No perspective signal. Use affine | F (MEASURED) |
| 4 | Per-block correlation tracks the **migrating in-focus band**, not geometry — response collapses 0.68 -> 0.13 while ECC composes correctly over 16 chained steps | A block-matching aligner would be **silently wrong** | F (MEASURED) |
| 5 | Scale-centre amplification **1541x** per frame pair, 98x at full baseline. Corrected estimate x = -176 +/- 127 px, y = -338 +/- 61 px | Solve **one** centre per stack at full baseline, regularised toward image centre. Never profile it — the max-shrink axis sits 4-10 deg from the subject's depth-gradient axis, so it is subject-dependent | F (MEASURED) |
| 6 | Laplacian winner-margin goes **negative** at sigma >= 0.01; ring-difference stays highest at every sigma | Do not use a Laplacian focus measure | B (MEASURED) |
| 7 | Argmax over N noise coefficients: 1.95x (N=10) -> 2.61x (N=60) | Selection is the defect. Gate on the noise floor | B (MEASURED) |
| 8 | PDAF: **0** candidate pixels over 5 frames; anomaly density at the noise floor | No PDAF mask, no PDAF depth cue | A + F (MEASURED, independently) |
| 9 | Sub-pixel *random* jitter **0.075 px** vs Wronski's >= 0.3 px gate | Classical multi-frame SR is off the table — **but see §6, breathing supplies structured diversity instead** | A (MEASURED) |
| 10 | H2D **56.9 GB/s**, D2D **1503 GB/s** measured locally; 66 MB frame transfers in 1.2 ms | PCIe is a non-issue. Do not build decode/compute overlap in v1 | D (MEASURED-LOCALLY) |
| 11 | Full budget 60x33 MP: **2.7-6.1 s**, decode-dominated | 15 s target has 2.5-5.5x margin | D (DERIVED) |
| 12 | SEL20TC at 2.8x: **MTF@Nyquist = 0.000 at every aperture** (wide open is already N_eff 21.3, past the 18.6 extinction point) | The tool should warn, and offer reduced-resolution output | F (DERIVED) |
| 13 | The reference 33-frame stack is **2.4x oversampled**; 14 frames sufficed | A capture advisor is a real feature | F (DERIVED) |
| 14 | ISO 400 is a **second base ISO** (read noise 4.20 -> 1.47 e-); DR is higher than ISO 320. Usable white level **15360**, not 16383 | Camera plugin must expose `dominated_isos()` and the true white level | F (MEASURED) |

### 4.1 Which of these are architecture, and which are artifacts of one stack

The empirical corpus is **n=1**: one stack, one subject, one body, one lens. The owner's
instruction is binding — *"don't overfit to anything specific to my setup."* Ruling:

| "Constant" | What it actually is | Verdict |
| --- | --- | --- |
| −1.012% scale drift | Per-**stack** by construction: depends on travel, magnification, focal length, and on a rail also on working distance | **Artifact. Fit at runtime, always.** The only defensible architectural claim is *"drift is smooth and low-order in frame index."* Fit quadratic. |
| affine ≈ homography (1.45e-3) | An artifact of the *breathing* case, where there is no perspective signal | **Known false for the rail case**, now in scope. Fit affine, measure residual, escalate to homography on threshold. ~20 lines; removes the n=1 dependency. |
| Scale centre (−176±127, −338±61 px) | Physically the principal point — within a few px of image centre. 176–338 px is **not physical**; x has 72% relative error | **Artifact: subject depth structure leaking into a geometric parameter.** F admits the max-shrink axis sits 4–10° from the subject's depth-gradient axis. Solve per stack, regularised toward the principal point with a **tight** prior. |
| `g = ISO/436.8`, ISO 400 second base, white level 15360 | Genuine **per-body-model sensor calibration** — the most legitimate constants here. White level and black level independently **confirmed by M1**. | **Keep — but in a camera-profile data file, never in pipeline code.** Read white level from file tags where present (firmware/compression dependent). `g` was validated by reproducing white level to 0.23%, which is a consistency check on one relation, *not* a photon-transfer measurement — extend experiment 1 to a real PTC. Dual-gain behaviour is per body *and* per firmware. |
| 0.075 px jitter ⇒ MFSR off the table | An artifact of the **capture mode** — in-camera bracketing on a tripod has no camera motion by design | **Do not bake anywhere.** A mechanical rail has 1–10 µm repeatability plus lateral runout; 5 µm at m=1 on a 5.12 µm pitch is ~**1 px**, far above Wronski's ≥0.3 px gate. **MFSR is back on the table for rail users.** |

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
failure mode, not an edge case. So the A/B harness is a **first-class component from commit one**,
not a later addition:

1. Every quality claim stored with a **named baseline artifact hash**.
2. **Pair every sharpness metric with a no-signal flat-ROI control**, and every noise metric with a
   genuinely *temporal* estimator.
3. Re-measure **non-default flag combinations** — the NLM inversion lived entirely inside an opt-in
   flag, and default-only CI is blind to it.
4. Ratchet **wall clock and peak RSS** together.
5. **Resolve every citation to a retrievable artifact before it reaches a design decision.**
6. Property-test the plugin graph on four properties, not just confluence: invariance,
   **sensitivity** (distinguishable configs must produce distinguishable output), no-residue
   across runs, and a calibrated fixture recovering the known -1.012% / [+412,-180] px. Confluence
   alone is passed by a function that returns a constant.

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
5. **Additive dark/offset FPN** is the one live threat to the multi-frame averaging pillar. It is
   absorbed indistinguishably into the noise model's `b` term. **M1 attempted to settle this for
   free from optically-masked sensor pixels and could not**: `rawler` reports `blackareas` as empty
   for Sony and crops the masked border away, leaving only synthetic zero padding. **It needs 20
   lens-cap frames at ISO 100 and ISO 400** — a two-minute capture.
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
   contributor loop — build-time WGSL splicing means a plugin author recompiles the whole binary,
   which is a real unacknowledged cost given that third-party contribution is the premise.

---

## 8. Sequencing — walking skeleton first, then experiments

The review's ruling, which the owner independently agreed with (*"probably measure before
building"*): experiments 1 and 2 are genuine go/no-go and cheap. Experiments 3 and 4 are **research
procrastination as standalone tasks**, because each needs decoded frames, a calibration, a focus
volume and an output path — i.e. you build most of the skeleton to run them anyway, in throwaway
form. So build the skeleton *as* the harness.

**Step 0 — the walking skeleton (one afternoon, zero plugin machinery).**
`decode 20 ARW -> calibrate -> NO alignment -> ring-difference focus volume -> plain argmax select
-> tiled TIFF out`, on a subset with negligible drift. This yields, in one pass:
(a) a real stacked image; (b) the **named baseline artifact** §5 mandates and which does not yet
exist; (c) the harness experiments 3 and 4 need; and (d) *the measured argmax-noise defect on our
own data*, which is the exact number the whole thesis argues against. Everything after this is
measured as a delta against a baseline that exists.

1. ~~**`rawler` decode throughput**~~ — **DONE. See `M1-decode-measured.md`.** 122/122 files
   decoded across two corpora, 0 failures. **60-frame stack: 1.78 s cold, 0.91 s warm** (rayon
   across files; 2.5x over one-at-a-time, because concurrent reads double effective disk
   bandwidth). Sensor constants independently confirmed. Decode is **6–12% of a 15 s budget, not
   the wall** — the dependency risk is cleared and the budget term is pinned.
2. **The sigma-vs-N curve.** >= 64 frames, static scene, **fixed focus**, straight ARW, NR off,
   plus matched darks. Plot per-pixel *temporal* sigma vs N, log-log, at ISO 100 and 6400. Slope
   -0.5 means independent; any asymptote **is** the fixed-pattern floor; re-run after master-bias
   subtraction to get the calibratable fraction. Go/no-go on the central pillar. **Extend it to a
   real photon-transfer curve** to measure `g` directly rather than inferring it — nearly free.
   *Blocked on 20 lens-cap dark frames at ISO 100 and ISO 400.*
3. **Focus-measure bake-off on real RAW**, against the noise model: ring-difference vs SML vs
   Tenengrad vs wavelet, scored by winner-margin versus sigma. Closes risk 2. *Run on the skeleton.*
   This — not the rail requirement — is what justifies build-time WGSL splicing.
4. **Alignment cost and accuracy at scale.** Now the largest unpinned budget term, by elimination.
   Measure the two-phase design (§3.3) against the chained one to confirm the review's ~0.5 s.
   *Run on the skeleton.*

Test data exists: `C:\dev\macro\test\109MSDCF\*.ARW` (36 MB lossless-compressed) plus `D:\personal\`
(2310 files, verified decodable).

---

## 9. Scope

**v1** — CLI. ARW in, tiled float TIFF + DNG out. Calibrate, two-phase align (global frame-index
model + parallel tile refinement) for **in-camera focus bracketing**, ring-difference focus volume,
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
darktable-style two-pass ROI negotiation (replaced by `fn halo(&self) -> u32`); the RON pipeline
graph (a graph language that can express exactly one topology; replaced by a `serde` struct with an
algorithm *name* per slot); Cordis-style `ctx.provide/require` DI (a `HashMap<TypeId>` replacing
eight explicit arguments, converting compile-time errors into runtime ones); `try_activate ->
Inactive{unmet}` (nothing can be unmet when everything is in-tree); and a universal per-stage CPU
fallback (keep `gpu() -> Option<..>` in the signature, but don't write every kernel twice).

**Kept, and correctly credited:** build-time WGSL splicing (~150 lines of `build.rs`, earned by the
four focus-measure candidates in experiment 3, *not* by the rail case); `TileView` (earned by
gather-at-consumption, not by plugins); the injected noise model; u16 CFA storage.

**The genuinely irreversible decisions are about data, not structure** — u16 CFA storage,
never-materialise/gather-at-consumption, the injected noise model, and `(id, semver, params_hash)`
cache keys. Those four are load-bearing and must be defended now. The rest are cheap refactors of
eight known call sites, and the rail requirement demonstrated the principle: the first genuine
second implementation the project met exerted pressure on **exactly one narrow interface** and on
none of the framework. Let the second variant of each thing tell you where the seam goes.

**Deliberately not v1** — rail capture and occlusion handling, CUDA, dynamic/WASM plugins, GUI,
decode/compute overlap, learned components, super-resolution, per-channel LCA exploitation.

---

## 10. Open questions

**Needs the owner:**
1. **20 lens-cap dark frames at ISO 100 and ISO 400.** Two-minute capture, no extra gear. Unblocks
   experiment 2, the go/no-go on the central pillar. `rawler` cannot supply masked pixels (M1).
   *Owner will provide later; proceeding without. Full capture spec in
   [`../captures-needed.md`](../captures-needed.md).* **Until it exists, every claim that depends on
   frame averaging is `ARGUED`, not `MEASURED`.**
2. ~~A rail-captured stack~~ — **no rail available. Rail support deferred from v1 (§9).**

**Needs measurement, not argument:**
3. Alignment cost for the two-phase design (experiment 4).
4. The radial dependence of sub-pixel jitter — resolves the fact #9 / novelty-bet-#1 contradiction
   (§4.1). Still live for breathing: bet #1 claims breathing itself supplies sub-pixel diversity.
5. `g` by direct photon transfer rather than by white-level consistency (§4.1). Needs (1).

**Licensing, for the record.** MIT OR Apache-2.0 on our own code is standard and fine. The
practical obligation comes from linking LGPL-2.1 `rawler`: **anyone we distribute a binary to must
be able to relink it against a modified `rawler`.** Ship it dynamically linked, or publish object
files / a reproducible build. Statically linking it into a monolithic binary and shipping only that
binary is the trap. Separately, the "link but do not read" constraint on GPL sources (enfuse,
`align_image_stack`, Hugin, darktable, RawTherapee) is a constraint on *how the project works* and
must be a written project rule in `AGENTS.md` before anyone opens those repositories.

**Licensing, for the record.** MIT OR Apache-2.0 on our own code is standard and fine. The
practical obligation comes from linking LGPL-2.1 `rawler`: **anyone we distribute a binary to must
be able to relink it against a modified `rawler`.** Ship it dynamically linked, or publish object
files / a reproducible build. Statically linking it into a monolithic binary and shipping only that
binary is the trap. Separately, the "link but do not read" constraint on GPL sources (enfuse,
`align_image_stack`, Hugin, darktable, RawTherapee) is a constraint on *how the project works* and
must be a written project rule in `AGENTS.md` before anyone opens those repositories.
