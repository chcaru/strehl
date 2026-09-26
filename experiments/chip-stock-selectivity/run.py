"""One pinned complete-chip flat2 ramp ablation; root execution only, no build or sweep."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, sys, time

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASELINE=ROOT/'outputs/quality-september25/chip-fixed'
RETAINED=ROOT/'experiments/base-band-transfer/run.py'
spec=importlib.util.spec_from_file_location('chip_selectivity_retained_helpers',RETAINED)
g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)
ref,read,save=g.ref,g.read,g.save
EXPECTED_EXE='bec4c357836ad1383800a6c933460ee7ef072c525b5957a6f5deb5194b203314'
PINNED={
    'invocation.json':'49b6277016ff71da05c144690b765130bac9ab31f3bc9c3a3dc20927bc7e8037',
    'input-order.json':'ca1d16d0ffab95372c3401c48e9da79b330d4d2c6a4dd76077e06aa74a39c364',
    'completion.json':'d03e75a7d8fef4234317c90b5eca48ec4092fbb8eb0c257e109466302fdf4239'}

def held_metadata(log):
    return [v for v in g.photographic_metadata(log) if not v.startswith('per-band exp ')]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve()
    assert out.is_relative_to(HERE) and out!=HERE and not out.exists() and out.parent.is_dir()
    started=time.perf_counter()
    baseline_bindings=[ref(BASELINE/name) for name in PINNED]
    assert all(v['sha256']==PINNED[Path(v['path']).name] for v in baseline_bindings)
    baseline_log_binding=ref(BASELINE/'render.log')
    invocation,baseline=read(BASELINE/'invocation.json'),read(BASELINE/'completion.json')
    assert invocation['frames']==baseline['frames']==299
    assert baseline['native_dimensions']==[6500,4332] and baseline['crop_quad_xywh']==[133,89,3250,2166]
    assert len(invocation['commands'])==1 and invocation['commands'][0][0]=='render'
    old=invocation['commands'][0][1];exe=Path(old[0])
    assert ref(exe)==invocation['executable']==baseline['executable'] and ref(exe)['sha256']==EXPECTED_EXE
    assert old[1]=='stack' and old.count('--pyramid-sharpen')==old.count('--out')==1
    assert '--limit' not in old and not any(v.startswith('--exposure') for v in old)
    sharpen_index,out_index=old.index('--pyramid-sharpen')+1,old.index('--out')+1
    assert old[sharpen_index]=='1.4' and old[old.index('--pyramid-exponent')+1]=='2'
    assert old[old.index('--pyramid-base')+1]=='mean'
    assert Path(old[out_index])==Path(baseline['master']['path'])
    for key in ('master','full_jpeg','overview'):assert ref(Path(baseline[key]['path']))==baseline[key]
    original_dir=Path(old[2]);before=g.original_records(original_dir)
    assert len(before)==299 and before==read(BASELINE/'input-order.json'),'Original content/order/mtime changed.'
    fields=invocation['environment'].copy();warp=Path(fields['STREHL_WARPMAP'])
    assert ref(warp)==invocation['existing_map']==baseline['warp_map']
    lines=warp.read_text().splitlines()
    assert 'reference 149' in lines and 'frames 299' in lines and 'resampler catmull-rom' in lines
    rows=[line.split() for line in lines if line and line.split()[0].isdigit()]
    assert [int(row[0]) for row in rows]==list(range(299)) and all(row[1]=='placed' for row in rows)
    assert 'STREHL_LOCAL_PLACEMENT_FILE' not in fields
    targets=read(HERE/'targets.json')
    assert targets['native_size']==[6500,4332] and targets['crop']==[133,89,3250,2166] and len(targets['regions'])==7
    assert len({v['name'] for v in targets['regions']})==7
    for target in targets['regions']:
        x,y,w,h=target['native_xywh']
        assert 0<=x<x+w<=6500 and 0<=y<y+h<=4332 and (w,h) in ((384,384),(512,512))
    master=out/'stack-master.tiff';command=old.copy()
    command[sharpen_index],command[out_index]='1.0',str(master)
    differences=[dict(index=i,baseline=a,candidate=b) for i,(a,b) in enumerate(zip(old,command)) if a!=b]
    assert len(command)==len(old) and [v['index'] for v in differences]==sorted([sharpen_index,out_index])
    out.mkdir();save(out/'input-order.json',before)
    spec=importlib.util.spec_from_file_location('chip_selectivity_bounded_process',g.HELPER)
    bounded=importlib.util.module_from_spec(spec);sys.modules[spec.name]=bounded;spec.loader.exec_module(bounded)
    assert ref(g.HELPER)==invocation['helper'] and ref(g.HARNESS)==invocation['harness']
    env,removed=bounded.clean_environment(fields.items())
    sources=[ref(p) for p in (Path(__file__).resolve(),HERE/'design.md',HERE/'targets.json',RETAINED,g.HELPER,g.HARNESS)]
    save(out/'invocation.json',dict(schema=1,baseline=baseline_bindings,baseline_master=baseline['master'],
        baseline_render_log=baseline_log_binding,
        executable=ref(exe),warp_map=ref(warp),reference=149,frames=299,command=command,baseline_command=old,
        command_differences=differences,environment=fields,removed_environment=removed,sources=sources,
        limits=dict(wall_seconds=300,cpu_seconds=1500,committed_bytes=8<<30),
        tone_policy='Independent production automatic tone in each arm. Logs are rounded descriptions, not held exact f32 anchors.',
        scope='One complete fixed flat2 ramp counterfactual. No search, default change or claim of improvement.'))
    api=bounded.load_job_api(bounded.binding(g.HARNESS))
    result=bounded.run(command,env,ROOT,out/'render.log',api=api,wall_seconds=300,cpu_seconds=1500,
        committed_bytes=8<<30,log_bytes=8<<20)
    save(out/'render-process.json',result)
    assert result['exit_code']==0 and result['error'] is None and result['terminal_job_accounting'] and not result['cleanup_errors']
    current_log=(out/'render.log').read_text(encoding='utf-8',errors='replace')
    baseline_log=(BASELINE/'render.log').read_text(encoding='utf-8',errors='replace')
    assert held_metadata(current_log)==held_metadata(baseline_log),'Held camera/geometry/merge metadata differ.'
    assert re.search(r'per-band exp\s*:\s*2 2 2 2 2 2 2\s+\(coarsest -> finest\)',current_log)
    assert 'sharpness ramps 1.0x per octave' in current_log
    assert re.search(r'base band\s*:\s*plain mean across frames',current_log)
    assert re.search(r'alignment\s*:\s*ON \(sidecar-override\), reference frame 149, 299 placed / 0 refused',current_log)
    domain=re.search(r'analysis domain\s*:\s*(\d+) x (\d+) at full-plane origin \((\d+), (\d+)\)',current_log)
    assert domain and list(map(int,domain.groups()))==[3250,2166,133,89]
    tones={name:[v for v in log.splitlines() if v.startswith('tone ')] for name,log in (('baseline',baseline_log),('flat2',current_log))}
    assert all(len(v)==1 for v in tones.values())
    import numpy as np,tifffile
    from PIL import Image
    views=out/'native-views';views.mkdir();view_records=[];pixel_hashes={};icc_ref=None
    for arm,path in (('baseline',Path(baseline['master']['path'])),('flat2',master)):
        with tifffile.TiffFile(path) as f:
            rgb=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
            assert len(f.pages)==1 and rgb.dtype==np.uint16 and rgb.shape==(4332,6500,3) and icc
        if icc_ref is None:icc_ref=icc
        else:assert icc==icc_ref
        pixel_hashes[arm]=hashlib.sha256(rgb.astype('<u2',copy=False).tobytes()).hexdigest()
        image=Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8))
        if arm=='flat2':
            image.save(out/'stack-full.jpg',quality=98,subsampling=0,icc_profile=icc)
            overview=image.copy();overview.thumbnail((1617,1617),Image.Resampling.LANCZOS)
            overview.save(out/'overview.jpg',quality=98,icc_profile=icc)
        for target in targets['regions']:
            x,y,w,h=target['native_xywh'];edge=384 if w==384 else 256
            for yy in range(y,y+h,edge):
                for xx in range(x,x+w,edge):
                    tile=views/f"{arm}-{target['name']}-{xx}-{yy}.png"
                    image.crop((xx,yy,xx+edge,yy+edge)).save(tile,icc_profile=icc)
                    view_records.append(dict(arm=arm,region=target['name'],native_xywh=[xx,yy,edge,edge],file=ref(tile)))
        del rgb,image
    assert pixel_hashes['flat2']!=pixel_hashes['baseline'],'Ramp ablation was inert; no photographic comparison admitted.'
    with Image.open(out/'stack-full.jpg') as check:assert check.size==(6500,4332) and check.info.get('icc_profile')==icc_ref
    after=g.original_records(original_dir);save(out/'input-order-after.json',after)
    assert after==before,'Original content/order/mtime changed.'
    for bound in [*sources,*baseline_bindings,baseline_log_binding,invocation['executable'],invocation['existing_map'],
                  baseline['master'],baseline['full_jpeg'],baseline['overview']]:
        assert ref(Path(bound['path']))==bound,'Held source or reference changed.'
    save(views/'receipt.json',dict(native_size=[6500,4332],crop=[133,89,3250,2166],targets=ref(HERE/'targets.json'),
        tiles=view_records,conversion='Identical (RGB16+128)//257 with retained ICC; native tiles never resampled.'))
    save(out/'completion.json',dict(schema=1,status='COMPLETE_AWAITING_INDEPENDENT_PHOTOGRAPHIC_REVIEW',frames=299,
        reference=149,crop_quad_xywh=[133,89,3250,2166],native_dimensions=[6500,4332],master=ref(master),
        full_jpeg=ref(out/'stack-full.jpg'),overview=ref(out/'overview.jpg'),baseline_master=baseline['master'],
        baseline_full_jpeg=baseline['full_jpeg'],baseline_overview=baseline['overview'],rgb16_le_sha256=pixel_hashes,
        icc_sha256=hashlib.sha256(icc_ref).hexdigest(),command_differences=differences,tone_log_lines=tones,
        tone_anchors_exactly_pinned=False,original_bytes_and_metadata_unchanged=True,native_views=ref(views/'receipt.json'),
        total_wrapper_wall_seconds=time.perf_counter()-started,
        resource_scope='Owned render job only; original hash audits and full-image/native PNG preparation lie outside child timing.',
        visual_verdict=None,scope='Reject smoothing, brightness-only change, lost tracks/scratches or colour damage. No sweep/default change.'))
    print(f'Complete flat2 counterfactual: {master}',flush=True)

if __name__=='__main__':main()
