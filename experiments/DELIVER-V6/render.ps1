# DELIVER-V6 -- re-render the 26 corpus masters from a CLEAN, PINNED build.
#
# Why this exists: every master in C:\dev\strehl-out\ORCH-FAITHFUL\faithful\ was
# rendered before the lateral-CA re-fit landed (optics.rs:461, eps_r =
# -508.4e-6), so every one of them carries the old coefficient and the magenta
# displacement it produced. The owner has never seen a frame with the fix in it.
#
# THE PROVENANCE PROBLEM THIS SCRIPT EXISTS TO SOLVE
# --------------------------------------------------
# ORCH-FAITHFUL's own log header says `commit=5f367a94` while every per-subject
# banner in the same log says `build: strehl 0.0.0 (8a480af9c6ba-dirty)`. That
# render came out of the shared working tree while other lanes were editing it,
# so what is actually in those masters is not recoverable from the record.
# Corpus fact 1886 measured the consequence directly: a coefficient-INDEPENDENT
# arm, which must reproduce bit-exactly, re-rendered with 33,003,417 pixels
# different and max 23210 DN, purely because the tree moved underneath it.
#
# So this script renders from a `git worktree` checkout of a named commit, built
# into a PRIVATE target dir, with the resulting exe copied out and pinned by
# SHA256. Every master here comes from that one binary.
#
# INVOCATION FIDELITY (brief: "same flags, same limits, same gates")
# -----------------------------------------------------------------
# The merge command is character-for-character ORCH-HEAD26's:
#     & $exe stack <dir> -o <out>.tiff --srgb
# No --limit, no --gate, no --auto-exposure, no --resampler, no --exposure.
# `--auto-exposure` is deliberately NOT passed, for the reason render_head26.ps1
# records: before 5f367a94 it double-normalised and blew 11 of 18 masters to a
# white median (facts 1815-1816).
#
# THE ONE ENVIRONMENT DEVIATION, AND WHY IT IS THE FAITHFUL CHOICE
# ---------------------------------------------------------------
# STREHL_CACHE_DIR is pointed at this run's own scratch. It is not a rendering
# flag; it relocates the warp-sidecar cache that `align_cmd::sidecar_path`
# reads. The shared default root (%LOCALAPPDATA%\strehl\warpmaps) currently
# holds 347 entries written by other lanes' binaries, and the cache key is
# (canonical capture path, solve config, generation) -- it does NOT include the
# binary. A warm entry from another lane's build would therefore be served to
# this render silently. Redirecting the cache forces every warp map to be solved
# by the pinned exe, which is the property this delivery is claiming.
#
# WHAT IS DELIBERATELY *NOT* SET
# ------------------------------
#   STREHL_WARPMAP  -- setting it would be a REAL behavioural deviation, not an
#     isolation. `merge_cmd::alignment_for` checks `is_tilted_subject` only on
#     the load_or_solve path; with STREHL_WARPMAP set it loads and APPLIES a
#     sidecar unconditionally. TILTED_SUBJECTS = ["highly-angled-ruler-mm-cpl"]
#     (align_cmd.rs:42) -- which is this delivery's control subject. Setting the
#     variable would silently register a stack the shipping default refuses to
#     register. AGENTS rule 45 recommends this variable against a hazard that
#     M97 has since fixed at source: sidecar_path is explicitly NOT
#     dir.join("warpmap.txt") any more, so the default path does not write into
#     the capture library. Verified: zero warpmap.txt under D:\personal\macro.
#   STREHL_GATE_FLOOR_SCALE, STREHL_ALIGN, STREHL_FIX_HALO, STREHL_FIX_CA,
#   STREHL_EDGE_AWARE, STREHL_SMOOTH, STREHL_SMOOTH_HUBER -- all cleared, so the
#     render is the shipping default. They are cleared rather than assumed
#     absent because they are inherited state (AGENTS rule 47's environment
#     clause).
#
# SUBJECT LIST
# ------------
# Taken from the 26 .tiff files already in ORCH-FAITHFUL, per the brief, NOT by
# re-scanning D:\personal\macro. The source library has since grown to 33
# subjects with ARW frames; rendering the 7 newer ones would produce masters
# with no old counterpart and confound the before/after this delivery exists to
# show. They are listed in the report as out of scope.

param(
    [string]$Exe     = "C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe",
    [string]$Commit  = "6af834dac08d6605aee7ea3ad75809fdf6313770",
    [string]$Root    = "D:\personal\macro",
    [string]$OldDir  = "C:\dev\strehl-out\ORCH-FAITHFUL\faithful",
    [string]$Dest    = "C:\dev\strehl-out\DELIVER-V6\masters",
    [string]$Scratch = "C:\dev\strehl-out\DELIVER-V6\scratch"
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Scratch "warpmaps") | Out-Null

