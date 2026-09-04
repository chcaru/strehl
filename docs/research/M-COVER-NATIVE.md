# M-COVER-NATIVE — scorecard crop adjudication and prior Q1–Q4 record

## Revised scorecard adjudication — Amendment 2

This section supersedes the earlier Q3/Q4 framing for the scorecard question.
It does not repeat the closed COVER lane's external-decoder campaign, border
profile, safe-inset search, or default decision.

### Q1.1 — native scale

Scorecard §1.5, lines 225–227, says in full:

> “Outputs must retain native scale. Resize is a hard invalidation.
>
> Crops are fixed from the common-input overlap before outputs exist. Retained
> field of view must be `>=99.0%` of that overlap.”

**PASS for native sampling; numeric confirmation PASS.** `cover-default.md`
already supplies the stronger evidence: Crop is byte-exact against an external
LibRaw decoder and therefore performs no rescale. No render was repeated here.

As requested, the unchanged frozen affine-ECC reader was rerun on one existing
Crop output, `m2-second-first16`, selected in `AMENDMENT-2.md` because it has
the smallest emitted rectangle:

| Reading | Result | §1.5 numeric limit |
|---|---:|---:|
| scale disagreement | **0.021415847%** | `<=0.10%` — PASS |
| rotation disagreement | **0.000001017 deg** | `<=0.02 deg` — PASS |

The frozen identity/translation nulls remained GREEN and its planted `+0.300%`
scale/rotation case remained RED before the TIFF was opened. The TIFF,
instrument, and luma-reader hashes matched their frozen values.

This reader is whole-image, 8x-downsampled affine ECC, not the literal
input-derived-landmark instrument named later in §1.5. It confirms the two
numeric readings but cannot license the whole similarity-fit conjunction.
The non-translation residual limb remains **UNMEASURED** because the inherited
residual reader fails pure-translation nulls.

### Q1.2 — no-inset field of view

**PASS at a zero-pixel inset for these eight M1/M2 arms.** Header-only
remeasurement gives:

| Arms | Bare Crop output, HxW | Retained against `4688 x 7032` |
|---|---:|---:|
| six arms | `4672 x 7012` | **99.375259661%** |
| `m2-bright-first16` | `4672 x 7008` | **99.318570979%** |
| `m2-second-first16` | `4664 x 7000` | **99.035321708%** |

All eight exceed `99.0%` even when the denominator is the entire native plane,
which is stricter than the scorecard's stated common-input-overlap
denominator. Against the separately frozen diagnostic common rectangle
`(y=40, x=58, h=4608, w=6912)`, every Crop arm retains
**100.000000000% geometrically**.

The COVER lane's `64.6047%` is the area left only after its separately required
256 px level-profile inset. It is not bare Crop's retained field of view.
Therefore that shipping inset and its `0.1%` level criterion are different and
stricter than §1.5's no-inset `>=99.0%` geometry bar.

### Q1.3 — the crop must be fixed before outputs exist

`CoverMode::Crop`'s emitted rectangle is computed from each arm's alignment
solution and differs across the eight renders. Scoring each arm over its own
entire emitted rectangle would change the scoring domain and does **not**
satisfy the quoted fixed-common-crop sentence under its strict reading.

The clause is nevertheless satisfiable without changing the renderer:

1. derive one common scene rectangle from the common inputs and frozen
   registrations;
2. freeze it before any scored output is inspected;
3. extract that same physical rectangle 1:1 from every strehl and comparator
   output, using only the analytically permitted translation.

The existing frozen `4608 x 6912` diagnostic rectangle is contained by all
eight strehl Crop outputs, so the geometry is feasible on this side. Formal
qualification is not complete: exact common-input-to-output coordinates,
comparator containment, the common ProPhoto-TIFF adapter/identity boundary,
and an admitted landmark/residual fit remain unmeasured. Accepting each
varying emitted rectangle as the scorecard crop instead would require an
explicit registrar interpretation.

### Q1.4 — the `2.6106%` boundary result

**No current scorecard clause independently fires from that number.** COVER's
measurement is a seven-band-versus-two-band boundary-level profile with its
own `0.1%` shipping gate. It is not §1.3's neutral-ramp sentinel, M3's
source-interval halo/veil statistic, or M8's source-support census, and it
cannot be silently imported as any of them.

It would affect scorecard eligibility if excluding the implicated border made
the frozen crop retain `<99%` of common overlap, left `<80%` of sites, or
caused `>2 pp` differential attrition. A separately commissioned M3 or M8
instrument could also detect a related failure. None of those conclusions
follows from the COVER profile alone.

### Program consequence

**The cover geometry is not blocked on a new no-resample mode.** Bare Crop
clears §1.5's native-sampling and numerical field-of-view bars at zero inset,
and one fixed 1:1 score rectangle can be applied outside Rust.

