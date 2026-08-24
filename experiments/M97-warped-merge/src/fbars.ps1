# M97q photometric wiring -- F-series bars. Rule 47 (as corrected): capture
# output first, read $LASTEXITCODE IMMEDIATELY and unfiltered, never truncate a
# live pipeline before reading it, record LITERAL exit codes not predicates.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = "utf-8"

$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97\f1"
$src = "C:\dev\blog\death-of-software\projects\strehl\experiments\M97-warped-merge\src"
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null

$env:STREHL_CACHE_DIR = "$out\cache"
$env:STREHL_ALIGN = "0"
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue

function Sha($p) {
    if (Test-Path $p) { (Get-FileHash $p -Algorithm SHA256).Hash.Substring(0, 16) } else { "NOFILE" }
}

# $photo: "off" | "flag" | "env"
function Run($name, $photo, $map) {
    if ($photo -eq "env") { $env:STREHL_PHOTOMETRIC = "1" }
    else { Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue }

    $a = @("stack", $dir, "--limit", "20", "--gate", "4", "--out", "$out\$name.tiff")
    if ($photo -eq "flag") { $a += "--photometric" }
    if ($map) { $a += @("--index-map", $map) }

    $o = & $exe @a 2>&1
    $code = $LASTEXITCODE                       # read IMMEDIATELY, unfiltered
    $o | Out-String | Set-Content -Encoding utf8 "$out\$name.log"
    Write-Output ("{0,-12} EXIT={1} IMG={2}" -f $name, $code, (Sha "$out\$name.tiff"))
}

Write-Output "=== runs ==="
Run "A_off"   "off"  "$out\A_idx.tiff"
Run "B_flag"  "flag" "$out\B_idx.tiff"
Run "C_env"   "env"  $null
Remove-Item Env:\STREHL_PHOTOMETRIC -ErrorAction SilentlyContinue

$ha = Sha "$out\A_off.tiff"; $hb = Sha "$out\B_flag.tiff"; $hc = Sha "$out\C_env.tiff"

Write-Output ""
Write-Output "=== F1: the default path is bit-identical to 8e5eb6e ==="
$frozen = "09FA927898ABF314"
Write-Output "  recorded at 8e5eb6e = $frozen"
Write-Output "  measured now        = $ha"
Write-Output ("  F1: " + $(if ($ha -eq $frozen) { "PASS" } else { "FAIL -- the opt-in path leaked into the default" }))

Write-Output ""
Write-Output "=== F1b: PLANT -- the flag must be able to move the bytes ==="
Write-Output "  off=$ha  photometric=$hb"
Write-Output ("  F1b: " + $(if ($ha -ne $hb) { "PASS" } else { "FAIL -- flag disconnected, F1 is VACUOUS" }))

Write-Output ""
Write-Output "=== F5: env twin agrees with the flag ==="
Write-Output "  flag=$hb  env=$hc"
Write-Output ("  F5: " + $(if ($hb -eq $hc -and $hb -ne "NOFILE") { "PASS" } else { "FAIL" }))

Write-Output ""
Write-Output "=== F2: election neutrality (bar: < 0.01% re-elected) ==="
python "$src\cmpmap.py" "$out\A_idx.tiff" "$out\B_idx.tiff" 0.01 below

Write-Output ""
Write-Output "=== F3: the fit is real and reported ==="
Get-Content "$out\B_flag.log" | Select-String "region |gain span|statistic|REFUSED|CAVEAT" |
    ForEach-Object { "  | " + $_.Line.Trim() }

Write-Output ""
Write-Output "=== provenance ==="
Write-Output "dir=$dir limit=20 gate=4 STREHL_ALIGN=0 cache=$out\cache"
Write-Output ("threads=" + $env:NUMBER_OF_PROCESSORS)
Push-Location C:\dev\blog\death-of-software\projects\strehl
Write-Output ("commit=" + (git rev-parse --short HEAD) + " + uncommitted M97q wiring")
Pop-Location
