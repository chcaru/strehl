# M95 arm 4 — the softness is one resampling step, and 59% of it is the interpolation kernel

Status: measured. Delta-only against `docs/research/M95-resolution.md` (arms 1–3).
Pre-registration: `experiments/M95-resample/PRE-REGISTRATION.md`, written before any
arm-4 number was read.

---

## 1. Headline

On `bee-3-cpl`, going from a strehl decode of a single in-focus frame with **no
resampling** to the **shipped `--gate 0` full-resolution merge** costs **−0.3999 dex** of
power in 0.30–0.48 cyc/px — **2.511× in power, 1.585× in amplitude**, equivalent to a
Gaussian blur of **σ = 0.410 px**.

That loss decomposes, and one term dominates:

| Term | dex | share |
| --- | --- | --- |
| the interpolation kernel | −0.2360 | 59.0% |
| the gather that is not the kernel | −0.0491 | 12.3% |
| election + coverage zoom | −0.1148 | 28.7% |
| **total B0 → C** | **−0.3999** | 100.0% |

**The single largest cause of the softness the owner is complaining about is the
Catmull-Rom interpolation kernel used by the merge's warp gather.** It costs **1.722× of
high-band power — σ = 0.312 px of blur — on every pixel of every frame**, and it is paid
even by the reference frame, whose warp is identity, because the coverage zoom makes every
sample position fractional.

**I am not shipping the fix.** It lives in `crates/strehl-core/src/align.rs` and
`crates/strehl-core/src/warpmap.rs`, which are M86's. Verbatim patch in §9. **Read §7
before applying it** — the best-sharpening kernel also rings **9.902×** as much as the
incumbent, on exactly the edges where M87 is currently fixing a halo.

---

## 2. The plain answer to the orchestrator's pivotal question

Asked twice, so answered first and without hedging.

**My "8.2 MP" figure meant the literal pixel dimensions of the file the default `--srgb`
path writes.** `ship-binned.tif` measures `(2344, 3516, 3)` = 8.24 MP from a 32.97 MP
capture. It was not per-CFA-plane working resolution, not a chroma co-siting effect, and
not narrower than luma. It was the emitted TIFF, measured.

**There is no contradiction with your measurement, because we measured different files.**
Your `bee-3-cpl-g0.tif` measures `(4688, 7032, 3)` = 32.97 MP. Only the `if demosaic`
branch emits `geom.width*2 × geom.height*2`. **You rendered with `--demosaic`.** You
therefore measured the very branch arm 3 recommended promoting to default, and you
correctly found it is not binned. Both measurements are right.

**Your "do not de-bin anything" instruction was already moot**: my de-binning change was
only ever a patch in a report, it targets `merge_cmd.rs` which is not mine, and it was
never applied. Nothing was mid-flight.

**Your 2.34× deficit stands, and this arm confirms it, prices it, and names its cause.**
My independently measured equivalent is **2.511× (−0.3999 dex)** between an unresampled
strehl single frame and the shipped merge. Two different instruments on two different
pairs landing on 2.34× and 2.51× is convergence, not coincidence.

**Your stated confound is small.** The demosaic-algorithm difference — rawpy/LibRaw
against strehl's Malvar-He-Cutler, isolated as `A → B0` — is **−0.0332 dex, 1.079× in
power**. It is 8% of a power ratio you measured at 2.34×. Your number is essentially all
real loss. You were right to flag it and right not to claim it away; it just turns out not
to matter.

**Your "two interpolations in series" hypothesis is falsified.** There is exactly **one**
gather. `cover_or_explain` folds the coverage zoom into the warp matrix, so the zoom and
the warp are resolved in a single Catmull-Rom pull. The measurement confirms the code:
one strehl gather costs −0.2851 dex; an independently written Catmull-Rom costs −0.2006
dex phase-averaged and −0.3897 dex at the worst phase; the in-crate M86b instrument reports
Catmull-Rom retaining 0.5139 of gradient energy at a half-pixel shift, which is −0.2894 dex.
Two gathers in series would land near −0.57 dex. It does not.

**And your proposed fix would not have worked.** Emitting the cropped region at native
sampling instead of stretching it back removes the *zoom*, but the cost is not in the zoom's
magnitude — it is in the gather's sub-pixel phase. The proof is `B0 → B1`: a **single frame
aligned to itself**, with a coverage scale of **0.9974**, still pays **−0.2851 dex**. A
0.26% zoom costs the same as a 6.85% one. Removing the stretch would have bought
approximately nothing, and I would have shipped it and found that out afterwards.

