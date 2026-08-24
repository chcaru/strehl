# M85 — Output correctness: colour and resolution

> **NOT INDEPENDENTLY VERIFIED.** Measured by M85. Rule 12 binds its author
> exactly as it binds any other milestone author. Every number below was
> produced on this machine, from `D:\personal\macro\bee-3-cpl`, 299 frames,
> `--gate 2`, unless it is namespaced to another milestone.

## VERDICT

**Both defects were real. Both are fixed. The measurement path is byte-identical.**

| | before M85 | after M85 |
|---|---|---|
| colour | camera-native RGB, white balance only | camera → sRGB (BT.709 primaries, D65), from the camera's own D65 characterisation |
| resolution | 3516×2344, one 2×2 quad per pixel | 7032×4688, every CFA site at its own position, Malvar-He-Cutler demosaic |
| linear binned TIFF | SHA-256 `41974F2A…F699` | SHA-256 `41974F2A…F699` — **identical** |

Three things in the dispatch's framing were wrong, and one of them mattered a
lot. They are argued in §2, §3 and §6.

- **The architecture change the brief asked for was already built.** The merge
  has estimated all four CFA sites at full resolution since M18. Only the
  *writer* binned. No merge, gate, fold or election code was touched.
- **`rawler`'s `xyz_to_cam` field is all zeros for this body.** The obvious
  field is not the one carrying the data; `color_matrix` is. A pipeline reading
  only the obvious field would have emitted camera-native RGB forever.
- **No colour-accuracy claim is possible from this corpus**, and none is made.

---

## 1. MEASURED — the cause of the cast, confirmed at the source

The brief's claim was that white balance is applied but no colour matrix
exists. **Confirmed.** A search of `crates/**/*.rs` for
`matrix|xyz|primaries|rec709|chromatic` returned zero hits before this
milestone. `write_merged` (`merge_cmd.rs`) and `write_outputs` (`stack.rs`)
did exactly: subtract black → apply as-shot WB gain → divide by range → clamp →
optional sRGB curve. Nothing else.

Camera RGB with white balance is **not a colour space**. The A7C II's filters
are much broader than sRGB's primaries, so an image rendered without the matrix
is systematically **desaturated** — which is exactly the flat grey-green the
owner saw. MEASURED on the full frame, mean HSV saturation:

| rendering | mean saturation | p99 |
|---|---:|---:|
| before (no matrix) | 0.0847 | 0.3431 |
| after (matrix) | **0.1274** | **0.4770** |

**+50.4% mean, +39.0% at p99.** That is the defect and its size.

## 2. MEASURED — where the matrix actually comes from, and a correction to the brief

The brief anticipated that a per-camera matrix might have to be embedded as
cited data. **It does not.** But the obvious route does not work either.

For `ILCE-7CM2`, `rawler` 0.7.2 returns:

```text
xyz_to_cam            : [[0,0,0],[0,0,0],[0,0,0],[0,0,0]]     <- ALL ZEROS
color_matrix[A]       : [[ 0.8784,-0.4791, 0.1177],[-0.3468,1.0693,0.3213],[0.0009,0.0507,0.7395]]
color_matrix[D65]     : [[ 0.7460,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584]]
```

MEASURED by `strehl-raw`'s
`the_decoders_matrix_agrees_with_the_independently_measured_one`, run with
`--ignored` against the real capture.

Two consequences, both load-bearing:

1. **The field named `xyz_to_cam` is empty and the table named `color_matrix`
   is full.** Code that read only the documented-looking field would silently
   render camera-native forever. `Frame::xyz_to_cam_rgb_with_source` tries the
   field, then falls through to the table.
2. **Which illuminant you pick is a decision that can be silently wrong.** The
   `A` (tungsten) entry is a completely different matrix. Choosing it would
   produce a plausible-looking, badly wrong image. The choice is therefore an
   explicit preference list, `DAYLIGHT_PREFERENCE = [D65, D55, Daylight,
   FineWeather, D50, D75]`, never `HashMap` order, and the CLI prints which one
   it used.

### The provenance check that matters (rule 35)

