# M126-default-audit — the B0 single-frame baseline.
#
# Renders the ONE frame that pick_single.py chose, alone, with STREHL_ALIGN=0,
# so it is pixel-exact and shares the M0u mask grid with B1u-noalign.
#
# This arm exists because "better than the current default" is not the same as
# "good": V-M116 measured that on a drifting stack the single frame BEATS the
# merge (tweezers-cpl single 0.84177 vs merge 0.37376). Every promotion verdict
# in this milestone is read against this floor as well as against A0.
#
# Run AFTER run.ps1 (which writes the A0 election maps) and pick_single.py.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M126\target\release\strehl.exe"
$SHA  = "d5ba764de26fd9addd01c167c8d0f6c465f25fb4"
$ROOT = "C:\dev\strehl-out\M126"
$GATE = 4

$SUBJECTS = @("bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl")

$STREHL_VARS = @("STREHL_WARPMAP", "STREHL_ALIGN", "STREHL_PHOTOMETRIC",
                 "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_FIX_HALO",
                 "STREHL_FIX_HALO_DELTA", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
                 "STREHL_ROBUST_ELECTION", "STREHL_DUMP_NEFF", "STREHL_DUMP_ELECTION",
                 "STREHL_DUMP_MERGE_STATE", "STREHL_CACHE_DIR",
                 "STREHL_FREEZE_REQUIRE", "STREHL_CAPTURES")
foreach ($v in $STREHL_VARS) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }

$rows = New-Object System.Collections.ArrayList

foreach ($S in $SUBJECTS) {
    $dir = Join-Path $ROOT "single\$S"
    $out = Join-Path $ROOT "measure\$S`__B0.tif"

    if (-not (Test-Path $dir)) { Write-Output "$S : no single dir, skipped"; continue }
    $arw = @(Get-ChildItem -Path $dir -Filter *.ARW)
    if ($arw.Count -ne 1) {
        Write-Output "$S : $($arw.Count) frames in the single dir, want exactly 1"
        continue
    }
    if (Test-Path $out) { Write-Output "  $S/B0-single  (already rendered, skipping)"; continue }

    $env:STREHL_ALIGN = "0"
    $strehlArgs = @("stack", $dir, "--limit", "1", "--gate", "$GATE", "--out", $out)

    $sw   = [Diagnostics.Stopwatch]::StartNew()
    $log  = & $EXE @strehlArgs 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()
    Remove-Item env:STREHL_ALIGN -ErrorAction SilentlyContinue

    $text = ($log | ForEach-Object { "$_" })
    $header = @(
        "# M126 $S B0-single",
        "# commit  $SHA",
        "# binary  $EXE",
        "# env     STREHL_ALIGN=0",
        "# frame   $($arw[0].Name)",
        "# argv    strehl " + ($strehlArgs -join " "),
        "# exit    $code",
        "# seconds $([math]::Round($sw.Elapsed.TotalSeconds, 2))",
        ""
    )
    Set-Content -Path (Join-Path $ROOT "logs\$S`__B0-single.log") -Value ($header + $text)

    if ($code -ne 0) { Write-Output "  $S/B0-single FAILED exit $code"; continue }

    $h = (Get-FileHash -Algorithm SHA256 $out).Hash
    [void]$rows.Add([pscustomobject]@{
        subject = $S; arm = "B0-single"; exit = $code
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        sha256 = $h; bytes = (Get-Item $out).Length
        frame = $arw[0].Name
        envs = "STREHL_ALIGN=0"; argv = "strehl " + ($strehlArgs -join " ")
    })
    Write-Output ("  {0,-16} B0-single  {1,6:N1}s  {2}" -f $S, $sw.Elapsed.TotalSeconds, $h.Substring(0, 12))
}

$rows | Export-Csv -NoTypeInformation -Path (Join-Path $ROOT "ledger-single.csv")
Write-Output "wrote $ROOT\ledger-single.csv"
