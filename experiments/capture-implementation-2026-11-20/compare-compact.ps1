# Final images for the owner: one capture rendered from its lossless files and from a
# compacted copy (strehl compact, k = 1), with the desktop's render command
# (stack --merge pyramid --srgb, four-shot remosaic). The compacted copy is made of hard
# links to the capture's archives; compact replaces each link with a new file, so the
# capture itself is not written (checked: link counts back to 1, hashes unchanged).
#   pwsh -NoProfile -File compare-compact.ps1 -Run D:/StrehlCaptures/<run> -Scratch C:\strehl-scratch -Out <folder>
param([Parameter(Mandatory)][string]$Run, [Parameter(Mandatory)][string]$Scratch, [Parameter(Mandatory)][string]$Out)
$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\..\.."
$exe = Join-Path $repo 'target\release\strehl.exe'
New-Item -ItemType Directory -Force $Out, $Scratch | Out-Null
$copy = Join-Path (Split-Path $Run -Parent) ('compact-compare-' + (Split-Path $Run -Leaf))
New-Item -ItemType Directory $copy | Out-Null
$files = Get-ChildItem $Run -File
$probe = $files | Where-Object Extension -eq '.straw' | Select-Object -First 3
$before = $probe | ForEach-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash }
foreach ($f in $files) {
    if ($f.Extension -eq '.straw') { New-Item -ItemType HardLink -Path (Join-Path $copy $f.Name) -Target $f.FullName | Out-Null }
    else { Copy-Item $f.FullName (Join-Path $copy $f.Name) }
}
try {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $exe compact $copy --apply --json (Join-Path $Out 'compact.json') *> (Join-Path $Out 'compact.log')
    $code = $LASTEXITCODE
    Write-Output ("compact: exit {0}, {1:n1} s" -f $code, $sw.Elapsed.TotalSeconds)
    if ($code -ne 0) { throw "compact failed" }
    $links = $files | Where-Object Extension -eq '.straw' | ForEach-Object { (fsutil hardlink list $_.FullName | Measure-Object).Count } | Group-Object | ForEach-Object { "$($_.Count) files with $($_.Name) link(s)" }
    Write-Output ("capture's archives after compact: " + ($links -join ', '))
    $after = $probe | ForEach-Object { (Get-FileHash $_.FullName -Algorithm SHA256).Hash }
    Write-Output ("capture's first three archives unchanged: " + (($before -join ',') -eq ($after -join ',')))
    $sizes = foreach ($d in @($Run, $copy)) { '{0:n2} GB' -f ((Get-ChildItem $d -File | Measure-Object Length -Sum).Sum / 1GB) }
    Write-Output ("size: lossless $($sizes[0]), compacted $($sizes[1])")
    $env:STREHL_PIXEL_SHIFT = 'remosaic'
    foreach ($job in @(@{ n = 'lossless'; d = $Run }, @{ n = 'compacted'; d = $copy })) {
        $env:STREHL_CACHE_DIR = Join-Path $Scratch "cache-$($job.n)"
        $tif = Join-Path $Out "$($job.n).tiff"
        $sw = [Diagnostics.Stopwatch]::StartNew()
        & $exe stack $job.d --merge pyramid --srgb --out $tif *> (Join-Path $Out "$($job.n).log")
        $code = $LASTEXITCODE
        Write-Output ("render {0}: exit {1}, {2:n1} s" -f $job.n, $code, $sw.Elapsed.TotalSeconds)
        Remove-Item -Recurse -Force $env:STREHL_CACHE_DIR -ErrorAction SilentlyContinue
        if ($code -ne 0) { throw "render failed" }
    }
} finally {
    Remove-Item -Recurse -Force $copy
}
