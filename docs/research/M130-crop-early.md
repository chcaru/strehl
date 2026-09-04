# M130: make Crop the Pyramid domain

**Date:** 2026-09-04
**Milestone:** M130
**Result:** **PASS** for the registered Pyramid/Crop prediction and the
pixel-area gate.

## Result

`strehl stack --merge pyramid --cover crop` now evaluates each warp in the
original full-plane coordinate system, then extracts the common covered
rectangle before luma, variance, the measured gate floor, pyramid construction,
local-energy weighting, accumulation, confidence, and collapse. The compact
collapsed plane is written directly. There is no writer-time second crop.

On the registered `109MSDCF` comparison:

| quantity | old late Crop | M130 early Crop |
|---|---:|---:|
| full reference plane | `3516x2344` | `3516x2344` |
| emitted Crop | `(23,16,3470,2312)` | `(23,16,3470,2312)` |
| safe inset per side | **256 plane px** | **8 plane px** |
| retained rectangle | `2958x1800` | `3454x2296` |
| retained/original pixels | `0.6460471292618435` | `0.9622496088092659` |
| retained area | **64.604712926%** | **96.224960881%** |
| registered `>=80%` pixel-area gate | **FAIL** | **PASS** |

The registered prediction was `<=8` plane px and `96.22496%`; the measurement
hit both. This is the COVER phase-0 **pixel-area** predicate. It is not the
different scorecard predicate that requires 80% of preregistered sites to
survive identically.

The default did not move: `DEFAULT_COVER_MODE` remains `Scale`, before/after
no-`--cover` renders are byte-identical, and an aligned Pyramid/default-Scale
row was appended to the byte-freeze registry. Early Crop is opt-in through
`--cover crop` or its pre-existing explicit environment twin
`STREHL_COVER=crop`; with neither set, existing users remain on Scale.

## Rule 40: prior art checked first

Before preregistration or source changes I ran:

```powershell
Set-Location C:\dev\blog\death-of-software\projects\strehl
python experiments\ORCH-drift-check\prior_art.py cover crop border pyramid inset retention
```

It exited 0. It required citation of:

* `docs/research/BUILD-CROP.md`
* `docs/research/M-COVER-BORDER.md`
* `docs/research/M-COVER-NATIVE.md`
* `docs/research/cover-default.md`
* `docs/research/M103-halfdrift.md`
* `docs/research/V-DILUTE.md`
* `docs/research/M112-real-pixels.md`
* `docs/research/BUILD-PYRNOISE.md`
* `docs/research/BUILD-SOFTGATE.md`
* `docs/research/M95-coverage.md`

It also surfaced topic mentions in `ORCH-veiling.md`, `M87-occlusion.md`,
`BUILD-ELECT.md`, `BUILD-SHARP.md`, `BUILD-HULL.md`, and `BUILD-BLEND.md`.
All were checked.

The controlling evidence was:

* `M-COVER-BORDER.md` specified the five-point repair and the registered border
  statistic. In particular, cropping RGB after full-plane weight computation
  is not a fix.
* `M-COVER-NATIVE.md` recorded the existing `2958x1800`,
  `64.604712926%` result and distinguished Crop geometry from Scale.
* `cover-default.md` recorded both the 80% pixel-area gate and Crop's historical
  `0 DN / 24,580,566 samples` identity result, with Scale changing
  `98.1462052%`.
* `experiments/cover-default/PREREGISTRATION.md:121-122` fixes the gate wording
  as at least 80% of the original **pixels**.
* `BUILD-PYRNOISE.md` externally measured the Pyramid backend's noise and gate
  behavior. The later `BUILD-GATE-2.md` documents the shipping per-frame,
  per-warp gate-floor probe as a weighting input. Therefore that probe had to
  use the compact domain too.

Nothing in the remaining reports superseded the repair specified by
`M-COVER-BORDER.md`.

## Preregistration

The real render was not scored until
`experiments/M130-crop-early/PREREGISTRATION.md` had been frozen.

| artifact | SHA-256 |
|---|---|
| `PREREGISTRATION.md` | `71DB51DF0026EA199EF3579DD75272685B21B219012DD9953BE8927AF0126E66` |
| `measure.py` | `C30852CB37C692B2FAA7818A2363499D6AACD8D2DA4EBA8DE4DBB55AA555F2DF` |
| `exactness.py` | `9EF51AE35D5F3A257F8911CF1CA3E0990BDB070EA459C936855D561EF26DC1CF` |

