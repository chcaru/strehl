"""Fetch the live-view frames a lab script left on the Pi into a local folder and delete them
there.   lv-fetch.py <local folder>"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import HOST, OPTIONS, remote  # noqa: E402

out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
subprocess.run(['scp', '-q', '-r', *OPTIONS, '-o', 'HostKeyAlias=10.0.0.187', 'strehl@' + HOST + ':/home/strehl/lab/lv/.', str(out)], check=True)
print(remote('import shutil\nshutil.rmtree("/home/strehl/lab/lv", ignore_errors=True)\nprint("remote frames removed")'))
print(sum(1 for _ in out.rglob('*.jpg')), 'frames in', out)
