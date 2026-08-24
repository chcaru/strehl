# M95 arm 7 — the demosaic has headroom, but not where the softness is

**Milestone:** M95 (dispatched as M93; renumbered by the orchestrator).
**Status:** complete. **Nothing shipped from this arm** — both candidates failed
their pre-registered ship bars and I did not move the bars.
**Pre-registration:** `experiments/M95-cdiff/PRE-REGISTRATION.md`, on disk before
any candidate was scored, with ADDENDUM 1 written between the two runs.

---

## 1. Headline

I was sent to land a coverage-rescale fix against a pre-registered bar, and to
follow it with a demosaic upgrade. **Neither ships, and for the same underlying
reason**, which this arm finally measures directly:

> **The cost is not the coverage scale and it is not the demosaic. It is the
> resampling kernel evaluated at a non-integer phase — and when the phase is
> integer that cost is `-0.0002 dex`, which is nothing.**

Three arms of one instrument, all re-measured in this session:

| mapping the gather is asked to perform | cost vs no gather |
| --- | --- |
| real warp **and** the 0.9315 coverage scale (`NOW`) | **+0.1844 dex** |
| real warp, coverage scale **removed** (`FIX`) | **+0.1701 dex** |
| integer translation, unit scale (`SNAP`) | **−0.0002 dex** |

Removing the coverage scale — the fix I was directed to land, priced by the
orchestrator at 64.2% of the deficit — recovers **+0.0143 dex**, which is
**7.8%** of what the gather costs. The registered DEAD bar (recovery < 0.03 dex)
**fires**. The registered SHIP bar (> 0.10 dex) does not.

`SNAP` is the number that explains the other two. Rounding every translation to
an integer and forcing unit scale makes the gather **free**. The scale is not the
problem; **sampling between the samples** is the problem, and it costs the same
whether the non-integer mapping comes from the coverage scale, from the frame's
own warp, or from both at once.

**The lever that is actually on the table is the kernel.** Measured this session
with independently written kernels: swapping Catmull-Rom for Lanczos-3 recovers
**+0.1343 dex** — **9.4× more than the rescale fix** — but it lives in
`crates/strehl-core/src/align.rs`, which I do not own. It is delivered as a patch
in §7, unlanded.

On the demosaic: real headroom exists and I built a candidate that captures part
of it, but **it is small and it is chromatic**, and my luma ship bar did not fire.

---

## 2. Why the prescribed fix cannot land

The orchestrator's model was: the pipeline crops to the covered region and then
**stretches it back** to sensor dimensions, so there are two things happening and
removing the stretch removes one of them.

That is not what the code does. `fit_to_cover` composes a pure scale `s` onto
every frame's placement `t` and returns `s.then(t)` — **one** composed mapping,
evaluated in **one** gather. So the output pixel `p` maps to a source position at

```
NOW : a * k * (p - c) + c + b       step ~ |a| * 0.9315
FIX : a *     (p - c) + c + b       step ~ |a|
```

Removing `k` does not remove a resampling step. It changes the step from `0.9315`
to `1.0009` — **still non-integer**, still landing between samples at every
output pixel, still paying the kernel's sag. That is why `FIX` recovers 7.8%
rather than 64.2%.

The orchestrator's own `resample_budget.py` is **consistent with this** and was
misread rather than wrong. It measured one gather at `k` costing `+0.2392` dex
against no gather at all. That is a measurement of **the gather**, not of `k`.
My instrument reproduces the same magnitude from the other side:

| what is doing the resampling | cost |
| --- | --- |
| the coverage scale acting alone, identity warp (`K6`) | +0.1836 dex |
| the real warp acting alone, no coverage (`FIX`) | +0.1701 dex |
| both at once (`NOW`) | +0.1844 dex |

**They do not add.** Either one alone costs ~0.17–0.18 dex, and both together
cost 0.1844. A second non-integer factor composed into the same gather is nearly
free, because the first one already put every output pixel at an arbitrary phase.
This is threshold behaviour, not dose behaviour, and it is the direct reason a
"remove one of the two resamples" fix returns almost nothing.

