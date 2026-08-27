# V-LINEAR / continue_as_expired.ps1
#
# MEASURE what Zerene Stacker actually does to a batch run when its trial
# licence has expired.
#
# The expired-trial dialog offers four buttons: Visit Website, Install License
# Key, Continue as Expired, Exit Immediately.  "Continue as Expired" is a path
# the vendor put there and offers to the user; pressing it is ordinary use of
# the software, not circumvention.  Nothing here inspects, patches, times out,
# rolls back or otherwise interferes with the licence check -- the check runs,
# reaches its own conclusion, and we take the option it offers.
#
# The question being measured is narrow and matters: the dialog claims "You
# will not be able to save images or projects until a valid license key is
# installed."  If that is literally true, the comparator arm cannot be
# regenerated and the lane is blocked.  If instead Zerene saves something
# degraded or watermarked, that is a different and worse problem which must be
# detected rather than assumed.  Either way the answer has to be MEASURED.
#
# Verification before the click: the cursor is moved to the target, the window
# is re-captured, and the hover highlight in that capture is what confirms
# which button is under the pointer.  Only then is the button pressed.

param(
  [int]$WaitSec = 20,
  [string]$Xml = 'C:\dev\strehl-out\V-LINEAR\logs\ZereneBatch-pilot-PMax.xml',
  [string]$OutDir = 'C:\dev\strehl-out\V-LINEAR\pilot-out',
  [int]$BtnX = 333, [int]$BtnY = 337,
  [int]$IdleAbortSec = 300, [int]$MaxMinutes = 60
)
$ErrorActionPreference = 'Stop'
$logs = 'C:\dev\strehl-out\V-LINEAR\logs'

if (-not ('ZUi' -as [type])) {
  Add-Type -TypeDefinition @'
using System;using System.Text;using System.Runtime.InteropServices;using System.Drawing;
public class ZUi {
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc l, IntPtr p);
 delegate bool EnumWindowsProc(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] static extern int GetWindowTextLength(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
 [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] static extern bool SetCursorPos(int x, int y);
 [DllImport("user32.dll")] static extern void mouse_event(uint f, int x, int y, uint d, IntPtr e);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 public static IntPtr Find(uint want, string title) {
   IntPtr found = IntPtr.Zero;
   EnumWindows((h,p) => { uint pid; GetWindowThreadProcessId(h, out pid);
     if (pid == want && IsWindowVisible(h)) { int n = GetWindowTextLength(h);
       if (n > 0) { var sb = new StringBuilder(n+2); GetWindowText(h, sb, n+2);
                    if (sb.ToString().Contains(title)) { found = h; return false; } } }
     return true; }, IntPtr.Zero);
   return found; }
 public static string Titles(uint want) {
   var o = new StringBuilder();
   EnumWindows((h,p) => { uint pid; GetWindowThreadProcessId(h, out pid);
     if (pid == want && IsWindowVisible(h)) { int n = GetWindowTextLength(h);
       if (n > 0) { var sb = new StringBuilder(n+2); GetWindowText(h, sb, n+2); o.Append(sb.ToString()).Append(" | "); } }
     return true; }, IntPtr.Zero);
   return o.ToString(); }
 public static int[] Rect(IntPtr h) { RECT r; GetWindowRect(h, out r); return new int[]{r.L,r.T,r.R,r.B}; }
 public static string Shot(IntPtr h, string path) {
   RECT r; GetWindowRect(h, out r); int w = r.R-r.L, ht = r.B-r.T;
   if (w<=0||ht<=0) return "bad rect";
   using (var bmp = new Bitmap(w, ht)) using (var g = Graphics.FromImage(bmp)) {
     IntPtr dc = g.GetHdc(); bool ok = PrintWindow(h, dc, 2); g.ReleaseHdc(dc);
     if (!ok) g.CopyFromScreen(r.L, r.T, 0, 0, new Size(w, ht));
     bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png);
     return string.Format("{0}x{1} printwindow={2}", w, ht, ok); } }
 public static void Hover(IntPtr h, int x, int y) {
   RECT r; GetWindowRect(h, out r); SetForegroundWindow(h); SetCursorPos(r.L+x, r.T+y); }
 public static void Click() { mouse_event(0x0002,0,0,0,IntPtr.Zero); mouse_event(0x0004,0,0,0,IntPtr.Zero); }
}
'@ -ReferencedAssemblies System.Drawing, System.Drawing.Primitives, System.Drawing.Common, System.Private.Windows.GdiPlus, System.Private.Windows.Core
}

