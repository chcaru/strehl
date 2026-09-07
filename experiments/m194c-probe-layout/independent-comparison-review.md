# M194c independent fixed-benchmark comparison review

**VERIFIED for the recorded synthetic software comparison.** The final
candidate-2 package contains the complete fixed forty-output matrix on the
same actual input manifests, geometry and settings as committed M194b. The
source, compilation, executable, controller and actual image bindings pass
independent checks. The independently chosen numerical read reproduces the
reported movements and the one engineering alarm. This is a storage-layout
correctness repair with a measured adverse noise movement, not an overall
quality improvement or a SOTA admission.

Owner: `roadmap_audit`, 2026-09-07. Choices were written in
[independent-comparison-preregister.md](independent-comparison-preregister.md)
before candidate outputs. Product/sampler/Probe/alternate-layout verification
belongs separately to Zeno's [independent-report.md](independent-report.md),
whose final run 4 passes both gather modes and reads 48 delivered TIFFs. This
review does not substitute that test executable for the fixed benchmark's
different bound executable. No capture was read or altered here.

## Sources, controller and live controls

[independent-comparison-provenance.json](independent-comparison-provenance.json)
directly checks all 99 entries of the original compiler-source map and the
eight supplementary entries (three included Rust files plus five controller,
preregistration and lineage files). Every supplementary byte snapshot matches.
The union covers the actual three M194c external Rust includes, including the
nested legacy function. The only changed member of the original compiler map
is `crates/strehl-cli/src/merge_cmd/gatefloor.rs`. The actual RNG arithmetic
body exactly matches committed M194b after replacing only the destination
iterator expression. The six frozen M194b source/input-index records match
commit `444eb759be0358cda25e97d4375f977a039efe6a` byte for byte.

The actual build log contains `Compiling strehl-cli`, a non-fresh compiler
artifact and successful build completion. The live compiler artifact and its
isolated copied executable both match the recorded bytes and SHA-256
`5b6995310b211c512973ccf6b5c782d0b67dd15cebaa1bdcde2a0f84ad979724`.
The original M194b copied executable remains unchanged at SHA-256
`92d2a31b03152c88060d7c2355b6071acf73e74450ca1cd3606f85f6ee814dc5`.
These checks read the artifacts rather than accepting recorded success flags.

The supplementary attestation is deliberately separate from M194b's frozen
map, which the existing driver checks exactly. It binds the supplementary
source set across build, the entire forty-output render and scoring. Its
include recognizer covers this repository's actual declared forms; this is
not a general Rust dependency parser or an authentication claim for arbitrary
fully forged execution records.

Independent commissioning results, all retained:

- [Seven component checks](independent-comparison-controls.json) use an actual
  retained TIFF region, a +20 DN bias, spatial-only blur, an inert flat blur,
  R/B permutation and known repeat variance. Blur reduces a real wave response;
  it does not manufacture a flat response. Inputs remain unchanged.
- [Eleven API checks](independent-comparison-api.json) use a new 13x17 aspect
  ratio, an irregular mask, changes both inside and outside that mask, nine
  asymmetric repetitions, exact paired signs/SEM and four malformed refusals.
- [Six source-set refusals](independent-comparison-sources.json) reject omitted
  nested bindings, changed hashes and actual bytes, unbound extra members,
  coherently rehashed unreachable sources and a coherently removed include.
  The actual current set and private unchanged fixture both pass.
- [Twelve rehashed controller contradictions](independent-comparison-bindings.json)
  all refuse: omitted/changed/extra source bindings, false render argv, failed
  or missing scoring, false compiler delta, missing original-input binding,
  altered frozen scorer, changed final source, wrong baseline and wrong scored
  index. An unchanged complete controller copy passes before the original is
  checked again. These are new JSON copies alongside unchanged real artifacts;
  their top-level checksums are recomputed. They exercise content checks, not
  just stale-digest rejection.

The complete controller verifier also reopens the bound index and replays the
unchanged M194b reader against actual CFA/TIFF artifacts, requiring the recorded
score to match. M194b's already commissioned rehashed input/model/crop/target
refusals remain applicable because those scripts are byte unchanged. They were
not relabelled as new M194c tests or needlessly repeated.

