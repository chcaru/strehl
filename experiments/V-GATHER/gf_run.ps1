param()
$exe  = "C:\dev\strehl-pin\VG-gatefloor\strehl.exe"
$out  = "C:\dev\strehl-out\V-GATHER\gatefloor"
$subs = @("leaf-2-cpl","coffee-bean","113MSDCF","flat-on-ruler-cpl","112MSDCF",
          "wrapped-text-1","109MSDCF","119MSDCF")
New-Item -ItemType Directory -Force -Path $out | Out-Null
$before = (Get-FileHash $exe -Algorithm SHA256).Hash
"PIN BEFORE: $before"
foreach ($s in $subs) {
  foreach ($arm in @("white","measured")) {
    $f = "$out\$s--$arm.tiff"
    if (Test-Path $f) { "SKIP $s $arm (exists)"; continue }
    if ($arm -eq "white") { $env:STREHL_GATE_FLOOR = "white" }
    else { Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue }
    Remove-Item Env:\STREHL_FULLRES_GATHER -ErrorAction SilentlyContinue
    $t0 = Get-Date
    & $exe stack "D:\personal\macro\$s" --out $f --srgb 2>&1 |
        Out-File -Encoding utf8 "$out\$s--$arm.log"
    $rc = $LASTEXITCODE
    $avg = (Select-String -Path "$out\$s--$arm.log" -Pattern "^averaged" | Select-Object -First 1).Line
    "{0,-22} {1,-9} rc={2} {3,5:N0}s  {4}" -f $s, $arm, $rc, ((Get-Date)-$t0).TotalSeconds, ($avg -replace '\s+',' ')
  }
}
Remove-Item Env:\STREHL_GATE_FLOOR -ErrorAction SilentlyContinue
$after = (Get-FileHash $exe -Algorithm SHA256).Hash
"PIN AFTER : $after"
"PIN UNCHANGED: $($before -eq $after)"
