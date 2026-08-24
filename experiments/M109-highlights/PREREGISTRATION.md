# M109 — highlight clipping: pre-registration

Written **before** any render, any build, and any edit to `crates/`. Working tree at
`2c13138b4ac6b5e5588ae3f40ebbd001de8e2ce3` (`M108: re-verify A/B/C against the new schema, and add check F`).
`color.rs`, `image_out.rs`, `stack.rs`, `main.rs` all clean at that SHA — no other agent is mid-edit in them.

Rule 20 binds this document: every bar below states the input that would make it **FAIL**.
Discipline 706 binds B3: a control that has never been shown to fail is not a control.

---

## 0. The defect, and the render path it lives in

`strehl stack --srgb` renders blown neutral highlights **magenta**. ORCH measured 2.002 % of a
33 MP render of `dry-erase-marker-head-cpl` affected, against an independent LibRaw decode that
renders the same region neutral white.

**Operation order, read from source, not assumed.** `strehl stack` dispatches to
`merge_cmd::run` → `merge_cmd::write_merged` (`merge_cmd.rs:2733`), **not** `stack.rs`:

1. `norm(raw, gain) = (raw - levels.black).max(0.0) * gain * exposure_gain / levels.range()`,
   `range = white - black = 15360 - 512 = 14848`. **Deliberately not clamped above.**
2. co-siting (`image_out::develop_binned`, red `+0.25`, blue `-0.25`, Keys `a = -1/2`) or
   Malvar–He–Cutler demosaic (`image_out::write_demosaiced`).
3. `color::apply(matrix, lin)` — the camera → linear-sRGB matrix.
4. `clamp(0, 1)`.
5. `color::srgb_encode`, then `(x * 65535 + 0.5) as u16`.

So: **black → green-normalised as-shot WB → exposure gain → resample → matrix → clamp → curve →
quantise.** The only clamp is at step 4, *after* the matrix; `image_out.rs`'s module doc defends
that placement ("clipping before the matrix would clip in the wrong space and shift hue"), and for
in-gamut colour it is right. It is wrong for a **container-pinned** sample, which is not a colour
measurement at all.

**Root cause (DERIVED from the code above, CONFIRMED numerically in `src/mechanism.py`).**
`levels.white` is 15360 but the container saturates at `CONTAINER_MAX_DN = 16383` (`clip.rs`, which
says in bold *do not unify them* — this fix does not). A pinned sample therefore lands at
`K0 = (16383 - 512) / (15360 - 512) = 1.068898` in render units, times its WB gain and the exposure
gain. Green's gain is 1.0 by construction; red's is 2.687 and blue's 1.532. So green stops at
`1.0689 · eg` while red and blue are carried to `2.87 · eg` and `1.64 · eg`. Step 3's green row
`[-0.1152, +1.4890, -0.3738]` is then dominated by the *unpinned* red and blue terms, green lands
below 1, red and blue clamp at 1 — **magenta**.

Feeding fact 1432's own raw means through this reproduces ORCH's triple:

| | R | G | B |
|---|---|---|---|
| `mechanism.py`, single point | 1.0000 | 0.8947 | 1.0000 |
| fact 1432, region mean | 0.9944 | 0.8915 | 0.9943 |

---

## 1. Predicates, fixed now

**Magenta fraction** `f_m`. On the written 16-bit TIFF, scaled to `0..1` by `/65535`, over **all**
pixels, the fraction satisfying `(R - G > 0.06) && (B - G > 0.06)`. This is ORCH's predicate from
`experiments/ORCH-drift-check/marker_wholeframe.py`, adopted verbatim so the before number is
comparable. No ROI: discipline 713 — let the predicate find the region.

**Green deficit** `d_g = max(R - G)` over the same pixels. Reported alongside `f_m` because `f_m` is
a thresholded statistic and can be gamed by a change that moves pixels to 0.0599.

---

## 2. Bars

### B1 — headline. Magenta must go.

