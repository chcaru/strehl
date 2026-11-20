"""Raw TCP rate from the Pi to this PC over the capture uplink (wlan1, 10.0.0.178), with one,
two and four parallel streams. The Pi listens; the PC connects (no inbound rule needed) and
receives. Also the link's own figures from the Pi (wpa_cli / /proc/net/wireless)."""
import pathlib
import socket
import sys
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import remote  # noqa: E402
sys.path.insert(0, str(ROOT / 'experiments/sony-edup-2026-11-12'))
from remote import ssh  # noqa: E402

HOST = '10.0.0.178'
PORT = 5207
SECONDS = 6

SERVER = r'''
import os, socket, sys, threading, time
port, seconds, streams = %d, %d, %d
block = os.urandom(1 << 20)
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('10.0.0.178', port)); srv.listen(8); srv.settimeout(15)
def serve(c):
    end = time.monotonic() + seconds
    try:
        while time.monotonic() < end:
            c.sendall(block)
    except OSError:
        pass
    c.close()
ts = []
for _ in range(streams):
    c, _a = srv.accept()
    t = threading.Thread(target=serve, args=(c,)); t.start(); ts.append(t)
for t in ts: t.join()
print('served')
'''

LINK = r'''
import subprocess
def sh(*a):
    try:
        r = subprocess.run(list(a), capture_output=True, text=True, timeout=10)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return 'ERR %r' % (e,)
print(open('/proc/net/wireless').read())
for dev in ('wlan1', 'wlan0'):
    print('--', dev)
    print(sh('wpa_cli', '-i', dev, 'signal_poll'))
    out = sh('wpa_cli', '-i', dev, 'status')
    print('\n'.join(l for l in out.splitlines() if l.split('=')[0] in ('freq', 'wifi_generation', 'key_mgmt', 'wpa_state', 'ieee80211ac', 'ieee80211ax')))
print(sh('nmcli', '-t', '-f', 'ACTIVE,CHAN,FREQ,RATE,SIGNAL,BARS,DEVICE', 'dev', 'wifi'))
print(sh('ethtool', '-i', 'wlan1'))
'''


def receive(results, i):
    s = socket.create_connection((HOST, PORT), timeout=10)
    n = 0
    t0 = time.perf_counter()
    while True:
        b = s.recv(1 << 20)
        if not b:
            break
        n += len(b)
    results[i] = (n, time.perf_counter() - t0)


print(ssh(LINK, host=HOST, root=True, timeout=40).stdout)
for streams in (1, 1, 2, 4):
    box = {}
    server = threading.Thread(target=lambda: box.setdefault('r', ssh(SERVER % (PORT, SECONDS, streams), host=HOST, timeout=60)))
    server.start()
    time.sleep(2.5)
    results = [None] * streams
    ts = [threading.Thread(target=receive, args=(results, i)) for i in range(streams)]
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wall = time.perf_counter() - t0
    server.join()
    total = sum(r[0] for r in results)
    print('%d stream(s): %.0f MB in %.2f s = %.1f MB/s (%s)' % (streams, total / 1e6, wall, total / 1e6 / wall,
          ', '.join('%.1f' % (r[0] / 1e6 / r[1]) for r in results)), flush=True)
    time.sleep(1)
