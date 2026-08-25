# Render a through-focus ladder of SINGLE frames (no election at all).
#
# The point: a veil is a property of the FRAME. If a near-edge background pixel
# is veiled by the defocused subject, its brightness must move as focus sweeps.
# Illumination, a contact shadow and estimator overshoot are all frame-invariant
# in the background, so this separates them without any gradient statistic.
$ErrorActionPreference = "Stop"
$exe = "C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe"
$out = "C:\dev\strehl-out\VEIL"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$h = (Get-FileHash $exe -Algorithm SHA256).Hash
Write-Output "binary sha256 : $h"
Write-Output "binary        : $exe"

$frames = @(0, 50, 100, 150, 200, 250, 298)
$subjects = @("lavendar-cpl", "flower-bud-with-background-fern-cpl")

foreach ($s in $subjects) {
  foreach ($f in $frames) {
    $tif = Join-Path $out ("{0}-f{1:d3}.tif" -f $s, $f)
    if (Test-Path $tif) { Write-Output "skip  $([IO.Path]::GetFileName($tif))"; continue }
    $env:STREHL_ONLY_FRAME = "$f"
    Remove-Item Env:STREHL_EDGE_AWARE -ErrorAction SilentlyContinue
    $sw = [Diagnostics.Stopwatch]::StartNew()
    # The engine writes its diagnostic banner to stderr. Under
    # ErrorActionPreference=Stop PowerShell turns that into a terminating
    # NativeCommandError, so drop to Continue and judge by the exit code.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $exe stack "D:\personal\macro\$s" --out $tif 2>$null | Out-Null
    $rc = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($rc -ne 0) { throw "render failed: $s f$f (rc=$rc)" }
    $sw.Stop()
    Write-Output ("done  {0}  {1:n1}s" -f [IO.Path]::GetFileName($tif), $sw.Elapsed.TotalSeconds)
  }
}
Remove-Item Env:STREHL_ONLY_FRAME -ErrorAction SilentlyContinue
Write-Output "ladder complete"
