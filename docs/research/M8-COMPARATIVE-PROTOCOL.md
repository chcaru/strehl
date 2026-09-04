# M8-COMPARATIVE-PROTOCOL — manufacturing a foreign-render contract

**Status: specification only. No render was made and no holdout was opened.**

## 1. Decision

The contract can be manufactured under full input control.

| candidate | protocol disposition |
| --- | --- |
| Zerene PMax | **conditionally manufacturable**; needs a valid Professional licence and all pixel gates |
| Zerene DMap | conditionally manufacturable as a separately preregistered project |
| retained `focus-stack` CLI | **conditionally manufacturable** through its documented `--no-align` bypass |
| Helicon Focus | not admitted; no verified bypass plus tagged-linear output contract |

The primary comparative boundary is the set of already-warped TIFFs delivered
to the foreign stacker. Every TIFF is on one common integer grid. The foreign
stacker is instructed to treat those files as already aligned and is not
allowed to crop, rotate, scale, shift, brightness-match or reinterpret their
colour encoding. At that boundary the placement of every frame is the identity,
the interpolation support is one source pixel, and the resampler negative mass
is zero.

That statement is conditional on measured admission gates. A checkbox or
command-line flag is not evidence by itself. The run is `UNMEASURED` if the
stacker cannot export or otherwise prove the pixel planes it actually used, if
the output grid fails the geometry witness, or if the output does not carry the
frozen linear profile.

The narrow licensed claim remains:

> **M8-O can establish invention. It cannot name the inventor.**

Even after input alignment has been removed as an explanation, an excursion may
come from pyramid reconstruction, local contrast, deconvolution, a non-convex
merge, sharpening, or an omitted transform.

This is a controlled merge audit, not a default-settings product benchmark.
Disabling a comparator's normal alignment deliberately removes one part of its
product. Any result applies to the named build and identity-input configuration,
not to every image the default application produces.

## 2. Scope and governance

1. Before reading any output, register the subject, uninterrupted capture
   session, reference frame, frame list, prepared-image crop, comparator build,
   comparator settings, stacking method and complete scored site.
2. Check the scorecard and `docs/STATUS.md` immediately before touching a
   capture. Use only a row explicitly cleared as non-holdout, or a new capture
   assigned by the registrar. One member burns its full subject/session unit.
3. Do not use the nine retained renders. They remain `UNMEASURED`; this protocol
   creates new artifacts with a different evidence contract.
4. Run each registered method as a separate project. PMax is the primary
   Zerene arm; DMap is optional. Never let one method inherit another method's
   project or aligned cache.
5. Make no manual retouch, levels, curves, output sharpening or colour edit.
6. Freeze every executable, script, ICC, XML/configuration file and manifest by
   SHA-256 before the first comparator output is opened.
7. Treat all comparative readings as candidates until the scorecard registrar
   licenses the comparative clause.

## 3. Prepared-input contract

### 3.1 Decode and pre-alignment

Prepare all frames once, outside every comparator:

1. Decode each RAW through one frozen decoder invocation into one documented
   linear RGB domain. Apply no sharpening, denoise, texture, clarity, dehaze,
   local tone or output tone curve.
2. Choose one reference frame before examining comparator outcomes.
3. Solve and freeze one output-to-source placement per frame. Record full
   precision coefficients, coordinate-centre convention, source orientation,
   boundary rule and exact source SHA-256.
4. Warp each decoded frame exactly once, in floating point, into the reference
   plane with one frozen resampler.
5. Select the largest integer rectangle valid in **every** warped frame,
   including the complete resampler support. Freeze that crop from geometry
   alone. Do not fill invalid borders and later call them observations.
6. Apply either no per-frame photometric correction, or a correction whose
   executable formula, coefficients and order are frozen before the prepared
   source boundary. The simplest and preferred arm has none.
7. Quantise every prepared frame with the same round-to-nearest rule.

For the common Zerene-versus-strehl end-to-end arm, use the exact placement
sidecars and crop that the frozen strehl run consumes. The external prewarper
must replay them; it must not independently solve a near-equivalent transform.