> **The orchestrator's registered bar — MERGE moving from +0.3693 to within noise
> of +0.1301 — cannot be met by this change, and I did not attempt to meet it.**
> Reporting the number that was actually measured was the registered instruction
> in the case where the prediction was wrong.

---

## 3. The demosaic: two candidates, two registered verdicts

Arm 6 (`docs/research/M95-demosaic.md`, `7086ba2`) measured the shipped
Malvar-He-Cutler demosaic losing **0.1586 dex** of true detail against a perfect
demosaic, with the loss **chromatic** — R and B carry roughly twice G's artifact
share, tracking their quarter-density sampling.

**CDIFF** interpolates the colour differences `R−G` and `B−G` against the
reconstructed full-resolution green plane instead of correcting R and B with
Malvar's fixed-gain Laplacian of the quarter-density known channel. It remains
**linear and shift-invariant within a CFA phase**, so it keeps every property
`demosaic.rs`'s docstring argues for.

**CDIFF2** adds one linear Jacobi refinement of the green plane, using the exact
R and B samples, then redoes the chroma against the refined green.

400 tiles of 64×64 ranked on the **truth's** own band energy, band 0.30–0.48
cyc/px:

| arm | ch | power | signal | artifact | share |
| --- | --- | --- | --- | --- | --- |
| MHC | Y | +0.0047 | −0.1586 | −0.4993 | 0.3134 |
| MHC | R | −0.0407 | −0.4881 | −0.2325 | 0.6430 |
| MHC | G | −0.0498 | −0.2127 | −0.5547 | 0.3127 |
| MHC | B | −0.0322 | −0.3874 | −0.2851 | 0.5586 |
| CDIFF | Y | +0.0110 | −0.1462 | −0.5064 | 0.3038 |
| CDIFF | R | −0.0602 | −0.4446 | −0.2913 | 0.5874 |
| CDIFF | G | −0.0498 | −0.2127 | −0.5547 | 0.3127 |
| CDIFF | B | −0.0366 | −0.3288 | −0.3468 | 0.4896 |
| CDIFF2 | Y | +0.1112 | −0.0911 | −0.3178 | 0.3724 |
| CDIFF2 | R | +0.0052 | −0.4038 | −0.2094 | 0.6101 |
| CDIFF2 | G | +0.0556 | −0.1599 | −0.3521 | 0.3912 |
| CDIFF2 | B | +0.0416 | −0.2904 | −0.2305 | 0.5344 |

### The verdicts

**CDIFF — BELOW BAR.** Luma signal gain **+0.0124 dex**, artifact share
**−0.0096**, per channel **R +0.0435 / G +0.0000 / B +0.0586**. B7 required
≥ 0.03 dex. It landed in the middle band I registered explicitly so that a
marginal result could not be talked upward, and I am not talking it upward.

The mechanism is confirmed exactly as hypothesised: **both chroma channels
improve and green is untouched**, which is what a chroma-only change must look
like. CDIFF is a **Pareto improvement** — there is no measured axis on which it
is worse than MHC. It is simply small.

**CDIFF2 — DO NOT SHIP, and this is the interesting one.** Luma signal gain
**+0.0675 dex**, comfortably over the 0.03 bar. It fails on the **second clause**:
artifact share rises **+0.0590**, over the 0.02 limit. Green signal moved
**+0.0528** so B12 confirms the refinement did the thing it was built to do —
it recovered real green detail — **and injected fabricated power while doing it**
(green artifact −0.5547 → −0.3521).

