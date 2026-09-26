"""Root-only bounded execution using the existing Windows job helper."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def ref(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == '--':
        command = command[1:]
    target = Path(command[0]).resolve()
    assert target.parent == HERE and target.name in ('model.py', 'stage.py', 'fit.py', 'independent-controls.py')
    out = args.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir(exist_ok=False)
    files = sorted(p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py', '.md'))
    sources = [ref(path) for path in files]
    (out/'bindings.json').write_text(json.dumps(sources, indent=2)+'\n')
    path = ROOT/'experiments/band-source-agreement/run.py'
    spec = importlib.util.spec_from_file_location('focus_front_existing_bounds', path)
    band = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = band
    spec.loader.exec_module(band)
    limits = dict(wall=120, cpu=600, gib=4) if target.name == 'stage.py' else dict(wall=180, cpu=900, gib=4)
    band.job([sys.executable, '-I', '-B', '-X', 'faulthandler', *command],
             dict(OMP_NUM_THREADS='8', MKL_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8',
                  PYTHONHASHSEED='0'), out, **limits)
    assert sources == [ref(Path(row['path'])) for row in sources], 'Bound source changed during job.'
    (out/'completed.json').write_text(json.dumps(dict(process_completed=True,
        sources_unchanged=True, photographic_qualification=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