The file was frozen at 2026-09-04 00:47:44 -07:00. Repository HEAD was then
`1e70edb470c2c8883fea22f12b16a5bdf87f894e`; this is a shared worktree, so the
preregistration also records the stronger pre-change file hashes. No real
M130 render or `109MSDCF` border score had been run. Only synthetic instrument
commissioning had run.

Those two script hashes identify the preregistered numerical implementations.
After the result was accepted, the scripts gained deterministic artifact
writers without changing the registered statistics. Their current source
hashes are pinned inside the generated artifacts.

The preregistered statistic was:

```text
E(lo,hi) =
  (mean G_b7(lo,hi) / mean G_b2(lo,hi)) / R_deep - 1

R_deep =
  mean G_b7(distance >= 768) / mean G_b2(distance >= 768)
```

Distance is from the emitted boundary in binned plane pixels. The fixed
threshold is `abs(E) <= 0.001`; fixed edges are
`0,2,4,8,16,32,64,96,128,160,192,256,320,384,448,512,640,768`.
The safe inset is the first edge at least 8 for which that annulus and every
deeper annulus pass. First-safe-at-768 is censored.

## Machine-readable evidence

The prose below is not the sole record of the result:

| artifact | ordinary file SHA-256 | internal canonical self SHA-256 |
|---|---|---|
| `experiments/M130-crop-early/results.json` | `27885F4ED35A1227CAD2463E29EFB591CD6C775299C647AD029BF6F28C8863EF` | `1CE89A1FAD14528FB7526E09D8D94D1C17E6F8D08DC9B9B04ED4E413F689C14B` |
| `experiments/M130-crop-early/freeze.json` | `08D71104381A625C1C6D6E094FD776B5D9D6E27B68BBF894C9EC1B11FD808820` | `4CFC7615B4C0008A44F5B832A443A79080D9AFF957C67656F5E9B5B4C7CC6EDA` |

Each `integrity.self_sha256` is calculated over canonical sorted-key UTF-8 JSON
after removing only that field. `artifact_io.py` writes atomically and the
`verify-results` / `verify-freeze` commands recalculate the seal.

`results.json` contains the complete old and new annular profiles, exact
retention numerators and denominators, 40-digit decimal ratios, full and Crop
geometry, the exactness/control comparisons, a freshly exercised Estimator
refusal, a freshly compiled 121-test result, hashes of all analyzed TIFFs and
sidecars, and a content-hash manifest of all 22 `109MSDCF` source frames.

`freeze.json` contains all four rows parsed from a successful live byte-freeze
harness run, each marked as exercised twice, plus the default before/after
comparison. It embeds the content-hash manifests for the first 20
`coffee-bean` frames and all 22 `109MSDCF` frames and hashes the registry,
harness, sidecar, and generating scripts.

The artifact writers regenerate all analyses and controls. They do **not**
rerender the expensive TIFF inputs: `results.json` and `freeze.json` label
those producers as `"manual command, not regenerated"` and bind the preserved
files by SHA-256. The exact producer commands and executable hashes remain in
this report. In contrast, the Estimator refusal, CLI tests, source-frame
manifests, and complete byte-freeze harness are run afresh while generating
the artifacts.

## Implementation

### One typed domain, two coordinate systems

`crates/strehl-cli/src/merge_cmd.rs:4523` adds `PyramidDomain`:

* `full` is the original reference geometry used for transforms, optical
  correction, CFA/full-resolution gather, and `WarpScratch`;
* `rect` carries the Crop origin and compact analysis geometry.

`pyramid_domain` at `merge_cmd.rs:4580` resolves this only after coverage is
known. `Scale`, `Skip`, and ordinary non-Crop paths receive the historical
whole-plane domain. Crop without alignment or without a covered rectangle
refuses instead of silently reverting to a full-plane merge.

`extract_planes` at `merge_cmd.rs:4616` is the single origin-aware extraction
path. Local `(x,y)` reads the already-warped destination at
`(rect.x+x, rect.y+y)`. The transform itself still runs against `domain.full`
at `merge_cmd.rs:4927`.

