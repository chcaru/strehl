# M116 addendum -- ORCH's adversarial warp-cache poisoning check (discipline 807).
#
# Claim under test: this campaign cannot have been poisoned by the shared warp
# cache, because every arm set STREHL_WARPMAP and `alignment_for` at the pinned
# SHA reaches `align_cmd::load_or_solve` -- the cached path -- only on the
# `else` branch where that variable is UNSET.
#
# Source reading is an argument. This is the measurement.
#
#   COLD    private empty cache, sidecar override -> H1
#   POISON  shared cache that a DIFFERENT arm (A2, soft gate) has just run
#           against, then the default arm -> H2
#   PLANT   the default arm pointed at ANOTHER SUBJECT's sidecar. This must not
#           silently succeed. Fact 1548: a null with no plant is a dead probe,
#           so the probe must be shown able to express a difference at all.
#
# PASS requires H1 == H2 == the hash recorded during the campaign, AND the
# plant to be refused or to differ.

$ErrorActionPreference = "Continue"
$EXE   = "C:\dev\strehl-out\M116-tree\target\release\strehl.exe"
$ROOT  = "C:\dev\strehl-out\M116"
$SUBJ  = "bee-3-cpl"
$OTHER = "tweezers-cpl"
$RECORDED = "478387EF2F9A"     # A0 bee-3-cpl, first 12, from the campaign ledger
$WARP  = "$ROOT\warp\$SUBJ-l100.txt"
$CACHE = "$ROOT\cachetest"

function Clear-StrehlEnv {
  Get-ChildItem env: | Where-Object Name -like "STREHL_*" |
    ForEach-Object { Remove-Item "env:$($_.Name)" -ErrorAction SilentlyContinue }
}

function Invoke-Arm {
  param(
    [string]$Tag,
    [string]$CacheDir,
    [string]$WarpPath,
    [string]$Gate,
    [string]$SoftGate = "",
    [string]$Out
  )
  Clear-StrehlEnv
  $env:STREHL_CACHE_DIR = $CacheDir
  if ($WarpPath) { $env:STREHL_WARPMAP = $WarpPath }
  if ($SoftGate) { $env:STREHL_SOFT_GATE = $SoftGate }
  New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null
  if (-not $Out) { throw "Invoke-Arm[$Tag]: empty output path" }
  # NOT $args -- that is an automatic variable and splatting it silently
  # produced an argv with an empty --out on the first attempt.
  $cmdArgs = @("stack","D:\personal\macro\$SUBJ","--limit","100","--gate",$Gate,"--out",$Out)
  # NOT $out -- PowerShell variables are case-insensitive, so $out would
  # overwrite the $Out PARAMETER with the log text and Test-Path would then
  # test the log instead of the file.
  $stdout = & $EXE @cmdArgs 2>&1
  $code = $LASTEXITCODE                      # captured BEFORE any pipeline
  $hash = if (Test-Path $Out) { (Get-FileHash $Out -Algorithm SHA256).Hash.Substring(0,12) } else { "(none)" }
  Clear-StrehlEnv
  [pscustomobject]@{ Tag=$Tag; Exit=$code; Hash=$hash; Log=($stdout | Out-String) }
}

Remove-Item -Recurse -Force $CACHE -ErrorAction SilentlyContinue
Write-Output "=== recorded campaign hash for $SUBJ A0 : $RECORDED ==="

# COLD -- private, empty cache
$cold = Invoke-Arm -Tag "COLD" -CacheDir "$CACHE\cold" -WarpPath $WARP -Gate 4 -Out "$ROOT\measure\_poison_cold.tif"
Write-Output ("COLD    exit={0}  hash={1}" -f $cold.Exit, $cold.Hash)

# POISON -- a DIFFERENT arm runs first against a SHARED cache, then the default
$pre = Invoke-Arm -Tag "PRE-A2" -CacheDir "$CACHE\shared" -WarpPath $WARP -Gate 4 -SoftGate "gaussian" -Out "$ROOT\measure\_poison_pre.tif"
Write-Output ("PRE-A2  exit={0}  hash={1}   (soft gate, must differ from A0)" -f $pre.Exit, $pre.Hash)
$poi = Invoke-Arm -Tag "POISON" -CacheDir "$CACHE\shared" -WarpPath $WARP -Gate 4 -Out "$ROOT\measure\_poison_after.tif"
Write-Output ("POISON  exit={0}  hash={1}" -f $poi.Exit, $poi.Hash)

# PLANT -- wrong subject's sidecar; must NOT silently succeed
$plant = Invoke-Arm -Tag "PLANT" -CacheDir "$CACHE\plant" -WarpPath "$ROOT\warp\$OTHER-l100.txt" -Gate 4 -Out "$ROOT\measure\_poison_plant.tif"
$refused = ($plant.Exit -ne 0)
Write-Output ("PLANT   exit={0}  hash={1}   (foreign sidecar)" -f $plant.Exit, $plant.Hash)
if ($refused) {
  $msg = ($plant.Log -split "`n" | Select-String -Pattern "sidecar|bracket|fitted" | Select-Object -Last 1)
  Write-Output ("PLANT   refused with: {0}" -f ($msg -replace '\s+',' ').Trim())
}

Write-Output ""
$agree   = ($cold.Hash -eq $poi.Hash) -and ($cold.Hash -eq $RECORDED)
$sgmoved = ($pre.Hash -ne $cold.Hash)
Write-Output ("cold == poisoned == recorded : {0}" -f $agree)
Write-Output ("soft-gate arm moved the hash : {0}   (probe is live, not dead)" -f $sgmoved)
Write-Output ("foreign sidecar refused      : {0}" -f $refused)
if ($agree -and $sgmoved -and $refused) {
  Write-Output "RESULT: CLEAN -- the campaign is not cache-poisonable, and the probe can move."
} else {
  Write-Output "RESULT: **PROBLEM** -- investigate before trusting any number in this report."
}
Remove-Item "$ROOT\measure\_poison_*.tif" -ErrorAction SilentlyContinue
