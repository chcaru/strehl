# M173 — Ask 2a one-shot audit

**[verified by running]** Audit date: 2026-09-04.
**[verified by running]** Audited HEAD: `0388ff52f62bb7be7797c9a97b485bc99d28e167`.
**[verified by running]** Audited blobs: `OWNER-ACTIONS.md` `690d7a7d158ce69ddbbcea60449ba08cd3a6271a`; `M147-preflight.md` `c0b6ad5bbbaea775e534c3efc0f1a8e42b21b826`; `preflight.py` `1a8d72b7a8c32e353e3e6fffa825ace9e5561184`.

## Verdict

DEFECTS FOUND

**[inferred] Specification verdict: NOT SOUND.**

- **[verified by reading]** Two valid images are sufficient to execute M147 for one converter-on/converter-off placement: the program accepts one role-labelled reference ARW and one role-labelled TC0 ARW and decides from their common-grid period ratio (`preflight.py:1283-1317,1404-1411`; `M147-preflight.md:40-51,295-302`).
- **[verified by reading]** Ask 2a is not a safe one-shot capture specification. It omits ARW/full-resolution format, exact grid/coverage, exposure/aperture/stabilisation/polarizer state, FULL-MF placement, axial-only camera motion, common-centre framing, and preserving/recording the accepted setup (`OWNER-ACTIONS.md:612-620`). Literal compliance can therefore produce unusable or non-transferable evidence.
- **[verified by running]** The changed behavior cannot yet be tested: all 10,509 archived ARWs report the converter-on identity and 200.0 mm. No real converter-off pair exists, so the central field result remains unverified.
- **[verified by reading]** A numerical `FAIL` or quality `REFUSED` result does not commission a gate. M164 permits another two-frame placement and requires abandoning the design if no working magnification satisfies ratio, field, and carrier constraints (`M164-m1-staged-capture.md:327-359,669-671`). Ask 2a omits those outcomes.

## Commands run

**[verified by running] Repository/version pin:**

```powershell
git -C C:\dev\blog\death-of-software\projects\strehl rev-parse HEAD; git -C C:\dev\blog\death-of-software\projects\strehl rev-parse HEAD:docs/OWNER-ACTIONS.md HEAD:docs/research/M147-preflight.md HEAD:experiments/M147-preflight/preflight.py; git -C C:\dev\blog\death-of-software\projects\strehl --no-pager diff --exit-code -- docs/OWNER-ACTIONS.md docs/research/M147-preflight.md experiments/M147-preflight/preflight.py; "DiffExit=$LASTEXITCODE"
```

```text
0388ff52f62bb7be7797c9a97b485bc99d28e167
690d7a7d158ce69ddbbcea60449ba08cd3a6271a
c0b6ad5bbbaea775e534c3efc0f1a8e42b21b826
1a8d72b7a8c32e353e3e6fffa825ace9e5561184
DiffExit=0
```

**[verified by running] Narrow M147 tests:**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; Set-Location 'C:\dev\blog\death-of-software\projects\strehl\experiments\M147-preflight'; python -m unittest -v test_preflight.DecisionTests test_preflight.HarmonicTests
```

```text
test_direct_period_ratio_passes (test_preflight.DecisionTests.test_direct_period_ratio_passes) ... ok
test_local_scale_defect_cannot_average_to_pass (test_preflight.DecisionTests.test_local_scale_defect_cannot_average_to_pass) ... ok
test_one_retained_site_cannot_be_medianed_out (test_preflight.DecisionTests.test_one_retained_site_cannot_be_medianed_out) ... ok
test_output_action_is_console_ascii (test_preflight.DecisionTests.test_output_action_is_console_ascii) ... ok
test_point_at_threshold_fails_on_lower_bound (test_preflight.DecisionTests.test_point_at_threshold_fails_on_lower_bound) ... ok
test_rotated_mapping_cannot_miss_a_bad_site (test_preflight.DecisionTests.test_rotated_mapping_cannot_miss_a_bad_site) ... ok
test_yx_rotation_maps_to_the_physical_site (test_preflight.DecisionTests.test_yx_rotation_maps_to_the_physical_site) ... ok
test_second_harmonic_exposes_primitive_alternative (test_preflight.HarmonicTests.test_second_harmonic_exposes_primitive_alternative) ... ok
test_weak_second_harmonic_primitive_refuses (test_preflight.HarmonicTests.test_weak_second_harmonic_primitive_refuses) ... ok
test_weak_third_harmonic_primitive_refuses (test_preflight.HarmonicTests.test_weak_third_harmonic_primitive_refuses) ... ok
----------------------------------------------------------------------
[timing line omitted under the required absolute-timing quarantine]
OK
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; Set-Location 'C:\dev\blog\death-of-software\projects\strehl\experiments\M147-preflight'; python -m unittest -v test_preflight.ContractTests.test_parameter_hash_is_canonical
```

```text
test_parameter_hash_is_canonical (test_preflight.ContractTests.test_parameter_hash_is_canonical) ... ok
----------------------------------------------------------------------
[timing line omitted under the required absolute-timing quarantine]
OK
```

**[verified by running] Frozen CLI on the recorded non-holdout same-state pair; output used Windows `NUL`, not a file:**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; Set-Location 'C:\dev\blog\death-of-software\projects\strehl'; python experiments\M147-preflight\preflight.py --reference-arw 'D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00042.ARW' --tc0-arw 'D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00043.ARW' --output-json NUL; "ProcessExit=$LASTEXITCODE"
```

