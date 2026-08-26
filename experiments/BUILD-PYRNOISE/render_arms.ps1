# BUILD-PYRNOISE -- render every arm through ONE pinned binary.
#
# Constraint 1 of the brief: one binary for every arm. The sha256 is asserted
# here rather than merely recorded, because a cross-build comparison in this
# project is VOID (green-bit-identical builds have moved red by 3902 DN).
#
# Every run's stderr is kept verbatim next to its TIFF. The banner in that file
# -- NOT this script's argv -- is the record of which backend ran. An argv says
# what the caller asked for; only the banner says what the program did.
#
# Usage:  pwsh -File render_arms.ps1 -Subject 109MSDCF [-SingleFrames all|<n>]

param(
    [Parameter(Mandatory = $true)][string]$Subject,
    [string]$SingleFrames = "all",
    [switch]$SkipStacks
)

$ErrorActionPreference = "Stop"

$BIN     = 'C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe'
$BIN_SHA = 'CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6'
$CORPUS  = 'D:\personal\macro'
$OUTROOT = 'C:\dev\strehl-out\BUILD-PYRNOISE'

$actual = (Get-FileHash $BIN -Algorithm SHA256).Hash
if ($actual -ne $BIN_SHA) { throw "BINARY MISMATCH: expected $BIN_SHA got $actual" }
Write-Host "binary sha256 OK: $actual"

$src = Join-Path $CORPUS $Subject
if (-not (Test-Path $src)) { throw "no such subject: $src" }
$dst = Join-Path $OUTROOT "renders\$Subject"
New-Item -ItemType Directory -Force -Path $dst | Out-Null

function Invoke-Arm {
    param([string]$Tag, [string[]]$ArgList, [hashtable]$EnvVars = @{})

    $tif = Join-Path $dst "$Tag.tif"
    $err = Join-Path $dst "$Tag.err"
    $out = Join-Path $dst "$Tag.out"
    if (Test-Path $tif) { Write-Host "  [skip] $Tag (exists)"; return }

    $saved = @{}
    foreach ($k in $EnvVars.Keys) {
        $saved[$k] = [Environment]::GetEnvironmentVariable($k)
        [Environment]::SetEnvironmentVariable($k, $EnvVars[$k])
    }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $BIN @ArgList 1> $out 2> $err
    $rc = $LASTEXITCODE
    $sw.Stop()
    foreach ($k in $EnvVars.Keys) { [Environment]::SetEnvironmentVariable($k, $saved[$k]) }

    # The banner, not the argv, is the record. `stack` prints `merge backend :`;
    # `argmax-baseline` is its own subcommand and names itself on line 1.
    $banner = (Select-String -Path $err -Pattern '^merge backend|^strehl argmax-baseline' | Select-Object -First 1).Line
    Write-Host ("  [{0,4}] {1,-28} {2,7:N1}s   {3}" -f $rc, $Tag, $sw.Elapsed.TotalSeconds, $banner)
    if ($rc -ne 0) { Write-Host ("         REFUSED: " + ((Get-Content $err) -join ' ' | Select-Object -First 1)) }
    "$Tag`trc=$rc`t$($sw.Elapsed.TotalSeconds)" | Add-Content (Join-Path $dst "_timing.tsv")
}

if (-not $SkipStacks) {
    Write-Host "`n== $Subject : stack arms =="

    # The shipping configuration: compiled-in default backend at its compiled-in gate.
    Invoke-Arm 'pyr_default'  @('stack', $src, '--merge', 'pyramid', '-o', "$dst\pyr_default.tif")
    # The configuration README L312/L322 tells users to keep.
    Invoke-Arm 'pyr_g4p5'     @('stack', $src, '--merge', 'pyramid', '--pyramid-gate', '4.5', '-o', "$dst\pyr_g4p5.tif")
    # Tie-back to the existing table's gate-2.0 row.
    Invoke-Arm 'est_g2'       @('stack', $src, '--merge', 'estimator', '--gate', '2', '-o', "$dst\est_g2.tif")
    # The selection reference already in the table.
    Invoke-Arm 'argmax'       @('argmax-baseline', $src, '-o', "$dst\argmax.tif")

    # Registration-free replicas: alignment resamples, and resampling smooths noise.
    # These put every merge arm on the SAME unresampled grid as argmax and the
    # single frames, so the ratio is at genuinely matched pixel sites.
    Invoke-Arm 'pyr_default_noalign' @('stack', $src, '--merge', 'pyramid', '-o', "$dst\pyr_default_noalign.tif") @{ STREHL_ALIGN = '0' }
    Invoke-Arm 'pyr_g4p5_noalign'    @('stack', $src, '--merge', 'pyramid', '--pyramid-gate', '4.5', '-o', "$dst\pyr_g4p5_noalign.tif") @{ STREHL_ALIGN = '0' }
    Invoke-Arm 'est_g2_noalign'      @('stack', $src, '--merge', 'estimator', '--gate', '2', '-o', "$dst\est_g2_noalign.tif") @{ STREHL_ALIGN = '0' }

    # NULL: a bit-identical re-render of the shipping arm. Must read 1.000x.
    Invoke-Arm 'pyr_default_null' @('stack', $src, '--merge', 'pyramid', '-o', "$dst\pyr_default_null.tif")
}

# --- single unstacked frames -------------------------------------------------
# `argmax-baseline --limit 1` over a directory holding exactly one frame is that
# frame, decoded, black-subtracted, white-balanced and binned by the SAME binary
# and the SAME code path as the argmax arm. No alignment, no interpolation.
$frames = Get-ChildItem $src -Filter *.ARW | Sort-Object Name
$idx = @()
if ($SingleFrames -eq "all") {
    $idx = 0..($frames.Count - 1)
} else {
    $n = [int]$SingleFrames
    $idx = 0..($n - 1) | ForEach-Object { [int][Math]::Round($_ * ($frames.Count - 1) / ($n - 1)) }
    $idx = $idx | Sort-Object -Unique
}

Write-Host "`n== $Subject : $($idx.Count) single frames of $($frames.Count) =="
$stage = Join-Path $OUTROOT "stage\$Subject"
foreach ($i in $idx) {
    $f = $frames[$i]
    $tag = "frame{0:d3}" -f $i
    if (Test-Path (Join-Path $dst "$tag.tif")) { Write-Host "  [skip] $tag"; continue }
    if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    Copy-Item $f.FullName $stage
    Invoke-Arm $tag @('argmax-baseline', $stage, '--limit', '1', '-o', "$dst\$tag.tif")
    "$tag`t$($f.Name)" | Add-Content (Join-Path $dst "_frame_map.tsv")
}
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }

Write-Host "`ndone: $dst"
