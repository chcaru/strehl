# Re-run the merge-vs-source comparison across the whole corpus with the
# corrected estimator (noise-subtracted focus score for best-frame selection,
# noise-gated edge metric for the verdict). Sequential: each subject renders a
# 188 MB single frame and the disk cannot take several at once.
$ErrorActionPreference = 'Continue'
$repo = 'C:\dev\blog\death-of-software\projects\strehl'
$log  = 'C:\dev\strehl-out\BUILD-TRIAGE\sweep.ns.log'
Set-Location $repo
"sweep started $(Get-Date -Format o)" | Out-File -FilePath $log -Encoding utf8

$subjects = Get-ChildItem 'C:\dev\strehl-out\SHIP-V1\*.tiff' |
            ForEach-Object { $_.BaseName } | Sort-Object

foreach ($s in $subjects) {
    "=== $s  $(Get-Date -Format HH:mm:ss)" | Out-File -FilePath $log -Append -Encoding utf8
    & python experiments/BUILD-TRIAGE/compare.py $s --tag .ns 2>&1 |
        Out-File -FilePath $log -Append -Encoding utf8
    "--- exit $LASTEXITCODE" | Out-File -FilePath $log -Append -Encoding utf8
}
"sweep finished $(Get-Date -Format o)" | Out-File -FilePath $log -Append -Encoding utf8