The `D65` entry is **numerically identical, to all four printed decimals**, to
the `rgb_xyz_matrix` that `docs/research/M26-colour-clipping-measured.md` §1
MEASURED through `rawpy`/LibRaw. `rawler` and LibRaw maintain **separate**
camera databases. Two independent parties reading the same physical
characterisation and agreeing exactly is the only kind of evidence that can
rule out a transposed, rescaled or mis-attributed matrix. Asserted in
`strehl-raw` at a tolerance of 5e-4 — one unit in M26's last printed place.

### A second, fully independent confirmation of the matrix's orientation

Applying the matrix to D65 XYZ gives the camera's neutral response
`s = [0.408527, 1.073044, 0.773176]`, i.e. **implied daylight WB of R 2.6266,
B 1.3878**. The as-shot EXIF WB on this stack is **R 2.5693, B 1.5684**, and
M26's six MEASURED stacks span R 2.131–2.861, B 1.408–1.884.

The implied gains land inside the measured envelope, R agreeing to 2.2%. The
inverse orientation would have produced gains around 0.4 and 1.3, nowhere near.
**DERIVED: `xyz_to_cam` is XYZ→camera, not camera→XYZ**, established from the
camera database against the per-shot EXIF tag — two unrelated sources.

## 3. The transform, stated explicitly

**Target: sRGB / IEC 61966-2-1.** BT.709 primaries, D65 white, the piecewise
transfer curve. `--srgb` emits encoded sRGB; `--demosaic` alone emits linear
camera-native at full resolution.

**Order, in code and in `image_out.rs`'s module docs:**

```text
raw DN → subtract black → as-shot WB (green = 1) → [demosaic] → matrix → clamp [0,1] → sRGB curve → u16
```

Two of those positions are decisions, not conventions:

- **WB before demosaic.** Malvar-He-Cutler interpolates colour *differences*
  (`R − G`); those are only small when the channels share a scale. Demosaicing
  first would hand the gradient correction a 2.57× red offset to treat as scene
  structure.
- **Demosaic before matrix, clamp after matrix.** The matrix mixes channels, so
  applying it first would smear every single-channel interpolation artifact
  across all three outputs. And it has negative off-diagonals, so it
  legitimately sends valid camera triples outside `[0,1]` — the clamp must be
  after it or the clip happens in the wrong space and shifts hue.

This matches the ordering rule M26 established (gate in native raw DN; WB and
colour after the merge).

**Construction of `camera_to_srgb`:** compose `xyz_to_cam · SRGB_TO_XYZ_D65`,
**row-normalise each row to sum 1**, invert. Row *i*'s sum is camera channel
*i*'s response to sRGB white, so normalising is the step that declares "the
input has already been white balanced". The result's rows sum to 1, so
**neutral in ⇒ neutral out exactly** — asserted at 1e-9 in `color.rs` and again
at 16-bit precision in `image_out.rs`.

```text
camera_to_srgb =  [ 1.636062  -0.448619  -0.187443 ]
                  [-0.115165   1.488971  -0.373806 ]
                  [-0.004740  -0.323601   1.328341 ]
```

**This is not CAT02 or any chromatic adaptation transform.** Adaptation is done
by von Kries scaling in camera space — that is what the as-shot WB *is*. This
is the standard raw-developer approximation and its residual error is discussed
in §7.

## 4. MEASURED — the required proof: the measurement path is unchanged

`strehl stack "D:\personal\macro\bee-3-cpl" --gate 2 --out …`, 299 frames, no
other flags — the exact command the corpus's numbers come from.

| | SHA-256 | bytes |
|---|---|---:|
| before any M85 change | `41974F2AA2187C63CE3031813BD51F7D1A0B6EB4972EDF1F7F1684E2D429F699` | 49 449 626 |
| after all M85 changes | `41974F2AA2187C63CE3031813BD51F7D1A0B6EB4972EDF1F7F1684E2D429F699` | 49 449 626 |

**Identical.** Re-verified against the final binary after `rustfmt`, after the
plant/restore cycle of §8, and after every source edit. Rule 26 satisfied by
hash, not by argument.

This is achieved structurally, not by luck: the binned no-matrix branch of
`write_merged` and `write_outputs` is the **literal pre-M85 arithmetic**, left
in place and commented as byte-frozen. The new capability is additive:

