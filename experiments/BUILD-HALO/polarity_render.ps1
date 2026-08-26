# POLARITY ARM: does the shipped upper envelope invert on a BRIGHT subject?
#
# Every subject in this build's evidence set is dark-on-bright, so nothing
# measured so far could have caught a sign error. `pencil-steep-angle-cpl` is
# the reversed case ORCH classified: backdrop 0.369, subject 0.686.
#
# The prediction, from reading `apply_veil`: `backdrop` is the GLOBAL p90 of
# merged green. When the subject is the bright population, p90 lands on the
# SUBJECT, the floor (0.5 x that) falls BELOW the true backdrop, and backdrop
# pixels become eligible -- at which point an upper envelope selects the
# MOST-veiled sample at every one of them.
#
# This is a prediction that can fail. If the floor happens to exclude the
# backdrop anyway, the arm is a no-op and the shipped code is accidentally
# safe. Either answer is worth the render; a guess is not.
#
# Both arms come from ONE binary, and the veil env is cleared between them so
# an arm cannot inherit the previous one's environment.

$ErrorActionPreference = "Continue"

$Exe = "C:\dev\strehl-out\pin-veil2\strehl.exe"
$Out = "C:\dev\strehl-out\VEIL"
$Src = "D:\personal\macro"
$Subject = "pencil-steep-angle-cpl"

if (-not (Test-Path $Exe)) { throw "pinned binary missing: $Exe" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null

$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash.Substring(0, 12)
Write-Output "BINARY $Exe"
Write-Output "SHA256 $hash  -- both arms below come from this one file"
Write-Output ""

$arms = @(
    @{ tag = "pen-pm-off"; env = @{} },
    @{ tag = "pen-pm-fl";  env = @{ STREHL_VEIL = "1.5"; STREHL_VEIL_MARGIN = "3"; STREHL_VEIL_FLOOR = "0.5" } }
)

foreach ($a in $arms) {
    $dst = Join-Path $Out "$($a.tag).tif"
    if (Test-Path $dst) { Write-Output "SKIP  $($a.tag) (exists)"; continue }

    Remove-Item Env:STREHL_VEIL        -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_VEIL_MARGIN -ErrorAction SilentlyContinue
    Remove-Item Env:STREHL_VEIL_FLOOR  -ErrorAction SilentlyContinue
    foreach ($k in $a.env.Keys) { Set-Item -Path "Env:$k" -Value $a.env[$k] }

    $t0 = Get-Date
    # Redirected to a file, NOT piped through Select-Object: an early pipeline
    # stop corrupts $LASTEXITCODE and this build has already had a working
    # guard read as inert because of exactly that.
    $log = Join-Path $Out "$($a.tag).log"
    & $Exe stack "$Src\$Subject" -o $dst --linear-srgb --gate 4.0 --photometric on *>&1 |
        Out-File -Encoding utf8 $log
    $rc = $LASTEXITCODE
    $dt = ((Get-Date) - $t0).TotalSeconds

    Write-Output ("ARM {0,-12} rc={1} {2:N0}s" -f $a.tag, $rc, $dt)
    Select-String -Path $log -Pattern "veil:|gain span|photometric" |
        ForEach-Object { Write-Output ("    " + $_.Line.Trim()) }
    if ($rc -ne 0) { Write-Output "    FAILED -- see $log" }
    Write-Output ""
}

Remove-Item Env:STREHL_VEIL        -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_VEIL_MARGIN -ErrorAction SilentlyContinue
Remove-Item Env:STREHL_VEIL_FLOOR  -ErrorAction SilentlyContinue
Write-Output "done"
