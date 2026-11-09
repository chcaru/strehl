# strehl — architecture

**What this document is.** A structural description of the system: the crates, the
pipeline, the two merge backends, the physical models, the extension seams, and the
systems design. It is the *how it is built and why* companion to `README.md`, which
covers *what it does and how well it performs*. Where the two disagree, the code wins
and both documents are wrong until fixed.

**Scope note.** Every mechanism below is labelled with where it actually runs:

| Label | Meaning |
| --- | --- |
| **DEFAULT** | Runs on `strehl stack <dir> --out x.tif` with no flags |
| **ESTIMATOR-ONLY** | Runs only under `--merge estimator` |
| **OPT-IN** | Reachable on the default path, off unless switched on |
| **BUILT-NOT-WIRED** | Compiled and tested, no call site on any user-reachable path |
| **REFUSED** | The CLI rejects the flag on that backend rather than ignoring it |

This labelling is the single most important thing in the document. The project's
research corpus describes a great deal of machinery that the shipping default does not
execute, and reading the module documentation without this distinction will give you a
picture of a system that does not run.

---

## 1. The thesis, and its honest qualification

### The claim

Conventional focus stackers are **selectors**. For each output pixel (or each band
coefficient) they decide which input frame is sharpest and copy it. Selection is
statistically expensive: choosing the maximum of N noisy measurements returns the noise
of a single frame *plus* a positive bias, so a stack of 300 frames can be noisier than
one frame of the same scene. The field's familiar defect catalogue — halos at occlusion
boundaries, speckle in defocused ground, rim artefacts — follows from selection.

strehl's thesis is that stacking is an **estimation** problem. Select only where the
difference between frames genuinely exceeds the calibrated noise floor; average
everywhere else. Where a frame is unambiguously sharpest, the estimator degenerates to a
selector; where no frame stands clear, it becomes a mean.

### Where the claim is literally implemented

In `merge.rs`, on `--merge estimator`. Elect a winner, admit every frame within
`threshold × √2 × σ_response` of it, average the admitted set. Pinned by
`with_frames_that_agree_the_estimator_averages_them` (`merge.rs:3430`),
`with_one_frame_clearly_sharpest_the_estimator_degenerates_to_a_selector`
(`merge.rs:3411`), and `averaging_beats_one_frame_and_selection_does_not`
(`merge.rs:3545`).

### Where the shipping default actually stands

The default is `--merge pyramid` (`merge_cmd.rs:429`), a per-band-coefficient soft-power
**selector** with a noise gate. The thesis survives there in a weaker, per-coefficient
form: the floor is `gate × beta × var` per band, a coefficient failing it gets weight
exactly zero, and where *no* frame clears the floor the coefficient falls back to a plain
mean across frames (`pyramid.rs:2641`, `pyramid.rs:2223-2233`; tests
`pure_noise_is_averaged_not_selected` `pyramid.rs:3368` and
`the_averaged_fraction_reports_where_the_gate_refused` `pyramid.rs:3627`).

But above that floor the default exponent ladder runs at 8.0 in every band but the two
coarsest (7.683 / 8.0 / 8.0 in the three finest before the coarse exponent moved to 4), which the module itself calls "already close to winner-take-all — a frame
with twice another's band energy gets 256 times the weight" (`pyramid.rs:1241-1242`).

And the project's own instrumentation measures selection concentration **higher in flat
regions than in detail regions at every band** on `coffee-bubbles` — 1.0000 vs 0.8214 at
band 0, 0.7837 vs 0.2989 at band 2 where a plain mean would read 0.0526. The module
comment names this exactly: *"That is a merge selecting on noise"* (`pyramid.rs:1136-1147`).
The fix is built (`STREHL_PYRAMID_SIGNIFICANCE`) and ships **off**, because at derived
strength it does not collapse the inversion — band 1's gap narrows 0.0657 → 0.0338 and
bands 2–6 move under 0.2% (`pyramid.rs:1150-1190`).

**Since 2026-11-02 the default runs the ensemble gate** (`MergeConfig::ensemble`,
`STREHL_PYRAMID_ENSEMBLE=0` disables), which addresses that inversion at its source: the
per-frame gate is a multiple-comparisons test that some noise frame passes at almost
every flat coefficient. A coefficient now selects only where the stack as a whole shows
signal (one frame dominating the rest, detail adding coherently across frames, or
structure in every frame); elsewhere it is the plain mean of all frames. Thresholds are
percentiles of a null measured from the floor probe's noise frames through each frame's
own warp. Measured: flat-region noise power 0.03–0.05x of the old default on deep
stacks, lower error against truth in 176 of 180 synthetic cells and on a held-out
fixed-focus burst; see `experiments/image-quality-2026-11-02/results.md`.

**So: the thesis is implemented and demonstrated on a backend that is not the default,
and holds in a diluted form on the backend that is.** That is the central architectural
fact about this system, and no other document in the repository states it plainly.

---

## 2. Crate topology

Four crates own the processing pipeline. A fifth, `strehl-ui`, provides the native
desktop workspace and runs the CLI as an owned background process.

| Crate | Owns | Notes |
| --- | --- | --- |
| `strehl-raw` | RAW decode, sensor geometry, camera identity | Wraps `rawler` (LGPL-2.1, **linked, never read** — `strehl-raw/src/lib.rs:3-5`) |
| `strehl-core` | Every algorithm and physical model | No `rayon` dependency at all — it is a library of kernels, not a scheduler |
| `strehl-plugin` | The focus-measure extension surface | Registry, host calibration, seven reference operators, deterministic RNG |
| `strehl-cli` | The binary, all orchestration, all parallelism, all I/O | Owns the pipeline; `strehl-core` owns the mathematics |
| `strehl-ui` | Desktop interface, source inventory, developed-image preview, job lifecycle | Rust egui/wgpu shell; RAW processing remains in the CLI |

The parallelism boundary is deliberate. `strehl-core::demosaic::demosaic_row` is
row-at-a-time specifically so the CLI can choose how to parallelise it
(`demosaic.rs:334-337`). Grepping `par_iter|par_chunks` in `strehl-core/src` matches only
two doc comments.

---

## 3. The three invariants

These are `AGENTS.md` rules 1–3, and they explain most of the structure that follows.

**1. Storage is `u16` CFA. Arithmetic is `f32`.** Never `f16` — a 10-bit mantissa gives
~8 LSB steps on linear 14-bit data. `Frame::data: Vec<u16>` (`strehl-raw/src/lib.rs:75`);
promotion happens at use, e.g. `(f32::from(...) - black).max(0.0)` in the deinterleave
(`merge_cmd.rs:4780`).

**2. Never materialise an aligned-frame volume.** Keep geometry in a sidecar and
consume one source at a time. The current full-resolution consumer nevertheless
uses per-source RGB reconstruction and an aligned CFA scratch buffer; avoiding
a retained frame volume does not mean it avoids those reconstruction stages.
Direct original-CFA reconstruction with only a final demosaic remains the
required architecture, rather than a property established by bounded storage.

**3. The noise model is injected, never re-derived per stage.** A private per-stage noise
estimate is the exact mechanism behind the prior project's 2–5× defect. The model is
constructed once, in `profile.rs`, and passed by value.

> Rule 3's enforcement is **by convention and single-constructor discipline, not by the
> compiler** — `PlaneNoise`'s fields are `pub` (`noise.rs:86-93`) and no test forbids a
> stage from building its own. And the rule has a second half that is **unimplemented**:
> there is no runtime noise estimator, so nothing cross-checks a profiled body against
> what its own frames actually show. The shipped coefficients are a consistency check
> against the camera's own white level, not a photon-transfer measurement.

---

## 4. The pipeline — default path, stage by stage

`Command::Stack` → `merge_cmd::run` → `run_pyramid` (`merge_cmd.rs:5331`).
(`stack.rs` is *not* on this path; it is the `argmax-baseline` negative control.)

### Once, before any frame is folded

1. **CA profile preflight** — the optical profile key is validated up front so a typo
   fails before an hour of work (`merge_cmd.rs:5335`).
2. **Exposure resolution** — refuses `--exposure` without `--srgb` (`merge_cmd.rs:5337-5355`).
3. **File list** — `*.arw` only, **sorted by filename = capture order** (`main.rs:1195-1207`).
4. **Prologue decode of frame 0** for geometry, levels, camera, ISO, white balance and
   `xyz_to_cam`; then dropped (`merge_cmd.rs:5366-5375`).
