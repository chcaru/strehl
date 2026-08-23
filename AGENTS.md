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
5. **Fit geometry at runtime; do not bake it.** Scale drift and the scale
   centre are per-stack quantities. Only sensor calibration belongs in a
   profile, and profiles live in data files.
6. **Never chain alignments, and never rely on a single fixed reference on a
   deep stack.** Both halves are measured, and the *reason* chaining fails is
   not the one originally assumed.

   Chaining is not merely noisy. **Short-baseline edges under-report
   magnification change by ~3.2-3.5x** — on `coffee-bean` the span-1 telescoping
   ladder totals −1.6876% against span-16's −5.8891%, with a monotone ramp
   between them (2.19x on 119MSDCF, 1.43x on 109MSDCF). Any span must telescope
   to the same total, so the gap is pure bias. It is **coherent**, so composing
   104 edges yields **40.3 plane px** of corner error with **36.4 px in scale
   alone**. The cause needs a real inter-frame content change and lives below
   ~0.5 px of differential displacement: a resampler-free control recovers a
   planted increment at ratio 1.00, the same increment on a real defocus pair
   recovers at 0.56. **Short baselines look best by tile residual while being
   worst by truth — never judge an edge by its residual.**

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

   6.76 px is not good enough for a final render. Treat deep-stack alignment as
   **usable, not solved** (SYNTHESIS risk 11). See
   `docs/research/M10-deep-alignment-measured.md` and
   `docs/research/M3-alignment-measured.md`.
7. **Never compute statistics over the full decoded buffer.** `rawler` returns
   7168x5120 for the A7C II but fills only the 7032x4688 active area. The rest
   is synthetic zeros, not black level.
8. **Every performance or quality claim needs a command that was run.** Label
   claims MEASURED / VERIFIED / DERIVED / ARGUED / UNVERIFIED.
9. **Pair every sharpness metric with a flat-ROI control.** A sharpening pass
   raises gradient energy on featureless foam; that is how the prior project
   fooled itself.
10. **Never compare a spatial sd to a temporal sigma.** They are different
    physical quantities. A spatial sd over an image region carries scene
    structure; a temporal sigma across frames does not. High-pass first, or
    compare like with like. This error has now caused **two** retractions —
    the prior corpus's 1.10x correlated-noise claim, and M2's "unexplained"
    1.46x model gap, which was 1.01x once matched properly.
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
13. **kebab-case** for directories and files. Crates are `strehl-*`.

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
| `M11-focus-bakeoff-measured.md` | **What to select with, and what selection costs.** A 47-operator pre-registered bake-off on two real stacks, scored on a measured Pareto front of selectivity against noise excess. **The shipped `ring(1,3)` ranks 26-27th of 36** (N = 1.3475x, ~45% of the best selectivity); the recommendation is **Tenengrad under an 11x11 box window** (N = 1.1324x) — re-tuning the ring cannot close the gap. Headline: **no operator anywhere on the front is noise-free** (0 of 36 reach N ≤ 1.02x), so operator choice alone cannot rescue a selector. Zero-centre-tap operators *are* noise-free (φ = 0.0000, Ncorr 0.989-0.997) but recover only 34-40% of a planted focus surface. **Windowing and normalisation each re-introduce a centre tap, additively** — so φ must be probed on the whole configured stage, not the kernel. Closes risk 2; facts 37-42 |
| `A-prior-corpus.md` | The prior attempt, filtered; includes retractions |
| `B-algorithms-sota.md` | Algorithmic state of the art per stage |
| `C-landscape.md` | Competitors, licensing, artifact taxonomy |
| `D-rust-and-hardware.md` | Crates, versions, hardware envelope |
| `E-plugin-architecture.md` | Plugin design space and Rust API |
| `F-camera-lens-optics.md` | Optics of the reference rig; DoF tables |

Claims inherited from `C:\dev\macro` are suspect by default. Several were
retracted under scrutiny — including a headline noise finding that measured
*spatial* sigma while labelling it *temporal*, and three fabricated citations.
`A-prior-corpus.md` records which survived.

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
