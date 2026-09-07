# Intended noise files and authority controls: prospective verification

Source/design release from root; **no numerical import or execution yet**.
The held private-noise core, private reader and producer are not edited.
The genuine float authority is
`independent-full-array-verification-1/float-commission.json`, SHA-256
`3f18d8954347382b2dffe0ca501f93ef8da54c3b966a1a606851323d86277a2b`.

## Two separate, explicit verification budgets

The pre-emission authority controls and post-generation actual-CFA verifier
each have their own named **120 CPU seconds / 240 wall seconds / 32 MiB live
named backing arrays / 16 MiB total output** budget. These are verification
budgets; neither restarts or extends the generation budget. Each begins before
imports/setup and covers controls, source snapshots, reads, final persistence
and checks. Outputs are small metadata and bounded negative-control files;
unchanged primary arrays are referenced. No new noise draws, encoder calls in
the author core, optical calls, or full image generation are permitted.

The intended reader imports the held independent private reader by externally
pinned source bytes to reuse its strict JSON/NPY reader, independent key
algebra and floor/fraction Q oracle. It never imports the author sampler or
constructs any Generator. Authority controls necessarily load the actual
author authority helper and its committed core dependency in their normal
order, but call only the authority reader, its scalar reader and finish check;
they must record zero requested variates and Generator constructions.

## Closed intended-read result and acyclic gate

The independent actual-CFA result has exactly these top-level keys:

```text
schema                 "m194g-independent-noise-files-read-v1"
status                 "PASS_SOFTWARE_NOISE_FILES_ONLY" or "UNCOMMISSIONED_NOISE_FILES"
ref_root               "repository"
method                 "actual-native-cfa-files-v1"
manifest               FileRef
generation_result      FileRef
float_commission       FileRef
noise_commission       FileRef
execution_release      FileRef
invocation             original interpreter argv list
sources_before         repository path -> {sha256,bytes}
sources_after          same shape, equal on success
inputs_before          repository path -> {sha256,bytes}
inputs_after           same shape, equal on success
file_count             90 on success
noise_off_count        10 on success
noisy_count            80 on success
files                  FileRow × 90, exact registered order
controls               {check_count,checks:[{name,pass,evidence}]}
work                   named verifier-budget receipt
error                  null on success; otherwise primary error
finalization_errors    [] on success; secondary errors retained otherwise
```

Every FileRef is exactly `{path,sha256,bytes}`, repository-relative POSIX with
contained resolution. Each FileRow has exactly
`scene,seed,index,cfa,audit,minimum,maximum,noise_off_exact`;
`cfa` and `audit` are repository-relative FileRefs. `seed` is null or the exact
registered integer; `index` is an integer0–4. `minimum`/`maximum` are actual
u16 integer extrema. `noise_off_exact` is true for each noise-off row and null
for each noisy row. Each control has a genuine bool `pass`; check count is an
integer equal to the complete implementation's registered list length.

The existing held outer gate is unchanged: schema
`m194g-software-noise-admission-v1`, status
`PASS_SOFTWARE_NOISE_FILES_ONLY`, ref_root `repository`, and exactly the five
FileRefs `manifest,generation_result,independent_read,float_commission,
noise_commission`. The four data/upstream refs in the inner result equal the
corresponding outer refs byte-for-byte, with typed equality. `independent_read`
points to the actual persisted successful result above. The result never
references this subsequently written gate. The two upstream commissions and
generation result likewise cannot reference this downstream gate.

Bridge consumers must require the two exact schemas/statuses, source/input
before/after equality, null error, empty finalization errors, all90 exact
ordered rows, 10 exact noise-off rows and all controls passing. They bind the
actual result bytes and require its four refs to match the outer gate. The
outer gate does not convert a partial result into admission.

## Actual-CFA reader obligations and controls

