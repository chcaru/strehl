# M166 — aperture ordering does not force an external detail reference

**Status: COMPLETE. Verdict: `NOT FORCED`.**

This report was prepared against:

- `docs/proposals/2026-08-sota-path.md`, SHA-256
  `72F8257918E929ACB3F50C4606A4A7A73A44594492F040B4FCF196072E6A0B94`;
- `docs/proposals/2026-09-sota-scorecard.md` v1.10, SHA-256
  `373A00FC68781D76C9FF904916F3FB8261BCF7D4896101868629988ADC6377C3`.

The scorecard was read only. No file under
`D:\personal\macro\requests\7-aperture-pairs\` was enumerated, read, or
decoded. The request-19 tree remained read only: ARWs were accessed through
directory metadata and ExifTool headers, the two capture README files were
read, and pixel evidence below comes from already-existing M128 artifacts.

## 0. Verdict

The proposed implication is:

> EXIF f-number fixes the true detail order, so a statistic that recovers that
> order is validated against sharpening.

That implication is false.

**`NOT FORCED`** is the only defensible verdict, for two independent reasons:

1. **Even granting the proposal its strongest possible physical premise, the
   aperture ladder is not identifying.** A common post-render sharpening
   operator preserves both the exact aperture rank and the exact relative Airy
   attenuation. The rendered triplet and its EXIF labels are identical to a
   second world with a sharper latent scene and no postfilter. This is an exact
   counterexample, not an empirical concern.
2. **The existing razor stacks do not establish that strongest premise.**
   Their focus step is aperture-relative, which defeats the assignment's first
   suspected failure, but their total depth spans differ; the razor's useful
   edge features are not valid optical references; signal and available frame
   budget are aperture-aligned; and the assumption that all three apertures
   lie beyond the aberration reversal is contradicted elsewhere on this rig and
   not established by request 19.

The f-number remains useful as a **necessary ordinal sabotage screen**. A
candidate that cannot survive a properly controlled aperture degradation
should be rejected. Passing that screen does not supply the external truth M1
needs.

## 1. Fatal counterexample: the order survives sharpening

Let:

- `X` be the unknown latent subject;
- `H_i` be the optical transfer at aperture `i`; and
- `K` be one common linear shift-invariant sharpening transfer applied after
  rendering.

The complete observation can arise in either of two worlds:

```text
world A: Y_i = K H_i X       ordinary latent scene, common postfilter
world B: Y_i = H_i X'        sharper latent scene, no postfilter
         X'  = K X
