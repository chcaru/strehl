<#
  BUILD-SHARP: render the arms for the veil-or-light verification.

  Load-bearing design notes:

  * ONE pinned binary for every arm, stated in the log.  Three other lanes are
    flipping defaults tonight (BUILD-BLEND's multi-band merge, BUILD-RENDER's
    lateral-CA default).  An unpinned comparison would be across three changes
    at once and could not attribute anything.

  * --linear-srgb, never --srgb, and no --auto-exposure.  The quantity under
    test is an ABSOLUTE BACKDROP LEVEL IN DN.  Any per-arm exposure choice
    normalises away exactly the additive bias the measurement exists to find.

  * The warp cache is shared across arms: alignment is upstream of the merge and
    must not vary between them.

  * $ErrorActionPreference is Continue around the native call.  Under "Stop" the
    pin's stderr provenance marker is promoted to a terminating
    NativeCommandError and the run dies on a successful render.
#>
[CmdletBinding()]
param(
    [string[]]$Subjects = @("flower-bud-alone-cpl", "109MSDCF", "coffee-bean", "couch-fibers-cpl"),
    [string]$Arm        = "base",
    [string]$Exe        = "C:\dev\strehl-out\BUILD-SHARP\pin-b001f22\target\release\strehl.exe",
    [string]$Gate       = "4.0",
    [hashtable]$Env     = @{}
)

$root = "C:\dev\strehl-out\BUILD-SHARP"
if (-not (Test-Path $Exe)) { throw "no pinned binary at $Exe" }

$env:STREHL_CACHE_DIR = Join-Path $root "warpcache"
New-Item -ItemType Directory -Force -Path $env:STREHL_CACHE_DIR | Out-Null
foreach ($v in @("STREHL_WARPMAP", "STREHL_FIX_HALO", "STREHL_SMOOTH", "STREHL_PHOTOMETRIC",
                 "STREHL_VEIL", "STREHL_VEIL_MARGIN", "STREHL_VEIL_FLOOR")) {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
$env:STREHL_ALIGN = "1"
foreach ($k in $Env.Keys) { Set-Item "Env:\$k" $Env[$k] }

$log = Join-Path $root "veil\run-$Arm.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$hash = (Get-FileHash $Exe -Algorithm SHA256).Hash
[IO.File]::WriteAllText($log, "BUILD-SHARP veil arm '$Arm' $(Get-Date -Format o)`npin: $Exe`nsha256: $hash`nextra env: $($Env.Keys -join ',')`n`n")

$ErrorActionPreference = "Continue"
foreach ($subj in $Subjects) {
    $dir = Join-Path "D:\personal\macro" $subj
    if (-not (Test-Path $dir)) { Write-Warning "no subject $dir"; continue }
    $out = Join-Path $root "veil\$subj\$Arm"
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $tif = Join-Path $out "linear-srgb.tif"

    $argv = @("stack", $dir, "--out", $tif, "--gate", $Gate, "--linear-srgb", "--demosaic")
    Write-Host "`n== $subj  arm=$Arm"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $txt = & $Exe @argv 2>&1 | Out-String
    $sw.Stop()
    if ($LASTEXITCODE -ne 0) { Write-Warning "render FAILED: $subj/$Arm"; }

    $rec = "=== $subj / $Arm ===`n" +
           "argv: strehl $($argv -join ' ')`n" +
           "sha256: $hash`n" +
           "extra env: $(($Env.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ' ')`n" +
           "elapsed: $([math]::Round($sw.Elapsed.TotalSeconds,1))s`n" + $txt + "`n"
    [IO.File]::AppendAllText($log, $rec)
    [IO.File]::WriteAllText((Join-Path $out "cmd.txt"), $rec)
    Write-Host ("   {0:N1}s -> {1}" -f $sw.Elapsed.TotalSeconds, $tif)
}
Write-Host "`nlog: $log"
