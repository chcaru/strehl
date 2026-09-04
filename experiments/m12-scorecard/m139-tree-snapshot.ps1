param(
    [Parameter(Mandatory = $true)]
    [string] $Output,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string] $MeasuredCommit,

    [Parameter(Mandatory = $true)]
    [ValidateSet('before', 'after')]
    [string] $Phase
)

$ErrorActionPreference = 'Stop'
$roots = @(
    'D:\personal\macro',
    'D:\edited\macro'
)
$utf8 = [System.Text.UTF8Encoding]::new($false)
$algorithm = [System.Security.Cryptography.HashAlgorithmName]::SHA256
$result = [ordered]@{
    schema = 1
    evidence_tag = 'VERIFIED'
    measured_commit = $MeasuredCommit.ToLowerInvariant()
    generated_utc = [DateTime]::UtcNow.ToString('o')
    phase = $Phase
    enumeration = 'Get-ChildItem -LiteralPath <root> -Force -Recurse'
    roots = @()
}

foreach ($root in $roots) {
    $resolved = (Resolve-Path -LiteralPath $root).Path
    $items = @(Get-ChildItem -LiteralPath $resolved -Force -Recurse |
        Sort-Object FullName)
    $hash = [System.Security.Cryptography.IncrementalHash]::CreateHash($algorithm)
    $fileCount = 0
    $directoryCount = 0
    [Int64] $totalBytes = 0
    foreach ($item in $items) {
        $relative = [System.IO.Path]::GetRelativePath($resolved, $item.FullName)
        $kind = if ($item.PSIsContainer) { 'D' } else { 'F' }
        [Int64] $length = if ($item.PSIsContainer) { 0 } else { $item.Length }
        if ($item.PSIsContainer) {
            $directoryCount++
        }
        else {
            $fileCount++
            $totalBytes += $length
        }
        $line = "{0}`t{1}`t{2}`t{3}`t{4}`t{5}`n" -f
            $kind,
            $relative,
            $length,
            $item.LastWriteTimeUtc.Ticks,
            [int]$item.Attributes,
            $item.LinkType
        $hash.AppendData($utf8.GetBytes($line))
    }
    $result.roots += [ordered]@{
        path = $resolved
        item_count = $items.Count
        file_count = $fileCount
        directory_count = $directoryCount
        bytes = $totalBytes
        metadata_sha256 = [Convert]::ToHexString($hash.GetHashAndReset())
    }
    $hash.Dispose()
}

$parent = Split-Path -Parent $Output
if ($parent) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
}
$json = $result | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($Output, $json + "`n", $utf8)
$result | ConvertTo-Json -Depth 8
