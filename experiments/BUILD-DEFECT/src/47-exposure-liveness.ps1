# 47-exposure-liveness.ps1 -- do --auto-exposure and --exposure reach pixels?
#
# THE CLAIM UNDER TEST. `scripts/check-defaults.py:1355` asserts, as background
# to its own blind-spot notice, that "--exposure and --auto-exposure reach no
# pixel while the banner announces +2.61 stops (gain 6.105x)". If that is true
# it is a shipping-path defect, because the command that produced all 26
# delivered masters -- and the one printed at the top of the owner's README --
# is
#
#     strehl stack "D:\personal\macro\<subject>" --out <out>.tiff --srgb --auto-exposure
#
# and every provenance record, every A/B and the whole tone-confound defence in
# the head-to-head rests on believing the render's report of what it did.
#
# WHY IT IS BEING RE-MEASURED RATHER THAN CITED. The nearest thing to a source
# for that claim is image_out.rs:76, and reading it shows it says something
# ELSE: that `--exposure`/`--auto-exposure` "claim the binned branch" -- a
# statement about which WRITER is reached, not about whether a gain reaches
# pixels. So the assertion is unsourced. This project has been burned twice in
# one night by treating a second-hand statement as measured: an argv records
# the request, a banner records the claim, and only the pixels record the
# behaviour.
#
# DESIGN -- A POTENT DISTURBANCE, WHICH IS THE ONLY KIND THAT CAN PROVE A NULL.
# A null result is worth nothing unless the input could have moved the output.
# `--exposure` takes STOPS and is documented as "one multiply in linear light"
# (main.rs:219), so +3 stops is a factor of 8 and -3 is a factor of 1/8. If a
# 64x span between arms C and D leaves the bytes identical, the path is dead
# and no subtler test is needed. This is the same shape as the STREHL_RESTORE
# finding, where three gain caps spanning 79% gave byte-identical output.
#
#   A  --srgb --auto-exposure     the shipping command
#   B  --srgb                     no exposure control at all
#   C  --srgb --exposure 3        +3 stops  (8x)
#   D  --srgb --exposure -3       -3 stops  (1/8x)
#   E  --exposure 3               no --srgb: must REFUSE, proving the flag is
#                                 parsed and reaches a decision at all
#
# Arm E is the control that makes a null interpretable, exactly as the bogus
# arm does for an env switch: without it, "all four arms identical" cannot
# distinguish "the gain is never applied" from "the flag never parsed".
#
# VERDICTS ARE COMPUTED, NOT EYEBALLED. Every printed number below is tested,
# because a value that is printed and that nothing conditions on is a defect
# this project has shipped three times.

$ErrorActionPreference = "Continue"

$bin     = "C:\dev\strehl-wt-expo\.cargo-target\release\strehl.exe"
$stack   = "D:\personal\macro\109MSDCF"
$scratch = "C:\dev\strehl-out\BUILD-DEFECT\47-expo"
$limit   = 4

New-Item -ItemType Directory -Force -Path $scratch | Out-Null

function Invoke-Arm {
    param([string]$Name, [string[]]$Flags)

    $out = Join-Path $scratch "$Name.tif"
    $log = Join-Path $scratch "$Name.log"
    Remove-Item $out -ErrorAction SilentlyContinue

    & $bin stack $stack --limit $limit @Flags --out $out *>&1 |
        Tee-Object -FilePath $log | Out-Null
    $code = $LASTEXITCODE

    $hash = "(none)"; $size = 0
    if (Test-Path $out) {
        $hash = (Get-FileHash $out -Algorithm SHA256).Hash
        $size = (Get-Item $out).Length
    }
    $expo = (Select-String -Path $log -Pattern "exposure" |
             ForEach-Object { $_.Line.Trim() }) -join " || "

    [PSCustomObject]@{
        arm = $Name; flags = ($Flags -join " "); exit = $code
        bytes = $size; sha256 = $hash; banner = $expo
    }
}

Write-Host "=== --auto-exposure / --exposure liveness ==="
Write-Host "binary : $bin"
Write-Host "commit : $(git -C C:\dev\strehl-wt-expo rev-parse --short HEAD)"
Write-Host "stack  : $stack (--limit $limit)"
Write-Host ""

$rows = @()
$rows += Invoke-Arm -Name "A-auto"      -Flags @("--srgb", "--auto-exposure")
$rows += Invoke-Arm -Name "B-plain"     -Flags @("--srgb")
$rows += Invoke-Arm -Name "C-plus3"     -Flags @("--srgb", "--exposure", "3")
$rows += Invoke-Arm -Name "D-minus3"    -Flags @("--srgb", "--exposure", "-3")
$rows += Invoke-Arm -Name "E-nosrgb"    -Flags @("--exposure", "3")

$rows | Select-Object arm, flags, exit, bytes, @{n="sha16";e={$_.sha256.Substring(0,[Math]::Min(16,$_.sha256.Length))}} |
    Format-Table -AutoSize | Out-String -Width 130 | Write-Host

Write-Host "--- banners ---"
foreach ($r in $rows) { Write-Host ("{0,-9} : {1}" -f $r.arm, $r.banner) }

Write-Host ""
Write-Host "--- verdicts ---"

$a, $b, $c, $d, $e = $rows

if ($e.exit -eq 0) {
    Write-Host "PARSE    : NOT PROVEN -- --exposure without --srgb was accepted (exit 0)."
    Write-Host "           A null below could mean the flag never parsed."
} else {
    Write-Host "PARSE    : PROVEN -- --exposure without --srgb exits $($e.exit), so the"
    Write-Host "           flag is parsed and reaches a decision. A null below is a"
    Write-Host "           statement about PIXELS, not about parsing."
}

$live = $false
if ($c.sha256 -ne $d.sha256) {
    Write-Host "POTENCY  : +3 stops and -3 stops DIFFER (64x span moved the bytes)."
    Write-Host "           --exposure reaches pixels. The :1355 claim is STALE."
    $live = $true
} else {
    Write-Host "POTENCY  : +3 and -3 stops are BYTE-IDENTICAL across a 64x span."
    Write-Host "           --exposure reaches NO pixel. The :1355 claim is CONFIRMED."
}

if ($a.sha256 -eq $b.sha256) {
    Write-Host "AUTO     : --auto-exposure is byte-identical to passing nothing."
    if ($a.banner) {
        Write-Host "           AND THE BANNER SPOKE ANYWAY -- it announced a gain that no"
        Write-Host "           pixel received. That is the misleading-surface defect."
    }
} else {
    Write-Host "AUTO     : --auto-exposure DIFFERS from passing nothing, so it reaches"
    Write-Host "           pixels on this path."
}

foreach ($r in @($a, $b, $c, $d)) {
    if ($r.exit -ne 0) { Write-Host "WARNING  : arm $($r.arm) exited $($r.exit) -- its hash is not a render" }
}

Write-Host ""
Write-Host "OVERALL  : exposure path is $(if ($live) { 'LIVE' } else { 'DEAD' })"
