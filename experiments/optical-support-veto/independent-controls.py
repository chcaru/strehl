"""Independent ray ownership, discrete footprint and saved-array quality checks."""
from pathlib import Path
import argparse,json,hashlib,itertools,time
import numpy as np
from scipy.ndimage import gaussian_filter

FOCUS=(1.,.75,.5,.25,0.)
POINTS=((0,48),(15,30),(28,48),(32,48),(40,30),(47,30),(55,48),(59,48),(62,48),(68,30),(95,40),(59,34))
WINDOWS={'outside':[44,20,6,12],'near':[56,40,7,18],'far':[66,20,10,12],'interior':[22,22,52,52]}

def prepare_controls(prep,pupil,tables):
    started=time.perf_counter();y,x=np.mgrid[:96,:96]
    alpha=((x<32)|((x>=58)&(x<61)&(y>=35)&(y<62)))
    assert np.array_equal(prep.scene('opaque')[2],alpha)
    assert pupil.shape==(16384,2) and len(tables)==5
    rows=[]
    for index,(f,table) in enumerate(zip(FOCUS,tables)):
        assert table.metadata['near_shift']==12*(f-1) and table.metadata['far_shift']==12*f
        assert np.all(table.weights>0)
        def taps(amount):
            pos=np.asarray(pupil,dtype=np.float64)*amount;lo=np.floor(pos).astype(int);frac=pos-lo
            offsets=[];positive=[]
            for dy,dx in ((0,0),(0,1),(1,0),(1,1)):
                offsets.append(lo+[dx,dy]);positive.append(((frac[:,0] if dx else 1-frac[:,0])*(frac[:,1] if dy else 1-frac[:,1]))>0)
            return np.stack(offsets,axis=1),np.stack(positive,axis=1)
        p,pw=taps(12*(f-1));q,qw=taps(12*f);cache={}
        def ray_bits(x,y):
            key=(x,y)
            if key in cache:return cache[key]
            pp=p+[x,y];qq=q+[x,y]
            pi=(pp[:,:,0]>=0)&(pp[:,:,0]<96)&(pp[:,:,1]>=0)&(pp[:,:,1]<96)
            qi=(qq[:,:,0]>=0)&(qq[:,:,0]<96)&(qq[:,:,1]>=0)&(qq[:,:,1]<96)
            # Read each ray's actual positive near interpolation sites. A far
            # lookup belongs to that SAME ray only when one near site transmits.
            opaque=np.zeros_like(pi);opaque[pi]=alpha[pp[:,:,1][pi],pp[:,:,0][pi]]
            v=int(np.any(pw&pi&opaque))
            transmitted=np.any(pw&pi&~opaque,axis=1)
            if np.any(transmitted&np.any(qw&qi,axis=1)):v|=2
            if np.any(pw&~pi) or np.any(transmitted&np.any(qw&~qi,axis=1)):v|=4
            cache[key]=v;return v
        observed=prep.support(alpha.astype(np.float32),table,3)
        comparisons=[]
        for x,y in POINTS:
            v=0
            for dy,dx in itertools.product(range(-3,4),repeat=2):
                sx,sy=x+dx,y+dy
                v|=ray_bits(sx,sy) if 0<=sx<96 and 0<=sy<96 else 4
            assert int(observed[y,x])==v,f'same-ray support differs at source{index},site{x,y}'
            comparisons.append(dict(x=x,y=y,bits=v))
        shifted=np.roll(observed,7,axis=1)
        sabotage=sum(int(shifted[r['y'],r['x']])!=r['bits'] for r in comparisons)
        assert sabotage>0,'shifted optical-support sabotage was not detected'
        rows.append(dict(source=index,sites=comparisons,shifted_support_mismatches=sabotage))
    return dict(status='SAME_RAY_SUPPORT_CONTROLS_PASS',seconds=time.perf_counter()-started,
        comparison='Independent continuous-pupil bilinear site ownership, not joint-table offset union',sources=rows)