That does **not** make M1/M2 immediately measurable under the scorecard as
currently written. §1.3, lines 175–177, separately requires each program to emit a
“native-size 16-bit linear TIFF,” while current Crop TIFFs are smaller. §1.2's
common-TIFF boundary, comparator geometry, the literal landmark/residual
instrument, and M1's withdrawn statistic/bar also remain unresolved. Native
**size** and native **scale** are distinct requirements on the strict reading;
if §1.5 was intended to authorize smaller emitted TIFFs, the registrar must
resolve that drafting tension rather than this lane silently waiving §1.3.

## Superseded earlier Q1–Q4 answer

The remainder records the earlier task and its provenance. Its Q3/Q4 product
framing is not the current scorecard adjudication, and its `64.6047%` COVER
safe-inset figure must not be used as bare Crop's §1.5 field-of-view value.

**MEASURED — Q1: yes, Crop passes the specific native-scale rule.** The shipped
`CoverMode::Crop` removes the Scale arm's 0.2901–0.4619% magnification failure:
all eight Crop arms measure 0.0174–0.0231% scale disagreement and remain within
0.02 degrees rotation. The frozen ECC estimator was unchanged and its Scale
control reproduced byte-for-byte.

**VERIFIED/DERIVED — Q2: Crop fails a different hard prerequisite.** Every TIFF
is a same-pitch, unity-scale crop, but every TIFF is smaller than the required
native `7032 x 4688` program output. Geometric array containment retains the
whole frozen common rectangle and every frozen site, but that is not a
clean-pixel certificate: the current scorecard's already-closed `COVER /
default path` row keeps Scale because the separately measured Crop safe inset
retained only 64.6047%, below 80%, and no general safe inset was established.
This lane did not duplicate that border measurement.

Independent review also found that the inherited four-tile residual reader
fails a pure-translation null. Its recorded 0.3162–1.4765 px values therefore
remain diagnostics, not an admitted 8/8 residual failure. The formal negative
answer does not depend on them: native-size fails 8/8, the common-ProPhoto-TIFF
adapter and comparator geometry remain absent, and the current scorecard's
`### M1 — WITHDRAWN: no admissible detail instrument` has no active statistic
or bar.

**VERIFIED/DERIVED — Q3: the deterministic header census quantifies the
field loss.** Against native `7032 x 4688`, the eight Crop outputs lose
20–32 columns, 16–24 rows, and 0.624740–0.964678% of native area. Worst arm
`m2-second-first16` is `7000 x 4664`. Every TIFF header and SHA-256 matches the
committed Phase A render manifest, every dimension is exactly twice its frozen
banner rectangle, and all eight geometrically retain 100.000000% of the frozen
common-overlap rectangle. The percentages are derived arithmetic, not new
experimental evidence, and geometric retention is still not clean-site
admission.

**VERIFIED — Q4: Scale is a documented, intentional product trade and
simultaneously a hard scorecard-conformance failure under §1.5 native scale.**
It preserves dimensions by composing `k <= 1` and paying an upsample of `1/k`
at every output pixel, including the identity reference. This lane does not
establish that trade as a general picture-quality defect: prior M112 evidence
found that removing it did not recover the expected sharpness, while
`cover-default.md` keeps Scale because Crop has the worse unresolved boundary
problem. It is not a simple export-setting bug, no default change is advocated,
and the current `COVER / default path` decision remains **CLOSED — keep Scale**.

## Frozen provenance and control

**VERIFIED.**

| Item | Frozen/result value |
|---|---|
| binary | `experiments\SCORECARD-BASELINE\work\bin\strehl.exe` |
| binary SHA-256 | `814eb719608cc0f085fbd49e7529eb6fa4e50031070f5f57af4fc2812cee4363` |
| binary version | `strehl 0.0.0 (4b60b1ba9f56)` |
| exact input instances | 112 files across eight existing frozen arm directories; all matched the 64 unique hashes in `INPUT-MANIFEST.json` |
| frozen dependency audit | all 160 hashed files unchanged before/after |
| frozen cache | all eight baseline warp maps unchanged |
| private cache | eight byte copies, filenames preserved, unchanged before/after every recorded run |
| Scale control arm | `m2-second-first16`, no `--cover` argument |
| required/control SHA-256 | `3d46f11413e5cf37bdeb730eb6faf66c266ac52107e1b5af1e032052080d16bc` / exact match |
| control dimensions | native `7032 x 4688`, array `4688 x 7032 x 3`, `uint16` |

The control matched before any Crop interpretation. No tuning or replacement
solve was attempted.

