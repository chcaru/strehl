# ACUITY ARM: does restoring the noise-driven window shrink recover the 6.6%
# the gallery delta charged to `57e4554`?
#
# BUILD-RENDER bisected the library-wide softening to `57e4554`, which deleted
# `min(r_noise, r_geom)` in favour of `r_geom` alone. Their bisect used SEPARATE
# BINARIES from pinned `git archive` checkouts -- sound, but expensive, and it
# cannot isolate WHICH of that commit's several deletions did the damage.
#
# `STREHL_ACUITY=0|1` puts both arms in ONE binary, so this A/B differs in the
# noise term and in nothing else. That matters here specifically: this build has
# already been burned twice by comparing two pins built hours apart while other
# agents committed underneath them.
#
# `couch-fibers-cpl` is the arm that matters. It is the sharpest subject in the
# library, it is the do-no-harm control, and it took the worst hit outside the
# bees (0.9342 against the audited reference).
#
# The prediction is NOT obvious, and it can fail. `tighten_by_acuity` only ever
# LOWERS the radius, so on a subject whose geometric rule already collapses
# nearly everywhere -- which merge_cmd.rs documents as exactly couch-fibers'
# situation -- restoring the term may change almost nothing. If this arm comes
# back flat, the deletion is not the mechanism and ORCH's option 1 is wrong.

$ErrorActionPreference = "Continue"

$Exe = "C:\dev\strehl-out\pin-acuity\strehl.exe"
$Out = "C:\dev\strehl-out\ACUITY"
$Src = "D:\personal\macro"

if (-not (Test-Path $Exe)) { throw "pinned binary missing: $Exe" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0, 12)
Write-Output "BINARY $Exe"
Write-Output "SHA256 $hash  -- every arm below comes from this one file"
Write-Output ""

$subjects = @("couch-fibers-cpl", "bee-2-cpl")
$arms = @(
    @{ tag = "acu-off"; acuity = "0" },
    @{ tag = "acu-on";  acuity = "1" }
)

foreach ($s in $subjects) {
    foreach ($a in $arms) {
        $tag = "$s.$($a.tag)"
        $dst = Join-Path $Out "$tag.tif"
        if (Test-Path $dst) { Write-Output "SKIP  $tag (exists)"; continue }

        Remove-Item Env:STREHL_VEIL -ErrorAction SilentlyContinue
        $env:STREHL_ACUITY = $a.acuity

        $t0 = Get-Date
        # Redirected to a file, NOT piped through Select-Object: an early
        # pipeline stop corrupts $LASTEXITCODE, and this build has already had a
        # working guard read as inert because of exactly that.
        $log = Join-Path $Out "$tag.log"
        & $Exe stack "$Src\$s" -o $dst --linear-srgb --gate 4.0 --photometric on *>&1 |
            Out-File -Encoding utf8 $log
        $rc = $LASTEXITCODE
        $dt = ((Get-Date) - $t0).TotalSeconds

        Write-Output ("ARM {0,-28} rc={1} {2:N0}s" -f $tag, $rc, $dt)
        Select-String -Path $log -Pattern "radius rule|by radius|collapse veto" |
            ForEach-Object { Write-Output ("    " + $_.Line.Trim()) }
        if ($rc -ne 0) { Write-Output "    FAILED -- see $log" }
        Write-Output ""
    }
}

Remove-Item Env:STREHL_ACUITY -ErrorAction SilentlyContinue
Write-Output "done"
