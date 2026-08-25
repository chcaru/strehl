# M116-promotion — the campaign driver.
#
# Runs every arm registered in prereg.txt, on the pinned worktree binary only.
# Records, for every output: the full invocation, every environment variable the
# tool reads, the SHA-256, the byte count and the wall time (AGENTS.md rule 47).
#
# Exit codes are captured into a variable BEFORE any pipeline touches them, and
# no pipeline whose status is later read contains `Select-Object -First`
# (AGENTS.md rules 46 and 47).

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M116-tree\target\release\strehl.exe"
$SHA  = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
$ROOT = "C:\dev\strehl-out\M116"
$LIB  = "D:\personal\macro"

$SUBJECTS = @("bee-3-cpl", "foam", "tweezers-cpl")
$LIMIT    = 100
$GATE     = 4

foreach ($d in @("warp", "measure", "view", "single", "logs", "maps")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ROOT $d) | Out-Null
}

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

# Run one `strehl` invocation, record everything about it, return the log text.
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
        "# M116 $Subject $Tag",
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

    Clear-StrehlEnv
    if ($code -ne 0) { throw "$Subject/$Tag FAILED with exit $code -- see $log" }
    return ,$out
}

foreach ($S in $SUBJECTS) {
    Write-Output "==================== $S ===================="
    $dir = Join-Path $LIB $S
    $wp  = Join-Path $ROOT "warp\$S-l$LIMIT.txt"

    # ---- registration, solved once and frozen for every arm ----------------
    if (-not (Test-Path $wp)) {
        Invoke-Strehl -Tag "align" -Subject $S -OutFile $wp -StrehlArgs @(
            "align", $dir, "--limit", "$LIMIT", "--out", $wp) | Out-Null
    }

    $W = @{ STREHL_WARPMAP = $wp }
    $m = { param($t) Join-Path $ROOT "measure\$S`__$t.tif" }

    # ---- M0: the mask arm, gate 0, not compared ----------------------------
    Invoke-Strehl -Tag "M0-mask-gate0" -Subject $S -OutFile (& $m "M0") -Env $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "0",
                      "--out", (& $m "M0")) | Out-Null

    # ---- A0: the default path, plus the byte-inert election map ------------
    Invoke-Strehl -Tag "A0-default" -Subject $S -OutFile (& $m "A0") -Env $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--index-map", (Join-Path $ROOT "maps\$S`__A0-index.tif"),
                      "--out", (& $m "A0")) | Out-Null

    # ---- the instrument arms -----------------------------------------------
    Invoke-Strehl -Tag "A1-photometric" -Subject $S -OutFile (& $m "A1") -Env $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--photometric", "--out", (& $m "A1")) | Out-Null

    Invoke-Strehl -Tag "A2-softgate-gauss" -Subject $S -OutFile (& $m "A2") `
        -Env ($W + @{ STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "A2")) | Out-Null

    Invoke-Strehl -Tag "A3-softgate-exp" -Subject $S -OutFile (& $m "A3") `
        -Env ($W + @{ STREHL_SOFT_GATE = "exponential" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "A3")) | Out-Null

    Invoke-Strehl -Tag "A4-photo-softgauss" -Subject $S -OutFile (& $m "A4") `
        -Env ($W + @{ STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--photometric", "--out", (& $m "A4")) | Out-Null

    # ---- the controls that must not fire -----------------------------------
    Invoke-Strehl -Tag "P1-placebo" -Subject $S -OutFile (& $m "P1") `
        -Env ($W + @{ STREHL_CACHE_DIR = (Join-Path $ROOT "placebo-cache") }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "P1")) | Out-Null

    Invoke-Strehl -Tag "N1-null" -Subject $S -OutFile (& $m "N1") -Env $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "N1")) | Out-Null

    Invoke-Strehl -Tag "T1-trap-dumpneff" -Subject $S -OutFile (& $m "T1") `
        -Env ($W + @{ STREHL_DUMP_NEFF = (Join-Path $ROOT "maps\$S`__T1-neff.tif") }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "T1")) | Out-Null

    Invoke-Strehl -Tag "T2-trap-softgate0" -Subject $S -OutFile (& $m "T2") `
        -Env ($W + @{ STREHL_SOFT_GATE = "0" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "T2")) | Out-Null

    # ---- section 6: the unaligned pixel-exact M85 pair ----------------------
    $U = @{ STREHL_ALIGN = "0" }
    Invoke-Strehl -Tag "M0u-mask-gate0-noalign" -Subject $S -OutFile (& $m "M0u") -Env $U `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "0",
                      "--out", (& $m "M0u")) | Out-Null

    Invoke-Strehl -Tag "B1u-merge-noalign" -Subject $S -OutFile (& $m "B1u") -Env $U `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "B1u")) | Out-Null

    Write-Output "---- $S measurement arms done ----"
}

$ledger | Export-Csv -NoTypeInformation -Path (Join-Path $ROOT "ledger-measure.csv")
$ledger | Format-Table subject, arm, exit, seconds, bytes, sha256 -AutoSize | Out-String -Width 200
Write-Output "CAMPAIGN-MEASURE-DONE"