---

## 3. Terms

All five are 7032 × 4688, 16-bit, **linear camera-native** (no `--srgb`, so no transfer
curve redistributes power across the band), rendered by the same binary in this session.

| Term | What it is | Demosaic | Election | Gather | Coverage |
| --- | --- | --- | --- | --- | --- |
| **A** | rawpy/LibRaw decode of `DSC00150.ARW` | LibRaw | no | no | — |
| **B0** | strehl 1-frame, `STREHL_ALIGN=0` | strehl MHC | trivial | **none** | — |
| **B1** | strehl 1-frame, alignment ON | strehl MHC | trivial | one | 0.9974 |
| **D** | strehl 299-frame gate 0, `STREHL_ALIGN=0` | strehl MHC | yes | **none** | — |
| **C** | strehl 299-frame gate 0, alignment ON | strehl MHC | yes | one | 0.9315 |

`DSC00150.ARW` is frame 149, the merge's own reference frame, so its warp is identity.

**`B0` is the key term and it did not exist before this session.** A single-frame stack
still reports `coverage: field of view scaled to 0.9974` and `resampler: CatmullRom`, so
`single-strehl.tif` is *not* resample-free. Setting `STREHL_ALIGN=0` on a one-frame
directory is what produces a genuinely unresampled strehl decode, and it is what makes
`B0 → B1` a clean single-variable price of one gather.

---

## 4. Pre-registered bars, and how they landed

| Bar | Condition | Result | Fired |
| --- | --- | --- | --- |
| **B4** resampling is the dominant cause | `D → C` ≥ 0.20 dex | **−0.2100 dex** | **YES** |
| **B5** the deficit is substantially demosaic difference | `A → B0` ≥ 0.20 dex | −0.0332 dex | no |
| **B6** resampling is NOT the cause | `D → C` < 0.05 dex | −0.2100 dex | no |

B4 fired and B5 did not, which is the outcome that says *build the fix and stop blaming
the decoder*. B4 is corroborated independently by `B0 → B1` = −0.2851 dex on a pair that
shares an election and differs only by one gather.

---

## 5. The decomposition

40 sharpest 256 px tiles by gradient energy **on B0**, so the single frame is in focus in
them. Statistic: mean over tiles of `log10(power 0.30–0.48 cyc/px / power 0.02–0.10
cyc/px)`, each image integrated over **its own coverage-scaled band** so every term covers
the same *scene* frequencies without any pixel data being resampled to make it so.

| Term | mean | sd | n | reg cc | dropped |
| --- | --- | --- | --- | --- | --- |
| B0 | −2.9963 | 0.6658 | 40 | 1.0000 | 0 |
| B1 | −3.2814 | 0.6435 | 40 | 0.9590 | 0 |
| D | −3.1726 | 0.3405 | 37 | 0.8281 | 3 |
| C | −3.3824 | 0.3935 | 38 | 0.8058 | 2 |
| A | −2.9632 | 0.6434 | 40 | 0.9572 | 0 |

| Pair | dex | power | amplitude | what it isolates |
| --- | --- | --- | --- | --- |
| A → B0 | −0.0332 | 1.079× | 1.039× | demosaic algorithm, LibRaw vs MHC |
| B0 → B1 | −0.2851 | 1.928× | 1.389× | **one gather, same frame** |
| B0 → D | −0.1524 | 1.421× | 1.192× | election on unregistered frames |
| D → C | −0.2100 | 1.622× | 1.273× | gather + coverage zoom |
| B0 → C | −0.3999 | 2.511× | 1.585× | **unresampled frame → shipped merge** |

**`B0 → D` is not clean and I am not claiming it as "the election".** `D` is rendered with
alignment off, so its election runs on frames carrying 232.7 px of drift and picks winners
whose scene content is displaced. It conflates the election with misregistration. My
pre-registration assumed it would isolate the election and that assumption was wrong. The
number is reported because it bounds the non-resampling remainder, not because it
attributes it.

---

## 6. End to end through the shipped binary

