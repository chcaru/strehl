# Responsiveness control: prove my harness genuinely renders and that its
# output RESPONDS to input state. Without this, "byte-identical" could mean
# "the harness never invoked the binary".
$ErrorActionPreference = 'Continue'
$exe  = 'C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe'
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
if (-not $hash.StartsWith('44C2F2CD2E5B2894')) { throw "PIN MISMATCH" }
$ren = 'C:\dev\strehl-out\V-REVIEW\shipv4'
$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER')
$src = 'C:\dev\strehl-out\V-H2H2\halves\113-A'
$map = 'C:\dev\strehl-out\V-H2H2\warpmaps\113-A.warpmap.txt'
$dst = "$ren\ctl-113-A-g0.tiff"
if (Test-Path $dst) { Remove-Item $dst -Force }
foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
$env:STREHL_FULLRES_GATHER = '0'   # <-- THE ONLY CHANGE
$env:STREHL_WARPMAP = $map
$t0 = Get-Date
& $exe stack $src --out $dst --merge pyramid --pyramid-gate 4.5 `
      --linear-srgb --demosaic 2>&1 | Out-File "$ren\logs\ctl-113-A-g0.log" -Encoding utf8
$code = $LASTEXITCODE
Write-Host ("control render exit={0} {1}s" -f $code, [math]::Round(((Get-Date)-$t0).TotalSeconds,1))
if ($code -ne 0) { throw "control render failed" }
Set-Content -Path "$dst.ok" -Value $hash -NoNewline -Encoding ascii
Set-Content -Path "$dst.provenance.txt" -Encoding utf8 -Value (@(
  "purpose       : RESPONSIVENESS CONTROL, not a measurement arm",
  "binary sha256 : $hash  (SHIP-V4 pin)",
  "command       : stack <src> --out <dst> --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic",
  "env set       : STREHL_FULLRES_GATHER=0  <- deliberately differs from the measurement arm",
  "              : STREHL_WARPMAP=$map",
  "rendered      : $(Get-Date -Format o)") -join "`n")
$g1 = (Get-FileHash "$ren\113-A-g1-v4.tiff" -Algorithm SHA256).Hash
$g0 = (Get-FileHash $dst -Algorithm SHA256).Hash
Write-Host ""
Write-Host "  measurement arm (gather=1) : $($g1.Substring(0,32))"
Write-Host "  control arm     (gather=0) : $($g0.Substring(0,32))"
Write-Host ("  DIFFER : " + ($g1 -ne $g0) + "   <- must be TRUE or the harness is inert")
