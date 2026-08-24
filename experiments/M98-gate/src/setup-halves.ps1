# M98 setup: parity-half copies of the corpus stacks.
# D:\personal\macro is READ-ONLY. Every render whose merge could cache a warp
# sidecar (align_cmd.rs:788 writes <dir>\warpmap.txt) operates on a copy under
# C:\dev\strehl-out\M98\frames, never on the corpus directory.
param(
    [Parameter(Mandatory = $true)][string]$Stack,
    [int]$Every = 1
)
$src = "D:\personal\macro\$Stack"
$root = "C:\dev\strehl-out\M98\frames"
$a = Join-Path $root "$Stack-A"
$b = Join-Path $root "$Stack-B"
New-Item -ItemType Directory -Force -Path $a, $b | Out-Null
$files = Get-ChildItem $src -File -Filter *.ARW | Sort-Object Name
$k = 0
$na = 0; $nb = 0
foreach ($f in $files) {
    if ($Every -gt 1 -and ($k % $Every) -ne 0) { $k++; continue }
    $dst = if (($na + $nb) % 2 -eq 0) { $a } else { $b }
    if ($dst -eq $a) { $na++ } else { $nb++ }
    $t = Join-Path $dst $f.Name
    if (-not (Test-Path $t)) { Copy-Item $f.FullName $t }
    $k++
}
Write-Output "$Stack : A=$na  B=$nb  (every=$Every, source frames=$($files.Count))"
