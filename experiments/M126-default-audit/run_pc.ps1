# M126-default-audit — the CORRECTED placebo/perturbation control (PC2).
#
# WHY THIS SCRIPT EXISTS. PREREG section 4 registered `PC-nearest` as the
# instrument check: `stack --resampler nearest` should visibly damage the merge,
# and if the metric cannot see that, PREREG's rule 20 forbids issuing any
# verdict at all.
#
# As run by run.ps1 that arm came back BYTE-IDENTICAL to A0. The cause is my
# design error, not a defect in the flag M124 landed. Every aligned arm in this
# campaign sets STREHL_WARPMAP (rule 45, so nothing writes into the read-only
# capture library), and when a sidecar is named it carries its own recorded
# resampler and that one wins. The tool says so, in capitals, and it said so in
# my own log:
#
#   alignment      : --resampler asked for Nearest but the sidecar named by
#   STREHL_WARPMAP was solved with CatmullRom; THE SIDECAR WINS. Unset
#   STREHL_WARPMAP to let --resampler choose.
#
# That is documented behaviour: merge_cmd.rs:1204-1258 and main.rs:381-389.
#
# The correct control therefore SOLVES a nearest-neighbour sidecar and merges
# against that, so the perturbation actually reaches the gather. This script is
# purely additive: it writes new files (W2 sidecar, __PC2.tif) and touches no
# arm run.ps1 already produced.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M126\target\release\strehl.exe"
$SHA  = "d5ba764de26fd9addd01c167c8d0f6c465f25fb4"
$ROOT = "C:\dev\strehl-out\M126"
$LIB  = "D:\personal\macro"
$LIMIT = 100
$GATE  = 4

$SUBJECTS = @("bee-3-cpl", "lead-1-cpl", "leaf-2-cpl", "coffee-bean", "tweezers-cpl")

$STREHL_VARS = @("STREHL_WARPMAP", "STREHL_ALIGN", "STREHL_PHOTOMETRIC",
                 "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_FIX_HALO",
                 "STREHL_FIX_HALO_DELTA", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
                 "STREHL_ROBUST_ELECTION", "STREHL_DUMP_NEFF", "STREHL_DUMP_ELECTION",
                 "STREHL_DUMP_MERGE_STATE", "STREHL_CACHE_DIR",
                 "STREHL_FREEZE_REQUIRE", "STREHL_CAPTURES")
function Clear-StrehlEnv {
    foreach ($v in $STREHL_VARS) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
}

$rows = New-Object System.Collections.ArrayList

function Invoke-Logged {
    param([string]$Tag, [string]$Subject, [string[]]$StrehlArgs,
          [string]$OutFile, [hashtable]$Env = @{})

    if (Test-Path $OutFile) {
        Write-Output "  $Subject/$Tag  (already rendered, skipping)"
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
    Clear-StrehlEnv

    $text = ($out | ForEach-Object { "$_" })
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
    Set-Content -Path (Join-Path $ROOT "logs\$Subject`__$Tag.log") -Value ($header + $text)

    if ($code -ne 0) { Write-Output "  $Subject/$Tag FAILED exit $code"; return }
    $h = (Get-FileHash -Algorithm SHA256 $OutFile).Hash
    [void]$rows.Add([pscustomobject]@{
        subject = $Subject; arm = $Tag; exit = $code
        seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        sha256 = $h; bytes = (Get-Item $OutFile).Length
        envs = $envRecord; argv = "strehl " + ($StrehlArgs -join " ")
    })
    Write-Output ("  {0,-16} {1,-12} {2,6:N1}s  {3}" -f $Subject, $Tag, $sw.Elapsed.TotalSeconds, $h.Substring(0, 12))
}

foreach ($S in $SUBJECTS) {
    $dir = Join-Path $LIB $S
    $w2  = Join-Path $ROOT "warp\$S-l$LIMIT-nearest.txt"

    Invoke-Logged -Tag "align-W2-nearest" -Subject $S -OutFile $w2 -StrehlArgs @(
        "align", $dir, "--limit", "$LIMIT", "--resampler", "nearest", "--out", $w2)

    if (-not (Test-Path $w2)) { continue }

    Invoke-Logged -Tag "PC2-nearest" -Subject $S `
        -OutFile (Join-Path $ROOT "measure\$S`__PC2.tif") `
        -Env @{ STREHL_WARPMAP = $w2 } `
        -StrehlArgs @("stack", $dir, "--limit", "$LIMIT", "--gate", "$GATE",
                      "--out", (Join-Path $ROOT "measure\$S`__PC2.tif"))
}

$rows | Export-Csv -NoTypeInformation -Path (Join-Path $ROOT "ledger-pc2.csv")
Write-Output "wrote $ROOT\ledger-pc2.csv"
