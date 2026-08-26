# BUILD-HIGHLIGHT render driver.
#
# ONE binary, two arms, one warpmap per subject. The arms differ only in
# STREHL_HIGHLIGHT_KNEE, so a before/after is not a cross-build comparison --
# the project has measured those to be void outside the green plane (two builds
# green-bit-identical while red moved 3902 DN on 97.7% of samples).
#
# --merge pyramid is passed EXPLICITLY on every render. Passing an
# estimator-only flag without --merge silently selects the estimator backend,
# and the banner is the only record of what actually ran, so every banner line
# is captured beside its render.
#
# Usage: h5_render.ps1 <subject> <arm-tag> [knee]
#   knee omitted -> the shipped default (on)
#   knee "off"   -> the render as it was before this module existed

param(
    [Parameter(Mandatory = $true)][string]$Subject,
    [Parameter(Mandatory = $true)][string]$Arm,
    [string]$Knee = ""
)

$ErrorActionPreference = "Stop"
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$exe = "$repo\.cargo-target-highlight\release\strehl.exe"
$scratch = "C:\dev\strehl-out\BUILD-HIGHLIGHT"
$src = "D:\personal\macro\$Subject"
$wm = "$scratch\warpmaps\$Subject.txt"
$out = "$scratch\renders\$Subject-$Arm.tif"
$log = "$scratch\renders\$Subject-$Arm.log"

New-Item -ItemType Directory -Force -Path "$scratch\warpmaps", "$scratch\renders" | Out-Null

$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
Write-Output "=== $Subject / $Arm ==="
Write-Output "binary   : $exe"
Write-Output "sha256   : $hash"

# Rule 45: solve the placement ONCE per subject and pin it, so the two arms
# cannot differ through the aligner.
if (-not (Test-Path $wm)) {
    Write-Output "align    : solving $wm"
    Remove-Item Env:STREHL_WARPMAP -ErrorAction SilentlyContinue
    & $exe align $src --out $wm 2>&1 |
        Out-String -Width 200 | Out-File -Encoding utf8 "$scratch\warpmaps\$Subject.log"
    if ($LASTEXITCODE -ne 0) { throw "align failed for $Subject (exit $LASTEXITCODE)" }
}
else {
    Write-Output "align    : reusing $wm"
}

$env:STREHL_WARPMAP = $wm
if ($Knee -eq "") {
    Remove-Item Env:STREHL_HIGHLIGHT_KNEE -ErrorAction SilentlyContinue
    $kneeLabel = "(default, on)"
}
else {
    $env:STREHL_HIGHLIGHT_KNEE = $Knee
    $kneeLabel = $Knee
}
Write-Output "knee     : $kneeLabel"

$sw = [Diagnostics.Stopwatch]::StartNew()
$text = & $exe stack $src --merge pyramid --linear-srgb -o $out 2>&1 | Out-String -Width 200
$code = $LASTEXITCODE
$sw.Stop()
$header = @(
    "invocation : $exe stack $src --merge pyramid --linear-srgb -o $out",
    "sha256     : $hash",
    "STREHL_WARPMAP        = $wm",
    "STREHL_HIGHLIGHT_KNEE = $kneeLabel",
    "exit       : $code   elapsed $([int]$sw.Elapsed.TotalSeconds) s",
    "") -join "`r`n"
($header + $text) | Out-File -Encoding utf8 $log

if ($code -ne 0) {
    Write-Output $text
    throw "render failed for $Subject/$Arm (exit $code)"
}
Select-String -Path $log -Pattern 'merge backend|^wrote|highlight:' |
    ForEach-Object { "banner   : " + $_.Line.Trim() }
Write-Output "outhash  : $((Get-FileHash $out -Algorithm SHA256).Hash)"
Write-Output ""
