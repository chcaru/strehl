param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Draw", "Verify")]
    [string]$Action,

    [string]$AlgorithmCommit = ""
)

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$repo = (Resolve-Path (Join-Path $root "..\..")).Path
$privateDir = Join-Path $root "private"
$cipherPath = Join-Path $privateDir "scored-seed.dpapi"
$publicPath = Join-Path $root "scored-seed-commitment.json"
$entropy = [Text.Encoding]::ASCII.GetBytes("strehl-m190-m10-scored-seed-v1")
$prefix = [Text.Encoding]::ASCII.GetBytes("M10-SYNTH-SEED-COMMIT-V1`0")

function Get-LowerHex([byte[]]$Bytes) {
    return [Convert]::ToHexString($Bytes).ToLowerInvariant()
}

function Get-Sha256([byte[]]$Bytes) {
    return [Security.Cryptography.SHA256]::HashData($Bytes)
}

function Get-Commitment([byte[]]$Seed) {
    if ($Seed.Length -ne 32) {
        throw "seed length must be exactly 32 bytes"
    }
    $preimage = New-Object byte[] ($prefix.Length + $Seed.Length)
    [Array]::Copy($prefix, 0, $preimage, 0, $prefix.Length)
    [Array]::Copy($Seed, 0, $preimage, $prefix.Length, $Seed.Length)
    return Get-LowerHex (Get-Sha256 $preimage)
}

if ($Action -eq "Draw") {
    if ($AlgorithmCommit -notmatch "^[0-9a-f]{40}$") {
        throw "-AlgorithmCommit must be the 40-character algorithm-precommit SHA"
    }
    if ((Test-Path $cipherPath) -or (Test-Path $publicPath)) {
        throw "refusing a second draw: seed escrow or public commitment already exists"
    }

    [IO.Directory]::CreateDirectory($privateDir) | Out-Null
    $seed = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Fill($seed)
    try {
        $commitment = Get-Commitment $seed
        $cipher = [Security.Cryptography.ProtectedData]::Protect(
            $seed,
            $entropy,
            [Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        [IO.File]::WriteAllBytes($cipherPath, $cipher)
        $public = [ordered]@{
            schema = "strehl.m10-scored-seed-commitment.v1"
            algorithm_precommit = $AlgorithmCommit
            draw_count = 1
            seed_bytes = 32
            draw_source = "System.Security.Cryptography.RandomNumberGenerator.Fill"
            commitment_algorithm = "SHA256(ASCII('M10-SYNTH-SEED-COMMIT-V1') || 0x00 || seed[32])"
            commitment_sha256 = $commitment
            escrow = [ordered]@{
                relative_path = "private/scored-seed.dpapi"
                format = "Windows DPAPI CurrentUser with fixed M190 entropy"
                ciphertext_byte_length = $cipher.Length
                ciphertext_sha256 = Get-LowerHex (Get-Sha256 $cipher)
            }
            disclosure_gate = @(
                "candidate executable hash frozen",
                "candidate settings hash frozen",
                "common-input manifest hash frozen",
                "campaign manifest committed",
                "candidate process receives rendered frames but not the seed or truth",
                "latent truth is released only after candidate product hashes are frozen"
            )
        }
        $json = $public | ConvertTo-Json -Depth 8
        [IO.File]::WriteAllText(
            $publicPath,
            $json + "`n",
            [Text.UTF8Encoding]::new($false)
        )
        Write-Output "DRAW_COUNT 1"
        Write-Output "COMMITMENT_SHA256 $commitment"
        Write-Output "CIPHERTEXT_BYTES $($cipher.Length)"
        Write-Output "CIPHERTEXT_SHA256 $($public.escrow.ciphertext_sha256)"
        Write-Output "SEED_PLAINTEXT_NOT_PRINTED"
    }
    finally {
        [Array]::Clear($seed, 0, $seed.Length)
    }
    exit 0
}

if (-not (Test-Path $cipherPath)) {
    throw "missing private scored-seed escrow"
}
if (-not (Test-Path $publicPath)) {
    throw "missing public scored-seed commitment"
}

$public = Get-Content -Raw -Encoding UTF8 $publicPath | ConvertFrom-Json
$cipher = [IO.File]::ReadAllBytes($cipherPath)
$cipherHash = Get-LowerHex (Get-Sha256 $cipher)
if ($cipher.Length -ne [int]$public.escrow.ciphertext_byte_length) {
    throw "ciphertext byte length mismatch"
}
if ($cipherHash -cne [string]$public.escrow.ciphertext_sha256) {
    throw "ciphertext SHA-256 mismatch"
}

$seed = [Security.Cryptography.ProtectedData]::Unprotect(
    $cipher,
    $entropy,
    [Security.Cryptography.DataProtectionScope]::CurrentUser
)
try {
    $commitment = Get-Commitment $seed
    if ($commitment -cne [string]$public.commitment_sha256) {
        throw "seed commitment mismatch"
    }
    $env:M190_SCORED_SEED_HEX = Get-LowerHex $seed
    Push-Location $repo
    try {
        $output = & python experiments\M190-m10-definition-freeze\verify_freeze.py 2>&1
        $code = $LASTEXITCODE
    }
    finally {
        Pop-Location
        Remove-Item Env:\M190_SCORED_SEED_HEX -ErrorAction SilentlyContinue
    }
    $output | ForEach-Object { Write-Output $_ }
    if ($code -ne 0) {
        throw "verify_freeze.py failed with exit $code"
    }
    Write-Output "ESCROW_COMMITMENT PASS"
    Write-Output "SEED_PLAINTEXT_NOT_PRINTED"
}
finally {
    [Array]::Clear($seed, 0, $seed.Length)
}