```text
M147 MAGNIFICATION PREFLIGHT
WARNING: provisional build; real converter-on/off commissioning is still required before shooting.
Reference period: 127.0221 sensor px
TC0 period:      126.9753 sensor px
Sampling ratio:  1.000304
Conservative 95% interval: [0.993420, 1.007240]
Verdict: FAIL
FAIL: the sampling ratio is not safely at or above 2.0. Reduce TC0 magnification by at least about 50.33% (about 51.09% to restore the registered 2.0312 target), or verify that the converter is seated and the reference is at maximum reproduction; then retake both preflight frames.
Artifact: \\.\NUL
[timing line omitted under the required absolute-timing quarantine]
ProcessExit=2
```

**[verified by running] Input-error edges:**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; Set-Location 'C:\dev\blog\death-of-software\projects\strehl'; python experiments\M147-preflight\preflight.py --reference-arw 'D:\does-not-exist\REF.ARW' --tc0-arw 'D:\does-not-exist\TC0.ARW' --output-json NUL; "ProcessExit=$LASTEXITCODE"
```

```text
INPUT ERROR: reference input is not a file: D:\does-not-exist\REF.ARW
ProcessExit=64
```

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; Set-Location 'C:\dev\blog\death-of-software\projects\strehl'; $f='D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl\flat-sw4-cpl\flat-et1s-sw4-cpl\DSC00042.ARW'; python experiments\M147-preflight\preflight.py --reference-arw $f --tc0-arw $f --output-json NUL; "ProcessExit=$LASTEXITCODE"
```

```text
INPUT ERROR: reference and TC0 paths must be different files
ProcessExit=64
```

**[verified by running] Independent decimal arithmetic:**

```powershell
python -c 'from decimal import Decimal, getcontext; getcontext().prec=30; ref=Decimal("2.7015"); tc=Decimal("1.33"); r=ref/tc; d=r-Decimal(2); print(f"ratio={r}"); print(f"absolute_margin={d}"); print(f"margin_over_threshold_percent={d/Decimal(2)*100}"); print(f"margin_as_fraction_of_achieved_percent={d/r*100}"); print(f"ratio_at_1.32={ref/Decimal("1.32")}"); print(f"ratio_at_1.36={ref/Decimal("1.36")}")'
```

```text
ratio=2.03120300751879699248120300752
absolute_margin=0.03120300751879699248120300752
margin_over_threshold_percent=1.56015037593984962406015037600
margin_as_fraction_of_achieved_percent=1.53618360170275772718859892658
ratio_at_1.32=2.04659090909090909090909090909
ratio_at_1.36=1.98639705882352941176470588235
```
**[verified by running] Read-only archive enumeration before and after metadata inspection:**

```powershell
$roots = @('D:\personal\macro','D:\edited\macro'); foreach ($root in $roots) { $files = @(Get-ChildItem -LiteralPath $root -Force -Recurse -File -Filter *.ARW -ErrorAction Stop); [pscustomobject]@{ Root=$root; ARWs=$files.Count; Bytes=($files | Measure-Object Length -Sum).Sum; HoldoutARWs=@($files | Where-Object FullName -Like 'D:\personal\macro\requests\7-aperture-pairs\*').Count } | Format-List }; "ExifTool version: $(& exiftool -ver)"
```