# Clear inherited render-affecting state, then set the one isolation variable.
foreach ($v in @("STREHL_GATE_FLOOR_SCALE","STREHL_WARPMAP","STREHL_ALIGN",
                 "STREHL_FIX_HALO","STREHL_FIX_CA","STREHL_EDGE_AWARE",
                 "STREHL_SMOOTH","STREHL_SMOOTH_HUBER","STREHL_DUMP_ELECTION",
                 "STREHL_COVER")) {
    Remove-Item "Env:\$v" -ErrorAction SilentlyContinue
}
$env:STREHL_CACHE_DIR = Join-Path $Scratch "warpmaps"

$exeHash = (Get-FileHash $Exe -Algorithm SHA256).Hash
$log      = Join-Path $Dest "render.log"
$manifest = Join-Path $Dest "MANIFEST.txt"

$subjects = Get-ChildItem (Join-Path $OldDir "*.tiff") | ForEach-Object { $_.BaseName } | Sort-Object

$hdr = @()
$hdr += "=== DELIVER-V6 masters"
$hdr += "exe            : $Exe"
$hdr += "exe SHA256     : $exeHash"
$hdr += "exe build      : $(& $Exe --version 2>&1)"
$hdr += "commit         : $Commit"
$hdr += "source root    : $Root  (READ-ONLY -- nothing is written here)"
$hdr += "STREHL_CACHE_DIR = $($env:STREHL_CACHE_DIR)"
$hdr += "all other STREHL_* : unset (shipping default)"
$hdr += "invocation     : <exe> stack <dir> -o <dest>\<subject>.tiff --srgb"
$hdr += "subjects       : $($subjects.Count) (from $OldDir)"
$hdr += "started        : $(Get-Date -Format o)"
$hdr | Out-File -FilePath $log -Encoding utf8
$hdr | Out-File -FilePath $manifest -Encoding utf8
"" | Out-File -FilePath $manifest -Append -Encoding utf8

$i = 0
foreach ($name in $subjects) {
    $i++
    $dir    = Join-Path $Root $name
    $target = Join-Path $Dest "$name.tiff"
    if (Test-Path $target) {
        "[$i/$($subjects.Count)] $name SKIP (exists)" | Tee-Object -FilePath $log -Append
        continue
    }
    if (-not (Test-Path $dir)) {
        "[$i/$($subjects.Count)] $name MISSING SOURCE $dir" | Tee-Object -FilePath $log -Append
        continue
    }
    $n = (Get-ChildItem $dir -File -Filter *.ARW).Count
    $sw = [Diagnostics.Stopwatch]::StartNew()

    # `stack` writes its banner to stderr; with ErrorActionPreference=Stop a
    # native command's stderr is a terminating error, so relax it around the
    # merge exactly as render_head26.ps1 does.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # AGENTS rule 46: capture the stream and the code in two statements and
    # filter the VARIABLE afterwards. A `| Select-Object -First N` between the
    # process and $LASTEXITCODE silently reports 0 under PS7 whenever it
    # truncates, which turns a failed render into a passing one.
    $out  = & $Exe stack $dir -o $target --srgb 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    $sw.Stop()

    $ok = (Test-Path $target) -and ($code -eq 0)
    $line = "[$i/$($subjects.Count)] $name frames=$n secs=$([math]::Round($sw.Elapsed.TotalSeconds,1)) exit=$code ok=$ok"
    $line | Tee-Object -FilePath $log -Append

    $banner = $out | Select-String -Pattern '^averaged|^measured floor|x white|^exposure|^build|^alignment|REFUSED|Error|error' |
        ForEach-Object { $_.Line.Trim() }
    foreach ($b in $banner) { "        $b" | Out-File -FilePath $log -Append -Encoding utf8 }

    if ($ok) {
        $oh = (Get-FileHash $target -Algorithm SHA256).Hash
        $bytes = (Get-Item $target).Length
        $rec = @()
        $rec += "subject   : $name"
        $rec += "frames    : $n"
        $rec += "command   : `"$Exe`" stack `"$dir`" -o `"$target`" --srgb"
        $rec += "env       : STREHL_CACHE_DIR=$($env:STREHL_CACHE_DIR) ; all other STREHL_* unset"
        $rec += "exe SHA256: $exeHash"
        $rec += "commit    : $Commit"
        $rec += "out SHA256: $oh"
        $rec += "bytes     : $bytes"
        $rec += "secs      : $([math]::Round($sw.Elapsed.TotalSeconds,1))"
        $rec += ""
        $rec | Out-File -FilePath $manifest -Append -Encoding utf8
    } else {
        @("subject   : $name", "FAILED exit=$code", "") |
            Out-File -FilePath $manifest -Append -Encoding utf8
    }
}

"=== finished=$(Get-Date -Format o)" | Tee-Object -FilePath $log -Append
Remove-Item Env:\STREHL_CACHE_DIR -ErrorAction SilentlyContinue
