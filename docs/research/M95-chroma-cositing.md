# M95 — Chroma co-siting: the binned render misregisters red and blue, and a fix

**Milestone:** M95 (chroma arm). The merge-vs-frame arm is
[`M95-merge-vs-frame-sharpness.md`](M95-merge-vs-frame-sharpness.md); this report is
delta-only against it and its candidate facts continue at **P18** so the two can be
folded without a numbering collision.

**Subject:** `D:\personal\macro\bee-3-cpl`, 299 frames, ILCE-7CM2 +
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, f/5.6, ISO 100.
**Code:** `experiments/M95-chroma-cositing/`.
**Images:** `C:\dev\strehl-out\M95-chroma-cositing\`.
**Ships in:** `crates/strehl-cli/src/image_out.rs` (a file I own).

---

## Headline

strehl's binned `--srgb` render placed **red and blue half a binned pixel apart on the
diagonal**, on every edge in every frame, since before the corpus existed. It is not a
subtle statistical effect: in a 2×2 RGGB quad the two greens straddle the quad centre
and average onto it exactly, but red sits at one corner and blue at the opposite one,
and all three were written into a single output pixel as though they were co-sited.

Measured on the real render against an independent reference: red was displaced
**0.5818** binned px and blue **0.4557**. Resampling red by `(+0.25, +0.25)` and blue by
`(-0.25, -0.25)` onto green's grid removes **91.6 %** and **93.2 %** of that, and drops
chroma RMS at luminance edges from **1286.2 DN to 419.5 DN**, a **67.4 %** reduction.

**This is fixed, not merely reported.** The correction is in `image_out.rs`, it ships by
default on the `--srgb` path, and the byte-frozen measurement path is proven untouched by
SHA-256 identity against the pinned binary.

**Scope, stated up front so the headline is not over-read:** this is a *colour* defect,
not the luminance softness the owner is looking at. Green — which carries essentially all
the luminance detail in a Bayer sensor — is not moved by this and was never misregistered.
This makes edges cleaner and removes colour fringing. **It does not make the picture
sharper, and I did not measure sharpness on this axis.** See §9.

---

## 1. The question, and why this arm exists

The merge-vs-frame arm answered the milestone's primary question decisively and
negatively: at `--gate 0` the merged output is *byte-identical* to the frame it elected,
so the combination stage destroys no detail (P1). The orchestrator then asked for
something narrower and more immediately useful:

> If you find a defect in the output path that is cheap to fix and visibly improves the
> render, fix it — do not merely report it. You own `image_out.rs`, `color.rs`,
> `demosaic.rs`.

This arm is the result of taking that seriously. It is a hunt through the output path
for defects, and it found one.

### 1.1 A hypothesis that was wrong, recorded because it cost time

My first hypothesis was that the `stack` subcommand had no `--demosaic` and therefore
always shipped the binned path with no way out. **That was wrong.** `Stack` is aliased to
`merge` and routes through `merge_cmd.rs`, which has `--demosaic`; `stack.rs` is the
retired `argmax-baseline` negative control, not the shipping path. I checked
`cargo test -p strehl-core --lib demosaic` (9/9 pass) and read the mosaic assembly in
`merge_cmd.rs`, which correctly interleaves all four CFA accumulators. Nothing wrong
there. The defect was one level down, in the *binning geometry*, not the demosaic.

---

## 2. The defect, derived

Take the quad centre as the origin and **one binned output pixel** as the unit of length.
A 2×2 RGGB quad occupies exactly one binned pixel, so its corners are at ±0.5 sensor px
= ±0.25 binned px from the centre on each axis.

`merge_cmd.rs` builds each binned pixel as:

| output channel | source | sensor site | offset from quad centre, binned px |
| --- | --- | --- | --- |
| R | `val(CfaPlane::R, i)` | (2px, 2py) | (−0.25, −0.25) |
| G | `gmean(i)` = mean of G1, G2 | (2px+1, 2py) and (2px, 2py+1) | **(0, 0)** — the two straddle the centre |
| B | `val(CfaPlane::B, i)` | (2px+1, 2py+1) | (+0.25, +0.25) |

Green is centred *for free*, because averaging two samples on opposite corners of a square
lands on its centre. Red and blue are not, and they are displaced in **opposite**
directions, so their separation is 0.5 binned px along the diagonal — `0.5 × √2 = 0.7071`
px of total displacement between them.

Writing all three into one pixel as if co-sited puts a signed colour swing on both sides
of every luminance edge. That is what colour fringing *is*.

The correction is to resample red at `(+0.25, +0.25)` and blue at `(−0.25, −0.25)`, in
linear light, before the colour matrix. Before is load-bearing: the matrix mixes channels,
so co-siting after it would be resampling a blend of three already-misregistered planes.

---

## 3. Pre-registered bars — and the sign error in them

The pre-registration is frozen in `experiments/M95-chroma-cositing/PRE-REGISTRATION.md`,
committed as `f91bc4a` **before** any displacement was computed.

**Registered bars:**

- **Confirm the defect** if the measured R↔B separation is `0.5 ± 0.1` binned px per axis
  and green reads `< 0.05` px against a co-sited reference.
- **Refute it** if the separation is `< 0.15` px per axis, or if green reads as large as
  red and blue (which would mean the instrument is measuring something else).
- **Ship the fix** only if all four hold: red and blue misregistration falls
  substantially; green is unchanged; the correction applied backwards is markedly worse;
  and the resample's own blur does not account for the gain.

**Disclosure — the frozen pre-registration has a sign error.** It predicts red at
**+0.5** relative to blue; the truth is **−0.5**, i.e. red is at the *negative* corner.
I settled the sign by construction rather than by re-deriving the algebra — control C6
builds synthetic RGGB data whose answer I made, and it read `R→B = (−0.5000, −0.5000)` on
5/5 seeds. **The magnitude bar is unaffected and the verdict does not turn on the sign**,
but the frozen document is wrong on that point and the record should say so rather than
quietly using the corrected version. This is the second time this session that settling a
convention *by construction* caught an error that re-derivation had already made once.

---

## 4. The instrument, and the four times it failed

The metric is a **sub-pixel shift estimator**: a least-squares fit of a phase ramp to the
cross-power spectrum of two windows, written from the definition rather than called from a
library. Discipline 594 requires that a null be shown capable of saying otherwise, so
every control below was run, and the ones that failed are here in full because they are
the reason the final number is trustworthy.

### 4.1 Controls the instrument passed

| id | what it plants | bar | result |
| --- | --- | --- | --- |
| C1 | shifts of 0, ±0.25, ±0.5, (−0.25, +0.75), (0.4, 0.1) | recover to 0.03 px | worst error **0.00543 px**; the zero-shift null reads **2.07e-16 px** |
| C2 | independent noise, no shift | reads ~0 | worst **4.45e-18 px** |
| C3 | cross-check against `skimage.phase_cross_correlation` | agree to 0.05 px | agree to **0.001617 px** worst |
| C5 | shift planted by frequency-domain phase ramp vs `scipy.ndimage.shift` | phase ramp must not blur | phase ramp preserves HF **0.9998–0.9999×**; `ndimage` order-3 **0.9891–0.9941×** — so `ndimage` was rejected as a planting tool |
| C6 | synthetic RGGB mosaic, binned; truth by construction | exact | **R→B (−0.5000, −0.5000)**, R→G (−0.2500, −0.2500), 5/5 seeds |
| C8 | large shift (3.20, −1.70) after the robust rewrite | recover exactly | worst planted error **9.31e-09 px**, null **2.13e-16 px** |
| C10 | synthetic co-sited comparison, truth by construction | exact | R **(+0.2500, +0.2500)**, G **(−0.0000, −0.0000)**, B **(−0.2500, −0.2500)**, 5/5 seeds |
| N5 | the reference registered against **itself** | ~0 | R **0.00000**, G **0.00000**, B **0.00000** px |

### 4.2 Failure 1 — S1: the fit residual was larger than the effect

The first run on real data returned a fit residual of **1.0736 px**, against an effect of
0.25 px. Two causes, both diagnosed rather than tuned away:

1. A naive phase-ramp fit **wraps** once `|d| · f_max > 0.5`, which at `f_max = 0.25`
   means above roughly 2 px, and it returns a confidently wrong number without announcing
   it.
2. Selecting ROIs by "detail" admits defocused regions whose high-frequency content is
   noise, not structure.

Fixed by adding a coarse de-ramp before the fine fit, and a coherence gate.

### 4.3 Failure 2 — C7 shows the naive estimator was genuinely broken

This is the control that justifies the rewrite rather than merely asserting it. Planting
a known shift and reading it with both estimators, at two ROIs per plant:

| planted | naive reads (ROI 1, ROI 2) | robust reads |
| --- | --- | --- |
| 0.5 | +0.4996, +0.4999 | 0.5000 |
| 1.5 | +1.4988, +1.4998 | 1.5000 |
| 2.5 | +2.4981, **+1.2227** | 2.5000 |
| **4.0** | +0.8986, **−0.2101** | 4.0000 |

The naive estimator does not degrade gracefully; at 4.0 px it reports **−0.21** with no
signal that anything is wrong, and the two ROIs disagree wildly at the same planted shift.
Worst naive error **4.2101**, worst robust error **3.89e-09**.

### 4.4 Failure 3 — C9: my coherence gate was identically 1

I added a coherence gate and it passed everything, including pure noise. The reason is
algebra, not tuning: for a single pair,

```
gamma = |conj(A)*B| / (|A|*|B|) = |A|*|B| / (|A|*|B|) = 1
```

**identically, for every input.** A gate that cannot reject is not a gate. Fixed by
averaging the cross- and auto-spectra over a frequency neighbourhood
(`uniform_filter(..., mode="wrap")`) before forming `γ² = |⟨Sxy⟩|² / (⟨Sxx⟩⟨Syy⟩)`.
After the fix: real image pairs read **0.99934–0.99947**, independent noise
**0.10939–0.12155**.

### 4.5 Failure 4 — S2: registering red against blue is not a valid instrument

With a working estimator I measured red against blue directly on real data. Per-ROI
standard deviation was ≈ 0.5 px and the two pairs disagreed on the constant. The cause is
not noise: **on a coloured subject, red and blue are different images, not shifted copies
of one image.** The fit was measuring scene chroma. That arm was retired as a failure, not
salvaged.

### 4.6 The redesign that worked

Compare **each channel to itself**, against a reference in which all three channels are
already co-sited: the demosaiced render, box-averaged 2×2 onto the same grid. Green then
becomes a *free internal null* — it should read zero, and any offset it reads is
instrument error that applies equally to red and blue.

---

## 5. The measurement

Real data, 35/35 ROIs coherent on both pairs, displacement in binned px against the
co-sited reference:

| channel | frame-183 | merged, gate 0 |
| --- | --- | --- |
| R | (+0.2316, +0.2344), sd (0.019, 0.026) | (+0.2274, +0.2441), sd (0.031, 0.036) |
| **G (internal null)** | **(+0.0012, +0.0016)**, sd (0.004, 0.005) | **(−0.0001, +0.0005)**, sd (0.003, 0.004) |
| B | (−0.2362, −0.2365), sd (0.014, 0.018) | (−0.2301, −0.2441), sd (0.023, 0.027) |

R↔B separation **0.6637** and **0.6691** binned px, against **0.7071** predicted. The
green null sits at **0.00161** and **0.00049** px (largest of the two axes) against red
signals of 0.2344 and 0.2441 px — a **146×** and **498×** separation, which is what
licenses reading the red and blue numbers as real.

**The ~6 % deficit against prediction is not explained to my satisfaction.** The plausible
account is that the reference is not perfectly independent: Malvar-He-Cutler interpolates
red and blue from neighbouring greens, which pulls them toward green's position and
shrinks the apparent displacement, and the box-average adds blur. That is an argument, not
a measurement, and §9 lists it as a live falsifier.

---

## 6. Does correcting it actually improve the picture?

### 6.1 The benefit, and the control that was empty

Correction: separable 4-tap **Keys cubic** (`a = −1/2`; Keys, IEEE ASSP-29(6), 1981),
chosen over bilinear because at `t = 0.25` bilinear has a measurably wider kernel and this
correction must not cost more sharpness than the misregistration it removes.

| variant | frame-183 regR / regB | merged regR / regB | edge chroma, merged |
| --- | --- | --- | --- |
| as shipped | 0.3298 / 0.3343 | 0.3345 / 0.3359 | 585.40 DN |
| **co-sited** | **0.0129 / 0.0110** | **0.0363 / 0.0266** | **232.31 DN** |
| N1 backwards | 0.6582 / 0.6645 | 0.6727 / 0.6732 | 1024.53 DN |
| N3 blur-only | 0.3298 / 0.3343 | 0.3345 / 0.3359 | 585.40 DN |

**N1 passed:** applying the correction backwards roughly doubles the error, so the metric
is measuring registration and its sign is right.

**Failure 5 — N3 was vacuous.** It was meant to be a blur-only control: same kernel, zero
shift, to show the gain came from co-siting rather than from resampling. It returned
digits *identical to as-shipped in every column*, which is the signature of a control that
did nothing. It did nothing for a real reason: **the Keys kernel at `t = 0` is exactly
`[0, 1, 0, 0]`, the identity.** For a 4-tap interpolator the blur is inseparable from the
shift, so this control cannot exist as designed. It was replaced, not quietly dropped.

### 6.2 N4 — the replacement control

Apply the same correction to **green**, which does not need it. If the metric merely
rewards resampling, green improves too.

| pair | green before | green after a +0.25 px shift |
| --- | --- | --- |
| frame-183 | 0.0060 | **0.3196** |
| merged, gate 0 | 0.0050 | **0.3312** |

Green gets **53–66× worse**. The metric is not rewarding resampling per se.

### 6.3 C11 — removing the circularity

The reference is the demosaiced render, and the demosaic co-sites its channels. So
"co-sited output resembles the reference more" is at risk of being true *by construction*.
C11 removes the demosaic from the loop entirely: a synthetic band-limited RGB scene,
mosaicked to RGGB, binned both ways, scored against the true 2×-downsampled scene. Truth
by construction, no interpolator anywhere.

| seed | chroma error as shipped | co-sited | reduction |
| --- | --- | --- | --- |
| 21 | 0.16571 | 0.05151 | 68.9 % |
| 22 | 0.16615 | 0.05172 | 68.9 % |
| 23 | 0.16599 | 0.05174 | 68.8 % |
| 24 | 0.16631 | 0.05175 | 68.9 % |
| 25 | 0.16640 | 0.05179 | 68.9 % |

Mean ratio **0.3113** against a pre-registered bar of `< 0.75`. The benefit is not an
artifact of the reference.

---

## 7. The fix, and its certification

### 7.1 Where it lives, and why that is safe

`write_binned` is reached from exactly two call sites, `merge_cmd.rs:2827` and
`stack.rs:1027`, and **both are inside `if let Some(m) = matrix`**. `merge_cmd.rs:2735`
sets `matrix` to `Some` **only under `--srgb`**. So `write_binned` is the "for looking at"
path by construction; the byte-frozen measurement path writes through `write_rgb16` and
never enters it. The fix therefore lands entirely inside a file I own, needs no patch to
anything shared, and cannot move a corpus number.

That is an argument from reading source. §7.4 measures it.

### 7.2 The change

`crates/strehl-cli/src/image_out.rs`, +245 −5. New: a `COSITE_SHIFT` constant, a
`keys_weights` kernel, a separable `resample_shift`, and a `develop_binned` split out of
`write_binned` so the correction is testable on values rather than on a file.

```rust
const COSITE_SHIFT: f32 = 0.25;

