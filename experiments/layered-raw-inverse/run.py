"""Root-owned bounded execution of the independently reviewed RAW inverse screen."""
from pathlib import Path
import argparse
import importlib.util
import importlib.metadata
import json
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'layered_bounded_common', ROOT / 'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    required = ['model.py', 'design.md', 'independent-controls.py',
                'independent-plan.md', 'independent-source-review.md', 'run.py']
    paths = [HERE / name for name in required]
    paths += [ROOT / name for name in (
        'experiments/full-context-placement/run.py',
        'experiments/m193c-output-grid/bounded-process.py',
        'experiments/m12-scorecard/m12-harness.py')]
    assert all(p.is_file() for p in paths)
    sources = [c.ref(p) for p in paths]
    out.mkdir()
    c.save(out / 'sources.json', sources)
    c.save(out / 'runtime.json', {
        'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
        'packages': {name: importlib.metadata.version(name) for name in ('torch', 'numpy', 'scipy')}})
    command = [sys.executable, '-I', '-B', '-X', 'faulthandler',
               str(HERE / 'independent-controls.py'), '--out', str(out / 'output')]
    c.job(command, {'OMP_NUM_THREADS': '4', 'MKL_NUM_THREADS': '4',
                    'OPENBLAS_NUM_THREADS': '4', 'PYTHONDONTWRITEBYTECODE': '1'},
          out, wall=900)
    assert all(c.ref(Path(r['path'])) == r for r in sources)
    result = out / 'output/screen.json'
    assert result.is_file()
    screen = json.loads(result.read_text())
    assert screen['status'] == 'SCREEN_COMPLETE' and screen['cases']
    c.save(out / 'completion.json', {
        'instrument_completed': True, 'sources_unchanged': True,
        'case_count': len(screen['cases']),
        'known_optics_utility_pass': screen['known_optics_utility_pass'],
        'real_photo_admission': screen['real_photo_admission'],
        'result': c.ref(result), 'process': c.ref(out / 'process.json'),
        'scope': 'Generated original-CFA reconstruction with supplied optics; '
                 'not a camera calibration or a full-stack photographic result.'})
    print(json.dumps({'completed': True, 'result': c.ref(result)}), flush=True)


if __name__ == '__main__':
    main()
