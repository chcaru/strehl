"""Preserve an overbroad build-guard refusal; audit its single nonconsumer edit."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('intercept_frozen_native', HERE/'native-run.py')
n = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = n
spec.loader.exec_module(n)
ref, read, save = n.ref, n.read, n.save
BUILD = HERE/'native-build-1'
AUDIT = HERE/'reconciliation-2.json'
EXCLUDED = ROOT/'experiments/source-gradient-target/lib.rs'
NEWLY_BOUND = [ROOT/p for p in (
    'crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt',
    'experiments/m193c-output-grid/derivative-controls-preregister.md',
    'experiments/m193c-output-grid/independent-derivative-design-review.md',
    'experiments/m193c-output-grid/private-protocol.md',
    'experiments/m193c-output-grid/registration-derivative-design.md',
    'experiments/native-gpu-gather/src/coordinates.glsl',
    'experiments/rb-own-guide/controls-1/output/screen.json')]


def audit():
    original = read(BUILD/'sources.json')
    changes = [(row, ref(Path(row['path']))) for row in original if ref(Path(row['path'])) != row]
    assert len(changes) == 1 and Path(changes[0][0]['path']) == EXCLUDED
    assert read(BUILD/'process.json')['exit_code'] == 0
    assert read(BUILD/'process.json')['error'] is None
    assert read(BUILD/'process.json')['terminal_job_accounting']
    assert not read(BUILD/'process.json')['cleanup_errors']
    log = (BUILD/'process.log').read_text(encoding='utf-8', errors='replace')
    assert 'Compiling strehl-cli' in log
    rows = []
    for line in log.splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    artifacts = [r for r in rows if r.get('reason') == 'compiler-artifact']
    cli, = [r for r in artifacts if r['target']['name'] == 'strehl' and r.get('executable')]
    core, = [r for r in artifacts if r['target']['name'] == 'strehl_core']
    assert cli['profile']['test'] and cli['fresh'] is False
    assert any(r.get('reason') == 'build-finished' and r['success'] is True for r in rows)
    compiled = Path(cli['executable'])
    exe = BUILD/'cli-tests.exe'
    assert (ref(exe)['sha256'], ref(exe)['bytes']) == (ref(compiled)['sha256'], ref(compiled)['bytes'])
    core_lib, = [Path(p) for p in core['filenames'] if p.endswith('.rlib')]
    deps = [compiled.with_suffix('.d'), core_lib.with_name(core_lib.stem.removeprefix('lib')+'.d')]
    texts = [p.read_text(encoding='utf-8').replace('\\', '/') for p in deps]
    assert all('source-gradient-target' not in s for s in texts)
    assert all('chip-focus-intercept/'+p in texts[0] for p in ('operator.rs', 'full-adapter.rs', 'independent-controls.rs'))
    assert 'source-gradient-target' not in (ROOT/'Cargo.toml').read_text()
    sources = [row for row in original if Path(row['path']) != EXCLUDED]
    sources += [ref(p) for p in (Path(__file__).resolve(), BUILD/'sources.json', BUILD/'process.json',
                                BUILD/'process.log', HERE/'reconciliation-review.md', *deps, *NEWLY_BOUND)]
    n.b.g.unchanged(sources)
    record = dict(original_build_guard_pass=False, compiler_succeeded=True,
        excluded_nonconsumer_change=dict(before=changes[0][0], after=changes[0][1]),
        dependency_files=[ref(p) for p in deps], actual_intercept_operator_adapter_controls_in_dependencies=True,
        changed_standalone_harness_absent_from_dependencies=True, compiled_executable=ref(compiled),
        copied_executable=ref(exe), original_sources=ref(BUILD/'sources.json'),
        retained_sources=sources, newly_bound_inputs=[ref(p) for p in NEWLY_BOUND],
        newly_bound_build_start_identity_known=False,
        scope='Only unrelated standalone module-path fix excluded; all other originally bound sources retain original hashes. Seven compiler inputs are bound now without a retrospective unchanged claim.')
    if AUDIT.exists():
        assert read(AUDIT) == record
    else:
        save(AUDIT, record)
    return exe, sources+[ref(AUDIT)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('controls', 'full'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--controls', type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    assert out != HERE and out.is_relative_to(HERE) and not out.exists()
    exe, sources = audit()
    if args.phase == 'controls':
        n.controls(out, exe, sources)
    else:
        n.full(out, exe, sources, args.controls.resolve())


if __name__ == '__main__':
    main()
