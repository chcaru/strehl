$exe = 'C:\dev\strehl-out\V-ca-wt\target\release\examples\blend-render.exe'
$out = 'C:\dev\strehl-out\V-ca\guard'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$src = 'D:\personal\macro\bee-1-cpl'
# ARM 1: default-on.  Operator silent, gear matches -> guard must fire.
Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
"=== ARM defaulton  $(Get-Date -Format HH:mm:ss)"
& $exe $src "$out\defaulton.tiff" --gate 4 --base-mean --chunks 5 2>&1 | Out-File "$out\defaulton.log" -Encoding utf8
"   exit=$LASTEXITCODE"
# ARM 2: operator forces OFF on matching gear.  Under default-on this is the
# ONLY way to get an uncorrected render, so it is load-bearing for the first time.
$env:STREHL_FIX_CA = 'off'
"=== ARM forcedoff  $(Get-Date -Format HH:mm:ss)"
& $exe $src "$out\forcedoff.tiff" --gate 4 --base-mean --chunks 5 2>&1 | Out-File "$out\forcedoff.log" -Encoding utf8
"   exit=$LASTEXITCODE"
# ARM 3: explicit env key, the way ORCH measured.
$env:STREHL_FIX_CA = 'a7c2-fe100gm-2xtc-x4cpl'
"=== ARM envon      $(Get-Date -Format HH:mm:ss)"
& $exe $src "$out\envon.tiff" --gate 4 --base-mean --chunks 5 2>&1 | Out-File "$out\envon.log" -Encoding utf8
"   exit=$LASTEXITCODE"
# ARM 4: a typo must ERROR, not silently fall back to the default.
$env:STREHL_FIX_CA = 'a7c2-fe100gm-2xtc-x4cp'
"=== ARM typo       $(Get-Date -Format HH:mm:ss)"
& $exe $src "$out\typo.tiff" --gate 4 --base-mean --chunks 5 2>&1 | Out-File "$out\typo.log" -Encoding utf8
"   exit=$LASTEXITCODE  (NONZERO EXPECTED)"
Remove-Item Env:\STREHL_FIX_CA -ErrorAction SilentlyContinue
"DONE $(Get-Date -Format HH:mm:ss)"
