# G0 REMEDIATION -- the confound bar failed, so the comparison is re-run pinned.
#
# --auto-exposure chose a DIFFERENT gain per arm: +1.54 / +1.53 / +1.51 / +1.49
# stops (gate 4.00 / 2.00 / 0.7078 / 0.00). That is a 0.05-stop spread, ~3.5% in
# brightness. Small -- but I registered G0 before the run precisely because a
# brightness difference biases a by-eye sharpness judgement and directly
# corrupts the G5 flat-ROI noise measurement. The bar failed; it is honoured.
#
# WHY THE DRIFT IS ITSELF INFORMATIVE (and not a bug): --auto-exposure puts the
# 99.9th percentile of linear-sRGB luminance at 0.90. A lower gate averages
# fewer frames, so the noise is higher, so the 99.9th percentile sits higher,
# so less gain is needed. The exposure drift IS the noise change, seen through
# the auto-exposure rule. It is a free, independent corroboration of G5.
#
# PIN: --exposure=1.54, the control arm's own chosen value. The tool states
# "reproduce this exact file with --exposure=1.54", so the gate-4.00 arm gives
# a SECOND validity check for free:
#
#   G1b  the pinned gate-4.00 arm must STILL hash
#        E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112
#        If --exposure=1.54 does not reproduce what --auto-exposure produced at
#        +1.54 stops, the tool's own reproduction instruction is wrong, and
#        that is a defect worth more than this experiment.

$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

$exe   = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-orch\release\strehl.exe"
$stack = "D:\personal\macro\bee-3-cpl"
$car   = "C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom-warpmap.txt"
$out   = "C:\dev\strehl-out\ORCH-gate"

$CONTROL_HASH = "E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112"
$PIN = "1.54"

$gates = @("4.00", "2.00", "0.7078", "0.00")

foreach ($g in $gates) {
    $tif = "$out\pin-bee-3-cpl-gate-$g.tif"
    if (Test-Path $tif) { Write-Output "SKIP gate-$g (exists)"; continue }

    $env:STREHL_WARPMAP = $car
    $t0  = Get-Date
    $log = & $exe stack $stack --gate $g --srgb --exposure=$PIN --out $tif 2>&1
    $code = $LASTEXITCODE
    Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
    $secs = ((Get-Date) - $t0).TotalSeconds

    $log | Out-File -FilePath "$out\pin-bee-3-cpl-gate-$g.log" -Encoding utf8
    $ovr = ($log | Select-String -Pattern "sidecar-override").Count
    $h   = (Get-FileHash $tif -Algorithm SHA256).Hash
    Write-Output "gate-$g  exit=$code  override=$ovr  $([math]::Round($secs,1))s  $h"
}

Write-Output ""
Write-Output "=== G1b  PINNED CONTROL (does --exposure=1.54 reproduce --auto-exposure +1.54?) ==="
$h4 = (Get-FileHash "$out\pin-bee-3-cpl-gate-4.00.tif" -Algorithm SHA256).Hash
if ($h4 -eq $CONTROL_HASH) { Write-Output "G1b PASS  $h4  -- the tool's reproduction instruction is exact" }
else { Write-Output "G1b FAIL  got $h4  want $CONTROL_HASH  -- DEFECT in --exposure reproduction" }

Write-Output ""
Write-Output "=== G2b  RESPONSIVENESS (pinned) ==="
$hs = @{}
foreach ($g in $gates) { $hs[$g] = (Get-FileHash "$out\pin-bee-3-cpl-gate-$g.tif" -Algorithm SHA256).Hash }
$n = ($hs.Values | Sort-Object -Unique).Count
Write-Output "distinct: $n of $($hs.Count)"
$hs.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Output "  $($_.Key)  $($_.Value)" }
