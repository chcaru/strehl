# Stack storage study, 2026-11-20

How much smaller a four-shot A7CR stack can be stored. Investigation only: no product code
was changed. Inputs were read-only (`D:/StrehlCaptures`): the scarab stack
(`stack-1794786793543-11226`, 784 RAWs, ISO 100), a dark-background stack
(`stack-1794689780304-11226`) and a run of six groups at one focus position
(`stack-1794687317465-11226`). Frames were restored with `strehl-raw-archive restore` to
`C:\strehl-scratch\storage-study` and deleted afterwards; the S7 and S9 copies and their
renders were deleted after S8 and S9. No scratch is left.

Labels: MEASURED, DERIVED, ARGUED. "bits/px" is over the whole 9600 x 6376 CFA strip.
The estimator (`est.py`) reports ideal code lengths of a decodable adaptive model with its
side information charged; an arithmetic or ANS coder reaches them within about 1 % (ARGUED).
Its speed was not measured.

## S1. Where the bytes are (MEASURED, `s1-byte-budget.txt`)

| Part of an ARW (125.6-127.1 MB) | Bytes |
| --- | ---: |
| CFA strip, 9600 x 6376 samples, 14 bits in 16 (active 9504 x 6336 at 32, 20) | 122.42 MB |
| Full-size JPEG, 9504 x 6336 | 2.8-4.0 MB |
| Preview JPEG, 1616 x 1080 | 0.22-0.40 MB |
| Thumbnail JPEG, 160 x 120 | 7-10 kB |
| Metadata and padding (85 % zero bytes) | 0.19 MB |

A format-2 archive is 49.8-64.1 MB: the strip at 5.90-7.81 bits/px plus the JPEGs stored
as they are (5-9 % of the archive). Format 2 predicts a sample as the mean of four causal
same-site neighbours and codes residuals in blocks of 32 (per-block shift, raw low bits, a
canonical code for the high part).

## S2. Raw values (MEASURED, `s2-value-stats.txt`)

Full 14-bit data: black near 512, clipped samples exactly 16383, no unused codes inside the
populated range of any frame, even/odd counts 0.996-1.001, no position dependence. The 32,
64, 20 and 20 border columns and rows outside the default crop are exposed image, not
masked. Nothing structural to exploit.

## S3. The floor (MEASURED and DERIVED, `s3-floor-repeat.txt`, `s3b-floor-frames.txt`)

A lossless coder that knew every pixel's true mean would still pay the entropy of the noise.
From the product's model (0.4040 DN/e-, 1.334 DN) scaled by the temporal variance measured
on flat pixels of the repeated run (0.94-1.02 of the model for red and green at 100 DN and
above, 0.85-0.94 below, blue 0.80-0.89):

| Frame | Floor, bits/px | Format 2, bits/px | Floor as a share of format 2's strip |
| --- | ---: | ---: | ---: |
| Scarab frame 1 | 6.80 | 7.41 | 92 % |
| Scarab frame 401 | 6.79 | 7.81 | 87 % |
| Dark-background stack, frame 201 | 5.07 | 6.27 | 81 % |
| Repeated run, frame 1 | 4.93 | 5.90 | 84 % |

So no lossless method of any kind can take more than 8-19 % off the strip. The repeated run
is not static (consecutive differences correlate -0.30 to +0.18), so only its flat pixels
measure noise. The sensor's fixed pattern (0.30/0.35/0.40 % of level, 2026-11-16) costs a
coder without a gain map 0.056 bits/px on the scarab and 0.002-0.011 on the dark runs.

## S4. Lossless, one frame at a time (MEASURED, `s4-intra-401.txt`, `s4-intra-others.txt`)

| bits/px | Scarab 1 | Scarab 401 | Dark 201 | Repeat 1 |
| --- | ---: | ---: | ---: | ---: |
| Format 2 as packed | 7.409 | 7.811 | 6.269 | 5.900 |
| JPEG-LS (CharLS), site planes | 7.453 | 7.725 | 6.083 | 5.621 |
| JPEG XL lossless, effort 3 | 7.451 | 7.649 | 5.972 | 5.585 |
| JPEG XL lossless, effort 7 | 7.579 | 7.793 | 6.028 | 5.614 |
| E0: format 2's predictor, adaptive contexts | 7.343 | 7.721 | 5.996 | 5.578 |
| E1: least squares, 10 same-site taps, per frame | 7.258 | 7.461 | 5.825 | 5.427 |
| E2: least squares, 22 cross-colour taps, per frame | 7.185 | 7.355 | 5.669 | 5.249 |
| E3: E2 with weights per 512 px tile | 7.100 | 7.266 | 5.601 | 5.167 |
| E3 against format 2 | -4.2 % | -7.0 % | -10.7 % | -12.4 % |
| Floor | 6.796 | 6.786 | 5.073 | 4.927 |

