# V-H2H2 -- the pre-flip / post-flip A/B, from ONE binary.
#
# RULE 47: the whole invocation is recorded here, including the flags left at
# their defaults and every environment variable this tool reads.
#
#   binary        C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe
#                 sha256 15EA73461905EA2D44B2F8242D578CD9330454450F61269AE1B1FBA71682A7B0
#                 git    740e70565d101b0edfaeffc7d0466feb01db8a0f  (the flip commit itself)
#   subcommand    stack <DIR> --out <OUT> --merge pyramid --pyramid-gate 4.5
#   NOT passed    --srgb, --exposure, --auto-exposure, --limit, --resampler,
#                 --gate, --threads.  The render is LINEAR: no tone gain, no
#                 sRGB transfer, no display S-curve, so there is no grade to
#                 remove and no exposure to pin.  That is deliberate -- the
#                 prior pass's single largest trap was the tone chain.
#   env  STREHL_FULLRES_GATHER  0 (pre-flip arm) / 1 (post-flip arm)   <-- THE VARIABLE
#        STREHL_WARPMAP         a scratch sidecar solved ONCE per stack, so both
#                               arms are registered identically and the only
#                               difference between them is the gather kernel.
#        STREHL_ALIGN           unset (= on)
#        STREHL_FIX_HALO        unset
#        every other STREHL_*   cleared below, by name, before every render.
#
# The warpmaps were solved by:
#   strehl align D:\personal\macro\113MSDCF   --out ...\113MSDCF.warpmap.txt
#   strehl align D:\personal\macro\coffee-bean --out ...\coffee-bean.warpmap.txt
# coffee-bean's solve reports held-out 6.671 px, digit-for-digit the number in
# the SHIP-V2 render log, so the isolated sidecar is the shipped solve.

# NOT 'Stop': the tool writes its banner to stderr, and `2>&1` under
# ErrorActionPreference=Stop turns the first banner line into a terminating
# error.  The exit code is checked explicitly instead, per rule 46/47.
$ErrorActionPreference = 'Continue'
$exe  = 'C:\dev\strehl-out\acceptance-pins\740e7056\target\release\strehl.exe'
$root = 'C:\dev\strehl-out\V-H2H2'
$rend = "$root\renders"
$logs = "$root\logs"
$wm   = "$root\warpmaps"

# Clear every environment variable the tool reads, by name.  An ambient value
# renders a different image than this script claims (rule 47).
foreach ($v in 'STREHL_FULLRES_GATHER','STREHL_ALIGN','STREHL_WARPMAP','STREHL_FIX_HALO',
                'STREHL_MERGE','STREHL_ACUITY','STREHL_ONLY_FRAME','STREHL_SOFT_GATE',
                'STREHL_COVER','STREHL_PYRAMID_WORKERS','STREHL_CACHE_DIR') {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}

$jobs = @(
    @{ tag='113-g0'; dir='D:\personal\macro\113MSDCF';    map="$wm\113MSDCF.warpmap.txt";    gather='0' },
    @{ tag='113-g1'; dir='D:\personal\macro\113MSDCF';    map="$wm\113MSDCF.warpmap.txt";    gather='1' },
    @{ tag='cb-g0';  dir='D:\personal\macro\coffee-bean'; map="$wm\coffee-bean.warpmap.txt"; gather='0' },
    @{ tag='cb-g1';  dir='D:\personal\macro\coffee-bean'; map="$wm\coffee-bean.warpmap.txt"; gather='1' }
)

foreach ($j in $jobs) {
    $out = "$rend\$($j.tag).tiff"
    $env:STREHL_WARPMAP        = $j.map
    $env:STREHL_FULLRES_GATHER = $j.gather
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $o  = & $exe stack $j.dir --out $out --merge pyramid --pyramid-gate 4.5 2>&1
    $code = $LASTEXITCODE
    $sw.Stop()
    Set-Content -Path "$logs\$($j.tag).log" -Value ($o | Out-String -Width 220)
    $sz = if (Test-Path $out) { (Get-Item $out).Length } else { -1 }
    "$($j.tag): exit=$code  $([math]::Round($sw.Elapsed.TotalSeconds,1))s  bytes=$sz  GATHER=$($j.gather)"
    if ($code -ne 0) { throw "$($j.tag) FAILED with exit $code" }
}
Remove-Item Env:\STREHL_FULLRES_GATHER -ErrorAction SilentlyContinue
Remove-Item Env:\STREHL_WARPMAP -ErrorAction SilentlyContinue
'ALL RENDERS DONE'
