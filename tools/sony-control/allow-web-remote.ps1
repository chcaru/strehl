#Requires -RunAsAdministrator
# Run from the extracted portable package, only if remote connections are blocked.
# Creates one application/port/source-scoped rule; it does not disable the firewall.
$ErrorActionPreference = 'Stop'
$captureExecutable = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'Strehl-Capture.exe')).Path
$captureHash = [System.Security.Cryptography.SHA256]::Create()
try {
    $captureRuleSuffix = [System.BitConverter]::ToString($captureHash.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($captureExecutable))).Replace('-', '').Substring(0, 12)
} finally {
    $captureHash.Dispose()
}
$captureRuleName = "StrehlCaptureWeb-$captureRuleSuffix"
if (Get-NetFirewallRule -Name $captureRuleName -ErrorAction SilentlyContinue) {
    Write-Host 'The firewall rule for this copy of Strehl Capture already exists.'
} else {
    New-NetFirewallRule -Name $captureRuleName -DisplayName 'Strehl Capture web remote' `
        -Description 'Private LAN and Tailscale access to the paired capture remote.' `
        -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8787 `
        -Program $captureExecutable -RemoteAddress 'LocalSubnet', '100.64.0.0/10' `
        -Profile Any -EdgeTraversalPolicy Block | Out-Null
    Write-Host 'Enabled port 8787 for this app from the local subnet and Tailscale addresses.'
}
Write-Host "Rule name: $captureRuleName"
Write-Host 'Move the extracted package? Run this helper again from its new location.'