#[inline]
fn keys_weights(t: f32) -> [f32; 4] {
    const A: f32 = -0.5;
    let (t2, t3) = (t * t, t * t * t);
    [
        A * (t3 - 2.0 * t2 + t),
        (A + 2.0) * t3 - (A + 3.0) * t2 + 1.0,
        -(A + 2.0) * t3 + (2.0 * A + 3.0) * t2 - A * t,
        -A * (t3 - t2),
    ]
}

fn develop_binned(width: usize, height: usize, rgb_lin: &[f32], dev: &Develop) -> Vec<u16> {
    assert_eq!(rgb_lin.len(), width * height * 3);
    let (src, _) = rgb_lin.as_chunks::<3>();

    let plane = |c: usize| src.iter().map(|p| p[c]).collect::<Vec<f32>>();
    let d = COSITE_SHIFT;
    let red = resample_shift(&plane(0), width, height, d, d);
    let blue = resample_shift(&plane(2), width, height, -d, -d);

    let mut rgb = vec![0u16; width * height * 3];
    let (dst, _) = rgb.as_chunks_mut::<3>();
    dst.par_iter_mut().enumerate().for_each(|(i, out)| {
        *out = develop_pixel([red[i], src[i][1], blue[i]], dev);
    });
    rgb
}
```

Cost: two extra f32 planes (≈ 33 MB each at 3516×2344) and 8 multiplies per pixel per
plane, rayon-parallel. Measured render time for the shipped configuration went from
**34 s to 47 s** at `--gate 0`; the binned+matrix write is a small share of a run
dominated by decode.

### 7.3 Unit tests, and the four defects planted to prove they work

Four new tests in `image_out.rs`. All 8 tests in the module pass, including the
pre-existing tripwire
`the_default_development_is_the_identity_the_corpus_was_measured_on`. Full suites:
**59/59** `strehl-cli`, **238/238** `strehl-core`.

A passing suite is not evidence unless it could have failed
(`experiments/M95-chroma-cositing/src/r1_mutation_controls.py`):

| id | planted defect | named test | caught? |
| --- | --- | --- | --- |
| R1 | correction applied backwards | `..._separates_red_from_blue` | **RED** |
| R2 | green resampled too (the "it just blurs everything" defect) | `..._separates_red_from_blue` | **RED** |
| R3 | shift of 0.5 instead of 0.25 | `..._separates_red_from_blue` | **RED** |
| R4 | kernel weights not summing to 1 | `a_constant_plane_is_invariant...` | **RED** (plus 3 others) |

**4/4 caught by the named test.** Restore reproduced the original SHA-256 exactly and the
restored build re-ran green — which is what proves the rebuild actually happened rather
than cargo skipping it on a preserved mtime.

Each mutation is anchored on a **unique full line** and a miss is a hard error, not a
silent skip.

### 7.4 The byte-frozen proof, measured

`experiments/M95-chroma-cositing/src/r2_byte_frozen.py` renders the corpus's default-path
file with the new binary and compares SHA-256 against the pinned binary's output:

```
pinned binary (arm 1) : 895e458dd8f4722de0dac57d5f2797b8bbcc1492c65462f526c13e69f5ce8288
new binary            : 895e458dd8f4722de0dac57d5f2797b8bbcc1492c65462f526c13e69f5ce8288
```

**Identical.** Its power control — the same pair rendered *with* `--srgb`, where the bytes
must differ — returns `76765a1f…` against `6f1cec08…`. They differ, so the identity above
is a measurement and not a demonstration that I ran one binary twice.

---

## 8. The shipped result

`strehl stack D:\personal\macro\bee-3-cpl --gate 2.0 --srgb`, alignment on — the
configuration that ships. "Before" is a binary built from **this same tree** with only
`COSITE_SHIFT` set to 0, so the two differ by nothing else.

| | red | green | blue | chroma RMS | chroma RMS at edges |
| --- | --- | --- | --- | --- | --- |
| before | 0.5818 px | 0.0764 px | 0.4557 px | 537.8 DN | 1286.2 DN |
| **after** | **0.0490 px** | **0.0084 px** | **0.0310 px** | **210.9 DN** | **419.5 DN** |
| removed | 91.6 % | 89.0 % | 93.2 % | 60.8 % | 67.4 % |

Green improves too, by 89 %, and that is **not** because the fix touches green. Under
`--srgb` the camera matrix mixes channels, so output green is
`m[1][0]·R + m[1][1]·G + m[1][2]·B` and was being contaminated by two misregistered
planes. Removing their misregistration cleans up output green as a side effect.

**Deliverable image:** `C:\dev\strehl-out\M95-chroma-cositing\M95-chroma-cositing-before-after.png`
— BEFORE / AFTER / REFERENCE at 5× nearest-neighbour, with chroma-only versions below.
The crop is chosen by **green-channel gradient energy alone**, which is blind to the
effect because green is the one channel the fix does not touch. No sharpness number
appears on any panel.

### 8.1 Failure 6 — the control that caught my own wrong diagnosis

The first version of §8 compared the **pinned** binary against the new one, with a control
demanding that output green be bit-identical. **It failed.** I diagnosed it as the pin
predating M86's live work in `align.rs`, built a control binary from the current tree, and
re-ran. **It failed again, with the same diff magnitudes to the digit** — 17119 and 13842
DN — which is the signature of a hypothesis that was never the cause.

Two things came out of chasing it:

- **C12 (passed):** the zero-shift binary reproduces the pinned binary's `--srgb` output
  **byte for byte** at `STREHL_ALIGN=0`, proving both that `COSITE_SHIFT = 0` is exactly
  the old arithmetic and that on that path my edit is the only difference between the pin
  and HEAD.
- **C13:** the pin and the current tree render the shipped configuration **byte-identically**
  (`00e87214…` both). So M86's work had not changed this render at all and **my diagnosis
  was simply wrong.**

The real cause is in §8's second paragraph: the matrix mixes channels, so output green
*must* move. **The control was mis-specified, not the code.** The claim "green is
untouched" is about the input to development, and it cannot be tested on a path that has a
matrix in it.

### 8.2 The corrected control, and its power

`N2'` — green on pixels where red and blue did not change — was **vacuous**: only 1357 of
8,241,504 pixels qualify, because the correction touches nearly everything. Reported as a
failure rather than as a pass.

