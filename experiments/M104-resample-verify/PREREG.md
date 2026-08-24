# M104 — PRE-REGISTRATION: independent verification of M95's coverage-rescale fix

**Written and committed BEFORE the fix exists and BEFORE any post-fix number
exists** (rule 12). Nothing below was chosen after seeing a result. Departures
are declared in the report as departures, with the reason.

**Milestone number.** `M104` claimed after checking for a stem collision: no
`docs/research/M104*`, no `experiments/M104*`, no `M104` in any commit subject,
and zero mentions in `SYNTHESIS.md` or `docs/`. `M100` is the frontier;
`M102`/`M103` were checked and are also clear, but `M104` is the next number.
(The orchestrator warned that `M93` is held by two agents.)

**HEAD at pre-registration:** `6a8ac3078d4c11df7ac9818fda0c381dd7fd625e`
**Fix status at pre-registration: NOT LANDED.** `crates/strehl-cli/src/merge_cmd.rs:1246`
still reads *"then upsampled to keep the output dimensions"*. Verified before
writing this. Every baseline number in this milestone is therefore a genuine
*before*, not a reconstruction.

**Binary:** `.cargo-target-m98\release\strehl.exe`, rebuilt at the HEAD above.

**Role.** I am the **independent verifier**. M95 implements; M95 does not verify
its own work. My instrument chain is my own — the ruler-based optical
magnification measurement built and validated in M98 — and is deliberately *not*
a re-run of the orchestrator's `resample_budget.py`, which is spectral and
synthetic. Two chains that agree are worth more than either alone; two chains
that are the same chain are worth one.

---

## 0. What is being fixed, and why I am the right instrument

`fit_to_cover` scales the field of view by `k ≤ 1` so that every frame covers
every output pixel, **and then upsamples back to the original output
dimensions**. The render is therefore an *interpolated enlargement* of the
optical image by `1/k`, at every pixel and every gate.

| stack | `k` (MEASURED, render logs) | upsample |
|---|---:|---:|
| `bee-3-cpl`, 299 frames | 0.9315 | +7.35% |
| `flat-on-ruler-cpl`, 79 frames | 0.9708 | +3.01% |
| `112MSDCF`, 79 frames | 0.9760 | +2.46% |

M95's change: emit the cropped region at its **native sampling** (`bee-3-cpl`:
~6550 × 4367 full-res, ~3275 × 2184 binned) instead of stretching it back to
7032 × 4688.

**Why the ruler is the right verifier, and why the obvious instruments are not.**

1. **The output dimensions change.** Any tile or ROI mapping that assumes
   7032 × 4688 will silently mis-register after the fix and read as blur. A
   millimetre ruler does not care about pixel dimensions: the tick pitch is a
   physical constant, so the comb frequency *in the render* measures the
   sampling directly, and a change of dimensions with unchanged sampling reads
   as **no change**. That is exactly the invariance the trap needs.
2. **A "sharper" verdict from a global gradient-energy metric is inadmissible.**
   Fact 1273 records its **third independent death** — M97's tile-wise
   band-limited detail metric was disqualified by its own responsiveness control
   and produced signs **inconsistent between subjects**. Discipline 605 and fact
   1235 both stand **RETRACTED** (fact 1250), which — per discipline 633 — is a
   stronger statement than absence, not a weaker one: it forecloses re-deriving
   the claim. **No gradient-energy metric appears in this milestone.**
3. **Magnification reads as sharpness** (discipline 606; fact 1250 is the
   orchestrator making that error a second time in one night, at 100%). Any
   pixel-space comparison between the pre-fix and post-fix renders is
   contaminated *by the very quantity being fixed*. Object-space is not
   optional here; it is the whole point.

---

## 1. Hypotheses, with falsifiers, fixed before the fix exists

| # | Hypothesis | Falsifier |
|---|---|---|
| **H1** | The fix removes the resample. My ruler's optical magnification instrument, comparing the registered render against `STREHL_ALIGN=0`, reads **1.000** after the fix where it reads ~1.030 before. | post-fix magnification differs from 1.000 by **> 2 SE**, in either direction |
| **H2** | The fix **recovers resolved detail** in object space — modulation at matched physical tick frequency rises. | post-fix object-space modulation ratio (post ÷ pre) is **< 1.000 − 2 SE** |
| **H3** | The fix does **not** change the field of view, only the sampling of it. The same physical extent of ruler is present before and after. | the subject extent changes by **> 1%** |
| **H4** | The high-band deficit of the merge against an unresampled reference falls, in the direction and roughly the magnitude the orchestrator predicts (**+0.3693 → ~+0.1301 dex**). | it falls by **< 50%** of the predicted 0.2392 dex drop, or **overshoots** past zero (see §3, `OVERSHOOT`) |

