# V-LINEAR / shot_window.ps1
# Capture a named top-level window of a running process to a PNG, for the record.
param([Parameter(Mandatory=$true)][string]$Title,
      [Parameter(Mandatory=$true)][string]$Png,
      [string]$ProcName = 'java')
$ErrorActionPreference = 'Stop'
if (-not ('ZShot' -as [type])) {
  Add-Type -TypeDefinition @'
using System;using System.Text;using System.Runtime.InteropServices;using System.Drawing;
public class ZShot {
 [DllImport("user32.dll")] static extern bool EnumWindows(EnumWindowsProc l, IntPtr p);
 delegate bool EnumWindowsProc(IntPtr h, IntPtr p);
 [DllImport("user32.dll")] static extern int GetWindowTextLength(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
 [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
 [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
 public static IntPtr Find(uint want, string title) {
   IntPtr f = IntPtr.Zero;
   EnumWindows((h,p) => { uint pid; GetWindowThreadProcessId(h, out pid);
     if (pid == want && IsWindowVisible(h)) { int n = GetWindowTextLength(h);
       if (n > 0) { var sb = new StringBuilder(n+2); GetWindowText(h, sb, n+2);
                    if (sb.ToString().Contains(title)) { f = h; return false; } } }
     return true; }, IntPtr.Zero);
   return f; }
 public static string Shot(IntPtr h, string path) {
   RECT r; GetWindowRect(h, out r); int w=r.R-r.L, ht=r.B-r.T;
   if (w<=0||ht<=0) return "bad rect";
   using (var b = new Bitmap(w, ht)) using (var g = Graphics.FromImage(b)) {
     IntPtr dc = g.GetHdc(); bool ok = PrintWindow(h, dc, 2); g.ReleaseHdc(dc);
     if (!ok) g.CopyFromScreen(r.L, r.T, 0, 0, new Size(w, ht));
     b.Save(path, System.Drawing.Imaging.ImageFormat.Png);
     return string.Format("{0}x{1} printwindow={2}", w, ht, ok); } }
}
'@ -ReferencedAssemblies System.Drawing, System.Drawing.Primitives, System.Drawing.Common, System.Private.Windows.GdiPlus, System.Private.Windows.Core
}
$procs = @(Get-Process $ProcName -ErrorAction SilentlyContinue)
if (-not $procs) { throw "no $ProcName process" }
foreach ($p in $procs) {
  $h = [ZShot]::Find([uint32]$p.Id, $Title)
  if ($h -ne [IntPtr]::Zero) { Write-Host ("pid {0}: {1}" -f $p.Id, [ZShot]::Shot($h, $Png)); Write-Host "saved $Png"; exit 0 }
}
throw "window '$Title' not found"
