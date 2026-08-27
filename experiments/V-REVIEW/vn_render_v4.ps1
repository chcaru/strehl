# V-REVIEW / vn_render_v4.ps1
# Re-render the strehl arm of subject 113 on the SHIP-V4 pin.
# Switch state copied verbatim from the RULE 47 block in
# experiments/V-HEADTOHEAD2/render_linear.ps1. ONLY the binary changes.
# Seals are written AT RENDER TIME, not backfilled.
$ErrorActionPreference = 'Continue'

$exe  = 'C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe'
$want = '44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490'
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
if ($hash -ne $want) { throw "PIN MISMATCH: got $hash want $want" }
$seal = (Get-Content 'C:\dev\strehl-out\acceptance\SHIP-V4\bee-1-cpl--SHIP-V4.tiff.ok' -Raw).Trim()
if ($hash -ne $seal) { throw "PIN DOES NOT MATCH SHIP-V4 CORPUS SEAL" }
Write-Host "pin verified against corpus seal: $($hash.Substring(0,16))"

$ren  = 'C:\dev\strehl-out\V-REVIEW\shipv4'
$logs = "$ren\logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER')

$leak = Get-ChildItem env: | Where-Object { $_.Name -like 'STREHL_*' -and $clear -notcontains $_.Name }
if ($leak) { throw ("UNEXPECTED STREHL_* SET: " + ($leak.Name -join ',')) }

foreach ($tag in @('113-A','113-B')) {
  $src = "C:\dev\strehl-out\V-H2H2\halves\$tag"
  $map = "C:\dev\strehl-out\V-H2H2\warpmaps\$tag.warpmap.txt"
  $dst = "$ren\$tag-g1-v4.tiff"
  $log = "$logs\$tag-g1-v4.log"
  if (Test-Path $dst) { Write-Host "  $tag exists, skipped"; continue }
  foreach ($v in $clear) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_WARPMAP = $map
  $t0 = Get-Date
  & $exe stack $src --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File -FilePath $log -Encoding utf8
  $code = $LASTEXITCODE
  $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
  if ($code -ne 0) { Write-Host "  $tag EXIT=$code"; Get-Content $log -Tail 20; throw "$tag failed" }
  $len = (Get-Item $dst).Length
  Write-Host ("  {0} exit={1} {2}s bytes={3}" -f $tag, $code, $dt, $len)
  # SEAL AT RENDER TIME
  Set-Content -Path "$dst.ok" -Value $hash -NoNewline -Encoding ascii
  $prov = @(
   "subject         : $tag  (half-stack of 113MSDCF)",
   "source frames   : $src",
   "binary          : $exe",
   "binary sha256   : $hash",
   "binary identity : equals the SHIP-V4 corpus seal (verified this run)",
   "command         : stack <src> --out <dst> --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic",
   "env set         : STREHL_FULLRES_GATHER=1",
   "                : STREHL_WARPMAP=$map",
   "env cleared     : $($clear -join ', ')",
   "not passed      : --srgb --binned --exposure --auto-exposure --limit --resampler --photometric --focus-seam",
   "switch state    : copied verbatim from experiments/V-HEADTOHEAD2/render_linear.ps1 RULE 47 block",
   "purpose         : SHIP-V4-pin re-derivation of the V-REVIEW noise cells",
   "rendered        : $(Get-Date -Format o)",
   "seconds         : $dt",
   "bytes           : $len"
  ) -join "`n"
  Set-Content -Path "$dst.provenance.txt" -Value $prov -Encoding utf8
  Write-Host "      sealed"
}
Write-Host "SHIP-V4 RENDERS DONE"