The prewarp transform is relevant to an optional end-to-end audit against the
decoded RAW planes. It is not part of the primary foreign-render M8-O
placement: the serialized prepared TIFFs are the declared inputs, so their
placement into the comparator is identity.

Any negative-lobe excursion introduced by prewarping is therefore already
inside the prepared source hull. The primary reading measures invention after
the comparator's declared input boundary; it does not credit or blame the
comparator for prewarp artifacts. Section 10 defines the separate end-to-end
accounting.

### 3.2 TIFF schema

Write every prepared input with one canonical writer:

| field | required value |
| --- | --- |
| dimensions | identical frozen `W x H` for every frame |
| samples | RGB, chunky, three channels, no alpha |
| sample type | unsigned 16-bit integer |
| compression | none |
| orientation | TIFF Orientation `1`; no EXIF rotation |
| colour domain | linear sRGB / BT.709-6 primaries, D65 |
| profile | one embedded, byte-frozen linear-sRGB ICC |
| transfer curve | identity in all three channels |
| metadata | no crop, scale, develop or orientation instruction |

The ICC is an input artifact, not a name inferred from a folder. Before use,
publish its SHA-256 and independently parse its description, `rXYZ/gXYZ/bXYZ`,
white point and three identity TRCs. Every input must carry byte-identical ICC
bytes. This is the domain emitted by strehl's measurement-safe
`--linear-srgb` path; do not use `--srgb`.

For every TIFF record:

* whole-file SHA-256;
* canonical `W x H x 3` pixel-array SHA-256;
* source RAW SHA-256;
* reference frame and exact prewarp sidecar SHA-256;
* ICC SHA-256;
* minimum, maximum and counts at 0 and 65535 by channel.

Write an ordered `prepared-manifest.json`. Comparator launchers must consume
that order explicitly; do not rely on a filesystem glob or locale sort.

### 3.3 Identity placement manifest

Create a checker input manifest containing, for every prepared frame,

```text
placement = [[1, 0, 0], [0, 1, 0]]
support   = one sample at (x, y)
validity  = full frozen W x H rectangle
```

The checker must refuse this manifest unless the comparator-specific evidence
in §4 has passed. Identity is a measured admission, not a user assertion.

## 4. Proving identity from pixels

Four independent gates are mandatory.

### 4.1 Prepared-frame equality

Canonical-decode every file immediately before comparator launch and reproduce
the pixel-array hashes in `prepared-manifest.json`. This proves what was handed
to the comparator, not what the comparator used.

### 4.2 Comparator-adjusted-plane equality

When the comparator can export the adjusted/aligned inputs it actually used,
export every one. Canonical-decode them and require exact pixel-array equality
with the prepared inputs, frame by frame. Metadata and TIFF strip layout may
differ; sample arrays may not. Extract the ICC from each adjusted image and
require byte equality with the prepared-input ICC.

For Zerene this is the load-bearing pixel test:

* save **File > Save Adjustment Parameters**;
* save **File > Save Other > Save Adjusted Input Images**;
* require every adjusted-image pixel array to equal its prepared source;
* require every saved adjustment to be identity and every brightness
  adjustment to be neutral.

Zerene documents “Save Adjusted Input Images” as a Professional-only feature.
Use a valid licence that exposes it. The currently installed expired trial
cannot save output and is not an execution path.

Before the first scored Zerene run, obtain and archive vendor confirmation that
“Save Adjusted Input Images” exports the adjusted pixel planes used by the
stacking operation, not a screen preview. Without that confirmation the files
remain a strong diagnostic but not the sole basis of the contract.

For a CLI comparator that cannot export adjusted planes, require a documented
true bypass plus §4.3. “Maximum shift = 0” is weaker than a bypass and is not a
substitute unless a pixel commissioning arm proves it.

### 4.3 Output-grid identity witness

Before the subject run, execute a non-capture geometry witness with the same
build, input schema, dimensions and geometry settings:

1. Generate a frozen, full-frame, aperiodic coordinate code containing unique
   coloured impulses, border codes, horizontal/vertical ramps and asymmetric
   corner marks.
2. Feed byte-identical copies of that image through the same source-count and
   output path as the subject run.
3. Test the **registered identity map only**. Do not estimate or fit a shift,
   affine transform or crop from the output.
