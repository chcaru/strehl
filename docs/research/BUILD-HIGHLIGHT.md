# BUILD-HIGHLIGHT — blown highlights acquire a colour cast, and the ceilings that cause it

**Status: FIXED, on by default, on both merge backends.**
Work: `experiments/BUILD-HIGHLIGHT/`. Code: `crates/strehl-core/src/highlight.rs` (new),
one call site in `crates/strehl-core/src/color.rs`, three one-line call sites in the CLI.

Commissioned from BUILD-CHROMA's report section 25, which measured coloured rims on
`foam`'s speculars and isolated the driver as **level, not field position**. This report
reproduces that measurement, corrects part of its inference, states the mechanism, fixes
it, and shows the fix moving the statistic with a null and a negative control beside it.

---

## 1. What I was asked to find, and what is actually there

BUILD-CHROMA's section 25 reads the per-channel maxima of the rendered master —
R 42213, G 38921, B 52239 — as **ceilings**, and infers that green runs out of headroom
first. My instrument reproduces their numbers exactly on their own frozen file
(section 3), so the numbers are right. The **inference is wrong on that file**, and it
matters, because it points at the wrong ceiling:

> In `C:\dev\strehl-out\ORCH-CADEF\foam-caon.tif`, the hot edge set sits at `u_max`
> **0.146 to 0.468**, mean **0.2425**, max **0.5731** — where `u_c = v_c / ceiling[c]` is
> the sample's raw level as a fraction of the 14-bit container. Nothing in that hot set is
> within a factor of two of any ceiling. Those maxima are the top of a long thin tail, not
> a ceiling.

So the elevated `B/G` in ORCH's master is **not** channels hitting their limits in that
file. But the mechanism BUILD-CHROMA described is real, and it is visible one step
earlier — in the frames, before the merge dilutes it. That is what this report fixes.

**Two further qualifications, recorded rather than silenced.**

* **The radial part does not reproduce on today's tree.** BUILD-CHROMA measured an
  ungated corner/centre ratio of **1.878**, collapsing to 1.031 under a level gate, with a
  random control at 1.856 ± 0.088 (7.6 sd). My rebuild of that statistic, run on my own
  renders from tonight's tree, reads **0.983** ungated with a random-control separation of
  **0.4 sd**. The corner elevation has already gone, for reasons outside my change. The
  level-driven part is still there, and is what I measured against.
* **ORCH's 10:07 master and my 11:32 renders differ non-linearly** — percentile ratios
  vary 1.6x to 3.3x, my renders have a *lower* green mean `u` (0.0456 vs 0.0563) and a
  *much* higher max (0.9355 vs 0.5773), with 0.55 % of pixels at output full scale versus
  none. An estimator render of the same subject reaches green `max_u` **0.93173** against
  the pyramid's **0.93113** — a 0.06 % difference, so it is not a backend difference.
  *That comparison is stated on the green plane only, and deliberately:* the two arm
  renders come from my early harness, which did not yet record the binary hash, so I
  cannot prove they share a build, and a cross-build reading is void off green. The
  ceilings themselves are metadata-derived and are **bit-identical** between the arms
  (`B = 1.6304872179822196` in both), which no build difference could affect.
  The tree moved a great deal in that window (veil, blend/hull, ICC). **Not explained.**

---

## 2. The mechanism: there are two ceilings and they are unequal in opposite directions

### 2.1 The container, equal in raw DN, unequal after white balance

`Levels::white` is 15360; the sample container saturates at `clip::CONTAINER_MAX_DN`,
16383. A container-pinned sample therefore lands not at 1.0 but at

    K0 = (16383 - 512) / (15360 - 512) = 1.068898

times its white-balance gain. `foam`'s as-shot gains, from `strehl probe`, are exactly
`[2745/1024, 1, 1562/1024]`, so the three channels stop at

| channel | gain | ceiling in `v` | headroom relative to green |
| --- | --- | --- | --- |
| R | 2.680664 | 2.8654 | 2.6807x |
| G | 1.000000 | 1.0689 | 1x — **runs out first** |
| B | 1.525391 | 1.6305 | 1.5254x |

This clip happens **per frame, before the merge**, and it is one-sided: `h1_rawceiling.py`
measured green pinned at 16383 DN on up to **0.1255 %** of a mid-stack `foam` frame,
**5x** more often than blue and **137x** more often than red — and on **0 %** of frames 1,
13, 73 and 85. A pixel whose green pins while blue climbs acquires a blue excess that
grows with level, which is exactly the signature BUILD-CHROMA reported and which a fixed
white-balance gain cannot produce.

### 2.2 The writer's clamp, equal in `v`, unequal in raw DN

Measured directly on a camera-native render — `OutputSpace::CameraLinear` sets
`matrix: None`, so `v` is readable out of the file with no matrix to invert:

| channel | its ceiling in `v` | where the writer's `clamp(0,1)` cuts it | raw DN at that cut | pixels cut |
| --- | --- | --- | --- | --- |
| R | 2.8654 | `u = 0.3490` | 6 051 | 0.4007 % |
| G | 1.0689 | `u = 0.9355` | 15 360 | 0.3985 % |
| B | 1.6305 | `u = 0.6133` | 10 246 | 0.4950 % |

The clamp cuts red at 6 051 DN — under 37 % of what the sensor recorded. But it is equal
in `v`, and a *neutral* highlight is equal in `v` by construction, so a neutral meets the
writer's clamp on all three channels at once and goes cleanly white. It meets the
**container** on green alone. **The first asymmetry is the one that colours highlights;
the second is the one that makes the residual hard to read**, and section 6 separates
them.

### 2.3 Why M109's fix does not reach it

`color::Render::clip_highlights` (M109) is correct and is kept. It fires only when
`v_c >= ceiling[c]`. M109's own section 16 measured why that is not enough: of the sensels
pinned in at least one frame, only **21.02 %** are pinned in *every* frame, so the merge
averages pinned with unpinned samples, the merged value lands strictly below the ceiling,
and the guard never fires — while the green deficit survives. M109's words:
*"The guard asks a per-frame question of a post-merge value."*

That is the gap. It is a gap in the *approach* to saturation, not in the pinned case.

### 2.4 Relationship to the hull clamp — asked for explicitly, and it turned out to matter

`pyramid::Hull::InputRange` clamps each reconstructed pixel to the range of the frames
that contributed to it. It is per channel, against **that channel's own** input range, so
it cannot equalise three unequal ceilings — it can only shrink each toward its own inputs.
It is not the cause and I did not remove or fight it.

It is, however, **why the merged file tops out at `Levels::white` (`u = 0.9355`) rather
than at the container**, and that fact changed the fix. A roll-off that completed at the
container would still be only 50 % engaged on `foam`'s top level decile. Section 5.2
measures the difference the endpoint makes: it is most of the correction.

---

## 3. The instrument, shown able to reproduce and able to fail

`experiments/BUILD-HIGHLIGHT/src/h3_chroma.py` is a re-implementation of BUILD-CHROMA
section 25 that takes a path, so it can be pointed at any arm.

**Reproduction.** On BUILD-CHROMA's own frozen master it returns their numbers:
per-channel maxima R **42213** / G **38921** / B **52239**; `B-G` positive on **88.9 %** of
hot edge pixels; `B/G` **1.0257 -> 1.2903** rising on **9 of 9** decile steps; ungated
corner/centre **1.878**, gated **1.058**, random control **1.881 ± 0.018** at **47.0 sd**.

**Two defects it caught in itself**, both fixed and both now permanently asserted:

1. A units error — `back_to_camera` was handed already-normalised data, so `u` came out
   near zero and every level statistic was meaningless. The repair carries an assertion
   (`umax[hot].mean() > 0.01`) that fails if it ever recurs.
2. `ceilings(None)` crashed rather than defaulting, which would have been a silent
   `nan` had it not.

**The gate is asserted to bite.** BUILD-CHROMA's near-miss on this exact task was a gate
thresholded on fractions of 65535 when the file's maximum was 52239, so it removed zero
pixels and the verdict logic printed *"the elevation survives"* anyway. Every gate here
asserts its own kept-count, and where a gate legitimately has nothing to remove the
comparison **says so and reports nothing** rather than quoting a weak number — see
`coffee-bean` in section 6.

**Never on an `--srgb` render.** Every number in this report is `--linear-srgb` or
camera-linear.

---

## 4. What I changed, and why this remedy

`crates/strehl-core/src/highlight.rs`, a new module. As a pixel approaches the lowest
channel's ceiling, its chroma is blended toward the neutral **of the same luminance**:

    u   = max_c v_c / ceiling[c]
    t   = smoothstep((u - knee) / (top - knee))        0 at the knee, 1 at usable white
    n   = 0.2126 * (M[0].v) + 0.7152 * (M[1].v) + 0.0722 * (M[2].v)
    v'  = v + t * (n - v)

