# DELIVER-V6 -- render an explicit list of subjects from the pinned build.
#
# This is render.ps1 generalised from "the 26 subjects that already had masters"
# to "whatever list you hand it", because the owner's request is now `please
# stack all samples` -- all 33 capture directories under D:\personal\macro that
# hold ARW frames. (The 34th, `flat-fields`, holds none; it is calibration data,
# not a subject.)
#
# Everything that made render.ps1 trustworthy is preserved verbatim: the same
# pinned exe, the same character-for-character invocation
#     & $exe stack <dir> -o <out>.tiff --srgb
# with no --limit / --gate / --auto-exposure / --resampler / --exposure, the same
# clearing of inherited STREHL_* state, the same private STREHL_CACHE_DIR so no
# other lane's warp sidecar can be served into this render, and the same AGENTS
# rule 46 exit-code capture (stream into a variable, read $LASTEXITCODE in the
# very next statement, filter the variable afterwards).
#
# THREE THINGS THIS ADDS
# ----------------------
# 1. -Subjects: an explicit list, so the run can be partitioned across several
#    concurrent streams. strehl uses roughly a third of this machine's 32 cores
#    on one stack, so three streams keep the box busy without thrashing. Each
#    stream is given its OWN scratch and its OWN manifest/log fragment; two
#    processes appending to one manifest would interleave records and the file
#    would be worthless as a delivery document.
# 2. The FULL banner is written to a per-subject file. render.ps1 filtered the
#    banner down to a handful of patterns, which was enough for the CA question
#    but throws away exactly the warnings ORCH now wants recorded -- notably the
#    noise-profile line, which is what reports the ISO and the extrapolation
#    below the profile's calibration floor.
# 3. ISO and the alignment disposition are lifted out of the banner into the
#    manifest record, because a delivery document that says "ISO 50, and the
#    shipped profile is calibrated at ISO 100" is the difference between a
#    reader trusting a soft-looking master and a reader re-diagnosing it.
#
# It does NOT stop on a failed subject. A run that dies on subject 11 of 33
# delivers nothing; a run that logs the failure and continues delivers 32.

param(
    [Parameter(Mandatory=$true)][string[]]$Subjects,
    [Parameter(Mandatory=$true)][string]$Tag,
    [string]$Exe     = "C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe",
    [string]$Commit  = "6af834dac08d6605aee7ea3ad75809fdf6313770",
    [string]$Root    = "D:\personal\macro",
    [string]$Dest    = "C:\dev\strehl-out\DELIVER-V6\masters",
    [string]$Scratch = "C:\dev\strehl-out\DELIVER-V6\scratch"
)

$ErrorActionPreference = "Stop"

$banners = Join-Path $Dest "banners"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
New-Item -ItemType Directory -Force -Path $banners | Out-Null
$cache = Join-Path $Scratch "warpmaps-$Tag"
New-Item -ItemType Directory -Force -Path $cache | Out-Null

