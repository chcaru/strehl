# M116-promotion — campaign 4: lateral chromatic aberration.
#
# Contract: experiments/M116-promotion/prereg-ca.txt, committed at 188b55c
# BEFORE this script rendered anything.
#
# Every arm gets a PRIVATE cache directory (discipline 807 — the warp cache was
# once keyed on capture path alone, so two configurations of one bracket shared
# an entry and were served silently). Every arm gets the same FROZEN warp
# sidecar via STREHL_WARPMAP, which bypasses the cache entirely and makes
# registration bit-identical across arms; CA composes on top of those frozen
# transforms inside `warp_frame_in_place`, so the arms differ in the CA
# composition and in nothing else (prereg S3/S5).
#
# Numbers come from LINEAR renders. sRGB is rendered only for the crops; its
# own --help says "For looking at, NOT for measuring."

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$TREE   = "C:\dev\strehl-out\M116-tree"
$ROOT   = "C:\dev\strehl-out\M116"
$CA     = Join-Path $ROOT "ca"
$LIB    = "D:\personal\macro"                 # READ-ONLY. Never written.
$STREHL = Join-Path $TREE "target\release\strehl.exe"
$PROFILE_KEY = "a7c2-fe100gm-2xtc-x4cpl"      # prereg S1: a KEY, never `1`
$LIMIT  = 100
$GATE   = 4

$SUBJECTS = @("bee-3-cpl", "flat-on-ruler-cpl",
              "tweezers-cpl", "flower-bud-with-background-fern-cpl")

