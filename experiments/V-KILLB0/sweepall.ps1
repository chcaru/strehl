param([string]$Arm="b0x4",[string]$Stats="C:\dev\strehl-out\V-KILLB0\stats")
$ErrorActionPreference="Continue"
$root="C:\dev\strehl-out\V-KILLB0"
$done=@()
foreach($f in Get-ChildItem "$root\default\*.tiff"){
  $n=$f.BaseName
  $b="$root\$Arm\$n.tiff"
  if(-not (Test-Path $b)){ continue }
  $j="$Stats\$n.json"
  if($Arm -ne "b0x4"){ $j="$Stats\$Arm-$n.json" }
  if(Test-Path $j){ "SKIP $n"; continue }
  $outn = $n
  if($Arm -ne "b0x4"){ $outn = "$Arm-$n" }
  python sweep.py $outn $f.FullName $b $Stats
  $done+=$n
}
"swept: $($done.Count)"
