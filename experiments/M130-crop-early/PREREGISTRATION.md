# M130 crop-early preregistration

**Frozen before any M130 real render or 109 border score:** 2026-09-04
00:47:44 -07:00.  The only measurements already run were the synthetic
commissions below.  Repository HEAD at freeze was
`1e70edb470c2c8883fea22f12b16a5bdf87f894e`; because this is a shared worktree,
the stronger source identities are the file hashes below.

This file is immutable after its SHA-256 is recorded in
`docs/research/M130-crop-early.md`.  Any necessary change is an explicitly
dated amendment, never an edit to this registration.

## 1. Prior-art search

Rule 40 was run before this registration:

```powershell
Set-Location C:\dev\blog\death-of-software\projects\strehl
python experiments\ORCH-drift-check\prior_art.py cover crop border pyramid inset retention
```

It exited 0.  It required citation of `BUILD-CROP.md`,
`M-COVER-BORDER.md`, `M-COVER-NATIVE.md`, `cover-default.md`,
`M103-halfdrift.md`, `V-DILUTE.md`, `M112-real-pixels.md`,
`BUILD-PYRNOISE.md`, `BUILD-SOFTGATE.md`, and `M95-coverage.md`.  It also
reported topic mentions in `ORCH-veiling.md`, `M87-occlusion.md`,
`BUILD-ELECT.md`, `BUILD-SHARP.md`, `BUILD-HULL.md`, and `BUILD-BLEND.md`.
The first four and `experiments/cover-default/PREREGISTRATION.md` define this
lane's diagnosis, geometry, identity property, and gate.  The remaining
reports were checked for interactions with coverage, pyramid depth,
confidence, selection, and output geometry.  None supersedes
`M-COVER-BORDER.md`'s proposed fix.

## 2. Registered implementation

The Pyramid backend will carry one typed domain containing:

* the original full plane used for decode, defect correction, warp evaluation,
  optical correction, CFA phase, and `WarpScratch`; and
* the common covered `CropRect`, whose geometry is used for every extracted
  CFA plane, luma, variance, gate-floor pyramid, local-energy field,
  `BandMerge`, accumulator, collapse workspace, confidence pass, and output.

The full-coordinate warp will run first.  Extraction will then address local
`(x,y)` at full destination `(rect.x+x, rect.y+y)`.  No destination sample
outside the rectangle may enter a pyramid.  The collapsed compact planes will
be written by local index; the writer must not address the same Crop window a
second time.  Crop origin remains carried in the domain and is printed with
the output provenance.

`Scale`, `Skip`, and no-alignment runs keep a whole-plane domain.  The
compiled default remains `CoverMode::Scale`.  Estimator Crop will be refused
before decoding, because its independent guide/statistics/election passes
have no equivalent compact-domain implementation; Estimator Scale remains
supported.  A silent late-cropped estimator render is forbidden.

The default measured gate-floor probe is part of weighting.  Therefore its
warp remains full-plane but its extracted noise luma and pyramid must use the
same compact domain.  Leaving it full-plane is not an admissible partial fix.

## 3. Registered predictions and gates

The target is the 22-frame `109MSDCF` stack with full reference plane
`3516x2344` and emitted Crop rectangle `(23,16,3470,2312)`.

The fixed green-plane statistic is:

```text
E(lo,hi) =
  (mean G_b7(lo,hi) / mean G_b2(lo,hi)) / R_deep - 1

R_deep =
  mean G_b7(distance >= 768) / mean G_b2(distance >= 768)
```

Distance is in emitted binned plane pixels.  Threshold is
`abs(E) <= 0.001`.  Fixed edges are
`0,2,4,8,16,32,64,96,128,160,192,256,320,384,448,512,640,768`.
The safe inset is the first edge at least 8 for which that and every deeper
annulus pass.  A value first safe at 768 is censored, not admitted.

Registered prediction: safe inset falls from 256 to **at most 8 plane px per
side**.  Registered pixel-area result:

```text
old = (3470 - 2*256) * (2312 - 2*256) / (3516*2344)
    = 5324400 / 8241504
    = 0.6460471292618435

predicted = (3470 - 2*8) * (2312 - 2*8) / (3516*2344)
          = 7930384 / 8241504
          = 0.9622496088092659
          = 96.22496% at the registered reporting precision
```