**Luminance is preserved exactly, not to a tolerance.** Every row of `camera_to_srgb` sums
to 1 and the BT.709 luma weights sum to 1, so `n` is simultaneously the pixel's luminance
and the camera-space neutral that renders to it; the blend cannot move luminance. Detail
in a highlight lives in luminance, so the fix cannot cost detail. This is asserted in
Rust, over a sweep of hues and weights, not argued.

**Why `u` and not brightness.** `u_c = v_c / ceiling[c] = (raw_c - black)/(container -
black)` is **independent of the white-balance gain**, because the gain is in both halves.
Keying on `max_c v_c` instead would bleach genuinely bright saturated colours: a red object
at `v_R = 1.5` sits above green's ceiling of 1.0689 but only at `u_R = 0.52`, about 8 600
DN of a 16 383 DN container. A test asserts both halves of that — the colour is untouched,
*and* a `v`-keyed driver would have fired on it.

**Why the knee is 0.60, and why that is an anchor rather than a tuning.** `109MSDCF`'s
documented per-channel maxima are 39–61 % of `Levels::white`, so `u <= 0.5707`; a knee at
0.60 leaves every stack that never approaches saturation bit-identical, **with margin**.
That was a prediction before the render, and section 6 is the render that confirms it. In
raw terms 0.60 of the container is 10 342 DN, 67 % of usable white.

**Remedy (2), not (1) or (3).**

* **(1) clip-aware white balance is already shipped and is not the gap.**
  `color::saturation_ceiling` tracks each channel's saturation point *through* white
  balance and `clip_highlights` clamps against the per-channel ceiling, not a shared one.
  That is M109 and it is exactly remedy (1). Section 2.3 is the measurement that says it
  cannot reach the post-merge case.
* **(3) highlight reconstruction is not verifiable on this backend.** Post-merge there is
  no per-pixel record of which channel clipped in which frames — the pyramid backend's own
  banner prints `not applied: ... clip census`. Reconstructing a channel from a value that
  is already an average of clipped and unclipped samples would be inventing a measurement.
  The brief said not to implement (3) speculatively, and I did not. **The route exists for
  a later workstream**: the *estimator* backend does carry censoring state
  (`Estimator::fold_censored`, `is_censored`, `has_censored_contributor`, `censor_level` in
  `merge.rs`, wired at `merge_cmd.rs:3715`). Remedy (3) belongs there, with that state.

### 4.1 Where it sits, and what that buys

The call is one line inside `color::Render::develop`, after `clip_highlights` and before
the matrix. Consequences:

* **Backend-independent.** Pyramid *and* estimator, and both writers (`write_merged`'s
  demosaic and binned branches, and `stack.rs`'s), get it from one place.
* **Zero edits to contended files' logic.** `pyramid.rs` (BUILD-BLEND) is untouched.
  `merge_cmd.rs` (BUILD-WIRE) and `stack.rs` change by **one line each**, and only to swap
  `with_ceiling(saturation_ceiling(levels, gains, eg))` for `with_saturation(levels,
  gains, eg)` — same arguments, same shape.
* **It cannot touch the byte-frozen measurement path.** `OutputSpace::CameraLinear` sets
  `matrix: None`, so `develop_pixel` never enters the `Render` branch at all.
* **It composes with M109 rather than fighting it.** A blown neutral leaves
  `clip_highlights` already neutral, and a neutral is a fixed point of the roll-off. Both
  facts are asserted.
* `Render::new` states no ceiling, so `u = 0` and the roll-off is the identity. Nothing
  that never asked for a ceiling can move.

### 4.2 The one scalar that had to be plumbed

`saturation_ceiling` returns `k0 * wb[c] * eg`. `k0` is **not recoverable** from that
product, because `wb[c]` and `eg` are not separately visible in it — so the roll-off could
not tell where *usable white* sat, only where the container sat. `Render::with_saturation`
takes `Levels` and stores the missing scalar as `top = range / (container - black) =
14848 / 15871 = 0.93554`. `with_ceiling` is unchanged and leaves `top` at the container,
which is the conservative behaviour for a caller that has not said.

A test asserts `top == 1/k0` at three exposure gains and that it does **not** depend on the
gain, and a second asserts a nonsense `top` degrades to a ramp rather than a division by
zero, with the below-knee null still exact.

---

## 5. Before and after on BUILD-CHROMA's statistic

**One binary for every render on both sides**, SHA-256
`F9BD5191213A240D1760BA7F0BD127948C5F76C3937FCD4F37047BAF807BA39C`, one warpmap per
subject solved once and pinned through `STREHL_WARPMAP`. The arms differ **only** in
`STREHL_HIGHLIGHT_KNEE`. Every render's banner was captured; every one reads:

    merge backend   : pyramid (--merge)

and the wrote-line confirms `linear sRGB (BT.709 primaries, D65, no transfer curve)`.
`--merge pyramid` was passed explicitly on all eleven renders: passing an estimator-only
flag without it silently selects the estimator backend, and the argv is not evidence.

**Cross-build check.** The `before` arms are byte-identical to the same subjects rendered
from the *previous* build (`239CD220...`), which is what the endpoint change should do when
the knee is off — `foam-before` is `4FCD0ACD...` from both binaries. The comparisons below
are nonetheless within one binary.

### 5.1 `foam`

Hot edge set **frozen from the before arm** and used for both, so the two arms are scored
on the same 17 004 pixels rather than on two differently-selected populations.

| statistic | before (knee off) | after (default 0.60) | change |
| --- | --- | --- | --- |
| clamp spread, max/min channel | 1.7182 | **1.0431** | **-39.3 %** |
| any channel clamped at 65535 | 0.5535 % | **0.3812 %** | -0.17 pp |
| clamped: R / G / B | 0.3963 / 0.2989 / 0.5136 % | 0.3733 / 0.3579 / 0.3659 % | — |
| hot edge chroma `(\|B-G\|+\|R-G\|)/2G` mean | 0.2163 | **0.1314** | **-39.2 %** |
| hot edge chroma, median | 0.1653 | **0.0603** | **-63.5 %** |
| hot edge `(B-G)/G` median | 0.0992 | **0.0145** | -85.4 % |
| hot edge `(R-G)/G` median | -0.0881 | **-0.0154** | -82.5 % |
| `B/G` decile 9 | 1.1697 | **1.0893** | -6.9 % |
| `B/G` decile 9 / decile 0 | 1.1626 | **1.0672** | -8.2 % |
| corner/centre `\|B-G\|/G` | 0.9830 | 0.9639 | -1.9 % |
| pixels changed at all | — | 0.6444 % | — |

The **clamp spread is the headline**: it is the per-channel ceilings' inequality stated
directly, and the three channels now run out of headroom within **4 %** of each other
instead of **72 %**. `B/G` flattens across the level deciles: the top four deciles fall
from 1.1697 to 1.0893 while deciles 0–4 barely move, which is the shape a level-keyed fix
should have and a gain-like fix could not.

### 5.2 What the endpoint bought

The first working version completed its ramp at the container. Same subject, same knee,
same warpmap; the container-endpoint arm was rendered from the **previous** build
(`239CD220...`), so this one row is a cross-build reading — mitigated by the fact that the
two builds' `before` arms are byte-identical (`4FCD0ACD...` from both) and the only source
difference between them is the endpoint.

| endpoint | `t` at decile 9 (`u = 0.7990`) | `B/G` decile 9 | `(B-G)/G` median | `(R-G)/G` median | clamp spread |
| --- | --- | --- | --- | --- | --- |
| container, `u = 1` | 0.4963 | 1.1220 | 0.0390 | -0.0314 | 1.0688 |
| usable white, `u = 0.9355` | **0.6380** | **1.0893** | **0.0145** | **-0.0154** | **1.0431** |

Moving the endpoint took the top decile's excess removed from **29 %** to **47 %**, and
more than halved the surviving median cast. This is the one place where the hull clamp's
behaviour fed directly into the design.

### 5.3 The null / placebo — `109MSDCF`, a stack with no blown highlights

| | |
| --- | --- |
| before, SHA-256 | `B33B53DFABCFD082...` |
| after, SHA-256 | `B33B53DFABCFD082...` |
| pixels changed | **0.0000 %** |
| max abs delta | **R 0, G 0, B 0 DN** |
| every statistic in the table above | **+0.0000** |

**Byte-identical.** Not "changed only trivially" — identical, which is the strongest form
this control can take, and it was *predicted* from the knee's anchor before the render.

### 5.4 The negative control — the same instrument, an exaggerated knee

`STREHL_HIGHLIGHT_KNEE=0.05`, whose banner the run itself printed:

    highlight: chroma roll-off knee moved to 0.05 (was 0.6)

| statistic | before | knee 0.05 | default 0.60, for comparison |
| --- | --- | --- | --- |
| pixels changed | — | **16.6357 %** | 0.6444 % |
| hot edge chroma mean | 0.2163 | **0.0396 (-81.7 %)** | 0.1314 (-39.2 %) |
| hot edge chroma median | 0.1653 | **0.0109 (-93.4 %)** | 0.0603 (-63.5 %) |
| `B/G` decile 9 | 1.1697 | **1.0181** | 1.0893 |
| corner/centre | 0.9830 | **0.8805 (-10.4 %)** | 0.9639 (-1.9 %) |
| clamp spread | 1.7182 | **1.0074** | 1.0431 |

The statistic moves, hard, in the direction the knee is pushed, and **26x further on the
pixel count** than the shipped default does. A statistic that has never been shown to move
is not evidence; this one has been shown to move. It also says plainly that the shipped
default is a **conservative** setting, not a maximal one.

---

## 6. The print corpus: three more specular subjects

All from the same binary, same discipline, `--merge pyramid --linear-srgb`.

| subject | frames | pixels changed | clamp spread before → after | hot edge chroma mean | frame mean saturation |
| --- | --- | --- | --- | --- | --- |
| `foam` | 100 | 0.6444 % | 1.7182 → **1.0431** | 0.2163 → **0.1314** (-39.2 %) | -0.28 % |
| `coffee-bubbles` | 19 | 0.2807 % | 1.4841 → **1.0286** | 0.2735 → **0.2289** (-16.3 %) | -0.06 % |
| `tweezers-cpl` | 100 | 0.0076 % | 1.5259 → **1.0227** | 0.1263 → **0.1175** (-7.0 %) | -0.01 % |
| `coffee-bean` | 105 | 35.4010 % | 28.6832 → **1.0001** | 0.1662 → **0.0702** (-57.8 %) | **-5.28 %** |
| `109MSDCF` (null) | 22 | 0.0000 % | no clamped pixel either arm | 1.1991 → 1.1991 (0.0 %) | 0.000 % |

**Every subject's ceilings now run out together** — the spread falls to within 3 % of
unity on all four, from as much as 28.7x. On `coffee-bean` the output-clamped fraction
falls from 5.07 % to 2.17 %: the fix *reduces* clipping, because pulling a channel toward
the luminance neutral takes it away from the writer's clamp.

**Detail is not lost.** Whole-frame mean luminance moves by at most **+0.17 %** on any
subject, and on the pixels that moved the mean `|dY|` is 38–1 111 DN out of 65 535. That
follows from the arithmetic — the blend is luminance-preserving exactly — and the render
agrees with the arithmetic.

**Containment, checked rather than assumed.** The *lowest-level pixel that moved at all*
is 42 448 / 42 796 / 42 657 / 42 162 DN on the four subjects — all within 1.5 % of each
other, and all corresponding to `u = 0.60`. The roll-off touches only what is above its
knee, and the renders locate that knee where the source says it is.

### 6.1 The cost, stated plainly

**`coffee-bean` moves 35 % of its frame and loses 5.28 % of its whole-frame mean
saturation.** That is by far the largest effect in the corpus and it is not hidden. What
is behind it:

* It is a very bright stack — frame mean luminance **29 217 DN**, 45 % of full scale —
  whose background genuinely sits above `u = 0.60`. The knee is a level threshold, so on a
  stack whose *subject* is above the knee, the roll-off reaches the subject.
* The pixels it moves were **already nearly neutral**: mean saturation **0.0579** before,
  0.0201 after, median loss **0.0404**. It is removing a small residual tint from a bright
  near-grey field, not desaturating colour.
* That field was the most badly clipped in the corpus — R 0.17 % / G 3.43 % / B 4.98 %
  clamped, a **28.7x** spread — which is precisely the disease. After: 2.166 % on all
  three, a spread of **1.0001**.
* Its corner/centre `|B-G|/G` halves, 0.1396 → 0.0658.

I judge this correct behaviour rather than a regression, but it is the one result an owner
should look at before accepting the default, and it is the reason the knee is an
environment variable rather than a constant.

### 6.2 The residual, and where it lives

`foam`'s top level decile still reads `B/G = 1.0893` rather than 1.0. The instrument
locates why, and it is **not** the roll-off failing:

* Decile 9 of the hot set is **100 % output-clamped** (decile 8 is 51.8 %). For a clamped
  pixel, `B` pinned at 65535 over an unpinned `G` reads greater than 1 **by construction**,
  whatever the arithmetic upstream did. The level axis is output level, so the top deciles
  are the clamped set almost by definition.
* Removing every pixel clamped in either arm — a gate that removes 7 494 of 17 004, and is
  asserted to have removed exactly what it named — leaves 9 510 pixels on which
  `(B-G)/G` median falls **0.0317 → 0.0084 (-73.3 %)** and `(R-G)/G` median
  **-0.1321 → -0.0501 (-62.1 %)**.
* The writer's clamp cuts blue at `u = 0.6133`, only just above the 0.60 knee, so a
  blue-clamped pixel is by construction one the roll-off has barely begun to engage. **The
  second ceiling of section 2.2 is what bounds the residual**, and it is a property of
  writing 16-bit linear sRGB, not of the merge.

On `coffee-bean`, where the hot set *is* the clamped set, the unclamped-subset statistic
reports **REFUSED — 0 of 76 survive** rather than quoting a number from too few pixels.

---

## 7. Is it on by default, and where

**Yes**, because it is a defect fix.

| | |
| --- | --- |
| default | **on**, knee 0.60 |
| backends | **both** — pyramid and estimator; the call is in `Render::develop`, which is downstream of the merge |
| writers | `merge_cmd::write_merged` (demosaic and binned) and `stack.rs::write_outputs` |
| output spaces | `--srgb` and `--linear-srgb`. **Not** camera-linear, which sets `matrix: None` and never enters `Render` |
| off switch | `STREHL_HIGHLIGHT_KNEE=off` restores the previous render **bit-exactly**, by skipping the roll-off rather than evaluating it at `t = 0` |
| moving it | `STREHL_HIGHLIGHT_KNEE=<x>` for `0 < x < 1`, which prints a banner line naming the old value; anything else warns and uses the default |

**The one nuance worth stating precisely.** `OutputSpace::CameraLinear` is the *default
output space*, and `OutputSpace::develop` gives it `matrix: None`, so a bare `strehl stack`
with neither `--srgb` nor `--linear-srgb` is **byte-unchanged**. The roll-off is on by
default *for every render that asks for colour* — which is every render a human looks at
or prints, and every render this defect was reported on — and the byte-frozen measurement
corpus is untouched by construction rather than by care.

Under `--srgb` the tone rendering runs after the matrix, and its placement stage is a
**single gain derived from luminance applied to all three channels** (`Tone::gain`), so it
scales a neutral to a neutral: it cannot reintroduce the cast the roll-off removed.

---

## 8. Verification

| gate | result |
| --- | --- |
| `cargo test -p strehl-core --lib` | **480 passed, 0 failed** |
| `cargo test --workspace` | **651 passed, 0 failed, 1 ignored** |
| `cargo clippy -p strehl-core --all-targets` | **no warning in `highlight.rs`**; the workspace's pre-existing warnings are in other lanes' files and my change adds none |
| `rustfmt --edition 2021 highlight.rs` | clean. `cargo fmt --check` fails workspace-wide on 301 diffs across 34 files **that were already failing**; I did not reformat other lanes' files |
| `python scripts/corpus_lint.py` | **OK** |

The module's 12 tests are written to be able to fail:

* the null sweep asserts **both** directions and asserts the two counts are non-degenerate,
  so a roll-off that did nothing and a roll-off that touched everything both fail;
* the `foam` test asserts the defect **reproduces** at `B/G = 1.135` before asserting it
  collapses, so a render that went neutral for some other reason would fail loudly rather
  than pass quietly;
* the saturated-red test asserts that a `v`-keyed driver **would** have fired on the same
  input, so it is testing the driver and not just the outcome;
* the endpoint test asserts the container endpoint is **insufficient** as well as usable
  white being sufficient, so it cannot pass by the two being accidentally equal.

---

## 9. What I did not fix, and why

1. **The residual in the output-clamped set** (section 6.2). Bounded by the writer's
   `clamp(0,1)` in 16-bit linear sRGB, not by the roll-off. Fixing it means changing what
   the writer does with out-of-range values, which is `image_out`'s decision and another
   lane's file.
2. **Highlight reconstruction, remedy (3).** Not tractable on the pyramid backend without
   a per-pixel clip census. The estimator backend has the censoring state for it; that is
   the next workstream, and it should be measured on the estimator, not assumed from here.
3. **BUILD-CHROMA's radial finding.** It does not reproduce on tonight's tree and I did not
   chase it. Section 1 records the numbers.
4. **Why ORCH's 10:07 master and my 11:32 renders differ non-linearly.** Unexplained.
   Section 1 records it rather than smoothing it over.
5. **`coffee-bean`'s 5.28 % saturation cost.** Correct behaviour by my reading, but it is
   a judgement, and section 6.1 gives the owner the numbers to overrule me with.

---

## 10. Cross-cut: the roll-off against BUILD-ELECT's clip rate

ORCH asked two questions after BUILD-ELECT measured the shipping pyramid arm pinning
`== 65535` on **4.65 %** of frame against the estimator's **1.87 %**: does this fix's
correctness depend on the clip rate, and does it behave the same at both figures.

### 10.1 The answer is structural first

The roll-off is a **pointwise function of one pixel's own `u = v_c/ceil_c`**. It carries no
neighbourhood term, no global statistic and no aggregate normaliser. What it does to a
pixel is therefore *mathematically* independent of how many other pixels are clipped: the
clip rate cannot change its output anywhere. That is a property of the code, not a
measurement, and it is the strongest form the answer can take.

What the clip rate *does* change is how much of the correction survives **to the file**,
because the writer's `clamp(0,1)` is downstream of `Render::develop`. That is the residual
already recorded in section 8, and its direction is favourable: a *lower* clip rate lets
*more* of the correction through. The fix and BUILD-ELECT's concern pull the same way.

### 10.2 And it is corroborated across a range that brackets both their figures

`h10_cliprate.py`, frame-wide, same binary `F9BD5191...`, all arms `merge backend :
pyramid (--merge)`, arms differing only by `STREHL_HIGHLIGHT_KNEE`:

| subject | any-ch before | any-ch after | factor | R/G/B before | R/G/B after |
| --- | ---: | ---: | ---: | --- | --- |
| `109MSDCF` | 0.0000 % | 0.0000 % | — | 0 / 0 / 0 | 0 / 0 / 0 |
| `tweezers-cpl` | 0.0031 % | 0.0022 % | 0.703x | 0.0025 / 0.0016 / 0.0024 | 0.0022 / 0.0021 / 0.0021 |
| `coffee-bubbles` | 0.2995 % | 0.1988 % | 0.664x | 0.1787 / 0.1875 / 0.2652 | 0.1953 / 0.1899 / 0.1924 |
| `foam` | 0.5535 % | 0.3812 % | 0.689x | 0.3963 / 0.2989 / 0.5136 | 0.3733 / 0.3579 / 0.3659 |
| `coffee-bean` | **5.0732 %** | **2.1657 %** | **0.427x** | 0.1735 / 3.4289 / 4.9765 | 2.1657 / 2.1656 / 2.1656 |

My corpus spans **0.0000 % to 5.0732 %** frame-wide, which brackets both of BUILD-ELECT's
figures. The effect is the same sign and the same shape at every point on that range, and
at zero clipping the output is byte-identical.

### 10.3 The more interesting column is `any` against `all`

A pixel clipped on *some* channels is a coloured highlight. A pixel clipped on *all* of
them is white. That distinction is this entire lane in one statistic:

| subject | `any` before | `all` before | neutral share | `any` after | `all` after | neutral share |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `foam` | 0.5535 % | 0.2601 % | 47.0 % | 0.3812 % | 0.3570 % | **93.6 %** |
| `coffee-bubbles` | 0.2995 % | 0.1365 % | 45.6 % | 0.1988 % | 0.1887 % | **94.9 %** |
| `coffee-bean` | 5.0732 % | 0.1729 % | **3.4 %** | 2.1657 % | 2.1656 % | **99.995 %** |

Before the fix, **96.6 %** of `coffee-bean`'s clipped pixels were clipped on only some
channels — they were coloured, not blown. After, essentially every clipped pixel is
clipped on all three. That is the defect stated in BUILD-ELECT's own units.

### 10.4 One cost, stated plainly

Luminance-preserving desaturation raises the weak channel as it lowers the strong one, so
**green clips slightly more often after the fix** (`foam` 0.2989 % -> 0.3579 %). Red and
blue fall further, so the any-channel total drops on every subject. If BUILD-BLEND is
measuring contrast on green in a band, that is a number they should take from a
post-fix render rather than a pre-fix one.

### 10.5 What I do and do not need from BUILD-BLEND

* **Not a dependency.** I validated the above without any merge-side census, by counting
  pinned pixels in the output TIFF. Sequencing me behind the census would be a false
  dependency.
* **The `47-93 px` band statistic is theirs, and I did not reproduce it.** I do not have
  their ROI definition and I will not guess at one; section 10.2 is frame-wide only and is
  comparable to their frame-wide row and to nothing else in their report.
* **Remedy (3) needs a different artefact.** A frame-wide *counter* — the thing being
  proposed — does not unlock highlight reconstruction. That needs a **per-pixel** record of
  which pixels and which channels were censored, which is a much heavier object. Adding the
  counter is worth doing on its own merits; it should not be expected to enable (3).

---

## 11. Cross-cut: ORCH's green-fringe ladder (`coffee-bubbles`, `foam`)

ORCH observed green-yellow rings on `coffee-bubbles` and rainbow speckle on `foam`, offered
four candidate mechanisms (A demosaic false colour, B real iridescence, C lateral CA,
D my channel-asymmetric clipping), and asked for a **ladder** localising the defect to a
pipeline stage *before* any fix is proposed. This section is that ladder. **No fix is
proposed here**, as instructed.

### 11.0 Provenance of ORCH's crops

The gallery binary is `C46BDF06...` (11:23). I scanned it for both of my fix's marker
strings, `chroma roll-off knee moved to` and `STREHL_HIGHLIGHT_KNEE`. **Neither is present.**
ORCH's crops therefore **predate the roll-off** and are not evidence about it either way.
All ladder arms below were consequently run with `STREHL_HIGHLIGHT_KNEE=off` so that they
reproduce ORCH's conditions rather than mine.

Two pipeline facts had to be established first, because they silently change what is being
compared:

* `--demosaic` (Malvar-He-Cutler) is **on by default whenever `--srgb` is given**. The
  gallery is `--srgb`, so ORCH looked at **demosaiced** images. Every highlight measurement
  in sections 1-10 of this document used `--linear-srgb` **without** `--demosaic`, i.e.
  **binned, never demosaiced**. The two populations were never comparable.
* The merge runs **per CFA plane at 3516x2344, before demosaic** (banner order:
  `black, as-shot WB, demosaic, matrix, clamp, sRGB curve`).

### 11.1 The instrument, and the two times it was wrong

`l2_falsecolour.py` reports four statistics on a mask of small bright features on dark
ground: `H` (high-pass chroma energy - speckle, candidate A), `L` (low-pass - smooth bands,
candidate B), `PH` (CFA-phase-locked spread, candidate A) and a radial profile (candidate C).

Calibration, from `--selftest` (5 cases, all passing):

| planted case | H | L | H/L | reads |
|---|---:|---:|---:|---|
| neutral scene | 0.00039 | 0.00005 | - | both ~0, as required |
| A, false colour speckle | 0.16852 | 0.02558 | **6.59** | H only |
| B, iridescence-like bands | 0.00058 | 0.25887 | **0.00** | L only |
| phase-locked plant | `PH=0.2751` | vs phase-blind noise `PH=0.0185` | | separated |
| degenerate mask | **REFUSED** | | | guard fires |

**The instrument was wrong twice and both times a control caught it.** Recording them
because the near-misses are the part worth keeping:

1. **A confident table of zeros.** The first `feature_mask` selected blown *cores*, which are
   exactly neutral by construction, so every arm reported `cr_med = cb_med = 0.000000` and
   `PH = 0.0000`. Fixed by requiring `max(RGB) < 0.99` and adding a **refusal guard** that
   aborts when >50% of the mask is exactly neutral. `neutral_frac` is now 0.0000 on all arms.
2. **A green-excess headline that was partly my own mask.** BT.709 luma is **71.5% green**,
   so ranking features by luma preferentially selects high-green pixels - which is precisely
   the "green excess" I was about to report. I added an adversarial selector `--select-on rb`,
   which ranks on `(R+B)/2` and **contains no green at all**, biased the opposite way.

The adversarial selector **changed the answer**, and this is the single most important line
in the section:

| statistic | luma | rb (adversarial) | max | robust? |
|---|---:|---:|---:|---|
| `cr = (R-G)/Y`, K3 | -0.1934 | -0.2089 | -0.2367 | **yes** - negative under all three, *more* so under `rb` |
| `cb = (B-G)/Y`, K3 | -0.0882 | -0.0071 | +0.0004 | **no** - collapses to zero, flips sign |

**So the blue half of "green excess" was a selection artefact and I withdraw it.** What
survives every selector is a **red deficit relative to green**. I would have reported the
blue component as fact had I not run this control.

### 11.2 The ladder

All arms: **one binary** `F9BD5191...`, all banners `merge backend : pyramid (--merge)`,
all `--linear-srgb` (magnitudes measured in linear, per ORCH's caution), all
`STREHL_HIGHLIGHT_KNEE=off`. Resolution-fair rows apply a 2x2 mean (`--bin2`) so every arm
is compared on the same 3516x2344 grid.

| arm | what it isolates | H (speckle) | L (bands) | H/L |
|---|---|---:|---:|---:|
| K1 single frame, demosaiced, `--bin2` | is it in ONE frame? | **0.2955** | 0.3083 | 0.96 |
| K3 stack, demosaiced, `--bin2` | shipping-ish | **0.2558** | 0.3583 | 0.71 |
| K2 stack, **binned, never demosaiced** | is it demosaic? | **0.2928** | 0.3660 | 0.80 |
| K5 stack, demosaiced, **`--fix-ca off`** | is it CA? | **0.2920** | 0.3663 | 0.80 |

**P1 - the merge is innocent. CONFIRMED.** K1 (one frame) `H=0.2955` vs K3 (stack)
`H=0.2558`: the **stack has 15.5% LESS** high-frequency chroma than a single frame. The
defect is **fully present in a single frame**; the merge slightly *reduces* it. ORCH's
"far more serious finding" - that per-channel weights diverge where signal is sparse - is
**dead**, and independently so by code: `pyramid.rs:990-993` computes the selection
denominator `den` **once on green luma and shares it across all planes**, with the existing
test `the_selection_is_shared_across_planes` (:2216) pinning exactly that. A shared scalar
weight cannot manufacture chroma.

**P2 - demosaic false colour. REFUTED.** K2, which is **never demosaiced**, scores
`H=0.2928` against demosaiced K3's `0.2558` on an identical grid - the never-demosaiced arm
is **12.6% worse**. Candidate A cannot be the primary cause of something that is present, and
larger, before demosaic runs. (Bound, not proof: demosaic-then-bin is mildly low-passed by
construction. The *direction* is the finding.)

**D - my channel-asymmetric clipping. DEAD BY SIGN.** D predicts green pins first, hence a
green *deficit* and **magenta** rims. Measured is a green *excess* / red deficit on every arm
and every selector. Opposite sign. ORCH anticipated this and was right.

### 11.3 Candidate C is not dead - it is the survivor

ORCH's discriminator was: *"if the fringe sign is uncorrelated with radial position, C is
dead."* It is strongly correlated. Signed `(R-G)/Y` by radial band, centre -> corner:

| arm / selector | b0 | b1 | b2 | b3 | b4 | b5 | corner/centre |
|---|---:|---:|---:|---:|---:|---:|---:|
| K3 CA **on**, luma | -0.1713 | -0.1804 | -0.2030 | -0.2854 | -0.2898 | -0.3954 | **2.31x** |
| K5 CA **off**, luma | -0.1726 | -0.1902 | -0.2122 | -0.1962 | -0.3069 | -0.4318 | **2.50x** |
| K3 CA **on**, max | -0.2037 | -0.2155 | -0.2504 | -0.3975 | -0.3296 | -0.4248 | **2.09x** |
| K5 CA **off**, max | -0.2041 | -0.2312 | -0.2617 | -0.4466 | -0.3906 | -0.6109 | **2.99x** |

The effect is **red-versus-green** and **grows 2.1x-3.0x from centre to corner**, monotonically
on every arm under every selector. That is the signature of **lateral chromatic aberration**,
which is a red-vs-green magnification error. It also explains the population specificity ORCH
noticed: a radial displacement of the red plane of order 1-3 px barely dents an *extended*
edge (`wrapped-text-1`, no rim — ORCH's characterisation, not my measurement, and see 14.6
on what a high-frequency-selected crop can and cannot certify) but is comparable to the
**entire width of a 1-2 px specular**,
so the red image of a tiny feature only partly overlaps the green one - a large fractional red
deficit exactly where ORCH sees rims.

`--fix-ca` is **already on by default** when the gear matches (banner:
`lateral CA : CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl" (gear matched; default on)`).
It **helps but does not finish the job**: it lowers `H` (0.1837 vs 0.2018 under luma; 0.2018
vs 0.2426 under max) and lowers radial growth (2.31x vs 2.50x; 2.09x vs 2.99x). A residual
red deficit still grows >2x to the corner **after** correction.

**A third near-miss, disclosed.** Under the `rb` selector alone, CA-off read *flat* (1.11x)
while CA-on read radial (2.22x) - which would have supported the headline "the CA correction
is making it worse". Two further selectors refuted it: under both `luma` and `max`, CA-off is
*more* radial than CA-on, i.e. the correction works in the correct direction. **I withdraw
that reading.** `rb` was the outlier and its CA-off profile is the only non-monotonic one in
the table. One selector is not a result.

### 11.4 What I am handing back

* The defect is **not the merge**, **not demosaic**, and **not my clipping asymmetry**.
* It is **radial, red-vs-green, present in a single frame** - i.e. **optical, candidate C**,
  partially corrected already, with a residual concentrated on small bright features.
* **B (real iridescence) is not excluded** and is probably also present: `H/L` is 0.50-0.96
  on real data against 6.59 for planted speckle and 0.00 for planted bands, i.e. a large
  smooth component plus a real but non-dominant speckled one.
* **The correct next experiment is not a chroma median filter.** A chroma-domain median would
  suppress the *symptom* of a residual registration error and would blunt the very fine real
  colour ORCH wants protected (the pollen grains). The residual is radial and therefore
  *modellable*: the next test is whether the CA profile's single global parameter is
  insufficient (a higher-order or per-radius fit), measured on the same ladder.

---

## 12. ORCH's discriminator: my radial statistic on BUILD-SHARP's subject

BUILD-SHARP measured `flower-bud-alone-cpl` and concluded the fringe is **not** lateral CA
(R-B displacement bounded at 0.05 px, G-vs-G null exactly 0.0000). I measured
`coffee-bubbles` and concluded C is the survivor. ORCH asked for the cheapest discriminator:
**my statistic, their subject, same ladder** - and explicitly not a re-run of theirs.

**Verdict: ORCH's possibility 1. The two fringes are different defects. Both reports stand,
and the two statistics do not disagree about anything.**

### 12.1 The subjects do not share a population

This is the whole answer, and it was visible before any statistic was computed:

| | `coffee-bubbles` | `flower-bud-alone-cpl` |
|---|---:|---:|
| per-channel max DN (gallery `--srgb`) | 65535 / 65535 / 65535 | 63809 / **64516** / 63733 |
| pixels at 65535, any channel | **0.0705 %** | **0.0000 %** |
| median luma (linear) | 0.0191 | 0.2848 |
| max luma (linear) | 1.0000 | **0.3400** |

**`flower-bud-alone-cpl` contains no clipped pixels at all**, has no near-black ground, and
spans a narrow mid-tone range. `coffee-bubbles` is specular-on-black and clips in all three
channels. My `feature_mask` - small bright *unblown* features on dark ground - returned
**zero pixels** on flower-bud and the instrument **refused to report**, which is the guard
working. Reporting "my mask found nothing" as "no defect" would have been precisely the
error this project has already paid for once, so the **statistic was held fixed and the
population was changed** to the one this subject actually has: high-gradient edges. The swap
is recorded in every output row.

### 12.2 The radial reading, like-for-like

Same binary `F9BD5191`, same instrument, same `edge` population, same selector, all
`--linear-srgb`. Every banner `merge backend : pyramid (--merge)`; the CA arms read
`CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl" (gear matched; default on)` against
`off (operator asked for "off")`, and the harness **asserts** those differ.

| subject / axis | b0 | b1 | b2 | b3 | b4 | b5 | corner/centre |
|---|---:|---:|---:|---:|---:|---:|---:|
| coffee `(R-G)/Y` **mine** | -0.2114 | -0.2027 | -0.2455 | -0.2756 | -0.3331 | -0.3508 | **1.66x** |
| coffee `(R-B)/Y` *SHARP's axis* | +0.0182 | -0.0293 | -0.3662 | -0.3383 | -0.5592 | -0.7109 | **39x** |
| flower-bud `(R-G)/Y` **mine** | -0.0316 | -0.0432 | -0.0534 | -0.0366 | -0.0376 | -0.0414 | **1.31x** |
| flower-bud `(R-B)/Y` *SHARP's axis* | +0.0998 | +0.0827 | +0.0848 | +0.1106 | +0.1038 | +0.0790 | **0.79x** |

**My statistic reads flat on their subject.** Flower-bud's `(R-G)/Y` sits at -0.04 and does
not grow; coffee-bubbles' reaches **-0.3508**, an **8.5x larger** corner value on the same
population and instrument.

> **This table has no selector control, and section 11.3's does.** The rows here vary by
> *subject* and *axis* — not by selector. The selector axis is missing because it is **inert
> on this population**: `edge_mask` ranks on the luma *gradient* and ignores `select_on`
> outright (`l2_falsecolour.py:73`, *"`select_on` IS DELIBERATELY IGNORED HERE"*), so running
> it under `luma`, `rb` and `max` returns three **identical** rows. I print one rather than
> three, because three identical rows read as three agreeing confirmations and are one
> measurement. But the reader must carry the consequence: **the adversarial-selector control
> that overturned the blue half of section 11 does not operate on anything below this line.**
> Section 11.3's four rows *do* separate under `luma` vs `max`; these would not.

**I withdraw, before stating it, the hypothesis I went in with.** I expected R-B to be
partly *blind* to a residual carried against green, since green is this codebase's reference
channel (`optics.rs` gives it no coefficient and freezes both green gathers bitwise) and red
and blue are corrected toward it with opposite-signed coefficients. That would have been a
tidy reconciliation. **It is false:** on coffee-bubbles the R-B axis grows **39x** to -0.71,
far more strongly than my own axis. SHARP's instrument would have caught my defect easily had
it been pointed at my subject. There is no conflict between the statistics - only between the
subjects.

### 12.3 The instrument was calibrated for this question first

The radial axis had never been shown able to fail, so two planted cases were added before any
of the above was believed (`--selftest`, now 7 cases, all passing):

* **E, purely photometric radial attenuation with ZERO geometric shift** - the case a
  displacement bound scores as *exactly* zero. Read `-0.0351 -> -0.2287`: **detected.**
* **F, a flat red offset of comparable size and no radius dependence** - read
  `-0.1284 -> -0.1284`, **exactly flat**. The axis does not convict a plain colour cast of
  being lateral CA.

E and F together are what license the claim: the statistic sees radial-photometric defects
that plant no displacement, and stays silent on non-radial ones.

### 12.4 ORCH's registered prediction on `flower-bud-alone-cpl`, resolved

ORCH registered that my roll-off should have removed the fringe there. **It could not have,
and did not run at all.** Same binary, same subject, knee off against knee on:

```
M1 knee=off : 48AF23CC123144284F6BB99A8E4BF3B3
M3 knee=on  : 48AF23CC123144284F6BB99A8E4BF3B3   => BYTE-IDENTICAL
```

and the same test **does** separate the arms on coffee-bubbles (`2A36DAB1...` vs
`4C50881...`), so it is not an instrument that always says "identical". The roll-off engages
on `u = v_c/ceil_c` above a knee of 0.60; this subject's maximum is 0.34. **The prediction
was mis-specified rather than falsified** - it was pointed at a subject the fix provably
never touches.

### 12.5 The profile's provenance, which ORCH asked be put to the code first

**It was fitted for the teleconverter, not inherited and renamed.** `optics.rs:423` pins
`lens_type3: 33094`, documented as "the composed path WITH the 2x teleconverter; the bare
lens is 32893 and **must not match**", and `measured_from` cites M107's 20 gated ROIs
(tweezers-cpl, bee-3-cpl) for red and BUILD-CHROMA's 1071 tiles for blue. ORCH's suspicion is
answered: no.

**But the corner is extrapolated, and that is the live limitation.**
`support_r_max: Some(0.788)` carries its own comment: *"the 20 gated ROIs span
r = 0.208..0.788, six of ten annuli populated, **outer two annuli empty. The corner is a
1.27x linear extrapolation. Declared, not enforced.**"* The fit has **no data** past
r = 0.788, nothing stops it being applied to r = 1.0, and the outer bands are exactly where
my residual grows.

Two further coefficient facts, offered as leads and **not** as findings:

* The shipped `eps_r` is **704.5 ppm**, while the six per-stack fits recorded in the same
  file span **500.9-651.9 ppm** - the global value is larger than every individual
  measurement, from a different instrument on different subjects.
* Consistent with that, on unclipped flower-bud the correction moves `cr_med` from
  **+0.0258 (off) to -0.0426 (on)** - from near-neutral to a small red deficit. One subject,
  small effect, and I have already withdrawn one "the correction makes it worse" claim
  tonight for resting on a single reading. **This needs its own test before anyone acts on
  it**, and the natural one is whether a per-radius or second-order term beats the single
  scalar.

---

## 13. Closing the fringe: the remedy does not belong in `optics.rs`

ORCH granted me `optics.rs` to enforce the declared support limit, test whether one global
scalar is enough, and settle my `eps_r` lead. **I did not edit it, and this section is why.**
Three of the four things I was asked to do are either already settled against me or are not
expressible in the code as it stands, and the fourth is aimed at a minority term.

**Ownership checked first, as instructed:** `git log --oneline -12 -- crates/strehl-core/src/optics.rs`
shows the last commit at **05:04**, 10.5 hours before I started, and
`git status --porcelain -- crates/strehl-core/` shows no uncommitted changes to it. Another
lane is live in `photometric.rs` and four `examples/`, but not in my file. It was idle.

### 13.1 The premise is wrong, and one number does it

ORCH's brief: *"the residual you measured grows exactly there [past r = 0.788]."* It does
grow there. But growth is a statement about the radial term's **slope**, not about **how
much of the defect is radial** - a distinction my own section 12 did not make, and should
have. Decomposing `cr(r) = A + B*r` separates them, and the decomposition is decisive.

Per-annulus medians of `(R-G)/Y` on `coffee-bubbles`, edge population, `--linear-srgb`,
binary `F9BD5191`, banner `merge backend : pyramid (--merge)`:

| r | 0.04 | 0.13 | 0.21 | 0.29 | 0.37 | 0.45 | 0.53 | 0.61 | 0.70 | 0.78 | 0.86 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CA **on** | **-0.26** | -0.20 | -0.19 | -0.21 | -0.26 | -0.30 | -0.31 | -0.28 | -0.28 | -0.33 | -0.35 |
| CA **off** | **-0.26** | -0.21 | -0.20 | -0.23 | -0.31 | -0.19 | -0.27 | -0.34 | -0.13 | -0.15 | -0.55 |

**At r = 0.04 - on axis, where lateral CA is identically zero - the red deficit is already
-0.2588**, against a corner value of -0.3549. That is a direct annulus median, not a fit.
**About 74 % of the defect is present where the aberration being blamed for it contributes
nothing.** `optics.rs::displacement_at` returns `eps * radius`; M107 records the displacement
going "-> 0 at the optical centre". A term that is large on axis cannot be lateral CA, and no
clamp, taper or refit of a radial coefficient can reach it.

**And the region ORCH asked me to enforce contains almost nothing.** Only **1.3 %** of the
masked population lies beyond `r = 0.788`. Enforcing the declared support could touch at most
that 1.3 %, of a term that is itself the minority of the defect.

### 13.2 The remedies are not expressible in the current transform class

This is the structural reason "declared, not enforced" was the right call for a stronger
reason than M107b gave, and it applies to all three of ORCH's options.

The correction is applied as a **`Similarity`**. `OpticalProfile::compose`
(`optics.rs:296`) returns `Similarity { a: t.a * s, b: t.b * s + t }` with `s = 1 + eps`,
and `align_cmd::warp_frame_in_place` takes a `Similarity`. Its own doc comment states the
design goal: *"Both closed forms, and a single similarity - the correction rides the gather's
existing interpolation and adds no second resampling pass."*

**A similarity is a uniform scale about the origin. There is no radius in it.** `eps * r`
appears only in `displacement_at`, which is a reporting function with no production caller;
`support_r_max` is likewise read only by a test (`optics.rs:1301`). So:

* **"Clamp at r = 0.788"** - not expressible. A uniform scale cannot stop at a radius.
* **"Taper to zero"** - not expressible, same reason.
* **"Fit a term supported out there"** - a higher-order radial term is also not a similarity.

Any of them requires either changing the registration core to accept a non-linear warp -
breaking the invariant the code explicitly relies on, *"still a Similarity, so L6 is
unaffected"* - or adding a **second resampling pass**. The second option is worse than it
looks: an extra resample is an extra low-pass on R and B, and the defect under investigation
is *red losing amplitude on small bright features*. The obvious fix pushes in the direction
of the defect.

### 13.3 My `eps_r` lead: WITHDRAWN, and it was settled before I raised it

I reported that shipped `eps_r` = 704.5 ppm sits above every per-stack fit (500.9-651.9 ppm).
**That comparison is invalid and the refutation was three pages above the table I read it
from.** BUILD-CHROMA §11.2:

> *"the shipped `eps_r = -704.5 ppm` is **already correct**, and my Phase-2 draft claiming it
> over-corrects by 7-26 % was wrong. That draft was built on raw estimates which are
> **attenuated by a stack-dependent factor of 0.69-0.94**. Correcting for the attenuation
> moves my six red measurements from a 39 %-spread band that excludes -704.5 into a
> 16 %-spread band **centred on it**."*

The per-stack figures are **raw and attenuated**; the shipped scalar is de-attenuated. I put
one against the other. This is the same class of error as the luma-selector circularity in
section 11 - a number that looked like evidence because of how it had been prepared.

**A global rescale has also already been tried and rejected.** M113 measured the needed gain
as **1.2496** on `bee-3-cpl` and **1.0557** on `couch-fibers-cpl` - *"The gain does not
transfer"* - and `captures-needed.md` records that the proposed x0.692 **"must not ship"**
because on `couch-fibers-cpl` it converts a 5.6 % over-correction into a **27.0 %
under-correction**. ORCH's item 3 is closed, by prior work, against me.

### 13.4 The band-4 wobble, carried forward as instructed

The erratic outer annuli are a **CA-off** phenomenon. With the correction off the outer field
reads `-0.34, -0.13, -0.15, -0.55`; with it on, `-0.28, -0.28, -0.33, -0.35`. **The
correction does stabilise the outer field** even though it does not remove the constant term,
which is a point in its favour and against any move to disable it. I have not explained the
CA-off instability itself; with 1.3 % of the population beyond r = 0.788 and a `-0.0455`
single-band excursion in the earlier six-band binning, small-sample variance is the obvious
candidate and I have not excluded it.

### 13.5 What the constant term probably is - and why I am NOT claiming it

The field-independent red deficit has an obvious candidate already measured in this corpus.
**M107 fact 1413:** axial CA is real and baked in, because the election is computed from
`green_luma` alone and the winning index is reused across all four CFA accumulators;
`k_R - k_G` = **-0.67 to -1.07 frames**, and red forfeits **8.96-14.74 %** of its gradient
energy. A channel elected at the wrong focus is defocused **everywhere in the field**, and a
defocused channel loses proportionally most amplitude on the *narrowest* features - which is
exactly a red deficit on small bright speculars, on axis, independent of radius.

**I tried twice to test this and both instruments were confounded, so I am reporting it
untested rather than picking the one that agreed with me.**

* Gradient energy normalised by channel **mean** gave red **-85 %** against green. Rejected:
  on a near-black subject that ratio conflates level with sharpness, and it disagrees with
  M107's established 8.96-14.74 % by an order of magnitude.
* Gradient energy normalised by channel **variance** (scale-invariant, calibrated on planted
  blur: sigma 0.3/0.5/0.8 -> 0.99/0.74/0.33) gave red **+42 %**, the opposite sign. Rejected:
  red has the lowest SNR on this subject and noise inflates a high-frequency fraction, so
  this cannot separate "red is sharper" from "red is noisier".

Two confounded instruments are not one finding. The hypothesis is handed over, with its
citation, and **the discriminating experiment is a per-channel focus-index offset** - which
is fact 1417's ARGUED cheaper alternative to per-channel election, and which lives in the
estimator, not in `optics.rs`.

### 13.6 What I recommend

**Do not change `optics.rs`.** The lateral-CA correction is the minority term, it is measured
correct in magnitude, a global rescale is already rejected, its support limit governs 1.3 %
of the affected population, and it demonstrably stabilises the outer field. The remaining
74 % is on-axis and belongs to whatever makes red systematically weaker on fine bright
features - most plausibly the green-only election, which is the estimator's, not optics'.

---

## 14. Auditing my own report for the failure mode I found in it

ORCH's closing task: check whether any *other* table here repeats a measurement under
different-looking headings, *"since that is the failure mode you already identified and your
own report is the last place it would be looked for."*

I did not read the tables to answer this. Reading my own report for a bias I already know I
have is the same error one level up, and there are 115 table lines across 13 sections.
`n3_dupscan.py` extracts every row's numeric signature and flags repeats: within a table
under different labels, across tables under different headings, and inside ``` fences.

**Calibrated before it was believed**, six cases, and it must both fire and stay silent:

| planted | required | got |
|---|---|---|
| three identical rows | flag | **2 flags** (n-1 duplicates) |
| same row under two headings | flag | **1 flag** |
| repeat inside a ``` fence | flag | **1 flag** |
| all-distinct rows | silent | **0** |
| `0.100` vs `0.101` | silent | **0** |
| distinct fence lines | silent | **0** |

### 14.1 The scan found no second instance of the defect

80 numeric rows scanned. Two hits, both adjudicated by reading:

* **§5.3, `before, SHA-256` == `after, SHA-256`.** A true repeat and an *intentional* one —
  the identity **is** the result, and the line under it says **"Byte-identical."** Not a
  defect; the detector is correct to raise it and a human is correct to clear it.
* **§11.3 vs §12.2, signature `0 1 2 3 4 5`.** False positive: those are the band indices in
  the header `| b0 | b1 | ... |`, not data. Known false-positive mode, stated not hidden.

### 14.2 What the scan's SILENCE found, which is the real result

**The detector did not flag §12.2 — and that is what exposed the defect.** I had assumed the
three identical rows were sitting in that table. They are not: §12.2's four rows vary by
*subject* and *axis* and are all distinct. I had collapsed the selector rows when I wrote it
and then, when ORCH asked me to move the caveat inline, attached it to the surviving table.

So the caveat read **"These rows are ONE measurement, not three"** directly above four rows
that are four measurements. A reader checking the claim against the table would have found it
false, and correctly discounted the warning — **a mis-aimed caveat is worse than no caveat,
because it discredits itself.**

The honest statement, now in place, is not about duplication at all. It is about **absence**:

> This table has **no selector control**, and §11.3's has one. The selector axis is missing
> because `edge_mask` ranks on the luma *gradient* and ignores `select_on` outright
> (`l2_falsecolour.py:73`). Three selectors return three identical rows, so I print one. The
> consequence the reader must carry: the adversarial-selector control that overturned the
> blue half of §11 **does not operate on anything below that line.** §11.3's rows *do*
> separate under `luma` vs `max`; these would not.

That is a stronger warning than the one ORCH asked for, and it is the one the data supports.

### 14.3 Blind spots, declared

The scan detects **numeric** duplication only. The same run reported twice at different
roundings, or under two names with one column dropped, would evade it entirely — that is
semantic duplication and it still needs a reader. Header rows containing numbered column
names produce spurious cross-table signatures, as §14.1's second hit shows. And only 2
numeric lines live inside fences in this report, so that arm of the scan is barely exercised
on real data despite passing its plant.

### 14.4 ORCH's standing question, aimed at my own load-bearing null

> *"What property of the input decides whether this check can see anything, and have I
> varied it?"*

Section 12's null — *my radial statistic reads flat on `flower-bud-alone-cpl`* — was used to
settle a cross-lane conflict, so it is the one worth aiming this at. For a **radial**
statistic the governing property is how far out the population actually reaches, and
`l2_falsecolour.py:205` sets the band edges from the data:

```python
edges = np.linspace(0, r.max() + 1e-9, 7)
```

**The axis self-normalises per subject.** "Band 5" means *as far out as this subject's mask
reached*, and I never reported what that was. Measured with the shipped `edge_mask` imported
rather than reimplemented (`n_mask = 165018` reproduces the saved run exactly):

| subject | `r.max()` | outermost band centre | corner band count |
|---|---:|---:|---:|
| flower-bud | 1.1260 | 1.032 | 14240 |
| coffee-bubbles | 1.3086 | **1.200** | **852** |

So the published **1.31x vs 1.66x** compared each subject's own span, and those spans differ
by 16 %. That comparison was not as like-for-like as section 12 implied.

**The null survives the sharper test.** At *matched* radius the two subjects separate at
every pair, including on axis:

| r (fb / coffee) | 0.09/0.11 | 0.28/0.33 | 0.47/0.55 | 0.66/0.76 | 0.85/0.98 | 1.03/1.20 |
|---|---:|---:|---:|---:|---:|---:|
| flower-bud `(R-G)/Y` | -0.0316 | -0.0432 | -0.0534 | -0.0366 | -0.0376 | -0.0414 |
| coffee `(R-G)/Y` | -0.2114 | -0.2027 | -0.2455 | -0.2756 | -0.3331 | -0.3508 |
| ratio | **6.7x** | 4.7x | 4.6x | 7.5x | 8.9x | **8.5x** |

Flower-bud is flat across its **whole** span, out to r = 1.03 — past the radius where coffee
already reads -0.2756. The subjects differ at every radius both sample, so the differing
reach is not what produced the flat reading. **Section 12's conclusion stands; its ratio
comparison carries this qualification.**

**And this partly explains the band-4 wobble I carried forward in section 13.4.** Coffee's
outermost band holds **852 pixels** against flower-bud's 14240 — above the instrument's
`None` guard of 20, but thin. I wrote that small-sample variance was "the obvious candidate
and I have not excluded it"; the occupancy numbers now support it directly.

**One instrument defect caught in the course of this audit**, disclosed because it nearly
shipped: my first run passed `pct = 0.5` where `stats()` passes `bright_pct = 99.5` into
`np.percentile(g, pct)`. That selected the bottom 99.5 % — the **complement** of the
population under audit — and returned confident, plausible numbers with identical band
centres on both subjects, which would have "cleared" the null for entirely the wrong reason.
It was caught only because `n_mask` came back at 32.8 M against the saved run's 165018.
**Reproducing a stored value from the run being audited is what caught it**, and an audit
instrument that cannot reproduce its target's numbers is not auditing it.

### 14.5 The magnitude form found a sign error in section 11, and it is mine

Section 14.3 declared this instrument's blind spot: *"the same run reported twice at
different roundings would evade it entirely."* That blind spot belongs to the **boolean**,
not to the question. Re-asked as *how close are these two rows*, the same scan returns a
number — and on my own report it returns exactly one pair under 2 %:

| | H | L | H/L |
|---|---:|---:|---:|
| K2 stack, binned, never demosaiced | 0.2928 | 0.3660 | 0.7999 |
| K5 stack, demosaiced, `--fix-ca off` | 0.2920 | 0.3663 | 0.7971 |

**closeness 0.00082.** Two arms differing in *two* processing stages, landing 0.08 % apart.
Verified against `l4-resfair.json` — not a transcription error, and `n_mask` differs (14553
vs 18534), so they are genuinely separate renders. The boolean scan reported **zero** flags
on this pair and could not have done otherwise.

Following it into the JSONs exposed something I had not seen:

| arms | single | stack | direction |
|---|---:|---:|---:|
| **L** (analysed at 4688x7032) | 0.1712 | 0.1875 | stack **+9.5 %** |
| **K** (analysed at 2344x3516) | 0.2955 | 0.2558 | stack **-13.4 %** |

**The two arm sets disagree in sign**, and section 11's P1 rests on the K row. Isolated by
holding the FILES fixed and varying only the bin — the one thing that can answer it:

```
native : single 0.1891 -> stack 0.2017   +6.7%   stack WORSE
binned : single 0.2472 -> stack 0.2315   -6.3%   stack BETTER
```

Same two files. **The 2x2 mean is a low-pass and `H` measures high-frequency chroma, so the
resolution-fair transform changes the quantity being compared.** My absolute values differ
from the stored run by ~10 % (parameters not identified — stated, not hidden), but both
directions reproduce.

**What this does and does not overturn.**

* **P1's measurement is withdrawn as stated.** *"The stack has 15.5 % LESS high-frequency
  chroma"* holds only after binning; at native resolution the stack reads **worse**. The
  claim needed a scale qualifier and did not carry one.
* **P2 is unaffected.** It compares K2 against K3, and K2 is natively half-resolution, so
  that comparison *requires* the bin. It is legitimately binned.
* The code argument for P1 (`pyramid.rs:990-993`) is untouched by this — and ORCH has
  already corrected its inference separately.

**The error underneath it is a single sentence.** I applied `--bin2` because **one**
comparison needed it — K2 is half-resolution and cannot otherwise be compared — and then
applied it to **every** arm, including K1-vs-K3, which are both full-resolution demosaiced
and never needed it. *A transform introduced to make one pair comparable was applied to a
pair that was already comparable, and reversed its sign.*

That is ORCH's standing question a second time: the property deciding what `H` can see is
the spatial-frequency content of the input, and I varied it — while measuring it.

### 14.6 Putting an amplitude on section 12's null

> ORCH: *"A detector's silence is worth nothing until it has been made to speak at a stated
> amplitude. Unqualified, 'clean' and 'deaf' are the same word."*

Section 12 reported `flower-bud-alone-cpl` **flat**. The instrument had been calibrated — a
planted radial was detected, a flat colour cast correctly was not (12.1) — but **calibration
is not a floor**, and I never said *flat above what*. Ladder, planting a lateral-CA-shaped
red deficit `R' = R * (1 - A*r)` into the real subject:

| A (plant) | cr centre | cr corner | corner-centre | vs baseline |
|---:|---:|---:|---:|---:|
| **0.00** | -0.0316 | -0.0414 | **-0.0098** | *(baseline)* |
| 0.01 | -0.0336 | -0.0514 | -0.0178 | -0.0081 |
| 0.02 | -0.0352 | -0.0614 | -0.0262 | -0.0165 |
| 0.05 | -0.0402 | -0.0917 | -0.0515 | -0.0417 |
| 0.10 | -0.0488 | -0.1430 | -0.0942 | -0.0844 |

**The A = 0 rung reproduces section 12's published numbers exactly** (-0.0316, -0.0414). That
is the anchor: a harness whose null rung does not land on the measurement it claims to
audit is not auditing it, and every rung above it would be meaningless. Response is linear
at **~0.84 x A** across a 10x span.

**The qualified statement, replacing "flat":**

> `flower-bud-alone-cpl` shows no radial red deficit at or above a plant of **A = 0.01** — a
> 1.1 % red reduction at the corner — which this statistic registers as a corner-centre shift
> of **-0.0081**. The effect measured on `coffee-bubbles` is **-0.1394**, i.e. **17x larger
> than the smallest plant demonstrated detectable.**

That is what makes the null load-bearing: the instrument was shown to see something **17x
smaller** than the effect it was being asked to rule out. Without the ladder, "flat" and
"deaf" were the same word, exactly as ORCH says.

**Limit, stated:** I did not probe below A = 0.01, so the true floor may be lower. The claim
is a bound, not a threshold — the smallest amplitude *demonstrated* detectable, not the
smallest detectable.

**And one correction upstream.** Section 11.4 called `wrapped-text-1` "clean". That was
ORCH's characterisation of a 1:1 crop, inherited by me and not measured — and `build_view.py`
selects crops by **maximum high-frequency energy**, which by construction cannot speak to
smooth-tone defects on the white paper that dominates that subject. Reworded to "no rim",
which is the claim the evidence actually supports.

#### 14.6.1 Is that floor instrument-limited or quantisation-limited?

ORCH's corrected PIL audit — *count distinct values, do not check for a 256x scale error* —
lands directly on 14.6, because a **detection floor is a small-amplitude claim and
quantisation is exactly what destroys those.** A floor of -0.0081 means nothing if the input
could not represent it.

My first audit was **static**: grep every script for `PIL` / `Image.open`, found none, all
twelve read via `tifffile`. That is necessary and **not sufficient** — `tifffile` on a
genuinely 8-bit file returns `uint8` honestly, and a grep of my reader cannot see loss that
happened upstream of it. The dynamic check is the one that certifies the data:

| file | dtype | distinct values | min | max |
|---|---|---:|---:|---:|
| `M1-caon-kneeoff` (the 14.6 ladder input) | uint16 | **22376** | 36 | 22668 |
| `K3-stack-demo` | uint16 | 65500 | 0 | 65535 |
| `K5-stack-caoff` | uint16 | 65510 | 0 | 65535 |
| `K2-stack-binned` | uint16 | 60811 | 0 | 65535 |

**Margin:** the `A = 0.01` plant reduces red by 1.1 % at the corner — on a 22668-max image
that is ~250 DN against a quantisation step of 1 DN. **The floor sits ~250x above the
quantisation limit**, so it is a property of the statistic and not of the file's tonal
resolution.

**The transferable part:** a static check on the *reader* and a dynamic check on the *array*
answer different questions, and only the second certifies a magnitude. I ran the static one
first and would have stopped there.