`N2''` (`s9_camera_linear_null.py`) makes the claim in the space where it lives. The
pipeline is invertible on unclipped pixels, so undoing the sRGB curve and multiplying by
`inv(M)` recovers camera-linear RGB. `M` is reconstructed by re-implementing
`color::camera_to_srgb` from the XYZ→cam matrix the binary **printed during this
session's render**, not copied from a note. 916,468 of 916,504 sampled pixels usable.

| plane | RMS difference, camera-linear (full scale 1.0) |
| --- | --- |
| R | 0.002567 |
| **G** | **0.000004** |
| B | 0.002704 |

**Green is 738× quieter than chroma on identical machinery.** The power control is the
point: an inversion this lossy could read "no difference" simply by being blunt, and the
red and blue columns show it is not. Green carries no independent change; residual green
is the 16-bit round trip, not the plane.

---

## 9. Scope: what this does **not** cover

1. **This is not the softness the owner is looking at.** Green carries essentially all the
   luminance detail on a Bayer sensor, green was never misregistered, and the fix does not
   move it. This removes colour fringing and cleans edges. **I did not measure luminance
   sharpness on this axis and claim no sharpness improvement.**
2. **It does not touch the cutout halo or the ghost hair echoes** the orchestrator
   identified as the dominant visible defect. M87 owns those and I stayed off them.
