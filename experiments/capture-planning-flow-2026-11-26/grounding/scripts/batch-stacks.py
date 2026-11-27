"""Extract and measure the other stacks used to check that nothing here is fitted to one subject.

For each run: extract.py (member 1 of each plane), curves.py, and the engine's own `strehl subject`
(13 planes) for an outline, since these captures carry none. Capture folders are read only.

  python batch-stacks.py <scratch root> <run> [<run> ...]
"""
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
CLI = pathlib.Path(os.environ['LOCALAPPDATA']) / 'Programs/Strehl/strehl-cli.exe'
CAPTURES = pathlib.Path('D:/StrehlCaptures')
root = pathlib.Path(sys.argv[1])
for name in sys.argv[2:]:
    run = CAPTURES / name
    out = root / name
    out.mkdir(parents=True, exist_ok=True)
    t = time.time()
    if not (out / 'curves' / 'focus.npy').exists():
        subprocess.run([sys.executable, str(HERE / 'extract.py'), str(run), str(out / 'planes'), '10'], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, str(HERE / 'curves.py'), str(out / 'planes'), str(out / 'curves'), '10'], check=True, stdout=subprocess.DEVNULL)
    if not (out / 'subject.json').exists():
        env = dict(os.environ, STREHL_CACHE_DIR=str(out / 'cache'))
        r = subprocess.run([str(CLI), 'subject', str(run), '--out', str(out / 'subject.json'), '--mask-png', str(out / 'subject.png')],
                           capture_output=True, text=True, env=env)
        (out / 'subject.txt').write_text(r.stdout + r.stderr)
    print(name, 'done in %.0f s' % (time.time() - t), flush=True)
