# Common-TIFF variable count and dimensions

2026-09-08. **MEASURED / INDEPENDENT-CHECKER-PASS; final independent
saved-result review pending.** This report is written by the product author
from committed metadata and receipts. It is not the author's verification of
the product, a completed final audit, or a SYNTHESIS fold.

The once-run fixed24-case population and135-control saved checker completed.
The saved checker reports PASS_COMMON_RGB_DIMENSIONS_SOFTWARE_INTEGRATION,
software_integration_complete=true, and no failures. Its explicit physical
noise calibration, real geometry admission and quality admission flags remain
false. Final interpretation and complete saved-evidence/source review remain
a separate independent task.

## Change and measured scope

The existing common-RGB stack-to-image consumer now admits the separately
versioned common-tiff-stack-v2 manifest with2..8 ordered inputs, each shared
axis64..512 and at most262144 pixels. It retains identity-grid RGB16 storage,
f32 arithmetic, one frame prepared/folded at a time, injected noise, exactly
three Laplacian bands plus base, and fixed explicit merge settings. The
implementation changes runtime layout/count in the common-stack manifest,
consumer and writer modules; it does not add maps, a new merger or calibration.

Version1 still requires exactly three inputs at128x96. The exercised legacy
constant case retains its archived whole-TIFF bytes (SHA256 below); this does
not claim unchanged report or error timing. As documented in the held
implementation review, invalid cardinality now receives an explicit count
refusal after JSON parsing instead of serde's fixed-array length error.
Frame-companion freshness is checked after authenticated N: a preexisting-frame
refusal can retain the initial incomplete receipt where the old initializer
refused earlier. Version2 bounds each encoded TIFF by6*pixels+64KiB, at
most1,638,400 bytes;
manifest64KiB and detailed report192KiB remain bounded. The actual fixtures
exercise64x64,129x97,512x512 and the retained128x96 legacy case, not every
possible count/dimension combination.

The actual noisy plan retains HardFloor gate2, SoftPower, exponent2,
sharpen_per_octave1.4, BaseMean, InputRange and Mean fallback. Its simulation
law is independent per-channel Rademacher +/-8: RGB covariance diag(64,64,64),
zero cross-covariances and proxy variance24 in RGB16-code-squared units.
Actual frame/proxy/variance hashes and supplied BandGain values are retained.
These are declared generating laws and operator gains, not measured physical
noise calibration of developed RGB. The profile remains the exact548-byte
linear-ProPhoto-D50 file with SHA256
16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef.
M165's PROPHOTO_DISPROVED qualification is not reversed by this integration.

## Saved checker outcome

The independent checker records all24 cases as verified, process-complete and
resource-admissible. There were nine admitted TIFF outputs,13 early semantic
refusals with zero folds, and two late refusals preserving four completed
folds. Expected refusals are successful tests of refusal behavior, not completed
images.

| Cases | Fixed purpose | Recorded outcome |
|---|---|---|
| 00-02 | Distinct contributors atN2/64x64,N5/129x97,N8/512x512 | Exact independently rounded constant RGB codes and complete ordered folds pass. |
| 03 | Five identical asymmetric odd-grid address frames | Exact RGB payload, final row/column/corner and channel/address checks pass. |
| 04 | Five spatially structured frames with distinct scalar offsets | Maximum absolute error0 over37,539 RGB samples, against the preregistered<=1 code-value tolerance. |
| 05-07 | Identical noisy population, observer off/on/placebo | Whole TIFF and pixel payload equality both true. |
| 08 | Original v1 constant request | Archived whole-TIFF identity retained. |
| 09-16 | Counts0/1/9; axis bounds63/513; width4294967296 | Early count/grid/typed-u32 refusals as registered. |
| 17-21 | Invalid v1 count/grid, duplicate input, profile and proxy variance | Registered early refusals; zero folded frames. |
| 22-23 | Final-frame geometry and file-hash faults | Exact four-frame prefix retained; no admitted final TIFF. |

The135 saved controls comprise108 competing means, three mean restorations,
14 original destroyers, six associated restorations, three offset destroyers
and one offset restoration. All record passed=true. The alternatives include
omission, appended duplication and replacement of contributors; wrong fold
counts, floor instead of ceil geometry, changed last row/column/corner,
channel/address changes, observer pixel mutation, profile/noise changes and
restoration. They are fixed software controls, not135 independent statistical
replicates.

Constant/address payload and identity comparisons use exact code values or
hashes. Case04 retains the original<=1 RGB16-code predicate; its +8, column and
corner destroyers fail that same predicate. Its finite-fixture rounding
argument was specified before execution, not fitted to the observed zero
error. This does not prove arbitrary odd-pyramid arithmetic. Final review must
also preserve the disclosed case04 oracle authorship and interpretation.

