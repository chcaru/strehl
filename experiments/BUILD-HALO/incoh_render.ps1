# Acceptance for the ELECTION-INCOHERENCE gate (supersedes the flatness gate).
#
# Why every arm is re-rendered rather than reusing VEILZ2's OFF arms: the OFF
# arm is not a constant of nature. It is whatever the shipped merge does in the
# tree at the moment it was built, and four other agents are committing into
# that merge tonight. An OFF arm from a different pin would make the code
# change and the tree drift indistinguishable in the difference.
#
# `coffee-bean` leads. It is out-of-sample -- it is the subject on which the
# flatness gate INVERTED (BUILD-HALO.md sec 32), so it is the one arm that can
# actually falsify this build. `flower-bud` is the in-sample subject the gate
# was designed against and it cannot, on its own, tell a fix from a fit.

$ErrorActionPreference = "Continue"

$Exe = "C:\dev\strehl-out\pin-incoh\strehl.exe"
$Out = "C:\dev\strehl-out\INCOH"
$Src = "D:\personal\macro"

if (-not (Test-Path $Exe)) { throw "pinned binary missing: $Exe" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0, 12)
Write-Output "BINARY $Exe"
Write-Output "SHA256 $hash  -- every arm below comes from this one file"
Write-Output ""

$subjects = @(
    @{ dir = "coffee-bean";            tag = "cb" },    # TARGET   out-of-sample; sec 32 inverted here
    @{ dir = "flower-bud-alone-cpl";   tag = "fb" },    # TARGET   in-sample
    @{ dir = "couch-fibers-cpl";       tag = "cf" },    # GUARD    owner-declared print-worthy
    @{ dir = "pencil-steep-angle-cpl"; tag = "pen" }    # POLARITY improve or decline
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
        Select-String -Path $log -Pattern "veil: |incoherence|collapse veto" |
            ForEach-Object { Write-Output ("    " + $_.Line.Trim()) }
        if ($rc -ne 0) { Write-Output "    FAILED -- see $log" }
    }
}

Remove-Item Env:STREHL_VEIL, Env:STREHL_VEIL_MARGIN, Env:STREHL_VEIL_FLOOR -ErrorAction SilentlyContinue
Write-Output ""
Write-Output "done"
