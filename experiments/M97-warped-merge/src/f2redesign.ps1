# M97q F2-REDESIGN. The pre-registered F2 used --index-map and its plant FAILED
# (0 px both ways). Diagnosis, MEASURED: merge_cmd.rs:1788 writes the election
# map from `p1.stats.best_index()`, and the photometric fit is built at :1837 --
# AFTER. Pass one never sees the gain, so --index-map cannot express the
# photometric term in either arm and the comparison was vacuous.
#
# n_eff is a pass-TWO quantity and is exactly what the noise calibration
# controls, so the plant is re-aimed onto it.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "C:\dev\strehl-target-m97"
$env:PYTHONIOENCODING = "utf-8"

$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97\f2r"
$src = "C:\dev\blog\death-of-software\projects\strehl\experiments\M97-warped-merge\src"
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:STREHL_CACHE_DIR = "$out\cache"
$env:STREHL_ALIGN = "0"

function Sha($p) {
    if (Test-Path $p) { (Get-FileHash $p -Algorithm SHA256).Hash.Substring(0, 16) } else { "NOFILE" }
}

function Arm($name, $photo) {
    $a = @("stack", $dir, "--limit", "20", "--gate", "4",
           "--out", "$out\$name.tiff", "--n-eff-map", "$out\${name}_neff.tiff")
    if ($photo) { $a += "--photometric" }
    $o = & $exe @a 2>&1
    $code = $LASTEXITCODE
    $o | Out-String | Set-Content -Encoding utf8 "$out\$name.log"
    Write-Output ("{0,-8} EXIT={1} IMG={2}" -f $name, $code, (Sha "$out\$name.tiff"))
}

Write-Output "=== clean build: A (off), B (photometric, correct propagation) ==="
Arm "A_off"  $false
Arm "B_ok"   $true

try {
    Write-Output ""
    Write-Output "=== planting: gain applied, noise model held ==="
    python "$src\mutate_photo.py" apply
    if ($LASTEXITCODE -ne 0) { throw "mutation failed to land" }
    Push-Location C:\dev\blog\death-of-software\projects\strehl
    cargo build --release -p strehl-cli --bins 2>&1 | Out-Null
    $bcode = $LASTEXITCODE
    Pop-Location
    Write-Output "build EXIT=$bcode"
    if ($bcode -ne 0) { throw "control build failed" }
    Arm "C_broken" $true
}
finally {
    python "$src\mutate_photo.py" restore
    Push-Location C:\dev\blog\death-of-software\projects\strehl
    cargo build --release -p strehl-cli --bins 2>&1 | Out-Null
    Write-Output "rebuild-clean EXIT=$LASTEXITCODE"
    Pop-Location
}

$ha = Sha "$out\A_off.tiff"; $hb = Sha "$out\B_ok.tiff"; $hc = Sha "$out\C_broken.tiff"
Write-Output ""
Write-Output "=== F2r-i: the GAIN is connected to the gate (A vs B, n_eff) ==="
python "$src\cmpmap.py" "$out\A_off_neff.tiff" "$out\B_ok_neff.tiff" 0.0 above

Write-Output ""
Write-Output "=== F2r-ii: PLANT -- the NOISE PROPAGATION is connected (B vs C) ==="
Write-Output "  correct=$hb  mis-propagated=$hc"
Write-Output ("  bytes differ: " + $(if ($hb -ne $hc) { "YES" } else { "NO -- propagation is DEAD" }))
python "$src\cmpmap.py" "$out\B_ok_neff.tiff" "$out\C_broken_neff.tiff" 0.0 above

Write-Output ""
Write-Output "=== provenance ==="
Write-Output "dir=$dir limit=20 gate=4 STREHL_ALIGN=0"
Push-Location C:\dev\blog\death-of-software\projects\strehl
Write-Output ("commit=" + (git rev-parse --short HEAD) + " + uncommitted M97q wiring")
Pop-Location
