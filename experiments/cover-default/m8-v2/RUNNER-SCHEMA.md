# M8-v2 registered runner and provenance contract

`run_v2.ps1` is a one-shot, fail-closed operator runner for the M8 amendment.
`manifest_v2.py` supplies deterministic inventories and verification.  This
document does not relax `CHECKER-SCHEMA.md`; the checker CLI and result schema
remain authoritative.

The implementation creates no default output location, never removes an output
tree, and never writes beneath `D:\personal\macro`. Every output root and
staging file is explicit. A private output root must be absent, outside the Git
worktree, outside `D:\personal\macro`, and have an existing parent.
Reparse-point output ancestors are refused, and `TEMP`/`TMP` are pinned to the
private root's dedicated `temp` directory for builds, tests, and adjudication.
The absolute private-root spelling is limited to 64 characters so the
content-addressed trace filenames remain below Windows' legacy `MAX_PATH`
boundary even on hosts where long-path support is disabled.

## Frozen cases

| case | exact source directory below the registered root | N | ref | sidecar | SHA-256 | Crop |
|---|---|---:|---:|---|---|---|
| `flat-1s` | `flat-et1s-sw4-cpl` | 60 | 30 | `flat-1s.warpmap.txt` | `862C6FD8E1956FDD53F527A12809B3079226334265EDADFF8AA1F0EA3B9B828C` | `25,17,3466,2310` |
| `flat-2p5s` | `flat-et2.5s-sw4-cpl` | 61 | 30 | `flat-2p5s.warpmap.txt` | `0C2CF172F7577189D2EE6F19F281D1A5BA821E7EC4A2F4D13F0BB12B87D4C638` | `23,16,3470,2312` |
| `flat-6s` | `flat-et6s-sw4-cpl` | 65 | 32 | `flat-6s.warpmap.txt` | `60A33EA0513E6408313EAA5698106FEC9B23FD6E8E325C246141C1905F2427F3` | `25,17,3466,2310` |

The accepted roots are exactly:

```text
D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl
D:\strehl-out\cover-default-slide-v2\warpmaps
```

The released one-second copied reference is exactly:

```text
D:\strehl-out\cover-default-slide-v2\refs\flat-1s\DSC00046.ARW
SHA-256 3A5FC6993D0EC24468FD24684AABE7783FE06D3D85EEC040584330AF0153A03B
```

## Universal process contract

Every build/render/checker process is noninteractive. The runner first removes
all inherited `STREHL_*` variables and pins:

```text
CARGO_BUILD_JOBS=8
CARGO_INCREMENTAL=0
RAYON_NUM_THREADS=8
OMP_NUM_THREADS=8
OPENBLAS_NUM_THREADS=8
MKL_NUM_THREADS=8
NUMEXPR_NUM_THREADS=8
BLIS_NUM_THREADS=8
VECLIB_MAXIMUM_THREADS=8
STREHL_PYRAMID_WORKERS=1
```

Real arms additionally pin:

```text
STREHL_GATE_FLOOR=white
STREHL_FULLRES_GATHER=on
STREHL_DEFECT=off
STREHL_RESTORE=off
STREHL_ALIGN=1
STREHL_WARPMAP=<frozen explicit sidecar>
```

`STREHL_CONFIDENCE_MAP`, `STREHL_CONFIDENCE_DEBUG`,
`STREHL_GATE_FLOOR_SCALE`, and `STREHL_RESTORE_SIGMA` are absent. The normal
full arm leaves `STREHL_FIX_CA` absent and then requires the product log to say
that default CA is `CORRECTING`. The identity arm passes `--fix-ca off` and
requires the log to say it is off.

Every registered render command is:

```text
strehl.exe stack SOURCE --out OUTPUT --merge pyramid --cover scale|crop \
  --resampler catmull-rom --binned
```

The identity command also has `--fix-ca off`. It passes neither `--srgb`,
`--linear-srgb`, `--demosaic`, `--auto-exposure`, `--exposure`, nor
`--confidence-map`. Thus the output is the ordinary pyramid path,
full-resolution Catmull-Rom gather, camera-native/camera-linear binned RGB16,
with defect correction, restoration, auto exposure, and confidence pass off.
The named sidecar is mandatory, so `stack` cannot discover, solve, or cache a
sidecar in the source directory.

## Phase 1: PREPARE

