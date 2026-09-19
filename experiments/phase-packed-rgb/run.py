"""Bounded test build/run using the established process launcher."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('phase_bounds', ROOT / 'experiments/full-context-placement/run.py')
common = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = common
spec.loader.exec_module(common)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['build', 'screen', 'full'])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--build', type=Path)
    p.add_argument('--filter', default='phase_packed_rgb::independent_controls::')
    a = p.parse_args()
    out = a.out.resolve()
    assert out.is_relative_to(ROOT)
    out.mkdir()
    if a.phase == 'build':
        (ROOT / 'crates/strehl-cli/src/merge_cmd.rs').touch()
        paths = set(common.source_paths())
        paths.update(HERE.glob('*.rs'))
        paths.update([Path(__file__), HERE / 'charter.md', HERE / 'independent-plan.md'])
        sources = [common.ref(x.resolve()) for x in sorted(paths)]
        common.save(out / 'sources.json', sources)
        command = ['cargo', 'test', '-p', 'strehl-cli', '--bin', 'strehl', '--test', 'byte-freeze',
                   '--no-run', '--release', '--features', 'native-pyramid-profile,native-gpu-gather,native-direct-planes',
                   '--jobs', '2', '--target-dir', str(ROOT / 'target/native-pyramid-profile'),
                   '--message-format=json-render-diagnostics', '--locked', '--offline']
        common.job(command, {'RAYON_NUM_THREADS':'8', 'CARGO_INCREMENTAL':'0'}, out)
        log = (out / 'process.log').read_text(encoding='utf-8', errors='replace')
        assert 'Compiling strehl-cli' in log
        artifacts = {}
        for line in log.splitlines():
            try: row = json.loads(line)
            except ValueError: continue
            if row.get('reason') == 'compiler-artifact' and row.get('executable') and row.get('target', {}).get('name') == 'strehl':
                name = 'cli-tests' if row['profile']['test'] else 'strehl'
                assert name not in artifacts
                dest = out / (name + '.exe')
                shutil.copyfile(row['executable'], dest)
                artifacts[name] = common.ref(dest)
        assert set(artifacts) == {'cli-tests', 'strehl'}
        assert all(common.ref(Path(r['path'])) == r for r in sources)
        common.save(out / 'executables.json', artifacts)
    else:
        build = a.build.resolve()
        sources = json.loads((build / 'sources.json').read_text())
        assert all(common.ref(Path(r['path'])) == r for r in sources)
        exe = build / 'cli-tests.exe'
        assert common.ref(exe) == json.loads((build / 'executables.json').read_text())['cli-tests']
        fields = {'RAYON_NUM_THREADS':'2', 'STREHL_PHASE_PACKED_OUT':str(out / 'output'),
                  'STREHL_FULLRES_GATHER':'1', 'STREHL_DIRECT_PLANES':'rounded',
                  'STREHL_PROBE_GATHER':'green', 'STREHL_GPU_GATHER':'off',
                  'STREHL_DEFECT':'off', 'STREHL_WARP_WRITEBACK':'parallel'}
        original_inventory = None
        if a.phase == 'full':
            rawdir = Path('D:/personal/macro/requests/misc-diagnostic/crystalized-vitamin-c-cpl')
            inventory = lambda: [dict(name=x.name, bytes=x.stat().st_size, mtime_ns=x.stat().st_mtime_ns)
                                for x in sorted(rawdir.iterdir()) if x.is_file()]
            original_inventory = inventory()
            assert [x['name'] for x in original_inventory] == [f'DSC{i:05d}.ARW' for i in range(94,164)]
            warp = ROOT / 'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
            warp_ref = common.ref(warp)
            config = dict(schema=1, source_dir=str(rawdir), warp_map=str(warp),
                warp_map_sha256=warp_ref['sha256'], out_dir=str(out / 'output'),
                expected_crop=[28,19,3460,2306], max_extra_inset_quads=8,
                expected_xyz_to_cam=[[.7460,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]],
                tone=[.090420,.914606,.55])
            common.save(out / 'config.json', config)
            common.save(out / 'inputs.json', dict(original_inventory=original_inventory, warp=warp_ref))
            fields.update(RAYON_NUM_THREADS='8', STREHL_PYRAMID_WORKERS='8', STREHL_GPU_GATHER='on',
                STREHL_GPU_SCHEDULE='device', STREHL_GPU_GATHER_LOG='off', STREHL_ALIGN='1', STREHL_WARPMAP=str(warp),
                STREHL_PHASE_PACKED_FULL_CONFIG=str(out / 'config.json'))
        env, removed = common.b.clean_environment(fields.items())
        command = ([str(exe), 'merge_cmd::phase_packed_rgb::full_stack::vitamin_c_complete_pair', '--exact', '--ignored',
                    '--nocapture', '--test-threads=1'] if a.phase == 'full' else
                   [str(exe), a.filter, '--nocapture', '--test-threads=1'])
        common.save(out / 'invocation.json', {'command':command,'environment':fields,'removed_environment':removed,
                    'executable':common.ref(exe),'sources':sources,'runner':common.ref(Path(__file__))})
        api = common.b.load_job_api(common.b.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
        result = common.b.run(command, env, ROOT, out / 'process.log', api=api,
                    wall_seconds=600 if a.phase=='full' else 120, cpu_seconds=3600 if a.phase=='full' else 300,
                    log_bytes=16<<20, committed_bytes=(16 if a.phase=='full' else 4)<<30)
        common.save(out / 'process.json', result)
        print(json.dumps({k:result[k] for k in ('exit_code','error','wall_seconds')}))
        assert result['exit_code']==0 and result['error'] is None
        assert result['terminal_job_accounting'] and not result['cleanup_errors']
        assert all(common.ref(Path(r['path'])) == r for r in sources)
        if original_inventory is not None:
            assert inventory() == original_inventory and common.ref(warp) == warp_ref
            common.save(out / 'originals-after.json', dict(original_metadata_unchanged=True, inventory=inventory()))
        log = (out / 'process.log').read_text()
        assert 'test result: ok.' in log and '0 passed;' not in log

if __name__ == '__main__':
    main()
