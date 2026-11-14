param([string]$InputPath, [string]$OutputFolder, [string]$ArchiveTool)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
if (-not $ArchiveTool) { $ArchiveTool = Join-Path $PSScriptRoot 'strehl-raw-archive.exe' }
if (-not (Test-Path -LiteralPath $ArchiveTool -PathType Leaf)) { throw 'strehl-raw-archive.exe is missing beside this script' }
if (-not $InputPath) {
    $picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $picker.Description = 'Select the captured stack folder containing .ARW.straw files'
    if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $InputPath = $picker.SelectedPath
    $picker.Dispose()
}
if (-not $OutputFolder) {
    $picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $picker.Description = 'Select a separate folder for the restored original ARWs'
    if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $OutputFolder = $picker.SelectedPath
    $picker.Dispose()
}
$source = (Resolve-Path -LiteralPath $InputPath).Path
if (Test-Path -LiteralPath $source -PathType Leaf) { $source = Split-Path -Parent $source }
[System.IO.Directory]::CreateDirectory($OutputFolder) | Out-Null
$destination = (Resolve-Path -LiteralPath $OutputFolder).Path
if ($source.TrimEnd('\') -eq $destination.TrimEnd('\')) { throw 'Choose a different folder so a stack never contains two copies of each exposure' }
& $ArchiveTool restore $InputPath --output-dir $destination
$result = $LASTEXITCODE
if ($result -ne 0) { throw "Restore stopped (exit $result). Existing originals and compressed files are unchanged." }
[System.Windows.Forms.MessageBox]::Show('Original ARWs restored and checksum verified. Compressed source files were kept.', 'Strehl RAW restore') | Out-Null
