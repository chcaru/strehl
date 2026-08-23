# M26 — Colour ordering and clipping: two traps in front of the merge

> **NOT INDEPENDENTLY VERIFIED.** Measured by the orchestrator. Rule 12 binds
> its author exactly as it binds any milestone author.

Review item **R13** (colour management) was the last item still marked *"no
plan"*. Most of it is a design decision, not a measurement — but two parts are
measurable right now, and both turn out to sit directly in front of the merge
that M18 is building. This milestone measures those two and leaves the rest of
R13 as design.

## 1. MEASURED — white balance is a large per-channel gain, and it is not constant

As-shot multipliers, normalised to green, read from the first frame of each stack:

| stack | R | G | B |
|---|---:|---:|---:|
| `109MSDCF` | **2.861** | 1.000 | 1.482 |
| `119MSDCF` | 2.711 | 1.000 | 1.408 |
| `coffee-bean` | 2.634 | 1.000 | 1.474 |
| `112MSDCF` | 2.615 | 1.000 | 1.789 |
| `113MSDCF` | 2.640 | 1.000 | 1.761 |
| `coffee-bubbles` | 2.131 | 1.000 | **1.884** |

Two things follow. **The multipliers are large** — R is scaled by up to 2.86×.
And **they vary per stack** (R spans 2.13–2.86, B spans 1.41–1.88), because the
body was on auto white balance. `daylight_whitebalance` is identical across all
six stacks, so it is the *as-shot* value that carries the variation. **Read WB
per stack; never hard-code it into a profile.**

Both green multipliers are exactly equal (1024/1024) on every stack, so no
G1/G2 imbalance term is needed for these captures.

The colour matrix `rgb_xyz_matrix` is identical across all six stacks, as
expected — it is a property of the camera model, not the capture:

```
 0.7460  -0.2365  -0.0588
-0.5687   1.3442   0.2474
-0.0624   0.1156   0.6584
```

## 2. DERIVED — so WB must not be applied before the noise-model gate

The calibrated model is `σ²(S) = g·S + (RN_e·g)²`, valid in **raw DN, per
channel, before white balance**. Scale a channel by `m` and the true noise
scales with it:

```
true:   σ²  =  m²·( g·S + (RN·g)² )
naive:  σ²  =  g·(m·S) + (RN·g)²        # the model applied to WB'd values
```

The ratio `σ_true/σ_naive` tends to **`m`** in the read-noise-limited (shadow)
limit and **`√m`** in the shot-noise-limited (highlight) limit:

| stack | channel | m | shadow error | highlight error |
|---|---|---:|---:|---:|
| `109MSDCF` | R | 2.861 | **2.86×** | 1.69× |
| `109MSDCF` | B | 1.482 | 1.48× | 1.22× |
| `coffee-bubbles` | R | 2.131 | 2.13× | 1.46× |
| `coffee-bubbles` | B | 1.884 | 1.88× | 1.37× |

**A gate that white-balances first believes the red channel is up to 2.86×
quieter than it is, and it believes it most strongly in the shadows** — which is
precisely where M2 measured the argmax defect. The failure is silent: nothing
crashes, the gate simply rejects too aggressively and the output reverts toward
the selector this project exists to replace.

**Ordering rule, DERIVED: demosaic-free gating happens in native per-channel raw
DN; white balance and the colour matrix are applied after the merge.** If any
future plugin needs WB applied earlier, it must transform the noise model with
it, and that transform must be part of the plugin contract rather than a
convention.

## 3. Checked and clean — the white-level trap is already handled

`rawpy` exposes **two** white levels for these files and they disagree:

| field | value |
|---|---|
| `white_level` | **16383** — the 14-bit container maximum |
| `camera_white_level_per_channel` | **[15360, 15360, 15360, 15360]** |

Taking the container value would overstate the usable range by 6.7% and put the
noise model's saturation knee in the wrong place. **The project already has this
right**: `strehl-core/src/noise.rs` documents `Levels::white` as *"15360, **not**
16383"* and pins it with the test
`usable_white_level_is_not_the_container_maximum`. Recorded here as a
checked-and-clean result so the next person does not re-derive it.

**But real data exceeds the declared white level**, which the code does not
currently anticipate — see §4.

## 4. MEASURED — saturation is real, per-stack, and absent from four of six stacks

Census over three frames per stack (first, middle, last):

| stack | max value | ≥ 15360 | = 16383 | fraction ≥ 15360 |
|---|---:|---:|---:|---:|
| `109MSDCF` | 5,962 | 0 | 0 | 0 |
| `119MSDCF` | 6,464 | 0 | 0 | 0 |
| `coffee-bean` | 16,383 | **1,249,261** | 1,580 | **1.26e-02** |
| `112MSDCF` | 6,416 | 0 | 0 | 0 |
| `113MSDCF` | 9,340 | 0 | 0 | 0 |
| `coffee-bubbles` | 16,383 | 73,080 | 62,054 | 7.39e-04 |

**Four of six stacks never come within 39% of the white level** — their maxima
sit at 39–61% of 15360. Two do reach it, and both contain pixels pinned at the
container maximum. So saturation is not a corner case to be assumed away, and it
is also not universal: it is a per-stack property that the pipeline must detect
rather than assume either way.

