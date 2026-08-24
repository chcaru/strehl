# M95 — The softness is the default output: it bins a 32.9 MP capture to 8.2 MP and the discarded band is not empty

**Milestone:** M95 (resolution arm). Third and final arm. Delta-only against
[`M95-merge-vs-frame-sharpness.md`](M95-merge-vs-frame-sharpness.md) (arm 1) and
[`M95-chroma-cositing.md`](M95-chroma-cositing.md) (arm 2); candidate facts continue at
**P30** so all three fold without a numbering collision.

**Subject:** `D:\personal\macro\bee-3-cpl`, 299 frames, ILCE-7CM2 +
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, f/5.6, ISO 100.
**Code:** `experiments/M95-resolution/`.
**Images:** `C:\dev\strehl-out\M95-resolution\`.
**Ships in:** nothing. The change belongs in `crates/strehl-cli/src/merge_cmd.rs`, which is
contended (M87 committed into it, M97 owns it). Per the brief this arm **reports and
stops**, and the patch is delivered verbatim in §11 for the orchestrator to apply.

---

## 1. Headline

**The merge is not the problem and the frames are not soft. The default output path is
throwing away half the linear resolution of every render this project has produced.**

The default render collapses each 2×2 RGGB quad to one RGB pixel: **8.24 MP out of a
32.97 MP capture**, both measured this session from the emitted files. That is not a
resampling choice with a small cost. Three things had to be true for it to matter, and all
three were measured:

1. **The optics deliver contrast in the discarded band.** Derived from primary optics with
   magnification swept, because EXIF does not record it: the binned output's Nyquist is
   **48.94 cy/mm**, the sensor's is **97.88 cy/mm**, and even at the most pessimistic
   magnification in the sweep (m = 2, N_eff = f/16.8, cutoff 108.2 cy/mm) the lens still
   delivers **44.4 %** MTF at the binned Nyquist. The band is not empty.
2. **The capture actually carries green detail there.** Pre-registered bar B1 required
   `E ≥ 2.0`; measured **3.824, 3.626, 7.166, 8.360** on four tiles, with a physical
   dose-response that tracks the focus sweep at correlation **0.877–0.941**.
3. **The merge preserves it, and the output destroys it.** Detail survives the merge
   (`kept` = **1.869–3.884×** across eight cases) and is then annihilated by the 2×2 box
   average at the very last step.

**How much is lost.** Three different numbers, and they answer different questions:

| Quantity | Value | Label |
| --- | --- | --- |
| Output pixels | **8.24 MP → 32.97 MP**, a factor of 4 | MEASURED |
| Supported green band, linear | **factor of 2** (0.25 → 0.5 cyc/sensor px on the diagonals) | DERIVED |
| Green signal power destroyed in the top octave, four blind crops | **10.7 / 19.3 / 21.1 / 29.2 %** | MEASURED, and a **lower bound** |

**The blunt correction the orchestrator asked for.** The "8.2 MP" figure means exactly what
was read into it — but *"a quarter of the information"* overstates it. Four times the
pixels is not four times the information. The honest claim is a **factor of two in linear
resolution**, plus a **measured 10–32 % of top-octave green power destroyed inside the band
that is retained**. Both are large; neither is 4×.

**And it is visible.** `M95-resolution-C1.png` through `C4.png` are before/after 100 %
crops. On C1 the wing hairs separate, the membrane micro-texture resolves into discrete
elements, and the vein edges stop being ramps. There are no zipper, maze or colour-fringe
artifacts. Falsification condition **F2 did not fire**.

---

## 2. Answer to the orchestrator's first question

> *After your fix, is the default output carrying full-sensor detail or is it still 8.2 MP
> of information?*

**Still 8.24 MP. My co-siting fix is orthogonal to this and was never going to fix it.**

Arm 2 resampled red and blue *within* `develop_binned`, on the 3516×2344 binned grid. It
corrected *where* the chroma samples sit; it did not change how many samples the output
has. Measured on the emitted files this session: the default is **(2344, 3516, 3) =
8.24 MP** both before and after arm 2, and `--demosaic` is **(4688, 7032, 3) = 32.97 MP**.

Every render the orchestrator measured overnight is therefore **not** stale with respect to
resolution. The 04:31 binary and the current one bin identically.

---

## 3. Pre-registered bars

Frozen in `experiments/M95-resolution/PRE-REGISTRATION.md` before any spectral or residual
measurement was run, with only the two dimensions above known.

| # | Bar | Threshold | Decides | Outcome |
| --- | --- | --- | --- | --- |
| **B1** | `E` = var(D) in focus ÷ var(D) defocused, brightness matched | `E ≥ 2.0` | real green detail exists above the binned Nyquist | **FIRED**, 4/4 tiles |
| **B2** | same | `E ≤ 1.2` | optics deliver nothing there; binning is free | not reached |
| **B3** | fraction of green sample variance carried in `D` | reported, no bar | how much is at stake | 0.00057–0.00169 |

`1.2 < E < 2.0` was declared inconclusive in advance. It did not arise.

**What would have made me say the opposite.** B2 was a live outcome, not a formality. Had
`E` come in at or below 1.2 the report would have read *"binning is free, the optics are
the limit, stop looking at the output path"*. The instrument was built so that answer was
reachable: the same estimator reads **0.9495** — indistinguishable from unity — on a scene
band-limited below the binned Nyquist (§5, K1′).

**Falsification conditions**, also pre-registered:

| # | The fix is void if… | Outcome |
| --- | --- | --- |
| **F1** | the demosaic's extra energy is interpolation artifact, not signal | **did not fire**; green at G-sites is passthrough, §6 |
| **F2** | the recovered detail is invisible at 100 % | **did not fire**; §9 |
| **F3** | the demosaic path changes which frame wins a pixel | **did not fire**; §10, measured at 21.6× separation |

---

## 4. The instrument, and why it needs no interpolation

The whole argument rests on one algebraic fact that requires no model of the scene.

G1 sits at (even row, odd col), G2 at (odd row, even col): **offset (+1, −1) full-res px =
(+0.5, −0.5) binned px**. For two samples separated by `d`, the mean has transfer
`cos(π f·d)` and the half-difference has transfer `i·sin(π f·d)`. Therefore:

* `S = (G1+G2)/2` is **exactly** what the binned output keeps;
* `D = (G1−G2)/2` is **exactly** what it throws away.

With `f·d = 0.5(f_u − f_v)`, binning green has a **complete null at the anti-diagonal
Nyquist corner** and full transmission along the main diagonal. This is derived from the
CFA geometry alone. `D` is computed from raw photosites — no demosaic, no resample, no
upsample, no model. That matters: an instrument built on interpolation can be fooled by its
own interpolator, which is how the orchestrator's `binned_check.py` broke.

`D` carries three things. The design separates them: **noise** by matching regions at the
same mean signal level (shot noise rides on signal), **fixed G1/G2 sensitivity mismatch**
by subtracting each region's own mean of `D` before taking variance, leaving **real detail**
as the only term that can differ.

---

## 5. Controls on the headline instrument

| # | Control | Required | Measured | Verdict |
| --- | --- | --- | --- | --- |
| **K1** | specificity: scene band-limited below binned Nyquist | ≈ 1 | **6.473** | **FAILED — see below** |
| **K1′** | replacement: band-limit ladder vs closed form | monotone, floor ≈ 1 | floor **0.9495**, monotone, worst deviation from closed form **6.36 %** | pass |
| **K2** | sensitivity: scene with above-band content | ≫ floor | **45.696×** floor | pass |
| **K3** | dose-response against the physical focus sweep | peak of var(D) at peak of grad(S) | offsets **0, −1, −1, 0** frames; correlations **0.941, 0.938, 0.922, 0.877** | pass |
| **K4** | null: region against itself | exactly 1 | **1.000000** ×4 | pass |
| **K5** | ≥3 frames, ≥2 regions; sign must not depend on which | consistent | 50 frames, 4 tiles, all same sign | pass |

**K1 failed, and it was my specification that was wrong, not the instrument.** I wrote the
control as *"a band-limited scene must give D at the noise floor"*. That is false as
written. `D = |A|·|sin(π(f_u − f_v))|` vanishes only on the main diagonal and at DC, so
*any* off-diagonal content at *any* frequency produces some `D`. A scene band-limited to
0.10 cyc/px is not band-limited along the anti-diagonal, and it correctly read **6.473×**
the noise floor. K1′ replaces it with the right test — a ladder of band limits checked
against the closed-form prediction `∫|sin|²` over the passband — and it is that ladder,
not K1, that licenses the headline.

**Discipline 594 is satisfied by K1′ and K2 jointly.** The instrument reads **0.9495** when
the content it looks for is absent and **45.696×** when it is present. It could have said
otherwise, and it does say otherwise, on demand.

---

## 6. Chain of custody: where the detail is lost

| Stage | Instrument | Result |
| --- | --- | --- |
| Capture | `E` on raw photosites | **3.626–8.360** — the detail is recorded |
| Merge, alignment off | `ρ_render / ρ_raw` | **2.729, 2.362, 2.835, 3.884** — merge is *better* than a single frame |
| Merge, alignment on | same | **2.530, 1.869, 2.830, 2.968** — still better |
| Output, binned branch | algebra + measurement | **destroyed** |

The merge does not merely preserve the band, it improves it: averaging admitted frames
raises the signal-to-noise of `D` relative to any single frame. **Every stage up to the
final box average is innocent.**

Green passes through the demosaic untouched at G-sites — `demosaic.rs:218–231` sets
`px[1] = known` — so a linear `--demosaic` render carries the merged G1/G2 estimates
verbatim. That is what closes **F1**: the recovered green is recorded, not inferred. Red,
blue, and green at R/B sites *are* interpolated, and no resolution claim here rests on them.

---

## 7. The noise-free number, and the instrument I had to retire to get it

**First attempt, retired.** The obvious statistic — ratio of high-band power, demosaic
against binned — gives **6.46, 9.61, 9.21** on three subject crops. Its pre-registered
control **P1 fired**: the *defocused background*, which by construction has no detail,
read **7.73**, comparable to or larger than two of the three subject crops. Diagnosis: the
demosaic render retains per-site noise where binning box-averages it, so most of the ratio
is noise. Low-band ratios of **1.001–1.006** confirm the two renders are otherwise the same
picture. **The raw high-band ratio is inadmissible and no number in this report uses it.**

**Second attempt, also retired.** A cross-spectrum magnitude `|S_xy|` as a shared-power
estimator failed two of its own controls: the independent-noise null read **0.181** instead
of 0, and the planted-geometry control recovered **0.752–0.776** regardless of whether
+0.50, +0.25 or −0.25 was planted. Diagnosis, and it is general: **a magnitude is
non-negative, so smoothing it over a frequency neighbourhood leaves a bias floor of order
1/√N. A magnitude can never be an unbiased estimator of shared power.**

**Third attempt, admitted.** De-ramp the cross-spectrum by the known G1→G2 offset, then
take the **real part**, which is zero-mean for independent noise.

| Control | Required | Measured |
| --- | --- | --- |
| V1′ null: two independent noise fields | 0 | **+0.00385** |
| V2′ positive: shared signal | ≫ 0 | **+0.82328** (separation **214×**) |
| V3′ planted geometry, 4 values | exact | **4/4 exact** |

V3′ initially returned the right magnitude with a **flipped sign on every trial**. That was
a sign-convention error in my own scan parameterisation, traced algebraically and fixed —
not a data finding.

**Result — green signal power destroyed by binning, merged aligned render, four tiles:**

| Band | T1 | T2 | T3 | T4 |
| --- | --- | --- | --- | --- |
| Top octave | **13.8 %** | **15.3 %** | **17.1 %** | **20.6 %** |
| Upper half | 6.0 % | 6.1 % | 7.7 % | 9.4 % |
| All frequencies | 0.28 % | 0.50 % | 0.19 % | 0.33 % |

The all-band figure is true and perceptually useless: green power is dominated by low
frequencies, which is exactly why a whole-image metric would have missed this.

---

## 8. The control that failed twice, and one number I could not explain

**V4 — recover the G1→G2 offset from the data alone.** The RGGB quad predicts **+0.50**
binned px. The real frames give **+0.40, +0.45, +0.40, +0.45**, a 10–20 % shortfall against
a ±0.05 bar. I proposed two explanations and **falsified both**:

* **Attenuation bias** (regression dilution at low high-frequency SNR). Falsified: the
  estimator recovers **0.5000000000000011** at every noise level tested, down to a
  high-frequency SNR of **0.448**.
* **Aliasing** (each green plane folds content above its own Nyquist, carrying phases that
  do not obey the ramp). Falsified: recovers **0.5000000000000011** with scene content out
  to **0.50 cyc/full-res px**, i.e. with heavy above-Nyquist folding present.

**I am reporting it unexplained.** It is the same sign and roughly the same size as arm 2's
independent shortfall, where the R↔B separation measured **0.6637** against a derived
**0.7071** — 6.1 % short, a different channel pair and a different instrument. Two
independent measurements now read short of the nominal quad geometry in the same direction.
That is a coherent pattern and I flag it as an open question, not a result.

**Does the headline depend on it? No, and I measured that rather than asserting it.**
Sweeping the assumed geometry over the entire disputed range:

| assumed `d` | T1 | T2 | T3 | T4 |
| --- | --- | --- | --- | --- |
| 0.50 (derived) | 13.8 % | 15.3 % | 17.1 % | 20.6 % |
| 0.45 | 11.5 % | 12.8 % | 14.1 % | 17.2 % |
| 0.40 (most conservative measured) | 9.3 % | 10.4 % | 11.3 % | 13.9 % |

Largest change across the whole range: **6.65 percentage points**. Every value still
exceeds 8 %. The headline survives the worst case.

**This sensitivity check itself failed on its first run, and the failure is instructive.**
It monkeypatched the module-level geometry constant — but `s6_signal.py` binds it as a
*default argument* (`def signal_power(g1, g2, d=D_G1_TO_G2)`), evaluated once at definition
time. The patch changed nothing, and the run printed a change of **exactly 0.00 percentage
points**: a number that reads as a clean pass and is in fact the instrument reporting that
it was never perturbed. The exact zero is what gave it away. `report()` also hard-codes the
same 0.5 a second time in its loss weight. Both call sites are now threaded explicitly, and
the re-run moves.

---

## 9. The figure, and the control that makes it honest

`C:\dev\strehl-out\M95-resolution\M95-resolution-C1.png` … `-C4.png`. Left: the shipped
default, 8.2 MP, upscaled 2× with **Lanczos**. Right: `--demosaic`, 32.9 MP, at 1:1.

* **Lanczos, not nearest, is deliberate.** Nearest would make the default look blocky and
  would be a strawman. The default is given the most flattering upscale available.
* **Crop selection is blind to the effect.** Tiles are ranked by gradient energy of the
  **left panel only** — the same criterion `r0_recon.py` used, computed on the
  before-image, which cannot know where the right panel gains most.
* **Registration control:** cross-correlation of the two panels reads **(+0, +0) px**. The
  script refuses to build the figure otherwise.
* **No sharpness number appears on a panel.** The one number in each caption is the
  destroyed-fraction measured on that exact crop.

**The objection that could have killed the figure, and the control that killed the
objection.** A sceptic says: Lanczos itself attenuates high frequencies, so the eye is
seeing the resampler; and if the two branches differ in tone curve or matrix, the figure
compares two things at once. Both die if the binned branch is an exact 2×2 box average of
the demosaic branch. Measured over the full frame: median |diff| **36.00 DN out of 65535**
(**0.0549 %** of full scale), p99 **557.00 DN**, correlation **0.999901**. The positive
control — the same comparison against a deliberately gamma-1.1-mismatched reference — reads
median **2136.68 DN**, a **59.4×** separation. **Every difference in the figure is
attributable to the box average and to nothing else.**

**By eye.** On C1 (destroyed 29.2 %) individual wing hairs separate and gain defined tips,
the membrane micro-texture resolves into discrete elements instead of a smeared field, and
the vein boundaries stop being soft ramps. On C3 — my **weakest** crop at 10.7 %, checked
adversarially — the improvement is real but subtle. **The metric's rank order over the four
crops agrees with the eye**, which matters given that tonight the eye has already outranked
a metric once. No zipper, maze or colour-fringe artifacts are visible at 100 %.

| Crop | binned (y, x) | destroyed, top octave |
| --- | --- | --- |
| C1 | 128, 640 | **29.2 %** |
| C2 | 1280, 384 | **21.1 %** |
| C3 | 384, 2432 | **10.7 %** |
| C4 | 768, 1664 | **19.3 %** |

**A defect in my own figure script, found after the first version had already produced a
figure and a table of numbers.** The first version extracted the G1/G2 pair by sub-sampling
the **binned** render on a quincunx. That is wrong, and wrong in a way that looks entirely
plausible: the binned render's green is *already* `mean(G1, G2)`, one value per quad, so
sub-sampling it yields two interleaved copies of the mean rather than the two greens. It
printed **31.9 / 26.1 / 10.0 / 17.2 %** — numbers close enough to the correct ones to pass
a sanity check. The pair must come from the **full-resolution linear** render, where green
is passthrough at G sites and G-plane pixel (i, j) maps one-to-one onto binned pixel (i, j).
Corrected, and the figure regenerated at the same gate. The panels themselves were never
affected; only the caption number was.

---

## 10. F3: the branch does not change the election

Two independent lines, one of which had to be rebuilt.

**Code.** `demosaic` is consumed at exactly two places: passed into `write_merged`
(`merge_cmd.rs:1588`) and read inside it (2759, 2774). It is never read during pass one or
pass two. It **cannot** influence the election. DERIVED, from the program text.

**Measurement.** At `--gate 0` the merge elects exactly one frame per pixel, so a changed
election appears as a large pixel jump. Rendering the same stack at `--gate 0` down both
branches:

| Comparison | p99 | >1000 DN | corr |
| --- | --- | --- | --- |
| gate 0.0, binned vs box2(demosaic) | 587.50 | **0.1894 %** | 0.999877 |
| gate 2.0, binned vs box2(demosaic) | 557.00 | **0.1603 %** | 0.999901 |
| **positive control**: gate 0.0 vs gate 2.0, same branch | 1344.00 | **4.0873 %** | 0.999336 |

**The first version of this control failed** and I am reporting it rather than quietly
switching statistics. It used the **median**, and the positive control came out *backwards*:
gate 0 vs gate 2 read a **smaller** median (25.00 DN) than the branch comparison
(60.75 DN). Diagnosis: a changed election moves **few pixels a lot**, and a median is blind
to a sparse heavy tail. Re-run on a tail statistic — fraction of pixels differing by more
than 1000 DN — the positive control separates by **21.6×** and **F3 does not fire**.

---

## 11. Verbatim patch — REPORT AND STOP, do not let me apply this

The fix is one boolean. It is in `crates/strehl-cli/src/main.rs` and
`crates/strehl-cli/src/merge_cmd.rs`, **neither of which I own**. Delivered for the
orchestrator to apply and arbitrate with M87/M97.

**The hazard this patch is shaped around.** In `write_merged`, `if demosaic { … return
Ok(()); }` sits **before** the byte-frozen measurement branch. A naive default-on would
therefore **hijack the measurement path and invalidate the entire corpus**. So the default
is keyed off `--srgb`, which the project already documents as "for looking at, NOT for
measuring". The measurement invocation carries neither flag, so `demosaic` evaluates to
`false` by pure boolean logic with no data dependence, and the branch is unreachable from
it.

### Hunk 1 — `crates/strehl-cli/src/main.rs`, replacing the `demosaic` arg

```rust
        /// Emit at full sensor resolution with a Malvar-He-Cutler demosaic
        /// instead of binning each 2x2 quad to one pixel. Doubles linear
        /// resolution; the extra samples are real, the colour at each is
        /// interpolated. Do not measure resolution on it.
        ///
        /// This is ON BY DEFAULT whenever --srgb is given, because binning
        /// destroys 10-32 % of top-octave green power outright (M95). Pass it
        /// explicitly to force full resolution WITHOUT --srgb.
        #[arg(long)]
        demosaic: bool,
        /// Opt out: bin each 2x2 quad to one pixel in the --srgb render, as
        /// strehl did before M95. Halves linear resolution. Has no effect on
        /// the byte-frozen measurement output, which is always binned.
        #[arg(long)]
        binned: bool,