5. **Noise model built once and injected** — `profile::noise_model_for(&camera, iso, levels)`
   (`merge_cmd.rs:5377`). This is rule 3's single construction point.
6. **Defect preflight** (`merge_cmd.rs:5397-5404`).
7. **Alignment** — `align_cmd::load_or_solve` reads or computes the warp sidecar
   (`merge_cmd.rs:5481`), then a crop/scale fit that must `cover_or_explain`.
8. **Memory plan** — worker count and chunking (`merge_cmd.rs:5538-5551`).

### Per frame, inside `BandWorker::fold`

9. **Decode** (`merge_cmd.rs:4708`) and a levels-consistency check.
10. **Sensor defect correction — BEFORE the warp** (`apply_defects`, `merge_cmd.rs:4741-4743`). The defect
    map is indexed by photosite and cannot address a resampled buffer; focus breathing
    moves a defect up to 232.7 plane px corner-to-corner. Pinned by a planted control test,
    `dust_correction_must_precede_the_warp_to_land_on_the_defect` (`defect_map.rs:23-25`).
11. **Warp** — `warp_frame_in_place` if the frame was Placed. A **Refused** frame is
    *dropped, never merged unregistered* (`merge_cmd.rs:4752-4776`).
12. **Per-frame measured band-noise floor** probe, warped frames only (`merge_cmd.rs:4760-4762`).
13. **Black subtraction and CFA deinterleave into four half-res planes** (`merge_cmd.rs:4771-4783`).
14. **Green luma** `L = (G1 + G2)/2` (`merge_cmd.rs:4786-4792`).
15. **Fold** — `merge.add_frame_with_gain(...)`. The frame is dropped before the next is read.

### Once, on the merged result

16. Worker accumulators summed (`BandMerge::absorb`), then `finish` collapses to four planes.
17. Optional confidence map second pass.
18. **Write** (`write_merged`, `merge_cmd.rs:6906`): crop by addressing, colour matrix if
    requested, exposure statistic, optional Wiener restore, then one of three mutually
    exclusive output branches.

**Final development demosaics the merged planes for each requested RGB output,
but this is not the total demosaic count of the default aligned path.** The default full-resolution gather
(`STREHL_FULLRES_GATHER=1`) first reconstructs each source with MHC, samples its
RGB channels with the selected resampler, and rounds/clips the result back into
u16 CFA storage before plane extraction and merging. `native-direct-planes`
changes that destination storage/precision; it does not remove the per-source
color reconstruction. Binned measurement output omits the final demosaic, not
the upstream reconstruction.

Thus the current default is CFA-domain fusion after per-source reconstruction,
not direct fusion of original CFA samples with one final demosaic. Keeping the
originals as u16 and arithmetic as f32 does not establish the stronger contract.
The experimental original-CFA sampler is a distinct, quality-rejected arm and
is not active here. See the [independent source trace and prior boundaries](../experiments/raw-quality-2026-10-27/dual-tree-cfa-gpu/photographic-observation/native-contract-review.md).

### What the default path prints as NOT applied

`photometric gain, clip census, outlier rejection, halo correction, through-focus
statistics` (`merge_cmd.rs:5468-5472`). All exist in the tree. All are estimator-path
stages.

---

## 5. The fork in the road — two merge backends

Selected by `--merge` or `STREHL_MERGE`; the flag wins; an unrecognised value is an error
in either channel. If `--merge` is absent the backend is **inferred from the flags given**
and the inference is printed (`main.rs:1044-1072`).

A flag belonging to the other backend is **refused, not ignored** — because a flag that
parses, prints nothing and does nothing is indistinguishable at the terminal from one
that worked. **Ten** flags are refused under `Pyramid`:

`--gate`, `--focus`, `--target-n-eff`, `--index-map`, `--n-eff-map`, `--photometric`,
`--stats`, `--stats-placebo`, `--flat-roi`, `--detail-roi` (`wrong_backend` table,
`main.rs:967-1022`; the ten pyramid rows are `968-999`).

**Seven** are refused under `Estimator`: `--pyramid-bands`, `--pyramid-gate`,
`--pyramid-exponent`, `--pyramid-sharpen`, `--pyramid-select`, `--pyramid-base`,
`--confidence-map`.

> `README.md`, the `--help` prose and the refusal table now all say **ten**. They
> disagreed — nine, eight and ten respectively — and the self-check test at `main.rs:1609`
> could not catch it, because it couples the help text only to *its own* count and never
> to `wrong_backend`, which it cannot reach: that table is a local built from parsed
> arguments inside `run`. Two flags were added to the table, the help's list and the
> help's count both stayed at eight, the two agreed with each other, and the test stayed
> green. A coupling between two copies of a claim keeps them consistent; it cannot keep
> them true.

### 5a. The pyramid backend — DEFAULT

Laplacian decomposition with the Burt–Adelson binomial kernel `[1,4,6,4,1]/16`
(`pyramid.rs:79`); separable, non-negative, unit DC; borders replicate.

**`DEFAULT_BANDS = 7`** (`pyramid.rs:136`). Seven octaves take a 3516×2344 quad plane down
to 28×19. Stopping at 4–5 leaves a ~100 px band still being *selected* — and that is the
halo.

Per coefficient (`add_frame_with_gain`, `pyramid.rs:1614-1700`):

1. Build the luma Laplacian pyramid plus a **Gaussian pyramid of per-pixel noise variance**.
2. Square the band coefficients and `smooth5` them with the same binomial kernel at the
   same scale — an unsmoothed `|L|` is one noisy sample.
3. `floor = gate × beta × max(v,0)`; `excess = max(e − floor, 0)`;
   `w = select_weight(excess, floor, p, r_floor)`.

Accumulate `den += w`, `num += w·L`, `usum += L`; output `num/den` where `den > 0`, else
the unweighted fallback `usum/N`. **The weight is computed on green luma only and shared
across all four planes.**

**The scale-ramped exponent** (`exponent_at`, `pyramid.rs:1221-1236`) is the backend's
signature idea:

```
p(k) = min(exponent × sharpen_per_octave^(bands-1-k), MAX_EXPONENT)
```

Defaults `exponent = 4.0` (`DEFAULT_EXPONENT`), `sharpen_per_octave = 1.4`,
`MAX_EXPONENT = 8.0`. The ladder, coarsest → finest: **4.000, 5.600, 7.840, 8.000, 8.000,
8.000, 8.000**. Until 2026-11-03 the default was `exponent = 2.0` (ladder 2.000, 2.800, 3.920,
5.488, 7.683, 8.000, 8.000), chosen when coarse bands selected on their own focus-blind
energy. With pooled evidence they select on their finer bands' focus evidence, and the
sharper coarse selection measured better against truth and drew less glow
(`experiments/image-quality-2026-11-02/results.md` §1d). Session fusion keeps 2.0 with its
previous selection.

The ramp is geometric rather than linear because band power itself falls geometrically
with scale, so a fixed *ratio* per octave is the scale-free choice. The justification is
asymmetric risk: in a fine band a wrong pick is one high-frequency coefficient nobody can
see; in a coarse band a wrong pick **is** the rim. A depth boundary therefore becomes a
transition inside each band rather than a step in the image.

`MAX_EXPONENT = 8.0` is set by f32 representability, not taste — the overflow-safe bound
on `p·ln(r)` is 80, so beyond about `p = 10` the sharpest coefficients all pin and get
averaged. More selectivity is `SelectMode::HardMax`, not a bigger exponent.

**Since 2026-11-03 bands select on pooled focus evidence** (`MergeConfig::pooled_evidence`,
`STREHL_PYRAMID_POOLED_EVIDENCE=0` disables): each band's weight is computed from a weighted
mean of its own and every finer band's energy in noise units, the finer ones reduced onto its
grid and each counted `pooled_evidence_ratio` (default 2, `STREHL_PYRAMID_POOLED_RATIO`) times
its next coarser one, because a coarse band's own energy barely depends on focus and a defocused frame's spread
light kept or raised it beside bright and dark detail. The base band is now **weighted** by
the coarsest band's selection and inherits that band's ensemble blend. Together they removed
most of the glow around edges on a tilted calibration slide (+35% -> +14.5% dark-ground
excess over a locally in-focus composite) and lowered error against truth on every synthetic
cell; see `experiments/image-quality-2026-11-02/results.md` §1b. On scene-linear masters the
slide's remaining excess is gone. The ratio of 2 (§1e) roughly halved the glow still left within
8-16 px of very bright edges on bug-4. Session fusion (Best result)
can select with the same pooled evidence and weighted base, pinned coefficient for coefficient
to the ordinary merge by a parity test, but sessions keep the previous selection (mean base, no
pooling): session fusion has no ensemble gate yet, and without it the two select noise in flat
dark ground.

