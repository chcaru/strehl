# Adversarial review of the architecture

Reviewer: independent `claude-opus-5` agent, briefed to attack the proposal.
Subject: `SYNTHESIS.md` (first draft) and the six research reports.

Turn 0 is the initial critique. Turn 1 is the revision after owner input on capture
method (rail support is a first-class requirement) and scope (do not overfit to one rig).

Findings 1-3 of turn 0 and finding 2 of turn 1 changed the design. `SYNTHESIS.md` has
been revised accordingly; this file is the unedited original so the reasoning survives.

---


[Turn 0]
I've read the synthesis, both budget sections, and the optics report. Here's my attack.

---

# Critique: `strehl` architecture proposal

## BLOCKING — these change the design

### 1. The D-vs-C alignment conflict is not a disagreement. They costed different algorithms, and your pipeline needs both.

I resolved it. Neither is wrong; the synthesis is.

- **D** (`D-rust-and-hardware.md:756`) budgets "Bayer align (pyramid build + coarse-to-fine search)" at ~15 GB / 1500 GB/s = 0.01 s ideal → 0.10 s. That is a **roofline for HDR+-style tile search**: fixed pass count, integer displacement, non-iterative, no readback.
- **C** (`C-landscape.md:808`) budgets "Multi-scale LK/ECC + warp" at 5.0 s. ECC is **iterative to convergence** with a CPU-side 6-DoF solve per iteration, per level.

