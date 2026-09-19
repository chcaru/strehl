"""One authorised observer-on replay, identical to the saved star baseline."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = HERE / 'star-matched-source-1'
BASELINE = HERE / 'star-full-context-placement/baseline-1'
BUILD = ROOT / 'experiments/full-context-placement/build-3'
COMMON = ROOT / 'experiments/full-context-placement/run.py'
spec=importlib.util.spec_from_file_location('star_observer_common',COMMON)
common=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=common
spec.loader.exec_module(common)


def main():
    OUT.mkdir(exist_ok=False)
    invocation=json.loads((BASELINE/'invocation.json').read_text())
    command=invocation['command']
    exe=BUILD/'cli-tests.exe'
    assert Path(command[0]).resolve()==exe.resolve()
    artifacts=json.loads((BUILD/'executables.json').read_text())
    assert common.ref(exe)==artifacts['cli-tests']
    sources=json.loads((BUILD/'sources.json').read_text())
    assert all(common.ref(Path(r['path']))==r for r in sources)
    baseline_inputs=json.loads((BASELINE/'inputs.json').read_text())
    baseline_done=json.loads((BASELINE/'completion.json').read_text())
    baseline_image=BASELINE/'output/replay.tiff'
    assert common.ref(baseline_image)==baseline_done['image']
    cfg=json.loads((BASELINE/'config.json').read_text())
    assert cfg['frames']==259 and cfg['observe'] is False
    assert cfg['tone']==dict(black=.01566,white=.51099,contrast=.55)
    assert common.ref(Path(cfg['map']))==baseline_inputs['warp']
    cfg.update(out=str(OUT/'output'),observe=True,
               regions=[dict(name=f'porous-source-{i}',frame=i,x=472,y=1352,width=328,height=328)
                        for i in (125,129,133)])
    common.save(OUT/'config.json',cfg)
    fields=dict(invocation['environment'])
    assert 'STREHL_LOCAL_PLACEMENT_FILE' not in fields
    fields['STREHL_MATCHED_SOURCE_CONFIG']=str(OUT/'config.json')
    rawdir=Path(cfg['dir'])
    files=sorted(p for p in rawdir.iterdir() if p.is_file() and p.suffix.upper()=='.ARW')
    assert [p.name for p in files]==[f'DSC{i:05d}.ARW' for i in range(16,275)]
    inputs=[dict(path=str(p),bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in files]
    assert inputs==baseline_inputs['inputs']
    common.save(OUT/'preregistration.json',dict(reference=129,selected_frames=[125,129,133],
        output_roi=[472,1352,328,328],source_selection='Preselected brackets, not known best-focus frames',
        comparison='Same actual developer for unwarped source CFA, gathered source, and merged CFA; source lacks CA correction',
        observer_nonperturbation='Require exact equality of every final RGB16 sample to saved observer-false baseline, and retain pixel hashes',
        falsifier='Any differing final RGB16 sample fails the observer check; identical structure in three sources cannot establish an acquisition limit',
        baseline=common.ref(baseline_image),build=common.ref(exe),runner=common.ref(Path(__file__))))
    common.save(OUT/'sources.json',sources)
    common.save(OUT/'inputs.json',inputs)
    common.job(command,fields,OUT)
    for row in inputs:
        st=Path(row['path']).stat()
        assert (st.st_size,st.st_mtime_ns)==(row['bytes'],row['mtime_ns'])
    assert all(common.ref(Path(r['path']))==r for r in sources)
    receipt=json.loads((OUT/'output/receipt.json').read_text())
    off=json.loads((BASELINE/'output/receipt.json').read_text())
    for key in ('crop_quad_xywh','tone_bits','wb_bits','levels','source_frame_count','native_map_reference'):
        assert receipt[key]==off[key], f'Baseline mismatch: {key}'
    assert receipt['raw_count']==receipt['gathered_count']==receipt['merged_count']==3
    import numpy as np
    import tifffile
    from PIL import Image
    a=tifffile.imread(baseline_image)
    b=tifffile.imread(OUT/'output/replay.tiff')
    assert a.shape==b.shape==(4480,6724,3) and a.dtype==b.dtype==np.uint16
    different=int(np.count_nonzero(a!=b))
    check=dict(different_rgb16_samples=different,total_rgb16_samples=int(a.size),
               baseline_pixel_sha256=hashlib.sha256(memoryview(a)).hexdigest(),
               observer_pixel_sha256=hashlib.sha256(memoryview(b)).hexdigest(),
               baseline_file=common.ref(baseline_image),observer_file=common.ref(OUT/'output/replay.tiff'))
    common.save(OUT/'observer-nonperturbation.json',check)
    assert different==0 and check['baseline_pixel_sha256']==check['observer_pixel_sha256'], 'Observer perturbed full output'
    views=[]
    for patch in receipt['patches']:
        image=tifffile.imread(OUT/'output'/(patch['stem']+'.tiff'))
        assert image.dtype==np.uint16 and image.shape==(336,336,3)
        crop=image[4:-4,4:-4]
        filename=patch['stem']+'-native.png'
        Image.fromarray(((crop.astype(np.uint32)+128)//257).astype(np.uint8)).save(OUT/filename)
        views.append(dict(frame=patch['frame'],stage=patch['stage'],file=filename,
                          padded_origin_xy=patch['padded_origin_xy'],coordinates=patch['coordinates']))
    common.save(OUT/'native-views.json',views)
    common.save(OUT/'completion.json',dict(status='MATCHED_SOURCE_OBSERVER_FINISHED',
        original_metadata_unchanged=True,observer_pixel_identical=True,selected_frames=[125,129,133],
        final_image=common.ref(OUT/'output/replay.tiff')))
    print(json.dumps(dict(observer_differing_samples=different,views=len(views))))


if __name__=='__main__': main()
