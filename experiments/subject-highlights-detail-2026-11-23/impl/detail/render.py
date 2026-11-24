"""Render A7CR four-shot stacks as the desktop does, outside the corpora (shd-d-detail).

  python render.py <engine exe> <arm> <out root> <capture folder> [...] [-- NAME=value | --flag ...]

As ../render.py (the desktop's arguments and environment from crates/strehl-ui/src/jobs.rs:
`stack <capture> --merge pyramid --srgb --out result.tiff --linear-master master.tiff`,
STREHL_UI_PROGRESS=1, STREHL_GPU_FOLD=auto, STREHL_TEMPORAL_ENERGY=off,
STREHL_PIXEL_SHIFT=remosaic, every other inherited STREHL_ variable removed, a private
STREHL_CACHE_DIR at <out root>/cache shared by the arms), plus: after `--`, NAME=value pairs go
to the environment and tokens starting with `--` are added to the `stack` arguments. A token
`{name}` in a flag is replaced by the capture folder's name (for per-capture subject files).
The capture folders' listings and modification times are checked unchanged after each render.

Writes <out root>/<arm>/<capture name>/{result.tiff, master.tiff, render.log, run.json}.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

args = sys.argv[1:]
extra, flags = {}, []
if '--' in args:
    k = args.index('--')
    for a in args[k + 1:]:
        if a.startswith('--'):
            flags.append(a)
        else:
            name, value = a.split('=', 1)
            extra[name] = value
    args = args[:k]
exe, arm, root = args[0], args[1], pathlib.Path(args[2])
captures = args[3:]


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for block in iter(lambda: f.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


env = {k: v for k, v in os.environ.items() if not k.upper().startswith('STREHL_')}
env.update(STREHL_UI_PROGRESS='1', STREHL_GPU_FOLD='auto', STREHL_TEMPORAL_ENERGY='off',
           STREHL_PIXEL_SHIFT='remosaic', STREHL_CACHE_DIR=str(root / 'cache'))
for capture in captures:
    name = pathlib.Path(capture).name
    out = root / arm / name
    out.mkdir(parents=True, exist_ok=True)
    e = dict(env)
    e.update(extra)
    before = sorted((q.name, q.stat().st_size, q.stat().st_mtime_ns) for q in pathlib.Path(capture).iterdir())
    for f in ('result.tiff', 'master.tiff'):
        if (out / f).exists():
            (out / f).unlink()
    cmd = [exe, 'stack', capture, '--merge', 'pyramid', '--srgb', '--out', str(out / 'result.tiff'),
           '--linear-master', str(out / 'master.tiff')] + [f.replace('{name}', name) for f in flags]
    started = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=e, encoding='utf-8', errors='replace')
    seconds = time.time() - started
    (out / 'render.log').write_text(p.stdout + p.stderr, encoding='utf-8')
    after = sorted((q.name, q.stat().st_size, q.stat().st_mtime_ns) for q in pathlib.Path(capture).iterdir())
    if after != before:
        raise SystemExit('the capture folder changed: ' + capture)
    run = {'exe': exe, 'exe_sha256': sha(exe), 'arm': arm, 'capture': capture, 'args': cmd[2:],
           'exit': p.returncode, 'seconds': round(seconds, 1), 'extra_env': extra,
           'worker_threads': os.cpu_count()}
    for f in ('result.tiff', 'master.tiff'):
        if (out / f).exists():
            run[f] = sha(out / f)
    (out / 'run.json').write_text(json.dumps(run, indent=1))
    print(arm, name, 'exit', p.returncode, '%.0f s' % seconds, run.get('result.tiff', '-')[:16],
          run.get('master.tiff', '-')[:16], flush=True)
