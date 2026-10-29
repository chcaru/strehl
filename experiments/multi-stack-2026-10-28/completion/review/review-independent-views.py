"""Fixed predeclared native review of two full independent views; no RAW reads."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, time
import numpy as np
import tifffile
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('display',HERE.parents[1]/'challenge'/'prepare-review.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def relative(root,text):
    p=Path(text);assert not p.is_absolute() and all(x not in ('..','') for x in p.parts)
    out=root/p;assert out.resolve().is_relative_to(root.resolve());return out

def freeze(run,out):
    assert (run/'completed.json').is_file()
    out.mkdir(parents=True,exist_ok=False)
    protocol=HERE/'independent-views-protocol-frozen.json';plan=load(protocol)
    source=run/'view-01/master.tiff'
    with tifffile.TiffFile(source) as t:baseline=json.loads(t.pages[0].description.split('DisplayBaseline: ',1)[1])
    with tifffile.TiffFile(run/'view-01/photograph.tiff') as t:icc=t.pages[0].tags[34675].value
    (out/'display-srgb.icc').write_bytes(icc)
    h.write_json(out/'fixed-transform.json',{'schema':'strehl.independent-review-transform.v1','parameter_source':str(source.resolve()),'parameter_source_sha256':h.digest(source),'display_baseline':baseline,'display_icc_file':'display-srgb.icc','display_icc_sha256':h.digest(out/'display-srgb.icc'),'policy':'First view metadata only; same transform for both independent gauges. No second-view pixel fitting.'})
    rois={};dimensions={}
    for label,witnesses in plan['native_witnesses'].items():
        with tifffile.TiffFile(run/label/'master.tiff') as t:height,width,_=t.pages[0].shape
        dimensions[label]=[width,height];rois[label]=[]
        for name,u,v in witnesses:
            x=max(0,min(width-384,math.floor(u*width-192+.5)));y=max(0,min(height-384,math.floor(v*height-192+.5)))
            rois[label].append({'name':name,'size':384,'origins':{label:[x,y]},'predeclared_center_uv':[u,v]})
    h.write_json(out/'roi-frozen.json',rois)
    h.write_json(out/'before-pixel-inspection.json',{'time_unix':time.time(),'protocol_sha256':h.digest(protocol),'transform_sha256':h.digest(out/'fixed-transform.json'),'roi_sha256':h.digest(out/'roi-frozen.json'),'dimensions':dimensions,'policy':'Rounded each own gauge from predeclared composition coordinates, never transferred between views; dimensions from TIFF headers only.'})
    h.commission_viewer(out)

def readback(path):
    with tifffile.TiffFile(path) as t:a=t.pages[0].asarray()
    b=tifffile.memmap(path,mode='r');sha=hashlib.sha256();lo=float('inf');hi=float('-inf');zeros=0
    assert a.dtype==np.float32 and a.ndim==3 and a.shape[2]==3
    for y in range(0,len(a),128):
        s=a[y:y+128];assert np.isfinite(s).all() and np.array_equal(s.view(np.uint32),b[y:y+128].view(np.uint32))
        sha.update(s.tobytes());lo=min(lo,float(s.min()));hi=max(hi,float(s.max()));zeros+=int(np.count_nonzero(np.all(s==0,axis=2)))
    return {'shape':list(a.shape),'pixel_sha256':sha.hexdigest(),'full_decode_equals_mapped_bits':True,'all_finite':True,'minimum':lo,'maximum':hi,'zero_rgb_pixels':zeros}

def inspect(run,out):
    freeze=load(out/'before-pixel-inspection.json');rois=load(out/'roi-frozen.json')
    assert freeze['roi_sha256']==h.digest(out/'roi-frozen.json') and freeze['transform_sha256']==h.digest(out/'fixed-transform.json')
    bundle=load(run/'bundle.json');complete=load(run/'completed.json');session=load(run/'session.json');ids=load(run/'source-identities.json')
    assert bundle['schema']=='strehl.independent-views.v1' and len(bundle['views'])==2
    assert complete['bundle_sha256']==h.digest(run/'bundle.json') and complete['report_sha256']==h.digest(run/'render-report.json')
    assert bundle['source_identities_sha256']==h.digest(run/'source-identities.json') and bundle['session_sha256']==h.digest(run/'session.json')
    assert bundle['relative_pose'] is None and bundle['intrinsics'] is None and not (run/'alignment.json').exists()
    evidence=[]
    for index,view in enumerate(bundle['views']):
        label=view['directory'];assert label==f'view-{index+1:02}'
        child=run/label
        for name,receipt in view['files'].items():
            path=relative(child,name);assert path.stat().st_size==receipt['bytes'] and h.digest(path)==receipt['sha256'],str(path)
        assert complete['render_bindings'][label+'/render-completion.json']==h.digest(child/'render-completion.json')
        render=load(child/'render-report.json');align=load(child/'alignment.json');focus=load(child/'focus/pass-01/geometry.json');child_ids=load(child/'source-identities.json')
        span=session['passes'][index]['global_range'];start,end=span['start'],span['end'];expected=list(range(start,end))
        assert view['source_indices']==expected and child_ids==ids[start:end]
        assert view['source_count']==299 and view['source_ids']==[row['sha256'] for row in child_ids]
        assert view['relative_pose'] is None and view['intrinsics'] is None
        assert render['mode']=='combine' and render['invalid_output_pixels']==0 and len(render['frames'])==299
        assert [f['frame'] for f in render['frames']]==list(range(299))
        assert all(f['pass']==0 and f['photometric_gain']==1 for f in render['frames'])
        x,y,w,hg=render['canvas'];g=view['gauge']
        assert g['origin_sensor']==[2*x,2*y] and g['dimensions']==[2*w,2*hg]
        assert g['focus_origin_sensor']==[2*x+.5,2*y+.5] and g['focus_step_sensor']==[2,2] and g['focus_dimensions']==[w,hg]
        assert focus['origin_quad']==[x,y] and focus['dimensions']==[w,hg] and focus['full_quad_geometry']==g['full_quad_geometry']==align['report']['geometry_plane_pixels']
        assert [r['ordinal'] for r in focus['ordinal_mapping']]==list(range(299))
        assert all(r['ordinal']==r['global_index']==r['acquisition'] for r in focus['ordinal_mapping'])
        for name in ['flags','usable','raw-coverage','focus-coverage']:
            with tifffile.TiffFile(child/f'focus/pass-01/{name}.tiff') as t:assert t.pages[0].shape==(hg,w)
        master=readback(child/'master.tiff');assert master['shape']==[2*hg,2*w,3]
        h.render(child/'master.tiff',out/label,out/'fixed-transform.json',label,compare=child/'photograph.tiff' if index==0 else None,rois=rois[label])
        evidence.append({'view':label,'name':view['name'],'source_count':299,'source_indices':expected,'all_originals_own_view_only':True,'gauge':g,'master':master,'geometry':align['report'],'recipe':render['recipe'],'bound_artifact_count':len(view['files'])})
    h.write_json(out/'artifact-audit.json',{'schema':'strehl.independent-views-review.v1','script_sha256':h.digest(__file__),'helper_sha256':h.digest(h.__file__),'views':evidence,'limits':['Independent per-view coordinates; no pixel difference or 2D join between views.','Shape/support focus flags are not metric depth or confidence probabilities.','Overviews are orientation only; all native witnesses are exact384 samples.','Useful complementary visible structure is distinct from a 3D reconstruction.']})

p=argparse.ArgumentParser();p.add_argument('stage',choices=['freeze','inspect']);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
(freeze if a.stage=='freeze' else inspect)(a.run,a.out)
