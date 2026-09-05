# M135 burned-slide physical commissioning instrument

Status: **SOURCE AND AUTHOR-COMMISSIONING ONLY — DEVELOPMENT, NEVER A SCORE**

This lane implements the frozen
[`PREREGISTRATION.md`](PREREGISTRATION.md) without changing it.  No command was
run against the authorized session while this source was authored.  In
particular, this workstream did not access, enumerate, inspect, hash, decode,
or otherwise touch any path under `D:\`.

## Prior art read before implementation

Rule 40 was run exactly as:

```powershell
python experiments\ORCH-drift-check\prior_art.py burned slide physical commissioning detail instrument
```

It returned these headline reports, all of which constrain this lane:

- `M135-detail-instrument.md`
- `M116-promotion.md`
- `M167-detail-battery.md`
- `M164-m1-staged-capture.md`
- `M46-detail-metric-measured.md`
- `M-PHASE0-SLANTEDGE.md`
- `V-bestframe.md`
- `M161-bar-feasibility.md`
- `M55-acceptance-spec.md`
- `M63-bimodality.md`

It also named `ORCH-veiling.md`, `BUILD-SHARP.md`, `BUILD-TRIAGE.md`,
`V-HEADTOHEAD2.md`, `M87-occlusion.md`, and `V-GATHER.md`.  The result is not
permission to reuse any authorized-slide outcome.  This lane reuses only
generic mechanics and the bars already frozen in `PREREGISTRATION.md`.

## What is implemented

`instrument.py` exposes five independent stages plus a summary:

1. **`inventory` (A)** — exact regular-ARW enumeration, raw-file SHA-256,
   numeric and formatted ExifTool records, timestamp/subsecond ordering, full
   `FocusPosition2` histograms, and the coarse range predicate.
2. **`decode` (B)** — copied-inside-context rawpy/LibRaw active-area decode,
   camera-linear black-subtracted `0.5*(G1+G2)`, and a bit-for-bit full-overlap
   crosscheck against a lane-local executable using the existing safe
   `strehl-raw`/rawler API.  The binary payload travels on stdout, so the
   decoder creates no scratch file or other writable capture-adjacent path.
   Before decoding any frame, Stage B requires the executable's exact byte
   count and SHA-256 to match `freeze-manifest.json`; the hash is checked again
   around every invocation.  The rawler full buffer and trailing active
   columns are recorded but never included in a statistic.
3. **`range` (C)** — a registration image whose Fourier mask is exactly zero
   at and above `0.06 cyc/native px`, a low-pass-only quadrilateral and affine
   registration, the fixed normalized 8x8 lattice, focus input hard-capped at
   `0.20 cyc/native px`, interior quadratic peaks, Huber IRLS
   `u10 = a + b*u4`, the frozen `0.02/0.04/0.03` bars, and the node-density
   ratio on the common fitted interval.
4. **`roles` (D)** — an explicit role ledger.  It rejects sw4-as-truth,
   odd/even as independent capture, the all-axis stack as a repeat, any shared
   source or calibration lineage, any source SHA absent from its declared
   inventory group, point-estimate sampling in place of
   reference-LCB/scored-UCB, a missing/hash-mismatched matched-flat manifest,
   a public checker template, and a source oracle.  Identifiability additionally
   requires `target.same_physical_sites=true` and a hash-bound site manifest
   with at least 64 unique identities and normalized coordinates mapped
   exactly across `R1/R2`, both sw4 outputs and both sw10 outputs.  A scalar
   `site_count` without that evidence is refused.  Missing roles return
   `REFERENCE_ROLE_ABSENT`, `j_tr_computed=false`, and `j_tr=null`.
5. **`flat` (E)** — the three exposure groups separately, fixed
   ordered-index-modulo-4 temporal splits, coefficients no higher than
   `0.25 cyc/native px`, one fixed sensor-coordinate lattice, and a
   phase-scramble repeatability null.  Repeatability is the maximum over the
   six split pairs of mean absolute site-averaged complex cross-power, so
   anti-correlated, rotating-sign and one-pair-only structure cannot cancel.
   The artifact reports that statistic and the same-statistic phase-scramble
   `q99` threshold explicitly.  The four modulo splits are never passed to the
   existing M135 core as pseudo-captures.  That core's lawful `NO_DETAIL`
   branch is commissioned separately on four independent synthetic streams.

`summarize` keeps inventory, coarse range, image range, role
identifiability, optical-arm presence, flat state, and physical binding as
separate fields.  It reruns Stage A through ExifTool, Stage B through both
decoders on every frame, Stage C from those bound inputs, Stage D from the
same-byte hashed ledger/manifest, and Stage E from the reproduced inputs.
Every complete measurement projection must match before a terminal summary is
written.  A quiet flat remains necessary and insufficient.

The green-plane frequency conversion is explicit throughout:

```text
one G1/G2-average plane pixel = two native sensor pixels
f_native = f_green_plane / 2
```

## Deterministic artifacts and exit codes

`artifact-schemas.json` freezes the required keys and terminal states.
Artifacts are UTF-8 JSON, lexicographically sorted, two-space indented, with
no NaN/Infinity and exactly one terminal newline.

- exit `0`: a well-formed terminal result, including a scientific negative,
  `IMAGE_RANGE_UNDETERMINED`, or `REFERENCE_ROLE_ABSENT`;
- exit `1`: a commissioned checker or independent decoder checksum failed;
- exit `2`: malformed input/config/schema, source drift, non-finite data, or
  another hard refusal.

Every artifact records the complete Python command, resolved config hash,
module/binary hashes, numeric-thread environment, unset/set `STREHL_*`
environment, and input artifact hashes.  The freeze derives the local Rust
dependency closure with locked Cargo metadata, binds its root workspace and
lock/toolchain inputs, applies MSVC `/Brepro`, and freezes the exact
byte-reproducible crosscheck executable.  Python dependencies carry compact
distribution-wide semantic hashes plus explicit runtime/native binaries for
NumPy, SciPy, rawpy and OpenCV.  ExifTool and rawler child invocations are
recorded without a truncating pipeline.

## Author commissioning only

The first two plant runs are preserved:

- `commission-run1-failed.json` — the original seven red controls;
- `commission-run2-failed.json` — three remaining ineffective controls.
- `commission-run3-failed.json` — the first semantic-chain fixture omitted its
  newly required missing-role evidence.
- `commission-run4-nondeterministic-before.json` and
  `commission-run4-nondeterministic-after.json` — identical green decisions
  with OpenCV diagnostics differing below `8e-11`.
- `commission-run5-nondeterministic-before.json` and
  `commission-run5-nondeterministic-after.json` — the ten-decimal repair still
  retained a `1e-10` diagnostic alternation.
- `commission-run6-failed.json` — the first SEND BACK repair run had the new
  site-evidence schema field absent from the schema-mutation fixture; 69 of 71
  direct checks were green and selector coverage correctly stayed red.

`AMENDMENT-1.md` and `AMENDMENT-2.md` describe the repairs before replacement
runs.  `AMENDMENT-3.md` records a pre-freeze fail-closed audit,
`AMENDMENT-4.md` records the lane-local Rust crosscheck, and
`AMENDMENT-5.md` and `AMENDMENT-6.md` record two adversarial review repairs.
`AMENDMENT-7.md` adds semantic artifact and scratch-path hardening, and
`AMENDMENT-8.md` records its fixture-only repair.  `AMENDMENT-9.md` supersedes
the pathname guard with a no-file stdout transport, and
`AMENDMENT-10.md` binds coarse/range decisions back to frame metadata and
recorded site curves, and `AMENDMENT-11.md` makes the terminal summary
recompute those curves from the bound inputs.  `AMENDMENT-12.md` does the same
for ExifTool metadata and chronological order, and `AMENDMENT-13.md` freezes
deterministic serialization of OpenCV diagnostics.  `AMENDMENT-14.md` tightens
that diagnostic-only quantization after the ten-decimal attempt remained
non-deterministic.  `AMENDMENT-15.md` closes the final self-consistent decode
artifact path by recomputing all stages at summary time.  `AMENDMENT-16.md`
records the independent SEND BACK and the pre-data repairs to the Cargo/native
freeze, exact crosscheck executable binding, physical-site evidence gate and
sign-robust flat statistic.  The final `commission.json` covers identity, bad
offset, bad slope, bad residual, non-convergence, too few eligible sites,
endpoint peaks, low-pass registration motion, an above-band distractor,
constant/alternating/rotating/one-pair flat structure, missing roles, every
forbidden role alias, every site-manifest bypass, a semantic
`Frame::active_row` mutation, a wrong crosscheck executable, and at least one
negative control for every declared load-bearing selector.  These are the
author's commissioning runs, not independent verification.

## Exact commissioning and freeze commands

From the repository root:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:BLIS_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$env:PYTHONHASHSEED='0'
$env:PYTHONDONTWRITEBYTECODE='1'
Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_COVER -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_RESAMPLER -ErrorAction SilentlyContinue
Remove-Item Env:RAYON_NUM_THREADS -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_HOME -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_TARGET_DIR -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_BUILD_TARGET -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_BUILD_RUSTC -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_BUILD_RUSTFLAGS -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_ENCODED_RUSTFLAGS -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_INCREMENTAL -ErrorAction SilentlyContinue
Remove-Item Env:RUSTC -ErrorAction SilentlyContinue
Remove-Item Env:RUSTC_WRAPPER -ErrorAction SilentlyContinue
Remove-Item Env:RUSTC_WORKSPACE_WRAPPER -ErrorAction SilentlyContinue
Remove-Item Env:RUSTFLAGS -ErrorAction SilentlyContinue
Remove-Item Env:RUSTUP_TOOLCHAIN -ErrorAction SilentlyContinue

$lane = 'experiments\M135-slide-physical-commissioning'
$exiftool = 'C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe'

$out = & cargo build --release --locked --manifest-path $lane\Cargo.toml 2>&1
$code = $LASTEXITCODE
$out
if ($code -ne 0) { throw "crosscheck build failed with exact exit $code" }
$crosscheck = Join-Path $lane 'target\release\m135-slide-raw-crosscheck.exe'

$out = & python -B $lane\freeze.py create `
  --manifest $lane\freeze-manifest.json --exiftool $exiftool `
  --crosscheck-bin $crosscheck 2>&1
$code = $LASTEXITCODE
$out
if ($code -ne 0) { throw "freeze create failed with exact exit $code" }

$out = & python -B $lane\commission.py `
  --config $lane\config.json --output $lane\commission.json `
  --freeze-manifest $lane\freeze-manifest.json `
  --crosscheck-bin $crosscheck 2>&1