**DEVIATION, VERIFIED:** the tracked diff/status of every protected path
remained unchanged, and the frozen baseline itself remained byte-identical.
During the run, ignored filesystem content under protected
`experiments\M8-overshoot` changed concurrently: the final provenance snapshot
grew from 5,403 to 5,729 files. Independent verification observed that growth
continuing after finalization, so no stable later whole-tree count is claimed.
This lane did not read file content there, write there,
revert it, or use it. Therefore whole-tree immutability of that one protected
path cannot be claimed, although its Git-visible state was unchanged.

## Exact invocation

**VERIFIED.** Commands ran serially. The absolute command for the Scale control
was:

```text
C:\dev\blog\death-of-software\projects\strehl\experiments\SCORECARD-BASELINE\work\bin\strehl.exe stack C:\dev\blog\death-of-software\projects\strehl\experiments\SCORECARD-BASELINE\work\inputs\m2-second-first16 --out C:\dev\blog\death-of-software\projects\strehl\experiments\M-COVER-NATIVE\out\renders\control-scale-m2-second-first16.tiff --linear-srgb --demosaic
```

The eight Crop invocations were the same frozen binary and corresponding
absolute frozen input/output paths:

```text
...\strehl.exe stack ...\work\inputs\m1-bright-a12        --out ...\out\renders\m1-bright-a12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m1-bright-b12        --out ...\out\renders\m1-bright-b12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m1-second-a12        --out ...\out\renders\m1-second-a12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m1-second-b12        --out ...\out\renders\m1-second-b12.tiff        --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-bright-first16    --out ...\out\renders\m2-bright-first16.tiff    --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-bright-second16   --out ...\out\renders\m2-bright-second16.tiff   --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-second-first16    --out ...\out\renders\m2-second-first16.tiff    --linear-srgb --demosaic --cover crop
...\strehl.exe stack ...\work\inputs\m2-second-second16   --out ...\out\renders\m2-second-second16.tiff   --linear-srgb --demosaic --cover crop
```

`RENDER-MANIFEST.json` contains every fully expanded absolute argv.

**VERIFIED environment:** `RAYON_NUM_THREADS=6`, `OMP_NUM_THREADS=6`,
`OPENBLAS_NUM_THREADS=6`, `MKL_NUM_THREADS=6`,
`NUMEXPR_NUM_THREADS=6`, `PYTHONIOENCODING=utf-8`, and
`STREHL_CACHE_DIR=<this lane>\work\cache`. Every other ambient `STREHL_*`
variable was removed before each binary invocation.

**VERIFIED defaults:** all files in each exact directory (`--limit` omitted);
default pyramid merge; 7 bands; gate 2.0; coarsest exponent 2.0; 1.4x
per-octave exponent ramp; soft selection; mean base; linear sRGB without the
display curve; full-resolution Malvar demosaic; exposure 0; auto exposure off;
Catmull-Rom; gear-matched lateral-CA default; no optional maps, estimator
controls, ROIs, or statistics. The binary banner states that photometric gain
and other estimator-only stages are not applied on this pyramid path. Scale was
the omitted control default; Crop was explicit.

The first Crop binary completed before the original harness selected the wrong
one of two coverage banners. `AMENDMENT-1.md` froze the parser repair before the
remaining seven renders. The completed TIFF was not overwritten or rerendered;
its exact command/log/output were recovered, and its binary `total: 10.6 s`
banner is the diagnostic wall value because the outer timer was lost.

## Estimator commissioning

**MEASURED before real values.** This is the unchanged frozen
`audit_geometry.py` whole-image ECC estimator: the images are area-downsampled
8x, an affine ECC fit is made over the whole image, and scale is derived from
the affine determinant. It is not literal discrete input-derived landmarks.
It was added after the score bytes and can reject an arm but cannot rescue or
score it.

| Commissioning case | Scale disagreement | Rotation | Expected/result |
|---|---:|---:|---|
| identity null | 0.000000% | -0.000000 deg | GREEN / GREEN |
| translation null | 0.008363% | -0.005718 deg | GREEN / GREEN |
| planted 0.300% scale + rotation | 0.303140% | -0.024093 deg | RED / RED |

The unchanged commission returned `commissioned=true`,
`null_stayed_green=true`, and `plant_went_red=true`. OpenCV's estimator thread
count was set to 6.

## Q1 — frozen Scale versus Crop geometry

**MEASURED.** `audit_geometry.OUT` alone was rebound to this lane's `out` and
`audit_geometry.WORK` to the frozen baseline `work`; unchanged
`audit_geometry.main()` then executed all eight inherited `PAIRS`. The Scale
columns are the committed frozen readings.

