# M97: is M100's 54A5E20F freeze actually broken, or is its RECORD incomplete?
#
# 2f11005 established that three "false breaks" tonight were fixtures whose
# record omitted a binding parameter -- "bee-3-cpl lost --gate, coffee-bean lost
# STREHL_ALIGN" -- and that "the renderer never moved".
#
# M100 3.3 records the fixture literally as `bee-3-cpl --limit 60`. No --gate,
# no STREHL_ALIGN. Both the orchestrator's freeze_control.ps1 and my first run
# used `--gate 2`, and both got CF266004 rather than 54A5E20F.
#
# So test M100's fixture AS WRITTEN, across the two bindings rule 47 now
# requires and its record omits. If any cell reproduces 54A5E20F, the freeze is
# intact and the defect is in the record, not the renderer.
#
#   E  no --gate, STREHL_ALIGN=0   (isolated path)
#   F  no --gate, aligned default  (integrated path)
#   G  --gate 2,  STREHL_ALIGN=0   (already have: 257A0DBD)
#   H  --gate 2,  aligned default  (already have: CF266004)

$ErrorActionPreference = "Continue"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\bee-3-cpl"
$out = "C:\dev\strehl-out\M97\freeze"
$FROZEN = "54A5E20F44255BB526C61D4397D239D6F1D26A06D54A8A56FBC944B91B37E7A2"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\M97\cache"

function Go($tag, $gate, $align) {
    $f = "$out\$tag.tif"
    if (Test-Path $f) { Remove-Item $f -Force }
    if ($align -eq $null) { Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue }
    else { $env:STREHL_ALIGN = $align }
    $a = @($dir, "--limit", "60", "--out", $f)
    if ($gate -ne $null) { $a += @("--gate", $gate) }
    & $exe stack @a 2>&1 | Out-Null
    Remove-Item Env:\STREHL_ALIGN -ErrorAction SilentlyContinue
    if (-not (Test-Path $f)) { return "NO-OUTPUT" }
    return (Get-FileHash $f -Algorithm SHA256).Hash
}

$rows = @()
$rows += ,@("E  no-gate  ALIGN=0", (Go "E" $null "0"))
$rows += ,@("F  no-gate  aligned", (Go "F" $null $null))
$rows += ,@("G  gate 2   ALIGN=0", (Go "G" "2" "0"))
$rows += ,@("H  gate 2   aligned", (Go "H" "2" $null))

Write-Output ""
Write-Output "M100 recorded : $FROZEN"
Write-Output ""
foreach ($r in $rows) {
    $mark = if ($r[1] -eq $FROZEN) { "  <== REPRODUCES M100" } else { "" }
    Write-Output ("{0} : {1}{2}" -f $r[0], $r[1], $mark)
}
Write-Output ""
$hit = @($rows | Where-Object { $_[1] -eq $FROZEN })
if ($hit.Count -ge 1) {
    Write-Output "VERDICT: the freeze HOLDS. The renderer did not move; M100's record"
    Write-Output "         omitted a binding parameter, exactly as 2f11005 describes."
} else {
    Write-Output "VERDICT: no cell reproduces 54A5E20F. Either a further parameter is"
    Write-Output "         unbound, or the measurement path genuinely moved. ESCALATE."
}
