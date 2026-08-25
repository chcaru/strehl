# Render every arm of the two-mechanism test BACK-TO-BACK FROM ONE BINARY.
#
# Three renders of one command produced three different files earlier in this
# build because other agents were landing commits mid-run. Every arm here comes
# from C:\dev\strehl-pin-1ba6dce, which was built from a `git archive` of an
# explicit SHA and commissioned with a planted sabotage that went red.
#
# ARMS
#   off   the shipped fixed-window election      -- mechanism (i) present
#   on    the adaptive-radius election (default) -- mechanism (i) treated
#   f000  ONE frame, bracket start, NO election  -- optics only
#   f298  ONE frame, bracket end,   NO election  -- optics only
#
# The two single-frame arms are the point. A merge-vs-merge comparison can only
# see what the election does. A single frame has no election, so any aura in it
# is the lens, and no selector can remove it.
#
# --linear-srgb: the project's standing rule is that quality is never judged on
# an --srgb render, because the transfer curve moves every ratio a metric
# computes.

$ErrorActionPreference = "Continue"

$Exe = "C:\dev\strehl-pin-1ba6dce\target\release\strehl.exe"
$Out = "C:\dev\strehl-out\TWOMECH"
$Src = "D:\personal\macro"
$Last = 298   # 299 frames, 0-based

if (-not (Test-Path $Exe)) { throw "pinned binary missing: $Exe" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0, 12)
Write-Output "BINARY $Exe"
Write-Output "SHA256 $hash  -- every arm below comes from this one file"
Write-Output ""

$subjects = @("lavendar-cpl", "bee-2-cpl")
$arms = @(
    @{ name = "off";  env = @{ STREHL_EDGE_AWARE = "0" } },
    @{ name = "on";   env = @{ STREHL_EDGE_AWARE = "1" } },
    @{ name = "f000"; env = @{ STREHL_ONLY_FRAME = "0" } },
    @{ name = "f298"; env = @{ STREHL_ONLY_FRAME = "$Last" } }
)

foreach ($s in $subjects) {
    foreach ($a in $arms) {
        $dst = Join-Path $Out "$s-$($a.name).tif"
        if (Test-Path $dst) { Write-Output "SKIP  $s-$($a.name) (exists)"; continue }

        # Clear BOTH hooks every time, so an arm can never inherit the previous
        # arm's environment. This is the cheapest possible guard against the
        # confound that already bit this build once.
        Remove-Item Env:STREHL_EDGE_AWARE -ErrorAction SilentlyContinue
        Remove-Item Env:STREHL_ONLY_FRAME -ErrorAction SilentlyContinue
        foreach ($k in $a.env.Keys) { Set-Item -Path "Env:$k" -Value $a.env[$k] }

        $t0 = Get-Date
        $log = & $Exe stack "$Src\$s" -o $dst --linear-srgb --gate 4.0 2>&1
        $rc = $LASTEXITCODE
        $dt = ((Get-Date) - $t0).TotalSeconds

        if ($rc -ne 0) {
            Write-Output "FAIL  $s-$($a.name) rc=$rc"
            $log | Select-Object -Last 6 | ForEach-Object { Write-Output "      $_" }
        }
        else {
            $sz = (Get-Item $dst).Length
            Write-Output ("OK    {0,-22} {1,6:N0}s  {2,12:N0} bytes" -f "$s-$($a.name)", $dt, $sz)
        }
    }
}

Remove-Item Env:STREHL_EDGE_AWARE -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_ONLY_FRAME -ErrorAction SilentlyContinue

Write-Output ""
Write-Output "=== distinctness: arms that should differ must actually differ ==="
foreach ($s in $subjects) {
    $hashes = @{}
    foreach ($a in $arms) {
        $p = Join-Path $Out "$s-$($a.name).tif"
        if (Test-Path $p) { $hashes[$a.name] = (Get-FileHash $p -Algorithm SHA256).Hash.Substring(0, 12) }
    }
    $uniq = ($hashes.Values | Sort-Object -Unique).Count
    Write-Output "$s : $($hashes.Count) arms, $uniq distinct"
    $hashes.GetEnumerator() | Sort-Object Name | ForEach-Object { Write-Output "    $($_.Key.PadRight(6)) $($_.Value)" }
    if ($uniq -ne $hashes.Count) { Write-Output "    WARNING: two arms are byte-identical -- an arm did not take effect" }
}