The unchanged gate is retained pixel area **at least 80% of the original
plane**.  This is not the scorecard's different predicate requiring 80% of
pre-registered sites to survive identically.

A miss is reported as measured.  No parameter may be tuned after seeing the
profile.

## 4. Registered controls

### 4.1 Instrument commission and RED control

Before this freeze, these commands exited 0:

```powershell
python -B experiments\M130-crop-early\measure.py commission
python -B experiments\M130-crop-early\exactness.py commission
```

`measure.py` SHA-256 is
`C30852CB37C692B2FAA7818A2363499D6AACD8D2DA4EBA8DE4DBB55AA555F2DF`.
Its planted 2% boundary poison extending 256 px returned safe inset 256 and
retention `0.6460471292618435`, making the 80% gate RED.  Reducing the poison
reach to 8 returned safe inset 8 and retention
`0.9622496088092659`, GREEN.  Thus an instrument that always reports the
registered answer cannot pass.

`exactness.py` SHA-256 is
`9EF51AE35D5F3A257F8911CF1CA3E0990BDB070EA459C936855D561EF26DC1CF`.
Its exact null returned 0 differences; an XOR `0x8000` changed exactly one
sample by 32768 DN; and a one-pixel origin plant changed all 3,600 fixture
samples.

### 4.2 Default/Scale freeze

Failure input: any M130 change that reaches the default Scale arm.  The same
no-`--cover` invocation run through separately preserved before/after
executables must then produce a different SHA-256, byte count, or dimensions.
The gate requires exact equality; a rebaseline is not permitted.

### 4.3 Crop identity

Failure input: rebasing the transform or extracting Crop at `(x+1,y)`.
Against one copied identity reference, external LibRaw encoding must disagree
strongly for the one-pixel plant and agree at every sample for the true
origin.  Crop must be `0 DN` max, `0 DN` RMS, and zero differing samples over
the complete emitted extent.  Scale is the positive resampling control and
must change more than 1% of the external overlap.

### 4.4 Backend specificity

Estimator + Crop must exit exactly 1 before decoding, while Pyramid + Crop and
Estimator + Scale must pass preflight.  `DEFAULT_COVER_MODE` must remain
`Scale`.

## 5. Frozen inputs and tools

* Full stack: `D:\personal\macro\109MSDCF`, sorted `DSC00009.ARW` through
  `DSC00030.ARW`, 22 ARWs.
* Full-stack sidecar source:
  `experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt`,
  SHA-256
  `C29CAB9C6F944F4D03C4402998E54AAD4D4221CC450AC4BEF42A453DE848434D`,
  recorded stack digest `b70554b8cfd9b93e`, reference 11, plane
  `3516x2344`, Catmull-Rom.
* One-frame RAW:
  `D:\strehl-out\cover-default\one-109-ref\DSC00020.ARW`, 38,178,816 bytes,
  SHA-256
  `77AAEC0B9958B97E8B712332E2A3C67013373623B8BCF52CC5C88B912F0070CA`.
* One-frame identity sidecar source:
  `D:\strehl-out\cover-default\one-109-ref.warpmap.txt`, 608 bytes,
  SHA-256
  `4C858562AF44E0646D9E45E445DEBAC17C6C9E4FEC28C325B9E653EB391E6C05`.
* Pre-change source hashes:
  `merge_cmd.rs`
  `8E1D2E75EA28AB3EA392F95A761767012C8EF4C216856C0F3B2D5925351DF8DC`;
  `merge_cmd/gatefloor.rs`
  `DDD2B0AC845D0E54268FBD8356FC2E44EEB6F4B61E57EA2F2FD6A25588AE3238`;
  `align_cmd.rs`
  `77498F962FE2C5F2373FD00AEFBBA6B7535C15594DA213271BE33624296E9CEE`.
* Cargo 1.98.0, rustc 1.98.0, Python 3.12.10, NumPy 2.4.4,
  tifffile 2026.5.2, rawpy 0.27.0 / LibRaw 0.22.1.

Every run copies a sidecar to M130-owned scratch first.  No command may allow
`load_or_solve` to write inside the capture library.

## 6. Exact reproduction commands

Run from PowerShell:

```powershell
Set-Location C:\dev\blog\death-of-software\projects\strehl
$out = 'C:\dev\strehl-out\M130-crop-early'
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item experiments\M-PHASE0-SPLIT\out\real-109\109-warpmap.txt `
  "$out\109-warpmap.txt"
