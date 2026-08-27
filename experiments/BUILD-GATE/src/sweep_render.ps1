# Render the gate sweep. One pinned binary, every arm, so the only thing that
# differs between arms is --pyramid-gate.
#
# The k values are not round numbers chosen for tidiness. MergeConfig::gate is
# documented as a false-positive control: the band-energy statistic is a
# smoothed mean of ~13 squared samples and fluctuates by ~39% of its mean under
# pure noise, so gate k sits (k-1)/0.39 standard deviations above the noise
# expectation. The sweep is therefore a sweep in SIGMA:
#
#   k=1.0  0.00 sigma   the gate is exactly the noise floor: maximum selection
#   k=1.4  1.03 sigma
#   k=1.7  1.79 sigma   what the SHIPPING path effectively used before the fix
#                       (2.0 / 1.1787, the measured band-0 floor error)
#   k=2.0  2.56 sigma   TODAY'S NOMINAL DEFAULT -- the labelled baseline arm
#   k=3.0  5.13 sigma
#   k=4.0  7.69 sigma   maximum averaging
#
# k=1.7 is included because it approximates the operating point the product has
# actually been shipping, which is not the same as its nominal one. It is an
# APPROXIMATION and not a reproduction: fact 631 established that rescaling a
# gate does not reproduce another configuration's decisions, and beta is now
# per-frame and per-band while k is global. The arm prices the old operating
# point; it does not recreate it.
$ErrorActionPreference = "Stop"
$PIN = "C:\dev\strehl-out\BUILD-GATE\pin\strehl.exe"
$ROOT = "C:\dev\strehl-out\BUILD-GATE\sweep"
$SRC = "D:\personal\macro"

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

foreach ($s in $subjects) {
  foreach ($a in $arms) {
    $dir = Join-Path $ROOT $a.name
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $out = Join-Path $dir "$s.tiff"
    if (Test-Path $out) { Write-Output "$($a.name)/$s  already rendered, skipping"; continue }
    if ($a.floor) { $env:STREHL_GATE_FLOOR = $a.floor } else { Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $log = & $PIN stack (Join-Path $SRC $s) --out $out --srgb --auto-exposure --merge pyramid --pyramid-gate $a.gate 2>&1
    $sw.Stop()
    $avg = ($log | Select-String -Pattern '^averaged' | Select-Object -First 1)
    $xw = ($log | Select-String -Pattern 'x white' | Select-Object -First 1)
    if (-not (Test-Path $out)) { Write-Output "$($a.name)/$s  RENDER FAILED"; $log | Select-Object -Last 5; continue }
    Write-Output ("{0,-9} {1,-22} {2,6:N1}s  {3}" -f $a.name, $s, $sw.Elapsed.TotalSeconds, ("$avg" -replace '\s+', ' '))
    if ($a.name -eq "G200") { Write-Output ("          {0}" -f ("$xw" -replace '\s+', ' ')) }
  }
}
Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue
Write-Output "SWEEP RENDER COMPLETE"