$code = $LASTEXITCODE
$out
if ($code -ne 0) { throw "commissioning failed with exact exit $code" }

$out = & python -B $lane\freeze.py create `
  --manifest $lane\freeze-manifest.json --exiftool $exiftool `
  --crosscheck-bin $crosscheck 2>&1
$code = $LASTEXITCODE
$out
if ($code -ne 0) { throw "final freeze create failed with exact exit $code" }

$out = & python -B $lane\freeze.py check `
  --manifest $lane\freeze-manifest.json `
  --crosscheck-bin $crosscheck 2>&1
$code = $LASTEXITCODE
$out
if ($code -ne 0) { throw "freeze check failed with exact exit $code" }
```

## Exact later data commands

**Do not run this block until the orchestrator explicitly releases the host
and authorizes the burned development session.**  The output and Cargo target
remain under this owned lane; the capture tree is input-only.

```powershell
Set-Location 'C:\dev\blog\death-of-software\projects\strehl'
$lane = 'C:\dev\blog\death-of-software\projects\strehl\experiments\M135-slide-physical-commissioning'
$session = 'D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl'
$exiftool = 'C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe'
$run = Join-Path $lane 'out'

$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:BLIS_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$env:PYTHONHASHSEED='0'
$env:PYTHONDONTWRITEBYTECODE='1'
Remove-Item Env:STREHL_ALIGN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_COVER -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_RESAMPLER -ErrorAction SilentlyContinue
Remove-Item Env:RAYON_NUM_THREADS -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_HOME -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_TARGET_DIR -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_BUILD_TARGET -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_BUILD_RUSTC -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_BUILD_RUSTFLAGS -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_ENCODED_RUSTFLAGS -ErrorAction SilentlyContinue
Remove-Item Env:CARGO_INCREMENTAL -ErrorAction SilentlyContinue
Remove-Item Env:RUSTC -ErrorAction SilentlyContinue
Remove-Item Env:RUSTC_WRAPPER -ErrorAction SilentlyContinue
Remove-Item Env:RUSTC_WORKSPACE_WRAPPER -ErrorAction SilentlyContinue
Remove-Item Env:RUSTFLAGS -ErrorAction SilentlyContinue
Remove-Item Env:RUSTUP_TOOLCHAIN -ErrorAction SilentlyContinue

