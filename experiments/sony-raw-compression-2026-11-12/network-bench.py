"""Pi encode + LAN SSH stream + PC decode + fsync, with exact RAW reconstruction.
SSH is a benchmark carrier, not a production HTTP throughput measurement.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,time,importlib.util
from wire import receive,controls
spec=importlib.util.spec_from_file_location('pi_runner',Path(__file__).with_name('run-pi.py'))
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
BASE,OUT,OPTS,DEST=runner.BASE,runner.OUT,runner.OPTS,runner.DEST

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',default=time.strftime('%Y%m%d-%H%M%S'))
    args=parser.parse_args()
    assert re.fullmatch(r'[A-Za-z0-9-]{1,64}',args.label)
    controls()
    subprocess.run(['scp',*OPTS,str(Path(__file__).with_name('wire.py')),'strehl@10.0.0.187:'+DEST+'/'],check=True)
    root=OUT/('network-roundtrips-'+args.label);root.mkdir(exist_ok=False)
    source=OUT/'inputs/pixel-shift-4/DSC01472.ARW'
    expected=hashlib.sha256(source.read_bytes()).hexdigest()
    for repeat,mode in enumerate(['identity','zstd','cfa','cfa','zstd','identity']):
        part=root/(f'{repeat}-{mode}.partial');final=part.with_suffix('.ARW');assert not final.exists()
        start=time.perf_counter()
        process=subprocess.Popen(['ssh',*OPTS,'strehl@10.0.0.187',
          'python3 '+DEST+'/wire.py send --file '+DEST+'/DSC01472.ARW --mode '+mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        with part.open('wb') as file:
            receipt=receive(process.stdout,file);file.flush();os.fsync(file.fileno())
        stderr=process.stderr.read();process.wait(timeout=10)
        assert process.returncode==0,stderr.decode()
        assert receipt['sha256']==expected
        part.replace(final)
        seconds=time.perf_counter()-start
        assert hashlib.sha256(final.read_bytes()).hexdigest()==expected
        print(json.dumps({'repeat':repeat,'mode':mode,'seconds_to_durable':seconds,'path':str(final),**receipt}),flush=True)
