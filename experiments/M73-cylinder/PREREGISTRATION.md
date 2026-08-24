# M73 — pre-registration: the cylinder invariant on real captures

**Status: REGISTERED.** Committed before any residual, ratio or hit rate existed.
The only numbers in this file are *design inputs* — geometry and drift measured
from image **intensity**, with no focus operator anywhere in their derivation —
and the thresholds they justify. Every one of them is stated here so that a later
disagreement with the result cannot be resolved by moving them.

Predecessor: `docs/research/M67-focus-correctness.md`. M67 designed this test,
measured `H = 99.955% ± 0.023%` on a **simulated** stack, ruled that `H` is not
measurable on any corpus stack, found the one subject that admits a substitute,
and deliberately did not run it. This milestone runs it.

---

## 0. The question

M67's headline is about **admission**: does the merge's gate admit the frames
that are actually in focus at each pixel? It answered that on a plant, where
`k*(x, y)` — the true per-pixel best-focus index — is known by construction. No
real stack carries a `k*`.

The `wrapped-text` brackets photograph text wrapped around a bottle. The label
region of a bottle is a **right circular cylinder**, and for a cylinder whose
axis lies along one image direction,

```text
    k*(x, y) = k*(x)        for every y
```

That is an invariant of the geometry. It needs no radius, no working distance
and no profile, so **there is nothing on that axis to tune**. It is not a fitted
model and its residual is not scored against a fit of my own.

**The question this milestone answers:** on a real capture, is the merge's
admitted-frame field constant along the cylinder axis, to within the precision
the instrument can resolve — and does M67's measured `E`-over-`A` advantage
transfer?

---

## 1. M67's three binding requirements, carried through verbatim in substance

These are conditions M67 placed on whoever ran its test. They are reproduced
here because they are constraints on the *claim*, not just on the method.

**R1 — a pass is self-consistency with an assumed geometry, not accuracy.** This
test asks whether admission respects a known invariant. It does **not** measure
absolute depth error and no sentence of the report may claim it does.

**R2 — the geometry must be fitted from the silhouette (or the text baseline),
NEVER from the index map.** Fitting the bottle's orientation from the very field
being scored is circular and would guarantee a pass. §3 below records how the
geometry was obtained and what it was obtained from.

**R3 — this test is BLIND to a bias that is constant in `y`, and that blindness
hides a failure M67 has already measured.** M67's degenerate cells ran `devmax`
**8.25–8.34 frames at `H ≈ 1`** — a large error that is nonetheless *smooth*.
The axial arm cannot see it. This is stated here, up front, rather than
discovered afterwards.

---

## 2. Two corrections and one closure, registered before the run

### 2.1 The invariant needs a cylinder, not "any surface of revolution"

M67 states the invariant holds "for any surface of revolution, whatever its
radius." **That is not true in general.** For a surface of revolution with
profile radius `r(s)` varying along the axis coordinate `s`, the nearest-point
depth is `z0 - r(s)`, which varies with `s`. Since `s` is the image `y`
coordinate under the assumed orientation, `k*` then depends on `y`.

What the invariant actually requires is **local axial translation invariance of
the profile** — a right circular cylinder, or a locally cylindrical patch. A
supplement-bottle label region is cylindrical to a good approximation, so the
test stands; but the premise is narrower than M67 wrote it, and a **taper**
appears as a smooth, low-order-in-`y` residual rather than as nothing at all.
§4.2's line fit is the direct consequence of this correction.

### 2.2 There is no silhouette in either capture — M67's circumferential arm is unrunnable

Measured from the frame-mean green luma (`src/01-geometry.py`), median DN above
black in a 64-px border strip against the label's own body median:

| stack | body | left | right | top | bottom |
| --- | --- | --- | --- | --- | --- |
| `wrapped-text-1` | 1457.6 | 80.9% | 130.5% | 132.3% | 127.6% |
| `wrapped-text-2` | 1810.2 | 85.8% | 141.8% | 123.7% | 111.6% |

Every border strip sits between 81% and 142% of the label body. **There is no
background anywhere in either frame** — the label fills the sensor edge to edge.

Consequence, registered: M67's **circumferential arm (fitted radius `R` and
centre `x_c`) cannot be run on this capture**, because its radius fit requires a
silhouette and R2 forbids taking the geometry from the index map instead.
Therefore R3's blind spot — bias constant in `y` — is **unclosable on this
data**, not merely outside this milestone's scope. No result below should be
read as bearing on it.

### 2.3 Registered *before* the run: the axis handling has no tunable parameter