Use a full 40-hex commit, not a ref or live worktree:

```powershell
pwsh -NoProfile -File experiments\cover-default\m8-v2\run_v2.ps1 `
  -Phase PREPARE `
  -OutputRoot D:\strehl-out\m8-v2-private\run-001 `
  -SourceCommit 0123456789abcdef0123456789abcdef01234567
```

Before creating the output root, the runner requires the complete committed
file set under `experiments\cover-default\m8-v2` to equal the checkout file set
and compares every checkout byte with its blob at `SourceCommit`. The related
released geometry and external-Q1 tools are checked the same way. This prevents
an untracked runner, checker, injector, fixture, producer, schema, or comparator
from entering a run.

PREPARE:

1. records the Git root tree and the complete `ls-tree` blob list;
2. creates one `git archive` and extracts it to exactly two private snapshots;
3. verifies the snapshots have the same recursive byte inventory;
4. copies `fixture_v2.rs` only to
   `crates\strehl-cli\examples\m8_fixture_v2.rs` in the instrumented snapshot;
5. runs `inject_trace_v2.py` only on that snapshot;
6. builds, with `--locked`, external target directories, and eight jobs:
   uninstrumented `strehl.exe`, instrumented `strehl.exe`, and
   `m8_fixture_v2.exe`;
7. proves both source snapshots did not change during Cargo builds; and
8. atomically writes `prepare.json`.

`prepare.json` has schema/version
`strehl-m8-v2-prepare/1`. It records the source commit, Git tree/blob identities,
archive, pre/post-injection snapshot identities, `Cargo.toml`, `Cargo.lock`,
`rust-toolchain.toml`, every M8-v2 tool, both Strehl binaries, the fixture
binary, exact commands/log hashes, Rust/Cargo versions, Python executable and
version, NumPy, tifffile, rawpy and LibRaw versions, OS, active Windows power
plan, and the complete capped environment. PREPARE performs no real render,
decode, EXIF read, or capture access.

## Phase 2: INPUT-MANIFEST

ExifTool must already be installed and available by the explicit command/path.
Absence is a hard refusal; no alternate EXIF implementation is selected.

Both outputs are new staging files for operator review. The `FinalPath` values
are the paths at which the exact staged bytes will be committed and later used:

```powershell
pwsh -NoProfile -File experiments\cover-default\m8-v2\run_v2.ps1 `
  -Phase INPUT-MANIFEST `
  -OutputRoot D:\strehl-out\m8-v2-private\run-001 `
  -CaptureRoot D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl `
  -SidecarRoot D:\strehl-out\cover-default-slide-v2\warpmaps `
  -ExifTool C:\Tools\exiftool.exe `
  -InputManifestStage C:\review\m8-input-manifest.json `
  -InputManifestFinalPath C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-input-manifest.json `
  -RunPlanStage C:\review\m8-run-plan.json `
  -RunPlanFinalPath C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-run-plan.json
```

The input manifest schema is `strehl-m8-v2-input-manifest/1`. For each source
directory it uses only direct-directory enumeration, `lstat`, byte hashing, and
ExifTool. Every `.ARW` spelling is accepted case-insensitively as Rust does,
but ordering is case-sensitive lexical filename order as Windows Rust
`PathBuf::Ord` does. An ARW symlink or non-regular ARW entry is refused.
Every regular file in the admitted source tree is also content-hashed, all
symlinks/special entries are refused, and the complete tree state must be
identical before and after inventory/EXIF collection. Later preflight and
VERIFY reconstruct that state, so an unexpected cached sidecar or other write
cannot hide merely because it is not an ARW.

Each ordered entry contains:

```json
{
  "frame_index": 0,
  "name": "DSC00000.ARW",
  "path": "D:\\...\\DSC00000.ARW",
  "size": 1,
  "mtime_utc": "2026-01-01T00:00:00.000000000Z",
  "mtime_ns": 1767225600000000000,
  "sha256": "64 HEX",
  "exif": {
    "schema": "canonical-exiftool-json-v1",
    "sha256": "64 HEX",
    "dump": {}
  }
}
```

The normalized dump is deterministic sorted JSON from:

```text
exiftool -j -G0:1:2:3:4 -a -s -u -n -sort \
  -charset filename=UTF8 -EXIF:all -MakerNotes:all -- SOURCE
```

