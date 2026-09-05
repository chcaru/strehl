param(
    [string]$Python = "C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe",
    [string]$Root = "C:\dev\blog\death-of-software\projects\strehl\experiments\M136-m8o-bar",
    [string]$CommissionReport = "",
    [string]$Result = "",
    [string]$Log = "",
    [string]$Work = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Verifier = Join-Path $Root "verifier_m136.py"
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

function Write-Result {
    param(
        [Parameter(Mandatory)][string]$Status,
        [Parameter(Mandatory)][int]$ExitCode,
        [Parameter(Mandatory)][string]$Detail,
        [string]$CommissionSha256 = ""
    )
    [ordered]@{
        schema = "m136-verifier-recommission-result-v1"
        status = $Status
        exit_code = $ExitCode
        detail = $Detail
        verifier = $Verifier
        preregistration = $Preregistration
        interpretation = $Interpretation
        commission_report = $CommissionReport
        commission_sha256 = $CommissionSha256
        log = $Log
        completed_utc = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Result -Encoding utf8
}

if (Test-Path -LiteralPath $Result) {
    throw "Refusing to overwrite prior result: $Result"
}

try {
    foreach ($path in @($Python, $Verifier, $Preregistration, $Interpretation)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required file is absent: $path"
        }
    }
    foreach ($path in @($CommissionReport, $Log, $Work)) {
        if (Test-Path -LiteralPath $path) {
            throw "Refusing to reuse output path: $path"
        }
    }

    $fixedLine = "100 * np.indices((8, 8), dtype=np.float64)[0]"
    $oldLine = "8 * np.indices((8, 8), dtype=np.float64)[0]"
    $verifierLines = @(Get-Content -LiteralPath $Verifier)
    if (@($verifierLines | Where-Object { $_.Trim() -ceq $fixedLine }).Count -ne 1) {
        throw "Corrected crop-fixture line is not uniquely present"
    }
    if (@($verifierLines | Where-Object { $_.Trim() -ceq $oldLine }).Count -ne 0) {
        throw "Obsolete crop-fixture line remains present"
    }

    Write-Result -Status "RUNNING" -ExitCode -1 -Detail "Commissioning started"

    $env:OMP_NUM_THREADS = "1"
    $env:OPENBLAS_NUM_THREADS = "1"
    $env:MKL_NUM_THREADS = "1"
    $env:NUMEXPR_NUM_THREADS = "1"

    & $Python -B $Verifier commission `
        --preregistration $Preregistration `
        --report $CommissionReport `
        --work-dir $Work *> $Log
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "Verifier commissioning exited $code"
    }
    if (-not (Test-Path -LiteralPath $CommissionReport -PathType Leaf)) {
        throw "Verifier commissioning did not write its report"
    }
    $report = Get-Content -LiteralPath $CommissionReport -Raw | ConvertFrom-Json
    if ($report.status -cne "PASS") {
        throw "Verifier commissioning report status is not PASS"
    }
    $reportHash = (Get-FileHash -LiteralPath $CommissionReport -Algorithm SHA256).Hash
    Write-Result -Status "PASS" -ExitCode 0 -Detail "Commissioning passed" `
        -CommissionSha256 $reportHash
    exit 0
}
catch {
    Write-Result -Status "FAIL" -ExitCode 1 -Detail $_.Exception.Message
    Write-Error $_
    exit 1
}
