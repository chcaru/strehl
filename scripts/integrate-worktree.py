"""Bring a helper's uncommitted worktree into this one: every file under the
given folders that differs from the helper's base commit is copied (new) or
three-way merged (`git merge-file`: ours = this worktree, base = the commit,
theirs = the helper's file). Line endings are compared and merged as LF and
written back as this worktree's file had them. Prints what it did and every
conflict; exits 1 if any.

  python scripts/integrate-worktree.py <helper worktree> <base commit> [folder ...]

Folders default to crates, scripts and experiments. `target` folders are
skipped.
"""
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path.cwd()
src = pathlib.Path(sys.argv[1])
base = sys.argv[2]
folders = sys.argv[3:] or ['crates', 'scripts', 'experiments', 'docs', 'third-party']


def base_blob(rel):
    r = subprocess.run(['git', 'show', f'{base}:{rel}'], cwd=HERE, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def norm(b):
    return b.replace(b'\r\n', b'\n')


changed, conflicts = [], []
# Files the helper did not touch keep the worktree's checkout time: only
# later ones are compared (two minutes past the checkout's own files).
checkout = (src / 'Cargo.toml').stat().st_mtime
for folder in folders:
    root = src / folder
    if not root.exists():
        continue
    for path in root.rglob('*'):
        if not path.is_file() or 'target' in path.relative_to(src).parts or '__pycache__' in path.parts:
            continue
        if path.stat().st_mtime < checkout + 120:
            continue
        rel = path.relative_to(src).as_posix()
        theirs = path.read_bytes()
        b = base_blob(rel)
        if b is not None and norm(b) == norm(theirs):
            continue
        ours_path = HERE / rel
        ours = ours_path.read_bytes() if ours_path.exists() else None
        crlf = ours is not None and b'\r\n' in ours
        if b is None:
            if ours is None:
                ours_path.parent.mkdir(parents=True, exist_ok=True)
                ours_path.write_bytes(theirs)
                changed.append(('new', rel))
            elif norm(ours) == norm(theirs):
                continue
            else:
                conflicts.append(('both added, different', rel))
            continue
        if ours is None:
            conflicts.append(('deleted here, changed there', rel))
            continue
        if norm(ours) == norm(theirs):
            continue
        with tempfile.TemporaryDirectory() as t:
            t = pathlib.Path(t)
            (t / 'ours').write_bytes(norm(ours))
            (t / 'base').write_bytes(norm(b))
            (t / 'theirs').write_bytes(norm(theirs))
            r = subprocess.run(['git', 'merge-file', '-p', str(t / 'ours'), str(t / 'base'), str(t / 'theirs')],
                               capture_output=True)
        merged = r.stdout
        if crlf:
            merged = merged.replace(b'\n', b'\r\n')
        ours_path.write_bytes(merged)
        if r.returncode != 0:
            conflicts.append((f'{r.returncode} conflict(s)', rel))
        else:
            changed.append(('merged', rel))
for kind, rel in changed:
    print(kind, rel)
for kind, rel in conflicts:
    print('CONFLICT', kind, rel)
print(len(changed), 'files,', len(conflicts), 'conflicts')
sys.exit(1 if conflicts else 0)
