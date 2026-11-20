"""Fetch the RAWs a lab script stashed on the Pi (/home/strehl/lab/raw) into a local scratch
folder and delete them there.   raw-fetch.py <local folder>"""
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import HOST, OPTIONS, remote  # noqa: E402

out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
t0 = time.time()
subprocess.run(['scp', '-q', '-r', *OPTIONS, '-o', 'HostKeyAlias=10.0.0.187', 'strehl@' + HOST + ':/home/strehl/lab/raw/.', str(out)], check=True)
files = sorted(out.glob('*.ARW'))
size = sum(f.stat().st_size for f in files)
print('%d RAWs, %.1f GB in %.0f s (%.0f MB/s)' % (len(files), size / 1e9, time.time() - t0, size / 1e6 / (time.time() - t0)))
print(remote('import shutil\nshutil.rmtree("/home/strehl/lab/raw", ignore_errors=True)\nprint("remote RAWs removed")'))
