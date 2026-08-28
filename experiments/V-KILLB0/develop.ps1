# V-KILLB0 linear develops -- byte-faithful to V-LINEAR/develop_frames.ps1 RULE 47
# record (same pinned binary, same flags, same env), so the qualification test I
# run on them is the same test V-LINEAR ran, differing ONLY in site selection.
# D:\personal\macro is READ-ONLY: each frame is COPIED to a private one-frame dir.
param([Parameter(Mandatory=$true)][string]$Subject,
      [Parameter(Mandatory=$true)][string]$Src,
      [int]$Step = 4)

$ErrorActionPreference = 'Continue'
$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$want = '15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0'
$got  = (Get-FileHash $exe -Algorithm SHA256).Hash
if ($got -ne $want) { throw "PINNED BINARY MISMATCH: got $got expected $want" }

$root = "C:\dev\strehl-out\V-KILLB0\lin\$Subject"
$work = "$root\src"; $dst = "$root\lintiff"
New-Item -ItemType Directory -Force -Path $work, $dst | Out-Null

$clear = @('STREHL_FULLRES_GATHER','STREHL_WARPMAP','STREHL_ALIGN','STREHL_MERGE',
           'STREHL_DEBUG','STREHL_LOG','STREHL_THREADS','STREHL_MEM_BUDGET_MB',
           'STREHL_NO_HALO','STREHL_SEED','STREHL_RESAMPLER','STREHL_GATE_FLOOR_SCALE')
foreach ($c in $clear) { Remove-Item "Env:\$c" -ErrorAction SilentlyContinue }
$env:STREHL_FULLRES_GATHER = '1'
$env:STREHL_ALIGN = '0'

$all = Get-ChildItem $Src -Filter *.ARW | Sort-Object Name
$sel = for ($i = 0; $i -lt $all.Count; $i += $Step) { $all[$i] }
"developing $($sel.Count) of $($all.Count) frames (step $Step) for $Subject"
$k = 0
foreach ($f in $sel) {
    $k++
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $out  = "$dst\${stem}.tif"
    if (Test-Path $out) { continue }
    $one = "$work\${stem}"
    New-Item -ItemType Directory -Force -Path $one | Out-Null
    Copy-Item $f.FullName -Destination $one -Force
    & $exe stack $one --out $out --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-Null
    Remove-Item $one -Recurse -Force -ErrorAction SilentlyContinue
    if ($k % 10 -eq 0) { "  $k/$($sel.Count)" }
}
"done: $((Get-ChildItem $dst -Filter *.tif).Count) tifs in $dst"