`SourceFile` is removed because the absolute path is already frozen separately.
Restricting the selection to EXIF and MakerNotes also excludes ExifTool's
filesystem pseudo-tags (notably access time), so repeated verification does not
turn a read into a changing metadata dump.
The ExifTool binary hash/version and exact argument vector are recorded.

The manifest independently reconstructs Rust FNV-1a over each ordered
`UTF8(name) + NUL + u64le(size) + NUL` record. It requires the released
FNV/count, the released SHA-256 of those identity bytes, sidecar stack name,
stack digest, count, reference, `3516x2344` plane, Catmull-Rom, a complete
placed record set, exact released source/sidecar paths, and the preregistered
sidecar SHA-256.

The separately staged run plan has schema `strehl-m8-v2-run-plan/1`. It binds
the PREPARE receipt hash, input-manifest hash and runtime path, source commit,
private output root, exact environment, output contract, all three render
commands per arm, checker commands, sidecar/crop identities, identity command,
and stopping rule. It also embeds (rather than merely links) the complete Git
tree/blob list, snapshot tree hashes, Cargo/toolchain identities, committed M8
tool hashes, binary hashes, runtime/package/LibRaw/OS/power-plan identities, and
PREPARE command/log identities. Review both staged files, put their exact bytes
at their recorded runtime paths, and commit them. A later arm requires an
explicit full `EvidenceCommit` containing those exact two blobs.

## Phase 3: COMMISSION

Synthetic commissioning accesses no capture:

```powershell
pwsh -NoProfile -File experiments\cover-default\m8-v2\run_v2.ps1 `
  -Phase COMMISSION `
  -OutputRoot D:\strehl-out\m8-v2-private\run-001
```

It runs:

* `checker_v2.py commission`;
* the existing `slide_external_decode.py commission`;
* successful PREPARE injection plus no-change reinjection refusal;
* the compiled producer fixture and block filename/content audit;
* tracing-off filesystem null;
* duplicate completed-state refusal;
* actual two-process one-winner/one-refusal race; and
* the runner's own concurrent and retained-duplicate create-new lock refusals;
  and
* checker-authoritative runner plants for missing, duplicate, concurrent writer,
  and three-way output-transparency failures.

After reviewing and committing the input manifest/run plan, run the real
copied-reference observational control explicitly:

```powershell
pwsh -NoProfile -File experiments\cover-default\m8-v2\run_v2.ps1 `
  -Phase COMMISSION -Identity `
  -OutputRoot D:\strehl-out\m8-v2-private\run-001 `
  -InputManifest C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-input-manifest.json `
  -RunPlan C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-run-plan.json `
  -EvidenceCommit fedcba9876543210fedcba9876543210fedcba98
```

This is the strict command/gate that needs RAW access; implementation and
synthetic testing must not run it. It copies only the frozen released reference
from `D:\strehl-out`, generates an exact one-frame identity sidecar, and renders
Crop `(5,4,3506,2337)` with the uninstrumented binary, instrumented tracing off,
and instrumented tracing on. The runner hashes all three TIFFs and does not open
checker results until all three SHA-256 values are identical. It then requires
four trace blocks, one writer launch, empty claims/staging, the complete
frame/site product, and invokes checker adjudication with the explicit Crop.

Finally, `manifest_v2.py external-identity` imports the committed existing
`slide_external_decode.py` comparator and invokes its two-context rawpy/LibRaw
loader, metadata validation, external prediction, TIFF reader, channel
comparator, and exactness predicate against all three candidates. Truth is not
derived from Strehl.

## Phase 4: FULL

Commissioning receipts, committed input/plan blobs, unchanged tools/binaries,
unchanged snapshots, and a current full input/EXIF/sidecar verification are
hard prerequisites:

```powershell
pwsh -NoProfile -File experiments\cover-default\m8-v2\run_v2.ps1 `
  -Phase FULL `
  -OutputRoot D:\strehl-out\m8-v2-private\run-001 `
  -InputManifest C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-input-manifest.json `
  -RunPlan C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-run-plan.json `
  -EvidenceCommit fedcba9876543210fedcba9876543210fedcba98 `
  -Case flat-1s -ArmMode scale