- `--srgb` now also applies the colour matrix — sanctioned by the dispatch, and
  legitimate because `--srgb` is documented as "for looking at, NOT for
  measuring". **Disclosure: a pre-M85 `--srgb` artefact is no longer
  reproducible from this binary.** Nothing in the corpus was measured on one.
- `--demosaic` is new and off by default.
- `Develop::default()` is the identity, with a tripwire test asserting it.

`crates/strehl-core/src/merge.rs` was **not modified**. No gate, fold, election
or noise-model code was touched.

## 5. MEASURED — the demosaic, against closed forms rather than eyeballs

Malvar-He-Cutler (ICASSP 2004), implemented from **the paper's published
stencils only**. No GPL implementation was opened — `librtprocess`,
RawTherapee and darktable are all GPL and all off-limits under the licence rule.
`rawler` is LGPL-2.1 and is linked, never read; the API facts in §2 came from
locally generated rustdoc HTML, never from `doc/src/`.

Chosen over adaptive/fashionable methods deliberately: it is linear and
shift-invariant, so its effect on noise is computable and it **cannot
manufacture detail** (rule 18); and it has closed-form known answers, which is
what makes the tests below possible at all.

### Known answers, all passing

| property | bar | result |
|---|---|---|
| all four stencils sum to 8 | exact | ✅ |
| constant **coloured** scene `[0.6,0.3,0.45]` survives | 1e-6 everywhere incl. borders | ✅ |
| linear ramp survives in the interior | 1e-6 | ✅ |
| `D(Tᵐ) = T(Dᵐ)` under transpose | exact | ✅ |
| row API == whole-image API | exact | ✅ |
| mirror border preserves CFA parity | exact | ✅ |

A constant *coloured* patch is the strongest cheap structural test: it catches
mistranscribed coefficients, `F_H`/`F_V` swaps and border-parity errors. A
*neutral* constant field catches none of them, because the mosaic is then flat.

### The false-colour / aliasing check, against a DERIVED closed form

Taking the DTFT of each tap list at `(ω, 0)` — a different domain from the
convolution being tested:

```text
H_G(ω) = H_H(ω) = (6 + 4cos ω − 2cos 2ω)/8
H_V(ω)          = (11 − 4cos ω + cos 2ω)/8
H_X(ω)          = (3 + 8cos ω − 3cos 2ω)/8
```

`H_G ≡ H_H` is a derived identity, not a typo. On a neutral grating of
amplitude `A` the worst false colour is
`A · max(|1−H_G|, |H_X−H_G|, |H_H−1|, |H_V−1|) · maxₓ|sin ωx|`.

| period | gain term | closed-form false colour |
|---:|---:|---:|
| 16 px | 0.0352 | 0.014065 |
| 8 px | 0.1036 | 0.041421 |
| 4 px | 0.2500 | 0.100000 |
| 2.5 px | **0.8181** | 0.311237 |

The closed-form column was **recomputed independently in numpy** from the
DTFTs above and matches the Rust test's own prediction to f32 rounding
(≤3e-5). The test asserts the **measured** false colour of the actual
convolution against that closed form at a tolerance of **3e-4**, at all four
periods, and passes.

**Where it fails, stated plainly (rule 30):** the gain term is 3.5% of
amplitude at a 16 px period and **81.8% at 2.5 px**. Near Nyquist this
algorithm turns a monochrome grating into a coloured one. Every demosaic fails
there; this one's failure is now predicted in closed form and asserted at its
predicted size rather than discovered later.

### Where the advantage is conditional — and it does not merely shrink, it reverses

MHC's gradient correction assumes `R − G` is smoother than either channel —
a property of real scenes, not a theorem. Two arms, on synthetic scenes with
known truth, PSNR against the interior:

| arm | bilinear | MHC | MHC − bilinear |
|---|---:|---:|---:|
| A — luminance-dominant, slow chroma | 29.34 dB | 34.88 dB | **+5.54 dB** |
| B — three independent mid-frequency channels | 29.19 dB | 23.90 dB | **−5.29 dB** |

Arm A's bar was **pre-registered at +3 dB** from the paper's own ~5.5 dB claim
on the Kodak set; the measured **+5.54 dB** reproduces the paper's figure
closely, on a different fixture.

