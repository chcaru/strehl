# M97 Defect 2 -- D-series bars. Rule 47: capture first, read $LASTEXITCODE
# immediately, record LITERAL exit codes, never a `-ne 0` predicate, never a
# pipeline containing -First before the read.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"

$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97\d2"
New-Item -ItemType Directory -Force -Path $out | Out-Null

$env:STREHL_CACHE_DIR = "$out\cache"      # hermetic: seven agents share the real one
$env:STREHL_ALIGN = "1"

function Run-Arm($name, $map, $img) {
    Write-Output "=== $name ==="
    $env:STREHL_WARPMAP = $map
    $log = "$out\$name.log"
    $o = & $exe stack $dir --out $img --gate 4 2>&1
    $code = $LASTEXITCODE                      # read IMMEDIATELY, unfiltered
    $o | Out-String | Set-Content -Encoding utf8 $log
    $len = if (Test-Path $img) { (Get-Item $img).Length } else { 0 }
    $h = if ($len -gt 0) { (Get-FileHash $img -Algorithm SHA256).Hash.Substring(0, 16) } else { "NOFILE" }
    Write-Output "EXIT=$code BYTES=$len SHA16=$h LOG=$log"
    $o | Out-String | Select-String -Pattern "DROPPING|refused|expected|folded|Error|error" |
        Select-Object -Last 8 | ForEach-Object { "    | " + $_.Line.Trim() }
    Write-Output ""
}

Run-Arm "clean"  "C:\dev\strehl-out\M97\warpmap-ruler.txt"           "$out\clean.tiff"
Run-Arm "refuse" "C:\dev\strehl-out\M97\warpmap-ruler-REFUSE.txt"    "$out\refuse.tiff"
Run-Arm "allref" "C:\dev\strehl-out\M97\warpmap-ruler-ALLREFUSE.txt" "$out\allref.tiff"

Write-Output "=== provenance (rule 47) ==="
Write-Output "dir=$dir limit=<none, all 79> gate=4 (explicit)"
Write-Output "env: STREHL_ALIGN=1 STREHL_WARPMAP=<per arm> STREHL_CACHE_DIR=$out\cache"
Write-Output ("threads=" + $env:NUMBER_OF_PROCESSORS)
Push-Location C:\dev\blog\death-of-software\projects\strehl
Write-Output ("commit=" + (git rev-parse --short HEAD) + " (working tree may differ)")
Pop-Location
