"""Single bounded RAW pass, nine retained u16 neighbours, five native nominees.

The unchanged September14 locator nominates frames, never image quality.
Only a rolling patch buffer and the best nine-frame neighbourhood are retained.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import json
import re
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=HERE/'star-focus-locator-1'
OLD=ROOT/'experiments/quality-september14'
MAP=HERE/'star-baseline-1/star.warpmap.txt'
MAP_HASH='6594d98255383218a3114fd783bfd0e2215b39b202777f1ee2e493f4b287a6a1'
SOURCE=Path('D:/personal/macro/requests/misc-diagnostic/star-sand-cpl')
OBSERVER=HERE/'star-matched-source-1/output'
DEMOSAIC=ROOT/'crates/strehl-core/src/demosaic.rs'
RENDERER=OLD/'patch-render-build-2/saved-rgb-render.exe'
RENDERER_HASH='3fea4f37deeb5935406d47e050276d72cf9eec5c624f268963b67d4a63f2ea49'
ORIGIN=[594,1424]
CORE_SENSOR=[626,1456,328,328]


def module(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m)
    return m


def save(path,data):
    with path.open('x',encoding='utf-8') as f: json.dump(data,f,indent=2,allow_nan=False);f.write('\n')


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def ordered_mhc(mosaic):
    import numpy as np
    assert mosaic.dtype==np.float32 and mosaic.ndim==2
    text=DEMOSAIC.read_text()
    taps={}
    for name in ('F_G','F_H','F_V','F_X'):
        content=re.search(r'const '+name+r': \[Tap; \d+\] = \[(.*?)\];',text,re.S).group(1)
        taps[name]=[ast.literal_eval(v) for v in re.findall(r'\([^()]+\)',content)]
    h,w=mosaic.shape
    padded=np.pad(mosaic,2,mode='reflect')
    convolved={}
    for name,items in taps.items():
        acc=np.zeros_like(mosaic)
        for dx,dy,weight in items:
            acc += np.float32(weight)*padded[2+dy:2+dy+h,2+dx:2+dx+w]
        convolved[name]=acc*np.float32(.125)
    yy,xx=np.indices((h,w));r=(yy%2==0)&(xx%2==0);b=(yy%2==1)&(xx%2==1);g1=(yy%2==0)&(xx%2==1)
    rgb=np.empty((h,w,3),np.float32)
    rgb[...,0]=np.where(r,mosaic,np.where(b,convolved['F_X'],np.where(g1,convolved['F_H'],convolved['F_V'])))
    rgb[...,1]=np.where(r|b,convolved['F_G'],mosaic)
    rgb[...,2]=np.where(b,mosaic,np.where(r,convolved['F_X'],np.where(g1,convolved['F_V'],convolved['F_H'])))
    return rgb


def product_render(folder,candidates):
    assert digest(RENDERER)==RENDERER_HASH
    stem='porous-source-129-frame129-raw'
    cfg=dict(receipt=str(OBSERVER/'receipt.json'),width=336,height=336,
        baseline_rgb=str(OBSERVER/(stem+'-mhc-camera-rgb.f32')),baseline_tiff=str(OBSERVER/(stem+'.tiff')),
        out=str(folder/'render'),candidates=candidates,
        xyz_to_cam=[[.746,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]])
    save(folder/'render-config.json',cfg)
    command=[str(RENDERER),str(folder/'render-config.json')]
    r=subprocess.run(command,capture_output=True,text=True,timeout=30)
    (folder/'render.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    assert r.returncode==0,r.stderr
    check=json.loads((folder/'render/receipt.json').read_text())
    assert check['baseline_differing_u16_samples']==0
    return check


def preflight():
    import numpy as np
    from scipy.ndimage import gaussian_filter
    folder=OUT/'preflight';folder.mkdir()
    # Reuse precisely the old score definition, including its failure direction.
    oldpath=OLD/'focus-locator.py'
    assert digest(oldpath)=='8c75f1a14fd0024774954a31423f4bf5bcf6bedc9dc5b4840cb0e22d450edb03'
    tree=ast.parse(oldpath.read_text())
    child=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='child')
    scoredef=next(n for n in child.body if isinstance(n,ast.FunctionDef) and n.name=='score')
    scope=dict(np=np,gaussian_filter=gaussian_filter)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[scoredef],type_ignores=[])),str(oldpath),'exec'),scope)
    score=scope['score']
    rng=np.random.default_rng(14092026);yy,xx=np.mgrid[:150,:150]
    flat=np.full((150,150),1000,dtype=np.float32)
    texture=flat+100*np.cos((xx+.3*yy)*2*np.pi/12)
    values=dict(flat=score(flat),flat_noise_sigma10=score(flat+rng.normal(0,10,flat.shape)),
        flat_noise_sigma100=score(flat+rng.normal(0,100,flat.shape)),sharp_texture=score(texture),
        blurred_texture=score(gaussian_filter(texture,5)))
    assert values['flat']==0 and values['flat_noise_sigma100']>values['flat_noise_sigma10']>0
    assert values['sharp_texture']>values['blurred_texture'] and values['flat_noise_sigma100']>values['blurred_texture']
    rows=[]
    for index in (125,129,133):
        stem=f'porous-source-{index}-frame{index}-raw'
        cfa=np.fromfile(OBSERVER/(stem+'-cfa.f32'),dtype='<f4').reshape(336,336)
        expected=np.fromfile(OBSERVER/(stem+'-mhc-camera-rgb.f32'),dtype='<f4').reshape(336,336,3)
        actual=ordered_mhc(cfa)
        different=int(np.count_nonzero(actual.view('u4')!=expected.view('u4')))
        rows.append(dict(frame=index,different_f32_rgb_bits=different,samples=int(actual.size)))
        assert different==0,'Ordered MHC differs from actual Rust fixture; no RAW pass allowed'
    development=product_render(folder,[])
    save(folder/'controls.json',dict(locator_values=values,ordered_mhc_goldens=rows,
        baseline_product_differing_u16_samples=development['baseline_differing_u16_samples'],
        failure='Noisy flat outranks blurred structure; score nominates only. Wrong MHC operation order fails exact Rust f32 fixtures.',
        old_locator_sha256=digest(oldpath),demosaic_source_sha256=digest(DEMOSAIC)))
    return score


def child():
    import numpy as np
    import rawpy
    from scipy.ndimage import gaussian_filter1d
    import tifffile
    from PIL import Image
    score=preflight()  # Flat/noise and exact-development checks precede ALL RAW decoding.
    assert digest(MAP)==MAP_HASH
    warp=module('star_locator_map',ROOT/'experiments/M-PHASE0-PHASE/src/clib.py').parse_warpmap(str(MAP))
    assert warp['reference_index']==129 and warp['plane']==(3516,2344)
    inputs=json.loads((HERE/'star-full-context-placement/baseline-1/inputs.json').read_text())['inputs']
    assert len(inputs)==259 and [Path(r['path']).name for r in inputs]==[f'DSC{i:05d}.ARW' for i in range(16,275)]
    observer=json.loads((OBSERVER/'receipt.json').read_text())
    wb=np.array(observer['wb_bits'],dtype='<u4').view('<f4')
    black,white=np.array(observer['levels'],dtype=np.float32)
    def normalize(raw):
        yy,xx=np.indices(raw.shape);channel=np.where((xx+yy)%2,1,np.where(yy%2,2,0))
        return np.maximum(raw.astype(np.float32)-black,np.float32(0))*wb[channel]/(white-black)
    centre=complex(3516,2344)
    corners=np.array([complex(594,1424),complex(985,1424),complex(594,1815),complex(985,1815)])
    roi_centre=complex(790,1620)
    scores=[];records=[];buffer={};best_score=-1;best_peak=None;best={};raw_fixture_checks=[]
    def nominate(k):
        nonlocal best_score,best_peak,best
        value=float(gaussian_filter1d(np.array(scores),2,mode='nearest')[k])
        if value>best_score:
            start=min(max(k-4,0),250)
            wanted=range(start,start+9)
            assert all(i in buffer for i in wanted)
            best={i:buffer[i] for i in wanted};best_peak=k;best_score=value
    for index,info in enumerate(inputs):
        source=Path(info['path']);st=source.stat()
        assert (st.st_size,st.st_mtime_ns)==(info['bytes'],info['mtime_ns'])
        a,b=warp['placements'][index]
        mapped=centre+a*(corners-centre)+2*b
        x0=2*int(np.floor((mapped.real.min()-12)/2));y0=2*int(np.floor((mapped.imag.min()-12)/2))
        x1=2*int(np.ceil((mapped.real.max()+13)/2));y1=2*int(np.ceil((mapped.imag.max()+13)/2))
        assert 0<=x0<x1<=7028 and 0<=y0<y1<=4688
        focus_centre=centre+a*(roi_centre-centre)+2*b
        # Match observer's source-centred, even-rounded 328+PAD4 crop.
        sx=(int(np.floor(focus_centre.real-164+.5))&~1)-4
        sy=(int(np.floor(focus_centre.imag-164+.5))&~1)-4
        assert x0<=sx and sx+336<=x1 and y0<=sy and sy+336<=y1
        with rawpy.imread(str(source)) as raw:
            assert raw.raw_image_visible.shape==(4688,7028) and raw.raw_pattern.tolist()==[[0,1],[3,2]]
            assert list(raw.black_level_per_channel)==[512]*4 and raw.white_level==16383
            patch=raw.raw_image_visible[y0:y1,x0:x1].copy()
        assert patch.dtype==np.uint16
        small=patch[sy-y0:sy-y0+336,sx-x0:sx-x0+336]
        scores.append(score(small[4:332,5:332:2][::2]))
        if index in (125,129,133):
            expected=np.fromfile(OBSERVER/f'porous-source-{index}-frame{index}-raw-cfa.f32',dtype='<f4').reshape(336,336)
            differing=int(np.count_nonzero(normalize(small).view('u4')!=expected.view('u4')))
            assert differing==0,'RAW-to-observer normalization or source coordinates differ'
            raw_fixture_checks.append(dict(frame=index,different_cfa_f32_bits=differing))
        margin=float(min((mapped.real-x0).min(),(mapped.imag-y0).min(),(x1-1-mapped.real).min(),(y1-1-mapped.imag).min()))
        assert margin>=12
        record=dict(index=index,source=str(source),bytes=info['bytes'],mtime_ns=info['mtime_ns'],
                    source_xywh=[x0,y0,x1-x0,y1-y0],source_display_xywh=[sx,sy,336,336],
                    a=[a.real,a.imag],b_plane=[b.real,b.imag],minimum_mapped_corner_margin_native=margin,
                    raw_u16_sha256=hashlib.sha256(patch.tobytes()).hexdigest())
        records.append(record);buffer[index]=patch
        if index>=8:
            nominate(index-8)
            for old in list(buffer):
                if old<index-12: del buffer[old]
        if index%32==0 or index==258: print(json.dumps(dict(stage='locate',frame=index)),flush=True)
    for k in range(251,259): nominate(k)
    smoothed=gaussian_filter1d(np.array(scores),2,mode='nearest')
    assert best_peak==int(np.argmax(smoothed)) and best_score==float(smoothed[best_peak])
    indices=sorted(best)
    assert len(indices)==9 and indices==list(range(indices[0],indices[0]+9))
    nominees=indices[::2]
    selected_records=[]
    for index in indices:
        np.save(OUT/f'frame-{index}-cfa.npy',best[index],allow_pickle=False)
        selected_records.append(records[index])
    secondary=ROOT/'experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe'
    anchor=records[best_peak];x,y,w,h=anchor['source_xywh']
    command=[str(secondary),anchor['source'],str(OUT),str(best_peak),str(y),str(x),str(h),str(w)]
    result=subprocess.run(command,capture_output=True,text=True,check=True,timeout=30)
    (OUT/'anchor-secondary.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    blob=(OUT/f'rawler-{best_peak}.bin').read_bytes()
    assert struct.unpack('<4I',blob[:16])==(y,x,h,w)
    other=np.frombuffer(blob,dtype='<u2',offset=16).reshape(h,w)
    different=int(np.count_nonzero(other!=best[best_peak]));assert different==0
    candidates=[]
    for index in nominees:
        record=records[index];x,y,_,_=record['source_xywh'];sx,sy,_,_=record['source_display_xywh']
        small=best[index][sy-y:sy-y+336,sx-x:sx-x+336]
        rgb=ordered_mhc(normalize(small))
        filename=OUT/f'frame-{index}-mhc-camera-rgb.f32';rgb.astype('<f4').tofile(filename)
        candidates.append(dict(name=f'frame-{index}',rgb=str(filename)))
    development=product_render(OUT,candidates)
    for index in nominees:
        rgb=tifffile.imread(OUT/'render'/f'frame-{index}.tiff')[4:-4,4:-4]
        assert rgb.shape==(328,328,3)
        Image.fromarray(((rgb.astype(np.uint32)+128)//257).astype(np.uint8)).save(OUT/f'frame-{index}-native.png')
    for info in inputs:
        st=Path(info['path']).stat();assert (st.st_size,st.st_mtime_ns)==(info['bytes'],info['mtime_ns'])
    save(OUT/'locator.json',dict(scores=scores,smoothed_scores=smoothed.tolist(),all_source_coordinates=records,
        nominated_anchor=best_peak,retained_indices=indices,photographic_nominees=nominees,
        scope='Nominations only; noise/contrast/scale can raise score. No photographic acceptance from scalar peak.',
        curve='Exact September14 G1 score, sigma1.2 spatial; Gaussian sigma2 on scalar frame curve only',
        region='Source-centred 328 native crop corresponding to frozen output core; no source resampling',
        known_source_fixture_checks=raw_fixture_checks))
    save(OUT/'receipt.json',dict(status='FOCUS_NEIGHBOURHOOD_NOMINATED',reference_index=129,local_anchor_nomination=best_peak,
        target_origin_native=ORIGIN,target_shape=[392,392],native_sensor_shape=[4688,7032],libraw_visible_shape=[4688,7028],
        levels=observer['levels'],wb_bits=observer['wb_bits'],tone_bits=observer['tone_bits'],map_sha256=MAP_HASH,
        frames=selected_records,photographic_nominees=nominees,independent_decode=dict(frame=best_peak,different_sensels=different,command=command),
        retained='Nine original-u16 padded CFA patches; no full RGB frames; global map remains reference129',
        source_metadata_unchanged=True,rawpy=rawpy.__version__,libraw=list(rawpy.libraw_version),
        baseline_developer_different_u16_samples=development['baseline_differing_u16_samples']))
    print(json.dumps(dict(nominated_anchor=best_peak,retained=indices,nominees=nominees,independent_differences=different)),flush=True)


def main():
    if '--child' in sys.argv: child();return
    OUT.mkdir(exist_ok=False)
    save(OUT/'preregistration.json',dict(helper_sha256=digest(Path(__file__)),map_sha256=MAP_HASH,
        source_frames=259,global_reference=129,target_sensor_support=[594,1424,392,392],minimum_margin_native=12,
        spatial_locator='Exact old 2D G1 score; flat/noise/blur control first',
        retention='Rolling13-patch buffer plus best9; five nominees at retained positions0,2,4,6,8',
        output='336-source RGB patch then PAD4 trim328; actual developer, identical starred golden fixtures first',
        wall_seconds=240,cpu_seconds=240,committed_bytes=2<<30))
    bounded=module('star_focus_bounded',ROOT/'experiments/m193c-output-grid/bounded-process.py')
    env,_=bounded.clean_environment(dict(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',RAYON_NUM_THREADS='1').items())
    api=bounded.load_job_api(bounded.binding(ROOT/'experiments/m12-scorecard/m12-harness.py'))
    command=[sys.executable,'-I','-B','-X','faulthandler',str(Path(__file__)),'--child']
    result=bounded.run(command,env,ROOT,OUT/'process.log',api=api,wall_seconds=240,cpu_seconds=240,log_bytes=2<<20,committed_bytes=2<<30)
    save(OUT/'process.json',dict(command=command,result=result))
    print(json.dumps(dict(exit_code=result['exit_code'],error=result['error'],accounting=result['job_accounting'])))
    assert result['exit_code']==0 and result['error'] is None and result['terminal_job_accounting']


if __name__=='__main__': main()