For the noisy-on case, the final shared selection denominators contain7,128
zero and9,395 positive sites across the three Laplacian levels. The mean base
is excluded. These are accumulated shared-denominator populations, not separate
RGB-plane counts or per-frame below/above-gate classifications. The odd level
shapes are129x97,65x49,33x25,17x13. This mixture establishes exercised gate
behavior on the fixed synthetic fixture; it is not a quality/noise-improvement
metric.

The three noisy outputs share whole-TIFF SHA256
7cd09ca3c0a9e878308c14921b95446a04165fb4459f7ac0bb474aeae0e6865a
and pixel SHA256
27b77b5dafcdb7c71870afab46f0b8b9f0f12e067b76c149b24beeb131520278.
The v1 output's archived whole-TIFF SHA256 remains
1e6c9f9bd3146c0c8f7314c422e26c842eb45ba25d76d12adae8f8d690842f7e.
These are findings of the saved checker; this report did not decode those TIFFs.

## Actual commands and retained execution

All paths below expand under
R=C:\dev\blog\death-of-software\projects\strehl and
D=R\experiments\common-tiff-dimensions.
P is C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe.
These are compact spellings of actual retained argv, not new invocations.
The full literal arrays are in the linked release/outer/child records.

Successful build2 actually invoked:

    cargo build -p strehl-cli --bin strehl-common-input --jobs 2 --target-dir R\target\common-tiff-dimensions-2 --message-format=json-render-diagnostics --locked --offline

Its saved compiler evidence records a fresh product artifact and actual
Compiling strehl-cli. The retained executable is3,201,536 bytes, SHA256
172a52135ebee5853169cd3cd8bd8e9c97b4dc6ad5a886c20bfd57ea0a4a0684.

The childless admission and later controllers actually invoked:

    P -I -S -B D\run-recovery-stage.py --release D\work\recovery-recovery-release-1.json --release-sha256 5e22e9ae1068085e656385645314a3d62a5afd774e67cd5c7c16f8301f56c75f
    P -I -S -B D\run-recovery-stage.py --release D\work\render-recovery-release-1.json --release-sha256 8fa5ae2079668068b70a089a2d8018c1f022f9ac0e8ba64c20884b50981a7907
    P -I -S -B D\run-recovery-stage.py --release D\work\verify-recovery-release-1.json --release-sha256 8058a0f8c48945d1e80e39fde629133f7aae618dcff8bea911b0eedc00b45686

For example, actual product child00 was:

    D\build-2\strehl-common-input.exe --stack-manifest D\prepare-1\fixtures\case-00.json --manifest-sha256 7c779b43527416f19a1cd2c006f5946bf25d40a63b1bef89fc91e537b89b751e --report D\render-1\case-00\report.json --observer off

The original fixed24 argv and expected exits are retained in
[the render release](../../experiments/common-tiff-dimensions/work/render-recovery-release-1.json);
actual per-child commands, exit, EOF/drain, Job and raw-log refs are
render-1/child-00.json through child-23.json. No generator or build ran during
recovery. The actual independent checker child was:

    P -I -S -B D\recovery-checker.py verify --fixtures D\prepare-1\fixtures\index.json --fixtures-sha256 d07f356bdd7b2286b88404a337afd831319130e979b9adc27222d5ad71b1bf98 --run-bundle D\render-bundle-1.json --run-bundle-sha256 ef7efea74505abd3b7e76bb984e11a9ec6d1879797c55533fd7ad78f9766094b --output D\verify-1\check --source-sha256 fe2956a41824952fefc5b7fbef22daf34b364f28f32d66b29733bc4615310143

The recorded environment fixes two Rayon threads and offline Cargo. These
single executions are not a throughput benchmark or comparison.

| Stage | Actual controller wall, seconds | Parent CPU sample + completed child Job CPU, seconds | Actual exit |
|---|---:|---:|---:|
| Successful build2 |70.40699999999197|45.546875+110.453125|0|
| Failed preparation1 |2.9839999999967404|0.828125+1.953125|1|
| Saved admission |1.6560000000026776|1.359375+0|0|
| Render24 |19.311999999990803|8.984375+10.5|0|
| Verify |4.514999999999418|1.546875+2.6875|0|

Each parent retains its2 CPU/3 wall final allowance. Parent CPU is a sample;
terminal owned-Job CPU is counted once, with zero active/live child accounting.
Do not add the checker's internal2.671875 CPU sample again to its containing
2.6875-second Job. Its internal wall sample2.817267099992023 and1 CPU/2 wall
publication allowance have a separate scope. No complete all-work CPU total
or all-history resource compliance is asserted.

