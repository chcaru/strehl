$ErrorActionPreference = 'Stop'
$taskOutput = $PSScriptRoot
$taskRoot = 'D:\personal\macro\requests\misc-diagnostic'
$taskNames = @('star-sand-cpl', 'crystalized-vitamin-c-cpl')
function Get-TaskInventory {
    @(foreach ($taskName in $taskNames) {
        Get-ChildItem -LiteralPath (Join-Path $taskRoot $taskName) -Force -Recurse -File |
            Sort-Object FullName | ForEach-Object {
                [pscustomobject]@{
                    stack = $taskName; path = $_.FullName; bytes = $_.Length
                    last_write_time_utc_ticks = $_.LastWriteTimeUtc.Ticks
                    attributes = $_.Attributes.ToString()
                }
            }
    })
}
$taskBefore = Get-TaskInventory
$taskBefore | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskOutput 'inventory-before.json') -Encoding utf8
$taskSelected = @(foreach ($taskName in $taskNames) {
    $taskFiles = @($taskBefore | Where-Object { $_.stack -eq $taskName -and [IO.Path]::GetExtension($_.path) -ieq '.ARW' })
    $taskIndices = @(0, [int][Math]::Floor($taskFiles.Count / 2), ($taskFiles.Count - 1))
    foreach ($taskIndex in $taskIndices) {
        [pscustomobject]@{ stack = $taskName; index = $taskIndex; frames = $taskFiles.Count; path = $taskFiles[$taskIndex].path; bytes = $taskFiles[$taskIndex].bytes }
    }
})
$taskSelected | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskOutput 'inputs.json') -Encoding utf8
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B (Join-Path $taskOutput 'extract-previews.py')
if ($LASTEXITCODE -ne 0) { throw 'Preview extraction failed' }
$taskAfter = Get-TaskInventory
$taskAfter | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskOutput 'inventory-after.json') -Encoding utf8
$taskChanges = @(Compare-Object $taskBefore $taskAfter -Property stack,path,bytes,last_write_time_utc_ticks,attributes)
if ($taskChanges.Count -ne 0) { throw 'Corpus listing changed during orientation' }
[pscustomobject]@{ inventory_method = 'Get-ChildItem -Force -Recurse -File'; before_after_listing_equal = $true; content_hash_check = $false; files = $taskBefore.Count; bytes = ($taskBefore | Measure-Object bytes -Sum).Sum; scope = 'Metadata and embedded JPEG extraction only; no full RAW pixel decode' } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'receipt.json') -Encoding utf8
