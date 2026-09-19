"""Same fixed green registrar, with a visually confirmed local focus anchor."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, struct, sys, time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
REG=ROOT/'experiments/quality-september14/local-green-translation.py'
REG_SHA='5b64f7e612fd94cd8a22515bffb67addcee71021f6338f10a249c63864420196'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

common=load('focused_fit_bounds',ROOT/'experiments/full-context-placement/run.py')

def child(args):
    started=time.process_time()
    assert hashlib.sha256(REG.read_bytes()).hexdigest()==REG_SHA
    reg=load('unchanged_green_registrar',REG)
    common.save(args.out/'controls.json',reg.controls())
    receipt=json.loads((args.samples/'receipt.json').read_text())
    assert receipt['reference_index']==129 and receipt['target_origin_native']==[594,1424]
    assert receipt['target_shape']==[392,392] and receipt['native_sensor_shape']==[4688,7032]
    assert receipt['local_anchor_nomination']==args.anchor
    assert receipt['levels']==[512,15360]
    warp=HERE/'star-baseline-1/star.warpmap.txt'
    assert common.ref(warp)['sha256']==receipt['map_sha256']
    bits={int(p[0]):p[2:6] for line in warp.read_text().splitlines()
          if len(p:=line.split())>5 and p[0].isdigit() and p[1]=='placed'}
    guides={};positions={};left,right=reg.grids();centre=complex(3516,2344)
    source_bindings=[]
    for row in receipt['frames']:
        original=[struct.unpack('>d',bytes.fromhex(word))[0] for word in bits[row['index']]]
        assert row['a']+row['b_plane']==original,'Retained patch geometry differs from bound global map'
        path=args.samples/f"frame-{row['index']}-cfa.npy"
        raw=np.load(path,allow_pickle=False)
        assert raw.dtype==np.uint16 and raw.shape==tuple(reversed(row['source_xywh'][2:]))
        assert hashlib.sha256(raw.tobytes()).hexdigest()==row['raw_u16_sha256']
        source_bindings.append(common.ref(path))
        black,white=map(np.float32,receipt['levels'])
        guides[row['index']]=reg.guide((raw.astype(np.float32)-black)/(white-black),row['source_xywh'][:2],raw<16383)
        mapped=[reg.mapped(p,receipt['target_origin_native'],centre,complex(*row['a']),complex(*row['b_plane']),row['source_xywh'][:2]) for p in (left,right)]
        radius=reg.RADIUS+reg.MAX_SHIFT+reg.FD_STEP+1
        for p in mapped:
            assert (p.min(axis=0)>radius).all()
            assert (p.max(axis=0)+radius < np.array([raw.shape[1]-1,raw.shape[0]-1])).all()
        positions[row['index']]=mapped
    reference=[reg.sample(guides[args.anchor],p) for p in positions[args.anchor]]
    rows=[];entries=[]
    for row in receipt['frames']:
        index=row['index']
        result,_=reg.fit(guides[index],*reference,*positions[index])
        before=result['before']['validation_rmse']
        ratio=result['after']['validation_rmse']/before if before>0 else None
        accepted=(index==args.anchor or (result['converged'] and not result['at_translation_bound']
                  and result['after']['gain_positive'] and ratio is not None and ratio<1))
        result.update(frame=index,validation_ratio=ratio,accepted=accepted)
        rows.append(result)
        if accepted:
            entries.append(dict(file_name=Path(row['source']).name,transform_bits=bits[index],
                delta_source_native=[0.0,0.0] if index==args.anchor else result['delta_source_native']))
        print(json.dumps({k:result[k] for k in ('frame','delta_source_native','validation_ratio','accepted','at_translation_bound')}),flush=True)
    cfg=dict(schema_version=1,source_dir=str(Path(receipt['frames'][0]['source']).parent),
        expected_frame_count=259,native_geometry=[7032,4688],support_native=[594,1424,392,392],taper_native=32,frames=entries)
    common.save(args.out/'result.json',dict(local_anchor=args.anchor,global_reference=129,frames=rows,
        source_receipt=common.ref(args.samples/'receipt.json'),source_bindings=source_bindings,
        cpu_seconds=time.process_time()-started,interpretation='Fixed guide prediction, not photographic quality. Failed fits retain the original map. Local anchor remains in global129 gauge.'))
    assert len(entries)>=2,'No neighbouring correction earned a photographic replay'
    common.save(args.out/'placement.json',cfg)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples',type=Path,required=True)
    parser.add_argument('--anchor',type=int,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--child',action='store_true')
    args=parser.parse_args();args.samples=args.samples.resolve();args.out=args.out.resolve()
    if args.child: child(args);return
    assert args.out.is_relative_to(ROOT) and args.samples.is_relative_to(ROOT)
    args.out.mkdir()
    common.save(args.out/'preregistration.json',dict(registrar_sha256=REG_SHA,anchor=args.anchor,
        samples=common.ref(args.samples/'receipt.json'),runner=common.ref(Path(__file__)),
        unchanged='sigma1.5, radius6, +/-4 source-native search, same left/right support and nuisance protocol',
        accept='Converged, off bounds, positive gain and held-out decrease; exact zero for visually confirmed local anchor. Photo review remains mandatory.',
        scope='Only saved u16 patches; no new RAW read, no search-bound expansion, no intensity correction'))
    command=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--samples',str(args.samples),'--anchor',str(args.anchor),'--out',str(args.out),'--child']
    common.job(command,dict(RAYON_NUM_THREADS='2',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'),args.out,120)

if __name__=='__main__':main()
