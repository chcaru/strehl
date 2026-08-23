# AGENTS.md — strehl

Noise-aware RAW focus stacker. Rust. CFA-native. Pluggable focus measures, merge
strategies and alignment models. Camera and lens knowledge is a **profile** — a
data file, not a plugin: measurement kept reclassifying "camera constants" as
per-stack quantities that are cheaper and more accurate to fit at runtime. See
`SYNTHESIS.md` §3.4.2 for exactly what survives.

Read [`docs/research/SYNTHESIS.md`](docs/research/SYNTHESIS.md) before changing
anything architectural. It is the decision record and it lists what lost.

## Licence discipline — read this before opening any other repository

This project is **MIT OR Apache-2.0**. Reading GPL source would contaminate it.

**Never open, read, browse, or copy from:**

| Project | Licence |
| --- | --- |
| enfuse / enblend | GPL-2.0 |
| `align_image_stack`, Hugin | GPL-2.0 |
| EPFL Extended Depth of Field | GPL-3.0 |
| ChimpStackr | GPL-3.0 |
| darktable (**including `exif.cc`**) | GPL-3.0 |
| RawTherapee, ART, Filmulator | GPL-3.0 |
| `librtprocess` | GPL-3.0 |
| ExifTool Perl source | GPL-3.0 |
| `rawler` / `dnglab` **source** | LGPL-2.1 — link only, do not read |

**Safe to read:** PetteriAimonen/focus-stack, z-stackr, stackaroni, `rawkit`
(all MIT/Apache-2.0).

**Do not link:** `dssim` (AGPL). Use `ssimulacra2` and `butteraugli` instead.

ExifTool's *tag tables* are not an independent specification — the pages are
generated from GPL source. Tag IDs, offsets and enum values are uncopyrightable
facts and may be used; the surrounding prose may not. Never read the Perl.

`rawler` is LGPL-2.1 and we link it. Ship it dynamically linked, or publish
object files or a reproducible build. Do not statically link it into a
monolithic binary and ship only that binary.

## Rules

1. **Storage is u16 CFA. Arithmetic is f32.** Never store f16 — a 10-bit
   mantissa gives ~8 LSB steps on linear 14-bit data.
2. **Never materialise aligned frames.** Gather at consumption inside each
   kernel. Materialising 60 aligned RGB frames is 24 GB and demosaics 60 times
   instead of once.
3. **The noise model is injected, never re-derived per stage.** A private
   per-stage noise estimate is the exact mechanism behind the prior project's
   2–5x defect.
4. **Never let a merge reference be a raw per-band argmax.** Argmax over N
   frames returns 1.95–2.61x single-frame noise. Use a regularised focus field.
   Measured: regularising drops speckle 34.4% -> 0.87% and noise 1.253x ->
   1.075x — necessary, and **still above 1.0**. A regularised selector is still
   a selector; the noise-gated average is the other half.
   **This rule was written and then broken by M30**, whose fact 242 ("2.3x more
   clipping whole-stack than at gathered frames") is an argmax artefact: at the
   shipped 31x31 regularisation it falls to 1.4x, and heavier still to 1.0x.
   The argmax *flees* clipped frames because clipping flattens the gradient.
   **The rule applies to analysis scripts, not just to the merge** — any
   statistic evaluated "at the best frame" inherits argmax's defects.
5. **Fit geometry at runtime; do not bake it.** Scale drift and the scale
   centre are per-stack quantities. Only sensor calibration belongs in a
   profile, and profiles live in data files.
6. **Never chain alignments, and never rely on a single fixed reference on a
   deep stack.** Both halves are measured, and the *reason* chaining fails is
   not the one originally assumed.

   Chaining is not merely noisy. **Short-baseline edges under-report
   magnification change**, and any span must telescope to the same total, so the
   gap is pure bias rather than accumulated error. On `coffee-bean` the span-1
   ladder totals −1.6876% against span-16's −5.8891%. The bias is **coherent**,
   so composing 104 edges yields **40.3 plane px** of corner error with
   **36.4 px in scale alone**. It needs a real inter-frame content change and
   lives below ~0.5 px of differential displacement: a resampler-free control
   recovers a planted increment at ratio 1.00, the same increment on a real
   defocus pair recovers at 0.56. **Short baselines look best by tile residual
   while being worst by truth — never judge an edge by its residual.**

   **Its magnitude is a property of the scene, not of the optics.** Across the
   five-stack corpus `1/S_W(1)` ranges **1.03x to 3.26x**: `coffee-bean` 3.26,
   `119MSDCF` 2.20, `109MSDCF` 1.32, but `112MSDCF` **1.05** and `113MSDCF`
   **1.03** — essentially none. Chaining all 78 adjacent edges on `112MSDCF`
   recovers **99.0%** of the direct long edge. Two stacks matched to 0.3% in
   per-frame displacement still differ **3.11x** in shrinkage, so it is not a
   function of baseline in any parameterisation, and no measurable property of
   the edge sets predicts it. Do not quote a single number for it.

   A single fixed reference fails differently: on a 105-frame stack it places
   only **76 of 105** frames, first failing at frame 73, because focus has swept
   the subject and the endpoints share no correlatable in-focus content
   (fact 4).

   **Do this instead.** Measure a sparse multiscale set of **direct** pairwise
   fits (a span ladder such as 1,2,3,4,6,8,12,16,24,32,48,64 plus every frame-0
   pair), composing nothing. **Discard spans 1-2 from the solve.** Then run one
   global linear least squares for per-frame `(log a, theta, tx, ty)` with Huber
   IRLS — `unit` weighting on deep stacks, `invvar` on shallow ones. This places
   105/105 frames at **6.76 plane px** held-out, and 0.58-0.67 px on shallow
   stacks. **Restrict the solution to the connected component containing the
   anchor** and report the rest unplaced: an unconstrained minimum-norm solve
   emits ~1e16 while still reporting full coverage. Verify with cycle
   consistency and held-out long-edge prediction, and **check the training
   graph's cycle rank first — a solve over a tree is chaining in disguise**, and
   any comparison against a chain is then vacuous.

   **Do not fit a shrinkage correction to escape any of this.** It is
   measurable and stable within a scene, and it transfers to **0 of 18**
   cross-scene pairs, making the worst case **83.4x worse**. Even an *oracle
   in-sample* correction leaves a chain at **13.92 px**, twice the error the
   plain global solve already achieves without it. The case the project would
   ship — fit on the deep stack you have, apply to the next capture — is the
   catastrophic one. Computing `1/S_W(1)` per stack is still worthwhile as a
   **diagnostic**, since it cleanly separates chainable stacks from unchainable
   ones, but it is a gauge, not a gain.

   6.76 px is not good enough for a final render. Treat deep-stack alignment as
   **usable, not solved** (SYNTHESIS risk 11). See
   `docs/research/M10-deep-alignment-measured.md`,
   `docs/research/M12-shrinkage-measured.md` and
   `docs/research/M3-alignment-measured.md`.
7. **Never compute statistics over the full decoded buffer.** `rawler` returns
   7168x5120 for the A7C II but fills only the 7032x4688 active area. The rest
   is synthetic zeros, not black level.
8. **Every performance or quality claim needs a command that was run.** Label
   claims MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED.
9. **Pair every sharpness metric with a flat-ROI control.** A sharpening pass
   raises gradient energy on featureless foam; that is how the prior project
   fooled itself. **This rule was written, published, and then broken by M38**,
   whose detail metric credits regularised argmax with **+35.47% "detail" on a
   flat ROI** — caught by an independent verifier, not by the author who had
   this rule in front of him. The control is one line. Run it *first*, not as
   a closing check, because a metric that fails it invalidates every number
   already computed with it.
10. **Never compare a spatial sd to a temporal sigma.** They are different
    physical quantities. A spatial sd over an image region carries scene
    structure; a temporal sigma across frames does not. High-pass first, or
    compare like with like. This error has now caused **three** retractions —
    the prior corpus's 1.10x correlated-noise claim, M2's "unexplained"
    1.46x model gap (1.01x once matched properly), and fact 88's 119MSDCF
    "43.2-53.1 DN", which the noise model caps at 22.9 DN at ISO 50 and which
    inverted the true noise ordering of two stacks. **The cheapest detector is
    the project's own model: any sigma that exceeds `sqrt(g*S + (RN_e*g)^2)`
    is not a temporal sigma. Check every published sigma against it.**
11. **Every claimed defect needs a placebo, and every headline number needs a
    regression test on its own code path.** What proved argmax was the cause of
    M2's 1.253x was not a better measurement of argmax — it was a *different
    merge rule* on identical data (mean, 0.534x) and a selector with the same
    winner histogram but no noise coupling (0.981x). Without those it was only
    correlational. And the 1.253x itself had 52 tests behind the library and
    zero covering the code that produced it.
12. **The author never verifies their own work.** M2 was self-verified
    thoroughly and still shipped five wrong supporting numbers, two of them in
    the direction that loses an argument. See `docs/research/M2-verification.md`.
13. **Sweeping a parameter? Check the plant can express the failure first.**
    M11 swept the focus window on a fronto-parallel plant and reported it "still
    improving" at the widest setting. That plant is mathematically incapable of
    producing an interior optimum for a symmetric window, so the result was not
    weak evidence — it was **none**, and it cost the project a window less than
    half the right size. Ask what the stimulus would have to contain for the
    answer to be anything but the endpoint. **Report an endpoint argmin as "no
    turnover found within the sweep", never as an optimum.**
14. **Verifying the read-only corpus guarantee? Use `Get-ChildItem -Force`.**
    Without `-Force` it silently skips hidden and system files and under-reports
    `C:\dev\macro` by **1081 files / ~312 MB**, which looks exactly like
    evidence that the tree was modified. Correct totals: **18530 files /
    286,893,514,060 bytes**. Also: `C:\dev\macro\test\119MSDCF` and
    `D:\personal\macro\119MSDCF` are the **same 33 frames**, verified
    byte-identical through a full measurement sweep. Two stacks must mean two
    *different* stacks — use 109/119 or 112/113, never a directory and its
    mirror.
15. **"Halo" is overloaded — never use the bare word.** In the plugin interface
    and SYNTHESIS fact 32 it is the *rectangle expansion* a filter needs beyond
    its output tile (19.42 / 32.39 / 89.23 plane px), an alignment and warp
    margin. In the stacking literature it is the *artifact* at an occluding edge
    where the selector drags one surface across another. Say **"plugin halo"**
    or **"occlusion halo"**.
16. **Timing a parameter sweep? Alternate direction and take the per-setting
    minimum.** M14 measured a single forward sweep at **−0.7%** and a reverse
    sweep at **+19%** on the same binary and settings, and a function reading
    **21% slow** purely for being timed last. Thermal drift, clock ramp and
    cache warming all correlate with sweep position, so a one-directional sweep
    attributes them to whichever parameter came last. Use several alternating
    sweeps, report the minimum per setting, and quote a near-flat result as a
    **bound, not a value** — two honest runs of the shipped cost sweep
    disagreed 0.69% vs 1.28%, which is larger than either is from zero.
17. **Before you bin a statistic, ask what map you are binning it against.** If
    the bins and the quantity being binned come from the same data, name the
    mechanism that could drive both — and if you can name one, the result is
    circular until you break the shared path. M21 scored occlusion bimodality
    against a depth-step map built from the same focus volume, but a bimodal
    pixel makes its own argmax flip and so *manufactures* the depth step it is
    credited with landing on: **29.47× collapsed to 4.38×** once the two were
    measured at different scales. M22's cross-scene test reported over a million
    "defects" against an independence baseline because both subjects sit
    centre-frame. **Fixes: bin at an independent scale, use a shift control that
    destroys per-pixel correspondence while preserving every spatial statistic,
    or permute the axis the effect lives on.** Pair any of them with a
    known-real positive control, or the collapse ratio has no scale to be read
    against. M20 §2 still carries an *unresolved* instance of this — its optics
    gate may be checking a formula against a constant derived from that formula.
18. **Say which direction each metric can be fooled in, next to where you use
    it.** `mean |∇|` rises when a merge *manufactures* detail exactly as it does
    when a merge preserves it — measured, plain argmax reads **above ground
    truth** at σ=0.050, and the Wiener output carries 24% more gradient
    magnitude while carrying 12% *less* gradient correlation with truth. So it
    is admissible as a test against **collapse** and inadmissible as evidence of
    quality. A metric with no stated failure direction is not an acceptance
    criterion.
19. **kebab-case** for directories and files. Crates are `strehl-*`.
20. **Before running any gate, control or metric, write down the input that
    would make it FAIL — and check that such an input exists.** If none does,
    it is arithmetic, not evidence, and must be labelled so. **Three shipped
    examples, all caught by independent verifiers and none by the author:**
    M20's optics "gate" is the algebraic *inverse of its own input* (`B` was
    obtained by inverting the equation the gate re-derives), so no
    configuration of the model could have failed it; M38's detail metric
    scores a flat ROI as *gaining* detail; and M33's two half-step phases,
    quoted as replicating each other at 0.05%, have hit rates summing to
    **1.0000 by construction** — they are complements, and a complement cannot
    corroborate its own partner. **Measuring instead of arguing buys nothing if
    the measurement has no power to reject.** Rules 9, 11 and 13 are special
    cases of this one. Prefer the cheap adversarial input: a flat ROI for a
    detail metric, an a-priori value for a fitted constant, a known destroyer
    for a quality score, an arithmetic check that two "independent" arms are
    not the same number twice.