4. Require the output dimensions and orientation to match exactly and every
   decoded coordinate mark to land at its registered integer coordinate.
5. Require border marks at all four sides to survive at their registered
   coordinates; this rejects crop-then-resize paths that preserve dimensions.
6. Commission the verifier before use:
   * GREEN: untouched identity path passes;
   * RED: planted `+0.25 px` translation, non-unit scale, 90-degree orientation
     and one-pixel crop each fail;
   * improvement: restoring the planted arm to identity changes reject to pass.

The witness must be specified and committed before it is rendered. A failure is
not repaired by fitting the observed transform. It makes the comparator arm
`UNMEASURED` until rerun under a configuration that passes.

Commit the decoder, coordinate list, arithmetic, tolerances and pass predicate
with the witness. “Looks aligned” and an interactively chosen correlation
threshold are not gates.

For the actual subject run also require the exact adjusted-plane equality in
§4.2, output `W x H`, Orientation `1`, and the output's recorded registration
values to be identity. The synthetic witness alone does not certify a different
configuration.

### 4.4 Linear-domain witness

Use the adjusted-input export to verify the colour path without asking the
merge to be value-preserving:

1. Prepare a non-capture TIFF containing full-frame constant RGB values and
   large constant channel patches at preregistered uint16 codes.
2. Load it through the exact comparator input configuration and save it through
   the adjusted-input export.
3. Require canonical pixel-array equality and byte-identical ICC bytes.
4. GREEN is the untouched linear path. RED plants are a gamma-encoded array
   under the linear tag, a non-identity channel matrix and the wrong ICC; each
   must fail. Restoring the correct array/profile must pass.

This proves the comparator's input decode and adjusted-image save path do not
silently tone-map or colour-convert the declared values. The direct stack output
must still carry the same ICC and saving configuration. A merge that changes
values is an M8 observation, not automatically a domain failure.

## 5. Zerene Stacker protocol

### 5.1 Owner prerequisite

Install a valid Zerene licence before scheduling the run. A Professional
licence is required for the adjusted-input export used by §4.2. Do not attempt
to bypass the expired-trial save restriction.

The registered starting build is Zerene Stacker
`1.04 Build T2026-05-04-0750`, with:

```text
C:\Program Files\ZereneStacker\ZereneStacker.jar
SHA-256 E138CE88BEDF2CFAB7EF78AA2398A57CA4944EC09571C285A0A11C10BCB4E549
```

Recheck the hash after licence installation. If the owner updates Zerene, stop
and register the new build before running controls.

Record:

* Help > About build string and screenshot;
* SHA-256 of `ZereneStacker.jar`;
* SHA-256 and full text of `%APPDATA%\ZereneStacker\zerenstk.launchcmd`;
* SHA-256 of `%APPDATA%\ZereneStacker\zerenstk.cfg`;
* Java executable/version and heap arguments;
* the complete saved batch XML.

Use the vendor-documented batch launcher derived from `zerenstk.launchcmd`.
Add only `-noSplashScreen`, `-exitOnBatchScriptCompletion`, `-runMinimized`,
`-leaveLastBatchProjectOpen` and `-batchScript <frozen.xml>`. Drain stdout and
stderr and retain `LastNormalLog.txt`.

### 5.2 Set these GUI controls

Set the controls in the GUI, then use **Batch > Save Batch Script** and audit
the generated XML. Do not guess companion fields by hand.

Give Zerene an isolated input directory containing only the prepared TIFFs,
named with the manifest's zero-padded ordinal prefix. With automatic ordering
off, verify the Input Files list exactly matches `prepared-manifest.json`
before saving the batch XML.

**Options > Preferences > Preprocessing**

* check **Add files to existing project as already aligned**;
* disable precrop;
* disable prerotation and set degrees to `0`;
* disable presize and set scale to `1.0`;
* keep input orientation at TIFF Orientation `1`.

The vendor's slabbing instructions explicitly use “Add files … as already
aligned” before stacking pre-aligned slab outputs. In batch XML the controlling
key is:

```xml
<AlignmentControl.AddNewFilesAsAlreadyAligned value="true" />
```

