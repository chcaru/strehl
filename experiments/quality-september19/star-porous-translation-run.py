"""One authorised nine-frame RAW patch extraction and frozen local guide fit."""
from pathlib import Path
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'star-porous-translation-1'
ADAPTER = HERE / 'star-local-green-translation.py'


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def save(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
        stream.write('\n')


def child():
    import numpy as np
    import rawpy
    adapter = module('star_local_adapter',ADAPTER)
    design = adapter.plan()
    design['rois'] = [r for r in design['rois'] if r['name'] == 'porous-grain']
    assert len(design['rois']) == 1
    target = design['rois'][0]
    folder = OUT / 'porous-grain'
    folder.mkdir()
    decoder = ROOT / 'experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe'
    records = []
    for record in target['frames']:
        source = Path(record['source'])
        before = (source.stat().st_size,source.stat().st_mtime_ns)
        x,y,w,h = record['source_xywh']
        with rawpy.imread(str(source)) as raw:
            assert raw.raw_image_visible.shape == (4688,7028)
            assert raw.raw_pattern.tolist() == [[0,1],[3,2]]
            assert list(raw.black_level_per_channel) == [512]*4 and raw.white_level == 16383
            patch = raw.raw_image_visible[y:y+h,x:x+w].copy()
        assert patch.dtype == np.uint16 and patch.shape == (h,w)
        np.save(folder / f"frame-{record['index']}-cfa.npy",patch,allow_pickle=False)
        different = None
        if record['index'] == 129:
            cmd = [str(decoder),str(source),str(folder),'129',str(y),str(x),str(h),str(w)]
            response = subprocess.run(cmd,capture_output=True,text=True,timeout=30,check=True)
            (folder / 'frame-129-secondary.log').write_text(response.stdout+response.stderr,encoding='utf-8')
            blob = (folder / 'rawler-129.bin').read_bytes()
            assert struct.unpack('<4I',blob[:16]) == (y,x,h,w)
            other = np.frombuffer(blob,dtype='<u2',offset=16).reshape(patch.shape)
            different = int(np.count_nonzero(patch != other))
            assert different == 0, 'Independent central-frame decode disagrees'
            save(folder / 'independent-decoder-command.json',cmd)
        assert (source.stat().st_size,source.stat().st_mtime_ns) == before
        records.append(dict(**record,bytes=before[0],mtime_ns=before[1],
                            raw_u16_sha256=hashlib.sha256(patch.tobytes()).hexdigest(),
                            independently_decoded_different_sensels=different,
                            exact_16383=int(np.count_nonzero(patch==16383))))
        print(f"Saved original u16 frame {record['index']}; independent check {different}",flush=True)
    receipt = dict(target)
    receipt['frames'] = records
    receipt.update(rawpy=rawpy.__version__,libraw=list(rawpy.libraw_version),
                   independent_decode_scope='Reference129 original-u16 patch only; other eight frames not second-decoded',
                   decoder_sha256=hashlib.sha256(decoder.read_bytes()).hexdigest(),
                   source_metadata_unchanged=True,scope='Original CFA; no WB, alignment resampling, demosaic, or reconstruction')
    save(folder / 'receipt.json',receipt)
    adapter.fit(OUT,OUT / 'fit',design)


def main():
    if '--child' in sys.argv:
        child()
        return
    OUT.mkdir(exist_ok=False)
    save(OUT / 'preregistration.json',dict(reference_index=129,frames=list(range(125,134)),roi='porous-grain',
         target_sensor_xywh=[594,1424,392,392],guide_sigma_native=1.5,translation_bounds_native=[-4,4],
         acceptance='No frame accepted at bound; report every held-out ratio, solver failure and nonpositive gain',
         falsifier='Known-shift controls must recover within .05 native pixels; wrong-sign control must worsen validation; a photographic correction fails when held-out RMSE does not decrease',
         limitation='Guide fit can improve by matching blur; this is not a sharpness or geometric-truth gate',
         requested_cpu_seconds=90,requested_wall_seconds=120,requested_committed_bytes=2<<30,
         helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         adapter_sha256=hashlib.sha256(ADAPTER.read_bytes()).hexdigest()))
    bounded = module('star_translation_bounded',ROOT / 'experiments/m193c-output-grid/bounded-process.py')
    env,_ = bounded.clean_environment(dict(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',RAYON_NUM_THREADS='1').items())
    api = bounded.load_job_api(bounded.binding(ROOT / 'experiments/m12-scorecard/m12-harness.py'))
    command = [sys.executable,'-I','-B','-X','faulthandler',str(Path(__file__)),'--child']
    result = bounded.run(command,env,ROOT,OUT / 'process.log',api=api,
                         wall_seconds=120,cpu_seconds=90,log_bytes=1<<20,committed_bytes=2<<30)
    save(OUT / 'process.json',dict(command=command,result=result))
    print(json.dumps(dict(exit_code=result['exit_code'],error=result['error'],accounting=result['job_accounting'])))
    assert result['exit_code']==0 and result['error'] is None and result['terminal_job_accounting']


if __name__ == '__main__':
    main()
