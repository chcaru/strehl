# M97m: does --index-map / STREHL_DUMP_ELECTION perturb the merged image?
#
# The interesting bar is a NULL (bytes unchanged), and a null is worthless
# without a plant proving the comparison can fire. Arm E is that plant.
$ErrorActionPreference = "Continue"
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$exe = "C:\dev\strehl-target-m97\release\strehl.exe"
$dir = "D:\personal\macro\109MSDCF"
$o   = "C:\dev\strehl-out\M97\election"
New-Item -ItemType Directory -Force -Path $o | Out-Null
Get-ChildItem $o -File | Remove-Item -Force

# Alignment off in EVERY arm: it removes the shared sidecar cache as a
# confound entirely, and treatment and control are then identical but for the
# flag under test.
$env:STREHL_ALIGN = "0"
Remove-Item Env:\STREHL_DUMP_ELECTION -ErrorAction SilentlyContinue

function Hash($p) {
  if (Test-Path $p) { (Get-FileHash $p -Algorithm SHA256).Hash.Substring(0,16) } else { "ABSENT" }
}

function Arm($name, $argv) {
  $out = & $exe @argv 2>&1
  $code = $LASTEXITCODE
  $out | Out-File -FilePath "$o\$name.log" -Encoding utf8
  $el = $out | Select-String "election map" | Out-String
  "  [$name] exit=$code $($el.Trim())"
}

"=== M97m: election map, byte-freeze bars ==="
"stack: $dir  limit 12  gate 4.0 (explicit)  STREHL_ALIGN=0"
""

Arm "A" @("stack",$dir,"--limit","12","--gate","4.0","--out","$o\A.tiff")
Arm "B" @("stack",$dir,"--limit","12","--gate","4.0","--out","$o\B.tiff","--index-map","$o\map-B.tiff")

$env:STREHL_DUMP_ELECTION = "$o\map-C.tiff"
Arm "C" @("stack",$dir,"--limit","12","--gate","4.0","--out","$o\C.tiff")
Remove-Item Env:\STREHL_DUMP_ELECTION

# PLANT: one more frame must move the merged bytes AND the election map.
# If this arm matches A, the hash comparison is dead and B1/B2 mean nothing.
Arm "E" @("stack",$dir,"--limit","13","--gate","4.0","--out","$o\E.tiff","--index-map","$o\map-E.tiff")

""
$hA=Hash "$o\A.tiff"; $hB=Hash "$o\B.tiff"; $hC=Hash "$o\C.tiff"; $hE=Hash "$o\E.tiff"
$mB=Hash "$o\map-B.tiff"; $mC=Hash "$o\map-C.tiff"; $mE=Hash "$o\map-E.tiff"
"merged A (no flag)      : $hA"
"merged B (--index-map)  : $hB"
"merged C (env var)      : $hC"
"merged E (PLANT limit13): $hE"
"map B / map C / map E   : $mB / $mC / $mE"
""
$fail = 0
function Bar($label, $ok) {
  if ($ok) { "PASS  $label" } else { "FAIL  $label"; $script:fail++ }
}
Bar "B2  --index-map does not move the merged image (A == B)"        ($hA -eq $hB -and $hA -ne "ABSENT")
Bar "B3  STREHL_DUMP_ELECTION does not move it either (A == C)"      ($hA -eq $hC)
Bar "B1  --index-map wrote a map"                                    ($mB -ne "ABSENT")
Bar "B3b env var wrote a map, identical to the flag's (B == C)"      ($mC -ne "ABSENT" -and $mB -eq $mC)
Bar "B4  PLANT: 13 frames moves the merged image (A != E)"           ($hA -ne $hE -and $hE -ne "ABSENT")
Bar "B4b PLANT: 13 frames moves the election map (mapB != mapE)"     ($mB -ne $mE -and $mE -ne "ABSENT")
""
if ($fail -eq 0) { "ALL BARS PASS" } else { "$fail BAR(S) FAILED" }