21. **A fitted constant cannot gate the model it was fitted to.** Where a
    constant was obtained by inverting a relation, gate that relation with an
    *independently predicted* value instead. `B = 1 + m/p = 3.000` from pure
    geometry predicts M5's measured knee to **2.1%** — that is a real gate, it
    costs one line, and it was available the whole time.
22. **The rules in this file are an executable checklist, not a creed.**
    Rules 4, 9 and 10 were each written down, published, and then violated by a
    later milestone *by the same author who wrote them* — M30's fact 242 is a
    raw argmax (rule 4), M38's detail metric shipped with no flat-ROI control
    (rule 9), and fact 88 compared a spatial sd to a temporal sigma (rule 10).
    All three were caught by independent verifiers. **Agreeing with a rule does
    not execute it.** Before publishing a milestone, walk this list and name,
    per rule, the line of code or the command that discharges it.
23. **`scipy.ndimage.sobel(cube, axis=k)` smooths every axis except `k`.** It
    applies `[-1,0,1]` along `axis` and `[1,2,1]` along all others — so passing
    a `(frames, y, x)` cube silently smooths along the **frame axis** and
    changes the focus measure. M32 did this and inflated its headline σ-count
    by ~1.7–1.9×. Extract the 2-D plane first, or pass `mode`/`axes`
    explicitly. **General form: any separable filter applied to an array with a
    non-spatial axis will touch that axis unless you stop it.**
24. **Verification must re-choose, not re-compute.** Across four independent
    passes over fourteen milestones, **every published number that was checked
    reproduced exactly**. Not one defect was arithmetic. All were *choices* — of
    nuisance estimator, reference, arm, null, or library default. A verifier who
    recomputes the author's formula on the author's inputs confirms every one of
    them. So a verification brief must name the choice points and require a
    different defensible setting at each. See discipline 253.
25. **Claim a number block before you use it, and check the claim
    programmatically, per namespace.** `SYNTHESIS.md` has **three** independent
    numbering spaces — facts (`§4` table rows), disciplines (`§5` list items) and
    questions (`§10` list items) — and disciplines and questions legitimately
    share numbers. M19 wrote "M19 owns 120–139" while M20-V already held 122–139.
    Run the collision check in `experiments/*/fold-*.py` before writing, **never
    eyeball it**, and if a block is taken, shift the whole block to open ground
    rather than interleaving. Record the shift in the fold and in the report.
26. **Prove that a diagnostic does not perturb the output, by hash.** Any
    statistic, probe or observer added to the merge must ship a run showing
    **byte-identical output** with it on and off, placebo included — the way
    fact 420 does. An argument that a channel is read-only is not evidence that
    it is.
