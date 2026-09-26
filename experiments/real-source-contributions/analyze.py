"""Offline numerical attribution of immutable actual-consumer records; no RAW reads."""
from pathlib import Path
import argparse, json, hashlib
import numpy as np

GROUPS=((0,79),(80,168),(169,319),(320,400),(401,487))

def read(p): return json.loads(p.read_text(encoding='utf-8'))
def ref(p): return dict(path=str(p.resolve()), bytes=p.stat().st_size, sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest())
def save(p,value):
    with p.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

def taps(x,n):
    c=x//2
    return ((max(0,c-1),.125),(c,.75),(min(n-1,c+1),.125)) if x%2==0 else ((c,.5),(min(n-1,c+1),.5))

def expansion_matrices(sizes,nodes,sites):
    """Analytic positive footprint for linear attribution, separate from f32 collapse."""
    indices=[{int(j):q for q,j in enumerate(v)} for v in nodes]
    a=np.zeros((len(sites),len(nodes[0])),dtype=np.float64)
    for s,(x,y) in enumerate(sites): a[s,indices[0][y*sizes[0][0]+x]]=1
    matrices=[a]
    for k in range(1,len(sizes)):
        a=np.zeros((len(sites),len(nodes[k])),dtype=np.float64)
        for q,j in enumerate(nodes[k-1]):
            x,y=int(j)%sizes[k-1][0],int(j)//sizes[k-1][0]
            for yy,wy in taps(y,sizes[k][1]):
                for xx,wx in taps(x,sizes[k][0]):
                    a[:,indices[k][yy*sizes[k][0]+xx]]+=matrices[-1][:,q]*(wx*wy)
        assert np.array_equal(a.sum(axis=1),np.ones(len(sites)))
        matrices.append(a)
    return matrices

def contrast(values):
    """Last axes are 25 sites,4 CFA planes, or 25 scalar sites."""
    if values.shape[-1]==25:
        v=values.reshape(*values.shape[:-1],5,5)
        return v[...,2]-.5*(v[...,0]+v[...,4])
    assert values.shape[-2:]==(25,4)
    v=values.reshape(*values.shape[:-2],5,5,4)
    return v[...,2,:]-.5*(v[...,0,:]+v[...,4,:])

