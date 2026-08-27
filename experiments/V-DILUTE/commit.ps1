$ErrorActionPreference = 'Stop'
$repo = 'C:\dev\blog\death-of-software\projects\strehl'
$paths = @(
  'docs/research/V-DILUTE.md',
  'experiments/V-DILUTE/PREREGISTRATION.md',
  'experiments/V-DILUTE/run_queue.ps1',
  'experiments/V-DILUTE/vd_metrics.py',
  'experiments/V-DILUTE/commission.py',
  'experiments/V-DILUTE/analyze.py',
  'experiments/V-DILUTE/broi_robust.py'
)

function Invoke-GitRetry {
  param([string[]]$GitArgs)
  for ($i = 1; $i -le 30; $i++) {
    $out = & git --no-pager -C $repo @GitArgs 2>&1
    if ($LASTEXITCODE -eq 0) { return $out }
    if ("$out" -match 'index\.lock') {
      Write-Host "  index.lock busy, retry $i ..."
      Start-Sleep -Seconds 3
      continue
    }
    Write-Host "git $($GitArgs -join ' ') failed:"; Write-Host $out
    throw "git failed"
  }
  throw "git still locked after 30 retries"
}

Invoke-GitRetry (@('add','--') + $paths) | Out-Null
Write-Host "staged."
$msg = 'V-DILUTE: selection-dilution hypothesis is dead - merge is near winner-take-all at every depth'
Invoke-GitRetry (@('commit','-m',$msg,'--') + $paths)
Write-Host "---"
Invoke-GitRetry @('log','-1','--stat','--oneline')