Read all90 actual headerless little-endian u16[240,320] files, exactly153600
bytes each, with distinct paths/file identities and explicit native RGGB
origin(0,0). The exact two scenes, nine states, five original indices,
reference2, identity placements, levels, factors, gain/read constants and
WB convention are taken from the held interface. The range is inclusive
[0,15360]; below-black512 values are valid.

Reopen both upstream commissions and generation source/command/input closure,
the generation-result-to-manifest association, and every actual audit. Check
stream tuple/key/call types and actual Q hashes; require null seed/streams for
noise-off and typed zero pre-clipping rail counters. Independently encode the
five genuine primary scalar arrays for textured noise-off and constant12000
for flat noise-off. Read the80 noisy Q files without inventing their absent
P/R/X intermediates. Noisy pre-clipping evidence remains the actual audit
bound through the commissioned source; Q alone cannot reconstruct X.

Controls use the actual intended reader entrypoint and its consuming file
reader, with valid/restored companions: missing/duplicate/mislabeled rows,
typed aliases, wrong origin/reference/factors, incomplete generation or
upstream association, changed Q/audit hash, wrong seeded/noise-off metadata,
short/appended CFA and declared-versus-actual range. One private u16 value511
must pass the new range reader while an old minimum512 predicate rejects it;
one15361 value must refuse. Noisy payloads are not changed and then claimed
reproducible; noise-off one-code mutations provide an exact expected-value
destroyer. Whole packages and all90 payloads are never duplicated per attack.

## Actual authority consumer controls

Call `FloatAuthority` on the genuine external gate, read all five original
`scalar(index)` values and call `finish`. Test incomplete/error-bearing
comparison/component/render children, changed admitted projection, bool/index
or reference changes, swapped/refined primary association, duplicate file
identity, and unsupported/out-of-root paths. Rehash edited ancestors so the
intended consuming boundary is reached. Retain reopened valid/restored
companions, including actual changed-file-between-reads detection.

Exercise the actual helper's bounded `Reads.scalar` on duplicate-key, huge
shape, object/Fortran, short/appended and nonfinite fixtures, always with the
same declared[240,320] boundary and preallocation checks. A few bounded
negative payloads may be written, but unchanged original primary files remain
referenced and untouched. Fixture authorities remain private and ineligible
as real optical/noise authority. Refusal controls accept the named intended
error; unrelated budget or I/O failures leave commissioning incomplete.

Both programs require an externally pinned
`m194g-numerical-execution-release-v1` with the exact original argv and all
actual source/input hashes before importing numerical dependencies. Root
freezes final source hashes and concrete commands before any run. A final
failure revokes downstream success and preserves primary/secondary errors.

## Concrete source/control freeze

The three new sources are `independent-noise-verifier-support.py` (standard
library budget/release/persistence support), `independent-noise-authority-controls.py`
and `independent-noise-files.py`. Existing private-noise sources remain unchanged.
Only syntax/AST reads preceded the eventual externally pinned execution release.

Authority control IDs, **38 in this exact order**:

```text
genuine-authority-five-scalars
incomplete-authority
bool-width
wrong-reference
bool-index
swapped-primary-scalar
refined-primary-receipt
duplicate-primary-row
actual-hardlink-primary-identity
projection-mismatch
component-command-failed
component-child-failed
component-error
comparison-incomplete
comparison-error
comparison-finalization-error
missing-render-role
author-render-incomplete
author-render-error
reference-render-error
scalar-traversal
scalar-absolute-path
restored-genuine-authority
scalar-valid-private
npy-duplicate-descr
npy-huge-shape
npy-object
npy-fortran
npy-short
npy-appended
npy-nan
npy-negative
changed-input-at-finish
restored-input-at-finish
live-owner-alias
expired-owner-reuse
live-cumulative-allocation
genuine-final-restored
```

Intended-reader IDs, **37 in this exact order**:

