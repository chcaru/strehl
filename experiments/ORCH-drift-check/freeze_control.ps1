# Negative control for the P1 byte-freeze failure.
#
# QUESTION: did the orchestrator's application of M100 change the byte-frozen
# measurement output, or was the freeze already broken at HEAD by a milestone
# that landed after M100 measured (M86c wired alignment into `strehl stack`)?
#
# METHOD: restore the pre-patch files, rebuild, re-run P1, compare. If pre-patch
# P1 == post-patch P1, M100 is inert on the measurement path and the freeze was
# broken earlier by someone else.
#
# PREDICTION (pre-registered): pre-patch P1 == CF266004EB1EE57A82E17038F3B6C9B497C4975CD8C5A7C5AB1748122A94B868
#
# NOTE: Copy-Item PRESERVES the source mtime, so cargo will skip the rebuild and
# measure the wrong binary. Every restore here is followed by an explicit touch.
$ErrorActionPreference = "Continue"
$root = "C:\dev\blog\death-of-software\projects\strehl"
$src = "$root\crates\strehl-cli\src"
$s = "$root\.cargo-target-orch\release\strehl.exe"
$dir = "D:\personal\macro\bee-3-cpl"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:CARGO_TARGET_DIR = "$root\.cargo-target-orch"
$POST = "CF266004EB1EE57A82E17038F3B6C9B497C4975CD8C5A7C5AB1748122A94B868"

function Restore-From($from) {
  foreach ($f in @("main.rs", "merge_cmd.rs")) {
    Copy-Item "$from\$f" "$src\$f" -Force
    (Get-Item "$src\$f").LastWriteTime = Get-Date
  }
}
function Build-It {
  Push-Location $root
  cargo build -p strehl-cli --release 2>&1 | Select-String -Pattern "^error|Finished" | ForEach-Object { "    $_" }
  Pop-Location
}
function P1-Hash($tag) {
  $out = "$env:TEMP\M100-bars\ctl-$tag.tif"
  & $s stack $dir --gate 2 --limit 60 --out $out 2>&1 | Out-Null
  if (-not (Test-Path $out)) { return "NO-OUTPUT" }
  return (Get-FileHash $out -Algorithm SHA256).Hash
}

# Preserve the patched work before touching anything.
New-Item -ItemType Directory -Force -Path "$env:TEMP\M100-patched" | Out-Null
foreach ($f in @("main.rs", "merge_cmd.rs")) { Copy-Item "$src\$f" "$env:TEMP\M100-patched\$f" -Force }
"patched files saved to $env:TEMP\M100-patched"

"=== restoring PRE-PATCH source ==="
Restore-From "$env:TEMP\M100-backup"
Build-It
$pre = P1-Hash "prepatch"
"PRE-PATCH  P1 : $pre"

"=== restoring PATCHED source ==="
Restore-From "$env:TEMP\M100-patched"
Build-It
$post = P1-Hash "postpatch"
"POST-PATCH P1 : $post"
""
if ($pre -eq $post) {
  "VERDICT: M100 IS INERT on the measurement path (pre == post)."
  "         The freeze was broken BEFORE this patch, by a milestone that landed"
  "         after M100 measured. That is a separate finding, not a defect here."
} else {
  "VERDICT: **M100 CHANGED THE BYTE-FROZEN OUTPUT.** This is a defect. Do not commit."
}
if ($post -ne $POST) { "WARNING: post-patch hash drifted from the earlier run ($POST) -- non-determinism?" }
