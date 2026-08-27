# Recover the merge banner for arms that were rendered without capturing it, and
# verify determinism while doing so.
#
# The sweep renders wrote only the TIFF, so the `averaged` fraction -- which is
# the variable the regime stratification is defined on -- survived only in a
# console transcript. A number transcribed from a transcript has no provenance
# and cannot be re-derived by a reader, so it is re-measured here.
#
# The re-render is not wasted work: it writes to a scratch path and hashes the
# result against the arm that is already on disk. If the two differ, the sweep
# was not reproducible and every number in it is suspect. So this is a
# determinism control that happens to also yield the banner. The scratch file is
# deleted after hashing; only the log is kept.
$ErrorActionPreference = "Stop"
$PIN = "C:\dev\strehl-out\BUILD-GATE\pin\strehl.exe"
$ROOT = "C:\dev\strehl-out\BUILD-GATE\sweep"
$LOGS = "C:\dev\strehl-out\BUILD-GATE\banner"
$SCRATCH = "C:\dev\strehl-out\BUILD-GATE\scratch"
$SRC = "D:\personal\macro"
New-Item -ItemType Directory -Force -Path $LOGS, $SCRATCH | Out-Null

$arms = @(
  @{ name = "G100"; gate = "1.0"; floor = "" },
  @{ name = "G140"; gate = "1.4"; floor = "" },
  @{ name = "G170"; gate = "1.7"; floor = "" },
  @{ name = "G200"; gate = "2.0"; floor = "" },
  @{ name = "G300"; gate = "3.0"; floor = "" },
  @{ name = "G400"; gate = "4.0"; floor = "" },
  @{ name = "WHITE200"; gate = "2.0"; floor = "white" }
)
$subjects = $args
if (-not $subjects) { $subjects = @("coffee-bubbles", "109MSDCF", "119MSDCF") }

$mismatch = 0
foreach ($s in $subjects) {
  foreach ($a in $arms) {
    $have = Join-Path (Join-Path $ROOT $a.name) "$s.tiff"
    $logp = Join-Path $LOGS "$s--$($a.name).log"
    if (-not (Test-Path $have)) { Write-Output "$($a.name)/$s  no arm on disk, skipping"; continue }
    if (Test-Path $logp) { Write-Output "$($a.name)/$s  banner already captured"; continue }
    $tmp = Join-Path $SCRATCH "$s--$($a.name).tiff"
    if ($a.floor) { $env:STREHL_GATE_FLOOR = $a.floor } else { Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue }
    $log = & $PIN stack (Join-Path $SRC $s) --out $tmp --srgb --auto-exposure --merge pyramid --pyramid-gate $a.gate 2>&1
    $log | Set-Content -Path $logp
    $ok = $false
    if (Test-Path $tmp) {
      $ok = ((Get-FileHash $tmp -Algorithm SHA256).Hash -eq (Get-FileHash $have -Algorithm SHA256).Hash)
      Remove-Item $tmp -Force
    }
    if (-not $ok) { $mismatch++ }
    $avg = ("$($log | Select-String -Pattern '^averaged' | Select-Object -First 1)" -replace '\s+', ' ')
    Write-Output ("{0,-9} {1,-22} determinism={2,-5}  {3}" -f $a.name, $s, $ok, $avg)
  }
}
Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue
Write-Output "BANNER CAPTURE COMPLETE  determinism mismatches = $mismatch"
if ($mismatch -gt 0) { exit 1 }
