[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$DesktopExe,
    [Parameter(Mandatory=$true)][string]$Receipt
)
$ErrorActionPreference='Stop'
try {
    $program=(Resolve-Path -LiteralPath $DesktopExe).Path
    if (!(Test-Path -LiteralPath (Join-Path (Split-Path -Parent $program) 'source/desktop-source.json'))) {
        throw 'Expected a source-inclusive Strehl package.'
    }
    $name='Strehl-Native-RAW-Receiver-Home-LAN'
    if (Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue) {
        throw 'The named rule already exists; inspect it instead of replacing it.'
    }
    New-NetFirewallRule -Name $name -DisplayName 'Strehl native RAW receiver - home LAN only' -Direction Inbound -Action Allow -Enabled True -Protocol TCP -LocalPort 8789 -RemoteAddress '10.0.0.0/24' -Profile Any -Program $program | Out-Null
    $rule=Get-NetFirewallRule -Name $name
    $port=$rule | Get-NetFirewallPortFilter
    $address=$rule | Get-NetFirewallAddressFilter
    $app=$rule | Get-NetFirewallApplicationFilter
    if ($port.LocalPort -ne '8789' -or $app.Program -ne $program -or $rule.Action -ne 'Allow') {throw 'Firewall read-back mismatch.'}
    @{ok=$true;name=$name;program=$app.Program;port=$port.LocalPort;remote_address=$address.RemoteAddress} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Receipt -Encoding utf8
} catch {
    @{ok=$false;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $Receipt -Encoding utf8
    exit 1
}