def analyze(run,out):
    layout=read(run/'layout.json');receipt=read(run/'receipt.json')
    plan_path=Path(__file__).with_name('independent-plan.json');plan=read(plan_path)
    expected_sites=[]
    expected_lines=[]
    for p in plan['profiles']:
        axis=0 if p['axis']=='x' else 1
        expected_lines.append(dict(name=p['name'],centre=p['centre_native'],axis=axis))
        for offset in plan['offsets_native']:
            point=list(p['centre_native']);point[axis]+=offset
            assert all(v%2==0 for v in point)
            expected_sites.append([v//2 for v in point])
    assert layout['quad_sites']==expected_sites and layout['native_lines']==expected_lines
    assert layout['native_offsets']==plan['offsets_native']
    assert layout['temporal_groups_inclusive']==plan['source_bins_inclusive']
    assert layout['schema']==receipt['schema']==1 and layout['count']==receipt['sources']==488
    assert layout['per_chunk']==122 and layout['numerator_scale']==65536
    assert all(receipt[k] for k in ('all_sampled_chunk_accumulators_bit_exact','all_final_accumulators_bit_exact','all_sampled_final_cfa_bit_exact'))
    sizes,nodes,sites=layout['sizes'],layout['nodes'],layout['quad_sites']
    assert len(sizes)==8 and len(sites)==25 and sizes[0]==[3134,2088]
    assert layout['temporal_groups_inclusive']==[list(g) for g in GROUPS]
    record=layout['source_record_floats'];frames=layout['count']
    raw=np.memmap(run/'sources.f32',dtype='<f4',mode='r')
    assert raw.size==frames*record
    raw=raw.reshape(frames,record);assert np.isfinite(raw).all()
    states=np.fromfile(run/'final-states.f32',dtype='<f4').reshape(-1,13)
    assert states.shape==(sum(map(len,nodes)),13) and np.isfinite(states).all()
    gathered=raw[:,:100].reshape(frames,25,4).astype(np.float64)
    matrices=expansion_matrices(sizes,nodes,sites)
    contribution=np.empty((frames,8,25,4),dtype=np.float64)
    share=np.empty((frames,8,25),dtype=np.float64)
    fallback=[];cursor=100;pos=0
    canonical_error=[]
    for k,indices in enumerate(nodes):
        n=len(indices);data=raw[:,cursor:cursor+7*n].reshape(frames,n,7);cursor+=7*n
        state=states[pos:pos+n];pos+=n
        weights=data[:,:,0].astype(np.float64);coeff=data[:,:,3:7].astype(np.float64)
        denominator=state[:,0].astype(np.float64);live=denominator>0
        normalized=np.full_like(weights,1/frames)
        normalized[:,live]=weights[:,live]/denominator[live]
        assert (weights>=0).all() and (denominator>=0).all()
        if k==7: assert not live.any() and np.all(data[:,:,:3]==0)
        share[:,k,:]=normalized@matrices[k].T
        for c in range(4): contribution[:,k,:,c]=(normalized*coeff[:,:,c])@matrices[k].T
        # Source attribution uses f64 real-valued normalized products. The
        # separately recorded actual f32 chunk/finish path is the numerical truth.
        restored=np.sum(normalized[:,:,None]*coeff,axis=0)
        canonical_error.append(float(np.max(np.abs(restored-state[:,9:13]))))
        fallback.append(dict(band=k,node_count=n,zero_denominator_nodes=int((~live).sum()),
                             role='terminal mean base' if k==7 else 'AC'))
    assert cursor==record and pos==states.shape[0]
    assert [v['quad'] for v in receipt['sites']]==sites
    pre=np.array([v['pre_hull_bits'] for v in receipt['sites']],dtype='<u4').view('<f4').astype(np.float64)
    post=np.array([v['post_hull_bits'] for v in receipt['sites']],dtype='<u4').view('<f4').astype(np.float64)
    bounds=np.array([v['bounds'] for v in receipt['sites']],dtype='<f4').astype(np.float64)
    assert np.array_equal(np.clip(pre,bounds[:,:,0],bounds[:,:,1]),post)
    reconstructed=contribution.sum(axis=(0,1))
    arithmetic_residual=pre-reconstructed;clamp_residual=post-pre
    maximum=float(np.abs(arithmetic_residual).max())
    assert maximum<=.02, f'f64 attribution does not account for actual pre-hull CFA within0.02 DN: {maximum}'
    profiles=contrast(contribution);source_profiles=contrast(gathered)
    fixed_sources=[]
    for label,index in plan['prescribed_sources'].items():
        fixed_sources.append(dict(label=label,index=index,
            gathered_profiles_dn=gathered[index].reshape(5,5,4).tolist(),
            signed_contrasts_dn=source_profiles[index].tolist()))
    records=[]
    for a,b in GROUPS:
        for k in range(8):
            for line,name in enumerate(layout['native_lines']):
                records.append(dict(group_inclusive=[a,b],source_count=b-a+1,band=k,
                    role='terminal mean base' if k==7 else 'AC',line=name['name'],
                    signed_contrast_dn=profiles[a:b+1,k,line,:].sum(axis=0).tolist(),
                    absolute_source_contrast_dn=np.abs(profiles[a:b+1,k,line,:]).sum(axis=0).tolist(),
                    signed_site_radiance_dn=contribution[a:b+1,k,line*5:(line+1)*5,:].sum(axis=0).tolist(),
                    normalized_denominator_share_by_site=share[a:b+1,k,line*5:(line+1)*5].sum(axis=0).tolist()))
    out.mkdir(exist_ok=False)
    np.savez(out/'source-contributions.npz',contribution=contribution,normalized_share=share,
        gathered=gathered,source_contrast=source_profiles,contribution_contrast=profiles,
        arithmetic_residual=arithmetic_residual,clamp_residual=clamp_residual)
    save(out/'attribution.json',dict(schema=1,independent_plan=ref(plan_path),inputs=[ref(run/n) for n in ('layout.json','receipt.json','sources.f32','final-states.f32')],
        max_f64_to_actual_pre_hull_error_dn=maximum,max_resolved_coefficient_error_by_band_dn=canonical_error,
        actual_pre_hull_profiles_dn=contrast(pre).tolist(),actual_post_hull_profiles_dn=contrast(post).tolist(),
        arithmetic_residual_profiles_dn=contrast(arithmetic_residual).tolist(),
        clamp_residual_profiles_dn=contrast(clamp_residual).tolist(),bands=fallback,temporal=records,
        fixed_source_witnesses=fixed_sources,
        actual_post_hull_five_point_profiles_dn=post.reshape(5,5,4).tolist(),
        total_signed_contrast_by_band_dn=profiles.sum(axis=0).tolist(),
        source_profiles_dn=source_profiles.tolist(),
        metric_failure_directions={
            'signed_contrast':'Noise, miscentering, nearby structures or a wrongly chosen line can change it; no ground truth or sharpness score.',
            'absolute_source_contrast':'Large cancelling opposite contributions can inflate it; not quality or a fraction of signed signal.',
            'denominator_share':'Weights choose source influence, not true physical ownership; fallback shares are1/488.',
            'f64_accounting':'Rejects missing numerical contributions only, not bad source/geometry/quality choices.'},
        scope='Frozen actual CFA profiles before demosaic/development, not an RGB quality or flat-noise measurement.'))
    print(json.dumps(dict(sources=frames,sites=len(sites),max_f64_to_actual_pre_hull_error_dn=maximum,
        attribution=str((out/'attribution.json').resolve()))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--trace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();analyze(a.trace.resolve(),a.out.resolve())
