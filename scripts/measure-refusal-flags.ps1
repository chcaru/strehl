<#
.SYNOPSIS
    Re-measure the "0 of N fail" claim in `strehl stack --help`.

.DESCRIPTION
    `main.rs` documents that the estimator-only flags are REFUSED under the
    pyramid backend, and that a caller who passes one WITHOUT `--merge
    estimator` still RUNS because the backend is inferred from the flags. That
    second sentence carries a MEASURED count -- "0 of N fail" -- and the unit
    test `the_migration_note_counts_the_flags_it_enumerates` refuses to let the
    count drift from the enumeration beside it.

    The test cannot take the measurement, only insist that one was taken. This
    script takes it, in three arms:

      ARM C  BASELINE          --merge estimator, no estimator-only flag.
                               Proves the SCENE stacks at all, so an arm-A
                               failure is attributable to the flag and not to
                               the capture.
      ARM A  THE CLAIM         each flag alone, no --merge. Must exit 0 and
                               report the estimator as INFERRED.
      ARM B  POSITIVE CONTROL  each flag with --merge pyramid. Must exit
                               nonzero with the refusal message.

    Arm B is not decoration. This harness's first two revisions reported "10 of
    10 fail" and then "0 of 10 refused"; both were defects in the harness
    rather than in the binary, and only the control distinguished a real result
    from a blind instrument. A green arm A on its own means nothing, because a
    harness that cannot observe failure reports success unconditionally.

    Run it whenever a flag is added to or removed from the `wrong_backend`
    table in `main.rs`, then update BOTH the enumeration and the count in the
    `--help` prose. Adding a flag without re-measuring fails the unit test,
    which is the point.

.PARAMETER Exe
    The strehl binary to measure. Defaults to the release build in this repo.

.PARAMETER Captures
    Capture library root. Honours $STREHL_CAPTURES, matching byte-freeze.rs.

.PARAMETER Stack
    Capture directory to stack. Must have a background large enough to fit
    photometric gain against -- the estimator normalises by default, and a
    scene without one (coffee-bubbles, for instance) aborts with "U3 the eroded
    low-detail region keeps only 0 px". That is a scene defect, not a flag
    defect, which is exactly what arm C exists to catch.

.PARAMETER Frames
    Frames to stack per invocation. Small is fine; this measures exit codes.

.OUTPUTS
    Exit 0 CONFIRMED, 1 CLAIM FALSE, 2 HARNESS BLIND, 3 SCENE UNUSABLE.
#>
[CmdletBinding()]
param(
    [string] $Exe      = (Join-Path $PSScriptRoot '..\target\release\strehl.exe'),
    [string] $Captures = $(if ($env:STREHL_CAPTURES) { $env:STREHL_CAPTURES } else { 'D:\personal\macro' }),
    [string] $Stack    = 'coffee-bean',
    [int]    $Frames   = 4
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $Exe)) {
    Write-Host "no binary at $Exe -- build it first, or pass -Exe."
    exit 3
}
$src = Join-Path $Captures $Stack
if (-not (Test-Path $src)) {
    Write-Host "no capture directory at $src -- pass -Captures/-Stack, or set `$STREHL_CAPTURES."
    exit 3
}

$out = Join-Path ([System.IO.Path]::GetTempPath()) ("strehl-refusal-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force -Path $out | Out-Null

try {
    # ---- ARM C: baseline -------------------------------------------------
    & $Exe stack $src --out "$out\c.tif" --limit $Frames --merge estimator 2>&1 | Out-Null
    $rcC = $LASTEXITCODE
    Write-Host "ARM C baseline (--merge estimator, no estimator-only flag): rc=$rcC"
    if ($rcC -ne 0) {
        Write-Host ""
        Write-Host "ABORT: the scene itself does not stack. Nothing measured here would mean anything."
        Write-Host "       Pick a -Stack with a real background; see the .PARAMETER note above."
        exit 3
    }
    Write-Host ""

    # Every flag the `wrong_backend` table refuses under Pyramid, in table
    # order. `--stats-placebo` is a bare flag that clap REQUIRES `--stats`
    # beside; passed alone it exits 2 during argument parsing, before any
    # backend is chosen, so it is measured with its documented prerequisite.
    $cases = @(
        @{ n = '--gate';          a = @('--gate', '4.0') },
        @{ n = '--focus';         a = @('--focus', 'tenengrad-w13') },
        @{ n = '--target-n-eff';  a = @('--target-n-eff', '2.0') },
        @{ n = '--index-map';     a = @('--index-map', "$out\idx.tif") },
        @{ n = '--n-eff-map';     a = @('--n-eff-map', "$out\neff.tif") },
        @{ n = '--photometric';   a = @('--photometric') },
        @{ n = '--stats';         a = @('--stats') },
        @{ n = '--stats-placebo'; a = @('--stats', '--stats-placebo') },
        @{ n = '--flat-roi';      a = @('--flat-roi', '2000,1500,64,64') },
        @{ n = '--detail-roi';    a = @('--detail-roi', '2000,1500,64,64') }
    )

    $rows = @()
    foreach ($c in $cases) {
        $oA  = & $Exe @(@('stack', $src, '--out', "$out\a.tif", '--limit', $Frames) + $c.a) 2>&1 | Out-String
        $rcA = $LASTEXITCODE
        $inferred = [bool]($oA -match 'merge backend\s*:\s*estimator \(inferred')

        $oB  = & $Exe @(@('stack', $src, '--out', "$out\b.tif", '--limit', $Frames, '--merge', 'pyramid') + $c.a) 2>&1 | Out-String
        $rcB = $LASTEXITCODE
        $refused = [bool]($oB -match 'belongs to the estimator merge|Refused rather than ignored')

        $rows += [pscustomobject]@{ flag = $c.n; A_rc = $rcA; A_inferred = $inferred; B_rc = $rcB; B_refused = $refused }
        Write-Host ("{0,-16} A: rc={1} inferred={2,-5}   B: rc={3} refused={4}" -f $c.n, $rcA, $inferred, $rcB, $refused)
    }

    $n        = $rows.Count
    $aFail    = @($rows | Where-Object { $_.A_rc -ne 0 }).Count
    $aInfer   = @($rows | Where-Object { $_.A_inferred }).Count
    $bRefused = @($rows | Where-Object { $_.B_rc -ne 0 -and $_.B_refused }).Count

    Write-Host ""
    Write-Host "================ SUMMARY ================"
    Write-Host "flags enumerated              : $n"
    Write-Host "ARM A failing (claim: 0)      : $aFail of $n"
    Write-Host "ARM A inferred estimator      : $aInfer of $n"
    Write-Host "ARM B refused under pyramid   : $bRefused of $n   <-- positive control"
    Write-Host ""

    if ($bRefused -ne $n) {
        Write-Host "VERDICT: HARNESS BLIND -- the positive control fired only $bRefused of $n."
        Write-Host "         Arm A proves nothing until this reads $n of $n. Fix the harness first."
        exit 2
    }
    if ($aFail -eq 0 -and $aInfer -eq $n) {
        Write-Host "VERDICT: CONFIRMED -- 0 of $n fail without --merge, all $n infer the estimator,"
        Write-Host "         and all $n are refused when the pyramid is named explicitly."
        Write-Host "         Write `"$n`" into BOTH the enumeration and the `"0 of N fail`" count in --help."
        exit 0
    }
    Write-Host "VERDICT: CLAIM FALSE -- $aFail of $n fail, $aInfer of $n inferred the estimator."
    exit 1
}
finally {
    Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
}
