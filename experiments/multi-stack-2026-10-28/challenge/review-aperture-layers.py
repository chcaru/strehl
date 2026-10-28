"""Bounded independent aperture Layers artifact review; TIFF and JSON only."""
from __future__ import annotations
import argparse, importlib.util, json, hashlib, platform, sys, time
from pathlib import Path
import numpy as np
from PIL import Image
import tifffile

ROOT = Path('outputs/multi-stack/fabric-aperture-layers-6')
OUT = Path('outputs/multi-stack/fabric-aperture-layers-6-review')
spec = importlib.util.spec_from_file_location('fixed_review', Path(__file__).with_name('prepare-review.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def master_readback(path):
    """Independent complete TIFF decode compared with uncompressed mapped samples."""
    with tifffile.TiffFile(path) as tf:
        assert len(tf.pages) == 1
        page = tf.pages[0]
        a = page.asarray()
        tags = {str(k):str(page.tags[k].value) for k in [256,257,258,259,262,277,284,339] if k in page.tags}
        desc = page.description
    mapped = tifffile.memmap(path, mode='r')
    assert a.dtype == np.float32 and a.ndim == 3 and a.shape[2] == 3
    assert np.isfinite(a).all()
    h = hashlib.sha256(); minimum = float('inf'); maximum = float('-inf')
    zero_rgb = 0
    for y in range(0,len(a),128):
        s = a[y:y+128]
        assert np.array_equal(s.view(np.uint32), mapped[y:y+128].view(np.uint32))
        h.update(s.tobytes()); minimum=min(minimum,float(s.min())); maximum=max(maximum,float(s.max()))
        zero_rgb += int(np.count_nonzero(np.all(s==0,axis=2)))
    return {'path':str(path.resolve()),'file_sha256':helper.digest(path),'pixel_sha256':h.hexdigest(),
            'shape':list(a.shape),'dtype':str(a.dtype),'all_finite':True,'complete_decode_equals_map_bits':True,
            'minimum':minimum,'maximum':maximum,'zero_rgb_pixels':zero_rgb,'tags':tags,'description':desc}


def prepare():
    OUT.mkdir(parents=True,exist_ok=False)
    master = ROOT/'layer-01/master.tiff'
    with tifffile.TiffFile(master) as tf:
        baseline = json.loads(tf.pages[0].description.split('DisplayBaseline: ',1)[1])
    with tifffile.TiffFile(ROOT/'layer-01/photograph.tiff') as tf:
        icc=tf.pages[0].tags[34675].value
    (OUT/'display-srgb.icc').write_bytes(icc)
    helper.write_json(OUT/'fixed-transform.json',{
        'schema':'strehl.independent-review-transform.v1','parameter_source':str(master.resolve()),
        'parameter_source_sha256':helper.digest(master),'display_baseline':baseline,
        'display_icc_file':'display-srgb.icc','display_icc_sha256':helper.digest(OUT/'display-srgb.icc'),
        'policy':'Frozen from layer-01 only before reading layer-02 pixels; no per-layer display fit.'})
    helper.commission_viewer(OUT)
    helper.render(master,OUT/'layer-01',OUT/'fixed-transform.json','layer-01',compare=ROOT/'layer-01/photograph.tiff')
    helper.write_json(OUT/'layer-01/master-readback.json', master_readback(master))
    print('Layer-01 only inspected numerically. Layer-02 pixels not opened.')


def finish():
    roi_path=OUT/'roi-frozen.json'
    rois=json.loads(roi_path.read_text())
    assert len(rois)>=6
    for r in rois:
        assert r['origins']['layer-01']==r['origins']['layer-02'] and r['size']==384
    transform=json.loads((OUT/'fixed-transform.json').read_text())
    assert transform['parameter_source_sha256']==helper.digest(ROOT/'layer-01/master.tiff')
    helper.write_json(OUT/'pre-layer-02-freeze.json',{'time_unix':time.time(),
        'transform_sha256':helper.digest(OUT/'fixed-transform.json'),'rois_sha256':helper.digest(roi_path),
        'layer-01_readback_sha256':helper.digest(OUT/'layer-01/readback.json'),
        'policy':'Native integer origins fixed using only complete layer-01 overview/locator before any layer-02 pixel access.'})
    icc=(OUT/'display-srgb.icc').read_bytes()
    a=tifffile.memmap(ROOT/'layer-01/master.tiff',mode='r')
    helper.write_json(OUT/'layer-01/crops-readback.json',helper.emit_crops(a,OUT/'layer-01',transform['display_baseline'],icc,rois,'layer-01'))
    del a
    helper.render(ROOT/'layer-02/master.tiff',OUT/'layer-02',OUT/'fixed-transform.json','layer-02',rois=rois)
    helper.write_json(OUT/'layer-02/master-readback.json',master_readback(ROOT/'layer-02/master.tiff'))
    s=json.loads((ROOT/'session.json').read_text()); calibration=json.loads((ROOT/'calibration.json').read_text())
    reports=[json.loads((ROOT/f'layer-{i+1:02}/render-report.json').read_text()) for i in range(2)]
    align=json.loads((ROOT/'alignment.json').read_text()); complete=json.loads((ROOT/'completed.json').read_text())
    assert reports[0]['canvas']==reports[1]['canvas']
    assert reports[0]['recipe']==reports[1]['recipe']
    layers=[]
    for i,report in enumerate(reports):
        expected=list(range(s['passes'][i]['global_range']['start'],s['passes'][i]['global_range']['end']))
        assert [f['frame'] for f in report['frames']]==expected
        assert all(f['pass']==i and f['photometric_gain']==1 for f in report['frames'])
        assert report['proposed_groups']==[[x] for x in expected]
        assert report['layer_pass']==i and report['mode']=='layers' and report['invalid_output_pixels']==0
        assert not report['recipe']['grouping_enabled']
        assert all(d['averaged']==0 for d in report['diagnostics'])
        rb=json.loads((OUT/f'layer-{i+1:02}/master-readback.json').read_text())
        _,_,pw,ph=report['canvas']; assert rb['shape']==[ph*2,pw*2,3]
        # Complete fixed-display PNG readback, including every pixel, against mapped linear master.
        master=tifffile.memmap(ROOT/f'layer-{i+1:02}/master.tiff',mode='r')
        shown=np.array(Image.open(OUT/f'layer-{i+1:02}/complete-fixed-display.png'))
        assert list(shown.shape)==rb['shape']
        for y in range(0,len(master),128):
            expected_pixels=helper.encoded8(helper.display(master[y:y+128],transform['display_baseline']))
            assert np.array_equal(shown[y:y+128],expected_pixels)
        del master,shown
        layers.append({'layer':i,'name':s['passes'][i]['name'],'frame_count':len(expected),
                       'global_range':s['passes'][i]['global_range'],'common_canvas':report['canvas'],
                       'recipe':report['recipe'],'calibration':calibration[i],
                       'clipped_source_observations':sum(f['clipped_pixels'] for f in report['frames']),
                       'per_frame_gains_all_one':True,'own_pass_frames_only':True,
                       'full_png_readback_exact':True,'master_readback':rb})
    summary={'schema':'strehl.independent-layers-review.v1','argv':sys.argv,
        'script_sha256':helper.digest(__file__),'display_helper_sha256':helper.digest(Path(helper.__file__)),
        'python':platform.python_version(),'numpy':np.__version__,'tifffile':tifffile.__version__,
        'completion':complete,'run_receipt':json.loads(Path('outputs/multi-stack/fabric-aperture-layers-6-run/receipt.json').read_text()),
        'metadata_hashes':{n:helper.digest(ROOT/n) for n in ['session.json','calibration.json','alignment.json','source-identities.json','completed.json']},
        'alignment':{k:v for k,v in align['report'].items() if k not in ['edges','focus_candidates']},
        'common_warpmap_sha256':align['warpmap_sha256'],'layers':layers,
        'limits':['No new RAW decode or engine render.', 'No ordinary per-pass baseline: this validates Layers output capability, not nonregression or aperture advantage.',
                  'Identical delivered coordinates do not establish exact correspondence or physical placement truth.',
                  'Per-pass WB and aperture/focus coverage differ; brightness/color differences are not isolated aperture effects.',
                  'Recorded optical calibration was fitted at f5.6/f8, with f11 explicitly untested; f14 is also outside that fit evidence.']}
    helper.write_json(OUT/'artifact-audit.json',summary)
    print(json.dumps({'masters_finite':True,'common_canvas':reports[0]['canvas'],'shape':layers[0]['master_readback']['shape'],
                      'frame_counts':[x['frame_count'] for x in layers],'full_png_readback_exact':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['prepare','finish']); args=p.parse_args()
    (prepare if args.mode=='prepare' else finish)()