Rather than fit an axis angle and score residuals about it, the scoring removes
a **per-column line in `y`** (§4.2). To first order this absorbs *exactly*: any
residual axis-angle error, any taper, and any inter-frame rotation. The
consequence is that no angle can be chosen to improve the result, because no
angle enters. The price is an extra blindness, registered in §7.

---

## 3. Geometry and drift: the design inputs, and what they came from

All of these were measured from **intensity only**, before any focus field, any
winner index or any admitted set existed for these stacks.

### 3.1 Axis direction

**E2 — text baselines (the estimator used).** Text printed on a wrapped label
runs around the circumference, i.e. perpendicular to the axis. The ink mask
(high-pass of the frame-mean image, negative tail) was rotated over a grid of
assumed axis angles and scored by the variance of its projection profile.

| stack | axis angle from image `+y` | text row pitch | ink fraction |
| --- | --- | --- | --- |
| `wrapped-text-1` | −0.2° | 375.2 plane px | 0.120 |
| `wrapped-text-2` | −0.2° | 469.0 plane px | 0.120 |

Estimator resolution is about ±0.5°: a 1° error smears a text row by
`3516 · tan 1° = 61` plane px against a glyph height of order 100 px. **The
assumed axis is the image `+y` axis exactly**, and §4.2's line fit absorbs the
residual angle.

**E1 — shading isophotes (measured, and DISCARDED, with the reason).** A
cylinder lit near the camera axis has an intensity constant along its axis, so
the structure tensor of a heavily low-passed frame-mean should point across it.
Measured anisotropy was **0.049** (stack 1) and **0.237** (stack 2) — too close
to isotropic for the direction to mean anything, because the label's own printed
layout and the scene illumination both contribute low-frequency structure that
has nothing to do with the cylinder. E1 is **not** used. Its marginal profiles
are nonetheless consistent with a vertical axis: the low-frequency swing across
`x` is 51.1% / 54.5% of the body level against 14.8% / 17.3% along `y`, a ratio
of 3.5 and 3.2.

### 3.2 Drift, rotation and breathing

Phase correlation of the high-pass detail image between the **first and last**
frame of each bracket, in a top band and a bottom band 1544 plane px apart
(`src/02-drift.py`; phase correlation is chosen because one of the two frames is
defocused relative to the other, which changes the amplitude spectrum and not the
phase ramp):

| stack | translation | rotation, whole stack | `y` magnification, whole stack |
| --- | --- | --- | --- |
| `wrapped-text-1` | < 0.02 px | +0.0002° | +0.0006% |
| `wrapped-text-2` | < 0.08 px | +0.0044° | +0.0048% |

**Registered conclusion:** breathing and inter-frame rotation are below the
resolution of this instrument and cannot contaminate the residual. The concern
that a rotation makes apparent depth vary linearly with `y` is real in principle
and absent in this data by four orders of magnitude.

### 3.3 The subject's depth gradient

From the preview sweep, the in-focus band traverses the full frame width across
the bracket, so `|dk*/dx| ~ 130 / 3516 = 0.037` frames per plane px. This is an
order-of-magnitude design input used only for the sensitivity statement in §7,
and it is the one number here that is read off a focus-related observation. It
enters no fit, no threshold and no arm.

---

## 4. Arms, reference and observables

### 4.1 Arms

Both are produced by `crates/strehl-cli/examples/m73-cylinder.rs`, which
reproduces `merge_cmd.rs`'s two-pass structure exactly — the same decode, the
same `green_luma_with_clip`, the same `FocusField::compute`, the same
`regularise`, the same `FocusStats` tie-break, the same `Gate::admits`.

| arm | election | gate | what it is |
| --- | --- | --- | --- |
| **E** | regularised field | regularised field, `DEFAULT_GATE = 4.0` | the shipped estimating merge |
| **A** | raw field | — (election only) | `ArgmaxBaseline`; M67's `A`, the arm its transferred prediction is about |
| **A′** | raw field | raw field, `4.0 · k_sd` | a *constructed* comparison merge, gate matched in noise SDs. `strehl stack` itself admits a singleton, so A′ is not a shipped path and the report says so wherever it is quoted. |

`k_sd = sd(raw)/sd(reg)` is re-measured in-crate by the crate's own
`FOCUS_NOISE_SD` procedure at every run (control K1).

### 4.2 The reference: a per-column line, and why a line

For each column `x`, ordinary least squares fits

```text
    w_hat(x, y) = a(x) + b(x) * y
```

to a winner map over the scored rows. The residual is
`r(x, y) = w(x, y) − w_hat(x, y)`.

A **line** rather than a **constant** because three distinct pieces of *geometry*
— residual axis-angle error, profile taper (§2.1), and inter-frame rotation —
all enter as terms linear in `y`, and none of the three is a merge defect. The
registered price is in §7.

