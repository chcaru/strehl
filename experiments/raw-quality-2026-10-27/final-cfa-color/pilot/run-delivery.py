"""Root-owned complete saved-CFA color comparison presentation, no reconstruction."""
from pathlib import Path
import argparse
import importlib.util
import sys

AREA = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('final_color_delivery_root', AREA / 'run.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
h = r.h


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--iteration', type=int, default=1)
    p.add_argument('--candidate-iteration', type=int, default=1)
    p.add_argument('--uniform-iteration', type=int, default=1)
    p.add_argument('--cost-iteration', type=int, default=1)
    p.add_argument('--null-iteration', type=int, default=1)
    p.add_argument('--full-iteration', type=int, default=1)
    a = p.parse_args()
    assert min(a.iteration, a.candidate_iteration, a.uniform_iteration, a.cost_iteration,
               a.null_iteration, a.full_iteration) > 0
    full, full_completion = r.finished_spectral_full(a.full_iteration)
    h.check_refs(full_completion['reports'])
    fields, env, removed = r.r.r.standard_environment()
    paths = [Path(__file__), AREA / 'views.py', AREA / 'saved-field.py', AREA / 'delivery-notes.md']
    bindings = r.common_bindings() + [h.ref(v) for v in paths]
    prerequisites = [h.ref(full / name) for name in ('process.json', 'completion.json', 'output/receipt.json')]
    arms = {}
    for name, iteration in (('candidate', a.candidate_iteration), ('uniform', a.uniform_iteration),
                            ('cost', a.cost_iteration), ('null', a.null_iteration)):
        source = r.folder(name, iteration)
        r.r.f.terminal_clean(source / 'process.json')
        completion = r.read(source / 'completion.json')
        expected = 'COMPLETE_HELD_NORMALIZED_CAMERA_NULL' if name == 'null' else 'COMPLETE_SAVED_FINAL_CFA_COLOR'
        assert completion['status'] == expected and completion['sources_unchanged']
        h.check_refs(completion['reports'])
        report = r.read(source / 'output/receipt.json')
        assert report['complete'] and not report['quality_claim'] and not report['photographic_admission']
        if name != 'null':
            expected_source = (r.r.folder('null', 1) / 'output/receipt.json' if name == 'cost'
                               else full / ('output/' + name + '/native/receipt.json'))
            assert Path(report['mhc_reference']['path']).samefile(expected_source)
            if name == 'cost':
                held = r.read(expected_source)
                assert held['cfa']['sha256'] == report['cfa']['sha256'] == '1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0'
                assert held['camera_rgb']['sha256'] == '42429be10904e1c81a95e83fc0d1fed22a1ced1eb211c9d449a20cb0cef2a7cf'
                assert held['pixel_hashes']['rgb16'] == 'f98cb4d9bc281eb9f28f4e618878607d7e7317eeb7ac20b349f35dfee81c280c'
                assert held['pixel_hashes']['linear_rgb32'] == 'ee2b711bc36e48b9913531e1c615bd265ad06fd395a74f6224ca94392e32be09'
            assert report['inputs_unchanged'] and report['entire_output'] and report['development_unchanged']
            assert r.read(source / 'numerical-dependencies.json') == r.numerical_bindings()
        arms[name] = source / 'output/receipt.json'
        prerequisites += [h.ref(source / v) for v in ('process.json', 'completion.json', 'output/receipt.json')]
    out = r.folder('views', a.iteration)
    out.mkdir(parents=True, exist_ok=False)
    h.save(out / 'source-bindings.json', bindings)
    h.save(out / 'prerequisite-bindings.json', prerequisites)
    for path in (Path(__file__), AREA / 'views.py'):
        (out / (path.stem + '-executed.py')).write_bytes(path.read_bytes())
    command = [sys.executable, '-B', '-X', 'faulthandler', str(AREA / 'views.py'),
        '--candidate-receipt', str(arms['candidate']), '--uniform-receipt', str(arms['uniform']),
        '--held-receipt', str(arms['cost']), '--null-receipt', str(arms['null']), '--out', str(out / 'output')]
    bounds = dict(wall_seconds=300, cpu_seconds=1200, committed_bytes=6 << 30, log_bytes=16 << 20)
    h.save(out / 'invocation.json', dict(command=command, bounds=bounds, environment=fields,
        removed_environment=removed, concurrent_work='No other root numerical, GPU or build job.',
        scope='Six complete final-color photographs and fixed native witnesses; no quality verdict.'))
    h.observed_run(command, env, out, bounds)
    report = r.read(out / 'output/views.json')
    assert report['status'] == 'COMPLETE_FINAL_CFA_COLOR_VIEWS_READY_NO_VERDICT'
    assert report['complete'] and not report['quality_claim'] and not report['photographic_admission']
    h.check_refs(bindings + prerequisites)
    h.save(out / 'completion.json', dict(status=report['status'], sources_unchanged=True,
        reports=[h.ref(q) for q in sorted((out / 'output').rglob('*')) if q.is_file()],
        photographic_improvement_claimed=False))


if __name__ == '__main__':
    main()
