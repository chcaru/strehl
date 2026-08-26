$exe = 'C:\dev\strehl-out\ORCH-CLAMP\interv\clamped\target\release\examples\blend-render.exe'
$out = 'C:\dev\strehl-out\V-ca'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$subs = 'coffee-bubbles','foam','couch-fibers-cpl','flowers-cpl','wrapped-text-1'
foreach($s in $subs){
  $env:STREHL_FIX_CA = 'a7c2-fe100gm-2xtc-x4cpl'
  $dst = Join-Path $out "$s--cafix.tiff"
  "=== ON  $s -> $dst  $(Get-Date -Format HH:mm:ss)"
  & $exe "D:\personal\macro\$s" $dst --gate 4 --base-mean --chunks 5 2>&1 | Out-File (Join-Path $out "$s--cafix.log") -Encoding utf8
  "    exit=$LASTEXITCODE"
}
# CONTROL: re-render one OFF arm with my own invocation, to test whether the
# gallery OFF arms are reproducible partners or carry run-to-run nondeterminism.
Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
$dst = Join-Path $out 'foam--offrepro.tiff'
"=== OFF-REPRO foam -> $dst  $(Get-Date -Format HH:mm:ss)"
& $exe 'D:\personal\macro\foam' $dst --gate 4 --base-mean --chunks 5 2>&1 | Out-File (Join-Path $out 'foam--offrepro.log') -Encoding utf8
"    exit=$LASTEXITCODE"
"ALL DONE $(Get-Date -Format HH:mm:ss)"
