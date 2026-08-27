import io
P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\V-REVIEW-noise-verification.md"
T = """

## 15. Was the comparator input denoised? No — and the premise was inverted

Pre-registered in `experiments/V-REVIEW/PREREG-nr.md`, committed as `f5b0e2e0`
before any probe was run.

### 15.1 The converter, named

The RAW-to-TIFF step that feeds `enfuse` and `focus-stack` is not a third-party
converter. It is **strehl's own decoder**, pin `740e7056`, sha
`15EA7346...A7B0` — verified by `Get-FileHash -SHA256` and equal to the SHIP-V3
corpus seal. It is invoked by `experiments/V-LINEAR/develop_frames.ps1` as a
one-frame `stack ... --linear-srgb --demosaic` with `STREHL_ALIGN=0`, producing
63 frames of 197,798,923 bytes each at `C:\\dev\\strehl-out\\V-LINEAR\\lintiff\\`.

**This is the same binary that rendered the strehl arm.** Both sides of the
head-to-head share the decoder bit for bit, so a decoder-level denoiser cannot
produce an asymmetry between them. That is structural and it already answers the
confound, but this project does not accept an argument from absence, so it was
measured anyway.

### 15.2 A defective search, caught by its own control

The first pass reported no denoise function anywhere in `crates/`. **That result
was an artifact of a broken query.** `Select-String -Path 'crates\\**\\*.rs'` does
not recurse in PowerShell. The positive control — search for a function that is
known to exist — returned `demosaic-ish fn definitions found: 0`, and a parallel
count found one `STREHL_*` environment variable where eleven were known. The
control caught it; the null was discarded and re-run under ripgrep, where the
same control returns eleven `demosaic` definitions.

Re-run correctly, three candidate forms were searched and all are empty: no NR
function in `crates/`, no config-file reader, and a complete dependency set —
`anyhow`, `thiserror`, `rayon`, `clap`, `tracing`, `rawler`, `tiff` — that
contains no image-processing library able to denoise.

### 15.3 The discriminator, and commissioning against a real denoiser

Chroma noise reduction works by averaging chroma over a neighbourhood, so its
unavoidable fingerprint is chroma noise correlated far beyond the demosaic
kernel's support. **D1** is the radius at which the normalised autocorrelation
of the high-passed chroma plane falls below 0.10, median over the 110 vetted
census tiles.

Commissioning did not use a synthetic blur. The identical `.ARW` was developed
twice through `rawpy`/LibRaw — once with all NR off, once with **FBDD full plus
two median passes** — so the probe was tested against a production denoiser
working on the same photons. All three pre-registered arms passed. MEASURED:

| commissioning arm | luma | R-Y | B-Y | required | result |
| --- | --- | --- | --- | --- | --- |
| C1 null, same frame twice | 1.64 | 2.19 | 2.23 | ratio exactly 1.000 | pass |
| C2 potency, FBDD full | 1.67 | 2.69 | 2.77 | chroma must separate | pass |
| C2 as a ratio to reference | 1.016x | 1.228x | 1.242x | greater than 1.15x | pass |
| C3 floor, white noise | 0.88 | 0.88 | 0.88 | shortest measured | pass |

The potency arm moved **chroma** by 23 to 24 percent and **luma** by 1.6
percent. FBDD is a chroma denoiser, so the probe responded in the correct
channel and not merely in the correct direction. That is the stronger result.

### 15.4 Result: no noise reduction was applied

MEASURED, D1 in pixels, 110 tiles, subject `113MSDCF`, frame `DSC00001`:

| development | luma | R-Y | B-Y |
| --- | --- | --- | --- |
| LibRaw, all NR off (reference) | 1.64 | 2.19 | 2.23 |
| **strehl `740e7056` (the comparator input)** | **1.48** | **2.27** | **2.24** |
| LibRaw, FBDD full (denoised) | 1.67 | 2.69 | 2.77 |

The comparator input sits **on the undenoised reference on both chroma
channels** — 2.27 against 2.19, and 2.24 against 2.23 — and nowhere near the
denoised arm at 2.69 and 2.77. On luma it reads *shorter* than the reference,
which is the signature of a sharper demosaic, the opposite of denoising.

**Verdict: NO NOISE REDUCTION. The confound is excluded.** The comparator inputs
were not denoised, so the six cells compare two merges.

### 15.5 The premise was inverted, and it matters more than the verdict

The task described the six cells as showing that "we are measurably noisier than
both comparators," with chroma "consistently worse for us." **Both statements
are backwards.** Every ratio in the published table is comparator-over-strehl,
printed as *cleaner*, and `vn_table.py` says so in its own docstring.

Stated as absolute sigma, where no orientation can be misread — MEASURED, same
gauge, same tiles, sigma times 1000, **lower is cleaner**:

| arm | Y | R-Y | B-Y |
| --- | --- | --- | --- |
| **strehl** | **52.96** | **60.70** | **56.01** |
| strehl in the 8-bit container | 68.75 | 88.02 | 88.29 |
| `enfuse` | 85.70 | 110.04 | 89.97 |
| `focus-stack` | 101.41 | 146.19 | 144.84 |

**strehl is the cleanest arm on all three channels.** These reproduce the
published cells exactly — 1.618, 1.813 and 1.606 against `enfuse` — which is an
internal control on the whole section.

Two consequences follow.

- **There is no noise deficit to close.** A build lane sent to fix it would be
  chasing a sign error.
- **The NR hypothesis was pointed the wrong way from the start.** A denoiser
  running on the comparator inputs would make the comparators *cleaner* and
  shrink strehl's lead. The observed pattern is that strehl's lead is **largest
  on chroma** — 1.813x on R-Y against `enfuse` versus 1.618x on luma. That is
  the opposite of the chroma-NR signature, so the stated motivation could have
  been ruled out on direction before any file was read.

### 15.6 A measurement I withdrew, with the mechanism

To attribute the difference to the merge, single-frame noise was measured on an
input frame and divided by the merged output — ideal `sqrt(31.5) = 5.61` for a
half stack. It returned **0.56x luma for all three arms**: every merge appeared
to *add* luma noise. An averaging merge cannot do that, so the number was
diagnosed rather than reported.

MEASURED, two estimators on the same images and tiles, sigma times 1000:

| arm | half-diff Y | high-pass Y | inflation |
| --- | --- | --- | --- |
| strehl | 52.96 | 136.61 | 2.58x |
| `enfuse` | 85.70 | 137.30 | 1.60x |
| `focus-stack` | 101.41 | 135.36 | 1.33x |

The high-pass estimator reads **136.6, 137.3 and 135.4** — nearly identical
across three arms whose true noise differs by a factor of two. It is measuring
the scene, which is the same scene, and the inflation is largest on the sharpest
arm. **The 9-pixel high-pass cannot separate detail from noise, and a merge adds
detail.** The reduction factors are withdrawn; they measured detail gained.

This is the same blind spot recorded in section 6, reached from the other
direction, and it is why the half-difference estimator exists.

A scene-blind reduction factor is **not measurable from this corpus**: it needs
two exposures at identical focus, and a focus stack contains none. Saying so is
the honest answer.

### 15.7 What is still open

The live alternative explanation is the one already flagged in section 9 and
still unquantified: each arm carries one registration resample, but **the
kernels differ** — Hugin's for the comparators, catmull-rom for strehl — and
resampling correlates and suppresses high-frequency noise. That would flatter
the comparators, meaning the measured strehl lead is if anything conservative.
It remains the most likely residual confound and it is not addressed here.
"""
io.open(P, "a", encoding="utf-8", newline="\n").write(T)
print("appended")
