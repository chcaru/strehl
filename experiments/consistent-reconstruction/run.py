"""Bounded generated-only test of the actual fused-coefficient reconstruction."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'consistent_reconstruction_existing_bounds', ROOT/'experiments/band-source-agreement/run.py')
band = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = band
spec.loader.exec_module(band)
g, c = band.g, band.c
read, save, ref = g.read, c.save, c.ref
FILTER = 'merge_cmd::consistent_reconstruction::independent_controls::'
OUTPUT_ENV = 'STREHL_CONSISTENT_RECONSTRUCTION_OUT'
REQUIRED = ('run.py', 'operator.rs', 'implementation.rs', 'design.md',
            'integration-plan.md', 'independent-controls.rs', 'independent-fixtures.rs', 'independent-plan.md')
# Independent names and the scientific screen schema are frozen before build.
EXPECTED_TEST_NAMES = ('independent_adjoint_dense_controls', 'independent_solver_controls',
                       'independent_refusal_controls', 'independent_quality_screen')
EXPECTED_CASES = 12
SCOPE = ('Generated native consumer only. Numerical consistency is not photographic quality, '
         'and a capped unconverged iterate cannot qualify a full render.')


def required_paths():
    assert EXPECTED_TEST_NAMES and EXPECTED_CASES > 0, 'Independent screen contract is not frozen.'
    paths = {HERE/name for name in REQUIRED}
    paths.update((Path(band.__file__).resolve(), Path(g.__file__).resolve(),
                  Path(c.__file__).resolve(), ROOT/'crates/strehl-cli/src/merge_cmd.rs',
                  ROOT/'crates/strehl-core/src/pyramid.rs',
                  ROOT/'experiments/m193c-output-grid/bounded-process.py',
                  ROOT/'experiments/m12-scorecard/m12-harness.py'))
    for name in ('donor-consistency', 'real-source-contributions', 'rb-own-guide',
                 'cross-scale-source-prior', 'shared-source-field', 'band-source-agreement'):
        paths.update((ROOT/'experiments'/name).glob('*.rs'))
    assert all(path.is_file() for path in paths), 'Freeze every implementation/control file before build.'
    control = (HERE/'independent-controls.rs').read_text(encoding='utf-8')
    assert set(re.findall(r'#\[test\]\s*fn\s+(\w+)', control)) == set(EXPECTED_TEST_NAMES)
    assert '/../../experiments/consistent-reconstruction/implementation.rs' in (
        ROOT/'crates/strehl-cli/src/merge_cmd.rs').read_text(encoding='utf-8')
    return paths


def build(out):
    out.mkdir(exist_ok=False)
    (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch()
    paths = {Path(row['path']) for row in g.bindings()}
    paths.update(required_paths())
    sources = [ref(path.resolve()) for path in sorted(paths)]
    save(out/'sources.json', sources)
    command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--no-run', '--release',
               '--features', g.FEATURES, '--jobs', '2', '--target-dir', str(ROOT/'target/native-pyramid-profile'),
               '--message-format=json-render-diagnostics', '--locked', '--offline']
    band.job(command, dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out,
             wall=600, cpu=2400, gib=16)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log
    artifacts = []
    for line in log.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if (row.get('reason') == 'compiler-artifact' and row.get('executable')
                and row.get('target', {}).get('name') == 'strehl' and row['profile']['test']):
            artifacts.append(row['executable'])
    assert len(artifacts) == 1
    exe = out/'cli-tests.exe'
    shutil.copyfile(artifacts[0], exe)
    g.unchanged(sources)
    save(out/'executables.json', {'cli-tests': ref(exe)})


def controls(out, build_dir):
    sources = read(build_dir/'sources.json')
    g.unchanged(sources)
    recorded = {row['path']: row for row in sources}
    assert len(recorded) == len(sources)
    for path in required_paths():
        current = ref(path.resolve())
        assert recorded.get(current['path']) == current
    exe = (build_dir/'cli-tests.exe').resolve()
    assert ref(exe) == read(build_dir/'executables.json')['cli-tests']
    built = read(build_dir/'process.json')
    assert built['exit_code'] == 0 and built['error'] is None
    assert built['terminal_job_accounting'] and not built['cleanup_errors']
    assert 'Compiling strehl-cli' in (build_dir/'process.log').read_text(encoding='utf-8', errors='replace')
    out.mkdir(exist_ok=False)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe), runner=ref(Path(__file__).resolve())))
    fields = band.fields()
    fields.update(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2',
                  STREHL_GPU_GATHER_LOG='off', **{OUTPUT_ENV: str(out/'output')})
    band.job([str(exe), FILTER, '--nocapture', '--test-threads=1'], fields, out,
             wall=240, cpu=900, gib=4)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == [str(len(EXPECTED_TEST_NAMES))]
    assert 'CONSISTENT_RECONSTRUCTION ' in log
    screen_path = out/'output/screen.json'
    screen = read(screen_path)
    assert screen['status'] == 'SCREEN_COMPLETE' and len(screen['cases']) == EXPECTED_CASES
    assert screen['photographic_replay_admitted'] is False
    decision_names = ('numerical_pass', 'preservation_pass', 'contact_positive',
                      'wrong_source_destroyer_exercised', 'candidate_qualified')
    assert screen['mechanical_pass'] is True
    assert all(type(screen[name]) is bool for name in decision_names)
    assert screen['candidate_qualified'] == all(screen[name] for name in decision_names[:-1])
    g.unchanged(sources)
    assert ref(exe) == read(out/'bindings.json')['executable']
    save(out/'completion.json', dict(instrument_completed=True, controls_executed=len(EXPECTED_TEST_NAMES),
        cases_executed=EXPECTED_CASES, sources_unchanged=True, screen=ref(screen_path),
        process=ref(out/'process.json'), photographic_replay_admitted=False,
        root_review_required=True, full_render_available=False, scope=SCOPE,
        **{name: screen[name] for name in decision_names}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('build', 'controls'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    if args.phase == 'build':
        assert args.build is None
        build(out)
    else:
        assert args.build is not None
        controls(out, args.build.resolve())


if __name__ == '__main__':
    main()
