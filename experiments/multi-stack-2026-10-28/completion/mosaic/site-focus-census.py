"""Bound-guide focus/source census at already frozen native nomination points."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import sys
import numpy as np

p=argparse.ArgumentParser()
p.add_argument('sites',type=Path)
p.add_argument('--guides',required=True,type=Path)
p.add_argument('--pass-lengths',required=True,nargs=2,type=int)
p.add_argument('--out',required=True,type=Path)
a=p.parse_args()
receipt=json.loads((a.guides/'receipt.json').read_text())
guides=[]
hashes=[]
dtype=np.dtype([('intensity','<f4'),('covered','u1'),('usable','u1'),('sources','<u8',(4,)),('ordinal','<f4'),('width','<f4')])
assert dtype.itemsize==46
for pass_ in range(2):
    data=(a.guides/f'guide-{pass_}.bin').read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    assert digest==receipt['passes'][pass_]['compact_guide_sha256']
    assert data[:8]==b'STRHGUI1'
    length=struct.unpack('<I',data[8:12])[0]
    header=json.loads(data[12:12+length])
    assert header['schema']=='strehl.cached-mosaic-guide.v1' and header['record_bytes']==46
    r=header['receipt'];w,h=r['guide_geometry']
    assert r['pass']==pass_ and len(data)==12+length+46*w*h
    values=np.frombuffer(data[12+length:],dtype=dtype).reshape(h,w)
    guides.append((r,values));hashes.append(digest)

def query(pass_,point,source):
    r,values=guides[pass_]
    xy=np.floor((np.array(point)-r['origin_quad_pixels'])/r['step_quad_pixels']+.5).astype(int)
    assert 0<=xy[0]<values.shape[1] and 0<=xy[1]<values.shape[0]
    v=values[xy[1],xy[0]]
    start=sum(a.pass_lengths[:pass_]);end=start+a.pass_lengths[pass_]
    assert start<=source<end
    original_ids=[int(s) for s in v['sources'] if s!=np.iinfo(np.uint64).max]
    assert all(start<=s<end for s in original_ids)
    finite=lambda x:float(x) if np.isfinite(x) else None
    return dict(guide_xy=xy.tolist(),covered=bool(v['covered']),usable=bool(v['usable']),
                source_in_top4=source in original_ids,top4=original_ids,
                ordinal=finite(v['ordinal']),width=finite(v['width']),original_ordinal=source-start)

data=json.loads(a.sites.read_text());rows=[]
for item in data['records']:
    c=item['receipt']['candidate']
    rows.append(dict(id=c['id'],role=c['role'],focus=[query(0,c['point_a_quad'],c['source_a']),query(1,c['point_b_quad'],c['source_b'])]))
summary={}
for role in ('fit','heldout'):
    selected=[r for r in rows if r['role']==role]
    summary[role]=dict(count=len(selected),both_usable=sum(all(f['usable'] for f in r['focus']) for r in selected),
                       both_originals_in_top4=sum(all(f['source_in_top4'] for f in r['focus']) for r in selected))
result=dict(schema='strehl.saved-site-focus-census.v1',command=sys.argv,
            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            sites_sha256=hashlib.sha256(a.sites.read_bytes()).hexdigest(),compact_guide_sha256=hashes,
            pass_lengths=a.pass_lengths,summary=summary,sites=rows,
            scope='Census at frozen original nomination coordinates, before any refined-coordinate lookup; no new source read, measurement acceptance or physical depth claim.')
with a.out.open('x') as f:
    json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(summary,indent=2))
