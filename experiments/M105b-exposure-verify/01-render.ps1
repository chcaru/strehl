# Renders every arm M105b's bars need, from ONE binary, and hashes each file.
#
# Nothing here writes to D:. All output goes to C:\dev\strehl-out\M105.
#
# Usage:  powershell -File 01-render.ps1
param(
    [string]$Exe = "C:\dev\strehl-m105-target\release\strehl.exe",
    [string]$Out = "C:\dev\strehl-out\M105",
    [string]$Stack = "D:\personal\macro\bee-3-cpl"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Render($name, $extra) {
    $tif = Join-Path $Out "$name.tif"
    $log = Join-Path $Out "$name.log"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $args = @("stack", $Stack, "--out", $tif) + $extra
    # The binary writes its whole report to stderr. With ErrorActionPreference
    # = Stop, PowerShell promotes native stderr to a terminating error, so the
    # redirect has to run with it relaxed.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $Exe @args 2>&1 | Out-File -FilePath $log -Encoding utf8
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $sw.Stop()
    $hash = if (Test-Path $tif) { (Get-FileHash $tif -Algorithm SHA256).Hash } else { "NO-FILE" }
    $expo = (Select-String -Path $log -Pattern '^exposure\s+:' | ForEach-Object { $_.Line.Trim() }) -join " | "
    [pscustomobject]@{
        name     = $name
        args     = ($extra -join " ")
        exit     = $code
        seconds  = [math]::Round($sw.Elapsed.TotalSeconds, 1)
        sha256   = $hash
        exposure = $expo
    }
}

$rows = @()

# --- V5a: the byte-frozen measurement path. No --srgb, no --demosaic. ---
$rows += Render "v5a-linear-60"   @("--limit", "60")

# --- V2/V3: the automatic choice on the full stack, and its printed round trip. ---
$rows += Render "v2-auto-299"     @("--srgb", "--auto-exposure")

# --- V4: placebo (must be identical) and positive control (must be exactly 2x). ---
$rows += Render "v4-plain-299"    @("--srgb")
$rows += Render "v4-exp0-299"     @("--srgb", "--exposure", "0")
$rows += Render "v4-exp1-299"     @("--srgb", "--exposure=1.00")

$rows | Format-Table -AutoSize | Out-String -Width 240 | Write-Output
$rows | ConvertTo-Json -Depth 3 | Set-Content -Path (Join-Path $Out "01-render.json") -Encoding utf8
