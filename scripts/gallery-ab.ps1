# gallery-ab.ps1 -- two merge backends, one binary, pictures to judge by eye.
#
# WHAT THIS ANSWERS
# -----------------
# The estimator draws a bright rim and a grey aura around a dark subject on a
# bright ground. The pyramid merge is measured to roughly halve that veil. A
# number is not a picture, and the owner has asked twice to SEE the difference,
# so this renders both arms of every subject from one binary and lays them side
# by side.
#
# THE ONE THING THAT MAKES IT HONEST
# ----------------------------------
# Both arms come from the SAME binary, the same flags, and the same CA profile;
# the ONLY difference is --merge. Anything else and the comparison attributes
# nothing, which is the defect the previous gallery had. The binary's sha256 and
# the git commit go in RUN.txt.
#
# The rim is a few pixels wide, so THE FULL FRAME AT 2400 px IS WHERE THIS
# DEFECT HIDES -- downsampling averages it away. The full frames here are
# context only. The 100% crops are the evidence, they are PNG (JPEG eats exactly
# the artifact we are chasing), and their location is chosen by crops.py's
# silhouette rule on ONE arm and applied unchanged to the other, so neither arm
# can be flattered by its crop site.
#
# A subject whose arm fails is written into the manifest as a failure. A missing
# row must never be readable as a passing row.

[CmdletBinding()]
param(
    [string]$Exe = 'C:\dev\strehl-out\acceptance-pins\e42ab13\target\release\strehl.exe',
    [string]$Sha = 'e42ab13',
    [string]$Library = 'D:\personal\macro',
    [string]$OutDir = 'C:\dev\strehl-out\gallery-ab',
    [string]$FixCa = 'a7c2-fe100gm-2xtc-x4cpl',
    # ORCH named the first five. lavendar-cpl is added because it is the other
    # subject the multi-band work was reported to fix, so it is a second chance
    # for the pyramid to be wrong in public.
    [string[]]$Subjects = @(
        'flower-bud-with-background-fern-cpl',
        'flower-bud-alone-cpl',
        'dry-erase-marker-head-cpl',
        'lavendar-cpl',
        'couch-fibers-cpl',
        'tweezers-cpl'
    )
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path (Join-Path $repo 'Cargo.toml'))) { throw "repo root not found at $repo" }
if (-not (Test-Path $Exe)) { throw "no binary at $Exe" }

# --merge is the ONLY difference. --pyramid-gate is a real flag on this binary
# (verified in `stack --help`, "Multiples of the modelled band-noise power");
# it is refused under --merge estimator rather than ignored, so it can only
# appear on the pyramid arm.
$ARMS = @(
    @{ Name = 'estimator'; Flags = @('--merge', 'estimator') }
    @{ Name = 'pyramid'; Flags = @('--merge', 'pyramid', '--pyramid-gate', '4') }
)
$COMMON = @('--srgb', '--demosaic')

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$tifDir = Join-Path $OutDir '_tiff'
New-Item -ItemType Directory -Force -Path $tifDir | Out-Null

$binHash = (Get-FileHash $Exe -Algorithm SHA256).Hash
Push-Location $repo
$gitSha = (git rev-parse HEAD).Trim()
Pop-Location

# Cleared for the same reason gallery.ps1 clears them: an inherited variable
# would silently re-route a render and the arm label would be a lie. FIX_CA is
# then SET explicitly, because since 96571ee "unset" no longer means "off".
foreach ($v in @('STREHL_ALIGN', 'STREHL_WARPMAP', 'STREHL_FIX_HALO', 'STREHL_EDGE_AWARE',
        'STREHL_ONLY_FRAME', 'STREHL_MERGE', 'STREHL_PYRAMID_WORKERS', 'STREHL_VEIL')) {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
$env:STREHL_FIX_CA = $FixCa

@(
    "strehl A/B merge comparison"
    "started    : $(Get-Date -Format o)"
    "git commit : $gitSha"
    "pin        : $Sha"
    "binary     : $Exe"
    "sha256     : $binHash"
    "library    : $Library  (READ ONLY -- nothing is written there)"
    "common     : $($COMMON -join ' ')"
    "STREHL_FIX_CA : $FixCa"
    ""
    "arm estimator : $($ARMS[0].Flags -join ' ')"
    "arm pyramid   : $($ARMS[1].Flags -join ' ')"
    ""
    "The ONLY difference between the arms is --merge (plus --pyramid-gate,"
    "which the binary REFUSES under --merge estimator rather than ignoring)."
    ""
    "Judge the 100% PNG crops under crops/. The 2400 px full frames are"
    "context: the rim is a few pixels wide and downsampling averages it away."
) | Out-File -Encoding utf8 (Join-Path $OutDir 'RUN.txt')

$manifest = Join-Path $OutDir 'manifest.tsv'
"subject`tarm`tframes`tsecs`texit`tbytes`tstatus" | Out-File -Encoding utf8 $manifest

foreach ($s in $Subjects) {
    $dir = Join-Path $Library $s
    if (-not (Test-Path $dir)) {
        Write-Warning "$s : no such subject"
        "$s`t-`t0`t0`t-1`t0`tNO-SUCH-SUBJECT" | Out-File -Encoding utf8 -Append $manifest
        continue
    }
    $frames = (Get-ChildItem -File $dir | Where-Object { $_.Extension -match '^\.(ARW|arw)$' }).Count

    foreach ($arm in $ARMS) {
        $tif = Join-Path $tifDir "$s--$($arm.Name).tiff"
        $log = Join-Path $tifDir "$s--$($arm.Name).log"
        if ((Test-Path $tif) -and (Get-Item $tif).Length -gt 0) {
            Write-Host "$s [$($arm.Name)] already rendered, skipping"
            "$s`t$($arm.Name)`t$frames`t0`t0`t$((Get-Item $tif).Length)`tskip" |
                Out-File -Encoding utf8 -Append $manifest
            continue
        }
        Write-Host "$s [$($arm.Name)] $frames frames..."
        $argv = @('stack', "`"$dir`"", '--out', "`"$tif`"") + $COMMON + $arm.Flags
        $sw = [Diagnostics.Stopwatch]::StartNew()
        $p = Start-Process -FilePath $Exe -ArgumentList $argv -NoNewWindow -PassThru `
            -RedirectStandardError $log -RedirectStandardOutput "$log.out"
        $null = $p.Handle   # makes ExitCode readable after exit
        $p.WaitForExit()
        $sw.Stop()
        $bytes = if (Test-Path $tif) { (Get-Item $tif).Length } else { 0 }
        $status = if ($p.ExitCode -eq 0 -and $bytes -gt 0) { 'ok' } else { "FAIL($($p.ExitCode))" }
        Write-Host ("    {0} {1:N0}s" -f $status, $sw.Elapsed.TotalSeconds)
        if ($status -ne 'ok') { Get-Content $log -TotalCount 3 | Write-Warning }
        "$s`t$($arm.Name)`t$frames`t$([math]::Round($sw.Elapsed.TotalSeconds,1))`t$($p.ExitCode)`t$bytes`t$status" |
            Out-File -Encoding utf8 -Append $manifest
    }
}

Write-Host ''
Write-Host "renders done. manifest: $manifest"
Get-Content $manifest | Write-Host
Write-Host ''
Write-Host "now run, per subject:"
Write-Host "  python scripts\crops.py $tifDir --subject <S> --ref estimator --out $OutDir\crops\<S> --display none"