### Every Pyramid consumer is compact

`BandWorker` at `merge_cmd.rs:4760` allocates its CFA planes, luma, variance,
`BandMerge`, and `FrameWorkspace` from `domain.analysis()`. `run_pyramid` at
`merge_cmd.rs:5515` resolves coverage before pyramid-sized allocation.
Confidence passes at `merge_cmd.rs:5046` and `:5195` receive the same domain.

The default measured gate-floor path is also compact:

* `merge_cmd/gatefloor.rs:174` builds level sizes from `domain.analysis()`;
* `gatefloor.rs:273` still evaluates the probe warp on `domain.full`;
* `gatefloor.rs:283` sends only the shared extracted rectangle into its luma
  and pyramid.

This closes the hidden poisoning route in which an otherwise compact frame
could still be weighted by a full-plane gate-floor pyramid.

Worker budgeting deliberately remains based on the full geometry. Crop must
not increase the automatic worker count and thereby alter the floating-point
reduction order.

### Collapse and output

`Merged::Bands` carries `PyramidDomain`. `write_merged` at
`merge_cmd.rs:7124` addresses compact indices directly and reports the retained
full-plane origin. It has no Crop argument and cannot apply the rectangle a
second time. No TIFF origin tag was added because that would change the
byte-frozen output format; the origin remains in the typed domain and stderr
provenance.

### Both backends are deliberate

The Pyramid backend implements early Crop. The Estimator backend still has
independent full-plane guide, statistics, election, and accumulation passes.
Rather than leave a silently different late-Crop operation under the same
flag, shared dispatch refuses `Estimator + Crop` before input traversal
(`merge_cmd.rs:2918-2954`). `Estimator + Scale` remains supported.

### Tests and freeze harness

Six focused tests cover nonzero-origin extraction, outside-domain poison
invariance, inside-domain specificity, whole-plane historical addressing,
invalid rectangles, direct compact writer indexing, missing Crop geometry, and
backend/default behavior. The CLI unit target has 121 tests.

An aligned Pyramid/default-Scale row was appended—not substituted—to
`crates/strehl-cli/tests/byte-freezes.tsv`:

```text
coffee-bean-20-gate2-pyramid-sidecar
FB76DE79359F46E4E7E7601520FCE45F08A79381F9019F0AEE763B2DDD88B084
49,450,019 bytes
```

It explicitly records Pyramid and gate `2.0`, uses the committed sidecar, and
deliberately has no `--cover`; the harness clears `STREHL_COVER`, so the row
freezes the compiled default Scale coverage path. The existing Pyramid row had
alignment off and could not exercise coverage resolution.

Adding the first aligned Pyramid row exposed a pre-existing parser defect:
Pyramid reports `0 refused, 0.0 s`, while the harness accepted only a terminal
token spelled exactly `refused`. `byte-freeze.rs` now ignores trailing ASCII
punctuation on the field-name token and has a test copied from the actual
Pyramid line. It still parses the preceding count strictly as `usize`.

## Measurements

### Inputs and environment

The full stack is `D:\personal\macro\109MSDCF`, 22 ARWs
`DSC00009.ARW..DSC00030.ARW`. The sidecar is an M130-owned copy of
`experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt`:

```text
SHA-256       C29CAB9C6F944F4D03C4402998E54AAD4D4221CC450AC4BEF42A453DE848434D
stack digest  b70554b8cfd9b93e
reference     11
plane         3516x2344
resampler     Catmull-Rom
```

Every comparable render first removed all inherited `STREHL_*` variables,
then set:

```text
STREHL_WARPMAP=<absolute M130 scratch sidecar>
STREHL_FULLRES_GATHER=1
STREHL_DEFECT=off
STREHL_FIX_CA=off
STREHL_PYRAMID_WORKERS=2
RAYON_NUM_THREADS=6
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
```

Tool versions were Cargo/rustc 1.98.0, Python 3.12.10, NumPy 2.4.4,
tifffile 2026.5.2, and rawpy 0.27.0 / LibRaw 0.22.1.

### Registered border result

The late-Crop control and early-Crop candidate were rendered with matched
before/after binaries and the environment above:

| render | SHA-256 |
|---|---|
| old b2 | `10F7DEAF5A82CA2A311C76A323AE5627207520E7DA3BB71D237BB861CC7CC977` |
| old b7 | `0465D253F14431CE76BA1DD68E54C1BD2CBAE56DA17F079D5DD572852FCAD304` |
| M130 b2 | `6538C53BDD0AFE36E3EBEA949E3352024CEC794F89C5644C3161B93CF64F6CDD` |
| M130 b7 | `8A67F2DBEE62EA2241BBFDA74516BFF9504CFD0AA81EE769B09C49F5C0267E9A` |

Every file is 48,136,827 bytes and decodes as `2312x3470x3 uint16`.

Independent recomputation, without importing `measure.py`, found:

```text
late Crop : Rdeep=0.999919203098472
            [192,256) E=+0.002807814855 (fails)
            [256,320) E=+0.000342497416
            safe=256

early Crop: Rdeep=0.999917153707409
            [8,16) E=-0.000463783135
            [16,32) E=-0.000639651632
            all deeper fixed annuli pass
            safe=8
```

The retained-area arithmetic is:

```text
old:
  (3470 - 2*256) * (2312 - 2*256) / (3516*2344)
  = (2958*1800) / 8241504
  = 0.6460471292618435

M130:
  (3470 - 2*8) * (2312 - 2*8) / (3516*2344)
  = (3454*2296) / 8241504
  = 0.9622496088092659
```

Thus the measured retained area is **96.224960881%**, and the registered
`>=80%` pixel-area gate **passes**.

### The instrument can go RED

Before the real score, `measure.py commission` applied a 2% boundary poison to
the registered geometry. With poison extending 256 px it returned safe inset
256, retention `0.6460471292618435`, and gate **FAIL**. With reach 8 it returned
safe inset 8, retention `0.9622496088092659`, and gate **PASS**. An instrument
that always emits the registered answer cannot pass this commission.

`exactness.py commission` separately proved an exact null, made one XOR
mutation differ by exactly 32768 DN, and made a one-pixel origin plant change
all 3,600 fixture samples.

### Default/Scale byte freeze

Preserved executables:

| build | executable SHA-256 | bytes |
|---|---|---:|
| before M130 | `EC4885C98EEBAEB5A99F5A8CDC0FF9753C7F22B64B06F01B51689A546DB6B489` | 9,861,632 |
| M130 | `25DD6D394B98FBDD9F7073060A0F19F2AA2C471EA856FE935B1DC3BEDA48E343` | 9,863,168 |

The same full-stack invocation, with no `--cover`, produced:

```text
before-default.tiff
after-default.tiff
SHA-256  84901F122C256961199EB153674309C328AE7ABF9C33D371A4BBBEE26CD4F594
bytes    49,450,019
shape    2344x3516x3 uint16
array    exactly equal; zero differing samples
```

The new registry row was also based on clean committed source
`6629348e1e319ce7dedac5b4c8ebd62077461cad`, not on an irreproducible dirty
tree. Two clean-source renders and one M130-source render all produced
`FB76DE...B084`. An independent verifier then ran the real harness. All four
rows rendered twice; the new row reported:

```text
freeze `coffee-bean-20-gate2-pyramid-sidecar` HOLDS:
FB76DE79359F46E4E7E7601520FCE45F08A79381F9019F0AEE763B2DDD88B084
(49450019 bytes, alignment on-sidecar-override,
 4 workers x 1328 MB, 20 placed / 0 refused) -- reproduced twice
```

### Crop remains an integer-sample view

One-frame input:

```text
RAW       D:\strehl-out\cover-default\one-109-ref\DSC00020.ARW
RAW SHA   77AAEC0B9958B97E8B712332E2A3C67013373623B8BCF52CC5C88B912F0070CA
sidecar   4C858562AF44E0646D9E45E445DEBAC17C6C9E4FEC28C325B9E653EB391E6C05
Crop      (5,4,3506,2337)
```

Output hashes:

| arm | SHA-256 |
|---|---|
| direct, alignment off | `447F1A6EF5212CECCE4890C0823C50E3D66DC65ED23733BC957F0217C31BFCF4` |
| Crop | `9033579443C98A769770F71A239104E3529F53FB152308080A7EE4AC1C72C972` |
| Scale | `23A385AC2E5C0C70B1F436C3D9E5F3C13E905FB8DE9A177AA1D988DAFDBE2FC2` |

