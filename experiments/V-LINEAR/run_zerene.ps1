# V-LINEAR / run_zerene.ps1
#
# Run Zerene Stacker headlessly on a directory of frames, one stacking method
# per invocation, and report enough for the run to be reproduced and audited.
#
# THE INVOCATION IS THE VENDOR'S OWN, NOT A GUESS.
# `%APPDATA%\ZereneStacker\zerenstk.launchcmd` is written by Zerene itself every
# time it launches from its icon, and its Batch API page says everything up to
# and including `com.zerenesystems.stacker.gui.MainFrame` is to be taken from
# that file unmodified.  This script READS that file and appends only the
# documented options `-noSplashScreen -exitOnBatchScriptCompletion
# -runMinimized -batchScript <path>`.  One substitution is made and stated:
#   javaw.exe -> java.exe   (the vendor's own docs: "This is required on Windows
#                            systems in order to produce console output that can
#                            be logged or examined.  If javaw.exe is used, then
#                            the application runs silently.")
# -Xmx may be lowered with -Xmx for pilot runs; the value used is printed.
#
# WHY EACH METHOD GETS ITS OWN RUN
# A single batch with two Tasks would stack the second method from a project
# whose frames Zerene has already registered, which risks a second resample on
# one arm and not the other.  Two runs from the pristine source directory give
# PMax and DMap exactly one registration each -- the same count strehl's own
# arm carries.
#
# WHY THERE IS A WATCHDOG
# MEASURED 2026-08-27: a malformed -Dlaunchcmddir (a stray quote left by a
# careless tokeniser) made Zerene open a modal dialog titled "Problem with
# application data directory" and then sit there.  The process stayed
# Responding, burned 2.03 s of CPU in nine minutes, wrote nothing, and never
# exited.  A batch runner for a GUI-hosted application therefore CANNOT use
# "exit code 0" as its liveness signal -- there is no exit code until a human
# clicks something.  This script polls CPU time and enumerates the process's
# visible top-level windows; if a window other than the known-benign ones
# appears, it prints the title, kills the process and fails loudly.

param(
  [Parameter(Mandatory=$true)][string]$Source,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [Parameter(Mandatory=$true)][ValidateSet('PMax','DMap')][string]$Method,
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$Xmx = '',
  [int]$IdleAbortSec = 240,
  [int]$MaxMinutes = 240
)

$ErrorActionPreference = 'Stop'
$logs = 'C:\dev\strehl-out\V-LINEAR\logs'
New-Item -ItemType Directory -Force -Path $OutDir, $logs | Out-Null

