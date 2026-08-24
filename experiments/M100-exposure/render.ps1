# M100 renders: byte-freeze baselines + tuning corpus (binned --srgb).
# READ-ONLY on D:\personal\macro. Outputs to C:\dev\strehl-out\M100.
# strehl writes its whole report to stderr, which PowerShell turns into
# NativeCommandError records under 'Stop'. Continue, and check exit codes.
$ErrorActionPreference = 'Continue'
$root = 'C:\dev\blog\death-of-software\projects\strehl'
$exe = Join-Path $root '.cargo-target-m100\release\strehl.exe'
$out = 'C:\dev\strehl-out\M100'
New-Item -ItemType Directory -Force -Path $out | Out-Null

# --- byte-freeze baselines, limit 60 for speed; the same limit is used after.
& $exe stack D:\personal\macro\bee-3-cpl --limit 60 --srgb --out "$out\freeze-before-srgb.tif" 2>$null
Write-Output "freeze-before-srgb exit $LASTEXITCODE"
& $exe stack D:\personal\macro\bee-3-cpl --limit 60 --srgb --demosaic --out "$out\freeze-before-srgb-demo.tif" 2>$null
Write-Output "freeze-before-srgb-demo exit $LASTEXITCODE"

# --- tuning corpus: binned, --srgb, FULL frame counts.
$stacks = @('bee-3-cpl','bee-2-cpl','lead-1-cpl','flat-on-ruler-cpl','highly-angled-ruler-mm-cpl','coffee-bean','foam')
foreach ($s in $stacks) {
    $dst = "$out\tune-$s-srgb.tif"
    if (Test-Path $dst) { Write-Output "skip $s"; continue }
    Write-Output "=== $s ==="
    & $exe stack "D:\personal\macro\$s" --srgb --out $dst 2>$null
    Write-Output "$s exit $LASTEXITCODE"
}
Write-Output "ALL RENDERS DONE"
