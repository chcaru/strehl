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
  none. The estimator backend renders equally bright, so it is not a backend difference.
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