3. **It only affects `--srgb`.** Every corpus number, and the default render, are
   bit-for-bit unchanged (§7.4). A user measuring on the default path sees nothing.
4. **It does not affect `--demosaic`.** Malvar-He-Cutler already estimates every channel
   at every site, so its output is co-sited by construction. `write_demosaiced` is
   untouched.
5. **The ~6 % deficit** between the measured R↔B separation (0.6637 / 0.6691) and the
   geometric prediction (0.7071) is *attributed* to the reference's own interpolation and
   the box-average, and that attribution is **not measured**.
6. **One subject, one stack.** All real-data numbers are from `bee-3-cpl`. The geometry is
   universal for RGGB and the synthetic control C11 is subject-free, but the DN magnitudes
   are not portable.
7. **Border pixels** are clamped rather than interpolated, which is correct for a
   partition-of-unity kernel on a constant but is an approximation on a gradient. The
   affected band is 2 px wide.
8. **The election-quality question remains open** from arm 1: I proved the merge faithfully
   emits *the frame it chose*, never that it chooses the *best* frame. That oracle test was
   designed and never run.

### 9.1 What would falsify this

- **A capture of a neutral, achromatic, high-contrast edge target** would settle §9.5
  outright. On a scene with no chroma, the entire measured R↔B separation must be the
  geometric 0.7071 px, because there is no scene colour for the estimator to confuse it
  with. If it still reads ~0.66, my attribution to the reference's interpolation is wrong
  and something else is shrinking it. **This is the capture I would ask for** (§11).