```text
Root        : D:\personal\macro
ARWs        : 10509
Bytes       : 485787389952
HoldoutARWs : 623

Root        : D:\edited\macro
ARWs        : 0
Bytes       :
HoldoutARWs : 0

ExifTool version: 13.58
```

```powershell
$roots=@('D:\personal\macro','D:\edited\macro'); foreach($root in $roots){$files=@(Get-ChildItem -LiteralPath $root -Force -Recurse -File -Filter *.ARW -ErrorAction Stop); "Root=$root ARWs=$($files.Count) Bytes=$(($files|Measure-Object Length -Sum).Sum)"}
```

```text
Root=D:\personal\macro ARWs=10509 Bytes=485787389952
Root=D:\edited\macro ARWs=0 Bytes=
```

**[verified by running] ExifTool metadata-only census; no archive image data were decoded, and the holdout was not passed to `rawpy` or another image reader:**

```powershell
$rows = @(& exiftool -r -ext ARW -csv -Model -LensModel -FocalLength -ImageStabilization -FocusDistance2 -FocusPosition2 'D:\personal\macro' | ConvertFrom-Csv); "ExifToolExit=$LASTEXITCODE Rows=$($rows.Count)"; foreach ($tag in @('Model','LensModel','FocalLength','ImageStabilization')) { "[$tag]"; $rows | Group-Object -Property $tag | Sort-Object Count -Descending | ForEach-Object { "Count=$($_.Count) Value=<$($_.Name)>" } }; foreach ($tag in @('FocusDistance2','FocusPosition2')) { $missing = @($rows | Where-Object { [string]::IsNullOrWhiteSpace($_.$tag) }).Count; $distinct = @($rows | Where-Object { -not [string]::IsNullOrWhiteSpace($_.$tag) } | Select-Object -ExpandProperty $tag -Unique).Count; $values = @($rows | Where-Object { -not [string]::IsNullOrWhiteSpace($_.$tag) } | Select-Object -ExpandProperty $tag -Unique | Sort-Object); "[$tag] Missing=$missing DistinctNonempty=$distinct First=<$($values | Select-Object -First 1)> Last=<$($values | Select-Object -Last 1)>" }
```

```text
83 directories scanned
10509 image files read
ExifToolExit=0 Rows=10509
[Model]
Count=10509 Value=<ILCE-7CM2>
[LensModel]
Count=10509 Value=<FE 100mm F2.8 Macro GM OSS + 2X Teleconverter>
[FocalLength]
Count=10509 Value=<200.0 mm>
[ImageStabilization]
Count=10509 Value=<On>
[FocusDistance2] Missing=0 DistinctNonempty=15 First=<0.2707 m> Last=<inf>
[FocusPosition2] Missing=0 DistinctNonempty=15 First=<255> Last=<70>
```

```powershell
$rows = @(& exiftool -r -ext ARW -csv -ReleaseMode -Quality -RAWFileType -SonyRawFileType 'D:\personal\macro' | ConvertFrom-Csv); "ExifToolExit=$LASTEXITCODE Rows=$($rows.Count)"; foreach ($tag in @('ReleaseMode','Quality','RAWFileType','SonyRawFileType')) { "[$tag]"; $rows | Group-Object -Property $tag | Sort-Object Count -Descending | ForEach-Object { "Count=$($_.Count) Value=<$($_.Name)>" } }
```

```text
83 directories scanned
10509 image files read
ExifToolExit=0 Rows=10509
[ReleaseMode]
Count=8957 Value=<Exposure Bracketing>
Count=1442 Value=<Normal>
Count=110 Value=<Continuous>
[Quality]
Count=10509 Value=<RAW>
[RAWFileType]
Count=7665 Value=<Lossless Compressed RAW>
Count=2844 Value=<Uncompressed RAW>
[SonyRawFileType]
Count=7665 Value=<Sony Lossless Compressed RAW 2>
Count=2844 Value=<Sony Uncompressed 14-bit RAW>
```

**[verified by running] Frozen artifact summary:**

