# Round 2: single-group four-shot renders (raw carry, no restoration, profile
# lateral colour only) for a run of consecutive planes. One render at a time.
param([int]$First = 84, [int]$Last = 116)
$ErrorActionPreference = 'Stop'
Set-Location C:\dev\blog\death-of-software\projects\strehl
$F = 'D:/StrehlCaptures/stack-1794786793543-11226'
$O = 'outputs\a7cr-fourshot-quality\series'
New-Item -ItemType Directory -Force $O | Out-Null
foreach ($k in $First..$Last) {
    $name = "one-$k"
    if (Test-Path "$O\$name.tif") { continue }
    $env = "STREHL_FRAME_PARITY=$k-$k;STREHL_PIXEL_SHIFT=remosaic;STREHL_CARRY_RGB=raw;STREHL_OPTICAL_RESTORE=off"
    $t0 = Get-Date
    $line = pwsh -NoProfile -File outputs\peak-run.ps1 "$O\$name.log" $env stack $F --demosaic --refine-ca=off --out "outputs/a7cr-fourshot-quality/series/$name.tif"
    $secs = [int]((Get-Date) - $t0).TotalSeconds
    Add-Content "$O\series-frames.txt" "$name : $line, $secs s"
}
Add-Content "$O\series-frames.txt" 'BATCH DONE'
