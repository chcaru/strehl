"""Bounded fixed-display review of complete diversity Layers; no RAW access."""
from pathlib import Path
import argparse, importlib.util, json, math, time, hashlib
import numpy as np
import tifffile
from PIL import Image
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review_helper',HERE.parents[1]/'challenge'/'prepare-review.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def prepare(run,out,protocol,key):
    assert (run/'completed.json').is_file()
    out.mkdir(parents=True,exist_ok=False)
    source=run/'layer-01/master.tiff'
    with tifffile.TiffFile(source) as t:
        page=t.pages[0]; height,width,_=page.shape
        baseline=json.loads(page.description.split('DisplayBaseline: ',1)[1])
    with tifffile.TiffFile(run/'layer-01/photograph.tiff') as t: icc=t.pages[0].tags[34675].value
    (out/'display-srgb.icc').write_bytes(icc)
    h.write_json(out/'fixed-transform.json',{'schema':'strehl.independent-review-transform.v1','parameter_source':str(source.resolve()),'parameter_source_sha256':h.digest(source),'display_baseline':baseline,'display_icc_file':'display-srgb.icc','display_icc_sha256':h.digest(out/'display-srgb.icc'),'policy':'Frozen from first-layer metadata only before opening second-layer pixels.'})
    rois=[]
    for r in load(protocol)['runs'][key]['witnesses_normalized']:
        u,v=r['center_uv'];x=max(0,min(width-384,math.floor(u*width-192+.5)));y=max(0,min(height-384,math.floor(v*height-192+.5)))
        rois.append({'name':r['name'],'size':384,'origins':{'layer-01':[x,y],'layer-02':[x,y]},'predeclared_center_uv':[u,v]})
    h.write_json(out/'roi-frozen.json',rois)
    h.write_json(out/'pre-second-layer-freeze.json',{'time_unix':time.time(),'protocol_sha256':h.digest(protocol),'transform_sha256':h.digest(out/'fixed-transform.json'),'roi_sha256':h.digest(out/'roi-frozen.json'),'dimensions':[width,height],'policy':'Integer rounding/clamping of predeclared normalized centers. No image fitting or second-layer pixel access. Native crops remain exact384 samples.'})
    h.commission_viewer(out)
    h.render(source,out/'layer-01',out/'fixed-transform.json','layer-01',compare=run/'layer-01/photograph.tiff',rois=rois)

def readback(path):
    with tifffile.TiffFile(path) as t: a=t.pages[0].asarray()
    b=tifffile.memmap(path,mode='r'); sha=hashlib.sha256(); lo=float('inf');hi=float('-inf');zeros=0
    assert a.dtype==np.float32 and a.ndim==3 and a.shape[2]==3
    for y in range(0,len(a),128):
        s=a[y:y+128];assert np.isfinite(s).all() and np.array_equal(s.view(np.uint32),b[y:y+128].view(np.uint32))
        sha.update(s.tobytes());lo=min(lo,float(s.min()));hi=max(hi,float(s.max()));zeros+=int(np.count_nonzero(np.all(s==0,axis=2)))
    return {'shape':list(a.shape),'file_sha256':h.digest(path),'pixel_sha256':sha.hexdigest(),'full_decode_equals_mapped_bits':True,'all_finite':True,'minimum':lo,'maximum':hi,'zero_rgb_pixels':zeros}

def finish(run,out):
    rois=load(out/'roi-frozen.json');freeze=load(out/'pre-second-layer-freeze.json');assert freeze['roi_sha256']==h.digest(out/'roi-frozen.json') and freeze['transform_sha256']==h.digest(out/'fixed-transform.json')
    h.render(run/'layer-02/master.tiff',out/'layer-02',out/'fixed-transform.json','layer-02',rois=rois)
    reports=[load(run/f'layer-{i:02}/render-report.json') for i in [1,2]]
    assert reports[0]['canvas']==reports[1]['canvas'] and reports[0]['recipe']==reports[1]['recipe']
    session=load(run/'session.json'); completed=load(run/'completed.json');assert completed['outputs']==2
    evidence=[]
    for i,report in enumerate(reports):
        prefix=f'layer-{i+1:02}';expected=list(range(session['passes'][i]['global_range']['start'],session['passes'][i]['global_range']['end']))
        assert [f['frame'] for f in report['frames']]==expected
        assert all(f['pass']==i and f['photometric_gain']==1 for f in report['frames'])
        assert report['mode']=='layers' and report['layer_pass']==i and report['invalid_output_pixels']==0
        rb=readback(run/prefix/'master.tiff');_,_,w,hg=report['canvas'];assert rb['shape']==[2*hg,2*w,3]
        evidence.append({'layer':i,'name':session['passes'][i]['name'],'frames':len(expected),'canvas':report['canvas'],'recipe':report['recipe'],'all_original_pass_sources_only':True,'master':rb})
        for name,sha in load(run/prefix/'render-completion.json')['files'].items(): assert h.digest(run/prefix/name)==sha
        assert h.digest(run/prefix/'render-completion.json')==completed['render_bindings'][prefix+'/render-completion.json']
    # Frozen native-pixel boards: 384px images copied without any resampling.
    for roi in rois:
        board=Image.new('RGB',(768,384))
        for i in [1,2]:
            im=Image.open(out/f'layer-{i:02}'/f"native-{roi['name']}.png");assert im.size==(384,384);board.paste(im,((i-1)*384,0))
        board.save(out/f"pair-{roi['name']}.png",icc_profile=(out/'display-srgb.icc').read_bytes())
    h.write_json(out/'artifact-audit.json',{'schema':'strehl.diversity-review.v1','script_sha256':h.digest(__file__),'helper_sha256':h.digest(h.__file__),'layers':evidence,'metadata_sha256':{n:h.digest(run/n) for n in ['session.json','source-identities.json','alignment.json','completed.json','calibration.json']},'limits':['Identical output gauge is not independent registration truth.','Per-pass white balance/exposure and focus spans differ; these are useful appearance/aperture choices, not isolated physical parameter measurements.','Overviews are orientation only; native witnesses are exact384 slices.']})

p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','finish']);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--key',choices=['razor-aperture','appearance']);a=p.parse_args()
if a.stage=='prepare':prepare(a.run,a.out,HERE/'diversity-protocol-frozen.json',a.key)
else:finish(a.run,a.out)
