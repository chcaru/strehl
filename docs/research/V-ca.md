# V-ca: audit of ORCH's "default-on `--fix-ca` when the gear guard matches"

**Verdict: SHIP-WITH-CONDITIONS.** The recommendation is *scientifically* sound and I could
not break it: the win reproduces exactly, generalises to 6/6 subjects including the opposite
polarity and low-contrast cases ORCH asked for, grows with field radius the way lateral CA
must, and the default-on code path is **byte-identical** to the arm ORCH measured. Do not stop
the implementer on the evidence.

**But the flip must not land in its current state.** The default-on change ships a
**fully inverted user-facing status line**, in both directions, on the exact switch it makes
load-bearing. That is a one-site fix and it is not optional.

Auditor: V-CA. Pinned HEAD `96571ee`. ORCH's binary `3dfa435` (sha256 `458ECD00...`), verified.

---

## 1. The defect that blocks the flip

`crates/strehl-cli/src/merge_cmd.rs:3842-3846` reports CA status by reading the **raw
environment variable**, not the guard's decision:

```rust
"lateral CA      : {}",
match std::env::var(strehl_core::optics::CA_ENV) {
    Ok(k) if !k.is_empty() && k != "0" => format!("CORRECTING, profile {k:?}"),
    _ => "off (--fix-ca / STREHL_FIX_CA unset)".to_string(),
}
```

Before default-on, env state and behaviour were the same thing, so this was correct. The
default-on change decoupled them (`align_cmd.rs:1409-1410` now resolves through
`profile_for_capture_env`) and **did not update this line**. Measured, both directions wrong:

| operator sets | what the render actually does | what the log prints |
|---|---|---|
| nothing | **CORRECTING** (byte-proven below) | `lateral CA : off (--fix-ca / STREHL_FIX_CA unset)` |
| `off` | **not correcting** (byte-proven below) | `lateral CA : CORRECTING, profile "off"` |

Both lines are copied verbatim from `C:\dev\strehl-out\V-ca\guard\{defaulton,forcedoff}.log`.

`"off"` is non-empty and `!= "0"`, so it satisfies the guard clause and prints `CORRECTING`,
while `profile_from_setting` (`optics.rs:566`) maps it to `Ok(None)`.

This matters more than a cosmetic slip for three reasons:

1. **ORCH used this line as evidence.** The recommendation states *its log reads `lateral CA :
   CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl"`*. That happened to be true because ORCH set
   the variable explicitly. Under default-on the same line no longer tracks behaviour.
2. `--fix-ca` publishes into the environment via `set_var` (`main.rs:717-730`), so the CLI flag
   the recommendation names inherits the identical defect.
3. The module's own docs say a silent disagreement between switch and behaviour is *"the exact
   failure mode this whole milestone is trying to escape"* (`optics.rs`, `active_profile`).

Also stale, same cause: `main.rs:717-720` still says the profile is selected by
`active_profile`; the render path calls `profile_for_capture_env`.

**Minimum fix:** print the resolved `Option<&OpticalProfile>` (and, when the guard fired with
the operator silent, say so), not `env::var`. One site.

---

## 2. Claims 1-4

### Claim 1 - the fringe is reduced: **CONFIRMED**

Reproduced with ORCH's own instrument, `experiments/ORCH-drift-check/cafringe.py`, unmodified.
**Declared reproduction of ORCH's numbers**, and they match to 4 d.p.:

| bee-1-cpl edge | sigma(R-G) | sigma(R-B) | sigma(B-G) |
|---|---|---|---|
| ORCH published | 0.737 | 0.806 | 0.959 |
| V-ca measured | **0.7373** | **0.8061** | **0.9590** |

Flat placebo also reproduces: 1.0049 / 1.0059 / 0.9991 vs ORCH's 1.005 / 1.006 / 0.999.

**Generality - my own renders, five new subjects, same binary, same flags (`--gate 4
--base-mean --chunks 5`), `STREHL_FIX_CA` the only difference:**