An independent rawpy/LibRaw decode and independent RGB16 encoder found:

| comparison | differing samples | fraction | max | RMS |
|---|---:|---:|---:|---:|
| external LibRaw to direct overlap | `0 / 24,710,448` | 0 | 0 DN | 0 DN |
| external LibRaw at `(5,4)` to Crop | `0 / 24,580,566` | 0 | **0 DN** | **0 DN** |
| direct window at `(5,4)` to Crop | `0 / 24,580,566` | 0 | 0 DN | 0 DN |
| external at wrong origin `(6,4)` to Crop | `23,892,271 / 24,580,566` | `97.1998407197%` | 6235 DN | 195.43755 DN |
| external to Scale overlap | `24,252,367 / 24,710,448` | `98.1462052003%` | 8656 DN | 215.44080 DN |

Crop therefore retains the registered **0-DN exactness across 24,580,566
samples**. The wrong-origin plant proves that the result is not an accidental
comparison against the wrong window, and Scale is the expected resampling
positive control.

### Backend and diagnostic controls

* `Estimator + Crop` exited exactly 1 before even a deliberately missing input
  path was traversed, and created no output.
* `Pyramid + Crop` succeeded.
* `Estimator + Scale` succeeded and reproduced the one-frame Scale hash.
* `Pyramid + Crop` with alignment disabled exited exactly 1 and created no
  output instead of falling back to a full-plane merge.
* Enabling both the confidence map and `STREHL_CONFIDENCE_DEBUG` left the
  primary one-frame Crop TIFF byte-identical at
  `903357...C972`. The confidence map and all five debug maps
  (`centrality`, `dmin`, `dsharp`, `spread`, `withinfrac`) are compact
  `2337x3506 uint16` planes.

No image was visually judged in this lane; the evidence is numerical and
byte-exact.

## Reproduction

Run from PowerShell. Do not use `-q`. Capture command output before inspecting
`$LASTEXITCODE`; do not pipe a live command through `Select-Object`.

### Prepare the owned sidecars and environment

```powershell
Set-Location C:\dev\blog\death-of-software\projects\strehl
$out = 'C:\dev\strehl-out\M130-crop-early'
$stack = 'D:\personal\macro\109MSDCF'
$one = 'D:\strehl-out\cover-default\one-109-ref'
$before = "$out\target-before\release\strehl.exe"
$after = "$out\target-after\release\strehl.exe"

New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt `
  "$out\109-warpmap.txt"
Copy-Item D:\strehl-out\cover-default\one-109-ref.warpmap.txt `
  "$out\one-109-ref.warpmap.txt"

Get-ChildItem Env:STREHL_* -ErrorAction SilentlyContinue | Remove-Item
$env:STREHL_WARPMAP = "$out\109-warpmap.txt"
$env:STREHL_FULLRES_GATHER = '1'
$env:STREHL_DEFECT = 'off'
$env:STREHL_FIX_CA = 'off'
$env:STREHL_PYRAMID_WORKERS = '2'
$env:RAYON_NUM_THREADS = '6'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'

Get-FileHash -Algorithm SHA256 "$out\109-warpmap.txt"
Get-FileHash -Algorithm SHA256 $before
Get-FileHash -Algorithm SHA256 $after
```

### Commission the instruments

```powershell
$log = & python -B experiments\M130-crop-early\measure.py commission 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "measure commission exited $code" }

$log = & python -B experiments\M130-crop-early\exactness.py commission 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "exactness commission exited $code" }
```

### Default before/after freeze

```powershell
$env:STREHL_WARPMAP = "$out\109-warpmap.txt"

$log = & $before stack $stack --out "$out\before-default.tiff" 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "before default exited $code" }

$log = & $after stack $stack --out "$out\after-default.tiff" 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "after default exited $code" }

Get-FileHash -Algorithm SHA256 "$out\before-default.tiff"
Get-FileHash -Algorithm SHA256 "$out\after-default.tiff"
python -c "import numpy as np,tifffile as t; a=t.imread(r'$out\before-default.tiff'); b=t.imread(r'$out\after-default.tiff'); print(a.shape,a.dtype,np.count_nonzero(a!=b)); assert np.array_equal(a,b)"
```