- If an independent co-sited reference — not derived from a demosaic — showed red and blue
  *already* aligned on the binned render, C11 would have to be wrong about its own
  construction. C11 makes that unlikely but not impossible.
- If the Keys resample's blur cost more high-frequency luminance than the misregistration
  removed, the fix would be a bad trade. It cannot: it does not touch green. But if a
  future change co-sited green too, that trade would become live and would need measuring.

---

## 10. Renumber and ownership

I was dispatched as **M93**, which was already held by another agent
(`docs/research/M93-election-gate.md`, commit `9a17d64`). The orchestrator reassigned me to
**M95**. The renumber was executed as a forward `git mv` in commit `45ba18b` — never a
history rewrite — and is recorded in §0 of the merge-vs-frame report. `C:\dev\strehl-out\M93-out`
and `M93-frames` were **deliberately left named** because the orchestrator's own
`experiments/ORCH-drift-check/m93pair.py` reads them by absolute path.

Files modified this arm: `crates/strehl-cli/src/image_out.rs` only. `color.rs` and
`demosaic.rs` are mine and were not touched. Nothing outside my ownership was edited.

---

## 11. Capture request

**A neutral achromatic slanted-edge target at the same magnification, f/5.6, ISO 100.**
Any matte, spectrally flat black-and-white edge — a razor blade on a white card is the
classic — shot as a small focus bracket so the merge has something to elect.

