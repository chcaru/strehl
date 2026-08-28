param([string[]]$Paths, [string]$MsgFile)

# Shared tree: other agents commit concurrently, so index.lock contention is
# expected. Retry, never delete the lock. Every git call is gated on
# $LASTEXITCODE captured IMMEDIATELY, because a silently failed `add` makes the
# following path-scoped `commit` fail with a misleading "pathspec did not
# match" for files that were never staged.

function Invoke-GitRetry {
    param([string[]]$GitArgs, [int]$Tries = 12)
    for ($i = 1; $i -le $Tries; $i++) {
        $out = & git @GitArgs 2>&1
        $rc = $LASTEXITCODE
        if ($rc -eq 0) {
            Write-Output ("  ok (attempt {0}): git {1}" -f $i, ($GitArgs -join ' '))
            return $true
        }
        if ($out -match 'index\.lock') {
            Write-Output ("  attempt {0}: index.lock held, backing off" -f $i)
            Start-Sleep -Seconds ([Math]::Min(15, 2 * $i))
            continue
        }
        Write-Output ("  FAILED rc={0}: {1}" -f $rc, ($out -join ' | '))
        return $false
    }
    Write-Output "  FAILED: lock never released"
    return $false
}

foreach ($p in $Paths) {
    if (-not (Invoke-GitRetry -GitArgs (@('add', '--') + $p))) { exit 1 }
}
if (-not (Invoke-GitRetry -GitArgs (@('commit', '-q', '-F', $MsgFile, '--') + $Paths))) { exit 1 }
Write-Output "committed"
git --no-pager show --stat --oneline HEAD | Select-Object -First 20
exit 0