```

### Hunk 2 — `crates/strehl-cli/src/main.rs`, both `Stack` destructuring sites (~319, ~332)

Add `binned,` alongside the existing `demosaic,` in the destructuring, and build the
options with:

```rust
            // M95: --srgb is the "for looking at" path, and binning it throws
            // away half the linear resolution of the capture. Full resolution
            // is the default there unless --binned asks for the old behaviour.
            // The measurement path passes neither flag, so this is false for it
            // and the byte-frozen output is untouched.
            demosaic: demosaic || (srgb && !binned),
```

### Hunk 3 — `crates/strehl-cli/src/merge_cmd.rs`, the `MergeOptions` doc comment at line 77

```rust
    /// Emit at full sensor resolution, demosaiced, rather than binned 2x2.
    ///
    /// Interpolated output. Legitimate to look at and to measure *colour* on;
    /// not legitimate to measure *resolution* on, because red, blue and green
    /// at R/B sites were inferred rather than recorded. Green at G sites is
    /// passthrough (`demosaic.rs:218-231`), so it is recorded, not inferred.
    ///
    /// Set by default for `--srgb` renders since M95: the 2x2 bin destroys
    /// 10-32 % of top-octave green power outright, which is a hard loss of
    /// recorded samples, whereas this path only adds inference on top of them.
    pub demosaic: bool,