```powershell
$p='C:\dev\blog\death-of-software\projects\strehl\experiments\M147-preflight'; foreach($name in @('preflight.py','commission.py','verify.py','out\null.json','out\commission.json','out\verification.json')) { $h=(Get-FileHash (Join-Path $p $name) -Algorithm SHA256).Hash; "$(Split-Path $name -Leaf) $h" }; $c=Get-Content "$p\out\commission.json" -Raw|ConvertFrom-Json; $v=Get-Content "$p\out\verification.json" -Raw|ConvertFrom-Json; "CommissionAllPass=$($c.all_recorded_arms_pass) FieldStatus=$($c.field_commission.status) Arms=$(@($c.arms.PSObject.Properties).Count) Coverage=$($c.coverage.covered_trials)/$($c.coverage.recorded_trials)"; "VerificationPass=$($v.pass) CheckCount=$(@($v.checks.PSObject.Properties).Count) FailedChecks=$(@($v.checks.PSObject.Properties|Where-Object {$_.Value -ne $true}).Count)"
```

```text
preflight.py 29BA7B8DE9DB80B7167FD068A3D96269D4D91287DB5C823109EBEB149B1B8E98
commission.py 41A2652136AED92268F866CC006FE14FF8DAA0BCD65D9582A1EE33F7AF7C91C7
verify.py 21C226B603DABA53F2D34249F979880F6E31671153ABA6FA62968684D8DA5D04
null.json 2488BE480821C66FB37998D552078E6773F4B273DC142840744DE1045A85C236
commission.json 93930D869EF5AA373EA5039CCD836241766193E3782308683D481060A7784BA9
verification.json 8FA86FBB8E1878006178DBBF40BD1B42E9E89D5B603CFD13A2570A581AA4C122
CommissionAllPass=True FieldStatus=BLOCKED Arms=38 Coverage=20/20
VerificationPass=True CheckCount=24 FailedChecks=0
```

**[verified by running] Sony's public page (`https://www.sony.jp/ichigan/products/SEL100M28GM/feature_1.html`):**

```powershell
$ProgressPreference='SilentlyContinue'; $u='https://www.sony.jp/ichigan/products/SEL100M28GM/feature_1.html'; $r=Invoke-WebRequest -UseBasicParsing -Uri $u -Headers @{'User-Agent'='Mozilla/5.0'} -TimeoutSec 30; $t=[System.Net.WebUtility]::HtmlDecode([regex]::Replace($r.Content,'<[^>]+>',' ')) -replace '\s+',' '; "HTTP=$($r.StatusCode)"; [regex]::Match($t,'レンズ本体で最大撮影倍率1\.4倍、さらに別売のテレコンバーター（\＊）を使用した場合は最大撮影倍率2\.8倍を実現。').Value; [regex]::Match($t,'スライド式の「フォーカスリング」で倍率/距離目盛と連動したFULL MFモードに切り替えが可能。FULL MFモードでは、無限遠と最短撮影距離の間でフォーカスリングが回転します。').Value
```

```text
HTTP=200
レンズ本体で最大撮影倍率1.4倍、さらに別売のテレコンバーター（＊）を使用した場合は最大撮影倍率2.8倍を実現。
スライド式の「フォーカスリング」で倍率/距離目盛と連動したFULL MFモードに切り替えが可能。FULL MFモードでは、無限遠と最短撮影距離の間でフォーカスリングが回転します。
```
## Claims checked

### 1. Sufficiency

