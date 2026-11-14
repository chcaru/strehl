[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$DesktopExe,[Parameter(Mandatory=$true)][string]$Receipt)
$ErrorActionPreference='Stop'
try {
    $program=(Resolve-Path -LiteralPath $DesktopExe).Path
    if (!(Test-Path -LiteralPath (Join-Path (Split-Path -Parent $program) 'source/desktop-source.json'))) {throw 'Expected a source-inclusive desktop package.'}
    $name='Strehl-Native-RAW-Receiver-Home-LAN'
    $rule=Get-NetFirewallRule -Name $name -ErrorAction Stop
    $port=$rule | Get-NetFirewallPortFilter
    $address=$rule | Get-NetFirewallAddressFilter
    $app=$rule | Get-NetFirewallApplicationFilter
    $previous=$app.Program
    if ($port.LocalPort -ne '8789' -or $rule.Direction -ne 'Inbound' -or $rule.Action -ne 'Allow' -or
        @($address.RemoteAddress).Count -ne 1 -or $address.RemoteAddress -notin @('10.0.0.0/24','10.0.0.0/255.255.255.0')) {
        throw 'The existing receiver rule no longer matches the scoped home LAN policy.'
    }
    $app | Set-NetFirewallApplicationFilter -Program $program
    $read=Get-NetFirewallRule -Name $name | Get-NetFirewallApplicationFilter
    if ($read.Program -ne $program) {throw 'Firewall program read-back mismatch.'}
    @{ok=$true;name=$name;previous_program=$previous;program=$read.Program;port=$port.LocalPort;remote_address=$address.RemoteAddress} |
        ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Receipt -Encoding utf8
} catch {
    @{ok=$false;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $Receipt -Encoding utf8
    exit 1
}