def axes_reduce(n):return [sorted(set(max(0,min(n-1,2*j+d)) for d in range(-2,3))) for j in range((n+1)//2)]
def axes_expand(n,m):
    return [sorted(set(max(0,min(n-1,j//2+d)) for d in ((-1,0,1) if j%2==0 else (0,1)))) for j in range(m)]
def union(src,xs,ys):
    return np.array([[np.bitwise_or.reduce(src[np.ix_(yy,xx)].ravel()) for xx in xs] for yy in ys],dtype=np.uint8)
def reduced(src):return union(src,axes_reduce(src.shape[1]),axes_reduce(src.shape[0]))
def expanded(src,shape):return union(src,axes_expand(src.shape[1],shape[1]),axes_expand(src.shape[0],shape[0]))
def verify_operator_support(folder,records):
    assert len(records)==4
    checked=[]
    for r in records:
        iw,ih=r['input_size'];ow,oh=r['output_size'];operation=r['operation']
        assert operation in ('reduce','expand') and r['fine_size'] in ([9,11],[32,32])
        actual=load_array(folder/r['file'],(iw*ih,ow*oh),'u1')
        if operation=='reduce':xs,ys=axes_reduce(iw),axes_reduce(ih)
        else:xs,ys=axes_expand(iw,ow),axes_expand(ih,oh)
        assert len(xs)==ow and len(ys)==oh
        expected=np.zeros_like(actual)
        for y,yy in enumerate(ys):
            for x,xx in enumerate(xs):
                for sy,sx in itertools.product(yy,xx):expected[sy*iw+sx,y*ow+x]=1
        assert np.array_equal(actual,expected),'actual discrete operator support differs from independent clamped phase derivation'
        assert not np.array_equal(np.roll(expected,1,axis=0),actual),'shifted operator-support sabotage is inert'
        checked.append(dict(operation=operation,fine_size=r['fine_size'],input_size=r['input_size'],output_size=r['output_size'],exact=True))
    assert {(r['operation'],tuple(r['fine_size'])) for r in checked}=={(op,sz) for op in ('reduce','expand') for sz in ((9,11),(32,32))}
    return checked
def coefficient_q(native,sharp):
    leaf=np.bitwise_or.reduce(native[16:80,16:80].reshape(32,2,32,2).transpose(0,2,1,3).reshape(32,32,4),axis=2)
    g=[leaf,reduced(leaf)];g.append(reduced(g[-1]));out=[]
    for k in (0,1):
        bits=g[k]|expanded(g[k+1],g[k].shape)
        labels=sharp[16:80:2*(2**k),16:80:2*(2**k)]
        out.append((bits==labels).astype(np.uint8))
    return out

def load_array(path,shape,dtype='<f4'):
    a=np.fromfile(path,dtype=dtype);assert a.size==np.prod(shape)
    a=a.reshape(shape);assert np.isfinite(a).all();return a
def region(a,xywh):
    x,y,w,h=xywh;return a[y-16:y-16+h,x-16:x-16+w]
def chroma(a):return np.stack((a[...,0]-a[...,1],a[...,2]-a[...,1]),axis=-1)
def error(a,t):return dict(rgb=float(np.sqrt(np.mean((a-t)**2))),chroma=float(np.sqrt(np.mean((chroma(a)-chroma(t))**2))))
def amplitudes(a,near,far):
    # Spatial channel means are nuisance DC; fit BOTH supplied components jointly.
    def centre(v):return (v-v.mean(axis=(0,1),keepdims=True)).ravel()
    templates=[centre(near),centre(far)];active=[i for i,t in enumerate(templates) if np.linalg.norm(t)>1e-9]
    if not active:return [None,None]
    matrix=np.column_stack([templates[i] for i in active]);assert np.linalg.matrix_rank(matrix)==len(active),'component templates not identifiable'
    coeff=np.linalg.lstsq(matrix,centre(a),rcond=None)[0];out=[None,None]
    for i,c in zip(active,coeff):out[i]=float(c)
    return out
def protected(candidate,current,truth,near,far):
    details=[];passed=True
    for label,component in [('near',0),('far',1)]:
        box=WINDOWS[label];c,b,t,n,f=[region(v,box) for v in (candidate,current,truth,near,far)]
        ce,be=error(c,t),error(b,t);ca,ba=amplitudes(c,n,f),amplitudes(b,n,f)
        amp_ok=ba[component] is not None and ba[component]>0 and .95*ba[component]<=ca[component]<=1.05*ba[component]
        ok=ce['rgb']<=1.05*be['rgb'] and ce['chroma']<=1.05*be['chroma'] and amp_ok
        details.append(dict(region=label,current_error=be,candidate_error=ce,current_amplitudes=ba,candidate_amplitudes=ca,pass_=bool(ok)))
        passed&=ok
    return bool(passed),details

def score(prepared,consumed):
    prepared,consumed=Path(prepared),Path(consumed)
    manifest=json.loads((prepared/'manifest.json').read_text());assert manifest['status']=='PREPARED'
    result=json.loads((consumed/'result.json').read_text());assert result['status']=='CONSUMED'
    assert manifest['independent_preparation_controls']['status']=='SAME_RAY_SUPPORT_CONTROLS_PASS'
    operators=verify_operator_support(consumed,result['operator_support'])
    allrows=[];flat_rms=None;opaque=None
    for name in ('flat','transparent','opaque'):
        folder=prepared/name;out=consumed/name
        truth,near,far=[load_array(folder/f'{p}rgb.f32',(96,96,3))[16:80,16:80] for p in ('truth-','near-truth-','far-truth-')]
        assert np.max(np.abs(truth-near-far))<2e-7,'common-focus components do not sum to truth'
        images={arm:load_array(out/f'{arm}-rgb.f32',(64,64,3)) for arm in ('current','all-one','oracle','permuted','no-clean')}
        current=images['current'];assert np.array_equal(current,images['all-one']),'all-one RGB differs'
        assert (out/'current-cfa.f32').read_bytes()==(out/'all-one-cfa.f32').read_bytes(),'all-one CFA differs'
        assert np.array_equal(current,images['no-clean']),'no-clean fallback RGB differs'
        assert (out/'current-cfa.f32').read_bytes()==(out/'no-clean-cfa.f32').read_bytes(),'no-clean fallback CFA differs'
        qs=[];weights=[]
        sharp=load_array(folder/'sharp-labels.u8',(96,96),'u1')
        for i in range(5):
            expected=coefficient_q(load_array(folder/f'frame-{i}-support.u8',(96,96),'u1'),sharp) if name=='opaque' else [np.ones((32,32),np.uint8),np.ones((16,16),np.uint8)]
            iq=[];iw=[]
            for k,shape in enumerate(((32,32),(16,16))):
                q=load_array(out/f'source-{i}-b{k}-q.u8',shape,'u1');assert np.array_equal(q,expected[k]),'discrete source footprint Q differs'
                w=load_array(out/f'source-{i}-b{k}-weights.f32',shape);assert np.all(w>=0)
                iq.append(q);iw.append(w)
            qs.append(iq);weights.append(iw)
        if name=='flat':
            assert all(np.array_equal(current,v) for v in images.values()),'flat Q treatment changes image'
            flat_rms=float(np.sqrt(np.mean(((current-truth).mean(axis=2))**2)))
            allrows.append(dict(name=name,errors=error(current,truth),luma_rms=flat_rms,null_exact=True));continue
        if name=='transparent':
            assert all(np.array_equal(current,v) for v in images.values()),'legitimate transparent superposition changed'
            allrows.append(dict(name=name,errors=error(current,truth),joint_amplitudes=amplitudes(current,near,far),null_exact=True));continue
        baseline_accepted,baseline_protection=protected(current,current,truth,near,far)
        assert baseline_accepted,'protected component baseline cannot pass its own guard; quality screen uncommissioned'
        exercised=0
        for k,n in enumerate((32,16)):
            q=np.stack([v[k] for v in qs]);w=np.stack([v[k] for v in weights]);bad=np.any((w>0)&(q==0),axis=0);clean=np.any((w>0)&(q!=0),axis=0)
            yy,xx=np.mgrid[:n,:n];xx=16+2*(2**k)*xx;yy=16+2*(2**k)*yy
            live=bad&clean&(xx>=44)&(xx<50)&(yy>=20)&(yy<32);exercised+=int(live.sum())
            assert np.array_equal(live,load_array(out/f'oracle-b{k}-exercised.u8',(n,n),'u1')!=0),'actual positive exercise differs'
        outside=region(current-truth,WINDOWS['outside']);excess=float(outside.mean(axis=2).mean())
        available=exercised>0 and excess>2*flat_rms
        arms=[]
        for arm in ('oracle','permuted'):
            im=images[arm];base_error=error(region(current,WINDOWS['outside']),region(truth,WINDOWS['outside']));candidate_error=error(region(im,WINDOWS['outside']),region(truth,WINDOWS['outside']))
            guard,detail=protected(im,current,truth,near,far)
            improvement=all(candidate_error[k]<base_error[k] for k in ('rgb','chroma'))
            arms.append(dict(arm=arm,outside_current=base_error,outside_candidate=candidate_error,protection=detail,protected=guard,paired_edge_improvement=improvement))
        destroyers={'blur':gaussian_filter(current,sigma=(2.,2.,0.),mode='reflect'),'grey':np.repeat(current.mean(axis=2,keepdims=True),3,axis=2),
                    'overcontrast':current.mean(axis=(0,1),keepdims=True)+1.5*(current-current.mean(axis=(0,1),keepdims=True))}
        destroyed=[]
        for label,im in destroyers.items():
            guard,detail=protected(im,current,truth,near,far);destroyed.append(dict(name=label,protection_rejected=not guard,details=detail))
        commissioned=all(r['protection_rejected'] for r in destroyed)
        admitted=bool(available and commissioned and arms[0]['protected'] and arms[0]['paired_edge_improvement'])
        opaque=dict(name=name,baseline_protection_accepts_current=baseline_accepted,baseline_protection=baseline_protection,
            positive_exercised_coefficients=exercised,outside_luma_excess=excess,twice_flat_luma_rms=2*flat_rms,
            fixture_exercised=bool(available),destroyers=destroyed,protection_commissioned=commissioned,arms=arms,generated_oracle_admitted=admitted)
        allrows.append(opaque)
    return dict(status='GENERATED_ORACLE_PASS' if opaque['generated_oracle_admitted'] else ('UNEXERCISED' if not opaque['fixture_exercised'] else 'GENERATED_ORACLE_REFUSED'),
        scenes=allrows,operator_support_checks=operators,photographic_replay_admitted=False,scope='Fixed generated oracle availability; no RAW, automatic visibility or SOTA claim.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',required=True);p.add_argument('--consumed',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    value=score(a.prepared,a.consumed)
    with Path(a.out).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    print(value['status'])