- **[verified by reading] Confirmed, conditional:** two original, different, full-resolution Sony ARWs of the same grid are the complete file inputs to M147. Grid and sensor pitch cancel, and EXIF focal length is unused (`M147-preflight.md:40-51`; `preflight.py:170-176,1283-1317`). No absolute pitch certificate is needed for the ratio.
- **[verified by reading] Refuted as written:** Ask 2a requests “one frame” twice but never says ARW or full resolution. A JPEG follows the prose but fails the extension check; a reduced/cropped or altered RAW violates the documented full-resolution requirement and can fail geometry/coverage (`OWNER-ACTIONS.md:612-620`; `preflight.py:170-176,839-849,1300-1315`).
- **[verified by reading] Qualified:** exact physical pitch need not be known, but pitch is not arbitrary. The primitive must land from `20` through `96` native green-site pixels in each image (`preflight.py:48-53,467-473`). The commissioned slide's existing converter-on null is about `63.5` green pixels per primitive and expected TC0 is about `31–32`, so that slide is in range (`M147-preflight.md:86-91`; `out/null.json`). Ask does not distinguish this high-resolution dot-grid slide from other calibration targets.
- **[verified by reading] Missing:** each green phase needs at least 12 coherent tile candidates; each image needs at least six coherent 512-green-pixel blocks; at least six reference regions must map to TC0 grid (`preflight.py:68-75,575-668,851-880,1130-1137`). There is no separate whole-frame minimum-period count. The 20–96 range means a qualifying 512-pixel tile contains about 5.3–25.6 primitive periods. The ask does not tell the owner to fill enough of both frames with the intended grid.
- **[verified by reading] Focus:** no numeric focus-error threshold exists. Modest defocus is tolerated, but weak/blurred evidence fails tile-range, peak-SNR, coherent-candidate, green-phase, or harmonic gates (`M147-preflight.md:78-84`; `preflight.py:54-64,391-396,575-583,706-711,851-867`). Both frames need critical focus. Ask explicitly says “focused” only for TC0 and does not say how to retain a selected reproduction setting while focusing.
- **[verified by reading] Exposure/ISO:** M147 does not inspect ISO, shutter, or matched exposure. It independently refuses over `0.5%` low-rail pixels, over `0.1%` high-rail pixels, or under `1%` robust RAW range (`preflight.py:38-42,275-302`). Equal exposure is not mathematically required. **[inferred]** To commission the registered configuration, both should nevertheless use M mode, ISO 100, 1 s, camera-indicated/marked f/5.6, fixed WB, EFCS, 14-bit RAW, and unchanged light (`M164-m1-staged-capture.md:672-675`). If exposure must change, restart and declare the whole pair.
- **[verified by reading] Aperture:** the CLI has no aperture check. **[inferred]** Aperture remains acquisition-critical because M147 calls its allowance unbound for different optical blur (`M147-preflight.md:109-121`); an arbitrary-aperture pair does not bind the planned f/5.6 state.
- **[verified by reading] Lighting flatness:** affine illumination is detrended, so perfect flatness is unnecessary (`M147-preflight.md:78-82`; `preflight.py:398-405`). Weak contrast, clipping, or patterned illumination can refuse. “Same lighting” does not require even illumination or a histogram check.
- **[verified by reading] Squareness:** no physical angle tolerance is stated. The tool refuses over `1%` local period MAD, over `5°` orientation MAD, over `1.5%` pair anisotropy, or over `15°` relative rotation (`preflight.py:73-78,670-703,1193-1213`). “Flat and square” does not tell the operator to lock the camera head and move only axially.
- **[verified by reading] Second null:** M147 requires no new second null pair. One same-state null is recorded and the field table names one converter pair (`M147-preflight.md:139-152,342-347`). Its interval explicitly is not a temporal repeat-capture interval (`M147-preflight.md:100-109`). **[inferred]** A new complete pair is required after any prescribed placement change; do not mix frames across attempts.
- **[verified by reading] State retention is missing:** M147's PASS action says preserve rig settings, and its interval excludes later drift (`preflight.py:1219-1225`; `M147-preflight.md:100-109`). Ask does not tell the owner to leave the rig locked or record enough state to reproduce it.

### 2. Magnification arithmetic and bench observability

- **[verified by running] Arithmetic confirmed with a denominator qualification:** `2.7015 / 1.33 = 2.0312030075…`; absolute headroom above `2.0` is `0.0312030075…x`. It is `1.53618%`, rounding to the stated `1.54%`, as a fraction of the achieved ratio. It is `1.56015%` as excess over the `2.0` requirement. The prose should name the denominator.
- **[verified by running]** At exactly `1.32`, the conservative geometric ratio is `2.0465909`; at `1.36`, it is `1.9863971`, below the point threshold before uncertainty. “About 1.32x” can include a failing placement if interpreted loosely.
- **[verified by running]** Sony confirms a physical magnification/distance scale coupled to the FULL-MF sliding focus ring, native maximum `1.4x`, and nominal `2.8x` with a 2x converter. **[inferred]** Rough `1.32x` placement is possible at the rig; metadata absence does not prevent rough capture-time placement.
- **[verified by running]** The archive's `FocusPosition2` has only 15 distinct values over 10,509 files, and neither it nor composite `FocusDistance2` is independently measured reproduction ratio. **[verified by reading]** M141 classifies physical magnification as metadata-recoverable for zero stacks (`M141-capture-inventory.md:90-99`).
- **[verified by reading]** M147 computes only `P_ref/P_TC0`; it never computes absolute `m_ref` or `m_TC0` (`M147-preflight.md:40-51`). The pair can verify required relative sampling after capture, but cannot certify absolute `1.32x` or `<=1.33x`.
- **[inferred]** Safe operation is to set the lens scale in FULL MF, then focus by moving the camera/lens assembly axially. Autofocusing, or turning the ring until an unmoved camera happens to focus, changes the magnification being tested. “Focused to about 1.32x” does not distinguish these actions.
- **[inferred]** A one-shot promise is not defensible unless the rig remains locked while the pair is run. Neither scale nor EXIF has demonstrated the sub-`0.76%` precision needed to distinguish `1.32` from `1.33`; the RAW result is the verifier, and a failed placement requires another pair.

