"""Bind complete numeric-fix outputs and localize changes; not a quality metric."""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
import tifffile

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def cache(meta):
    m=read(meta);p=meta.parent/m['binary']
    assert sha(p)==m['binary_sha256'] and p.stat().st_size==m['binary_bytes']
    a=np.memmap(p,dtype='<f4',mode='r',shape=(4,m['crop'][3],m['crop'][2]))
    assert np.isfinite(a).all()
    return m,a
def box(mask):
    y,x=np.nonzero(mask)
    return [int(x.min()),int(y.min()),int(x.max()-x.min()+1),int(y.max()-y.min()+1)] if x.size else None

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run=a.run.resolve();out=a.out.resolve()
    assert out.is_relative_to(Path(__file__).resolve().parent) and not out.exists()
    cfg=read(run/'config.json');new=read(run/'output/receipt.json')
    oldp=Path(cfg['historical']['receipt']);assert sha(oldp)==cfg['historical']['sha256'];old=read(oldp)
    assert new['plan']==old['plan'] and new['threads']==old['threads']==8
    assert new['held_source_evidence_exact'] and new['historical_cache_replay_exact']
    oldmeta=Path(old['baseline_cache']['path']);newmeta=run/'output/candidate-cache.json'
    assert sha(oldmeta)==old['baseline_cache']['sha256'] and sha(newmeta)==new['candidate_cache']['sha256']
    om,ov=cache(oldmeta);nm,nv=cache(newmeta)
    assert om['crop']==nm['crop'] and om['frames']==nm['frames']
    census=read(run/'census.json');assert all(not any(x['scan'][k] for k in ('nan','positive_infinity','negative_infinity')) for x in census if 'scan' in x)
    rows=[]
    for c in range(4):
        changed=ov[c].view('u4')!=nv[c].view('u4')
        rows.append(dict(plane=c,changed=int(changed.sum()),quad_bbox=box(changed),max_abs_dn=float(np.abs(nv[c]-ov[c]).max())))
    with tifffile.TiffFile(cfg['expected_baseline']) as f: op=f.asarray();oi=bytes(f.pages[0].tags[34675].value)
    with tifffile.TiffFile(run/'output/candidate.tiff') as f: npix=f.asarray();ni=bytes(f.pages[0].tags[34675].value)
    assert op.shape==npix.shape and op.dtype==npix.dtype==np.uint16 and oi==ni
    rgb_changed=np.any(op!=npix,axis=2)
    out.mkdir()
    (out/'comparison.json').write_text(json.dumps(dict(
        scope='Exact state checks and change localization; a smaller/larger change count is not an image-quality score.',
        candidate_receipt_sha256=sha(run/'output/receipt.json'),historical_receipt_sha256=sha(oldp),
        plan_and_threads_exact=True,held_source_evidence_exact=True,all_finish_values_finite=True,
        plane_changes=rows,native_dimensions=[op.shape[1],op.shape[0]],
        changed_rgb_pixels=int(rgb_changed.sum()),native_rgb_bbox=box(rgb_changed),icc_exact=True),indent=2)+'\n')
    print(json.dumps(dict(plane_changes=rows,changed_rgb_pixels=int(rgb_changed.sum()))))

if __name__=='__main__':main()
