<#
  Owner's do-no-harm acceptance test.

  couch-fibers-cpl is currently GOOD and is the subject most likely to be
  silently degraded by BUILD-SHARP's work.  109MSDCF and bee-1-cpl ride along.

  Both arms of every subject are rendered BACK TO BACK FROM ONE PINNED BINARY
  (rule 4).  The only difference between the arms is STREHL_SMOOTH:

    BEFORE = STREHL_SMOOTH=0    the free solve, i.e. HEAD before 70934bb
    AFTER  = unset              the shipped default, lambda = 1

  Nothing else moves.  restore.rs is not on any product path, so it cannot
  appear in either arm; this run tests the alignment default only.
#>
$ErrorActionPreference = "Stop"
$drv = "C:\dev\strehl-out\BUILD-SHARP\run-render.ps1"

foreach ($subject in @("couch-fibers-cpl", "109MSDCF", "bee-1-cpl")) {
    foreach ($pair in @(@("guard-BEFORE", "0"), @("guard-AFTER", "default"))) {
        & $drv -Subject $subject -Arm $pair[0] -Smooth $pair[1]
    }
}
