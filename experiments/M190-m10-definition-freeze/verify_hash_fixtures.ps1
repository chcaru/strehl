$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$fixtures = Get-Content -Raw -Encoding UTF8 (Join-Path $root "fixtures.json") |
    ConvertFrom-Json -Depth 100

function Get-BytesFromHex([string]$Hex) {
    return [Convert]::FromHexString($Hex)
}

function Get-LowerHex([byte[]]$Bytes) {
    return [Convert]::ToHexString($Bytes).ToLowerInvariant()
}

function Get-Sha256([byte[]]$Bytes) {
    return [Security.Cryptography.SHA256]::HashData($Bytes)
}

function Join-Bytes([byte[][]]$Parts) {
    $length = 0
    foreach ($part in $Parts) {
        $length += $part.Length
    }
    $result = New-Object byte[] $length
    $offset = 0
    foreach ($part in $Parts) {
        [Array]::Copy($part, 0, $result, $offset, $part.Length)
        $offset += $part.Length
    }
    return $result
}

function Get-U32BE([uint32]$Value) {
    return [byte[]]@(
        [byte](($Value -shr 24) -band 0xff)
        [byte](($Value -shr 16) -band 0xff)
        [byte](($Value -shr 8) -band 0xff)
        [byte]($Value -band 0xff)
    )
}

function Get-U16BE([uint16]$Value) {
    return [byte[]]@(
        [byte](($Value -shr 8) -band 0xff)
        [byte]($Value -band 0xff)
    )
}

function Assert-Equal($Observed, $Expected, [string]$Name) {
    if ($Observed -cne $Expected) {
        throw "$Name mismatch: observed=$Observed expected=$Expected"
    }
    Write-Output "PASS $Name"
}

$quotaPrefix = [Text.Encoding]::UTF8.GetBytes("M10-POP-V1|")
$cellBytes = [Text.Encoding]::UTF8.GetBytes([string]$fixtures.quota_hash.cell_id)
$quotaPreimage = Join-Bytes @($quotaPrefix, $cellBytes)
$quotaDigest = Get-Sha256 $quotaPreimage
Assert-Equal (Get-LowerHex $quotaPreimage) ([string]$fixtures.quota_hash.preimage_utf8_hex) "quota preimage bytes"
Assert-Equal (Get-LowerHex $quotaDigest) ([string]$fixtures.quota_hash.digest_sha256_lowerhex) "quota SHA-256"
$quotaLittleEndian = New-Object byte[] 33
for ($i = 0; $i -lt 32; $i++) {
    $quotaLittleEndian[$i] = $quotaDigest[31 - $i]
}
$quotaInteger = [Numerics.BigInteger]::new($quotaLittleEndian)
Assert-Equal ($quotaInteger.ToString()) ([string]$fixtures.quota_hash.unsigned_256_big_endian_decimal) "quota big-endian uint256"

$artifactBytes = Get-BytesFromHex ([string]$fixtures.raw_artifact_hash.input_hex)
Assert-Equal $artifactBytes.Length ([int]$fixtures.raw_artifact_hash.byte_length) "artifact byte length"
Assert-Equal (Get-LowerHex (Get-Sha256 $artifactBytes)) ([string]$fixtures.raw_artifact_hash.sha256_lowerhex) "artifact SHA-256 lowerhex"

$seed = Get-BytesFromHex ([string]$fixtures.seed_commitment.seed_hex)
$seedPrefix = [Text.Encoding]::ASCII.GetBytes("M10-SYNTH-SEED-COMMIT-V1`0")
$seedPreimage = Join-Bytes @($seedPrefix, $seed)
Assert-Equal (Get-LowerHex $seedPreimage) ([string]$fixtures.seed_commitment.preimage_hex) "seed commitment preimage"
Assert-Equal (Get-LowerHex (Get-Sha256 $seedPreimage)) ([string]$fixtures.seed_commitment.digest_sha256_lowerhex) "seed commitment SHA-256"

$prfPrefix = [Text.Encoding]::ASCII.GetBytes("M10-SYNTH-PRF-V1`0")
$paramLabel = [Text.Encoding]::ASCII.GetBytes("PARAM")
$paramPreimage = Join-Bytes @(
    $prfPrefix,
    $seed,
    [byte[]]@($paramLabel.Length),
    $paramLabel,
    (Get-U32BE 0)
)
Assert-Equal (Get-LowerHex $paramPreimage) ([string]$fixtures.synthetic_prf.parameter_block.preimage_hex) "parameter PRF preimage"
Assert-Equal (Get-LowerHex (Get-Sha256 $paramPreimage)) ([string]$fixtures.synthetic_prf.parameter_block.digest_sha256_lowerhex) "parameter PRF SHA-256"

$textureLabel = [Text.Encoding]::ASCII.GetBytes("TEX")
$texturePreimage = Join-Bytes @(
    $prfPrefix,
    $seed,
    [byte[]]@($textureLabel.Length),
    $textureLabel,
    (Get-U32BE 7),
    [byte[]]@(1, 2),
    (Get-U16BE 130),
    (Get-U16BE 111)
)
Assert-Equal (Get-LowerHex $texturePreimage) ([string]$fixtures.synthetic_prf.texture_block.preimage_hex) "texture PRF preimage"
Assert-Equal (Get-LowerHex (Get-Sha256 $texturePreimage)) ([string]$fixtures.synthetic_prf.texture_block.digest_sha256_lowerhex) "texture PRF SHA-256"
$textureDigest = Get-Sha256 $texturePreimage
$textureWord = ([int]$textureDigest[0] -shl 8) + [int]$textureDigest[1]
$textureValue = 8192 + ($textureWord % 49152)
Assert-Equal $textureValue ([int]$fixtures.synthetic_prf.texture_value.u16) "texture u16 derivation"

$raw = @()
foreach ($hex in $fixtures.origin_fit.raw_step_binary64_hex) {
    $bytes = Get-BytesFromHex ([string]$hex)
    [Array]::Reverse($bytes)
    $raw += [BitConverter]::ToDouble($bytes, 0)
}
$sum = [double]$raw[0] + [double]$raw[1] + [double]$raw[3]
$origin = $sum / 3.0
$originBytes = [BitConverter]::GetBytes($origin)
[Array]::Reverse($originBytes)
Assert-Equal (Get-LowerHex $originBytes) ([string]$fixtures.origin_fit.expected.origin_binary64_hex) "origin N=3 binary64"

Write-Output "VERDICT GREEN"
