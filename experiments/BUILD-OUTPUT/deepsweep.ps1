# How large a coarse multiplier does it take to make the gate fire at levels
# 4-6 at all?
#
# WHY THIS ARM EXISTS. The five arms ORCH specified top out at 32x and every one
# of them leaves levels 4, 5 and 6 at 0.0% averaged -- the gate never fires
# there. So "raising the coarse floor does not cut mottle" would be an
# overstatement of what those arms tested: at the coarsest bands they delivered
# no dose at all, and a null response to no dose is not evidence about the
# mechanism. §14 measured why the dose is so small: the modelled band noise gain
# falls 370x from L0 (0.8898) to L3 (0.0024) while image structure does not, so
# a multiplier of 32 against a floor that is already orders of magnitude below
# the coefficients is nowhere near enough.
#
# 4096 is chosen to be absurd on purpose. If the gate still does not fire at
# levels 4-6 under a 4096x floor, that is a structural fact about the merge and
# not a question of tuning, and no value of this knob can reach the band the
# six subjects were convicted in.

$ErrorActionPreference = "Stop"
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$exe  = Join-Path $repo "target\release\strehl.exe"
$logs = "C:\dev\strehl-out\BUILD-RECERT\logs"
$six  = "coffee-bubbles,lead-1-cpl,113MSDCF,flat-on-ruler-cpl,112MSDCF,foam"

$sha = (Get-FileHash $exe -Algorithm SHA256).Hash
Write-Host "binary : $($sha.Substring(0,16))"
if ($sha.Substring(0,16) -ne "BC6FA3C787A18CAA") {
    throw "REFUSED: binary changed mid-experiment. The arms would not be comparable."
}

$arms = [ordered]@{
    "SC-D64"   = "1,1,1,64,64,64,64"
    "SC-D4096" = "1,1,1,4096,4096,4096,4096"
}

foreach ($tag in $arms.Keys) {
    $val = $arms[$tag]
    $arm = "$tag-bc6fa3c7"
    $env:STREHL_GATE_FLOOR_SCALE = $val
    Write-Host "`n===== $arm  STREHL_GATE_FLOOR_SCALE=$val ====="
    $t0 = Get-Date
    & python (Join-Path $repo "experiments\BUILD-RECERT\recert.py") `
        --candidate $exe --arm $arm --only $six --stages "identity,render" `
        *>&1 | Tee-Object -FilePath (Join-Path $logs "scalesweep-$tag.txt")
    $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $n  = (Get-ChildItem "C:\dev\strehl-out\BUILD-RECERT\arms\$arm" -Filter "*.tiff" -ErrorAction SilentlyContinue).Count
    Write-Host "----- $arm done in ${dt}s, $n master(s)"
}
Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue
Write-Host "`nDEEP SWEEP COMPLETE"