| Arm | Scale ECC scale | Crop ECC scale | Crop rotation | §1.5 scale/rotation |
|---|---:|---:|---:|---|
| `m1-bright-a12` | 0.294655% | 0.017553% | -0.000704 deg | PASS |
| `m1-bright-b12` | 0.301891% | 0.017422% | -0.003205 deg | PASS |
| `m1-second-a12` | 0.290072% | 0.020748% | +0.000216 deg | PASS |
| `m1-second-b12` | 0.290358% | 0.021350% | -0.001268 deg | PASS |
| `m2-bright-first16` | 0.337678% | 0.023079% | +0.002455 deg | PASS |
| `m2-bright-second16` | 0.299185% | 0.018739% | -0.002527 deg | PASS |
| `m2-second-first16` | 0.461888% | 0.021416% | +0.000001 deg | PASS |
| `m2-second-second16` | 0.299620% | 0.018310% | +0.000529 deg | PASS |

**MEASURED verdicts:**

- Scale disagreement `<=0.10%`: PASS, 8/8 Crop arms.
- Rotation disagreement `<=0.02 deg`: PASS, 8/8 Crop arms.
- Non-translation residual `<=0.10 output px RMS`: **UNMEASURED by an
  admitted instrument**.
- Complete §1.5 geometry conjunction: **UNMEASURED**, not a pass.

The separate inherited residual reader was not commissioned by the ECC tests
above. Independent review planted pure translations into that exact reader:
`+2.0 px` in x returned `0.509902 px RMS`, and `(y=+1.35,x=-0.6) px` returned
`0.200000 px RMS`, both false failures after translation should have been
removed. Its executed values are retained as diagnostics:

| Arm | Scale residual diagnostic | Crop residual diagnostic |
|---|---:|---:|
| `m1-bright-a12` | 3.343651 px | 0.663325 px |
| `m1-bright-b12` | 3.083829 px | 1.170470 px |
| `m1-second-a12` | 3.593049 px | 0.678233 px |
| `m1-second-b12` | 3.187475 px | 0.489898 px |
| `m2-bright-first16` | 5.053711 px | 1.476482 px |
| `m2-bright-second16` | 3.266497 px | 0.800000 px |
| `m2-second-first16` | 5.094114 px | 0.911043 px |
| `m2-second-second16` | 3.445287 px | 0.316228 px |

An independent alternative landmark audit re-chose the estimator on three
arms. It corroborated the scale verdict at `0.009502%`, `0.010331%`, and
`0.041621%`. Its post-similarity residual diagnostics were `0.690`, `0.421`,
and `0.999 px`, but that audit was not a preregistered replacement scorecard
instrument and is not promoted. Its persisted readings and nulls are in
`out/INDEPENDENT-VERIFICATION.json`.

## Crop outputs and integer scene mapping

**VERIFIED/DERIVED.** The banner's Crop rectangle is in half-resolution CFA
plane pixels. The writer crops by integer addressing and doubles both axes for
the demosaiced output. Every observed TIFF dimension equals exactly twice its
banner rectangle; no coverage scale is composed.

| Arm | `k` | Plane crop `(x,y,w,h)` | Output width x height | Bytes | SHA-256 |
|---|---:|---|---:|---:|---|
| `m1-bright-a12` | 0.9973 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `995bec815fbc9d7b0b29ec4d9b8a0fcbcf622ac084cfe5d5c6765d2fb1adc3ee` |
| `m1-bright-b12` | 0.9972 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `b6468ca016396f63767ee8f61270bfc4126167e3b931e781abf6e29ebfb371db` |
| `m1-second-a12` | 0.9973 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `2508c70feab85b2331b420453e92c93f96d80ced5b868051c30b9be3bc9fae2a` |
| `m1-second-b12` | 0.9973 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `ec03b3051c83f76536848f17effee15d136519a4eb9fd73f5f5ee740f96cedc1` |
| `m2-bright-first16` | 0.9969 | `(6,4,3504,2336)` | `7008 x 4672` | 196,451,080 | `e883de25b493cdf8c55d6e7008a5810e0dc92e4553e635a0920f9f87e1b93f83` |
| `m2-bright-second16` | 0.9972 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `a3d71e96623fd55f11125292ac6807414e61c156d0ff38a915871153e6db29b7` |
| `m2-second-first16` | 0.9956 | `(8,6,3500,2332)` | `7000 x 4664` | 195,890,824 | `a0b38ce9cab2cd0c1030da21d8d44dc5832055045c03dc89c5d45e27a893ee1c` |
| `m2-second-second16` | 0.9972 | `(5,4,3506,2336)` | `7012 x 4672` | 196,563,208 | `7f58d9c124ebdf20af69a2c85f43905d24d1ecd1eb37d87c872ca26f6f5b3129` |

All outputs are `HxWx3 uint16` linear-sRGB TIFFs. None equals native active
`7032 x 4688` (`4688 x 7032` array order), but all exceed frozen
`COMMON_SHAPE = 4608 x 6912`.

The corresponding full-resolution Crop rectangles in `(y,x,h,w)` are:

