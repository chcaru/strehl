param(
    [string]$Python = "C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe",
    [string]$Root = "C:\dev\blog\death-of-software\projects\strehl\experiments\M136-m8o-bar",
    [string]$CommissionReport = "",
    [string]$Result = "",
    [string]$Log = "",
    [string]$Work = "",
    [string]$LaunchReceipt = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Verifier = Join-Path $Root "verifier_m136.py"
$Launcher = Join-Path $Root "launch-verifier.ps1"
$BootstrapPreregistration = Join-Path $Root "bootstrap-contract-preregistration.md"
$Preregistration = Join-Path $Root "clamped-m8o-preregistration.json"
$Interpretation = Join-Path $Root "prospective-interpretations.md"
if ([string]::IsNullOrWhiteSpace($CommissionReport)) {
    $CommissionReport = Join-Path $Root "verifier-commission-candidate.json"
}
if ([string]::IsNullOrWhiteSpace($Result)) {
    $Result = Join-Path $Root "verifier-recommission-result.json"
}
if ([string]::IsNullOrWhiteSpace($Log)) {
    $Log = Join-Path $Root "verifier-recommission.log"
}
if ([string]::IsNullOrWhiteSpace($Work)) {
    $Work = Join-Path $Root "rc"
}
if ([string]::IsNullOrWhiteSpace($LaunchReceipt)) {
    $LaunchReceipt = Join-Path $Root "verifier-launch-receipt.json"
}

$ExpectedLauncherContract = "M136 launch-verifier.ps1 retained-handle contract v1"
$ExpectedBootstrapContract = "M136 Python argv bootstrap exact-byte exec v1"
$Utf8 = [Text.UTF8Encoding]::new($false)

function ConvertTo-Hex {
    param([Parameter(Mandatory)][byte[]]$Bytes)
    return -join ($Bytes | ForEach-Object { $_.ToString("X2") })
}

function Get-StreamSha256 {
    param([Parameter(Mandatory)][IO.Stream]$Stream)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        $Stream.Position = 0
        $digest = $algorithm.ComputeHash($Stream)
        $Stream.Position = 0
        return (ConvertTo-Hex $digest)
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-BytesSha256 {
    param([Parameter(Mandatory)][byte[]]$Bytes)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return (ConvertTo-Hex ($algorithm.ComputeHash($Bytes)))
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-PinnedFileSha256 {
    param([Parameter(Mandatory)][string]$Path)
    $stream = [IO.File]::Open(
        $Path,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    try {
        return (Get-StreamSha256 $stream)
    }
    finally {
        $stream.Dispose()
    }
}

function Read-PinnedJson {
    param([Parameter(Mandatory)][string]$Path)
    $stream = [IO.File]::Open(
        $Path,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    try {
        $memory = [IO.MemoryStream]::new()
        try {
            $stream.CopyTo($memory)
            $bytes = $memory.ToArray()
        }
        finally {
            $memory.Dispose()
        }
        $text = [Text.UTF8Encoding]::new($false, $true).GetString($bytes)
        return [ordered]@{
            document = ($text | ConvertFrom-Json)
            sha256 = Get-BytesSha256 $bytes
        }
    }
    finally {
        $stream.Dispose()
    }
}

function Write-Json {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][object]$Value
    )
    [IO.File]::WriteAllText(
        $Path,
        (($Value | ConvertTo-Json -Depth 8) + "`n"),
        $Utf8
    )
}

function Write-TextCreateNew {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Text
    )
    $payload = $Utf8.GetBytes($Text)
    $stream = [IO.File]::Open(
        $Path,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::Read
    )
    try {
        $stream.Write($payload, 0, $payload.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

function Write-Result {
    param(
        [Parameter(Mandatory)][string]$Status,
        [Parameter(Mandatory)][int]$ExitCode,
        [Parameter(Mandatory)][string]$Detail,
        [string]$CommissionSha256 = "",
        [string]$LauncherSha256 = "",
        [string]$VerifierSha256 = "",
        [string]$BootstrapSha256 = "",
        [string]$LauncherContract = "",
        [string]$BootstrapContract = "",
        [string]$LaunchReceiptSha256 = "",
        [string]$BootstrapPreregistrationSha256 = ""
    )
    Write-Json -Path $Result -Value ([ordered]@{
        schema = "m136-verifier-recommission-result-v2"
        status = $Status
        exit_code = $ExitCode
        detail = $Detail
        trust_root = (
            "operator-invoked recommission wrapper/current PowerShell process, " +
            "Windows share-mode semantics, and approved Python runtime/dependencies"
        )
        launcher = [ordered]@{
            path = $Launcher
            sha256 = $LauncherSha256
            contract = $LauncherContract
        }
        verifier = [ordered]@{
            path = $Verifier
            sha256 = $VerifierSha256
            contract = "M136 independent verifier v1"
        }
        bootstrap = [ordered]@{
            contract = $BootstrapContract
            sha256 = $BootstrapSha256
        }
        bootstrap_contract_preregistration = [ordered]@{
            path = $BootstrapPreregistration
            sha256 = $BootstrapPreregistrationSha256
        }
        preregistration = $Preregistration
        interpretation = $Interpretation
        commission_report = $CommissionReport
        commission_sha256 = $CommissionSha256
        launch_receipt = $LaunchReceipt
        launch_receipt_sha256 = $LaunchReceiptSha256
        log = $Log
    })
}

if (Test-Path -LiteralPath $Result) {
    throw "Refusing to overwrite prior result: $Result"
}

$LauncherSha256 = ""
$VerifierSha256 = ""
$BootstrapSha256 = ""
$LauncherContract = ""
$BootstrapContract = ""
$LaunchReceiptSha256 = ""
$CommissionSha256 = ""
$BootstrapPreregistrationSha256 = ""
$LauncherStream = $null

try {
    foreach ($path in @(
        $Python,
        $Verifier,
        $Launcher,
        $BootstrapPreregistration,
        $Preregistration,
        $Interpretation
    )) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required file is absent: $path"
        }
    }
    foreach ($path in @($CommissionReport, $Log, $Work, $LaunchReceipt)) {
        if (Test-Path -LiteralPath $path) {
            throw "Refusing to reuse output path: $path"
        }
    }
    if ($PSVersionTable.PSEdition -cne "Core") {
        throw "Recommissioning requires the current PowerShell Core process"
    }
    $PowerShellHost = [Environment]::ProcessPath
    if (
        [string]::IsNullOrWhiteSpace($PowerShellHost) -or
        -not (Test-Path -LiteralPath $PowerShellHost -PathType Leaf)
    ) {
        throw "Current PowerShell process path is unavailable"
    }

    $BootstrapPreregistrationSha256 = Get-PinnedFileSha256 $BootstrapPreregistration
    Write-Result -Status "RUNNING" -ExitCode -1 -Detail "Commissioning started"

    $env:OMP_NUM_THREADS = "1"
    $env:OPENBLAS_NUM_THREADS = "1"
    $env:MKL_NUM_THREADS = "1"
    $env:NUMEXPR_NUM_THREADS = "1"

    $LauncherStream = [IO.File]::Open(
        $Launcher,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    $LauncherSha256 = Get-StreamSha256 $LauncherStream

    $verifierArguments = @(
        "commission",
        "--preregistration",
        $Preregistration,
        "--report",
        $CommissionReport,
        "--work-dir",
        $Work
    )
    $verifierArgumentsJson = ConvertTo-Json -Compress -InputObject (
        [object[]]$verifierArguments
    )
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $PowerShellHost
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    foreach ($argument in @(
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $Launcher,
        "-Python",
        $Python,
        "-Verifier",
        $Verifier,
        "-Receipt",
        $LaunchReceipt,
        "-VerifierArgumentsJson",
        $verifierArgumentsJson
    )) {
        [void]$info.ArgumentList.Add($argument)
    }
    $info.Environment["OMP_NUM_THREADS"] = "1"
    $info.Environment["OPENBLAS_NUM_THREADS"] = "1"
    $info.Environment["MKL_NUM_THREADS"] = "1"
    $info.Environment["NUMEXPR_NUM_THREADS"] = "1"
    $info.Environment["M136_RECOMMISSION_POWERSHELL"] = $PowerShellHost

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $info
    try {
        if (-not $process.Start()) {
            throw "Could not start retained launcher"
        }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        $code = [int]$process.ExitCode
    }
    finally {
        $process.Dispose()
    }
    if ($stdout.Length -gt 0) {
        [Console]::Out.Write($stdout)
    }
    if ($stderr.Length -gt 0) {
        [Console]::Error.Write($stderr)
    }
    Write-TextCreateNew -Path $Log -Text (
        "STDOUT`n" + $stdout + "`nSTDERR`n" + $stderr
    )

    if (-not (Test-Path -LiteralPath $LaunchReceipt -PathType Leaf)) {
        throw "Launcher did not write its receipt"
    }
    $receiptCapture = Read-PinnedJson $LaunchReceipt
    $receipt = $receiptCapture.document
    $LaunchReceiptSha256 = $receiptCapture.sha256
    $LauncherContract = [string]$receipt.launcher_contract
    $BootstrapContract = [string]$receipt.bootstrap_contract
    $BootstrapSha256 = [string]$receipt.bootstrap_sha256
    $VerifierSha256 = [string]$receipt.verifier_sha256
    if (
        $receipt.schema -cne "m136-launch-verifier-receipt-v1" -or
        $receipt.schema_version -ne 1 -or
        $receipt.status -cne "CHILD_EXIT" -or
        $receipt.child.started -ne $true -or
        $receipt.child.exit_code -ne $code -or
        $receipt.expected_verifier_source -cne "retained_handle" -or
        $receipt.expected_verifier_sha256 -cne $VerifierSha256 -or
        $receipt.verifier_sha256_after_child -cne $VerifierSha256 -or
        $receipt.attack.requested -ne $false -or
        $receipt.attack.landed -ne $false -or
        $receipt.error_type -ne $null
    ) {
        throw "Launcher receipt does not prove retained same-byte execution"
    }
    if (
        $LauncherContract -cne $ExpectedLauncherContract -or
        $BootstrapContract -cne $ExpectedBootstrapContract
    ) {
        throw "Launcher/bootstrap contract identity is wrong"
    }
    if ($code -ne 0) {
        throw "Verifier commissioning exited $code"
    }
    if (-not (Test-Path -LiteralPath $CommissionReport -PathType Leaf)) {
        throw "Verifier commissioning did not write its report"
    }
    $reportCapture = Read-PinnedJson $CommissionReport
    $report = $reportCapture.document
    $CommissionSha256 = $reportCapture.sha256
    if ($report.status -cne "PASS") {
        throw "Verifier commissioning report status is not PASS"
    }
    if (
        $report.protocol -cne "M136 independent verifier v1" -or
        $report.verifier.sha256 -cne $VerifierSha256 -or
        $report.bootstrap_execution_identity.launcher_contract -cne
            $LauncherContract -or
        $report.bootstrap_execution_identity.bootstrap_contract -cne
            $BootstrapContract -or
        $report.bootstrap_execution_identity.bootstrap_sha256 -cne
            $BootstrapSha256 -or
        $report.verifier_bootstrap_substitution.status -cne "PASS"
    ) {
        throw "Commission report does not bind launcher/verifier/bootstrap identities"
    }
    Write-Result -Status "PASS" -ExitCode 0 -Detail "Commissioning passed" `
        -CommissionSha256 $CommissionSha256 `
        -LauncherSha256 $LauncherSha256 `
        -VerifierSha256 $VerifierSha256 `
        -BootstrapSha256 $BootstrapSha256 `
        -LauncherContract $LauncherContract `
        -BootstrapContract $BootstrapContract `
        -LaunchReceiptSha256 $LaunchReceiptSha256 `
        -BootstrapPreregistrationSha256 $BootstrapPreregistrationSha256
    exit 0
}
catch {
    Write-Result -Status "FAIL" -ExitCode 1 -Detail $_.Exception.Message `
        -CommissionSha256 $CommissionSha256 `
        -LauncherSha256 $LauncherSha256 `
        -VerifierSha256 $VerifierSha256 `
        -BootstrapSha256 $BootstrapSha256 `
        -LauncherContract $LauncherContract `
        -BootstrapContract $BootstrapContract `
        -LaunchReceiptSha256 $LaunchReceiptSha256 `
        -BootstrapPreregistrationSha256 $BootstrapPreregistrationSha256
    Write-Error $_
    exit 1
}
finally {
    if ($null -ne $LauncherStream) {
        $LauncherStream.Dispose()
        $LauncherStream = $null
    }
}
