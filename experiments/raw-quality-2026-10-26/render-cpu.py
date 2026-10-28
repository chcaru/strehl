"""Render one ordered Sony RAW stack with the current normal CPU pipeline."""
from pathlib import Path
import argparse,importlib.util,json,math,re,sys
import numpy as np
import tifffile
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
HELPER=ROOT/'experiments/m193c-output-grid/bounded-process.py'
spec=importlib.util.spec_from_file_location('native_delivery_bounded',HELPER)
b=importlib.util.module_from_spec(spec);sys.modules[spec.name]=b;spec.loader.exec_module(b)
def save(path,value):
    with path.open('x',encoding='utf-8') as f:f.write(json.dumps(value,indent=2)+'\n')
def ref(path):return dict(path=str(path),**b.binding(path))
def raw_paths(folder):
    # Same nonrecursive lexical filename order and ARW filter as the CLI.
    return sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower()=='.arw'),key=lambda p:str(p))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--exe',type=Path);p.add_argument('--sha256')
    p.add_argument('--build-manifest',type=Path,default=ROOT/'scripts/native-build.json')
    p.add_argument('--warp-map',type=Path);p.add_argument('--exposure',type=float)
    a=p.parse_args();source=a.input.resolve();out=a.out.resolve()
    if bool(a.exe)!=bool(a.sha256):p.error('--exe and --sha256 must be supplied together')
    manifest=None
    if a.exe:
        exe=a.exe.resolve();expected=a.sha256.lower()
    else:
        manifest=a.build_manifest.resolve();m=json.loads(manifest.read_text(encoding='utf-8'))
        assert m['schema']==1,'unsupported build manifest'
        entry=m['executable'];exe=Path(entry['path']);exe=(ROOT/exe).resolve() if not exe.is_absolute() else exe.resolve()
        expected=entry['sha256'].lower()
    assert re.fullmatch('[0-9a-f]{64}',expected) and exe.is_file(),'valid explicit executable binding required'
    executable=ref(exe);assert executable['sha256']==expected,'executable hash mismatch'
    assert source.is_dir() and not out.exists() and out.parent.is_dir(),'existing input and fresh output directory required'
    assert not out.is_relative_to(source),'output must be outside the read-only input directory'
    assert a.exposure is None or math.isfinite(a.exposure),'finite exposure required'
    sources=raw_paths(source);assert 3<=len(sources)<=1024,'expected 3..1024 ordered ARW files'
    print(f'Binding {len(sources)} originals and the selected executable',flush=True)
    inputs=[dict(index=i,mtime_ns=s.stat().st_mtime_ns,**ref(s)) for i,s in enumerate(sources)]
    warp=a.warp_map.resolve() if a.warp_map else out/'alignment.txt'
    existing_map=ref(warp) if a.warp_map else None
    if existing_map:assert 'resampler catmull-rom' in warp.read_text().splitlines(),'retained map must use catmull-rom'
    out.mkdir();save(out/'input-order.json',inputs)
    fields=dict(RAYON_NUM_THREADS='4',STREHL_PYRAMID_WORKERS='4',STREHL_ALIGN='1',STREHL_WARPMAP=str(warp),
        STREHL_FULLRES_GATHER='1',STREHL_DEFECT='off',STREHL_TEMPORAL_ENERGY='off',
        STREHL_SPATIAL_NOISE_FLOOR='off')
    env,removed=b.clean_environment(fields.items());master=out/'stack-master.tiff'
    commands=[]
    if a.warp_map is None:commands.append(('align',[str(exe),'align',str(source),'--out',str(warp),'--threads','4','--resampler','catmull-rom']))
    render=[str(exe),'stack',str(source),'--merge','pyramid','--pyramid-bands','7','--pyramid-gate','2',
        '--pyramid-exponent','2','--pyramid-sharpen','1.4','--pyramid-select','soft','--pyramid-base','mean',
        '--srgb','--demosaic','--resampler','catmull-rom','--cover','crop','--out',str(master),'--linear-master',str(out/'linear-master.tiff')]
    if a.exposure is not None:render.append(f'--exposure={a.exposure}')
    commands.append(('render',render));harness=ROOT/'experiments/m12-scorecard/m12-harness.py'
    save(out/'invocation.json',dict(schema=1,executable=executable,build_manifest=ref(manifest) if manifest else None,
        runner=ref(Path(__file__).resolve()),helper=ref(HELPER),harness=ref(harness),commands=commands,
        environment=fields,removed_environment=removed,existing_map=existing_map,frames=len(inputs),
        settings='Current normal CPU fullres gather, 4 workers, matching camera/lens profile, as-shot WB, automatic tone; explicit exposure only when supplied.'))
    api=b.load_job_api(b.binding(harness))
    for label,command in commands:
        print(f'{label}: {len(sources)} frames',flush=True)
        result=b.run(command,env,ROOT,out/f'{label}.log',api=api,wall_seconds=3600,cpu_seconds=24000,
            log_bytes=32<<20,committed_bytes=24<<30)
        save(out/f'{label}-process.json',result)
        assert result['exit_code']==0 and result['error'] is None and result['terminal_job_accounting'] and not result['cleanup_errors'],result
        lines=warp.read_text().splitlines();rows=[line.split() for line in lines if line and line.split()[0].isdigit()]
        assert 'resampler catmull-rom' in lines,'held native resampler differs'
        assert len(rows)==len(inputs) and [int(r[0]) for r in rows]==list(range(len(inputs))) and all(r[1]=='placed' for r in rows)
        if existing_map:assert ref(warp)==existing_map,'retained map changed'
    with tifffile.TiffFile(master) as f:
        assert len(f.pages)==1;rgb=f.asarray();icc=bytes(f.pages[0].tags[34675].value)
    assert rgb.dtype==np.uint16 and rgb.ndim==3 and rgb.shape[2]==3 and icc,'RGB16 with ICC required'
    log=(out/'render.log').read_text(encoding='utf-8',errors='replace')
    domain=re.search(r'analysis domain\s*:\s*(\d+) x (\d+) at full-plane origin \((\d+), (\d+)\)',log)
    assert domain,'native cropped domain absent'
    w,h,x,y=map(int,domain.groups());assert rgb.shape[:2]==(2*h,2*w),'native output dimensions differ'
    image=Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8))
    image.save(out/'stack-full.jpg',quality=98,subsampling=0,icc_profile=icc)
    image.thumbnail((1617,1617),Image.Resampling.LANCZOS);image.save(out/'overview.jpg',quality=98,icc_profile=icc)
    with Image.open(out/'stack-full.jpg') as check:assert check.size==(2*w,2*h) and check.info.get('icc_profile')==icc
    assert raw_paths(source)==sources and ref(exe)==executable,'input list or executable changed'
    for s,i in zip(sources,inputs):
        assert s.stat().st_mtime_ns==i['mtime_ns'] and ref(s)=={k:i[k] for k in ('path','bytes','sha256')},'original changed'
    save(out/'completion.json',dict(schema=1,status='RENDERED_AWAITING_INDEPENDENT_VISUAL_REVIEW',frames=len(inputs),
        native_dimensions=[2*w,2*h],crop_quad_xywh=[x,y,w,h],master=ref(master),full_jpeg=ref(out/'stack-full.jpg'),
        overview=ref(out/'overview.jpg'),warp_map=ref(warp),executable=executable,original_bytes_and_metadata_unchanged=True,
        viewing_note='Full JPEG and RGB16 master contain the entire stack output. Overview is resampled for orientation.'))
    print(f'Complete: {master} ({2*w} x {2*h})',flush=True)
if __name__=='__main__':main()
