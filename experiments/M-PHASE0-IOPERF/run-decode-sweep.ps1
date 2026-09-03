[CmdletBinding()]
param(
    [string]$CaptureDir = 'D:\personal\macro\112MSDCF'
)

$ErrorActionPreference = 'Stop'
$manifest = Join-Path $PSScriptRoot 'Cargo.toml'
$oldRayon = $env:RAYON_NUM_THREADS
$oldCapture = $env:IOPERF_ARW_DIR

$sweeps = @(
    [pscustomobject]@{ Name = 'forward'; Threads = @(1, 2, 4, 8, 16, 32) },
    [pscustomobject]@{ Name = 'reverse'; Threads = @(32, 16, 8, 4, 2, 1) }
)

try {
    $env:IOPERF_ARW_DIR = $CaptureDir
    foreach ($sweep in $sweeps) {
        foreach ($threads in $sweep.Threads) {
            $env:RAYON_NUM_THREADS = [string]$threads
            Write-Output "SWEEP_BEGIN,direction=$($sweep.Name),rayon_threads=$threads,time=$([DateTimeOffset]::Now.ToString('o'))"
            & cargo bench --manifest-path $manifest --bench decode
            if ($LASTEXITCODE -ne 0) {
                throw "decode benchmark failed at $threads threads"
            }
            Write-Output "SWEEP_END,direction=$($sweep.Name),rayon_threads=$threads,time=$([DateTimeOffset]::Now.ToString('o'))"
        }
    }
}
finally {
    $env:RAYON_NUM_THREADS = $oldRayon
    $env:IOPERF_ARW_DIR = $oldCapture
}
