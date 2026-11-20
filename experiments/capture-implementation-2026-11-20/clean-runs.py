"""Delete test runs named in files (any stack-NNN-NNN token), only under D:/StrehlCaptures."""
import pathlib
import re
import shutil
import sys

root = pathlib.Path('D:/StrehlCaptures')
names = set()
for f in sys.argv[1:]:
    names.update(re.findall(r'stack-\d{13}-\d+', pathlib.Path(f).read_text(errors='replace')))
gone = 0
for n in sorted(names):
    p = root / n
    # Only today's test runs (2026-11-20, after the owner's last run 1795114440478).
    if p.is_dir() and int(n.split('-')[1]) >= 1795160000000:
        shutil.rmtree(p)
        gone += 1
print('deleted', gone, 'of', len(names), 'named runs')