Your §3.3 pipeline specifies **both**: *"coarse-to-fine ECC on Bayer-quad luma, chained frame-to-previous, **+** HDR+ 32px tile residual refinement."* D budgeted only the second half. The ECC stage — the one C says dominates — **appears in no budget line anywhere in the document.** The "2.7–6.1 s total, 2.5–5.5x margin" (fact #11) is therefore not a total. Fix the table before you defend the margin.

Sizing the missing line: ECC at 2048px, ~3 levels × ~50 iterations = ~150 GPU→CPU round-trips per pair at ~30–50 µs each ≈ 5–8 ms/pair. Serial × 59 = **0.3–0.5 s**. Latency-bound, not bandwidth-bound, so D's roofline method cannot see it. Real answer: ~0.5 s, not 0.1 and not 5.0.

**But the more important finding: your own measured facts destroy the premise of the serial chain.** Fact #1 says drift is **linear** at −1.012% over 33 frames; fact #2 says intervals are uniform to ±0.02 s. If scale is a *predictable linear function of frame index*, you do not need frame k−1 to seed frame k — you seed from the global model. Then all N refinements are **independent and fully parallel**, and C's Amdahl wall vanishes. Chaining exists in Zerene/focus-stack because they have no optical prior. You have one. That is the actual differentiator here, and the document buries it as a "prior" instead of recognising it as the thing that deletes risk #1.

Also: chaining 59 estimates is a random walk of residual error, and fact #5 says scale-centre error amplifies **1541x per frame pair**. F validated composition over **16** steps, not 59. Chaining is not just slow, it is *less accurate* than global seeding at N=60. Kill it.

### 2. The Wiener gate's reference is argmax-selected — so it reimports the exact defect the thesis exists to remove.

This is the crux and it is unaddressed. HDR+'s guarantee ("shrinkage never exceeds 1.0", fact #7 mitigation) is *relative to the reference frame*. HDR+'s reference is a **fixed single frame**, so output noise ≤ reference noise, always. §1 generalises this to *"a per-band focus-selected"* reference — i.e. **argmax over frames per band**. Fact #7 says argmax over N returns 1.95–2.61x single-frame noise.

So: in every band where the gate *rejects* (high-frequency, textured — see below, that's most detail), the output is the argmax-selected reference ⇒ **2–2.6x noise, exactly the prior project's measured defect.** The Wiener bound is preserved and irrelevant, because the thing it is bounded against is now the noisy quantity.

Fix: never let the reference be a raw per-band argmax. Select it from a **regularised focus field** — spatially smoothed, parabola-fit across frame index, or average the top-k frames whose focus measure is within the noise floor of the peak. You already compute peak-vs-floor for the confidence map (§1.3); apply it to reference selection. This is a small change now and a rewrite of the merge stage later.

### 3. The "3–5.5x at N=33" headline is wrong by roughly 3x, and the win is in a different place than claimed.

Computed from your own numbers. `F-camera-lens-optics.md:417` sets `step = DoF/k`, `k ≈ 1.3–1.5`. Frames whose DoF covers a given depth = `DoF/step = k`. So at 33% overlap, **1.3–1.5 frames contribute in-focus signal at a pixel** — not 33. sqrt gain = **1.14–1.22x**. Even on the reference stack, which F calls 2.4x oversampled (fact #13), k_eff ≈ 3.4 ⇒ **1.8x**. To reach 5.5x you need 30 overlapping frames ⇒ ~20x oversampling ⇒ 660 frames.

Answering your (a)/(b) directly: **it's (a).** The gate is per-frequency. Defocus is a low-pass, so `|D|` is small at low frequency (averages, correctly) and large wherever there is resolved texture (rejects → selection). On fine detail you get selection back and no sqrt(N).

**But this doesn't kill the thesis — it relocates it.** In *flat, low-detail* regions all N frames are identical up to noise, `|D|² ≪ cσ²`, and you average all 33 for a genuine **5.7x**. And flat regions are precisely where A measured the prior tool at **1.82x worse than a single frame in flat highlights**. So the honest claim is:

> ~sqrt(N) in flat/smooth regions where selection is currently *worse than not stacking at all*; ~1.2–1.8x on resolved detail.

That is still a strong, defensible, verifiably-absent-from-the-field result. State it that way. If you ship "3–5.5x in the depth-overlap region" and measure 1.2x, your own §5 discipline convicts you of a metric-validity failure identical to the retracted 1.10x claim.

---

## Changes the plan

### 4. Over-engineering: cut four things, and the "don't foreclose" list is backwards.

Justified, keep: build-time WGSL splicing (~150 lines of `build.rs`, buys kernel fusion and A/B — real), `TileView` (earned by gather-at-consumption, *not* by plugins), the injected noise model, u16 CFA storage.

**Cut for v1:**
- **darktable two-pass ROI negotiation.** darktable needs it because it is an interactive zoomable viewer computing arbitrary regions at varying scale. A batch CLI processing whole frames has exactly one ROI. Every stage here is point-wise or fixed-halo. Replace the entire protocol with `fn halo(&self) -> u32`.
- **RON pipeline graph.** §3.4 says stage ordering is explicitly *not* pluggable. A graph language that can express exactly one topology is a config file cosplaying as a compiler. Use a `serde` struct with an algorithm *name* per slot.
- **`ctx.provide/require` (Cordis DI).** Eight in-tree stages and one injected model. This is a `HashMap<TypeId>` replacing eight explicit function arguments, and it converts compile-time errors into runtime ones.
- **`try_activate → Inactive{unmet}`.** Nothing can be unmet when everything is in-tree.
- **Universal CPU fallback per stage.** Keep `gpu() -> Option<..>` in the signature; don't *write* two implementations of every kernel for a v1 targeting a 5090.

**What the "don't foreclose" list gets wrong:** it lists six items and five are cheap refactors of 8 known call sites (Stage signature, ROI negotiation, provide/require, manifest-first, source-level composition). The genuinely irreversible decisions are about **data, not structure**: u16 CFA storage, never-materialise/gather-at-consumption, the injected noise model, and `(id, semver, params_hash)` cache keys. Those four are load-bearing; defend them. The rest is a framework you're pre-paying for.

### 5. Single-stack over-generalisation, and the rail hole is bigger than stated.

−1.012%, affine≈homography (1.45e-3), and the scale-centre (−176±127, −338±61 px — the x error is 72% of the estimate) are **n=1: one stack, one subject, one lens, one FL**. "Homography adds literally nothing" is only true where there is no perspective signal; a rail *creates* perspective signal. Treat these as **defaults with a fitted fallback**, not architectural constants: fit affine, measure residual, escalate to homography if residual exceeds a threshold. That is ~20 lines and removes the n=1 dependency entirely.

The rail question matters more than the doc thinks — and note `F:446` shows the measured 1.012% is **equally consistent with a 2.0 mm rail move**, so the 85% confidence rests on `FocusPosition2` ticks, not on the drift itself. What actually breaks on a rail is not scale: it is **parallax**. Rail translation changes occlusion for a 3D subject; breathing does not. Affine cannot model parallax, and at occlusion boundaries different frames see *different surfaces* — which your Wiener gate will read as a large `|D|` and handle as "sharp vs blurred", incorrectly. Serious macro shooters use rails constantly. Detect the case (residual + EXIF) and warn; do not silently apply a breathing model to rail data.

### 6. RAW-native: steelman you didn't write.

Everyone demosaics first for three reasons worth confronting: (i) **alignment is easier on luma** — CFA quads halve resolution and alias, and your sub-pixel accuracy target is 0.075 px; (ii) **the CFA is a sampling lattice, so any warp resamples on a lattice whose phase varies per channel** — this is why `D:657` warns u16 survives exactly *one* resample; (iii) **every downstream tool expects RGB**, so you inherit the entire colour pipeline as your problem. Wronski's >3 dB is measured for *burst denoising with sub-pixel jitter*, which fact #9 says you **do not have** (0.075 px vs the ≥0.3 px gate). The CFA gain may not transfer to your regime. It's still the right call — but it's a bet, not a settled VERIFIED win, and it should be labelled as such.

### 7. Missing entirely — the ones that will actually bite

- **Colour management.** The merge "emits RGB" from CFA with no demosaic stage — so *where* is the CFA→RGB transform, and what defines it? Worse, white balance scales noise **per channel**, so WB must be ordered relative to the noise model. That is a hard ordering constraint on your load-bearing abstraction, not a TODO. Output has no colorimetry story at all (matrix, primaries, transfer, ICC/DNG tags).
- **Dust and hot pixels.** C's artifact #8: defects are fixed in *sensor* coordinates while the subject is stabilised, so alignment smears them into trails. "Never materialise aligned frames" (§3.1) means there is no aligned frame to inspect — this design makes the standard fix harder. Needs a pre-align defect map.
- **Wind/motion, and one bad frame.** A single motion-blurred or clipped frame poisons both the argmax reference and the average. No outlier rejection anywhere.
- **Retouch.** You emit a confidence map and provide no way to act on it. A confidence map you cannot act on is a bug report, not a feature.
- **Contributor loop.** Build-time WGSL splicing means a plugin author edits one kernel and **recompiles the whole binary**. That is a direct, unacknowledged cost of the chosen mechanism — and this project's premise is third-party contribution. Needs a dev-mode runtime shader path.
- **Image-quality testing.** §5 mandates "a named baseline artifact hash" and no baseline exists.

### 8. Sequencing: half research procrastination.

Keep experiments **1** (sigma-vs-N; genuine go/no-go on the central pillar) and **2** (rawler decode; ~20 lines, collapses the dominant budget term). Both are hours.

Defer **3** and **4**. The focus-measure bake-off needs a harness, and the alignment measurement needs decoded frames and a warp — you will build most of the skeleton to run them anyway, in throwaway form.

**Smallest useful thing:** decode 20 ARWs → calibrate → **no alignment** → ring-difference focus volume → plain argmax select → tiled TIFF out. Zero plugin machinery. One afternoon on a subset with negligible drift. That gives you (a) a real stacked image, (b) the named baseline artifact §5 requires, (c) the harness experiments 3 and 4 need, and (d) the *measured* argmax-noise defect on your own data, which is the number the whole thesis is arguing against. Then add alignment and the gated merge and measure the delta against a baseline that exists.

---

**Right, briefly:** never-materialise/gather-at-consumption, u16 CFA storage, the 8 GB RSS CI ratchet, cutting CUDA on a 1.1x-on-20% argument, the injected noise model, and the §5 discipline section (particularly "pair every sharpness metric with a flat-ROI control") are all well-reasoned and should proceed unchanged.

[Turn 1]
[Message]
Owner input just arrived that bears directly on two of your review questions. Fold it into your critique — it changes the ground under Q1 and Q4.

**1. On capture method (your Q4, my "85% confidence" concern).** The owner shoots **in-camera focus bracketing exclusively**. So the breathing model is correct for the reference corpus — that part is now settled, not inferred. BUT he added, unprompted:

> "i only shoot in-camera focus bracketing. but a SOTA focus stacker should support focus rail as well. a great example of a composable plugin system at work, right?"

So the rail case is **in scope as a first-class requirement**, not a hypothetical. This means:
- Your Q4 sub-question "what breaks if a user shoots on a rail" is no longer a risk to assess — it is a requirement to design for. Both geometry models must exist.
- It supplies a genuine, non-speculative second implementation of the alignment abstraction. Re-examine your Q1 (over-engineering) in this light: does a real second case justify the `Stage` abstraction, or does it only justify a much narrower one — e.g. a `GeometryModel` enum or trait with two variants — while leaving the rest of the plugin machinery (RON graph, ROI negotiation, TileView, build-time WGSL splicing) still unjustified? Be precise about which abstractions the rail requirement actually pays for and which it does not. I suspect it justifies far less than it appears to, and I want you to either confirm or refute that.

**2. On scope and over-fitting (sharpens your Q4 generally).** On being asked what to build first, he said:

> "probably measure before building -- but don't overfit to anything specific to my setup. this should be a generally SOTA focus stacker."

This is a direct instruction against the failure mode you were already probing: the entire empirical corpus is **one stack, one subject, one body, one lens**. Please treat "which of the synthesis's architectural constants are actually artifacts of a single test stack" as a **first-tier finding**, not a fourth-tier one. Specifically rule on:
- the −1.012% scale drift and the affine-vs-homography verdict
- the scale-centre estimate
- the noise model coefficients (g = ISO/436.8, the ISO 400 second-base-ISO claim, usable white level 15360)
- the "sub-pixel jitter 0.075 px, therefore classical MFSR is off the table" conclusion — this one worries me most, because on a **rail** the jitter characteristics could be completely different, which would put multi-frame super-resolution back on the table for exactly the users we just added

For each: is it a physical constant, a per-body/per-lens calibration, a per-stack estimate, or an artifact? Say which must be *measured at runtime* rather than baked in. A constant baked in from one stack is a latent bug for every other user.

**3. On licensing.** Owner picked MIT OR Apache-2.0 but said "i'm honestly not sure the implications". Not a review question — just don't assume he has ratified any read/link constraint. If you think the LGPL `rawler` dependency carries a practical obligation he should understand before committing, note it in one line.

Everything else in my original brief stands — Q2 (the 50× alignment budget conflict between reports C and D) is still the most important item, and the rail requirement may make it worse, since rail frames need different and possibly more expensive alignment than breathing frames. Still under 1200 words; spend them on what changes the design.

[Response]
I've re-read the relevant sections against the new input. Both items change my ruling materially, and one of them changes it in the owner's favour.

---

# Critique — revision after owner input

## 1. The rail requirement changes the alignment design, and it settles Q2 more cleanly than before

**The rail case is not a second global 2D transform. It is genuine parallax, and no affine/homography can represent it.**

Breathing changes the lens's internal magnification with the **camera fixed** — every depth scales about one centre, and occlusion never changes. A rail **moves the camera**, so a point at distance `u` scales by `(u−f)/(u−δ−f)`, which is a function of `u`. Different depths scale differently, and surfaces occlude and disclose at depth discontinuities.

Magnitudes, using F's own geometry (`f = 200 mm`, `u−f = 200 mm`, total travel 2.03 mm ⇒ the measured 1.012%, `F:446`): the depth-differential residual is `±Δ/(u−f)` of the total 42 px corner displacement — **~0.4 px for a 4 mm subject, ~2 px at 20 mm depth, and growing linearly with subject depth.** Un-modellable globally, and concentrated at the corners.

**This is good news for the design, and it kills the chained aligner outright.** The residual is depth-dependent but *locally* near-constant — which is exactly what a 32 px HDR+ tile refinement handles. So:

- **Global parametric seed (parallel, from the frame-index model) + per-tile local refinement (parallel) covers both capture modes.** Neither needs frame-to-previous chaining. My earlier finding that fact #1's linearity deletes the serial chain now holds for *both* cases, for a stronger reason: on a rail there is no correct global transform to chain in the first place.
- **The budget conflict is therefore an architecture choice, not a factual dispute.** C's 5.0 s prices the chained iterative ECC that §3.3 specifies. D's 0.10 s prices the tile search. Build the two-phase design and you pay D's number plus a cheap seed (~0.1–0.3 s). Build §3.3 as written and you pay C's. **Delete the chain from §3.3.**
- Rail promotes tile refinement from optional polish to **mandatory** — so D's 0.10 s is now the floor, not the optimistic case. It still fits.
- Free bonus: on a rail the per-tile displacement field *is* a depth cue (axial structure-from-motion). Worth one line in §6 as a better-grounded bet than the three currently listed.

**One thing rail genuinely costs you that nothing in the document covers:** occlusion. At depth discontinuities, different frames see *different surfaces*. Your Wiener gate reads that as a large `|D|` and handles it as "sharp vs blurred" — incorrectly. Combined with my earlier finding that the gate's reference is an argmax, occlusion boundaries are where this fails most visibly, and halos live at exactly those boundaries. This needs explicit coverage/visibility accounting, not just a residual.

## 2. Which constants are artifacts — first-tier ruling

The instruction "don't overfit to my setup" is the correct read. Here is the ruling.

| Constant | What it actually is | Verdict |
|---|---|---|
| **−1.012% scale drift** | Per-**stack**, by construction — depends on travel, magnification, focal length, and on a rail on `δ` and working distance | **Artifact. Must be fitted at runtime, always.** The defensible architectural claim is only "scale drift is smooth and low-order in frame index." Fit **quadratic, not linear**: rail scale is `∝ 1/(u−δ−f)`, hyperbolic, and over 2 mm/200 mm the second-order term is ~1% of 42 px ≈ 0.4 px — detectable, and free to fit. |
| **affine ≈ homography (1.45e-3)** | An artifact of the *breathing* case, where there is genuinely no perspective signal | **Now known false for the newly-in-scope rail case.** A homography partially absorbs depth-dependent radial flow. Do not bake affine. Fit, measure residual, escalate. Runtime decision, ~20 lines. |
| **Scale-centre (−176±127, −338±61 px)** | Physically this is the principal point — a per-body/lens property that sits within a few px of image centre. An offset of 176–338 px is not physical | **Artifact: subject depth structure leaking into a geometric parameter.** F admits it — *"the max-shrink axis sits 4–10 deg from the subject's depth-gradient axis, so it is subject-dependent."* x has 72% relative error. Solve per stack, but regularise toward the principal point with a **tight** prior (tens of px), not one that treats ±127 px as evidence. |
| **`g = ISO/436.8`, ISO 400 second base, white level 15360** | Genuine **per-body-model sensor calibration** — the most legitimate constants in the document | **Keep, but they must live in the camera-profile data file, never in pipeline code — and the white level must be read from file tags where present** (it is compression/firmware-dependent). Two caveats: (a) `g` was validated by reproducing the white level to 0.23%, which is a *consistency check on one relation*, not a photon-transfer measurement — extend experiment 1 to a real PTC and measure `g` directly, it's nearly free; (b) **dual-gain behaviour is per body and per firmware.** |
| **0.075 px jitter ⇒ MFSR off the table** | An artifact of the **capture mode** — in-camera bracketing on a tripod has no camera motion by design | **Your worry is correct. Do not bake this anywhere.** See below. |

**The single biggest generalisation risk is the noise model, not the geometry.** Every gating decision in the merge depends on the noise floor. With no profile for a body, a user gets a *wrong* floor and the Wiener gate silently mis-gates — no error, just bad output. **A runtime estimator must exist on the v1 path**, not v2: per-stack temporal σ from the frames themselves, plus a flat-region photon-transfer fit. Ship it as the fallback and use it to *validate* the A7C II profile — if the estimator disagrees with the baked profile on the reference body, one of them is wrong and you want to know on day one.

**On MFSR and rail — you are right and it is sharper than you framed it.** A mechanical rail has 1–10 µm positioning repeatability plus lateral runout; at m=1 and 5.12 µm pitch, 5 µm of lateral error ≈ **1 px**, versus Wronski's ≥0.3 px gate. Add stepper backlash and controller step error. So MFSR is genuinely back on the table for rail users.

But there is a live contradiction in the document you should force it to resolve: **fact #9 (0.075 px, "MFSR off the table") and novelty bet #1 ("breathing supplies structured, radially-growing sub-pixel diversity") cannot both be true as stated.** If breathing offsets grow with radius, 0.075 px is a centre-of-frame or whole-frame-average number and the corner value is much larger. Ask for the radial dependence before either claim reaches a design decision — this is precisely the §5 metric-validity failure mode.

The fix is cheap and correct for both cases: **measure the sub-pixel jitter distribution per stack from the alignment residuals**, which the pipeline already computes and §1.3 already retains, and gate SR on the measurement at runtime. Zero pixel cost, no baked constant, and it generalises to capture modes you haven't seen.

## 3. What the rail requirement actually justifies — refuting the "great example of a plugin system" reading

**Your suspicion is correct. It justifies far less than it appears — but for an interesting reason.**

The rail/breathing difference lives entirely in **what prior seeds the alignment** and **whether the residual is depth-dependent**. That is one narrow interface:

```rust
enum Geometry { Breathing { .. }, Rail { .. } }   // or a 2-method trait
// seed(frame_idx) -> (Transform, sigma);  residual_kind() -> Global2D | DepthDependent
```

Both variants are in-tree, both are known, both are the *same stage* with different parameters. Concretely, it pays for **nothing else**:

- **`Stage` trait object + ROI negotiation** — no pressure at all. Rail is a strategy *inside* one stage, not a second stage. Both have identical ROI behaviour.
- **RON pipeline graph** — no. Identical topology. This is `geometry = "rail"` in a config struct field.
- **`TileView`** — no. Already earned by gather-at-consumption, independent of rail.
- **`ctx.provide/require`, `try_activate → Inactive{unmet}`** — no.
- **Build-time WGSL splicing** — no. The seed difference is a uniform, not a kernel. (This mechanism *is* justified — by the four real focus-measure candidates in experiment 3. Keep it, but credit it correctly.)
- **Camera/lens plugin** — marginally yes: rail needs `dm/dz` from focal length and working distance; breathing needs the breathing curve. Both are `Option`-returning accessors the doc already specifies.

**And the meta-point is the valuable one.** The first genuine second-implementation the project has encountered exerted pressure on exactly *one* narrow interface, and on none of the framework. That is evidence **for** letting the second variant of each thing tell you where the seam goes, and **against** pre-building six seams from imagination. My cut list stands unchanged: ROI negotiation, RON graph, `ctx.provide/require`, `try_activate`, universal per-stage CPU fallback.

Two things rail *does* add to v1 scope that are real: **detecting which mode a stack is** (EXIF + fitted-residual signature — it must not be a user-only flag, because users will get it wrong), and **occlusion/coverage handling** at depth discontinuities.

## 4. Licensing — one line, as requested

MIT OR Apache-2.0 on your own code is fine and standard. The practical obligation: **linking LGPL-2.1 `rawler` means anyone you distribute a binary to must be able to relink it against a modified `rawler`** — so either ship it dynamically linked or publish the object files / a reproducible build, because statically linking it into a monolithic binary and shipping only that binary is the trap. Separately, the "link but do not read" constraint on GPL sources (enfuse, `align_image_stack`, Hugin — `C-landscape.md:500`) is a real constraint on *how the team works*, and since you haven't ratified it, it should be an explicit written project rule before anyone opens those repos.