```

For common LSI transfers,

```text
K H_i X = H_i K X
```

for every aperture. Therefore:

- every rendered pixel is identical in the two worlds;
- every EXIF f-number is identical;
- the true diffraction order can be strictly correct in both;
- relative transfer between apertures is identical; and
- the two worlds require opposite provenance labels for the extra
  high-frequency amplitude.

The f-number is genuinely outside the rendered pixels. It nevertheless adds
only information about `H_i`; it does not identify `X` separately from the
common renderer transfer `K`.

I reran `experiments/M164-aperture-identifiability/witness.py`:

```text
PASS: 9/9 checks; verdict=OBJECTION_CORRECT;
max_world_error=0.000e+00; captures_opened=0
```

At `0.25 cyc/px`, its deterministic construction gives:

| marked aperture | Airy MTF | unsharpened score | common-USM score |
|---|---:|---:|---:|
| f/5.6 | `0.4456704781` | `0.0222835239` | `0.0314079461` |
| f/8 | `0.2404167769` | `0.0120208388` | `0.0169430051` |
| f/11 | `0.0452826354` | `0.0022641318` | `0.0031912246` |

The sharpening is rewarded by `1.409469446x` in every arm, yet both score
columns have the correct order. More strongly, the relative vector after
sharpening is:

```text
[1.0, 0.5394496353, 0.1016056428]
```

It agrees with the predicted relative Airy attenuation to `1.11e-15`. The
two worlds' arrays differ by exactly zero.

This directly falsifies the sentence that “a sharpening-fooled statistic will
fail” the known ordering. Some such statistics will fail. The exhibited one
does not.

## 2. Focus sampling and depth coverage

### 2.1 The feared fixed absolute step is not present

The coarse Sony focus tags are too quantized to resolve individual frames.
The MakerNote nevertheless contains a finer monotone lens-state quantity. I
used:

```text
q = SonyFNumber2 / SonyFNumber
```

`q` is not asserted here as calibrated metres. It is fit for this narrower
question because:

- it changes monotonically through every stack;
- equal values recur across apertures at equal coarse focus distances;
- dividing by the aperture value collapses all three arms onto one coordinate;
  and
- the independently pixel-selected best horizontal-edge frame lands at the
  same `q` in all three arms.

Across all 789 headers:

| composition | arm | frames | `q` start | `q` end | span | mean `Δq/frame` | `(Δq/frame)/N` |
|---|---|---:|---:|---:|---:|---:|---:|
| diagonal | f/5.6 | 279 | `2.283752408` | `2.175118122` | `0.108634286` | `0.000390771` | `6.7234e-5` |
| diagonal | f/8 | 210 | `2.286846253` | `2.175118122` | `0.111728131` | `0.000534584` | `6.6823e-5` |
| diagonal | f/11 | 143 | `2.286846253` | `2.166301992` | `0.120544261` | `0.000848903` | `7.5033e-5` |
| horizontal | f/5.6 | 67 | `2.259151857` | `2.231792849` | `0.027359008` | `0.000414530` | `7.1322e-5` |
| horizontal | f/8 | 50 | `2.259151857` | `2.228773485` | `0.030378372` | `0.000619967` | `7.7496e-5` |
| horizontal | f/11 | 40 | `2.259151857` | `2.225758206` | `0.033393651` | `0.000856247` | `7.5682e-5` |

Within each composition, `Δq/frame` grows approximately in proportion to
f-number. `(Δq/frame)/N` varies by only `12.3%` diagonally and `8.7%`
horizontally. An aperture-independent physical step would instead leave
`Δq/frame` approximately common.

The existing M128 pixel sweep independently selected the frame of maximum local
edge gradient in every horizontal arm:

| arm | selected frame | frame index | `q` |
|---|---|---:|---:|
| f/5.6 | `DSC00045.ARW` | 27 | `2.243911263441333` |
| f/8 | `DSC00056.ARW` | 25 | `2.243911263441325` |
| f/11 | `DSC00042.ARW` | 21 | `2.243911263441321` |

The spread is `1.15e-14`. Actual image content therefore elects the same
metadata focus state at all three apertures.

**Ruling on the assignment's first threat:** the camera's step-width 4 is
aperture/DOF-relative in these files, not a fixed absolute focus increment.
There is no evidence that f/5.6 is uniquely gap-blurred for the proposed
reason. This does not prove continuous no-gap coverage at every scene point,
but it removes the claimed aperture-directed mechanism.

### 2.2 Total depth coverage is not equal

The same fine coordinate proves a different defect. The arms do not cover
identical total focus ranges:

| composition | common span / union | f/5.6 span / f/11 span |
|---|---:|---:|
| diagonal | `0.901198` | `0.901198` |
| horizontal | `0.819288` | `0.819288` |

The diagonal f/5.6 and f/8 arms end together, while f/11 extends farther. The
horizontal arms start together, then f/8 and f/11 extend progressively farther
than f/5.6.

The measured horizontal edge focus at `q=2.243911263441` lies inside the common
interval, so that one local feature is covered by all arms. No existing map
establishes that every scored scene point in either composition lies inside
the common interval. Full-frame stacks therefore are not three observations
of an identical depth support.

**Route verdict: CONFIRMED confound.** An aperture comparison using these
captures would have to define and independently verify common-focus support
before any ordinal result could be interpreted. The capture set as a whole
does not provide that equality.

## 3. Diffraction, aberration, and the teleconverter

### 3.1 Pixel pitch derived from the camera dimensions

The delivered EXIF image is `7008 × 4672`. With the specified
`35.9 × 23.9 mm` sensor:

```text
horizontal pitch = 35.9 mm / 7008 = 5.12272 um
vertical pitch   = 23.9 mm / 4672 = 5.11558 um
representative pitch              = 5.11915 um
```

At `λ = 0.550 um`, the Airy first-zero diameter `2.44 λ N` is:

| marked aperture | Airy diameter | sensor pixels |
|---|---:|---:|
| f/5.6 | `7.5152 um` | `1.468 px` |
| f/8 | `10.7360 um` | `2.097 px` |
| f/11 | `14.7620 um` | `2.884 px` |

Sony's more precise MakerNote values are `5.8121`, `8.0000`, and `11.3137`,
which give `1.524`, `2.097`, and `2.966 px`.

The focus-varying `SonyFNumber2` values imply still larger diameters if they
are read as macro effective aperture, roughly `3.40–3.44`, `4.67–4.74`, and
`6.60–6.70 px` over the horizontal arms. ExifTool itself warns that
`SonyFNumber2` sometimes deviates, so this report uses it as a lens-state
coordinate and does not promote it into a calibrated optical constant.

These numbers establish that diffraction is material. They do **not**
establish that residual aberration, defocus, motion, or sampling is negligible
relative to it. “Airy disc larger than one pixel” and “decisively
diffraction-limited” are different statements.

### 3.2 The teleconverter is already in EXIF

Every one of the 789 frames reports:

- focal length `200 mm`;
- lens model `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`;
- lens information `200 mm, f/5.6`; and
- maximum aperture approximately `f/5.6`.

The base lens is 100 mm f/2.8. Both focal length and maximum aperture are
doubled in the body metadata. Therefore the 2× teleconverter is already folded
into `FNumber`. Doubling the reported f-number again would be wrong.

### 3.3 The aberration reversal is not excluded

Diffraction makes the ideal incoherent cutoff decrease with f-number. It does
not guarantee that an arbitrary in-band detail score decreases when lens
aberration, residual focus, sampling, and stacking remain live.

The repository already contains a measured counterexample on this rig.
`M-PHASE0-QUINCUNX` reports that noise-subtracted transfer in
`0.260–0.330 sensor cyc/px` rises by `1.916x` from f/5.6 to f/8, with f/11
stronger still in that band. Its own ruling is that both f/5.6 and f/8 transmit
the entire band under every bellows hypothesis, so the reversal is MTF shape:
aberration or residual focus error. It explicitly calls a macro lens improving
from f/5.6 to f/8 ordinary.

Request 19 cannot resolve that question with its edge. M128 found the one
smooth repeatable feature to have:

| estimator | measured `rise(11)/rise(5.6)` | diffraction prediction |
|---|---:|---:|
| isotonic | `0.79099` | `1.96429` |
| erf | `0.90228` | `1.96429` |

The feature becomes narrower, not broader, and fits an intrinsic width of
about `17–19 um` with the diffraction coefficient pinned at zero. It is a
subject-width diagnostic, not an optical one.

**Route verdict: the premise is not established and contrary evidence exists.**
The Airy arithmetic is valid; the claim that these three complete imaging
operators are strictly ordered is not forced by it.

## 4. The razor does not cancel out

The ground cutting edge measures `1.23 green px RMS` locus wander against a
`0.044 px` photon-noise prediction. M128's independent tolerance experiment
found:

- straight-line registration passes at `0.02` and first fails at
  `0.03 green px RMS`;
- the interpolated first crossing is `0.02278 px`;
- the actual edge is about `54x` that crossing;
- the full measured-contamination control C2 recovers only `1/15` cases within
  5%, with worst absolute error `359.770%`; and
- per-column registration already biases cutoff by `+91.047%` at zero
  raggedness, so following the edge sharpens it against itself.

The cancellation assumption also fails directly across apertures. On common
columns, apparent locus RMS is:

| arm | common-coordinate RMS, green px |
|---|---:|
| f/5.6 | `1.77638` |
| f/8 | `1.64144` |
| f/11 | `1.91766` |

Pairwise correlations are about `0.807`, `0.803`, and `0.915`, with a shared
component of `1.63194 px` and an aperture-specific component of `0.70697 px`.
M128's within-arm two-green-plane reduction separately found the independent
registration component increasing from `0.2672` to `0.2885` to `0.3555 px`, a
33% spread. The same physical edge is not a common scalar term under the three
PSFs and locators.

The smooth feature is no escape: its measured aperture trend is reversed and
its intrinsic width dominates. Thus request 19 contains both:

1. a sharp but geometrically ragged edge that defeats the estimator; and
2. a smooth but physically wide edge that does not expose the optical PSF.

**Route verdict: CONFIRMED fatal for this subject as a referee.** The razor may
exercise or reject an instrument in development. It cannot admit one as an M1
truth reader.

## 5. Frame count and photon budget

The counts are aligned with the proposed “wide is best” result:

| composition | f/5.6 | f/8 | f/11 |
|---|---:|---:|---:|
| diagonal | 279 | 210 | 143 |
| horizontal | 67 | 50 | 40 |

Simple equal-count subsampling does not isolate that variable.

### 5.1 Uniform thinning breaks focus sampling

Keeping the full focus span while reducing every arm to the f/11 count
multiplies the f/5.6 physical spacing by:

- `1.958x` diagonally; and
- `1.692x` horizontally.

It removes the aperture-relative compensation established in §2.1 and creates
the very wide-aperture gap mechanism this audit was asked to test.

### 5.2 Contiguous equal-count subsets break depth coverage

Keeping the original spacing but taking contiguous subsets leaves only:

- `51.1%` of the diagonal f/5.6 span; and
- `59.1%` of the horizontal f/5.6 span.

The arms then cease to cover the same subject depth.

### 5.3 Equal frame count still does not equalize photons

ISO and shutter are fixed within each composition, so expected per-frame
irradiance scales approximately as `1/N²`. The existing pixel survey measures
best-frame edge contrast of:

| arm | contrast, DN |
|---|---:|
| f/5.6 | `2695` |
| f/8 | `1396` |
| f/11 | `690` |

The ratios `1.931x`, `2.023x`, and `3.906x` closely follow the exact MakerNote
irradiance ratios `1.895x`, `2.000x`, and `3.789x`.

A coarse whole-capture photon-opportunity proxy,
`frame_count × exposure / N²`, favors f/5.6 over f/11 by `7.393x`
diagonally and `6.347x` horizontally. This is not asserted as a per-output-pixel
photon count; that requires the stack's actual contribution map. It establishes
the direction and magnitude of the aligned acquisition budget.

**Route verdict: CONFIRMED confound; equal-count subsampling is insufficient.**
It either changes focus density or depth span, and it leaves the per-frame
photon difference intact.

## 6. Exposure and motion

All headers within each composition agree:

| field | diagonal | horizontal |
|---|---:|---:|
| exposure | `2.5 s` | `3.2 s` |
| ISO | `100` | `100` |
| focal length | `200 mm` | `200 mm` |
| image stabilization | `On` | `On` |
| electronic front curtain | `On` | `On` |

Every arm's shutter counter is consecutive, with no missing exposure inside a
stack.

The proposed longer-f/11-exposure failure is therefore absent: f/11 does not
use a longer shutter than f/5.6 in either composition. Metadata cannot certify
equal realized vibration across separate multi-minute sequences, especially
with stabilization active, so motion equality remains unmeasured rather than
proved. The much lower narrow-aperture signal is measured and remains live.

**Route verdict:** aperture-specific shutter duration is **NOT FOUND**;
realized motion is **UNDETERMINED**; the aligned SNR difference is
**CONFIRMED**.

## 7. Route-by-route ruling

| attack route | evidence | ruling |
|---|---|---|
| Fixed absolute focus step leaves f/5.6 depth gaps | `Δq/frame` scales with `N`; `(Δq/frame)/N` is nearly common; pixel-selected peaks share one `q` | **NOT FOUND** |
| Total physical depth differs | f/5.6 covers `90.12%` and `81.93%` of f/11's span | **CONFIRMED** |
| All arms are decisively diffraction-limited | Airy blur is material, but same-rig measured transfer reverses f/5.6→f/8 and request-19 edge cannot adjudicate optics | **NOT ESTABLISHED; contrary evidence** |
| Teleconverter double-count | EXIF reports 200 mm and f/5.6 maximum for the 100 mm f/2.8 + 2× assembly | **REJECTED; TC already folded in** |
| Razor raggedness cancels | 54× beyond tolerance; aperture-dependent locator component; C2 fails | **REJECTED** |
| Equal-count subsampling removes count confound | It must coarsen focus spacing or truncate depth and does not equalize photons | **REJECTED** |
| Longer f/11 exposure adds motion blur | Shutter is identical within each composition | **NOT FOUND** |
| F-number order rejects sharpening-sensitive scores | Exact commuting-filter witness preserves order and relative Airy ratios while rewarding sharpening `1.409469446x` | **FATAL COUNTEREXAMPLE** |

## 8. What remains usable

The existing aperture arms can be used as a **development falsifier** under a
frozen protocol. A wrong order is evidence against a candidate.

They cannot supply a positive M1 admission because no condition stated solely
over:

- the three EXIF f-numbers;
- the three rendered outputs;
- their ordinal ranking; or
- their relative Airy attenuation

breaks the exact `X' = KX` ambiguity in §1.

