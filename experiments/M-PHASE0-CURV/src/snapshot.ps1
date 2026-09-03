param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('before', 'after')]
    [string]$Label
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'out'
New-Item -ItemType Directory -Force -Path $out | Out-Null

$roots = @(
    'D:\personal\macro\requests\8-tilted-planar',
    'D:\personal\macro\requests\30-calibration-grid',
    'D:\personal\macro\flat-on-ruler-cpl',
    'D:\personal\macro\dime-flat-narrow-slices-cpl'
)

$rows = foreach ($capture in $roots) {
    $items = @(Get-ChildItem -LiteralPath $capture -Force -File -Recurse)
    $newest = $items | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    [pscustomobject]@{
        path = $capture
        file_count = $items.Count
        arw_count = @($items | Where-Object Extension -IEq '.ARW').Count
        total_bytes = [int64](($items | Measure-Object Length -Sum).Sum)
        newest_write_utc = if ($null -eq $newest) { $null } else {
            $newest.LastWriteTimeUtc.ToString('o')
        }
    }
}

$record = [ordered]@{
    label = $Label
    command = 'Get-ChildItem -LiteralPath <root> -Force -File -Recurse'
    recorded_utc = [DateTime]::UtcNow.ToString('o')
    captures = @($rows)
}
$json = $record | ConvertTo-Json -Depth 5
$path = Join-Path $out "readonly-$Label.json"
$json | Set-Content -LiteralPath $path -Encoding utf8
Write-Output $path