**Two references, both reported, each with its bias direction declared:**

* **Reference E** — the line fit to `win_E`. Scoring both arms against it
  **favours E**, because E's residual is taken about E's own trend.
* **Reference A** — the line fit to `win_A`. Symmetrically **favours A**.

A conclusion is only claimed where it holds under **both** references. This
mirrors M67, where both arms were scored against one shared `k*`; here no shared
truth exists, so the bias is bracketed instead of eliminated.

### 4.3 Scored mask

Interior only, margin **22 plane px** = `SUPPORT_RADIUS + REGULARISER_RADIUS`,
which is where the focus field is defined without edge clamping.

* **Primary mask**: the full interior.
* **Declared secondary mask**: the interior minus every column in which more
  than 20% of pixels elect a bracket-boundary frame (`k = 0` or `k = K−1`),
  because there the argmax is censored and its residual is not a depth error.
  The excluded fraction is reported whatever it is.

### 4.4 Observables

| symbol | definition |
| --- | --- |
| `S(arm)` | `mean \|r\|` over the scored mask, in frames — the direct analogue of M67's `mean \|win − k*\|` |
| `RMS(arm)`, `med(arm)` | RMS and median of `\|r\|`, reported alongside because the mean is outlier-sensitive and arm A has outliers |
| `H_ax` | fraction of scored pixels whose **admitted set** brackets the column reference: `lo_adm ≤ w_hat ≤ hi_adm`. This is M67's `H` with the column consensus standing in for `k*`. |
| `H_null` | shape-matched null for `H_ax`: each pixel keeps its admitted span width `W = hi − lo + 1` but the interval is placed uniformly at random in `[0, K−1]`, fixed seed. M67's own null construction. |
| `span` | `hi_adm − lo_adm + 1`, the admitted-index span — the analogue of M67's `devmax` |
| `A_P` | amplitude (max − min) of the **signed** residual averaged by phase modulo the measured text row pitch `P` |

---

## 5. Controls, and the consequence if each is NOT met

| id | control | consequence if NOT met |
| --- | --- | --- |
| **K1** | the crate's `FOCUS_NOISE_SD` procedure re-run in-crate; measured regularised SD within 4 SEM of the declared constant | the run aborts; nothing below it is believable |
| **K2** | this harness's admitted-frame counter equals `Estimator::mean_n_eff()` at `f64` equality | the run aborts; the harness is not counting what the merge counts |
| **K3** | every pixel's tracked `[lo, hi]` brackets its elected winner | the run aborts; the dumped bounds are not the admitted set |
| **C1** | **axis swap, a positive control that must fail.** The whole scoring repeated with `x` and `y` exchanged: a line fit in `x` within each *row*. Depth varies strongly with `x`, so this must be far worse. Registered: `S_swap / S > 3`. | the instrument has no power on this subject; **the result is INCONCLUSIVE** and the report says the instrument does not work on this data |
| **C2** | **frame-label permutation placebo.** `w` replaced by `π(w)` for a fixed random permutation of frame labels, destroying the index↔depth ordering while preserving the per-pixel choice structure exactly. Registered: `S_perm / S > 10`. | the residual is not measuring depth ordering; **INCONCLUSIVE** |
| **C3** | **the ink-shape diagnostic — the defect this test exists to detect.** Signed residual folded by the text row pitch `P`; null is the same fold at the incommensurate pitch `P·√2`. | (this is a test, not a gate; see D1) |
| **C4** | **texture stratification.** Scored mask split by frame-mean gradient magnitude (focus-operator-free) into top and bottom terciles; `S` reported in each, with subpopulation sizes. | (diagnostic) |
| **C5** | **cross-stack replication.** Both stacks scored independently. | a headline that holds in one stack only is reported as single-capture and not generalised |

**Registered in advance about C4:** a blank patch of label carries no focus
information, so `\|r\|` will be **larger** off-ink and smaller on-ink. That
negative correlation is benign physics and is **not** the failure signature. The
failure signature is a **signed, ink-phase-locked** bias — C3 — not a variance
difference.

---

## 6. Decisions, with the rules fixed now

### D1 — does the merge admit correctly on real captures?

* **ADMITS CORRECTLY** — C1 and C2 both pass; `H_ax ≥ 0.95`; `H_ax − H_null ≥ 10`
  percentage points; C3 finds no ink-locked signature (`A_P` within 3× of its
  incommensurate null); **in both stacks**.
* **DOES NOT ADMIT CORRECTLY** — C1 and C2 both pass, and either `H_ax < 0.80`,
  or C3 finds `A_P` more than 3× its incommensurate null **and** phase-aligned
  with the ink template's own phase profile, **in both stacks**.
