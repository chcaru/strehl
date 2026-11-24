"""Render single test planes with the product's engine, so a stack and one of its planes go
through the same development. Restoration off; private cache.

  python render-planes.py <index.json> <engine exe> <out folder> <position> [series ...]
"""
import json
import os
import pathlib
import subprocess
import sys

rows = json.loads(pathlib.Path(sys.argv[1]).read_text())
exe, out_root, position = sys.argv[2], pathlib.Path(sys.argv[3]), int(sys.argv[4])
series = sys.argv[5:] or ['ladder', 'repeat', 'single-ref']
env = dict(os.environ, STREHL_PIXEL_SHIFT='remosaic', STREHL_OPTICAL_RESTORE='off',
           STREHL_CACHE_DIR=str(out_root.parent.parent / 'cache'))
made = []
for r in rows:
    if r.get('position') != position or r.get('series') not in series or not r.get('folder'):
        continue
    name = pathlib.Path(r['folder']).name
    out = out_root / name
    out.mkdir(parents=True, exist_ok=True)
    if not (out / 'master.tiff').exists():
        p = subprocess.run([exe, 'stack', r['folder'].replace(chr(92), '/'), '--merge', 'pyramid', '--srgb', '--out', str(out / 'result.tiff'),
                            '--linear-master', str(out / 'master.tiff')], capture_output=True, text=True, env=env, encoding='utf-8', errors='replace')
        (out / 'render.log').write_text(p.stdout + p.stderr, encoding='utf-8')
        if p.returncode != 0:
            raise SystemExit('render failed for %s: %s' % (name, p.stderr[-400:]))
    made.append({'series': r['series'], 'seconds': r['seconds'], 'note': r.get('note'), 'name': name, 'started': r.get('started')})
(out_root / 'index.json').write_text(json.dumps(made, indent=1))
print(len(made), 'single-plane renders in', out_root)
