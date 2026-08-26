# Full acceptance re-run on ONE binary, after the polarity gate changed the
# backdrop estimator for every subject.
#
# The earlier arms cannot be reused. `pen-pm-off` came from pin-veil2 and
# `pen-pol` from pin-veil3, and they are not byte-identical even though the
# veil declined and touched nothing -- because other agents are committing to
# this shared tree between builds, so two pins differ by more than my edit.
# Every comparison below therefore has BOTH arms from pin-veil3.
#
# ARMS per subject: veil off, veil on. One variable.

$ErrorActionPreference = "Continue"

$Exe = "C:\dev\strehl-out\pin-veil3\strehl.exe"
$Out = "C:\dev\strehl-out\VEIL"
$Src = "D:\personal\macro"

if (-not (Test-Path $Exe)) { throw "pinned binary missing: $Exe" }
$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0, 12)
Write-Output "BINARY $Exe"
Write-Output "SHA256 $hash  -- every arm below comes from this one file"
Write-Output ""

$subjects = @(
    @{ dir = "pencil-steep-angle-cpl"; tag = "pen" },   # POLARITY  (on arm exists: pen-pol)
    @{ dir = "109MSDCF";               tag = "d109" },  # PLACEBO
    @{ dir = "couch-fibers-cpl";       tag = "cf3" },   # GUARD
    @{ dir = "flower-bud-alone-cpl";   tag = "fb" }     # TARGET    (on arm exists: fb-pol)
)

foreach ($s in $subjects) {
    foreach ($arm in @("off", "on")) {
        # The two ON arms already rendered above keep their existing names.
        $tag = if ($arm -eq "on" -and $s.tag -in @("pen", "fb")) { "$($s.tag)-pol" }
               else { "$($s.tag)-p3-$arm" }
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
        Write-Output ("ARM {0,-14} rc={1} {2:N0}s" -f $tag, $rc, ((Get-Date) - $t0).TotalSeconds)
        Select-String -Path $log -Pattern "veil: gate" | ForEach-Object { Write-Output ("    " + $_.Line.Trim()) }
        if ($rc -ne 0) { Write-Output "    FAILED -- see $log" }
    }
}

Remove-Item Env:STREHL_VEIL, Env:STREHL_VEIL_MARGIN, Env:STREHL_VEIL_FLOOR -ErrorAction SilentlyContinue
Write-Output ""
Write-Output "done"
