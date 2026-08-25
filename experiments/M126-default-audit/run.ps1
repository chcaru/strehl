# M126-default-audit — the campaign driver.
#
# Runs every arm registered in PREREG.md section 4, on the pinned worktree
# binary only. Records, for every output: the full invocation, every environment
# variable the tool reads, the SHA-256, the byte count and the wall time
# (AGENTS.md rule 47).
#
# Exit codes are captured into a variable BEFORE any pipeline touches them, and
# no pipeline whose status is later read contains `Select-Object -First`
# (AGENTS.md rules 46 and 47).
#
# `STREHL_WARPMAP` is set on every aligned arm so nothing in this campaign can
# read or cache over the shared sidecar inside the read-only capture library
# (rule 45). D:\ is never written.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M126\target\release\strehl.exe"
$SHA  = "d5ba764de26fd9addd01c167c8d0f6c465f25fb4"
$ROOT = "C:\dev\strehl-out\M126"
$LIB  = "D:\personal\macro"

$SUBJECTS = @("bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl")
$LIMIT    = 100
$GATE     = 4
$CAKEY    = "a7c2-fe100gm-2xtc-x4cpl"
$LAMBDA   = "1"

foreach ($d in @("warp", "measure", "single", "logs", "maps")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ROOT $d) | Out-Null
}

$ledgerPath = Join-Path $ROOT "ledger.csv"
$ledger = New-Object System.Collections.ArrayList

$STREHL_VARS = @("STREHL_WARPMAP", "STREHL_ALIGN", "STREHL_PHOTOMETRIC",
                 "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_FIX_HALO",
                 "STREHL_FIX_HALO_DELTA", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
                 "STREHL_ROBUST_ELECTION", "STREHL_DUMP_NEFF", "STREHL_DUMP_ELECTION",
                 "STREHL_DUMP_MERGE_STATE", "STREHL_CACHE_DIR",
                 "STREHL_FREEZE_REQUIRE", "STREHL_CAPTURES")

function Clear-StrehlEnv {
    foreach ($v in $STREHL_VARS) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
}

function Invoke-Strehl {
    param(
        [string]   $Tag,
        [string]   $Subject,
        [string[]] $StrehlArgs,
        [string]   $OutFile,
        [hashtable]$Env = @{},
        [switch]   $Force
    )

    if ($OutFile -and (Test-Path $OutFile) -and -not $Force) {
        Write-Output "  $Subject/$Tag  (already rendered, skipping)"
        $h = (Get-FileHash -Algorithm SHA256 $OutFile).Hash
        [void]$ledger.Add([pscustomobject]@{
            subject = $Subject; arm = $Tag; exit = 0; seconds = 0
            sha256 = $h; bytes = (Get-Item $OutFile).Length
            envs = "(cached)"; argv = "strehl " + ($StrehlArgs -join " ")
            outfile = $OutFile; starved = ""; chunk = ""
        })
        return
    }

    Clear-StrehlEnv
    foreach ($k in $Env.Keys) { Set-Item "env:$k" $Env[$k] }

    $envRecord = ($Env.GetEnumerator() | Sort-Object Name |
                  ForEach-Object { "$($_.Name)=$($_.Value)" }) -join " "
    if (-not $envRecord) { $envRecord = "(none set)" }

    $sw   = [Diagnostics.Stopwatch]::StartNew()
    $out  = & $EXE @StrehlArgs 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()

    $text = ($out | ForEach-Object { "$_" })

    # The worker plan and the robust ring's starvation count, pulled out of the
    # log so they land in the ledger beside the number they qualify
    # (merge.rs:554 requires the starved count beside any claim about the gate).
    $chunk   = ""
    $starved = ""
    foreach ($line in $text) {
        if ($line -match 'workers\s+:\s+(\d+) chunks of <= (\d+) frames') {
            $chunk = "$($Matches[1])x$($Matches[2])"
        }
        if ($line -match '(?i)starv\w*\s*[:=]?\s*(\d+)') { $starved = $Matches[1] }
    }

    $log = Join-Path $ROOT "logs\$Subject`__$Tag.log"
    $header = @(
        "# M126 $Subject $Tag",
        "# commit  $SHA",
        "# binary  $EXE",
        "# env     $envRecord",
        "# argv    strehl " + ($StrehlArgs -join " "),
        "# exit    $code",
        "# seconds $([math]::Round($sw.Elapsed.TotalSeconds, 2))",
        ""
    )
    Set-Content -Path $log -Value ($header + $text)

    $hash = ""
    $len  = 0
    if ($OutFile -and (Test-Path $OutFile)) {
        $hash = (Get-FileHash -Algorithm SHA256 $OutFile).Hash
        $len  = (Get-Item $OutFile).Length
    }

    [void]$ledger.Add([pscustomobject]@{
        subject = $Subject; arm = $Tag; exit = $code
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        sha256  = $hash; bytes = $len
        envs    = $envRecord; argv = "strehl " + ($StrehlArgs -join " ")
        outfile = $OutFile; starved = $starved; chunk = $chunk
    })

    Clear-StrehlEnv
    if ($code -ne 0) { throw "$Subject/$Tag FAILED with exit $code -- see $log" }
    Write-Output ("  {0,-22} {1,6:N1}s  {2}" -f $Tag, $sw.Elapsed.TotalSeconds, $hash.Substring(0, 12))
}