The strongest result here, because nothing is modelled. The **same frame**, the **same
binary**, the **same demosaic**, the **same output path** — only the resampler recorded in
the warp sidecar changes.

| gather | dex vs B0 | power | amplitude | n |
| --- | --- | --- | --- | --- |
| nearest | −0.0491 | 1.120× | 1.058× | 40 |
| catmull-rom (**ships**) | −0.2851 | 1.928× | 1.389× | 40 |
| bilinear | −0.4831 | 3.042× | 1.744× | 40 |

**Attributable to the interpolation kernel alone: −0.2360 dex, 1.722× power, 1.312×
amplitude, σ = 0.312 px.** The whole gather, kernel plus everything else it does, is
**σ = 0.344 px**.

Both predictions were registered before the numbers were read, and both are falsifiers
rather than confirmations:

- **Nearest is a permutation. It moves samples and interpolates nothing, so it must cost
  ≈ 0.** It read **−0.0491 dex**. Had it read −0.28, the loss would not have been the
  kernel and this entire diagnosis would be wrong. This is the power control required by
  discipline 595: the instrument was handed the disturbance it is claiming to attribute,
  through the real code path, and it separated it.
- **Bilinear is strictly blurrier than Catmull-Rom, so it must cost more.** −0.4831 < −0.2851.

---

## 7. What a kernel change buys, and what it costs — read this before applying §9

Independently written kernels, applied to B0's own tiles at eight sub-pixel phases,
measured with the same instrument. A zoom sweeps the phase uniformly across the field, so
the honest figure is phase-averaged, not the worst phase.

| kernel | phase-avg | worst phase | at identity |
| --- | --- | --- | --- |
| catmull-rom | −0.2006 | −0.3897 | +0.000000 |
| mitchell | −0.3738 | −0.5309 | −0.200830 |
| lanczos-3 | −0.0663 | −0.1244 | +0.000000 |
| cubic B-spline (prefiltered) | −0.0951 | −0.1725 | +0.000000 |

- **lanczos-3 recovers +0.1343 dex** — 1.362× power, 1.167× amplitude.
- **cubic B-spline recovers +0.1055 dex** — 1.275× power, 1.129× amplitude.

**But the sharpest kernel is also the ringiest, and this project has already been burned by
exactly that trade.** M87 shipped a halo correction whose own metric read +72.9% while
erasing the bee's abdomen hairs. So I measured overshoot before recommending anything —
maximum excursion beyond the local `[min, max]` of the source neighbourhood, as a fraction
of the local range, at a half-pixel phase:

| kernel | mean overshoot | p99.9 overshoot | negatives | vs catmull-rom |
| --- | --- | --- | --- | --- |
| nearest | 0.000000 | 0.000000 | 0.0000% | — |
| bilinear | 0.000000 | 0.000000 | 0.0000% | — |
| catmull-rom | 0.000061 | 0.022139 | 0.0000% | 1.000× |
| cubic B-spline | 0.000383 | 0.084537 | 0.0000% | **6.274×** |
| lanczos-3 | 0.000604 | 0.108394 | 0.0000% | **9.902×** |

**Lanczos-3 buys 1.362× of power at 9.902× the ringing.** At the sharpest 0.1% of pixels it
overshoots by 10.8% of the local range. Next to a specular highlight on linear sensor data
that is a bright fringe — which is, in kind, the **cutout halo tracing the bee's silhouette**
that the orchestrator identified as the dominant visible defect and that **M87 owns**.

**My recommendation, and it is a hedge on purpose because the eye has already outranked a
metric once tonight:** prefer the **cubic B-spline**. It takes 78.6% of Lanczos-3's
sharpening gain at 63.4% of its overshoot, and it is a strictly cheaper change at runtime —
one recursive prefilter pass per plane per frame, then the same 4-tap gather, instead of a
36-tap one. **Whichever is chosen, this must be graded by eye against M87's halo work
before it ships, and I am not the one to grade it.**

---

## 8. Controls, including the ones that failed

Every control run in this arm. Discipline 594: a null is a claim about the world only if
the instrument could have said otherwise, and the instrument must be shown saying otherwise.

### Passed

