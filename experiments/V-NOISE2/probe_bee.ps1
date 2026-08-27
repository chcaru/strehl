# V-NOISE2 / probe_bee.ps1 -- DIAGNOSTIC ONLY, touches no pipeline directory.
#
# WHY THIS EXISTS.  `fba` (205 frames) aborted align_image_stack at the default
# -t 3 with "After control points pruning reference images has no control
# points", and probing isolated the cause to FRAME 0, not to stack length: the
# first 20 frames failed at -t 3 and passed at -t 25, while a middle 20-frame
# slice passed at -t 3.  -t 25 is expensive (>40 min on 205 frames where the
# default aborted in 5 min), and `bee` has 299 frames, so whether `bee` needs
# the same loosening is the single largest schedule unknown in this lane.
#
# This script answers it WITHOUT writing into C:\dev\strehl-out\V-NOISE2\bee\,
# so it cannot race the queued serial build.  It develops the first N bee
# frames into a scratch directory with the EXACT develop command run_subject.ps1
# uses, then runs align_image_stack on them at a given -t.
#
# It also times one develop, which is the other number needed to decide whether
# bee's 299 develops can be run in parallel with fba's align.
#
# D:\ IS READ-ONLY.  Frames are copied out before decoding.

param(
  [string]$Src = 'D:\personal\macro\bee-1-cpl',
  [int]$N = 20,
  [int]$Tdist = 3,
  [string]$Probe = 'C:\dev\strehl-out\V-NOISE2\_probe\bee'
)

$ErrorActionPreference = 'Stop'
$exe = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$hb  = 'C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin'

$lin = "$Probe\lin"; $ali = "$Probe\ali"; $wrk = "$Probe\wrk"; $logs = "$Probe\logs"
foreach ($d in $lin,$ali,$wrk,$logs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format HH:mm:ss), $m) }

$all = Get-ChildItem $Src -File -Filter *.ARW | Sort-Object Name
Say "$($all.Count) ARW under $Src ; probing first $N"
$frames = $all[0..($N-1)]

foreach ($v in 'STREHL_WARPMAP','STREHL_MERGE','STREHL_DEBUG','STREHL_THREADS') {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

$devTimes = @()
foreach ($f in $frames) {
  $stem = [IO.Path]::GetFileNameWithoutExtension($f.Name)
  $dst = "$lin\$stem.tif"
  if (Test-Path $dst) { continue }
  $one = "$wrk\dev1"
  Remove-Item "$one\*" -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force -Path $one | Out-Null
  Copy-Item $f.FullName "$one\$($f.Name)" -Force
  $env:STREHL_FULLRES_GATHER = '1'
  $env:STREHL_ALIGN = '0'
  $t0 = Get-Date
  & $exe stack $one --out $dst --merge pyramid --pyramid-gate 4.5 `
        --linear-srgb --demosaic 2>&1 | Out-File "$logs\dev-$stem.log" -Encoding utf8
  if ($LASTEXITCODE -ne 0) { throw "develop $stem exit $LASTEXITCODE" }
  $devTimes += ((Get-Date) - $t0).TotalSeconds
}
Remove-Item 'env:STREHL_FULLRES_GATHER' -ErrorAction SilentlyContinue
Remove-Item 'env:STREHL_ALIGN' -ErrorAction SilentlyContinue

if ($devTimes.Count -gt 0) {
  $m = ($devTimes | Measure-Object -Average -Minimum -Maximum)
  Say ("develop seconds: n={0} mean={1} min={2} max={3}" -f $m.Count,
       [math]::Round($m.Average,1), [math]::Round($m.Minimum,1), [math]::Round($m.Maximum,1))
} else { Say "develops already present, not re-timed" }
$sz = (Get-ChildItem "$lin\*.tif" | Select-Object -First 1).Length
Say ("developed {0} files, frame size {1} bytes" -f (Get-ChildItem "$lin\*.tif").Count, $sz)

Remove-Item "$ali\al_*.tif" -Force -ErrorAction SilentlyContinue
$inp = Get-ChildItem "$lin\*.tif" | Sort-Object Name | ForEach-Object FullName
Say "align_image_stack -t $Tdist on $($inp.Count) frames"
$t0 = Get-Date
& "$hb\align_image_stack.exe" -l -m -C -t $Tdist --use-given-order -a "$ali\al_" @inp 2>&1 |
    Out-File "$logs\ais-t$Tdist.log" -Encoding utf8
$c = $LASTEXITCODE
$have = (Get-ChildItem "$ali\al_*.tif" -ErrorAction SilentlyContinue).Count
Say ("  exit=$c {0}s -> $have of $($inp.Count) files" -f [math]::Round(((Get-Date)-$t0).TotalSeconds,1))
if ($have -ne $inp.Count) {
  Say "  TAIL OF LOG:"
  Get-Content "$logs\ais-t$Tdist.log" | Select-Object -Last 8 | ForEach-Object { Say "    $_" }
}
Say "PROBE DONE Tdist=$Tdist result=$(if ($have -eq $inp.Count) { 'PASS' } else { 'FAIL' })"
