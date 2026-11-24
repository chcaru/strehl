"""Render A7CR four-shot stacks as the desktop does, outside the corpora (shd-q-restore).

  python render.py <engine exe> <arm> <out root> <capture folder> [...] [-- NAME=value ...]

Arguments and environment follow crates/strehl-ui/src/jobs.rs (render_command and
configure_render_environment): `stack <capture> --merge pyramid --srgb --out result.tiff
--linear-master master.tiff`, STREHL_UI_PROGRESS=1, STREHL_GPU_FOLD=auto,
STREHL_TEMPORAL_ENERGY=off, STREHL_PIXEL_SHIFT=remosaic, every other inherited STREHL_ variable
removed. Isolation: a private STREHL_CACHE_DIR (<out root>/cache, shared by the arms so the
alignment is solved once), where `stack` caches its solved warp map (STREHL_WARPMAP would need a
map made beforehand, and the desktop solves its own); the capture folders' listings and
modification times are checked unchanged after each render. The optical restoration's
spectra are dumped beside the render (STREHL_OPTICAL_RESTORE_DUMP). Extra NAME=value pairs after
`--` are added to the environment.

Writes <out root>/<arm>/<capture name>/{result.tiff, master.tiff, render.log, spectra.json,
run.json}; run.json holds the exit code, seconds and SHA-256 of the outputs.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

args = sys.argv[1:]
extra = {}
if '--' in args:
    k = args.index('--')
    extra = dict(a.split('=', 1) for a in args[k + 1:])
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
    e = dict(env, STREHL_OPTICAL_RESTORE_DUMP=str(out / 'spectra.json'))
    before = sorted((q.name, q.stat().st_size, q.stat().st_mtime_ns) for q in pathlib.Path(capture).iterdir())
    e.update(extra)
    for f in ('result.tiff', 'master.tiff'):
        if (out / f).exists():
            (out / f).unlink()
    started = time.time()
    p = subprocess.run([exe, 'stack', capture, '--merge', 'pyramid', '--srgb', '--out', str(out / 'result.tiff'),
                        '--linear-master', str(out / 'master.tiff')], capture_output=True, text=True, env=e,
                       encoding='utf-8', errors='replace')
    seconds = time.time() - started
    (out / 'render.log').write_text(p.stdout + p.stderr, encoding='utf-8')
    after = sorted((q.name, q.stat().st_size, q.stat().st_mtime_ns) for q in pathlib.Path(capture).iterdir())
    if after != before:
        raise SystemExit('the capture folder changed: ' + capture)
    run = {'exe': exe, 'exe_sha256': sha(exe), 'arm': arm, 'capture': capture, 'exit': p.returncode,
           'seconds': round(seconds, 1), 'extra_env': extra, 'worker_threads': os.cpu_count()}
    for f in ('result.tiff', 'master.tiff'):
        if (out / f).exists():
            run[f] = sha(out / f)
    (out / 'run.json').write_text(json.dumps(run, indent=1))
    print(arm, name, 'exit', p.returncode, '%.0f s' % seconds, run.get('result.tiff', '-')[:16], flush=True)