Other defaults: `BaseBand::WeightedFromCoarsest`, `SelectMode::SoftPower`,
`Hull::InputRange` — output clamped to the frames' hull, because per-band convexity does
not imply reconstruction convexity.

**Gate `2.0`** is in multiples of modelled band-noise **power**, justified by the
smoothing: the energy statistic is a mean of ~13 squared samples fluctuating ~39% of its
mean under pure noise, so 2.0 sits about 2.6 of its own SDs above the noise expectation.

Supporting constants, all derived rather than fitted:

- **`SNR_REF = 64.0`** — a pure reference point. Every weight at a level divides by the
  same constant, so the merge is mathematically unchanged by it; it exists only to centre
  `ln(r)` so the ±80 clamp never binds.
- **`NU_SMOOTH = 13.37469`** — effective degrees of freedom of the smoothed band-power
  estimate, derived from `KERNEL`: 1-D `Σa² = 70/256`, 2-D separable `= 0.07476807`,
  `ν = 1/0.07476807`. The independence assumption is the *conservative* end; measuring
  true ν would strengthen the effect, not reverse it.
- **`significance_floor(gate) = sigma_rel() / (gate × SNR_REF)`** = 0.0030211 at gate 2.0.

**The per-frame measured gate floor is DEFAULT**, opt-*out* via `STREHL_GATE_FLOOR=white`.
The older white-noise `beta[k]` describes an *unwarped* frame; measured
`beta_actual/beta_white` ran 0.3432–0.9981 over eight warps, every entry below 1.0, so the
bar sat at up to **3.7× the true noise power** (`merge_cmd/gatefloor.rs:1-17`).

### 5b. The estimator backend — ESTIMATOR-ONLY

**Two passes**, because the gate needs each frame's response *relative to the winner* and
the winner is unknown until all frames are seen. A one-pass fold would carry per-pixel
through-focus state growing with the acceptance set; two passes carry **O(1) state per
pixel**. Both passes are associative and order-independent, hence partitionable with an
exact `absorb`.

- **Pass one, `FocusStats`** — folds each frame's regularised focus field, keeping only
  `best_focus: Vec<f32>` and `best_index: Vec<u16>`. Regulariser is a 17×17 box
  (`REGULARISER_RADIUS = 8`).
- **Pass two, `Estimator`** — admit if `winner || gate.admits(...)`, accumulate
  `sum[s][i] += wt·v` and `n[i] += 1`.

**The gate:**

```
tolerance() = threshold × √2 × noise_sd
admits(focus, best) = (best − focus) <= tolerance
```

`√2` because it is a *difference* of two responses each carrying `noise_sd`.
`DEFAULT_GATE = 4.0`, i.e. 5.66σ. `FOCUS_NOISE_SD = 0.015214` is measured, and is a
property of the **operator**, not the merge. Non-finite responses are never admitted
because NaN comparisons are false.

Calibration ladder from a static burst (`merge.rs:430-435`): threshold 0 → n_eff 1.00/30
at 0.9768× noise; 2 → 18.4/30 at 3.776×; **4 → 29.5/30 at 5.4316×**; 8 → 30.0/30 at
5.4777×; ideal √30 = 5.4772.

Sufficient statistics per pixel: `best_focus`, `best_index`, `sum[4]`, `n`, optionally
`wsum`/`wsq`, `pmax[4]` plus Welford `vmean`/`vm2`/`vn`, and `luma_sum`/`luma_sumsq` in
**f64** — f64 because sumsq ≈ 2.4e10 against a variance ≈ 1e3 cancels about seven
significant figures. Memory is pinned by
`memory_is_bounded_and_independent_of_the_frame_count` (`merge.rs:4265`).

> **`SELECTION_INFLATION = 1.0` and both branches of `selection_inflation(n)` return 1.0.**
> The noise penalty for selecting is a *known missing term*. The previously shipped
> 1.074× was refuted on four independent grounds and fact 341 is open again.

#### The veil estimator — ESTIMATOR-ONLY

At an occlusion boundary a dark defocused foreground *veils* the bright backdrop.
Veiling is a **convex combination** between backdrop and occluder, so its direction is
set by which layer is brighter. Because darkening can only reduce a backdrop pixel, **the
largest sample a pixel ever took is its least-veiled one** — so the per-plane maximum
over frames estimates the unveiled value and is not an outlier.

Critically, `pmax` accumulates over **every** frame, above the gate's `continue`, because
at a veiled backdrop pixel the admitted set is exactly the frames where the foreground is
most defocused and spilling hardest.

One-sidedness is the safety property, enforced three ways: a polarity precondition that
sets `declined` and moves nothing if the scene is the wrong way round; a luminance floor
below which a pixel is subject rather than veiled backdrop; and an operator that can only
ever **raise** a value. The move is ramped, not switched. The failure that motivated the
luminance floor: on `bee-2-cpl` an unfloored correction cleaned the leg rim and punched
flat grey blotches through eye, thorax and wing.

Eligibility comes from `election_coherence.rs`: the local SD of the *elected frame index*
over a 9×9 window. Dead ground elects incoherently (argmax chasing noise); a real object
elects coherently. It never reads luminance, so brightness cannot fool the silhouette.
Thresholds must be **quantiles of this image's own distribution** — passing constants
reintroduces the defect it was built to fix.

---

## 6. The physical chain

### Noise model — the spine of the system

```
σ²(S) = g·S + (RN_e·g)²
```

`g = max(iso, base_iso)/gain_divisor` DN/e⁻. Provenance is a **runtime type**, not a
convention: `enum Provenance { Profile, Measured, Fallback }` with `is_trustworthy()`
= `!Fallback`.

Reference body (Sony A7C II): `gain_divisor 436.8`, `base_iso 100.0`,
`read_noise_e_low 4.20`, `read_noise_e_high 1.2392`, `second_base_iso 400.0`
(`profile.rs:367-376`). Exactly **one** body is profiled (`profile.rs:387`); an unknown
body degrades to `Provenance::Fallback` rather than erroring.

Black and white levels are deliberately **not** in the profile table — they are firmware
and compression dependent, and `profile.rs:14` says so explicitly. The 512/15360 pair
reaches the pipeline from the decoded file. Active area 7032×4688 is asserted at
`align.rs:2947`; the RGGB-only gate is at `strehl-raw/src/lib.rs:271`. The 5.12 µm pixel
pitch is recorded in `AGENTS.md` § *Reference rig* and appears **nowhere in the code** —
no stage consumes it.

A third, PRNU term is **measured but off**: κ = 0.3102% R / 0.3096% G / 0.2528% B. The
shipped model is consequently over-confident above S = 504 DN, by −12.8% at S = 8000.

### Lateral chromatic aberration — OPT-OUT, default-on for matching gear

Modelled as a per-channel radial magnification error ("scale minus one") plus an optional
uniform translation — a similarity, not a polynomial. `eps_r = −508.4e-6`,
`eps_b = +174.4e-6`. **Green never moves**: `eps(Green)` returns `None` and short-circuits
to a bit-identical return, asserted by test.

It is **folded into the alignment similarity so that only one interpolation happens** —
`OpticalProfile::compose`, live at `align_cmd.rs:1929` and `:2095`. That composition is
the whole reason CA correction is free.

Unsupported gear is a three-valued **refusal** (`Match` / `Unknown` / `Mismatch`), and a
typo'd `STREHL_FIX_CA` is an error, not silence. The direction is a pull, `s = 1 + eps`:
the inverted version shipped once and made the aberration 7.2% worse, where the corrected
direction removes 94.3%. Out-of-sample leave-one-out transfer is 93.7%/93.3%, taking
corner residual from 1.519 px to 0.071 px.

