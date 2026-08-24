# M97: does a STALE binary still pollute a capture directory?
#
# The corpus now scans clean at 0 strays and the relocate is in HEAD (8118dd7,
# 10:32). But a source fix reaches an agent only when that agent REBUILDS, and
# 10 of 13 strehl.exe builds in this tree predate 10:32.
#
# If that is right it explains fact 1390 -- sweeps did not lower the stray rate
# because stale binaries kept recreating the files behind the sweep.
#
# Tested on a SCRATCH COPY of a few frames under C:\dev\strehl-out\M97\.
# D:\personal\macro is read-only and is only ever read from; deliberately
# polluting it to prove a point would be the very thing being fixed.
#
#   STALE  : an older agent's binary, run on the scratch dir
#   FIXED  : my post-10:32 binary, run on the same scratch dir
#
# Bar: STALE writes scratch\warpmap.txt, FIXED does not. If STALE also writes
# nothing, the timestamp inference is wrong and I withdraw the claim.

$ErrorActionPreference = "Continue"
$src    = "D:\personal\macro\coffee-bubbles"
$scratch= "C:\dev\strehl-out\M97\stalecheck\coffee-bubbles"
$STALE  = "C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m103\release\strehl.exe"
$FIXED  = "C:\dev\strehl-target-m97\release\strehl.exe"

if (Test-Path (Split-Path $scratch)) { Remove-Item (Split-Path $scratch) -Recurse -Force }
New-Item -ItemType Directory -Force -Path $scratch | Out-Null
Get-ChildItem $src -Filter *.ARW | Select-Object -First 10 |
    ForEach-Object { Copy-Item $_.FullName $scratch }
Write-Output "scratch: $((Get-ChildItem $scratch -Filter *.ARW).Count) frames copied"
Write-Output "STALE binary: $((Get-Item $STALE).LastWriteTime.ToString('MM-dd HH:mm'))"
Write-Output "FIXED binary: $((Get-Item $FIXED).LastWriteTime.ToString('MM-dd HH:mm'))"
Write-Output ""

function Strays { @(Get-ChildItem $scratch -Filter *.txt -ErrorAction SilentlyContinue).Count }

$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"

Write-Output "=== ARM 1: STALE binary (.cargo-target-m103, pre-fix) ==="
Get-ChildItem $scratch -Filter *.txt -ErrorAction SilentlyContinue | Remove-Item -Force
& $STALE align $scratch 2>&1 | Select-Object -Last 3 | ForEach-Object { "    $_" }
$a1 = Strays
Write-Output "  .txt files left in the capture dir: $a1"
Get-ChildItem $scratch -Filter *.txt -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Output "    STRAY $($_.Name) ($($_.Length) b)" }

Write-Output ""
Write-Output "=== ARM 2: FIXED binary (post-8118dd7) ==="
Get-ChildItem $scratch -Filter *.txt -ErrorAction SilentlyContinue | Remove-Item -Force
& $FIXED align $scratch 2>&1 | Select-Object -Last 3 | ForEach-Object { "    $_" }
$a2 = Strays
Write-Output "  .txt files left in the capture dir: $a2"

Write-Output ""
Write-Output "=== VERDICT ==="
Write-Output "STALE wrote into the capture dir : $(if($a1 -ge 1){'YES'}else{'no'})"
Write-Output "FIXED wrote into the capture dir : $(if($a2 -ge 1){'YES'}else{'no'})"
if ($a1 -ge 1 -and $a2 -eq 0) {
    Write-Output "CONFIRMED: the fix works, and every pre-10:32 binary still pollutes."
    Write-Output "           Sweeping cannot win while those binaries are in use."
} elseif ($a1 -eq 0) {
    Write-Output "WITHDRAWN: the stale binary did not pollute either. The timestamp"
    Write-Output "           inference is wrong and I retract the claim."
} else {
    Write-Output "ALARM: the FIXED binary polluted. The relocate is not working."
}
Remove-Item (Split-Path $scratch) -Recurse -Force -ErrorAction SilentlyContinue