> That second clause is the entire lesson of arm 6, applied to my own work one
> arm later. An arm that is louder *and* more detailed can still be buying the
> detail with artifact. Had I registered only a signal bar, **I would have
> shipped CDIFF2 tonight**, into a codebase where the eye has already outranked a
> metric once (M87's halo correction read +72.9% while erasing abdomen hairs).

**Neither candidate ships.** Registered outcome, unmodified.

### 3.1 What the eye says, and an independent metric that agrees

`C:\dev\strehl-out\M95-cdiff\M95-cdiff-panels.png` — four panels at 100%,
identical crop chosen on the **truth's** own in-band energy, one shared transfer
fixed from the truth crop alone, no panel resampled, no number burned into any
panel.

**TRUTH, MHC, CDIFF and CDIFF2 are visually indistinguishable.** Not "close" —
I could not pick them apart, and that includes telling the ground truth from the
shipped demosaic. On the sharpest crop in the frame, at full magnification, the
demosaic choice is invisible.

That is the honest visual answer to "is the demosaic worth a night's work", and
it is **no**.

A second, entirely independent metric agrees with the B10 rejection. Mean
absolute pixel error against truth in that crop — **not** band-limited, **not**
`alpha`-decomposed, so it shares no machinery with the ladder:

| arm | R | G | B |
| --- | --- | --- | --- |
| MHC (shipped) | 0.00124 | 0.00056 | 0.00112 |
| CDIFF | 0.00124 | 0.00056 | **0.00111** |
| CDIFF2 | **0.00139** | **0.00068** | **0.00128** |

**CDIFF2 is worse than the shipped demosaic on every channel** while reading
+0.0675 dex better on band-limited signal. A signal-only bar would have shipped a
change that is measurably worse in the pixel domain. The artifact clause was not
bureaucracy; it was the only thing standing between this arm and a regression.

---

## 4. Controls, and four of my own predictions refuted

### 4.1 Three registered controls were non-discriminating

I registered that K8 would reject a mis-normalised variant, K10 would reject a
parity-swapped variant, and K9 would reject `NEAREST`. **Every arm passed every
control.** Diagnoses:

| control | why it could not fail | my error |
| --- | --- | --- |
| **K8 constant** | on a constant mosaic the colour difference is identically zero, so scaling the chroma kernel scales zero | it tests the green path only |
| **K10 shift (2,2)** | a Bayer-parity swap is itself invariant to a two-pixel shift | foreseeable; I did not foresee it |
| **K9 linearity** | replication **is** a linear operator | I confused "crude" with "non-linear" |

### 4.2 What did discriminate

**The ladder itself** caught the parity break decisively: `CDIFF_BADPARITY`
scores artifact share **0.7470** against `CDIFF`'s 0.3038.

The ladder did **not** catch the normalisation break (`CDIFF_BADNORM` share
0.3071, signal −0.1444 — marginally *better* than CDIFF). **This is a blind spot
in the arm-6 instrument and it was not previously recorded:** `decompose`'s
per-bin `alpha` absorbs a linear gain by construction, so a chroma gain error is
invisible to it.

**K11 — known-sample preservation**, added post-hoc and labelled as such:
CDIFF **5.960e-08**, `CDIFF_BADNORM` **1.603e-01**, `CDIFF_BADPARITY`
**6.549e-01**. It rejects both broken variants where nothing else did, and it is
the **only** control in this arm that rejects anything at all.

### 4.3 K11 is itself blind to the green refinement

On `CDIFF2`, K11 reads **0.000e+00** for the deliberately mis-normalised variant
too — **non-discriminating again**. The reason is structural: CDIFF2 preserves
known samples *by construction* regardless of the refinement kernel, because
`R = g2 + (M − g2) = M` at an R site whatever `g2` is.

So **CDIFF2's green refinement is guarded by no control I possess.** That is an
independent reason not to ship it, over and above B10.

### 4.4 The rescale harness

| control | reading | verdict |
| --- | --- | --- |
| K1 NULL — identity warp, no coverage | **−0.000041 dex** | harness does not blur by itself |
| K6 — identity warp, coverage on | **+0.1836 dex** | instrument responds to a known resample |
| `SNAP` — integer translation, unit scale | **−0.0002 dex** | the geometry floor is zero |

The null and the positive control bracket every arm reported, and `SNAP` is a
second null reached by a completely different route.

---

## 5. Where the softness actually is

Budget from arm 4 (`experiments/M95-resample/out/x6_summary.txt`, `56efa4e`/
`4ac71e9`), single in-focus frame → shipped merge, **0.3999 dex total**:

| contributor | cost | share | whose file |
| --- | --- | --- | --- |
| **interpolation kernel** | **+0.2360 dex** | **59.0%** | `align.rs` — **not mine** |
| gather that is not the kernel | +0.0491 dex | 12.3% | `align.rs` — not mine |
| election + coverage zoom | +0.1148 dex | 28.7% | merge — contended |
| *demosaic algorithm (separate)* | *+0.0332 dex* | — | `demosaic.rs` — mine |

The single largest term is the kernel, it is 59% of the deficit, and **the whole
demosaic-algorithm difference between strehl and rawpy-AHD is 0.0332 dex** — less
than a seventh of it. Arm 7's best Pareto-safe candidate buys **+0.0124 dex**.

**The demosaic is not where the owner's softness lives.** Arm 6 was right that
headroom exists; this arm establishes that the headroom is small relative to the
kernel and that the safe part of it is smaller still.

---

## 6. Kernel measurements, re-run this session

Independently written kernels, 40 in-focus tiles, phase-averaged, against the
same baseline:

| kernel | phase-avg | worst phase | phase (0,0) |
| --- | --- | --- | --- |
| catmullrom | −0.2006 | −0.3897 | +0.0000 |
| mitchell | −0.3738 | −0.5309 | **−0.2008** |
| lanczos3 | **−0.0663** | −0.1244 | +0.0000 |
| bspline | −0.0951 | −0.1725 | +0.0000 |

**Identity-phase control:** every interpolating kernel must cost ~0 at phase
(0,0). Catmull-Rom, Lanczos-3 and B-spline all read exactly `+0.000000`;
Mitchell reads `−0.200830` and is correctly flagged **non-interpolating** — a
control that fires on one arm and not the others, which is what makes the other
three readings admissible.

**What a kernel change would buy:**

- **lanczos3 vs catmullrom: +0.1343 dex** — 1.362× power, 1.167× amplitude
- bspline vs catmullrom: +0.1055 dex — 1.275× power, 1.129× amplitude

**The cost, and it is not small:** arm 4 measured ringing as mean overshoot
relative to local range at half-pixel phase — catmullrom `0.000061` mean /
`0.022139` p99.9, against lanczos3 `0.000604` / `0.108394`. **Lanczos-3 rings
~9.9× as much.** In a codebase where M87 is actively fighting a cutout halo on
the same edges, that trade is an arbitration, not an obvious win, and it is not
mine to make.

---

## 7. The patch I cannot land

`Resampler` lives in `crates/strehl-core/src/align.rs`, with its string
round-trip in `warpmap.rs` and its CLI parse in `align_cmd.rs` — all M86's, and
`align_cmd.rs` is mid-edit and untracked. **I have not touched any of them.**
Delivered for the orchestrator to apply or reject.

Add beside `sample_catmull_rom` in `align.rs`:

```rust
/// Lanczos-3 (windowed sinc, `a = 3`) gather.
///
/// Interpolating: the window is 1 at 0 and the sinc has zeros at every other
/// integer, so an identity transform is a true identity. Its passband is
/// materially flatter than Catmull-Rom's, which is the entire reason to pay for
/// six taps per axis instead of four.
///
/// **It rings.** Measured at half-pixel phase on linear sensor data, mean
/// overshoot relative to local range is 0.000604 against Catmull-Rom's 0.000061,
/// and p99.9 is 0.108394 against 0.022139 — roughly 9.9x. On hard edges that is
/// a visible light fringe, so a caller that already has an edge artefact should
/// not reach for this without measuring the interaction.
#[inline]
fn lanczos3_weights(f: f32) -> [f32; 6] {
    #[inline]
    fn l3(x: f32) -> f32 {
        if x.abs() < 1e-6 {
            return 1.0;
        }
        if x.abs() >= 3.0 {
            return 0.0;
        }
        let px = std::f32::consts::PI * x;
        3.0 * (px.sin() * (px / 3.0).sin()) / (px * px)
    }
    let mut w = [0f32; 6];
    let mut s = 0f32;
    for (i, wi) in w.iter_mut().enumerate() {
        *wi = l3(f - (i as f32 - 2.0));
        s += *wi;
    }
    // Renormalise so a flat field is preserved exactly; the truncated window
    // does not sum to 1 on its own and an unnormalised gather would apply a
    // phase-dependent gain, which reads as banding on smooth gradients.
    if s.abs() > 1e-12 {
        for wi in w.iter_mut() {
            *wi /= s;
        }
    }
    w
}

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

Then four one-line registrations:

```rust
// align.rs, enum Resampler
    Lanczos3,
// align.rs, Resampler::sample
            Resampler::Lanczos3 => sample_lanczos3(p, x, y),
// align.rs, Resampler::support
            Resampler::Lanczos3 => 3.0,
// warpmap.rs, the two string arms
            Resampler::Lanczos3 => "lanczos3",
            "lanczos3" => Some(Resampler::Lanczos3),
// align_cmd.rs, the two parse tables
            "lanczos3" => Resampler::Lanczos3,
            ("lanczos3", Resampler::Lanczos3),
```

**I recommend adding it as an option and NOT changing the default in the same
change**, so the ringing interaction with M87's halo work can be measured on its
own before it becomes what everyone renders.

### 7.1 The patch is verified, not merely asserted

Handing someone code to paste into a file I cannot build is not a deliverable, so
the kernel body above is carried **verbatim** in
`crates/strehl-cli/examples/m95-lanczos.rs` — a self-contained example that
touches nothing of M86's — and compiled and asserted this session:

| control | reading | why it is there |
| --- | --- | --- |
| **C1** interpolating at phase 0 | `max\|w − δ\| = 2.301e-8` | an identity transform must be an identity; this is the control **Mitchell fails** at −0.2008 dex |
| **C2** partition of unity | `max\|Σw − 1\| = 2.384e-7` | a truncated window does not sum to 1 on its own; without the renormalisation a flat field acquires a phase-dependent gain and smooth gradients band |
| **C3** support vanishes at the window edge | `w[0] = 0.000e0` | otherwise the clamp in `sample_lanczos3` reads pixels the kernel still weights |
| **C4** discrimination vs Catmull-Rom | lanczos3 **0.6466**, catmullrom **0.4488** at 0.40 cyc/px, half-pixel phase | a comparison that cannot separate the two kernels is not evidence that they differ |

`M95 LANCZOS-3 PATCH VERIFIED (4/4 controls)`. C4's 1.441× amplitude advantage at
a single worst-case phase is consistent with the 1.167× measured phase-averaged
across the 0.30–0.48 band in §6, which is the sense in which the two independent
routes to this kernel agree.

---

## 8. Answers to the orchestrator's standing questions

1. **"Tell me plainly what your 8.2 MP figure actually meant."** The literal
   pixel dimensions of the `--srgb` file *before* commit `56bd846`. It was correct
   about that file. That file no longer exists as a default: `--srgb` now implies
   `--demosaic`, so the default `--srgb` render is full sensor resolution.
   **Your reading of it as a claim about the merge's luma resolution was wider
   than the finding, and your `fullres_check.py` result at 0.861 on a
   binned→full scale is consistent with mine rather than a refutation.**
2. **"`--srgb` should imply `--demosaic` — tell me and I will make the change."**
   **Already shipped, by me, in `56bd846`.** `main.rs:405` and `:436` read
   `demosaic: demosaic || (srgb && !binned)`, with `--binned` as the opt-out.
   **Do not open `main.rs`; there is nothing to change.**
3. **"Do not de-bin anything."** Nothing was de-binned. The binned path is
   untouched by every arm of M95 since `56bd846`.
4. **"Emit the cropped region at native sampling."** Built and measured in arm 5,
   committed `1024ddc`, re-measured this session at **+0.0143 dex recovery**
   against a registered 0.10 ship bar. **It does not ship.** §2 explains why.
5. **"Is it resampling, and are there two of them?"** It is resampling, and there
   is exactly **one** gather — you were right about that and right to warn me off
   hunting a second one. But the cost belongs to the **kernel at non-integer
   phase**, not to the scale factor, which is why removing the scale returns 7.8%.
6. **"Report the measured number even if it embarrasses the prediction."** Done,
   in §1 and §2. The prediction was wrong and the mechanism is now measured.

---

## 9. Candidate facts

- **P74.** Removing the 0.9315 coverage scale from the merge's gather recovers
  **+0.0143 dex** of 0.30–0.48 cyc/px power, **7.8%** of what the gather costs.
  Registered DEAD bar (< 0.03) fires; SHIP bar (> 0.10) does not. `MEASURED`
- **P75.** A gather with **integer translation and unit scale** costs
  **−0.0002 dex**. The geometry floor is zero, so the entire resampling cost is
  attributable to non-integer phase rather than to any particular scale factor.
  `MEASURED`
- **P76.** The coverage scale alone (+0.1836 dex) and the real warp alone
  (+0.1701 dex) each cost nearly as much as both together (+0.1844 dex).
  Composed non-integer factors in a single gather are **threshold, not dose**.
  `MEASURED`
- **P77.** Swapping Catmull-Rom for Lanczos-3 recovers **+0.1343 dex** (1.362×
  power) phase-averaged, **9.4× the coverage-rescale fix**, at ~**9.9×** the
  ringing. `MEASURED`
- **P78.** Interpolating chroma as colour differences against the reconstructed
  green plane (`CDIFF`) gains **+0.0124 dex** luma signal and **reduces** artifact
  share by 0.0096, with per-channel gains **R +0.0435 / G +0.0000 / B +0.0586**.
  A Pareto improvement, below the registered 0.03 ship bar. `MEASURED`
- **P79.** One linear green refinement (`CDIFF2`) gains **+0.0675 dex** luma
  signal — over the ship bar — while raising artifact share **+0.0590**, over the
  0.02 limit. Detail and fabrication rise together; a signal-only bar would have
  shipped it. `MEASURED`
- **P80.** `decompose`'s per-bin `alpha` **absorbs a linear gain error by
  construction**, so the arm-6 instrument is blind to a mis-normalised chroma
  kernel. Known-sample preservation (K11) catches it; nothing else tried did.
  `MEASURED`
- **P81.** Known-sample preservation is **structurally blind** to an error in
  CDIFF2's green refinement, because the algorithm reproduces exact samples
  whatever the refinement returns. `ARGUED`
- **P82.** Of the 0.3999 dex single-frame→merge deficit, the interpolation kernel
  is **59.0%** and the entire strehl-vs-rawpy-AHD demosaic difference is
  **0.0332 dex**. The demosaic is not the dominant term. `MEASURED`
- **P83.** `CDIFF2` reads **+0.0675 dex better** on band-limited signal while
  being **worse than the shipped MHC on mean absolute pixel error in all three
  channels** (R 0.00139 vs 0.00124, G 0.00068 vs 0.00056, B 0.00128 vs 0.00112).
  Two metrics sharing no machinery disagree in sign; the artifact clause is what
  reconciles them. `MEASURED`
- **P84.** At 100% on the highest in-band-energy crop of the frame, ground truth,
  MHC, `CDIFF` and `CDIFF2` are **visually indistinguishable**. The demosaic
  choice is not visible on this subject at this magnification. `MEASURED`

---

## 10. Scope, falsifiers, and a capture request

- The re-run of arm 5 used the **quarantined** sidecar
  (`ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt`, 8 placed frames) because the
  original was moved after arm 5 first ran. It is therefore **not a bit-exact
  reproduction** of the committed number (`1024ddc` recorded NOW +0.1813 → FIX
  +0.1855). Both runs fire the same DEAD verdict, and the fresh run is the one
  quoted throughout. Anyone re-deriving this should expect the third decimal to
  move with the warp set.
- Truth `T` remains a 2× box-downsampled AHD decode, not a CFA-free capture. Arm
  6's K5 bounds the contamination (ranking invariant across three truths, MHC
  moving ≤ 0.0198 dex) but does not remove it.
- **Capture request, for the orchestrator to file** (`docs/captures-needed.md` is
  theirs): **R, G and B filtered exposures of one static high-detail subject**,
  same focus and aperture, so a CFA-free ground truth can be built. Every demosaic
  number in arms 6 and 7 is currently measured against a decode rather than
  against the scene.
- **What would falsify §1:** a gather with integer translation and unit scale
  reading materially above zero, or a coverage-scale removal recovering > 0.10
  dex on any stack. Both are one `x8_fix.py` run away.
- **What would falsify §7:** Lanczos-3 failing the identity-phase control in Rust,
  or its ringing measuring below Catmull-Rom's — either would mean the Python
  kernels I measured are not the kernel the patch implements.