### 3. Ambiguity for the operator

- **[verified by reading]** “The calibration slide” is ambiguous: the archive contains both `30-calibration-grid` and `high-res-calibration-slide-cpl`; M147 was commissioned on the latter's regular dot grid (`commission.py:33-42`; `verify.py:90-93`).
- **[verified by reading]** “Maximum reproduction” does not say “converter fully seated, lens in FULL MF, native `1.4:1`/minimum-focus end, then focus by axial rail motion.” Sony confirms those controls exist; the prose permits autofocus or camera-stationary focusing.
- **[verified by reading]** “Same slide, same position” constrains the slide but not the camera. M147 requires preserving target plane and camera roll/yaw and moving axially to reframe (`M147-preflight.md:295-302`). Ask 2a omits axial-only motion, tripod-head lock, no lateral shift, and same physical centre.
- **[verified by reading]** The local mapper contains centred scale and rotation but no translation term (`preflight.py:367-383,1006-1048`). The 38-arm battery contains rotation and perspective attacks but no translated real-pair arm. **[inferred]** If the slide or camera head shifts, discard both images and restart.
- **[verified by running]** Every archived ARW reports `ImageStabilization: On`, while the downstream protocol requires body SteadyShot and lens OSS off. Ask 2a says neither. **[inferred]** Both must be off for a representative field pair.
- **[verified by reading]** The planned state includes a fixed crossed-polarizer state (`2026-09-319-frame-session.md:500-527`; `M164-m1-staged-capture.md:674-675`). “Same lighting” does not explicitly keep the CPL fitted and unrotated.
- **[verified by reading]** Ask does not say whether exposure must match. M147 permits different valid exposures; commissioning transfer is cleaner if ISO, shutter, aperture, light, and polarizer remain fixed. The replacement below fixes them and requires restarting both if anything changes.
- **[verified by reading]** Ask does not say what to do after target motion, focus miss, clipping, numerical failure, or refusal. The tool has distinct outcomes; “the target moves” is not correct for all of them.

### 4. Falsifiability and outcomes

- **[verified by reading] Numeric PASS:** only `status == OK` with unrounded lower bound `>= 2.0` passes (`preflight.py:1216-1260`; `M147-preflight.md:127-137`). The executable still prints a provisional-build warning on every result (`preflight.py:1363-1371`), so PASS alone does not authorize the session.
- **[verified by reading] Numeric FAIL:** lower bound `< 2.0` rejects that placement and may prescribe lower TC0 magnification plus a complete new pair (`preflight.py:1226-1249`). It does not commission the new setting before retest.
- **[verified by reading] Quality REFUSED:** clipping, weak/ambiguous grid, insufficient coverage, nonuniform plane, green disagreement, anisotropy, rotation, or mapping failure yields no ratio. Correct and retake; it is not optical-design failure (`preflight.py:1324-1360`; `M164-m1-staged-capture.md:353-359`).
- **[verified by reading] Design STOP:** M164's feasible set also includes common-field and carrier-frequency bounds. An empty set, or a second valid failure at the lowest otherwise eligible `M_work`, abandons the shared-prime inversion (`M164-m1-staged-capture.md:337-359,669-671`).
- **[verified by reading] Refuted:** Ask does not disclose design STOP. It says the target moves and that two frames replace argument with measurement (`OWNER-ACTIONS.md:24-35,640-644`). One first pair near `1.32x` can return PASS, placement FAIL requiring another pair, or REFUSED; it cannot alone prove no lower eligible setting exists.

### 5. Rig and archive