| subject | polarity / contrast | f | CPL | edge sigma(R-G) ON/OFF | flat placebo sigma(R-G) |
|---|---|---|---|---|---|
| bee-1-cpl | dark on white (ORCH's) | 5.6 | yes | 0.7373 | 1.0049 |
| coffee-bubbles | **bright on near-black** | 8 | no | 0.8483 | 0.9947 |
| foam | bright, blown highlights | 8 | no | **0.3624** | **0.7983** |
| couch-fibers-cpl | **low contrast** (sd 0.105) | 5.6 | yes | 0.5434 | **0.8780** |
| flowers-cpl | **low contrast** (g99.9 0.121) | 5.6 | yes | 0.8564 | 0.9988 |
| wrapped-text-1 | text on white | 5.6 | no | 0.6032 | 0.9396 |

**6 of 6 improve.** The win is not an artefact of ORCH's subject.

**One qualification ORCH should carry:** `cafringe.py`'s docstring says *"a win that also moves
the placebo is not a win"*, and the placebo moves on 3 of 6. I do **not** read that as
indicting the correction. In a flat set the content is mostly read noise, and any resampling
attenuates noise, so the flat placebo reads below 1 wherever noise dominates. The subjects
whose placebo moves are exactly the ones whose flat sigma is smallest (foam 0.00098, an order
of magnitude below bee-1's 0.01236). So the placebo cannot separate "correction leaking into
flat regions" from "resampling attenuating noise" - which also means **bee-1's clean 1.005 was
luck, not validation.** ORCH generalised a single-subject placebo; it does not generalise.

### Claim 2 - red's correction is a genuine radial shift: **CONFIRMED**

Confirmed by an instrument independent of ORCH's phase correlation. Binning the *benefit* by
field radius, lateral CA predicts a correction that does nothing at the centre and grows
outward; a blur predicts roughly uniform change. Measured `sigma(R-G)` ON/OFF on the edge set:

| subject | 0.00-0.20 | 0.20-0.40 | 0.40-0.60 | 0.60-0.79 | 0.79-0.90* | 0.90-1.00* |
|---|---|---|---|---|---|---|
| bee-1-cpl | **1.0136** | 0.8068 | 0.6190 | 0.6247 | 0.6806 | n<2k |
| foam | 0.7289 | 0.4613 | 0.3511 | 0.2857 | 0.2924 | 0.2852 |
| flowers-cpl | n<2k | 0.8081 | 0.8328 | 0.8171 | 0.9290 | 0.6738 |

`*` = beyond the profile's declared `support_r_max: Some(0.788)`, which `optics.rs:362-365`
calls *"a 1.27x linear extrapolation. Declared, not enforced."*

Two findings ORCH did not have:

- **Monotone growth with radius.** This is the lateral-CA signature and a blur cannot produce
  it. It corroborates Claim 2 without using ORCH's estimator at all.
- **The corner extrapolation holds.** ORCH's weak point #3 was that all 155 tiles sat inside
  ~75 % of the field and the corners were unmeasured. They are now measured, and the
  correction still helps out there (bee-1 0.6806, foam 0.2852). This resolves weak point #3
  **in ORCH's favour** - the outcome I did not expect.
- **The centre is where it is worst.** bee-1 reads 1.0136 at r<0.2: marginally *harmful*.

### Claim 3 - the shift estimator is commissioned: **UNDERDETERMINED** (ORCH's weak point #5 is real)

ORCH plants with **bilinear** (`caradial.py:97-99`, written out longhand). The pipeline that
produced both arms gathers with **Catmull-Rom**, hard-coded: `blend-render.rs:376`,
`align_cmd::load_or_solve(&args.dir, &paths, 0, Resampler::CatmullRom)`. Different kernel,
different MTF - `restore.rs:10` puts Catmull-Rom at 0.940 at 0.25 cyc/sample.

So the recovery ratio 0.266 calibrates ORCH's own plant, not the pipeline's shift, exactly as
ORCH suspected. Consequences, split:

- The **radial/tangential ratio of 9.94 is not affected** in leading order: both components
  pass through the same estimator and the shrinkage divides out. Claim 2 survives.
- The **absolute px magnitudes (0.041 -> 0.094 -> 0.158 -> 0.177) do not.** Bilinear is the
  blurrier kernel, so the estimator recovers less from ORCH's plant than from the pipeline's
  shift, and dividing by 0.266 therefore **overstates** the true displacement by an unmeasured
  factor. Do not quote those four numbers as physical displacements.

I did not re-run the commissioning with a Catmull-Rom plant; that is the fix, and it is the
one number that would restore Claim 3. Marked UNDERDETERMINED, not refuted - the direction of
the bias is inferable but its size is not measured.

### Claim 4 - blue's arm may be free blur: **CONFIRMED**

Note first that `eps_b` is **no longer `None`** - BUILD-CHROMA landed `Some(174.4e-6)`
(`optics.rs:382`). Blue is actively corrected in both ORCH's arms and default-on.

Measured with my own high-pass instrument (3x3 box high-pass, RMS over the arm-mean edge set -
**not** ORCH's `caprice.py`, so these numbers are not comparable to ORCH's 9.36 % term):

| subject | sigma(B-G) benefit | B edge HF lost |
|---|---|---|
| bee-1-cpl | 4.1 % | 3.1 % |
| coffee-bubbles | **-0.2 %** | 3.9 % |
| foam | 20.8 % | 13.3 % |
| couch-fibers-cpl | 13.9 % | 9.7 % |
| flowers-cpl | 1.8 % | **12.6 %** |
| wrapped-text-1 | 7.0 % | 9.4 % |

**Blue's benefit is smaller than its high-frequency cost on 3 of 6 subjects**, and on
coffee-bubbles the chroma got marginally *worse*. The profile's own docs supply the mechanism:
blue's coefficient is the leave-one-out median of six per-stack measurements with **per-stack
range 101.3-222.7 ppm** - a 2.2x spread, worse than red's 23.6 % - and per-stack `r_squared`
**0.32-0.88**. The code already says it: *"It is the weaker arm and it may want a second-order
term."*

**Recommendation: default-on for red, keep blue behind an explicit opt-in** until it has a
second-order term or a tighter fit. That is a data-only change to `eps_b`, and it is the
cheapest way to keep the confirmed part of the win without the unearned part.

---

## 3. ORCH's three explicit questions

**(a) Does the win survive on a subject that is not a dark object on a white field? YES.**
`coffee-bubbles` is the opposite polarity (frame mean 0.0514, 0.9 % of pixels above mid-grey -
bright speculars on near-black) and improves 0.8483. `flowers-cpl` is the lowest-gradient
subject in the gallery and improves 0.8564. `foam` (f/8, blown highlights) improves most at
0.3624. No subject regressed.

**(b) Is blue earning its 9.36 %? Mostly NO** - see Claim 4. Benefit < cost on 3 of 6.
On ORCH's sampling worry: blue's tiles are not the issue, the coefficient is - a 2.2x
per-stack spread and r^2 as low as 0.32 is an under-determined fit, not an under-sampled one.

**(c) Does the guard still decline correctly once the default flips?**
**The behaviour is correct and I proved it in the render domain; the reporting is not.**
Built `blend-render` at `96571ee` and ran four arms on `bee-1-cpl`, all `--gate 4 --base-mean
--chunks 5`, hashing outputs per discipline 919:

| arm | operator sets | sha256 (40) | equals |
|---|---|---|---|
| `defaulton` | nothing | `20D895F219EAC92307A30525F8B1436E441AA68D` | **== ORCH's env-on arm** |
| `envon` | the profile key | `20D895F219EAC92307A30525F8B1436E441AA68D` | == defaulton |
| `forcedoff` | `off` | `4CFA8F25F7FC3C0A4AC1CEB10EDD741713A65F85` | **== gallery OFF arm** |
| `typo` | `a7c2-...-x4cp` | (no output) | errors, exit != 0 |

Three things fall out, all favourable:

1. **The default-on path is byte-identical to the arm ORCH measured.** Every number in ORCH's
   recommendation transfers to the new code path exactly - not "probably", identically. This
   is the strongest possible answer to *"a default is a new code path and prior verification
   does not transfer to it."* Here it does, and it is now proven rather than assumed.
2. **The off switch genuinely works.** `forcedoff` reproduces the uncorrected render
   byte-for-byte, so the newly load-bearing off path is correct.
3. `forcedoff == gallery-OFF(3dfa435)` also shows the unrelated `merge.rs` (+322) and
   `merge_cmd.rs` (+163) changes between the two commits did not perturb output at all.

`cargo test -p strehl-core --lib optics::` -> **24 passed, 0 failed**, including
`the_guard_declines_the_bare_lens`, `the_guard_declines_a_different_body`,
`the_guard_declines_an_unreadable_file`.

**What is still not verified, and cannot be here:** every one of those negatives is synthetic.
`optics.rs:685` says so itself - *"This guard has never declined a real file... the guard is
correct by construction, not by experiment."* I confirmed the premise empirically: all seven
subjects I read report identical `ILCE-7CM2` / `33094`. There is no real negative in the
corpus to test against. The existing ask for a short bracket without the teleconverter is the
right fix and remains open.

---

## 4. The guard is looser than the profile it gates

This is my one substantive addition to ORCH's own list of worries, and it is a scope problem,
not a measurement problem.

`matches_gear` (`optics.rs:641`) compares **body model and `lens_type3`, and nothing else**.
Real EXIF, read with `strehl_raw::identity` built at `96571ee`:

| subject | model | lens_type3 | **f_number** | CPL |
|---|---|---|---|---|
| bee-1-cpl, couch-fibers-cpl, flowers-cpl, wrapped-text-1 | ILCE-7CM2 | 33094 | **5.6** | mixed |
| foam, coffee-bubbles | ILCE-7CM2 | 33094 | **8** | no |
| 109MSDCF | ILCE-7CM2 | 33094 | **11** | no |

The guard admits all of them. The profile was fitted on `tweezers-cpl` and `bee-3-cpl` (red)
- both f/5.6, both with the CPL.

Two gaps, and they are not the same kind:

- **Aperture: closable, and free.** `optics.rs:357-360` sets `measured_at: None` with the
  comment *"lateral CA varies with aperture and magnification, so a guess here would silently
  widen the profile's claimed applicability."* The profile deliberately refuses to claim an
  aperture - and the guard that turns it on by default then ignores aperture entirely. That is
  an internal contradiction inside one file. `f_number` is **already parsed** by the identity
  reader the guard calls. Recording `measured_at` and comparing it costs one field and one
  comparison.
- **CPL: not closable, ever.** The profile key names the filter (`-x4cpl`) and
  `optics.rs:638` states the filter is invisible to EXIF and always will be. Default-on will
  apply a CPL-fitted profile to non-CPL captures. My data says this is *empirically* benign -
  `foam` and `coffee-bubbles` are non-CPL and both improved - so I do not treat it as
  blocking, but it should be stated in the release note rather than discovered later.

Note the favourable reading too: f/8 non-CPL subjects (`foam` 0.3624, `coffee-bubbles` 0.8483)
improved, so the coefficient does transfer off its fitted configuration. The gap is that
nothing in the code *knows* that; it is true by measurement, not by guard.

---

## 5. Measured harms

Real, and smaller than the benefit on every subject, but not zero. Measured where it is
unambiguous: **in the flat set there is no fringe to remove, so any HF loss there is blur.**
This is the step that breaks ORCH's dead end #1 - HF amplitude cannot price the edge set,
because fringe removal and blur both lower it, but the flat set has only one interpretation.

HF RMS ratio ON/OFF, flat set:

| subject | R | G | B |
|---|---|---|---|
| bee-1-cpl | 0.9715 | 0.9943 | 0.9882 |
| coffee-bubbles | 0.9849 | 1.0027 | 0.9960 |
| foam | **0.8566** | **0.9555** | 0.9721 |
| couch-fibers-cpl | 0.9599 | 0.9894 | 0.9737 |
| flowers-cpl | 0.9979 | 0.9992 | 0.9983 |
| wrapped-text-1 | 0.9567 | 0.9895 | 0.9684 |

R loses 0.2-14.3 % of flat high-frequency content. **Green loses up to 4.5 % despite being
bitwise frozen in camera space** (`l5_green_is_never_touched`,
`the_cfa_site_map_leaves_both_greens_bitwise_frozen`, both passing) - so that is entirely
downstream coupling through the Malvar-He-Cutler demosaic and the colour matrix, and it is a
cost paid by a channel the correction never touches.

Standing objection carried forward from my M107 audit (V-CA-audit.md section 6.4): the shipped
`eps_r = -704.5e-6` **over-corrects both subjects it was ever fitted on** (bee-3 -529.9 ppm,
couch-fibers -654.9 ppm; residuals +132.3 ppm / 25.0 % and +36.5 ppm / 5.6 %, all seven bee
rings positive at 25-30 sigma). Optimum strength is ~0.752x / 0.930x, not 1.0x. Default-on
ships the over-correcting value. This is a strength question, not an on/off question, and it
is the second cheapest improvement available after the log fix.

---

## 6. What I checked that came back clean, including against me

Reported because a clearance is worth as much as a defect, and because four of these were my
own objections.

- **The arms are a valid pair.** I re-rendered `foam` OFF myself with an independent
  invocation: **byte-identical** to the gallery render (`09035E42894140BF...`). The pipeline is
  deterministic at `--chunks 5` and ORCH's use of gallery renders as OFF arms is legitimate.
- **My "the arms differ by more than one variable" suspicion: REFUTED.** The logs do differ -
  auto-fitted tone black point, 0.00757 vs 0.00754 on bee-1 - and I priced it rather than
  asserting it. A global tone change is a per-value lookup with no spatial content, so I
  regressed each channel's delta on a 65536-bin LUT of its own OFF value: it explains
  **0.55 % / 0.78 % / 0.39 %** of the variance in R/G/B. Negligible, and the drift is *caused
  by* the correction, not by run-to-run noise (the determinism control above settles that).
- **My "green's movement is the colour matrix" hypothesis: REFUTED, and it was my sharpest
  objection.** I predicted `dG/dR = -0.070392` at every pixel from the verified
  `camera_to_srgb`. The *aggregate* ratio agrees seductively well (measured 0.07221 vs 0.07039
  predicted) - but the per-pixel regression gives slope **+0.017887 with r^2 = 0.047**, and
  blue moves **79x** more than the matrix permits (0.22820 measured vs 0.00290). The magnitude
  agreement is a coincidence. So **ORCH's own attribution - pre-demosaic correction coupling
  into green's interpolation - is the one that survives**, and mine does not. ORCH flagged this
  as unverified weak point #1; it is now verified, in ORCH's favour.
- **My "ORCH measured a different correction from the one default-on ships" suspicion:
  REFUTED.** `3dfa435` already contains the radial-only redirect, `applied_form`, the whole
  gear guard and `eps_b: Some(174.4e-6)`. Both the env path and the default path resolve to
  `A7C2_FE100GM_2XTC_X4CPL_RADIAL` with translation zeroed. The byte-identity above closes it.
- **My Phase-1 expectation that `wrapped-text-1` would reverse sign: NOT reproduced here.** It
  improves (0.6032). My earlier reversal was measured in binned-linear camera space on the
  default `strehl stack` path; this is full-res demosaiced. Different space, different answer,
  and I flag it because the two are easy to confuse.
- **`--chunks` was pinned in every A/B**, and frame counts match across all six pairs.
- **Space:** ORCH describes the arms as *"Both are sRGB, not linear."* Worth correcting for the
  record - `cafringe.py` calls `srgb_to_linear` on both arms, so the published numbers are
  **linear-sRGB**, not encoded sRGB. The instrument is better than its description. The colour
  matrix is still in the path, so these remain cross-channel numbers measured in a mixed space;
  that inflates the headline relative to camera-native but does not change its sign.

---

## 7. What would change my verdict, cheapest first

1. **Fix `merge_cmd.rs:3842-3846`** to report the resolved profile. One site. **Blocking.**
2. **Gate blue.** Set `eps_b` back to opt-in until it has a second-order term. Data-only.
3. **Record and compare `measured_at`** (aperture/magnification). One field, one comparison,
   and the identity reader already parses `f_number`.
4. Re-run ORCH's commissioning with a Catmull-Rom plant to restore Claim 3's absolute px.
5. Capture a short bracket without the teleconverter, to exercise the decline path on a real
   file for the first time.

Items 4 and 5 do not block the flip. Items 1-3 are what I would want in the owner's morning.

---

## 8. Provenance

Instruments under `experiments/V-CA/`: `a1_matrix_test.py`, `a2_magnitudes.py`,
`a3_tone_lut.py`, `a4_subject_survey.py`, `a5_render.ps1`, `a6_census.ps1`, `a7_flat_blur.py`,
`a8_guard_render.ps1`, `a9_radial.py`. Reproduction of ORCH's Claim 1 used
`experiments/ORCH-drift-check/cafringe.py` unmodified - declared where used.

Renders under `C:\dev\strehl-out\V-ca\` (5 ON arms, 1 OFF reproducibility control, 4 guard
arms). Worktree `C:\dev\strehl-out\V-ca-wt` at `96571ee`, detached; removed after use. No file
under `crates/` was modified. Nothing was written to `D:\`.

**I did not self-verify.** Filing for an independent verifier, as ORCH did for M107.
