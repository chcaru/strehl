"""Root-owned bounded preparation/build/actual-consumer screen. No RAW route."""
from pathlib import Path
import argparse, importlib.util, json, re, shutil, sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
g=load('optical_support_bounded_common',ROOT/'experiments/cross-scale-source-prior/run.py')
c=g.c
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def own_sources():
    required=['prepare.py','implementation.rs','core-bridge.rs','run.py','design.md','integration.md','independent-controls.py']
    assert all((HERE/n).is_file() for n in required),'independent controls must be frozen before execution'
    paths={HERE/n for n in required}
    paths.update(HERE.glob('independent-*.md'))
    paths.update(ROOT/'experiments/layered-raw-inverse'/n for n in ('pupil-stencil.py','model.py','pupil-stencil-results.md'))
    paths.update(Path(r['path']) for r in g.bindings())
    lib=Path(sys.executable).parent/'Lib/site-packages/torch/lib'
    paths.update(lib/n for n in ('nvrtc64_120_0.dll','nvrtc-builtins64_128.dll','cudart64_12.dll'))
    paths.add(Path('C:/Windows/System32/nvcuda.dll'))
    assert all(p.is_file() for p in paths)
    return [c.ref(p.resolve()) for p in sorted(paths)]
def exact(rows):assert all(c.ref(Path(r['path']))==r for r in rows),'bound source/input changed'
def inputs(prepared):
    root=prepared/'output';m=read(root/'manifest.json')
    assert m['status']=='PREPARED' and m['frames']==5 and m['native_size']==[96,96]
    paths=[root/'manifest.json']
    for scene in m['scenes']:
        assert scene['name'] in ('flat','transparent','opaque')
        for row in scene['files']:
            path=root/scene['name']/row['file'];assert path.parent==root/scene['name']
            binding=c.ref(path);assert binding['sha256']==row['sha256'];paths.append(path)
    assert len(m['scenes'])==3
    return [c.ref(p) for p in paths]
def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('prepare','build','consume'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--build',type=Path);p.add_argument('--prepare',type=Path)
    a=p.parse_args();out=a.out.resolve();assert out.is_relative_to(HERE) and out!=HERE and not out.exists();out.mkdir()
    if a.phase=='build':
        (ROOT/'crates/strehl-cli/src/merge_cmd.rs').touch();(ROOT/'crates/strehl-core/src/pyramid.rs').touch()
    sources=own_sources();c.save(out/'sources.json',sources)
    if a.phase=='prepare':
        fields=dict(OMP_NUM_THREADS='4',MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1',CUDA_CACHE_DISABLE='1')
        g.job([sys.executable,'-I','-B','-X','faulthandler',str(HERE/'prepare.py'),'--out',str(out/'output')],fields,out,wall=120,cpu=240,gib=4)
        exact(sources);bindings=inputs(out);c.save(out/'completion.json',dict(prepared=True,inputs=bindings,generated_only=True));return
    if a.phase=='build':
        command=['cargo','test','-p','strehl-cli','--bin','strehl','--test','byte-freeze','--no-run','--release','--features',g.FEATURES,
            '--jobs','2','--target-dir',str(ROOT/'target/native-pyramid-profile'),'--message-format=json-render-diagnostics','--locked','--offline']
        g.job(command,dict(RAYON_NUM_THREADS='8',CARGO_INCREMENTAL='0'),out,wall=600,cpu=1800,gib=16)
        log=(out/'process.log').read_text(encoding='utf-8',errors='replace')
        assert 'Compiling strehl-cli' in log and 'Compiling strehl-core' in log
        artifacts={}
        for line in log.splitlines():
            try:r=json.loads(line)
            except ValueError:continue
            if r.get('reason')=='compiler-artifact' and r.get('executable') and r.get('target',{}).get('name')=='strehl':
                key='cli-tests' if r['profile']['test'] else 'strehl';assert key not in artifacts
                dst=out/(key+'.exe');shutil.copyfile(r['executable'],dst);artifacts[key]=c.ref(dst)
        assert set(artifacts)=={'cli-tests','strehl'};exact(sources);c.save(out/'executables.json',artifacts);return
    assert a.build is not None and a.prepare is not None
    build=a.build.resolve();prepared=a.prepare.resolve();bound=read(build/'sources.json');exact(bound)
    assert {r['path'] for r in sources}<={r['path'] for r in bound},'build lacks current bindings'
    data=inputs(prepared);assert read(prepared/'completion.json')['inputs']==data
    exe=build/'cli-tests.exe';assert c.ref(exe)==read(build/'executables.json')['cli-tests']
    c.save(out/'bindings.json',dict(executable=c.ref(exe),input_files=data,build=c.ref(build/'executables.json')))
    fields=dict(RAYON_NUM_THREADS='8',STREHL_PYRAMID_WORKERS='8',STREHL_ALIGN='1',STREHL_FULLRES_GATHER='1',
        STREHL_DIRECT_PLANES='rounded',STREHL_PROBE_GATHER='green',STREHL_WARP_WRITEBACK='parallel',STREHL_GPU_GATHER='on',
        STREHL_GPU_SCHEDULE='device',STREHL_GPU_GATHER_LOG='on',STREHL_DEFECT='off',STREHL_FINE_SUPPORT='off',
        STREHL_CA_BEFORE_MHC='off',STREHL_OPTICAL_SUPPORT_INPUT=str(prepared/'output'),STREHL_OPTICAL_SUPPORT_OUT=str(out/'output'))
    g.job([str(exe),'merge_cmd::optical_support_veto::','--include-ignored','--nocapture','--test-threads=1'],fields,out,wall=120,cpu=480,gib=4)
    log=(out/'process.log').read_text(encoding='utf-8',errors='replace')
    assert re.findall(r'test result: ok\. (\d+) passed;',log)==['2'] and 'OPTICAL_SUPPORT_CONSUMED' in log
    result=read(out/'output/result.json');assert result['status']=='CONSUMED' and len(result['scenes'])==3
    exact(sources);exact(bound);exact(data);assert c.ref(exe)==read(build/'executables.json')['cli-tests']
    c.save(out/'completion.json',dict(instrument_completed=True,photographic_replay_admitted=False,
        result=c.ref(out/'output/result.json'),scope='Independent exercise/quality scoring required; no photographic RAW'))
if __name__=='__main__':main()