I expect H1 and H3 to survive and H2 to be the one that disappoints, because
removing an upsample recovers *sampling*, not *optics*, and the ruler comb on
`flat-on-ruler-cpl` sits at 0.047–0.206 cyc/px where a 3% resample costs little.
**On `bee-3-cpl`, where `k = 0.9315`, the effect is 2.4× larger and that is where
the owner's photograph lives.**

---

## 2. Instruments — exact, with failure directions (rule 18)

All measurement is on the **binned linear camera-native** output. `--srgb` and
`--demosaic` are used only for anything a human looks at, and **no number is
measured on them**.

| symbol | definition | can be fooled by |
|---|---|---|
| `f₀` | 2-D spectral peak of the ruler tick comb within `f ∈ [0.03, 0.40]` cyc/px, half-plane so the conjugate is not double-counted, found per 512² ROI | a subject with a stronger periodic structure than the ruler; guarded by the `INERT` S/B gate |
| `mag` | `f₀(reference) / f₀(test)` — the **optical magnification** of test relative to reference. **Dimension-agnostic by construction**: it is a ratio of frequencies, not of sizes. | nothing in the pixel-count domain; it *can* be fooled by the two ROIs looking at different parts of a non-uniform ruler, which is why ROIs are paired by index and the comb is uniform |
| `M` | comb modulation: peak disc power minus the median of its two sidebands, square-rooted, **divided by the ROI mean level** so it is a modulation *depth* and is invariant to exposure and to scale. **This normalisation is the defect M98 §5.3 declared in its own `s8`, fixed here.** | a comb not resolved at all — guarded by `INERT` |
| `M_obj` | `M` evaluated at the **same physical tick frequency** in both renders (each render's own fundamental *is* that frequency), so magnification divides out | — |
| `D_hi` | mean `log10` band power over `f ∈ [0.30, 0.48]` cyc/px, **magnification-compensated** by evaluating the band on the object-frequency axis | a band chosen after seeing the answer — it is fixed here, and it is the orchestrator's band deliberately, so H4 is comparable |

**Rule 18, stated for the headline.** Removing an upsample makes the render
*smaller in pixels*. Every per-pixel metric will therefore report *higher*
frequencies and *narrower* edges **for free**, with no optical improvement
whatsoever. **That bias runs toward "the fix worked."** It is precisely the
error that produced facts 1235 and 1237 and their retraction. Every headline in
this milestone is therefore in **object space**, and any pixel-space number is
reported as a diagnostic and labelled as one.

### Reference arm

The unresampled reference is **`STREHL_ALIGN=0` at gate 0**: strehl's own
selector output, same decoder, same binning, same demosaic-free path, **no warp
and no rescale**. This is deliberately *not* a rawpy decode — using the same
decoder on both sides removes a cross-decoder confound that the orchestrator's
chain carries, and makes my chain independent of theirs rather than a copy.

### ROI grid

24 ROIs of 512² on a procedural 6×4 lattice: centre `(W(2i+1)/12, H(2j+1)/8)`,
clamped inside the frame. **Defined as a fraction of the emitted dimensions**,
so it follows the frame when the dimensions change — which is the trap, handled
by construction rather than by remembering.

---

## 3. Bars — numeric, fixed in advance, PASS/FAIL

Primary stack for H1–H3: **`flat-on-ruler-cpl`** (it is the only stack with an
a-priori physical scale). Primary stack for H4: **`bee-3-cpl`** (the owner's
photograph, and the largest `k`).

| bar | quantity | PASS | FAIL |
|---|---|---|---|
| **B1** | post-fix `mag` (registered vs `STREHL_ALIGN=0`), `flat-on-ruler-cpl` | \|`mag` − 1.000\| ≤ 2 SE **and** the pre-fix 1.03008 excluded at ≥ 2σ | otherwise |
| **B2** | post-fix emitted dimensions, `flat-on-ruler-cpl` binned | within ±4 px of `round(k · pre)` = **3417 × 2276** | otherwise |
| **B3** | post-fix emitted dimensions, `bee-3-cpl` binned | within ±4 px of **3275 × 2184** | otherwise |
| **B4** | object-space modulation ratio post ÷ pre, matched tick frequency | ≥ 1.000 − 2 SE | < 1.000 − 2 SE |
| **B5** | subject extent (ruler ticks spanned by the frame), post ÷ pre | within **1%** of 1.000 | otherwise |
| **B6** | `D_hi` deficit of merge vs `STREHL_ALIGN=0` gate 0, `bee-3-cpl`, object-space | falls by **≥ 50%** of the predicted 0.2392 dex | falls by < 50% |
| **B7** | `OVERSHOOT` | the post-fix deficit does **not** go below **+0.02 dex** | it does — see below |

**B7 is the bar the orchestrator specifically asked for, and it is a FAIL, not a
celebration.** If the deficit lands *better* than the rescale alone can explain,
then something other than the rescale changed in the same commit, and the
measurement no longer isolates the fix. The registered response is: **report
FAIL-OVERSHOOT, do not certify, and name what else moved.** A verification that
cannot fail upward is not a verification.

**Verdict rule.**
- **PASS** — B1, B2, B3, B5 all pass, **and** B6 passes, **and** B7 does not trip.
- **PASS-WITH-CAVEAT** — B1, B2, B3, B5 pass but B4 or B6 misses. The fix did
  what it says (the resample is gone) but did not buy what was predicted. That
  distinction matters and will be reported as itself.
- **FAIL** — any of B1, B2, B3, B5 fails, or B7 trips.

**What would make me say the fix failed even though the picture looks better:**
B1 passing while B5 fails — i.e. the magnification is gone but the field of view
moved — means the crop changed rather than the resample being removed, and the
two are not the same operation. I will report that as FAIL.

---

## 4. Controls, each with the input that makes it fail (rule 20, rule 39)

| # | control | bar, at an **exact** value | the input that makes it fail |
|---|---|---|---|
| **SELF** | Feed the instrument the **same file twice**. | `mag` must read **exactly `1.000000`**. Not "~1.0". | **NCX** below |
| **NCX** | *The negative control made to go red.* Resample one copy by **exactly 1.030000** with the same 4-tap kernel and re-run `SELF`. | `SELF` must read **`1.030000 ± 0.004`** and go **RED**. If it still reads `1.000000`, the instrument is not reading the file and every magnification claim here is void. | by construction |
| **DOSE** | Plant magnifications **1.000 / 1.010 / 1.030 / 1.075** and recover each. | monotone, each within **±0.004** of truth; the 1.075 rung is `bee-3-cpl`'s actual `1/k` | a non-monotone or compressed response means the instrument cannot resolve the effect being verified |
| **DIM** | *The dimension trap, converted into a control.* Crop the pre-fix render to **different output dimensions at unchanged sampling** and re-measure. | `mag` must read **`1.000 ± 0.004`** despite the dimensions changing | if it moves, my chain has the exact defect the orchestrator warned about, and Phase 2 is void |
| **PL** | *Placebo.* Swap which render is called reference and which test. | `mag` must invert to **`1/x` within 1e−6** | any other change is a harness bug |
| **INERT** | Rule 13. The tick comb must clear its sidebands by **≥ 3×** in the reference render. | S/B ≥ 3.0 on ≥ 8 ROIs | if not, the ruler is **no evidence**, not a null |

`scripts/corpus_lint.py` must exit 0 before the milestone closes, run as its own
call, never chained to a commit (discipline 556).

---

## 5. Registered predictions, to be scored (so being wrong is visible)

| # | prediction |
|---|---|
| (a) | post-fix `mag` on `flat-on-ruler-cpl` lands in `[0.998, 1.002]` |
| (b) | B4 (object-space modulation) **passes but is boring** — the ratio lands in `[1.000, 1.010]`, because a 3% resample at 0.047–0.206 cyc/px costs almost nothing |
| (c) | the pre-fix object-space price of the rescale on `flat-on-ruler-cpl` is **under 0.02 in modulation ratio**, i.e. under 2% |
| (d) | `bee-3-cpl`'s post-fix binned dimensions are **3275 × 2184** exactly |
| (e) | B6 passes and the residual post-fix deficit lands in `[0.08, 0.18]` dex, bracketing the orchestrator's 0.1301 |

---

## 6. What I will not do

- Not edit `merge_cmd.rs` (contended, and it is M95's), nor `merge.rs`,
  `through_focus.rs`, `align.rs`, `warpmap.rs`, `robust.rs`, `noise.rs`,
  `profile.rs`, `align_cmd.rs`, `lib.rs`, `main.rs`.
- Not use any whole-frame or tile-wise **gradient-energy** sharpness metric.
  Three independent deaths (fact 1273); settled corpus.
- Not accept a pixel-space "sharper" reading as evidence. Removing an upsample
  makes every pixel-space metric improve for free.
- Not write to `D:\personal\macro` or `D:\macro-dark-frames`. Render scripts
  assert the full recursive listing (name, size, mtime) before and after.
- Not push. Path-scoped commits only.
