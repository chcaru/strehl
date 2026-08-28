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


## 15. The commanded quantity, measured where it is defined

Section 14 shipped the engine fix and proved the default render does not move.
Two things were still open: the fix was in `stack.rs`, which does **not**
implement `strehl stack`; and the only calibrated magnitude claim rested on a
unit test rather than on a rendered file.

### 15.1 `stack.rs` is not `strehl stack` — a filename sits *below* argv

`main.rs:223` declares `Stack` with `#[command(alias = "merge")]` and
dispatches it to **`merge_cmd::run`** at `:1084`. `stack::run` at `:856` serves
`argmax-baseline`, declared at `:757`. The two files hold near-duplicate
exposure and writer implementations carrying **identical banner strings**,
which is why the confusion survived so long: the fixed binary printed
*"ONE multiply in linear light, before the curve"* and that string greps to
`merge_cmd.rs:6929`, not to the file I had edited.

This is a new rung *below* the ladder in §14.5. An argv records what the caller
said; a banner records what the program claims; a **filename records neither**
— it is not even a request, only a name someone chose, and a name can be shared
by two implementations of which only one runs. I found it by grepping the
running binary's own output back to its source, which is the only channel here
that is causally downstream of execution.

`merge_cmd.rs` is live under another lane, so §15.3 prepares the wiring as a
patch rather than applying it.

### 15.2 A display-space slope cannot be compared with a commanded linear gain

The first regression of the patched binary gave a slope of `0.0447894` on
`--exposure 3` against `--exposure -3`, against a commanded `0.015625`. Read
naively that is "the flag over-delivers by 2.9x". It is not a result at all.
`--srgb` applies, **after** the gain, the sRGB transfer curve (`srgb_encode`, a
~1/2.4 power law) and then `s_curve(x, 0.55)` in display space; and at ±3 stops
87.5% of samples clip. A ratio of linear quantities is not preserved through a
power law, and a clipped sample has had its gain removed by the ceiling rather
than by the pipeline — which drags any slope toward `1.0`, toward the very null
the measurement exists to exclude. Comparing the two numbers would have been a
**units error dressed as a result**, the same shape of substitution as hashing
a file and calling it the pixels.

`experiments/BUILD-DEFECT/src/53-linear-delivered-gain.py` measures where the
quantity is defined instead. Both display stages are monotone on `[0,1]`, so
both invert: `srgb_encode` analytically, `s_curve` by bisection. The renderer
emits `u16`, so the inverse has exactly 65,536 possible inputs and is built
once as a lookup table — the same arithmetic, evaluated on every value it can
ever be asked for.

The arms are `--exposure +0.25` and `--exposure -0.25`, chosen so that almost
nothing clips. **Prediction, written before the result was read:** the fix
multiplies the placed value by `g` on the far side of a normalisation that has
already cancelled the upstream `g`, so the pre-encode linear output is
proportional to `g` and the regression must return `2^-0.5 = 0.7071068`.

**Commissioned first, on this very data.** Arm E's decoded linear values were
multiplied by an exactly known factor, pushed forward through the same encode,
s-curve and quantisation the renderer uses, then inverted and regressed:

| planted | recovered |
|---|---|
| `2.0` | `2.000000` |
| `0.5` | `0.500000` |
| `1.0` | `1.000000` |

The `0.5` arm is not decoration. An estimator bounded below at `1.0`, or an
"inverse" that is subtly not one, passes the `2.0` arm on its own.

**Result.**

| quantity | value |
|---|---|
| usable (unclipped) samples | 71,245,125 of 98,898,048 |
| excluded (clipped or black) | 27,652,923 |
| commanded linear ratio | `0.7071068` |
| **delivered** | **`0.7067677`** |
| error | **−0.048%** |

The residual is a quantisation story: least-squares through the origin is
dominated by bright samples, the s-curve compresses hardest there, and one
count of `u16` rounding inverts into a larger relative step. It is 0.05% on a
commanded 41% change.

That completes the ladder for this flag on real rendered files, not in a unit
test: **argv → banner → bytes moved → the commanded quantity was delivered.**

### 15.3 The `merge_cmd.rs` wiring, prepared and verified without applying it

`experiments/BUILD-DEFECT/patches/merge_cmd-exposure-wiring.patch` — 3 hunks,
+65/−2. It chains `.with_exposure_gain(applied.gain())` onto the two `Develop`
builders at `merge_cmd.rs:6962` (demosaiced) and `:7107` (binned), and adds a
guard test.

The patch is **generated mechanically** by
`src/51-prepare-merge-cmd-patch.py`: the script copies the file to `$TEMP`,
edits the copy, produces the diff with `git diff --no-index`, rewrites the
paths to repo-relative, and validates with `git apply --check`. It writes
nothing under `crates/` and asserts the source file is byte-unchanged when it
finishes.

"It applies cleanly" is a statement about `git`, not about the fix, so the
patch was verified in a **disposable worktree** at `C:\dev\strehl-wt-bdpatch`
— which honours the ownership constraint, since the hazard is a silent clobber
in the *shared* tree:

| check | result |
|---|---|
| `git apply --check` | clean |
| `cargo build --release` | compiles |
| guard test | passes |
| guard test **commissioned RED** | `2 writer develop site(s) but only 1 carry the exposure gain builder` |
| shipping path, `--exposure ±3` | **98,891,642 of 98,898,048 samples differ** |
| same arms, **before** the patch | **0 samples differ** |

The guard test counts writer `develop(` sites and requires every one of them to
carry the gain builder, so a **third** writer added later fails it rather than
silently shipping uncorrected. Writing it exposed a self-reference bug worth
recording: the first draft's assertion messages contained the literals the test
was counting, so each needle would have inflated its own count and the test
would have passed by describing itself. The needles are now assembled at
runtime from fragments.

## 16. The deep-stack alignment lane: refused on prior art, with the search that establishes it

I was handed *"deep-stack alignment, 6.76 px held-out"* with two candidate
approaches and three pre-registered gates. Before measuring anything I searched
the corpus, because rule 43 requires that an assertion of absence — including
"nobody has tried this" — be **established** rather than assumed. Both
approaches have already been built, measured and killed by name, and the
brief's description of current behaviour is false. This section is the search,
not an opinion about the search.

### 16.1 Both candidate approaches are already dead

**Candidate 1, per-edge self-calibration, is M23.** The proposed estimator is
verbatim M23's: plant ±δ on the measured pair, form
`R = (m(+δ) − m(−δ)) / 2δ`, divide that edge's log-scale by its own `R`.
M23's verdict:

> *"The answer is no, and the reason kills the premise rather than the
> implementation. R4 ships nothing."*

Two results do the killing, and neither is about implementation quality:

- The **shuffled-`R` null reproduces 93.3%** of the correction's movement *with
  zero per-edge information*. Whatever `R` carries, it is not 93% about the
  edge it was measured on.
- **Held-out error is unchanged at 6.758 px** — gate (c), the only gate that
  ships anything, fails.

M23 also registers the hazard that makes this approach worse than inert:
`E[1/R] > 1/E[R]` by Jensen, so a **noisy `R` inflates a corrected magnitude
even when it carries no information at all**. That is a metric whose error sign
is not centred on zero — the same shape of defect as the sharpness statistic
bounded below by zero that this project shipped. A correction built on it can
appear to do work while doing none.