```text
actual-full-ninety-entry
private-layout-entry
missing-bundle
duplicate-bundle
wrong-scene
bool-seed
bool-frame-index
missing-frame
wrong-focus
wrong-origin
wrong-reference
wrong-factors
extra-manifest-field
incomplete-manifest
restored-layout-entry
incomplete-generation
generation-source-change
generation-input-change
generation-error
generation-manifest-association
actual-full-entry-incomplete-generation
private-below-black-valid
old-black-floor-destroyer
actual-cfa-hardlink-identity
private-range-restored
cfa-short
cfa-appended
cfa-above-white
cfa-bool-extent
audit-q-hash
audit-seed
audit-key
audit-rail
audit-noise-off-stream
noise-off-one-code
restored-noise-off
restored-noisy-audit
```

Every refusing case must reach its named expected error fragment. Other
exceptions and incomplete control populations refuse the invocation. The
first intended check requires the genuine full entry and all90 actual files;
layout-only companion calls terminate explicitly without authority. Metadata
and audit faults exercise the same consuming functions as that full entry.
The known noise-off pixel perturbation is fixed at native(row17,column23),
+1 code, with its Q hash coherently changed before the exact-value check.
The live allocation rejection holds18MiB and requests another18MiB; the alias
and expired-owner controls cannot reset this invocation's budget. These are
engineering reader controls, not physical noise calibration.

The additive actual-hardlink control was registered before the first authority
run after root identified that duplicate-primary-row reaches only the earlier
index guard. It creates two distinct private scalar paths hardlinked to the
unchanged genuine primary0 NPY, and clones only first-two receipts plus their
primary-result/comparison/authority ancestors. Each receipt retains its own
actual index0/1 inputs. It asserts identical nonzero device/inode identity and
requires the actual `aliased primary file identity` refusal at index1. The
remaining three original rows are intentionally unreached in this negative;
genuine five-frame initial/restored/final calls remain mandatory. Both links'
logical lengths count toward the fixed16MiB output cap.

Before the first intended-reader release, root required two additive actual
entry controls. A persisted private copy of the generation result with status
PARTIAL goes through `read_files` with the genuine manifest and the full-mode
flag, requiring its generation refusal. A distinct private hardlink to the
511-valued CFA is read after its original through the same identity set and
must refuse the actual duplicate identity. The existing restored range read
uses a fresh set. The hardlink's153600 logical bytes are counted; no genuine
emission file changes.

Authority command shape (root freezes exact argv, fresh cache and digest):

```text
python.exe -X utf8 -X faulthandler -X pycache_prefix=.../cache-noise-authority-controls-1
  experiments/m194g-larger-pupil/independent-noise-authority-controls.py
  --release <released-json> --release-sha256 <external-sha>
  --float-commission experiments/m194g-larger-pupil/independent-full-array-verification-1/float-commission.json
  --float-commission-sha256 3f18d8954347382b2dffe0ca501f93ef8da54c3b966a1a606851323d86277a2b
  --output experiments/m194g-larger-pupil/independent-noise-authority-controls-1
```

Its release scope is `noise-authority-controls`; returned schema is
`m194g-independent-noise-authority-controls-v1`, success
`PASS_ACTUAL_FLOAT_AUTHORITY_CONTROLS`. It never writes the downstream gate.

The actual90 reader command uses a distinct fresh cache, source
`independent-noise-files.py`, release scope `noise-files-verification`, and
arguments `--release`, `--release-sha256`, `--manifest`, `--manifest-sha256`,
`--generation-result`, `--generation-result-sha256`, `--output`. The released
input list binds the actual manifest, generation result and both upstream
commissions before array reads. It emits `result.json` and, only on complete
success, `noise-admission.json`. The source map includes all executed source
dependencies and this design. Generation retains its separately frozen exact
ten-source set; these new sources do not retroactively change generation.

Reported `work` is the real pre-terminal receipt; the same cumulative budget
also enforces each subsequent result/gate persistence and post-write check.
The final input map includes actual CFA/audit/scalar and source files read by
the verifier. Actual runtime file hashes are rechecked at final persistence;
runtime files outside the repository remain named in the bound runtime record.
