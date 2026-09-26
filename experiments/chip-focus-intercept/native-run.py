"""Root-only bounded native observation; reuses existing build/job/view machinery."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRONT = ROOT/'experiments/chip-focus-front'
spec = importlib.util.spec_from_file_location('focus_intercept_native_existing', ROOT/'experiments/band-source-agreement/run.py')
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
read, save, ref = b.read, b.save, b.ref
FILTER = 'merge_cmd::chip_focus_intercept::independent_controls::'
FULL = 'merge_cmd::chip_focus_intercept_full::complete_pair'
SCOPE = 'One separately authorized exploratory single-surface intercept observation; original proxy and general intercept screen remain refused.'
GAUSSIAN = ROOT/'experiments/chip-focus-radiance/full-1/output/receipt.json'
SMALL = HERE/'controls-1'
RECORDS = ('arithmetic', 'support', 'planar', 'adversary')


def bindings():
    paths = {Path(row['path']) for row in b.bindings()}
    paths.update(p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.rs', '.md', '.py'))
    paths.update(FRONT/'fit-1'/name for name in ('model.json', 'receipt.json', 'judgment.json'))
    paths.add(GAUSSIAN)
    paths.update(SMALL/'output'/(name+'.json') for name in RECORDS)
    paths.add(SMALL/'completion.json')
    return [ref(p.resolve()) for p in sorted(paths)]


def build(out):
    out.mkdir(exist_ok=False)
    (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch()
    sources = bindings()
    save(out/'sources.json', sources)
    save(out/'revision.json', dict(head=subprocess.check_output(
        ['git', '--no-optional-locks', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()))
    b.job(['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl',
        '--no-run', '--release', '--features', b.g.FEATURES, '--jobs', '2',
        '--target-dir', str(ROOT/'target/native-pyramid-profile'),
        '--message-format=json-render-diagnostics', '--locked', '--offline'],
        dict(RAYON_NUM_THREADS='8', CARGO_INCREMENTAL='0'), out, wall=600, cpu=2400, gib=16)
    log = (out/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log
    artifacts = {}
    for line in log.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get('reason') == 'compiler-artifact' and row.get('executable') and row.get('target', {}).get('name') == 'strehl':
            key = 'cli-tests' if row['profile']['test'] else 'strehl'
            assert key not in artifacts
            path = out/(key+'.exe')
            shutil.copyfile(row['executable'], path)
            artifacts[key] = ref(path)
    assert set(artifacts) == {'cli-tests'}
    b.g.unchanged(sources)
    save(out/'executables.json', artifacts)


def built(path):
    sources = read(path/'sources.json')
    b.g.unchanged(sources)
    assert ref(HERE/'native-run.py') in sources
    exe = path/'cli-tests.exe'
    assert ref(exe) == read(path/'executables.json')['cli-tests']
    assert 'Compiling strehl-cli' in (path/'process.log').read_text(encoding='utf-8', errors='replace')
    return exe, sources


def controls(out, exe, sources):
    out.mkdir(exist_ok=False)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe)))
    env = b.fields()
    env['STREHL_CHIP_FOCUS_INTERCEPT_OUT'] = str(out/'output')
    b.job([str(exe), FILTER, '--nocapture', '--test-threads=1'], env, out, wall=180, cpu=900, gib=4)
    log = (out/'process.log').read_text()
    matches = re.findall(r'test result: ok\. (\d+) passed;', log)
    assert matches == ['4']
    records = {name: read(out/'output'/(name+'.json')) for name in RECORDS}
    assert all(row['mechanical_pass'] is True for row in records.values())
    assert records['planar']['scientific_pass'] is True
    assert records['adversary']['scientific_pass'] is False and records['adversary']['depth_pass'] is False
    assert records['adversary']['contact_pass'] is True
    assert all(records[name]['canonical_consumer_qualified'] is False
               and records[name]['photographic_quality_admitted'] is False for name in ('planar', 'adversary'))
    assert read(SMALL/'completion.json')['scientific_screen_pass'] is False
    assert all(ref(out/'output'/(name+'.json'))['sha256'] == ref(SMALL/'output'/(name+'.json'))['sha256'] for name in RECORDS), 'Native-build controls changed from standalone records.'
    b.g.unchanged(sources)
    save(out/'completion.json', dict(controls_pass=True, passed_count=int(matches[0]),
        sources_unchanged=True, process=ref(out/'process.json'), scope=SCOPE,
        results={name: ref(out/'output'/(name+'.json')) for name in records},
        general_screen_pass=False, exploratory_single_surface_observation=True,
        photographic_quality_admitted=False))


def validate(run):
    import numpy as np
    cfg, data = read(run/'config.json'), read(run/'output/receipt.json')
    assert data['phase'] == 'full' and data['mode'] == 'focus-intercept'
    assert data['source_count'] == data['probe_source_count'] == 299
    assert [row['index'] for row in data['frames']] == list(range(299))
    assert data['crop'] == [133, 89, 3250, 2166] and data['native_dimensions'] == [6500, 4332]
    assert data['map_sha256'] == cfg['warp_map_sha256'] and data['threads'] == 8
    assert data['original_metadata_unchanged'] and data['actual_tone_pinned'] and data['baseline_pinned_rewrite_exact']
    assert data['model_sha256'] == cfg['model_sha256'] == ref(Path(cfg['model_json']))['sha256']
    assert data['fit_receipt_sha256'] == cfg['fit_receipt_sha256']
    assert data['generated_photographic_replay_admitted'] is False
    assert data['predictive_proxy_admitted'] is False and data['general_promotion'] is False
    assert len(data['all_colour_site_support_checks']) == 299 and all(data['all_colour_site_support_checks'])
    assert data['changed_dc'] is True
    assert data['general_screen_pass'] is False and data['exploratory_single_surface_observation'] is True
    assert data['canonical_generated_qualified'] is False
    assert data['gaussian_receipt_sha256'] == cfg['gaussian_receipt_sha256'] == ref(GAUSSIAN)['sha256']
    assert data['gaussian_source_and_gather_exact'] is True and data['gaussian_development_exact'] is True
    if data['candidate_valid']:
        assert data['status'] == 'OBSERVATION_COMPLETE' and data['candidate_refusal'] is None
        assert 0 < data['mass_min'] <= data['mass_max'] < float('inf')
        assert data['noise_policy_pass'] and data['summary_cfa_unchanged']
        assert data['condition_max'] <= 1e4 and min(data['left_fraction_min'], data['right_fraction_min']) >= 0.01
        assert data['noise_gain_max'] <= 0.75 and data['noise_ratio_max'] <= 2.0
    else:
        assert data['status'] == 'NUMERICAL_REFUSAL' and data['candidate_refusal']
        assert all(data[key] is None for key in ('candidate_sha256', 'candidate_rgb16_le_sha256', 'candidate_planes_sha256', 'candidate_cache'))
    expected, expected_icc, expected_hash = b.image(Path(cfg['expected_baseline']))
    assert ref(Path(cfg['expected_baseline']))['sha256'] == cfg['expected_baseline_sha256']
    assert expected_hash == cfg['expected_baseline_pixels_sha256'] == data['baseline_rgb16_le_sha256']
    for arm in ('baseline', 'candidate'):
        if arm == 'candidate' and not data['candidate_valid']:
            assert data['status'] == 'NUMERICAL_REFUSAL'
            assert not (run/'output/candidate.tiff').exists()
            assert not (run/'output/candidate-cache.json').exists()
            assert not (run/'output/candidate-planes.f32').exists()
            continue
        path = run/'output'/(arm+'.tiff')
        pixels, icc, digest = b.image(path)
        assert ref(path)['sha256'] == data[arm+'_sha256'] and digest == data[arm+'_rgb16_le_sha256']
        assert icc == expected_icc
        if arm == 'baseline':
            assert np.array_equal(pixels, expected)
        del pixels
        cache_path = run/'output'/(arm+'-cache.json')
        cache = read(cache_path)
        assert ref(cache_path)['sha256'] == data[arm+'_cache']['sha256']
        assert cache['arm'] == arm and cache['phase'] == 'full'
        assert cache['frames'] == 299 and cache['reference'] == 149
        assert cache['crop'] == cfg['expected_crop'] and cache['full_geometry'] == cfg['expected_full_geometry']
        assert cache['map_sha256'] == cfg['warp_map_sha256'] and cache['tone_policy'] == cfg['tone_policy']
        binary = run/'output'/cache['binary']
        assert binary.parent == run/'output'
        assert ref(binary)['sha256'] == cache['binary_sha256'] == data[arm+'_cache']['binary_sha256']
        assert binary.stat().st_size == cache['binary_bytes'] == 4*3250*2166*4
        planes = np.memmap(binary, dtype='<f4', mode='r', shape=(4, 2166, 3250))
        assert np.isfinite(planes).all()
        hashes = [hashlib.sha256(p.tobytes()).hexdigest() for p in planes]
        assert hashes == cache['plane_sha256'] == data[arm+'_planes_sha256']
        del planes
    del expected
    pinned, icc, digest = b.image(run/'output/baseline-pinned-rewrite.tiff')
    assert digest == expected_hash and icc == expected_icc
    del pinned
    return data


def full(out, exe, sources, controls_path):
    assert read(controls_path/'bindings.json') == dict(sources=sources, executable=ref(exe))
    completed = read(controls_path/'completion.json')
    assert completed['controls_pass'] and completed['sources_unchanged'] and completed['passed_count'] == 4
    assert completed['process'] == ref(controls_path/'process.json')
    process = read(controls_path/'process.json')
    assert process['exit_code'] == 0 and process['error'] is None and process['terminal_job_accounting']
    assert not process['cleanup_errors']
    assert set(completed['results']) == set(RECORDS)
    assert completed['general_screen_pass'] is False and completed['exploratory_single_surface_observation'] is True
    assert all(ref(controls_path/'output'/(name+'.json')) == row for name, row in completed['results'].items())
    front = read(FRONT/'fit-1/receipt.json')
    judgment = read(FRONT/'fit-1/judgment.json')
    assert front['predictive_proxy_admitted'] is False and judgment['predictive_proxy_admitted'] is False
    assert judgment['numerical_pass'] and judgment['coverage_pass'] and judgment['bands'][0]['pass_predictive']
    assert ref(FRONT/'fit-1/model.json') == front['model']
    out.mkdir(exist_ok=False)
    config, baseline_bindings, ordered = b.recipe(out)
    config.update(mode='focus-intercept', model_json=str(FRONT/'fit-1/model.json'),
        model_sha256=front['model']['sha256'], fit_receipt=str(FRONT/'fit-1/receipt.json'),
        fit_receipt_sha256=ref(FRONT/'fit-1/receipt.json')['sha256'],
        gaussian_receipt=str(GAUSSIAN), gaussian_receipt_sha256=ref(GAUSSIAN)['sha256'])
    save(out/'config.json', config)
    save(out/'input-order.json', ordered)
    save(out/'bindings.json', dict(sources=sources, executable=ref(exe),
        controls=ref(controls_path/'completion.json'), baseline=baseline_bindings,
        config=ref(out/'config.json'), targets=ref(b.TARGETS), root_authorized_observation=True, scope=SCOPE))
    env = b.fields()
    env.update(STREHL_WARPMAP=config['warp_map'], STREHL_CHIP_FOCUS_INTERCEPT_CONFIG=str(out/'config.json'))
    b.job([str(exe), FULL, '--exact', '--ignored', '--nocapture', '--test-threads=1'], env, out,
        wall=1200, cpu=7200, gib=16)
    assert re.findall(r'test result: ok\. (\d+) passed;', (out/'process.log').read_text()) == ['1']
    b.g.unchanged(sources)
    assert all(ref(Path(row['path'])) == row for row in baseline_bindings)
    for row in ordered:
        st = Path(row['path']).stat()
        assert (st.st_size, st.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
    data = validate(out)
    save(out/'completion.json', dict(status='COMPLETE_AWAITING_INDEPENDENT_PHOTOGRAPHIC_REVIEW'
        if data['candidate_valid'] else 'NUMERICAL_REFUSAL', candidate_valid=data['candidate_valid'],
        phase='full', source_count=299, reference=149, sources_unchanged=True,
        baseline_current_production_pixels_and_icc_exact=True, actual_tone_pinned=True,
        candidate_pixels_changed=data['candidate_valid'] and data['candidate_rgb16_le_sha256'] != data['baseline_rgb16_le_sha256'],
        original_metadata_unchanged=True, receipt=ref(out/'output/receipt.json'), process=ref(out/'process.json'),
        generated_general_qualification=False, general_screen_pass=False,
        exploratory_single_surface_observation=True, photographic_replay_admitted=False, visual_verdict=None, scope=SCOPE))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('build', 'controls', 'full', 'views'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--controls', type=Path)
    parser.add_argument('--run', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out != HERE and out.is_relative_to(HERE) and not out.exists()
    if args.phase == 'build':
        build(out)
    elif args.phase == 'views':
        assert read(args.run/'completion.json')['candidate_valid'], 'No refused/partial candidate views.'
        b.validate, b.SCOPE = validate, SCOPE
        b.views(args.run.resolve(), out)
    else:
        exe, sources = built(args.build.resolve())
        if args.phase == 'controls':
            controls(out, exe, sources)
        else:
            full(out, exe, sources, args.controls.resolve())


if __name__ == '__main__':
    main()