One thread: JPEG-LS encodes 57-68 MP/s and decodes 63-82; JPEG XL effort 3 26-29 and 43,
effort 7 2-3 and 21-24. Format 2 decodes about 640 MP/s (95.6 ms a file). The off-the-shelf
codecs are no better than format 2 on bright frames. Format 2's entropy coder is close to
ideal for its predictor on bright frames (E0 is 1 % smaller) and 4-5 % short on dark ones;
the predictor is where the rest is.

## S5. Lossless, across frames (MEASURED, scarab plane 101, `s5-cross-401.txt`, `s5-self-map-401.txt`, `s5b-gain-map.txt`)

Same estimator; each variant adds taps from frames a decoder would already hold to E3.

| Variant | bits/px, mean of the group | Against intra E3 | Against format 2 (7.811) |
| --- | ---: | ---: | ---: |
| I: intra E3 | 7.261 | | -7.0 % |
| G: + earlier shots of the group (5 x 5 windows) | 7.060 (shots 2-4: 7.025, 6.989, 6.961) | -2.8 % | -9.6 % |
| P: + the same shot of the previous plane | 7.045 | -3.0 % | -9.8 % |
| GP: both | 6.986 | -3.8 % | -10.6 % |
| M: intra + gain map from 62 of the stack's frames | 7.233 | -0.39 % | |
| M: intra + the noisier 2026-11-16 calibration map, x 0.3 | 7.249 | -0.17 % | |
| Floor | 6.786 | | -13.1 % |

Per-tile motion search between planes changed nothing (shifts in 3-5 % of tiles). The
learned map costs 19-27 MB to store once (0.2-0.1 % steps) and saves 0.21 MB a frame: it
breaks even after 90-130 frames. What each costs: G needs the group's earlier shots (the
engine already decodes groups whole); P chains planes (a key plane every N bounds it; one
damaged file then loses up to N planes); M makes every archive depend on a map file. All
three end the README's promise that archives are independent.

## S6. Calibrated near-lossless (MEASURED, `s6-bits.txt`, `s6-stats.txt`, `s6-theory.txt`, `s6b-embedded-jpeg.txt`)

`quant.py`: a table per sample value. Bins of odd integer width w, the largest with
(w^2 - 1) / 12 <= (k sigma)^2 / 12 at the model's sigma; a sample is restored as its bin's
middle member; 16383 is kept exact. No prediction and no neighbours.

| k | bits/px: JPEG-LS / JPEG XL e3 / estimator E3 (scarab 401) | E3, dark 201 | Strip, MB (scarab, E3) | Added noise, bound | Worst bias of a mean (DERIVED) |
| ---: | --- | ---: | ---: | ---: | ---: |
| lossless | 7.725 / 7.649 / 7.266 (format 2: 7.811) | 5.601 | 55.6 (format 2: 59.8) | | |
| 0.25 | 5.156 / 5.075 / 4.735 | 5.123 | 36.2 | +0.26 % | 1e-16 sigma |
| 0.5 | 4.077 / 3.949 / 3.620 | 4.020 | 27.7 | +1.04 % | 1e-16 sigma |
| 1 | 3.048 / 2.926 / 2.584 | 2.772 | 19.8 | +4.08 % | 9e-10 sigma |
| 2 | 2.103 / 2.052 / 1.666 | 1.775 | 12.8 | +15.5 % | 4.6e-3 sigma |

On six repeats: added variance is 0.34, 0.66, 0.82 and 0.91 of (k sigma)^2 / 12 for
k = 0.25 to 2 (odd widths round down); the mean of six quantised frames minus the mean of
the originals correlates -0.0008 to +0.003 between disjoint halves (no signal-locked
pattern) and is offset by +0.036 DN at k = 1 and +0.123 DN at k = 2, the DERIVED
k^2 a / 12 = 0.034 and 0.135 DN of bins that widen with level (a constant a table can
remove). A first version that restored the centre in the variance-stabilised domain had
level-dependent biases of up to 0.05 sigma (`s6-stats-v1.txt`): the odd-width bins are the
fix. Subtractive dither is not needed at k <= 2 and was not built.

