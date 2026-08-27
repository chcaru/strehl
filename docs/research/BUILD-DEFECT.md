# BUILD-DEFECT — sensor defect correction: the mechanism, and what the sensor actually has

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`P1, P2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision:** `9b05d0b7` (`V-H2H2: correct three numbers against the
persisted logs`).

**Read-only inputs, never written to:** `D:\macro-dark-frames` (242 frames),
`D:\personal\macro\flat-fields` (18 captures x 20 frames),
`D:\personal\macro` (26 subject stacks).
Scripts and artefacts: `experiments/BUILD-DEFECT/`.

---

## 0. The commission, and the prior work my brief did not name

### 0.1 What I was asked

> *Build sensor defect correction — hot/stuck pixels and dust — and wire it into
> the shipping stack path. Dust is fixed in sensor coordinates … a dust mote
> that is a single stationary blob in sensor space smears into an arc/trail in
> the merged output … Hot pixels are a magnet for the focus measure.*

### 0.2 The prior art, found by rule 40 before writing any code

The brief said this was "a total gap". It is not, and two of its three premises
were already settled:

- **`M101-defect.md` ran the hot-pixel arm end to end and returned a
  well-controlled NULL.** In-situ amplitude 1.5 DN; the election does not prefer
  a hot pixel below 100–250 DN; the elected trail measures **0.931 px against a
  0.937 px shift null**, and an identity-warp control reads exactly 1.000. **My
  brief's "hot pixels smear into trails" premise is refuted for this body.**
- **`M29-static-defects-measured.md`** is the licence for the dust arm:
  *"Dust must be handled explicitly… This is now a design decision, not an open
  question."* Dilution `D = 0.999` at `n_eff = 3`, i.e. dust arrives at full
  contrast.
- **`M71-flat-fields.md`** measured a boolean dust mask of 2,898 quads. §4.3
  below shows that mask is an artefact of its own high-pass.

So the genuinely open deliverable was **dust**, and the hot arm was a mechanism
to build and ship OFF, not a defect to chase.

### 0.3 Three corrections to the brief's facts

The orchestrator asked that these be carried as corrections rather than quietly
absorbed. The brief was wrong on all three.

- **P1 (MEASURED).** `D:\macro-dark-frames` holds **242** frames in **11 ISO
  groups of 22**, ISO 50–2000, all 1/100 s — not "22 dark frames".
- **P2 (MEASURED).** **20 of the 26 subject stacks are f/5.6**, the same
  aperture as the flats. M71's caveat that its mask is "a lower bound, the
  corpus shoots f/8–f/11" does not apply to most of the corpus.
- **P2b (MEASURED, prior art).** The brief's central motivating claim — "a dust
  mote smears into an arc/trail in the merged output, a defect the stacking
  itself creates" — **is refuted for this body**, and was already refuted before
  I started. M101 measured the elected trail at **0.931 px against a 0.937 px
  shift null**: the stack is not spreading defects. The correction in this lane
  is worth building because the mote is a *stationary −8.24% attenuation*, not
  because it is smeared. The ordering requirement (§0.4) survives the
  correction unchanged — a map addressed to photosites cannot be applied after
  a resample regardless of how far the defect travels.

---

## 1. Pre-registered bars

Fixed before the measurements in §4 were run.

| # | Bar | Why |
|---|---|---|
| B1 | A dust search must return **zero** components on a null where every capture is rolled independently. | Rule: a search that cannot fail returns its least-bad candidate. |
| B2 | A metric must read a **planted defect** RED **and** a known-clean input GREEN **and** a planted **improvement** must move it the *other* way. | Rule: a suite of degradations cannot separate blind from perverse. |
| B3 | Every input must land in **exactly one** counted outcome, and the outcomes must sum to the total. | "corrected: 0" must be distinguishable from "examined: 0". |
| B4 | Any printed confidence must be **gated on**, not merely printed. | Rule: print, then TEST. |
| B5 | The feature must be **OFF by default** and must not move `byte-freezes.tsv`. | The registry is the orchestrator's. |
| B6 | A typo'd override must **error**, never fall back. | House convention. |

---

## 2. The answer, up front

**P3 (MEASURED). The flat-field-derived dust map is mis-registered and must not
ship.** Of the four motes the flats nominate, scored against a commissioned
local null on twelve real subject stacks:

| flats component | in the photographs | p |
|---|---|---|
| 396 quads at quad (3192,109) | **+0.2001%** | 0.9900 |
| 127 quads at quad (3210,136) | **+0.1571%** | 0.9501 |
| 66 quads at quad (3440,2281) | **+0.5398%** | 1.0000 |
| 29 quads at quad (3209,116) | −3.1952% | 0.0025 |

**P4 (MEASURED). The sensor has exactly two dust motes that reach the owner's
photographs, and the flats put both in the wrong place.** Re-locating each
nomination to the deepest 8-quad disc within ±40 quads:

| from | to | core | p | moved |
|---|---|---|---|---|
| (3192,109) | **(3202,121)** | **−3.6303%** | 0.0025 | 16 quads |
| (3210,136) | (3202,120) | −3.6303% | 0.0025 | 18 quads |
| (3209,116) | (3201,122) | −3.6272% | 0.0025 | 10 quads |
| (3440,2281) | **(3434,2305)** | **−8.2359%** | 0.0025 | 25 quads |

Three of the flats' four components are mis-registered fragments of **one** mote
at quad (3202,121). The deepest defect on the sensor is at (3434,2305) at
**−8.24%** and the flats placed their component 25 quads away, where the
photographs read **+0.5398% at p = 1.0000**. Correcting at the flats'
coordinates would brighten clean pixels beside an uncorrected mote.

**P5 (MEASURED). A blind search of the photographs for further dust cannot be
commissioned on this corpus.** Every setting sensitive enough to recover a
planted 2.5% disc has a roll null returning **22 to 434** false components;
every setting whose null is clean is **blind to the plant**. There is no setting
that is both. I therefore report **no** exhaustive dust census, and the two
motes above are a *targeted* result: the flats nominate, the photographs confirm
and relocate.

**P6 (MEASURED). The hot arm is a mechanism, not a fix.** 14,626 hot sites,
0.0444% of the sensor, reproducing M101's 14,604 to **+0.2%**. Only **111**
sites survive at the amplitude floor where split-half reproducibility is 1.000.
M101 already measured the arm immaterial to the election. It ships OFF.

**What ships:** a working, commissioned mechanism — map format, detectors,
corrector, metric, CLI wiring **in the shipping `pyramid` merge path, applied
in sensor coordinates before the warp** (§6.2) — **off by default**, plus a
photograph-derived map holding the two real motes. The default-off is now a
*measured* decision twice over: the map that a naive flats pipeline produces is
actively wrong (P3), and a map that is merely *stale* fails the same way one
step later in time (§8 Q3).

---

## 3. The map (commission section 1)

### 3.1 Hot pixels, from 242 darks

**P7 (MEASURED).** 6σ same-plane neighbour excess, recurrence ≥ 6/11 ISO groups
(recurrence across independent groups, not a sigma threshold, is the correct
discriminator — M22). Census **14,626**: R 111 / G1 125 / G2 8,157 / B 6,233.

**P8 (MEASURED).** Row asymmetry `(G2+B)/(R+G1)` = **60.97×**, against M101's
**61.1×** — an independent reproduction of a striking number.

**P9 (MEASURED).** External agreement: M101 14,604 (+0.2%), M48c 13,650 (+7.2%),
M22 11,393 (+28.4%). 462 sites recur at 11/11.

**P10 (MEASURED).** Split-half reproducibility by amplitude stratum (electrons),
interleaved halves of the same darks: 0–2 → 0.000, 2–4 → 0.116, 4–8 → 0.607,
8–16 → **1.000**, ≥16 → **1.000**. Jaccard by plane R 0.128 / G1 0.093 (noise)
vs G2 0.345 / B 0.355 — M101's P3 reproduced. **Only 111 sites lie at or above
the 8 e⁻ floor where reproducibility is 1.000**, and `HotFloor::REPRODUCIBLE`
defaults there.

### 3.2 Dust, from 18 flat captures

**P11 (MEASURED).** The high-pass removes **264.9×** of the between-capture
disagreement the moving cloud creates: 3.6194% → 0.0137%. This is the
illumination/dust separation the brief asked me to prove rather than assert.

**P12 (MEASURED).** Illumination drift is a 2.35× swing (M71) and per-capture
residual rms is 0.0979%–0.4882%; the seed bar is set at **0.50%**, above the
noisiest capture's rms, which is the stated reason for the number.

**P13 (MEASURED).** The roll null — all 18 captures rolled independently —
returns **0 components at every one of 24 settings** of a
`seed × recurrence × floor` sweep, against 4 components / 618 quads on the real
arm. **B1 discharged on the flats.**

### 3.3 The format

Text, because `*.npy` and `*.tif` are gitignored and a map that cannot be
committed is not a camera property, it is a scratch file. `MAGIC` +
`VERSION`, sensor and covered geometry, aperture, provenance comments, then
`h x y excess_e` and `d px py gain` records and a terminating `end`.

**P14 (MEASURED).** The terminating `end` record is load-bearing: the first
photograph-derived map I wrote omitted it and the loader refused it —
`defect map is truncated: header declares 14626 hot sites and 1135 dust quads,
14626 and 1135 were read, and the terminating 'end' record is absent`. A
truncated map is the failure mode that silently under-corrects.

Hot amplitudes are stored in **electrons**, not DN, so one map serves every ISO;
the DN conversion happens once, at the call site, through the injected
`NoiseModel` (rule 3).

---

## 4. THE DECIDING MEASUREMENT (commission section 2)

### 4.1 The discriminator

A subject has detail, and in a focus bracket the subject is nearly stationary,
so averaging frames *within* one stack cannot separate detail from dust. The
discriminator is **between subjects**: a bee, a coffee bean and a sheet of
wrapped text share nothing but the sensor. Per subject, the median over frames
of the per-frame high-pass residual; across subjects, the median of those.

### 4.2 Commissioning the statistic (B2)

**P15 (MEASURED).** A 2.5% disc planted into all twelve subjects and pushed
through the identical operator is recovered at **−1.8022% to −2.5016%** core
depth. The statistic is **not blind**.

**P16 (MEASURED).** A disc **BRIGHTENED** by +2.5% at the same location moves
the score the *other* way — core +2.3611% to +3.0759%, p = 1.0000 in every arm.
The statistic is **not perverse**. This is the arm the project has been burned
by omitting.

**P17 (MEASURED).** The procedure has a **scope**, and the scope is a property
of the neighbourhood. Mid-frame at quad (1400,1200) the local null's 1st
percentile is **−5.0085%** and a planted 2.5% disc reads **p = 0.1197** — not
significant. In the right-hand region where all four nominations live, the local
null's 1st percentile is −0.23% to −0.51% and the same plant reads **p =
0.0025**. The claim this licenses is *"in the quiet right-hand region of these
twelve stacks, a 2.5% mote is detectable and this is what is there"*, and
explicitly **not** *"the sensor has no other dust"*.

### 4.3 M71's dust mask is a border artefact

**P18 (MEASURED). This corrects committed prior work.** M71's 2,898-quad mask
has distance-from-nearest-edge percentiles `[0, 0, 1, 2, 5, 8, 42]`: **99.93%
of it lies within 40 quads of an edge and 100% within 90**, against area-share
nulls of 5.61% and 12.41% — **17.8× and 8.1× enriched**. Median distance from an
edge is **2 quads**.

The cause is measured, not guessed. Ring median of the residual by distance from
the nearest edge: **−0.9340%** at d = 0, −0.5194% at 10, −0.2307% at 20,
−0.0975% at 30, **−0.0030%** at 40, +0.0236% at 90, +0.0238% at 500. Three
passes of a half-width-30 box smoother have support 90 and the artefact reaches
~40 quads; the shipped border is 60. **At border 90, zero components survive at
M71's own settings.**

**M71's roll control could not have caught this**, and that is the generalisable
lesson: rolling moves the shelf off the border that made it, so the control
passes on an artefact that is *created by* the frame edge.

### 4.4 The result

§2 P3–P5. The whole-sensor location null used first (script 09) gave
p = 0.0299 / 0.85 / 0.85 / 0.83; the **local** null of §4.2, which controls for
the fact that the right-hand region is quiet in every subject, sharpened this to
p = 0.0025 / 0.9900 / 0.9501 / 1.0000.

### 4.5 The delivered pixels (B3, B4)

Two `strehl argmax-baseline` renders of `bee-3-cpl --limit 20` at a **fixed**
`--exposure=1.47`, differing in exactly one thing — whether `STREHL_DEFECT_MAP`
was set:

```
pixels differing: 16039 of 32966016 (0.048653%)
changed bounding box: x 6350..6927, y 184..4667
max |delta| = 3974 DN of 65535
  mote (3202,121): core 62669.3 -> 63184.1 = x1.00821  surround 63315.9 -> 63325.6 = x1.00015
  mote (3434,2305): core 51764.7 -> 53522.4 = x1.03395  surround 53787.1 -> 53842.5 = x1.00103
  CONTROL (1600,1000): 26160.2 -> 26160.2, bit-identical: True