**Options > Preferences > Alignment**

* uncheck X shift;
* uncheck Y shift;
* uncheck rotation;
* uncheck scaling;
* uncheck brightness/contrast correction;
* disable automatic reordering.

Audit these XML values:

```xml
<AlignmentControl.AllowRotation value="false" />
<AlignmentControl.AllowScale value="false" />
<AlignmentControl.AllowShiftX value="false" />
<AlignmentControl.AllowShiftY value="false" />
<AlignmentControl.CorrectBrightness value="false" />
<AlignmentControl.Order.Automatic value="false" />
```

Set all four maximum movement limits to zero if the installed build accepts
zero. If it rejects zero, retain the disabled booleans, record the rejected
attempt, and rely on adjusted-plane equality rather than silently restoring a
positive allowance.

Audit the non-alignment geometry keys:

```xml
<Precrop.Selected value="false" />
<Prerotation.Degrees value="0" />
<Prerotation.Selected value="false" />
<Presize.UserSetting.Scale value="1.0" />
<Presize.UserSetting.Selected value="false" />
<Presize.Working.Scale value="1.0" />
<SkewSequence.Selected value="false" />
```

**Options > Preferences > Color Management**

* leave fallback handling at **Use EXIF/DCF rules**; it is irrelevant because
  every input embeds the frozen ICC;
* select **Copy input profile** for output;
* enable input-profile use for display only as an operator sanity check.

Audit:

```xml
<ColorManagement.InputOption value="Use_EXIF_and_DCF_rules" />
<ColorManagement.OutputOption value="CopyInput" />
```

The output ICC must nevertheless be extracted and byte-compared with the input
ICC. A copied-profile checkbox is not enough.

**Options > Preferences > Image Saving**

* TIFF;
* 16 bits per colour;
* no compression;
* **Retain full dynamic range off**;
* copy source EXIF metadata off;
* no metadata-driven resize or external save conversion.

Audit:

```xml
<SaveImage.FileType value="tif" />
<SaveImage.BitsPerColor value="16" />
<SaveImage.CompressionType value="none" />
<SaveImage.PropagateEXIF value="false" />
<SaveImage.RescaleImageToAvoidOverflow value="false" />
```

The vendor documents “Retain full dynamic range” as a brightness/contrast
rescale used to avoid clipping. It is forbidden because it changes the
radiometric map. With it disabled, report rail occupancy; clipping preserves
the one-sided M8 caveat.

**PMax**

```xml
<PyramidControl.RetainUDRImage value="false" />
<PyramidControl.RetainOnlyUDRImage value="false" />
```

Run plain PMax with no retouch. A DMap arm, if registered, must be a separate
fresh project with estimation radius, smoothing radius and contrast threshold
frozen before output. Do not choose a threshold from the result.

**Options > Preferences > Multiprocessing**

* disable “use all cores”;
* select exactly 6 processing cores.

Audit:

```xml
<Multiprocessing.SelectedNumberOfCores value="6" />
<Multiprocessing.UseAllCores value="false" />
```

Use this output naming template:

```text
M8-{method}-XS{XS}-YS{YS}-RO{RO}-SC{SC}-CB{CB}-N{numinp}
```

The vendor documents those tags as the selected alignment controls and input
count. The filename is redundant evidence, not a replacement for the XML,
adjusted pixels and output description.

### 5.3 Zerene admission after the run

Do not open the image for visual selection. First require:

1. batch XML hash matches;
2. all prepared source hashes match;
3. `AdjustmentParameters.txt` reports identity/neutral values;
4. all saved adjusted input pixel arrays equal the prepared arrays;
5. output description lists the expected sources and identity registration
   values;
6. output witness passed on the same build/configuration;
7. output is exactly `W x H x 3`, uint16, Orientation `1`;
8. output ICC bytes equal the frozen input ICC;
9. no UDR, retouch or rescale output exists in the scored path.

Any failure is `UNMEASURED`, not an invitation to estimate a correction.

## 6. `focus-stack` CLI protocol

The second candidate is deliberately the currently retained custom CLI:

```text
C:\dev\macro\focus-stack\dist\focus-stack.exe
SHA-256 0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D
```