foreach ($S in $SUBJECTS) {
    Write-Output "==================== $S ===================="
    $dir = Join-Path $LIB $S
    $w0  = Join-Path $ROOT "warp\$S-l$LIMIT-free.txt"
    $w1  = Join-Path $ROOT "warp\$S-l$LIMIT-smooth$LAMBDA.txt"

    # ---- registration: two solves, frozen for every arm that reads them -----
    if (-not (Test-Path $w0)) {
        Invoke-Strehl -Tag "align-W0-free" -Subject $S -OutFile $w0 -StrehlArgs @(
            "align", $dir, "--limit", "$LIMIT", "--out", $w0)
    }
    if (-not (Test-Path $w1)) {
        Invoke-Strehl -Tag "align-W1-smooth" -Subject $S -OutFile $w1 `
            -Env @{ STREHL_SMOOTH = $LAMBDA } -StrehlArgs @(
            "align", $dir, "--limit", "$LIMIT", "--out", $w1)
    }

    $W0 = @{ STREHL_WARPMAP = $w0 }
    $W1 = @{ STREHL_WARPMAP = $w1 }
    $m  = { param($t) Join-Path $ROOT "measure\$S`__$t.tif" }

    $base = @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE")

    # ---- the mask arm, gate 0, never compared ------------------------------
    Invoke-Strehl -Tag "M0" -Subject $S -OutFile (& $m "M0") -Env $W0 `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "0", "--out", (& $m "M0"))

    # ---- A0: the current default. Carries the byte-inert election map. -----
    Invoke-Strehl -Tag "A0" -Subject $S -OutFile (& $m "A0") -Env $W0 `
        -StrehlArgs ($base + @("--index-map", (Join-Path $ROOT "maps\$S`__A0-index.tif"),
                               "--out", (& $m "A0")))

    # ---- N1: A0 without the map. Rule 26's byte-inertness proof. -----------
    Invoke-Strehl -Tag "N1" -Subject $S -OutFile (& $m "N1") -Env $W0 `
        -StrehlArgs ($base + @("--out", (& $m "N1")))

    # ---- each gate alone ---------------------------------------------------
    Invoke-Strehl -Tag "G1-ca" -Subject $S -OutFile (& $m "G1") `
        -Env ($W0 + @{ STREHL_FIX_CA = $CAKEY }) `
        -StrehlArgs ($base + @("--out", (& $m "G1")))

    Invoke-Strehl -Tag "G2-robust" -Subject $S -OutFile (& $m "G2") `
        -Env ($W0 + @{ STREHL_ROBUST_ELECTION = "soft" }) `
        -StrehlArgs ($base + @("--out", (& $m "G2")))

    Invoke-Strehl -Tag "G3-smooth" -Subject $S -OutFile (& $m "G3") -Env $W1 `
        -StrehlArgs ($base + @("--out", (& $m "G3")))

    Invoke-Strehl -Tag "G4-softgate" -Subject $S -OutFile (& $m "G4") `
        -Env ($W0 + @{ STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs ($base + @("--out", (& $m "G4")))

    Invoke-Strehl -Tag "G5-photometric" -Subject $S -OutFile (& $m "G5") -Env $W0 `
        -StrehlArgs ($base + @("--photometric", "--out", (& $m "G5")))

    Invoke-Strehl -Tag "G6-halo" -Subject $S -OutFile (& $m "G6") `
        -Env ($W0 + @{ STREHL_FIX_HALO = "1" }) `
        -StrehlArgs ($base + @("--out", (& $m "G6")))

    # ---- all on, and drop-one-out from all on ------------------------------
    $allEnv = $W1 + @{ STREHL_FIX_CA = $CAKEY; STREHL_ROBUST_ELECTION = "soft";
                       STREHL_SOFT_GATE = "gaussian" }
    Invoke-Strehl -Tag "ALL" -Subject $S -OutFile (& $m "ALL") -Env $allEnv `
        -StrehlArgs ($base + @("--photometric", "--out", (& $m "ALL")))

    Invoke-Strehl -Tag "D1-noca" -Subject $S -OutFile (& $m "D1") `
        -Env ($W1 + @{ STREHL_ROBUST_ELECTION = "soft"; STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs ($base + @("--photometric", "--out", (& $m "D1")))

    Invoke-Strehl -Tag "D2-norobust" -Subject $S -OutFile (& $m "D2") `
        -Env ($W1 + @{ STREHL_FIX_CA = $CAKEY; STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs ($base + @("--photometric", "--out", (& $m "D2")))

    Invoke-Strehl -Tag "D3-nosmooth" -Subject $S -OutFile (& $m "D3") `
        -Env ($W0 + @{ STREHL_FIX_CA = $CAKEY; STREHL_ROBUST_ELECTION = "soft";
                       STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs ($base + @("--photometric", "--out", (& $m "D3")))

    Invoke-Strehl -Tag "D4-nosoftgate" -Subject $S -OutFile (& $m "D4") `
        -Env ($W1 + @{ STREHL_FIX_CA = $CAKEY; STREHL_ROBUST_ELECTION = "soft" }) `
        -StrehlArgs ($base + @("--photometric", "--out", (& $m "D4")))

    Invoke-Strehl -Tag "D5-nophotometric" -Subject $S -OutFile (& $m "D5") -Env $allEnv `
        -StrehlArgs ($base + @("--out", (& $m "D5")))

    # ---- the controls that must not fire -----------------------------------
    Invoke-Strehl -Tag "P1-placebo" -Subject $S -OutFile (& $m "P1") `
        -Env ($W0 + @{ STREHL_FIX_CA = "0"; STREHL_ROBUST_ELECTION = "off";
                       STREHL_SOFT_GATE = "0"; STREHL_SMOOTH = "0" }) `
        -StrehlArgs ($base + @("--out", (& $m "P1")))

    Invoke-Strehl -Tag "P2-ungated" -Subject $S -OutFile (& $m "P2") `
        -Env ($W0 + @{ STREHL_ROBUST_ELECTION = "ungated" }) `
        -StrehlArgs ($base + @("--out", (& $m "P2")))

    # ---- the control that MUST fire ----------------------------------------
    Invoke-Strehl -Tag "PC-nearest" -Subject $S -OutFile (& $m "PC") -Env $W0 `
        -StrehlArgs ($base + @("--resampler", "nearest", "--out", (& $m "PC")))

    # ---- the unaligned, pixel-exact group ----------------------------------
    $U = @{ STREHL_ALIGN = "0" }
    Invoke-Strehl -Tag "M0u" -Subject $S -OutFile (& $m "M0u") -Env $U `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "0", "--out", (& $m "M0u"))

    Invoke-Strehl -Tag "B1u-noalign" -Subject $S -OutFile (& $m "B1u") -Env $U `
        -StrehlArgs ($base + @("--out", (& $m "B1u")))

    $ledger | Export-Csv -NoTypeInformation -Path $ledgerPath
}

$ledger | Export-Csv -NoTypeInformation -Path $ledgerPath
Write-Output "wrote $ledgerPath"
Write-Output "CAMPAIGN-DONE"
