$ErrorActionPreference = "Continue"
$Exe = "C:/w/shd-s4-out/new/strehl.exe"
$S = "C:/w/shd-s4-out/subj"
New-Item -ItemType Directory -Force $S | Out-Null
$caps = @{
  weevil = "D:/StrehlCaptures/stack-1795460665629-8651";
  scarab = "D:/StrehlCaptures/stack-1795300522964-6430";
  tile4 = "D:/StrehlCaptures/stack-1795476520452-8651";
  tile1 = "D:/StrehlCaptures/stack-1795478933629-8651"
}
# A. Without a subject: the base script with the new binary.
pwsh -NoProfile -File C:/w/shd-s4-out/run-base.ps1 -Exe $Exe -Out C:/w/shd-s4-out/new -Cache C:/w/shd-s4-out/cache-new
# B. With subjects.
$env:STREHL_CACHE_DIR = "C:/w/shd-s4-out/cache-subj"
"exe $Exe" | Out-File "$S/log.txt"
foreach ($k in @("tile1", "tile4")) {
  & $Exe subject $caps[$k] --json --out "$S/subject-$k.json" > $null 2> "$S/subject-$k.txt"
  "subject $k exit $LASTEXITCODE" | Out-File -Append "$S/log.txt"
}
Copy-Item C:/w/shd-s4-out/new/subject-weevil.json "$S/subject-weevil.json"
Copy-Item C:/w/shd-s4-out/new/subject-scarab.json "$S/subject-scarab.json"
foreach ($k in @("weevil", "scarab", "tile4", "tile1")) {
  & $Exe focus-step $caps[$k] --subject "$S/subject-$k.json" --json "$S/focus-step-$k.json" *> "$S/focus-step-$k.txt"
  "focus-step $k exit $LASTEXITCODE" | Out-File -Append "$S/log.txt"
}
foreach ($k in @("weevil", "scarab")) {
  $w = (Get-Content "$S/focus-step-$k.json" | ConvertFrom-Json).width
  & $Exe subject $caps[$k] --width $w --json --out "$S/bounds13-$k.json" > $null 2> "$S/bounds13-$k.txt"
  "bounds13 $k width $w exit $LASTEXITCODE" | Out-File -Append "$S/log.txt"
  & $Exe subject $caps[$k] --every 1 --width $w --json --out "$S/boundsall-$k.json" > $null 2> "$S/boundsall-$k.txt"
  "boundsall $k width $w exit $LASTEXITCODE" | Out-File -Append "$S/log.txt"
}
foreach ($k in @("tile1", "tile4")) {
  & $Exe pixel-shift $caps[$k] --all-groups --subject "$S/subject-$k.json" --json "$S/pixel-shift-$k.json" *> "$S/pixel-shift-$k.txt"
  "pixel-shift $k exit $LASTEXITCODE" | Out-File -Append "$S/log.txt"
}
& $Exe follow $caps["tile1"] --subject "$S/subject-tile1.json" --interval-ms 200 --idle-timeout-s 120 *> "$S/follow-tile1.txt"
"follow tile1 exit $LASTEXITCODE" | Out-File -Append "$S/log.txt"
"done" | Out-File -Append "$S/log.txt"
