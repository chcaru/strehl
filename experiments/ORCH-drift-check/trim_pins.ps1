# Trim the pinned build trees: keep each pin's built binary, drop the build
# intermediates that can be rebuilt from the pinned source.
#
# A byte-freeze is reproduced by RUNNING a pinned binary, not by rebuilding it,
# so target/release/strehl.exe is the load-bearing artifact and the ~0.48 GB of
# incremental/dep/object files behind it is not. The pinned source checkout is
# left alone so a rebuild remains possible.
#
# Banks every pinned binary's SHA256 first, so a pin's identity survives even if
# the binary is later lost.
$ErrorActionPreference = 'Stop'
trap { Write-Host $_.Exception.Message; exit 1 }

$root = 'C:\dev\strehl-out\acceptance-pins'
$outDir = 'C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check'
$out = Join-Path $outDir 'acceptance-pin-binaries.txt'

if (-not (Test-Path $root)) { throw "REFUSING: pin root not found: $root" }

$L = New-Object System.Collections.Generic.List[string]
$L.Add('=== ACCEPTANCE PIN BINARIES')
$L.Add("generated : $(Get-Date -Format o)")
$L.Add("root      : $root")
$L.Add('note      : each pin directory is named for the git commit it was built from.')
$L.Add('            A byte-freeze is reproduced by RUNNING the pinned binary, so the')
$L.Add('            binary is the load-bearing artifact. Build intermediates under')
$L.Add('            target/ were deleted; target/release/strehl.exe was kept, and the')
$L.Add('            pinned source checkout was left intact so a rebuild is possible.')
$L.Add('')

$pins = @(Get-ChildItem $root -Directory | Sort-Object Name)
if ($pins.Count -eq 0) { throw "REFUSING: no pin directories under $root" }

foreach ($pin in $pins) {
  $exe = Join-Path $pin.FullName 'target\release\strehl.exe'
  if (-not (Test-Path $exe)) { throw "REFUSING: pin $($pin.Name) has no target\release\strehl.exe -- trimming would strand it" }
  $h = (Get-FileHash $exe -Algorithm SHA256).Hash
  $L.Add(("  pin {0,-10}  sha256 {1}  {2,10} bytes" -f $pin.Name, $h, (Get-Item $exe).Length))
}
$L.Add('')
$L.Add("pins indexed : $($pins.Count)")
Set-Content -Path $out -Value ($L -join "`n") -Encoding utf8

$check = Get-Content $out -Raw
if ($check.Length -lt 200) { throw "REFUSING: index re-read is only $($check.Length) bytes" }
Write-Host "BANKED $out  ($($pins.Count) pins)"

$before = (Get-ChildItem $root -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum

foreach ($pin in $pins) {
  $tgt = Join-Path $pin.FullName 'target'
  if (-not (Test-Path $tgt)) { continue }
  $keep = (Resolve-Path (Join-Path $pin.FullName 'target\release\strehl.exe')).Path
  Get-ChildItem $tgt -Recurse -File -EA SilentlyContinue | Where-Object { $_.FullName -ne $keep } | Remove-Item -Force -EA SilentlyContinue
  Get-ChildItem $tgt -Recurse -Directory -EA SilentlyContinue | Sort-Object { $_.FullName.Length } -Descending | ForEach-Object {
    if (-not (Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue)) { Remove-Item $_.FullName -Force -Recurse -EA SilentlyContinue }
  }
}

$after = (Get-ChildItem $root -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host ("TRIMMED acceptance-pins: {0:N2} GB -> {1:N2} GB   reclaimed {2:N2} GB" -f ($before / 1GB), ($after / 1GB), (($before - $after) / 1GB))

$stranded = 0
foreach ($pin in $pins) {
  if (-not (Test-Path (Join-Path $pin.FullName 'target\release\strehl.exe'))) { Write-Host "STRANDED: $($pin.Name)"; $stranded++ }
}
if ($stranded -gt 0) { throw "FATAL: $stranded pin(s) lost their binary" }
Write-Host "all $($pins.Count) pin binaries still present"