Copy-Item D:\strehl-out\cover-default\one-109-ref.warpmap.txt `
  "$out\one-109-ref.warpmap.txt"

Get-ChildItem Env:STREHL_* | Remove-Item
$env:STREHL_FULLRES_GATHER = '1'
$env:STREHL_DEFECT = 'off'
$env:STREHL_FIX_CA = 'off'
$env:STREHL_PYRAMID_WORKERS = '2'
$env:RAYON_NUM_THREADS = '6'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
```

### 6.1 Before-change build and default render

```powershell
cargo build --release -p strehl-cli --bin strehl `
  --target-dir "$out\target-before"
$before = "$out\target-before\release\strehl.exe"
Get-FileHash -Algorithm SHA256 $before

$env:STREHL_WARPMAP = "$out\109-warpmap.txt"
$before stack D:\personal\macro\109MSDCF `
  --out "$out\before-default.tiff"
Get-FileHash -Algorithm SHA256 "$out\before-default.tiff"
```

The source is then changed and the before executable is never rebuilt.

### 6.2 After-change build and default render

```powershell
cargo build --release -p strehl-cli --bin strehl `
  --target-dir "$out\target-after"
$after = "$out\target-after\release\strehl.exe"
Get-FileHash -Algorithm SHA256 $after

$env:STREHL_WARPMAP = "$out\109-warpmap.txt"
$after stack D:\personal\macro\109MSDCF `
  --out "$out\after-default.tiff"
Get-FileHash -Algorithm SHA256 "$out\after-default.tiff"
```

`before-default.tiff` and `after-default.tiff` must have the same SHA-256,
byte count, and `3516x2344x3 uint16` decoded shape.

### 6.3 Real Crop profile

```powershell
$env:STREHL_WARPMAP = "$out\109-warpmap.txt"
$after stack D:\personal\macro\109MSDCF --merge pyramid --cover crop `
  --pyramid-bands 2 --out "$out\crop-b2.tiff"
$after stack D:\personal\macro\109MSDCF --merge pyramid --cover crop `
  --pyramid-bands 7 --out "$out\crop-b7.tiff"

$b2 = (Get-FileHash -Algorithm SHA256 "$out\crop-b2.tiff").Hash
$b7 = (Get-FileHash -Algorithm SHA256 "$out\crop-b7.tiff").Hash
python -B experiments\M130-crop-early\measure.py profile `
  --b2 "$out\crop-b2.tiff" --b7 "$out\crop-b7.tiff" `
  --expected-b2-sha $b2 --expected-b7-sha $b7
```

The exact profile output is reported even if the command exits 1.

### 6.4 One-frame external exactness

```powershell
$one = 'D:\strehl-out\cover-default\one-109-ref'
$env:STREHL_WARPMAP = "$out\one-109-ref.warpmap.txt"
$after stack $one --merge pyramid --pyramid-bands 7 --cover crop `
  --out "$out\one-crop.tiff"
$after stack $one --merge pyramid --pyramid-bands 7 --cover scale `
  --out "$out\one-scale.tiff"
$env:STREHL_ALIGN = '0'
$after stack $one --merge pyramid --pyramid-bands 7 `
  --out "$out\one-direct.tiff"
Remove-Item Env:STREHL_ALIGN

python -B experiments\M130-crop-early\exactness.py measure `
  --raw "$one\DSC00020.ARW" `
  --direct "$out\one-direct.tiff" `
  --crop "$out\one-crop.tiff" `
  --scale "$out\one-scale.tiff" --origin 5 4
```

### 6.5 Narrow source checks

No Cargo command uses `-q`.

```powershell
$env:CARGO_TARGET_DIR = "$out\target-test"
cargo test -p strehl-cli --bin strehl crop_domain
cargo test -p strehl-cli --bin strehl cover_backend
cargo test -p strehl-cli --lib gatefloor
cargo fmt --check
```

Final verification belongs to an independent verifier, not the author.

## 7. Not established by this registration

This lane does not move the default, establish the separate identical-site
survival gate, establish a universal scene-independent inset, prove visual
quality, or implement Estimator Crop.  It does not add a TIFF Crop-origin tag;
the origin is retained in the typed domain and run provenance without
changing the byte-frozen output format.
