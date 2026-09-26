"""Generated-only native photometric estimator/consumer falsifiers."""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('photometric_existing_build', ROOT/'experiments/consistent-reconstruction/run.py')
gen = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gen
spec.loader.exec_module(gen)
band, g, c = gen.band, gen.g, gen.c
read, save, ref = gen.read, gen.save, gen.ref
FILTER = 'merge_cmd::native_photometric_normalization::independent_controls::'
NAMES = ('independent_identity_and_noise_controls', 'independent_estimator_discrimination_controls',
         'independent_refusal_controls', 'independent_quality_screen')
OLD_REQUIRED = gen.required_paths


def required_paths():
    paths = OLD_REQUIRED()
    paths.update(HERE/name for name in ('run.py', 'design.md', 'implementation.rs',
        'independent-controls.rs', 'independent-fixtures.rs', 'independent-plan.md'))
    assert all(path.is_file() for path in paths)
    names = re.findall(r'#\[test\]\s*fn\s+(\w+)', (HERE/'independent-controls.rs').read_text())
    assert len(names) == 4 and set(names) == set(NAMES)
    assert '/../../experiments/native-photometric-normalization/implementation.rs' in (
        ROOT/'crates/strehl-cli/src/merge_cmd.rs').read_text(encoding='utf-8')
    return paths


gen.required_paths = required_paths


def controls(out, build_dir):
    sources = read(build_dir/'sources.json')
    g.unchanged(sources)
    recorded = {row['path']:row for row in sources}
    for path in required_paths():
        row = ref(path.resolve()); assert recorded[row['path']] == row
    exe = (build_dir/'cli-tests.exe').resolve()
    assert ref(exe) == read(build_dir/'executables.json')['cli-tests']
    built = read(build_dir/'process.json')
    assert built['exit_code'] == 0 and built['error'] is None
    assert built['terminal_job_accounting'] and not built['cleanup_errors']
    assert 'Compiling strehl-cli' in (build_dir/'process.log').read_text(encoding='utf-8', errors='replace')
    out.mkdir(exist_ok=False)
    (out/'output').mkdir()
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe)))
    env = band.fields()
    env.update(RAYON_NUM_THREADS='2', STREHL_PYRAMID_WORKERS='2', STREHL_GPU_GATHER_LOG='off',
               STREHL_NATIVE_PHOTOMETRIC_OUT=str(out/'output'))
    band.job([str(exe), FILTER, '--nocapture', '--test-threads=1'], env, out,
             wall=240, cpu=1200, gib=4)
    process = read(out/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None
    assert process['terminal_job_accounting'] and not process['cleanup_errors']
    log = (out/'process.log').read_text()
    assert re.findall(r'test result: ok\. (\d+) passed;', log) == ['4']
    assert all(FILTER+name in log for name in NAMES)
    data = {name:read(out/'output'/(name+'.json')) for name in ('mechanical','estimator','refusals','screen')}
    assert all(row['schema'] == 1 and row['mechanical_pass'] is True for row in data.values())
    mechanical = data['mechanical']
    assert all(mechanical[key] is True for key in
               ('unity_cfa_mhc_exact', 'off_unity_identical', 'variance_destroyer_exercised'))
    assert mechanical['half_quad_translation'] == [0.5, -0.5] and len(mechanical['frames']) == 5
    assert [row['name'] for row in data['refusals']['cases']] == [
        'insufficient-eroded-support', 'clipped-nonreference', 'implausibly-dim-nonreference']
    assert all(row['exact_unity'] is True for row in data['refusals']['cases'])
    assert [row['scene'] for row in data['estimator']['cases']] == [
        'two-depth-colour-texture', 'flux-conserving-broad-defocus']
    assert data['estimator']['gain_tolerance'] == 0.002
    assert all(isinstance(row['null'], dict) and isinstance(row['uniform'], dict)
               for row in data['estimator']['cases'])
    screen = data['screen']; assert len(screen['cases']) == 7
    assert [(row['scene'], row['drift'], row['noise']) for row in screen['cases']] == [
        ('flat', 'none', True), ('flat', 'uniform', True),
        ('two-depth-colour-texture', 'none', True), ('two-depth-colour-texture', 'uniform', True),
        ('flux-conserving-broad-defocus', 'none', False), ('flux-conserving-broad-defocus', 'uniform', False),
        ('two-depth-colour-texture', 'left-only', True)]
    assert screen['photographic_replay_admitted'] is False
    decisions = ('quality_pass', 'positive_exercised', 'brightness_destroyer_exercised')
    assert all(type(screen[key]) is bool for key in decisions)
    assert type(data['estimator']['estimator_pass']) is bool
    qualified = all(screen[key] for key in decisions) and data['estimator']['estimator_pass']
    g.unchanged(sources)
    assert ref(exe) == read(out/'bindings.json')['executable']
    save(out/'completion.json', dict(instrument_completed=True, controls_executed=4, cases_executed=7,
        sources_unchanged=True, process=ref(out/'process.json'),
        receipts={name:ref(out/'output'/(name+'.json')) for name in data},
        quality_pass=screen['quality_pass'], estimator_pass=data['estimator']['estimator_pass'],
        positive_exercised=screen['positive_exercised'], brightness_destroyer_exercised=screen['brightness_destroyer_exercised'],
        candidate_qualified=qualified, photographic_replay_admitted=False, full_render_available=False,
        scope='Existing fixed-window scalar estimator on generated actual native consumer; no physical drift attribution or photographic qualification.'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('build','controls'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE and not out.exists()
    if args.phase == 'build':
        gen.build(out)
    else:
        assert args.build is not None
        controls(out,args.build.resolve())


if __name__ == '__main__':
    main()