**Arm B is the result worth reading.** When the three channels carry
independent mid-frequency content, MHC is **5.3 dB worse than bilinear** — the
gradient correction injects a neighbouring channel's structure into a channel
that does not share it. The advantage does not merely shrink; it inverts. This
is the direction the algorithm can be fooled in (rule 18), and it is a real
property of the method, not a defect in this implementation.

The test asserts only that arm B's gain is *smaller* than arm A's, so it does
not depend on the sign — but the sign is the honest finding and is recorded
here. **For this corpus arm A is the relevant regime**: a bee under diffuse
light is overwhelmingly luminance-detail with slow chroma. The claim is
therefore "MHC is the right choice *for this subject matter*", not "MHC is
better".

## 6. MEASURED — the resolution work needed no architecture change

**The dispatch proposed changing the merge to gather at full resolution. It
already does.** `Estimator` (`merge.rs:438`) holds `sum: [Vec<f32>; 4]` — four
independent accumulators per quad, one per CFA site — and `fold_inner` adds each
of a frame's four samples to its own plane, under one per-quad focus decision.
That is precisely the architecture the brief described. Only `write_merged`
binned, by calling `value(R)`, `green_mean()`, `value(B)`.

Building the full-resolution mosaic is therefore **pure interleaving of data
that was already there**. No decision logic changed. This de-risked the whole
resolution workstream and is the single most useful thing found tonight.

**Verified by read-back, not by reading the code:** in the full-resolution
linear output, `(G1 + G2)/2` reproduces the binned green to **max 0.50 DN, mean
0.2495 DN** of 65535 — exactly half-LSB quantisation, i.e. the same numbers.

### Is the extra resolution real, or interpolated?

At a G1 site the output carries the merged G1 sample itself; MHC leaves a known
channel alone. So "does binning destroy real detail" is exactly "is `G1 − G2`
bigger than noise". The image supplies its own control: in a flat region
`G1 − G2` must be pure noise.

| region | RMS(G1 − G2) |
|---|---:|
| flat (background card) | 83.50 DN |
| detailed | **744.15 DN** |
| ratio | **8.91×** |

**8.9× the noise floor.** Binning was discarding a large, real signal.

A sharper question: could an interpolator have predicted it from the binned
image? Fitting the best linear predictor available from the binned data (its own
gradients, in the direction separating a G1 site from its G2 neighbour):

| arm | total RMS | residual after fit | vs noise floor |
|---|---:|---:|---:|
| flat, real `G1−G2` | 84.98 DN | 84.96 DN (0.0% explained) | 1.00× |
| detail, real `G1−G2` | 753.24 DN | **345.22 DN** (79.0% explained) | **4.06×** |
| detail, interpolated (CONTROL) | 683.21 DN | 162.63 DN (94.3% explained) | 1.91× |

**Honest limitation:** the control does not fully collapse to the floor
(1.91×, not 1.00×), because a bicubic upsample is a 4-tap kernel and the
predictor is a 2-tap gradient, so even a deterministic function of the binned
image is not fully explainable by it. The discrimination is still clear — 4.06×
against 1.91× — but the residual is an **upper bound** on unpredictable
content, not a clean measurement of it. ARGUED, not MEASURED.

**A control that failed and was discarded:** the first spectral test compared
full-res high-band energy against a *nearest-neighbour* upsample of the binned
image and got 0.00156 vs 0.01135 — the "control" scored 7× higher. That is
correct behaviour: box replication is broadband. The control was wrong, not the
result. Recorded because rule 20 is about controls that can fail, and this one
failed by being unsound.

## 7. The colour claim that is NOT being made

**There is no grey card in any frame of this corpus, the scene was shot through
a circular polariser, and the light was uncontrolled. No colour-accuracy claim
is possible and none is made.**

What *is* established: the transform is correct by construction
(neutral-preserving, rows sum to 1), it uses the camera's own D65
characterisation confirmed by an independent decoder, and it agrees with an
independent numpy re-implementation applied to the byte-frozen linear file to
**max 14.1 DN of 65535 (0.02%), mean 0.76 DN** — consistent with 16-bit
quantisation of the linear input amplified by the sRGB curve's slope near black.