- `(8,10,4672,7012)` for six arms;
- `(8,12,4672,7008)` for `m2-bright-first16`;
- `(12,16,4664,7000)` for `m2-second-first16`.

**DERIVED:** every output rectangle is large enough to contain the complete
registered array rectangle `(40,58,4608,6912)`, so geometric common-overlap
containment is 100.0% in every arm. The unchanged `output_luma` centre slice
starts at array index `(40,60)`.

Independent review found that these are not one proven physical coordinate
frame: the rawpy visible input is 7028 px wide while strehl's active output
frame is 7032 px wide. The apparent two-pixel offset is therefore index
arithmetic, not a measured fixed scene translation. The containment conclusion
survives the unquantified four-pixel frame-width difference because the
smallest horizontal margin is 42 px and the vertical frames agree, but exact
scene-coordinate identity remains unmeasured.

## Geometric site containment

**DERIVED from the verified integer rectangles and frozen site manifest.**

| Site family/comparison | Sites per arm | Survival | Differential attrition |
|---|---:|---:|---:|
| M1 bright (`a12`, `b12`) | 486 | 100.0%, 100.0% | 0.0 pp |
| M1 second light (`a12`, `b12`) | 486 | 100.0%, 100.0% | 0.0 pp |
| M2 bright (`first16`, `second16`) | 455 | 100.0%, 100.0% | 0.0 pp |
| M2 second light (`first16`, `second16`) | 455 | 100.0%, 100.0% | 0.0 pp |

Thus raw rectangle containment is 100.0% and geometric differential attrition
is 0.0 pp. This does **not** establish formal clean-site survival. The current
scorecard's closed COVER row records only 64.6047% retained after the
separately measured safe inset on `109MSDCF`, and its second subject established
no general inset. Those numbers are prior evidence, not measurements on these
bee arms; live `M-COVER-BORDER` owns the unresolved border mechanism.

## Q2 — actual current scorecard rules

**VERIFIED:** current §1.5 content and frozen v1.1 §1.5 are identical after the
repository's CRLF/LF normalization: 778 bytes,
SHA-256 `39efbd5c6f8d251c8bb4ed1c64e1a73b084511886229c6670e7bdca008e35ef9`.

The current file states:

- lines 156–157: “Write **uncompressed** 16-bit **linear ProPhoto RGB, D50**
  TIFFs at the native active-image dimensions.”
- lines 163–166: the programs must receive the exact same TIFF bytes; without a
  strehl adapter or boundary hash identity, competitive quality remains
  `UNMEASURED`.
- lines 175–177: “Each program must emit a native-size 16-bit linear TIFF,”
  with no resized output after stacking.
- line 225: “Outputs must retain native scale. Resize is a hard invalidation.”
- lines 226–229: crops are frozen from common-input overlap, must retain
  `>=99.0%`, translation may be removed analytically, and frequency metrics may
  not resample an output.
- lines 230–232: scale `<=0.10%`, rotation `<=0.02 deg`, and non-translation
  residual `<=0.10 output px RMS`.
- lines 233–235: `>=80%` identical site survival and no more than `2 percentage
  points` differential attrition.
- line 458, the `COVER / default path` row: “**CLOSED — keep Scale.**” Its
  recorded safe inset leaves 64.6047% retained area against 80%, and Crop is
  not licensed as the default.
- line 491: “### M1 — WITHDRAWN: no admissible detail instrument”; line 516
  states that the `S_25` requirement is withdrawn rather than weakened.

### Per-clause verdict

| Current clause | Verdict | Basis |
|---|---|---|
| §1.2 common native-size linear ProPhoto input | **UNMET / UNMEASURED** | This is the registered native-RAW product diagnostic, not the absent common-TIFF arm; no strehl TIFF adapter or internal byte-identity proof was added. |
| §1.3 16-bit linear output | **PASS for container/linearity** | TIFF pages are `uint16 RGB`; banners say linear sRGB with no transfer curve. |
| §1.3 native-size program output | **FAIL 8/8** | Crop outputs are `7000–7012 x 4664–4672`, not `7032 x 4688`. |
| §1.3 no resized post-output | **PASS for this path** | Crop is integer addressing at unity pitch; no output resize/upsample occurs. |
| §1.5 native scale / hard resize invalidation | **PASS 8/8 as rejection audit** | ECC scale is 0.0174–0.0231%; banners state unity scale and no coverage scale. |
| §1.5 fixed common-overlap FOV `>=99%` | **GEOMETRIC PASS 8/8** | Array containment gives 100.0%; exact rawpy-to-strehl scene-frame identity is unmeasured. |
| §1.5 analytic translation / no metric resampling | **PASS for the ECC procedure** | ECC fits translation without resampling a frequency score. The inherited residual reader is not admitted. |
| §1.5 scale `<=0.10%`, rotation `<=0.02 deg` | **PASS 8/8** | Table above. |
| §1.5 non-translation residual `<=0.10 px` | **UNMEASURED** | The inherited reader reports 0.3162–1.4765 px but fails pure-translation nulls. |
| §1.5 sites `>=80%`, differential attrition `<=2 pp` | **GEOMETRIC CONTAINMENT PASS; FORMAL CLEAN-SITE STATUS UNMEASURED** | Raw containment is 100.0% / 0.0 pp; Crop's border-safe inset does not have a transferable certificate. |
| Current M1 card | **WITHDRAWN** | `### M1 — WITHDRAWN: no admissible detail instrument`; no active statistic or bar exists. |
| Current COVER/default gate | **CLOSED — keep Scale** | The scorecard records Crop retained area 64.6047% after its evidenced safe inset, below 80%, with no general safe inset. |
| Formal comparability to a full-frame comparator | **UNMEASURED / not admitted** | Native-size output fails; comparator render geometry was not measured; common-TIFF adapter remains absent; the ECC audit is not literal input-landmark scoring. |
| Scientific comparability of the shared crop | **ARGUED possible, not established** | Same-pitch array overlap exists, but exact scene-frame mapping, admitted residual, and clean-border site survival remain unresolved. |

