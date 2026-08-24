# M97: B2 round-trip, done properly, with the plant my first attempt lacked.
#
# My first run reported "C binned PASS / D demosaiced PASS" -- four identical
# hashes. That was half a dead probe: at current HEAD `--srgb` alone already
# reports "7032 x 4688, Malvar-He-Cutler demosaic", so `--demosaic` adds
# nothing and C and D were the SAME path run twice.
#
# So: one real viewing path, and a plant that proves the comparison can fail.
#
#   R1  --srgb                    baseline
#   R2  --srgb --exposure 0       must be BIT-IDENTICAL to R1   (M100 B2)
#   R3  --srgb --exposure 0.5     must DIFFER from R1           (the plant)
#   R4  --demosaic (no --srgb)    does the flag do anything alone?
#   R5  default                   reference for R4
#
# R3 is the whole point: without it, R1 == R2 is equally consistent with the
# exposure flag being ignored entirely.

$ErrorActionPreference = "Continue"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\bee-3-cpl"
$out = "C:\dev\strehl-out\M97\freeze"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"
Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue

function Go($tag, $extra) {
    $f = "$out\rt-$tag.tif"
    if (Test-Path $f) { Remove-Item $f -Force }
    $a = @($dir, "--limit", "60", "--out", $f) + $extra
    $line = (& $exe stack @a 2>&1 | Select-String -Pattern 'wrote\s+:') -join " "
    if (-not (Test-Path $f)) { return @{h="NO-OUTPUT"; d=""} }
    $dim = ""
    if ($line -match '\((\d+ x \d+[^)]*)\)') { $dim = $Matches[1] }
    return @{ h=(Get-FileHash $f -Algorithm SHA256).Hash; d=$dim }
}

$R1 = Go "1-srgb"     @("--srgb")
$R2 = Go "2-srgb-e0"  @("--srgb","--exposure","0")
$R3 = Go "3-srgb-e05" @("--srgb","--exposure","0.5")
$R4 = Go "4-demonly"  @("--demosaic")
$R5 = Go "5-default"  @()

Write-Output "R1 --srgb             : $($R1.h)"
Write-Output "   dims               : $($R1.d)"
Write-Output "R2 --srgb --exposure 0: $($R2.h)"
Write-Output "R3 --srgb --exposure .5: $($R3.h)"
Write-Output "R4 --demosaic alone   : $($R4.h)"
Write-Output "   dims               : $($R4.d)"
Write-Output "R5 default            : $($R5.h)"
Write-Output "   dims               : $($R5.d)"
Write-Output ""
Write-Output "=== VERDICT ==="
Write-Output "B2 round trip (R1 == R2)      : $(if($R1.h -eq $R2.h){'PASS bit-identical'}else{'FAIL'})"
Write-Output "PLANT  (R3 != R1)             : $(if($R3.h -ne $R1.h){'PASS -- the probe CAN see an exposure change'}else{'FAIL -- probe is dead, R1==R2 proves nothing'})"
Write-Output "--demosaic alone is a no-op   : $(if($R4.h -eq $R5.h){'YES -- identical to default'}else{'no -- it changes the output'})"
