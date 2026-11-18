"""Read-path experiments on the capture drive (read-only access).

  python io-bench.py DIR

Modes, each over its own slice of files so that no mode reads another's cache:
  unbuf   FILE_FLAG_NO_BUFFERING, whole file per ReadFile, page-aligned buffer
  buf     ordinary buffered ReadFile of the whole file (what std::fs::read does)
  bufseq  the same with FILE_FLAG_SEQUENTIAL_SCAN
  map     map the file, PrefetchVirtualMemory the view, then copy it once
  mapcold map the file and copy it once with no prefetch

Before a buffered or mapped mode the files are opened once with
FILE_FLAG_NO_BUFFERING, which makes NTFS drop their cached pages; the script
checks that claim with the drive's read counter and says so.
"""
import ctypes
import os
import sys
import threading
import time
from ctypes import wintypes

import psutil

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 1
OPEN_EXISTING = 3
NO_BUFFERING = 0x20000000
SEQUENTIAL = 0x08000000
INVALID = ctypes.c_void_p(-1).value
k32.CreateFileW.restype = wintypes.HANDLE
k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                            wintypes.DWORD, wintypes.HANDLE]
k32.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                         ctypes.c_void_p]
k32.VirtualAlloc.restype = ctypes.c_void_p
k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
k32.CreateFileMappingW.restype = wintypes.HANDLE
k32.CreateFileMappingW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                   wintypes.LPCWSTR]
k32.MapViewOfFile.restype = ctypes.c_void_p
k32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
k32.CloseHandle.argtypes = [wintypes.HANDLE]


class Range(ctypes.Structure):
    _fields_ = [('addr', ctypes.c_void_p), ('size', ctypes.c_size_t)]


k32.PrefetchVirtualMemory.argtypes = [wintypes.HANDLE, ctypes.c_size_t, ctypes.POINTER(Range), wintypes.ULONG]
k32.GetCurrentProcess.restype = wintypes.HANDLE
CAP = 80 << 20


def alloc():
    p = k32.VirtualAlloc(None, CAP, 0x3000, 0x04)
    ctypes.memset(p, 1, CAP)
    return p


def open_file(path, flags):
    h = k32.CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, None, OPEN_EXISTING, flags, None)
    if h == INVALID or h is None:
        raise OSError(ctypes.get_last_error(), path)
    return h


def read_whole(path, flags, buf):
    size = os.path.getsize(path)
    want = (size + 4095) & ~4095
    h = open_file(path, flags)
    got = wintypes.DWORD(0)
    total = 0
    while total < size:
        ok = k32.ReadFile(h, buf + total, min(want - total, 1 << 30), ctypes.byref(got), None)
        if not ok or got.value == 0:
            break
        total += got.value
    k32.CloseHandle(h)
    return total


def read_mapped(path, prefetch, buf):
    size = os.path.getsize(path)
    h = open_file(path, 0)
    m = k32.CreateFileMappingW(h, None, 0x02, 0, 0, None)
    v = k32.MapViewOfFile(m, 0x04, 0, 0, 0)
    if prefetch:
        r = Range(v, size)
        k32.PrefetchVirtualMemory(k32.GetCurrentProcess(), 1, ctypes.byref(r), 0)
    ctypes.memmove(buf, v, size)
    k32.UnmapViewOfFile(v)
    k32.CloseHandle(m)
    k32.CloseHandle(h)
    return size


def purge(paths):
    for p in paths:
        k32.CloseHandle(open_file(p, NO_BUFFERING))


def run(mode, paths, threads):
    it = iter(paths)
    lock = threading.Lock()
    done = [0]

    def work():
        buf = alloc()
        while True:
            with lock:
                p = next(it, None)
            if p is None:
                return
            if mode == 'unbuf':
                n = read_whole(p, NO_BUFFERING, buf)
            elif mode == 'buf':
                n = read_whole(p, 0, buf)
            elif mode == 'bufseq':
                n = read_whole(p, SEQUENTIAL, buf)
            elif mode == 'map':
                n = read_mapped(p, True, buf)
            else:
                n = read_mapped(p, False, buf)
            with lock:
                done[0] += n

    me = psutil.Process()
    d0 = psutil.disk_io_counters(perdisk=True)['PhysicalDrive1'].read_bytes
    c0 = me.cpu_times()
    t0 = time.perf_counter()
    ts = [threading.Thread(target=work) for _ in range(threads)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    dt = time.perf_counter() - t0
    c1 = me.cpu_times()
    d1 = psutil.disk_io_counters(perdisk=True)['PhysicalDrive1'].read_bytes
    return done[0], dt, d1 - d0, (c1.user - c0.user), (c1.system - c0.system)


def main():
    d = sys.argv[1]
    files = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.straw'))
    n = 48
    cursor = [40]

    def take():
        s = files[cursor[0]:cursor[0] + n]
        cursor[0] += n
        if cursor[0] + n > len(files):
            cursor[0] = 40
        return s

    print('%-8s %-5s %3s %7s %7s %8s %7s %7s' % ('mode', 'cache', 'thr', 'GB', 'GB/s', 'diskGB', 'user_s', 'kern_s'))
    plan = [('unbuf', 1), ('unbuf', 2), ('unbuf', 4), ('unbuf', 8), ('unbuf', 16),
            ('buf', 1), ('buf', 4), ('buf', 8), ('buf', 16),
            ('bufseq', 1), ('bufseq', 4), ('bufseq', 16),
            ('map', 1), ('map', 4), ('map', 8), ('map', 16),
            ('mapcold', 1), ('mapcold', 8)]
    for mode, thr in plan:
        s = take()
        purge(s)
        b, dt, disk, u, k = run(mode, s, thr)
        print('%-8s %-5s %3d %7.2f %7.2f %8.2f %7.2f %7.2f' % (mode, 'cold', thr, b / 2**30, b / 2**30 / dt, disk / 2**30, u, k),
              flush=True)
        if mode != 'unbuf':
            b, dt, disk, u, k = run(mode, s, thr)
            print('%-8s %-5s %3d %7.2f %7.2f %8.2f %7.2f %7.2f' % (mode, 'warm', thr, b / 2**30, b / 2**30 / dt, disk / 2**30, u, k),
                  flush=True)


if __name__ == '__main__':
    main()