Recheck that hash immediately before execution; a mismatch requires a new
registration. This binary's help defines `--no-align` as “Skips the alignment
completely, overrides all other alignment options.”

Pass the ordered input file list explicitly and use:

```text
--no-align
--no-transform
--no-whitebalance
--no-contrast
--nocrop
--input-colorspace=linear-rec2020
--internal-colorspace=linear
--output-colorspace=linear-rec2020
--output-bitdepth=16
--hdr-preserve=off
--threads=6
--output=<fresh-output.tif>
```

`--no-transform`, `--no-whitebalance` and `--no-contrast` are deliberate
redundancies. Retain the complete help text, executable hash, command line,
stdout, stderr and output hash. Freeze every merge option, including defaults;
do not let a later build redefine them.

This binary cannot emit linear sRGB. Do not silently feed it the main
linear-sRGB prepared set and pool its result with Zerene/strehl. Derive a
separate linear-Rec.2020 prepared set from the same prewarped floating planes
with one frozen matrix and ICC, then use the command above. Its M8 reading is
valid within that registered Rec.2020 arm but is not directly pooled with the
linear-sRGB rate; M8's channelwise hull is colour-basis dependent.

Require the same geometry witness and output schema as Zerene. If the CLI omits
the ICC, attach the frozen profile in a metadata-only canonicalization step and
prove the canonical pixel-array SHA-256 is unchanged before versus after. The
render-time command and log remain the domain declaration; the attached profile
prevents downstream ambiguity.

Helicon is not an active arm in this protocol. Its public controls describe
allowed shift, rotation and magnification ranges, but this lane has not verified
a true alignment bypass or a tagged linear 16-bit output path. Setting ranges
to zero without pixel evidence would repeat the error this protocol exists to
remove.

## 7. Output contract

The scored foreign output must be:

* the direct automated stack output, before retouch or downstream editing;
* exactly `W x H x 3`, uint16, Orientation `1`;
* uncompressed TIFF;
* tagged with the byte-frozen ICC for that arm's declared linear domain;
* accompanied by the exact batch/configuration, build hash, log, source
  manifest and output SHA-256;
* accompanied by channel minima/maxima and counts at both rails.

The existing strehl files

```text
C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff
C:\dev\strehl-out\DELIVER-V6\masters\119MSDCF.tiff
C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff
```

are explicitly inadmissible. They are `4688 x 7032 x 3`, sRGB, “For viewing”
outputs with nonlinear tone rendering. Inverting them cannot recover clipped
values.

The current `strehl stack` command accepts a directory of RAW files, not the
prepared TIFFs. Therefore do **not** compare the primary prepared-boundary rate
in §8 directly with an ordinary strehl self-reading and call the boundaries
equal. A truly identical TIFF-input merge comparison would require a future
registered replay path; this specification neither assumes nor implements one.

A common **end-to-end** comparison is still constructible without that feature:

1. use strehl's frozen post-demosaic, post-colour-matrix, pre-alignment
   `--linear-srgb --demosaic` planes as the common original source boundary;
2. freeze strehl's exact placements, centre convention, Catmull support and
   common crop;
3. materialize the foreign prepared TIFFs by replaying those same placements;
4. render a new strehl science output from RAW with the same frozen sidecars,
   crop, `--linear-srgb` and `--demosaic`, never `--srgb`;
5. measure both final outputs against the same original decoded planes and
   supports.

That end-to-end pair includes the foreign arm's materialization to uint16;
report its exact rounding allowance separately. It is the common-stack
comparative reading. The identity-boundary foreign reading in §8 remains the
cleaner diagnosis of what happened after the comparator received its files.
This protocol renders neither arm.

## 8. Primary M8-O computation

At the prepared-input boundary:

```text
lo(x,y,c) = min_k prepared[k,x,y,c]
hi(x,y,c) = max_k prepared[k,x,y,c]
```

All frames are valid throughout the frozen common crop. Placement is identity;
the support is one sample; fractional phase is `(0,0)`; resampler negative mass
is zero.