**Per-capture refinement — DEFAULT ON (`--refine-ca=off` / `STREHL_REFINE_CA=off` to skip; desktop: "Refine fringing per stack").** The constants
are right on average and wrong per capture: a channel's effective wavelength is weighted by
the scene's spectrum (SYNTHESIS fact 1570), so red's native scale measured −258 to −611 ppm
across seven captures, and red/blue carry a translation of up to 0.3 px the profile does not
apply. By default `stack` first merges a preview of every Nth frame (at least ~32
frames, at most every 8th), measures on its white-balanced **mosaic** — each colour
interpolated from its own sites only, because a demosaic that borrows green's detail
under-reads the displacement — the red and blue displacement against green as translation +
scale (`ca_refine.rs`: per 256 px tile, windowed cross-correlation of gradient magnitude
refined to 1/400 px, then a structure-weighted trimmed fit), installs it on top of the
profile (`optics::set_ca_refinement`, consumed by `compose`), and renders in full. About +18%
time; skipped automatically with no matching profile, `--fix-ca=off`, alignment off, or binned output, and the preview is silent on the desktop progress channel. Multi-pass sessions run their own preview through the session consumer (whose original-CFA gather leaves its own residual) and apply the result to every lighting group; aligned layers keep the profile alone. MEASURED: edge fringing on the neutral slide-2 7.34% → 2.97% (red), 5.37% → 2.11%
(blue); bug-4's red residual +250 → +10 ppm. With `--refine-ca=off` the output is pixel-identical to the profile-only render.
See `experiments/image-quality-2026-11-02/results.md` section 3c.

### Sensor defects — OPT-IN, off by default

Two defect classes with two different arithmetics: **hot** pixels are additive
(`S → S − c`, thermal, ISO and exposure dependent, 99.8% singletons); **dust** is
multiplicative (`S → S·g`, aperture dependent, discs of tens of quads). Dust matters
because it scales with signal — −1.8% is 72 DN on a 4000 DN midtone, 2.4× the shot noise.

Sidecar is plain text, magic `strehl-defect-map`, **`VERSION = 2`**. v2 exists because a
v1 map lacked a coordinate-space key, and reading the wrong array gave +54.8% / +22.2%
errors — a dust mote read as a bright spot. A v1 map is **refused**.

The **hot arm is a measured null on this body** (in-situ excess reaching a light frame is
1.5 DN) and ships off. Dust is not a null. A backend that cannot apply a configured map
**refuses to render** rather than silently dropping it.

### Photometric normalisation — ESTIMATOR-ONLY

Whole-frame flux moves **8.2%–36.9%** end to end across a bracket. Because the merge
elects different source frames in adjacent regions, a per-frame level difference becomes
a **brightness step at the election boundary**.

It fits **one gain scalar per frame, no offset**. The estimator is a conserved **flux
ratio** over a low-detail mask, not a patch median, because blur conserves flux: on
`bee-3-cpl` patch medians move 18.2% while flux moves 8.7%. The intercept (up to 491 DN)
is blur, not dark current, which is why no offset is fitted.

It correctly drags the noise model with it: scaling by `c` scales σ by `c`, not `√c`, so
`gain_dn_per_e *= c` while `read_noise_e` is unchanged. Failing to do this under-estimates
σ by up to a factor `c`, the gate fires too readily on brightened frames, and **noise wins
elections**.

> `DEFAULT_PHOTOMETRIC_MODE = On` is an **estimator-path** default. On the shipping
> pyramid backend photometric gain is printed as `not applied`, and `--photometric` is
> refused with the message "NOT YET IMPLEMENTED on this backend, rather than
> inapplicable" — fitting it needs every frame's flux before the first frame is folded,
> which a single-pass fold does not do.

### Demosaic, colour, highlights

**Malvar-He-Cutler is the default** (`demosaic.rs:337-342`); a directional arm is opt-in
and was measured and rejected on real captures; bilinear is a reference arm only. Border
rule is **mirror**, because reflection preserves CFA parity.

