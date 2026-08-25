# M122-photometric-promotion — the render campaign driver.
#
# Renders the A0 (default) and A1 (--photometric) arms of every stack in the
# corpus, on a warp map solved ONCE PER SUBJECT and reused by both arms, so
# registration is held constant and the arms differ only in the photometric fit.
#
# Protocol copied from experiments/M116-promotion/run_measure.ps1 so that the
# three shared subjects reproduce M116 byte for byte.
#
# Records, for every output: the full invocation, every environment variable the
# tool reads, the exit code, the SHA-256, the byte count and the wall time
# (AGENTS.md rule 47).
#
# Exit codes are captured into a variable BEFORE any pipeline touches them, and
# no pipeline whose status is later read contains `Select-Object -First`
# (AGENTS.md rules 46 and 47).
#
# NEVER writes to D:\. Every output path is under C:\dev\strehl-out\M122\.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M116-tree\target\release\strehl.exe"
$SHA  = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
$ROOT = "C:\dev\strehl-out\M122"
$LIB  = "D:\personal\macro"
$GATE = 4

foreach ($d in @("warp", "measure", "logs", "cache", "view")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ROOT $d) | Out-Null
}

$ledgerPath = Join-Path $ROOT "ledger-measure.csv"
$ledger = New-Object System.Collections.ArrayList

function Clear-StrehlEnv {
    foreach ($v in @("STREHL_WARPMAP", "STREHL_ALIGN", "STREHL_PHOTOMETRIC",
                     "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_FIX_HALO",
                     "STREHL_FIX_HALO_DELTA", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
                     "STREHL_DUMP_NEFF", "STREHL_DUMP_ELECTION",
                     "STREHL_DUMP_MERGE_STATE", "STREHL_CACHE_DIR",
                     "STREHL_FREEZE_REQUIRE", "STREHL_CAPTURES")) {
        Remove-Item "env:$v" -ErrorAction SilentlyContinue
    }
}

function Invoke-Strehl {
    param(
        [string]   $Tag,
        [string]   $Subject,
        [string[]] $StrehlArgs,
        [string]   $OutFile,
        [hashtable]$Env = @{}
    )

    Clear-StrehlEnv
    foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }

    $envRecord = ($Env.GetEnumerator() | Sort-Object Name |
                  ForEach-Object { "$($_.Name)=$($_.Value)" }) -join " "
    if (-not $envRecord) { $envRecord = "(none set)" }

    $sw   = [Diagnostics.Stopwatch]::StartNew()
    $out  = & $EXE @StrehlArgs 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()

    $log = Join-Path $ROOT "logs\$Subject`__$Tag.log"
    $header = @(
        "# M122 $Subject $Tag",
        "# commit  $SHA",
        "# binary  $EXE",
        "# env     $envRecord",
        "# argv    strehl " + ($StrehlArgs -join " "),
        "# exit    $code",
        "# seconds $([math]::Round($sw.Elapsed.TotalSeconds, 2))",
        ""
    )
    Set-Content -Path $log -Value ($header + ($out | ForEach-Object { "$_" }))

    $hash = ""
    $len  = 0
    if ($OutFile -and (Test-Path $OutFile)) {
        $hash = (Get-FileHash -Algorithm SHA256 $OutFile).Hash
        $len  = (Get-Item $OutFile).Length
    }

    [void]$ledger.Add([pscustomobject]@{
        subject = $Subject
        arm     = $Tag
        exit    = $code
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        sha256  = $hash
        bytes   = $len
        envs    = $envRecord
        argv    = "strehl " + ($StrehlArgs -join " ")
        outfile = $OutFile
    })
    $ledger | Export-Csv -NoTypeInformation -Path $ledgerPath

    Clear-StrehlEnv
    return $code
}

$SUBJECTS = Get-ChildItem $LIB -Directory |
            Where-Object { (Get-ChildItem $_.FullName -File -Force -Filter '*.ARW').Count -gt 0 } |
            Sort-Object Name

foreach ($sd in $SUBJECTS) {
    $S = $sd.Name
    $dir = $sd.FullName
    $n = (Get-ChildItem $dir -File -Force -Filter '*.ARW').Count
    $L = [Math]::Min(100, $n)

    Write-Output "==================== $S  (N=$n, L=$L) ===================="

    $wp = Join-Path $ROOT "warp\$S-l$L.txt"
    $a0 = Join-Path $ROOT "measure\$S`__A0.tif"
    $a1 = Join-Path $ROOT "measure\$S`__A1.tif"

    if (-not (Test-Path $wp)) {
        $c = Invoke-Strehl -Tag "align" -Subject $S -OutFile $wp `
            -Env @{ STREHL_CACHE_DIR = (Join-Path $ROOT "cache") } `
            -StrehlArgs @("align", $dir, "--limit", "$L", "--out", $wp)
        if ($c -ne 0) { Write-Output "  !! $S align FAILED exit $c -- skipping subject"; continue }
    }

    $W = @{ STREHL_WARPMAP = $wp }

    if (-not (Test-Path $a0)) {
        $c = Invoke-Strehl -Tag "A0-default" -Subject $S -OutFile $a0 -Env $W `
            -StrehlArgs @("stack", $dir, "--limit", "$L", "--gate", "$GATE", "--out", $a0)
        if ($c -ne 0) { Write-Output "  !! $S A0 FAILED exit $c -- skipping subject"; continue }
    }

    if (-not (Test-Path $a1)) {
        $c = Invoke-Strehl -Tag "A1-photometric" -Subject $S -OutFile $a1 -Env $W `
            -StrehlArgs @("stack", $dir, "--limit", "$L", "--gate", "$GATE",
                          "--photometric", "--out", $a1)
        if ($c -ne 0) { Write-Output "  !! $S A1 FAILED exit $c -- skipping subject"; continue }
    }

    $h0 = (Get-FileHash -Algorithm SHA256 $a0).Hash
    $h1 = (Get-FileHash -Algorithm SHA256 $a1).Hash
    $ident = if ($h0 -eq $h1) { "IDENTICAL -- PLUMBING NULL" } else { "differ (ok)" }
    Write-Output "  A0 $h0"
    Write-Output "  A1 $h1"
    Write-Output "  bit-identity: $ident"
}

$ledger | Export-Csv -NoTypeInformation -Path $ledgerPath
Write-Output "CAMPAIGN-MEASURE-DONE"
