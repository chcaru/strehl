"""Root-owned small exact-operator screen. No RAW, photograph or default change."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('intercept_existing_bounds', ROOT/'experiments/band-source-agreement/run.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
read, save, ref = b.read, b.save, b.ref
FILTER = 'chip_focus_intercept::independent_controls::'
TESTS = ('a_flat_and_unchanged_nonquadratic', 'b_moments_and_dense_oracle',
         'c_support_refusal', 'd_contact_depth_and_overshoot')
RECORDS = ('arithmetic', 'support', 'planar', 'adversary')


def bindings():
    paths = set(p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.rs', '.py', '.md', '.toml', '.lock'))
    paths.update(ROOT/'experiments/chip-focus-radiance'/name for name in ('operator.rs', 'independent-controls.rs'))
    paths.update(Path(row['path']) for row in b.bindings() if Path(row['path']).suffix == '.py')
    return [ref(p.resolve()) for p in sorted(paths)]


def build(out):
    out.mkdir(exist_ok=False)
    required = ('operator.rs', 'independent-controls.rs', 'preregistration.md', 'charter.md')
    assert all((HERE/p).is_file() for p in required), 'Freeze author and reviewer files first.'
    lock = out/'lock'
    lock.mkdir()
    b.job(['cargo', 'generate-lockfile', '--manifest-path', str(HERE/'Cargo.toml'), '--offline'],
          dict(CARGO_INCREMENTAL='0'), lock, wall=60, cpu=120, gib=2)
    (HERE/'lib.rs').touch()
    sources = bindings()
    save(out/'sources.json', sources)
    save(out/'revision.json', dict(head=subprocess.check_output(
        ['git', '--no-optional-locks', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()))
    b.job(['cargo', 'test', '--manifest-path', str(HERE/'Cargo.toml'), '--lib', '--no-run',
           '--release', '--jobs', '2', '--target-dir', str(ROOT/'target/chip-focus-intercept'),
           '--message-format=json-render-diagnostics', '--locked', '--offline'],
          dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out, wall=240, cpu=900, gib=8)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-chip-focus-intercept' in log
    artifacts = []
    for line in log.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get('reason') == 'compiler-artifact' and row.get('executable') and row['profile']['test']:
            assert row['target']['name'] == 'strehl_chip_focus_intercept'
            artifacts.append(row['executable'])
    assert len(artifacts) == 1
    exe = out/'controls.exe'
    shutil.copyfile(artifacts[0], exe)
    b.g.unchanged(sources)
    save(out/'executable.json', ref(exe))


def controls(out, built):
    sources = read(built/'sources.json')
    b.g.unchanged(sources)
    assert ref(HERE/'run.py') in sources
    exe = built/'controls.exe'
    assert ref(exe) == read(built/'executable.json')
    assert 'Compiling strehl-chip-focus-intercept' in (built/'process.log').read_text(encoding='utf-8', errors='replace')
    out.mkdir(exist_ok=False)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe)))
    env = dict(RAYON_NUM_THREADS='8', STREHL_CHIP_FOCUS_INTERCEPT_OUT=str(out/'output'))
    try:
        b.job([str(exe), FILTER, '--nocapture', '--test-threads=1'], env, out, wall=120, cpu=600, gib=4)
    except AssertionError:
        # A genuine test refusal is retained. Resource/cleanup failures are errors.
        process = read(out/'process.json')
        assert process['exit_code'] == 101 and process['error'] is None
        assert process['terminal_job_accounting'] and not process['cleanup_errors']
    b.g.unchanged(sources)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    matches = re.findall(r'test result: (ok|FAILED)\. (\d+) passed; (\d+) failed;', log)
    assert len(matches) == 1 and int(matches[0][1])+int(matches[0][2]) == len(TESTS)
    assert all('test '+FILTER+name+' ...' in log for name in TESTS)
    records = sorted((out/'output').glob('*.json'))
    assert {p.stem for p in records} == set(RECORDS), 'Incomplete control evidence.'
    results = {p.stem: read(p) for p in records}
    scientific = results['planar']['scientific_pass'] is True and results['adversary']['scientific_pass'] is True
    mechanical = all(row['mechanical_pass'] is True for row in results.values())
    save(out/'completion.json', dict(test_status=matches[0][0], passed=int(matches[0][1]),
        failed=int(matches[0][2]), sources_unchanged=True, process=ref(out/'process.json'),
        scientific_screen_pass=scientific and mechanical and matches[0][0]=='ok', canonical_consumer_qualified=False,
        records=[ref(p) for p in records], photographic_quality_admitted=False,
        scope='Operator-only falsifier; canonical native consumer and real image remain untested.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('build', 'controls'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out != HERE and out.is_relative_to(HERE) and not out.exists()
    if args.phase == 'build':
        build(out)
    else:
        controls(out, args.build.resolve())


if __name__ == '__main__':
    main()