The brief anticipated the objection — *"this is not the scalar correction this
project already killed"* — and it is right that per-edge ≠ scalar. But M23 ran
the scalar as its own null arm N2 (*"constant `R` = group median — this is
literally the scalar M12 refuted"*) precisely so the two could be told apart,
and the per-edge arm still failed gate (c).

**Candidate 2, blur equalisation, is M78.** Both arms moved held-out the wrong
way:

| arm | held-out before | after |
|---|---|---|
| A | 7.241426 px | **7.266073 px** (worse) |
| B | 7.241426 px | **7.244330 px** (worse) |

M78's mechanism probe is the part that matters: `Q(1e-4) = 0.987588` against a
firing threshold of `0.10`. **The blur-asymmetry mechanism does not fire.** The
approach is not badly implemented; the effect it corrects is not present at a
magnitude that matters. That agrees with four independent findings —
M6 (*"no evidence of one"*), `F-camera-lens-optics.md:1015` (*"within 0.4% of
truth, so defocus difference does not bias phase correlation"*), `M103:33`
(*"The cause is not blur asymmetry"*), and SYNTHESIS fact 31 (*"symmetric peak
**degradation**, not directed peak **displacement** … null on all three
stacks"*).

### 16.2 The brief's premise is false, and I checked it rather than repeating it

The brief states *"the current response is to discard spans 1–2 entirely — which
throws away the most numerous, best-overlapped, most tile-rich measurements."*
Read at the working tree, `align_cmd.rs`:

```
DEFAULT_SPANS = [1, 2, 4, 8, 16, 32, 64, 96, 128]
```

Spans 1 and 2 **are shipped**. The discard was withdrawn in M103 §16.10b and is
measured *harmful*: max per-frame placement error **628.1 px**. So the proposed
remedy — "re-admit corrected short edges" — is a remedy for a condition the
product does not have. There is nothing to re-admit.

### 16.3 Gate (c) uses a gauge that is structurally blind to what the merge consumes

Even had the mechanism been live, criterion (c) — *"must beat 6.76 px
held-out"* — rests on a gauge `BUILD-SHARP.md:208-217` has already indicted:

> *"the merge does not consume end-to-end error … **The relevant gauge is
> span-1 residual, and the end-to-end gauge is structurally blind to it.**"*

And `M86:451-454` records that `E*` is **not portable between stacks** and is
**an upper bound of unknown tightness, because the held-out edges are
themselves products of the biased estimator** — the gauge is contaminated by
the thing it is grading. `6.76 px` is additionally a **`coffee-bean`** number;
`bee-3-cpl`'s correct baseline is `13.578 px`. Comparing a `bee-3-cpl`
improvement against a `coffee-bean` bar would have satisfied gate (c) by
changing subject, which is exactly the failure mode the brief warned against
(*"a held-out number that improved because the held-out set changed"*).

### 16.4 The file is contended, and I found that only after a capped listing lied to me

`align_cmd.rs` has taken **four commits from at least three other lanes in the
last 24 hours** (`8457dfc2` BUILD-GATE, `740e7056` V-GATHER, `e41ee5d3` and
`52cb4c4d` BUILD-RESAMP). By the same reasoning that withheld `merge_cmd.rs`
from me, it is not free to take. The one lead I thought was live — M23's
observation that the `R` deficit tracks the **resampler** rather than defocus
(self-pair `R = 0.372`, resampler-free `R = 0.965`) — belongs to **BUILD-RESAMP**,
and the surrounding question is already covered by M95, M104, M113 and M118.

**How I nearly missed that, recorded because the shape recurs.** I listed
recently-modified experiment directories with `Select-Object -First 20`, saw no
`BUILD-RESAMP`, and was one step from reporting the lead as unowned. There are
**192** experiment directories; the listing was capped and `BUILD-RESAMP` was
below the cut. A truncated search prints the *same glyph* as an exhaustive one
— absence and "I stopped looking" are indistinguishable in the output. The
targeted re-check (`Test-Path` on the exact name) found it immediately. This is
the fourth instance of the absence defect in this lane's history and the second
I caught in myself.

### 16.5 What I recommend instead

This lane ships nothing on the brief as written, and that is the result. If the
deficit is to be attacked, the two things not already dead are:

1. **Change the gauge before changing the solver.** Adopt span-1 residual as
   the reported alignment number. The instrument exists —
   `experiments/BUILD-SHARP/src/bs_residual.rs`, self-control **0.0014 plane
   px** — and it measures what the merge actually consumes. Every alignment
   verdict in the corpus is currently written in a unit `BUILD-SHARP` says is
   blind to the defect.
2. **Re-examine the bar, not the estimator.** `E*` is an upper bound of unknown
   tightness computed from edges the biased estimator produced. Until its
   tightness is established, "6.76 px held-out" cannot tell an improved solver
   from a differently-biased one, and any future arm will be graded by a ruler
   made of the thing it is grading.

## 17. E* is not a loose ruler. It is a ruler that runs backwards.

ORCH's redirect: establish `E*`'s tightness before touching the solver, on the
argument that until it is known, every alignment result this project has
produced is ungradable. The pre-registration is
`experiments/BUILD-DEFECT/PREREG-estar.txt`, committed at **`e732cfb8`** before
any outcome number for this question existed.

The answer is worse than "loose". On the class of error alignment is actually
suspected of, **`E*` moves the wrong way**: the worse the estimator, the better
the gate reads.

### 17.1 The ruler that is not self-referential

`E*` (`heldout_error`, `align_cmd.rs:618`) trains a global solve on **short**
edges and scores it against **long** ones. Both sides are outputs of the same
estimator, which is why `M86:451-454` calls it an upper bound of unknown
tightness. To measure the gap I needed truth that the estimator did not produce.

It already exists: **`experiments/m10-deep-align/data/p4-warp-{edges,truth}.csv`**.
M10's P4 is 105 frames synthesised from one real coffee-bean frame by a *known*
smooth similarity sequence plus a growing depth-dependent blur — planted total
drift 98.6 plane px, −4.574% scale, deliberately matched to M6's measured real
coffee-bean drift. **The truth is the plant.** 761 real measured edges, same
estimator, same code path.

Definitions used throughout: `E_true` is the median worst-corner distance
between solved and planted poses, gauge-aligned so frame 0 is identity;
`Λ = E_true / E*` is the looseness.

### 17.2 Commissioning: the solver, the gauge, and the shipped statistic

I re-derived the solve in numpy from the algebra in `align.rs` rather than
calling the Rust, because a sympathetic re-reading of source cannot catch a
misunderstanding of it. Three gates before any verdict:

| gate | bar | result |
|---|---|---|
| gauge check: frame 0 truth vs identity | `0` | `0.000e+00 px` |
| **G0**: reproduce M10's published S3-ba-unit median against truth | ±0.05 px | **`0.6203` vs M10's `0.622`, Δ `0.0017`** |
| the shipped Rust solver on the same tables | ±0.01 px | **worst Δ `0.0003 px`** |

G0 scores my arithmetic against a number M10 published from a *different
implementation*. The third gate matters more: `56-shipped-estar-ladder.py` runs
the identical ladder through `m86-align solve-csv` — shipped weighting, shipped
IRLS, shipped robust reduction, shipped decision rule, none of which my numpy
solve reproduces — and it agrees to `0.0003 px`. **Everything below is a
statement about the product's own gate, not about my re-derivation.**

### 17.3 The arms, and the prediction that was wrong in the dangerous direction

| arm | `E*` | `E_true` | `Λ` |
|---|---|---|---|
| A null | `0.5987` | `0.6203` | `1.04` |
| **B bias ρ=0.526** | **`0.3837`** | **`31.6665`** | **`82.54`** |
| C noise | `0.8065` | `0.6225` | `0.77` |
| D improvement | `0.2993` | `0.3102` | `1.04` |

Arm C moves `E*` **+34.7%** — the instrument is not dead, so arm B's reading is
attributable. Arm D moves both **−50.0%** — `E*` is not bounded below and not
perverse on a *genuine* improvement, so a null in B is not an artefact of a
statistic that only ever falls. Without both of those arms, B says nothing.

**My pre-registered prediction failed, and the truth is worse than what I
predicted.** I predicted `E*` would be *unchanged* under arm B (bar: ≤25%
movement). It moved **−35.9%**. It did not fail to charge for the defect; it
*paid* for it, while `E_true` rose **+5004.8%**, from `0.62` px to `31.67` px.

ρ = 0.526 is not a hypothetical. It is **M23's own measured response on real
span-1 edges**.

### 17.4 The ladder, and the internal null that proves the mechanism

A single point could be coincidence. The full sweep cannot:

| ρ | `E*` | `E*_scale` | `E*_trans` | `E_true` | `Λ` |
|---|---|---|---|---|---|
| 1.000 | `0.5987` | `0.4607` | `0.1344` | `0.6203` | `1.04` |
| 0.900 | `0.5523` | `0.4162` | `0.1345` | `6.9651` | `12.61` |
| 0.800 | `0.5151` | `0.3714` | `0.1346` | `13.5344` | `26.27` |
| 0.700 | `0.4660` | `0.3262` | `0.1345` | `20.1322` | `43.20` |
| 0.600 | `0.4233` | `0.2807` | `0.1346` | `26.7529` | `63.20` |
| **0.526** | `0.3837` | `0.2467` | `0.1346` | `31.6665` | **`82.54`** |
| 0.400 | `0.3230` | `0.1885` | `0.1347` | `40.0600` | `124.02` |
| 0.300 | `0.2757` | `0.1419` | `0.1347` | `46.7459` | `169.54` |

Both columns are **strictly monotone, in opposite directions**, across the whole
sweep.

**The `E*_trans` column is the proof.** The planted bias touches only the
scale/rotation part `a`; translation is copied through untouched. `E*_scale`
falls with ρ almost exactly proportionally, while `E*_trans` sits at `0.1345 ±
0.0002` on **every rung**. That is a null control I did not have to construct —
it was inside the measurement. It rules out a global artefact of my pipeline and
localises the effect to precisely the degree of freedom the bias was planted in.

The mechanism follows: `E*` is a residual **in the same units as the signal**.
Attenuating the log-scale increment shrinks the disagreement between edges by
the same factor it shrinks the quantity being measured. The estimator becomes
*more self-consistent* as it becomes *less correct*. That is not a bug in the
implementation of `heldout_error`; it is what a consistency statistic does.

### 17.5 It is not an artefact of the synthetic case

`57-estar-per-subject.py` plants the same bias on **real measured edges**:

| subject | `E*` at ρ=1.000 | `E*` at ρ=0.526 | move |
|---|---|---|---|
| **coffee-bean** | **`6.758`** | **`4.849`** | **−28.2%** |
| stack-112 | `1.462` | `0.986` | −32.6% |
| p4-warp | `0.660` | `0.419` | −36.5% |
| coffee-bean-m6 | `5.177` | `3.400` | −34.3% |

**4 of 4 subjects: a worse estimator reads better.** On `coffee-bean` — the
stack whose `6.758 px` *is* the project's headline alignment number and ORCH's
gate (c) — planting M23's own measured attenuation makes the gate report a
**28% improvement**. A lane that *introduced* this defect would have been
congratulated by the gate and shipped.

### 17.6 `E*` per subject, and the two subjects where it does not exist

| subject | frames | ok edges | test edges | `E*` |
|---|---|---|---|---|
| coffee-bean | 105 | 1461 | 125 | `6.758` |
| coffee-bean-m6 | 105 | 204 | 38 | `5.177` |
| stack-112 | 79 | 1017 | 107 | `1.462` |
| p4-warp | 105 | 761 | 161 | `0.660` |
| shallow-119 | 33 | 244 | **0** | **UNDEFINED** |
| shallow-109 | 22 | 137 | **0** | **UNDEFINED** |

Partition: **6 examined = 4 computed + 2 undefined + 0 refused.**

Two findings. First, the spread among computed subjects is **10.24×**, and
correlation with stack depth is only `r = +0.468` — **depth does not explain
it**, so a single pooled "6.76 px" hides which subjects are actually broken.
`6.758` is a `coffee-bean` number and nothing else's.

Second, `MIN_SPAN = 40` exceeds the entire depth of both shallow stacks, so
**no edge can ever be a test edge** and `heldout_error` returns `None`. An
entire class of subject has **no gate at all**. That outcome is reported as
`UNDEFINED` here specifically so it cannot be read as a small error — the
distinction between "measured and fine" and "never examined" is the one this
lane has now been caught by four times.

### 17.7 What this retires, and what it does not

**Retired: `E*` as an accuracy gate.** It cannot grade any change that alters
the estimator's scale response — which is the entire class M23 and M78 were
built to address. Gate (c) as ORCH wrote it (*"must beat 6.76 px held-out"*) is
satisfiable by making the estimator worse in a specific, plausible, already-
measured way.

**This retroactively re-reads M23.** Its gate (c) reported held-out *unchanged*
at 6.758 px. On this evidence that gate could not have detected the correction
working, because a change to the scale response is the one thing `E*` cannot
see. **M23's kill still stands** — but it stands on its *shuffled-`R` null*
(93.3% of the movement reproduced with zero per-edge information), which is a
sound and independent argument. The held-out number contributed nothing.

**Not retired: `E*` as a consistency check.** Arm A gives `Λ = 1.04`; on a
clean case `E*` tracks truth well. It is a fine detector of *incoherence*
between edges. It is simply not a bound on placement error, and the two have
been used interchangeably.

**Not established here:** whether the shipped estimator actually carries
ρ ≈ 0.526. M23 measured that response, and M23 also found it tracks the
*resampler* rather than defocus, so it may be an artefact of the probe rather
than an attenuation of the measurement. This section's claim is about **the
gate's ability to detect such a bias**, not about whether one is present. Those
are different questions and only the first one is answered here.

### 17.8 What a real ruler would need

Only two constructions in reach avoid the self-reference:

1. **Planted truth, as P4 does.** It is the only place in this corpus where
   `E_true` is computable at all, and it is already built. Any alignment change
   should be scored there *in addition to* on real stacks — cheaply, since the
   edges are committed and the whole ladder above runs in seconds.
2. **A statistic in units that do not shrink with the bias.** `E*` fails
   because it is a residual measured in the same quantity the bias attenuates.
   A gauge normalised by the stack's own total drift — or the span-1 residual
   `BUILD-SHARP.md:208-217` argues for — does not share that defect by
   construction. Either must be commissioned on the ladder in §17.4 before use:
   **the bar is that it rises monotonically as ρ falls.** That ladder is now a
   reusable commissioning suite for any future alignment metric, and it is the
   durable output of this lane.

## 18. Sensor or filter? The control that was in the data all along

### 18.1 A premise check first, because the brief was wrong

The brief for this block opened: *"Build sensor defect correction — hot/stuck
pixels and dust ... This is currently a total gap: there is no `defect_map.rs`
anywhere in the tree."*

There is. I wrote it earlier in this same session:

| | |
|---|---|
| `crates/strehl-core/src/defect_map.rs` | **4,165 lines** |
| `crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt` | 1,150 lines |
| commits | `0dd3d3f9`, `49227061`, `439563ff`, `eb5145d4` |
| report | §§0–13 of this document |
| wiring | `merge_cmd.rs` 79 lines, `stack.rs` 95 lines |

Hot pixels came from all 242 darks (§3.1); dust came from the flats (§13.3);
the corrector runs in sensor coordinates before the warp (§6.2); it is off by
default and §13.1 says why. One command shows it: `git log --follow --
crates/strehl-core/src/defect_map.rs`.

This is the same shape of error the alignment brief carried in §16, and it is
the third time tonight a lane has been sent after something already built.
**Checking a brief costs one command and I will keep spending it.**

### 18.2 The one thing the brief named that I genuinely had not done

The brief said to use the with/without-CPL pair as a control:

> *"dust on the sensor is in both; anything present in only one belongs to the
> filter or the light."*

**That is correct, it matters, and I had not done it.** Worse, I had seen it.
Line 327 of this document says:

> *"CPL is a rotating element, and the flats were shot ~4.5 h after
> `bee-3-cpl`."*

I wrote the concern down and then pooled all 360 frames anyway.
`defect-flat-census.rs` splits the flats **odd/even by capture order**, which is
a null against *cloud* — illumination cannot respect an arbitrary partition of
capture order. It is not a null against the *filter*. So nothing in this lane
had ever established that what it calls a **sensor** defect map is not partly a
**filter** defect map, and the distinction is not cosmetic:

- a mote on the sensor is in every frame this body will ever take;
- a mote on the CPL appears only in CPL captures — **17 of the 26 corpus
  stacks** — and a CPL *rotates*, so its position depends on a filter
  orientation that is recorded nowhere and changes between sessions. A fixed
  map coordinate would then be right only by luck.

### 18.3 The controlled pair was already in the data

No new capture was needed. `exiftool` over the 360 flats: ISO 100, f/5.6,
200 mm, one session, and `ExposureTime` takes exactly nine values, forty frames
each. Sorted by filename it forms exactly **eighteen** constant runs of twenty:

```text
  1/250 1/125 1/60 1/30 1/20 1/13 1/10 1/8 1/5     DSC00083..00262
  1/250 1/125 1/60 1/30 1/20 1/13 1/10 1/8 1/5     DSC00263..00442
```

**The nine-step ladder runs twice, exposure-matched step for step.** Same paper,
same lens, same session, twenty frames per step. Two blocks of 180 whose only
intended difference is the filter. A defect in both is in the fixed optical
path; a defect in one is on the filter. Someone only had to notice the ladder
repeats.

Pre-registered in `experiments/BUILD-DEFECT/PREREG-cpl.txt` (commit `9353ecdc`)
before any depth was measured in either block, including the prediction and the
arms below.

### 18.4 This experiment predicts a null, which is when a blind instrument wins

From optics, before measuring. A particle at height `z` blurs its shadow by
roughly `z / N_eff`. The flats focus at infinity so `N_eff ≈ 5.6`. §13.3's
published profile is a disc ~306 µm across whose edge falls from −1.03% to
−3.65% over ~51 µm, so

```text
  z ≈ 51 µm × 5.6 ≈ 286 µm ≈ 0.29 mm
```

— the cover glass. A front filter 150–250 mm away would blur by tens of
millimetres and would not be a disc at all. **So I predicted no block effect.**

A blind instrument returns "no difference" for free, so the verdict is void
unless the discriminator is first shown able to say otherwise:

| arm | plants | requires | measured | |
|---|---|---|---|---|
| `G0` | nothing; block 1 odd vs even | not block-specific | Δ **+0.001 pp**, p 0.7900 | **PASS** |
| `G1` | −4% disc in block 2 only | block-specific | Δ **−3.953 pp**, p 0.0000 | **PASS** |
| `G2` | −4% disc in **both** blocks | common | Δ **−0.002 pp**, p 0.7776 | **PASS** |
| `G3` | divides the **real** mote out of block 2 | Δ moves **positive** | Δ −0.006 → **+3.428 pp** | **PASS** |

`G2` is what stops `G1` being passed by a statistic that calls everything
block-specific. **`G3` is the improvement arm this project requires** — a suite
of degradations cannot separate a metric that is *blind* to a defect from one
that scores the defect *better*. `G3`'s correct answer has a sign, and the
magnitude checks too: removing 3.434 pp of depth moved Δ by 3.434 pp.

Planting is applied to the accumulated field rather than to 360 frames per arm,
which is exact rather than approximate because a mask over ~200 of 8.25 M quads
leaves the frame median alone — and that is **measured**, not asserted:
`|median shift| = 1.414e-4`.

### 18.5 The answer: both motes are on the sensor side, with a bound

```text
   site      block 1    block 2      DELTA        p     outcome
   mote 1    -0.865%    -0.820%     +0.045   0.0183   Underpowered
   mote 2    -3.480%    -3.486%     -0.006   0.4487   Common
   partition: examined 2 = 1 Common + 1 Underpowered
```

**Mote 2 — the deepest defect on this sensor, the one that reaches −8% to −15%
in real subjects — reads −3.480% and −3.486% in the two blocks. It is in both.
It is not on the filter.**

And a null deserves a bound rather than a shrug. A *wholly* filter-borne mote
would put its entire depth into Δ, so the largest filter-borne share that could
hide under the null is `p95(null) / depth`:

| site | depth | matched null p95 | Δ | **filter-borne share** |
|---|---|---|---|---|
| mote 1 | 0.865% | 0.056 pp | +0.045 pp | **≤ 6.52%** |
| mote 2 | **3.486%** | 0.052 pp | −0.006 pp | **≤ 1.50%** |

At least **98.5%** of mote 2 is in the fixed optical path. The sensor-space,
pre-warp correction site is confirmed against the control §13.3 never ran.

### 18.6 I checked my own threat and it was real

`PREREG-cpl.txt` §8 raised this against itself: mote 2 sits **38 quads** from
the nearest edge while `SEARCH_BORDER` is **64**, so mote 2 lies *inside* the
band the interior null excludes. An interior null describes noise somewhere the
mote is not, and near an edge a truncated box mean and steep falloff can widen
the block-to-block difference — which would make p optimistic.

Measured, by sampling clean sites at the **same distance from an edge**:

```text
  interior null           p95  0.025 pp
  edge-matched at 38      p95  0.052 pp     2.1x wider
```

**The threat was real: the interior null is optimistic by 2.1× at mote 2's
position.** The verdict survives — Δ −0.006 pp gives p 0.8507, still `Common` —
but the check was not free, because **it changed an outcome**: mote 1 reads
`Underpowered` against the interior null and `Common` against the matched one.
The matched null is the correct control for a site's position, so mote 1 is
common to both blocks too; had I only run the interior null I would have
reported an inconclusive result as if the instrument had been asked properly.

This resembles **Q10** (p inflated near a frame edge because the null annulus
reaches into optical falloff) and puts a number on the edge effect for the first
time — 2.1× at 38 quads. It is a different null from the shipping validator's,
so it quantifies the effect Q10 names without closing Q10.

### 18.7 The open search found no filter dust, and says at what sensitivity

```text
   floors: |DELTA| >= 1.0 pp AND p <= 0.0025 AND >= 64 quads from every edge
   scanned 469792 sites -> 0 above the bar -> 0 after suppression
   NO filter-specific defect found at this sensitivity.
```

The search can return nothing and did. Its sensitivity is **established rather
than asserted**: `G1` planted a −4% disc of the same radius and it was detected
at p = 0.0000, so the search resolves a defect of that depth and size. **The CPL
carries no dust this instrument can see.**

### 18.8 The photometric gate refused, and the timeline answered instead

Gate `C1` was to label the blocks by transmission: a CPL costs light, the
shutter speeds are identical, so the CPL block must be consistently darker. It
required one side of unity at all nine steps **and** spread below 0.5 stop.

**`C1` FAILED.** Same side at 9 of 9, but spread **2.130 stops**, so per the
pre-registration the program printed blocks "1" and "2" and claimed no label.
`44-cpl-label.py` diagnoses why, post-hoc and labelled as such: a ratio of
medians is a ratio of transmissions only where the sensor is linear, and the
ladder's ends are not — 1/5 s reads **1.0466 of range in block 2**, i.e.
clipped, and 1/250 s reads **0.0136 in block 1**, i.e. on the black floor. Only
**3 of 9** steps have both blocks inside `[0.08, 0.80]`, and there the spread is
**0.488 stops** — just inside the bar `C1` was given. That explains the failure;
it does not overturn it, and I did not re-run `C1` on a window chosen after
seeing the data.

The label came instead from evidence that cloud cannot touch — **the clock**:

| strand | reading |
|---|---|
| largest pause inside the 360 flats | **58 s, before `DSC00263`** |
| next largest of the other 358 | 11 s → **5.3×** |
| block boundary from the exposure ladder | `DSC00263` — derived **independently** |
| labelled sweeps | `WITH cpl` 16:31:55 → flats → `NO cpl` 16:51:17 |
| block 2 brighter | 9 of 9 steps |

A 58-second pause, five times any other, landing exactly on a boundary derived
from a different column entirely, is a filter being unscrewed. With the labelled
sweeps bracketing the flats CPL-first, **block 1 wears the CPL and block 2 is
bare**. Partition: 4 strands = 3 supporting + 1 refusing + 0 silent.

**One tension, stated rather than buried.** Removing a CPL should brighten by
1.3–2.5 stops; the in-window measurement is **+0.65 stops**. Cloud between
16:45:35 and 16:46:33 is unmeasured and is the obvious candidate, but I cannot
measure it, so the discrepancy stands unexplained. It is also why `C1` could not
hold a constant ratio, and why the label rests on the clock and not on the light.

**None of §18.8 matters to §18.5.** Mote 2 is in both blocks whichever wears the
filter. The labelling only decides what to *call* them.

### 18.9 What this changes, and what it does not

- **Changes:** the map's framing as a *sensor* defect map is now measured rather
  than assumed, for both of its sites, with a bound (≤1.50% and ≤6.52%
  filter-borne). Mote 1's status improves from inconclusive to common. The edge
  effect Q10 names has a number: 2.1× at 38 quads.
- **Does not change:** the default. `STREHL_DEFECT` stays **OFF**. §13.1 set it
  off because the correction *site* was disputed, and nothing here bears on
  that — this experiment asks which optical element the mote sits on, not
  whether the map should run. No code in `crates/strehl-core/src/` was touched.
- **Does not change:** Q9. Mote 1 is common to both blocks, but its centroid is
  still ~22 quads off the −1.53% blob the flats find at `(3201, 141)`. Being on
  the sensor is not the same as being in the right place.

### 18.10 Artifacts

| | |
|---|---|
| pre-registration | `experiments/BUILD-DEFECT/PREREG-cpl.txt` (`9353ecdc`) |
| discriminator | `crates/strehl-cli/examples/defect-cpl-split.rs` |
| labelling | `experiments/BUILD-DEFECT/src/44-cpl-label.py` |
| logs | `out/43-cpl-split.log`, `out/44-cpl-label.log` |
| runtime | 2.3 min for 360 raw decodes |

### 18.11 The verifier caught itself being blind, which is the point of having one

`experiments/BUILD-DEFECT/src/45-verify-s18.py` checks every number in §18
against `43-cpl-split.log` and `44-cpl-label.log`. **It contains no measured
value.** Both sides of every comparison are parsed — the document under test on
one side, the log on the other — because a checker holding its own expected
values verifies the checker. Another lane this session ran 37/37 green and then
caught 5 of 13 planted defects for exactly that reason.

It is commissioned by planting six defects into a scratch copy of this document
and requiring RED on each. Every mutation is anchored on a unique full-line
string and hard-errors if the anchor does not land, because a `replace()` that
silently matches nothing produces a green run that means nothing.

**The first commissioning run caught 5 of 6.** The miss is worth recording:

> plant: `edge-matched at 38  p95 0.052 pp` → `0.025 pp` in §18.6.
> Result: **GREEN. Defect missed.**

`0.052` appears **twice** in §18 — once in §18.5's bound table and once in
§18.6's code block — and the check was pinned to the first. A presence-based
check is satisfied by any duplicate of the value, so §18.6 was being verified by
a copy of a number it was not testing. The repair is one anchor per site plus
two **derived** checks that recompute rather than string-match (the 2.1×
widening is recomputed as the quotient of the two logged p95s). Final state:

```text
   partition: 34 checks = 34 agreed + 0 disagreed + 0 doc-not-found + 0 log-not-found
   selftest: 6 plants = 6 caught + 0 missed
   == verdict: live GREEN, commissioning PASSED ==
```

Had I shipped the verifier on its live GREEN alone, it would have been a
regression check that had never been shown to fail — a hypothesis wearing the
costume of a test.

---

## 19. THE EXPOSURE FLAG, AND WHAT THE DEFECT MAP ALREADY COVERS

### 19.1 The premise check: two files differed, one image did not

The orchestrator reported verifying `--exposure=3` against `--exposure=-3` on
the pin binary and observing **two different file hashes**, and read that as the
flag working. It is the same inference §14 was written to refute, one step
further along. A 16-bit TIFF from this renderer carries an `ImageDescription`
holding the tone anchors and the requested exposure, and §14 measured those
anchors scaling by *exactly* the commanded gain — `8.0000 / 0.1250 / 6.1050` —
while the pixel array stayed bit-identical across all 98,898,048 samples. Two
renders can therefore differ in hash, differ in banner, and be the same picture.

> An argv records the request and a banner records the claim; **a hash records
> the file.** Only the pixels record behaviour.

So `58-stack-path-exposure.py` reads the pixel arrays and nothing else. It does
not consult `ImageDescription`, because that is the surface already known to
move when the image does not.

### 19.2 The two paths, and which one `stack` takes

**P58 (MEASURED).** `main.rs` declares both `mod merge_cmd` and `mod stack`, and
dispatches them to different subcommands:

```text
crates\strehl-cli\src\main.rs:856    } => stack::run(&StackOptions {
crates\strehl-cli\src\main.rs:873      Command::Stack {
crates\strehl-cli\src\main.rs:1084       merge_cmd::run(&MergeOptions {
```

`Command::Stack` reaches **`merge_cmd::run`**, not `stack::run`. Commit
`9cb7f5d9` added `Develop::exposure_gain` in `image_out.rs` and wired it in
`stack.rs` — a real fix on a path the `stack` subcommand does not take. The
run banner confirms the destination independently: `merge backend : pyramid
(default)`.

### 19.3 The measurement

Subject `coffee-bubbles`, 19 frames, 7032 × 4688, `--srgb`, three arms.

| arm | binary | samples moved | delivered |
| --- | --- | --- | --- |
| A `--exposure=1` vs none | before patch | **0 of 98,898,048** | 1.0 (bit-identical) |
| B `--exposure=1` vs none | after patch | **98,821,621 of 98,898,048** | **2.0132800×** |
| C default `--srgb` only | before vs after | **0 of 98,898,048** | unchanged |

Arm A: `max |delta| 0 DN`, while the banner read `exposure : +1.00 stops (gain
2.000x), as asked` and the two hashes differed (`A9F7D7DC…` vs `51164D7A…`).
That is the whole defect in one line — the request reached the banner and the
header and did not reach the image.

Arm B against a commanded `2.0000000×` is **+0.664%**, n = 43,001,570.
**This is not as clean as §15's ±0.25-stop measurement, which returned
−0.048%, and the difference is not diagnosed.** Two non-linearities are active
at +1 stop and absent at ±0.25: 76,427 samples are pinned at an endpoint, and
the highlight chroma roll-off is in play (`highlight::tests::
the_rolloff_commutes_with_the_exposure_gain` asserts commutation, not
identity). Clipping drags a slope *toward* 1.0 and so cannot explain an
overshoot; the roll-off can, but I have not measured that it does. The
low-exposure figure is the trustworthy one; **+0.664% is reported, not
explained.**

### 19.4 Requirement 4, restated and re-measured

Arm C is the one that protects the 26 delivered masters: the default `--srgb`
render is **bit-identical before and after the patch**, 0 of 98,898,048 samples
moved, `max |delta| 0 DN`. `exp2(0)` is exactly `1.0` and `x * 1.0` is `x`
bit-for-bit, so this is a property of the arithmetic rather than a lucky
rounding. **Both byte-freezes HOLD** — the `strehl-cli` integration bucket
passes 5/5 including the freeze test, and `byte-freezes.tsv` is untouched.

Suite: **713 pass / 0 fail**, up one from 712 for the new guard.

### 19.5 The guard was commissioned RED, in the tree it will live in

`every_writer_develop_carries_the_exposure_gain` counts `.develop(` sites
against `.with_exposure_gain(` sites and requires them **equal**. A presence
check would be satisfied by any one occurrence and would still pass the day a
third writer is added unchained — the exact blind spot that let the original
defect ship. The needles are assembled at runtime so the test cannot count its
own source text.

Planting the original defect — deleting the demosaic branch's wiring — gives:

```text
2 writer develop site(s) but only 1 carry the exposure gain builder.
test result: FAILED. 0 passed; 1 failed
```

Restored: `test result: ok. 1 passed`. The guard has been shown to fail on the
defect it exists to catch.

### 19.6 The restore read a false RED, and the reason generalises

Restoring the file from `$env:TEMP` and re-running returned **FAILED** again,
with the wiring demonstrably back in the source (`Select-String` found both
sites) and the restored file hashing equal to the backup. The cause is that
`Copy-Item` **preserves the backup's `LastWriteTime`**, which was older than the
mutated build, so cargo's mtime fingerprint judged the crate up to date and the
test ran the stale mutated binary. `include_str!("merge_cmd.rs")` bakes the
content in at compile time, so a skipped rebuild is a skipped mutation.
Setting the mtime to now produced `Compiling strehl-cli` and `1 passed`.

The false-RED direction cost a cycle. **The false-GREEN direction is the one to
fear:** a mutation written with an older timestamp would not rebuild either, the
guard would report GREEN with the defect present, and the commissioning would
bank a blind metric as proven. A restore is not complete until the build system
has been made to notice it.

### 19.7 What `defect_map.rs` already covers — the hot-pixel answer

Asked plainly, so it is not assumed wrong again. **Hot pixels are built, not
outstanding.** `crates/strehl-core/src/defect_map.rs` carries `HotSite`,
`HotParams`, `HotCensus`, `HotFloor`, `detect_hot`, `hot_residual`,
`hot_area_fraction` and `Correction::HOT`.

- **Identified from the darks (§3.1).** 6σ same-plane neighbour excess with
  recurrence ≥ 6/11 ISO groups — recurrence across independent groups, not a
  sigma threshold, because that is the correct discriminator (M22). Census
  **14,626**: R 111 / G1 125 / G2 8,157 / B 6,233. Row asymmetry
  `(G2+B)/(R+G1)` = **60.97×** against M101's **61.1×**. External agreement:
  M101 14,604 (+0.2%), M48c 13,650 (+7.2%), M22 11,393 (+28.4%); 462 sites
  recur at 11/11.
- **Behaviour under the warp: identical to dust, and handled identically.**
  Both classes are fixed in sensor coordinates, so both smear along the
  per-frame similarity if corrected late.
- **The ordering is measured, not chosen (§6.2).** `load_frame` applies the map
  **between the levels check and `warp_frame_in_place`**, and two tests hold it
  there: `dust_correction_must_precede_the_warp_to_land_on_the_defect` fails if
  those lines move below the warp, and
  `with_an_identity_warp_the_two_orderings_are_bit_identical` is its null —
  it proves the first test measures the *ordering* rather than the resampler.
- **It ships OFF, and that is a measured decision.** Split-half reproducibility
  by amplitude stratum is 0.000 / 0.116 / 0.607 / **1.000** / **1.000**, and
  **only 111 of 14,626 sites** lie at or above the 8 e⁻ floor where
  reproducibility reaches 1.000. M101 already measured the arm immaterial to
  the election. The hot arm is **a working mechanism whose population is
  mostly noise** — that is a different claim from "unbuilt", and the honest
  summary is that it is built, commissioned, and not worth turning on.

So of the original brief's two classes, dust is the live question and hot
pixels are closed with a null. §19.7 exists because the null was previously
legible only by reading §3.1 and §6.2 together.
## 20. THE PLANTED-MOTE FIDELITY INSTRUMENT, AND THREE DEFECTS IT FOUND IN ITSELF

ORCH asked for evidence that the correction can be turned ON: a measured
improvement on real stacks, no print-gate regression, a planted-improvement
arm, and proof that the corrector does not invent detail. This section
delivers the first half of the split ORCH accepted -- **planted-mote
fidelity measured against truth**. It makes no claim about the two real
motes; that is the print gate's question and it is still open.

The instrument is `crates/strehl-cli/examples/defect-plant-fidelity.rs`.
Every number below is from `experiments/BUILD-DEFECT/out/62-plant-fidelity.log`.

### 20.1 The geometry refusal was a real question, and the answer was not the safe one

The first run refused. The flats decode a 3520x2344 quad grid; `coffee-bubbles`
decodes 3516x2344. The embedded map declares `sensor 7032 4688` while its own
header records that it was built from 160 flats -- which decode at 7040. So the
shipping map is applied to two different bodies, and P39's census had labelled
the wide one:

```
DOES NOT MATCH -> the correction refuses
```

That label was a **prediction about `check_geometry` printed by code that never
called `check_geometry`**. P61 called it:

```
narrow 7032x4688  ADMITTED   mismatch 0.0000% vs bar 1.00%
wide   7040x4688  ADMITTED   mismatch 0.1138% vs bar 1.00%
```

`MAX_ACTIVE_MISMATCH_FRAC = 0.01` and 8/7032 = 0.1138%, so the wide body is
admitted, not refused. The census was wrong and is corrected.

Admission is the *more* dangerous outcome of the two, because a refusal fails
loudly at fold frame 0 while an admission could misregister every corrected
quad in silence. So the displacement was measured rather than assumed, by
reading the active origin from a real frame of each geometry:

```
narrow  7032x4688 at (0,0)   DSC00034.ARW
wide    7040x4688 at (0,0)   DSC00001.ARW
active origin same in both : true
max mapped quad px 3448, narrow quad limit 3516  -> all named quads inside both
```

Shared origin means quad (px,py) addresses the same photosite in both bodies;
the extra 8 columns extend the right edge only. **Displacement is zero and the
admission is safe** -- for the 1,135 quads this map names, all of which are
inside the narrower width. The census now reads `exact-match 15 / 27,
differing-but-admitted 12 / 27`.

This does not generalise to a map whose quads reach past 3516, and nothing in
the module currently enforces that. Recorded as an open item, not fixed here.

### 20.2 The cleanliness test rejected every site, and the refusal was the finding

ORCH's first requirement was to plant only where the truth is genuinely clean.
The first cleanliness test high-passed a 20-frame mean flat and required the
residual below 0.125%. It refused all 110,538 candidates.

A search that rejects every input is not a strict search, it is an
uncommissioned one -- so the refusal was partitioned before it was believed:

```
scanned 110538 = near-mote 568 + near-exclude 0 + too-dirty 109970
               + no-signal 0 + accepted 0  [sums]
best residual among eligible candidates: 0.60701% against a floor of 0.12500%
```

Only 568 sites were excluded by mote clearance. The whole field read dirty, at
about 5x the floor. Without the partition this would have read as "the sensor
is filthy"; with it, the failure is clearly in the statistic.

### 20.3 Split-half reproducibility, and why the sign is load-bearing

A fixed multiplicative defect is identical in two independent estimates of the
field; shot noise is not. The 120 usable flats were therefore accumulated into
two **interleaved** halves -- used frame 0,2,4,... against 1,3,5,... The
interleaving is the control for ORCH's own caveat about moving cloud: splitting
the sequence into a first and a second half would put the illumination drift
entirely into the difference between halves, and the statistic would read the
weather as irreproducibility.

Split-half agreement removed the shot noise and the site still read dirty.
That reading is not a remembered one: the statistic this suite replaced is
re-measured on the same pixels in every run, as a gated commissioning arm, so
the claim lives or dies with the current log:

```
PRIOR-STAT  unsigned worst quad   0.47301%   expect >= floor   PASS
```

This is the part worth keeping. **Split-half cannot remove PRNU.** Per-photosite
response non-uniformity is a fixed multiplicative pattern, so it is
reproducible *by definition* and appears in both halves at full strength. At
0.473% it is 3.8x the floor, and no site on this sensor could ever have been
certified. The floor was not too strict for the dust; it was below the sensor's
own grain.

PRNU and dust are separable by **geometry**, not amplitude: PRNU is spatially
white, a mote is a correlated disc tens of quads across. So the statistic keeps
the sign of the reproducible residual and averages it over a dust-sized disc.
PRNU cancels toward zero as 1/sqrt(area); a coherent disc does not. Measured at
the site the search finally chose:

```
disc response 0.00001%   worst single quad in the same region 0.46105%
```

A separation of about 4.6e4 between the two statistics on the same pixels,
while the planted-defect arm still reads 1.88% on the disc statistic. That is
the evidence the disc average is cancelling PRNU rather than cancelling
everything.

### 20.4 Commissioning the cleanliness statistic, including an arm that had to be rewritten

Five arms, gated before any site is certified:

```
PRIOR-STAT  unsigned worst quad          0.47301%   expect >= floor         PASS
BASELINE    untouched site               0.01388%   expect < floor          PASS
DEFECT      disc in both halves          1.88280%   expect >= 4x baseline   PASS
NULL        disc in one half only        0.04113%   expect <= 25% of span   PASS
IMPROVEMENT planted mote divided out     0.03613%   expect back to baseline PASS
```

The PRIOR-STAT arm exists because the first draft of this section quoted
0.47301% from a run whose log had since been overwritten by a later run of the
same script. The number was right, but nothing on disk backed it. Re-measuring
the superseded statistic inside the live suite, and gating it, converts a
citation into a measurement -- and the arm would fail, loudly, if PRNU on this
sensor ever fell below the floor and the argument for the replacement
evaporated.

The NULL arm is the one that proves the statistic suppresses non-reproducible
structure rather than merely being small, and the IMPROVEMENT arm is ORCH's
requirement that the statistic be able to score a fix and not only a defect.

**The first version of this suite failed its own NULL arm for the wrong
reason.** It scored the null against the absolute floor and read `0.40489% >=
0.125% FAIL` -- while baseline at the same site was 0.47301%. The one-sided
stamp had moved the statistic *downward* by 0.068%, which is exactly what the
null wanted to see. Scoring against an absolute floor instead of against
baseline turned a passing null into a failing one. Every arm is now scored as a
response above baseline, and the span `DEFECT - BASELINE` is the scale the
other two are judged against.

### 20.5 Two more instrument defects, both caught by disagreement rather than by inspection

**A search with two floors.** The site search accepted candidates on
cleanliness alone, returned quad (1441,553), and the run then refused because
that site sits at 0.016 of range on the subject. Cleanliness is a property of
the sensor and brightness is a property of the scene; a search that optimises
one and discovers the other afterwards has a hidden second criterion. Subject
signal is now a search criterion with its own census bucket
(`dark-on-subject`), which is where 85,764 of the 110,538 candidates go.

**Two statistics wearing one name.** After that fix the search accepted a site
at >= 0.080 of range and the final gate refused the same site at 0.079 -- twice,
at two different sites. `mean_signal` was indexing `(oy + qy*QUAD)*stride + ox +
qx*QUAD`, the top-left photosite of every quad, which under a Bayer CFA is
always the same colour channel. It was reporting the red channel's level and
calling it the site signal, while the search used `quad_mean` over R, G, G and
B. Not a boundary case: a channel bias. `mean_signal` now averages the whole
quad and the site reads 2061.4 DN = 0.139 of range.

Both were found because two numbers that should have agreed did not. Neither
would have been visible by reading the code.

### 20.6 The six arms

```
A CHARGE       planted, uncorrected    residual   91.307 DN   ring  70.088 DN
B FIDELITY     planted, exact gain     residual    0.097 DN   ring   0.019 DN
E PERVERSE     planted, 2x gain        residual   91.322 DN   ring  70.069 DN
C CONTAINMENT  distant clean site      moved   0 sample(s)
D INVENTION    HF energy   truth 334.6762   B 334.7147   E 346.7149
F0 MISMATCH    gaussian mote, raw      residual   67.365 DN   ring  38.119 DN
F  MISMATCH    gaussian, parabolic fix residual   31.825 DN   ring  33.250 DN

partition: 6 arms = 6 pass + 0 fail + 0 undefined
```

Every corrector report partitions: `examined 697 = corrected 697 + no-change 0 +
clipped 0 + outside 0` on all four corrected arms.

- **C CONTAINMENT** is exact, not tolerant: 0 samples moved at a distant
  certified-clean site the map does not name. This is the null ORCH asked for
  -- a corrector that repaints everywhere would look excellent on a planted
  mote and destroy the image.
- **D INVENTION** is measured, not argued. It is also structurally weak by
  design, because `DefectMap::apply` reads and writes the same index with no
  neighbour and no inter-frame term (§13, verified again here). The corrector
  cannot reconstruct texture because it never reads a second sample.
- **E PERVERSE** reads 91.322 DN against B's 0.097. That E lands within 0.02 DN
  of the uncorrected arm A is expected arithmetic, not a coincidence: a 2x
  correction over-restores by exactly the attenuation depth, so the residual
  magnitude matches the uncorrected one.

### 20.7 Arm B is circular, which is why arm F exists

`mote_map` sets `gain = 1.0 / plant_profile(d)` on the same `d` the plant used.
Arm B therefore corrects a mote that is the algebraic inverse of the
correction, and its 0.097 DN establishes exactly two things: that `apply`
implements `(v - black) * gain + black` correctly, and that u16 rounding costs
about a tenth of a DN. It establishes **nothing about a mote the model does not
fit**, and real dust does not consult the map's profile function.

Arm F plants a **Gaussian** mote -- same centre, same central transmission,
same footprint radius, `sigma = PLANT_R/2` -- and corrects it with the
parabolic map:

```
uncorrected  residual 67.365 DN   ring 38.119 DN
corrected    residual 31.825 DN   ring 33.250 DN     -> 52.8% of the charge removed
```

It passes, and the pass is narrow in the direction that matters. The residual
halves, but the **footprint edge barely moves**: 33.250 against 38.119, a
reduction of 12.8%. A shape-mismatched correction leaves a correction ring
almost as strong as the mote's own edge. That is the honest limit of this
result and it bears directly on the default-ON question, because §13.6 measured
that stored depth can be wrong by up to 4.3x -- wrong amplitude is the normal
case, not the edge case.

### 20.8 What this section does and does not license

It licenses: the corrector, given a map that names the right quads with the
right gains, restores a planted mote to quantisation, touches nothing outside
the quads it names, adds no high-frequency content the truth lacks, is charged
more when its amplitude is wrong, and still removes half the charge of a mote
whose profile it does not model.

It does not license turning the correction ON. Nothing here measures the two
real motes, for which no independent clean reference exists, and nothing here
touches the print gate. (An earlier draft cited a standing of 17 PASS / 5 FAIL /
4 REFUSED. That split was withdrawn by ORCH on 2026-08-27: `recert.py` re-measured
`orch_printready.py` at 17 PASS / 0 FAIL / 9 ACQUITTED, and `recert.py:456` records
that the phantom FAILs were 5 ACQUIT->FAIL transitions mislabelled as PASS->FAIL.
The withdrawn figure also named the wrong instrument for this clause -- see 22.)
In ORCH's words:
**planted-mote fidelity measured against truth; real-mote improvement measured
against the print gate; no claim that the second inherits the first.** The
second is not yet measured. §13.1 stays OFF until it is.

### 20.10 The verifier missed a plant, and the reason is the same one twice

`63-verify-s20.py` parses every claim out of the report and every ground truth
out of the log the report cites. Nothing in it is an expected value: a checker
that compares the artifact against its own constants runs green while the
artifact drifts, which is how another lane scored 37/37 and then caught 5 of 13.

It read 30/30 on the first pass. `64-commission-s20.py` then planted 14 known
defects and it caught **13**:

```
plants declared : 14   caught 13   missed 1   unanchored 0   [sums]
MISSED  arm F ring -- verifier stayed GREEN
```

Arm F's ring is stated twice: once in the §20.6 table and once again in §20.7's
prose. Only the table was pinned, so the prose could be changed to any value at
all and the verifier would not notice. **A presence check is satisfied by any
duplicate of the value.** This is the second time this exact failure has been
recorded in this report -- §18.11 is the first, where `0.052` occurred at two
sites and the check was pinned to one.

The repair was four site-scoped claims plus two DERIVED checks that recompute
`52.8%` and `12.8%` from the report's own residuals instead of string-matching
them, so a percentage cannot agree with itself while disagreeing with its
inputs. Two further instrument defects surfaced during that repair and both are
worth naming, because they are the kind that make a checker quietly weaker:

- Four claims resolved against the **wrong site**, because the §20.6 table
  states the same quantities and matched first. Fixed by giving each claim an
  explicit scope rather than searching the whole section.
- `corrected\s+residual` matched inside **un**`corrected`, so the derived check
  compared 67.365 against itself and reported `0.0000%` removed. It read as a
  mismatch rather than a pass, which is the safe direction, but a substring
  collision that had landed the other way would have been a silent green.

Final state:

```
claims declared : 36 (34 parsed + 2 derived)   resolved 36   unresolved 0   mismatched 0  [sums]
plants declared : 14   caught 14   missed 0   unanchored 0  [sums]
report restored byte-identical : True
```

The commissioning script backs the report up to `$env:TEMP` and restores from
that copy, never `git checkout --`, and it verifies the restoration is
byte-identical before it exits.

### 20.9 Artifacts

| Path | What it is |
| --- | --- |
| `crates/strehl-cli/examples/defect-plant-fidelity.rs` | The six-arm instrument and the four-arm cleanliness commissioning |
| `crates/strehl-cli/examples/defect-geometry-verdict.rs` | P61: calls `check_geometry` instead of predicting it |
| `crates/strehl-cli/examples/defect-geometry-census.rs` | P39, with the false refusal label corrected |
| `experiments/BUILD-DEFECT/out/61-geometry-verdict.log` | The admission verdict and the origin reads |
| `experiments/BUILD-DEFECT/out/62-plant-fidelity.log` | All six arms and the commissioning |
| `experiments/BUILD-DEFECT/out/60-geometry-census.log` | 15 exact-match / 12 differing-but-admitted |
| `experiments/BUILD-DEFECT/src/63-verify-s20.py` | Verifies this section; 36 claims, no constant of its own |
| `experiments/BUILD-DEFECT/src/64-commission-s20.py` | Plants 14 defects and requires the verifier to catch each |
| `experiments/BUILD-DEFECT/out/64-commission-s20.log` | 14 caught / 0 missed / 0 unanchored |

Suite at the time of writing: 713 pass, 0 fail. Both byte-freezes hold.

## 21. THE HASH THAT SAID YES: `--exposure` WAS INERT AT THE PIN, AND THE SEALED CORPUS INHERITED IT

This section was not planned. It is what happened when I tried to render a
matched OFF/ON pair for the default-flip decision (§13.1, Q1) and could not get
the OFF arm to look like the sealed master it was supposed to match.

### 21.1 The premise I was working from, and how it broke

The orchestrator had tested the claim that `--exposure` does nothing, and had
recorded the test as follows: on pin binary `9b05d0b7`, `--exposure=3` and
`--exposure=-3` "produce **different files**" with SHA-256 prefixes
`D749F1FDCD07355F` and `A5846DD2B0ACDC3A`, the banner reads "as asked", and the
pin folds the gain into the normalisation. On that evidence the accusation was
withdrawn before it reached the README.

I was replaying each subject's recorded `exposure_stops` from the SHIP-V4
manifest so that my OFF arm would be comparable to the sealed corpus the print
gate grades. On subject `109MSDCF`, `exposure_stops` is `+2.60`. The seal has a
mean of 47719.1 and 0.0012% of samples at full scale. My HEAD render at the same
`+2.60` came back at mean 61822.1 with **85.5234%** of samples clipped.

Both binaries printed the identical banner:

```
exposure   : +2.60 stops (gain 6.063x), as asked
```

The banner is not evidence of what was applied. That trap is registered twice
already in this project and it caught me a third time, on the input side: I
believed a recorded parameter because a banner had once confirmed it.

### 21.2 The measurement

I rendered `109MSDCF` five times and compared the outputs sample by sample over
the full 98,898,048-sample plane. `experiments/BUILD-DEFECT/src/72-exposure-inert-at-pin.py`.

```
pair                   stops commanded samples differ  % differ    max |d|    mean |d|
------------------------------------------------------------------------------------
pin  +3    vs -3        6.00     64.0x              0   0.0000%          0      0.0000
pin  +2.60 vs 0         2.60      6.1x        451,463   0.4565%          1      1.0000
pin  0     vs -3        3.00      8.0x              0   0.0000%          0      0.0000
HEAD +2.60 vs 0         2.60      6.1x     98,856,221  99.9577%      65535  14013.6874
```

The first row is the orchestrator's literal evidence pair. I reproduced both of
its hashes exactly — `D749F1FDCD07355F` and `A5846DD2B0ACDC3A` — so this is the
same binary and the same experiment, not an adjacent one.

**Those two files are different bytes and the same image. Zero of 98,898,048
samples differ.** Across a commanded 64.0x linear gain, the mean is identical to
eight significant figures: 47719.088 against 47719.088.

The only pin pair that moved at all moved 0.4565% of samples by **exactly 1 DN**
of 65535 — every differing sample differed by one. That is dither, and the
instrument classifies it as such rather than reading it as a small effect.

### 21.3 Where the hash difference actually came from

Eleven bytes differ, at file offsets 339 through 359, inside the TIFF's embedded
description. Not in the pixel data, which begins after it and runs to
197,796,096 bytes.

```
exposure=+3 : ... Tone rendering: black 0.037985, white 1.311591 (linear, ...
exposure=-3 : ... Tone rendering: black 0.000594, white 0.020494 (linear, ...
```

```
black ratio +3 / -3 = 63.9478      commanded 2^6 = 64.0000    agreement 0.082%
white ratio +3 / -3 = 63.9988      commanded 2^6 = 64.0000    agreement 0.002%
```

The recorded tone points scale by **exactly the commanded gain**, and that is the
whole mechanism. From the pin, `git show 9b05d0b7:crates/strehl-cli/src/stack.rs`:

```rust
let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain * eg / range;
```

`eg` multiplies the linear image. The tone rendering then chooses black and
white as luminance percentiles **of that same already-gained image** and
normalises by `(white - black)`. The gain divides out to the last bit. The file
faithfully records the two numbers that cancelled it.

So the gain was applied, and then removed, and the removal is what got written
into the metadata that made the hashes differ. **The file's record of the
request is the thing that made the test say yes.**

### 21.4 Why the test could not have failed

The check was "do the hashes differ". `--exposure=N` writes N into the file's
tone record. Therefore any two distinct values of `--exposure` produce different
hashes **whether or not the flag does anything to the image**. There is no value
of the flag for which the test could have returned "same file". A test that
cannot return the answer that would falsify the claim is not evidence about the
claim.

This is the same shape as §17's `E*`: a quantity that moves for a reason
unrelated to the thing being graded. Here it is narrower and sharper, because the
confounder is not a subtle statistical dependence — it is a literal transcript of
the command line embedded in the artifact under test.

A hash is a presence test. It answers "did any byte move", never "did the image
change". The two questions have opposite answers here.

### 21.5 Commissioning

A difference detector that reads quiet on everything would print "no-op" for
every input and look like a finding, so the readings above are gated on three
arms, all of which must pass before any verdict is printed:

```
positive control : HEAD +2.60 vs 0, max |d| = 65535 DN, needs >= 256  ->  LOUD
negative control : pin-eneg.tiff against itself, 0 samples differ     ->  SILENT
improvement arm  : HEAD mean 61822.1 at +2.60 vs 47814.3 at 0         ->  brighter
```

The improvement arm is the one that earns its place. The two controls establish
that the detector can see a difference and does not invent one, but both are
satisfied by a detector that reports `|delta|` with its operands transposed. The
third arm checks a **signed** quantity — a positive gain must brighten — so a
detector that had exposure running backwards could not pass all three.

The verdict band is `INERT <= 2 DN`, `LIVE >= 256 DN`, and **AMBIGUOUS between**,
so the instrument can decline. `INERT_MAX_DN` is 2 rather than 0 because a
renderer is entitled to dither; the question is whether a 64x gain is
distinguishable from rounding, not whether the pipeline is bit-deterministic.
The four declared pairs partition as 4 measured + 0 missing-input + 0 failed,
asserted to sum, and a pair whose input is absent reads UNDEFINED — never PASS.

### 21.6 The consequence, which reaches past this lane

`exposure_stops` in `C:\dev\strehl-out\acceptance\SHIP-V4\manifest.tsv` was
chosen under semantics where it did nothing. The 26 sealed masters are, to the
bit, zero-exposure renders. Commit `9cb7f5d9`/`f2254c12` made the flag real by
applying the gain past the tone normalisation — which is the correct fix — and
in doing so it **silently invalidated every recorded exposure value in the
corpus**.

```
subject 109MSDCF, exposure_stops = +2.60
  SHIP-V4 seal                     mean 47719.1   clipped 0.0012%
  pin  9b05d0b7  --exposure=+2.60  mean 47719.1   clipped 0.0012%   reproduces the seal
  HEAD           --exposure=+2.60  mean 61822.1   clipped 85.5234%  blown out
  HEAD           --exposure=0      mean 47814.3   clipped 0.0013%   0.20% from the seal
```

Anyone who re-renders the sealed corpus at HEAD using the manifest's own
parameters will produce blown-out images and grade them. Nothing warns them: the
banner says "as asked" in both binaries, and it is telling the truth about the
request in both cases.

The correct HEAD replay of a SHIP-V4 seal is **`--exposure=0`**, and that follows
from the measurement rather than from taste: if the recorded value did nothing,
the seal is the zero render. The residual 0.20% is other pin-to-HEAD drift and is
not attributable to exposure.

### 21.7 What this cost me, and what it is worth

It cost the pilot renders. §21.6 explains why `109MSDCF` read CLIPPED in the
first arm-mechanism probe: at 85.5% saturation the correction had no headroom to
show in, and I had briefly taken that for a property of the subject. Those
renders are void and the Q1 default decision is unblocked but not yet made.

What it is worth is that the ledger now reads correctly in three places it did
not. The exposure accusation was **true**. The lane that raised it was right, the
fix that landed was necessary, and the test that dismissed it was structurally
incapable of dismissing anything. And the sealed corpus has a documented
incompatibility with the binary that is supposed to succeed it, found from the
outside, by a lane that was trying to do something else.

### 21.8 What the commissioning found in the verifier

The verifier read clean before it was commissioned. Then 18 planted defects
were run through it and it caught 16. The two it did not are both defects in the
instrument, and neither was visible by reading it. The suite has since grown to
22 plants, four of them covering this subsection's own figures, and it now
catches every one.

```
declared 22 = caught 22 + missed 0 + unanchored 0     (after the repairs below)
clean control : PASS -- declared 58 = matched 58 + mismatched 0 + unresolved 0
restoration   : byte-identical to the original, verified by SHA-256
```

**A tolerance argument that meant something other than what its call site
assumed.** The clip-fraction check was written as `v.check(..., truth, 0.05)`
with the intent of allowing 0.05 percentage points. The fourth positional
parameter is a *relative* tolerance, so the check actually allowed 5% — which on
an 85.5234% clip fraction is **4.3 percentage points** of slack. A planted
0.2 pp error passed. The sizing note I wrote next to that plant said "check is
abs 0.05 pp", so the comment and the code disagreed and the comment was the one
I trusted. Repaired by naming both parameters and giving `check` an explicit
`abs_floor`, because a single relative tolerance cannot serve a quantity that
ranges from 0.0012% to 85.5234% while the report rounds it to four decimals.

**A presence test standing in for a reference.** The hash check asked
`"D749F1FDCD07355F" in sec`. Both prefixes appear twice in this section — once
in 21.1 quoting the orchestrator and once in 21.2 reporting the reproduction —
so corrupting either occurrence leaves the other to satisfy the test. The plant
anchor guard caught this first and reported **UNANCHORED**, refusing to score
rather than mutating an occurrence it could not identify; that refusal is what
exposed the duplication. Repaired by parsing both prefixes out of one canonical
sentence, so the check has a site rather than a haystack.

The general form, which this project has now hit in three separate instruments:
**a check satisfied by any copy of the value is not checking the copy you care
about.** Give each measured number one canonical site and pin its check there.

### 21.9 Artifacts

| Path | What it is |
| --- | --- |
| `experiments/BUILD-DEFECT/src/72-exposure-inert-at-pin.py` | The gated difference instrument and its three commissioning arms |
| `experiments/BUILD-DEFECT/out/72-exposure-inert-at-pin.log` | 3 INERT / 1 LIVE, partition 4 = 4 + 0 + 0 |
| `experiments/BUILD-DEFECT/out/72-exposure-inert-at-pin.json` | Per-pair counts, verdicts and the gating thresholds |
| `experiments/BUILD-DEFECT/src/73-verify-s21.py` | Verifies this section; 58 claims, no expected value of its own |
| `experiments/BUILD-DEFECT/out/73-verify-s21.log` | 58 declared = 58 matched + 0 mismatched + 0 unresolved |
| `experiments/BUILD-DEFECT/src/74-commission-s21.py` | Plants 22 defects, each anchored and sized against its check's tolerance |
| `experiments/BUILD-DEFECT/out/74-commission-s21.log` | 22 caught / 0 missed / 0 unanchored, restoration verified |
