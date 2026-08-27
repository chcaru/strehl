# V-LINEAR / capture_dialog.ps1
#
# Launch Zerene exactly as run_zerene.ps1 does, wait for the modal window it
# stops on, capture that window to a PNG, then kill the process.
#
# WHY THIS EXISTS.  Zerene's batch run stalls on a window titled "Welcome to
# Zerene Stacker".  Swing draws its dialog contents as lightweight components
# inside a single HWND, so EnumChildWindows returns nothing and there is no way
# to read the message as text.  The only honest way to find out what the
# application is telling us -- and specifically whether it is refusing to run,
# nagging, or offering a degraded mode -- is to look at the pixels it drew.
#
# This reads a dialog the application chose to display.  It does not inspect,
# patch or bypass anything.

param([int]$WaitSec = 20)
$ErrorActionPreference = 'Stop'
$png = 'C:\dev\strehl-out\V-LINEAR\logs\zerene-welcome.png'

if (-not ('ZCap' -as [type])) {
  Add-Type -TypeDefinition @'
using System;using System.Text;using System.Runtime.InteropServices;
using System.Drawing;
public class ZCap {
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc l, IntPtr p);
 delegate bool EnumWindowsProc(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] static extern int GetWindowTextLength(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 public static IntPtr Find(uint want, string title) {
   IntPtr found = IntPtr.Zero;
   EnumWindows((h,p) => {
     uint pid; GetWindowThreadProcessId(h, out pid);
     if (pid == want && IsWindowVisible(h)) {
       int n = GetWindowTextLength(h);
       if (n > 0) { var sb = new StringBuilder(n+2); GetWindowText(h, sb, n+2);
                    if (sb.ToString().Contains(title)) { found = h; return false; } }
     }
     return true;
   }, IntPtr.Zero);
   return found;
 }
 public static string Shot(IntPtr h, string path) {
   RECT r; GetWindowRect(h, out r);
   int w = r.R - r.L, ht = r.B - r.T;
   if (w <= 0 || ht <= 0) return "bad rect";
   using (var bmp = new Bitmap(w, ht))
   using (var g = Graphics.FromImage(bmp)) {
     IntPtr dc = g.GetHdc();
     bool ok = PrintWindow(h, dc, 2);   // PW_RENDERFULLCONTENT
     g.ReleaseHdc(dc);
     if (!ok) { g.CopyFromScreen(r.L, r.T, 0, 0, new Size(w, ht)); }
     bmp.Save(path, System.Drawing.Imaging.ImageFormat.Png);
     return string.Format("{0}x{1} printwindow={2}", w, ht, ok);
   }
 }
 public static string Titles(uint want) {
   var o = new StringBuilder();
   EnumWindows((h,p) => { uint pid; GetWindowThreadProcessId(h, out pid);
     if (pid == want && IsWindowVisible(h)) { int n = GetWindowTextLength(h);
       if (n > 0) { var sb = new StringBuilder(n+2); GetWindowText(h, sb, n+2); o.Append(sb.ToString()).Append(" | "); } }
     return true; }, IntPtr.Zero);
   return o.ToString();
 }
}
'@ -ReferencedAssemblies System.Drawing, System.Drawing.Primitives, System.Drawing.Common, System.Private.Windows.GdiPlus, System.Private.Windows.Core
}

$lc = (Get-Content "$env:APPDATA\ZereneStacker\zerenstk.launchcmd" -Raw).Trim()
$tok = New-Object System.Collections.ArrayList
$cur = New-Object System.Text.StringBuilder; $inq = $false
foreach ($ch in $lc.ToCharArray()) {
  if ($ch -eq '"') { $inq = -not $inq; continue }
  if (-not $inq -and [char]::IsWhiteSpace($ch)) { if ($cur.Length) { [void]$tok.Add($cur.ToString()); [void]$cur.Clear() }; continue }
  [void]$cur.Append($ch)
}
if ($cur.Length) { [void]$tok.Add($cur.ToString()) }
$exe = $tok[0] -replace 'javaw\.exe$', 'java.exe'

$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $exe
foreach ($t in $tok[1..($tok.Count-1)]) { $psi.ArgumentList.Add(($t -replace '^-Xmx.*$', '-Xmx4g')) }
foreach ($a in @('-noSplashScreen','-exitOnBatchScriptCompletion','-runMinimized',
                 '-batchScript','C:\dev\strehl-out\V-LINEAR\logs\ZereneBatch-pilot-PMax.xml')) { $psi.ArgumentList.Add($a) }
$psi.UseShellExecute = $false
$p = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Seconds $WaitSec
$p.Refresh()
if ($p.HasExited) { Write-Host "process already exited: $($p.ExitCode)"; exit 0 }
Write-Host ("visible titles: {0}" -f ([ZCap]::Titles([uint32]$p.Id)))
$h = [ZCap]::Find([uint32]$p.Id, 'Welcome')
if ($h -eq [IntPtr]::Zero) { Write-Host 'no Welcome window found' } else { Write-Host ([ZCap]::Shot($h, $png)); Write-Host "saved $png" }
Stop-Process -Id $p.Id -Force
