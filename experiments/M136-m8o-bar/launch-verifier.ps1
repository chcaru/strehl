param(
    [Parameter(Mandatory = $true)][string]$Python,
    [Parameter(Mandatory = $true)][string]$Verifier,
    [string]$ExpectedVerifierSha256 = "",
    [string[]]$VerifierArguments = @(),
    [string]$VerifierArgumentsJson = "",
    [Parameter(Mandatory = $true)][string]$Receipt,
    [string]$CommissioningAttackBackup = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$LauncherContract = "M136 launch-verifier.ps1 retained-handle contract v1"
$BootstrapContract = "M136 Python argv bootstrap exact-byte exec v1"
$SharingViolation = 32
$BootstrapLines = @(
    "import hashlib, sys",
    "bootstrap_source, path, expected, contract, *verifier_args = sys.argv[1:]",
    "bootstrap_sha256 = hashlib.sha256(bootstrap_source.encode('utf-8')).hexdigest().upper()",
    "handle = open(path, 'rb')",
    "try:",
    "    raw = handle.read()",
    "finally:",
    "    handle.close()",
    "observed = hashlib.sha256(raw).hexdigest().upper()",
    "if observed != expected:",
    "    raise SystemExit('M136 verifier digest mismatch')",
    "sys.argv = [path, *verifier_args]",
    "__name__ = '__main__'",
    "__file__ = path",
    "__package__ = None",
    "__spec__ = None",
    "__cached__ = None",
    "_M136_PINNED_SOURCE = {'path': path, 'raw': raw, 'sha256': observed, 'bootstrap_sha256': bootstrap_sha256, 'contract': contract}",
    "exec(compile(raw, path, 'exec'), globals(), globals())"
)
$Bootstrap = [string]::Join("`n", $BootstrapLines)
$Utf8 = [Text.UTF8Encoding]::new($false)

function ConvertTo-Hex {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)
    return -join ($Bytes | ForEach-Object { $_.ToString("X2") })
}