*Why:* it settles §9.5 in one measurement, by removing scene chroma as a confound
entirely. It would also give the project its first proper MTF target, which the 74 cy/mm
artifact-floor question in the merge-vs-frame arm needs and currently does not have.

---

## 12. Every number here was printed by code run this session

The brief says a number recalled from earlier notes is not a measurement, and my
predecessor was caught quoting `+8.43/+1.26 dB` from its own summary when the measured
values were `+5.54/−5.29 dB`. So the report is machine-checked against the artifacts:
`experiments/M95-chroma-cositing/src/verify_report.py` recomputes **91** quoted values
from the stored JSON and asserts each appears in this file.

```
checking 91 numbers against the artifacts
baseline: 91/91 present
== negative control: plant a wrong digit for each check ==
   all 91 checks discriminate: the true value is present and a
   one-digit corruption of it is not.
VERIFIER: ALL VERIFIED
```

The negative control is the point: a verifier that only ever prints PASS is
indistinguishable from one that checks nothing. It found **three defects in itself**, all
fixed, none of which were errors in the report:

1. **Five false FAILs**, every one a negative number. The prose uses the Unicode minus
   U+2212; the verifier formatted ASCII hyphens. `collapse()` now normalises both.
2. **A substring confound.** Corrupting C5's `0.9998` to `0.9993` "found" it inside C9's
   `0.99934`, so the check looked unable to discriminate. Matching is now digit-boundary
   aware.