untouched: 99.9513% of the frame
VERDICT: PASS
```

**P19 (MEASURED).** The correction lands on the motes and **nowhere else**: the
changed bounding box is x 6350..6927 in sensor pixels, i.e. quads 3175..3463,
exactly the two motes; a control region 1,600 quads away is **bit-identical**;
the core moves 55× and 33× more than its own surround.

**P20 (MEASURED, and a caveat I am not going to bury).** The core ratios in
delivered sRGB (×1.008, ×1.034) are *smaller* than the map's linear gains
(median 1.033, 1.061). Both motes sit in bright regions — 62,669 and 51,765 of
65,535 — where the sRGB transfer curve compresses. The correction is applied in
linear light before the curve; the delivered contrast change is therefore real
but smaller than the linear gain, and on a *dark* subject region it would be
larger.

**P20b (the limit of P20, stated so it is not read past).** The measured
quantity is an **amplitude**: ×1.034 in delivered sRGB at the larger mote.
**Visibility is not established.** Nobody has run the experiment that would
establish it — no print was made, no observer was asked, no detection threshold
for a soft low-contrast disc at this size and surround luminance was measured
or cited. The honest form of this result is "measured amplitude, visibility not
established", and this report does not claim, in either direction, what a print
reviewer would notice. The brief's framing ("a defect a reviewer finds in five
minutes") is a hypothesis this lane did not test.

### 4.6 The report partitions (B3)

From the same run, with the dust arm on and the hot arm off:

```
defect map      : 14626 hot, 1135 dust quads, arms dust (floor 8.0 e-, gain 0.22894 DN/e-)
hot             : examined 0, corrected 0, below floor 0, clipped 0, outside 0, no change 0
dust            : examined 22700, corrected 22700, clipped 0, outside 0, no change 0
samples changed : 90800 over 20 frames (4540.0 per frame)
```

`22700 = 1135 × 20`; `90800 = 22700 × 4`. `hot examined 0` is the arm being off,
and it is *distinguishable* from an arm that ran and found nothing. With both
arms on the same stack reads `hot: examined 292520, corrected 2220, below floor
290300` — `292520 = 14626 × 20` and `2220 = 111 × 20`, the 111 being exactly the
sites at the reproducible floor (P10). **The partition is not merely printed:
`stack.rs` `ensure!`s that it sums, and a report that does not reconcile is a
hard error (B4).**

---

## 5. Threats to validity

- **T1.** The map is built at **f/5.6**. Three corpus stacks are f/8 and three
  f/11; a smaller aperture makes a mote smaller and deeper. **Untested.**
- **T2.** The **Python builder and the Rust `detect_dust` are two
  implementations of one spec and I have not run both on the same real input.**
  Mitigated but not removed: the *shipping* path — load, apply, measure — is all
  Rust and is exercised on real RAWs in §4.5.
- **T3.** M48c fact 33 (rawpy's visible area is rawler's leading 7,028 columns,
  origin-aligned) is **inherited, not re-verified by me**. The last 4 sensor
  columns are recorded as `covered` separately from `sensor` — **unmeasured, not
  clean**.
- **T4.** Twelve subjects × 8 frames. A thirteenth subject could move a marginal
  p-value; it could not plausibly move p = 0.0025 or p = 1.0000.
- **T5.** Why the flats mis-locate by 10–25 quads is **not established**. A deep
  mote's bright high-pass ring fragmenting the component explains the (3202,121)
  cluster; the 25-quad offset at (3434,2305) is **unexplained**. Candidates: the
  CPL is a rotating element, and the flats were shot ~4.5 h after `bee-3-cpl`.
- **T6.** The `--merge pyramid` shipping path is **not** wired (§6.2).

---

## 6. What I built, and what I did not

### 6.1 Built

- `crates/strehl-core/src/defect_map.rs` — format (`to_text`/`from_text`/
  `load`/`save`), `DefectMapError` (12 variants, every one a refusal),
  `HotSite`/`DustQuad`, `Correction` + `Correction::parse`, `CorrectionReport` +
  `check_partition`, `HotFloor`, `DefectMap::apply` (sensor coordinates, refuses
  geometry mismatch, leaves clipped samples alone), `detect_hot`/`detect_dust`
  with census structs, and the `dust_residual`/`hot_residual` metric. **24
  commissioning tests.**
- `crates/strehl-core/src/lib.rs` — `pub mod defect_map;`, one line.
- `crates/strehl-cli/src/stack.rs` — `DefectPlan`, `defect_plan_from_env`,
  correction applied immediately after decode and before anything reads the
  frame, per-chunk `CorrectionReport` folded through `Partial::absorb`, printed
  and `ensure!`d.
- `experiments/BUILD-DEFECT/src/01..17` and their logs and JSON.
- `experiments/BUILD-DEFECT/out/defect-map-ILCE-7CM2.txt` (the flats map, kept
  as the record of P3) and `-photo.txt` (**the one that is correct**).

### 6.2 The shipping wire-up (added after the orchestrator took Q1)

**P21 (corrected — this was "not built", and now it is).**
`crates/strehl-cli/src/stack.rs` is the `argmax-baseline` negative control,
**not** the shipping `strehl stack`. The shipping path is `main.rs:797
Command::Stack → merge_cmd::run → run_pyramid`, with per-frame decode at
`merge_cmd.rs fn load_frame`. On the orchestrator's instruction I took that
patch myself. What landed:

- **`run_pyramid`** builds the plan **once** and prints a banner
  (`defect map      : … arms dust …` or `none (set STREHL_DEFECT_MAP to
  enable)`), then borrows it to the fold and to *both* confidence passes.
- **`load_frame`** applies it **between the levels check and
  `warp_frame_in_place`.** That ordering is the entire feature. The map's
  coordinates name **photosites**; after the warp the sample at (x, y) is a
  resampled blend of photosites from elsewhere, so the map addresses nothing
  and the defect has already been spread by the per-frame similarity.
  `dust_correction_must_precede_the_warp_to_land_on_the_defect` fails if those
  lines move below the warp;
  `with_an_identity_warp_the_two_orderings_are_bit_identical` proves that test
  measures the *ordering* and not the resampler.
- **`load_frame` is shared by the merge fold and the confidence pass
  deliberately** (its own doc comment says so), so one insertion covers both
  and the confidence map cannot end up measuring the correction instead of the
  merge.
- **The report** is folded across workers by a `DefectTally` of relaxed
  atomics — `merge_cmd`'s fold has no per-worker accumulator to hang a `&mut`
  on — then printed **and `ensure!`d** by the same
  `stack::print_and_check_defects` both paths call.

**P22 (MEASURED — the two call sites agree).** `stack.rs` and `merge_cmd.rs`
call one shared `stack::apply_defects`, and on `coffee-bean --limit 20` with
the photo map they return **identical** counts: `dust: examined 22700,
corrected 22700, clipped 0, outside 0, no change 0`, `samples changed 89074`.
Two independent paths through the same data reporting the same number is the
cross-check that the wiring is not doing something different in one of them.
**P22b (MEASURED — a correction can be right and still move nothing).** 89,074
of a possible 90,800 samples moved (98.10%). The 1,726-sample shortfall is
**not a bug and not a partial failure**: those are samples whose
black-subtracted signal was small enough that multiplying by 1.03–1.06 rounded
back to the *same* `u16`. A gain correction on a value of 20 DN at ×1.034 asks
for 20.7 and stores 21; at 8 DN it asks for 8.27 and stores 8. **There is a
quantisation floor on any multiplicative correction**, and near the black point
the correction is arithmetically correct and physically inert.

This is why `samples_changed` and `corrected` are **separate counters** and must
stay separate. `corrected` counts *quads the correction was applied to*;
`samples_changed` counts *stored values that actually moved*. A single merged
counter would have reported 89,074 "corrections" and quietly redefined the word
— and the 1.90% gap, which is a real property of the correction at low signal,
would have been invisible. Nobody reading a future shortfall should file it as a
defect without first checking the signal level: **the shortfall is the expected
reading, and equality would be the surprise.**

### 6.2.1 P23 — an architectural seam, and a guard over it

**P23 (MEASURED — the finding, which outlives this patch).**
`strehl-cli` has **two independent frame loaders**:

| loader | used by | defect correction |
|---|---|---|
| `merge_cmd.rs fn load_frame` | `run_pyramid` fold **and** both confidence passes | **applied** (§6.2) |
| `field_for` / `Scratch` | `run_estimator` | **absent** |

A per-frame correction added to one is **silently absent from the other**. That
is the fact, and it is not about dust: it is a property of the command surface
that the next per-frame correction anyone adds — a bad-column map, a per-frame
flat, a linearity LUT — will hit in exactly the same way, and will hit it
silently, because neither loader knows the other exists.

The observable failure is not "one backend lacks a feature". It is **"a
configured correction is silently not applied"** — the user exports
`STREHL_DEFECT_MAP`, passes `--merge estimator`, gets a clean exit and a
finished TIFF, and has no way to learn that the map was ignored. An
uncorrected render that *says nothing* is the worst available outcome, which is
the same principle that makes a malformed map file a hard error rather than a
skip.

**The remedy is a refusal, not a second wiring.** When a defect map is
configured *and* the estimator backend is selected, the command must
hard-error before any frame is decoded. Wiring the second loader would double
the number of places a correction must be maintained and would leave the seam
itself intact for the next feature; a refusal converts a silent wrong answer
into a loud stop, which is the outcome this project prefers whenever the two
are on offer.

**State plainly what that buys: the refusal is a *guard over* the seam, not a
*fix of* it.** After it lands, `strehl-cli` still has two loaders and they still
disagree about what a frame is. What changes is only that this *particular*
divergence can no longer be reached silently. The next correction added to
`load_frame` will be absent from `field_for` again, and will need its own guard,
because nothing structural prevents it. Closing the seam properly means one
loader — a larger change than this lane, and one that touches files owned by
other lanes.

**Status: BLOCKED, not done.** See §6.2.2.

### 6.2.2 P24 — the refusal is written but NOT applied: lane collision

**P24 (OBSERVED).** The orchestrator authorised the refusal on 2026-08-27. The
lane-safety check it required ran **first**, and it stopped the work:

```
> git --no-pager status --porcelain -- crates/strehl-cli/
 M crates/strehl-cli/Cargo.toml
 M crates/strehl-cli/src/main.rs
 M crates/strehl-cli/src/merge_cmd.rs      <-- the file the refusal needs