| id | control | result |
| --- | --- | --- |
| K7 | null, B0 against itself | **+0.000000 dex**, exactly |
| K6 | planted Fourier-exact Gaussian blur | σ=0.10 → −0.0248; σ=0.25 → −0.1530; σ=0.50 → −0.5896; σ=1.00 → −2.1031 dex |
| K8 | anchor separation gate ≥ 0.30 dex | **2.1031 dex**, PASS; all five deltas lie inside the anchors |
| K9 | tiles selected on B0, not the merge | 40 tiles; selecting on the merge would flatter the merge |
| K10 | registration | cc 0.81–0.96; 5 of 200 tile placements dropped below cc 0.50 |
| — | identity phase, interpolating kernels | catmull-rom, lanczos-3, B-spline all **+0.000000** |
| — | ordering, mitchell worse than catmull-rom | −0.3738 < −0.2006, PASS |
| — | nearest is free (end-to-end falsifier) | −0.0491, PASS |
| — | bilinear worse than catmull-rom (end-to-end) | −0.4831 < −0.2851, PASS |
| — | bilinear cannot overshoot (non-negative weights) | **0.000000**, PASS |
| — | nearest cannot overshoot (a permutation) | **0.000000**, PASS |
| — | lanczos-3 rings more than catmull-rom | 0.000604 > 0.000061, PASS |

The K6 ladder is what licenses every attribution here: an instrument that resolves **a
tenth of a pixel** of blur (−0.0248 dex at σ=0.10) is entitled to say that −0.2360 dex is
real and that −0.0332 dex is small.

**The report's own numbers are verified under mutation.** `verify_report.py` checks 98
quantities against the recorded JSON: **98/98 present, 98/98 discriminating** — every one
disappears when its last digit is changed, so none is passing by collision with a
neighbouring value. That verifier is itself certified by `verify_negative_control.py`,
which plants a one-digit defect in three separate places, requires the verifier to go red
each time, and restores the report from a copy in `TEMP`: **green → red, red, red →
green**. The mutation anchors are unique full-line strings and the control hard-errors if
an anchor is not found exactly once, because a control anchored on an ambiguous string
proves nothing.

### Failed, with diagnosis

**F-1 — the first instrument decoded wraparound as a valid registration offset.**
`x1_pairs.py` took the cross-correlation argmax over the full circular FFT range. `D`
reported `max|off| = 124 px` and `C` reported `279 px` from a **±24 px search**, which is
impossible. Diagnosed as circular wraparound being read as a large negative shift. Fixed
in `x2_pairs.py` by restricting the argmax to the physically reachable `0..2·SEARCH`
window. **The impossible number is what exposed it** — the run before it looked entirely
plausible.

**F-2 — the first instrument had no geometric prediction, so C could never register.**
C's field of view is scaled to 0.9315, putting a scene point up to ~300 px from where a
blind ±24 px search would look. `x1` read C at cc 0.4717. Fixed by predicting the tile
position through the known coverage scale and letting the search only refine it; cc rose
to 0.8058.

**F-3 — the planted-blur control was a delta, not a blur.** `x1`'s `gauss_blur` used
radius `ceil(4σ)`, so σ = 0.25 px got a 3-tap kernel of `[3.4e-4, 0.99932, 3.4e-4]`. It
duly read **−0.0011 dex** and looked exactly like an instrument sensitivity floor at a
quarter pixel. It was a kernel truncation artifact. Fixed by applying the blur in the
frequency domain as `exp(−2π²σ²f²)`, which is exact for a continuous Gaussian and cannot
truncate; the same control then read **−0.1530 dex**. **A sensitivity floor and a broken
sensitivity control are indistinguishable from the reading alone**, and this one would have
made the instrument look 139× less sensitive than it is.

**F-4 — my own identity-phase control fired a false alarm on Mitchell.** It asserted that
"every interpolating kernel must cost ~0 at a zero shift" and flagged Mitchell's −0.200830
as `*** NON-ZERO AT IDENTITY ***`. Mitchell (B=C=1/3) is **approximating, not
interpolating**; it does not pass through its samples and blurs at zero shift by
construction. The control was right about the number and wrong about the premise. Kept as
a record, because it demonstrates the instrument distinguishing interpolating from
approximating kernels — which is the property the whole §7 comparison rests on.

**F-5 — symlinking the read-only stack failed.** `New-Item -ItemType SymbolicLink` needs
Administrator. This is why §6 is measured on a single frame rather than on all 299: I could
not write a sidecar next to a read-only stack, and an 11.4 GB copy was not worth it once
the single-frame pair proved to be the cleaner instrument anyway.

