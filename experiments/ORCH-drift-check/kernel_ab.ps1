# ORCH kernel A/B: hold the SOLVE fixed, vary ONLY the gather kernel.
#
# The sidecar records `resampler <name>` and merge_cmd.rs:923 gathers with
# map.resampler(). So copying one sidecar and rewriting that single line
# isolates the interpolation kernel perfectly: identical placements,
# identical reference, identical stack digest, identical frame count.
#
# BARS REGISTERED BEFORE RUNNING (this file was written and committed first):
#
#   B1 VALIDITY  the catmull-rom arm must hash IDENTICAL to the existing
#                ORCH-gallery3\bee-3-cpl.tif. That render came from a
#                separate invocation days apart in wall-clock terms. If it
#                does not match, something other than the kernel is varying
#                and every other arm is uninterpretable. HALT on mismatch.
#
#   B2 SWITCH    each arm's stderr must print a resampler line naming the
#                kernel its sidecar asked for. If all three print CatmullRom
#                the sidecar field is decorative and the switch does NOT ship.
#
#   B3 EFFECT    nearest and catmull-rom must NOT hash equal. If they do, the
#                kernel never reaches the gather. B2 can pass while B3 fails
#                (a value read, printed, and then ignored), which is why both
#                are here.
#
#   B4 JUDGEMENT by eye at 100%: does nearest resolve bee hair that
#                catmull-rom loses? NOT scored by any scalar. A Laplacian
#                metric rated a visibly mosaicked render 2.73x sharper
#                tonight; sharpness metrics have earned no trust here.
#
# B1 is the one that makes the rest mean anything, and it is the one most
# likely to fail.

$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

$root = "C:\dev\blog\death-of-software\projects\strehl"
$exe  = "$root\.cargo-target-orch\release\strehl.exe"
$gal  = "C:\dev\strehl-out\ORCH-gallery3"
$out  = "C:\dev\strehl-out\ORCH-kernel"
$stack = "D:\personal\macro\bee-3-cpl"

if (-not (Test-Path $exe)) { throw "no binary at $exe" }
New-Item -ItemType Directory -Force -Path $out | Out-Null

$srcCar = "$gal\bee-3-cpl-warpmap.txt"
if (-not (Test-Path $srcCar)) { throw "no sidecar at $srcCar" }

$refTif = "$gal\bee-3-cpl.tif"
$refHash = (Get-FileHash $refTif -Algorithm SHA256).Hash
"reference render $refTif"
"  sha256 $refHash"
""

$arms = @("catmull-rom", "nearest", "bilinear")
$results = @{}

foreach ($k in $arms) {
    "=== arm: $k ==="
    $car = "$out\bee-3-cpl-$k-warpmap.txt"

    # single-line rewrite; everything else byte-preserved
    $lines = Get-Content $srcCar
    $hit = 0
    $new = $lines | ForEach-Object {
        if ($_ -match '^resampler\s') { $hit++; "resampler $k" } else { $_ }
    }
    if ($hit -ne 1) { throw "expected exactly 1 resampler line, rewrote $hit" }
    Set-Content -Path $car -Value $new -Encoding ASCII

    $check = (Get-Content $car | Where-Object { $_ -match '^resampler\s' })
    if ($check -ne "resampler $k") { throw "sidecar rewrite failed: '$check'" }
    "  sidecar says: $check"

    $tif = "$out\bee-3-cpl-$k.tif"
    $env:STREHL_WARPMAP = $car

    $t0 = Get-Date
    # rule 46: capture first, filter afterwards. NEVER read $LASTEXITCODE
    # through a pipeline that can truncate.
    $log = & $exe stack $stack --srgb --auto-exposure --out $tif 2>&1
    $code = $LASTEXITCODE
    $secs = ((Get-Date) - $t0).TotalSeconds

    Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

    $log | Set-Content "$out\bee-3-cpl-$k.log"
    "  exit $code in $([math]::Round($secs,1)) s"

    if ($code -ne 0) {
        $log | Select-Object -Last 15 | ForEach-Object { "    $_" }
        throw "arm $k exited $code"
    }

    $rline = $log | Where-Object { $_ -match 'resampler' } | Select-Object -First 1
    $sline = $log | Where-Object { $_ -match 'sidecar' }   | Select-Object -First 1
    "  tool reports: $($rline -replace '\s+',' ')"
    "  sidecar path: $($sline -replace '\s+',' ')"

    $h = (Get-FileHash $tif -Algorithm SHA256).Hash
    "  sha256 $h"
    $results[$k] = @{ hash = $h; report = $rline; secs = $secs }
    ""
}

"================ BARS ================"

$b1 = ($results["catmull-rom"].hash -eq $refHash)
"B1 VALIDITY  catmull-rom arm == existing gallery render : $(if($b1){'PASS'}else{'FAIL'})"
if (-not $b1) {
    "   arm $($results['catmull-rom'].hash)"
    "   gal $refHash"
    "   HALT-WORTHY: the solve or the code changed under the experiment."
}

$b2ok = $true
foreach ($k in $arms) {
    $want = switch ($k) {
        "catmull-rom" { "CatmullRom" }
        "nearest"     { "Nearest" }
        "bilinear"    { "Bilinear" }
    }
    $got = $results[$k].report
    $ok = ($got -match $want)
    if (-not $ok) { $b2ok = $false }
    "B2 SWITCH    $k -> expects '$want' : $(if($ok){'PASS'}else{"FAIL ($got)"})"
}

$b3 = ($results["nearest"].hash -ne $results["catmull-rom"].hash)
"B3 EFFECT    nearest != catmull-rom bytes : $(if($b3){'PASS'}else{'FAIL'})"

""
"B4 is by eye and is not scored here. Next: crops.py"
"verdict: switch ships end-to-end = $(if($b2ok -and $b3){'YES'}else{'NO'})"
