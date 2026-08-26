# Acceptance re-run for the FLATNESS gate.
#
# The eligibility rule changed from an absolute ceiling on `best_focus` to the
# debiased peak prominence against the merge's own significance gate, so no
# earlier arm is comparable: the estimator's domain is a different set of
# pixels. Both arms of every subject therefore come from this one pin.
#
# `STREHL_VEIL`'s magnitude is now only an on/off switch -- the gate is taken
# from `--gate`, not from this number. 1.5 is kept purely so the command line
# is character-identical to the previous acceptance run and the ONLY difference
# between the two is the code.

$ErrorActionPreference = "Continue"

$Exe = "C:\dev\strehl-out\pin-veilgate\strehl.exe"
$Out = "C:\dev\strehl-out\VEILGATE"
$Src = "D:\personal\macro"

if (-not (Test-Path $Exe)) { throw "pinned binary missing: $Exe" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0, 12)
Write-Output "BINARY $Exe"
Write-Output "SHA256 $hash  -- every arm below comes from this one file"
Write-Output ""

$subjects = @(
    @{ dir = "flower-bud-alone-cpl";   tag = "fb" },    # TARGET   beat -247 DN at d=120-200
    @{ dir = "pencil-steep-angle-cpl"; tag = "pen" },   # POLARITY improve or no-op
    @{ dir = "109MSDCF";               tag = "d109" },  # PLACEBO  ~no-op
    @{ dir = "couch-fibers-cpl";       tag = "cf" }     # GUARD    unchanged
)

foreach ($s in $subjects) {
    foreach ($arm in @("off", "on")) {
        $tag = "$($s.tag)-$arm"
        $dst = Join-Path $Out "$tag.tif"
        if (Test-Path $dst) { Write-Output "SKIP  $tag (exists)"; continue }

        Remove-Item Env:STREHL_VEIL, Env:STREHL_VEIL_MARGIN, Env:STREHL_VEIL_FLOOR -ErrorAction SilentlyContinue
        if ($arm -eq "on") {
            $env:STREHL_VEIL = "1.5"; $env:STREHL_VEIL_MARGIN = "3"; $env:STREHL_VEIL_FLOOR = "0.5"
        }

        $log = Join-Path $Out "$tag.log"
        $t0 = Get-Date
        & $Exe stack "$($Src)\$($s.dir)" -o $dst --linear-srgb --gate 4.0 --photometric on *>&1 |
            Out-File -Encoding utf8 $log
        $rc = $LASTEXITCODE
        Write-Output ("ARM {0,-10} rc={1} {2:N0}s" -f $tag, $rc, ((Get-Date) - $t0).TotalSeconds)
        Select-String -Path $log -Pattern "veil: gate|veil: declined|collapse veto" |
            ForEach-Object { Write-Output ("    " + $_.Line.Trim()) }
        if ($rc -ne 0) { Write-Output "    FAILED -- see $log" }
    }
}

Remove-Item Env:STREHL_VEIL, Env:STREHL_VEIL_MARGIN, Env:STREHL_VEIL_FLOOR -ErrorAction SilentlyContinue
Write-Output ""
Write-Output "done"
