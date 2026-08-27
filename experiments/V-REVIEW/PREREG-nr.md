# Pre-registration: were the comparator inputs denoised?

Written and committed **before any discriminator is run**. Nothing below was
chosen after seeing a result.

## The question

The six noise cells could be measuring a RAW converter's denoiser against
strehl's refusal to denoise, rather than two merges. The chroma cells are worse
for strehl than the luma cells in all four chroma readings, which is the
signature chroma noise reduction would leave.

## What is already established documentarily, and why it is not enough

`experiments/V-LINEAR/develop_frames.ps1` shows the RAW-to-TIFF step is
**strehl's own decoder**, pin `740e7056`, the same binary that rendered the
strehl arm. Searches found no NR flag, no NR function, no config-file reader,
and a dependency set containing no image-processing library. **That is an
argument from absence and this project does not accept one.** The measurement
below is what decides it.

## Discriminator, fixed in advance

Chroma noise reduction works by averaging chroma over a neighbourhood. Its
unavoidable fingerprint is that **chroma noise becomes spatially correlated far
beyond the demosaic kernel's support.**

- **D1, chroma noise correlation length.** On each census tile, high-pass the
  opponent chroma plane with a 9-pixel box, compute the normalised spatial
  autocorrelation, and report the radius in pixels at which it first falls
  below 0.10. Reported as the median over tiles.
- **D2, fine-to-coarse chroma power ratio.** Chroma noise power at 3-pixel
  scale divided by that at 15-pixel scale. Noise reduction suppresses the
  numerator.

Both are computed on the same 110 census tiles already vetted for flatness, so
the site selection cannot be tuned to the answer.

## Commissioning, fixed in advance

The probe is worthless unless it responds to a denoiser and stays quiet without
one. All three arms must pass before any verdict is read.

- **C1, null.** A frame against itself must give a ratio of exactly 1.000.
- **C2, potency with a REAL denoiser, not a synthetic one.** The identical RAW
  file is developed twice through `rawpy`/LibRaw: once with every noise
  reduction disabled (`fbdd_noise_reduction=Off`, `median_filter_passes=0`,
  `noise_thr=None`) and once with **FBDD full** noise reduction on. D1 must be
  **materially longer** on the denoised development. If the probe cannot see a
  production denoiser doing its job on the same photons, it cannot clear
  strehl either.
- **C3, clean floor.** Synthetic white chroma noise must read the shortest
  correlation length of anything measured, confirming the statistic reads
  "undenoised" correctly rather than returning short values indiscriminately.

## Decision rule, fixed in advance

Let `D1(ref)` be the LibRaw no-NR development and `D1(nr)` the FBDD-on
development of the same file. Let `D1(strehl)` be the comparator input frame.

- **NO NR PRESENT** if `D1(strehl)` lies at or below `D1(ref)`. The converter
  removed nothing, the confound is excluded, and the noise deficit is ours.
- **NR PRESENT** if `D1(strehl)` exceeds `D1(ref)` and approaches or exceeds
  `D1(nr)`. Then the six cells are re-measured on undenoised comparator inputs.
- **INDETERMINATE** if `D1(strehl)` sits between the two without approaching
  either, or if `D1(nr)` fails to separate from `D1(ref)` in commissioning. An
  indeterminate result is reported as indeterminate, not resolved by argument.

**The independent developer is the control, not the judge.** LibRaw and strehl
demosaic differently, so a small difference in `D1` is expected from the kernel
alone and is not evidence of a denoiser. Only movement toward `D1(nr)` counts.

## The follow-on measurement, also fixed in advance

Whatever the NR verdict, the question a build lane needs answered is how much
noise each merge actually removed **from the same inputs**.

Measure single-frame noise on the developed input frames in the same 110 tiles
and the same three channels, then report `sigma_input / sigma_output` for each
arm. The ideal for 63 frames is `sqrt(63) = 7.94`. This is reported per channel
so the deficit can be attributed to luma or chroma.

Caveat stated in advance: the strehl arm read the `.ARW` files directly while
the comparators read these developed TIFFs. The decode is the same code in the
same binary, but the strehl arm additionally ran with alignment on, so the
input-noise figure is the common decode's per-frame noise and not a byte-exact
account of what the strehl merge consumed.