foreach ($v in @("STREHL_GATE_FLOOR_SCALE","STREHL_WARPMAP","STREHL_ALIGN",
                 "STREHL_FIX_HALO","STREHL_FIX_CA","STREHL_EDGE_AWARE",
                 "STREHL_SMOOTH","STREHL_SMOOTH_HUBER","STREHL_DUMP_ELECTION",
                 "STREHL_COVER")) {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
$env:STREHL_CACHE_DIR = $cache

$exeHash  = (Get-FileHash $Exe -Algorithm SHA256).Hash
$log      = Join-Path $Dest "render-$Tag.log"
$manifest = Join-Path $Dest "manifest-$Tag.txt"

$hdr = @()
$hdr += "=== DELIVER-V6 stream $Tag"
$hdr += "exe            : $Exe"
$hdr += "exe SHA256     : $exeHash"
$hdr += "exe build      : $(& $Exe --version 2>&1)"
$hdr += "commit         : $Commit"
$hdr += "source root    : $Root  (READ-ONLY -- nothing is written here)"
$hdr += "STREHL_CACHE_DIR = $cache"
$hdr += "all other STREHL_* : unset (shipping default)"
$hdr += "invocation     : <exe> stack <dir> -o <dest>\<subject>.tiff --srgb"
$hdr += "subjects       : $($Subjects.Count) -- $($Subjects -join ', ')"
$hdr += "started        : $(Get-Date -Format o)"
$hdr | Out-File -FilePath $log -Encoding utf8
$hdr | Out-File -FilePath $manifest -Encoding utf8
"" | Out-File -FilePath $manifest -Append -Encoding utf8

$i = 0
foreach ($name in $Subjects) {
    $i++
    $dir    = Join-Path $Root $name
    $target = Join-Path $Dest "$name.tiff"
    if (-not (Test-Path $dir)) {
        "[$Tag $i/$($Subjects.Count)] $name MISSING SOURCE $dir" | Tee-Object -FilePath $log -Append
        @("subject   : $name", "FAILED  missing source $dir", "") |
            Out-File -FilePath $manifest -Append -Encoding utf8
        continue
    }
    $n = (Get-ChildItem $dir -File -Filter *.ARW).Count
    $sw = [Diagnostics.Stopwatch]::StartNew()

    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out  = & $Exe stack $dir -o $target --srgb 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $sw.Stop()

    $text = ($out | ForEach-Object { "$_" }) -join "`n"
    $text | Out-File -FilePath (Join-Path $banners "$name.txt") -Encoding utf8

    $ok = (Test-Path $target) -and ($code -eq 0)
    $secs = [math]::Round($sw.Elapsed.TotalSeconds,1)
    "[$Tag $i/$($Subjects.Count)] $name frames=$n secs=$secs exit=$code ok=$ok" |
        Tee-Object -FilePath $log -Append

    # Lift the facts a delivery document needs out of the banner text.
    $iso = "unknown"
    $mIso = [regex]::Match($text, 'ISO\s+(\d+)')
    if ($mIso.Success) { $iso = $mIso.Groups[1].Value }
    $align = "not reported"
    $mAl = [regex]::Match($text, '(?m)^\s*alignment\s*:\s*(.+)$')
    if ($mAl.Success) { $align = $mAl.Groups[1].Value.Trim() }
    $ca = "not reported"
    $mCa = [regex]::Match($text, '(?m)^\s*lateral CA\s*:\s*(.+)$')
    if ($mCa.Success) { $ca = $mCa.Groups[1].Value.Trim() }
    $notes = @()
    foreach ($ln in $text -split "`n") {
        if ($ln -match 'REFUSED|refus|calibrated at ISO|extrapolat|WARN|warning|clip|CLIP') {
            $t = $ln.Trim()
            if ($t -and ($notes -notcontains $t)) { $notes += $t }
        }
    }

    if ($ok) {
        $oh = (Get-FileHash $target -Algorithm SHA256).Hash
        $rec = @()
        $rec += "subject   : $name"
        $rec += "frames    : $n"
        $rec += "ISO       : $iso"
        $rec += "command   : `"$Exe`" stack `"$dir`" -o `"$target`" --srgb"
        $rec += "env       : STREHL_CACHE_DIR=$cache ; all other STREHL_* unset"
        $rec += "exe SHA256: $exeHash"
        $rec += "commit    : $Commit"
        $rec += "out SHA256: $oh"
        $rec += "bytes     : $((Get-Item $target).Length)"
        $rec += "secs      : $secs"
        $rec += "alignment : $align"
        $rec += "lateral CA: $ca"
        foreach ($nt in $notes) { $rec += "banner    : $nt" }
        $rec += ""
        $rec | Out-File -FilePath $manifest -Append -Encoding utf8
    } else {
        @("subject   : $name", "frames    : $n", "FAILED exit=$code after $secs s",
          "banner    : see banners\$name.txt", "") |
            Out-File -FilePath $manifest -Append -Encoding utf8
    }
}

"=== stream $Tag finished=$(Get-Date -Format o)" | Tee-Object -FilePath $log -Append
Remove-Item Env:\STREHL_CACHE_DIR -ErrorAction SilentlyContinue