3. **A range confound.** A one-digit corruption of `0.9999` lands exactly on `0.9998`,
   the other endpoint of the same range, which the report legitimately contains. Ranges
   are now checked as a single string.

It also did its job on the report. Running it forced a recompute of the console-only
control values, and **four of them were wrong** in the first draft because I had carried
them from a transcript rather than from JSON: C3's worst delta (written `0.00162`,
actually `0.001617` worst over all rows), C8 (written `0.00000 px`, actually
`9.31e-09`), C9's noise floor (written `0.118`, actually a `0.10939–0.12155` range), and
— the largest — the green-null separation, written as `100–450×` when the measured values
are **146×** and **498×**. All four are corrected above.

---

## 13. Patches for files I do not own

**None.** The fix landed entirely inside `image_out.rs`. No `pub mod` line, no `main.rs`
subcommand arm, and no shared registration point was touched.

One **suggestion**, deliberately *not* written as a patch because it is a product decision
rather than a defect: `--demosaic` produces a co-sited, full-resolution render and is
currently opt-in. With co-siting fixed, the binned path's remaining disadvantage against
it is resolution rather than registration. Whether `--demosaic` should become the default
for `--srgb` is the orchestrator's call and I have not pre-judged it.

---

## Candidate facts

**P18 — MEASURED.** strehl's binned render places red at **(−0.25, −0.25)** and blue at
**(+0.25, +0.25)** binned px relative to green, which the two-green average centres
exactly. Measured against a co-sited reference on `bee-3-cpl`, 35/35 coherent ROIs on both
a single frame and the merge: R **(+0.2316, +0.2344)** and **(+0.2274, +0.2441)**, B
**(−0.2362, −0.2365)** and **(−0.2301, −0.2441)**, with green as an internal null at
**0.00161** and **0.00049 px** — a 146× and 498× separation from the signal.
*Significance:* a fixed, systematic chroma misregistration of 0.66 binned px between red
and blue on every edge of every binned `--srgb` render strehl has ever produced. It is
geometry, not noise, and it was present before the corpus existed.

**P19 — DERIVED.** The displacement follows from the RGGB quad alone: a quad is one binned
pixel wide, its corners are ±0.25 binned px from its centre, red and blue occupy opposite
corners, and the two greens straddle the centre so their mean lands on it exactly.
Predicted R↔B separation `0.5 × √2 = 0.7071` binned px; measured **0.6637** and **0.6691**.
*Significance:* the defect is universal to any RGGB binning that writes the four quad
samples as one pixel, so it is not specific to this body, this subject or this pipeline.

**P20 — MEASURED.** Co-siting red and blue onto green's grid with a separable 4-tap Keys
(`a = −1/2`) resample removes **91.6 %** of red and **93.2 %** of blue misregistration on
the shipped render (0.5818 → 0.0490 px, 0.4557 → 0.0310 px) and lowers chroma RMS at
luminance edges by **67.4 %** (1286.2 → 419.5 DN) and overall by **60.8 %**.
*Significance:* the fix is large, cheap and now shipped in `image_out.rs`.