### Late-Crop control and M130 profile

```powershell
$env:STREHL_WARPMAP = "$out\109-warpmap.txt"

foreach ($case in @(
  @($before,2,'before-crop-b2.tiff'),
  @($before,7,'before-crop-b7.tiff'),
  @($after,2,'crop-b2.tiff'),
  @($after,7,'crop-b7.tiff')
)) {
  $exe,$bands,$name = $case
  $log = & $exe stack $stack --merge pyramid --cover crop `
    --pyramid-bands $bands --out "$out\$name" 2>&1
  $code = $LASTEXITCODE
  $log
  if ($code -ne 0) { throw "$name exited $code" }
}

$log = & python -B experiments\M130-crop-early\measure.py profile `
  --b2 "$out\before-crop-b2.tiff" --b7 "$out\before-crop-b7.tiff" `
  --expected-b2-sha 10F7DEAF5A82CA2A311C76A323AE5627207520E7DA3BB71D237BB861CC7CC977 `
  --expected-b7-sha 0465D253F14431CE76BA1DD68E54C1BD2CBAE56DA17F079D5DD572852FCAD304 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 1) { throw "late-Crop control should exit 1, got $code" }

$log = & python -B experiments\M130-crop-early\measure.py profile `
  --b2 "$out\crop-b2.tiff" --b7 "$out\crop-b7.tiff" `
  --expected-b2-sha 6538C53BDD0AFE36E3EBEA949E3352024CEC794F89C5644C3161B93CF64F6CDD `
  --expected-b7-sha 8A67F2DBEE62EA2241BBFDA74516BFF9504CFD0AA81EE769B09C49F5C0267E9A 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "M130 profile exited $code" }
```

### One-frame Crop exactness

```powershell
$env:STREHL_WARPMAP = "$out\one-109-ref.warpmap.txt"

$log = & $after stack $one --merge pyramid --pyramid-bands 7 --cover crop `
  --out "$out\one-crop.tiff" 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "Crop exited $code" }

$log = & $after stack $one --merge pyramid --pyramid-bands 7 --cover scale `
  --out "$out\one-scale.tiff" 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "Scale exited $code" }

$env:STREHL_ALIGN = '0'
$log = & $after stack $one --merge pyramid --pyramid-bands 7 `
  --out "$out\one-direct.tiff" 2>&1
$code = $LASTEXITCODE
$log
Remove-Item Env:STREHL_ALIGN
if ($code -ne 0) { throw "direct arm exited $code" }

$log = & python -B experiments\M130-crop-early\exactness.py measure `
  --raw "$one\DSC00020.ARW" `
  --direct "$out\one-direct.tiff" `
  --crop "$out\one-crop.tiff" `
  --scale "$out\one-scale.tiff" --origin 5 4 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "exactness measure exited $code" }
```

### Refusal and compact confidence outputs

```powershell
$refused = "$out\must-not-exist.tiff"
Remove-Item $refused -ErrorAction SilentlyContinue
$log = & $after stack $one --merge estimator --cover crop --out $refused 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 1) { throw "Estimator Crop should exit 1, got $code" }
if (Test-Path $refused) { throw "Estimator Crop created output" }

$env:STREHL_WARPMAP = "$out\one-109-ref.warpmap.txt"
$env:STREHL_CONFIDENCE_DEBUG = "$out\confidence-debug"
$log = & $after stack $one --merge pyramid --pyramid-bands 7 --cover crop `
  --confidence-map "$out\one-confidence.tiff" `
  --out "$out\one-crop-diagnostic.tiff" 2>&1
$code = $LASTEXITCODE
$log
Remove-Item Env:STREHL_CONFIDENCE_DEBUG
if ($code -ne 0) { throw "confidence run exited $code" }
Get-FileHash -Algorithm SHA256 "$out\one-crop-diagnostic.tiff"
```

### Source tests and append-only byte freeze

```powershell
Get-ChildItem Env:STREHL_* -ErrorAction SilentlyContinue | Remove-Item
$env:CARGO_TARGET_DIR = "$out\target-test"
cargo test -p strehl-cli --bin strehl
if ($LASTEXITCODE -ne 0) { throw "CLI tests failed" }

cargo test -p strehl-cli --test byte-freeze `
  the_alignment_parser_names_every_mode_the_tool_can_report -- --nocapture
