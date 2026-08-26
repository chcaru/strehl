# BUILD-RESAMP / render7-h2h.ps1
#
# Head-to-head comparator render: strehl vs the prior focus-stack fork, from
# ONE identical staged directory of ARW files, both writing LINEAR output.
#
# Why a decimated subset: the fork holds every input frame as a full-raster
# float32 3-channel image (~396 MB each).  Measured on this machine it
# completes at 6 / 12 / 24 frames (48 s / 86 s / 211 s) and dies at 33 with
# 0xC0000005 -- an access violation, i.e. an unchecked allocation failure --
# after loading the last frame.  Both tools therefore see the SAME stride-6
# subset, which still spans the full focus travel.
#
# STREHL_WARPMAP beats --resampler, so it is cleared explicitly (AGENTS r45's
# advice to pin a sidecar would silently void this experiment).

# native tools write progress to stderr; 'Stop' turns that into a terminating
# NativeCommandError and kills the run, so this must stay 'Continue'.
$ErrorActionPreference = 'Continue'
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_COVER   -ErrorAction SilentlyContinue

$root    = 'C:\dev\strehl-out\BUILD-RESAMP'
$src     = 'D:\personal\macro\wrapped-text-1'
$stage   = "$root\subset24\wrapped-text-1"
$out     = "$root\h2h24"
$strehl  = "$root\bin\strehl.exe"
$fork    = 'C:\dev\macro\focus-stack\dist\focus-stack.exe'
$stride  = 6

New-Item -ItemType Directory -Force -Path $stage, $out | Out-Null
Get-ChildItem $stage -Filter *.ARW | Remove-Item -Force

$all = @(Get-ChildItem $src -Filter *.ARW | Sort-Object Name)
$pick = @(for ($i = 0; $i -lt $all.Count; $i += $stride) { $all[$i] })
foreach ($f in $pick) { Copy-Item $f.FullName "$stage\$($f.Name)" }
Get-ChildItem $stage -Filter *.ARW | ForEach-Object { $_.LastWriteTime = Get-Date }
"staged $($pick.Count) of $($all.Count) frames (stride $stride)"
($pick | ForEach-Object { $_.Name }) -join "`n" | Out-File "$out\framelist.txt" -Encoding utf8

$files = @(Get-ChildItem $stage -Filter *.ARW | Sort-Object Name | ForEach-Object { $_.FullName })

# ---- arm A: the prior fork ------------------------------------------------
$t = Get-Date
$log = & $fork "--output=$out\wrapped-text-1--fork.tif" `
       --output-colorspace=linear-rec2020 --output-bitdepth=32 @files 2>&1
$c = $LASTEXITCODE
$w = [math]::Round(((Get-Date) - $t).TotalSeconds, 1)
$log | Out-File "$out\wrapped-text-1--fork.log" -Encoding utf8
"ARGV: $fork --output=... --output-colorspace=linear-rec2020 --output-bitdepth=32 <$($files.Count) ARW from $stage>" |
    Out-File "$out\wrapped-text-1--fork.log" -Append -Encoding utf8
"EXIT: $c   WALL_S: $w   FRAMES: $($files.Count)" |
    Out-File "$out\wrapped-text-1--fork.log" -Append -Encoding utf8
"FORK exit $c  $w s"

# ---- arm B: strehl, shipping default --------------------------------------
$env:STREHL_PYRAMID_WORKERS = '2'
$t = Get-Date
$log = & $strehl stack $stage --out "$out\wrapped-text-1--strehl.tiff" `
       --merge pyramid --demosaic --resampler catmull-rom 2>&1
$c = $LASTEXITCODE
$w = [math]::Round(((Get-Date) - $t).TotalSeconds, 1)
$log | Out-File "$out\wrapped-text-1--strehl.log" -Encoding utf8
"ARGV: $strehl stack $stage --out ... --merge pyramid --demosaic --resampler catmull-rom  [STREHL_PYRAMID_WORKERS=2]" |
    Out-File "$out\wrapped-text-1--strehl.log" -Append -Encoding utf8
"EXIT: $c   WALL_S: $w   FRAMES: $($files.Count)" |
    Out-File "$out\wrapped-text-1--strehl.log" -Append -Encoding utf8
"STREHL exit $c  $w s"

"H2H24 RENDERS COMPLETE"