**The one honest negative result.** MEASURED in linear light on the background
card (713 flat bright patches):

| | R/G | B/G |
|---|---:|---:|
| camera-native, after as-shot WB | 0.9480 | 1.0420 |
| after the matrix | 0.9159 | 1.0665 |
| deviation from neutral | −5.2% → **−8.4%** | +4.2% → **+6.7%** |

The background is **not** neutral before the matrix, and the matrix amplifies
that residual by ≈1.6×. This is expected — the matrix is neutral-preserving, so
a genuine cast is expanded along with all other chroma — but it means the
rendered background carries an ≈8% cyan cast. Three candidate causes, none of
which this milestone can distinguish:

1. the light was not D65 while the matrix is the D65 one (the standard
   raw-developer approximation, applied here knowingly);
2. the circular polariser has its own spectral transmission;
3. the white backing surface is probably not neutral — optical brightening
   agents in white plastic/paper fluoresce blue, and a +4% B/G excess is exactly
   that signature.

Distinguishing them needs a grey card in frame. That is a capture request, and
it is **not** filed here because `docs/captures-needed.md` is outside M85's
ownership — it needs filing by whoever owns that file.

## 8. MEASURED — the control that was made to fail

Rule 20: a colour transform that cannot be shown to be doing anything is not
verified.

**Plant.** `camera_to_srgb` was edited in the *shipping* path to swap rows 0
and 2 of its result — a channel-swapped matrix. `color.rs` hashed before
(`C0CBAE2F…6037`), rebuilt, re-run.

**Prediction, stated before the run:** swapping rows 0 and 2 of camera→sRGB
swaps the R and B *output* channels exactly, leaving green untouched.

**Read-back:**

```text
control mean R0.42253 G0.42281 B0.40880
planted mean R0.40880 G0.42281 B0.42253
planted R == control B ?  max|diff| 0.00000000
planted B == control R ?  max|diff| 0.00000000
planted G == control G ?  max|diff| 0.00000000
did the image change at all ?  max|diff| 0.14225986
```

Exactly the predicted direction, exactly. The matrix is demonstrably doing
something, and doing what its algebra says.

**Which tests caught it — including one that did not.** With the plant in
place, `synthetic_patches_of_known_chromaticity_round_trip` and
`a_transposed_or_channel_swapped_matrix_fails_the_round_trip` both failed.
**`a_neutral_stays_neutral_and_the_unnormalised_matrix_does_not` still
passed** — because swapping two rows preserves neutrality, both rows still
summing to 1. That is a documented blind spot, and it is why the round-trip
test exists. Stating it is rule 20's actual requirement.

**Restore.** `color.rs` restored from the pristine copy; hash re-verified equal
to `C0CBAE2F…6037`; rebuilt; re-run; output SHA-256 `2A072C3E…9DB5` identical
to the pre-plant control. **Byte-planted and byte-restored.**

## 9. Deliverable

