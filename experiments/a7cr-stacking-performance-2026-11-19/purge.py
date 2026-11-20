"""Drop a folder's files from the Windows file cache (read-only access).

Opening a file with FILE_FLAG_NO_BUFFERING makes NTFS drop its cached pages
(checked against the drive's read counter in io-bench.py, 2026-11-18).
"""
import ctypes
import os
import sys
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.CreateFileW.restype = wintypes.HANDLE
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                            wintypes.DWORD, wintypes.HANDLE]
k32.CloseHandle.argtypes = [wintypes.HANDLE]
n = 0
for name in os.listdir(sys.argv[1]):
    h = k32.CreateFileW(os.path.join(sys.argv[1], name), 0x80000000, 1, None, 3, 0x20000000, None)
    if h and h != ctypes.c_void_p(-1).value:
        k32.CloseHandle(h)
        n += 1
print('purged', n, 'files')