- **[verified by running]** `Get-ChildItem -Force` found 10,509 ARWs / 485,787,389,952 bytes under `D:\personal\macro` and zero ARWs under `D:\edited\macro`; counts and bytes were unchanged afterward.
- **[verified by running]** ExifTool 13.58 over all 10,509 ARWs reports model `ILCE-7CM2`, lens `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, focal length `200.0 mm`, and `ImageStabilization: On` for every file. This confirms the A7C II, Sony 100 mm base lens, and communicating 2x optical state.
- **[verified by running]** EXIF does not identify Viltrox; that brand remains owner testimony.
- **[verified by running]** Release mode is not uniform: 8,957 files say `Exposure Bracketing`, 1,442 `Normal`, and 110 `Continuous`. **[inferred]** Metadata supports extensive in-camera bracketing but does not prove every inventoried ARW belongs to a focus bracket; fixed-focus, flat, dark, and repeat captures include other modes. Nor does the generic `Exposure Bracketing` string independently prove focus bracketing in every case.
- **[verified by running]** All files are RAW: 7,665 lossless-compressed and 2,844 uncompressed 14-bit. The field pair should be untouched full-resolution ARWs.
- **[verified by running]** The holdout subtree was enumerated and read only through ExifTool metadata. No holdout file was passed to `rawpy`, decoded, rendered, or otherwise read as image data. The sole production RAW decode used the explicitly non-holdout `misc-diagnostic/high-res-calibration-slide-cpl` null pair.

## Defects

1. **[verified by reading] CRITICAL — Literal compliance can deliver inputs M147 cannot use.** `docs/OWNER-ACTIONS.md:612-620`; reproduce by shooting JPEGs, reduced/cropped RAWs, or another calibration grid. JPEG fails the extension check; reduced/cropped RAW violates the documented full-resolution requirement; and the intended grid must supply coherent coverage in the admitted period band; the ask does not say so.
2. **[verified by reading] CRITICAL — Focus/reframe instructions can produce the wrong magnification or blur.** `docs/OWNER-ACTIONS.md:614-620`; reproduce by leaving the camera fixed after converter removal and turning the ring until sharp. That does not preserve a selected `1.32x`. M147 requires axial camera motion while preserving plane and roll/yaw (`docs/research/M147-preflight.md:295-302`).
3. **[inferred] HIGH — The pair is not bound to the configuration it is meant to commission.** `docs/OWNER-ACTIONS.md:612-620`; reproduce with IBIS/OSS on, another aperture, auto exposure, or a moved polarizer. The CLI does not check these, so it can numerically pass a non-representative pair.
4. **[verified by running] HIGH — “About 1.32x” is not an on-rig gate, and accepted state is not preserved or recorded.** `docs/OWNER-ACTIONS.md:615-620,646-650`; reproduce at `1.36x`, which gives only `1.986397...`, or dismantle a passing setup. EXIF lacks absolute ratio, M147 measures only relative ratio, and its interval excludes later drift.
5. **[verified by reading] HIGH — Outcome disclosure is incomplete.** `docs/OWNER-ACTIONS.md:24-35,640-644`; a quality refusal requires a new pair, while failure at the lowest field/carrier-eligible setting can falsify the shared-prime design. Current text promises only that the target moves.
6. **[verified by running] MEDIUM — The evidence paragraph is stale.** `docs/OWNER-ACTIONS.md:633-638`; the frozen artifact reports null ratio `1.000303904...` (error `0.0303904%`) and nominal recovered ratio `2.032915850...` for truth `2.0312` (error `0.0844747%`), not Ask 2a's numbers. Both absolute-duration figures recorded across the two documents are under unknown load and remain UNVERIFIED; neither should be used as evidence.
7. **[verified by reading] MEDIUM — Slight slide/camera translation has no specified recovery.** `docs/OWNER-ACTIONS.md:618-620`; reproduce by bumping the slide or shifting the head. The mapper models centred scale and rotation, not translation, and no translation commissioning arm exists. Instructions must require restarting both frames.

## Gaps

- **[verified by running]** No real converter-off RAW exists, so the core converter-change behavior cannot be run before owner data arrive. No test exists for that changed optical behavior; field commissioning remains unverified despite passing synthetic and same-state tests.
- **[verified by reading]** One unknown-ratio real pair supplies no external truth value for converter-dependent estimator bias. M147's `0.25%` expansion remains explicitly unbound for a real optical-train change (`M147-preflight.md:109-121`). **[inferred]** Admission needs independent review and must not relabel that allowance calibrated merely because the estimator emitted a number.
- **[verified by reading]** M147 does not test temporal repeat-capture uncertainty, absolute `1.32x`, later replacement of the setting, or full-target field/carrier feasibility.
- **[verified by reading]** The whole `ContractTests` class was not run because `test_decode_refusal_preserves_file_provenance` intentionally writes temporary fake ARWs, forbidden by this lane's read-only rule. Its non-writing hash test ran; missing-file and identical-file behavior were probed directly.

## Exact replacement text for Ask 2a

**[inferred]** Replace the current **“What to shoot”** block and its following setup paragraph with:

> **Before you start:** this is one preflight attempt, normally two RAW files. It may require a second two-frame attempt if the first placement misses the gate or either file is refused. Do not begin the rehearsal or scored session from these frames alone.
>
> **What to shoot:**
>
> 1. Use the **high-resolution calibration slide's regular dot grid** used for the existing `high-res-calibration-slide-cpl` captures—not the ruler, the older calibration-grid target, or a nonperiodic patch. Mount it rigidly, flat, and as square to the sensor as you can. Choose one grid intersection near frame centre and keep that same physical point centred in both frames. Make the grid fill most of both frames.
> 2. Set **M mode, ISO 100, 1 s, camera-indicated/marked f/5.6, fixed white balance, EFCS, and full-resolution 14-bit lossless-compressed ARW**. Turn **body SteadyShot/IBIS OFF** and the lens **OSS switch OFF**. Keep the light warmed and fixed. Leave the CPL/polarizer fitted and do not rotate it. Do not use crop mode, digital zoom, autofocus, focus bracketing, or an in-camera JPEG for either requested frame.
> 3. Fit and fully seat the 2x converter. Put the sliding focus ring in **FULL MF** and set the lens to its native **1.4:1 / minimum-focus end stop**; that is “maximum reproduction” here. Do not change focus on the lens after setting it. Move the complete camera/lens assembly **only along the optical axis on the rail** until the grid is critically sharp. Lock the tripod head and rail, confirm the selected grid intersection is centred, and take one frame. Identify the untouched original as `TR-REF-PREFLIGHT.ARW`.
> 4. Do not touch the slide, target tilt, light, polarizer, tripod head, camera height, camera lateral position, roll, or yaw. Remove the converter and mount the 100 mm lens directly. Put the lens in FULL MF and use its magnification scale to aim near **1.32x**, on the lower-magnification side rather than above the **1.33x ceiling**. This scale is only the initial placement; the RAW measurement, not the printed mark or EXIF, decides acceptance.
> 5. Keep that lens setting fixed. Refocus **only by moving the complete camera/lens assembly axially on the rail**. Do not pan, tilt, roll, yaw, raise, or shift sideways. Keep the same physical grid intersection centred and the same grid plane in view. Take one frame and identify the untouched original as `TC0-PREFLIGHT.ARW`.
> 6. If the slide, tripod head, camera centre, light, polarizer, aperture, ISO, shutter, or RAW mode changed—or if either frame is not critically sharp—discard **both** frames and restart at step 1. Never combine one frame from before a shift with one from after it.
> 7. Record or phone-photograph the bare-lens magnification-scale indication and rail/working-distance reading. Leave the rig locked and unchanged while the two original ARWs are checked. Send the originals, not exports. If the rig cannot remain locked, say so; a live pair must be repeated before the later session.

**[inferred]** Replace **“What it settles”** through the end of the current synthetic caveat with:

> **What it settles.** These files test the one physical placement you captured. The checker divides the same grid's measured periods, so it does not need grid pitch, sensor pitch, focal-length metadata, or an EXIF magnification value. It does **not** infer absolute `1.32x` from metadata.
>
> There are three possible first results:
>
> - **Numerical PASS:** the measurement is valid and its unrounded lower bound is at least `2.0`. Keep the setup unchanged while the result is reviewed. A provisional console `PASS` is not permission to start either session; wait for an explicit go-ahead.
> - **Numerical FAIL:** the pair was measured, but this placement lacks enough margin. We may ask you to lower bare-lens magnification and repeat **both** frames.
> - **REFUSED / no ratio:** focus, exposure, grid coverage, target plane, camera pose, or input format was not measurable. Correct the named problem and repeat **both** frames; this is not an optical-design verdict.
>
> A lower TC0 setting is usable only if the required target field and detail frequencies still fit. If no setting satisfies all three conditions—sampling ratio, common field, and carrier frequency—the present shared-lens reference design stops rather than lowering the `2.0` bar. These files can therefore save the large shoot, require one corrected pair, or show that this design must change.

**[inferred]** Replace the arithmetic sentence in **“The blocking finding”** with:

> As designed, `2.7015 / 1.33 = 2.031203...x`. That is `0.031203...x` above the `2.0x` gate: `1.560%` relative to the required value, or `1.536%` relative to the achieved ratio. The shorthand `1.54%` uses the latter denominator.