Do not write another hull implementation. A future producer-neutral adapter may
canonical-decode the prepared TIFFs and emit the existing checker's `.m8site`
input format with the frozen identity manifest, but the unchanged commissioned
checker must compute the hull, tolerance and violations. Commit and commission
that adapter before reading a subject output: an identity copy is GREEN, a
known out-of-hull upper/lower pair is RED, and replacing a planted non-identity
manifest with identity must restore the expected result.

Run the unchanged commissioned M8 checker. For uint16 output add exactly
`0.5/65535` serialization tolerance to the applicable ULP tolerance. Report:

* lower, upper and total violation counts;
* denominator over all output channel samples;
* denominator over samples with a valid source hull;
* rate against each denominator;
* signed minimum/maximum excess;
* absolute-excess median, p99 and maximum, normalized and in DN;
* sign counts and balance;
* every violating coordinate;
* rail occupancy.

For each violation define:

```text
e = max(lo - O, O - hi, 0)
delta = hi - lo
rho = e / delta, when delta > 0
DN = 65535 * e
```

Report `e`, `rho` and DN distributions. Count `delta=0` violations separately;
their normalized excess is undefined, not zero, and interpolation with
sum-to-one weights has no span from which to create an excursion.

Under the full-intersection crop the two denominators should be equal. If they
are not, the validity contract is wrong and the run stops.

## 9. Sharpening pair with one changed variable

Do not ask the comparator to merge twice. Render one admitted unsharpened merge
`M`, hash it, and derive both arms from that same file through one frozen
downstream program:

```text
arm 0: amount = 0.0
arm 1: amount = 0.5
S = M + amount * (M - G_sigma * M)
```

Freeze before execution:

* `sigma = 2.0 px`;
* the finite Gaussian support and all coefficient bytes;
* separable convolution order;
* boundary extension;
* arithmetic precision and rounding;
* output writer and ICC;
* whether channels are processed independently.

Both arms must decode `M`, pass through the same code path, and serialize once
with the same writer. Amount is the only changed byte in the configuration.
Retain the unclamped floating result and report how many values each uint16
serialization clips.

The source hull for both arms is the same prepared-frame manifest. This pair can
test the registered mechanism prediction that downstream sharpening raises
M8-O. It cannot prove that Zerene's intrinsic PMax contrast, or any advantage in
an unrelated retained render, was caused by sharpening.

Commission the downstream program before use:

* GREEN: amount `0` is sample-identical after the common serialization path;
* RED: an interior-edge amount `0.5` plant produces both signs;
* monotonic plant: registered positive amounts increase excess;
* improvement: reducing amount back to `0` removes the planted excess.

## 10. Phase-exact resampler bound

The primary prepared-input audit has identity phase and negative mass zero. An
optional end-to-end audit may instead ask whether the final render exceeds what
the **declared prewarp** could produce from the decoded source planes.

For one separable Catmull-Rom pass at sample phases `(t_x,t_y)`:

```text
n(t) = 0.5 * t * (1 - t)
N(t_x,t_y) = n(t_x) + n(t_y) + 2*n(t_x)*n(t_y)
delta_k = hi_k - lo_k
```

For frame `k`, interpolation alone is bounded by:

```text
[lo_k - N*delta_k, hi_k + N*delta_k]
```

Compute this per sample from the exact phases, weights and support actually
used. Do not substitute `0.0625`, `0.125`, `0.28125`, or another global
constant for the per-sample value.

For multiple linear resampling passes, compose the sparse coefficient row from
original source samples to that final sample. On the union support let:

```text
N_composed = -sum_i min(coefficient_i, 0)
```

Use that exact composed negative mass. Do not add per-pass bounds. The looser
operator bound

```text
N <= (product_j (1 + 2*N_j) - 1) / 2
```

may be reported as conservative, but cannot replace exact composition when
making a close claim. Spatially varying transforms require a different
coefficient row at every output sample.

Any colour matrix, gain, offset or other linear operation before the declared
boundary must also be composed or moved to the prepared side of the boundary.
The negative-mass formula assumes coefficients sum to one and there is no
offset. A general affine chain requires exact interval propagation including
its coefficient sum and offset. A nonlinear or undocumented step ends
mechanism attribution.