?? crates/strehl-cli/examples/build-plugin-field.rs
?? crates/strehl-cli/src/focus_plugin.rs
```

`merge_cmd.rs` carries **145 uncommitted lines** that are not mine (0 of them
mention `defect`; the new `focus_plugin.rs` and `examples/build-plugin-field.rs`
identify them as BUILD-PLUGIN's live work). `main.rs` carries 90 more.

The refusal has **no in-lane alternative**. `merge_cmd::run` dispatches
`MergeBackend::Estimator => run_estimator(opts)` at `merge_cmd.rs:2812`, and
`run_estimator` calls nothing I own — it never constructs a `DefectPlan`, which
is precisely *why* the correction is silently absent. Nothing in `stack.rs` or
`defect_map.rs` can observe that the estimator was selected. The check must be
inserted into the dirty file or it cannot exist.

Per the standing instruction — *"if BUILD-PLUGIN has committed to the file you
need, or has it dirty, stop and report — do not resolve a conflict yourself"* —
I stopped. **My committed work at `107b37e0` was verified intact and
unclobbered** (all eight `defect` sites still present in the working file).

**The patch, ready to apply.** It belongs at `merge_cmd.rs:2820`, immediately
after `align_cmd::preflight_ca_profile()?`, which is already the house idiom for
this exact situation — *"fail on configuration before a frame is read. An
invalid `STREHL_FIX_CA` otherwise surfaces only after the first decode
(53.4 s), which reads as a slow arm in a matrix."* The refusal is the same
argument with a different input:

```rust
    // A configured defect map that is SILENTLY NOT APPLIED is worse than no
    // map: the render finishes, exits zero, and the uncorrected motes are
    // indistinguishable from corrected ones. This arm loads frames through
    // `field_for`/`Scratch`, not `load_frame`, so the correction wired in
    // BUILD-DEFECT.md sec 6.2 does not reach it -- see P23, the seam this
    // guards. Refused at setup, before any decode, for the same reason
    // `preflight_ca_profile` is: a failure that costs 53 s of render first
    // reads as a slow arm rather than a misconfiguration.
    if let Some(plan) = crate::stack::defect_plan_from_env(&noise_free_probe())? {
        anyhow::bail!(
            "STREHL_DEFECT_MAP is set ({} hot sites, {} dust quads, arms {}) but \
             the `estimator` merge backend DOES NOT APPLY defect correction, and \
             this render would silently ignore it. The `pyramid` backend applies \
             it in sensor coordinates before the warp. Re-run without \
             `--merge estimator` (pyramid is the default), or unset \
             STREHL_DEFECT_MAP to render deliberately uncorrected.",
            plan.map.hot.len(),
            plan.map.dust.len(),
            plan.correction
        );
    }
```

Two tests, both required — *a refusal with no negative control is untested*:

1. `a_defect_map_with_the_estimator_backend_refuses_rather_than_ignoring_it` —
   set `STREHL_DEFECT_MAP`, select `MergeBackend::Estimator`, assert non-zero
   exit and that stderr names `estimator`, `pyramid`, and "not appl".
2. `the_estimator_backend_runs_normally_with_no_defect_map_configured` — the
   negative control, asserting the guard is not universal.

**One open design point for whoever applies it**, stated rather than guessed:
the snippet above needs a `NoiseModel` to call `defect_plan_from_env`, but at
`run_estimator`'s preflight no frame has been decoded, so no `NoiseModel`
exists yet — that is the *point* of refusing there. The clean fix is to split
the env *parse* from the plan *build* (`defect_map_configured() -> Result<bool>`
reading only `STREHL_DEFECT_MAP`), so the guard needs no calibration. That is a
small addition to `stack.rs`, which is in my lane; I have not made it because
it would be dead code until the `merge_cmd.rs` half can land, and committing a
`pub(crate)` function with no caller invites someone to wire it wrongly.

**`RENDER_ENV` was closed in the same commit.** `STREHL_DEFECT_MAP`,
`STREHL_DEFECT_ARM` and `STREHL_DEFECT_HOT_FLOOR` are now cleared by
`byte-freeze.rs` before each row renders. Off-by-default is a property of the
*code*; it says nothing about an operator who has exported the variable in
their shell, who would otherwise render a corrected stack and compare it to an
uncorrected hash. Per the header of `byte-freezes.tsv` this is the
`STREHL_ALIGN=0` defect, already committed twice in this repository; this is
the first variable added to that list **in the same commit as the feature that
reads it**.

### 6.3 My own defects, disclosed

1. **A half-rolled control is not a control.** Rolling 9 of 18 captures left a
   median over 18 still set by the 9 that corresponded: **9,966 false sites**,
   1.41× the real count, which reads like a *failed* control. Repaired: 0/0/0.
2. **Border 31 was wrong.** Three passes of a half-width-30 box have support
   **90**. Measured reach 40; shipped 60.
3. **A silent axis bug.** `hot-recur.npy` is `(2344, 3514, 4)` with plane on the
   **last** axis; `recur[p]` read the first four *rows* and returned 22 sites
   against a census of 14,626. Only an impossible number caught it.
4. **A commissioning plant sat on the detector's own floor.** 12 e⁻ × 0.229
   DN/e⁻ = 2.75 DN against a 2.9 DN cut, so 2 of 3 "finds" were noise. Raised to
   40 e⁻ and the floor documented.
5. **My commissioning gate was mis-specified.** A conjunction of *m* independent
   GREEN arms each at α = 0.05 fails with probability 1 − (1 − α)^m = **14.3%**
   for m = 3 — one time in seven on a correctly calibrated procedure. One arm
   read p = 0.0424 and the gate refused. The bar is now a **formula** (α/m),
   fixed by the number of arms rather than chosen after seeing which arm failed,
   and **both verdicts are reported** in `data/15-corner.json`.
6. **Scripts 10 and 11 nearly shipped a blind search.** Script 11 got its roll
   null to 0/0/0 and its real arm to 50 components — a clean story — while
   **missing the planted 2.5% disc at every setting**. The improvement arm is
   the only reason that is visible. Its cause was using a *sign* test across 12
   subjects, which carries no depth information and kept 21,504 quads where
   chance predicts 2,009.

---

## 7. What I would do next

1. ~~**Wire `merge_cmd::load_frame`**~~ — **DONE**, §6.2, commit `107b37e0`.
   `RENDER_ENV` closed in the same commit.
2. **Apply the estimator refusal** (§6.2.2 P24) once `merge_cmd.rs` is free.
   Blocked on a lane collision, not on a question.
3. **Settle T5** — re-shoot flats immediately after a subject stack, without
   touching the CPL, and see whether the 25-quad offset persists.
4. **Aperture transfer (T1)** — see Q4 below; this is an **open question, not a
   caveat I have retired**.
5. **Run the Rust `detect_dust` on the real flats** to close T2, via a small
   `strehl defect-map build` subcommand.
5. **The hot arm remains a null.** Do not spend more on it without a body whose
   in-situ amplitude exceeds M101's 1.5 DN.

---

## 8. Facts, disciplines and questions

**Facts:** P1–P21 above.

**Disciplines**

- **D1.** A control that leaves *any* input corresponding is not a control. Roll
  **all** of them.
- **D2.** A commissioning suite of degradations cannot separate a **blind**
  metric from a **perverse** one. Plant an improvement in every suite.
- **D3.** Commission a *local* procedure **where it is used**. A statistic
  commissioned mid-frame and applied at the edge is uncommissioned.
- **D4.** A conjunction of *m* GREEN arms at level α is a gate that fails
  1 − (1−α)^m of the time by construction. Correct for *m*, by formula, in
  advance.
- **D5.** When a component's *median* and its *minimum* disagree in sign, the
  component is mis-registered. Re-locate before you believe the footprint.
- **D6.** A defect map derived from calibration targets must be **confirmed in
  the photographs** before it is applied to them. §2 P3 is the whole argument.

**Questions**

- **Q1.** Why do the flats mis-locate by 10–25 quads (T5)?
- **Q2.** Does the (3434,2305) mote deepen at f/11, and by how much?
- **Q4 (OPEN — the aperture transfer, unclaimed).** **The shipped map is
  measured at f/5.6 only, and I do not claim it transfers.** What is
  established is *coverage*, not transfer: P2 measured 20 of the 26 subject
  stacks at f/5.6, so the map is calibrated at the aperture most of the corpus
  was shot at. Those are different statements and the difference matters,
  because dust sits a small distance above the sensor and its shadow **sharpens
  and deepens as the aperture closes** — the same mote should read *more*
  negative at f/11 than the −8.24% measured at f/5.6, and the correction map
  would then be an under-correction of unknown size. Applying an f/5.6 map to
  an f/11 frame is a partial fix whose residual nobody has measured.

  **The capture that would settle it**, stated specifically so it can be shot
  rather than debated: a single subject, tripod-locked and untouched between
  frames, **20 frames at f/5.6 and 20 at f/11 with nothing else changed** —
  same focus point, same CPL orientation, same session, exposure compensated to
  match the histogram. Run the §4.1 discriminator at the two known cores
  (3202,121) and (3434,2305) on each set. That yields the depth ratio
  `d(f/11) / d(f/5.6)` directly, with the same commissioned local null and the
  same p-values, and it is the *only* comparison that isolates aperture,
  because both sets come from one sensor state and one session. The 26-stack
  corpus **cannot** answer it: its f/8 and f/11 stacks are different subjects
  shot on different days, so a depth difference there confounds aperture with
  every other thing that changed.

  Until that is shot, the honest scope of the map is **f/5.6**, and §5 T1
  stands.
- **Q3 (ANSWERED by the orchestrator — the rationale for the default).** The
  feature ships **opt-in**, and the reason is a *correctness* argument, not
  caution. A defect map is a statement about the sensor **on a particular
  date**. The two motes are real today. But if the owner cleans the sensor, a
  default-on map applies a **+8% brightening to a spot where nothing is
  wrong**: it manufactures the exact defect it was built to remove, and does it
  **silently**, because nothing downstream can distinguish a corrected mote
  from an invented one. An explicit `STREHL_DEFECT_MAP` sidecar keeps the
  staleness visible at the call site, where somebody can notice the file is a
  year old.

  This is the same failure as §2 P3 — correcting at the *flats'* coordinates
  would have brightened clean pixels beside a mote it missed — moved one step
  later **in time** rather than in space. P3 was a map wrong about *where*;
  a stale map is one wrong about *when*. Both fail the same way: they write a
  confident correction onto pixels that did not need one, and the output cannot
  be told apart from a correct one.

  The *visibility* half of the original Q3 is **withdrawn as unanswerable from
  what I measured** — see P20b. Amplitude ×1.034 in delivered sRGB is measured;
  visibility is not established, and this report asserts nothing about it.

---

## 9. Rules discharged

| Rule | Where |
|---|---|
| 3 — inject, never derive | `DefectPlan.gain_dn_per_e` comes from the injected `NoiseModel`, not re-derived |
| 28 — local fact numbering | P1–P24 |
| 33 — never `-q`; a run with no `Compiling` line is not evidence | §10 quotes the `Compiling` lines |
| 40 — prior-art search first | §0.2; it reshaped the mission |
| Nothing is true until measured | Every number here is quoted from a persisted log in `experiments/BUILD-DEFECT/out/` |
| Commission every metric | §4.2, P15/P16/P17 — RED, GREEN **and** an improvement arm |
| A search must be able to fail | P5, P13, and the two explicit refusals in scripts 12 and 14 |
| Print, then TEST | §4.6 — both paths `ensure!` the partition via `stack::print_and_check_defects` |
| Partition into counted outcomes | §4.6; `check_partition`; `every_site_lands_in_exactly_one_counted_outcome` |
| Typed errors over silent defaults | `DefectMapError`, 12 refusals; `a_typod_correction_arm_errors_rather_than_falling_back_to_the_default` |
| Off by default | `Correction::default()` is both arms off; `the_default_correction_is_off_and_changes_no_byte`; §8 Q3 is the correctness argument for the default |
| 47 — record the environment beside the hash | `STREHL_DEFECT_MAP`/`_ARM`/`_HOT_FLOOR` added to `RENDER_ENV` in the same commit as the wire-up (§6.2) |

---

## 10. Verification

**After the shipping wire-up** (`merge_cmd.rs` + `RENDER_ENV`), re-run in full:

```
cargo test --release -p strehl-core -p strehl-cli
   Compiling strehl-cli v0.0.0 (C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli)
     Running unittests src\main.rs
running 110 tests
test result: ok. 110 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.49s
     Running tests\byte-freeze.rs
running 5 tests
test the_frozen_renders_still_produce_their_recorded_bytes has been running for over 60 seconds
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 170.42s
     Running unittests src\lib.rs
