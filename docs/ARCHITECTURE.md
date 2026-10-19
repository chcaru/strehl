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

But above that floor the default exponent ladder runs at 7.683 / 8.0 / 8.0 in the three
finest bands, which the module itself calls "already close to winner-take-all — a frame
with twice another's band energy gets 256 times the weight" (`pyramid.rs:1241-1242`).

And the project's own instrumentation measures selection concentration **higher in flat
regions than in detail regions at every band** on `coffee-bubbles` — 1.0000 vs 0.8214 at
band 0, 0.7837 vs 0.2989 at band 2 where a plain mean would read 0.0526. The module
comment names this exactly: *"That is a merge selecting on noise"* (`pyramid.rs:1136-1147`).
The fix is built (`STREHL_PYRAMID_SIGNIFICANCE`) and ships **off**, because at derived
strength it does not collapse the inversion — band 1's gap narrows 0.0657 → 0.0338 and
bands 2–6 move under 0.2% (`pyramid.rs:1150-1190`).

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

**2. Never materialise aligned frames.** Gather at consumption inside each kernel.
Materialising 60 aligned RGB frames is 24 GB and demosaics 60 times instead of once. This
is why alignment is a *sidecar* and not a preprocessing pass, and why demosaic is the last
stage rather than the first.

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

**Demosaic runs exactly once, at the end, on the merged planes** — and on the *default
measurement path it does not run at all*, because the default output is binned 2×2
(`merge_cmd.rs:7337-7341`). It executes only when `demosaic || (srgb && !binned)`
(`main.rs:1144`). The fold is on CFA planes throughout, which is what "CFA-native"
means.

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

Defaults `exponent = 2.0`, `sharpen_per_octave = 1.4`, `MAX_EXPONENT = 8.0`. The ladder,
coarsest → finest: **2.000, 2.800, 3.920, 5.488, 7.683, 8.000, 8.000** (last two capped
from 10.756 and 15.059).

The ramp is geometric rather than linear because band power itself falls geometrically
with scale, so a fixed *ratio* per octave is the scale-free choice. The justification is
asymmetric risk: in a fine band a wrong pick is one high-frequency coefficient nobody can
see; in a coarse band a wrong pick **is** the rim. A depth boundary therefore becomes a
transition inside each band rather than a step in the image.

`MAX_EXPONENT = 8.0` is set by f32 representability, not taste — the overflow-safe bound
on `p·ln(r)` is 80, so beyond about `p = 10` the sharpest coefficients all pin and get
averaged. More selectivity is `SelectMode::HardMax`, not a bigger exponent.

Other defaults: `BaseBand::Mean` (`pyramid.rs:1280`), `SelectMode::SoftPower`,
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

*Solve*: `solve_global` — one weighted complex linear least squares over **all** measured
edges simultaneously, via normal equations plus Hermitian Cholesky with iterative
refinement. Transforms are carried in **f64**, not f32.

No pair's fit is ever composed into another's. Chaining exists **only as a measurable
negative control**: `solve_hops` with `max_span = 1` is the forbidden adjacent chain,
"implemented here only so that the forbidden thing can be *measured* rather than
asserted — do not ship it." It scores 40.342 plane px held-out against the global solve's
6.758 px.

Frames outside frame 0's connected component get `None` unless smoothing is on, in which
case their placement is **extrapolation of the model, not a measurement**, and the module
requires reports to say so.

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

The transform is applied by **gathering at the point of consumption**, never by
materialising a warped copy. Interpolation is a lowpass; applying it twice — once to
register, once to output — throws away exactly the fine detail the project exists to keep.

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
`Vec<u16>`. What exists instead is a **memory-budget planner**.

The invariant is a fold: each worker decodes → folds → **drops** one frame before reading
the next, so peak memory is O(workers), not O(frames). Measured, memory is flat at
5.6–5.8 GB from 20 to 299 frames — a 3.2% spread over a 14.9× change in N.

Work is split by **contiguous chunks of the frame list**, `chunk_len = frames.div_ceil(workers)`,
with a coverage-exactly-once test. These are frame ranges, **not spatial tiles** — there is
no image tiling on this path.

`MEMORY_BUDGET_BYTES = 6 GiB`, read at 15 sites and deliberately not overridable. The
pyramid banner's "4 workers × 1328 MB" comes from a per-worker cost model over
accumulators, frame workspace, band planes and frame bytes.

### Parallelism

One rayon task per frame-chunk. Data-parallel with **no locks on the hot path**: each
worker owns a private accumulator and results are combined afterwards by an exact
`absorb`. The only shared mutable state on the baseline path is two atomic counters and an
atomically-absorbed defect tally.

**Worker count on the pyramid backend is memory-derived only — `available_parallelism()`
is deliberately excluded**, because the worker count sets the float reduction order and
would otherwise make output host-dependent. Measured, 2 vs 7 workers differ on 0.2573% of
pixels at a maximum of 1 DN. This is a real determinism/throughput trade: the memory-derived
4-worker cap costs **1.29×** against 8 workers on a 16-core part.

> The estimator and argmax paths *do* min with `available_parallelism()`. That
> inconsistency between backends is unresolved.

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
| `demosaic.rs` (Malvar) | **DEFAULT** when developing | Runs once, at the end; not at all on the binned measurement path |
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
- **The default backend still selects on noise in flat regions.** Measured, at every band.
  The fix is built and off because at derived strength it does not collapse the inversion.
- **`SELECTION_INFLATION` is 1.0** — the noise penalty for selecting is a known missing
  term.
- **One profiled camera body, one optical path.** The gear-matching guard has never
  declined a real file, because all corpus stacks are the same rig.
- **Rail capture is deferred** — no rail hardware to test against, and an untested geometry
  model would violate rule 8.
