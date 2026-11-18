"""Run one strehl command and record a 100 ms utilisation timeline.

  python trace.py --exe X.exe --tag name [--env A=1 --env B=2] -- stack DIR --demosaic --out o.tif

Writes <tag>.log (stderr, each line prefixed with seconds since start),
<tag>.csv (the timeline), <tag>.gpu.csv (nvidia-smi at 100 ms) and appends one
summary line to runs.txt. Nothing here touches the capture folder.

Columns of the timeline: t, process user CPU s, process kernel CPU s, process
read bytes, process read ops, private bytes, working set, threads, host CPU %
(all logical processors), busy logical processors (>50 %), available bytes,
standby bytes, disk read bytes of the capture's physical drive.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import threading
import time

import psutil
import win32pdh

# Outputs go to an ignored folder, never beside these tracked scripts.
HERE = os.environ.get('STREHL_PERF_OUT') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'outputs', 'a7cr-perf-2')
os.makedirs(HERE, exist_ok=True)


def pdh_counters(paths):
    query = win32pdh.OpenQuery()
    handles = []
    for p in paths:
        try:
            handles.append(win32pdh.AddEnglishCounter(query, p))
        except Exception:
            handles.append(None)
    win32pdh.CollectQueryData(query)

    def read():
        win32pdh.CollectQueryData(query)
        out = []
        for h in handles:
            if h is None:
                out.append(-1.0)
                continue
            try:
                out.append(win32pdh.GetFormattedCounterValue(h, win32pdh.PDH_FMT_DOUBLE)[1])
            except Exception:
                out.append(-1.0)
        return out

    return read


def thread_name(tid, cache={}):
    """The description Rust's std gives a named thread (SetThreadDescription)."""
    if tid in cache:
        return cache[tid]
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL('kernel32', use_last_error=True)
    k32.OpenThread.restype = wintypes.HANDLE
    k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.GetThreadDescription.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
    k32.LocalFree.argtypes = [ctypes.c_void_p]
    name = ''
    h = k32.OpenThread(0x0800, False, tid)
    if h:
        out = ctypes.c_wchar_p()
        if k32.GetThreadDescription(h, ctypes.byref(out)) >= 0 and out.value:
            name = out.value
        k32.CloseHandle(h)
    if name:
        cache[tid] = name
    return name


