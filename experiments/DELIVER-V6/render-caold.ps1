# DELIVER-V6 arm C -- the ONE-BUILD before/after for the lateral-CA re-fit.
#
# WHY THIS ARM EXISTS (this is the important part)
# ------------------------------------------------
# The obvious before/after is ORCH-FAITHFUL's masters against DELIVER-V6's. That
# comparison is CONFOUNDED and I am not willing to ship it as "the fix":
#
#   * The old masters' own banner says `strehl 0.0.0 (8a480af9c6ba-dirty)` -- a
#     DIRTY tree, so the code that made them is not recoverable from any record.
#   * Between 8a480af9 and this delivery's pin 6af834da, SIX commits touch
#     `crates/`, and only ONE of them is the CA re-fit (393d7ca3). The other
#     five are argued default-neutral -- 6341a7a4 adds STREHL_HULL default-off
#     and byte-identical when unset; aa40cc78's `--cover crop` left the default
#     alone; 9c11209e is examples/ only; 5f367a94 only touches the
#     --auto-exposure path, which is not passed; 910e6bc0 is a comment. But
#     "argued neutral" is not measured neutral.
#   * Corpus fact 1886 measured the residual directly: a COEFFICIENT-INDEPENDENT
#     arm re-rendered from a moved tree differed on 33,003,417 px, max 23210 DN.
#
# So old-vs-new answers "what shipped before vs what ships now", which is a real
# question, but it does NOT isolate the coefficient. This arm does: it is the
# SAME pinned commit, the SAME source frames, the SAME flags, built from a
# worktree whose ONLY difference from the delivery build is one line --
#
#     crates/strehl-core/src/optics.rs:  eps_r: -508.4e-6  ->  -704.5e-6
#
# verified as `1 file changed, 1 insertion(+), 1 deletion(-)`. Both arms of this
# A/B come from one commit, which is what BUILD-CROP 16.1 concluded is mandatory
# after it was burned by exactly this.
#
# The binary self-reports `6af834dac08d-dirty`, which is correct and is left
# visible on purpose: it IS the pinned commit plus a deliberate one-line
# regression, and the banner should say so.
#
# CACHE
# -----
# A SEPARATE STREHL_CACHE_DIR from the delivery arm, so this binary solves its
# own warp maps end to end rather than inheriting the other arm's. That is the
# faithful choice: each arm does what it would do on its own. It also makes the
# two arms' solved sidecars comparable, which is a free check on whether the
# coefficient reaches the SOLVE or only the GATHER.
#
# SUBJECTS
# --------
# Not all 26 -- this arm is a diagnosis, not a delivery, and every subject here
# is one the corpus already named:
#   dry-erase-marker-head-cpl  BUILD-CROP 14.6: magenta "most VISIBLE on
#                              dry-erase because that subject has the highest
#                              edge contrast"
#   tweezers-cpl               one of the two stacks the superseded -704.5 red
#                              coefficient was originally fitted on
#   lavendar-cpl               a re-fit stack, strongly coloured
#   highly-angled-ruler-mm-cpl THE CONTROL. The only subject still showing the
#                              lens's NATURAL opposite-sign pattern
#                              (R -1.535, B +0.800, r2 = 0.814), so the re-fit
#                              can plausibly make it WORSE. Also the only member
#                              of TILTED_SUBJECTS, so it merges UNREGISTERED.
#   113MSDCF                   quoted at +0.972 px; cheap at 63 frames

param(
    [string]$Exe     = "C:\dev\strehl-out\DELIVER-V6\bin\strehl-caold.exe",
    [string]$Commit  = "6af834dac08d6605aee7ea3ad75809fdf6313770 + eps_r reverted to -704.5e-6",
    [string]$Root    = "D:\personal\macro",
    [string]$Dest    = "C:\dev\strehl-out\DELIVER-V6\masters-caold",
    [string]$Scratch = "C:\dev\strehl-out\DELIVER-V6\scratch",
    [string[]]$Subjects = @(
        "dry-erase-marker-head-cpl",
        "tweezers-cpl",
        "lavendar-cpl",
        "highly-angled-ruler-mm-cpl",
        "113MSDCF"
    )
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Scratch "warpmaps-caold") | Out-Null

