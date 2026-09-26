"""Root execution wrapper for the fixed learned focus-selection pilot."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
    assert command and Path(command[0]).resolve() == (HERE/'pilot.py').resolve()
    assert command[1] != 'fetch', 'Public downloads run separately from model execution.'
    out = args.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir(exist_ok=False)
    sources = [ref(HERE/name) for name in ('pilot.py', 'run.py', 'decision.md',
                                          'readiness.md', 'independent-plan.md')]
    (out/'bindings.json').write_text(json.dumps(sources, indent=2)+'\n')
    band = load('stackmff_existing_bounds', ROOT/'experiments/band-source-agreement/run.py')
    band.job([sys.executable, '-I', '-B', '-X', 'faulthandler', *command],
             dict(OMP_NUM_THREADS='8', MKL_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8',
                  CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='0'),
             out, wall=120, cpu=300, gib=8)
    assert sources == [ref(Path(row['path'])) for row in sources], 'Pilot source changed during execution.'
    (out/'completed.json').write_text(json.dumps(dict(process_completed=True,
        sources_unchanged=True, quality_qualification=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
