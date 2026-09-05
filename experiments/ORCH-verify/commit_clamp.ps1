param()
$ErrorActionPreference = 'Continue'
Set-Location 'C:\dev\blog\death-of-software\projects\strehl'

$paths = @(
  'docs/research/ORCH-clamp-default-decision.md',
  'experiments/ORCH-verify/vclamp.py',
  'experiments/ORCH-verify/commission_vclamp.py'
)

function Invoke-GitWithRetry {
  param([string[]]$GitArgs, [int]$MaxAttempts = 8)
  for ($i = 1; $i -le $MaxAttempts; $i++) {
    $out = & git @GitArgs 2>&1
    $code = $LASTEXITCODE
    if ($code -eq 0) { return @{ ok = $true; out = $out; attempt = $i } }
    if ("$out" -match 'index\.lock') {
      Start-Sleep -Milliseconds (400 * $i)
      continue
    }
    return @{ ok = $false; out = $out; attempt = $i }
  }
  return @{ ok = $false; out = 'exhausted retries on index.lock'; attempt = $MaxAttempts }
}

$addArgs = @('add', '--') + $paths
$r = Invoke-GitWithRetry -GitArgs $addArgs
Write-Output ("add: ok={0} attempt={1}" -f $r.ok, $r.attempt)
if (-not $r.ok) { Write-Output $r.out; exit 1 }

$msg = @'
Register the clamped-default product decision prospectively

M8 fails 100% on Catmull-Rom overshoot and M172's clamp forces M8-R to
integer zero by construction, so the temptation to flip the shipping
default is real and had to be governed before any number was read.

Registering it turned up the disqualifying clause. The scorecard already
lists "destructive clipping can force a zero rate" as a known defeat and
names a conjunctive control against buying the hull result by clamping:
a future M1 AND the retained M4 flat-power-plus-transfer component. M1 is
blocker (a). So a clamped default is a legitimate product question and
NOT a route to an M8 pass while M1 is absent -- recorded as N5.

Found while verifying my own citation: M136 4.4 anchors the licence limit
at :1573-1582, which is the v1.5 legitimacy ruling instead. Correct
anchors are :1631 and :1639-1642, and M136's paraphrase silently drops
M4 from a conjunctive control. Routed to M136.

vclamp.py pins nine source quotes whitespace-collapsed plus three sited
anchors. commission_vclamp.py plants five arms: 4 caught, 0 missed, 1
inert stayed GREEN, 5 of 5 accounted, baseline restored GREEN. Arm A
first MISSED because a bare presence test for :1631 was satisfied by the
duplicate in the correction paragraph; each anchor is now pinned to its
own site.
'@
$msgFile = Join-Path $env:TEMP ('clampmsg-{0}.txt' -f [guid]::NewGuid())
# WriteAllText with a BOM-less UTF8 encoder: Set-Content -Encoding UTF8 on
# Windows PowerShell 5.1 emits a BOM, which lands in the commit subject line.
[IO.File]::WriteAllText($msgFile, $msg, (New-Object Text.UTF8Encoding($false)))

$commitArgs = @('commit', '-q', '-F', $msgFile, '--') + $paths
$r2 = Invoke-GitWithRetry -GitArgs $commitArgs
Write-Output ("commit: ok={0} attempt={1}" -f $r2.ok, $r2.attempt)
if (-not $r2.ok) { Write-Output $r2.out; Remove-Item $msgFile -Force; exit 1 }
Remove-Item $msgFile -Force

& git --no-pager log -1 --format='%H%n%s'
& git --no-pager show --stat --oneline -s HEAD | Out-Null
& git --no-pager diff-tree --no-commit-id --name-only -r HEAD
