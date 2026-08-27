# BUILD-GATE acceptance matrix: does the measured floor make the two gather
# arms CONVERGE on the `averaged` fraction?
#
# Four configs per subject: {plane, fullres} x {white floor, measured floor}.
# An align-refused subject is the placebo and must move exactly 0.0, because a
# frame that is never warped never calls the probe.
param(
    [string[]]$Subjects,
    [int]$Limit = 12,
    [string]$OutDir = "C:\dev\strehl-out\BUILD-GATE\matrix"
)
$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$exe = "C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe"

function Run-One($subject, $arm, $floor) {
    $tag = "$subject-g$arm-$floor"
    $log = Join-Path $OutDir "$tag.log"
    if (-not (Test-Path $log)) {
        $env:STREHL_FULLRES_GATHER = $arm
        $env:STREHL_GATE_FLOOR = $floor
        & $exe stack "D:\personal\macro\$subject" --limit $Limit `
            --out (Join-Path $OutDir "$tag.tif") *>&1 | Out-File -FilePath $log -Encoding utf8
    }
    $m = Select-String -Path $log -Pattern "^\s*averaged\s+:" | Select-Object -First 1
    if (-not $m) { return $null }
    $nums = [regex]::Matches($m.Line, "([0-9.]+)%") | ForEach-Object { [double]$_.Groups[1].Value }
    $f = Select-String -Path $log -Pattern "folded\s+:\s+(\d+) / (\d+)" | Select-Object -First 1
    [pscustomobject]@{
        b0     = $nums[0]
        b1     = $nums[1]
        b2     = $nums[2]
        folded = if ($f) { "$($f.Matches[0].Groups[1].Value)/$($f.Matches[0].Groups[2].Value)" } else { "?" }
    }
}

$out = @()
foreach ($s in $Subjects) {
    $d = @{}
    foreach ($arm in @("0", "1")) {
        foreach ($floor in @("white", "measured")) { $d["$arm-$floor"] = Run-One $s $arm $floor }
    }
    if ($d["0-white"] -and $d["1-white"] -and $d["0-measured"] -and $d["1-measured"]) {
        $out += [pscustomobject]@{
            subject = $s
            folded  = $d["1-white"].folded
            planeW  = $d["0-white"].b0
            fullW   = $d["1-white"].b0
            planeM  = $d["0-measured"].b0
            fullM   = $d["1-measured"].b0
        }
    }
    else { Write-Host "$s INCOMPLETE" }
}

Write-Host ""
Write-Host "band 0 `averaged` fraction, %   (W = white floor / shipping, M = measured floor / fixed)"
Write-Host ("{0,-22} {1,7} {2,8} {3,8} {4,8} {5,8} {6,8} {7,8}" -f `
        "subject", "folded", "planeW", "fullW", "|gap|W", "planeM", "fullM", "|gap|M")
Write-Host ("-" * 82)
foreach ($r in $out) {
    Write-Host ("{0,-22} {1,7} {2,8:N1} {3,8:N1} {4,8:N2} {5,8:N1} {6,8:N1} {7,8:N2}" -f `
            $r.subject, $r.folded, $r.planeW, $r.fullW, [Math]::Abs($r.fullW - $r.planeW), `
            $r.planeM, $r.fullM, [Math]::Abs($r.fullM - $r.planeM))
}
$gw = ($out | ForEach-Object { [Math]::Abs($_.fullW - $_.planeW) } | Measure-Object -Average).Average
$gm = ($out | ForEach-Object { [Math]::Abs($_.fullM - $_.planeM) } | Measure-Object -Average).Average
Write-Host ("-" * 82)
Write-Host ("mean arm gap: white {0:N2} pp -> measured {1:N2} pp   ({2})" -f $gw, $gm,
    $(if ($gm -lt $gw) { "CONVERGED" } else { "DIVERGED" }))