if ($LASTEXITCODE -ne 0) { throw "placement parser test failed" }

cargo test -p strehl-cli --test byte-freeze `
  every_registry_row_records_a_complete_invocation -- --nocapture
if ($LASTEXITCODE -ne 0) { throw "registry validation failed" }

$env:STREHL_FREEZE_REQUIRE = '1'
cargo test -p strehl-cli --test byte-freeze `
  the_frozen_renders_still_produce_their_recorded_bytes -- --nocapture
if ($LASTEXITCODE -ne 0) { throw "byte freeze failed" }
```

The independently run full target completed in 493.16 s and printed `HOLDS`
for all four rows, each reproduced twice.

### Regenerate the machine-readable artifacts

The artifact writers consume the preserved, hash-checked render products. They
do not claim to have produced those TIFFs. `record-results` does freshly run
the Estimator refusal and CLI unit tests; `record-freeze` freshly runs the
complete two-pass byte-freeze harness.

```powershell
$exactnessComponent = "$out\exactness-component.json"
$resultsTarget = "$out\target-artifact-results"
$freezeTarget = "$out\target-artifact-freeze"

$log = & python -B experiments\M130-crop-early\exactness.py measure `
  --raw "$one\DSC00020.ARW" `
  --direct "$out\one-direct.tiff" `
  --crop "$out\one-crop.tiff" `
  --scale "$out\one-scale.tiff" --origin 5 4 `
  --output $exactnessComponent 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "exactness artifact exited $code" }

Remove-Item -LiteralPath $resultsTarget -Recurse -Force `
  -ErrorAction SilentlyContinue
$log = & python -B experiments\M130-crop-early\measure.py record-results `
  --repo . `
  --full-stack $stack `
  --full-stack-identifier '109MSDCF:DSC00009.ARW..DSC00030.ARW' `
  --full-stack-limit 22 `
  --sidecar "$out\109-warpmap.txt" `
  --one-sidecar "$out\one-109-ref.warpmap.txt" `
  --one-frame-identifier '109MSDCF:DSC00020.ARW' `
  --candidate $after `
  --estimator-stack $one `
  --cargo-target $resultsTarget `
  --default-before "$out\before-default.tiff" `
  --old-b2 "$out\before-crop-b2.tiff" `
  --old-b7 "$out\before-crop-b7.tiff" `
  --new-b2 "$out\crop-b2.tiff" `
  --new-b7 "$out\crop-b7.tiff" `
  --expected-old-b2-sha 10F7DEAF5A82CA2A311C76A323AE5627207520E7DA3BB71D237BB861CC7CC977 `
  --expected-old-b7-sha 0465D253F14431CE76BA1DD68E54C1BD2CBAE56DA17F079D5DD572852FCAD304 `
  --expected-new-b2-sha 6538C53BDD0AFE36E3EBEA949E3352024CEC794F89C5644C3161B93CF64F6CDD `
  --expected-new-b7-sha 8A67F2DBEE62EA2241BBFDA74516BFF9504CFD0AA81EE769B09C49F5C0267E9A `
  --exactness-json $exactnessComponent `
  --output experiments\M130-crop-early\results.json 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "results artifact exited $code" }

Remove-Item -LiteralPath $freezeTarget -Recurse -Force `
  -ErrorAction SilentlyContinue
$log = & python -B experiments\M130-crop-early\exactness.py record-freeze `
  --repo . `
  --captures 'D:\personal\macro' `
  --default-stack $stack `
  --default-capture-identifier '109MSDCF:DSC00009.ARW..DSC00030.ARW' `
  --default-limit 22 `
  --default-before "$out\before-default.tiff" `
  --default-after "$out\after-default.tiff" `
  --cargo-target $freezeTarget `
  --output experiments\M130-crop-early\freeze.json 2>&1
$code = $LASTEXITCODE
$log
if ($code -ne 0) { throw "freeze artifact exited $code" }

python -B experiments\M130-crop-early\measure.py verify-results `
  --input experiments\M130-crop-early\results.json
if ($LASTEXITCODE -ne 0) { throw "results verification failed" }