Colour targets sRGB/IEC 61966-2-1. The matrix is built **per file** from the decoder's
`xyz_to_cam` — there is no per-body colour constant in `color.rs` at all. Construction
normalises each row to sum 1 (which is precisely the statement "input is already white
balanced"), so neutral maps to neutral by construction.

Order (`color.rs:26-36`): raw DN → subtract black → **as-shot** WB gains → demosaic →
matrix → clamp → sRGB encode. Everything after the merge, in the writer — because the
noise model lives in native per-channel raw DN, and a gate that white-balances first
believes red is up to 2.86× quieter than it is.

Highlight handling is two cooperating pieces: `clip.rs` is a census of samples pinned at
the container maximum (`CONTAINER_MAX_DN = 16383`, deliberately *not* unified with the
model's white level of 15360), and `highlight.rs` handles the *approach* to the ceiling,
which the census cannot see because only 21.02% of ever-pinned sensels are pinned in every
frame. The roll-off is **luminance-preserving exactly**, because every row of
`camera_to_srgb` sums to 1 — pinned by test. Below the knee it is bit-exact identity.

### Wiener restore — OPT-IN

A single-image zero-phase Wiener filter where **H is the project's own Catmull-Rom gather
kernel**, known to machine precision, rather than a lens model. It exists because the
gather MTF is 0.940 at 0.25 cyc/sample and 0.625 at Nyquist — 18.6% of the merge's blur
variance.

The honest verdict is a negative: achievable gains are 1.096 and 1.298 on two test
subjects against an ideal of 1.60, and gain caps of 1.4, 1.7 and 2.5 produce
**byte-identical output** because the cap never binds — the calibrated noise stops it
first. There is no ringing "because it is too weak to ring."

> **`STREHL_RESTORE` is read on both backends** — the estimator path at
> `merge_cmd.rs:4452` and the default pyramid path at `merge_cmd.rs:5765` — so the label
> is OPT-IN, not unreachable. The file records how easily that is misread: an orchestrator
> set `STREHL_RESTORE=1`, saw byte-identical output, and concluded the stage was never
> wired in. `1` is the documented no-op, because the value *is* the gain cap.

---

## 7. Alignment and the warp sidecar

### The model

**Similarity only — four real parameters.** `p' = a·p + b` on plane coordinates relative
to the plane centre, `a` complex (uniform scale + rotation), `b` complex (translation).
No affine, no homography. Rail capture is explicitly out of scope: depth-dependent
parallax has no global 2D transform.

This is sufficient because v1 targets **in-camera focus bracketing** — the camera is
fixed, focus moves, so frames differ by magnification (focus breathing) and occlusion
never changes. Real drift reaches **299.2 plane px corner-to-corner** on a 299-frame
bracket, so this is not a small correction.

### The solver

Two separated halves. *Measure*: tiled zero-mean normalised cross-correlation with
parabolic sub-pixel refinement, a least-squares similarity fit to the tile displacement
field, and one MAD outlier pass. The coarse decimation ladder exists **only** to bring the
fine stage into capture range; all accuracy comes from the fine stage correlating the two
full planes directly.

*Solve*: `solve_global_in_component` - one weighted complex linear least squares over measured
edges simultaneously, via normal equations plus Hermitian Cholesky with iterative
refinement. Transforms are carried in **f64**, not f32.

No pair's fit is ever composed into another's. Chaining exists **only as a measurable
negative control**: `solve_hops` with `max_span = 1` is the forbidden adjacent chain,
"implemented here only so that the forbidden thing can be *measured* rather than
asserted — do not ship it." It scores 40.342 plane px held-out against the global solve's
6.758 px.

Normal alignment admits only the requested reference's measured connected component;
other frames remain `None` even when smoothing is on. The numerical gauge is the
smallest admitted original frame index, followed by an explicit rebase to the requested
reference. Smoothness rows use only complete adjacent triples in original frame order
inside that component; gaps are not compressed into new neighbors.

The legacy research `solve_global` API retains its historical frame-0 behavior:
smoothing can extrapolate outside measured reach. That is model extrapolation, and
reports using that API must say so. Ordinary maps declare the measured-component
policy in their strategy; cached old ordinary maps are recomputed, while explicitly
named old ordinary maps are refused without replacement.

### The sidecar

Alignment is a **calibration artefact kept as data**, like every other profile — the solve
costs ~55 s on a 299-frame stack and must not be repeated per merge.

Plain inspectable text, magic `strehl-warpmap`, `VERSION = 1`. Floats are stored
**hex-exact**; the decimal columns are a human aid and are *not parsed*. Written
write-then-rename atomically into a cache root keyed by a hash of the canonical directory
and solve config — **never into the capture directory** (a previous version left eleven
strays). Every failure mode is a refusal, never a degraded map; there are thirteen
distinct error variants.

Provenance carried: reference frame, strategy, **held-out** corner error, cycle floor,
frame count and stack digest. Held-out — not fit — because "a fit error on a global solve
is not a measure of anything a consumer cares about." Real held-out error spans **33×**
across stacks, 0.353 px to 11.562 px.

**Refusal is not identity.** `FrameWarp` has two states and there is deliberately **no**
accessor that turns a refusal into a transform. Consumers must drop the frame, and
`merge_cmd.rs:3562` does.

### One resampling pass, ever

The stored transform is applied at source consumption. The current default
full-resolution route reconstructs and gathers source RGB, then writes a
temporary aligned CFA buffer; the direct-plane option can omit that buffer.
Neither route retains an aligned-frame volume. Avoiding an extra registration
resample is distinct from avoiding the source reconstruction and final demosaic
described above; the present implementation does not satisfy the latter goal.

Kernel is Catmull-Rom (`a = −1/2`). Every stored `Similarity` is a **placement**
(reference coords → that frame's coords) and the resampler is a *pull*, so registering
requires **no inversion** — `gather_checked` exists so that direction is decided once
under test, because inverting it is "the single most likely bug, and it is silent"
(misregistration by twice the drift).

> **Stated caveat:** Catmull-Rom's superiority over bilinear is measured only on a
> zero-defocus self-pair, and this resampler, like bilinear, destroys most sub-pixel
> displacement — planted motion reads gain 0.29 against 0.98 interpolator-free. Never
> measured on a real merge.

---

## 8. Focus measurement and the plugin seam

### The operator

Tenengrad: `g = √(Gx² + Gy²)`, 3×3 Sobel scaled by 1/8, aggregated by a box mean of
**radius 13** (a 27×27 window), normalised pointwise by the injected noise model's luma
sigma. `SUPPORT_RADIUS = 14`.

Radius 13 is a **measurement, not a preference**. M11 was a pre-registered **47-operator**
bake-off scored on a Pareto front of selectivity against merged-noise excess; the
predecessor `ring(1,3)` placed 26–27th of 36 and is dominated on *both* axes. M13 chose
the radius: over 36 occluding-edge cells, radius 13 is the argmin of both mean regret
(3.171 DN) and worst-case regret (12.111 DN), stable across three noise seeds.

The scoping is stated honestly in the module: **0 of 36 operators reached N ≤ 1.02×**. No
operator is noise-free — "the escape from selection's noise penalty is estimation, not a
better selector."

### The occlusion halo, and the fix

At a background pixel within 13 px of an occluding silhouette, the box also contains
foreground. In the frame where the foreground is sharp, the box sum is dominated by
foreground gradient energy, so the argmax elects that frame **for a background pixel** —
which then renders defocused and veiled. The window's radius *is* the halo's length scale.

This was turned into a dose-response by sweeping the radius on `bee-3-cpl`:

| `WINDOW_RADIUS` | 3 | 6 | 9 | 13 | 20 | 26 |
| --- | --- | --- | --- | --- | --- | --- |
| rim w50, px | 8.75 | 8.75 | 9.50 | 10.75 | 19.00 | 25.75 |
| rim cutoff, px | 9.25 | 9.75 | 10.75 | 14.00 | 21.25 | 29.00 |

Over w9–w26 the cutoff is linear in radius with slope **1.07** and intercept **1.08** —
the cutoff tracks the window radius 1:1 over a 3× range, offset by `SOBEL_RADIUS`, which
is 1. Evaluated at the shipped `WINDOW_RADIUS` of 13 that line lands on the focus
operator's own `SUPPORT_RADIUS`. That is about as clean a mechanism identification as
this codebase contains.

The fix (`edgeaware.rs`) is three cooperating pieces:

1. **A narrow guide, not the winner field.** The obvious construction — find depth steps
   in pass one's winner field — *does not work*, because the winner field is itself haloed,
   so its step sits ~13 px from the true silhouette and a window truncated there still
   swallows it. The guide is instead elected at a small radius, read only near a strong
   luminance step, and never used to elect output.
2. **`SelectionScale`, a quantised distance transform.** Per pixel, the largest radius
   whose box does not span more than τ frames of the guide. Hard against an edge the
   support collapses to 1 px and returns to the full 13 px by 13 px out. Support is
   **maximal everywhere it is safe** — this is not a global window shrink, and flat-field
   election is untouched.
3. **`LayerSupport`, depth-binned masked means.** Pixels are placed on a continuous depth
   axis of 6 bins and **tent-splatted** so the grid interpolates rather than quantises;
   hard bin assignment caused visible blotching.

Constants: `DT_SIGMA_R = 12.0` in units of the plane's **median absolute luma gradient**
(deliberately not a DN threshold, so it carries no brightness scale between stacks);
`DT_ITERATIONS = 3`; `FLOOR_Q = 0.10`; `FEATHER = 1.25`; `MIN_LAYER_FRACTION = 0.12`.

The edge-stopping filter is a **domain transform recursive filter** — a one-tap IIR whose
feedback is driven to zero by a large luma step, so it restarts on the far side. "That is
the whole edge-awareness mechanism, and it is why this costs the same as a box filter
regardless of radius."

Every guard **ramps** rather than vetoes, because hard treatment switching produced a cliff
at the treatment boundary — "hard-edged blobs hugging silhouettes." The three ramps
multiply, which is why the feather is kept thin.

> **This entire subsystem is ON by default *within the estimator* and ABSENT from the
> default pyramid backend.** `pyramid.rs` contains zero references to `edgeaware`. The
> pyramid's answer to the same defect is the seventh band and the exponent ramp, not an
> edge-aware window.

### The plugin seam

**`FocusMeasure` is the system's only extension trait** (`strehl-core/src/focus.rs:619`).
Two other traits exist — `QuadSource` (`plane.rs:63`) and `GreenField` (`stack.rs:1291`) —
but both are internal data-access abstractions, not extension points.
`strehl-plugin/src/measure.rs` merely re-exports `FocusMeasure` — a load-bearing move,
because while the trait lived in `strehl-plugin` the CLI did not depend on that crate and
the pipeline existed **twice**, agreeing only by test.

```rust
pub trait FocusMeasure: Send + Sync {
    fn id(&self) -> &str;
    fn stencil_radius(&self) -> usize;
    fn window(&self) -> Window;
    fn normalisation(&self) -> Normalisation;
    fn respond(&self, luma: &[f32], geom: PlaneGeometry, out: &mut [f32]);
    fn aggregate(&self, ...) { /* defaulted */ }
    fn normalise(&self, ...) { /* defaulted */ }
    fn support_radius(&self) -> usize { stencil + window.radius() }
}
```

Declaring `Custom` and not overriding **panics** rather than silently passing through — "a
silent identity here would be a silently mis-scaled gate." There is deliberately **no
`fn noise_sd`**: that omission *is* the design.

**Registration calibrates on the way in.** `Registry::new` **refuses to exist** unless a
self-check first reproduces both in-crate constants in both configurations.
`register(Arc<dyn FocusMeasure>)` rejects empty ids and duplicates, then calibrates — a
degenerate or non-finite operator is refused rather than admitted with a plausible
constant. `ids()` returns sorted, so nothing downstream can inherit registration order.

**Why calibration is mandatory.** `FOCUS_NOISE_SD` is a property of the operator. Across
the seven reference operators the true value spans **10.27×**. At SML's `k = 6.68` an
intended `--gate 1.0` actually runs at **0.150**, and **89.02%** of pixels fall back to a
single frame instead of the intended 41.66% — "and every such case is indistinguishable
from the log, the exit code, and the calibration block." The registry hands out a
pre-normalised field whose noise SD is 1.0 by construction, paired with a dimensionless
gate.

Host calibration runs the operator over synthetic **unit-variance** noise planes through
the host's own regulariser and takes the interior SD. Spread is taken **across seeds,
never pooled within a plane**, because neighbouring interior responses are correlated. The
RNG is load-bearing and measured: as a plain LCG, `FOCUS_NOISE_SD` varied **1.30× across
seeds** because consecutive LCG outputs lie on lattice planes and Box-Muller consumes them
in pairs — "a single-seed measurement would have baked a 30% error into the gate."

**The honest limits of the plugin story:**

- The registry is **in-tree and static**. There is no `libloading`, no `dlopen`, no
  `inventory`. Contributing an operator **requires patching this repository** — add a type
  and add it to `survey()`.
- **`--focus` is refused on the default backend**, because the pyramid computes no focus
  field at all. The plugin surface and the shipping path **do not intersect**.

---

## 9. The systems model

### Streaming

**There is no memory-mapped I/O anywhere in this tree.** RAW files are read into an owned
`Vec<u16>`. What exists instead is a **memory-budget planner**, and every stage that
touches all frames holds a bounded window of them, never the stack.

- **Alignment streams.** The edge ladder pairs frames at most `max(spans)` (128) apart, so
  `measure_ladder_streaming` keeps a window of `max_span + 2 × batch` decoded green planes
  and evicts a frame once every pair reading it is measured; the next batch decodes while
  the current one is measured. Pairs are tagged with their ordinal and returned in ladder
  order, so the solve sees the same rows: sidecars are byte-identical to the former
  whole-stack decode. Before 2026-11-08 every plane was resident at once — 33 MB per
  33 MP frame, about 48 GB for a 1,444-frame bracket before a single pair was measured.
  The window is budgeted at `LADDER_WINDOW_BYTES` (6 GiB) with a minimum batch of 4.
- **The solve is banded.** Unknowns are in frame order and rows span at most one edge, so
  the normal matrix is stored and factored by its envelope (`align.rs`, `Envelope`):
  `O(n b²)` instead of a dense `O(n³)` Cholesky, bit-identical by construction and by test.
- **The fold** decodes → prepares → folds → **drops** each frame, so peak memory is
  O(look-ahead slots), not O(frames). RAW decoding (single-threaded per file) runs ahead
  on four decoder threads into a bounded window (`merge_cmd/decode-ahead.rs`) in the
  order the fold will ask, honouring the CA preview's stride.
- **The full-resolution gather is banded** (`warp_fullres_banded`). Each band of 16
  destination rows computes only the mosaic rows, Malvar rows and Catmull-Rom taps its
  samples touch, in per-thread buffers, instead of materialising the balanced mosaic and
  three demosaiced channels (528 MB per frame at 33 MP) and reading them back per site.
  `STREHL_GATHER_BANDS=off` restores the whole-plane route for A/B checks; both produce
  the same pixels.

Work is split by **contiguous chunks of the frame list** (canonical chunks, below), with a
coverage-exactly-once test. These are frame ranges, **not spatial tiles**.

`MEMORY_BUDGET_BYTES = 6 GiB`, read at 15 sites and deliberately not overridable. It sets
the canonical chunk count from a per-worker cost model over accumulators, frame workspace,
band planes and frame bytes; that model is part of the output contract (below), not a
measurement of the process peak.

### Parallelism

**Canonical chunks fix the arithmetic; threads do not.** The number of chunks — and so the
floating-point reduction order — is derived from the memory model and the geometry only.
Chunks fold serially, each into a reused accumulator absorbed in order. Execution threads
default to every core (`STREHL_PYRAMID_WORKERS` overrides) and only parallelise work
inside a frame, so output is identical at any thread count. Frames are prepared up to
`STREHL_PYRAMID_LOOKAHEAD` ahead (4 at 33 MP) and folded in index order. Until 2026-11-08
the look-ahead was disabled whenever the `temporal-energy` feature was *compiled*, which is
every desktop build; it now follows the runtime temporal decision.

**The fold is memory-bandwidth bound, not core bound.** MEASURED on bug-7 (100 frames,
desktop engine, 2026-11-08): 0.26 / 0.22 / 0.23 s per frame at 8 / 16 / 32 threads, and
`pyramid-add` floors at ~90 ms per frame at any thread count from 8 up — consistent with the
~5 GB of pyramid and accumulator traffic each frame moves. Further speed comes from moving
fewer bytes, not from threads. Fusing each Laplacian difference with its expansion (no
level-0 copy, no expanded buffer) and the per-level evidence/weight/ensemble passes into one
sweep took `pyramid-add` to ~77 ms and the pipeline to 0.20 s per frame, pixel-identical. The
GPU route, and why its divisions must go through f64 and its `ln`/`exp` stay matched to the
CPU, is in [the GPU fold proposal](proposals/2026-11-gpu-resident-fold-and-planner.md).

> The estimator and argmax paths *do* min with `available_parallelism()`. That
> inconsistency between backends is unresolved.

### The GPU fold

`crates/strehl-gpu` (engine feature `gpu`; `STREHL_GPU_FOLD=on|auto|off`, the desktop
requests `auto`) runs the default fold on a Vulkan GPU with the merge's accumulators resident
in device memory for each canonical chunk. At a chunk's end they are written into the CPU
`BandMerge`, which absorbs, thresholds and collapses exactly as before; chunking and
reduction order are unchanged. It is **bit-identical** to the CPU fold, which rests on four
measured conditions, each pinned by a test that fails without it:

- every f32/f64 arithmetic result is decorated `NoContraction` (no fused multiply-add);
- f32 division goes through f64 (native f32 division mismatched 29% of samples);
- `ln`/`exp` are `strehl_core::portable_math`, used by the CPU too since 2026-11-08 (the C
  runtime's are not correctly rounded; changing them moved 0.0026% of bug-7's samples by
  1 DN, attributed by `STREHL_WEIGHT_MATH=platform`);
- every entry point declares `DenormPreserve`: flat ground drives every frame's weight to the
  `exp(-80)` clamp, its soft-power numerator is subnormal, and a flushing device zeroed those
  coefficients (3.5% of samples, up to 6213 DN, before the fix).

Another device or driver must pass `cargo test -p strehl-gpu -- --ignored` before it is
trusted. With the GPU fold the desktop's live mid-chunk accumulator preview and per-band
surfaces are not produced (the device does not hand full fields back); stage progress is.

**Frame preparation on the GPU.** When the fold is on the GPU and the render uses the
default preparation (sidecar or no alignment, Catmull-Rom, Malvar, no defect correction, an
integral black level; `STREHL_GPU_PREP=off` declines), the decoded u16 CFA is uploaded once
and everything else runs on the device: Malvar, the checked Catmull-Rom gather with f64 site
pulls, extraction, the luma variance, the whole gate-floor probe and the ensemble null's
accumulation. Only the probe's four interior f64 sums (32 bytes) come back per frame; the
CPU turns them into the floor and hands each band's null unit back (`BandMerge::
note_external_null_frame` counts the frame exactly as `add_null_frame` would), and the
null's maxima and sums stay in device memory until the chunk ends, like the accumulators.
The probe is reproduced without uploading a probe frame:

- its noise is `portable_math::probe_gaussian_pair` (SplitMix64 emulated in u32 pairs on the
  device). The CPU fill uses the same functions; over 2^30 quantised samples they gave the
  same u16 as the C runtime's `ln`/`sin`/`cos` (MEASURED,
  `portable_math::tests::probe_noise_census`), and bug-7 renders were unchanged.
- f64 runs at 1/64 rate on this GPU, so each pair is first computed by an f32 screen made of
  IEEE add/multiply only (bit-reproducible). Its error against the f64 pair is bounded by
  exhaustive census over all 2^24 values of each draw (`probe_f32_census`), and only
  samples within twice that bound of a rounding boundary are recomputed in f64. The device
  test runs a 33 MP fill against the CPU; with the margin set to zero it fails (59 samples).
- the pooled interior sums are now each row summed in order, then the rows in order: a fixed
  association any IEEE device reproduces (it was one sequential sum, which only the CPU
  could). The f32 floor rounds the difference away except within ~1e-13 of a boundary; bug-7
  (100 frames and all 1,444) and the byte-freeze rows were unchanged.

**Data movement.** A frame is copied once, in parallel 4 MB pieces, into one of two
persistently mapped upload buffers (re-mapped after the device copy, not reallocated), then
copied on the device into one of two raw slots; a third slot holds the probe. Frames are
pipelined one deep: frame *n + 1* is decoded, staged and its probe submitted before frame *n*
waits for its own probe's sums (`PendingProbe`, a wait on that submission alone) and is
folded, so the CPU's floor and bookkeeping overlap the device. As soon as a frame is staged its
73 MB sample buffer goes back to the decoders, and the next decode writes into it
(`strehl_raw::decode_into`) instead of into new memory whose pages would fault in. At a chunk's end the accumulators come
back through one reusable 64 MB readback buffer, piece by piece, instead of one staging copy
of the whole merge (over 1 GB on bug-7). The first chunk's are copied into a new merge; every
later chunk's are absorbed into it as they arrive (`GpuFold::absorb_chunk`), with the
elementwise sums, minima and maxima `BandMerge::absorb` uses, in the same operand order
(`BandMerge::EXTERNAL_ABSORB`, tested against `absorb` with signed zeros and infinities).
So the worker's own merge only counts frames, and holds the ensemble null's windows when the
CPU prepares frames (`absorb_external_remainder` moves both): attaching the GPU fold releases its totals
(`release_external_totals`), the CPU fold's workspace and, under GPU preparation, the CPU's
preparation buffers. None of this changes an operation's inputs or order.

The engine executables (CLI and desktop) use mimalloc as the global allocator
(`strehl_cli::EngineAllocator`). Every frame allocates and frees ~100 MB of decoder buffers;
the Windows system allocator hands blocks that large straight to `VirtualAlloc`, so each
starts as fresh pages faulted in and zeroed, and those faults contend across decoder threads:
a single-threaded, independent decode took 74, 116 and 166 ms with 4, 8 and 16 decoders
(MEASURED, bug-7, GPU preparation). mimalloc reuses the memory: on all 1,444 frames one
decode went from 125 to 88 ms at 8 decoders and CPU time from 775 to 589 s (MEASURED). A
size-keyed cache of freed large blocks was tried first and gave nothing measurable.
`STREHL_DECODE_THREADS` overrides the decoder count.

**Decoding.** With the device preparing frames, decoding became the limit: the linked decoder
spent ~165 ms of CPU per 33 MP frame (one thread) and stopped at ~78 frames/s on this machine
whatever the thread count, because it parallelises inside each file on the shared pool. Sony's
lossless-compressed raw is tiled lossless JPEG, so `strehl_raw` decodes those pixels itself
(`lossless-jpeg.rs`, from ITU-T T.81; the linked decoder still supplies every other field and
decodes every other file): an 8192-entry table gives the whole difference and its length for
nearly every sample, the bit buffer refills without branches, and two tiles decode in one loop
so a core runs two dependency chains. ~50 ms per frame on one thread, plus ~10 ms of the
linked decoder's metadata. Its output equals the linked decoder's on every sample of every file
checked (`tests/lossless-jpeg.rs`: 4,052 files across 12 captures, ISO sweeps and dark frames
included; 3,692 of them lossless-compressed). Each file now decodes on one thread, so with GPU
preparation the decode-ahead pool uses half the logical cores (16 here); 8 left the fold waiting
for decodes. `STREHL_RAW_DECODER=rawler` decodes every pixel with the linked decoder.

MEASURED, bug-7 1,444 frames, desktop path (sRGB + linear master + progress + CA preview),
same machine: CPU 329.9 s; GPU fold with CPU preparation 209.2 s; GPU preparation 42.2 s
(0.02 s per frame folded); with the data movement and allocator above 32.5-32.8 s against
43.5-44.4 s for the build before them, alternated (fold 22.6 s, CPU time 555 s against 848 s,
peak private memory 7.3 GB against 6.7 GB); with the decoder above and buffer reuse 26.5-26.7 s
against 33.1-33.5 s, alternated (fold 17.2-17.4 s against 23.5-23.9 s, CPU time 300-309 s
against 578 s, peak private memory 9.2-9.4 GB against 7.3-7.4 GB: sixteen frames decode at
once); with the host buffers released and chunks absorbed from the device 25.9-26.0 s against
27.0 s, alternated, peak private memory 7.1 GB against 8.9 GB and peak working set 3.85 GB
against 5.8 GB. The fold now waits on the device, ~12 ms per frame. Photograph and float master are
identical to the CPU's in every one of these runs. `STREHL_GPU_PROFILE=1` times every dispatch
with GPU timestamps (diagnostic; it serialises submits; the device timing test,
`crates/strehl-gpu/tests/timing.rs`, prints the per-kernel report).

### Determinism and provenance

Output carries `Software` tag 305 with version and git build id, an `ImageDescription`
develop statement, an ICC profile where the pixels honestly are sRGB (and deliberately
**no** profile where they are camera-native, since mislabelling would be worse than not
labelling), and print resolution tags. `VERSION` is stamped by `build.rs` from the source
commit with a `-dirty` suffix.

The primary provenance channel is the stderr run banner: build id, backend and the reason
it was chosen, camera, CA decision, ISO, levels, noise-model provenance, defect plan,
frame count, geometry, band config, alignment (placed/refused/held-out error/resampler),
memory plan, folded count, band noise gain, measured floor, averaged fraction per level,
timings and colour handling.

The system is byte-frozen: a regression suite pins whole-output SHA-256 hashes across
backends, so any unintended change to the merge is caught as a hash movement.

### Measured performance

- **299 frames, 33 MP, 11.3 GB of ARW → 7032×4688 TIFF in 116.9 s warm** (best of 3) on
  the default pyramid backend; 102.2 s on a quiet box. The fold is 98.5% of the run.
  `wall = 1.1 s + 0.77 s × N`, R² = 0.998.
- **22.58× `enfuse`**; against a `focus-stack` fork, 0.366 s/frame vs 13.93 s/frame with
  7.64 GiB peak RSS vs 47.37 GiB.
- Whole 26-subject corpus: **4,825 frames in 16.2 min = 0.2015 s/frame**.

- **bug-7, 1,444 frames, 33 MP, 46.6 GB of ARW** — MEASURED 2026-11-08 on a Ryzen 9 9950X3D
  (16 cores / 32 threads, 64 GB, NVMe), desktop engine (`temporal-energy` compiled, off),
  `stack --merge pyramid --srgb --linear-master`, `STREHL_UI_PROGRESS=1`, CA refinement on:
  - before (`86cdc47ec`), alignment **already cached**: 645.2 s (CA preview 68.2 s + main
    576.5 s at 0.40 s/frame), 3.26 GB peak private. Its whole-stack alignment could not be
    run at this depth on this host: it holds every plane (~48 GB); at 300 frames it peaked
    at 13.28 GB against 6.75 GB streaming, with byte-identical sidecars.
  - after, **including a fresh alignment**: 464.7 s, 7.22 GB peak private (four look-ahead
    slots and the decode-ahead window, which the desktop engine never had). Alignment alone:
    12,645 pair fits in 89.8 s at 7.18 GB.
  - Photograph and float linear master **pixel-identical** to before (compared decoded,
    since the TIFF `Software` tag carries the build id).

> The README's **51.6 s** headline was measured on the **estimator** path and explicitly
> does not transfer to the default. The 36–42× comparator headline is **retracted to
> 2.4×** against the build that actually produced it.

---

## 10. Status of every major module

| Module | Status | Note |
| --- | --- | --- |
| `pyramid.rs` | **DEFAULT** | The shipping merge |
| `merge_cmd/gatefloor.rs` | **DEFAULT** (opt-out) | Per-frame measured band-noise floor |
| `align.rs`, `warpmap.rs` | **DEFAULT** (sidecar-cached) | Solve once, gather at consumption |
| `optics.rs` (lateral CA) | **DEFAULT** for matching gear | Composed into the alignment similarity |
| `ca_refine.rs` (per-capture CA refinement) | **DEFAULT** where a profile applies (`--refine-ca=off` skips) | Preview pass + measured residual on top of the profile |
| `demosaic.rs` (Malvar) | **DEFAULT** in full-resolution alignment and development | Per-source reconstruction during full-resolution gather, plus final demosaic when developing; binned output omits only the latter |
| `color.rs`, `highlight.rs`, `clip.rs` | **DEFAULT** in the writer | Roll-off is identity below the knee |
| `noise.rs`, `profile.rs` | **DEFAULT** | Injected once; PRNU term measured but off |
| `defect_map.rs` | **OPT-IN**, off | Dust arm real; hot arm a measured null on this body |
| `restore.rs` | **OPT-IN**, off | `STREHL_RESTORE` carries the gain cap; read on both backends |
| `merge.rs` (estimation, `n_eff`, veil) | **ESTIMATOR-ONLY** | Where the thesis is literally implemented |
| `focus.rs`, `edgeaware.rs` | **ESTIMATOR-ONLY** | Absent from the default backend entirely |
| `photometric.rs` | **ESTIMATOR-ONLY** | `--photometric` REFUSED on default |
| `through_focus.rs` | **ESTIMATOR-ONLY**, diagnostic | Cannot move the selection field — asserted by test |
| `softgate.rs` | **ESTIMATOR-ONLY**; inert on default | Correctly-spelled kernel exits 0 and changes nothing on pyramid |
| `robust.rs` | **BUILT-NOT-WIRED** | `merge_cmd` never calls `new_robust`; inert on *both* backends |
| `outlier.rs` | **BUILT-NOT-WIRED** | The header explicitly forbids wiring it |
| `flat_ratio.rs` | Reporting only | Acceptance statistic; modifies no image data |
| `strehl-plugin/` | Real trait seam, **REFUSED on default** | In-tree registry; no dynamic loading |

---

## 11. Known gaps

**Against the brief:**

- **GPU is entirely unused.** Speed is already SOTA on CPU, so this does not block
  quality, but it is in the brief and unaddressed.
- **No SIMD anywhere** — zero matches for `std::simd`, `f32x`, `wide::`, `target_feature`,
  `avx` or `fma`. No cache-line or prefetch work either. All parallelism is rayon at
  frame-chunk granularity. The measured performance is achieved by algorithmic structure
  and memory discipline alone, which means substantial headroom remains untouched.
- **Pluggability is 1 of 5 kinds.** Focus measures are a genuine, calibrated, demonstrated
  trait seam. Merge strategy is an enum in core; alignment model, optical profile and
  output stage have no trait at all. And the one real seam is refused on the default
  backend.

**Against quality:**

- **Print-ready: NO.** 24 of 26 masters are clean to the eye at 1:1, but of the halo
  scores only 11 of 26 are actually *clean* — 4 blind and 7 unmeasurable remain UNSCORED,
  which is not the same as clean. 13 subjects FAIL on a rim axis at ±12 px that the halo
  work never reached.
- **The default backend selected on noise in flat regions** until the ensemble gate
  (2026-11-02). Remaining: plateau regions, where every frame holds the same detail,
  still select rather than average; multi-pass Best result sessions do not use the gate.
- **`SELECTION_INFLATION` is 1.0** — the noise penalty for selecting is a known missing
  term.
- **One profiled camera body, one optical path.** The gear-matching guard has never
  declined a real file, because all corpus stacks are the same rig.
- **Rail capture is deferred** — no rail hardware to test against, and an untested geometry
  model would violate rule 8.

## 12. Opt-in multi-stack sessions

**EXPERIMENTAL, COMPILED ONLY WITH THE `multi-stack` FEATURE** (strehl-cli and strehl-ui,
off by default since 2026-11-04). Without it the `session` subcommand, the session engine
modules and the desktop's session actions are absent; the session specification types and
folder discovery stay compiled so saved results still open.

**SEPARATE SESSION PATH.** `strehl session` consumes a versioned manifest of
ordered passes, each with one or more ordered continuation folders.
[The session guide](multi-stack.md) describes the user contract. The existing
`stack` command does not call this consumer. A one-pass, one-folder
Combine/Repeat session delegates to the ordinary command and adds only source
binding and completion receipts around it.

### Source and geometry contract

`session-input.rs` retains global, pass, segment and local indices. Canonical
paths, file stamps and whole-original SHA256 identities bind each run;
duplicate paths or duplicate file content are refused. Outputs and caches
must remain outside every capture folder.

`session-cache.rs` stores original active CFA codes as `u16`, preserving
decoded geometry, levels and calibration. The in-memory cache has a byte
budget and pinned handles. Checksummed disk entries bind the original identity
and decoder implementation; corrupt or stale derived entries are rebuilt.
This cache contains no aligned frame volume.

`session-align.rs` builds bounded guides, proposes intra-pass and cross-pass
pairs, refines accepted seeds directly against original native data, and solves
the direct measured graph in one reference gauge. Core's
`solve_global_in_tracks` applies the smoothness prior within explicit pass
tracks only. It does not introduce rows across pass boundaries or chain poses.
The ordinary solver retains its original single-track behavior.

Reports preserve components, cycle rank, per-pass placement/refusal counts,
direct edges and candidate correspondence. Fitted scale proximity and mutual
nearest partners are retrieval hints; `validated_same_focus` remains false.
A connected graph establishes connectivity, not placement accuracy or
identical physical focus. Geometry caches bind source identities, ordered
session layout, configuration, resampler and owned implementation sources.

### Sampling and fusion

`session-sampling.rs` gathers original same-color CFA samples at consumption.
Coordinates explicitly relate each CFA site to the green-quad alignment gauge.
Only the current source's signed `f32` planes are materialized. Coverage and
original clipping support are separate masks. The clipping check includes
nonzero negative-lobed interpolation taps; clipped data are not silently
turned into valid zero-valued observations.

Each pass receives the existing injected sensor-noise model. A deterministic
original-CFA Rademacher probe measures the actual gather-plus-pyramid variance
transfer for each placement, profile, canvas and resampler. Luma and color
transfer are separate. This is an operator measurement with known input
variance, not a new fitted sensor noise estimate. It is a spatial average
under stationary independent noise and does not represent exact local
covariance. Nonlinear clamped Catmull-Rom is refused.

`session-transfer-cache.rs` caches only those small measured operator reports.
Its binding includes exact placement bits, canvas, full geometry, optical
profile, probe settings, platform and implementation sources. Payload float
bits, checksum, dimensions, support counts and positivity are checked.
Worker count is excluded because indexed parallelism preserves the
measurement's reduction order; one-versus-sixteen-worker controls cover it.

Core's `pyramid::session_fusion` is an additional coefficient consumer.
Disjoint proposed groups contain at most one observation per pass. Compatible
repeats use an equal-weight coefficient mean with variance
`sum(v_i) / K^2`; this is valid propagation, not an inverse-variance optimal
HDR estimator. Disagreement uses ordinary noise-gated admission, or the
explicit primary's supported coefficient. Absent a primary, the automatically
chosen geometry reference has no fusion preference. Combine mode admits
sources independently unless a primary requires matching-overlap handling.

Strict uncensored support is preferred across groups. A separate coverage
fallback retains real saturated values only where all observations lack
strict support; it never claims to recover clipped information. The hull uses
uncensored observations where available. Actual unsupported output pixels
withhold the completed photograph. CFA planes are demosaiced once by the
existing writer into the photograph and scene-linear master.

### Modes, resources and desktop boundary

Fused sessions require compatible camera, lens, decoded sensor calibration,
known ISO and aperture. Combine/Repeat also require equal shutter time.
Different apertures or lighting appearances remain separate in Aligned layers,
which shares geometry/canvas while preserving each pass's final calibration.
Physical camera-body identity cannot be established from model metadata alone.

HDR's `session-photometry.rs` validates one bounded multiplicative correction
per pass after nominal shutter normalization. A fixed checkerboard split of
spatial patches separates fitting and validation; several proposed focus
partners must span the tracks. Original clipping/coverage masks and injected
noise eligibility guard the measurement. Supported contradictory radiometry
vetoes the pass rather than disappearing through accepted-pair selection.
All pair evidence, tolerances, gains and refusals are retained. The consumer
applies the accepted gain to signal and its square to propagated variance.
Calibration phase and retained report memory are checked before merge buffers
are allocated. These are sampled compatibility checks, not calibration of
physical focus or a general camera response.

The optional primary anchors framing and preference over disagreeing matched
overlap. It does not suppress useful unmatched focus coverage. For layers it
sets the shared reference and initially opened layer. Neither mode is a
stitching implementation.

A checked session memory reservation covers cache, sampling, probes,
coefficient workspaces and output development. It is separate from ordinary
stacking's existing planner. Deterministic row and pixel-chunk parallelism
uses CPU workers without changing per-pixel source order. GPU support remains
the desktop display path; experimental GPU fusion is not silently enabled.

The desktop saves a session recipe separately from ordinary catalog stacks.
Its isolated engine worker receives an immutable manifest, fresh output
directory and shared cache outside captures. Publication checks completed
source identities against the imported recipe and validates every photograph
and linear master. Leaving session mode restores the entire ordinary recipe.
Pass groups and layer ownership survive saved-run reopening.

Depth-aware mosaics, super-resolution, calibrated depth, and Fourier-ring
resolution claims are not implemented by this path. Their capture and
identifiability requirements remain separate from usable session input,
common-gauge layers and conservative fusion.