`f_m` on `dry-erase-marker-head-cpl` must fall from **2.002 %** to **< 0.10 %**, and `d_g` from
**0.4490** to **< 0.10**.

*Fails if*: `f_m` stays above 0.10 %, or `d_g` above 0.10, or if the fix clears `f_m` by darkening
the render (guard: the 99th-percentile green of the after-render must stay within ±0.02 of before).

**B1 has two arms because of a file-ownership blocker, declared here in advance:**

* **B1-stack** — ORCH's exact reproduce command. The fix cannot reach it without ~3 lines in
  `merge_cmd.rs`, which **M97 owns and I may not edit** (§5). If that patch is not routed to me,
  B1-stack records as **BLOCKED**, not PASS and not FAIL, and the report says so plainly.
* **B1-argmax** — `strehl argmax-baseline --srgb`, whose writer (`stack.rs`) I do own. Same scene,
  same colour path, same predicate, run before and after.

**Pre-registered prediction for B1-argmax, and it is not the same number.** `argmax-baseline` has
**no exposure knob** (`StackOptions`, `stack.rs:166`, has no exposure field), so it renders at
`eg = 1`. `mechanism.py` measured that at `eg = 1` the blob's mean renders `(1.0000, 0.9629, 1.0000)`
— `R - G = 0.0371`, **below the 0.06 predicate**. Negative exposure *amplifies* the defect 2.8×
(0.0371 → 0.1053) because the two clamped channels cannot move down while the pinned one can.
So I predict **B1-argmax's before-`f_m` is well under 2.002 %** — non-zero, because ORCH measured
`d_g = 0.4490` and pixels far out in that tail still trip the predicate at `eg = 1`, but smaller.
I am registering that prediction now so that a small before-number is not read afterwards as the
fix having nothing to do.

### B2 — null. An unsaturated stack must not move by one byte.

`109MSDCF` (22 frames; `clip.rs` documents it as having **zero** saturated pixels) rendered
`--srgb`, SHA-256 before == SHA-256 after.

*Fails if*: a single byte differs. **This bar has already changed the design.** The obvious fix —
clamp every channel at the neutral ceiling unconditionally — is *not* the identity on unsaturated
data: it clips red above `raw ≈ 6420 DN` and blue above `≈ 10863 DN`, and 109MSDCF's maxima are
39–61 % of white, so it would clip real data and B2 would fail. The fix is therefore **conditional**
(§3), which makes B2 hold *by construction* rather than by observation.

### B3 — negative control, shown red before it is trusted.

Plant a defect that expresses **this specific failure**, confirm B1-argmax's harness turns red, then
remove it. The plant: force the ceiling to `+inf` in `color::saturation_ceiling`, i.e. restore
exactly the shipped behaviour while leaving every other line of the fix in place.

*Requirements*: the mutation is anchored on a **unique full-line string** and the script
**hard-errors** if the anchor does not match exactly once (rule 29). Restore is by copy from
`$env:TEMP`, never `git checkout`, and the restored file gets `LastWriteTime = Get-Date` (rule 33).

*Fails if*: the harness still reports PASS with the defect planted. That would mean B1 is measuring
something other than what I think.

### B4 — byte-freeze.

`cargo test -p strehl-cli --test byte-freeze` still passes.

*Fails if*: any frozen hash moves. Predicted to hold **by construction**: both rows in
`byte-freezes.tsv` are `srgb=no`, so they take the `write_rgb16` branch, which no part of this fix
touches. Predicted-by-construction is not evidence, so it is still run.

### B5 — LibRaw cross-check.

Decode `DSC00150.ARW` with `rawpy` (LibRaw) and compare the blob region against strehl's after-fix
render. Not required to match — LibRaw applies its own highlight logic — but a **large residual
disagreement is a finding I must report**. Threshold for "must explain": mean `|ΔR-G|` > 0.05.

### B6 — the owner's eye.

