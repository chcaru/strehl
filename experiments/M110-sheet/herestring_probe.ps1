# Measure the PowerShell here-string hazard directly rather than relaying it.
#
# Claim under test (ORCH, from fact 1488): in a DOUBLE-quoted here-string
# @"..."@ a backtick is an escape introducer, so a markdown inline-code span
# `bee-3-cpl` loses BOTH the backtick AND the following letter, leaving a
# single 0x08 followed by "ee-3-cpl".
#
# Writes only to $env:TEMP. Emits raw bytes so the result is measured, not
# inferred from how the string renders.

$ErrorActionPreference = "Continue"
$tmp = Join-Path $env:TEMP "m110_herestring_probe"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

# ARM A: double-quoted here-string, the hazard.
$a = @"
subject `bee-3-cpl` and `experiments/` and `foam`
"@

# ARM B: single-quoted here-string, the prescribed fix.
$b = @'
subject `bee-3-cpl` and `experiments/` and `foam`
'@

$pa = Join-Path $tmp "arm_a.txt"
$pb = Join-Path $tmp "arm_b.txt"
[System.IO.File]::WriteAllText($pa, $a, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($pb, $b, [System.Text.Encoding]::UTF8)

function Show-Bytes($path, $label) {
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $ctrl = @($bytes | Where-Object { $_ -lt 0x20 -and $_ -ne 0x0A -and $_ -ne 0x0D })
    Write-Output "$label"
    Write-Output ("  text     : " + ([System.Text.Encoding]::UTF8.GetString($bytes)).Trim())
    Write-Output ("  bytes    : " + (($bytes | ForEach-Object { "{0:X2}" -f $_ }) -join " "))
    Write-Output ("  ctrl chars: " + $ctrl.Count)
    Write-Output ("  backticks : " + @($bytes | Where-Object { $_ -eq 0x60 }).Count)
    Write-Output ""
}

Write-Output "PowerShell $($PSVersionTable.PSVersion)"
Write-Output ""
Show-Bytes $pa 'ARM A -- @"..."@ (double-quoted)'
Show-Bytes $pb "ARM B -- @'...'@ (single-quoted)"

$ba = [System.IO.File]::ReadAllBytes($pa)
$bb = [System.IO.File]::ReadAllBytes($pb)
$ctrlA = @($ba | Where-Object { $_ -lt 0x20 -and $_ -ne 0x0A -and $_ -ne 0x0D }).Count
$ctrlB = @($bb | Where-Object { $_ -lt 0x20 -and $_ -ne 0x0A -and $_ -ne 0x0D }).Count
$tickA = @($ba | Where-Object { $_ -eq 0x60 }).Count
$tickB = @($bb | Where-Object { $_ -eq 0x60 }).Count

Write-Output "VERDICT"
Write-Output "  arm A control chars $ctrlA, backticks $tickA"
Write-Output "  arm B control chars $ctrlB, backticks $tickB"
if ($ctrlA -gt 0 -and $ctrlB -eq 0 -and $tickB -eq 6) {
    Write-Output "  CONFIRMED: double-quoted eats backticks; single-quoted preserves all 6."
} else {
    Write-Output "  NOT CONFIRMED as described -- read the byte dumps above."
}
Remove-Item -Recurse -Force $tmp
