# M116-promotion — the baseline and viewing renders.
#
# Run AFTER run_measure.ps1 and pick_single.py.
#
#  * B0  : the sharpest single source frame, rendered alone, STREHL_ALIGN=0, so
#          that it shares a pixel-exact grid with B1u and no resampling enters
#          the M85 comparison (prereg section 6).
#  * view: one --srgb render per arm per subject at a FIXED exposure, solved
#          once by --auto-exposure on A0 and then passed literally to every
#          other arm, so the arms differ in the merge and not in the gain.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M116-tree\target\release\strehl.exe"
$SHA  = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
$ROOT = "C:\dev\strehl-out\M116"
$LIB  = "D:\personal\macro"

$SUBJECTS = @("bee-3-cpl", "foam", "tweezers-cpl")
$LIMIT    = 100
$GATE     = 4

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
    return ,$out
}

$picks = Get-Content (Join-Path $ROOT "single-frame-picks.json") -Raw | ConvertFrom-Json

foreach ($S in $SUBJECTS) {
    Write-Output "==================== $S ===================="
    $dir = Join-Path $LIB $S
    $wp  = Join-Path $ROOT "warp\$S-l$LIMIT.txt"
    $W   = @{ STREHL_WARPMAP = $wp }
    $m   = { param($t) Join-Path $ROOT "measure\$S`__$t.tif" }
    $v   = { param($t) Join-Path $ROOT "view\$S`__$t.tif" }

    # ---- B0: the sharpest single source frame, unaligned, measurement file --
    $sdir = Join-Path $ROOT "single\$S"
    Invoke-Strehl -Tag "B0-single-measure" -Subject $S -OutFile (& $m "B0") `
        -Env @{ STREHL_ALIGN = "0" } `
        -StrehlArgs @("stack", $sdir, "--limit", "1", "--gate", "$GATE",
                      "--out", (& $m "B0")) | Out-Null

    # ---- the exposure, solved once on A0 and then frozen ------------------
    $out = Invoke-Strehl -Tag "A0-view-autoexposure" -Subject $S -OutFile (& $v "A0") -Env $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--auto-exposure", "--out", (& $v "A0"))
    $text = ($out | Out-String)
    $mt = [regex]::Match($text, '--exposure=(-?[0-9]+(?:\.[0-9]+)?)')
    if (-not $mt.Success) { throw "$S : could not parse the solved exposure" }
    $EXP = $mt.Groups[1].Value
    Write-Output "$S : frozen exposure --exposure=$EXP"
    Set-Content -Path (Join-Path $ROOT "view\$S`__exposure.txt") -Value $EXP

    # ---- every other arm at that exact exposure ---------------------------
    Invoke-Strehl -Tag "M0-view" -Subject $S -OutFile (& $v "M0") -Env $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "0",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "M0")) | Out-Null

    Invoke-Strehl -Tag "A1-view" -Subject $S -OutFile (& $v "A1") -Env $W `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--photometric", "--srgb", "--exposure=$EXP",
                      "--out", (& $v "A1")) | Out-Null

    Invoke-Strehl -Tag "A2-view" -Subject $S -OutFile (& $v "A2") `
        -Env ($W + @{ STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "A2")) | Out-Null

    Invoke-Strehl -Tag "A3-view" -Subject $S -OutFile (& $v "A3") `
        -Env ($W + @{ STREHL_SOFT_GATE = "exponential" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "A3")) | Out-Null

    Invoke-Strehl -Tag "A4-view" -Subject $S -OutFile (& $v "A4") `
        -Env ($W + @{ STREHL_SOFT_GATE = "gaussian" }) `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--photometric", "--srgb", "--exposure=$EXP",
                      "--out", (& $v "A4")) | Out-Null

    Invoke-Strehl -Tag "B0-view" -Subject $S -OutFile (& $v "B0") `
        -Env @{ STREHL_ALIGN = "0" } `
        -StrehlArgs @("stack", $sdir, "--limit", "1", "--gate", "$GATE",
                      "--srgb", "--exposure=$EXP", "--out", (& $v "B0")) | Out-Null

    Write-Output "---- $S viewing arms done ----"
}

$ledger | Export-Csv -NoTypeInformation -Path (Join-Path $ROOT "ledger-view.csv")
$ledger | Format-Table subject, arm, exit, seconds, bytes -AutoSize | Out-String -Width 200
Write-Output "CAMPAIGN-VIEW-DONE"