## Failures, additive recovery and chronology

The source application record preserves the post-apply hash-assertion failure
before publication, the separately issued formatting command that still ran,
and a later metadata newline-argument publication failure. Subsequent exact
reconstruction/format comparisons were recorded separately; the missing
intermediate bytes and first failure's cause are not invented.

Build1 refused at a scratch scanner canonical-path observation for a
proc-macro2 temporary rmeta file. The underlying cause was not established.
Owned failure termination reduced6 active processes to0; no product binary or
completed product compile was admitted. A separately frozen scratch-only
scanner correction, its fixed controls and a fresh build2 followed. Keep the
failed600 CPU/300 wall allocation and the separately granted successful build;
short actual samples do not refund either.

Preparation1's generator actually exited0 and created the59 files/24 cases,
but its parent refused the legacy ordinary-versus-Windows-verbatim path
association. The old parent remains REFUSED. Additive recovery preserved the
original190 bindings, added a closed ten-source operational namespace and
bound the unchanged compiled118-source closure and build2 executable. The
genuine new admission says SAVED_FIXTURES_ADMITTED, old_prepare_status=REFUSED,
subject_complete=false, with16,025,258 bytes of saved fixtures. This was
childless saved-byte admission, not a regenerated fixture set or a fabricated
successful old preparation.

The separate40-group recovery controls completed45 predicate invocations.
Their independent saved-control review recorded253 passed predicates, but its
publication history is material. The first verbose saved-reader stdout was
truncated; a compact metadata reread stayed distinct from the once-only controls.
An overlong publication command failed with Windows error206 before a process
or write. The subsequent owned-file publication call took22.6 seconds, exceeding
the original20 active-wall-second review allowance by itself. Original review
resource compliance is therefore not established; its exact total CPU is unknown.

Root acted on the reviewer's ACCEPTED controls message before that publication
overrun was reported, and then performed admission and the24-case run. Those
later events do not repair the review's overrun. Root subsequently granted a
prospective5 CPU/30 active-wall/1 MiB read finalization slice within the same
1 MiB retained review family; it reran no control or253-predicate evaluation.
See [recovery-controls-result-review.md](../../experiments/common-tiff-dimensions/recovery-controls-result-review.md)
for the preserved chronology, qualifications and exact records. Final independent
saved-result review must authenticate the later outcomes separately.

All previous preparation, scanner, review, archive and metadata reservations
remain retained. No global sum is fabricated from samples with different scopes,
and no later grant retroactively makes an earlier overrun compliant.

## Evidence anchors and remaining disposition

| Evidence | Commit |
|---|---|
| Product/source continuation |c9d84f93d27bf15f7b1a05f736902576aceb55f1|
| Successful build2 |ae83e07c18883d57c2be170ba22726f06d393c97|
| Failed preparation and original fixtures |133daa331fc31fbd94df231934899f3527ffc593|
| Additive recovery source |ece53b2ee70d8b6828a7db215f2fe0be143b9a2f|
| Actual recovery controls |ecea6f3dae408dbc236cf1fc4b3443a3d9280e56|
| Actual admission |436cc70fe721d19ac0656ba365a4d5458586a853|
| Actual24-case render |e5f3e8c02680cf9c9ca0f976b30bd5ab26c0a6ee|
| Actual saved verifier |671e10fa1485c78228e4c47014906ddfd2931ca3|

Primary outcome:
[verify-1/check/result.json](../../experiments/common-tiff-dimensions/verify-1/check/result.json),
31,792 bytes, SHA256
80384f8b86e8831908f03b7da33963070186fe1b0557a2b856ae751ef560241f.
Render parent SHA2567356f6c63ea57fe4af6ea337bbc8151dbd2238ec0695b950713e286ebdde2cad;
verification parent SHA256640139b1e50b9a3b883a9026f85e30f568888b12e75681c7af8ddd39b7f12e39.
Their actual outer records are
[render](../../experiments/common-tiff-dimensions/work/render-recovery-external-1-outer.json)
and [verify](../../experiments/common-tiff-dimensions/work/verify-recovery-external-1-outer.json).

For the initial draft, the product author read1,529,446 bytes of selected committed metadata/protocol
contents, including repeated reads, under the8 MiB report scope; Git revision
queries were metadata-only. This draft executed no TIFF decode, checker,
candidate, simulation, compiler or product and changed no held source.

The next integer-translation/crop charter remains a draft for a separate
commission after final validation. This report makes no fractional covariance,
real alignment, arbitrary developed-RGB calibration, quality or SOTA claim.
Final saved-result review is pending and must be recorded before this report
is promoted to a fully independently reviewed outcome.
