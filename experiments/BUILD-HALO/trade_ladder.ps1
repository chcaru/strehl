# DOSE-RESPONSE ON THE FIX'S STRENGTH, BOTH AXES, ONE BINARY.
#
# ORCH asked for the honest shape of the trade: how much halo reduction, at how
# much couch-fibers softening, across the range of the fix's strength. This
# renders the ladder; trade_measure.py reads it.
#
# THE KNOB. STREHL_EDGE_TAU is the depth-step tolerance in frames. A pixel's
# support collapses when the guide winner field varies by more than tau across
# its box, so LOW tau = more pixels read as a silhouette = more collapse =
# STRONGER fix. Unset, it solves to (q99-q01)/8 of the guide's own robust span,
# floored at 4 -- about 37 frames on a 299-frame bracket, which is why the
# ladder brackets that value on both sides.
#
# THE TWO SUBJECTS ARE NOT INTERCHANGEABLE.
#   flower-bud-with-background-fern-cpl  the blocking defect: a hard rim on a
#                                        dark subject against bright ground.
#   couch-fibers-cpl                     the do-no-harm guard: a fibre tangle
#                                        with NO depth silhouettes, so the fix
#                                        should be a no-op on it. Any deviation
#                                        from the off arm is damage, which makes
#                                        this a placebo rather than a metric
#                                        that has to be interpreted.
#
# f221 IS THE REFERENCE, AND IT IS THE POINT. STREHL_ONLY_FRAME renders one
# frame with NO election at all, so it cannot contain a selection artifact.
# Frame 221 is what the far background of flower-bud actually elects (read off
# the election map, not guessed), i.e. the background-focused frame. The halo
# is then the merge's departure FROM it near the silhouette -- a comparison a
# merge-vs-merge ladder structurally cannot make.
#
# --linear-srgb: quality is never judged on an --srgb render, because the
# transfer curve moves every ratio a metric computes.

$ErrorActionPreference = "Continue"

$Exe = "C:\dev\strehl-pin-ce2c793\target\release\strehl.exe"
$Out = "C:\dev\strehl-out\TRADE"
$Src = "D:\personal\macro"