100 % crop montage of the affected region, before and after, to
`C:\dev\strehl-out\M109\`. Per discipline 708 the montage carries an exposure-matched panel so the
change cannot be mistaken for a brightness change.

---

## 3. The fix, stated before it is written

**At any pixel where some channel is at or above its own container ceiling, clamp every channel to
the neutral ceiling, in white-balanced camera space, before the colour matrix. Elsewhere, identity.**

```
ceil_c = K0 * gain_c * exposure_gain          per channel
K      = min_c ceil_c                          the neutral ceiling
if any_c ( v_c >= ceil_c )  then  v_c := min(v_c, K)  for all c
```

Why it renders blown neutral as neutral: `camera_to_srgb`'s rows each sum to 1, so an equal-channel
input is an equal-channel output by construction (`image_out.rs` already has a test for that
property). A blown neutral has all three channels above `K`, so all three become exactly `K`.

Why the null is exact: if no channel reaches its own ceiling the branch never fires, so the
transform is literally `identity` on every pixel of an unsaturated stack.

Why `min(v_c, K)` and not "set all channels to `K`": a pixel where green pins but red is genuinely
low is a blown *coloured* highlight, not a blown neutral. `min` leaves the low channel alone and
keeps the hue direction; "set all" would turn saturated cyan into white.

**The cost, stated up front.** At a pinned pixel the headroom above `K` in the unpinned channels is
discarded. For a genuinely saturated *red* object (red pinned, green and blue low) this desaturates
slightly — `mechanism.py` measures the green output rising `0.0000 → 0.2681`. That is the honest
price: a pinned channel is not a measurement of how red the object was, and preserving `2.87 · eg`
would be fabricating saturation the sensor never recorded.

**Alternatives rejected, with reasons:**

1. **Clamp camera-space at 1.0 as well as after the matrix.** Rejected on measurement: at `eg = 1`
   it happens to work, but the defect is exposure-dependent (`mechanism.py` Q2), so a fixed 1.0 is
   the right ceiling only at one exposure. It also throws away more in-gamut headroom than `K`.
2. **Post-matrix desaturation keyed on out-of-gamut output.** Rejected: it cannot distinguish a
   genuinely magenta object from a blown neutral, because after the matrix the two look identical.
   The ceiling is the only thing that carries "this was pinned".
3. **Data-derived ceiling (detect the green histogram's plateau).** Rejected as too clever for the
   evidence: it introduces an estimator with real failure modes (partial pinning across a 299-frame
   stack, G1/G2 averaging, plateaus that are not clipping) to replace two numbers the decoder
   already knows exactly.
4. **Highlight reconstruction** (estimate the pinned channel from the unpinned ones). Attractive —
   it recovers detail rather than discarding it — but it invents pixels the sensor never measured,
   needs a neighbourhood pass, and needs validation this milestone cannot afford. Recorded as
   follow-up, not attempted.

**Known residual, predicted now.** The blob *interior* should clear exactly. The "coloured fringing
along specular edges" is made of **partially** pinned pixels — green averaged over frames or over
G1/G2 lands just below `K` — and a hard threshold will **not** clear those. I expect a non-zero
residual `f_m` concentrated on edges, and I will report it rather than tune the threshold to hide
it (discipline 710).

---

## 4. Invocations, by value, including defaults (rule 47)

```
CARGO_TARGET_DIR = C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m109
STREHL_ALIGN     = (unset)      STREHL_FIX_HALO = (unset)
STREHL_WARPMAP   = C:\dev\strehl-out\M109\warpmap-m109.txt   (rule 45 isolation)
$ErrorActionPreference = "Continue"

B1-stack  (BLOCKED unless merge_cmd.rs is routed):
  strehl.exe stack "D:\personal\macro\dry-erase-marker-head-cpl" --srgb --auto-exposure
      --gate 4 --out <path>
  defaults in force: --limit unset (299 frames), --demosaic implied by --srgb,
      --binned false, --memory-model m8

B1-argmax:
  strehl.exe argmax-baseline "D:\personal\macro\dry-erase-marker-head-cpl" --srgb --out <path>
  defaults in force: --limit unset, --demosaic implied by --srgb, --binned false,
      --index-map none, --flat-roi none, --memory-model m8

