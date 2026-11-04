"""Complete SR review under the preexisting HDR transform and frozen native ROIs.

No RAW/engine work. Freeze reads reference JSON only; rendering requires the root
mechanics receipt for candidates and never fits any parameter to candidate pixels.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import argparse,copy,importlib.util,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('review',R/'experiments/multi-stack-2026-10-28/challenge/prepare-review.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
load=lambda p:json.loads(p.read_text())
FROZEN=Path(__file__).with_name('sr-full-review-frozen.json')
TRANSFORM=R/'experiments/multi-stack-2026-10-28/review/hdr-physical-reference-transform.json'
ROIS=R/'experiments/multi-stack-2026-10-28/review/hdr-roi-mapped-frozen.json'
NATIVE=R/'outputs/multi-stack/completion/sr-chart-native-14c'
PRIOR=R/'outputs/multi-stack/completion/sr-chart-constant-02/report.json'

def freeze():
    reference=R/'outputs/multi-stack/slide-hdr-pair-6'
    n=load(NATIVE/'render-report.json'); a=load(NATIVE/'alignment.json')
    assert n['canvas']==load(reference/'render-report.json')['canvas']==[26,17,3464,2310]
    assert a['warpmap']==load(reference/'alignment.json')['warpmap']
    prior=load(PRIOR)
    assert prior['warpmap_sha256']==a['warpmap_sha256']
    old_input=Path(prior['input_render'])
    if not old_input.is_absolute():old_input=R/old_input
    assert load(old_input/'alignment.json')['warpmap']==a['warpmap']
    ox,oy,w,hh=prior['roi_sensor'];assert [ox,oy,w,hh]==[4105,3245,192,192]
    rois=[]
    for q in load(ROIS)['rois']:
        rois.append({'name':q['name'],'origin':q['origins']['shared-hdr-gauge'],'size':q['size'],'selection':q['selection']})
    assert len(rois)==12
    rois.append({'name':'prior-physical-dot-roi','origin':[ox-2*n['canvas'][0],oy-2*n['canvas'][1]],'size':w,
        'selection':'Previously reviewed original chart192 ROI; exact saved warp gauge, integer crop offset only. No new image fit.'})
    h.write_json(FROZEN,{'schema':'strehl.full-sr-independent-review-freeze.v1',
        'scope':'Twelve previously frozen HDR384 witnesses plus prior chart192 dot ROI. Complete images required; resized overviews orientation only.',
        'native_reference':str(NATIVE),'reference_canvas':n['canvas'],'reference_warpmap_sha256':a['warpmap_sha256'],
        'transform':load(TRANSFORM),'transform_sha256':h.digest(TRANSFORM),'hdr_rois_sha256':h.digest(ROIS),
        'prior_dot_report_sha256':h.digest(PRIOR),'prior_dot_full_sensor':[ox,oy,w,hh],
        'rois':rois,'candidate_pixels_used_for_selection':False,
        'negative_reading':'Unsupported pixels must remain exact native. More contrast or changed supported pixels alone cannot establish detail or noise improvement.',
        'optional_boundary_rule':'Only if needed, add first raster-order transition and maximal mixed 384-window at stride192 (ties raster-order), selected solely from support; label diagnostic and retain all13 frozen witnesses.'})
    print(json.dumps({'freeze':str(FROZEN),'witnesses':len(rois),'dot_origin':rois[-1]['origin']}))

def render(args):
    frozen=load(FROZEN);assert h.digest(TRANSFORM)==frozen['transform_sha256']
    source=args.source.resolve();native=source==NATIVE.resolve()
    report=load(source/'render-report.json');nr=load(NATIVE/'render-report.json')
    assert (source/'completed.json').is_file()
    assert report['canvas']==nr['canvas']==frozen['reference_canvas']
    assert load(source/'alignment.json')['warpmap']==load(NATIVE/'alignment.json')['warpmap']
    assert h.digest(source/'source-identities.json')==h.digest(NATIVE/'source-identities.json')
    mechanics=None
    if not native:
        assert args.mechanics is not None,'Candidate requires completed root mechanics receipt'
        mechanics=load(args.mechanics)
        assert Path(mechanics['candidate']).resolve()==source
        assert mechanics['maps_and_tiles_bound'] and mechanics['sources_and_saved_warp_identical']
        for name in ('master.tiff','photograph.tiff'):
            v=mechanics['files'][name]
            assert v['all_pixels_finite'] and v['native_fallback_pixel_bits_identical']
            assert h.digest(source/name)==v['sha256']
    rois=[dict(q,origins={args.label:q['origin']}) for q in frozen['rois']]
    h.render(source/'master.tiff',args.destination,TRANSFORM,args.label,rois=rois)
    support_receipts=[]
    if not native:
        import numpy as np
        from PIL import Image
        support=h.tifffile.memmap(source/'reconstruction/support.tiff',mode='r')
        for q in frozen['rois']:
            x,y=q['origin'];s=q['size'];mask=np.asarray(support[y:y+s,x:x+s])
            assert mask.shape==(s,s) and np.isin(mask,[0,1]).all()
            path=args.destination/f"support-{q['name']}.png"
            Image.fromarray((mask*255).astype(np.uint8)).save(path)
            support_receipts.append({'name':q['name'],'origin':q['origin'],'size':s,'supported_pixels':int(mask.sum()),'total_pixels':s*s,'sha256':h.digest(path)})
    h.write_json(args.destination/'comparison-binding.json',{'freeze_sha256':h.digest(FROZEN),'same_warpmap':True,'same_canvas':report['canvas'],
        'same_source_identities':True,'mechanics_receipt':str(args.mechanics) if args.mechanics else None,
        'mechanics_sha256':h.digest(args.mechanics) if args.mechanics else None,'source':str(source),'source_report_sha256':h.digest(source/'render-report.json'),
        'reconstruction':report.get('reconstruction'),'support_per_witness':support_receipts})

def boards(args):
    from PIL import Image,ImageDraw
    args.destination.mkdir(parents=True,exist_ok=False)
    receipts=[]
    for q in load(FROZEN)['rois']:
        size=q['size'];board=Image.new('RGB',(2*size+24,size+32),(30,30,30));draw=ImageDraw.Draw(board);images=[]
        for k,(label,directory) in enumerate((('Native',args.native),(args.label,args.candidate))):
            p=directory/f"native-{q['name']}.png";im=Image.open(p).convert('RGB');assert im.size==(size,size)
            x=8+k*(size+8);y=24;board.paste(im,(x,y));draw.text((x,5),label,fill='white')
            assert board.crop((x,y,x+size,y+size)).tobytes()==im.tobytes()
            images.append({'label':label,'file':str(p),'sha256':h.digest(p),'paste_origin':[x,y]})
        p=args.destination/f"{q['name']}.png";board.save(p)
        receipts.append({'name':q['name'],'size':list(board.size),'sha256':h.digest(p),'images':images})
    h.write_json(args.destination/'layout.json',{'resampling':False,'boards':receipts,'freeze_sha256':h.digest(FROZEN)})
    print(json.dumps({'boards':len(receipts),'destination':str(args.destination)}))

p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
sub.add_parser('freeze')
a=sub.add_parser('render');a.add_argument('--source',type=Path,required=True);a.add_argument('--destination',type=Path,required=True);a.add_argument('--label',required=True);a.add_argument('--mechanics',type=Path)
a=sub.add_parser('boards');a.add_argument('--native',type=Path,required=True);a.add_argument('--candidate',type=Path,required=True);a.add_argument('--destination',type=Path,required=True);a.add_argument('--label',required=True)
args=p.parse_args()
if args.mode=='freeze':freeze()
elif args.mode=='render':render(args)
else:boards(args)