27. **Before declaring a long-running process dead, state what a healthy one
    would look like at this instant.** If a working run and a failed run predict
    the same observation, the observation is not evidence and the correct action
    is to wait. Three specific traps, all of which fired here (see
    [`2026-08-external-review.md`](docs/proposals/2026-08-external-review.md) §5
    item 6): **zero bytes on disk is not zero work** — an agent that reads for
    three hours before its first write is indistinguishable from a corpse under
    a file-count probe; **a turn counter read at 473 s measures the sampling
    instant, not the run**; and **a stand-down is an intervention, not an
    observation** — telling live workers to stop causes the silence it was sent
    to diagnose. Ten agents were written off on this evidence and every one of
    them later landed a folded milestone.
28. **A report's proposed numbers are not where its facts live. Check for an
    existing fold by CONTENT before folding, never by number.** M19's §9
    proposes facts 120–139; those facts are actually folded at **400–419**,
    because rule 25's collision check moved the block. An orchestrator resuming
    on a stale note read "120–139 are free", which is true, and would have
    written a **20-row duplicate** of an already-folded milestone. The number
    being free is not evidence the fold has not happened. Match the first ~70
    characters of each proposed fact against the whole of `§4` and require
    **zero** matches before writing; if all match, the fold is done and the only
    correct action is to record the mapping in the report. The same check is
    what proves a re-run is a genuine double-fold rather than a new block.
    **Corollary for report authors:** number proposed facts `P1, P2, …`, not
    `120, 121, …`. Absolute numbers belong to the orchestrator at fold time, and
    every absolute block proposed in a report so far has either collided or
    moved.

## Layout

| Path | What |
| --- | --- |
| `crates/strehl-core/` | Types, noise model, tile views, geometry |
| `crates/strehl-raw/` | RAW decode behind `rawler` |
| `crates/strehl-cli/` | The binary |
| `docs/captures-needed.md` | **Data owed by the owner.** Read before asking for captures. |
| `docs/research/` | Research corpus and decision record |

## Research corpus

