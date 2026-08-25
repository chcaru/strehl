# M116-promotion — the occlusion-halo campaign (prereg-halo.txt).
#
# Arms per prereg-halo.txt section 1. Registration is solved once per subject
# and loaded read-only by every arm through STREHL_WARPMAP, so warps are
# bit-identical across arms by construction and the warp-map cache is bypassed
# entirely (report P20-P22).
#
# bee-3-cpl and tweezers-cpl reuse the warp sidecars already solved by
# run_measure.ps1 at this same SHA. That makes H0 a cross-campaign replicate of
# A0: it MUST hash identically, and score_halo.py asserts it.
#
# Exit codes are captured into a variable BEFORE any pipeline touches them and
# no pipeline whose status is later read contains `Select-Object -First`
# (AGENTS.md rules 46 and 47).

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M116-tree\target\release\strehl.exe"
$SHA  = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
$ROOT = "C:\dev\strehl-out\M116"
$HALO = Join-Path $ROOT "halo"
$LIB  = "D:\personal\macro"

$SUBJECTS = @("bee-3-cpl",
              "flower-bud-with-background-fern-cpl",
              "flower-bud-alone-cpl",
              "tweezers-cpl")
$LIMIT = 100
$GATE  = 4

foreach ($d in @("measure", "view", "logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $HALO $d) | Out-Null
}
New-Item -ItemType Directory -Force -Path (Join-Path $ROOT "warp") | Out-Null

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
        [hashtable]$UseEnv = @{}
    )
    Clear-StrehlEnv
    foreach ($k in $UseEnv.Keys) { Set-Item "env:$k" $UseEnv[$k] }

    $envRecord = ($UseEnv.GetEnumerator() | Sort-Object Name |
                  ForEach-Object { "$($_.Name)=$($_.Value)" }) -join " "
    if (-not $envRecord) { $envRecord = "(none set)" }

    $sw     = [Diagnostics.Stopwatch]::StartNew()
    # strehl writes its progress report to stderr. Under `2>&1` PowerShell wraps
    # each stderr line in an ErrorRecord, and with EAP=Stop the FIRST such line
    # is a terminating error -- the whole campaign dies on arm one having
    # written nothing. Drop to Continue across the native call only, and take
    # the exit code into a variable before any pipeline can touch it.
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $stdout = & $EXE @StrehlArgs 2>&1
    $code   = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    $sw.Stop()

    $log = Join-Path $HALO "logs\$Subject`__$Tag.log"
    $header = @(
        "# M116-halo $Subject $Tag",
        "# commit  $SHA",
        "# binary  $EXE",
        "# env     $envRecord",
        "# argv    strehl " + ($StrehlArgs -join " "),
        "# exit    $code",
        "# seconds $([math]::Round($sw.Elapsed.TotalSeconds, 2))",
        ""
    )
    Set-Content -Path $log -Value ($header + ($stdout | ForEach-Object { "$_" }))

    $hash = ""; $len = 0
    if ($OutFile -and (Test-Path $OutFile)) {
        $hash = (Get-FileHash -Algorithm SHA256 $OutFile).Hash
        $len  = (Get-Item $OutFile).Length
    }
    [void]$ledger.Add([pscustomobject]@{
        subject = $Subject; arm = $Tag; exit = $code
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        sha256 = $hash; bytes = $len; envs = $envRecord
        argv = "strehl " + ($StrehlArgs -join " "); outfile = $OutFile
    })
    Clear-StrehlEnv
    if ($code -ne 0) { throw "$Subject/$Tag FAILED with exit $code -- see $log" }
    return ,$stdout
}

foreach ($S in $SUBJECTS) {
    Write-Output "==================== $S ===================="
    $dir = Join-Path $LIB $S
    $wp  = Join-Path $ROOT "warp\$S-l$LIMIT.txt"

    if (-not (Test-Path $wp)) {
        Invoke-Strehl -Tag "align" -Subject $S -OutFile $wp -StrehlArgs @(
            "align", $dir, "--limit", "$LIMIT", "--out", $wp) | Out-Null
        Write-Output "$S : solved a new warp sidecar"
    } else {
        Write-Output "$S : reusing the frozen warp sidecar from run_measure.ps1"
    }

    $W = @{ STREHL_WARPMAP = $wp }
    $m = { param($t) Join-Path $HALO "measure\$S`__$t.tif" }
    $v = { param($t) Join-Path $HALO "view\$S`__$t.tif" }

    # ---- linear measurement arms, at the product gate ----------------------
    Invoke-Strehl -Tag "H0-default" -Subject $S -OutFile (& $m "H0") -UseEnv $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "H0")) | Out-Null

    Invoke-Strehl -Tag "H1-halo-d40" -Subject $S -OutFile (& $m "H1") `
        -UseEnv ($W + @{ STREHL_FIX_HALO = "1" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "H1")) | Out-Null

    Invoke-Strehl -Tag "H2-halo-d80" -Subject $S -OutFile (& $m "H2") `
        -UseEnv ($W + @{ STREHL_FIX_HALO = "1"; STREHL_FIX_HALO_DELTA = "80" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "H2")) | Out-Null

    Invoke-Strehl -Tag "H3-trap-halo0" -Subject $S -OutFile (& $m "H3") `
        -UseEnv ($W + @{ STREHL_FIX_HALO = "0" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (& $m "H3")) | Out-Null

    # ---- bee only: gate 0, M87's own terms ---------------------------------
    if ($S -eq "bee-3-cpl") {
        Invoke-Strehl -Tag "G0-gate0-default" -Subject $S -OutFile (& $m "G0") -UseEnv $W `
            -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "0",
                          "--out", (& $m "G0")) | Out-Null

        Invoke-Strehl -Tag "G1-gate0-halo-d40" -Subject $S -OutFile (& $m "G1") `
            -UseEnv ($W + @{ STREHL_FIX_HALO = "1" }) `
            -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "0",
                          "--out", (& $m "G1")) | Out-Null
    }

    # ---- viewing renders: sRGB, one frozen exposure across the arms --------
    $stdout = Invoke-Strehl -Tag "H0-view-autoexposure" -Subject $S -OutFile (& $v "H0") -UseEnv $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--auto-exposure", "--out", (& $v "H0"))
    $text = ($stdout | Out-String)
    $mt = [regex]::Match($text, '--exposure=(-?[0-9]+(?:\.[0-9]+)?)')
    if (-not $mt.Success) { throw "$S : could not parse the solved exposure" }
    $EXP = $mt.Groups[1].Value
    Write-Output "$S : frozen exposure --exposure=$EXP"
    Set-Content -Path (Join-Path $HALO "view\$S`__exposure.txt") -Value $EXP

    Invoke-Strehl -Tag "H1-view" -Subject $S -OutFile (& $v "H1") `
        -UseEnv ($W + @{ STREHL_FIX_HALO = "1" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "H1")) | Out-Null

    Invoke-Strehl -Tag "H2-view" -Subject $S -OutFile (& $v "H2") `
        -UseEnv ($W + @{ STREHL_FIX_HALO = "1"; STREHL_FIX_HALO_DELTA = "80" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "H2")) | Out-Null

    Write-Output "---- $S halo arms done ----"
}

$ledger | Export-Csv -NoTypeInformation -Path (Join-Path $HALO "ledger-halo.csv")
$ledger | Format-Table subject, arm, exit, seconds, bytes -AutoSize | Out-String -Width 200
Write-Output "CAMPAIGN-HALO-DONE"
