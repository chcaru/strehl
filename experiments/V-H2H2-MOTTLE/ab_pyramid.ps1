# Is the significance fix live ON THE SHIPPING PATH?
#
# The byte-freeze suite cannot answer this: `byte-freeze.rs:574` hardcodes
# `--merge estimator` for every row, while `merge_cmd.rs:429` sets
# `DEFAULT_MERGE_BACKEND = Pyramid`. So the freezes exercise a backend this
# change cannot reach, and their byte-identical result across arms 0/1/1000 is a
# fact about the harness, not about the fix.
#
# This renders the same 20-frame stack on the PYRAMID backend at three arms:
#   0    -- off, must reproduce the shipping merge bit for bit
#   1    -- the value derived from the noise model, no fitted constant
#   1000 -- POTENCY. r_floor = 3.02 is enormous; nearly every coefficient should
#           collapse toward a plain mean. If 1000x is byte-identical to 0, the
#           code path is dead and no measurement of it means anything. This arm
#           exists because arms 0 and 1 alone cannot tell "too small to matter"
#           from "never executed" -- both render identical bytes.
#
# Same binary for every arm, hashed before and after, because a shared tree with
# a dozen lanes in it can rebuild strehl.exe underneath a measurement.

$ErrorActionPreference = "Stop"
$root  = "C:\dev\blog\death-of-software\projects\strehl"
$cli   = Join-Path $root "target\release\strehl.exe"
$stack = "D:\personal\macro\coffee-bean"
$outdir = Join-Path $env:TEMP "vh2h2-sig"
New-Item -ItemType Directory -Force -Path $outdir | Out-Null

function CliSha { (Get-FileHash -Algorithm SHA256 $cli).Hash }
$sha0 = CliSha
Write-Host "strehl.exe sha256: $sha0"
Write-Host "stack            : $stack (limit 20, --merge pyramid)"
Write-Host ""

$res = @{}
foreach ($arm in @("0", "1", "1000")) {
    $env:STREHL_PYRAMID_SIGNIFICANCE = $arm
    $out = Join-Path $outdir "arm-$arm.tif"
    Remove-Item $out -ErrorAction SilentlyContinue
    $ErrorActionPreference = "Continue"
    $log = & $cli stack $stack --merge pyramid -l 20 -o $out 2>&1 | Out-String -Width 4096
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ((CliSha) -ne $sha0) { Write-Host "VOID: strehl.exe changed during arm $arm"; exit 2 }
    if ($rc -ne 0 -or -not (Test-Path $out)) {
        $res[$arm] = "FAILED(rc=$rc)"
        Write-Host ("arm {0,-5} -> FAILED rc={1}" -f $arm, $rc)
        ($log -split "`n" | Select-Object -Last 12) | ForEach-Object { Write-Host "    $_" }
        continue
    }
    $res[$arm] = (Get-FileHash -Algorithm SHA256 $out).Hash
    # The merge banner's own duty-cycle line, which is where a change in how
    # much the merge averages should show up first.
    $avg = ($log -split "`n" | Select-String -Pattern 'averaged\s+:' | Select-Object -First 1)
    Write-Host ("arm {0,-5} -> {1}" -f $arm, $res[$arm])
    if ($avg) { Write-Host ("           {0}" -f $avg.ToString().Trim()) }
}
Remove-Item Env:STREHL_PYRAMID_SIGNIFICANCE -ErrorAction SilentlyContinue
if ((CliSha) -ne $sha0) { Write-Host "VOID: strehl.exe moved across the run"; exit 2 }

Write-Host ""
$off = $res["0"]; $on = $res["1"]; $hot = $res["1000"]
if ($off -like "FAILED*" -or $on -like "FAILED*" -or $hot -like "FAILED*") {
    Write-Host "INCONCLUSIVE: an arm failed to render; nothing is comparable."
    exit 1
}
Write-Host ("x1    vs off : {0}" -f $(if ($on  -eq $off) { "SAME  -- derived strength moves no byte" } else { "DIFFERS -- the fix is live at the derived strength" }))
Write-Host ("x1000 vs off : {0}" -f $(if ($hot -eq $off) { "SAME  -- THE PATH IS DEAD; potency control FAILED" } else { "DIFFERS -- the path executes; potency confirmed" }))
if ($hot -eq $off) {
    Write-Host ""
    Write-Host "VERDICT: no conclusion may be drawn about the fix. A 1000x floor that"
    Write-Host "         changes nothing means the code is not running."
} elseif ($on -eq $off) {
    Write-Host ""
    Write-Host "VERDICT: the path is live but the DERIVED strength is below the output"
    Write-Host "         quantiser. The mechanism is real; its magnitude at the value the"
    Write-Host "         noise model actually implies is nil."
}
