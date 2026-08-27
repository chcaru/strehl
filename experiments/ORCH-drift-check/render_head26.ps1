# Render every corpus subject at the current HEAD build.
#
# Why this exists: as of fact 1805 every master on disk was rendered at pin
# 9b05d0b7, which is 13 commits and 12,637 lines of `crates/` behind HEAD, so
# every quality verdict in the campaign was pronounced on a stale artefact
# (discipline 34). This produces the current control that the whole fleet is
# missing, and the set the owner can actually look at.
#
# Arms are selected by -Scale. Unset renders the shipping default; a value is
# passed through STREHL_GATE_FLOOR_SCALE, whose all-ones null is byte-identical
# to unset (fact 1809), so the arm label is honest by construction.

param(
    [string]$Scale = "",
    [string]$Tag   = "default",
    [string]$Root  = "D:\personal\macro",
    [string]$Out   = "C:\dev\strehl-out\ORCH-HEAD26",
    [string]$Exe   = "C:\dev\blog\death-of-software\projects\strehl\target\release\strehl.exe"
)

$ErrorActionPreference = "Stop"
$exe = $Exe
$dest = Join-Path $Out $Tag
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$log = Join-Path $dest "render.log"

# Pin the binary into the log. A verdict that does not name the binary it was
# measured on is exactly the defect discipline 34 exists to stop.
$sha = (Get-FileHash $exe -Algorithm SHA256).Hash.Substring(0, 16)
$commit = (git -C "C:\dev\blog\death-of-software\projects\strehl" rev-parse --short HEAD)
"=== ORCH-HEAD26 tag=$Tag scale='$Scale' binary=$sha commit=$commit started=$(Get-Date -Format o)" |
    Out-File -FilePath $log -Encoding utf8

if ($Scale -ne "") { $env:STREHL_GATE_FLOOR_SCALE = $Scale }
else { Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue }

$subjects = Get-ChildItem $Root -Directory |
    Where-Object { (Get-ChildItem $_.FullName -File -Filter *.ARW -ErrorAction SilentlyContinue).Count -gt 0 } |
    Sort-Object Name

$total = $subjects.Count
$i = 0
foreach ($s in $subjects) {
    $i++
    $n = (Get-ChildItem $s.FullName -File -Filter *.ARW).Count
    $target = Join-Path $dest "$($s.Name).tiff"
    if (Test-Path $target) {
        "[$i/$total] $($s.Name) SKIP (exists)" | Tee-Object -FilePath $log -Append
        continue
    }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    # `stack` writes its banner to stderr. With ErrorActionPreference=Stop a
    # native command's stderr is a *terminating* error, which killed the first
    # run of this script after one subject -- so the merge is deliberately
    # performed with it relaxed, and the render is judged by whether the file
    # appeared rather than by the stream it wrote to.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    # `--auto-exposure` is deliberately NOT passed. It is superseded on the
    # `--srgb` path as of 5f367a94 and now applies nothing, but before that fix
    # it double-normalised and blew 11 of 18 masters to a white median (facts
    # 1815-1816). Omitting it states the intent rather than relying on the
    # guard, and keeps this script honest if it is ever run against an older
    # binary via -Exe.
    $banner = & $exe stack $s.FullName -o $target --srgb 2>&1 |
        Select-String -Pattern '^averaged|^measured floor|x white|exposure|^build' |
        ForEach-Object { $_.Line.Trim() }
    $ErrorActionPreference = $prev
    $sw.Stop()
    $ok = Test-Path $target
    $line = "[$i/$total] $($s.Name) frames=$n secs=$([math]::Round($sw.Elapsed.TotalSeconds,1)) ok=$ok"
    $line | Tee-Object -FilePath $log -Append
    foreach ($b in $banner) { "        $b" | Out-File -FilePath $log -Append -Encoding utf8 }
}

"=== finished=$(Get-Date -Format o)" | Tee-Object -FilePath $log -Append
Remove-Item Env:\STREHL_GATE_FLOOR_SCALE -ErrorAction SilentlyContinue
