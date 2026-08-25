$bin = 'C:\dev\strehl-out\V-CA-anti-wt\target\release\strehl.exe'
$src = 'D:\personal\macro\bee-3-cpl'
$sid = 'C:\dev\strehl-out\M110-sheet\bee-3-cpl\default.warp.json'
$out = 'C:\dev\strehl-out\V-CA-anti'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$arms = @(
  @{n='unset';   v=$null},
  @{n='zero';    v='0'},
  @{n='off';     v='off'},
  @{n='false';   v='false'},
  @{n='correct'; v='a7c2-fe100gm-2xtc-x4cpl'},
  @{n='anti';    v='a7c2-fe100gm-2xtc-x4cpl-anti'}
)
$env:STREHL_WARPMAP = $sid
$rows = @()
foreach($a in $arms){
  if($null -eq $a.v){ Remove-Item env:STREHL_FIX_CA -ErrorAction SilentlyContinue }
  else { $env:STREHL_FIX_CA = $a.v }
  $tif = Join-Path $out ("{0}.tif" -f $a.n)
  $t0 = Get-Date
  $so = & $bin stack $src --out $tif 2>&1
  $ec = $LASTEXITCODE
  $secs = ((Get-Date)-$t0).TotalSeconds
  if($ec -ne 0){
    Write-Host ("{0,-8} EXIT {1}  {2}" -f $a.n,$ec,($so | Select-Object -Last 2))
    $rows += [pscustomobject]@{arm=$a.n; exit=$ec; sha=''; bytes=0; secs=[math]::Round($secs,1)}
    continue
  }
  $h = (Get-FileHash $tif -Algorithm SHA256).Hash
  $b = (Get-Item $tif).Length
  Write-Host ("{0,-8} exit 0  {1:N1}s  {2:N0} B  {3}" -f $a.n,$secs,$b,$h.Substring(0,16))
  $rows += [pscustomobject]@{arm=$a.n; exit=$ec; sha=$h; bytes=$b; secs=[math]::Round($secs,1)}
}
Remove-Item env:STREHL_FIX_CA -ErrorAction SilentlyContinue
Remove-Item env:STREHL_WARPMAP -ErrorAction SilentlyContinue
$rows | ConvertTo-Json | Set-Content (Join-Path $out 'arms.json')
Write-Host "`n=== HASH TABLE ==="
$rows | Format-Table -AutoSize