```

Run the analogous `flat-1s/crop` command. Each arm is new and one-shot. A
retained create-new lock refuses duplicate and concurrent runners.

The sequence is fixed:

1. materialize the checker inventory from the frozen committed manifest;
2. render uninstrumented;
3. render instrumented with tracing absent;
4. create one writer record and render instrumented with tracing enabled;
5. hash all three TIFFs and refuse on any mismatch;
6. only after equality, audit trace block filename/content hashes, empty
   claims/staging, exactly `4*N` blocks, exactly one writer, and the complete
   ordered `(frame,R|G1|G2|B)` Cartesian product;
7. invoke `checker_v2.py adjudicate` with explicit inventory, sidecar SHA-256,
   mode, and (for Crop) frozen rectangle;
8. invoke `checker_v2.py verify`;
9. reverify inputs and both prepared source trees; and
10. atomically publish `receipt.json`.

For every Crop render the runner parses the product's single `CROPPED ...`
coverage banner and requires its reported `(x,y,width,height)` to equal the
frozen rectangle before opening the checker. All three reported rectangles are
retained in the arm receipt and rechecked against the adjudicated result.

Receipt verification is relational, not a collection of free-standing hashes:
it requires the exact planned arm/root/case/mode and evidence commit, binds the
reported Crop rectangle to the immutable run-plan rectangle, binds both source
trees and all three binaries to PREPARE, binds the writer and trace audit to
their fixed arm paths, reruns the independent checker verification, and
requires the retained-file index to equal every file below the arm plus its
single create-only lock. Empty or internally consistent substitute trees,
results, audits, writers, and file lists are refused.
Each real-arm receipt also requires the exact number of executed commands,
unique `logs\*.log` / `*.log.command.json` pairs, the command-record schema and
repo working directory, zero exit codes, and one exact file/argument/environment
match for each of the three planned render roles. Arbitrary hash-valid files
cannot stand in for command or log provenance.

The later `VERIFY` phase writes its own diagnostic command/log pair below the
private root's separate `verification-logs\` directory, never into the sealed
arm tree. Verification therefore observes rather than mutates the exhaustive
arm file set.

Do not pass `-ContinueAfterFlat1s` until both flat-1s receipts have been
independently verified and the operator has read the Crop stopping result.
Later cases require that explicit switch. They are refused unconditionally if
flat-1s Crop has any primary/delivered M8-R or M8-O violation. Flat 6 s is
additionally refused until both flat-2.5 s receipts verify and flat-2.5 s Crop
also remains exact-zero, enforcing the preregistered exposure order.

## Phase 5: VERIFY

```powershell
pwsh -NoProfile -File experiments\cover-default\m8-v2\run_v2.ps1 `
  -Phase VERIFY `
  -OutputRoot D:\strehl-out\m8-v2-private\run-001 `
  -InputManifest C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-input-manifest.json `
  -RunPlan C:\dev\blog\death-of-software\projects\strehl\experiments\cover-default\m8-run-plan.json `
  -EvidenceCommit fedcba9876543210fedcba9876543210fedcba98 `
  -ArmReceipt D:\strehl-out\m8-v2-private\run-001\arms\flat-1s-crop\receipt.json
```

VERIFY is also one-shot because its command/log is retained. It:

* reruns checker result/index/artifact verification;
* verifies every receipt-indexed file byte count and SHA-256;
* reruns the complete trace Cartesian-product/content audit;
* verifies the three transparency hashes and one writer;
* re-hashes source inputs and deterministic EXIF dumps;
* rechecks all sidecar identities;
* rechecks plan/input Git blobs at `EvidenceCommit`;
* rechecks every runner/tool byte against `SourceCommit`;
* rechecks prepared binaries; and
* proves both source snapshots still have their post-build tree hashes.

## Arm receipt

`receipt.json` is `strehl-m8-v2-arm-receipt/1` and is written only after checker
verification. It contains:

* source and evidence commits;
* prepare, run-plan, input-manifest, binary, TIFF, sidecar, inventory, command,
  log, writer, trace-audit, checker-result and evidence-index identities;
* the identical three-way output SHA-256;
* complete block records ordered by frame/site;
* pre/post source-tree identities;
* checker result and content-addressed result-index references; and
* every retained arm file's absolute path, byte count, and SHA-256.

There is no cleanup/retry path. A failed arm retains its lock and partial private
state for diagnosis; the operator must choose a distinct new private output
root rather than deleting or silently reusing evidence.
