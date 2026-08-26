# Commission the default-ON lateral-CA change, on pixels rather than on a log line.
#
# A log line saying "profile applied" is a claim the binary makes about itself.
# Four arms from ONE pinned binary, compared by file hash, is a claim about the
# image. The two disagree exactly when the wiring is broken, which is the case
# this exists to catch.
#
#   default   no flag, env cleared      -> expect the profile to apply
#   explicit  --fix-ca <key>            -> must be BYTE-IDENTICAL to default
#   off       --fix-ca off              -> must DIFFER from default
#   typo      --fix-ca not-a-profile    -> must exit non-zero
#
# The identity pair is the load-bearing one. "Default differs from off" alone is
# satisfied by any change whatsoever, including a bug; "default equals the
# explicit profile AND differs from off" pins down which of the two states the
# default landed in.
#
# Rendered WITHOUT --srgb. Results in this project have been retracted for
# measuring on a display-space render; the tone curve is not invertible and it
# is not what the correction acts on.

param(
    [string]$Exe = 'C:\dev\strehl-out\BUILD-RENDER-target\release\strehl.exe',
    [string]$Subject = 'D:\personal\macro\flat-on-ruler-cpl',
    [string]$Out = 'C:\dev\strehl-out\BUILD-RENDER-cadefault',
    [string]$Key = 'a7c2-fe100gm-2xtc-x4cpl'
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$label = Split-Path $Subject -Leaf

$binHash = (Get-FileHash $Exe -Algorithm SHA256).Hash
Write-Host "binary  : $Exe"
Write-Host "sha256  : $binHash"
Write-Host "subject : $label"
Write-Host ""

function Invoke-Arm {
    param([string]$Name, [string[]]$Extra)
    $tif = Join-Path $Out "$label-$Name.tif"
    $log = Join-Path $Out "$label-$Name.log"
    if (Test-Path $tif) { Remove-Item $tif -Force }
    # Cleared for EVERY arm, so an arm's result depends only on its own flag and
    # not on what a previous arm left in the environment.
    Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
    $argv = @('stack', "`"$Subject`"", '--out', "`"$tif`"", '--demosaic') + $Extra
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $Exe -ArgumentList $argv -NoNewWindow -PassThru `
        -RedirectStandardError $log -RedirectStandardOutput "$log.out"
    $null = $p.Handle
    $p.WaitForExit()
    $sw.Stop()
    $exit = $p.ExitCode
    $hash = if (Test-Path $tif) { (Get-FileHash $tif -Algorithm SHA256).Hash } else { '(no output)' }
    [pscustomobject]@{
        arm = $Name; exit = $exit; secs = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        sha256 = $hash; tif = $tif; log = $log
    }
}

$arms = @()
$arms += Invoke-Arm -Name 'default'  -Extra @()
$arms += Invoke-Arm -Name 'explicit' -Extra @('--fix-ca', $Key)
$arms += Invoke-Arm -Name 'off'      -Extra @('--fix-ca', 'off')
$arms += Invoke-Arm -Name 'typo'     -Extra @('--fix-ca', 'not-a-profile')

$arms | Format-Table arm, exit, secs, @{n='sha256'; e={ $_.sha256.Substring(0, [Math]::Min(16, $_.sha256.Length)) }} -AutoSize

$d = $arms | Where-Object arm -eq 'default'
$e = $arms | Where-Object arm -eq 'explicit'
$o = $arms | Where-Object arm -eq 'off'
$t = $arms | Where-Object arm -eq 'typo'

$checks = @(
    @{ n = 'default renders'                              ; ok = ($d.exit -eq 0) }
    @{ n = 'explicit renders'                             ; ok = ($e.exit -eq 0) }
    @{ n = 'off renders'                                  ; ok = ($o.exit -eq 0) }
    @{ n = 'default == explicit  (default applies profile)'; ok = ($d.sha256 -eq $e.sha256) }
    @{ n = 'default != off       (default is not off)'    ; ok = ($d.sha256 -ne $o.sha256) }
    @{ n = 'typo exits non-zero  (no silent no-op)'       ; ok = ($t.exit -ne 0) }
    @{ n = 'typo wrote no output'                         ; ok = (-not (Test-Path $t.tif)) }
)

Write-Host ''
$fail = 0
foreach ($c in $checks) {
    $v = if ($c.ok) { 'PASS' } else { 'FAIL'; }
    if (-not $c.ok) { $fail++ }
    Write-Host ("  [{0}] {1}" -f $v, $c.n)
}
Write-Host ''
if ($fail -eq 0) {
    Write-Host "COMMISSIONED: $($checks.Count)/$($checks.Count) arms correct." -ForegroundColor Green
} else {
    Write-Host "NOT COMMISSIONED: $fail of $($checks.Count) checks failed." -ForegroundColor Red
}

$rep = Join-Path $Out 'COMMISSION.txt'
$lines = @(
    "commissioning of the default-ON lateral-CA change",
    "binary  : $Exe",
    "sha256  : $binHash",
    "subject : $Subject",
    "key     : $Key",
    "when    : $(Get-Date -Format o)",
    ""
) + ($arms | ForEach-Object { "{0,-9} exit={1} {2,7}s {3}" -f $_.arm, $_.exit, $_.secs, $_.sha256 }
) + @('') + ($checks | ForEach-Object { "[{0}] {1}" -f $(if ($_.ok) { 'PASS' } else { 'FAIL' }), $_.n })
$lines | Out-File -Encoding utf8 $rep
Write-Host "wrote : $rep"
exit $fail