The missing thing is not another scalar computed from these renders. It is an
observation or restriction that identifies provenance: for example an
independently known input signal/transfer, an independently sampled reference,
or a separately validated model that excludes one of the two constructed
worlds. Its resulting claim would inherit that calibration's scope.

For these particular captures, even ordinal development use additionally
requires verified common-focus support, a frozen tone/registration path,
explicit contribution/noise accounting, and an intervention whose optical
order is independently established rather than inferred from f-number alone.
Meeting those conditions would make the ladder a cleaner screen. It would not
turn it into external truth.

## 9. Reproduction and artifacts

Owned artifacts:

- `experiments/M166-aperture-premise/exif.csv` — 789 read-only ExifTool rows;
- `experiments/M166-aperture-premise/capture-snapshot-before.json` — pre-read
  file inventory;
- `experiments/M166-aperture-premise/capture-snapshot-after.json` and
  `readonly-verification.json` — `PASS`, all 789 entries unchanged in path,
  length, and modification time;
- `experiments/M166-aperture-premise/focus-tags.txt` — targeted focus-tag
  samples;
- `experiments/M166-aperture-premise/sensor-tags.txt` — delivered/raw
  dimensions;
- `experiments/M166-aperture-premise/analyze.py` — deterministic reduction;
- `experiments/M166-aperture-premise/analysis.json` — 17/17 checks passing;
- `experiments/M166-aperture-premise/verify.py` and `verification.json` —
  12/12 report-to-evidence checks passing.

From the repository root:

```powershell
python -B projects\strehl\experiments\M166-aperture-premise\analyze.py
```

Expected:

```text
PASS: 17/17 checks; rows=789; pixel_peak_spread=1.155e-14
```

The script opens no capture. It consumes the saved EXIF CSV and tracked M128
and M164 evidence. Any exception emits a serialized `FAIL` and exits nonzero.

Then:

```powershell
python -B projects\strehl\experiments\M166-aperture-premise\verify.py
```

Expected:

```text
PASS: 12/12 report checks
```
