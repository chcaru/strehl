# M116-promotion -- the DELTA dose ladder (prereg-ladder.txt).
#
# Registration is frozen: every arm loads the same per-subject warp sidecar
# through STREHL_WARPMAP, so warps are bit-identical across rungs and the
# warp-map cache is bypassed entirely.
#
# The ladder's bottom rung is delta = 1, NOT delta = 0. Source read S2:
# delta_in_use() applies `.filter(|d| *d > 0)` and falls through to
# unwrap_or(DELTA), so 0 silently renders the shipped 40. Arm LZ measures that.
#
# Exit codes are captured into a variable before any pipeline touches them, and
# EAP drops to Continue across the native call only (AGENTS.md rules 46/47 and
# report discipline D-p).

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M116-tree\target\release\strehl.exe"
$SHA  = "4beac7300e318f6f0aaf10b6a88e57f311b9e814"
$ROOT = "C:\dev\strehl-out\M116"
$HALO = Join-Path $ROOT "halo"
$LIB  = "D:\personal\macro"

$LIMIT = 100
$GATE  = 4

# subject -> the rungs it carries. 40 and 80 are already rendered as H1/H2 and
# are reused unchanged; they are not re-run here.
$LADDER = [ordered]@{
    "bee-3-cpl"                          = @(1, 5, 10, 20, 160)
    "flower-bud-with-background-fern-cpl" = @(1, 5, 10, 20, 160)
}

foreach ($d in @("measure", "view", "logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $HALO $d) | Out-Null
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

    $sw = [Diagnostics.Stopwatch]::StartNew()
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $stdout = & $EXE @StrehlArgs 2>&1
    $code   = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    $sw.Stop()

    $log = Join-Path $HALO "logs\$Subject`__$Tag.log"
    $header = @(
        "# M116-ladder $Subject $Tag",
        "# commit  $SHA",
        "# binary  $EXE",
        "# env     $envRecord",
        "# argv    strehl " + ($StrehlArgs -join " "),
        "# exit    $code",
        "# seconds $([math]::Round($sw.Elapsed.TotalSeconds, 2))",
        ""
    )
    Set-Content -Path $log -Value ($header + ($stdout | ForEach-Object { "$_" }))

    # LB6 needs the tool's own treated count, straight out of its report.
    $text    = ($stdout | Out-String)
    $treated = ""
    $mt = [regex]::Match($text, '([0-9]+)\s+treated')
    if ($mt.Success) { $treated = $mt.Groups[1].Value }

    $hash = ""; $len = 0
    if ($OutFile -and (Test-Path $OutFile)) {
        $hash = (Get-FileHash -Algorithm SHA256 $OutFile).Hash
        $len  = (Get-Item $OutFile).Length
    }
    [void]$ledger.Add([pscustomobject]@{
        subject = $Subject; arm = $Tag; exit = $code
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        sha256 = $hash; bytes = $len; treated = $treated; envs = $envRecord
        argv = "strehl " + ($StrehlArgs -join " "); outfile = $OutFile
    })
    Clear-StrehlEnv
    if ($code -ne 0) { throw "$Subject/$Tag FAILED with exit $code -- see $log" }
    return ,$stdout
}

foreach ($S in $LADDER.Keys) {
    Write-Output "==================== $S ===================="
    $dir = Join-Path $LIB $S
    $wp  = Join-Path $ROOT "warp\$S-l$LIMIT.txt"
    if (-not (Test-Path $wp)) { throw "$S : frozen warp sidecar missing at $wp" }
    $W = @{ STREHL_WARPMAP = $wp }

    $expFile = Join-Path $HALO "view\$S`__exposure.txt"
    if (-not (Test-Path $expFile)) { throw "$S : frozen exposure missing at $expFile" }
    $EXP = (Get-Content $expFile -Raw).Trim()
    Write-Output "$S : reusing frozen warps and frozen exposure --exposure=$EXP"

    # ---- LB1 dead-rung probe: delta=0 must render byte-identical to delta 40 --
    if ($S -eq "bee-3-cpl") {
        $lz = Join-Path $HALO "measure\$S`__LZ.tif"
        Invoke-Strehl -Tag "LZ-deadrung-d0" -Subject $S -OutFile $lz `
            -UseEnv ($W + @{ STREHL_FIX_HALO = "1"; STREHL_FIX_HALO_DELTA = "0" }) `
            -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                          "--out", $lz) | Out-Null
    }

    # ---- linear ladder rungs -------------------------------------------------
    foreach ($D in $LADDER[$S]) {
        $tag = "L$D"
        $out = Join-Path $HALO "measure\$S`__$tag.tif"
        Invoke-Strehl -Tag "$tag-halo-d$D" -Subject $S -OutFile $out `
            -UseEnv ($W + @{ STREHL_FIX_HALO = "1"; STREHL_FIX_HALO_DELTA = "$D" }) `
            -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                          "--out", $out) | Out-Null
    }

    # ---- viewing renders for the LB7 crops: sRGB at the frozen exposure -------
    # H0 and delta 40 on both subjects; the ladder ends on bee for the contact
    # sheet. Views are for looking at only and no bar is decided on them.
    $viewRungs = if ($S -eq "bee-3-cpl") { @("H0", "1", "40", "160") } else { @("H0", "40") }
    foreach ($R in $viewRungs) {
        $vt  = if ($R -eq "H0") { "H0" } else { "V$R" }
        $out = Join-Path $HALO "view\$S`__$vt.tif"
        $env = if ($R -eq "H0") { $W }
               else { $W + @{ STREHL_FIX_HALO = "1"; STREHL_FIX_HALO_DELTA = "$R" } }
        Invoke-Strehl -Tag "$vt-view" -Subject $S -OutFile $out -UseEnv $env `
            -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                          "--srgb", "--exposure=$EXP", "--out", $out) | Out-Null
    }

    Write-Output "---- $S ladder done ----"
}

$ledger | Export-Csv -NoTypeInformation -Path (Join-Path $HALO "ledger-ladder.csv")
$ledger | Format-Table subject, arm, exit, seconds, treated -AutoSize | Out-String -Width 200
Write-Output "CAMPAIGN-LADDER-DONE"
