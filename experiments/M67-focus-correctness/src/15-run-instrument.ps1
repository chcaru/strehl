# M67 -- run the instrument over every rendered plant.
#
# Each plant gets its own log under out/.  Skips plants whose log already
# exists so the sweep can be resumed, and runs the mirrored-truth negative
# control on the headline cell's first seed.
#
#   $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
#   powershell -File src\15-run-instrument.ps1

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent (Split-Path -Parent $root)
$exe = Join-Path $repo 'target\release\examples\m67-focus-correctness.exe'
$plants = Join-Path $root 'plants'
$out = Join-Path $root 'out'
New-Item -ItemType Directory -Force -Path $out | Out-Null

if (-not (Test-Path $exe)) { throw "instrument not built: $exe" }

$metas = Get-ChildItem (Join-Path $plants '*.meta.txt') | Sort-Object Name
Write-Host "$($metas.Count) plants"
foreach ($m in $metas) {
    $name = $m.Name -replace '\.meta\.txt$', ''
    $log = Join-Path $out "$name.log"
    if (Test-Path $log) { Write-Host "$name  (log exists, skipping)"; continue }
    $prefix = Join-Path $plants $name
    $t = [Diagnostics.Stopwatch]::StartNew()
    & $exe $prefix *>&1 | Tee-Object -FilePath $log | Out-Null
    Write-Host ("{0,-46} {1,6:N0}s" -f $name, $t.Elapsed.TotalSeconds)
}

# The instrument's own negative control, on the headline cell.
$head = $metas | Where-Object { $_.Name -like '*s1024*seed1*' } | Select-Object -First 1
if ($head) {
    $name = $head.Name -replace '\.meta\.txt$', ''
    $log = Join-Path $out "$name.MIRROR.log"
    if (-not (Test-Path $log)) {
        & $exe (Join-Path $plants $name) --truth-mirror *>&1 |
            Tee-Object -FilePath $log | Out-Null
        Write-Host "$name  mirrored-truth control written"
    }
}
Write-Host 'done'
