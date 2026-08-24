# M97: end-to-end proof that `strehl align` no longer writes into the owner's
# read-only capture corpus.
#
# Discipline 598: a null is only a null if the probe that reported it can be
# shown to fire. Three bars, all pre-registered:
#
#   A (null)     no new *.txt appears anywhere under D:\personal\macro
#   B (positive) the solve DID write a sidecar, in the cache, and it loads
#   C (plant)    the same scanner, pointed at a directory that does contain a
#                warpmap.txt, reports it -- so bar A is not a dead probe
#
# A run that satisfies A alone is indistinguishable from a solve that crashed
# before it would have written anything. B is what makes A mean something.

$ErrorActionPreference = "Continue"
$corpus = "D:\personal\macro"
$stack  = "$corpus\coffee-bubbles"
$cache  = "C:\dev\strehl-out\M97\cache"
$plant  = "C:\dev\strehl-out\M97\plantdir"
$exe    = "C:\dev\strehl-target-m97\release\strehl.exe"

function Scan([string]$root) {
    if (-not (Test-Path $root)) { return @() }
    @(Get-ChildItem $root -Recurse -File -Filter *.txt -ErrorAction SilentlyContinue |
        ForEach-Object { $_.FullName })
}

Write-Output "=== BEFORE ==="
$before = Scan $corpus
Write-Output "corpus .txt files: $($before.Count)"
$before | ForEach-Object { Write-Output "  $_" }

if (Test-Path $cache) { Remove-Item $cache -Recurse -Force }
$env:STREHL_CACHE_DIR = $cache

Write-Output ""
Write-Output "=== RUN: strehl align $stack ==="
$sw = [Diagnostics.Stopwatch]::StartNew()
& $exe align $stack 2>&1 | Select-Object -Last 12 | ForEach-Object { Write-Output "  $_" }
$rc = $LASTEXITCODE
$sw.Stop()
Write-Output "  rc=$rc  elapsed=$([math]::Round($sw.Elapsed.TotalSeconds,2))s"

Write-Output ""
Write-Output "=== AFTER ==="
$after = Scan $corpus
Write-Output "corpus .txt files: $($after.Count)"
$new = @($after | Where-Object { $before -notcontains $_ })
Write-Output "NEW files in corpus: $($new.Count)"
$new | ForEach-Object { Write-Output "  NEW $_" }

Write-Output ""
Write-Output "=== BAR B: did the write path actually execute? ==="
$made = @(Scan $cache)
Write-Output "cache files: $($made.Count)"
foreach ($f in $made) {
    $sz = (Get-Item $f).Length
    $hd = (Get-Content $f -TotalCount 4) -join " | "
    Write-Output "  $f  ($sz bytes)"
    Write-Output "    head: $hd"
    $tail = (Get-Content $f -Tail 1)
    Write-Output "    tail: $tail"
}

Write-Output ""
Write-Output "=== BAR C: plant -- can the scanner see a corpus write at all? ==="
if (Test-Path $plant) { Remove-Item $plant -Recurse -Force }
New-Item -ItemType Directory -Path $plant -Force | Out-Null
Set-Content -Path "$plant\warpmap.txt" -Value "planted"
$seen = @(Scan $plant)
Write-Output "planted dir .txt files seen by the same scanner: $($seen.Count)"
$seen | ForEach-Object { Write-Output "  $_" }
Remove-Item $plant -Recurse -Force

Write-Output ""
Write-Output "=== VERDICT ==="
$aPass = ($new.Count -eq 0)
$bPass = ($made.Count -ge 1) -and ($rc -eq 0)
$cPass = ($seen.Count -eq 1)
Write-Output "A null      (no new corpus .txt): $(if($aPass){'PASS'}else{'FAIL'})"
Write-Output "B positive  (sidecar written to cache, rc=0): $(if($bPass){'PASS'}else{'FAIL'})"
Write-Output "C plant     (scanner fires on a real write):  $(if($cPass){'PASS'}else{'FAIL'})"
if ($aPass -and $bPass -and $cPass) { Write-Output "OVERALL: PASS" } else { Write-Output "OVERALL: FAIL" }