### Independent corroboration from code I did not write

`strehl align D:\personal\macro\bee-3-cpl --resampler-cost` is an **in-crate M86b
instrument**, written by another milestone, on a different statistic (gradient energy), on
the full 299-frame stack:

```
  baseline gradient energy 9.8367e9
  resampler       gradient energy   retained
  nearest                9.8346e9    0.9998
  bilinear               3.2395e9    0.3293
  catmull-rom            5.0553e9    0.5139
```

`retained = 0.5139` is **−0.2894 dex**. My end-to-end `B0 → B1` is **−0.2851 dex**.
Different statistic, different band, different author, 0.0043 dex apart. Its `nearest`
reading of 0.9998 independently reproduces my nearest control.

---

## 9. Verbatim patch — for whoever owns `align.rs`

I have **not** applied any of this, and I did not edit any file under `crates/`.

**Route this carefully: `align.rs` has uncommitted work in the tree right now that is not
M86's.** `git diff crates/strehl-core/src/align.rs` shows 326 insertions adding an
iterative re-seeding stage whose own doc comments cite **M103** ("on `bee-3-cpl` M103
measured it costing between 20% and 89% of the true scale"). The brief assigned this file
to M86. Two milestones are in it. **Arbitrate before applying, or a `pub enum` arm gets
silently lost the way a `pub mod` line did earlier.**

The patch was compiled and executed standalone with `rustc` — see
`experiments/M95-resample/src/m95_lanczos_check.rs` — because the workspace does not
currently build (`align_cmd.rs` is M86's mid-edit untracked file). It **compiles and
passes four checks**:

```
1. weights sum to 1: worst |sum-1| = 2.384e-7
2. identity at integer positions: worst error = 6.199e-6 DN
3. half-pixel gather, gradient energy at 0.45 cyc/px:
     catmull-rom 2.6332e7
     lanczos-3   4.0695e7   (1.545x)
4. smooth ramp, worst |catmull-rom - lanczos3| = 9.155e-5 DN
ALL CHECKS PASS
```

Check 2 is the property `align.rs` already asserts of Catmull-Rom in
`catmull_rom_reproduces_the_samples_at_integer_positions`. Check 4 is a negative control:
if the two kernels disagreed on a smooth ramp, check 3 would be measuring a gain or
geometry change rather than sharpness.

### 9.1 `crates/strehl-core/src/align.rs`

Add after `sample_catmull_rom`:

```rust
/// Normalised Lanczos-3 weights for the six taps at offsets `-2 ..= 3`.
#[inline]
fn lanczos3_weights(f: f32) -> [f32; 6] {
    #[inline]
    fn l3(x: f32) -> f32 {
        if x == 0.0 {
            return 1.0;
        }
        let ax = x.abs();
        if ax >= 3.0 {
            return 0.0;
        }
        let px = std::f32::consts::PI * x;
        3.0 * px.sin() * (px / 3.0).sin() / (px * px)
    }
    let mut w = [0f32; 6];
    let mut s = 0f32;
    for (i, wi) in w.iter_mut().enumerate() {
        *wi = l3(f - (i as f32 - 2.0));
        s += *wi;
    }
    // Lanczos weights do NOT sum to one at an arbitrary phase. Without this the
    // gather applies a phase-dependent gain, which under a zoom is a smooth radial
    // brightness ripple -- exactly the kind of artefact that reads as a halo.
    if s != 0.0 {
        for wi in w.iter_mut() {
            *wi /= s;
        }
    }
    w
}

/// Lanczos-3 gather.
///
/// Interpolating, like [`sample_catmull_rom`], so an identity transform is a true
/// identity. M95 measured it retaining **1.362x** the power of Catmull-Rom in
/// 0.30-0.48 cyc/px, phase-averaged, on `bee-3-cpl`.
///
/// It also **rings 9.902x as much** (M95, mean overshoot beyond the local range at a
/// half-pixel phase; p99.9 overshoot 10.8% of local range against Catmull-Rom's 2.2%).
/// On linear sensor data next to a specular highlight that is a visible bright fringe.
/// Do not adopt it without grading the result by eye against the halo work.
pub fn sample_lanczos3(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {
    if p.width < 6 || p.height < 6 {
        return sample_catmull_rom(p, x, y);
    }
    let x = x.clamp(2.0, (p.width - 4) as f64);
    let y = y.clamp(2.0, (p.height - 4) as f64);
    let (x0, y0) = (x.floor() as usize, y.floor() as usize);
    let wx = lanczos3_weights((x - x0 as f64) as f32);
    let wy = lanczos3_weights((y - y0 as f64) as f32);
    let mut acc = 0f32;
    for (dy, wyv) in wy.iter().enumerate() {
        let row = (y0 + dy - 2) * p.width + x0 - 2;
        let mut r = 0f32;
        for (dx, wxv) in wx.iter().enumerate() {
            r += p.data[row + dx] * *wxv;
        }
        acc += r * *wyv;
    }
    acc
}
```

Then three one-line additions:

```rust
pub enum Resampler {
    Nearest,
    Bilinear,
    CatmullRom,
    Lanczos3,          // ADD
}
```

```rust
    pub fn sample(self, p: PlaneRef<'_>, x: f64, y: f64) -> f32 {
        match self {
            Resampler::Nearest => sample_nearest(p, x, y),
            Resampler::Bilinear => sample_bilinear(p, x, y),
            Resampler::CatmullRom => sample_catmull_rom(p, x, y),
            Resampler::Lanczos3 => sample_lanczos3(p, x, y),   // ADD
        }
    }
```

```rust
    pub fn support(self) -> f64 {
        match self {
            Resampler::Nearest => 0.5,
            Resampler::Bilinear => 1.0,
            Resampler::CatmullRom => 2.0,
            Resampler::Lanczos3 => 3.0,   // ADD
        }
    }
```

**`support()` matters and is not cosmetic.** `sample_checked` refuses samples whose support
would leave the plane, so raising it to 3.0 shrinks the valid rectangle by one plane pixel
per side and will move the coverage `k` that `cover_or_explain` solves, very slightly.
That is correct behaviour, not a regression, but it means **the elected frame at the extreme
border can change**, and arm 1's byte-exact election result is a regression test. Expect it
to move at the border and nowhere else, and check that it does.

### 9.2 `crates/strehl-core/src/warpmap.rs`

```rust
fn resampler_name(r: Resampler) -> &'static str {
    match r {
        Resampler::Nearest => "nearest",
        Resampler::Bilinear => "bilinear",
        Resampler::CatmullRom => "catmull-rom",
        Resampler::Lanczos3 => "lanczos3",        // ADD
    }
}

fn resampler_from_name(s: &str) -> Option<Resampler> {
    match s {
        "nearest" => Some(Resampler::Nearest),
        "bilinear" => Some(Resampler::Bilinear),
        "catmull-rom" => Some(Resampler::CatmullRom),
        "lanczos3" => Some(Resampler::Lanczos3),  // ADD
        _ => None,
    }
}
```

### 9.3 `crates/strehl-cli/src/align_cmd.rs`

This file is mid-edit and does not compile, so I give the change in words rather than as
context lines that will not apply: add `"lanczos3" => Resampler::Lanczos3` to the match in
`fn resampler(&self)` (~line 140), and add `("lanczos3", Resampler::Lanczos3)` to the
`RESAMPLERS` table used by `--resampler-cost` (~line 726) so the in-crate instrument prices
it alongside the others.

**No `lib.rs` or `main.rs` change is required.** No new module, no new subcommand.

---

## 10. What I did NOT change, and why

**Nothing.** This arm ships no code.

I own `image_out.rs`, `color.rs` and `demosaic.rs`, and **the defect is in none of them**.
That is a measured statement, not an assumption: `A → B0` prices strehl's entire demosaic
against LibRaw's at **−0.0332 dex**, 1.079× in power. There is no meaningful sharpness left
on the table in the demosaic, and the output path performs no resampling at all. The cheap
output-path fix the orchestrator hoped for **does not exist**, because the loss is upstream
of the output path.

Per the standing constraint — *"if the resolution loss is in the merge rather than the
output path, report that to me and stop"* — I have reported and stopped. It is not even in
the merge; it is in the warp gather.

---

## 11. Scope, and what would falsify this

**Covered:** the full-resolution `--demosaic` linear branch on `bee-3-cpl`, at `--gate 0`,
in the band 0.30–0.48 cyc/px, on the 40 sharpest tiles of frame 149.

**Not covered:**

- **The default binned `--srgb` path.** Arm 3 measured that separately. The kernel loss
  measured here is upstream of the bin and is therefore paid on that path too, but its
  *size* after a 2×2 box average is not measured and must not be assumed equal.
- **Gates above 0.** Every term is `--gate 0`. At higher gates more frames are averaged per
  pixel and each carries its own gather; whether the kernel cost compounds, cancels or
  stays flat is unmeasured.
- **Other stacks.** One stack, one subject. M52 measured mean `n_eff` at a fixed gate
  spanning 12.22× across the seven corpus stacks; nothing here is portable without
  re-measuring.
- **Absolute MTF.** `--demosaic`'s help says its extra samples are interpolated and its
  resolution is not to be measured. That warning is about *absolute* high-band content and
  it is correct. Every claim here is a *ratio* between renders that share the identical MHC
  interpolation, so it cancels — except `A → B0`, which is reported as a demosaic
  difference precisely because it does not.
- **Whether B-spline or Lanczos-3 looks better.** Measured on power and on overshoot; **not
  graded by eye**, and §7 says it must be before anything ships.

**Falsifiers:**

1. If a render built with a Lanczos-3 or B-spline gather does **not** reduce the measured
   `B0 → B1` deficit by at least +0.10 dex, §7's prediction is wrong.
2. If the nearest-neighbour control had read anything near −0.28 dex, the loss would not
   have been the interpolation kernel and §1 would be wrong. It read −0.0491.
3. If someone shows the 40 tiles are not in focus in B0, K9 fails and the comparison
   flatters nothing — it becomes meaningless. Tiles were chosen by gradient energy on B0
   alone, which is checkable.
4. If a kernel change visibly worsens the halo M87 is fixing, the sharpness gain is not
   worth taking, regardless of §7's numbers. This is the failure mode this project has
   already hit once and it outranks the metric.

**Capture request:** none.

---

## 12. Deliverable image

`C:\dev\strehl-out\M95-resample\M95-resample-kernel.png` — 100% crop of `bee-3-cpl`, 2×
nearest-neighbour magnification (so no display filter can add or remove the detail the
figure is about), identical linear stretch on every panel computed from B0 alone.

- **Row 1 — the loss:** B0 (no resample) | B1 (one Catmull-Rom gather) | C (shipped merge).
- **Row 2 — the cause:** the same frame through the same binary with only the sidecar's
  resampler changed: nearest | catmull-rom | bilinear.

The crop was chosen blind to the effect — the sharpest tile by gradient energy on B0. Every
panel carries the number measured on **exactly that panel's own axis**; no panel carries a
number measured on a different one. **The eye ranks the six panels in the same order the
metric does**, which is the agreement this project requires before a sharpness number is
allowed to mean anything.

---

## Candidate facts

Self-contained and delta-only against arms 1–3.

**P44.** On `bee-3-cpl` at `--gate 0`, the full-resolution merge is **−0.3999 dex** (2.511×
power, 1.585× amplitude, σ ≈ 0.410 px of Gaussian blur) below an unresampled strehl decode
of a single in-focus frame, in 0.30–0.48 cyc/px over the 40 sharpest tiles.
*Significance:* independently reproduces the orchestrator's 2.34× deficit at 2.51× with a
different instrument on a different pair, and converts "the stacks look soft" into a
measured quantity. **MEASURED.**

**P45.** That loss decomposes as **59.0% interpolation kernel** (−0.2360 dex), **12.3%
gather that is not the kernel** (−0.0491 dex), **28.7% election plus coverage zoom**
(−0.1148 dex). *Significance:* the dominant cause of the softness is a four-tap cubic
weight table, not the gate, not the demosaic, not the alignment residual. **MEASURED.**

**P46.** Switching only the resampler recorded in the warp sidecar, through the shipped
binary on the same frame: nearest **−0.0491 dex**, catmull-rom **−0.2851**, bilinear
**−0.4831**. Nearest is a permutation and costs ≈ 0, which is the falsifier the kernel
attribution needed. *Significance:* the attribution is end-to-end through production code,
not modelled. **MEASURED.**

**P47.** The demosaic-algorithm difference between rawpy/LibRaw and strehl's
Malvar-He-Cutler, isolated on the same frame and tiles, is **−0.0332 dex (1.079× power)**.
*Significance:* prices the confound that blocked the orchestrator's outside-the-codebase
measurement, and clears strehl's demosaic — there is no sharpness left to recover there.
**MEASURED.**

**P48.** The cost of a gather is set by the sub-pixel **phase**, not by the magnitude of
the zoom. A single frame aligned to itself at coverage **0.9974** pays **−0.2851 dex**, the
same order as the 299-frame merge at coverage **0.9315**. *Significance:* removing the
coverage stretch, or emitting the cropped region at native sampling, would recover
approximately nothing; it was the obvious fix and it is the wrong one. **MEASURED.**

**P49.** The merge performs exactly **one** gather, not two. `cover_or_explain` folds the
coverage zoom into the warp matrix, and the measured single-gather cost (−0.2851 dex)
matches an independently written Catmull-Rom (−0.2006 phase-averaged, −0.3897 worst phase)
and the in-crate M86b instrument (0.5139 retained = −0.2894 dex), where two in series would
land near −0.57 dex. *Significance:* falsifies the "two interpolations in series"
hypothesis and removes a whole class of proposed fixes. **MEASURED.**

**P50.** Replacing Catmull-Rom would recover **+0.1343 dex (1.362× power)** with Lanczos-3
or **+0.1055 dex (1.275× power)** with a prefiltered cubic B-spline, phase-averaged.
*Significance:* the size of the available sharpness win, measured before anyone writes the
Rust. **MEASURED.**

**P51.** Those same kernels ring **9.902×** (Lanczos-3) and **6.274×** (B-spline) more than
Catmull-Rom in mean overshoot beyond the local range at a half-pixel phase; p99.9 overshoot
goes from 2.2% of local range to **10.8%** and **8.5%**. *Significance:* the sharpening win
trades directly against the cutout-halo defect that is currently the owner's top visible
complaint, on the same edges; B-spline takes 78.6% of the gain for 63.4% of the ringing.
**MEASURED.**

**P52.** A **single-frame** stack is not resample-free: it reports `coverage: field of view
scaled to 0.9974` and gathers with Catmull-Rom, costing −0.2851 dex for a 0.26% crop.
`STREHL_ALIGN=0` on a one-frame directory is required to obtain an unresampled strehl
decode. *Significance:* any future single-frame reference term is silently pre-blurred
unless alignment is explicitly disabled, which would bias every comparison built on it
toward "the merge is fine". **MEASURED.**

**P53.** A planted-blur sensitivity control built from a sampled Gaussian kernel of radius
`ceil(4σ)` degenerates to a delta at small σ: at σ = 0.25 px the kernel is
`[3.4e-4, 0.99932, 3.4e-4]` and the control read **−0.0011 dex**, indistinguishable from a
genuine instrument floor. Applied in the frequency domain as `exp(−2π²σ²f²)` the same
control reads **−0.1530 dex**, 139× larger. *Significance:* a broken sensitivity control
and a real sensitivity floor produce the same reading, and the broken one silently licenses
false null results. **MEASURED.**

**P54.** A cross-correlation registration that takes its argmax over the full circular FFT
range reports wraparound peaks as valid offsets — here **124 px and 279 px from a ±24 px
search**. *Significance:* the tell is that the reported offset exceeds the search
half-width, which is checkable in one line and was the only thing that exposed an otherwise
plausible-looking run. **MEASURED.**

**P55.** An identity-phase control asserting "every interpolating kernel costs ≈ 0 at zero
shift" fires a true positive on Mitchell (B=C=1/3), which reads **−0.200830 dex** because
it is **approximating, not interpolating**, and blurs at zero shift by construction.
*Significance:* the check is a valid discriminator between interpolating and approximating
kernels, but its failure message must not be read as an implementation bug. **MEASURED.**

**P56.** strehl's own gather costs **−0.0845 dex more** than an independently written
full-resolution Catmull-Rom at the same phase-average, consistent with the gather being
performed on the CFA plane at 3516 × 2344 — half the output's linear resolution — so the
same kernel blurs twice as far in output pixels. *Significance:* names a possible second
lever (gather after demosaic rather than before) and bounds it at 0.0845 dex, but the
mechanism is inferred from the resolution at which the code operates rather than
demonstrated by a controlled comparison. **ARGUED.**