Embedded JPEGs: 3.0-4.4 MB a file. JPEG XL's JPEG transcoding restores them byte for byte
and saves 1.07-1.14 MB a file (libjxl, BSD-3-Clause). Brunsli (MIT) saved 1.2-1.4 MB but its
output was not byte-exact through imagecodecs (not investigated).

## S7. A quantised copy to render (`s7-quantised-copy.txt`, `s7-check.txt`)

`C:\strehl-scratch\storage-study\scarab-k1`: the first 24 scarab planes (96 ARWs) with only
the CFA strip replaced by its k = 1 reconstruction (rms change 9.0 DN, mean +0.03 DN),
`manifest.json`, `result.json`, and `events.jsonl` and `transfer-receipts.jsonl` cut to
those files with their SHA-256 replaced. Checked without the engine: hashes and sizes match
the journal and receipts, bytes outside the strip are identical.

## S8. The render from calibrated frames (MEASURED, `s8-render-k1.txt`, `s8-shift-k1.txt`)

`render-k1.ps1` rendered the first 24 scarab planes with the product's default four-shot
route (build of `13fed04c0`, isolated cache) from the lossless archives (`--limit 24`,
SHA-256 `E37E8E6F...`, the reference) and from the S7 copy; `compare-k1.py` compares the two
linear float renders in 128 px tiles of the green channel.

| Check (k = 1 against lossless) | Result |
| --- | --- |
| Flat tiles first: gradient energy (the render's noise) | 1.011 unblurred, 1.004 at a 1 px blur: noise amplitude +0.5 % and +0.2 % |
| Channel means | +0.22 to +0.44 on levels of 14 000-16 300 (+1.4e-5 to +2.8e-5) |
| Detail tiles (top tenth), floor removed, blurs 0.5-2.5 px | median 1.0001-1.0005, 10th percentile 0.9997-1.0000, 1st percentile 0.9993-0.9997 |
| Rms difference of the two renders | 8.8 in flat tiles (0.32 of the render's own noise there), 33.7 in detail tiles |
| Displacement between the renders (phase correlation, 24 windows) | median 0.02 px, largest 0.04 px; explains 5-36 % of the difference in those windows |

The difference is larger where there is detail, so it is not only added noise: the merge
selects, and the lateral-colour measurement and the selection respond to any perturbation of
their input (the two logs differ by 0.02 px in the measured red and blue shifts). S9 asks
whether that response is special to quantising.

## S9. The placebo (MEASURED, `s9-placebo.txt`)

`s9-placebo-copy.py` writes the same 96 frames with, instead of quantising, an independent
random integer added to every sample, uniform over the range the k = 1 quantiser's error has
at that level (rms change 9.002 DN, the same as S7's). Rendered the same way.

| Pair | Rms difference, flat tiles | Detail tiles (median) | Detail tiles (90th percentile) | Whole frame |
| --- | ---: | ---: | ---: | ---: |
| k = 1 against lossless | 8.774 | 33.72 | 44.34 | 20.35 |
| Placebo against lossless | 8.725 | 34.14 | 45.29 | 20.41 |
| k = 1 against placebo | 11.72 | 54.14 | 67.27 | 28.04 |

Gradient energy against the lossless render: k = 1 1.0042 (flat) and 1.0003 (detail); placebo
1.0040 and 1.0002. A render from frames quantised at one sigma stands where a render from
frames with that much extra random noise stands: the merge cannot tell them apart. What the
calibrated tier costs a photograph is therefore its added noise, +0.2 to +0.5 % in amplitude
on this render, and nothing else that these measures see.

## Not verified

- The calibrated tier on a whole stack, on another subject, and by eye on the finished
  photograph (S8 and S9 are 24 planes of one stack; three 160 px crops were looked at).
- Encode and decode speed of an E3-class coder; the estimator is not a codec.
- Cross-frame figures are from one plane of one stack; the dark stack was not tried.
- A gain map from the whole stack (62 frames were used); other ISO settings and bodies.
