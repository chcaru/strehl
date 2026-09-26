"""Root-owned bounded build and generated colour-evidence controls only."""
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
    'chromatic_existing_band_bounds', ROOT/'experiments/band-source-agreement/run.py')
band = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = band
spec.loader.exec_module(band)
g, c = band.g, band.c
read, save, ref = g.read, c.save, c.ref

FILTER = 'merge_cmd::chromatic_source_evidence::independent_controls::'
OUTPUT_ENV = 'STREHL_CHROMATIC_SOURCE_EVIDENCE_OUT'
REQUIRED = ('run.py', 'operator.rs', 'implementation.rs', 'design.md',
            'integration-plan.md', 'independent-controls.rs', 'independent-fixtures.rs', 'independent-plan.md')
# Independent author contract: projection, paired covariance/floor, admission
# union, and the fixed eight-case image screen. Never accept zero/missing tests.
EXPECTED_TEST_NAMES = ('independent_projection_controls', 'independent_paired_floor_controls',
                       'independent_union_controls', 'independent_quality_screen')
EXPECTED_TESTS = len(EXPECTED_TEST_NAMES)
EXPECTED_CASES = 8
SCOPE = ('Generated RAW colour-evidence controls only. Successful execution is not '
         'photographic admission, a default change or a speed/quality claim.')


def required_paths():
    paths = {HERE/name for name in REQUIRED}
    paths.update((Path(band.__file__).resolve(), Path(g.__file__).resolve(),
                  Path(c.__file__).resolve(), ROOT/'crates/strehl-cli/src/merge_cmd.rs',
                  ROOT/'crates/strehl-core/src/pyramid.rs',
                  ROOT/'experiments/m193c-output-grid/bounded-process.py',
                  ROOT/'experiments/m12-scorecard/m12-harness.py'))
    # Actual reused Rust includes; do not add unrelated experiment documents,
    # output receipts or a second broad recursive experiment inventory.
    for name in ('phase-packed-rgb', 'rb-own-guide', 'boundary-cfa-wavelet',
                 'native-correction-variance', 'cross-scale-source-prior', 'shared-source-field'):
        paths.update((ROOT/'experiments'/name).glob('*.rs'))
    assert all(path.is_file() for path in paths), 'Freeze all required source/control files first.'
    controls_source = (HERE/'independent-controls.rs').read_text(encoding='utf-8')
    assert set(re.findall(r'#\[test\]\s*fn\s+(\w+)', controls_source)) == set(EXPECTED_TEST_NAMES)
    assert '/../../experiments/chromatic-source-evidence/implementation.rs' in (
        ROOT/'crates/strehl-cli/src/merge_cmd.rs').read_text(encoding='utf-8'), 'Root CLI hook is absent.'
    assert '/../../experiments/chromatic-source-evidence/independent-controls.rs' in (
        HERE/'implementation.rs').read_text(encoding='utf-8'), 'Independent child module is absent.'
    return paths


def bindings():
    # Keep the established source-bound inventory, including its existing
    # out-of-tree Rust scan. Extend it only with this lane and actual helpers.
    paths = {Path(row['path']) for row in g.bindings()}
    paths.update(required_paths())
    return [ref(path.resolve()) for path in sorted(paths)]


def build(out):
    out.mkdir(exist_ok=False)
    # Only the CLI include owner is new; no core hook or arithmetic is edited.
    (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch()
    sources = bindings()
    save(out/'sources.json', sources)
    command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--no-run', '--release',
               '--features', g.FEATURES, '--jobs', '2',
               '--target-dir', str(ROOT/'target/native-pyramid-profile'),
               '--message-format=json-render-diagnostics', '--locked', '--offline']
    band.job(command, dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out,
             wall=600, cpu=2400, gib=16)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log, 'Fresh CLI compile evidence is required.'
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


def shared_build(path):
    """Accept a retained shared build only when this lane was bound BEFORE it."""
    sources = read(path/'sources.json')
    g.unchanged(sources)
    recorded = {row['path']: row for row in sources}
    assert len(recorded) == len(sources), 'Duplicate source binding.'
    # Do not rescan g.bindings here: a newly added unrelated unbound experiment
    # cannot invalidate a retained executable. Its existing bound files must
    # still be exact, and every actual lane/helper input must already be bound.
    for source in required_paths():
        current = ref(source.resolve())
        assert recorded.get(current['path']) == current, 'Required input was not bound before this build.'
    exe = (path/'cli-tests.exe').resolve()
    assert ref(exe) == read(path/'executables.json')['cli-tests']
    process = read(path/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    log = (path/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log, 'Fresh CLI compile evidence is required.'
    return exe, sources


def controls(out, exe, sources):
    out.mkdir(exist_ok=False)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe), runner=ref(Path(__file__).resolve())))
    fields = band.fields()
    fields.update(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2',
                  STREHL_GPU_GATHER_LOG='off', **{OUTPUT_ENV: str(out/'output')})
    band.job([str(exe), FILTER, '--nocapture', '--test-threads=1'], fields, out,
             wall=180, cpu=900, gib=4)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == [str(EXPECTED_TESTS)]
    assert 'CHROMATIC_SOURCE_EVIDENCE ' in log
    screen_path = out/'output/screen.json'
    screen = read(screen_path)
    assert screen['status'] == 'SCREEN_COMPLETE' and len(screen['cases']) == EXPECTED_CASES
    assert screen['mechanical_pass'] is True
    for name in ('quality_pass', 'positive_exercised', 'wrong_source_destroyer_exercised', 'candidate_qualified'):
        assert type(screen[name]) is bool
    assert screen['candidate_qualified'] == (screen['quality_pass'] and screen['positive_exercised']
                                           and screen['wrong_source_destroyer_exercised'])
    assert screen['photographic_replay_admitted'] is False
    g.unchanged(sources)
    assert ref(exe) == read(out/'bindings.json')['executable']
    save(out/'completion.json', dict(instrument_completed=True, controls_executed=EXPECTED_TESTS,
        cases_executed=EXPECTED_CASES, sources_unchanged=True, screen=ref(screen_path),
        process=ref(out/'process.json'), photographic_replay_admitted=False,
        mechanical_pass=True, quality_pass=screen['quality_pass'],
        positive_exercised=screen['positive_exercised'],
        wrong_source_destroyer_exercised=screen['wrong_source_destroyer_exercised'],
        candidate_qualified=screen['candidate_qualified'],
        root_review_required=True, full_render_available=False, scope=SCOPE))


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
        exe, sources = shared_build(args.build.resolve())
        controls(out, exe, sources)


if __name__ == '__main__':
    main()