$lc = (Get-Content "$env:APPDATA\ZereneStacker\zerenstk.launchcmd" -Raw).Trim()
$tok = New-Object System.Collections.ArrayList
$cur = New-Object System.Text.StringBuilder; $inq = $false
foreach ($ch in $lc.ToCharArray()) {
  if ($ch -eq '"') { $inq = -not $inq; continue }
  if (-not $inq -and [char]::IsWhiteSpace($ch)) { if ($cur.Length) { [void]$tok.Add($cur.ToString()); [void]$cur.Clear() }; continue }
  [void]$cur.Append($ch) }
if ($cur.Length) { [void]$tok.Add($cur.ToString()) }
$exe = $tok[0] -replace 'javaw\.exe$','java.exe'

$before = @{}
Get-ChildItem $OutDir -File -ErrorAction SilentlyContinue | ForEach-Object { $before[$_.Name] = $_.Length }

$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $exe
foreach ($t in $tok[1..($tok.Count-1)]) { $psi.ArgumentList.Add(($t -replace '^-Xmx.*$','-Xmx16g')) }
foreach ($a in @('-noSplashScreen','-exitOnBatchScriptCompletion','-runMinimized','-batchScript',$Xml)) { $psi.ArgumentList.Add($a) }
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
$t0 = Get-Date
$p = [System.Diagnostics.Process]::Start($psi)
$tOut = $p.StandardOutput.ReadToEndAsync(); $tErr = $p.StandardError.ReadToEndAsync()

Start-Sleep -Seconds $WaitSec
$p.Refresh()
if ($p.HasExited) { Write-Host "exited early: $($p.ExitCode)"; exit 1 }
$h = [ZUi]::Find([uint32]$p.Id, 'Welcome')
if ($h -eq [IntPtr]::Zero) { Stop-Process -Id $p.Id -Force; throw 'no Welcome dialog' }
[ZUi]::Hover($h, $BtnX, $BtnY)
Start-Sleep -Milliseconds 900
Write-Host ([ZUi]::Shot($h, "$logs\zerene-hover.png"))
Write-Host "hover capture saved -> $logs\zerene-hover.png  (verify the highlight before trusting the click)"
[ZUi]::Click()
Start-Sleep -Seconds 3
Write-Host ("titles after click: {0}" -f [ZUi]::Titles([uint32]$p.Id))

$lastCpu = 0.0; $lastMove = Get-Date; $verdict = 'ok'
while (-not $p.HasExited) {
  Start-Sleep -Seconds 15; $p.Refresh(); if ($p.HasExited) { break }
  $cpu = $p.TotalProcessorTime.TotalSeconds
  if ($cpu - $lastCpu -gt 1.0) { $lastMove = Get-Date; $lastCpu = $cpu }
  $idle = ((Get-Date) - $lastMove).TotalSeconds
  Write-Host ("  [{0,5:N0}s] cpu={1,8:N1}s ws={2,6:N0}MB idle={3,4:N0}s titles={4}" -f `
    ((Get-Date)-$t0).TotalSeconds, $cpu, ($p.WorkingSet64/1MB), $idle, [ZUi]::Titles([uint32]$p.Id))
  if ($idle -gt $IdleAbortSec) { $verdict = "no CPU progress ${idle}s"; Stop-Process -Id $p.Id -Force; break }
  if (((Get-Date)-$t0).TotalMinutes -gt $MaxMinutes) { $verdict = 'MaxMinutes'; Stop-Process -Id $p.Id -Force; break }
}
$p.WaitForExit()
$tOut.Result | Out-File "$logs\zerene-expired.stdout.log" -Encoding utf8
$tErr.Result | Out-File "$logs\zerene-expired.stderr.log" -Encoding utf8
if (Test-Path "$env:APPDATA\ZereneStacker\LastNormalLog.txt") {
  Copy-Item "$env:APPDATA\ZereneStacker\LastNormalLog.txt" "$logs\zerene-expired.zslog.txt" -Force }
Write-Host ("EXIT={0}  {1:N1}s  watchdog={2}" -f $p.ExitCode, ((Get-Date)-$t0).TotalSeconds, $verdict)
$new = Get-ChildItem $OutDir -File | Where-Object { -not $before.ContainsKey($_.Name) }
Write-Host "NEW FILES IN OUTPUT FOLDER:"
if (-not $new) { Write-Host "  (none)" } else { $new | ForEach-Object { Write-Host ("  {0}  {1} bytes" -f $_.Name, $_.Length) } }
