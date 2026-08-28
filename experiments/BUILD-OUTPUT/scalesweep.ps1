# Render the STREHL_GATE_FLOOR_SCALE sweep over the six mottle-convicted
# subjects, one arm per scale setting, ALL AT ONE BINARY.
#
# WHY A BASE ARM IS RENDERED RATHER THAN ADOPTED
# `arms/HEAD-f190a0ea` already holds 26 masters and it is tempting to reuse it
# as the unset-env control. It is not one. `git log f190a0ea..HEAD -- crates/`
# is five commits, and two of them change the path these renders take:
# `5f367a94 fix(exposure): stop --auto-exposure double-normalising the srgb
# render` (every master here is `--srgb --auto-exposure`) and `8a480af9
# pyramid: n_eff`. An arm rendered by a different binary cannot be the control
# for an env var, because the difference it reports is the env var plus five
# commits and nothing separates them.
#
# The null arm `1,1,1,1,1,1,1` must come out BYTE-IDENTICAL to BASE. That is
# this sweep's own instrument check: if the null differs, the env var is doing
# something other than what it says, and every other arm's difference is
# uninterpretable.

$ErrorActionPreference = "Stop"
$repo = "C:\dev\blog\death-of-software\projects\strehl"
$exe  = Join-Path $repo "target\release\strehl.exe"
$logs = "C:\dev\strehl-out\BUILD-RECERT\logs"
$six  = "coffee-bubbles,lead-1-cpl,113MSDCF,flat-on-ruler-cpl,112MSDCF,foam"

$sha = (Get-FileHash $exe -Algorithm SHA256).Hash
Write-Host "binary : $($sha.Substring(0,16))  $((Get-Item $exe).Length) bytes"
if ($sha.Substring(0,16) -eq "44C2F2CD2E5B2894") {
    throw "REFUSED: that is the SHIPPING PIN, not a candidate."
}

# arm tag -> scale value ($null means leave the variable UNSET)
$arms = [ordered]@{
    "SC-BASE"  = $null
    "SC-NULL"  = "1,1,1,1,1,1,1"
    "SC-4"     = "1,4,4,4,4,4,4"
    "SC-8"     = "1,8,8,8,8,8,8"
    "SC-16"    = "1,16,16,16,16,16,16"
    "SC-RAMP"  = "1,1,4,16,32,32,32"
}

foreach ($tag in $arms.Keys) {
    $val = $arms[$tag]
    $arm = "$tag-bc6fa3c7"
    $log = Join-Path $logs "scalesweep-$tag.txt"

    if ($null -eq $val) { Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue }
    else                { $env:STREHL_GATE_FLOOR_SCALE = $val }

    $shown = if ($null -eq $val) { "(unset)" } else { $val }
    Write-Host "`n===== $arm  STREHL_GATE_FLOOR_SCALE=$shown ====="
    $t0 = Get-Date

    # The env var is read by the renderer through inherited environment; recert
    # copies os.environ into the PowerShell child (recert.py:149).
    & python (Join-Path $repo "experiments\BUILD-RECERT\recert.py") `
        --candidate $exe --arm $arm --only $six --stages "identity,render" `
        *>&1 | Tee-Object -FilePath $log

    $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $n  = (Get-ChildItem "C:\dev\strehl-out\BUILD-RECERT\arms\$arm" -Filter "*.tiff" -ErrorAction SilentlyContinue).Count
    Write-Host "----- $arm done in ${dt}s, $n master(s)"
    Add-Content $log "`nARM $arm  scale=$shown  elapsed=${dt}s  masters=$n"
}

Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue
Write-Host "`nSWEEP COMPLETE"
