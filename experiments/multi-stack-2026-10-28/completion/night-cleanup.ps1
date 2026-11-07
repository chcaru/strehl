# User-authorized nightly cleanup. Preserve captures, results and source archives.
$ErrorActionPreference = 'Stop'
$taskRoot = 'C:\Users\chris\.codex\worktrees\multi-stack\strehl'
$taskStorage = 'D:\codex-work\multi-stack-2026-10-28'
$taskSource = Join-Path $taskRoot 'outputs\multi-stack\completion\mosaic-source-cache'
$taskDestination = Join-Path $taskStorage 'mosaic-source-cache'
$taskReceipt = Join-Path $taskRoot 'outputs\multi-stack\night-checkpoint\cleanup.json'

function Assert-LocalTaskDirectory([string]$LiteralPath) {
    $resolved = (Resolve-Path -LiteralPath $LiteralPath).ProviderPath.TrimEnd('\')
    if (-not $resolved.StartsWith($taskRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Cleanup path leaves the explicit task workspace: $resolved"
    }
    $item = Get-Item -LiteralPath $resolved -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Cleanup requires a real task directory, not a link: $resolved"
    }
    $ancestor = $item.Parent
    while ($ancestor.FullName -ne $taskRoot) {
        if ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Cleanup ancestor is a link: $($ancestor.FullName)"
        }
        $ancestor = $ancestor.Parent
        if ($null -eq $ancestor) { throw 'Workspace ancestor not found' }
    }
    foreach ($entry in Get-ChildItem -LiteralPath $resolved -Force -Recurse) {
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Cleanup subtree contains a link: $($entry.FullName)"
        }
    }
    return $resolved
}

if (Test-Path -LiteralPath $taskReceipt) { throw 'Cleanup receipt already exists; do not repeat blindly' }
if (Test-Path -LiteralPath $taskDestination) { throw 'Cache destination already exists; inspect before reuse' }
$taskSource = Assert-LocalTaskDirectory $taskSource
if ($taskSource -ne (Join-Path $taskRoot 'outputs\multi-stack\completion\mosaic-source-cache')) {
    throw 'Resolved source differs from the explicitly named cache'
}
$resolvedStorage = (Resolve-Path -LiteralPath $taskStorage).ProviderPath.TrimEnd('\')
if ($resolvedStorage -ne 'D:\codex-work\multi-stack-2026-10-28') { throw 'Unexpected storage root' }
if ((Get-Item -LiteralPath $resolvedStorage).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Storage root is a link'
}
$snapshot = @(Get-ChildItem -LiteralPath $taskSource -File -Recurse -Force | Sort-Object FullName)
$bytes = ($snapshot | Measure-Object Length -Sum).Sum
if ($snapshot.Count -eq 0 -or (Get-PSDrive D).Free -lt ($bytes + 10GB)) { throw 'Insufficient copy space or empty cache' }
$receipt = [ordered]@{
    schema = 'strehl.night-cleanup.v1'; started_utc = [DateTime]::UtcNow.ToString('o')
    state = 'copying'; free_c_before = (Get-PSDrive C).Free; free_d_before = (Get-PSDrive D).Free
    source = $taskSource; destination = $taskDestination; source_bytes = $bytes
    verified_files = @(); removed = @()
}
function Save-Receipt { $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $taskReceipt -Encoding utf8 }
Save-Receipt
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$verified = [Collections.Generic.List[object]]::new()
foreach ($file in $snapshot) {
    $relative = $file.FullName.Substring($taskSource.Length + 1)
    $destination = Join-Path $taskDestination $relative
    $parent = Split-Path -Parent $destination
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    $originalHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $file.FullName -Destination $destination
    $copiedHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    $after = Get-Item -LiteralPath $file.FullName
    if ($originalHash -ne $copiedHash -or $after.Length -ne $file.Length -or $after.LastWriteTimeUtc -ne $file.LastWriteTimeUtc) {
        throw "Cache copy verification failed: $relative"
    }
    $verified.Add([ordered]@{ relative = $relative; bytes = $file.Length; sha256 = $originalHash; modified_utc = $file.LastWriteTimeUtc.ToString('o') })
    if ($verified.Count % 100 -eq 0) { Write-Output "Verified $($verified.Count)/$($snapshot.Count) cache files" }
}
$current = @(Get-ChildItem -LiteralPath $taskSource -File -Recurse -Force | Sort-Object FullName)
if ($current.Count -ne $snapshot.Count) { throw 'Source cache census changed during copy' }
for ($i=0; $i -lt $current.Count; $i++) {
    if ($current[$i].FullName -ne $snapshot[$i].FullName -or $current[$i].Length -ne $snapshot[$i].Length -or $current[$i].LastWriteTimeUtc -ne $snapshot[$i].LastWriteTimeUtc) {
        throw 'Source cache changed before relocation'
    }
}
$receipt.verified_files = $verified.ToArray()
$receipt.state = 'verified-copy'
Save-Receipt
$checkedSource = Assert-LocalTaskDirectory $taskSource
if ($checkedSource -ne $taskSource) { throw 'Source path changed before removal' }
Remove-Item -LiteralPath $checkedSource -Recurse -Force
New-Item -ItemType Junction -Path $taskSource -Target $taskDestination | Out-Null
$junction = Get-Item -LiteralPath $taskSource -Force
if ($junction.LinkType -ne 'Junction' -or $junction.Target -ne $taskDestination) { throw 'Cache junction verification failed' }
$receipt.state = 'relocated'
Save-Receipt

$cleanupPaths = @(
    'outputs\multi-stack\prefetch-cache-a1', 'outputs\multi-stack\prefetch-cache-a2',
    'outputs\multi-stack\prefetch-cache-b1', 'outputs\multi-stack\prefetch-cache-b2',
    'target\debug\incremental'
)
foreach ($relative in $cleanupPaths) {
    $path = Join-Path $taskRoot $relative
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $checked = Assert-LocalTaskDirectory $path
    if ($checked -ne $path) { throw 'Resolved cleanup directory differs' }
    $files = @(Get-ChildItem -LiteralPath $checked -File -Recurse -Force)
    $size = ($files | Measure-Object Length -Sum).Sum
    Remove-Item -LiteralPath $checked -Recurse -Force
    $receipt.removed += [ordered]@{ path = $checked; files = $files.Count; logical_bytes = $size }
    Save-Receipt
    Write-Output "Removed regenerable cache: $relative ($size bytes)"
}
$receipt.state = 'complete'
$receipt.finished_utc = [DateTime]::UtcNow.ToString('o')
$receipt.free_c_after = (Get-PSDrive C).Free
$receipt.free_d_after = (Get-PSDrive D).Free
$receipt.reclaimed_c_bytes = $receipt.free_c_after - $receipt.free_c_before
Save-Receipt
Write-Output ([pscustomobject]$receipt | Select-Object state, source_bytes, reclaimed_c_bytes, free_c_after, free_d_after | ConvertTo-Json)