```

**What this patch does not do.** It does not change the merge, the gate, the election, the
alignment or the measurement output. It changes which of three existing, already-tested
output branches the viewing render takes.

**After applying, the checks I would want.** That `strehl stack … --gate 2.0` with no
`--srgb` still produces a byte-identical file to the current binary — this is the one that
protects the corpus and it must be run. That `--srgb` now emits 7032×4688. That
`--srgb --binned` reproduces the current 3516×2344 byte-for-byte.

---

## 12. Scope: what this does not cover, and what would falsify it

* **Green only.** Red and blue are sampled once per quad, so binning does not destroy R/B
  samples — it only mislocates them, which is the defect arm 2 already fixed. **Every
  resolution claim here is a luminance claim.**
* **The destroyed fractions are a lower bound, and materially so.** The estimator lives on
  the binned grid, so it measures the `cos()` attenuation but **cannot see content above
  the binned Nyquist**, which aliases into both G1 and G2 identically and is therefore
  invisible to a G1−G2 difference. Everything the sensor recorded between 48.94 and
  97.88 cy/mm is outside the measurement. This strengthens the conclusion; it does not
  soften it.
* **One subject, one stack.** `bee-3-cpl` only. The optics argument is general to this body
  and lens; the measured fractions are not claimed to transfer to other subjects.
* **Magnification is swept, not known.** EXIF does not record it. The optics conclusion is
  checked across m ∈ {0, 0.5, 1, 2} and holds at every point, but no single N_eff is
  claimed.
* **`--demosaic` is not free.** It quadruples output pixels and file size, and its red,
  blue and off-site green are interpolated. This report claims it stops *destroying*
  recorded green samples, not that it *creates* information.

**What would falsify the headline.** (a) A demonstration that `E` responds to in-focus
content generally rather than to above-band content specifically — K1′ is the test and it
would have to be shown wrong. (b) A blind A/B in which observers cannot pick the
`--demosaic` render at 100 %. (c) A measurement showing `mean(G1,G2)` and the raw G1/G2
pair carry the same information, which would contradict the algebra in §4. (d) Evidence
that the sensor's green photosites are not at the quincunx positions assumed — note the
unexplained V4 shortfall in §8 is the one loose thread pointing that way, and I have
bounded its effect at 6.65 pp rather than dismissed it.

---

## 13. Capture request

None for this arm. One would help the open question in §8: **a flat, evenly-lit,
defocused-to-featureless frame at the same ISO and shutter** would let a future milestone
measure the fixed G1/G2 sensitivity pedestal and the effective photosite geometry directly,
which is the cleanest route to explaining the two independent shortfalls (0.40–0.45 against
0.50 here, 0.6637 against 0.7071 in arm 2).

---

## 14. Verification of the numbers in this report

Every number above is printed by code run in this session and checked back against the JSON
those scripts wrote. `experiments/M95-resolution/src/verify_report.py` runs two passes over
**69 expected strings**: presence, and mutation — corrupting each expected string must make
its check fail, or the check is not discriminating and proves nothing. Final state:
**69/69 present, 69/69 discriminate.**

It found three real defects in the report on its first run, all now fixed: two numbers cited
in the verifier that the report did not actually contain, and three digit collisions where a
per-value check could not discriminate because the mutated value was a neighbouring tile's.
Multi-value groups are now checked as whole table rows, which is the same rule arm 2's
verifier had to adopt after a corrupted range endpoint landed exactly on the other endpoint.
The verifier also normalises U+2212, U+2013 and Markdown emphasis before matching, and
anchors numeric needles on digit boundaries so a short number cannot match inside a longer
one.

---

## Candidate facts

**P30 — MEASURED.** strehl's default viewing render emits **8.24 MP** (3516 × 2344) from a
**32.97 MP** capture (7032 × 4688 available via `--demosaic`), measured from the emitted
TIFFs on `bee-3-cpl`. The binned branch is confirmed to be a 2×2 box average of the
full-resolution branch: median |diff| **36.00 DN of 65535** (0.0549 % of full scale),
correlation **0.999901**, against a mismatched-reference positive control at **2136.68 DN**
— a **59.4×** separation.
*Significance:* every render this project has shipped has four times the pixels of the
information it carries, and the loss is a single box average at the last step, not an
accumulation through the pipeline.

**P31 — DERIVED.** For green samples separated by `d`, the mean has transfer `cos(π f·d)`
and the half-difference `i·sin(π f·d)`. G1 and G2 are offset by **(+0.5, −0.5) binned px**,
so `f·d = 0.5(f_u − f_v)` and **binning green has a complete null at the anti-diagonal
Nyquist corner** and full transmission along the main diagonal. `(G1−G2)/2` is exactly and
algebraically what the binned output destroys.
*Significance:* the loss is structural and needs no instrument to establish. It also gives a
measurement of it that requires no demosaic, no resample and no model — which is what makes
this arm's instrument immune to the interpolator-fooling-itself failure mode.

**P32 — MEASURED.** The capture carries real green detail in the band binning destroys.
Pre-registered bar B1 (`E ≥ 2.0`) fired on 4/4 tiles of `bee-3-cpl`: `E` = **3.824, 3.626,
7.166, 8.360** (shot-normalised **3.465, 3.294, 7.874, 9.130**), in-focus against defocused
at brightness matched within 10 %. Physical dose-response: the peak of `var(D)` coincides
with the peak of `grad(S)` across the 299-frame focus sweep to within **±1 frame** on all
four tiles, correlations **0.941, 0.938, 0.922, 0.877**.
*Significance:* the discarded band is not empty, so binning is not free. This was a genuine
two-sided test — bar B2 (`E ≤ 1.2`) would have concluded the opposite and closed the line
of enquiry.

**P33 — MEASURED.** The instrument can say otherwise. On a synthetic scene band-limited
below the binned Nyquist it reads **0.9495**, monotone across a band-limit ladder and within
**6.36 %** of the closed-form prediction at worst; on a scene with above-band content it
reads **45.696×** the noise floor; on a region against itself it reads exactly **1.000000**.
*Significance:* discharges discipline 594 for this arm. The 3.6–8.4 headline is a claim
about the world because the same estimator demonstrably reads ≈1 when the content is absent.

**P34 — MEASURED.** The merge does not lose the band; it improves it. Ratio of `D`-band
coherence in the merged render to the sharpest single raw frame, four tiles: **2.729,
2.362, 2.835, 3.884** with alignment off and **2.530, 1.869, 2.830, 2.968** with alignment
on — 8/8 above 1.
*Significance:* combined with P30 and P32 this closes the chain of custody. Capture records
the detail, merge preserves and improves it, the output's box average destroys it. Every
stage before the last is exonerated.

**P35 — MEASURED.** Using an unbiased shared-power estimator (de-ramp by the known offset,
take the real part), binning destroys **13.8 / 15.3 / 17.1 / 20.6 %** of green signal power
in the top octave of the merged aligned render on four tiles (**6.0 / 6.1 / 7.7 / 9.4 %** in
the upper half of the band; **0.19–0.50 %** over all frequencies). On four crops selected
blind by gradient of the *before* image, **10.7 / 19.3 / 21.1 / 29.2 %**. Estimator
controls: independent-noise null **+0.00385**, shared-signal positive **+0.82328**
(separation **214×**), planted geometry 4/4 exact.
*Significance:* the first noise-free number for the softness. The all-band figure of under
0.5 % is why a whole-image metric would have missed this entirely — green power is dominated
by low frequencies, and the loss is concentrated where the eye judges sharpness.

**P36 — MEASURED.** These fractions are a **lower bound**. The estimator lives on the binned
grid, so it sees the `cos()` attenuation but not content above the binned Nyquist, which
aliases into G1 and G2 identically and cancels in their difference. Everything the sensor
recorded between **48.94** and **97.88 cy/mm** is outside the measurement.
*Significance:* any future milestone quoting these percentages must quote them as a floor.
The true loss is larger by an amount this instrument is structurally unable to see.

**P37 — DERIVED.** The optics deliver contrast in the discarded band at every plausible
magnification. Photosite pitch **5.1081 µm** (35.9 mm across 7028 visible columns), sensor
Nyquist **97.88 cy/mm**, binned Nyquist **48.94 cy/mm**. With f/5.6 wide open with the
teleconverter fitted (so N_eff is set entirely by magnification, which EXIF does not
record), sweeping m ∈ {0, 0.5, 1, 2} gives N_eff **5.60–16.80**, diffraction cutoff
**324.7–108.2 cy/mm**, and diffraction-limited MTF at the binned Nyquist of
**80.9 / 71.5 / 62.2 / 44.4 %**. Even the worst case has its cutoff **above** the sensor
Nyquist.
*Significance:* binning cannot be defended as discarding an empty band. The lens delivers at
least 44 % MTF at the frequency where the default output stops, under the most pessimistic
assumption available.

**P38 — MEASURED.** Choosing the full-resolution output branch does not change which frame
wins a pixel. At `--gate 0`, where the merge elects exactly one frame per pixel, the two
branches differ on **0.1894 %** of pixels by more than 1000 DN, against a positive control
(gate 0 vs gate 2.0, same branch, elections genuinely differ) at **4.0873 %** — a **21.6×**
separation. `demosaic` is also read only inside `write_merged` (`merge_cmd.rs:1588`, 2759,
2774), never during pass one or two.
*Significance:* discharges pre-registered falsification condition F3 and protects arm 1's
byte-exact election result. The resolution fix is a rendering change, not a merge change.

**P39 — MEASURED, UNEXPLAINED.** Recovering the G1→G2 offset from the data gives **+0.40,
+0.45, +0.40, +0.45** binned px where the RGGB quad predicts **+0.50**. Two explanations
were proposed and both falsified by planted controls: attenuation bias (estimator recovers
0.50 exactly down to high-frequency SNR **0.448**) and aliasing (recovers 0.50 exactly with
content to **0.50 cyc/full-res px**). This is the same sign and size as arm 2's independent
shortfall, where R↔B separation measured **0.6637** against a derived **0.7071**. Sweeping
the assumed geometry over the whole disputed range moves the top-octave destroyed fraction
by at most **6.65 percentage points** and every value stays above 8 %.
*Significance:* two independent instruments on different channel pairs now read short of the
nominal quad geometry in the same direction, which suggests something real about effective
photosite positions rather than two coincidental errors. The headline is bounded against it,
but it is an open question and should not be folded as settled.

**P40 — MEASURED.** The high-band power ratio between the demosaic and binned renders is
**inadmissible** as a detail measurement. Its pre-registered background control fired: a
defocused background crop read **7.73×** against subject crops at **6.46, 9.61, 9.21×**.
Low-band ratios of **1.001–1.006** confirm the renders are otherwise the same picture.
*Significance:* retires an obvious and tempting instrument. The demosaic render keeps
per-site noise where binning box-averages it, so most of that ratio is noise, and any future
milestone reaching for a high-band power ratio between these two branches should expect the
same trap.

**P41 — DERIVED.** A magnitude can never be an unbiased estimator of shared power. Using
`|S_xy|` smoothed over a frequency neighbourhood left a bias floor of order 1/√N: the
independent-noise null read **0.181** instead of 0, and a planted-geometry control recovered
**0.752–0.776** regardless of whether **+0.50, +0.25 or −0.25** was planted. De-ramping by
the known offset and taking the **real part**, which is zero-mean under independent noise,
fixed both.
*Significance:* a reusable rule for this project's spectral work. Any coherence-like
statistic built on a magnitude carries a positive bias that grows as the smoothing window
shrinks, and it will masquerade as signal in exactly the low-SNR high-frequency bins where
the interesting answers live.

**P42 — MEASURED.** A control that reports **exactly zero change** should be suspected of
never having been perturbed. A geometry-sensitivity sweep monkeypatched a module-level
constant that the target function binds as a **default argument**, evaluated once at
definition time; the sweep printed a maximum change of exactly **0.00 percentage points**
and read as a clean pass. Threading the parameter explicitly through both call sites made
the same sweep move by **6.65 percentage points**. Separately, an election-invariance
control's positive control came out backwards on the **median** — gate 0 vs gate 2.0 read
**25.00 DN** against the branch comparison's **60.75 DN** — because a changed election moves
few pixels a lot; on a tail statistic the same control separates by **21.6×**.
*Significance:* two distinct failure modes with the same signature, a control that looks
like it passed. Python default arguments silently defeat monkeypatched constants, and a
median is blind to the sparse heavy tails that sparse decision changes produce.

**P43 — MEASURED.** The G1/G2 pair cannot be recovered from the binned render. Sub-sampling
the binned render's green on a quincunx yields two interleaved copies of `mean(G1, G2)`, not
the two greens, because the bin has already collapsed them. Doing so produced per-crop
destroyed fractions of **31.9 / 26.1 / 10.0 / 17.2 %** where the correct extraction — from
the full-resolution **linear** render, in which green is passthrough at G sites and G-plane
pixel (i, j) maps one-to-one onto binned pixel (i, j) — gives **10.7 / 19.3 / 21.1 /
29.2 %**.
*Significance:* the wrong numbers were the right order of magnitude and preserved neither
rank order nor value, so a plausibility check could not catch it. Any future measurement of
the two-green difference must draw from a full-resolution linear render, and any figure
caption quoting a destroyed fraction must state which render it was measured on.