## Q3 — deterministic TIFF-header geometry census

### Method and commissioning

**VERIFIED.** `PHASE-B-METHOD.md` was committed before the census ran. It
states explicitly that Phase A had already observed the actual dimensions, so
this is a deterministic census and cross-check, not blinded discovery.
`geometry_census.py --commission` then exercised the same TIFF-header parser and
the same integer loss predicate on two tiny TIFF arrays under ignored `work`:

| Synthetic case | Fixed native | Header read | Integer loss `(W,H)` | Expected/result |
|---|---:|---:|---:|---|
| matching-dimensions null | `12 x 8` | `12 x 8` | `(0,0)` | GREEN / GREEN |
| known smaller crop | `12 x 8` | `10 x 6` | `(2,2)` | RED / RED |

Both files were removed before commissioning returned. Only after that artifact
was GREEN did the production command read the eight existing ignored Crop TIFF
headers. No TIFF was rerendered. `GEOMETRY-CENSUS.json` records nine decimal
places for every derived percentage.

For every arm, the header shape and SHA-256 equal the committed Phase A
`RENDER-MANIFEST.json` record, and output width/height equal exactly twice the
frozen banner Crop rectangle. Scale/native mode is fixed at `7032 x 4688`
(`4688 x 7032` array order) for all eight baseline arms.

### Exact census

**VERIFIED integers; DERIVED percentages.** `ΔW` and `ΔH` are total columns and
rows lost relative to native, across both sides. Retained-area percentages use
the `32,966,016`-pixel native rectangle. Common-overlap percentages use the
separate frozen `6912 x 4608` common rectangle.

| Arm | W | H | ΔW px | ΔH px | Width loss | Height loss | Area loss | Retained area | Common-overlap geometric retention |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `m1-bright-a12` | 7012 | 4672 | 20 | 16 | 0.284414% | 0.341297% | 0.624740% | 32,760,064 (99.375260%) | 100.000000% |
| `m1-bright-b12` | 7012 | 4672 | 20 | 16 | 0.284414% | 0.341297% | 0.624740% | 32,760,064 (99.375260%) | 100.000000% |
| `m1-second-a12` | 7012 | 4672 | 20 | 16 | 0.284414% | 0.341297% | 0.624740% | 32,760,064 (99.375260%) | 100.000000% |
| `m1-second-b12` | 7012 | 4672 | 20 | 16 | 0.284414% | 0.341297% | 0.624740% | 32,760,064 (99.375260%) | 100.000000% |
| `m2-bright-first16` | 7008 | 4672 | 24 | 16 | 0.341297% | 0.341297% | 0.681429% | 32,741,376 (99.318571%) | 100.000000% |
| `m2-bright-second16` | 7012 | 4672 | 20 | 16 | 0.284414% | 0.341297% | 0.624740% | 32,760,064 (99.375260%) | 100.000000% |
| **`m2-second-first16`** | **7000** | **4664** | **32** | **24** | **0.455063%** | **0.511945%** | **0.964678%** | **32,648,000 (99.035322%)** | **100.000000%** |
| `m2-second-second16` | 7012 | 4672 | 20 | 16 | 0.284414% | 0.341297% | 0.624740% | 32,760,064 (99.375260%) | 100.000000% |

`m2-second-first16` is the asserted worst arm on width, height, and area loss.
Native-size is RED 8/8 even though no arm loses 1% of native area. Conversely,
all eight rectangles contain the complete frozen common overlap, so §1.5's
`>=99.0%` field-of-view predicate is a **geometric pass at 100.000000%**. These
are not contradictory: §1.3 requires exact native output dimensions, while
§1.5 uses the smaller pre-frozen common-overlap denominator.

