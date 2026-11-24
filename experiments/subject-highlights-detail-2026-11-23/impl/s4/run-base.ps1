param([string]$Exe = "C:/w/shd-s4-out/base/strehl.exe", [string]$Out = "C:/w/shd-s4-out/base", [string]$Cache = "C:/w/shd-s4-out/cache-base")
$ErrorActionPreference = "Continue"
$env:STREHL_CACHE_DIR = $Cache
$caps = @{
  weevil = "D:/StrehlCaptures/stack-1795460665629-8651";
  scarab = "D:/StrehlCaptures/stack-1795300522964-6430";
  tile4 = "D:/StrehlCaptures/stack-1795476520452-8651";
  tile1 = "D:/StrehlCaptures/stack-1795478933629-8651"
}
"exe $Exe" | Out-File "$Out/log.txt"
foreach ($k in @("weevil", "scarab", "tile4", "tile1")) {
  $t = Get-Date
  & $Exe focus-step $caps[$k] --json "$Out/focus-step-$k.json" *> "$Out/focus-step-$k.txt"
  "focus-step $k exit $LASTEXITCODE $(((Get-Date) - $t).TotalSeconds) s" | Out-File -Append "$Out/log.txt"
}
foreach ($k in @("weevil", "scarab")) {
  $t = Get-Date
  & $Exe subject $caps[$k] --json --out "$Out/subject-$k.json" > "$Out/subject-$k.stdout.json" 2> "$Out/subject-$k.txt"
  "subject $k exit $LASTEXITCODE $(((Get-Date) - $t).TotalSeconds) s" | Out-File -Append "$Out/log.txt"
}
foreach ($k in @("tile1", "tile4")) {
  $t = Get-Date
  & $Exe pixel-shift $caps[$k] --all-groups --json "$Out/pixel-shift-$k.json" *> "$Out/pixel-shift-$k.txt"
  "pixel-shift $k exit $LASTEXITCODE $(((Get-Date) - $t).TotalSeconds) s" | Out-File -Append "$Out/log.txt"
}
$t = Get-Date
& $Exe follow $caps["tile1"] --interval-ms 200 --idle-timeout-s 120 *> "$Out/follow-tile1.txt"
"follow tile1 exit $LASTEXITCODE $(((Get-Date) - $t).TotalSeconds) s" | Out-File -Append "$Out/log.txt"
"done" | Out-File -Append "$Out/log.txt"