`C:\dev\strehl-out\M85-before-after\` — same crop, three panels each:

- `claw-0-side-by-side.png`, `eye-0-side-by-side.png` — before / colour /
  colour + resolution, captioned so they cannot be mixed up later.
- `full-1-before.png`, `full-2-after.png` — whole frame.

## 10. Verification performed

| gate | result |
|---|---|
| `cargo build --release -p strehl-cli` | clean |
| `cargo test -p strehl-core -p strehl-raw -p strehl-cli --lib --bins` | **238 passed, 0 failed, 1 ignored** |
| `strehl-raw` `--ignored` real-capture matrix test | passed |
| `cargo clippy -p strehl-core -p strehl-raw --all-targets -- -D warnings` | clean |
| `cargo clippy -p strehl-cli --bins --tests -- -D warnings` | clean |
| `cargo fmt --check` | clean **on every file M85 owns** |

**Two failures that are not M85's**, reported rather than touched, per the
ownership rule: `crates/strehl-cli/examples/m86-align.rs` has `rustfmt` diffs
and does not compile against M86's in-flight `crates/strehl-core/src/align.rs`
(`Cx` field mismatch at `m86-align.rs:1415`). That file belongs to M86. No
alignment code appeared in any M85-owned file.

## 11. Candidate facts

Numbered `P1…` per the rule-28 corollary; these are proposals, not corpus
numbers. **SYNTHESIS.md was not edited.**

| # | claim | label |
|---|---|---|
| **P1** | `rawler` 0.7.2 returns an **all-zero** `xyz_to_cam` for the ILCE-7CM2 and carries the real characterisation in `color_matrix`, keyed by illuminant (`A` and `D65` present). | MEASURED |
| **P2** | `rawler`'s `color_matrix[D65]` for the ILCE-7CM2 is numerically identical to fact-namespace M26's `rawpy`/LibRaw `rgb_xyz_matrix` to all four printed decimals. Two independent camera databases. | MEASURED |
| **P3** | That matrix implies daylight WB of **R 2.6266, B 1.3878**, inside M26's measured as-shot envelope (R 2.131–2.861, B 1.408–1.884) — independent confirmation the matrix is XYZ→camera. | DERIVED |
| **P4** | Adding the camera→sRGB matrix raises mean saturation on `bee-3-cpl` from **0.0847 to 0.1274 (+50.4%)**; p99 from 0.3431 to 0.4770. | MEASURED |
| **P5** | The merge has always estimated all four CFA sites at full sensor resolution; only the writer binned. Full-resolution output required **no** change to merge, gate, fold or election code. | MEASURED |
| **P6** | In the full-resolution output `(G1+G2)/2` reproduces the binned green to max **0.50 DN** (half-LSB) — the extra samples are the sensor's own readings, not inferences. | MEASURED |
| **P7** | RMS(G1 − G2) on `bee-3-cpl` is **83.50 DN** in flat regions and **744.15 DN** in detailed regions, a **8.91×** ratio. Binning discarded real signal ≈9× the noise floor. | MEASURED |
| **P8** | After removing the best linear prediction from the binned image, **345 DN (4.06× the noise floor)** of green signal remains, against **1.91×** for an interpolated control. Upper bound, not a clean measurement — see §6. | ARGUED |
| **P9** | Malvar-He-Cutler's worst false colour on a neutral grating equals `A·max(\|1−H_G\|,\|H_X−H_G\|,\|H_H−1\|,\|H_V−1\|)·maxₓ\|sin ωx\|` with the §5 responses; the measured convolution matches that closed form to better than **3e-4** at 16, 8, 4 and 2.5 px. | DERIVED + MEASURED |
| **P10** | That gain term is **3.5% of amplitude at a 16 px period and 81.8% at 2.5 px**. The algorithm's Nyquist failure is now predicted, not merely known. | DERIVED |
| **P11** | Malvar-He-Cutler beats bilinear by **+5.54 dB** on a luminance-dominant synthetic scene (reproducing the paper's ~5.5 dB claim on a different fixture) but is **5.29 dB worse** than bilinear when the three channels carry independent mid-frequency content. The advantage **inverts**, it does not merely shrink. | MEASURED |
| **P12** | The linear binned TIFF is byte-identical before and after M85: SHA-256 `41974F2A…F699`, 49 449 626 bytes. The corpus's ~1138 facts remain valid. | MEASURED |
| **P13** | The rendered background on `bee-3-cpl` carries an ≈8% cyan cast (R/G 0.9159, B/G 1.0665) because the camera-native background is already 5% off neutral and the matrix amplifies residual chroma ≈1.6×. Cause undetermined among illuminant mismatch, CPL transmission, and a non-neutral card. **No colour-accuracy claim is made.** | MEASURED (effect) + UNVERIFIED (cause) |

## 12. What M85 did not do

- **No colour-accuracy claim.** §7. It needs a grey card in frame.
- **`argmax-baseline` got the matrix but not `--demosaic`.** `Selection` exposes
  all four planes, so it is cheap, but the baseline exists to be *free of
  interpolation artifacts* — giving it a demosaic would blunt the thing it is
  for. ARGUED, deliberate.
- **No ICC profile is embedded** in the TIFF. The output is sRGB and most
  viewers assume sRGB, so it renders correctly, but an untagged file is a
  latent trap for a colour-managed viewer that assumes something else.
- **No highlight reconstruction.** The matrix's negative off-diagonals clip
  saturated colours to gamut, and §3 says where. Recovering them needs
  per-channel clipping logic that M26 mapped and nobody has built.