| File | What |
| --- | --- |
| `SYNTHESIS.md` | **Start here.** Decision record, revised after review. |
| `M39-verify-detail-metric.md` | **INDEPENDENT.** First outside verification since M2. Found M38's detail metric credits a *flat ROI* with +35% detail, inverted M38's error budget, and showed fact 19's 1.253x does not reproduce on the shipped operator (1.068x) |
| `OWNER-QUESTIONS.md` | **Read this before asking Chris anything.** Decisions I could not make alone, captures still outstanding, and two numbers that must NOT reach a user-facing recommendation yet. Append; do not rewrite. |
| `M20-VERIFICATION.md` | **INDEPENDENT.** M20's optics gate is a **tautology**; the 15.1% headline is one capture out of a **3.5%–65.8%** corpus range; refutes fact 88's mechanism; flags the f/5.6 advice as a two-stop extrapolation with no aberration term |
| `M31-VERIFICATION.md` | **INDEPENDENT.** 15 defects across M27–M30. Refutes fact 242 as a raw-argmax artefact (rule 4). Every published number reproduced exactly — **every defect was a choice of estimator, reference, arm or null, not an arithmetic error** |
| `M36-VERIFICATION.md` | **INDEPENDENT.** M32's focus measure was `sobel` on a *cube*, silently smoothing the frame axis: headline 142–991σ is really **84–512σ**. M33's direction is inverted (48.7% HIT) and its "replication" is complementary by construction. Fact 281's mechanism refuted — the real channel is **acceptance-set size** |
| `REVIEW.md` | Adversarial review that corrected four design errors |
| `REVIEW-plugin.md` | **Plugin-architecture critique.** Cordis verified against the PDF; four blocking interface fixes; camera/lens plugins are profiles |
| `M2-rss-resolved.md` | **Tiebreak.** Two docs disagreed 2.2x on peak RSS; resolved by measurement. Peak tracks live concurrency, and the 8 GB ratchet is at 89% by N=105 |
| `M1-decode-measured.md` | Measured decode throughput and sensor constants |
| `M2-baseline-skeleton.md` | The naive argmax baseline, and the measured defect it exposes |
| `M2-verification.md` | **Independent re-derivation of M2.** Headline confirmed and causally proven; five supporting numbers refuted |
| `M3-alignment-measured.md` | Measured alignment cost, motion model, and why chaining is dead |
| `M4-fpn-measured.md` | Dark-frame noise: sigma-vs-N, the fixed-pattern floor, read noise vs ISO |
| `M5-diffraction-measured.md` | **The bellows factor, measured from the raw CFA.** `B = (1+m/p) ∈ [2.41, 3.06]`, `p ≈ 1.0-1.4`; `p=0.5` refuted model-free. EXIF `FNumber` is **not** bellows-corrected — marked f/11 is optically f/33 |
| `M6-residual-halo-measured.md` | **Why alignment stops at 0.6-1.3 px, and how big the halo is.** The residual is **blur-induced correlation bias**, not depth-dependent magnification: in-focus tiles align at **0.144-0.172 px** (at the 0.19 px estimator floor) while far-from-focus tiles in the same pairs sit at 0.25-0.69 px, surviving within-pair (p=0.010) and within-tile. But the bias is **symmetric degradation, not directed displacement** (S6 null on all three stacks) — so **the lens plugin stays a data file** and the fix is in the aligner (weight tiles by `\|c − w\|`). Halo is **stack-dependent** (19.4 / 32.4 / 89.2 px), which is what kills a scalar `halo()`; §3.4.1 B1's "39 px" was a *displacement*, not a halo. Closes questions 6 and 10, closes §3.4.2, opens risk 11 |
| `M7-gpu-focus-measured.md` | **The fusion prize, priced.** Ring-difference focus + merge on the GPU is **4.117 ms / 22 frames**, bandwidth-bound at 84% of measured DRAM read. Fusing focus into the merge saves **1.45 ms = 0.14% of the pipeline** — *not* enough to justify constraining plugins to spliceable WGSL. Answers risk 10 / question 11; fact 21 is CPU-time-under-concurrency and cannot bound a GPU design |
| `M8-scratch-measured.md` | **Decoder scratch, and the term that was actually missing.** Scratch is **39.36 ± 0.11 MiB per concurrent decode**, file-size proportional. But **most of the planner's error was never scratch** — peak resolves into `14.4 MiB floor + live x 342.8 MiB + ⌈log₂ chunks⌉ x 110.04 MiB`, that last term being one `Selection` per level of rayon's reduce tree (= `px x 14`, 550 MiB at 18 chunks). Recommends the worker cap 20 → 16. **Also refutes SYNTHESIS §3.2.1 assertions 1 and 2 at assertion 1's own specified pair**, and finds the "379 vs 321 MB" per-worker gap was a MiB/MB unit mismatch |
| `M9-support-coupling-measured.md` | **What the merge is actually coupled to, and why nothing goes on the interface for it.** Argmax's noise excess tracks the focus operator's **centre-tap sensitivity fraction φ** (ρ = **+0.918 / +0.894**, p < 0.0001), **not** its support radius (ρ = −0.170 / −0.243, n.s.); a zero-centre-tap Sobel shows **no excess at all (0.9952x)**. For a ring difference **φ = 1/(2·(2·inner+1)²) and the outer radius cancels exactly**, so the proposed `support_px()` would have reported the one term that provably does not matter. **Rejects §3.4.1 B3** — the last Blocking verdict standing on an unmeasured claim — and reinterprets (does not retract) fact 25. Also: the flat-ROI noise objective is **monotone-then-flat with no interior optimum**, and regularising can *harm* |
| `M10-deep-alignment-measured.md` | **Deep-stack alignment: why chaining really fails, and what works instead.** Chaining does not fail from accumulated random error — **short-baseline edges under-report magnification change by ~3.2-3.5x**, coherently, so 36.4 of the chain's 40.3 px corner error is scale alone. Proved by a telescoping conservation identity (span-1 −1.6876% vs span-16 −5.8891%), then isolated: the bias needs a **real inter-frame content change** and lives **below ~0.5 px** of differential displacement (resampler-free control recovers a planted increment at 1.00; a real defocus pair at 0.56). A global least-squares solve over a sparse multiscale graph of direct edges places **105/105 frames at 6.76 plane px** against a fixed reference's **76/105**. Error is bounded by the *edges*, not the solver. Also: the scale centre is per-stack, not per-rig. **Risk 11 → partially solved; rule 6 rewritten**; facts 43-48 |
| `M12-shrinkage-measured.md` | **Can the short-baseline shrinkage be calibrated away? No.** Fitted on one stack it transfers to **0 of 18** cross-scene pairs and makes the worst case **83.4x worse**; even an oracle in-sample correction leaves a chain at twice the error the plain global solve already achieves. The magnitude is a property of the **scene**, ranging 1.03x-3.26x across five stacks — two stacks matched to 0.3% in displacement differ **3.11x** — so fact 43's "3.2-3.5x" is rescoped to `coffee-bean` alone. Also **corrects fact 49**: `112`/`113` share a per-frame focus step rather than sampling one interval at two densities, measured both by magnification and from the focus band in the pixels. Introduces a **focus index** measurable without metadata, since `FocusPosition2` has only 3 distinct values across a 79-frame sweep. **Rule 6 amended; risk 11's shrinkage question closed**; facts 50-54 |
| `M11-focus-bakeoff-measured.md` | **What to select with, and what selection costs.** A 47-operator pre-registered bake-off on two real stacks, scored on a measured Pareto front of selectivity against noise excess. **The shipped `ring(1,3)` ranks 26-27th of 36** (N = 1.3475x, ~45% of the best selectivity); the recommendation is **Tenengrad under an 11x11 box window** (N = 1.1324x) — re-tuning the ring cannot close the gap. Headline: **no operator anywhere on the front is noise-free** (0 of 36 reach N ≤ 1.02x), so operator choice alone cannot rescue a selector. Zero-centre-tap operators *are* noise-free (φ = 0.0000, Ncorr 0.989-0.997) but recover only 34-40% of a planted focus surface. **Windowing and normalisation each re-introduce a centre tap, additively** — so φ must be probed on the whole configured stage, not the kernel. Closes risk 2; facts 37-42 |
| `M13-window-depth-measured.md` | **Where the focus window sits, and why a depth discontinuity is what puts it there.** M11's 11x11 is **dominated** — `tenengrad-w8` beats it in **36 of 36** occluding-edge cells at lower noise and identical cost — and the measured argmin is **`tenengrad-w13`, a 27x27 box**, stable in all three noise seeds. The central finding: **remove the depth step and the objective stops turning over**, running to the sweep endpoint; put it back and an interior optimum appears. So M11's "still improving at 23x23" carried *no* information — a fronto-parallel plant **cannot** turn over. **M11's per-pixel metric is structurally blind to the damage in 30 of 30 cells** (18.48 DN mean penalty), which is why it chose a window less than half the right size. Cost is **flat in the radius** (2.53% spread over w1-w40) because the box is a running sum, so the widening is free. Adaptivity has real oracle headroom (5.7-46.8%) that **no realisable rule reached**. Also corrects **M11 A1's φ monotonicity** (φ peaks at w15-w17 then declines) and proves `D:\personal\macro\119MSDCF` is a **byte-identical mirror**. **Closes question 15; facts 60-69** |
| `M14-tenengrad-implemented.md` | **Shipping the operator M11 and M13 chose, and what shipping it exposed.** Replaces the ring difference in `strehl-core` with Sobel magnitude under a 27x27 running-sum box. Two results the research milestones could not produce. **(a) The benchmarked operator is the gradient MAGNITUDE, not the squared "energy"** its name implies (`squared: false`) — shipping the textbook form would have inherited M11's and M13's evidence under a name that did not earn it. **(b) The shipped CLI reproduces M13's separately-written harness to every printed digit** (1.068x, 30.114 DN, 6 winners), which is the cross-implementation check that separates "the operator is right" from "one harness is self-consistent". Index speckle falls **34.381% → 1.010%**. Also refuses M13 §6.4's φ bracket, correctly: **φ spans 47x over a 64x texture-amplitude range**, so the bracket pins an ROI. **Verification found a blind spot M14 under-reported as a note about a test: the shipped operator has EXACTLY ZERO focus discrimination on an untextured monotone edge** (fact 73) — which is why confidence must come from cross-frame spread, never magnitude. **Facts 70-73; opens question 19** |
| `M15-regulariser-window-measured.md` | **Does the window optimum survive the merge regulariser? Yes — and the orchestrator's hypothesis was refuted.** The argmin is **w13-w14, always `interior`, at every regulariser width 1-33**; shipping w13 costs **0.050 DN** at width 17 against a pre-registered 0.87 DN threshold. **Closes question 17 and discharges M13's last recommendation-moving caveat.** The mechanism is real but lands off-target: the regulariser substitutes for the window at **1.72 : 1 (r² 0.94)** on cells with no depth step and at **≈ 0 (r² 0.10)** on the cells that decide the window — a wide window buys contrast *localisation* at an occluding boundary, which a post-hoc smooth cannot supply. Three results beyond the question: the flat aggregate is a **cancellation** (`horizontal` 10/10 narrower, `vertical` and `bar` wider) and doubles as the positive control; the regulariser is worth **−35% absolute error**, the largest unbuilt win in the project; and width 3 is **worse than no regulariser at all**, reproducing fact 36 unregistered. Gate A reproduced M13's committed CSVs **byte for byte** on both stacks. Two self-corrections, both disclosed rather than dropped. **Facts 80-88; opens question 20** |
| `M16-orientation-fpn-measured.md` | **The orientation anomaly is the scene, not the machinery — and `WINDOW_RADIUS = 13` survives.** Fact 83's asymmetry transposes exactly when the *plant's textures* are rotated 90° with every piece of code held fixed (median shift difference **0.0** windows vs **8.0**), and symmetrising the texture nulls it to **+0.0**. Mechanism: horizontal edges are localised by `Gy`, vertical by `Gx`, and this corpus carries **14-22× more vertical gradient energy**. The review's proposed row/column-destripe fix moves the statistic by **0.0 windows** and is *worse* on the level statistic; the row-FPN mechanism it assumed is refuted at source — this sensor's fixed pattern is **isotropic at all 11 measured ISOs** (0.968-0.999), and the row-correlated component is **~10³ smaller** than the scene's own row structure. **Read §11 before trusting any `dmae_far`/`bleed_*`/`mis_*` number for a horizontal edge** (fact 506: `edge.rs` derives its baseline band from `roi.width` regardless of axis, emptying the far band on non-square ROIs; `E_excess` is unaffected, which is why it was the primary statistic). Facts **90-99, 506-508**; disciplines **40-44**; closes question 20. Its §13 was renumbered on fold — see the reconciliation note there. | M16 |
| `M17-dual-response-measured.md` | **Question 19 (fact 73's monotone-edge blind spot), settled — and the dual loses.** The box `max` fixes the blind spot and costs *no* noise, but costs **+18.91 DN** on M13's occluding-edge cells, **21.7x** the pre-registered bar. Candidate (c) `tenengrad-sq-w13` clears every gate and is **0.96x** the shipped cost. Answers question 100. |
| `M20-deconvolution-ceiling-measured.md` | **Does the external review's multi-frame Wiener reframe beat selection here? Measured: no — and the reason is the aperture, not the algorithm.** The estimator `L̂ = Σ H* Y / (Σ\|H\|² + σ²/S)` **is** MMSE, confirmed by three independent routes agreeing to 6 decimals, so the algebra is right. But **unguarded it LOSES to plain argmax by up to 31% RMSE even given oracle depth and an oracle prior** — the fallback guard is load-bearing, not optional — and on real data **only 15.1% of pixels** sit past the crossover, because for the *median* pixel local noise exceeds local signal structure **in its own best frame**. Hard ceiling: where every frame's OTF is zero the estimator returns exactly zero, and at marked f/8 and f/11 MTF@Nyquist **is** zero. The prize turns out to be a capture change: **blur-per-step in pixels is aperture-invariant**, so marked f/11 → f/5.6 buys **9.6×** contrast at 4-px detail for 2× the frames and no extra light. Four self-corrections, including a broken MMSE control and a guard that was algebraically identical to the thing it was guarding. **Facts 140-145; verification in flight; the optics gate may be circular — see §2** |
| `M21-occlusion-bimodality-measured.md` | **Is the through-focus curve really bimodal at occluding edges? Yes, and 85% of my first number was a tautology.** Multi-peaked curves are enriched **4.38×** at depth steps on `coffee-bean` against a scene-matched **frame-permutation placebo reading 1.01×**, stable across subsample offsets, surviving stratification in *every* intensity-gradient quintile (pooled ~2.7×, up to **14.3×** in the most textured), and intensity-edge binning alone gives **0.00×** — so it is not an edge artifact. **But it is undetectable on `109`/`119`, where the permutation null shows noise alone flags 60–98% of pixels**, so the detector only works gated on calibrated σ — the same conclusion M20 reached by a different route. Two reusable failure modes kept in the record: the shipped R=13 window **destroys the signal it looks for** (54 sensor px vs a much narrower veiled zone), and binning against an argmax field from the same volume is **circular**, since a bimodal pixel manufactures its own depth step. **Facts 150-152; binds the M18 fold seam** |
| `M22-hot-pixels-measured.md` | **How bad is this sensor? Cleaner than the review assumed.** The 242 darks arrive as 11 ISO groups, which is a free replication test: **recurrence, not a σ threshold, is the discriminator** — 3,947 pixels recur in ≥6 groups against 2e-08 expected by chance, while 108,776 single-group flags are *fewer* than chance and are simply the threshold's false positives. This deleted a tuning knob instead of tuning it. **But the defect barely matters:** in real 1.3 s frames the excess is **+3.0 DN mean, 0.0 median**, flat across three signal decades (a fixed additive offset), worth **0.39σ → 0.13σ** from shadow to upper midtone; only 3 pixels sensor-wide are both always-hot and >100 DN. **The delivered darks are also at the wrong exposure** — all 1/100 s against real stacks of 1/60 s–2.5 s — and a cross-scene test with a **shift control** finds ~839 scene-independent defects of which the dark map contains 5. My first cross-scene test used an independence baseline and reported >1M "defects" because both subjects sit centre-frame; the known-real dark map is the positive control. **Facts 160-162; adds `captures-needed.md` §6** |
| `M23-metacalibrated-edges-measured.md` | **R4 (per-edge metacalibration), and it ships NOTHING.** Dead three ways: the local-linearity premise is refuted (`R` swings 0.53 to 0.99 across delta), the response measures the plant's own **bilinear resampler** not defocus (a zero-defocus self-pair reads 0.372), and held-out is **6.758 px unchanged**. Withdraws fact 45's causal reading. |
| `M24-photometric-drift-measured.md` | **Does R9's premise hold — is there per-frame photometric drift to model? Yes, and the fix is sharper than the review asked for.** Peak-to-peak mean level varies **2.88% / 6.84% / 8.93% / 11.70%** across four stacks — and **`109MSDCF`, the stack most of this project's measurements were made on, is the quietest at 0.91%**, so a clean result there says nothing about photometric handling. The framing confound (breathing changes magnification, which moves the mean without any exposure change) is discharged both ways: `coffee-bean` genuinely changes exposure mid-capture (`4/5 s` → `5/8 s`), and a central 600 px ROI moves *at least as much* as the full frame on all three stacks tested, correlating +0.85 to +0.97 — the opposite of the framing prediction. **The useful part is that the simple explanation fails:** the measured level ratio across `coffee-bean`'s two exposure groups is **1.0443 against an EXIF-predicted 1.2800**, i.e. 16% of prediction, most likely auto-exposure compensating a drifting light. So **the per-frame gain must be FITTED, never read from metadata** — EXIF is blind to 7–9% on two stacks and overcorrects ~6× on a third. A probe, not a full milestone: no gain was fitted and no merge output was measured. **Facts 180-182** |
| `M25-simulator-measured.md` | **The calibrated simulator reproduces the project's noise-and-selection machinery and does NOT reproduce its optics or its subjects.** Gate 1a **PASS 16/16** — fact 35's φ↔excess mechanism emerges from calibrated constants alone, with a zero-centre-tap placebo reading exactly zero. Gate 1b **PARTIAL 3/5**: no single defocus rate matches both fact 19's argmax ratio and its plain-mean ratio. Gate 1c **FAIL** — transplanted to a two-layer plant with known ground truth, M21's byte-identical occlusion detector reports enrichment **0.77× against a real 4.38×** while its permutation placebo stays honest, so the detector fails rather than the harness. **Gate 2 is the one that matters: the negative control fires on gain, on correlated noise and on no noise, and is BLIND to deleting the diffraction PSF entirely** — a change that moves green-plane power at 0.455 cyc/px by **123×**. That single result disqualifies the twin from scoring deconvolution, which is the job the external review assigned it. Also lands a hit on a shipped constant: fact 14's two-level read noise under-predicts measured dark σ at **ISO 50 by 45%** while being within 2.6% at ISO 160, so the model is the wrong *shape*, not merely mis-tuned — and ISO 50 is where a tripod macro stack is shot. Six of its own errors are documented in §5, including a plant pinned at a fixed point of its own harness. Facts 540-550, disciplines 268-275, questions 111-116. | M25 |
| `M41-r3-kill-measured.md` | **R3 — "make the merge itself a multi-frame Wiener deconvolution" — STANDS REFUTED, and the second pass had to withdraw one of the two metrics that scored it.** Guarded focus-axis RIF costs **3.47× / 3.91×** the shipped merge's flat-ROI high-pass noise against a pre-registered 1.10× bar, so the two REFUTED clauses are **exhaustive over the detail axis** — refuted at every `f_D/f_A` from 0.50 to 5.00 (fact 479). It puts **63.97% / 81.25%** of detail pixels outside the range of every input frame, against 0.000% for the shipped merge; Forster 2004 called ~30% a defect. The scorer is not a tautology: arm C returns SPLIT REOPEN/REFUTED, and the clauses are disjoint over an 800 000-point grid. **The positive control passes** — on a plant where the OTF is exactly the one being inverted, arm D wins by **+11.17 dB** — so the optics refuse it, not the algebra (fact 464), and ~8 of those ~10 dB are the diffraction term rather than the focus axis R3 proposed. **The withdrawal:** the FRC 1/7 crossing of `0.4961` reported by every arm, both nulls and both circularity variants, is `ff[-1]` — the last ring centre returned when the curve never crosses. A right-censored bound published as a measurement, then used as **both** sides of a ratio (facts 475-476). 32 repair settings, none admissible. **It also corrects fact 417 and fact 49**, and the honest closing note is that the verdict survived by margin rather than design: at 1.2× instead of 3.5×, half the condition would have rested on a metric with no power. Facts 460-479, disciplines 276-283, questions 117-122. | M41 + M44 (second pass) |
| `M26-colour-clipping-measured.md` | **The measurable half of R13 (colour), and it caught a hole in a decision already taken.** Two results. (1) **Do not white-balance before the noise gate.** As-shot WB is a per-channel gain of **2.13–2.86× on red**, varying per stack because the body was on auto WB; the calibrated model is valid only in native raw DN, so gating after WB understates σ by a factor tending to **m** in the shadows and **√m** in the highlights — believing red up to **2.86× quieter than it is**, hardest exactly where M2 measured the argmax defect. Nothing errors; the gate just reverts toward the selector. (2) **Clipping defeats discipline 29.** Cross-frame peak contrast — chosen over focus magnitude *precisely because* magnitude fails on fact 73 — reads **1.0000, its maximum**, on pixels pinned in every frame that carry zero information, since **85.9%** of them have `f_min` exactly 0 (clipped-blob interior) against **0.0000%** of never-clipped, while `f_max` is **52× typical** (the blob's edge crosses in another frame). Magnitude fails there too, so the input must be masked rather than the metric swapped — one comparison per sample. Saturation is per-stack: **four of six stacks have none at all**, `coffee-bean` has 1.26%. The author's own headline prediction (partial clipping) was **mostly refuted** — 1.67× collapsed to **1.06–1.09×** under brightness matching. Checked-and-clean: the 16383-vs-15360 white-level split is already handled and tested in `noise.rs`. **Facts 200-203, discipline 110-111; qualifies discipline 29** |
| `M27-coverage-gap-measured.md` | **Can the pipeline tell, from the stack alone, that the bracket did not cover the subject? Yes — and the answer changed a headline design decision.** Ground truth by construction: remove frames from a real bracket and the pixels whose best frame was among them have provably lost coverage. A **hole** is detectable from **one** missing frame — peak-curvature excess **+0.45 to +1.39** over a null stable at **1.40–1.43**, vertex-offset excess −0.10 to −0.48 — using only the reduced stack. **Uniform** under-coverage, where no internal control exists at all, does **not** need the optical model as predicted: frames within 50% of peak height is **absolute** and falls **3 → 2 → 1** under decimation, with the min-estimation confound closed by holding the threshold at the full-stack minimum (identical column). Deployable recipe: pixels resolved by ≤1 sample = **0.01%** at 53 frames, **37.46%** at 27, **75.76%** at 9 — so `coffee-bean`'s 105-frame bracket is **~2–4× denser than needed** at f/8, which (DERIVED, contingent on M20's circularity check) roughly pays for the aperture change M20 wants. **The headline is the direction:** a gap makes the curve look **sharper and better centred**, refuting the author's prediction, and joining fact 73 and fact 203 as a *third* mode reading maximum confidence at zero information — which promotes discipline 120 and **disqualifies every self-normalised shape statistic as confidence**. Two further author errors recorded: the first detector was an oracle, the first control drifted. **Facts 210-213, discipline 120-121; supersedes discipline 29 in scope** |
| `M28-robustness-mask-measured.md` | **R10's robustness mask, and the premise needed correcting before the mask could be built.** Wronski's shape — noise-normalised disagreement against a running estimate — is right for a **burst**, where frames are nominally identical. **A focus stack is the opposite case: the frames are supposed to disagree.** Measured fix, one line: **reference the immediate neighbours, not the stack.** On the *clean* stack the pairwise residual grows **1.13 → 12.30** as separation goes 1 → 16 (near-linear = accumulating breathing; noise would be flat, defocus would saturate), and the radial profile is **1.82× centre-to-corner with a whole-stack reference against 0.98× with an adjacent one**. The architectural consequence inverts the prediction: **the mask can run BEFORE alignment**, so alignment can be protected by it. Sensitivity, plant-measured with a shift-zero placebo that fires **0.0%** at FPR ≤ 1%: a **4-green-pixel (≈20 µm at the subject) shift is caught 53.8%** at FPR 1% and 89% at FPR 5%. **Tile scale is not a sensitivity knob** — detection is flat within 10% across a 4× range, because the baseline tail is deterministic so signal and threshold average down together; pick the scale on compute cost. Transfers: a clean-calibrated threshold flags **1.01% / 8.33% / 17.88%** on clean / bubbles-move / scene-evolves, ordering pre-registered. Two incidental results: the **M4 noise model predicts the clean tile residual to 9.9%** with no free parameters, an independent validation at a scale it was never fitted to; and **M24 needed a *how*** — the author's own median-over-subject-crop gain read 4.28% where M24 measured 0.91%, because that median absorbs focus signal, so **fit gain as the mean over all pixels**. Four author predictions refuted, incl. a gradient normalisation that was an artefact of its own divisor. **Facts 220-225, discipline 130-131, question 45** |
| `M29-static-defects-measured.md` | **R11's other half — dust — and the free lunch the review argued for does not exist.** The claim was that an estimator averaging `n_eff` frames dilutes a sensor-fixed shadow while a selector copies it whole. Priced from measured warp geometry rather than by detecting any dust: **`D = 0.999` at `n_eff = 3`.** The mechanism is general and worth carrying — **suppression is bought by the *span* of frames averaged, not their count, and a focus merge averages ADJACENT frames precisely because they agree** (M27: `n_eff ≈ 3`; M28: disagreement grows near-linearly with separation). Adjacent-frame warp is **sub-pixel, 0.07–0.22 green px**, which independently corroborates fact 221. **Dust must therefore be handled explicitly.** It also cannot be measured from subject stacks: limit **32–50% shadow** against real dust of 1–15%, no excess over the shift null, and the floor is **scene texture — rms exponent +0.025 over a 16× frame sweep**, so more frames buy nothing. Flats reach a **0.120%** floor at n=20, **158× better**, which turns `captures-needed.md` §4 into a specification. The mechanism behind all of it: a self-ratio static map responds to depth × **local scene brightness**, `R ≈ 0.92·(g/blur(g))` — which is *why* a flat is the right instrument. **Five author errors, disclosed:** a global correlation provably an order of magnitude below its own null before it was run; a positive control scored against an oracle difference map (259.6σ there, 0.074σ against the available quantity); a window-extremum readout that moved 0.005 over a 32× depth range; standardising a common fractional defect; and choosing a reference to maximise sample count — the exact error discipline 130 was written to prevent, committed by its own author two milestones later. **Facts 230-234, discipline 140-142, question 50** |
| `M30-hdr-cobracket-measured.md` | **R17 (HDR co-bracketing), and a general constraint that settles most of the capture-design workstream.** The review's premise is right and already paid for — the estimator handles per-frame gain (M24, M28) — so the question is whether there is a dynamic-range problem worth spending frames on. **At fixed total exposure time, splitting a light budget across exposures is EXACTLY NEUTRAL in the shot-noise regime**: `m` base + `m` at +2 EV cost the same `5m` time units as `5m` base frames and reach the same variance. Measured per pixel: median ratio **1.00041 / 1.00470 / 1.00192**, residual attributable to read noise in the predicted direction. **That identity constrains R15, R16 and R17 together — how a budget is *divided* across frames does not affect noise, only the total does — so every capture decision reduces to the non-noise asymmetries, and all are now measured.** Read noise binds below **2.0–6.5 DN** above black (0.014–0.044% of full scale) and **not one pixel in three stacks** sits there; clipping **at the frames a merge gathers** is **0.075%** max and **2.3× lower** than whole-stack, because highlights are disproportionately out of focus. What is left is **aperture**, which changes the optics rather than the allocation and which M20 prices at 9.6× — so capture co-design should spend its effort there. Two smaller results: the review's direction is **backwards for highlights** (a **−2 EV** pass rescues clipping; +2 EV clips *more*, 1.89% newly clipped), and **R16's half-step proposal is disposed of for free** — once photons are indifferent it is purely a focus-coverage question, and M27 measured coverage as saturated at 53 frames. **One author error, which voided script 01's headline:** the placebo held **frame count** constant when the scarce resource is **exposure time**, so four units of light were compared against one and `√4/√2 = 1.414` was recovered to four significant figures across three stacks that should all have perturbed it. **Facts 240-243, discipline 150, question 55** |
| `M32-posterior-confidence-measured.md` | **R2's confidence limb: posterior entropy is NOT the confidence output, and the frame choice was never the uncertain part.** A posterior over frame-of-best-focus needs a temperature, and that choice *is* the choice discipline 120 is about — the noise sd from the M4 model (external) versus `std_k(f_k)` (self-normalised). **The self-normalised arm fails with a number: across a 6.1× range of focus evidence it reports 0.6480 → 0.6482** (0.03%), non-monotonically, and under a 16× SNR degradation it moves 9% while the calibrated arm moves **22 orders of magnitude**. **The calibrated arm does not fail — it is degenerate:** the through-focus peak stands at **142–991 σ** above its own curve, so a calibrated posterior is a **delta function** on real data (perplexity 1.0000, rising only to 1.206 after 16× degradation, against a no-information null of 33.97). That σ was re-estimated model-free from the curve's along-`k` roughness and agreed to **1.24×** in the conservative direction, so the conclusion survives the noise model being wrong by two orders of magnitude. **Consequence: the defect in selection is not a noise problem** — a 142 σ peak is not SNR-limited, so M2's argmax defect and M27's under-resolved pixels are **sampling and model failures**, and confidence must be built from the merged estimate's predicted σ, the acceptance-set width and the sub-frame peak offset. **This also explains M20 from the other side:** when one frame stands 10²–10³ σ above the rest the minimum-variance estimator *is* nearly a selector. Two of the milestone's own pre-registered predictions died to its own controls — the no-information fixed point is **0.874, not 1.0** (the statistic is built from a maximum), and the "information-free" population carried 119 σ of evidence because its threshold was computed on frame-averaged data. **Facts 260-264, discipline 170, question 65** |
| `M33-subframe-offset-measured.md` | **Settles `B` §4.4's UNVERIFIED marker (parabolic vs Gaussian sub-frame interpolation) and answers question 65's candidate (c).** Ground truth is the full 105-frame `coffee-bean` grid against its ×2 decimation, adequate by **3.87×** and no more. **At operational sampling 48.7% of pixels miss their focus peak and give up a median 4.64% of their response (10.74% p90, 17.34% p99)** — nothing at the median, a great deal in a large minority, which is exactly what a per-pixel confidence map is for. **The finding that generalises: three-point parabolic interpolation gives a peak HEIGHT estimate anti-correlated with what it reports** — on a synthetic Gaussian its predicted deficit falls **21×** while the truth rises **8×**, because the relative deficit depends only on the scale-free *shape* of three samples. Discipline 120's failure mode in a third guise, inside the most standard piece of sub-pixel machinery in the field. **The log-domain fit with baseline subtraction is the fix** (exact on a Gaussian; calibration 0.710 / 51.2% within 2× on real data at ×2, against the parabola's 0.457 / 37.5%), and its placebo confirms it is not universally better — on a genuine parabola the parabola fit is exact and the log fit is 3.02× wrong. **Scope that keeps it honest: the failure is specific to peak HEIGHT.** For peak POSITION the parabola is fine at operational density (4.03× over the trivial argmax, only 9.4% worse than the log fit) — position is set by first-order asymmetry, height by curvature extrapolated beyond the samples, which is purely the assumed functional form. **Facts 270-274, discipline 180-181, question 70** |
| `M34-confidence-vector-measured.md` | **Decides M18's output contract: confidence is a VECTOR, not a number.** The three real-valued channels (predicted σ, posterior `n_eff`, sub-frame deficit) flag almost disjoint pixel sets — union **14.278%** against a **15.0%** perfectly-disjoint ceiling, **95.19% of the way there** — while every pairwise overlap sits at **0.53×–1.35× of chance** and the label-shuffle null returns **0.0256** against an analytic **0.0256**. **The decisive argument is not orthogonality but ANTI-correlation:** predicted σ has a worst-5% lift of **0.89×** on the true sub-frame deficit — the pixels it calls worst have *less* true deficit than average, because photon-starved pixels have flat through-focus curves — so **no monotone scalar summary of these channels is faithful**. Controls: each channel is **70–76% self-reproducible** under an independent noise re-realisation (three orthogonal *noise* sources would have produced the same table); a random channel scores **+0.0014** against truth; C4's degenerate row is a free second null. Specificity against M33's dense grid: deficit **+0.5560**, perplexity **+0.3349**, σ **−0.0726**. **The honest "do not trust" mask is the union — 14.3% of pixels, 3× what any single channel reports.** Qualifies fact 261 (per-pixel perplexity is a delta for only 76.5%, p99 4.74, max 39.05 — the tail is where confidence lives). Three of eight pre-registered predictions falsified. **Facts 280-284, discipline 190-191, question 75** |
| `M35-fit-generality-measured.md` | **Tests M33's fit on a marked-aperture ladder (119MSDCF f/5.6, coffee-bean f/8, 112MSDCF f/11 — coffee-bean recomputed, not quoted) and audits M33's own design.** **Question 70 comes back unanswerable: M33's adequacy gate fires on two of three stacks** (headroom 2.18× and 2.10× against coffee-bean's 3.62×), so those dense grids measure themselves rather than the estimator; `captures-needed.md` §7 now requires **2.5× the normal frame count**. **The deficit ladder's log–log slope is a cheaper second adequacy diagnostic** — 1.818 when adequate, 1.09–1.13 when not, because a sub-quadratic slope means the reference already misses peaks. **What survives the failed gate is the ratio between estimators**, since a multiplicative error in a shared reference cancels: the log fit wins on all three stacks (2.05× / 1.53× / 1.79×) across a 2× aperture and 10× ISO range. **Two audit results on M33: its numbers reproduce EXACTLY from independent code (0.457 / 0.710 / 51.2%), and its design had a real confound** — it scored a raw parabola against a baseline-subtracted log fit and never ran `parabola-baseline`. The missing cell prices it at **9% baseline / 91% log domain** (3% / 97% at ×4), so **fact 272 survives and is better supported**. Four of six predictions falsified; two of them uninformative because they read off the failed stacks. **Facts 300-304, discipline 210-211, question 85** |
| `M38-merge-on-real-frames-measured.md` | **The merge meets photographs, and its acceptance metric turns out to be broken.** Invariant 1 passes: flat-ROI noise **0.890× at gate 2.0** against argmax's 1.253×, two ROIs agreeing to 0.6% at every gate, six-gate sweep in 2.9 s. **Gate 0 reproduces M2-verification's independently measured 1.075× to 0.1%**, which validates the whole pass-one chain end to end. **Invariant 2 was measuring noise, not sharpness**: mean \|∇\| falls when a merge blurs *and* when it denoises, so the uncorrected reading showed a −45% "detail collapse" that is **−4.6% once the calibrated model's noise contribution is subtracted** — ~90% of the apparent loss was the merge being charged for its own purpose, and **fact 24 carries the same confound reversed**. **Fact 24's convention was identified by enumeration** as `mean(0.5(\|dx\|+\|dy\|))` to 0.01%; the reasoned π/2 guess died on a 1.43×-anisotropic ROI, and there is **no constant conversion** between the harnesses. **The gate does not transfer**: at a fixed threshold `n_eff` spans 2.26–7.42 across five stacks, `n_eff/N` clusters at 0.068–0.079, and hitting fact 212's target of 3 needs thresholds from 1.1 to 2.9 — so the free parameter must be **the target `n_eff`, not the gate**. **Facts 320-324, discipline 230-231, question 95** |
| `M18-merge-implemented.md` | **The sufficient-statistics seam (review item 6), decided: two-pass, 60 B/px constant in frame count.** The gather is proved non-perturbing by **byte-identical SHA256**. Also the model for discipline 254: it checked its own brief against the tree and found three of four items stale. |
| `crates/strehl-core/src/merge.rs` | **The estimation merge — the project's thesis in code, and the primary build artifact.** Two-pass: pass one folds each frame's 17×17-regularised focus field into a winner map (fact 84's −35%), pass two admits every frame within the gate of the winner and averages them in native raw DN (fact 19's 0.534×, fact 23's "only averaging goes below one frame"). Both passes commutative and associative, pinned by test. **"Never noisier than one frame" was asserted here and is FALSE** — it was structural reasoning (the winner is admitted unconditionally, so `n_eff ≥ 1`, so averaging can only help), and it survived four days because `predicted_sigma` was blind in exactly the place it could be violated. At `n = 1` the merge is *selecting*, and selection measurably costs **1.074×**. Fixed in `253e56f`: `SELECTION_INFLATION` prices it, and the test is now a two-branch contract that asserts **both branches actually occur**. Facts 428-431, question 101. `FOCUS_NOISE_SD` is measured in-crate at `0.015214 ± 0.000075`, and getting that number right required fixing a test LCG whose lattice aliased against the box filters (1.30× across seeds), a chosen tolerance no honest measurement could meet, and a plane too small to escape the finite-region SD bias. **That constant belongs to the operator, not the host** — the gate tolerance is `t·√2·FOCUS_NOISE_SD`, so a plugged-in operator that inherits it silently rescales the gate (M43, facts 436-438). **The gate threshold is deliberately unmeasured and explicit at the API boundary** — fact 212's `nwide = 3` is its target, and **M38 measured that no fixed threshold hits it across stacks** (fact 324). Facts 310-314, discipline 220-221, question 90 |
| `crates/strehl-cli/src/merge_cmd.rs` | **The merge on real frames** — the additive `strehl merge` subcommand. Two decode passes (pass two recomputes rather than caching, keeping memory `O(workers)`), the whole gate sweep in **one invocation** because decode dominates and folding one frame into N accumulators is nearly free, and both passes share `Ctx::field_for` so the gate compares against a field produced by the arithmetic that elected the winner. `run()` in `stack.rs` is untouched. **`detail_metrics()` is the part to read**: the noise-corrected detail invariant, `sqrt(raw² − model²)`, and the doc block explaining why the absolute gradient could not be corrected in place. Facts 320-324 |
| `A-prior-corpus.md` | The prior attempt, filtered; includes retractions |
| `B-algorithms-sota.md` | Algorithmic state of the art per stage |
| `C-landscape.md` | Competitors, licensing, artifact taxonomy |
| `D-rust-and-hardware.md` | Crates, versions, hardware envelope |
| `E-plugin-architecture.md` | Plugin design space and Rust API. **§F5 is a measured amendment (M43) and the part to read before building any of it**: the merge gate is denominated in a constant the *focus operator* owns, `Caps` has no field for it, and **all four of §F4's property tests pass a plugin that gets it wrong** — confluence, sensitivity, residue and the calibrated fixture, because a wrong noise SD does not move the peak. §F5.3 concludes the host should **measure** the plugin at load rather than ask it, which makes the fault unrepresentable and `--gate` dimensionless. §F5.4 upgrades §F4.5 to two calibration targets. Facts 436-439, 500-503. |
| `F-camera-lens-optics.md` | Optics of the reference rig; DoF tables |
| `G-edof-deconvolution.md` | **The microscopy/EDOF literature the review said was never surveyed (M19).** Settles novelty: the multi-frame focal-stack Wiener estimator is **Levin et al. 2009, Appendix B, Eq. (52)**, and they conclude against it. "First to model the occlusion halo" is **FALSE** (28 years of prior art). Do not build iterative deconvolution. |
| `M40-VERIFICATION.md` | **The orchestrator's `SELECTION_INFLATION = 1.074` repair does not stand, and every defect was a CHOICE (rule 24 again).** The arithmetic reproduced to four decimals; the reasoning did not. **The constant multiplies a SPATIAL sd ratio into a TEMPORAL sigma** — undefined regardless of value (fact 440). It **exceeds its own ceiling**: a pure-noise plant built to maximise the winner's curse caps the operator at **1.045x** (fact 446). It is **not a constant** — the same estimator reads 1.0001x…1.2732x over six ROIs (fact 443) — and a fixed-frame arm with no selection at all reproduces the worst reading to 0.0001 (fact 444). The n>1 branch is **wrong at every n**: the decay is smooth 1.0770→1.0220, not a step (fact 448). **On a genuinely detail-free plant the correction crosses zero and lands FURTHER from truth than the defect it replaced** (−11.63 DN where truth is 0), hidden by the shipped `max(0,.)` (fact 454). And **fact 341's premise is false**: the "flat" ROI spans 3.5× in per-frame detail and its modal winner carries 1.267× the reference frame's detail unmerged (fact 455). Also found a **fourth consumer** nobody enumerated (`merge_cmd.rs:912`), which still prints the unrepaired 1.0000x and is Jensen-wrong by 2.4–5.9% (facts 452-453). **Recommendation: revert to 1.0** — shipping 1.074 is worse than shipping nothing. Keeps the two-branch *shape* (fact 458). Facts 440-459, disciplines 263-267, questions 106-110; re-rules 428-431 and re-opens 341. | M40 (independent) |
| `M42-window-ladder-measured.md` | **The window optimum belongs to the operator, and M17's operator does not want 13.** Re-ran M13/M15's ladder for `tenengrad-sq`: pooled argmin moves **w13 → w11**, and **0 of 6** independent subsets choose 13 (against **6/6 → w13** for the shipped magnitude operator). 13 survives the pre-registered 0.87 DN basin by **0.0096 DN — 1.1% of the tolerance** — a real pass, and the weakest available. Re-radiusing is **free**: `box_mean` is O(1) in radius, w11 and w13 both 3.226 ms/frame/Mpx. Falsified its own prediction 3: the blind-spot cure is **radius-invariant** (D = 0.1860 from w8 to w40) because squaring breaks TV conservation itself. **New open limitation: on a width-9 smooth ramp `tenengrad-sq` reads D = 0.6802 vs 1.0000 — fact 73's blind spot is closed on steps and only half-cured on gradients**, which is the common macro case. **Read the orchestrator addendum at the top before acting on the recommendation: the edit is a TRIPLE** — operator, radius *and* `FOCUS_NOISE_SD`, which moves **1.528×** and would silently turn `--gate 1.0` into 0.654 (facts 509-511). Facts 480-491, disciplines 258-261, questions 103-105. Answers Q1. | M17 (re-task) |
| `M45-plugin-crate-implemented.md` | **The plugin seam is built, and it closes the §F4.6 fault-5 hole by construction rather than by test.** `crates/strehl-plugin` (~3 400 lines, 33 tests): `FocusMeasure` **deliberately has no noise-SD method** and `Calibration` has **no public constructor**, so a contributed operator has nowhere to put a wrong constant — the host measures it at load. The calibrator reproduces `FOCUS_NOISE_SD` to **−0.018%** and `FINE_FOCUS_NOISE_SD` to **−0.000%**, an order of magnitude tighter than the Python reference, and reproduces all seven fact-439 `k` values to **±0.43%** — an independent second-language confirmation of M43, SML at 6.6833 vs 6.680. **It also refuted three things in §F5.3's own published sketch, one structurally:** the sketch's `calibrate()` is *unseeded*, measuring **5.56% spread** across planes, so the fix for fault 5 as designed would have violated §F4's confluence property; the margin omits the host regulariser (bias +0.31% and operator-dependent, so it does not cancel in `k`); and fact 505's 1.7 ms cost bound is **2.95× low per plane, 35× low per registration**. §F5.5's proposed byte-identical test **would have gone red**. **Read §6.2 regardless of what you are doing here** — its first positive control divided both the field *and* the tolerance by the same wrong constant, which is the identical comparison, measured 0 flips in both arms, and would have let a `rate < 1e-4` assertion pass green with zero power. Facts 520-529, disciplines 284-286, questions 123-125. **Nothing is wired into `merge.rs`** — that is one multiplication, owned by whoever holds that file. |
| `M43-plugin-calibration-seam.md` | **The pluggability requirement has a measured hole, and the existing design cannot see it.** The gate is calibrated in units of a constant owned by the *focus operator*, and workstream E has no slot for it. A contributed operator that inherits the host's constant silently rescales the gate: measured, one such mistake reverts **87.76% of pixels to pure selection** while the log still reads `gate 1.00`. Capability negotiation, confluence and the §F4.3 sensitivity test all pass it — **a missing contract, not a missing test**. §8 surveys seven textbook operators and finds `k` spanning **10.4×**, worst case **6.68** at the sum-modified-Laplacian — the canonical SFF operator, i.e. the likeliest contribution there is — which makes the load-time refusal mandatory. **§8 also corrects §2's own `k`**: it had divided a regularised SD by an unregularised one, and a two-target calibration caught it. Facts 436-439, 500-501, disciplines 256-257, question 102. |

Claims inherited from `C:\dev\macro` are suspect by default. Several were
retracted under scrutiny — including a headline noise finding that measured
*spatial* sigma while labelling it *temporal*, and three fabricated citations.
`A-prior-corpus.md` records which survived.

**Reusing an experiment harness?** `experiments/m11-focus-bakeoff/run-m11.ps1`
does **not** list the ROIs that appear in M11's committed CSVs. Take ROIs from
`data/noise-*.csv` and `data/planted-*.csv`, not from the script, or the numbers
will not reproduce. **The discriminator is PER STACK, not global** (fact 88): on
109MSDCF a flat ROI has `single_sigma` ~28-30 DN and a detail ROI ~630-700 DN,
but on 119MSDCF all four *correct* flat ROIs sit at **43.2-53.1 DN** — applying
109's band to 119 rejects every one of them. Separate the two populations within
a stack; never carry a threshold across stacks. More generally, **reproduce one
published number from the original data before extending anyone's experiment** —
and stratify on every column the original stratified on. Better still, re-run
the original harness unmodified first: it is deterministic, so a published
command line should reproduce that milestone's committed CSVs **byte for byte**
(M15 §0.2 did, on both stacks). If it does not, stop — nothing downstream is a
valid comparison. Byte-identity is a *consistency* check, not independent
evidence (discipline 20).

## Build

```
cargo build --release
cargo test
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

## Reference rig

Sony A7C II (`ILCE-7CM2`) + Sony FE 100mm F2.8 Macro GM OSS (`SEL100M28GM`).
Pixel pitch 5.12 um. RGGB. Black level 512, white level 15360, active area
7032x4688. Confirmed by measurement, not by documentation.

**v1 targets in-camera focus bracketing only** — camera fixed, focus moves, so
frames differ by magnification and occlusion never changes.

Focus rails translate the camera, producing genuine parallax and occlusion. Rail
support is **deferred**: no rail hardware is available to test against, and an
untested geometry model would violate rule 8. The `CaptureMode` enum and mode
detection stay in place because that is the one seam the rail case genuinely
needs. Never silently apply the breathing model to rail data — detect from EXIF
plus fitted residual signature, and warn. Never trust a user flag alone.
