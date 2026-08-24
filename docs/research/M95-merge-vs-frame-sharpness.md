# M95 — Is the merge losing sharpness? Merged output vs. the frame that went in

**Milestone:** M95 (merge-vs-frame arm)
**Pinned build:** `1f17c1d547a996d05a412570a9257894005d786b`, built once to
`C:\dev\strehl-out\M95-pin\target\release\strehl.exe` and used for every render below.
**Subject:** `D:\personal\macro\bee-3-cpl`, 299 frames, ILCE-7CM2 + `FE 100mm F2.8 Macro
GM OSS + 2X Teleconverter`, f/5.6, ISO 100, 1/6 s.
**Code:** `experiments/M95-merge-vs-frame/`. **Images:** `C:\dev\strehl-out\M95-merge-vs-frame\`.

---

## 0. Renumber: this milestone was dispatched as M93 and is now M95

**Read this before filing, because part of it is already in the history.**

I was dispatched as **M93**. That stem was already taken: `docs/research/M93-election-gate.md`
was added by a different agent in commit `9a17d64` ("M93: pre-register the election gate…"),
which predates my dispatch, and that agent has since committed again on the same stem
(`9b316d1`) and owns `crates/strehl-cli/examples/m93-election.rs` and
`experiments/M93-election/`. I never touched any of those.

I detected the collision at the start of my run and defended against it with a distinct
*slug* (`M93-merge-vs-frame`), which avoided a file-level clobber but not the stem
clash. The orchestrator has since corrected the allocation and **reassigned me to M95**.

**What that means for the history, stated plainly:**

- I had **already committed under M93 names**, as `b782da5`
  ("M93 (merge-vs-frame): the merge loses nothing; the softness is upstream"), 37 files.
  That commit is in the history and **I did not rewrite it.**
- The renumber was done as a forward `git mv` in a later commit: 38 tracked paths moved
  from `M93-merge-vs-frame*` to `M95-merge-vs-frame*`, plus `m93lib.py` → `m95lib.py`.
- Internal references were rewritten by
  `experiments/M95-merge-vs-frame/src/renumber_m93_to_m95.py`, which is an **ordered
  token map with protected tokens**, not a blind search-and-replace: **50 substitutions
  applied, 48 occurrences deliberately left alone.** The protected set is the other
  agent's identifiers (`M93-election-gate`, `M93-election`, `m93-election`) and the
  on-disk scratch paths `C:\dev\strehl-out\M93-out` and `M93-frames`.
- **The scratch directories keep their M93 names on purpose.** The orchestrator's own
  `experiments/ORCH-drift-check/m93pair.py` reads `C:\dev\strehl-out\M93-out` and its
  `m93_crops.npy` / `m93_elected_*.npy` by absolute path. Renaming them would have
  silently broken a live script for a cosmetic gain. The **deliverable** image directory
  *was* renamed, to `C:\dev\strehl-out\M95-merge-vs-frame\`.
- Every number in this report was re-verified after the renumber; see §7.3.

**Rule 41 (stem allocation) still failed here**, and the failure mode is worth keeping
even though this instance is resolved: the collision was invisible to both agents at
dispatch time and was only caught because one of them went looking. See P16.

**Corpus-write disclosure.** `warpmap.txt` sidecars now exist inside
`D:\personal\macro\bee-3-cpl` and `bee-2-cpl`. They were written by a sibling agent, not
by me. My runs read that sidecar (§8) and write nothing under `D:\`.

---

## 1. Headline

> **The merge is not losing sharpness.** At `--gate 0` the merged output is
> byte-identical to the frame that won each pixel:
> 180,697 pixels across 47 frame/ROI combinations, 100.0000 % exact, maximum difference 0 DN of 65535.
> **The softness the owner sees is upstream of the merge.**

There is no room in that number for a lost detail. The gather/elect/render path does
not filter, does not interpolate, does not average, and does not round: where frame *k*
was elected, the output byte *is* frame *k*'s byte.

That is a negative result on the question I was given, and it is the whole point of
having asked it. It retires the second of the two suspects M85 named. Combined with
fact 1196 (the gate is not the cause) and fact 1145 (nor is the occlusion halo), **every
part of the combination stage is now eliminated.**

The same session found where the sharpness actually goes, and it is not subtle:

> **strehl's default output is binned.** It emits one pixel per 2×2 Bayer quad —
> 3516×2344 = 8.2 MP from a 32.9 MP capture — placing the output Nyquist at
> 48.94 cy/mm, where this lens still delivers **42–62 % MTF** (§9). The detail
> above that limit is measurably present in the raw: in in-focus regions the
> G1−G2 difference carries **1.78–2.65× the sd the noise model predicts**, of which
> **68.5–85.8 % of the variance is scene, not noise**, against **1.09×** in a
> defocused control (§10). The binning averages real, resolved detail away.

I did not set out to find that. It is what the controls for the primary question kept
running into.

---

## 2. Pre-registered bars, and the verdict against them

Frozen in `experiments/M95-merge-vs-frame/PRE-REGISTRATION.md`, committed as `573b170`
**before any merge-vs-frame comparison number existed**. Quoted verbatim:

> - **CONCLUDE THE MERGE LOSES SHARPNESS** if `σ_eq ≥ 0.25 px` on **≥ 2 of the 3**
>   detail ROIs, under both the raw and the noise-subtracted reduction, and stable
>   across the peak ± 2 frame neighbourhood.
> - **CONCLUDE THE MERGE DOES NOT LOSE SHARPNESS** if `σ_eq ≤ 0.10 px` on **all
>   three** detail ROIs under both reductions.
> - **INDETERMINATE** otherwise, and it will be reported as indeterminate rather
>   than argued in either direction.

**Verdict on the pre-registered axis: the axis was retired as confounded, not passed
and not failed.** The measured `σ_eq` (M relative to F, at the peak frame) was
**−0.7504 / −0.4846 / −0.5587 px** raw and **−0.8595 / −0.5045 / −0.5857 px**
noise-subtracted (`out/s6_spectral.json`, key `PRIMARY`). Negative means the merge read
*sharper* than the frame, by a large margin, on every ROI and under both reductions.

**I am not reporting that as a result, because I do not believe it, and I can say why.**
Arm M is unaligned. Fact 1177's drift is real and large on this stack: from the
`warpmap.txt` similarity fit, corner displacement spans **28.5 to 240.7 plane px**
across the sequence (`out/s1_drift.json`). Inside one 512×512 window the merge is
therefore a **collage** of frames translated by up to ~25 px relative to one another,
and every seam between two elected frames injects broadband high-frequency energy that
a power spectrum reads as sharpness. The metric was measuring seams.

The pre-registration anticipated a confound in the aligned arms and stratified ROIs by
radius for it. It did not anticipate that the confound would attack arm M itself. That
is a design miss and I am recording it as one.

**What replaced it.** Because arm M at `--gate 0` averages exactly one frame per pixel,
the merged TIFF is a *readable record of the election* — a far stronger instrument than
any spectral ratio, and one that needs no access to `merge.rs`. §4 sets it out. It
answers the pre-registered question directly and with no confound: not "is the merge
about as sharp as the frame" but "is the merge's output the frame's bytes". It is.

---

## 3. Setup

### 3.1 Arms

All five rendered by the one pinned binary. `n_eff` and singleton fraction are read from
each run's own log, this session:

| arm | invocation | mean `n_eff` | `n_eff = 1` |
|---|---|---:|---:|
| **M** | `STREHL_ALIGN=0 … --gate 0` | 1.000 | 100.00 % |
| **M4** | `STREHL_ALIGN=0 … --gate 4` | 60.860 | 35.02 % |
| **C** | `… --gate 0`, alignment ON | 1.000 | 100.00 % |
| **Z** | `STREHL_ALIGN=zoom … --gate 0` | 1.000 | 100.00 % |
| **F** | one frame, same flags | — | — |

The M/M4 pair independently reproduces fact 1196's ladder endpoints: **1.000 → 60.860**,
a 60.9× change in frames averaged per pixel, on the same subject.

### 3.2 ROIs — and the selection defect that had to be fixed first

Pre-registration step 3 scored windows on "a 20-frame subsample of the stack". **That
rule is wrong and the data caught it.** The chosen flat control turned out to have
**61.8× through-focus contrast with a 7-frame FWHM**: a genuinely detailed feature whose
focus peak fell *between* the 20 sampled frames. The coarse scan had aliased past it.
A "flat" control that is actually the sharpest thing in the frame would have inverted
rule 9's entire purpose.

Fixed by re-selecting against **all 299 frames** via a running per-pixel max-detail map
(`src/s2b_rois.py`). Final ROIs, 512×512 on the binned plane:

| ROI | plane (x,y) | peak detail | peak frame | focus contrast | FWHM |
|---|---|---:|---:|---:|---:|
| ROI-LOWDRIFT | (320, 64) | 51814 | 183 | 27.5× | 27 |
| ROI-MIDDRIFT | (320, 1344) | 29387 | 145 | 36.0× | 15 |
| ROI-HIGHDRIFT | (2624, 576) | 45394 | 144 | 47.1× | 18 |
| ROI-FLAT (control) | (64, 576) | 850 | 103 | **1.18×** | 148 |

The replacement flat control has **61× less peak detail** and 1.18× focus contrast. Its
top-5 frames are `[103, 24, 18, 102, 12]` — non-contiguous, i.e. noise, which is what a
flat control should look like. The three detail ROIs have contiguous top-5 sets.

---

## 4. The decisive instrument

At `--gate 0` with `STREHL_ALIGN=0` there is **no resampler in the path** and exactly
one frame contributes to each output pixel. So each merged pixel must equal the
*byte-exact* value that the same binary writes when handed that one frame alone.

The test needs no knowledge of `merge.rs`:

1. Render arm F for each frame of interest — the identical binary, decode, black/white
   levels, white balance, binning, writer, grid and crop.
2. For every merged pixel, find which rendered frames reproduce its value exactly.
3. Where the match is unique, that is the election, read out of the output file.
4. Then invert it: for each frame, take the pixels it won and ask whether the merged
   values there are exactly that frame's render.

Step 4 is the answer to the milestone question.

**Why this is stronger than any spectral comparison.** A spectral ratio asks whether two
images have similar statistics. This asks whether they are the same numbers. There is no
band, no window, no fit, no noise floor and no confound from drift, because it never
compares different scene content — it compares a pixel to itself.

---

## 5. Result — fidelity

### 5.1 The headline test (`out/s5b_election_checks.json`, CHECK 1)

For each ROI, every frame that won ≥ 200 pixels; compare merged against that frame's
own arm-F render on exactly its elected pixels.

| ROI | frames tested | pixels | min fraction exact | max abs diff |
|---|---:|---:|---:|---:|
| ROI-LOWDRIFT | 12 | 57,977 | 1.000000 | 0 DN |
| ROI-MIDDRIFT | 16 | 59,648 | 1.000000 | 0 DN |
| ROI-HIGHDRIFT | 19 | 63,072 | 1.000000 | 0 DN |
| **total** | **47** | **180,697** | **1.000000** | **0 DN** |

Not "close". Not "within a quantisation step". **Identical.**

### 5.2 Coverage: does every merged pixel come from a frame?

| ROI | matches *some* frame | distinct frames elected |
|---|---:|---:|
| ROI-LOWDRIFT | 99.9413 % | 288 |
| ROI-MIDDRIFT | 99.9409 % | 292 |
| ROI-HIGHDRIFT | 99.9676 % | 195 |
| ROI-FLAT | 99.9176 % | 298 |

The 0.03–0.08 % residual is rounding, not loss: median distance to the nearest frame
value is **1 DN**, and 99.35–100 % of non-matching pixels are within 2 DN. One outlier
at 30 DN in ROI-LOWDRIFT out of 154 such pixels.

### 5.3 Is the election a depth map or noise?

195–292 distinct frames per 512×512 window sounds alarming. It is not: the election is
a smooth surface. Against a 5×5 median of the election map,

- median deviation **0.00 frames**, p90 **0.0 frames**, on all four ROIs;
- pixels electing a frame further than **half the focus FWHM** from their neighbours:
  **0.81 % / 0.52 % / 0.44 %** on the detail ROIs, **2.04 %** on the flat control.

That is a depth map. The count is high because the depth ramp sweeps continuously
through the stack: in the figure's 360×360 crop, exactly one frame (183) wins **3.07 %**
of pixels, which is what a smooth ramp across ~30 frames looks like.

---

## 6. The deliverable image

`C:\dev\strehl-out\M95-merge-vs-frame\M95-merged-vs-single-frame.png`

Four panels on the identical 360×360 binned-plane crop at (415, 84), shown 2× nearest
neighbour, sRGB transfer for viewing only — every measurement above was on linear data.

- **A** — merged, `--gate 0`, alignment off, 299 frames.
- **B** — single frame 183 (`DSC00184.ARW`), same binary, decode, levels and writer.
- **C** — `|A − B|` at 40×, with the pixels frame 183 won outlined in red. **Inside that
  outline: 3979 / 3979 byte-identical, max difference 0 DN.** Outside it the merge chose
  a different frame, so of course they differ — that is the merge doing its job.
- **D** — the same frame through `--demosaic`, full sensor grid, same subject area and
  same display size. This is the sampling the default output does not keep.

No sharpness number appears on any panel. The only numbers on the panels are the
byte-identity count — measured on exactly those pixels, by `src/s11_figure.py`, in this
session — and frame indices.

A second image, `M95-election-map.png`, renders the election read out of the merged
file for ROI-LOWDRIFT.

**A defect in my own figure, recorded.** The first version selected pixels where the
election was within ±2 of frame 183 and compared them against frame 183 alone. It
reported 3738 / 23192 identical, max difference 6393 DN — which looked like a
catastrophic fidelity failure and was entirely my error: pixels that elected frames 181,
182, 184, 185 are not supposed to equal frame 183. Restricting to `elected == 183` gives
3979 / 3979 at 0 DN. **The first number was a bug in the figure script, not a
measurement, and it is only in this report so that it cannot be mistaken for one later.**

---

## 7. Controls

Every control, including the six that failed.

### 7.1 Passed

| id | control | result |
|---|---|---|
| **R4** | loader (rule 32): arm F vs. an independent `rawpy` decode + my own binning | implied black **511.99988**, range **14847.99984**, max abs diff **1 DN** of 65535, **99.9763 %** exact, residual rms 0.289 DN. **PASS** |
| **R5** | determinism: arm M rendered twice | sha256 `895e458d…5288` **identical**. **PASS** |
| **R6a** | elected vs. unelected frame | frame 183 matches **100.0000 %** where elected; unelected frame 36 matches **0.0519 %** ROI-wide. **PASS** |
| **R6b** | one-pixel shift of the merged plane | "matches some frame" collapses **99.9413 % → 10.1360 %** (9.9×). **PASS** |
| **R6c** | plant +3 DN on a 64×64 patch of arm F | candidate matches collapse **4453 → 80**. **PASS** |
| **R1a** | discipline 594: plant a known blur, frequency-domain exact | recovers σ = 0.10–1.50 px to within **0.04 %** worst case. **PASS** |
| **R1b** | same, noise-subtracted reduction | within **28.7 %** over 0.10–1.00 px; **41.0 %** at 1.50 px, outside the ±25 % bar and reported as such. |
| **R2** | discipline 595 power control: M vs. deliberately defocused frames | monotone. ROI-MIDDRIFT σ_eq −0.485 (peak) → −0.765/−0.802 (±10) → −0.874/−0.880 (±25). The comparison has power in the direction of the test. |
| **R3** | rule 9 flat control | σ_eq −0.6350; model white-noise PSD 9768.5 vs. measured plateau 11419.1 (1.169×). Reported, **not** interpreted as retention (fact 1127). |
| **C2** | isotropy null on synthetic isotropic noise | diag/axis **1.0025**. **PASS** |
| **C3** | planted quincunx diamond vs. planted circles | diamond `A` = **1.50 × 10⁻¹²**, hard circle **0.9836**, diffraction circle **0.9978** — ~10¹² separation. **PASS** |
| **C4** | identity resample, k = 1.0 | max abs difference out vs. in = **0.0**, exactly. **PASS** |
| **C5** | planted Gaussian through the resample measurement | σ 0.25/0.50/1.00 recovered to **−0.94 %**. **PASS** |
| **R7** | G1−G2 vs. the calibrated noise model | §10. |
| **V1** | **numeric integrity** — every load-bearing number in this report is re-read from its source JSON by `src/verify_report.py`, which prints the report value beside the source value | **all checks OK.** |
| **V2** | **negative control on V1** (`src/control_verifier2.py`) — plant a single wrong digit into a copy of the report, require the verifier to go red | **18 / 18 planted errors caught**; report restored byte-identical; post-restore green. **PASS** |

### 7.2 Failed — and what each failure meant

**F1 — ROI selection aliased past a focus peak.** §3.2. The pre-registered 20-frame
subsample selected as "flat" a window with 61.8× focus contrast and a 7-frame FWHM.
*Meaning:* the rule was under-sampled relative to the depth-of-field of this optic.
*Fix:* re-select against all 299 frames. **The pre-registration's ROI rule is defective
and should not be reused as written.**

**F2 — R1's stimulus was mislabelled, not its instrument.** Planting blur with
`scipy.ndimage.gaussian_filter(σ=0.25)` gave a recovered 0.021 px, a −91 % error that
read as a failed instrument. It was not. scipy's truncated discrete kernel at σ = 0.25
is ≈ `[3.4e-4, 0.99933, 3.4e-4]`, whose true second moment is **0.026 px**. The
instrument reported 0.021. It was right; my label was wrong.
*Meaning:* below roughly σ = 0.5 px a discrete Gaussian is not the Gaussian you named.
*Fix:* plant in the frequency domain with amplitude `exp(−2π²σ²f²)`, exact by
construction. **Anyone planting sub-pixel blur in this corpus should do the same.**

**F3 — S7's geometry control failed on 2 of 3 ROIs.** Cross-correlating arm M against
arms C and Z gave offsets (0, +37), (+147, −46), (−1, +2) — mutually inconsistent with
any global affine. *Meaning:* content mismatch, not geometry: arm M is a collage. *Fix:*
retire the C/Z-vs-M sharpness comparison entirely and derive the resample cost
analytically instead (§8). **The provisional numbers (Z vs M +0.192/+0.432/−0.211;
C vs M +0.275/+0.495/−0.206) are not admissible and are recorded only so nobody
resurrects them.**

**F4 — the `knee` statistic was retired.** My first floor statistic read **0.973** on a
planted quincunx diamond whose ground truth is **1.414**. *Meaning:* it degenerates —
a hard spectral cut sets the floor to zero, so a `1.15 × floor` threshold is passed by
every bin. *Fix:* replaced by a normalised sector-power ratio (§9).

**F5 — I planted the diamond in the wrong place.** The C3 diamond used
`|fx| + |fy| ≤ 0.3536` instead of `≤ 0.5`, putting the cut band outside both measurement
sectors; the circle arm then read 0.484 instead of ≈1. *Meaning:* a control that fails
because the *control* is wrong is indistinguishable from a broken statistic until you
look. *Fix:* corrected the plant; C3 then passed as tabled above.

**F6 — C6 failed, and my first explanation for it was wrong.** The measured resample
MTF read **1.0360**, above unity. My first hypothesis was interpolation imaging
replicas, so I built a band-limited stimulus to remove them. It changed the number by
**1.1 × 10⁻⁷** — the hypothesis was refuted by its own control. Diagnosis from the data:
the maximum sits at **f = 0.0361 cy/px**, in the lowest radial bins where the radial
average has too few FFT samples to be stable. Restricted to f ≥ 0.10 cy/px the maximum
is **1.0036**. *Meaning:* the failure was statistic instability at low radial bins, not
physics. And, separately: `k = 1.074 > 1` means **no** source content aliases, so there
were never any replicas to remove — the band-limited control was right to say nothing
happened.

**F7 — the verifier left the headline uncovered, and only the control found it.**
`verify_report.py` initially checked the fidelity result by looking for the substring
`**0 DN**`. That string occurs in the §5.1 table *and* the number also appears in the
headline as `0 DN of 65535`. Mutating the **headline** to `1 DN of 65535` left the
verifier **green**: the single most load-bearing number in the report was unverified.
*Meaning:* a bare-substring check over a document that quotes the same figure at several
sites verifies whichever site it happens to hit, and silently licenses the rest to drift.
Four numbers turned out to be quoted at 2–4 sites each. *Fix:* every repeated figure is
now checked at each site with a context-anchored needle, and the headline is checked as
one literal sentence assembled from the source JSON.

**F8 — the control's own anchors were broken twice.** First by line wrap: an anchor of
the form `spans **<value>×** across the stack` matched **0 times**, because the hard wrap
falls between `across` and `the`. Then by blockquote markers: after joining tokens on
`\s+`, the headline anchor still matched 0 times, because the wrapped line begins `> `.
*Meaning:* both failures presented as "anchor not unique", i.e. as a *report* defect,
when the defect was in the control. *Fix:* anchors compile to
`\s+(?:>\s*)?`-joined regexes, the substitution is spliced back into the matched span so
wrapping survives, and a non-unique anchor **hard-errors** instead of quietly passing.
*Footnote, because it is the same lesson twice:* writing this section reproduced F7 —
quoting a checked figure verbatim inside the prose that documents it created a second
site, and the control went red until the quotation was written with the value elided.

### 7.3 Re-verification after the M93 → M95 renumber

The renumber (§0) rewrote paths inside 24 files, including the report itself and the
verifier that checks it. That is exactly the kind of edit that can quietly break a
checker into vacuous success, so both were re-run afterwards rather than assumed:

| Check | Result after renumber |
| --- | --- |
| `verify_report.py` — every load-bearing number re-read from `out/*.json` | ALL VERIFIED |
| `control_verifier2.py` — planted single-digit errors caught | 18 / 18 |
| `control_verifier2.py` — baseline and post-restore, unmutated | GREEN, GREEN |
| Report restored after mutation | byte-identical |

The mutation control is the load-bearing one here. A path rewrite that silently pointed
the verifier at a missing JSON, or at the wrong report, would still print a green
`verify_report.py` if the checker degraded to "no anchors matched, nothing to fail"; the
control rules that out by requiring the checker to go **red** on demand.

---

## 8. The resample — the only step with a measurable cost

The aligned path prints `field of view scaled to 0.9315`, i.e. an upsample of
**k = 1.07354**, resampled Catmull-Rom. Since F3 killed the image-domain comparison,
I implemented the separable 4-tap Keys cubic (a = −1/2) myself, pushed noise through it,
and measured its transfer (`src/s12_resample.py`).

| f (cy/px) | kernel `H(f)` | with source-grid replicas | measured |
|---:|---:|---:|---:|
| 0.103 | 0.9979 | 0.9979 | 0.9946 |
| 0.197 | 0.9743 | 0.9747 | 0.9758 |
| 0.247 | 0.9414 | 0.9433 | 0.9524 |
| 0.297 | 0.8888 | 0.8956 | 0.9094 |
| 0.397 | 0.7220 | 0.7703 | 0.7842 |

The bare kernel CTFT under-predicts at high frequency because a resampler evaluates the
kernel at a source-grid *phase* that varies per output pixel, so the phase-averaged power
transfer is `Σ_n |H(f+n)|²`. Adding those replicas cuts the worst deviation from
**0.0623 to 0.0406** over 0.05–0.40 cy/px, and at 0.40 cy/px from +8.6 % to +1.8 %.

**Equivalent Gaussian σ of one resample, fitted over 0.05–0.40 cy/px:
measured 0.2558 px** (kernel-only 0.2908, with replicas 0.2706). Over the narrower
0.05–0.25 cy/px band, 0.1807 px.

So: alignment costs about **σ ≈ 0.26 px** of blur, once, and the merge costs **zero**.
That is the whole of the pipeline's measurable sharpness budget on this path. It is not
enough to explain "those stacks don't look too good yet".

---

## 9. Second arm — the 74 cy/mm floor

### 9.1 Optics, re-derived from primary EXIF this session

Read with `exifread` from the subject's own files, not taken on report:

`ILCE-7CM2`; `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`; `FNumber 28/5` = **5.6**;
`MaxApertureValue 159/32` → **f/5.60**; `FocalLength 200`; ISO 100; 1/6 s. There is **no**
`FocalPlaneXResolution` tag.

**f/5.6 is wide open with the teleconverter fitted.** There is zero aperture headroom:
stopping down is not available as a remedy, and the diffraction limit below is a floor
on the *best case*, not on a chosen setting.

Pitch is therefore derived, not read: CFA 7028×4688 over a 35.9 mm active width gives
**5.1081 µm** (bracket 5.066–5.122). Hence **full-res Nyquist 97.88 cy/mm**, and —
because the default output is binned — **binned Nyquist 48.94 cy/mm**.

Working magnification is unknown for this stack, so it is carried as an interval rather
than imported: m ∈ {2.0, 2.72, 2.8} × pupil factor p ∈ {1.31, 1.62, 1.94}, giving
N_eff = N(1 + m/p) ∈ **11.37–17.57** and incoherent cutoff f_c = 1/(λN_eff) ∈
**103.5–159.9 cy/mm** at λ = 0.55 µm. (I did **not** import M84b's ruler-rig
m = 2.7198; it is a different rig and saying so is the point.)

Incoherent circular-pupil MTF at the three frequencies that matter:

| | min | max |
|---|---:|---:|
| MTF @ 74 cy/mm (M85's floor) | **0.175** | **0.432** |
| MTF @ binned Nyquist 48.94 | **0.421** | **0.616** |
| MTF @ full-res Nyquist 97.88 | 0.015 | 0.272 |

The 74 cy/mm row **independently reproduces M85 §7's 19–34 %** from primary EXIF, by a
different route. That is a genuine cross-check, and M85's number survives it.

### 9.2 Is the floor the green quincunx? No.

The hypothesis: the green channel of a Bayer array samples on a quincunx, whose Nyquist
is a **diamond** — 69.21 cy/mm on the diagonals, 97.88 on the axes, radial mean 77.67 —
which brackets M85's measured 69.7–80.9 cy/mm floor almost too well.

Test statistic, after F4 retired the first one:

`A = [P_diag / P_axis]_{0.38–0.46 cy/px} ÷ [P_diag / P_axis]_{0.10–0.20}`, sectors ±12°.
A quincunx cut predicts **A ≈ 0**; isotropic optics predict **A ≈ 1**. C3 validates the
separation at ~10¹² (§7.1).

**Measured, demosaiced:** `A` = **0.8955 / 4.6273 / 0.7985**, flat control **1.5180**.
**Measured, binned plane:** **0.6380 / 2.2372 / 0.6308 / 1.0079**.

**Quincunx refuted.** Nothing reads near zero; two ROIs read *above* 1.

*Limitation, stated plainly:* `A` is unstable when the scene is strongly anisotropic at
low frequency. ROI-MIDDRIFT's reference band is 0.1298, which is what drives its 4.63.
The statistic separates "diamond" from "not diamond" robustly; it does not measure the
degree of anisotropy reliably on real scenes.

### 9.3 So what is the plateau?

Aliased scene detail, not a fixed artifact. Across the stack, the high-frequency plateau
of a **detail** ROI spans **3.2015×** with focus; the **flat control** spans **1.2081×**.
A floor imposed by demosaic, resampling or the merge would not track focus. One imposed
by the scene's own content folding past Nyquist does.

---

## 10. Where the sharpness actually goes

The binned default discards real, resolved detail. Test (`R7`): compare the two green
sites of each Bayer quad. `G1 − G2` samples structure at a scale the binned output
averages out. Its sd is predicted by the calibrated noise model (`profile.rs` /
`noise.rs`, ISO 100, measured green gain **0.224103** DN/e⁻, read noise 4.20 e⁻).

| ROI | frame | signal (DN) | predicted sd | measured sd | ratio | scene share of variance |
|---|---:|---:|---:|---:|---:|---:|
| ROI-LOWDRIFT | 183 | 3142.0 | 18.78 | 49.81 | **2.65×** | **85.8 %** |
| ROI-MIDDRIFT | 145 | 2448.6 | 16.58 | 38.39 | **2.32×** | **81.4 %** |
| ROI-HIGHDRIFT | 144 | 2795.2 | 17.71 | 31.56 | **1.78×** | **68.5 %** |
| ROI-FLAT (control) | 103 | 4471.1 | 22.39 | 24.31 | **1.09×** | 15.1 % |

The flat control is the discipline-595 power control for this claim: handed a region
with no resolved detail, the same statistic reads 1.09×. It could have said otherwise
and it did not.

Combined with §9.1 — MTF **0.42–0.62** at the binned Nyquist — the picture is
consistent: the optic is delivering resolvable contrast well above the frequency where
the default output stops sampling.

---

## 11. Scope, and what would falsify this

### What the fidelity result covers
One subject (`bee-3-cpl`, 299 frames), one gate setting (`--gate 0`), alignment **off**,
the binned linear camera-native output path, three detail ROIs plus one flat control,
47 frame/ROI combinations, 180,697 pixels.

### What it does **not** cover
1. **Gate > 0.** At `--gate 4` the merge averages 60.86 frames per pixel and byte
   identity is not even meaningful. Fact 1196 covers that axis; this milestone does not.
2. **The aligned path.** Arm C resamples. Its cost is characterised analytically and
   numerically in §8 (σ ≈ 0.26 px) but was **never measured on this image**, because F3
   killed the comparison. This is the largest remaining gap.
3. **Election quality.** I proved the merge faithfully emits *the frame it chose*. I did
   **not** prove it chooses the *best* frame. The election-quality (oracle) test was
   designed and not run. If the focus measure systematically elects a slightly-defocused
   frame, every result here still holds and the output is still soft.
4. **Any other stack.** M52 measured the gate achieving a given `n_eff` varying 28.9×
   across the corpus. Nothing here transfers without re-running.
5. **The demosaic path.** Measured for the floor statistic only; not for fidelity.

### What would falsify the headline
A single frame/ROI combination at `--gate 0`, alignment off, where merged pixels on that
frame's elected set differ from its arm-F render by even 1 DN, with the loader control
(R4) still passing. The test is `src/s5b_checks.py` CHECK 1 and it is cheap to re-run.

### What would falsify the binning claim
`R7`'s ratio dropping to ≈1 on detail ROIs under a corrected noise model — i.e. if the
G1−G2 excess is really an uncalibrated gain or PRNU term rather than scene structure.
The flat control argues against that (it would inflate there too, and it reads 1.09×),
but a direct check against a defocused *flat-field* capture would settle it, which is
the capture request below.

---

## 12. Capture request

I cannot write `docs/captures-needed.md` (orchestrator's file). Requesting:

1. **A low-drift stack.** Same subject class, same optic, with the rail motion minimised
   or the subject re-framed so inter-frame displacement stays under ~2 px. This is the
   only way to measure the aligned path's real price on an image: arm M must stop being
   a collage before it can be compared with arm C. **This unblocks gap 2 above and it is
   the highest-value capture I can name.**
2. **A slanted-edge or bar target at this exact magnification**, f/5.6, same teleconverter.
   Would convert §9.1's m-interval into a measured N_eff and turn the whole MTF table
   from DERIVED into MEASURED.
3. **A defocused flat field** (uniform illumination, lens defocused) at ISO 100, same
   exposure. Would let R7 separate scene structure from PRNU directly, closing the
   falsification route in §11.

---

## 13. Patches for files I do not own

**None required.** Every measurement here was made with the shipped binary at a pinned
sha, from python, without modifying `merge.rs`, `align.rs`, `stack.rs`, `lib.rs` or
`main.rs`. I made no change to any file I own either — `image_out.rs`, `color.rs` and
`demosaic.rs` are untouched.

The one change this work argues for is a **product** decision, not a bug fix, and I am
deliberately not writing it as a patch: **the default binned output is discarding
detail the optic resolves** (§9.1, §10). Whether to change the default, add an opt-in
full-resolution mode, or leave it is the owner's call and touches `merge.rs` and
`main.rs`, both contended. §10's numbers are the evidence for that conversation.

---

## Candidate facts

**P1 — MEASURED.** At `--gate 0` with alignment off, every merged pixel is
**byte-identical** to the frame that won it: 47 frame/ROI combinations, 180,697 pixels
on `bee-3-cpl`, minimum fraction exact **1.000000**, maximum absolute difference
**0 DN of 65535**.
*Significance:* the gather/elect/render path destroys no detail whatsoever. Together
with facts 1196 and 1145 this eliminates the combination stage entirely as a cause of
soft output. The softness is upstream of the merge.

**P2 — MEASURED.** 99.9176–99.9676 % of merged pixels at `--gate 0` equal *some* frame's
rendered value exactly; the residual differs from the nearest frame value by a median of
**1 DN**, with 99.35–100 % within 2 DN.
*Significance:* the merged file at `--gate 0` is a complete, readable record of the
election, and the residual is rounding. This makes the election auditable from the output
alone, with no access to `merge.rs`.

**P3 — MEASURED.** The election at `--gate 0` is a smooth depth map, not noise: against a
5×5 median, median deviation **0.00** frames and p90 **0.0** frames on all four ROIs;
only **0.81 / 0.52 / 0.44 %** of detail-ROI pixels elect a frame more than half the focus
FWHM from their neighbours (flat control 2.04 %). 195–292 distinct frames are elected per
512×512 window because the depth ramp is continuous.
*Significance:* a high distinct-frame count is not evidence of a noisy selector.

**P4 — MEASURED.** strehl's default output is binned to one pixel per 2×2 Bayer quad:
**3516×2344 = 8.2 MP from a 32.9 MP capture**, putting the output Nyquist at
**48.94 cy/mm** against the sensor's 97.88 cy/mm.
*Significance:* a 4× pixel-count reduction applied before any measurement of output
sharpness. Every corpus number measured on the default path is measured below this limit.

**P5 — MEASURED.** In in-focus regions the per-quad **G1 − G2** difference carries
**1.78–2.65×** the sd the calibrated ISO-100 noise model predicts, i.e. **68.5–85.8 %** of
its variance is scene structure; the defocused flat control reads **1.09×** (15.1 %).
*Significance:* detail below the binned sampling scale is measurably present in the raw
frames and the default output averages it away. The flat control is the discipline-595
power control and it could have said otherwise.

**P6 — DERIVED.** For `bee-3-cpl` (`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`,
`FNumber 28/5` = 5.6, `MaxApertureValue 159/32` → f/5.60, so **wide open with zero
aperture headroom**), pitch **5.1081 µm** (no `FocalPlaneXResolution` tag; derived from
7028 px over 35.9 mm). Over m ∈ {2.0, 2.72, 2.8} × pupil ∈ {1.31, 1.62, 1.94}:
N_eff **11.37–17.57**, f_c **103.5–159.9 cy/mm**, and incoherent MTF
**0.421–0.616 at the binned Nyquist**, **0.175–0.432 at 74 cy/mm**,
**0.015–0.272 at the full-res Nyquist**.
*Significance:* independently reproduces M85 §7's 19–34 % at 74 cy/mm from primary EXIF
by a different route, and shows the lens still delivers 42–62 % contrast at the frequency
where the default output stops sampling. Stopping down is not available as a remedy.

**P7 — MEASURED.** The 74 cy/mm artifact floor is **not** the green quincunx. A
normalised diagonal/axis sector-power ratio `A` (validated by a planted diamond reading
**1.50 × 10⁻¹²** against planted circles at **0.9836** and **0.9978**) measures
**0.8955 / 4.6273 / 0.7985** demosaiced and **0.6380 / 2.2372 / 0.6308** binned, against
a quincunx prediction of ≈0.
*Significance:* retires the leading structural explanation for M85's floor. The floor
reads isotropic, consistent with optics plus aliasing.

**P8 — MEASURED.** The high-frequency plateau tracks focus: it spans **3.2015×** across
the stack on a detail ROI but only **1.2081×** on the flat control.
*Significance:* the plateau is aliased scene detail, not a fixed artifact injected by
demosaic, resampling or the merge. Corroborates P7.

**P9 — DERIVED, numerically validated.** One Catmull-Rom resample at the aligner's
measured **k = 1.07354** upsample costs an equivalent Gaussian of **σ = 0.2558 px**
(measured; 0.2908 kernel-only, 0.2706 with source-grid replicas), fitted over
0.05–0.40 cy/px — MTF **0.995 / 0.952 / 0.784** at 0.10 / 0.25 / 0.40 cy/px.
*Significance:* the only measurable sharpness cost anywhere in the pipeline, and it is
small. Bare `|H(f)|` under-predicts because a phase-varying resampler transfers
`Σ_n |H(f+n)|²`; including replicas cuts the worst deviation from 0.0623 to 0.0406.

**P10 — MEASURED.** On `bee-3-cpl` the unaligned merge at `--gate 0` is a **collage**:
from `warpmap.txt`, corner displacement spans **28.5–240.7 plane px** across 299 frames,
so a 512×512 window mixes frames offset by up to ~25 px. Its seams inject broadband
high-frequency energy, making the unaligned merge read **σ_eq = −0.48 to −0.86 px**
*sharper* than any single frame on a power-spectrum metric.
*Significance:* **any spectral sharpness comparison against an unaligned strehl merge on
a high-drift stack is confounded and will report a spurious sharpness gain.** This
invalidated M95's own pre-registered axis and it will invalidate others.

**P11 — MEASURED.** Selecting a rule-9 flat control from a coarse frame subsample can
alias past a focus peak. A 20-frame subsample of a 299-frame stack selected as "flat" a
window with **61.8× through-focus contrast and a 7-frame FWHM**; re-selection against all
299 frames found a control with 61× less peak detail and **1.18×** contrast.
*Significance:* flat-control selection must be sampled finer than the stack's
depth-of-field, or rule 9's control is silently inverted.

**P12 — MEASURED.** `scipy.ndimage.gaussian_filter` is not a usable positive control
below about σ = 0.5 px: at a nominal σ = 0.25 the truncated discrete kernel is
≈ `[3.4e-4, 0.99933, 3.4e-4]`, true second moment **0.026 px**, and an instrument
correctly reporting 0.021 px looks like a −91 % failure.
*Significance:* discipline 594 requires planting a *known* effect. Sub-pixel blur must be
planted in the frequency domain (`exp(−2π²σ²f²)`), which recovers σ = 0.10–1.50 px to
within **0.04 %**.

**P13 — MEASURED.** A radially averaged PSD ratio is unstable in its lowest bins: a
resample MTF that must not exceed 1 read **1.0360** at f = 0.0361 cy/px but **1.0036**
for f ≥ 0.10 cy/px. A band-limited stimulus changed the value by **1.1 × 10⁻⁷**,
refuting the imaging-replica explanation.
*Significance:* radial-PSD statistics in this corpus should be read only above
~0.10 cy/px, and low-bin excursions are bin-count noise rather than physics.

**P14 — MEASURED.** Independently reproduces fact 1196's ladder endpoints on
`bee-3-cpl`: `--gate 0` gives mean `n_eff` **1.000** with **100.00 %** of pixels
singleton; `--gate 4` gives **60.860** and **35.02 %**.
*Significance:* confirms the gate axis at a different sha, by a different agent, with a
freshly pinned build.

**P15 — MEASURED.** Rule-32 loader control: strehl's binned linear output is reproduced
from an independent `rawpy` decode by
`out = floor(clip((green_mean − 512)/14848, 0, 1) × 65535 + 0.5)` to **99.9763 %** exact,
max **1 DN**, implied black **511.99988** and range **14847.99984**.
*Significance:* the byte-exact fidelity test (P1) rests on this; it also gives any future
milestone a validated route to predict strehl's output from outside the binary.

**P16 — ARGUED.** Milestone stem `M93` was allocated to at least two independent agents:
`docs/research/M93-election-gate.md` + `experiments/M93-election/` (introduced in commit
`9a17d64`, before my dispatch) and this work, which was dispatched as M93 and committed
once under that stem as `b782da5` before the orchestrator reassigned it to **M95**.
The collision was invisible to both agents at dispatch and was caught only because one of
them searched the tree for its own stem before writing.
*Significance:* rule 41 (stem allocation) did not hold under concurrency, and a stem
search performed by the *agent* is currently the only thing that catches it. The
recovery is cheap while it is caught early — a forward `git mv` plus a protected-token
reference rewrite, no history rewrite — but it is not cheap once two milestones have
folded into the corpus index under one stem.

**P17 — MEASURED.** A report-number verifier that searches for bare substrings verifies
only whichever site it happens to hit. In this report four figures were quoted at 2–4
sites each, and mutating the **headline's** copy of the fidelity result left the verifier
green. Re-anchored per site, a mutation control catches **18 / 18** planted single-digit
errors.
*Significance:* any corpus document whose numbers are machine-checked needs the check
anchored per occurrence, and the checker needs its own mutation control. Anchors must
also tolerate hard wrap and blockquote markers — matching `\s+`-joined tokens alone still
misses quoted text, and both failure modes present as a *report* defect rather than a
*checker* defect.