* **INCONCLUSIVE** — C1 fails, or C2 fails, or the two stacks land on opposite
  sides of the ADMITS / DOES-NOT boundary, or the scored mask is under 20% of
  the plane.

### D2 — the transferred prediction

M67's plant measured `mean|win − k*|` of **0.71747** for `E` and **0.81473** for
`A`; the ratio is **0.71747 / 0.81473 = 0.88063**, an 11.94% tightening.

* **T1 (ordering)** — `S(E)/S(A) < 1.000`, under **both** references of §4.2.
* **T2 (magnitude)** — `S(E)/S(A) ∈ [0.761, 0.940]`, i.e. a tightening between
  0.5× and 2× of 11.94%.

Four registered outcomes:

1. **REPRODUCES** — T1 and T2 both hold.
2. **ORDERING TRANSFERS, MAGNITUDE DOES NOT** — T1 holds, T2 fails. Registered
   reading, fixed now so it cannot be invented later: M67's plant carries uniform
   synthetic texture, while a printed label alternates high-contrast glyphs with
   blank stock. If `S(E)/S(A)` comes out **far below** 0.761, the honest
   statement is that the plant **understates** what regularisation buys, because
   the plant has no blank regions for a raw argmax to fail in. If it comes out
   **above** 0.940 but below 1.000, the honest statement is that the plant
   **overstates** it.
3. **REFUTED** — `S(E)/S(A) ≥ 1.000` under either reference. M67's asserted
   ordering does not transfer to a real capture. This is reported as a
   refutation, in the house form, without softening.
4. **INCONCLUSIVE** — C1 or C2 fails.

**Registered caveat, stated now because it weakens one direction and not the
other:** any residual common-mode geometry error is shared by both arms and
therefore compresses the ratio *toward* 1.000. A confirmed T1 is thus a
**lower** bound on the true separation, while a null result is **weak** evidence
against it. The §4.2 line fit is what keeps this compression small.

### D3 — scope of whatever D1 concludes

Fixed now: any D1 verdict is a statement about **self-consistency with an assumed
cylindrical geometry along one image axis**. It is not a statement about absolute
depth accuracy (R1), and it is blind to any admission error that is constant or
linear in `y` within a column (R3 and §7).

---

## 7. What will NOT be claimed

1. **No absolute accuracy.** `S` is a deviation from a column consensus, not from
   a true `k*`. A merge that is uniformly 8 frames wrong in a column scores
   `S = 0`. M67 measured exactly that failure mode at `devmax` 8.25–8.34 frames
   with `H ≈ 1`, and this instrument cannot see it.
2. **No claim about bias constant in `y`.** R3, and per §2.2 it is *unclosable*
   on this capture because there is no silhouette to fit the circumferential arm
   from.
3. **No claim about bias linear in `y` within a column.** §4.2's line fit removes
   it deliberately, to buy immunity from axis error, taper and rotation. This is
   an additional blindness beyond M67's.
4. **No claim about through-focus curve shape.** M67 asserted asymmetry and
   withdrew it; SYNTHESIS fact 1006 records that no corpus fact establishes it.
   M70 is measuring it independently. Nothing here bears on it and nothing here
   is built on either answer.
5. **No claim that A′ is a shipped path.** `strehl stack` admits a singleton;
   A′ is a construction for a like-for-like admission comparison.
6. **No capture is owed and no `merge.rs` change is proposed.** If the verdict is
   negative, this milestone reports it and stops.

**Sensitivity, registered:** with `|dk*/dx| ~ 0.037` frames/px (§3.3), an
uncorrected axis error of 0.5° over the full 2344-px height would inject an RMS
residual of about `0.037 · tan(0.5°) · 2344/√12 = 0.22` frames — the same order
as M67's plant residual of 0.717. That is precisely why §4.2 fits a line and not
a constant, and it is why an angle-fitting version of this test would have been
worth very little.

---

## 8. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cargo build --release --example m73-cylinder      # must print `Compiling`

cargo run --release --example m73-cylinder -- `
  --dir "D:\personal\macro\wrapped-text-1" --out experiments\M73-cylinder\out\s1
cargo run --release --example m73-cylinder -- `
  --dir "D:\personal\macro\wrapped-text-2" --out experiments\M73-cylinder\out\s2

$env:PYTHONIOENCODING='utf-8'
python -X faulthandler experiments\M73-cylinder\src\01-geometry.py
python -X faulthandler experiments\M73-cylinder\src\02-drift.py
python -X faulthandler experiments\M73-cylinder\src\03-score.py
```

`D:\personal\macro` is read-only and is never written to. The `.bin` dumps are
large intermediates and are not committed.