**P21 — MEASURED.** Under `--srgb` the camera matrix mixes channels, so correcting red and
blue also improves **green** registration by **89.0 %** (0.0764 → 0.0084 px) without green
itself being resampled.
*Significance:* chroma misregistration was contaminating the luminance-bearing channel
through the matrix. A "chroma-only" defect is not chroma-only once a colour matrix is in
the path, and the same will be true of any future chroma-domain correction.

**P22 — MEASURED.** The correction does not disturb the byte-frozen measurement path.
`write_binned` is reachable only inside `if let Some(m) = matrix`, and `matrix` is `Some`
only under `--srgb`. Rendering `bee-3-cpl --gate 0` with the new binary reproduces the
pinned binary's default-path output at SHA-256 `895e458d…`, **identical**, while the same
pair under `--srgb` differs (`76765a1f…` vs `6f1cec08…`), which gives the identity power.
*Significance:* no corpus number moved. The looking-at path and the measuring path are
genuinely separated in code, and that separation has now been measured rather than assumed.

**P23 — MEASURED.** A 4-tap Keys interpolator at `t = 0` is exactly `[0, 1, 0, 0]`, so a
zero-shift resample is a bit-exact no-op and **a "same blur, no shift" control for a
sub-pixel resample cannot exist**. The attempted control returned digits identical to the
uncorrected image in every column.
*Significance:* a methodological trap for any future resampling work in this repo. The
blur of an interpolating kernel is inseparable from its shift, so isolate the shift by
applying the correction where it is **not** needed (green got 53–66× worse) rather than by
trying to subtract the blur.

**P24 — MEASURED.** Single-pair spectral coherence is **identically 1** for every input,
because `|conj(A)·B| / (|A|·|B|)` reduces to `|A||B| / (|A||B|)`. It carries information
only after the cross- and auto-spectra are averaged over a frequency neighbourhood: after
that fix, real pairs read **0.99934–0.99947** and independent noise **0.10939–0.12155**.
*Significance:* a coherence gate written the obvious way admits everything while appearing
to work. This one passed pure noise before it was fixed.

**P25 — MEASURED.** A naive phase-ramp shift estimator wraps once `|d| · f_max > 0.5` and
returns a **confidently wrong** value with no failure signal: a planted 4.00 px read as
**−0.21 px**. Coarse de-ramping before the fine fit reads **4.0000**, worst error
**3.89e-09** against a naive worst error of **4.2101**.
*Significance:* any future sub-pixel registration in this repo — alignment, warpmap,
drift — must either bound the shift below the wrap or de-ramp first.

**P26 — ARGUED.** Registering one colour channel against another is not a valid instrument
on a coloured subject: red and blue are different images, not shifted copies, so the fit
measures scene chroma. Per-ROI sd was ≈ 0.5 px against a 0.25 px effect and the constants
disagreed between pairs. Comparing **each channel to itself** against a co-sited reference
removes the confound and makes green a free internal null.
*Significance:* the design rule that turned a failed arm into a decisive one, and it
generalises to any cross-channel geometric measurement.

**P27 — MEASURED.** The `bee-3-cpl` shipped render (`--gate 2.0 --srgb`, alignment on) is
**byte-identical** between build `1f17c1d5` and current HEAD with co-siting disabled
(SHA-256 `00e87214…` both).
*Significance:* recorded because I predicted the opposite. It means the pinned binary
remains a valid "before" for this configuration, and that M86's in-flight alignment work
had not changed this render as of tonight.

**P28 — MEASURED.** Machine-checking a report's numbers against its artifacts catches real
errors: a 91-number verifier over this report found **four** values I had carried from a
transcript rather than recomputed, the largest being a separation ratio written `100–450×`
when the measured values are `146×` and `498×`.
*Significance:* it converts "a number I recall is not a measurement" from a rule people
are told to follow into a check that runs. Every number in this report is now printed by
code run this session.

**P29 — MEASURED.** A substring-based number verifier over a numeric document needs
**digit-boundary-aware matching** and must check ranges as one string. Both failure modes
were observed here: a corruption of `0.9998` matched inside `0.99934` elsewhere in the
document, and a corruption of `0.9999` landed exactly on `0.9998`, the other endpoint of
its own range. In both cases the mutation control reported that the check could not
discriminate when the report was in fact correct.
*Significance:* without these two rules a report verifier silently loses power on exactly
the dense-numeric documents this repo writes, and the loss is invisible unless a mutation
control is run.

---

*Every number in this report was printed by code run in this session; the aggregator is
`experiments/M95-chroma-cositing/src/report_numbers.py`, which reads only the JSON the
experiments wrote.*