That §1.5 conclusion remains geometric only. It does not turn contained sites
into admitted clean sites, does not establish a transferable safe inset, and
does not change the current residual status: **UNMEASURED because its inherited
reader fails pure-translation nulls**.

### `sample_lanczos3` support is not part of these dimensions

**VERIFIED source reading; prior evidence, not a Q3 measurement.** Current
`crates\strehl-core\src\align.rs`, symbol `sample_lanczos3`, says:

> “Interpolating like Catmull-Rom — at integer phase every tap but the centre
> lands on a zero of `sinc`, so an identity transform is a true identity — but
> with a far flatter passband. M95 measured it recovering **+0.1160 dex** of
> 0.30–0.48 cyc/px power against Catmull-Rom on the shipped `bee-3-cpl` warps,
> against **+0.0179 dex** for removing the coverage rescale: the kernel is the
> larger of the two levers by 6.5x.”

The surrounding support sentence is:

> “Support is 3 px, not 2, so [`Resampler::sample_checked`] rejects a wider
> border — one more px of the coverage-cropped field is unavailable per side.”

That sentence is specifically the Lanczos-3 support cost relative to
Catmull-Rom. The frozen Phase A banners and manifest say `catmull-rom`; no
Lanczos-3 arm ran. Therefore the sentence adds **zero pixels** to the measured
Crop losses above. The `+0.1160 dex` versus `+0.0179 dex` passage is cited only
as prior source evidence and is not a number measured by M-COVER-NATIVE.

## Q4 — what Scale is, and how it is classified

### Current `CoverMode` documentation

**VERIFIED source reading.** Current
`crates\strehl-cli\src\align_cmd.rs`, symbol `CoverMode`, documents Scale:

> “[`CoverMode::Scale`] shrinks the reference grid by `k <= 1` about the plane
> centre and composes that scale into every placement, so the same pixel
> dimensions come out. **The dropped field of view is paid for by an upsample
> of `1/k` at every pixel of every render**, and because `S_k` rides on every
> placement, the reference frame -- whose placement is the identity, and which
> would otherwise pass through the interpolator untouched -- is resampled too.”

It documents Crop:

> “[`CoverMode::Crop`] composes **nothing**. It renders the covered rectangle at
> unity scale and emits it, so the output is about `k*W x k*H` instead of
> `W x H` and no upsample happens anywhere. A frame whose placement is an
> integer translation -- the reference frame's identity is the extreme case --
> then reaches the output through an interpolating kernel evaluated exactly on
> a sample, which is a copy.”

And it states the exact two-price passage:

> “The price of `Crop` is the one the doc on [`fit_to_cover`] named: **the
> output dimensions change**, which is why it is opt-in and why
> [`CoverMode::Scale`] is still the default. There is a second price that is
> easier to miss: the merge still runs on the full plane, so frames that do
> not reach the border still fold their black fill there, and the pyramid's
> coarse bands spread that fill inward some distance before the crop discards
> it. Measure a border profile before trusting the outermost pixels.”

### Classification

**Scale is a DOCUMENTED, INTENTIONAL PRODUCT TRADE and simultaneously a HARD
SCORECARD-CONFORMANCE FAILURE under §1.5 native scale.**

- **Documented and intentional:** it deliberately exchanges field of view and
  an all-pixel `1/k` upsample for stable output dimensions and full-frame
  coverage.
- **Hard conformance failure:** current §1.5 says “Outputs must retain native
  scale. Resize is a hard invalidation.” The frozen Scale arms measure
  0.2901–0.4619% disagreement against the `<=0.10%` gate. Preserving the output
  dimensions does not cure that scale failure.
- **Not established here as a general picture-quality defect:** prior
  `M112-real-pixels.md` found that removing the coverage scale did not recover
  the expected sharpness on the relevant real-stack evidence.
  `BUILD-CROP.md` likewise limits its claim to mechanism rather than general
  quality. These are prior results, not Q4 measurements.
- **Not a simple export-setting bug:** Scale changes the placement composed
  before interpolation; Crop changes the emitted rectangle only after the
  full-plane merge has already admitted black fill and spread it through coarse
  pyramid bands. Changing only TIFF export settings cannot satisfy both sides.
- **No default recommendation:** prior `cover-default.md` keeps Scale because
  Crop's boundary problem is worse and unresolved; its decision remains
  **CLOSED — keep Scale**. This lane neither advocates a default change nor
  reopens that scorecard decision.

`M104-resample-verify.md` is relevant prior method evidence because it separates
native sampling from field of view and treats changed dimensions as a trap
rather than evidence of sharpness. It is not quoted as a new measurement here.