foreach ($d in @("measure", "view", "cache", "logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $CA $d) | Out-Null
}

$ledger = New-Object System.Collections.ArrayList

function Clear-StrehlEnv {
    Get-ChildItem Env: | Where-Object { $_.Name -like "STREHL_*" } |
        ForEach-Object { Remove-Item "Env:$($_.Name)" -ErrorAction SilentlyContinue }
}

function Invoke-Strehl {
    param(
        [string]$Tag, [string]$Subject, [string]$OutFile,
        [hashtable]$UseEnv, [string[]]$StrehlArgs
    )
    Clear-StrehlEnv
    # Private cache per arm. Two arms must never share one.
    $cache = Join-Path $CA "cache\$Subject-$Tag"
    New-Item -ItemType Directory -Force -Path $cache | Out-Null
    $env:STREHL_CACHE_DIR = $cache
    $envRecord = "STREHL_CACHE_DIR=$cache"
    foreach ($k in $UseEnv.Keys) {
        Set-Item "Env:$k" $UseEnv[$k]
        $envRecord += "; $k=$($UseEnv[$k])"
    }

    $log = Join-Path $CA "logs\$Subject`__$Tag.log"
    Write-Output "  [$Subject/$Tag] rendering ..."
    $sw = [Diagnostics.Stopwatch]::StartNew()
    # A native tool writing to stderr under 2>&1 is a terminating error while
    # ErrorActionPreference is Stop. Drop to Continue across the native call
    # only, and capture $LASTEXITCODE immediately.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $stdout = & $STREHL @StrehlArgs 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $sw.Stop()
    $stdout | Out-File -FilePath $log -Encoding utf8

    $hash = ""; $len = 0
    if (Test-Path $OutFile) {
        $hash = (Get-FileHash -Algorithm SHA256 $OutFile).Hash
        $len = (Get-Item $OutFile).Length
    }
    [void]$ledger.Add([pscustomobject]@{
        subject = $Subject; arm = $Tag; exit = $code
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        sha256 = $hash; bytes = $len; cache = $cache; envs = $envRecord
        argv = "strehl " + ($StrehlArgs -join " "); outfile = $OutFile
    })
    Clear-StrehlEnv
    if ($code -ne 0) { throw "$Subject/$Tag FAILED with exit $code -- see $log" }
    return ,$stdout
}

foreach ($S in $SUBJECTS) {
    Write-Output "==================== $S ===================="
    $dir = Join-Path $LIB $S
    $wp = Join-Path $ROOT "warp\$S-l$LIMIT.txt"
    if (-not (Test-Path $wp)) { throw "$S : frozen warp sidecar missing at $wp" }
    $W = @{ STREHL_WARPMAP = $wp }
    $m = { param($t) Join-Path $CA "measure\$S`__$t.tif" }
    $v = { param($t) Join-Path $CA "view\$S`__$t.tif" }

    # ---- A-OFF : the shipped default -------------------------------------
    Invoke-Strehl -Tag "OFF" -Subject $S -OutFile (& $m "OFF") -UseEnv $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "OFF")) | Out-Null

    # ---- CB1 null : the same arm again, cold private cache ---------------
    # Must be byte-identical to A-OFF or every difference below is confounded.
    Invoke-Strehl -Tag "OFF2" -Subject $S -OutFile (& $m "OFF2") -UseEnv $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "OFF2")) | Out-Null

    # ---- A-ON : the profile, by key. A truthy value is refused (S1) -------
    Invoke-Strehl -Tag "ON" -Subject $S -OutFile (& $m "ON") `
        -UseEnv ($W + @{ STREHL_FIX_CA = $PROFILE_KEY }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "ON")) | Out-Null

    # ---- viewing renders: sRGB, ONE frozen exposure across both arms ------
    # The exposure is solved on this OFF view, which is NOT a compared arm,
    # and then passed as a literal so no compared arm can move its own scale.
    $expFile = Join-Path $CA "view\$S`__exposure.txt"
    $stdout = Invoke-Strehl -Tag "VOFF-autoexposure" -Subject $S -OutFile (& $v "OFF") -UseEnv $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--auto-exposure", "--out", (& $v "OFF"))
    $text = ($stdout | Out-String)
    $mt = [regex]::Match($text, '--exposure=(-?[0-9]+(?:\.[0-9]+)?)')
    if (-not $mt.Success) { throw "$S : could not parse the solved exposure" }
    $EXP = $mt.Groups[1].Value
    Set-Content -Path $expFile -Value $EXP
    Write-Output "$S : frozen exposure --exposure=$EXP"

    # Re-render the OFF view at the frozen literal so both views share a scale.
    Invoke-Strehl -Tag "VOFF" -Subject $S -OutFile (& $v "OFF") -UseEnv $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "OFF")) | Out-Null

    Invoke-Strehl -Tag "VON" -Subject $S -OutFile (& $v "ON") `
        -UseEnv ($W + @{ STREHL_FIX_CA = $PROFILE_KEY }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "ON")) | Out-Null

    Write-Output "---- $S done ----"
}

# ---- A-PLACEBO : bee only. Same config as A-OFF, different output path and
# a cache that a DIFFERENT arm has already written to. If the metric moves
# here it is measuring the harness, not the photograph.
$S = "bee-3-cpl"
$dir = Join-Path $LIB $S
$W = @{ STREHL_WARPMAP = (Join-Path $ROOT "warp\$S-l$LIMIT.txt") }
$plac = Join-Path $CA "measure\$S`__PLACEBO.tif"
Clear-StrehlEnv
$env:STREHL_CACHE_DIR = Join-Path $CA "cache\$S-ON"   # deliberately the ON cache
$env:STREHL_WARPMAP = $W.STREHL_WARPMAP
$prev = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$so = & $STREHL stack $dir --limit $LIMIT --gate $GATE --out $plac 2>&1
$code = $LASTEXITCODE
$ErrorActionPreference = $prev
$so | Out-File -FilePath (Join-Path $CA "logs\$S`__PLACEBO.log") -Encoding utf8
[void]$ledger.Add([pscustomobject]@{
    subject = $S; arm = "PLACEBO"; exit = $code; seconds = 0
    sha256 = (Get-FileHash -Algorithm SHA256 $plac).Hash
    bytes = (Get-Item $plac).Length
    cache = $env:STREHL_CACHE_DIR
    envs = "reuses the ON arm's cache on purpose"
    argv = "strehl stack $dir --limit $LIMIT --gate $GATE --out $plac"
    outfile = $plac })
Clear-StrehlEnv
if ($code -ne 0) { throw "PLACEBO failed with exit $code" }

$ledger | Export-Csv -NoTypeInformation -Path (Join-Path $CA "ledger-ca.csv")
$ledger | Format-Table subject, arm, exit, seconds -AutoSize | Out-String -Width 200
Write-Output "CAMPAIGN-CA-DONE"