running 510 tests
test result: ok. 510 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 4.21s
```

**625 tests, 0 failed. The byte-freeze HOLDS after the wire-up. Neither hash
moved, and `byte-freezes.tsv` was not touched:**

```
freeze `coffee-bean-20-gate2-unaligned` HOLDS:
  88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620
  (49450019 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar` HOLDS:
  52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206
  (49450019 bytes, alignment on-sidecar-override, 10 chunks of <= 2 frames,
   20 placed / 0 refused) -- reproduced twice
```

A typo'd arm errors rather than falling back:

```
> $env:STREHL_DEFECT_ARM="dsut"; strehl argmax-baseline ...
Error: STREHL_DEFECT_ARM="dsut" (the arms are "none", "hot", "dust", "both")
Caused by:
    unknown defect correction arm "dsut"; the arms are "hot", "dust", "both" and "none"
exit=1
```

### 10.1 The command that applies the correction

```powershell
$env:STREHL_DEFECT_MAP = "experiments\BUILD-DEFECT\out\defect-map-ILCE-7CM2-photo.txt"
$env:STREHL_DEFECT_ARM = "dust"
strehl.exe stack D:\personal\macro\coffee-bean --out out.tiff --srgb --auto-exposure --limit 20
```

Real output from that run, through the **shipping** `pyramid` path:

```
merge backend   : pyramid (default)
defect map      : 14626 hot, 1135 dust quads, arms dust (floor 8.0 e-, gain 0.22894 DN/e-)
--- defect correction (MEASURED) ---
hot             : examined 0, corrected 0, below floor 0, clipped 0, outside 0, no change 0
dust            : examined 22700, corrected 22700, clipped 0, outside 0, no change 0
samples changed : 89074 over 20 frame loads (4453.7 per frame)
folded          : 20 / 20 frames in 22.1 s (1.11 s per frame, 4 workers)
wrote           : ... (7032 x 4688, 16-bit RGB, sRGB ...)
```

`hot: examined 0` is the arm being **off**, and it is distinguishable from
`corrected 0` with the arm on — which is the whole reason the outcomes are
partitioned rather than summarised. Unset `STREHL_DEFECT_MAP` and the banner
reads `defect map      : none (set STREHL_DEFECT_MAP to enable)` and no
correction block is printed at all.

---

## 11. The self-validating map: the design holds, and it overturns my own default

Added after `V-EYES` measured the delivered corpus and the orchestrator
withdrew the opt-in decision. Scripts `20`–`23`, logs in `out/`.

### 11.1 What changed my mind, and what did not

The orchestrator's staleness argument — *a stale map applies a brightening to a
spot where nothing is wrong, and nothing downstream can tell a corrected mote
from an invented one* — is **still correct, and §11.5 measures its cost at
+8.6 to +16.4 percentage points.** What was wrong was the premise it was
attached to: that the amplitude was too small to matter. `V-EYES` measured mote 2
at **−13.28%** on `highly-angled-ruler-mm-cpl`, present in **18 of 26** delivered
images, and *saw* it unstretched as a ~45 px grey disc on near-white.

Both positions being correct at once is the signature of a wrong framing, and
the orchestrator's proposed reframing is right: **make the map self-validating at
the point of use.** A stale map cannot manufacture a defect it is required to
observe first. I set out to find the flaw in it and instead found a stronger
version of it (§11.4).

### 11.2 The one thing that could have sunk it, and did not

**P25 (MEASURED).** Per-stack detection has sufficient power. Over 10 stacks,
8 frames each, reading raw Bayer via `quad_mean(raw_image_visible)` — sensor
coordinates, before any warp — scored against a 400-draw local null
(`src/20-selfvalidate.py`):

```
FIRES  mote1 6/10   mote2 8/10   CONTROLS 0/40  (controls must be 0)
```

The committed map established these motes at `p = 0.0025` by **pooling 12
stacks**. The concern was that one stack has a twelfth of that evidence and would
silently no-op. It does not: a single stack reaches the same `p = 0.0025` floor,
because the bar is a *local spatial* null within one frame rather than a
cross-subject recurrence test, and one frame already contains 400 independent
control draws.

**P26 (MEASURED).** Where it declines, it declines for the right reason.
`tweezers-cpl` (`p = 0.3092`) and `wrapped-text-1` (`p = 0.2519`) are exactly the
two stacks whose control sites read −8.4% and −15.3% — busy background, wide
null, no detection. **This is the requirement working, not failing.** V-EYES
independently notes *"Subjects with no smooth background at that spot cannot show
it"*. The test's power and the defect's visibility are governed by the *same*
quantity — local background smoothness — so **where the check cannot see the
mote, neither can a viewer.** That correlation is what makes skipping safe rather
than merely cheap.

### 11.3 A coordinate bug of mine, disclosed

The first run of `20-selfvalidate.py` read `raw.raw_image`; the map was built on
`raw.raw_image_visible`. `raw_image` includes the masked optical-black border, so
every site was offset and mote 2 read **+54.8%, +22.2%, +44.3%** on four stacks —
absurd values for a high-pass residual, which is what exposed it. Fixed in
`out/20-selfvalidate.log`. **Any per-stack check must read the same array the map
was written against**, and the map format does not currently record which one.
See Q5.

### 11.4 The map must nominate the location and must NOT dictate the amplitude

This is the part I did not expect and it strengthens the design.

**P27 (MEASURED).** Depth at the *same* sensor site varies **1.91×** across
stacks (`src/21-depth-aperture.py`):

| subject | f/ | measured | vs map −8.236% |
|---|---|---|---|
| coffee-bean | **8.0** | **−14.758%** | **1.79×** |
| flower-bud-alone-cpl | 5.6 | −9.380% | 1.14× |
| pencil-steep-angle-cpl | 5.6 | −8.814% | 1.07× |
| highly-angled-ruler-mm-cpl | 5.6 | −8.585% | 1.04× |
| couch-fibers-cpl | 5.6 | −8.467% | 1.03× |
| lavendar-cpl | 5.6 | −8.387% | 1.02× |
| bee-3-cpl | 5.6 | −7.994% | 0.97× |
| leaf-2-cpl | 5.6 | −7.737% | 0.94× |

The seven f/5.6 stacks span **0.94×–1.14×** — tight. The one f/8 stack is
**1.79×**. This is the direction Q2 predicted (*"a smaller aperture makes a mote
smaller and deeper"*) and it is the first measurement of it.

**P28 (ARGUED, and the caveat is load-bearing).** The printed
`corr(f-number, depth) = −0.9758` **is not a correlation and must not be quoted
as one.** It is a two-group comparison with **n = 1** in the f/8 group; a
correlation across seven points at one x-value and one point at another is
determined entirely by the single outlier. The *direction* is consistent with the
physics and with Q2's prediction; the *slope* is one stack. Q4 stays open.

**P29 (DERIVED).** The design consequence does not depend on the cause. A
correction that applied the **map's** gain would, on `coffee-bean`, remove 8.2
points of a 14.8-point defect and leave a 6.6-point mote; on a shallower stack it
would over-correct into a bright spot — **the inverse defect, manufactured**. So:
**shape from the map, amplitude from the frames in front of us.** Scaling in
log-gain space, `g' = exp(ln(g) · s)` with
`s = ln(1/(1−|d_meas|)) / ln(1/(1−|d_map|))`.

**P30 (MEASURED).** With amplitude taken from the data
(`src/22-selfvalidating.py`), all five firing stacks correct to under 0.7%
residual — **including the f/8 stack at 1.79× the map's nominal**:

| subject | measured | after correction |
|---|---|---|
| highly-angled-ruler-mm-cpl | −8.585% | **−0.476%** |
| pencil-steep-angle-cpl | −8.814% | **−0.606%** |
| coffee-bean (f/8) | −14.758% | **−0.672%** |
| couch-fibers-cpl | −8.467% | **−0.478%** |
| lavendar-cpl | −8.387% | **−0.518%** |

**94–96% of the defect removed**, uniformly across a 1.79× amplitude range.
**Taking amplitude from the data makes the aperture-transfer question (Q4) moot
for the correction path** — the correction no longer needs to know the aperture,
because it measures the depth it is about to remove. Q4 remains open as a
question about the *map*, but it no longer gates shipping.

### 11.5 The arm that decides the design

**P31 (MEASURED). The STALENESS arm.** Divide the real mote out of the frames —
simulating a sensor that has since been cleaned — then run the check completely
unmodified. It must decline to correct.

```
subject                       measured        p  action  after corr     STALE->     MANUF
highly-angled-ruler-mm-cpl     -8.585%   0.0025 CORRECT     -0.476%       SKIP    +8.93%
pencil-steep-angle-cpl         -8.814%   0.0025 CORRECT     -0.606%       SKIP    +9.18%
coffee-bean                   -14.758%   0.0025 CORRECT     -0.672%       SKIP   +16.44%
couch-fibers-cpl               -8.467%   0.0025 CORRECT     -0.478%       SKIP    +8.93%
lavendar-cpl                   -8.387%   0.0025 CORRECT     -0.518%       SKIP    +8.64%
tweezers-cpl                   -5.726%   0.3092    SKIP           -          -         -
examined 6   corrected 5   skipped 1   (sums to total)
all arms PASS -- self-validation blocks the stale-map failure mode
```

**Five of five cleaned-sensor cases SKIP.** The failure mode the opt-in default
existed to prevent is **unreachable**, not merely unlikely.

**P32 (MEASURED). The MANUFACTURE arm** quantifies what the guard is worth:
applying the correction at a site with no mote injects **+8.64% to +16.44%**
brightening. That is the defect an unguarded default-on map would create, and it
is the same order as the defect it removes. **The guard is load-bearing, not
decorative** — which is the measured form of the orchestrator's original
objection, and the reason it should be recorded as vindicated rather than
withdrawn.

**P33 (MEASURED). Commissioned in both directions**, per rule and per the two
instruments this project has already caught reading backwards:

| arm | expected | measured |
|---|---|---|
| planted −4% disc | FIRE | fires 4/4, `p = 0.0025`, depth −3.79% to −5.03% |
| planted **+4% bright** disc | NO FIRE | 0/4 fire, `p = 0.9975–1.0000` |
| **improvement**: mote divided out | NO FIRE | 5/5 skip (P31) |
| clean control sites | NO FIRE | 0/40 fire |

The perverse arm reads `p ≈ 1.0` rather than merely "below the bar" — the
statistic moves the *right way* on a brightening, so it is not blind to sign.

### 11.6 Cost, measured

**P34 (MEASURED).** The null draws reach 400 quads, so a 560-quad half-window
around each site is sufficient:

```
full-frame residual  0.370 s/frame
cropped   residual   0.016 s/frame  (23.5x cheaper)
two sites            0.032 s/frame
agreement full vs cropped at mote2: -9.4444% vs -9.4444%  (delta 0.0000 pp)
```

**Exact agreement, 23.5× cheaper.** Total per stack at 8 frames: **0.26 s of
compute** — one frame's worth of the 0.26 s/frame budget, for the whole stack —
plus **~2.5 s of decode** if the check runs as a separate preflight pass
(0.308 s/frame × 8). On a 105–299 frame stack that is under 1%; on a 20-frame
stack it is closer to 10%, and folding the sample into an existing decode pass
would remove it entirely.

**P35 (DERIVED).** Where it reads: `quad_mean(raw_image_visible)` is the raw
Bayer array, black-subtracted, 2×2 averaged — the same coordinate system the map
is written in and the same one the correction is applied in, strictly **before**
the aligner. **There is no interaction with the warp**, by construction, and that
is the same ordering argument that justified the original wire-up.

### 11.7 My recommendation, and the decision that is not mine

**The design holds. I recommend building it and defaulting it ON**, with
amplitude taken from the frames (P29) rather than from the map.

**But default-ON moves both byte-freezes, and that is the orchestrator's call.**

**P36 (MEASURED).** `coffee-bean` is a byte-freeze subject, and it fires under
the freeze's exact configuration (`src/23-freeze-check.py`):

```
coffee-bean total frames: 105
  first 20 (freeze config) depth  -14.859%  p 0.0025  FIRES True
  all 105                  depth  -14.758%  p 0.0025  FIRES True
```

So enabling the correction by default **will** change the rendered bytes of both
`coffee-bean-20-gate2-unaligned` and `coffee-bean-20-gate2-sidecar`. Unlike every
previous freeze movement I have reported, this one is **intended** — it is the
feature working. `byte-freezes.tsv` is the orchestrator's file and I will not
re-baseline it, so this needs an explicit decision before the default flips.

### 11.8 New open question

- **Q5 (CLOSED at §12.6).** The map format records `sensor` and `covered` geometry but not
  **which raw array its coordinates are indexed against**
  (`raw_image` vs `raw_image_visible`). That ambiguity cost me a full run (§11.3)
  and would silently mis-register any future consumer. A `frame raw_image_visible`
  key in the header would close it. **Not added: the format is versioned and
  changing it is a compatibility decision, not a lane decision.**
  *(Update: the orchestrator took the decision. Closed in §12.6.)*

---

## 12. BUILT AND SHIPPED — the self-validating map (shipped default ON; **reverted to opt-in in §13.1**)

> **Read §13 first.** Everything measured in this section stands, but its
> *default* does not: a second lane could not reproduce mote 2, and the
> correction was returned to opt-in pending adjudication. Every "default ON"
> and "on by default" phrase below describes the state of the tree between
> commits `49227061` and the §13 revert, not the shipping default.

§11 recommended the design and asked for a decision. The orchestrator took it and
added one requirement before default-ON: a **stationarity arm** proving the check
can distinguish sensor dust from genuine dark subject detail that happens to land
on the mote's coordinates. That arm is §12.1. It passed, and it changed the design
in a way I did not expect (§12.2).

This section is what was built, what it measures, and the one prediction in my own
§11.7 that turned out to be **wrong** (§12.4).

### 12.1 The stationarity arm (the one the orchestrator required)

**The threat.** An eye, a dark hair, a shadow edge at `(3434, 2305)`. The check
reads a local darkening, fires *correctly by its own definition*, and the
correction then brightens real image content. On near-white background this is
unlikely; across 27 subjects it is a matter of time.

**The discriminator the orchestrator named, and it is the right one.** A mote is
fixed in sensor coordinates. The subject is not — the bracket drifts and breathes,
and the aligner's entire existence is the proof. So a mote's darkening is
stationary in raw sensor coordinates; subject detail at the same raw coordinate
varies as the feature translates through it.

**Implemented as `presence`**: the fraction of individually-examined frames in
which the site reads at least 1.0% deep. A stationary mote is present in every
frame; a feature drifting through the site is present in some and absent in
others, *even when the pooled depth still looks convincing*.

`src/24-stationarity.py`, 4 stacks, 5 arms each — including both a planted
**defect** and a planted **improvement**, per standing policy:

```
bars: p <= 0.0025  AND  pooled depth <= -1.5%  AND  presence >= 0.75

subject                   arm                        depth        p  presence  fires
highly-angled-ruler-mm-cp REAL mote2               -8.585%   0.0025      1.00   True
                          FIXED planted -8%        -7.847%   0.0025      1.00   True
                          MOVING planted -8%       -0.044%   0.3766      0.25  False   (moved 126 quads)
                          PERVERSE planted +8%      7.608%   1.0000      0.00  False
                          IMPROVE mote removed     -0.099%   0.3142      0.00  False
lavendar-cpl              REAL mote2               -8.387%   0.0025      1.00   True
                          FIXED planted -8%        -7.759%   0.0025      1.00   True
                          MOVING planted -8%       -0.033%   0.3142      0.25  False
                          PERVERSE planted +8%      7.710%   1.0000      0.00  False
                          IMPROVE mote removed     -0.005%   0.3192      0.00  False
couch-fibers-cpl          REAL mote2               -8.467%   0.0025      1.00   True
                          FIXED planted -8%        -7.639%   0.0025      0.88   True
                          MOVING planted -8%       -0.423%   0.5536      0.50  False
                          PERVERSE planted +8%      7.854%   1.0000      0.00  False
                          IMPROVE mote removed      0.129%   0.6459      0.38  False
leaf-2-cpl                REAL mote2               -7.737%   0.0025      1.00   True
                          FIXED planted -8%        -6.862%   0.0025      1.00   True
                          MOVING planted -8%       -1.141%   0.3466      0.62  False
                          PERVERSE planted +8%      8.753%   1.0000      0.25  False
                          IMPROVE mote removed      0.964%   0.8678      0.38  False

examined 4 stacks; all arms PASS
```

Read the arms as a matrix rather than a list:

- **REAL / FIXED** — fires 4/4 and 4/4. The check is not blind.
- **MOVING** — fires 0/4. Subject detail of *identical depth and size* that moves
  is rejected. This is the arm the orchestrator asked for.
- **PERVERSE** — a planted **+8% bright** disc, i.e. the inverse defect. `p` pins
  at exactly **1.0000**, the ceiling of a one-sided 400-sample null. This is the
  arm that would have caught `tri.blur_equiv` and `overshoot_frac`: a statistic
  bounded below at zero cannot produce a 1.0000, and one that scored a planted
  gain as a defect would have fired here.
- **IMPROVE** — the real mote **divided out** of the real frames before the check
  runs, i.e. a genuine improvement to a genuine defect at a real site. Fires 0/4,
  depths −0.10% to +0.96%. The check does not fire on a site that has been fixed,
  which is precisely the cleaned-sensor case §11 was built around.

### 12.2 `presence` is load-bearing — and I nearly shipped it as dead weight

**A defect I found in my own result.** In every MOVING arm above, the pooled depth
also collapsed (−0.03% to −1.14%), which fails the −1.5% depth bar *on its own*.
So on this evidence `presence` never actually decided anything. Per rule — a gate
condition nothing has been shown to decide is dead weight that can only produce
false SKIPs — I had to either show it earns its place or delete it.

`src/25-drift-sweep.py` sweeps the drift scale from 1.000 (stationary) to 1.070
(the fitted scale another lane measured between a middle frame and its master on
`bee-3-cpl`) and records **which bar rejects first**:

```
leaf-2-cpl  (site is 1529 quads off centre)
  scale      shift     depth        p  presence   p ok    dep ok  pres ok   FIRES
  1.000       0.0q   -6.862%   0.0050      1.00   False   True    True      False
  1.004       5.1q   -6.864%   0.0025      1.00   True    True    True      True
  1.008      11.2q   -6.792%   0.0025      1.00   True    True    True      True
  1.012      17.3q   -6.784%   0.0025      0.62   True    True    False     False
  1.016      23.5q   -6.760%   0.0025      0.62   True    True    False     False
  1.020      29.6q   -6.718%   0.0025      0.62   True    True    False     False
  1.030      44.9q   -5.633%   0.0125      0.62   False   True    False     False
  1.050      75.7q   -3.063%   0.0599      0.62   False   True    False     False
  1.070     106.3q   -1.141%   0.2494      0.62   False   False   False     False

WHERE EACH BAR FIRST REJECTS
  lavendar-cpl         depth bar: scale 1.030 (45 quads)    presence bar: scale 1.016 (24 quads)
  leaf-2-cpl           depth bar: scale 1.070 (106 quads)   presence bar: scale 1.012 (17 quads)
```

**P37 (MEASURED). `presence` is decisively load-bearing.** On `leaf-2-cpl` at
scale 1.020 — 30 quads of travel, well inside the drift a real bracket has — a
**moving** −8% disc reads depth **−6.718% at p 0.0025**. Both other bars pass. It
is only `presence` (0.62) that rejects it. Without that bar the correction would
have brightened moving subject content at a −6.7% amplitude and reported it as a
confirmed mote. The 126-quad displacement in §12.1 was simply too generous to the
check; the sweep is the arm that actually tests it.

**The honest limit, stated rather than hidden.** Below roughly **11 quads** of
travel all three bars fire on moving content, and at scale 1.000 they fire by
construction. **A genuinely motionless dark subject feature is not separable from
dust by a motion-based test.** That is a property of the discriminator, not a bug
in it: at zero travel the two hypotheses are observationally identical. What
bounds the damage is that the correction is a **multiplicative brightening capped
at ×1.25 over a ~45 px disc**, applied only where the site also clears p ≤ 0.0025
and −1.5%.

**One false SKIP, disclosed.** `leaf-2-cpl` at scale 1.000 did **not** fire
(p = 0.0050) — one null sample landed as deep as the planted mote on that busy
background. A genuine planted mote was declined. That is a miss in the **safe**
direction and it is the price of a 0.0025 bar; it is not corrected for.

### 12.3 Commissioned in Rust, not only in Python

The Python above is the design evidence. The shipping code is Rust, and a
commissioning suite that only ever ran against the prototype proves nothing about
what renders. `crates/strehl-core/src/defect_map.rs` carries **17 new tests**
mirroring every arm on a 600×600 synthetic sensor, including:

- the planted **improvement** arm and the **perverse** (inverted-sign) arm;
- a test asserting the `NotStationary` verdict specifically — tuned to 12 quads of
  travel so it lands in the presence-only band from §12.2. Because the three bars
  are checked **in order** (`NotSignificant` → `TooShallow` → `NotStationary`), a
  `NotStationary` verdict is *proof* that p and depth both passed. That is the
  §12.2 finding pinned as an executable assertion: if someone deletes the presence
  bar, this test fails rather than the correction quietly widening;
- `depth_scale` recovering the published −3.63% / −8.24% nominal depths from the
  gains that encode them, so `Mote::map_depth` cannot disagree with the map;
- the `coords` header key (§12.6) rejecting an absent value and a typo'd one.

```
cargo test --release -p strehl-core
test result: ok. 531 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

### 12.4 THE BYTE-FREEZE DOES NOT MOVE — my §11.7 prediction was wrong

§11.7 predicted that default-ON "**will** change the rendered bytes of both
`coffee-bean` rows", and the orchestrator authorised a re-baseline on that basis.

**That prediction was wrong, and the reason is the §6.2.1 seam.**

**P38 (MEASURED).** Every row in `byte-freezes.tsv` is rendered with
`--merge estimator`, hardcoded in `byte-freeze.rs::argv` (line 538). The defect
correction lives in `stack.rs`'s `load_frame`, which is the **pyramid** loader.
The estimator loads through `field_for`/`Scratch`. **No row in that registry has
ever been rendered with the correction, and none can be.** Flipping the default
therefore cannot move those bytes — it makes those rows **exit non-zero**, because
`preflight_defect_backend_support` (§12.5) refuses to render an estimator stack
with a correction configured.

So the harness now sets `STREHL_DEFECT=off` explicitly, hardcoded beside
`--merge estimator` and for the same stated reason, with the same expiry
condition: *the day a pyramid row is added, this must become a registry column.*
This is not the harness suppressing a feature to keep a hash still. It is the
harness **spelling out the value these rows already render under**, which the
registry header demands of every variable: "`unset` is a VALUE, spelled out, never
an empty field."

**Measured result — both rows reproduce bit-exactly. No re-baseline is required.**

Verified in a **detached `git worktree` at pinned commit `7eea5f6e`** containing
exactly five changed files, all mine — six other agents are writing to the working
tree and "the tests pass" there is not a statement about my code:

```
freeze `coffee-bean-20-gate2-unaligned` HOLDS: 88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620
    (49450019 bytes, alignment off, 10 chunks of <= 2 frames) -- reproduced twice
freeze `coffee-bean-20-gate2-sidecar`   HOLDS: 52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206
    (49450019 bytes, alignment on-sidecar-override, 10 chunks of <= 2 frames, 20 placed / 0 refused) -- reproduced twice

byte-freeze     : 5 passed; 0 failed   (STREHL_FREEZE_REQUIRE=1, so a skip would have failed)
strehl-cli      : 113 passed; 0 failed
strehl-core     : 531 passed; 0 failed
```

Re-measured a second time after the P39 geometry fix, in a fresh worktree at
pinned `25313471`: both hashes hold, reproduced twice, same suite counts. A
verification that is not repeated after the next change is a verification of the
previous change.

**This is a result, not the absence of one.** The prediction written *before* the
render was that they could not move, because the correction is unreachable from
this backend — and the freeze is now a **specificity control** on that claim. If a
row had moved, the correction would have been reaching a code path it is not wired
into.

**And it means the corpus has no byte-frozen evidence of the correction at all.**
The registry cannot acquire any until it grows a pyramid row. Logged as **Q7**.

`STREHL_DEFECT` is in `RENDER_ENV` in the same commit, alongside `_MAP`, `_ARM`
and `_HOT_FLOOR`. Its polarity is now **inverted** from when those were added: the
hashes are measured with the correction *deliberately off*, so an operator with
`STREHL_DEFECT=on` exported in their shell would… still get the refusal, not a
wrong hash. The clear is kept anyway, because relying on that is relying on a
second feature to cover for a missing entry.

### 12.5 The estimator refusal, landed (§6.2.2 discharged)

Parked in §6.2.2 for a lane collision; the seam opened and it is in.

`merge_cmd::preflight_defect_backend_support(backend)` fires **at command setup,
before any frame is decoded** — a refusal surfacing after 53.4 s of decoding reads
as a slow arm in a matrix rather than as a configuration error. Verified live:

```
$ strehl stack D:\personal\macro\coffee-bean --limit 20 --gate 2.0 --out ...
build           : strehl 0.0.0
merge backend   : estimator (inferred from --gate; pass --merge pyramid to override)
Error: REFUSING TO RENDER: the sensor defect correction was NOT applied.

A correction is configured (the map embedded in this build, arms `dust`), but the
`estimator` merge backend does not apply it. The estimator loads frames through a
different path from the one the correction is wired into, so this render would
silently contain the uncorrected dust.

This is an error, not a warning; nothing was rendered. Either:
  - run the `pyramid` backend, which applies the correction, or
  - set STREHL_DEFECT=off to render without it deliberately.
```

Exit code 1, **before the first decode**.

**It takes the backend, not the options, so that it has a negative control.** A
refusal tested only in the arm where it fires cannot be distinguished from a
refusal that fires always. `the_estimator_refuses_a_configured_defect_correction_it_cannot_apply`
has four arms:

| arm | input | expected |
|---|---|---|
| fires | estimator + default (on) | `Err`, naming `estimator`, `pyramid`, "not applied", "refusing", "not a warning" |
| control (backend axis) | **pyramid** + same correction | `Ok` — pyramid is the backend that *does* apply it |
| control (config axis) | estimator + `STREHL_DEFECT=off` | `Ok` — the arm the brief asked for |
| control (arm axis) | estimator + `STREHL_DEFECT_ARM=none` | `Ok` — a map that corrects nothing drops nothing |
| typo | `STREHL_DEFECT=0` | `Err` naming the variable **and** the value |

```
test merge_cmd::tests::the_estimator_refuses_a_configured_defect_correction_it_cannot_apply ... ok
test result: ok. 113 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
```

**The refusal is a guard OVER the seam, not a fix OF it.** `strehl-cli` still has
two independent frame loaders and the next per-frame correction anyone adds will
hit the same seam silently. That finding stands as §6.2.1.

### 12.6 Q5 closed — the map format now names its coordinate space

Format `VERSION` **1 → 2**. New required header key:

```
coords active
```

`active` = coordinates index the **visible/active** array (`raw_image_visible`);
`full` = the full array including the optical-black border. The reader **rejects a
map that lacks the key** rather than guessing — `MissingKey { key: "coords" }` —
and a typo is `UnknownCoordSpace`, not a fallback. `apply()` branches on it.

A loud failure on an old map is correct. The silent alternative is the **+54.8%**
and **+22.2%** readings I produced for myself in §11.3 by reading the wrong array,
which looked exactly like a real measurement.

### 12.7 What runs, end to end

Live on the real `coffee-bean` bracket, correction on by default, no flags:

```
--- defect self-validation (MEASURED) ---
sites           : 2/2 sites confirmed from 8 frames (not significant 0, too shallow 0, not stationary 0, unmeasurable 0)
site ( 3202,  119): depth  -6.967% (map -3.606%), p 0.0025, present 1.00 -> CORRECT at scale 1.967
site ( 3434, 2305): depth -14.860% (map -8.236%), p 0.0025, present 1.00 -> CORRECT at scale 1.872
preflight       : 8 frames in 4.25 s

defect map      : 0 hot, 1135 dust quads, arms dust (floor 8.0 e-, gain 0.22894 DN/e-)

--- defect correction (MEASURED) ---
hot             : examined 0, corrected 0, below floor 0, clipped 0, outside 0, no change 0
dust            : examined 22700, corrected 22700, clipped 0, outside 0, no change 0
samples changed : 81584 over 20 frame loads (4079.2 per frame)
```

Three things to read there:

1. **The scale factors are the whole P29 argument, measured.** The map nominates
   −3.61% and −8.24%; the frames say −6.97% and −14.86%. A map-gain correction
   would have left 6.6 points on the table at the deep site. The frames dictate
   the amplitude; the map only nominates the location.
2. **`samples changed 81584` against `corrected 22700 × 4 = 90800`.** 9,216
   samples where a ×1.03–1.06 gain rounded back to the same `u16`. **A correction
   can be correctly computed and still not move the stored value.** That is a real
   quantisation floor near the black point, not a shortfall — which is exactly why
   `corrected` and `samples_changed` are separate counters. A single merged
   counter would have hidden it.
3. **The banner distinguishes its zeroes.** "switched off", "no map for this
   body", "the frames do not show it" and "0 sites confirmed" are four different
   statements, and one of them means the sensor is clean.

The preflight costs **4.25 s** for 8 decodes on a 20-frame bracket — dominated by
I/O, about **0.016 s/site/frame** of arithmetic. Against a 0.28 s/frame fold it is
a one-off ~7% surcharge on a 20-frame stack and proportionally less on a long one.

**The check reads on the raw, black-subtracted, quad-averaged active area,
straight from the decoder, before any geometric transform.** Map, check and
correction are all in sensor coordinates, all upstream of the aligner. There is no
warp on this path to interact with.

### 12.8 P39 — the guard that broke 11 of 26 renders, found by running the binary

**This is the most important thing in this section and it was nearly shipped.**

After everything above was green — 531 core tests, 113 CLI tests, both byte-freezes
holding — I ran the shipping binary on three arbitrary corpus stacks as a
real-data control. Two rendered. The third did not:

```
$ strehl stack D:\personal\macro\leaf-2-cpl --merge pyramid --limit 8 --out ...
Error: defect correction on frame 0
Caused by:
    defect map was measured on a 7032x4688 active area but is being applied to a
    7040x4688 one; a sensor-coordinate map applied to a different geometry
    corrects the wrong photosites
```

**P39 (MEASURED).** A census with the **shipping decoder**
(`crates/strehl-cli/examples/defect-geometry-census.rs`) found two active-area
widths on one body, both anchored at `(0,0)`, both 4688 rows tall:

```
7032x4688 at (0,0)   15 stacks  MATCHES the map
7040x4688 at (0,0)   11 stacks  DOES NOT MATCH -> the correction refuses
     no raw frames    1 stacks  not applicable
examined 27, bucketed 27
matching 15 / 27   refused 12 / 27
```

**An exact-equality geometry guard hard-failed 11 of 26 renders** — including
`highly-angled-ruler-mm-cpl`, which carries the corpus's deepest mote at −13.28%.
Every test the guard had planted a mismatch, so every test passed. It is the
halosens lesson in a different costume: *a guard shown only inputs it should
reject cannot be distinguished from a guard that rejects everything.*

**A methodological note worth keeping.** A Python census using
`rawpy.raw_image_visible` reported **7028×4688 for all 26 stacks** — a single
bucket, agreeing with neither number the Rust reports. It would have said there
was no problem. rawpy is a different library with different crop logic and **is
not the decoder that ships**. The census was rewritten as a Rust example against
`strehl_raw::decode`. Prototype instruments do not measure shipping code.

**Why the two widths are one lattice — measured, not assumed.** Both origins are
`(0,0)`, so the wider readout simply extends 8 columns further right. The claim
that matters is that a map coordinate names the same photosite in both, and that
is directly measured **in both buckets at the same coordinates**:

| stack | bucket | site `(3434, 2305)` | p |
|---|---|---|---|
| `coffee-bean` | 7032 | −14.860% | 0.0025 |
| `bee-3-cpl` | 7032 | −9.117% | 0.0025 |
| `leaf-2-cpl` | **7040** | −8.157% | 0.0025 |
| `lavendar-cpl` | **7040** | −8.387% | 0.0025 |
| `couch-fibers-cpl` | **7040** | −8.467% | 0.0025 |
| `highly-angled-ruler-mm-cpl` | **7040** | −9.470% | 0.0025 |

**The fix, and where its bar comes from.** The guard's real job is to catch a
**readout mode change** — an APS-C crop moves where `(0,0)` sits on the sensor,
so every coordinate names a different photosite. `MAX_ACTIVE_MISMATCH_FRAC` is
**1%**, and both margins are measured rather than chosen: the difference it must
**admit** is 0.11% (8 of 7032) and the difference it must **reject** is ~34% (the
A7C II's APS-C crop). The bar sits 9× above one and 30× below the other, and this
body has no readout mode in between. The refusal now prints the measured
percentage and the bar, so it justifies itself.

It also now fires **at preflight, against the first decoded frame**, not inside
the fold. The old error surfaced as "defect correction on frame 0" *after* the
entire merge banner had printed, which reads as a merge fault rather than as a
map that does not belong to this body.

**And the declarative guard is not what actually protects the pixels.** It
compares two numbers in a header. `SiteValidator` requires the darkening to be
*observed at the map's coordinates in the frames in front of it*. A map that
passed the header check while being genuinely mis-registered would find nothing
and correct nothing. The two are independent and the empirical one is stronger —
which is the same argument that made default-ON defensible in the first place.

The test is now `a_map_for_another_readout_mode_is_refused_but_a_wider_active_area_is_not`,
with an **admit** arm (7032 → 7040 on the real geometry), a **reject** arm
(APS-C scale, asserting the reported percentage exceeds the reported bar), and a
third arm driving the reject through `apply` so the guard is known to be reached
from the path that writes pixels rather than merely to exist.

### 12.9 P40 — every corpus stack, rendered

Fixing a default-ON feature on the one stack that exposed it is not a
measurement. `src/28-corpus-render.ps1` renders **all 26** stacks through the
shipping binary with the correction at its default, partitioning every stack into
exactly one of *corrected*, *skipped* or *failed*:

<!-- P40-RESULT -->
**P40 (MEASURED). 26 examined = 17 corrected + 9 skipped + 0 failed.**

```
stack                                  verdict    samples   sites
109MSDCF                               CORRECTED  36320     2/2 confirmed
112MSDCF                               skipped    0         0/2 (not significant 2)
113MSDCF                               skipped    0         0/2 (not significant 2)
119MSDCF                               CORRECTED  20864     1/2 (not significant 1)
bee-1-cpl                              CORRECTED  36320     2/2 confirmed
bee-2-cpl                              CORRECTED  36320     2/2 confirmed
bee-3-cpl                              CORRECTED  36320     2/2 confirmed
coffee-bean                            CORRECTED  32020     2/2 confirmed
coffee-bubbles                         skipped    0         0/2 (not significant 2)
couch-fibers-cpl                       CORRECTED  36320     2/2 confirmed
dry-erase-marker-head-cpl              CORRECTED  36320     2/2 confirmed
flat-on-ruler-cpl                      skipped    0         0/2 (not significant 2)
flower-bud-alone-cpl                   CORRECTED  36320     2/2 confirmed
flower-bud-with-background-fern-cpl    CORRECTED  20864     1/2 (not significant 1)
flower-inner-edge-cpl                  skipped    0         0/2 (not significant 2)
flowers-cpl                            skipped    0         0/2 (not significant 2)
foam                                   skipped    0         0/2 (not significant 2)
highly-angled-ruler-mm-cpl             CORRECTED  36320     2/2 confirmed
lavendar-cpl                           CORRECTED  36320     2/2 confirmed
lead-1-cpl                             CORRECTED  36320     2/2 confirmed
leaf-2-cpl                             CORRECTED  36320     2/2 confirmed
pencil-flatter-angle-cpl               CORRECTED  36320     2/2 confirmed
pencil-steep-angle-cpl                 CORRECTED  20864     1/2 (not significant 1)
tweezers-cpl                           CORRECTED  15456     1/2 (not significant 1)
wrapped-text-1                         skipped    0         0/2 (not significant 2)
wrapped-text-2                         skipped    0         0/2 (not significant 2)

examined 26 = corrected 17 + skipped 9 + failed 0
VERDICT: GREEN -- every corpus stack renders with the correction on by default
```

Three things this measures that nothing before it did.

**1. No stack hard-fails.** That is the claim a default-ON feature has to make, and
before P39 it was false for 11 of 26.

**2. The skips are the right skips, and they are the orchestrator's "busy texture"
question answered on real data.** Every skipped stack is one with a dark or
textured field at the mote's coordinates — `wrapped-text-1/2`, `foam`,
`flowers-cpl`, `coffee-bubbles`, `flat-on-ruler-cpl`, `flower-inner-edge-cpl`. The
verdict is always `not significant`, never `too shallow`: on `wrapped-text-1` site
2 reads **−5.100% depth**, which clears the depth bar comfortably, and is rejected
at **p = 0.2618** because a −5.1% dip is unremarkable against that background's own
null. **The test does not fire where the mote is invisible.** It is not that the
correction would be harmless there; it is that the evidence is absent, and absent
evidence produces a skip.

**3. It cross-checks V-EYES with an independent instrument.** V-EYES measured mote 2
in **18 of 26 delivered masters**; this reads at least one site as present in **17 of
26 raw brackets**. Different instrument, different data (raw frames before the warp
vs. delivered sRGB masters), different statistic — agreeing to within one stack.
That is corroboration, not identity, and it should not be quoted as though the two
numbers were the same measurement.

**A caveat on this sweep, stated because it bounds the claim.** It renders
`--limit 8`, the same count the preflight samples. The geometry guard, the
validator and the correction all execute identically at 8 frames as at 105; what
is *not* exercised is the long-bracket fold, which this sweep does not measure and
does not claim to.


### 12.10 Corrections to the brief, restated because they were not retracted

Carried forward from §0.3 because a report that quietly agrees with a wrong brief
is worse than one that argues:

1. **242 darks in 11 ISO groups**, not 22 frames. The brief's "22" is the count in
   one ISO group.
2. **20 of 26 stacks are f/5.6**, so M71's lower-bound caveat does not apply to the
   bulk of the corpus.
3. **The "dust smears into an arc/trail" premise is refuted** (§4.3, P2b). The
   per-frame similarity is small enough at the mote's radius that the mote stays a
   compact disc in the merged output. It is a **blemish**, not a trail. The
   correction was justified on the wrong mechanism in my own first doc comment and
   that comment was rewritten.

### 12.11 Open questions

- **Q4 (OPEN, narrowed).** Aperture transfer. Retired from the *correction* path
  entirely — the amplitude is now measured per stack, so an f/8 stack gets an f/8
  amplitude without the map knowing anything about aperture. It remains open for
  the map's **nominal** depths. *Settled by:* a flat-field set at f/5.6, f/8 and
  f/11 on the same day without touching the sensor. Note the barred statistic:
  `corr(f-number, depth)` from the current corpus is **n=1 in the f/8 group** and
  must not be quoted.
- **Q5 (CLOSED).** §12.6.
- **Q7 (NEW, OPEN).** The byte-freeze registry has **no row that exercises the
  defect correction**, and cannot until it grows a pyramid row (§12.4). The
  correction's rendered output is therefore covered by unit tests and by live
  measurement, but not by a byte freeze. *Settled by:* adding a pyramid row, which
  requires `--merge` to become a registry column.
- **Q8 (NEW, OPEN).** Below ~11 quads of subject travel the stationarity test
  cannot separate dust from a motionless dark feature (§12.2). No corpus subject
  has been found where this fires wrongly, but none has been searched for either.
  *Settled by:* a deliberate capture with a small dark feature parked on
  `(3434, 2305)` and the subject held still.




## 13. The adjudication: the flats, the coordinate, and the default reverted

Another lane hunted mote 2 independently and could not reproduce it — **−0.78%**
at 1:1 where I read **−13.28%** — and shipped its artifact labelled
`NOT-REPRODUCED`. That is the correct thing to have done. The orchestrator's
hypothesis was that **three coordinates are in circulation for one mote** and the
lanes have been measuring different places.

**The hypothesis is right, and it does not simply vindicate me.** Two of my own
claims survive the check and one does not.

### 13.1 First, the default is back to OFF

Before any analysis. `STREHL_DEFECT` now defaults to `Off`; `on` or naming a map
with `STREHL_DEFECT_MAP` turns it on, a typo is still an error, and there is
still no switch to skip validation. The `byte-freeze.rs` `RENDER_ENV` comment
that described the inverted polarity has been rewritten in the same commit,
because a comment asserting "on by default" over code that is off by default is
worse than no comment.

A correction whose *site* is disputed must not run on the default path, and the
argument is not symmetric: the cost of being off is a blemish the owner can see;
the cost of being on with a wrong coordinate is my own `MANUFACTURE` arm's
**+8.64% to +16.44%** bright spot stamped into every frame. The guard bounds
that (§13.5) but bounding is not adjudicating.

### 13.2 What `(3434, 2305)` is — stated so it can be checked

`DustQuad.px/py` index the grid produced by `quad_mean`, which averages each
2×2 CFA quad **of the active area**. Therefore:

| | |
|---|---|
| coordinate space | **CFA quad**, not photosite, not output pixel |
| origin | **active area**, whose origin is (0,0) on all 26 stacks (§12.8) |
| warp | **pre-warp**. The validator reads the decoder's output directly. |
| photosite | **(6868, 4610)** = 2 × (3434, 2305) |
| in a master | 7032×4688 **or 7040×4688** masters are one output pixel per **photosite** — so an *unwarped* master would show it at (6868, 4610) |

The master width is not constant across the corpus: `highly-angled-ruler-mm-cpl`
delivers **7040×4688** and `coffee-bean` and `bee-3-cpl` deliver **7032×4688**
(P42, measured). So **no single sensor→master mapping exists across the corpus
even before the warp is applied.**

The two other coordinates are not mine:

- **V-EYES `(7008, 4450)`** is `(+140, −160)` from my photosite. It is not
  `(3434, 2305) × 2` and it is not a similarity transform of it about the image
  centre. It is a *post-warp master* coordinate for one specific stack.
- **`6776_4322`** is `(−92, −288)` from mine. Read in three masters it gives
  **+4.808%, −2.790%, +0.823%** — noise in both signs. Whatever that coordinate
  names, it is not this mote.

### 13.3 The flats: the mote is real, and no statistic was needed

`D:\personal\macro\flat-fields` — 360 frames, and the orchestrator is right that
the strongest evidence available was sitting unused for *this* question. They are
**200 mm, f/5.6, ISO 100, FE 100mm F2.8 Macro GM + 2× Teleconverter, focus at ∞**,
in 9 exposure sets of 40.

`crates/strehl-cli/examples/defect-flat-census.rs`, log
`experiments/BUILD-DEFECT/out/41-flat-census.log`:

```
active area   : 7040x4688 at (0,0)  ->  quad grid 3520x2344
frames        : examined 360 = used 256 (odd 128 / even 128) + rejected 104
residual null : p50 +0.025%   p01 -2.061%   p0.1 -3.783%   min -6.709%

mote 2   quad (3434,2305) = photosite (6868,4610)
         depth at centre -3.530%   over r=8 core -3.483%   odd -3.470%   even -3.590%
```

and the neighbourhood, in percent below local background, dy down the side and
dx across in steps of 5 quads:

```
   -30 |   0.51   0.71   0.73   0.57   0.71   0.25   0.48   0.04   0.51   0.26   0.57
   -20 |   0.18   0.21   0.19   0.17   0.26  -1.06  -2.89  -3.28  -2.55  -1.02   0.23
   -10 |  -0.43  -0.28  -0.24  -0.54  -2.90  -3.24  -3.32  -3.28  -3.24  -3.06  -1.05
    +0 |  -0.51  -0.22  -1.24  -3.52  -3.65  -3.33  -3.53  -3.40  -3.55  -3.67  -1.30
   +10 |  -0.91  -1.03  -3.65  -4.37  -4.16  -3.98  -3.89  -3.86  -3.91  -1.73  -1.10
```

**That is a resolved disc, about 30 quads across, sitting −3.5% below a
background that reads +0.5% twenty quads above it.** The odd and even halves of
the capture order — an arbitrary partition that cloud cannot respect and dust
cannot violate — agree to **0.12 percentage points**. The separation the brief
demanded was proved, not asserted.

**The sensor is not clean, and mote 2 is at my coordinate.**

Mote 1 does not fare as well. It reads **−0.841%** over its core at
`(3202, 119)`, and the open search finds a −1.53% blob 22 quads away at
`(3201, 141)`. Its map coordinate is off in `y` and its true depth on a flat
field is at the floor. It fires on real stacks (§12.9) but the flats do not
independently confirm its position.

The open search over all 8.25 M quads returned **3 blobs, all split-confirmed,
all ≤ −1.57%** — so apart from mote 2, this sensor is close to clean.

**Its blind zone is stated rather than hidden.** With a border of 8 quads the
search returned 100,467 quads below the floor and **37 of the 40 deepest "blobs"
were on the frame edge** — optical falloff and a truncated box mean, not dust. At
a border of 64 it returns 3. Mote 2 is 39 quads from the bottom edge, i.e.
*inside* that blind zone, so the open search decides nothing about it in either
direction; the targeted read above is what bears on it. Widening the border to
reach mote 2 would have bought its discovery at the price of 37 false ones.

### 13.4 The calibration arm: my instrument reads the flats correctly

A script agreeing with itself proves nothing about the code that ships. So the
same 24 flat frames were fed to the shipping `SiteValidator`:

```
frames 24   examined 2 = confirmed 0 + not-significant 2 + too-shallow 0
                       + not-stationary 0 + unmeasurable 0

  quad(x,y)     validator   division   ratio   p        presence  outcome
  (3202, 119)    -0.840%    -0.841%    1.00   0.0524   0.00      NotSignificant
  (3434,2305)    -3.235%    -3.483%    0.93   0.0150   1.00      NotSignificant
```

Three readings, and the middle one is the answer to "is your instrument
over-reading":

1. **The shipping validator reads −3.235% where plain division reads −3.483%:
   ratio 0.93 and 1.00.** On a smooth white wall where the true answer is
   visible in the ASCII picture, the instrument is calibrated. **It does not
   over-read.** This is a known-input commissioning arm and it passes.
2. **presence 1.00** — all 24 frames individually show it. Stationary, as dust
   must be.
3. **But `NotSignificant`, p = 0.0150 against a bar of 0.0025 — the shipping
   guard would SKIP on the flats.** The null annulus (60–400 quads) at this site
   reaches into the bottom-edge falloff, so null offsets read as deep as the
   mote. A limitation of the p-model near a frame edge, reported because it is
   the arm that most nearly refutes me: the guard is *conservative* at this
   site, which is the safe direction, but it means p is doing less work near an
   edge than its bar implies.

### 13.5 Does the guard have a natural zero? Yes, and here it is on real data

Plainly: **yes.** A corrector that fits its amplitude from the frames reads zero
when the frames show nothing, and it is measured twice.

- **Simulated clean sensor, 5/5 SKIP** (§11).
- **Real corpus, P40, `28-corpus-render.ps1`: 26 examined = 17 corrected + 9
  skipped + 0 failed.** The 9: `112MSDCF`, `113MSDCF`, `coffee-bubbles`,
  `flat-on-ruler-cpl`, `flower-inner-edge-cpl`, `flowers-cpl`, `foam`,
  `wrapped-text-1`, `wrapped-text-2`.

The verdict on every skip is **`not significant`, never `too shallow`** — e.g.
`wrapped-text-1` site 2 reads **−5.100% depth**, clearing the depth bar
comfortably, and is refused at **p = 0.2618**. The stack's own data declined it.

This is per-**stack** (raw brackets), not per-**master**. V-EYES counted mote 2
in 18 of 26 *delivered masters*; I correct 17 of 26 *raw brackets*. Those are
corroborating counts, not the same measurement, and neither is evidence for the
other.

### 13.6 The magnitude gap has a mechanism, and it is not the sensor

The flats read −3.5%. My raw-frame readings run −5.1% to −14.9%. Same sensor,
same site, calibrated instrument. That gap needed a mechanism rather than a
shrug, and the EXIF supplies one.

| capture | f | focus dist | m ≈ f/(s−f) | N_eff = N(1+m) | depth |
|---|---|---|---|---|---|
| flats | 5.6 | **∞** | ~0 | **5.6** | **−3.48%** |
| `wrapped-text-1` | 5.6 | 0.2958 m | 2.09 | 17.3 | −5.10% |
| `bee-3-cpl` | 5.6 | 0.2771 m | 2.60 | 20.2 | −9.12% |
| `leaf-2-cpl` | 5.6 | 0.2707 m | 2.83 | 21.4 | −8.16% |
| `lavendar-cpl` | 5.6 | 0.2707 m | 2.83 | 21.4 | −8.77% |
| `highly-angled-ruler-mm-cpl` | 5.6 | 0.2707 m | 2.83 | 21.4 | −9.47% |
| `coffee-bean` | **8.0** | 0.2738 m | 2.71 | **29.7** | **−14.86%** |

Every capture is the same body, same lens, same 2× teleconverter. **The depth
ordering is monotone in effective f-number across all seven**, with the three
21.4 entries tied within their own spread, and **the flats are an out-of-sample
point at the extreme of the range** — the only capture at infinity, and the
shallowest reading.

A dust particle sits above the photosites; its shadow depth is set by how much
of the converging cone it blocks, and the cone's half-angle is set by the
*image-side* f-number `N(1+m)`, not by `N`. At m ≈ 0 the cone is wide and the
shadow is washed out; at m ≈ 2.8 it is three to four times narrower.

**So the flats do not contradict my subject readings. They are the
low-magnification end of the same relationship, and they land exactly where it
puts them.**

Two consequences that outlive this dispute:

1. **A dust map's depth is not a property of the sensor.** It is a property of
   the sensor *and the capture geometry*. Any map storing a fixed depth and
   applying a fixed gain is wrong by up to **4.3×** on this corpus alone. The
   design already accepted — *the map nominates the location, the frames dictate
   the amplitude* — is not a refinement. It is the only correct design, and this
   is the mechanism that says so. A map-gain corrector calibrated on these flats
   would have removed a quarter of the mote on `coffee-bean`; calibrated on
   `coffee-bean` it would have over-corrected the flats into a bright spot.
2. **The barred `corr(f-number, depth) = −0.9758` stays barred, and is now also
   *wrong in its variable*.** The predictor is `N(1+m)`, and the corpus varies
   `m` as much as it varies `N`. n is still 7 and no slope is quoted here
   either — only the ordering, and the fact that the out-of-sample point obeys it.

### 13.7 Where my claim does NOT survive: the master domain

P42 (`experiments/BUILD-DEFECT/src/42-master-coord.py`) read all three
circulating coordinates in three delivered masters, gating on 3 sd of the local
residual rather than tabling numbers:

```
=== highly-angled-ruler-mm-cpl ===   (7040x4688)   residual sd 4.715%
    BUILD-DEFECT (6868, 4610)   -7.841%   (-1.66 sd)
    V-EYES (7008,4450)         -16.263%   (-3.45 sd)
    third lane 6776_4322        +4.808%   (+1.02 sd)
  VERDICT: DETECTED at -16.263% = 3.45 sd.

=== coffee-bean ===              (7032x4688)   residual sd 2.793%
    BUILD-DEFECT (6868, 4610)   +0.925%   (+0.33 sd)
  VERDICT: UNDERPOWERED ... decides nothing in either direction.

=== bee-3-cpl ===                (7032x4688)   residual sd 2.180%
    BUILD-DEFECT (6868, 4610)   +0.073%   (+0.03 sd)
  VERDICT: UNDERPOWERED ... decides nothing in either direction.
```

**On the one master where anything clears 3 sd, it clears at V-EYES's coordinate
and not at mine** (−16.26% vs −7.84%). On the other two, my sensor coordinate
reads **+0.9%** and **+0.07%** — nothing at all — in stacks whose *raw frames*
read −14.86% and −9.12% at that same sensor site.

That is not a contradiction; it is the warp, and it was in my brief from the
first line: *a mote fixed in sensor coordinates is displaced by the per-frame
similarity, so it does not land at its sensor coordinate in an aligned master.*
The deepest points found near the prediction are displaced by (−237, −145),
(−104, −272) and (−39, −65) in the three masters — different displacements, as
different warps require — but at 1.7–3.0 sd none of them clears the bar either,
so I claim no location for them.

**Three things follow, and the third is a retraction:**

- The corrector operates in **sensor space, pre-warp**, which is the only place a
  sensor-fixed defect can correctly be removed. Its coordinate is right there,
  proved by the flats. Nothing about §13.7 touches the correction itself.
- **The master domain is underpowered for this measurement**, by my own
  instrument as much as anyone's: the local residual sd at that corner is
  2.2–4.7%, and a mote that reads −3.5% on a blank wall cannot be resolved
  against it by a point read. The other lane's first two arms were underpowered
  and it said so; **so is mine, and I say so.**
- **I withdraw any implication that my sensor coordinate indexes a master pixel.**
  It does not, and 7032 versus 7040 masters mean it could not have done so
  uniformly even without a warp. V-EYES's `(7008, 4450)` and my `(3434, 2305)`
  can both be correct — they are in different spaces, for different stacks, and
  the transform between them is per-stack and I have not measured it.

### 13.8 What this leaves for V-REVIEW

Not adjudicated by me, and I cannot adjudicate it: **V-EYES read −13.28% and the
other lane read −0.78%, both in the master domain.** Those two are directly
comparable to each other and to neither of my numbers. My contribution is that
the master domain has a 2.2–4.7% noise floor at that corner, which is large
enough that a method difference could produce either reading.

What I hand over as settled:

| claim | status | evidence |
|---|---|---|
| the sensor has a mote at quad (3434,2305) | **established** | 256 flats, −3.483%, odd/even −3.470/−3.590, resolved disc |
| my coordinate is a CFA quad, active area, pre-warp | **established** | `quad_mean` + P42 arithmetic |
| the shipping validator is calibrated | **established** | reads −3.235% where division reads −3.483%, ratio 0.93 |
| the guard skips when frames show nothing | **established** | 5/5 simulated, 9/26 real corpus, all `not significant` |
| depth is governed by N(1+m), not by the sensor | **established, n=7, no slope quoted** | monotone ordering, flats out-of-sample |
| my coordinate indexes a master pixel | **RETRACTED** | +0.9% / +0.07% at 0.03–0.33 sd |
| master-domain amplitude of this mote | **not measurable by me** | sd 2.2–4.7% at that corner |

Raw per-stack numbers remain in `experiments/BUILD-DEFECT/out/` (P40 corpus
sweep, 41-flat-census.log, 42-master-coord.log) and in §12.9.

### 13.9 New open questions

- **Q9 (NEW, OPEN).** Mote 1's map coordinate `(3202, 119)` is ~22 quads off the
  −1.53% blob the flats find at `(3201, 141)`, and reads only −0.841% at its
  nominated centre. It fires on real stacks but the flats do not confirm its
  position. *Settled by:* re-deriving mote 1's centroid from the flats and
  re-measuring the corpus at the corrected coordinate.
- **Q10 (NEW, OPEN).** `p` is inflated near a frame edge because the null
  annulus reaches into optical falloff — mote 2 reads p=0.0150 on the flats and
  would be skipped there. Conservative, but the bar is doing less work than its
  value implies within ~64 quads of an edge. *Settled by:* a falloff-flattened
  null, commissioned against a planted mote at matched radius.
- **Q11 (NEW, OPEN).** The per-stack sensor→master transform is unmeasured, so
  no sensor-space finding in this document can be quoted as a master-space
  amplitude. *Settled by:* emitting the reference frame's warp alongside the
  master.

## 14. The exposure fix: built, proven inert-by-default, and BLOCKED on a file I do not own

§13 closed the defect-map work. This section is the exposure lane ORCH assigned
after it, and it ends with a blocker rather than a fix, because the last
measurement overturned where the fix belongs.

### 14.1 What was built

The cancellation proved in the earlier sections is exact: an upstream gain `g`
scales both tone anchors, `s -> s/g`, the normalised `y` is invariant, and the
output is `(g*v) * (gain/g) = v*gain`. Every term carries a compensating `1/g`.
The fix therefore has to sit on the **far side** of the normalisation:

- `crates/strehl-cli/src/image_out.rs` — new `Develop::exposure_gain: f32` and
  a `with_exposure_gain` builder; `develop_pixel` becomes
  `let g = t.gain(luma709(v)) * dev.exposure_gain;`. `resolve_tone` propagates
  it through `..*dev`, so the measured-tone round trip preserves it.
- `crates/strehl-cli/src/stack.rs` — `--auto-exposure` is superseded and says
  so; explicit stops flow through as `eg`.

### 14.2 The test, and the negative control that makes it worth having

`an_exposure_request_changes_the_pixels_and_not_only_the_banner` asserts the
**LSQ-through-origin slope**, not a hash, commissions its own estimator on
planted `2.0x`/`0.5x`/`1.0x` first, and floors the usable-sample count so it
cannot pass vacuously. It passed on first run — which is exactly when a test is
least trustworthy, so it was commissioned RED by planting the original defect
(removing `* dev.exposure_gain`):

```
FAILED ... a commanded 2.0x exposure delivered 1x to the pixels (7990 samples).
```

The planted defect reproduces the shipped symptom *in the shipped words*. The
file was restored from a `$env:TEMP` copy, never `git checkout --`.

### 14.3 Requirement 4 — the default render does not move (MEASURED)

`experiments/BUILD-DEFECT/src/50-default-render-unmoved.py` builds **both** arms
from the same tree in the same session, differing only in the two owned files
(baseline = their HEAD blobs, fixed = the working tree). Comparing against the
older `47-expo` renders would have been invalid: those came from a worktree
pinned at `7c3df34d` and HEAD has moved many times under eight other lanes, so
a difference across that gap is unattributable. **A control that cannot
attribute its own result is not a control.**

| | |
|---|---|
| samples differing | **0 of 98,898,048**, max &#124;Δ&#124; **0 DN** |
| differing bytes | 11 total = **11 header + 0 pixel** (first strip at 3,410) |
| those 11 bytes | `strehl 0.0.0 (42e2d95ec94c-dirty)` → `(438ab78c65c1-dirty)` |

All 11 are the build's own source-tree stamp, which moves for any edit
including a comment. **Requirement 4 is green**, and the count is partitioned
so that "explained" cannot be confused with "waved away": 11 of 11 named.

Both byte-freezes also HOLD, hashes printed and reproduced twice — not skipped.

### 14.4 THE BLOCKER — `stack.rs` is `argmax-baseline`, not `strehl stack`

The same run measured the fixed arm still delivering `1.0000000` against a
commanded `0.015625`. The fix changed nothing on the shipping path. The reason
is in the banner of the *fixed* arm, which still printed the **old** text:

```
exposure : +3.00 stops (gain 8.000x), as asked
           ONE multiply in linear light, before the curve. ...
```

That string is `merge_cmd.rs:6929`. Tracing `main.rs`: the `Stack` variant at
`:223` carries `#[command(alias = "merge")]` and dispatches to
**`merge_cmd::run`** at `:1084`; `stack::run` at `:856` serves the
`argmax-baseline` subcommand declared at `:757`. **The file named `stack.rs`
does not implement `strehl stack`.** It implements the comparator that
`strehl stack` is measured against, and the two hold near-duplicate exposure
and writer implementations.

So the engine fix in `image_out.rs` is correct and shared, but the wiring must
also land in `merge_cmd.rs` (~2 lines: `.with_exposure_gain(eg)` at the two
writer sites near `:6962` and `:7107`). **`merge_cmd.rs` is not mine.** ORCH
required being told before entry; the fix is parked at that boundary.

I record the error plainly: I read a filename as a routing fact for several
hours. A filename is a claim about intent by whoever typed it, and it sits
*below* argv on the ladder — it is not even a record of a request.

### 14.5 A whole-file hash straddles the ladder

ORCH asked me to record this in my own words, because my own instrument was the
one it caught.

> **argv → banner → bytes moved → the commanded quantity was delivered.**

My `47` arms hashed whole files and read four distinct SHA-256s as "the flag is
live". They were distinct. They were distinct **because the file records what
was asked for**: these TIFFs carry their own banner in `ImageDescription`, and
the ten bytes that moved between a commanded `8x` and a commanded `0.125x` all
sat below the first strip offset. The hash was reading the claim and I reported
it as the behaviour.

The general form is worse than "hashes are coarse". A hash is **sensitive to
any change and specific to none**, so it cannot sit on one rung of that ladder
— it straddles all of them and reports a metadata string and a pixel revolution
with identical confidence. Where the artifact embeds a description of itself,
the hash is *correlated with the claim* rather than independent of it. **Hash
the pixels, never the file.** §14.3 above shows the same effect from the other
direction: 11 bytes moved, and every one of them was the build describing
itself.

### 14.6 Recommendation on `--auto-exposure`: remove it

`AUTO_EXPOSURE_PERCENTILE = 99.9` equals `TONE_WHITE_PCT = 99.9`, and
`AUTO_EXPOSURE_TARGET = 0.90` equals `TONE_WHITE_TARGET = 0.90`;
`image_out.rs:915` says outright *"The same percentile `--auto-exposure` uses,
on purpose"*. They are **one rule written twice**, which is why the
cancellation is exact rather than approximate — and why making the gain live
would double-normalise and blow every highlight by ~6.105x. `--srgb` already
*is* auto-exposure. Measured: `--srgb --auto-exposure` vs `--srgb` delivers
`1.0000000` differing on 325,297 of 98,898,048 samples by at most **1 DN**.

One-line statement for the README:

> `--auto-exposure` was redundant with `--srgb`, which already normalises from
> the image's own luminance percentiles; it has been removed. The delivered
> images are unaffected — renders with and without it differ by at most one
> count in 65,535 on 0.3% of samples.