This also re-frames the corpus. The stacks that most measurements were made on
(`109`, `119`) are the ones with **no** saturated pixels at all, which is a
second respect — after M24's photometric finding — in which they are the
gentlest stacks available.

## 5. MEASURED — the headline: **both** confidence candidates read *maximum* on clipped pixels

On `coffee-bubbles` (19 frames), classifying every pixel of the green sublattice
by how many frames clip it:

| group | n |
|---|---:|
| never clipped | 8,199,287 |
| **sometimes** clipped | 36,913 |
| **always** clipped | **616** |

First, pixel-value spread across frames, against the model:

| group | cross-frame std | modelled σ |
|---|---:|---:|
| always clipped | **exactly 0.000** | 190.6 DN |

Then discipline 29's actual quantity — **cross-frame contrast of the focus
peak**, `(f_max − f_min)/f_max`, which the project chose *specifically because*
focus magnitude fails on fact 73's monotone edge:

| group | n | median contrast | mean contrast |
|---|---:|---:|---:|
| never clipped | 8,199,287 | 0.5398 | 0.5776 |
| sometimes clipped | 36,913 | 0.8998 | 0.8788 |
| **always clipped** | **616** | **1.0000** | 0.9698 |

**Always-clipped pixels return 1.0000 — the metric's maximum — at pixels whose
value is pinned in every frame and which therefore carry exactly zero
information.** This is the same class of failure as fact 73, arriving through
the quantity that was chosen to prevent it.

The mechanism is measured, not assumed:

| group | median `f_min` | median `f_max` | fraction with `f_min` **exactly** 0 |
|---|---:|---:|---:|
| always clipped | **0.000** | 7,598.1 | **0.859** |
| never clipped | 69.723 | 145.6 | 0.000000 |

In at least one frame the pixel sits *inside* a uniformly clipped blob, where
the gradient is identically zero; in another the blob's edge crosses it, giving a
gradient **52× the typical** `f_max`. The contrast ratio is then 1.0 by
construction. So focus *magnitude* reads maximum there too — **both candidates
fail in the same direction**, and discipline 29 does not protect against this
one.

**Fix, and it is nearly free: mask pixels at or above the container maximum
before they enter the focus volume, and propagate the mask.** One comparison per
sample.

## 6. What I got wrong

**I predicted the danger was in the *partially* clipped population and it
mostly is not.** The reasoning was that a pixel clipped in some frames but not
others has a truncated through-focus curve, manufacturing spurious cross-frame
contrast. Raw numbers looked like strong support: sometimes-clipped pixels read
0.8998 against never-clipped 0.5398, a **1.67×** elevation.

Restricting both groups to the same mean-level bin — so brightness cannot
explain the difference — collapses it:

| mean-level bin | never (n, median) | sometimes (n, median) | ratio |
|---|---|---|---:|
| [8000, 12000) | 8,271, 0.8383 | 13,315, 0.8910 | **1.063** |
| [12000, 14000) | 389, 0.7913 | 6,739, 0.8582 | **1.085** |

**So ~90% of the apparent effect was brightness, not clipping**, and the real
residual is 6–9%. The hypothesis survives only in a weak form. This is
discipline 70 applied to my own work: the first framing binned a statistic
against a population that co-varies with it.

The finding that *did* survive is the one I had reasoned my way past — I had
argued that a fully clipped blob would show *zero* focus contrast and therefore
correctly report zero confidence. That is wrong, and it is wrong because I
thought about the blob's interior in a single frame instead of about how its
*extent* changes across the bracket.

## 7. What was NOT measured

- **No brightness-matched control is constructible for the always-clipped
  group**, because by definition no unclipped pixel reaches that level. The §5
  claim rests on the measured `f_min = 0` mechanism plus the deterministic
  argument that a pinned pixel carries no information — not on a matched
  comparison. It should be read as MEASURED mechanism, DERIVED consequence.
- **The frames are not aligned.** Cross-frame spread therefore contains scene and
  breathing motion. For the always-clipped group this is conservative (motion
  could only *raise* their spread above zero, and it did not), but the
  never-clipped baselines are inflated by an unknown amount.
- **616 pixels is 0.0075% of the plane.** The severity is maximal but the
  population is small; `coffee-bean`'s 1.26% ≥ white-level population is much
  larger and was not run through §5.
- Only the green sublattice at `(0,1)`, only `R = 2`, only `coffee-bubbles`.
- **The rest of R13 is untouched**: no colorimetric target chosen, no rendering
  intent, no ICC/DNG output decision. Those are design, not measurement.
- PRNU (`κ`) remains blocked on the flat-field capture, `captures-needed.md` §4.

## 8. Proposed record

Facts **200–203**, discipline **110–111**, question **35**. Reconciled by the
orchestrator at fold time, not here.

## 9. Reproducing

```
experiments/m26-colour-clipping/src/
  01-colour-metadata.py     WB multipliers, colour matrix, levels, per stack
  02-white-level.py         the 16383 vs 15360 discrepancy
  03-saturation-census.py   saturation census + the WB/noise-model error table
  04-crossframe-spread.py   pixel-value spread vs modelled sigma, binned
  05-focus-contrast.py      discipline 29's quantity by clip group + matched control
  06-mechanism.py           f_min -> 0 as the mechanism
```
