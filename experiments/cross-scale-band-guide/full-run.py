"""Root-owned bounded native bridge controls and complete vitamin-C observation."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('cross_scale_full_jobs', HERE / 'run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
c = runner.c


def read(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['controls', 'cost', 'full'])
    for key in ('build', 'weights', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    for key in ('predictions', 'mechanical', 'review', 'cost'):
        parser.add_argument('--' + key, type=Path)
    args = parser.parse_args()
    out, build, model = args.out.resolve(), args.build.resolve(), args.weights.resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    sources = read(build / 'sources.json')
    assert all(c.ref(Path(row['path'])) == row for row in sources)
    exe = build / 'cli-tests.exe'
    assert c.ref(exe) == read(build / 'executable.json')
    server = HERE / 'score-server.py'
    paths = [Path(__file__), server, HERE / 'generic-consumer.py', HERE / 'train.py', model,
        HERE / 'run.py', ROOT / 'experiments/learned-band-guide/run.py',
        ROOT / 'experiments/learned-band-guide/train.py',
        ROOT / 'experiments/full-context-placement/run.py',
        ROOT / 'experiments/m193c-output-grid/bounded-process.py',
        ROOT / 'experiments/m12-scorecard/m12-harness.py']
    bindings = [c.ref(path) for path in paths]
    bridge = dict(python=sys.executable, score_server=str(server),
        score_server_sha256=c.ref(server)['sha256'], weights=str(model),
        weights_sha256=c.ref(model)['sha256'],
        generic_consumer_sha256=c.ref(HERE / 'generic-consumer.py')['sha256'],
        out_dir=str(out / 'output'))
    env = dict(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1', STREHL_DIRECT_PLANES='rounded', STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel', STREHL_GPU_GATHER='on', STREHL_GPU_GATHER_LOG='off',
        STREHL_GPU_SCHEDULE='device', STREHL_DEFECT='off', STREHL_FINE_SUPPORT='off',
        STREHL_CA_BEFORE_MHC='off', CUDA_VISIBLE_DEVICES='0', PYTHONHASHSEED='137',
        CUBLAS_WORKSPACE_CONFIG=':4096:8')
    out.mkdir()
    if args.phase == 'controls':
        assert args.predictions is not None
        predictions = args.predictions.resolve()
        assert read(predictions)['model_sha256'] == bridge['weights_sha256']
        bindings.append(c.ref(predictions))
        prediction_data = read(predictions)
        bindings.append(c.ref(Path(prediction_data['dataset'])))
        for record in prediction_data['records']:
            case = Path(record['case'])
            bindings.append(c.ref(case))
            for row in read(case)['arrays'].values():
                path = Path(row['file'])
                bindings.append(c.ref(path if path.is_absolute() else case.parent / path))
            for row in record['arrays'].values():
                path = Path(row['file'])
                bindings.append(c.ref(path if path.is_absolute() else predictions.parent / path))
        config = dict(out=str(out / 'output'), bridge=bridge, predictions=str(predictions),
            thin_case=str(ROOT / 'experiments/learned-band-guide/export-1/output/held-near-fine-far-coarse-n5/case.json'),
            scale_case=str(HERE / 'export-train-1/output/train-multiscale-gabor-v0-n5-b7/case.json'))
        env['STREHL_CROSS_SCALE_BRIDGE_CONFIG'] = str(out / 'config.json')
        test = 'merge_cmd::cross_scale_band_full::independent_controls::independent_bridge_controls'
        command = [str(exe), test, '--exact', '--nocapture', '--test-threads=1']
        wall, cpu = 300, 1800
    else:
        assert args.mechanical is not None and args.review is not None
        mechanical = args.mechanical.resolve()
        assert read(mechanical / 'output/bridge-controls.json')['passed'] is True
        previous = read(mechanical / 'bindings.json')
        assert previous['sources'] == sources and previous['executable'] == c.ref(exe)
        assert previous['model_sha256'] == bridge['weights_sha256']
        assert read(mechanical / 'completion.json')['process_completed'] is True
        bindings += [c.ref(mechanical / 'completion.json'), c.ref(args.review.resolve()),
            c.ref(mechanical / 'output/bridge-controls.json'), c.ref(mechanical / 'bindings.json')]
        ordered = read(ROOT / 'experiments/parallel-cfa-wavelet/full-1/inputs.json')['inputs']
        assert len(ordered) == 70
        inputs = []
        for index, row in enumerate(ordered):
            path = Path(row['path'])
            stat = path.stat()
            assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
            assert path.name == f'DSC{94 + index:05}.ARW'
            inputs.append(dict(index=index, path=str(path), identity_name=path.name,
                bytes=stat.st_size, sha256=c.ref(path)['sha256']))
        warp = ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
        assert c.ref(warp)['sha256'] == '84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f'
        prior_baseline = ROOT / 'experiments/parallel-cfa-wavelet/full-1/output/baseline.tiff'
        prior_receipt = read(prior_baseline.parent / 'receipt.json')
        assert c.ref(prior_baseline)['sha256'] == prior_receipt['baseline_sha256']
        # The saved prior reference predates the production /65536 numerator fix.
        # Preserve its exact four-code discrepancy; compare repeated current runs
        # against the same-build anchor, with no general numerical tolerance.
        baseline = HERE / 'full-cost-1/output/baseline-historical-tone.tiff'
        transition = HERE / 'full-cost-1/baseline-discrepancy.json'
        reference_review = HERE / 'baseline-reference-review.md'
        assert reference_review.is_file()
        discrepancy = read(transition)
        assert c.ref(baseline)['sha256'] == discrepancy['current_master_sha256'] == 'de1e5dccc0a0c92a4d1f3c93cee6109fb0ea123dbae990a1759b92203d4a70ef'
        assert discrepancy['prior_master_sha256'] == c.ref(prior_baseline)['sha256']
        assert discrepancy['current_rgb16_sha256'] == 'e870e3ec57f9d2819fee58d049f5de839c1e05584929afccbefc2b00dc9253b9'
        assert discrepancy['changed_channel_samples'] == 4 and discrepancy['maximum_absolute_code_difference'] == 1
        assert discrepancy['rgb8_rounding_exact'] and discrepancy['icc_exact']
        config = dict(schema=1, phase=args.phase, mode='learned-guide',
            stack_name='crystalized-vitamin-c-cpl', inputs=inputs, warp_map=str(warp),
            warp_map_sha256=c.ref(warp)['sha256'], out_dir=str(out / 'output'),
            expected_reference=35, expected_full_geometry=[3516, 2344], expected_crop=[28, 19, 3460, 2306],
            expected_baseline=str(baseline), expected_baseline_sha256=c.ref(baseline)['sha256'],
            expected_baseline_pixels_sha256=discrepancy['current_rgb16_sha256'],
            expected_camera='ILCE-7CM2', expected_iso=100., exposure_stops=0.,
            tone_policy='automatic-baseline-then-exact-pinned-candidate', historical_tone=[.090420, .914606, .55],
            **{key: value for key, value in bridge.items() if key != 'out_dir'})
        bindings += [c.ref(warp), c.ref(baseline), c.ref(prior_baseline),
            c.ref(prior_baseline.parent / 'receipt.json'), c.ref(transition), c.ref(reference_review),
            c.ref(HERE / 'full-cost-1/output/baseline-ready.json'),
            c.ref(HERE / 'full-cost-1/output/baseline-cache.json'),
            c.ref(HERE / 'full-cost-1/output/baseline-planes.f32')]
        c.save(out / 'input-metadata.json', ordered)
        if args.phase == 'full':
            assert args.cost is not None
            cost = args.cost.resolve()
            decision = read(cost / 'root-cost-decision.json')
            assert decision['full_observation_feasible'] is True
            assert decision['model_sha256'] == bridge['weights_sha256']
            assert read(cost / 'bindings.json')['sources'] == sources
            assert read(cost / 'completion.json')['process_completed'] is True
            bindings += [c.ref(cost / name) for name in
                ('root-cost-decision.json', 'bindings.json', 'completion.json')]
        env.update(STREHL_WARPMAP=str(warp), STREHL_CROSS_SCALE_BAND_FULL_CONFIG=str(out / 'config.json'))
        command = [str(exe), 'merge_cmd::cross_scale_band_full::complete_pair',
            '--exact', '--ignored', '--nocapture', '--test-threads=1']
        wall, cpu = (600, 3600) if args.phase == 'cost' else (1800, 12000)
    c.save(out / 'config.json', config)
    bindings.append(c.ref(out / 'config.json'))
    c.save(out / 'bindings.json', dict(sources=sources, executable=c.ref(exe), inputs=bindings,
        model_sha256=bridge['weights_sha256'], phase=args.phase, photographic_improvement=False))
    runner.old.run_job(command, env, out, wall, cpu, 16 << 30)
    assert 'test result: ok. 1 passed;' in (out / 'process.log').read_text()
    assert all(c.ref(Path(row['path'])) == row for row in sources + bindings)
    if args.phase == 'controls':
        assert read(out / 'output/bridge-controls.json')['passed'] is True
    else:
        actual_receipt = read(out / 'output/receipt.json')
        anchor = read(HERE / 'full-cost-1/output/baseline-cache.json')
        assert actual_receipt['baseline_planes_sha256'] == anchor['plane_sha256']
        for row in ordered:
            stat = Path(row['path']).stat()
            assert (stat.st_size, stat.st_mtime_ns) == (row['bytes'], row['mtime_ns'])
        if args.phase == 'full':
            import tifffile
            import numpy as np
            for arm in ('baseline', 'candidate'):
                with tifffile.TiffFile(out / 'output' / (arm + '.tiff')) as tif:
                    assert len(tif.pages) == 1 and tif.pages[0].shape == (4612, 6920, 3)
                    assert tif.pages[0].dtype == np.uint16 and tif.pages[0].tags[34675].value
    c.save(out / 'completion.json', dict(process_completed=True, phase=args.phase,
        sources_unchanged=True, inputs_unchanged=True, photographic_improvement=False,
        model_sha256=bridge['weights_sha256'], scope='Mechanical evidence or complete observation; independent photographic review still required.'))


if __name__ == '__main__':
    main()