## Independent actual-pixel result

[independent-comparison-read.json](independent-comparison-read.json) reads all
40 candidate TIFFs and all 40 baseline TIFFs, pairing by scene, repetition and
arm. All input manifest digests and parsed plans match, except the explicitly
different build stamp. It uses literal TIFF ROI rows 50:162/columns 46:238,
independent pupil integration and 32-node cell quadrature, direct complex wave
projection, streaming Welford variance, per-repeat MSE differences/SEM and an
independently formed leave-one-repeat-out variance-difference jackknife.

The native gauge is unchanged: crop quad(9,7), native offset(18,14), RGB16
284x212 and native ROI [64,256)x[64,176), 21,504 pixels. Values below are
post-WB linear DN, with TIFF samples multiplied by 14848/65535. Temporal
uncertainty comes from the eight whole repetitions, not from treating pixels
as independent samples.

All eleven final read checks pass. Maximum disagreement with the root
comparison is 1.52e-8 DN for RMSE changes, 3.41e-12 DN for wave amplitude,
zero for pixel RMS, 1.90e-12 DN² for temporal variance changes, 2.56e-7 DN²
for paired mean MSE, 1.34e-9 DN² for paired SEM and 1.44e-12 DN² for the
variance-difference jackknife. These are numerical agreement tolerances, not
image-quality bars or physical model uncertainty estimates.

Nineteen pairs change; twenty-one are complete byte matches. All twenty
single4 outputs and flat/noise-off/full9 are unchanged. Across all registered
whole-ROI/channel/target rows, RMSE change ranges from -0.215026 to +0.278286 DN.
No registered >1 DN RMSE-rise or >1 DN noise-off wave-loss alarm occurs.

The registered >2% temporal-variance alarm **does fire**, for flat/full9:

| Channel | Candidate/baseline variance | Variance change DN² | Paired jackknife SE DN² |
| --- | ---: | ---: | ---: |
| R | 1.0213676499 | +3.96203234 | 0.85704654 |
| G | 1.0253804785 | +4.65196078 | 0.88654097 |
| B | 1.0191812656 | +3.80151452 | 0.83945614 |

R and G cross the unchanged threshold; B still worsens. The paired flat MSE
changes are +3.90445, +4.60825, +3.87458 DN², with SEM 0.87537, 0.87045, 0.84617.
This is an observed adverse movement, not a zero effect excused as uncertainty.
No new seed, threshold or input was selected to suppress it.

The plane/full9 movements remain target dependent: mean MSE against the
continuous ideal rises by about 29.82–31.01 DN² while MSE against the in-focus
optical observation falls by about 1.27–1.46 DN². On its noise-off output,
wave 1 amplitude falls 0.531–0.534 DN and wave 2 rises 0.108–0.113 DN. An optical
observation target can favor attenuation; ideal error and wave rows prevent
that from being presented as general detail recovery. Neither target is a
commissioned universal attainable floor. The actual single4 comparator still
uses local probe index 0 while full9 uses local index 4 for original frame 4.

### Descriptive localization of the reported peak

After reading the reported maximum, a separate
[extreme localization](independent-comparison-extremes.json) directly checked
its location. This is declared post hoc and adds no acceptance threshold.
The largest component movement is 461 TIFF LSB, 104.446906 DN: flat/repeat 709/
full9 at native (142,170), red, **inside the scored ROI**. Its value moves from
2997.014481 to 3101.461387 DN against the flat target near 3000 DN, worsening
that pixel's truth error. That pair has 672 of 64,512 ROI components moving by
more than 10 DN. Small aggregate RMSE movement therefore does not establish
uniformly small or harmless pixel changes. The peak is not an outer-border
artifact, nor is maximum movement in general a quality metric.

## Disposition and retained corrections

Accepting the bounded repair for canonical storage correctness is defensible:
unused padding must not choose the probe realization; Zeno's independent
actual-gather/Probe/TIFF cases establish that property with live controls; and
the RNG sequence/arithmetic remains the legacy sequence for packed even data.
The registered engineering alarms explicitly request review rather than define
a universal promotion bar. Acceptance must preserve the real flat-noise alarm
and sparse adverse change above. It must not become a claim of overall quality
gain, harmless output differences, camera calibration or general RAW behavior.
The small-domain probe's sampling sensitivity remains a useful bounded
follow-up. No timing or new RAW comparison was performed here.

