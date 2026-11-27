"""Delete the test runs the rig series made, and nothing else.

A folder is deleted only if it is named in a series' record.json, lies in the receiver's folder,
its manifest says `capture_kind: test`, it started after the series began, and it holds at most
four RAWs. Prints what it would do; `--delete` does it.

  python clean-test-runs.py <series folder> [<series folder> ...] [--delete]
"""
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('D:/StrehlCaptures').resolve()
args = [a for a in sys.argv[1:] if a != '--delete']
delete = '--delete' in sys.argv
total = freed = 0
for series in args:
    rec = json.loads((pathlib.Path(series) / 'record.json').read_text())
    began = min([p['base']['started_unix'] for p in rec.get('proofs', [])] + [s['started_unix'] for s in rec.get('survey', [])]) - 5
    folders = [p[k]['folder'] for p in rec.get('proofs', []) for k in ('base', 'highlight')] + [s['folder'] for s in rec.get('survey', [])]
    for f in folders:
        d = pathlib.Path(f).resolve()
        if not d.exists():
            continue
        m = json.loads((d / 'manifest.json').read_text())
        raws = [x for x in d.iterdir() if x.name.endswith('.straw')]
        ok = (d.parent == ROOT and d.name.startswith('stack-') and m.get('capture_kind') == 'test'
              and m.get('started_unix_ms', 0) / 1000 >= began and len(raws) <= 4)
        size = sum(x.stat().st_size for x in d.iterdir())
        if not ok:
            print('KEPT (does not look like one of this series\' test runs):', d)
            continue
        total += 1
        freed += size
        if delete:
            shutil.rmtree(d)
print('%s %d test runs, %.1f GB' % ('deleted' if delete else 'would delete', total, freed / 1e9))
