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

### 0.3 Two corrections to the brief's facts

- **P1 (MEASURED).** `D:\macro-dark-frames` holds **242** frames in **11 ISO
  groups of 22**, ISO 50–2000, all 1/100 s — not "22 dark frames".
- **P2 (MEASURED).** **20 of the 26 subject stacks are f/5.6**, the same
  aperture as the flats. M71's caveat that its mask is "a lower bound, the
  corpus shoots f/8–f/11" does not apply to most of the corpus.

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
corrector, metric, CLI wiring — **off by default**, plus a photograph-derived
map holding the two real motes. The default-off is now a *measured* decision:
the map that a naive flats pipeline produces is actively wrong.

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

### 6.2 Not built, and why

**P21.** `crates/strehl-cli/src/stack.rs` is the `argmax-baseline` negative
control, **not** the shipping `strehl stack`. The shipping path is
`main.rs:797 Command::Stack → merge_cmd::run`, with per-frame decode at
`merge_cmd.rs:4297 fn load_frame`. **Both files are outside my lane.** The patch
needed there is three lines — call `defect_plan_from_env` once in `run`, call
`map.apply` on the decoded frame in `load_frame` **before**
`warp_frame_in_place`, fold the report — and I am handing it to the orchestrator
rather than reaching across lanes.

`STREHL_DEFECT_MAP` is also not in `byte-freeze.rs`'s `RENDER_ENV`, which I
cannot edit. Harmless today because both freeze rows render through `merge_cmd`,
which is untouched — but once the shipping wire-up lands, the variable must be
added to `RENDER_ENV` or the freeze stops being hermetic.

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

1. **Wire `merge_cmd::load_frame`** (§6.2) and add `STREHL_DEFECT_MAP` to
   `RENDER_ENV`.
2. **Settle T5** — re-shoot flats immediately after a subject stack, without
   touching the CPL, and see whether the 25-quad offset persists.
3. **Aperture transfer (T1)** — the map at f/8 and f/11 from the three stacks at
   each.
4. **Run the Rust `detect_dust` on the real flats** to close T2, via a small
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
- **Q3.** Is a −8.24% mote visible to a print-quality reviewer, or is P19's
  ×1.034 in delivered sRGB below the threshold of notice? I measured the
  amplitude; I did not measure the *noticing*.

---

## 9. Rules discharged

| Rule | Where |
|---|---|
| 3 — inject, never derive | `DefectPlan.gain_dn_per_e` comes from the injected `NoiseModel`, not re-derived |
| 28 — local fact numbering | P1–P21 |
| 33 — never `-q`; a run with no `Compiling` line is not evidence | §10 quotes the `Compiling` lines |
| 40 — prior-art search first | §0.2; it reshaped the mission |
| Nothing is true until measured | Every number here is quoted from a persisted log in `experiments/BUILD-DEFECT/out/` |
| Commission every metric | §4.2, P15/P16/P17 — RED, GREEN **and** an improvement arm |
| A search must be able to fail | P5, P13, and the two explicit refusals in scripts 12 and 14 |
| Print, then TEST | §4.6 — `stack.rs` `ensure!`s the partition |
| Partition into counted outcomes | §4.6; `check_partition`; `every_site_lands_in_exactly_one_counted_outcome` |
| Typed errors over silent defaults | `DefectMapError`, 12 refusals; `a_typod_correction_arm_errors_rather_than_falling_back_to_the_default` |
| Off by default | `Correction::default()` is both arms off; `the_default_correction_is_off_and_changes_no_byte` |

---

## 10. Verification

```
cargo test --release -p strehl-core -p strehl-cli
   Compiling strehl-cli v0.0.0 (C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli)
   Compiling strehl-core v0.0.0 (C:\dev\blog\death-of-software\projects\strehl\crates\strehl-core)
    Finished `release` profile [optimized] target(s) in 47.91s

running 110 tests   ... test result: ok. 110 passed; 0 failed
running 5 tests     ... test result: ok.   5 passed; 0 failed
running 510 tests   ... test result: ok. 510 passed; 0 failed
```

**The byte-freeze HOLDS. Neither hash moved:**

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
