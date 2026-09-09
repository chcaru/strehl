"""One real publication race and one escape refusal; root alone releases execution."""
from pathlib import Path
from types import SimpleNamespace
import argparse, ast, hashlib, json, os, stat, sys, time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
START=time.monotonic()
HELD=ROOT/'experiments/m194h-pedestal-causality/build-and-run.py'
HELD_SHA='b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410'

def read_source(p,cap):
    before=p.stat()
    assert stat.S_ISREG(before.st_mode) and 0<before.st_size<=cap
    with p.open('rb') as f:raw=f.read(before.st_size+1)
    after=p.stat()
    assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)
    assert len(raw)==before.st_size
    return raw

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--shim-sha256',required=True)
    args=parser.parse_args()
    assert os.name=='nt' and Path.cwd().resolve()==ROOT
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    fixture=HERE/'work/publication-race-controls-1'
    output=HERE/'work/publication-race-controls-1.json'
    assert not fixture.exists() and not output.exists()
    shim_path=HERE/'native-publication-scan.py'
    shim_raw=read_source(shim_path,16384)
    held_raw=read_source(HELD,65536)
    own_raw=read_source(Path(__file__).resolve(),16384)
    assert hashlib.sha256(shim_raw).hexdigest()==args.shim_sha256
    assert hashlib.sha256(held_raw).hexdigest()==HELD_SHA
    shim={'__file__':str(shim_path),'__name__':'publication_control_selected_shim'}
    exec(compile(shim_raw,str(shim_path),'exec'),shim)
    rows=[];error=None
    try:
        fixture.mkdir()
        payload=b'native-stage\n'
        selected=[n for n in ast.parse(held_raw).body if isinstance(n,ast.FunctionDef) and n.name in ('need','lexical','owned','scan')]
        assert {n.name for n in selected}=={'need','lexical','owned','scan'} and len(selected)==4
        def race(entry):
            native_root=fixture/entry;native_root.mkdir()
            directory=native_root/'native-run-1';directory.mkdir()
            stage=directory/'frame-00-original.u16.stage';final=directory/'frame-00-original.u16'
            with stage.open('xb') as f:assert f.write(payload)==len(payload)
            armed=[entry=='lstat'];events=[]
            def publish_now():
                armed[0]=False
                assert stage.parent==directory and stage.resolve().is_relative_to(fixture.resolve())
                os.link(stage,final);stage.unlink()
                events.append({'operation':'link-final-then-unlink-stage','entry':entry,'stage':str(stage),'final':str(final)})
            class RacePath(type(Path())):
                def lstat(self):
                    if entry=='lstat' and armed[0] and self==stage:publish_now()
                    return super().lstat()
                def stat(self,*,follow_symlinks=True):
                    if entry=='stat' and armed[0] and follow_symlinks and self==stage:publish_now()
                    return super().stat(follow_symlinks=follow_symlinks)
            namespace={'Path':RacePath,'ROOT':ROOT,'os':os,'stat':stat}
            exec(compile(ast.Module(body=selected,type_ignores=[]),str(HELD),'exec'),namespace)
            original_owned=namespace['owned']
            def timed_owned(path):
                result=original_owned(path)
                if entry=='stat' and result==stage:armed[0]=True
                return result
            namespace['owned']=timed_owned
            held=SimpleNamespace(**{k:namespace[k] for k in ('need','lexical','owned','scan')},ROOT=ROOT)
            active=[1];scan=shim['make_scanner'](held,active,native_root)
            observed=scan(directory,1024,tolerate_disappearance=False)
            actual=final.read_bytes()
            assert not stage.exists() and actual==payload and len(events)==1 and not armed[0]
            assert observed['files']==1 and observed['bytes']==len(payload) and observed['observed_disappearances']==0
            assert observed['publication_transitions']==1 and len(observed['publication_samples'])==1
            sample=observed['publication_samples'][0]
            assert Path(sample['stage'])==stage and Path(sample['final'])==final and sample['bytes']==len(payload)
            active[0]=None;completed=scan(directory,1024,tolerate_disappearance=False)
            assert completed['files']==1 and completed['bytes']==len(payload) and 'publication_transitions' not in completed
            rows.append({'id':'actual-publication-during-'+entry,'passed':True,'expected_bytes':len(payload),
                         'final_sha256':hashlib.sha256(actual).hexdigest(),'events':events,'live':observed,'completed_strict':completed})
            return directory
        race('lstat');directory=race('stat')
        escaped=fixture/'frame-00-original.u16.stage'
        with escaped.open('xb') as f:assert f.write(payload)==len(payload)
        refused=None
        try:shim['published_stat'](escaped,directory)
        except ValueError as exc:refused=str(exc)
        assert refused=='same-directory publication stage'
        assert escaped.read_bytes()==payload
        rows.append({'id':'same-name-outside-active-directory','passed':True,'stage':str(escaped),
                     'directory':str(directory),'expected_error':'same-directory publication stage','actual_error':refused})
    except BaseException as exc:
        error={'type':type(exc).__name__,'message':str(exc)[:2048]}
    ok=error is None and len(rows)==3 and all(r['passed'] is True for r in rows)
    value={'schema':'native-sensor-transfer-publication-controls-v1','status':'PASS_TARGETED_PUBLICATION_CONTROLS' if ok else 'REFUSED',
           'rows':rows,'error':error,'invocation':sys.orig_argv,
           'source':{'path':str(shim_path),'bytes':len(shim_raw),'sha256':args.shim_sha256},
           'held_source':{'path':str(HELD),'bytes':len(held_raw),'sha256':HELD_SHA},
           'control_source':{'path':str(Path(__file__).resolve()),'bytes':len(own_raw),'sha256':hashlib.sha256(own_raw).hexdigest()},
           'cpu_sample':time.process_time(),'wall_sample':time.monotonic()-START,
           'scope':'Fixed real same-directory hardlink/unlink publications at held lexical lstat and post-owned stat; one real sibling-file escape refused through the same fallback. Private Path and post-owned timing adapters only. No RAW, product, numerical, reparse-race or general filesystem commissioning.'}
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    assert len(raw)<=16384 and time.process_time()+1<=10 and time.monotonic()-START+2<=20
    with output.open('xb') as f:assert f.write(raw)==len(raw)
    assert sys.stdout.buffer.write(raw)==len(raw)
    sys.stdout.buffer.flush()
    assert time.process_time()<=10 and time.monotonic()-START<=20
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
