# BUILD-SOFTGATE render harness.
#
# AGENTS.md rule 47: the whole invocation, including the environment, travels
# with every hash. This script IS the record -- it builds the command and the
# environment together so they cannot drift apart.
#
# AGENTS.md rule 46: never read $LASTEXITCODE through a truncating pipeline.
# Output and code are captured in two statements and the code is asserted
# against an EXACT expected value, never "-ne 0".
#
# AGENTS.md rule 45: STREHL_WARPMAP is pinned into this lane's scratch. This
# lane's independent variable is the ADMISSION KERNEL, not the gather kernel,
# so the sidecar pin does not hold the variable under test constant.

param(
  [Parameter(Mandatory=$true)][string]$Exe,
  [Parameter(Mandatory=$true)][string]$Stack,
  [Parameter(Mandatory=$true)][int]$Limit,
  [Parameter(Mandatory=$true)][string]$Out,
  [string]$SoftGate = 'unset',       # 'unset' is a VALUE, spelled out.
  [string]$Backend  = 'pyramid',     # pyramid | estimator
  [string[]]$Extra  = @(),
  [switch]$Srgb,
  [int]$ExpectCode  = 0,
  [string]$Warpmap   = ''
)

$scratch = 'C:\dev\strehl-out\BUILD-SOFTGATE'

# Every render-affecting variable this tool reads, cleared before every run so
# the ambient shell cannot quietly render a different pipeline than the record
# claims. Mirrors RENDER_ENV in crates/strehl-cli/tests/byte-freeze.rs, plus
# STREHL_SOFT_GATE -- which is MISSING from that list and is this lane's finding.
$renderEnv = @(
  'STREHL_ALIGN','STREHL_WARPMAP','STREHL_CACHE_DIR','STREHL_FIX_HALO',
  'STREHL_FIX_HALO_DELTA','STREHL_GATE_FLOOR','STREHL_DEFECT','STREHL_DEFECT_MAP',
  'STREHL_DEFECT_ARM','STREHL_DEFECT_HOT_FLOOR','STREHL_EDGE_AWARE','STREHL_EDGE_TAU',
  'STREHL_EDGE_CONF','STREHL_ACUITY','STREHL_FULLRES_GATHER','STREHL_ONLY_FRAME',
  'STREHL_MERGE','STREHL_PYRAMID_WORKERS','STREHL_VEIL','STREHL_VEIL_MARGIN',
  'STREHL_VEIL_FLOOR','STREHL_FIX_CA','STREHL_PHOTOMETRIC',
  'STREHL_SOFT_GATE','STREHL_ROBUST_ELECTION','STREHL_PYRAMID_MEAN_COARSE',
  'STREHL_HULL','STREHL_PYRAMID_WEIGHT_DUMP','STREHL_BAND_WORKERS'
)
foreach ($v in $renderEnv) { Remove-Item "Env:\$v" -ErrorAction SilentlyContinue }

# Rule 45 isolation: private sidecar, private cache. Both under this lane's
# scratch so no other agent's solve can reach this render and vice versa.
$leaf = Split-Path $Stack -Leaf
$env:STREHL_WARPMAP   = "$scratch\warpmaps\$leaf-$Limit.warpmap.txt"
$env:STREHL_CACHE_DIR = "$scratch\cache"
New-Item -ItemType Directory -Force -Path "$scratch\warpmaps","$scratch\cache" | Out-Null

if ($SoftGate -ne 'unset') { $env:STREHL_SOFT_GATE = $SoftGate }

$argv = @('stack', $Stack, '-l', "$Limit", '--merge', $Backend, '--out', $Out)
if ($Srgb) { $argv += '--srgb' }
$argv += $Extra

# NB: PowerShell variable names are CASE-INSENSITIVE. An earlier draft captured
# the process output into `$out`, which is the SAME VARIABLE as the `$Out`
# parameter, and silently destroyed the output path -- so every arm reported
# NO-FILE while the renders were sitting on disk. Named `$stdxx` to keep it
# unambiguously distinct from every parameter.
$sw = [Diagnostics.Stopwatch]::StartNew()
$stdxx = & $Exe @argv 2>&1
$code  = $LASTEXITCODE         # captured IMMEDIATELY, no pipeline in between
$sw.Stop()

$hash = 'NO-FILE'; $bytes = 0
if (Test-Path -LiteralPath $Out) {
  $hash  = (Get-FileHash -LiteralPath $Out -Algorithm SHA256).Hash
  $bytes = (Get-Item -LiteralPath $Out).Length
}

[pscustomobject]@{
  SoftGate = $SoftGate
  Backend  = $Backend
  Code     = $code
  Expected = $ExpectCode
  CodeOK   = ($code -eq $ExpectCode)
  Sha256   = $hash
  Bytes    = $bytes
  Secs     = [math]::Round($sw.Elapsed.TotalSeconds,1)
  Argv     = ($argv -join ' ')
  Stderr   = ($stdxx | Out-String)   # Out-String is safe; -First is not.
}