### Why Q3 does not supply a conforming existing mode

| Existing mode | Native output dimensions (§1.3) | Native scale (§1.5) | Common overlap / sites |
|---|---|---|---|
| Scale | PASS | **HARD FAIL** on the frozen scale audit | Full dimensions, but the native-scale gate already invalidates it |
| Crop | **FAIL 8/8** | PASS for the specific frozen scale/rotation audit; residual still UNMEASURED | 100% geometric common-overlap containment, but clean-site/border admission remains UNMEASURED |

Thus neither offered mode satisfies all current rules. **ARGUED, speculative
only:** if a future lane finds the distinction useful, it would need a
native-size, no-resample output representation—for example, preserving a
unity-pitch interior on a native canvas while marking the exterior explicitly
invalid—plus scorecard-admitted border, invalid-pixel, common-overlap, and site
semantics. Current rules do not license that representation merely because it
can be described. This report does not design it, edit it, or recommend
shipping it.

## Prior-art boundary

**VERIFIED as design provenance, not remeasurement.**

- `BUILD-CROP.md` and `cover-default.md` establish Crop as the no-coverage-
  resample arm while warning against trusting its outer pixels; Scale remained
  the default.
- `M103-halfdrift.md` separates geometry repair from a sharpness claim.
- `M112-real-pixels.md` motivates evaluating only verified covered support.
- `M95-coverage.md` and `M95-dose.md` show that coverage resampling is not the
  whole quality mechanism.
- `M104-resample-verify.md` distinguishes native sampling from field of view.
- `M99-photometric.md` requires scene-fixed interpretation of level changes.
- `V-RIM.md` disqualifies its rim statistic as a generic border certificate.
- `M-PHASE0-SPLIT2.md` licenses analytic translation without metric
  resampling.
- `SCORECARD-BASELINE.md` records the original Scale geometry rejection and
  absent common-TIFF adapter.
- Current scorecard §3.2 already records `COVER / default path` as
  `CLOSED — keep Scale`; this lane does not reopen that decision.
- Live `M-COVER-BORDER` owns border contamination. This phase did not open its
  results as a new measurement and did not implement a border-profile
  instrument.

No `M8-overshoot` content was read or duplicated.

## Limitations

- **DETERMINISTIC, NOT BLINDED:** Phase A had already observed all eight Crop
  dimensions. Q3 commissioned the header parser and loss predicate, then
  reproduced and cross-checked known headers and hashes.
- **DERIVED:** width, height, and area percentages are arithmetic from fixed
  integer dimensions; they are not independent experimental observations.
- **UNVERIFIED:** comparator output geometry; no comparator was rendered or
  measured here.
- **UNVERIFIED:** formal common-input identity; the common-ProPhoto-TIFF adapter
  is still absent.
- **UNVERIFIED in this phase:** Crop outer-pixel cleanliness. Existing Crop
  design records warn about the boundary, and `M-COVER-BORDER` owns its live
  instrument.
- **LIMITED:** the ECC audit is whole-image, downsampled, affine, and
  post-score rejection-only, whereas current §1.5 literally names
  input-derived landmarks.
- **UNMEASURED:** the unchanged four-tile residual reader reports nonzero
  residuals but fails pure-translation nulls and cannot license an 8/8 failure.
- **Q4 SCOPE:** source documentation and prior-art classification do not
  establish a general visual-quality defect, license a default change, or
  establish the speculative native-canvas representation.
- **CURRENT SCORECARD:** M1 is withdrawn for lack of an admissible statistic and
  bar, independently of this geometry result.
- **DEVIATION:** concurrent ignored-file growth under protected
  `experiments\M8-overshoot` prevents a whole-tree “unchanged” claim for that
  path; frozen inputs, caches, tracked protected state, and all owned outputs
  remained auditable.

## Superseded earlier ruling

This ruling answered the earlier native-size/default-path brief. Amendment 2's
scorecard-specific ruling at the top of this report controls.

**MEASURED/VERIFIED: Crop fixes the specific native-scale magnification
failure, but it does not unblock M1 or produce a conforming existing cover
mode.** Every Crop arm passes the frozen scale/rotation audit, every Crop arm
fails the native-size program-output clause, and the exact Q3 field loss is
20–32 columns, 16–24 rows, and 0.624740–0.964678% of native area while retaining
100.000000% of the frozen common rectangle geometrically. Scale preserves
dimensions through an intentional all-pixel resample and therefore hard-fails
§1.5 native scale; Crop avoids that resample but changes dimensions and retains
an unresolved boundary.

Residual geometry and clean-site survival remain unmeasured by an admitted
instrument, the current COVER gate remains **CLOSED — keep Scale**, the
common-input adapter/comparator arms remain absent, and current M1 has no
statistic or bar. Formal competitive comparison remains `UNMEASURED`.