To bound a final merged output by this resampler interval, every downstream
operation must also be declared and hull-preserving, such as a convex merge.
Zerene PMax does not provide that operator contract. For PMax, the phase-exact
calculation can exclude the known prewarp/alignment resampler as the **sole**
explanation, but cannot certify what the complete proprietary merge can or
cannot produce.

Exceeding the exact bound licenses only:

> This sample cannot be produced by the declared resampler chain from the
> recorded source support.

It does not license “this sample was sharpened.”

## 11. Stop rules

Stop and report `UNMEASURED` if any of these occurs:

* source, executable, ICC, configuration or output hash differs;
* a selected capture is or becomes a holdout;
* prepared or adjusted input arrays differ;
* the geometry witness fails;
* any frame has invalid support inside the frozen crop;
* output dimensions, orientation, ICC or sample type differ;
* Zerene produces UDR/rescaled/retouched output instead of the direct arm;
* focus-stack silently aligns, crops, brightness-matches or changes colour
  domain;
* the sharpening arms differ in anything except amount;
* a transform or tone map is estimated from the scored output.

Do not repair a failed run in place. Register a new configuration and rerun from
the same frozen prepared inputs.

## 12. Imperative owner instructions

1. **Install a valid Zerene Professional licence.** The current expired trial
   cannot save the output or adjusted-input evidence. Do not bypass it. Ask
   Zerene support to confirm that Save Adjusted Input Images exports the planes
   used by stacking, and archive the response.
2. **Ask the registrar for one non-holdout subject/session.** Do not open image
   outcomes until the selection row is committed.
3. **Create a fresh run root under
   `C:\dev\strehl-out\M8-COMPARATIVE-CONTROLLED\<run-id>`.** Never write under
   `D:\personal\macro` or `D:\edited\macro`; treat both trees as read-only.
4. **Generate and freeze the prepared inputs and manifest exactly as §3.**
5. **Generate, preregister and run the geometry/domain controls before the
   subject.** Stop if any control fails.
6. **Set Zerene through the GUI exactly as §5.2, then save the batch XML.**
   Hash it before running.
7. **Run one fresh PMax project with `-leaveLastBatchProjectOpen`.** Do not
   retouch or select a prettier output.
8. **Save Adjustment Parameters and every Adjusted Input Image.** Put them in
   scratch, not beside the captures.
9. **Close the project and repeat from pristine inputs for any DMap arm.**
10. **Run the frozen focus-stack command as a separate candidate.**
11. **Execute admission checks before opening any result visually.**
12. **Only after admission, run M8-O and the downstream sharpening pair.**

## 13. Evidence basis

Vendor documentation:

* Zerene batch API and launcher:
  <https://zerenesystems.com/cms/stacker/docs/batchapi>
* Zerene's official slabbing workflow, including “Add files … as already
  aligned”:
  <https://zerenesystems.com/cms/stacker/docs/slabbing>
* Zerene colour-management behavior:
  <https://zerenesystems.com/cms/stacker/docs/options/preferences/colormanagement>
* Zerene 16-bit TIFF and “Retain full dynamic range” behavior:
  <https://zerenesystems.com/cms/stacker/docs/options/preferences/imagesaving>
* Zerene modification history for Save Adjusted Input Images, saved adjustment
  parameters and output descriptions:
  <https://zerenesystems.com/cms/stacker/docs/modificationhistory>

Repository evidence:

* `experiments/V-LINEAR/make_batch.py` records the working batch keys.
* `experiments/V-LINEAR/run_zerene.ps1` records the working vendor launcher and
  GUI-watchdog requirements.
* `docs/research/V-LINEAR.md` records the expired licence and the need for
  matched linear development.
* `docs/research/M8-COMPARATIVE.md` records the failed retained-artifact
  admission, one-sided interpretation and exact Catmull bounds.
* `strehl stack --help` states that the command consumes a RAW directory and
  that `--linear-srgb` is the measurement-safe linear output; it does not
  provide a prepared-TIFF merge input.
* `experiments/M8-COMPARATIVE/focus-stack-executable-provenance.json` records
  the currently located focus-stack binaries; the execution protocol must pick
  and hash one rather than infer which made an old render.
