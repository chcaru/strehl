param([Parameter(Mandatory=$true)][string]$Manifest)
$ErrorActionPreference = 'Stop'
$receiptPath = [IO.Path]::ChangeExtension($Manifest, 'write-result.json')
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Administrator privileges are required to write the microSD.' }
    $m = Get-Content -LiteralPath $Manifest -Raw | ConvertFrom-Json
    $imagePath = (Resolve-Path -LiteralPath $m.image).Path
    $imageInfo = Get-Item -LiteralPath $imagePath
    if ($imageInfo.Length -ne $m.imageBytes -or $imageInfo.Length % 512 -ne 0) { throw 'Image size mismatch.' }
    if ((Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $m.imageSha256) { throw 'Image checksum mismatch.' }
    # Re-identify the explicitly authorized F: card immediately before any write.
    $disk = Get-Partition -DriveLetter F | Get-Disk
    if ($disk.Number -ne $m.diskNumber -or $disk.UniqueId -ne $m.diskUniqueId -or $disk.Size -ne $m.diskBytes -or $disk.FriendlyName -ne $m.diskName -or $disk.BusType -ne 'USB' -or $disk.IsBoot -or $disk.IsSystem -or $disk.IsReadOnly -or $disk.IsOffline) { throw 'F: is no longer the recorded removable SanDisk card. Nothing was written.' }
    $partitions = @(Get-Partition -DiskNumber $disk.Number)
    if ($partitions.Count -ne 1 -or $partitions[0].DriveLetter -ne 'F') { throw 'The card partition layout changed. Nothing was written.' }
    if ($imageInfo.Length -ge $disk.Size) { throw 'Image does not fit the card.' }
    Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.ComponentModel;
using System.Security.Cryptography;
using Microsoft.Win32.SafeHandles;
public static class StrehlCardWriter {
  [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
  static extern SafeFileHandle CreateFileW(string name,uint access,uint share,IntPtr security,uint creation,uint flags,IntPtr template);
  [DllImport("kernel32.dll", SetLastError=true)]
  static extern bool DeviceIoControl(SafeFileHandle file,uint code,IntPtr input,uint inputLength,IntPtr output,uint outputLength,out uint returned,IntPtr overlapped);
  static SafeFileHandle Open(string path,uint access) {
    var handle=CreateFileW(path,access,3,IntPtr.Zero,3,0x80000000,IntPtr.Zero);
    if(handle.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error(),"Open "+path);
    return handle;
  }
  public static string Write(string image,int disk,string backup,string progress) {
    using(var volume=Open(@"\\.\F:",0xC0000000)) {
      uint ignored;
      if(!DeviceIoControl(volume,0x00090018,IntPtr.Zero,0,IntPtr.Zero,0,out ignored,IntPtr.Zero)) throw new Win32Exception(Marshal.GetLastWin32Error(),"Close any Explorer window using F:; card lock failed");
      if(!DeviceIoControl(volume,0x00090020,IntPtr.Zero,0,IntPtr.Zero,0,out ignored,IntPtr.Zero)) throw new Win32Exception(Marshal.GetLastWin32Error(),"Card dismount failed");
      using(var handle=Open(@"\\.\PhysicalDrive"+disk,0xC0000000))
      using(var device=new FileStream(handle,FileAccess.ReadWrite,4*1024*1024,false))
      using(var source=new FileStream(image,FileMode.Open,FileAccess.Read,FileShare.Read,4*1024*1024)) {
        byte[] buffer=new byte[4*1024*1024];
        int prior=device.Read(buffer,0,2*1024*1024);
        using(var old=new FileStream(backup,FileMode.CreateNew,FileAccess.Write)){old.Write(buffer,0,prior);old.Flush(true);}
        device.Position=0;long done=0;int count;
        while((count=source.Read(buffer,0,buffer.Length))>0) {
          device.Write(buffer,0,count);done+=count;
          File.WriteAllText(progress,"Writing "+done+" / "+source.Length+" bytes");
        }
        device.Flush(true);device.Position=0;done=0;
        using(var sha=SHA256.Create()) {
          while(done<source.Length) {
            int needed=(int)Math.Min(buffer.Length,source.Length-done);
            count=device.Read(buffer,0,needed);
            if(count==0)throw new IOException("Card ended during verification");
            sha.TransformBlock(buffer,0,count,null,0);done+=count;
            File.WriteAllText(progress,"Verifying "+done+" / "+source.Length+" bytes");
          }
          sha.TransformFinalBlock(new byte[0],0,0);
          return BitConverter.ToString(sha.Hash).Replace("-","").ToLowerInvariant();
        }
      }
    }
  }
}
'@
    $directory = Split-Path -Parent $Manifest
    $readback = [StrehlCardWriter]::Write($imagePath, $disk.Number, (Join-Path $directory 'card-before-first2MiB.bin'), (Join-Path $directory 'card-write-progress.txt'))
    if ($readback -ne $m.imageSha256) { throw 'Card readback checksum differs from the prepared image.' }
    $ruleName = 'StrehlCapturePiLocalReceiver'
    if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name $ruleName -DisplayName 'Strehl Pi RAW receiver - home LAN only' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8789 -RemoteAddress '10.0.0.0/24' -Profile Any -Program $m.receiverExecutable | Out-Null
    }
    [ordered]@{status='verified';completedUtc=[DateTime]::UtcNow.ToString('o');diskNumber=$disk.Number;diskUniqueId=$disk.UniqueId;bytes=$imageInfo.Length;imageSha256=$m.imageSha256;readbackSha256=$readback;firewallRule=$ruleName} | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding utf8
} catch {
    [ordered]@{status='failed';error=$_.Exception.Message;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding utf8
    exit 1
}