foreach ($v in @("STREHL_GATE_FLOOR_SCALE","STREHL_WARPMAP","STREHL_ALIGN",
                 "STREHL_FIX_HALO","STREHL_FIX_CA","STREHL_EDGE_AWARE",
                 "STREHL_SMOOTH","STREHL_SMOOTH_HUBER","STREHL_DUMP_ELECTION",
                 "STREHL_COVER","STREHL_HULL")) {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
$env:STREHL_CACHE_DIR = Join-Path $Scratch "warpmaps-caold"

$exeHash = (Get-FileHash $Exe -Algorithm SHA256).Hash
$log      = Join-Path $Dest "render.log"
$manifest = Join-Path $Dest "MANIFEST.txt"

$hdr = @()
$hdr += "=== DELIVER-V6 arm C -- CA-OLD one-build control"
$hdr += "exe            : $Exe"
$hdr += "exe SHA256     : $exeHash"
$hdr += "exe build      : $(& $Exe --version 2>&1)"
$hdr += "commit         : $Commit"
$hdr += "delta vs pin   : optics.rs eps_r -508.4e-6 -> -704.5e-6 (1 insertion, 1 deletion)"
$hdr += "STREHL_CACHE_DIR = $($env:STREHL_CACHE_DIR)"
$hdr += "invocation     : <exe> stack <dir> -o <dest>\<subject>.tiff --srgb"
$hdr += "started        : $(Get-Date -Format o)"
$hdr | Out-File -FilePath $log -Encoding utf8
$hdr | Out-File -FilePath $manifest -Encoding utf8
"" | Out-File -FilePath $manifest -Append -Encoding utf8

$i = 0
foreach ($name in $Subjects) {
    $i++
    $dir    = Join-Path $Root $name
    $target = Join-Path $Dest "$name.tiff"
    if (Test-Path $target) { "[$i/$($Subjects.Count)] $name SKIP (exists)" | Tee-Object -FilePath $log -Append; continue }
    $n = (Get-ChildItem $dir -File -Filter *.ARW).Count
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out  = & $Exe stack $dir -o $target --srgb 2>&1
    $code = $LASTEXITCODE           # AGENTS rule 46: read BEFORE any pipeline
    $ErrorActionPreference = $prev
    $sw.Stop()
    $ok = (Test-Path $target) -and ($code -eq 0)
    "[$i/$($Subjects.Count)] $name frames=$n secs=$([math]::Round($sw.Elapsed.TotalSeconds,1)) exit=$code ok=$ok" |
        Tee-Object -FilePath $log -Append
    $out | Select-String -Pattern '^averaged|^measured floor|x white|^exposure|^build|^alignment|REFUSED' |
        ForEach-Object { "        $($_.Line.Trim())" } | Out-File -FilePath $log -Append -Encoding utf8
    if ($ok) {
        @("subject   : $name",
          "frames    : $n",
          "command   : `"$Exe`" stack `"$dir`" -o `"$target`" --srgb",
          "env       : STREHL_CACHE_DIR=$($env:STREHL_CACHE_DIR) ; all other STREHL_* unset",
          "exe SHA256: $exeHash",
          "commit    : $Commit",
          "out SHA256: $((Get-FileHash $target -Algorithm SHA256).Hash)",
          "bytes     : $((Get-Item $target).Length)",
          "") | Out-File -FilePath $manifest -Append -Encoding utf8
    }
}
"=== finished=$(Get-Date -Format o)" | Tee-Object -FilePath $log -Append
Remove-Item Env:\STREHL_CACHE_DIR -ErrorAction SilentlyContinue