python -B experiments\M130-crop-early\exactness.py verify-freeze `
  --input experiments\M130-crop-early\freeze.json
if ($LASTEXITCODE -ne 0) { throw "freeze verification failed" }

Get-FileHash -Algorithm SHA256 `
  experiments\M130-crop-early\results.json, `
  experiments\M130-crop-early\freeze.json
```

## Independent verification

The author did not adjudicate the result. Two independent verifier passes:

1. rebuilt the candidate in a verifier-owned target;
2. ran all 121 CLI unit tests;
3. rendered a fresh one-frame Crop from current source and reproduced
   `903357...C972`;
4. reran the before/after default and full-stack b2/b7 renders;
5. reimplemented the border statistic without importing `measure.py`;
6. independently decoded LibRaw and reimplemented the RGB16 arithmetic;
7. exercised Estimator Crop and Pyramid/no-alignment refusal;
8. checked compact confidence outputs;
9. rebuilt committed baseline `6629348e`, reproduced the new freeze hash twice,
   then ran the complete four-row registry harness after the parser fix.

The final independent results were:

```text
cargo test -p strehl-cli --bin strehl
  121 passed; 0 failed

placement parser target
  1 passed; 0 failed

registry completeness target
  1 passed; 0 failed

full byte-freeze target
  1 passed; 0 failed
  all four rows HOLDS, each reproduced twice

registered profile
  old: safe 256, retention 0.6460471292618435, FAIL
  M130: safe 8, retention 0.9622496088092659, PASS

external Crop exactness
  0 / 24,580,566 differing; max 0 DN; RMS 0 DN
```

The verifier found no high-confidence implementation defect.

Strict Clippy is **not** claimed. This command:

```powershell
cargo clippy -p strehl-cli --bin strehl -- -D warnings
```

exited 101 first on the pre-existing
`crates/strehl-cli/build.rs:101` `collapsible_if` in both a clean detached
pre-M130 `6629348e` worktree and the M130 candidate. Continuing with that lint
allowed exposed existing `strehl-core`, `image_out.rs`, and `main.rs` warnings;
because the first build-script error stops strict Clippy, this does not claim
that no later candidate-only lint is hidden behind it. No unrelated lint
cleanup was made.

Workspace `cargo fmt --all -- --check` was also red across 45 files before M130
and remains red across the same count. The clean pre-M130 worktree produced 511
formatter diff blocks; after
formatting only M130-touched expressions, the candidate produced 506. Comparing
normalized diff bodies left one candidate-only block, but its only requested
change is the same pre-existing `level_sizes` import ordering present in the
baseline; the newly added `use super::{...}` line is context and is not changed
by rustfmt. Thus M130 adds no rustfmt-targeted line. `git diff --check` on the
M130 Rust implementation passed.

## What this does not establish

M130 does **not**:

* change the default from Scale to Crop;
* clear the separate scorecard gate requiring 80% of preregistered sites to
  survive identically;
* establish that 8 px is universal across scenes, lenses, transforms, band
  counts, or resamplers;
* establish visual superiority or perform a visual assessment;
* implement Crop for the Estimator backend. Consequently an integer-sample
  Crop cannot currently be combined with the Estimator-only photometric
  normalisation, clip census, outlier rejection, halo correction,
  through-focus statistics, or `n_eff` diagnostics; callers must choose
  Pyramid Crop or Estimator Scale;
* add a TIFF Crop-origin metadata tag;
* make explicit Crop representable in the current byte-freeze TSV schema—the
  appended row freezes the required no-flag default Scale path, while Crop is
  covered by the independent border and LibRaw instruments;
* certify non-Windows execution.

## Conclusion

The defect was the domain, not the output rectangle. Restricting only the
writer—or only the RGB bands after full-plane weights were computed—would have
left the contamination path intact. M130 instead makes the common Crop
rectangle the complete Pyramid analysis domain while preserving original
coordinates for warp evaluation.

Measured on `109MSDCF`, the safe inset is **8 plane px per side** and retained
area is **96.224960881%**. The registered `>=80%` pixel-area gate **passes**.
The default Scale render is byte-identical, and Crop remains exactly
`0 DN` from the external LibRaw reference over all **24,580,566** emitted
samples.
