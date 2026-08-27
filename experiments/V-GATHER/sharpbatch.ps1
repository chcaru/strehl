# V-GATHER: batch driver. Subject, exposure as SHIP-V4 chose it, frames to render.
$jobs = @(
  @("109MSDCF",        "+2.60", 0),
  @("119MSDCF",        "+1.53", 0),
  @("coffee-bean",     "-0.22", 33),
  @("foam",            "-0.34", 33),
  @("flat-on-ruler-cpl","+1.95",33),
  @("wrapped-text-1",  "+2.27", 33),
  @("couch-fibers-cpl","+1.82", 33),
  @("lavendar-cpl",    "+1.43", 33),
  @("tweezers-cpl",    "+1.13", 33),
  @("bee-1-cpl",       "+1.50", 33)
)
foreach ($j in $jobs) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File "C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER\sharprender.ps1" -Subject $j[0] -Exposure $j[1] -Nmax $j[2]
}
Write-Host "BATCH COMPLETE"