def thread_sampler(p, t0, stop, sink, interval=0.5):
    while not stop.is_set():
        t = time.perf_counter() - t0
        try:
            for th in p.threads():
                sink.append((t, th.id, thread_name(th.id), th.user_time, th.system_time))
        except Exception:
            return
        stop.wait(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--threads', action='store_true', help='also sample per-thread CPU by thread name')
    ap.add_argument('--exe', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--env', action='append', default=[])
    ap.add_argument('--disk', default='PhysicalDrive1')
    ap.add_argument('--out', default=None, help='output file to hash')
    ap.add_argument('--interval', type=float, default=0.1)
    ap.add_argument('rest', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    args = [x for x in a.rest if x != '--'] if a.rest and a.rest[0] == '--' else a.rest
    if args and args[0] == '--':
        args = args[1:]
    env = dict(os.environ)
    for kv in a.env:
        k, v = kv.split('=', 1)
        env[k] = v
    base = os.path.join(HERE, a.tag)
    standby = pdh_counters([
        r'\Memory\Standby Cache Normal Priority Bytes',
        r'\Memory\Standby Cache Reserve Bytes',
        r'\Memory\Standby Cache Core Bytes',
        r'\Memory\Modified Page List Bytes',
    ])
    psutil.cpu_percent(percpu=True)
    time.sleep(1.0)
    before = psutil.cpu_percent(percpu=True)
    host_before = sum(before) / len(before)
    gpu_log = open(base + '.gpu.csv', 'w')
    gpu = subprocess.Popen(
        ['nvidia-smi', '--query-gpu=timestamp,utilization.gpu,utilization.memory,memory.used,power.draw',
         '--format=csv,noheader,nounits', '-lms', '100'], stdout=gpu_log, stderr=subprocess.DEVNULL)
    time.sleep(0.3)
    t0 = time.perf_counter()
    wall0 = time.time()
    proc = subprocess.Popen([a.exe] + args, env=env, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    lines = []

    def pump(stream, sink, stamp):
        for raw in iter(stream.readline, b''):
            t = time.perf_counter() - t0
            text = raw.decode('utf-8', 'replace').rstrip('\r\n')
            sink.append((t, text) if stamp else text)

    out_lines = []
    th = threading.Thread(target=pump, args=(proc.stderr, lines, True), daemon=True)
    th2 = threading.Thread(target=pump, args=(proc.stdout, out_lines, False), daemon=True)
    th.start()
    th2.start()
    p = psutil.Process(proc.pid)
    tsink = []
    tstop = threading.Event()
    if a.threads:
        threading.Thread(target=thread_sampler, args=(psutil.Process(proc.pid), t0, tstop, tsink), daemon=True).start()
    rows = []
    peak_priv = 0
    last = None
    disk0 = psutil.disk_io_counters(perdisk=True).get(a.disk)
    while proc.poll() is None:
        t = time.perf_counter() - t0
        try:
            with p.oneshot():
                ct = p.cpu_times()
                io = p.io_counters()
                mi = p.memory_info()
                nt = p.num_threads()
        except Exception:
            break
        per = psutil.cpu_percent(percpu=True)
        vm = psutil.virtual_memory()
        sb = standby()
        d = psutil.disk_io_counters(perdisk=True).get(a.disk)
        peak_priv = max(peak_priv, mi.private)
        rows.append((t, ct.user, ct.system, io.read_bytes, io.read_count, mi.private, mi.rss, nt,
                     sum(per) / len(per), sum(1 for x in per if x > 50.0), vm.available,
                     sb[0] + sb[1] + sb[2], (d.read_bytes - disk0.read_bytes) if d and disk0 else -1,
                     ' '.join('%d' % x for x in per)))
        last = (ct, io)
        nxt = t0 + (len(rows)) * a.interval
        delay = nxt - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
    proc.wait()
    wall = time.perf_counter() - t0
    th.join(timeout=5)
    th2.join(timeout=5)
    gpu.terminate()
    gpu_log.close()
    tstop.set()
    if a.threads:
        with open(base + '.threads.csv', 'w', encoding='utf-8') as f:
            f.write('t,tid,name,user_s,kernel_s\n')
            for r in tsink:
                f.write('%.2f,%d,%s,%.3f,%.3f\n' % r)
    with open(base + '.log', 'w', encoding='utf-8') as f:
        for t, text in lines:
            f.write('%8.2f | %s\n' % (t, text))
    with open(base + '.stdout', 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines))
    with open(base + '.csv', 'w') as f:
        f.write('t,user_s,kernel_s,read_bytes,read_ops,private,ws,threads,host_cpu_pct,busy_lps,available,standby,disk_read,per_cpu\n')
        for r in rows:
            f.write(','.join(str(x) if not isinstance(x, float) else '%.3f' % x for x in r) + '\n')
    sha = 'NO-OUTPUT'
    if a.out and os.path.exists(a.out):
        h = hashlib.sha256()
        with open(a.out, 'rb') as f:
            for block in iter(lambda: f.read(1 << 24), b''):
                h.update(block)
        sha = h.hexdigest().upper()
    user = last[0].user if last else 0.0
    kern = last[0].system if last else 0.0
    rd = last[1].read_bytes if last else 0
    summary = ('wall_s=%.1f user_s=%.1f kernel_s=%.1f avg_cores=%.1f read_GB=%.2f peak_private_GB=%.2f '
               'host_cpu_before_pct=%.0f exit=%d sha=%s' % (
                   wall, user, kern, (user + kern) / wall, rd / 2**30, peak_priv / 2**30, host_before,
                   proc.returncode, sha))
    stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(wall0))
    with open(os.path.join(HERE, 'runs.txt'), 'a', encoding='utf-8') as f:
        f.write('%s %s [%s] env=%s args=%s : %s\n' % (stamp, a.tag, a.exe, ';'.join(a.env), ' '.join(args), summary))
    print(a.tag, ':', summary)


if __name__ == '__main__':
    main()