$build = & cargo build --release --locked `
  --manifest-path $lane\Cargo.toml 2>&1
$buildCode = $LASTEXITCODE
$build
if ($buildCode -ne 0) { throw "crosscheck build failed with exact exit $buildCode" }
$crosscheck = Join-Path $lane 'target\release\m135-slide-raw-crosscheck.exe'

$freeze = & python -B $lane\freeze.py check `
  --manifest $lane\freeze-manifest.json `
  --crosscheck-bin $crosscheck 2>&1
$freezeCode = $LASTEXITCODE
$freeze
if ($freezeCode -ne 0) { throw "pre-data freeze check failed with exact exit $freezeCode" }

$a = & python -B $lane\instrument.py --config $lane\config.json inventory `
  --session-root $session --exiftool $exiftool `
  --output $run\stage-a-inventory.json 2>&1
$aCode = $LASTEXITCODE
$a
if ($aCode -ne 0) { throw "stage A failed with exact exit $aCode" }

$b = & python -B $lane\instrument.py --config $lane\config.json decode `
  --inventory $run\stage-a-inventory.json `
  --rawler-crosscheck-bin $crosscheck `
  --freeze-manifest $lane\freeze-manifest.json `
  --output $run\stage-b-decode.json 2>&1
$bCode = $LASTEXITCODE
$b
if ($bCode -ne 0) { throw "stage B failed with exact exit $bCode" }

$c = & python -B $lane\instrument.py --config $lane\config.json range `
  --inventory $run\stage-a-inventory.json --decode $run\stage-b-decode.json `
  --output $run\stage-c-range.json 2>&1
$cCode = $LASTEXITCODE
$c
if ($cCode -ne 0) { throw "stage C failed with exact exit $cCode" }

$d = & python -B $lane\instrument.py --config $lane\config.json roles `
  --inventory $run\stage-a-inventory.json `
  --ledger $lane\role-ledger.template.json `
  --output $run\stage-d-roles.json 2>&1