if (-not (Test-Path $Exe)) { throw "pinned binary missing: $Exe" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash
Write-Output "BINARY $Exe"
Write-Output "SHA256 $hash"
Write-Output "  every arm below comes from this one file, rendered back to back"
Write-Output ""

$arms = @(
    @{ name = "off";     env = @{ STREHL_EDGE_AWARE = "0" } },
    @{ name = "default"; env = @{} },
    @{ name = "tau064";  env = @{ STREHL_EDGE_AWARE = "1"; STREHL_EDGE_TAU = "64" } },
    @{ name = "tau032";  env = @{ STREHL_EDGE_AWARE = "1"; STREHL_EDGE_TAU = "32" } },
    @{ name = "tau016";  env = @{ STREHL_EDGE_AWARE = "1"; STREHL_EDGE_TAU = "16" } },
    @{ name = "tau008";  env = @{ STREHL_EDGE_AWARE = "1"; STREHL_EDGE_TAU = "8" } },
    @{ name = "tau004";  env = @{ STREHL_EDGE_AWARE = "1"; STREHL_EDGE_TAU = "4" } }
)

# ORDERING IS PART OF THE DESIGN, AND THE FIRST VERSION OF IT WAS WRONG.
# Rendering every arm of one subject before starting the other put ALL of the
# couch-fibers texture guard at the end of a 100-minute run, so a run cut short
# would have produced a halo curve with no texture axis to trade it against --
# which is not half the deliverable, it is none of it.
#
# So: interleave the subjects, and order the ladder by how much each arm tells
# you rather than by its tau. off and default are the A/B that has to exist;
# then the strong end, where the halo should be most reduced and the texture
# most damaged, because that is where the trade is decided. The weak end is
# close to off and is refinement, not evidence.
#
# The guide pass roughly doubles render cost (214 s off, 483 s default), so
# every arm dropped from the front of this list is eight minutes sooner to a
# readable curve.
$order = @("off", "default", "tau008", "tau032", "tau004", "tau016", "tau064")

$jobs = @()
# The no-election reference first: everything on the halo axis is measured
# against it, so without it the flower-bud renders cannot be scored at all.
$jobs += @{ subj = "flower-bud-with-background-fern-cpl"; arm = @{ name = "f221"; env = @{ STREHL_ONLY_FRAME = "221" } } }
foreach ($n in $order) {
    $a = $arms | Where-Object { $_.name -eq $n }
    $jobs += @{ subj = "flower-bud-with-background-fern-cpl"; arm = $a }
    $jobs += @{ subj = "couch-fibers-cpl"; arm = $a }
}

# Every hook that re-routes the election, cleared before every arm, so an arm
# can never inherit the previous one's environment. This is the same defect the
# byte-freeze registry's header describes and it has bitten this build twice.
$hooks = @("STREHL_EDGE_AWARE", "STREHL_EDGE_TAU", "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME")

$i = 0
foreach ($j in $jobs) {
    $i++
    $tag = "$($j.subj)-$($j.arm.name)"
    $dst = Join-Path $Out "$tag.tif"
    if (Test-Path $dst) { Write-Output ("SKIP  [{0,2}/{1}] {2}" -f $i, $jobs.Count, $tag); continue }

    foreach ($h in $hooks) { Remove-Item "Env:$h" -ErrorAction SilentlyContinue }
    foreach ($k in $j.arm.env.Keys) { Set-Item -Path "Env:$k" -Value $j.arm.env[$k] }

    $t0 = Get-Date
    $log = & $Exe stack "$Src\$($j.subj)" -o $dst --linear-srgb --gate 4.0 2>&1
    $rc = $LASTEXITCODE
    $dt = ((Get-Date) - $t0).TotalSeconds

    # Keep the stderr: the Acuity arm prints the solved tau and the collapsed
    # fraction, which is the only record of what the knob actually did.
    $log | Set-Content -Encoding utf8 (Join-Path $Out "$tag.log")

    if ($rc -ne 0) {
        Write-Output ("FAIL  [{0,2}/{1}] {2} rc={3}" -f $i, $jobs.Count, $tag, $rc)
        $log | Select-Object -Last 8 | ForEach-Object { Write-Output "        $_" }
    }
    else {
        Write-Output ("OK    [{0,2}/{1}] {2,-52} {3,5:N0}s" -f $i, $jobs.Count, $tag, $dt)
    }
}

foreach ($h in $hooks) { Remove-Item "Env:$h" -ErrorAction SilentlyContinue }

# COMMISSIONING THE KNOB, not just the binary. A dose-response is worthless if
# the dose is not connected: if STREHL_EDGE_TAU were ignored, every arm would
# come back byte-identical and a flat trade curve would read as "no trade".
Write-Output ""
Write-Output "=== knob potency: the ladder arms must not be byte-identical ==="
foreach ($s in @("flower-bud-with-background-fern-cpl", "couch-fibers-cpl")) {
    $h = [ordered]@{}
    foreach ($a in $arms) {
        $p = Join-Path $Out "$s-$($a.name).tif"
        if (Test-Path $p) { $h[$a.name] = (Get-FileHash $p -Algorithm SHA256).Hash.Substring(0, 12) }
    }
    $uniq = ($h.Values | Sort-Object -Unique).Count
    Write-Output "$s : $($h.Count) arms, $uniq distinct"
    $h.GetEnumerator() | ForEach-Object { Write-Output "    $($_.Key.PadRight(8)) $($_.Value)" }
    if ($uniq -lt $h.Count) {
        Write-Output "    NOTE: arms sharing a hash are a REAL result on couch-fibers (the fix"
        Write-Output "          is meant to be a no-op there) but a DEAD KNOB on flower-bud."
    }
}
