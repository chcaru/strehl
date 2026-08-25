# run_invariant.ps1 -- render the photometric A/B in M93's UNWARPED grid.
#
# Why this exists. ORCH's patchwork_invariant.py scores a merge against M93's
# single frames at identical (x, y). M116's existing arms cannot be scored that
# way: they carry a frozen warp map, and I measured them displaced (287, -154)
# px from M93's frames -- M120 independently measured NCC(A0, M93-gate4) =
# 0.7136 and refused the same mixture. Scoring M116's A0 against M93 singles
# returns 0.090 against ORCH's 1.114 for the same nominal treatment, which is a
# registration artefact and nothing else.
#
# So these two arms are rendered with STREHL_ALIGN=0 -- the same `alignment :
# OFF` grid M93's armM4 and every armF-f*.tif are logged on -- at the shipped
# DEFAULT_GATE of 4.0, over the full 299-frame stack. Then ORCH's instrument is
# valid on them unmodified.
#
# What is held constant (discipline 832): same capture, same 299 frames, same
# binary at the same pinned SHA, same gate, same unwarped grid, same output
# geometry. The arms differ in `--photometric` and in nothing else.
#
# Writes only to C:\dev\strehl-out\M116\invariant. Never writes to D:.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M116-tree\target\release\strehl.exe"
$LIB  = "D:\personal\macro"          # READ-ONLY
$S    = "bee-3-cpl"
$ROOT = "C:\dev\strehl-out\M116\invariant"
$GATE = 4                             # merge.rs DEFAULT_GATE = 4.0, verified at the pin
$LIMIT = 299                          # the whole stack, as M93 used

New-Item -ItemType Directory -Force -Path $ROOT | Out-Null
$ledger = New-Object System.Collections.ArrayList

function Clear-StrehlEnv {
    foreach ($v in @("STREHL_WARPMAP", "STREHL_ALIGN", "STREHL_PHOTOMETRIC",
                     "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_FIX_HALO",
                     "STREHL_FIX_HALO_DELTA", "STREHL_SMOOTH",
                     "STREHL_SMOOTH_HUBER", "STREHL_DUMP_NEFF",
                     "STREHL_DUMP_ELECTION", "STREHL_DUMP_MERGE_STATE",
                     "STREHL_CACHE_DIR", "STREHL_FREEZE_REQUIRE",
                     "STREHL_CAPTURES")) {
        Remove-Item "env:$v" -ErrorAction SilentlyContinue
    }
}

function Invoke-Arm {
    param([string]$Tag, [string[]]$ExtraArgs, [hashtable]$Env)

    Clear-StrehlEnv
    # A private cache per arm. The warp cache was keyed on capture path alone
    # (corpus fact 1561); arms sharing a cache can serve each other stale state
    # across a configuration change, and an A/B whose arms differ in their cache
    # rather than their treatment looks entirely plausible.
    $cache = Join-Path $ROOT "cache-$Tag"
    New-Item -ItemType Directory -Force -Path $cache | Out-Null
    $env:STREHL_CACHE_DIR = $cache
    $env:STREHL_ALIGN = "0"
    foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }

    $out = Join-Path $ROOT "$S`__$Tag.tif"
    $log = Join-Path $ROOT "$Tag.log"
    $dir = Join-Path $LIB $S
    $args = @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
              "--out", $out) + $ExtraArgs

    $recorded = @{}
    foreach ($v in @("STREHL_ALIGN", "STREHL_PHOTOMETRIC", "STREHL_CACHE_DIR")) {
        $recorded[$v] = [Environment]::GetEnvironmentVariable($v)
    }

    Write-Host "[$Tag] $EXE $($args -join ' ')"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $EXE @args *>&1 | Tee-Object -FilePath $log | Out-Null
    $code = $LASTEXITCODE
    $sw.Stop()

    if ($code -ne 0) { throw "$Tag FAILED with exit $code -- see $log" }
    $hash = (Get-FileHash -Algorithm SHA256 $out).Hash
    [void]$ledger.Add([pscustomobject]@{
        tag = $Tag; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        bytes = (Get-Item $out).Length; sha256 = $hash.Substring(0, 12)
        args = ($ExtraArgs -join " "); envs = ($recorded | ConvertTo-Json -Compress)
    })
    Write-Host "[$Tag] done in $($sw.Elapsed.TotalSeconds.ToString('N1'))s  sha $($hash.Substring(0,12))"
}

# P0: the shipped default path on the unwarped grid. Must reproduce M93's armM4.
Invoke-Arm -Tag "P0-default" -ExtraArgs @() -Env @{}

# P1: the ONLY difference is --photometric. This is ORCH's prediction arm.
Invoke-Arm -Tag "P1-photometric" -ExtraArgs @("--photometric") -Env @{}

# P2: the placebo. Same configuration as P0, different private cache path -- a
# change that cannot affect an image. If P2 differs from P0 by a single byte the
# renderer is not deterministic and every difference below is confounded.
Invoke-Arm -Tag "P2-placebo" -ExtraArgs @() -Env @{}

Clear-StrehlEnv
$ledger | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $ROOT "ledger.json")
$ledger | Format-Table tag, seconds, bytes, sha256, args -AutoSize | Out-String -Width 200
