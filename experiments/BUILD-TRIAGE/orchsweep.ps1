# Re-run the merge-vs-source comparison at ORCH's independently-chosen
# best-resolved site for every subject.
#
# Rationale: see experiments/BUILD-TRIAGE/orchsites.py.  BUILD-TRIAGE's own
# percentile selectors deliberately include the EMPTIEST sites in each frame,
# which is right for the headline and wrong for classification.  This sweep
# supplies a second, independent window per subject, chosen by a different
# agent with a different statistic.
#
# ~85 s/subject, ~37 min total.  Sequential on purpose: each compare.py run
# shells out to strehl.exe and is already internally parallel.

$ErrorActionPreference = 'Continue'
$repo = 'C:\dev\blog\death-of-software\projects\strehl'
$out  = 'C:\dev\strehl-out\BUILD-TRIAGE'
$log  = Join-Path $out 'orchsweep.log'

Set-Location $repo
New-Item -ItemType Directory -Force -Path $out | Out-Null
"=== ORCH-site sweep started $(Get-Date -Format o) ===" | Out-File $log -Encoding utf8

$subjects = python experiments/BUILD-TRIAGE/orchsites.py |
    Select-String -Pattern '^\s*\d+\s+(\S+)\s+\d+\s+(\d+),(\d+)' |
    ForEach-Object {
        [pscustomobject]@{
            Name = $_.Matches[0].Groups[1].Value
            X    = $_.Matches[0].Groups[2].Value
            Y    = $_.Matches[0].Groups[3].Value
        }
    }

"parsed $($subjects.Count) subjects" | Tee-Object -FilePath $log -Append

foreach ($s in $subjects) {
    $stamp = Get-Date -Format 'HH:mm:ss'
    "--- [$stamp] $($s.Name) @ $($s.X),$($s.Y) ---" | Tee-Object -FilePath $log -Append
    python experiments/BUILD-TRIAGE/compare.py $s.Name --tag .orch `
        --at "ORCH-BEST:$($s.X),$($s.Y)" 2>&1 | Out-File $log -Append -Encoding utf8
    if ($LASTEXITCODE -ne 0) {
        "!!! $($s.Name) exited $LASTEXITCODE" | Tee-Object -FilePath $log -Append
    }
}

"=== ORCH-site sweep finished $(Get-Date -Format o) ===" | Tee-Object -FilePath $log -Append
