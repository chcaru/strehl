# M97q F2b RED CONTROL. Mutates a file in a SHARED tree, so the restore is in
# a finally: a mid-run failure must not leave the mutation behind.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "C:\dev\strehl-target-m97"
$env:PYTHONIOENCODING = "utf-8"

$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\flat-on-ruler-cpl"
$out = "C:\dev\strehl-out\M97\f2b"
$src = "C:\dev\blog\death-of-software\projects\strehl\experiments\M97-warped-merge\src"
Remove-Item $out -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $out | Out-Null
$env:STREHL_CACHE_DIR = "$out\cache"
$env:STREHL_ALIGN = "0"

try {
    python "$src\mutate_photo.py" apply
    if ($LASTEXITCODE -ne 0) { throw "mutation failed to land" }

    Push-Location C:\dev\blog\death-of-software\projects\strehl
    $b = cargo build --release -p strehl-cli --bins 2>&1
    $bcode = $LASTEXITCODE
    Pop-Location
    Write-Output "build EXIT=$bcode"
    if ($bcode -ne 0) { $b | Out-String | Write-Output; throw "control build failed" }

    foreach ($arm in @(@("A_off", $false), @("B_flag", $true))) {
        $a = @("stack", $dir, "--limit", "20", "--gate", "4",
               "--out", "$out\$($arm[0]).tiff", "--index-map", "$out\$($arm[0])_idx.tiff")
        if ($arm[1]) { $a += "--photometric" }
        $o = & $exe @a 2>&1
        $code = $LASTEXITCODE
        $o | Out-String | Set-Content -Encoding utf8 "$out\$($arm[0]).log"
        Write-Output ("{0,-8} EXIT={1}" -f $arm[0], $code)
    }

    Write-Output ""
    Write-Output "=== F2b: PLANT -- mis-propagated build must re-elect > 1% ==="
    python "$src\cmpmap.py" "$out\A_off_idx.tiff" "$out\B_flag_idx.tiff" 1.0 above
}
finally {
    python "$src\mutate_photo.py" restore
    Push-Location C:\dev\blog\death-of-software\projects\strehl
    cargo build --release -p strehl-cli --bins 2>&1 | Out-Null
    Write-Output "rebuild-clean EXIT=$LASTEXITCODE"
    Pop-Location
}