function Get-StreamSha256 {
    param([Parameter(Mandatory = $true)][IO.Stream]$Stream)
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
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return (ConvertTo-Hex ($algorithm.ComputeHash($Bytes)))
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-PathSha256 {
    param([Parameter(Mandatory = $true)][string]$Path)
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

function Get-HResultLowWord {
    param([Parameter(Mandatory = $true)][Exception]$Exception)
    $current = $Exception
    while ($null -ne $current.InnerException) {
        $current = $current.InnerException
    }
    return [int]($current.HResult -band 0xFFFF)
}

function Write-JsonCreateNew {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Value
    )
    $parent = [IO.Path]::GetDirectoryName($Path)
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        [void][IO.Directory]::CreateDirectory($parent)
    }
    $payload = $Utf8.GetBytes(($Value | ConvertTo-Json -Depth 8) + "`n")
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

$PythonPath = [IO.Path]::GetFullPath($Python)
$VerifierPath = [IO.Path]::GetFullPath($Verifier)
$ReceiptPath = [IO.Path]::GetFullPath($Receipt)
if (-not [IO.File]::Exists($PythonPath)) {
    throw "Python executable is absent: $PythonPath"
}
if (-not [IO.File]::Exists($VerifierPath)) {
    throw "Verifier source is absent: $VerifierPath"
}
if ([IO.File]::Exists($ReceiptPath) -or [IO.Directory]::Exists($ReceiptPath)) {
    throw "Refusing to overwrite launcher receipt: $ReceiptPath"
}

if (
    -not [string]::IsNullOrWhiteSpace($VerifierArgumentsJson) -and
    @($VerifierArguments).Count -ne 0
) {
    throw "Use either VerifierArguments or VerifierArgumentsJson, not both"
}
if (-not [string]::IsNullOrWhiteSpace($VerifierArgumentsJson)) {
    $trimmedArguments = $VerifierArgumentsJson.Trim()
    if ($trimmedArguments -ceq "[]") {
        $VerifierArguments = @()
    }
    else {
        $parsedArguments = ConvertFrom-Json `
            -InputObject $VerifierArgumentsJson `
            -NoEnumerate
        if (-not ($parsedArguments -is [System.Array])) {
            throw "VerifierArgumentsJson must encode a JSON array"
        }
        $validatedArguments = [System.Collections.Generic.List[string]]::new()
        foreach ($argument in $parsedArguments) {
            if (-not ($argument -is [string])) {
                throw "Every verifier argument must be a string"
            }
            $validatedArguments.Add($argument)
        }
        $VerifierArguments = $validatedArguments.ToArray()
    }
}

$BootstrapSha256 = Get-BytesSha256 ($Utf8.GetBytes($Bootstrap))
$VerifierStream = $null
$ObservedVerifierSha256 = ""
$ExpectedSha256 = ""
$ExpectedSource = ""
$FinalPinnedSha256 = ""
$AttackRequested = -not [string]::IsNullOrWhiteSpace($CommissioningAttackBackup)
$AttackBackupPath = ""
$AttackLanded = $false
$AttackHResultLowWord = $null
$AttackRestoredOrUnchanged = -not $AttackRequested
$ChildStarted = $false
$ChildExitCode = $null
$Status = "LAUNCHER_ERROR"
$ErrorType = $null
$ScriptExitCode = 1
$Caught = $null
$ChildStdout = ""
$ChildStderr = ""

try {
    $VerifierStream = [IO.File]::Open(
        $VerifierPath,
        [IO.FileMode]::Open,
        [IO.FileAccess]::Read,
        [IO.FileShare]::Read
    )
    $ObservedVerifierSha256 = Get-StreamSha256 $VerifierStream

    if ([string]::IsNullOrWhiteSpace($ExpectedVerifierSha256)) {
        $ExpectedSha256 = $ObservedVerifierSha256
        $ExpectedSource = "retained_handle"
    }
    else {
        $ExpectedSha256 = $ExpectedVerifierSha256.ToUpperInvariant()
        $ExpectedSource = "caller"
        if ($ExpectedSha256 -cnotmatch "^[0-9A-F]{64}$") {
            throw "Expected verifier SHA-256 must be 64 uppercase hexadecimal digits"
        }
        if ($ExpectedSha256 -cne $ObservedVerifierSha256) {
            throw "Expected verifier SHA-256 does not match retained verifier bytes"
        }
    }

    if ($AttackRequested) {
        $AttackBackupPath = [IO.Path]::GetFullPath($CommissioningAttackBackup)
        if (
            [string]::Equals(
                $AttackBackupPath,
                $VerifierPath,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "Commissioning attack backup must differ from verifier path"
        }
        if (
            [IO.File]::Exists($AttackBackupPath) -or
            [IO.Directory]::Exists($AttackBackupPath)
        ) {
            throw "Commissioning attack backup already exists"
        }
        try {
            [IO.File]::Move($VerifierPath, $AttackBackupPath)
            $AttackLanded = $true
        }
        catch {
            $AttackHResultLowWord = Get-HResultLowWord $_.Exception
            if ($AttackHResultLowWord -ne $SharingViolation) {
                throw "Commissioning rename did not fail with sharing violation"
            }
        }

        if ($AttackLanded) {
            $VerifierStream.Dispose()
            $VerifierStream = $null
            if ([IO.File]::Exists($VerifierPath)) {
                throw "Attack landed but verifier pathname is unexpectedly occupied"
            }
            [IO.File]::Move($AttackBackupPath, $VerifierPath)
            $AttackRestoredOrUnchanged = (
                [IO.File]::Exists($VerifierPath) -and
                -not [IO.File]::Exists($AttackBackupPath) -and
                (Get-PathSha256 $VerifierPath) -ceq $ObservedVerifierSha256
            )
            if (-not $AttackRestoredOrUnchanged) {
                throw "Attack landed and accepted verifier bytes were not restored"
            }
            $FinalPinnedSha256 = $ObservedVerifierSha256
            $Status = "REFUSED_ATTACK_LANDED"
            $ScriptExitCode = 1
        }
        else {
            if (
                -not [IO.File]::Exists($VerifierPath) -or
                [IO.File]::Exists($AttackBackupPath)
            ) {
                throw "Denied commissioning rename changed the verifier pathname"
            }
            $AttackRestoredOrUnchanged = $true
        }
    }

    if (-not $AttackLanded) {
        $info = [Diagnostics.ProcessStartInfo]::new()
        $info.FileName = $PythonPath
        $info.UseShellExecute = $false
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        foreach ($argument in @(
            "-I",
            "-B",
            "-c",
            $Bootstrap,
            $Bootstrap,
            $VerifierPath,
            $ExpectedSha256,
            $BootstrapContract
        )) {
            [void]$info.ArgumentList.Add($argument)
        }
        foreach ($argument in @($VerifierArguments)) {
            [void]$info.ArgumentList.Add($argument)
        }

        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $info
        try {
            if (-not $process.Start()) {
                throw "Could not start Python verifier child"
            }
            $ChildStarted = $true
            $stdoutTask = $process.StandardOutput.ReadToEndAsync()
            $stderrTask = $process.StandardError.ReadToEndAsync()
            $process.WaitForExit()
            $ChildStdout = $stdoutTask.GetAwaiter().GetResult()
            $ChildStderr = $stderrTask.GetAwaiter().GetResult()
            $ChildExitCode = [int]$process.ExitCode
        }
        finally {
            $process.Dispose()
        }

        if ($ChildStdout.Length -gt 0) {
            [Console]::Out.Write($ChildStdout)
        }
        if ($ChildStderr.Length -gt 0) {
            [Console]::Error.Write($ChildStderr)
        }
        $FinalPinnedSha256 = Get-StreamSha256 $VerifierStream
        if ($FinalPinnedSha256 -cne $ObservedVerifierSha256) {
            throw "Retained verifier bytes changed while Python was running"
        }
        $Status = "CHILD_EXIT"
        $ScriptExitCode = $ChildExitCode
    }
}
catch {
    $Caught = $_
    $ErrorType = $_.Exception.GetType().FullName
    $Status = "LAUNCHER_ERROR"
    $ScriptExitCode = 1
}
finally {
    if ($null -ne $VerifierStream) {
        $VerifierStream.Dispose()
        $VerifierStream = $null
    }
    if (
        $AttackLanded -and
        -not [string]::IsNullOrWhiteSpace($AttackBackupPath) -and
        [IO.File]::Exists($AttackBackupPath) -and
        -not [IO.File]::Exists($VerifierPath)
    ) {
        try {
            [IO.File]::Move($AttackBackupPath, $VerifierPath)
            $AttackRestoredOrUnchanged = (
                (Get-PathSha256 $VerifierPath) -ceq $ObservedVerifierSha256
            )
        }
        catch {
            $AttackRestoredOrUnchanged = $false
        }
    }
}

$receiptObject = [ordered]@{
    schema = "m136-launch-verifier-receipt-v1"
    schema_version = 1
    status = $Status
    launcher_contract = $LauncherContract
    bootstrap_contract = $BootstrapContract
    bootstrap_sha256 = $BootstrapSha256
    verifier_sha256 = $ObservedVerifierSha256
    expected_verifier_sha256 = $ExpectedSha256
    expected_verifier_source = $ExpectedSource
    verifier_sha256_after_child = $FinalPinnedSha256
    attack = [ordered]@{
        requested = $AttackRequested
        landed = $AttackLanded
        hresult_low_word = $AttackHResultLowWord
        restored_or_unchanged = $AttackRestoredOrUnchanged
    }
    child = [ordered]@{
        started = $ChildStarted
        exit_code = $ChildExitCode
    }
    error_type = $ErrorType
}

try {
    Write-JsonCreateNew -Path $ReceiptPath -Value $receiptObject
}
catch {
    Write-Error $_
    exit 1
}
if ($null -ne $Caught) {
    Write-Error $Caught
}
exit $ScriptExitCode
