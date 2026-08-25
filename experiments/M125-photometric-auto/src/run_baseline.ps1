# M125 — freeze the CURRENT binary's output on two of the owner's stacks.
#
# This is the control the byte-identity proof is measured against (AGENTS.md
# rules 26, 39, 47). It runs the binary built from HEAD *before* any M125 edit,
# frozen at C:\dev\strehl-out\M125\bin\strehl-baseline.exe.
#
# Rule 45: STREHL_WARPMAP is pinned into this milestone's own scratch, so the
# shared sidecar inside the read-only capture library is never written.
# Rule 46/47: the exit code is captured in the statement after the call, before
# any pipeline touches it; the whole invocation and environment are recorded.
#
# NEVER writes to D:\. Every output path is under C:\dev\strehl-out\M125\.

$ErrorActionPreference = "Stop"

$EXE  = "C:\dev\strehl-out\M125\bin\strehl-baseline.exe"
$ROOT = "C:\dev\strehl-out\M125"
$LIB  = "D:\personal\macro"
$GATE = 4

$ledgerPath = Join-Path $ROOT "ledger-baseline.csv"
$ledger = New-Object System.Collections.ArrayList

function Clear-StrehlEnv {
    foreach ($v in @("STREHL_WARPMAP", "STREHL_ALIGN", "STREHL_PHOTOMETRIC",
                     "STREHL_SOFT_GATE", "STREHL_FIX_CA", "STREHL_FIX_HALO",
                     "STREHL_FIX_HALO_DELTA", "STREHL_SMOOTH", "STREHL_SMOOTH_HUBER",
                     "STREHL_DUMP_NEFF", "STREHL_DUMP_ELECTION", "STREHL_ROBUST_ELECTION",
                     "STREHL_DUMP_MERGE_STATE", "STREHL_CACHE_DIR",
                     "STREHL_FREEZE_REQUIRE", "STREHL_CAPTURES", "STREHL_RESAMPLER")) {
        Remove-Item "env:$v" -ErrorAction SilentlyContinue
    }
}

function Invoke-Strehl {
    param(
        [string]   $Exe,
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

    # Windows PowerShell 5.1 turns any native stderr write into a terminating
    # NativeCommandError while $ErrorActionPreference is Stop, and this binary
    # writes its entire measurement report to stderr. The preference is local
    # to this function, so restoring it is automatic on return.
    $ErrorActionPreference = "Continue"
    $sw   = [Diagnostics.Stopwatch]::StartNew()
    $out  = & $Exe @StrehlArgs 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()

    $log = Join-Path $ROOT "logs\$Subject`__$Tag.log"
    $header = @(
        "# M125 $Subject $Tag",
        "# binary  $Exe",
        "# binsha  $((Get-FileHash -Algorithm SHA256 $Exe).Hash)",
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
        binary  = $Exe
        envs    = $envRecord
        argv    = "strehl " + ($StrehlArgs -join " ")
        outfile = $OutFile
    })
    $ledger | Export-Csv -NoTypeInformation -Path $ledgerPath

    Clear-StrehlEnv
    return $code
}

foreach ($S in @("tweezers-cpl", "bee-3-cpl")) {
    $dir = Join-Path $LIB $S
    $n = (Get-ChildItem $dir -File -Force -Filter '*.ARW').Count
    $L = [Math]::Min(100, $n)
    Write-Output "==================== $S  (N=$n, L=$L) ===================="

    $wp = Join-Path $ROOT "warp\$S-l$L.txt"
    $a0 = Join-Path $ROOT "measure\$S`__BASE.tif"

    if (-not (Test-Path $wp)) {
        $c = Invoke-Strehl -Exe $EXE -Tag "align" -Subject $S -OutFile $wp `
            -Env @{ STREHL_CACHE_DIR = (Join-Path $ROOT "cache") } `
            -StrehlArgs @("align", $dir, "--limit", "$L", "--out", $wp)
        if ($c -ne 0) { throw "$S align FAILED exit $c" }
    }

    $c = Invoke-Strehl -Exe $EXE -Tag "BASE" -Subject $S -OutFile $a0 `
        -Env @{ STREHL_WARPMAP = $wp } `
        -StrehlArgs @("stack", $dir, "--limit", "$L", "--gate", "$GATE", "--out", $a0)
    if ($c -ne 0) { throw "$S BASE FAILED exit $c" }
    Write-Output "  BASE $((Get-FileHash -Algorithm SHA256 $a0).Hash)"
}

$ledger | Export-Csv -NoTypeInformation -Path $ledgerPath
Write-Output "BASELINE-DONE"
