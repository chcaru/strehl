# Commission `the_embedded_profile_states_the_transfer_curve_the_pixels_carry`.
#
# Rule 2 of AGENTS.md: a metric is worth nothing until it has been shown to read
# a PLANTED DEFECT as RED and a KNOWN-CLEAN input as GREEN, and to move the right
# way on a planted IMPROVEMENT. A suite that plants only degradations cannot tell
# a test that is BLIND to a defect from one that is PERVERSE on it.
#
# Four arms, each a real edit to `icc_for` in image_out.rs, each compiled and run:
#
#   CLEAN     the tree as committed                       -> expect GREEN
#   SWAP      exchange the sRGB and linear profile arms    -> expect RED (new test)
#             ... and the PRE-EXISTING ICC tests must stay GREEN, which is the
#             evidence that the hole was real and that this test, not they, closes it.
#   THIRDARM  revert the (matrix, no curve, tone) arm to the pre-change behaviour
#             of handing it the linear profile                -> expect RED
#             This is the planted IMPROVEMENT read backwards: the arm is the
#             change this lane made, so RED-before/GREEN-after proves the test is
#             sensitive to the improvement rather than blind to it.
#   BACKWARDS store the TRC in the encoding direction         -> expect RED
#
# The source file is copied to $env:TEMP and restored from the copy in a finally
# block. `git checkout --` is NEVER used: it reverts to HEAD and has already
# destroyed uncommitted work on this machine.
#
# Usage:  pwsh -File experiments/BUILD-OUTPUT/commission_icc.ps1

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$src = "crates\strehl-cli\src\image_out.rs"
$bak = Join-Path $env:TEMP ("image_out.rs.commission." + [guid]::NewGuid().ToString('N'))

$NEW_TEST = 'the_embedded_profile_states_the_transfer_curve_the_pixels_carry'
# The tests that existed BEFORE this lane touched the file. If a planted defect
# leaves all of these green, they did not have power over it.
$OLD_TESTS = @(
    'only_the_colorimetric_paths_get_a_profile',
    'the_profile_is_structurally_well_formed_and_deterministic',
    'the_derived_primaries_match_the_published_srgb_icc_columns',
    'the_primary_columns_sum_to_the_pcs_white',
    'the_transfer_curve_is_stored_in_the_decoding_direction'
)

function Invoke-Arm {
    param([string]$Name, [scriptblock]$Mutate)
    if ($Mutate) {
        & $Mutate
        # A silent no-op Replace would make a planted defect look like a clean
        # tree and the arm would "pass" for the wrong reason. This is the same
        # class of error as a metric that never runs.
        if ((Get-Content $src -Raw) -eq (Get-Content $bak -Raw)) {
            Write-Output "ARM $Name : MUTATION DID NOT APPLY -- arm is meaningless, aborting"
            return
        }
    }
    # cargo writes progress to stderr; with $ErrorActionPreference = 'Stop' that
    # becomes a terminating NativeCommandError before a single test has run.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $out = & cargo test --release -p strehl-cli --bin strehl image_out 2>&1 | Out-String
    $ErrorActionPreference = $prev
    if ($out -match 'could not compile|error\[E') {
        Write-Output "ARM $Name : BUILD FAILED"
        Write-Output ($out -split "`n" | Select-String 'error' | Select-Object -First 6)
        return
    }
    $newRes = if ($out -match "test image_out::tests::$NEW_TEST \.\.\. (\w+)") { $Matches[1] } else { 'MISSING' }
    $oldRes = @()
    foreach ($t in $OLD_TESTS) {
        $r = if ($out -match "test image_out::tests::$t \.\.\. (\w+)") { $Matches[1] } else { 'MISSING' }
        $oldRes += "$t=$r"
    }
    $summary = ($out -split "`n" | Select-String 'test result:' | Select-Object -First 1).ToString().Trim()
    Write-Output "ARM $Name"
    Write-Output "  new test  : $NEW_TEST -> $($newRes.ToUpper())"
    Write-Output "  pre-existing ICC tests:"
    foreach ($r in $oldRes) { Write-Output "      $r" }
    Write-Output "  $summary"
    Write-Output ""
}

try {
    Copy-Item $src $bak -Force
    Write-Output "backup: $bak"
    Write-Output ""

    Invoke-Arm 'CLEAN (known-good, expect GREEN)' $null

    Invoke-Arm 'SWAP (planted defect: sRGB and linear profiles exchanged, expect RED)' {
        $t = Get-Content $bak -Raw
        $t = $t.Replace(
            "        (true, true, _) => Some(icc_srgb_v2(false)),`n        (true, false, false) => Some(icc_srgb_v2(true)),",
            "        (true, true, _) => Some(icc_srgb_v2(true)),`n        (true, false, false) => Some(icc_srgb_v2(false)),")
        Set-Content $src $t -NoNewline
    }

    Invoke-Arm 'THIRDARM (improvement reverted: tone-in-linear gets the linear profile, expect RED)' {
        $t = Get-Content $bak -Raw
        $t = $t.Replace(
            "        (true, false, true) => None,",
            "        (true, false, true) => Some(icc_srgb_v2(true)),")
        Set-Content $src $t -NoNewline
    }

    Invoke-Arm 'BACKWARDS (planted defect: TRC stored in the encoding direction, expect RED)' {
        $t = Get-Content $bak -Raw
        # The inverse of srgb_eotf, inlined at the one call site that fills the
        # curve. This is the defect the house has always warned about: every
        # structural check still passes and the file renders with wrong contrast.
        $t = $t.Replace(
            "                let y = srgb_eotf(i as f64 / (N - 1) as f64);",
            "                let x = i as f64 / (N - 1) as f64;`n                let y = if x <= 0.003_130_8 { 12.92 * x } else { 1.055 * x.powf(1.0 / 2.4) - 0.055 };")
        Set-Content $src $t -NoNewline
    }
}
finally {
    Copy-Item $bak $src -Force
    # Rule 33: cargo keys on mtime, and a restore can hand back an OLDER
    # timestamp than the artefacts built from the mutated file. Without this the
    # next `cargo test` reports success from a binary built from the defect.
    Set-ItemProperty $src -Name LastWriteTime -Value (Get-Date)
    Remove-Item $bak -Force -ErrorAction SilentlyContinue
    Write-Output "restored $src from backup, mtime bumped"
}