Pre-run review corrected the root's incomplete include discovery, overly broad
source-freeze set, native-versus-quad crop argument, then the actual crop-dict
shape. These are recorded in
[comparison-design-corrections.md](comparison-design-corrections.md); no output
existed at those corrections. One preflight during Zeno's source handoff refused
an external Rust file not yet included by the product module, correctly. Final
real source closure passes. Earlier source/API receipts are retained separately.

Candidate-1 completed its forty outputs, then the comparison refused because
the reader returned a tuple while JSON stored a list. The retained
[first failure](comparison-first-failure.json) shows zero numeric differences
and exact JSON-normalized equality. The correction normalizes JSON containers
without adding any numerical tolerance. Root produced candidate-2 after the
final comparison source and Zeno's separate test-lifecycle correction were
bound. A subsequent [direct rerun-byte check](independent-comparison-rerun.json)
matches all forty actual TIFF pairs between candidate-1 and candidate-2; this
is a build-binding repeat, not an independent noise realization. Candidate-1
is preserved; its completed render is not retroactively
labelled a successful final comparison. Zeno's report separately preserves the
test compile/setup failures. Its stats-flag equalities are inert option controls,
not proof of an active observer. No new product observer was added here.

## Reproduction and final bindings

These commands ran from the repository root with exit 0; their corresponding
`independent-comparison-*.json` and `.log` artifacts are retained. The binding
test creates new controller-copy names and never overwrites the original
controller. After the first successful run, an optional collision-free filename
suffix was added to permit repetition in the same artifact directory; the
same twelve controls and unchanged copy passed again. Both receipts remain.

```text
python -B experiments/m194c-probe-layout/independent-comparison-controls.py
python -B experiments/m194c-probe-layout/independent-comparison-api.py
python -B experiments/m194c-probe-layout/independent-comparison-sources.py
python -B experiments/m194c-probe-layout/independent-comparison-provenance.py --controller experiments/m194c-probe-layout/candidate-2/controller.json --sha256 460bcec07f4fb7df28af519b3a6becb4dc789ca55e571007d5b97bc418332bce
python -B experiments/m194c-probe-layout/independent-comparison-bindings.py --controller experiments/m194c-probe-layout/candidate-2/controller.json --sha256 460bcec07f4fb7df28af519b3a6becb4dc789ca55e571007d5b97bc418332bce
python -B experiments/m194c-probe-layout/independent-comparison-read.py --candidate-index experiments/m194c-probe-layout/candidate-2/run/run-index.json --index-sha 71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab --comparison experiments/m194c-probe-layout/comparison-2.json --comparison-sha 95c4bc9d99194fbe7d4787f4df04d282618121a0a4af15e08edbdd7f75e599bd
python -B experiments/m194c-probe-layout/independent-comparison-extremes.py
python -B experiments/m194c-probe-layout/independent-comparison-rerun.py
```

| Final artifact | SHA-256 |
| --- | --- |
| candidate-2/controller.json | `460bcec07f4fb7df28af519b3a6becb4dc789ca55e571007d5b97bc418332bce` |
| candidate-2/build.json | `64975e805b77552f81158424de066bc26903170372af61b84cf394d6743e643f` |
| candidate-2/run/run-index.json | `71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab` |
| candidate-2/score.json | `5963b7b5804e9b726bd0cb4ee561dd857c45b26c996625794d53b81d3aa83428` |
| comparison-2.json | `95c4bc9d99194fbe7d4787f4df04d282618121a0a4af15e08edbdd7f75e599bd` |
| run-candidate.py | `c47cc1d52cc4a9f5756e8dc1fd39d4e2d601c574a9f5ea815aba131de19f9c23` |
| compare-candidate.py | `71991f3296f85d3e0343a87d1c8c50b0b38141de7be9d70d9e26c02c4b86422a` |

All original inputs, image bytes and source bindings remain unchanged after
the independent read. No scorecard, model, threshold, product source or frozen
M194b artifact was edited by this review.
