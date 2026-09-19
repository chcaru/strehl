"""Bounded exact-consumer fine-support diagnostic; no candidate render."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fine_common', ROOT/'experiments/full-context-placement/run.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['build','controls','measure'])
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir()
    if args.phase == 'build':
        (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch()
        paths = set(c.source_paths())
        for directory in [HERE, ROOT/'experiments/phase-packed-rgb']:
            paths.update(directory.glob('*.rs'))
        paths.update([Path(__file__), HERE/'charter.md',
            ROOT/'experiments/native-correction-variance/core-bridge.rs',
            ROOT/'crates/strehl-cli/Cargo.toml',ROOT/'crates/strehl-core/Cargo.toml'])
        sources = [c.ref(p.resolve()) for p in sorted(paths)]
        c.save(out/'sources.json', sources)
        command = ['cargo','test','-p','strehl-cli','--bin','strehl','--no-run','--release',
            '--features','native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance',
            '--jobs','2','--target-dir',str(ROOT/'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics','--locked','--offline']
        c.job(command,dict(RAYON_NUM_THREADS='8',CARGO_INCREMENTAL='0'),out)
        log = (out/'process.log').read_text(encoding='utf-8',errors='replace')
        assert 'Compiling strehl-cli' in log
        artifacts = []
        for line in log.splitlines():
            try: row=json.loads(line)
            except ValueError: continue
            if row.get('reason')=='compiler-artifact' and row.get('executable') and row.get('target',{}).get('name')=='strehl' and row['profile']['test']:
                artifacts.append(row['executable'])
        assert len(artifacts)==1
        exe=out/'cli-tests.exe'
        shutil.copyfile(artifacts[0],exe)
        assert all(c.ref(Path(row['path']))==row for row in sources)
        c.save(out/'executable.json',c.ref(exe))
        return
    build=args.build.resolve()
    sources=json.loads((build/'sources.json').read_text())
    assert all(c.ref(Path(row['path']))==row for row in sources)
    exe=build/'cli-tests.exe'
    assert c.ref(exe)==json.loads((build/'executable.json').read_text())
    fields=dict(RAYON_NUM_THREADS='8',STREHL_PYRAMID_WORKERS='8',STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1',STREHL_DIRECT_PLANES='rounded',STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel',STREHL_GPU_GATHER='on',STREHL_GPU_SCHEDULE='device',
        STREHL_GPU_GATHER_LOG='off',STREHL_DEFECT='off',STREHL_FINE_SUPPORT_OUT=str(out/'output'))
    command=[str(exe),'merge_cmd::fine_support_tests::','--nocapture','--test-threads=1']
    inputs=None
    if args.phase=='measure':
        prior=json.loads((ROOT/'experiments/quality-september19/vitamin-c-baseline-1/invocation.json').read_text())
        inputs=prior['inputs']
        warp=ROOT/'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
        warp_ref=c.ref(warp)
        config=dict(schema=1,source_dir=str(Path(inputs[0]['path']).parent),warp_map=str(warp),
            warp_map_sha256=warp_ref['sha256'],out_dir=str(out/'output'),expected_crop=[28,19,3460,2306],
            expected_xyz_to_cam=[[.7460,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]],
            expected_wb_bits=[1070374912,1065353216,1076715520],tone=[.090420,.914606,.55],
            weight_trace_dir=str(ROOT/'experiments/quality-september19/vitamin-c-weight-trace-1'))
        c.save(out/'config.json',config)
        c.save(out/'inputs.json',dict(inputs=inputs,map=warp_ref))
        fields.update(STREHL_WARPMAP=str(warp),STREHL_FINE_SUPPORT_CONFIG=str(out/'config.json'))
        command=[str(exe),'merge_cmd::fine_support_tests::actual_green_fine_support',
            '--exact','--ignored','--nocapture','--test-threads=1']
    def check_inputs():
        for row in inputs or []:
            stat=Path(row['path']).stat()
            assert (stat.st_size,stat.st_mtime_ns)==(row['bytes'],row['mtime_ns'])
    check_inputs()
    c.save(out/'bindings.json',dict(sources=sources,executable=c.ref(exe),runner=c.ref(Path(__file__))))
    c.job(command,fields,out,wall=180 if inputs else 120)
    log=(out/'process.log').read_text()
    assert 'test result: ok.' in log and '0 passed;' not in log
    assert all(c.ref(Path(row['path']))==row for row in sources)
    check_inputs()
    if inputs:
        assert c.ref(warp)==warp_ref
        c.save(out/'originals-after.json',dict(original_metadata_unchanged=True,map_unchanged=True))

if __name__=='__main__':
    main()