if (-not ('ZWin' -as [type])) {
  Add-Type -TypeDefinition @'
using System;using System.Text;using System.Collections.Generic;using System.Runtime.InteropServices;
public class ZWin {
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc l, IntPtr p);
 delegate bool EnumWindowsProc(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] static extern int GetWindowTextLength(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 public static List<string> Titles(uint want) {
   var outp = new List<string>();
   EnumWindows((h,p) => {
     uint pid; GetWindowThreadProcessId(h, out pid);
     if (pid == want && IsWindowVisible(h)) {
       int n = GetWindowTextLength(h);
       if (n > 0) { var sb = new StringBuilder(n+2); GetWindowText(h, sb, n+2); outp.Add(sb.ToString()); }
     }
     return true;
   }, IntPtr.Zero);
   return outp;
 }
}
'@
}
# Titles Zerene legitimately shows while working.  Anything else is a dialog
# waiting for a click, i.e. a hang.
$benign = @('Zerene Stacker', 'theAwtToolkitWindow', 'MSCTFIME UI', 'Default IME', '')

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$xml  = Join-Path $logs "ZereneBatch-$Name.xml"
python (Join-Path $here 'make_batch.py') --source $Source --outdir $OutDir `
       --method $Method --name $Name --xml $xml
if (-not (Test-Path $xml)) { throw "batch script not written: $xml" }

# ---- tokenise the vendor launch command --------------------------------
# Split on whitespace that is outside double quotes; drop the quote characters
# wherever they appear in the token.  A regex like '"[^"]*"|\S+' plus Trim('"')
# is WRONG: it mangles -Dfoo="C:\path with no spaces" into -Dfoo="C:\path,
# which is what caused the modal-dialog hang described above.
$lc = (Get-Content "$env:APPDATA\ZereneStacker\zerenstk.launchcmd" -Raw).Trim()
$tok = New-Object System.Collections.ArrayList
$cur = New-Object System.Text.StringBuilder
$inq = $false
foreach ($ch in $lc.ToCharArray()) {
  if ($ch -eq '"') { $inq = -not $inq; continue }
  if (-not $inq -and [char]::IsWhiteSpace($ch)) {
    if ($cur.Length -gt 0) { [void]$tok.Add($cur.ToString()); [void]$cur.Clear() }
    continue
  }
  [void]$cur.Append($ch)
}
if ($cur.Length -gt 0) { [void]$tok.Add($cur.ToString()) }

$exe = $tok[0] -replace 'javaw\.exe$', 'java.exe'
if (-not (Test-Path $exe)) { throw "java not found: $exe" }
$jargs = @()
foreach ($t in $tok[1..($tok.Count - 1)]) {
  if ($Xmx -ne '' -and $t -like '-Xmx*') { $jargs += "-Xmx$Xmx" } else { $jargs += $t }
}
$jargs += @('-noSplashScreen', '-exitOnBatchScriptCompletion', '-runMinimized',
            '-batchScript', $xml)

Write-Host "batch script : $xml"
Write-Host "launchcmd    : $lc"
Write-Host ("java exe     : {0}" -f $exe)
foreach ($a in $jargs) { Write-Host ("  arg          : {0}" -f $a) }

$before = @{}
Get-ChildItem $OutDir -File -ErrorAction SilentlyContinue | ForEach-Object { $before[$_.Name] = $_.Length }

# Start-Process -ArgumentList joins the array with single spaces and does NOT
# quote members containing spaces, which splits the -classpath value at
# "C:\Program Files" and yields
#   Error: Could not find or load main class Files\ZereneStacker\...
# MEASURED 2026-08-27.  ProcessStartInfo.ArgumentList (.NET 5+) applies the
# Win32 CommandLineToArgvW quoting rules per element, so use that instead.
$so = "$logs\zerene-$Name.stdout.log"
$se = "$logs\zerene-$Name.stderr.log"
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $exe
foreach ($a in $jargs) { $psi.ArgumentList.Add($a) }
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError  = $true
$t0 = Get-Date
$p = [System.Diagnostics.Process]::Start($psi)
# Drain both pipes on background threads: a full 4 KB pipe buffer deadlocks the
# child, and that deadlock looks exactly like "still working" to a watchdog.
$tOut = $p.StandardOutput.ReadToEndAsync()
$tErr = $p.StandardError.ReadToEndAsync()

# ---- watchdog ----------------------------------------------------------
$lastCpu = 0.0; $lastMove = Get-Date; $verdict = 'ok'
while (-not $p.HasExited) {
  Start-Sleep -Seconds 15
  $p.Refresh()
  if ($p.HasExited) { break }
  $titles = [ZWin]::Titles([uint32]$p.Id)
  $bad = @($titles | Where-Object { $benign -notcontains $_ })
  if ($bad.Count -gt 0) {
    Write-Host ("WATCHDOG: unexpected window(s): {0}" -f ($bad -join ' | '))
    $verdict = "modal dialog: $($bad -join ' | ')"
    Stop-Process -Id $p.Id -Force; break
  }
  $cpu = $p.TotalProcessorTime.TotalSeconds
  if ($cpu - $lastCpu -gt 1.0) { $lastMove = Get-Date; $lastCpu = $cpu }
  $idle = ((Get-Date) - $lastMove).TotalSeconds
  $el = [math]::Round(((Get-Date) - $t0).TotalSeconds)
  Write-Host ("  [{0,5}s] cpu={1,8:N1}s ws={2,6:N0}MB idle={3,4:N0}s" -f $el, $cpu, ($p.WorkingSet64/1MB), $idle)
  if ($idle -gt $IdleAbortSec) {
    $verdict = "no CPU progress for ${idle}s"; Stop-Process -Id $p.Id -Force; break
  }
  if (((Get-Date) - $t0).TotalMinutes -gt $MaxMinutes) {
    $verdict = "exceeded MaxMinutes=$MaxMinutes"; Stop-Process -Id $p.Id -Force; break
  }
}
$p.WaitForExit()
$code = $p.ExitCode
$dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
$tOut.Result | Out-File -FilePath $so -Encoding utf8
$tErr.Result | Out-File -FilePath $se -Encoding utf8

$zl = "$env:APPDATA\ZereneStacker\LastNormalLog.txt"
if (Test-Path $zl) { Copy-Item $zl "$logs\zerene-$Name.zslog.txt" -Force }

Write-Host ("EXIT={0}  {1}s  watchdog={2}" -f $code, $dt, $verdict)
$new = Get-ChildItem $OutDir -File | Where-Object { -not $before.ContainsKey($_.Name) }
Write-Host "NEW FILES IN OUTPUT FOLDER:"
if (-not $new) { Write-Host "  (none)" } else { $new | ForEach-Object { Write-Host ("  {0}  {1} bytes" -f $_.Name, $_.Length) } }

if ($verdict -ne 'ok') { throw "Zerene run aborted by watchdog: $verdict" }
if ($code -ne 0)       { throw "Zerene exited $code" }
if (-not $new)         { throw "Zerene exited 0 but wrote no output file to $OutDir" }
