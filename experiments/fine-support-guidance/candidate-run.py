"""One fixed finest-band support candidate through the actual RAW consumer."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fine_candidate_common',ROOT/'experiments/full-context-placement/run.py')
c=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=c
spec.loader.exec_module(c)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('phase',choices=['build','controls','off','candidate'])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--build',type=Path)
    p.add_argument('--screen',type=Path)
    p.add_argument('--filter',default='merge_cmd::fine_support_candidate_tests::')
    a=p.parse_args()
    out=a.out.resolve()
    assert out.is_relative_to(HERE)
    out.mkdir()
    if a.phase=='build':
        (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch()
        (ROOT/'crates/strehl-core/src/pyramid.rs').touch()
        paths=set(c.source_paths())
        for directory in [HERE,ROOT/'experiments/phase-packed-rgb']:
            paths.update(directory.glob('*.rs'))
        paths.update([Path(__file__),HERE/'candidate-independent-plan.md',
            ROOT/'crates/strehl-core/src/pyramid.rs',ROOT/'crates/strehl-core/src/boxfilter.rs',
            ROOT/'experiments/native-correction-variance/core-bridge.rs',
            ROOT/'crates/strehl-cli/Cargo.toml',ROOT/'crates/strehl-core/Cargo.toml'])
        sources=[c.ref(f.resolve()) for f in sorted(paths)]
        c.save(out/'sources.json',sources)
        command=['cargo','test','-p','strehl-cli','--bin','strehl','--no-run','--release',
            '--features','native-pyramid-profile,native-gpu-gather,native-direct-planes,native-correction-variance',
            '--jobs','2','--target-dir',str(ROOT/'target/native-pyramid-profile'),
            '--message-format=json-render-diagnostics','--locked','--offline']
        c.job(command,{'RAYON_NUM_THREADS':'8','CARGO_INCREMENTAL':'0'},out)
        log=(out/'process.log').read_text(encoding='utf-8',errors='replace')
        assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
        executables=[]
        for line in log.splitlines():
            try: row=json.loads(line)
            except ValueError: continue
            if row.get('reason')=='compiler-artifact' and row.get('executable') and row.get('target',{}).get('name')=='strehl' and row['profile']['test']:
                executables.append(row['executable'])
        assert len(executables)==1
        exe=out/'cli-tests.exe'
        shutil.copyfile(executables[0],exe)
        assert all(c.ref(Path(r['path']))==r for r in sources)
        c.save(out/'executable.json',c.ref(exe))
        return
    build=a.build.resolve()
    sources=json.loads((build/'sources.json').read_text())
    assert all(c.ref(Path(r['path']))==r for r in sources)
    exe=build/'cli-tests.exe'
    assert c.ref(exe)==json.loads((build/'executable.json').read_text())
    fields=dict(RAYON_NUM_THREADS='8',STREHL_PYRAMID_WORKERS='8',STREHL_ALIGN='1',
        STREHL_FULLRES_GATHER='1',STREHL_DIRECT_PLANES='rounded',STREHL_PROBE_GATHER='green',
        STREHL_WARP_WRITEBACK='parallel',STREHL_GPU_GATHER='on',STREHL_GPU_SCHEDULE='device',
        STREHL_GPU_GATHER_LOG='off',STREHL_DEFECT='off',STREHL_FINE_SUPPORT='off',
        STREHL_FINE_SUPPORT_CANDIDATE_OUT=str(out/'output'))
    inputs=None
    if a.phase=='controls':
        fields.update(RAYON_NUM_THREADS='2',STREHL_GPU_GATHER='off')
        command=[str(exe),a.filter,'--nocapture','--test-threads=1']
    else:
        screen_dir=a.screen.resolve()
        screen=screen_dir/'output/screen.json'
        assert json.loads(screen.read_text())['photographic_replay_admitted'], 'fixed quality screen refused photographic replay'
        screen_bindings=json.loads((screen_dir/'bindings.json').read_text())
        assert screen_bindings['sources']==sources and screen_bindings['executable']==c.ref(exe)
        c.save(out/'screen-binding.json',c.ref(screen))
        prior=json.loads((ROOT/'experiments/quality-september19/vitamin-c-baseline-1/invocation.json').read_text())
        inputs=prior['inputs']
        warp=ROOT/'experiments/quality-september19/vitamin-c-baseline-1/vitamin-c.warpmap.txt'
        warp_ref=c.ref(warp)
        cfg=dict(dir=str(Path(inputs[0]['path']).parent),map=str(warp),out=str(out/'output'),frames=70,
            tone=dict(black=.090420,white=.914606,contrast=.55),
            regions=[dict(name='dark-inclusion',frame=33,x=3050,y=1850,width=384,height=384)],observe=False)
        c.save(out/'config.json',cfg)
        c.save(out/'inputs.json',dict(inputs=inputs,map=warp_ref))
        fields.update(STREHL_WARPMAP=str(warp),STREHL_MATCHED_SOURCE_CONFIG=str(out/'config.json'),
            STREHL_FINE_SUPPORT='radius32' if a.phase=='candidate' else 'off')
        command=[str(exe),'merge_cmd::matched_source_tests::matched_source_actual_consumer',
            '--exact','--ignored','--nocapture','--test-threads=1']
    def check_inputs():
        for r in inputs or []:
            st=Path(r['path']).stat()
            assert (st.st_size,st.st_mtime_ns)==(r['bytes'],r['mtime_ns'])
    check_inputs()
    c.save(out/'bindings.json',dict(sources=sources,executable=c.ref(exe),runner=c.ref(Path(__file__))))
    c.job(command,fields,out,wall=180)
    log=(out/'process.log').read_text()
    assert 'test result: ok.' in log and '0 passed;' not in log
    assert all(c.ref(Path(r['path']))==r for r in sources)
    check_inputs()
    if inputs:
        import numpy as np
        import tifffile
        assert c.ref(warp)==warp_ref
        result=out/'output/replay.tiff'
        with tifffile.TiffFile(result) as tif:
            shape=tif.pages[0].shape
            dtype=tif.pages[0].dtype
        assert shape==(4612,6920,3) and dtype==np.uint16
        record=dict(image=c.ref(result),shape=list(shape),original_metadata_unchanged=True,map_unchanged=True)
        if a.phase=='off':
            baseline=ROOT/'experiments/phase-packed-rgb/full-1/output/baseline.tiff'
            expected='c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21'
            assert c.ref(baseline)['sha256']==expected
            left=tifffile.imread(baseline)
            right=tifffile.imread(result)
            assert np.array_equal(left,right),'disabled consumer differs from retained pinned-tone baseline'
            record.update(disabled_rgb16_bit_exact=True,baseline=c.ref(baseline),
                whole_file_identical=c.ref(result)['sha256']==expected)
        c.save(out/'completion.json',record)

if __name__=='__main__':
    main()