$dCode = $LASTEXITCODE
$d
if ($dCode -ne 0) { throw "stage D failed with exact exit $dCode" }

$e = & python -B $lane\instrument.py --config $lane\config.json flat `
  --inventory $run\stage-a-inventory.json --decode $run\stage-b-decode.json `
  --roles $run\stage-d-roles.json --ledger $lane\role-ledger.template.json `
  --output $run\stage-e-flat.json 2>&1
$eCode = $LASTEXITCODE
$e
if ($eCode -ne 0) { throw "stage E failed with exact exit $eCode" }

$s = & python -B $lane\instrument.py --config $lane\config.json summarize `
  --inventory $run\stage-a-inventory.json --decode $run\stage-b-decode.json `
  --range $run\stage-c-range.json --roles $run\stage-d-roles.json `
  --flat $run\stage-e-flat.json --output $run\summary.json 2>&1
$sCode = $LASTEXITCODE
$s
if ($sCode -ne 0) { throw "summary failed with exact exit $sCode" }
```

The checked-in ledger intentionally has no `R1/R2` or independent A/B
calibration roles.  On the recorded session it must produce
`REFERENCE_ROLE_ABSENT`; editing it to relabel sw4, odd/even frames, the
all-axis stack, or the public checker as truth is a commissioned failure path,
not a route to a score.  A future identifiable ledger must use each
inventory row's RAW SHA-256 as `source_file_ids` and point to an actual
`m135-matched-flat-evidence-v1` JSON whose byte hash and complete calibration
lineage and per-role capture/source bindings match the ledger.  It must also
point to a hash-bound `m135-physical-site-manifest-v1` with at least 64 unique
normalized slide sites and exact per-site identity/coordinate mappings across
`R1`, `R2`, `sw4_Y1`, `sw4_Y2`, `sw10_Y1`, and `sw10_Y2`; `site_count` alone
is refused.  Each required role consumes one complete, unique leaf capture
unit recorded by Stage A; partitioning one flat directory into pseudo-repeats
is rejected.

## Known unresolved execution risk

No authorized pixel has been read by this implementation.  The automatic
low-pass quadrilateral selector may therefore return
`IMAGE_RANGE_UNDETERMINED` on the real slide, and that is the correct
fail-closed result rather than permission for an outcome-selected crop.  The
session also lacks the independent physical roles needed for a claim-bearing
M135 binding, so even a quiet flat and equivalent range cannot make `J_TR`
identifiable.