B2 null:
  strehl.exe argmax-baseline "D:\personal\macro\109MSDCF" --srgb --out <path>
  (and, if routed, the same stack via `stack --gate 4`)
```

Every hash recorded in the report carries its full invocation, its byte count, and the commit SHA.

---

## 5. Declared blocker

`merge_cmd.rs` is M97's. The fix is built so that **merge_cmd.rs keeps compiling and keeps rendering
byte-identically without being touched** — `camera_to_srgb` changes return type from
`Option<[[f32;3];3]>` to `Option<color::Render>`, where `Render` is the matrix plus a ceiling that
defaults to `+inf` = "this caller stated no ceiling" = today's behaviour exactly. Activating it on
`strehl stack` is then 3 lines, given in the report for ORCH to route. Until they land, B1-stack is
BLOCKED and the shipped default keeps the defect. I will not edit that file.

---

## Addendum B7-B9 -- written 2026-08-24, BEFORE running ORCH's control battery

ORCH supplied a LibRaw single-frame control (`cca4157`): D1 magenta 0.0061%,
D8 partial-clip 1.6941%, against strehl's 2.0017% / 2.1585%; a 328x excess.
Registered here before I run anything against it.

**Confound I am registering in advance.** The control uses `no_auto_bright=True`
(exposure gain 1.0) and a single frame; strehl's 2.0017% was measured on 299
frames at `--exposure=-0.24` (gain 0.8467). I have already measured that
exposure ALONE moves argmax-baseline from 0.0349% to 0.3378% -- 9.7x, same code
path, same frames. The 328x therefore mixes at least three variables. It is not
wrong, but it is not yet attributable.

### B7 -- exposure-invariance signature (the sharp test)

A pipeline that clips channels together is exposure-INVARIANT in magenta
fraction: scaling a neutral triple keeps it neutral. A pipeline that does not is
exposure-DEPENDENT, because the pinned channel cannot follow the others down.

- PREDICT: LibRaw control magenta stays within 2x across gain 1.0 -> 0.8467.
- PREDICT: strehl BEFORE varies by >5x across the same two gains. (Already
  measured at 9.7x; recorded here so the pair is registered, not fitted.)
- PREDICT: strehl AFTER varies by <2x, i.e. it acquires LibRaw's invariance.
- FAILS IF: after-fix spread stays above 3x, which would mean the fix reduces
  magenta without removing its cause.

This is a mechanism-level bar. It can fail even if B1's magnitude bar passes.

### B8 -- D8 partial-clip must fall

The fix converts partial clipping (1-2 channels at 1.0) into full clipping (all
three at K together), so D8 should fall, not merely magenta.

- PREDICT: D8 falls after the fix at matched exposure.
- PREDICT: it lands at or below the control's 1.6941%.
- FAILS IF: D8 is unchanged or rises. Unchanged D8 with reduced D1 would mean I
  am recolouring clipped pixels rather than clipping them together, and the
  ceiling is not doing what I claim.

### B9 -- D1 against the control, exposure-matched

- PREDICT: after-fix does NOT reach 0.0061%. I have already measured a 28%
  residual of partially-pinned fringe pixels that a hard threshold cannot reach.
- PREDICT: after-fix lands in 0.03%-0.10% at -0.24 stops, i.e. 5x-16x the
  control, and I will report it as a PARTIAL fix, per ORCH's point 2.
- FAILS IF: it lands above 0.10% (worse than predicted) or below 0.03% (better
  than predicted -- which would mean my residual-fringe analysis is wrong).

Stated plainly so it cannot be repaired later: **I expect to report a partial
fix, not a clean one.**

## Addendum B10 -- written 2026-08-24, BEFORE writing the radial script

ORCH asks a question I can answer read-only, on artefacts already on disk: **is
the residual fringe that survives my fix spatially RADIAL?** Lateral chromatic
aberration is zero at the optical centre and grows with field height. If the
residual's density rises toward the corners it is M107's object and the two
fixes compose; if it is flat, M107's fix will not clear it and the two
milestones are addressing different things.

**Residual fringe** = pixels where the magenta predicate still fires in
`marker-argmax-e024-after.tif`. Same predicate, imported from `magenta.py`, not
re-typed (discipline 742).

### The confound I am registering in advance

**Raw area-normalised density is confounded by where the subject is.** Specular
highlights occur on the marker, not uniformly across the frame. If the marker
sits centrally, raw density falls toward the corners *for lack of subject*, and
a genuinely radial effect would read as flat or even anti-radial. So two
normalisers are reported, and **the eligibility-normalised one is the bar**:

1. **per unit area** -- fringe pixels / all pixels, per annulus.
2. **per eligible pixel** -- fringe pixels / partially-clipped pixels, per
   annulus, where partial clipping is ORCH's D8 population (1-2 channels at
   1.0, not all 3). That is the population mechanically at risk, so it removes
   the subject's placement from the denominator.

Annuli: 20 equal-width bins in r normalised to the centre-to-corner distance.
The denominator is the **measured** pixel count per annulus, not an area
formula, so rectangle clipping at the corners is handled exactly. Annuli whose
denominator is below 5 000 px are dropped as too noisy.

**Caveat registered, not discovered later:** the optical centre is assumed to be
the frame centre. This is a stack of aligned frames, so alignment could shift
the true optical centre by the warp's translation. A shift of a few hundred px
on a 7040x4688 frame cannot convert a flat profile into a monotonic one, but it
could weaken a real gradient. This bar can therefore produce a false NOT-RADIAL
more easily than a false RADIAL.

### Controls -- both required, and neither is optional

A "flat" result is uninterpretable unless the instrument is shown able to read
non-flat. Per discipline 706 and the null/positive pairing:

- **B10-null**: sample a uniform-random subset of eligible pixels, equal in
  count to the real fringe population. PREDICT `|rho| < 0.5` and outer/inner
  ratio in `[0.7, 1.4]`. **If this fails the instrument is biased and no other
  number in B10 may be quoted.**
- **B10-pos**: plant a synthetic population drawn with probability proportional
  to `r`. PREDICT `rho > 0.8` and ratio `> 2.0`. **If this fails the instrument
  cannot see radial structure and a flat real reading means nothing.**

### The decision rule, fixed now

On the **eligibility-normalised** profile:

- `rho > 0.7` AND ratio `> 2.0` -> **RADIAL**: consistent with lateral CA, expect
  M107 to clear it, expect the milestones to collide if both run on it.
- `rho < 0.3` OR ratio `< 1.5` -> **NOT RADIAL**: M107's fix will not clear it.
- anything else -> **EQUIVOCAL**, reported as such and not resolved by
  re-analysis.

I am registering the equivocal band deliberately so that a middling result
cannot be talked into either camp after the fact.

**What this cannot license.** It is a spatial-distribution test, not a mechanism
test. A RADIAL reading is consistent with lateral CA but does not prove it --
vignetting-driven exposure falloff and corner-softening both share the
signature. I will report it as consistent-with, never as identification, and I
am not coordinating with M107 on it.

## Addendum B11 -- written after B10 FAILED, before writing the diagnostic

**B10 failed as written and is reported as failed.** Both controls failed and
the instrument disqualified itself (exit 4), so per its own registered
consequence none of its readings may be quoted. It failed for a reason I did
not anticipate: on the eligibility denominator only **2 of 20 annuli** cleared
`MIN_DENOM`, both outer, so Spearman rho was `+1.0000` degenerately on two
points and outer/inner was `nan` for want of any inner annulus. The null
control fired on that degeneracy, which is precisely why it was there.

`radial.py` is **left exactly as it is**. It is the registered B10 instrument,
it behaved correctly, and editing it now would convert a reported failure into
a silent repair.

**B11 is a different question, not a rescue of B10.** B10 asked *is the
residual radial*. B11 asks the prior question B10's failure exposed: **does the
population even span enough field height for "radial" to be measurable?**

- Report, per annulus, with **no minimum-denominator cut**: total pixels,
  eligible (partial-clip) pixels, residual fringe pixels, and fringe per
  eligible pixel.
- **Decidability precondition, fixed now.** The radial question is decidable
  only if the eligible population has support at both ends: at least 5 000
  eligible px in some annulus with `mid < 0.50` AND at least 5 000 in some
  annulus with `mid > 0.85`. If either is absent, the verdict is
  **UNDECIDABLE-BY-SUPPORT** and no rho or ratio is reported at all.
- If decidable, require at least 4 surviving annuli before computing rho, and
  re-run both B10 controls under that constraint.

PREDICT: undecidable. B10's kept-annuli count already suggests the eligible
population is confined to a narrow band, and I am recording that expectation
before running so that an undecidable result is not presented as a discovery.

**A negative result here is informative and I am registering what it means in
advance.** Lateral CA grows monotonically with field height. If the residual
instead peaks mid-field and collapses at the largest radii *while eligible
pixels remain present there*, that is evidence against lateral CA. If eligible
pixels are absent there, the corners are simply untested and I must say so
rather than reading the collapse as evidence.

## Addendum B12 -- written after B11, before writing the edge-denominator test

B11 returned UNDECIDABLE-BY-SUPPORT as predicted, and in doing so split the
residual into two spatially disjoint populations:

- **72.5 % clipping-coupled** -- inside the partial-clip population, confined to
  r 0.52-0.88 with 90 % of it in r 0.75-0.85.
- **27.5 % NOT clipping-coupled** -- sitting in annuli containing **zero**
  eligible pixels, spread across r 0.02-0.93.

The second population is the only part that could plausibly be M107's object,
and unlike the first it **does** span field height, so the radial question is
decidable on it. B12 asks it, with a denominator that spans the frame.

- **Numerator**: residual fringe pixels NOT in the partial-clip population.
- **Denominator**: luminance edge pixels -- Sobel gradient magnitude of luma
  above its 99th percentile, restricted to luma > 0.15. Chromatic aberration
  acts on high-contrast edges, and edges exist at every field height, so this
  denominator has the radial lever arm B10's lacked.
- Same decidability precondition as B11, same >= 4 annuli requirement, and
  **both B10 controls re-run on this denominator**.
- Same decision thresholds as B10, unchanged: `rho > 0.7 AND ratio > 2.0` ->
  RADIAL; `rho < 0.3 OR ratio < 1.5` -> NOT RADIAL; otherwise EQUIVOCAL.

PREDICT: not radial. B11's area-normalised profile for this subset peaks near
r = 0.125 and falls to near zero beyond r = 0.75, which is the inverse of the
lateral-CA signature -- but that profile is confounded by subject placement,
which is exactly what the edge denominator is meant to remove. Recording the
expectation before the run so a confirmation is not mistaken for a discovery,
and so a reversal is visible as one.

**Registered in advance: a NOT RADIAL result does not clear M107.** It would say
that *this* residual is not lateral CA and that M107's fix should not be
expected to remove it -- which is the composition question ORCH asked. It says
nothing about whether M107's own defect is real.

---

## B13 -- job 2, `--resampler` on `strehl stack` (REGISTERED BEFORE ANY RUN)

Registered 2026-08-24 15:2x, **before** the patch was written and before
`align_cmd.rs` was touched. ORCH has withheld the go on `align_cmd.rs`; these
bars exist so that when it arrives the measurement is already defined.

**Harness guard (discipline 740).** The harness MUST refuse to run, non-zero,
if `git status --porcelain -- crates/strehl-cli/src/align_cmd.rs` is non-empty
at start. A collision, not a merge, is the failure this protects against.

**Method (discipline 741).** Both arms built from ONE tree at ONE moment. The
stored binary is NOT the "before". Other agents committed `e8d74c7`, `94621e0`
and `f886b02` tonight; any baseline rendered before those is a different
program.

| bar | prediction | fails if |
|---|---|---|
| **B13-null** | `strehl stack` with **no** `--resampler` is **byte-identical** to the same tree without the patch | any byte differs |
| **B13-reach** | `--resampler lanczos3` produces a **different** hash from the default | hashes are equal -- the flag is **inert** |
| **B13-key** | the lanczos3 run resolves a **different** `solve_config_key` and therefore re-solves rather than reusing the catmull-rom sidecar | the same sidecar is reused -- a warp map solved with the other kernel is served silently |
| **B13-red** | making `merge_config` ignore its new argument (return the literal) turns **B13-reach RED** | it stays green -- then B13-reach never tested the flag |
| **B13-freeze** | byte-freeze 5/5 with `STREHL_FREEZE_REQUIRE=1` | fewer than 5 |

**B13-null is the load-bearing one.** ORCH's instruction is that the default
render must not move, so this bar decides whether the change may ship at all.
The hash is **not named in advance**: it must be measured on the tree the patch
is applied to, because naming tonight's `559407FE..AD12E5` would silently assert
that no other agent's commit has moved the default render since 15:02, which is
exactly the assumption discipline 741 exists to forbid.

**B13-key is the bar I expect to be hardest**, and it is the one ORCH
specifically asked for. `solve_config_key` already hashes `format!("{resampler:?}")`,
so the key *should* vary the moment the value does. But that is a reading of the
code, not a measurement, and it is only true if the flag reaches
`solve_config_key` rather than being applied downstream of the cache lookup. A
flag that changes the gather but not the key is worse than no flag: it would
serve a cached catmull-rom warp map under a lanczos3 command line.

**What would make me not ship it:** B13-null failing, or B13-red staying green.
Either one means I cannot tell what the flag does.

---

## B15 -- why does 0.5060 % survive? The merge-dilution hypothesis (REGISTERED BEFORE RUNNING)

Registered 2026-08-24 15:5x, before the script existed and before any frame was
read. Read-only on `D:\personal\macro`.

**Hypothesis H-merge.** My guard fires on `v_c >= ceil_c`, an equality against
the container ceiling. But `write_merged` clips the **merged** value, and the
merge averages ~55 frames per pixel. A pixel whose green is pinned at 16383 in
*some* frames and unpinned in others averages to something **strictly below**
the ceiling. The guard therefore never fires on it, while green is still
suppressed relative to red and blue -- so it stays magenta.

If true, the residual is not a tuning failure. It is the guard asking a
per-frame question of a post-merge value.

**Sharp, falsifiable prediction.** Let `f` = the fraction of frames in which a
given sensel's green is pinned at `CONTAINER_MAX_DN`, computed over pixels
pinned in at least one frame.

| outcome | reading |
|---|---|
| a substantial share of pinned pixels have `0 < f < 1` | H-merge **supported** |
| **>= 95 % of pinned pixels have `f == 1`** | H-merge **DEAD** -- averaging cannot be diluting anything, and ORCH's other three hypotheses take over |

**Bonus quantitative check, stated in advance.** If H-merge is the whole story,
the share of pinned pixels with `f == 1` should be **comparable to the ~72-75 %
of the defect the clip actually cleared**, and the `0 < f < 1` share comparable
to the ~25 % residual. I am recording this before looking. A large mismatch
means H-merge is *a* mechanism but not the *only* one, which is a different and
weaker claim than the one I am testing.

**What this cannot show.** It cannot prove the residual pixels are the same
pixels; frames are warped before merging, so a raw sensel and an output pixel
are not in perfect correspondence. This is a population-level test and I will
report it as one.

**Instrument check (discipline 763 applied to myself).** Before believing any
null here, the script must show it can see pinning at all: it reports the count
of pixels with `f == 1`, and if that count is **zero** the instrument is not
finding saturation and no conclusion may be drawn in either direction.
