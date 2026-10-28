"""Independent fixed spectral controls; root schedules all execution."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
COST_INDICES = [0,108,7848,7956,54,3924,4032,7902,1989,2016,2043,3951,4005,5913,5940,5967]
PHASE = ((0,0),(1,0),(0,1),(1,1))
CHANNEL = (0,1,1,2)
BLACK = 512.
GAIN = (.15,.13,.17,.21)
READ = (9.,8.,11.,13.)
SOURCE_HW = (640,640)
OUTPUT_HW = (64,64)
ORIGIN = (256,256)
LIMIT = 10 << 30
SAMPLES = [(0,0),(0,63),(63,0),(63,63),(16,19),(31,32),(47,44),(32,31)]


def ref(path):
    path = Path(path).resolve()
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''): h.update(block)
    st = path.stat()
    return dict(path=str(path),sha256=h.hexdigest(),bytes=st.st_size,mtime_ns=st.st_mtime_ns)


def bind(value):
    actual = ref(value['path'])
    assert (actual['sha256'],actual['bytes']) == (value['sha256'],value['bytes'])
    return actual


def save(path, value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,allow_nan=False); f.write('\n')


def load_module(path):
    spec=importlib.util.spec_from_file_location('independent_spectral_producer',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def array_file(path, value):
    value.tofile(path)
    return dict(**ref(path),shape=list(value.shape),dtype=str(value.dtype))


def score(np, actual, expected, maximum=.06, rms=.01):
    difference=np.asarray(actual,dtype=np.float64)-np.asarray(expected,dtype=np.float64)
    mx=float(np.max(np.abs(difference))); r=float(np.sqrt(np.mean(difference*difference)))
    return dict(maximum=mx,rms=r,maximum_bar=maximum,rms_bar=rms,
                pass_=bool(np.isfinite(difference).all() and mx<=maximum and r<=rms))


def reflect(np, value, extent):
    a=np.remainder(value,2*(extent-1))
    return np.where(a<extent,a,2*(extent-1)-a).astype(np.int64)


def lattice_reference(np, raw, origins, kind):
    n=256 if kind==1 else 128
    y,x=np.indices((n,n),dtype=np.int64)
    u=x+origins[kind][0]; v=y+origins[kind][1]
    if kind==1: sx,sy=u+v+1,u-v
    else: sx,sy=2*u+(kind==2),2*v+(kind==2)
    sx=reflect(np,sx,raw.shape[1]); sy=reflect(np,sy,raw.shape[0])
    return raw[sy,sx].astype(np.float64)-BLACK, sy*raw.shape[1]+sx


def independent_geometry(np, origins, affine):
    a=np.asarray(affine,dtype=np.float64); axis=np.arange(64)*2
    yy,xx=np.meshgrid(axis,axis,indexing='ij'); lattices=[]; queries=[]
    for ox,oy in origins:
        sx,sy=a[:,:2]@np.array([ox+63.5,oy+63.5])+a[:,2]
        centers=[(sx/2,sy/2),((sx+sy-1)/2,(sx-sy-1)/2),((sx-1)/2,(sy-1)/2)]
        loc=[tuple(int(np.rint(v-(n-1)/2)) for v in center) for center,n in zip(centers,[128,256,128])]
        q=[]
        for phase,(px,py) in enumerate(PHASE):
            rx=ox+xx+px; ry=oy+yy+py
            sx=a[0,0]*rx+a[0,1]*ry+a[0,2]; sy=a[1,0]*rx+a[1,1]*ry+a[1,2]
            kind=(0,1,1,2)[phase]
            if kind==1: u,v=(sx+sy-1)/2,(sx-sy-1)/2
            else: u,v=(sx-(kind==2))/2,(sy-(kind==2))/2
            q.append(np.stack([u-loc[kind][0],v-loc[kind][1]],axis=-1))
        lattices.append(loc); queries.append(q)
    return lattices,np.asarray(queries)


def direct_fourier(np, values, queries, affine, kind, cell=True):
    """Independent f64 DFT evaluation, including split Nyquist representatives."""
    n=values.shape[0]; mean=float(np.mean(values,dtype=np.float64))
    axis=np.arange(n,dtype=np.float64); edge=n//8
    distance=np.minimum(axis,n-1-axis)
    t=np.where(distance<edge,.5-.5*np.cos(np.pi*distance/edge),1.)
    z=np.fft.fft2((values-mean)*(t[:,None]*t[None,:]),norm='ortho')
    k=np.arange(-n//2,n//2+1); split=np.ones(n+1); split[[0,-1]]=.5
    z=z[np.ix_(k%n,k%n)]*split[:,None]*split[None,:]
    v,u=np.meshgrid(k/n,k/n,indexing='ij')
    if kind==1: fx,fy=(u+v)/2,(u-v)/2
    else: fx,fy=u/2,v/2
    if cell:
        a=np.asarray(affine); rx=a[0,0]*fx+a[1,0]*fy; ry=a[0,1]*fx+a[1,1]*fy
        z=z*np.sinc(rx)*np.sinc(ry)/(np.sinc(fx)*np.sinc(fy))
    answer=[]
    for qx,qy in queries:
        ex=np.exp(2j*np.pi*(k/n)*qx); ey=np.exp(2j*np.pi*(k/n)*qy)
        answer.append(float(np.real(ey@z@ex)/n+mean))
    return np.asarray(answer)


def analyse_reference(np, gathered):
    axis=np.arange(64,dtype=np.float64)
    h=np.sin(np.pi*axis/64)**2; s=np.sqrt(h[:,None]*h[None,:])
    means=np.sum(gathered*s,axis=(-2,-1))/s.sum()
    z=np.fft.fft2((gathered-means[...,None,None])*s,norm='ortho')
    z[...,0,0]=0
    return z,means


def ola_reference(np, gathered, origins, width,height,origin):
    axis=np.arange(64,dtype=np.float64); h=np.sin(np.pi*axis/64)**2
    h=h[:,None]*h[None,:]; out=np.zeros((height,width)); cov=np.zeros_like(out)
    for p,(ox,oy) in enumerate(origins):
        for c,(px,py) in enumerate(PHASE):
            xs=ox-origin[0]+px+2*np.arange(64); ys=oy-origin[1]+py+2*np.arange(64)
            ix=np.where((xs>=0)&(xs<width))[0]; iy=np.where((ys>=0)&(ys<height))[0]
            out[np.ix_(ys[iy],xs[ix])]+=gathered[p,c][np.ix_(iy,ix)]*h[np.ix_(iy,ix)]
            cov[np.ix_(ys[iy],xs[ix])]+=h[np.ix_(iy,ix)]
    return np.divide(out,cov,out=np.zeros_like(out),where=cov>0),cov


def mode(amplitudes,fx,fy,phase=0.,depth=0):
    return dict(amplitudes=amplitudes,fx=fx,fy=fy,phase=phase,depth=depth)


def disk_transfer(radius,frequency):
    # 2*J1(2*pi*r*f)/(2*pi*r*f), independent convergent analytic series.
    x=math.pi*radius*frequency
    term=1.; total=1.
    for j in range(1,48):
        term *= -(x*x)/(j*(j+1)); total += term
    return total


def continuous(np, xy, components, focus=None, blur='gaussian', shift=(0.,0.)):
    x,y=xy; output=np.empty((*x.shape,3),dtype=np.float64); output[:]=[2048.,3072.,2560.]
    for m in components:
        f2=m['fx']**2+m['fy']**2
        sigma=0. if focus is None else focus[m['depth']]
        transfer=(math.exp(-2*math.pi**2*sigma*sigma*f2) if blur=='gaussian'
                  else disk_transfer(sigma,math.sqrt(f2)))
        wave=np.cos(2*np.pi*(m['fx']*(x-shift[0])+m['fy']*(y-shift[1]))+m['phase'])
        wave*=np.sinc(m['fx'])*np.sinc(m['fy'])*transfer
        output+=wave[...,None]*np.asarray(m['amplitudes'])
    return output


def acquisition(np, components, focus, seed, blur='gaussian', shift=(0.,0.), noisy=True):
    y,x=np.indices(SOURCE_HW,dtype=np.float64)
    rgb=continuous(np,(x,y),components,focus,blur,shift)
    phase=(2*(y.astype(int)%2)+x.astype(int)%2)
    channel=np.array(CHANNEL)[phase]; raw=np.take_along_axis(rgb,channel[...,None],axis=2)[...,0]+BLACK
    variance=np.array(READ)[phase]+np.array(GAIN)[phase]*np.maximum(raw-BLACK,0.)
    if noisy: raw+=np.random.default_rng(seed).normal(size=raw.shape)*np.sqrt(variance)
    return np.ascontiguousarray(np.clip(np.rint(raw),0,65535).astype(np.uint16))


def develop(np, renderer, development, cfa, directory, origin=ORIGIN):
    directory.mkdir(); raw=directory/'input-cfa.f32le'
    array_file(raw,np.ascontiguousarray(cfa,dtype='<f4'))
    cfg=dict(schema=1,cfa={k:v for k,v in ref(raw).items() if k!='mtime_ns'},width=int(cfa.shape[1]),height=int(cfa.shape[0]),
             active_origin_xy=list(origin),physical_pattern='RGGB',units='black-subtracted-DN',
             development_receipt={k:v for k,v in development.items() if k!='mtime_ns'},out_dir=str(directory/'native'),
             expected_executable_sha256=renderer['sha256'],parity_reference=None)
    save(directory/'config.json',cfg)
    command=[renderer['path'],str(directory/'config.json')]
    p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=40,check=False)
    (directory/'native.log').write_text(p.stdout,encoding='utf-8')
    save(directory/'process.json',dict(command=command,returncode=p.returncode))
    assert p.returncode==0, p.stdout
    receipt=json.loads((directory/'native/receipt.json').read_text())
    assert receipt['status']=='COMPLETE_NATIVE_CFA_DEVELOPMENT' and receipt['signed_cfa_copy_bit_exact']
    assert receipt['pixel_readback_exact'] and receipt['demosaic_stages']==1 and not receipt['quality_claim']
    camera=np.fromfile(receipt['camera_rgb']['path'],dtype='<f4').reshape((*cfa.shape,3))
    meta=json.loads(Path(development['path']).read_text())
    bits=lambda v:np.asarray(v,dtype=np.uint32).view(np.float32)
    black,white=bits(meta['levels_bits']); wb=bits(meta['wb_bits'])
    return receipt,camera.astype(np.float64)*(float(white)-float(black))/wb


def component_scores(np, camera, truth, components, xy):
    bases=[np.ones(camera.shape[:2])]
    for m in components:
        bases.append(np.cos(2*np.pi*(m['fx']*xy[0]+m['fy']*xy[1])+m['phase'])*np.sinc(m['fx'])*np.sinc(m['fy']))
    design=np.stack([v.ravel() for v in bases],axis=1)
    fitted=np.linalg.lstsq(design,camera.reshape(-1,3),rcond=None)[0]
    rows=[]
    for k,m in enumerate(components):
        for c,amp in enumerate(m['amplitudes']):
            value=float(fitted[k+1,c]); bar=max(3.,.10*max(abs(v) for v in m['amplitudes']))
            rows.append(dict(component=k,channel=c,truth_amplitude=amp,measured_amplitude=value,
                             recovery=None if amp==0 else value/amp,false_channel_bar=bar,
                             pass_=bool(abs(value)<=bar) if amp==0 else bool(value/amp>=.80)))
    error=camera-truth
    chroma=error[..., [0,2]]-error[...,1,None]
    return dict(rgb_rmse_dn=float(np.sqrt(np.mean(error*error))),chroma_rmse_dn=float(np.sqrt(np.mean(chroma*chroma))),components=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--renderer-binding',type=Path,required=True)
    parser.add_argument('--development-receipt',type=Path,required=True)
    args=parser.parse_args(); out=args.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter(); report=dict(status='INCOMPLETE_NATIVE_SPECTRAL_CONTROLS',complete=False,
        controls_pass=False,quality_pass=False,quality_claim=False,photographic_admission=False,mechanics={},cases=[])
    inputs=[ref(__file__),ref(HERE/'controls-protocol.md'),ref(HERE/'spectral-operator.py'),
            ref(HERE/'api.md'),ref(HERE/'brief.md'),ref(args.renderer_binding),ref(args.development_receipt)]
    try:
        import numpy as np
        import torch
        torch.set_num_threads(4); torch.set_num_interop_threads(1)
        torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False
        assert not torch.is_autocast_enabled()
        module=load_module(HERE/'spectral-operator.py'); inputs.append(ref(module.LOADER))
        renderer=json.loads(args.renderer_binding.read_text()); renderer=bind(renderer.get('executable',renderer))
        development=ref(args.development_receipt); inputs.append(renderer)
        engine=module.SpectralConsumer(torch,LIMIT); noise=module.Noise(BLACK,GAIN,READ)
        report['runtime_before']=engine.metadata(); report['threads']=dict(cpu=4,interop=1,tf32=False,autocast=False)
        report['source_bindings']=inputs; save(out/'source-bindings.json',inputs)
        identity=[[1.,0.,0.],[0.,1.,0.]]
        origins=module.patch_origins(64,64,ORIGIN)
        fixed=module.patch_origins(6896,4596,(68,46))
        expected=[(68+x,46+y) for y in range(-64,4596,64) for x in range(-64,6896,64)]
        assert fixed==expected and len(fixed)==7957
        report['fixed_cost_population']=[dict(index=i,origin_xy=list(fixed[i])) for i in COST_INDICES]
        # Flats are the first actual consumer outputs, before any detail case.
        all_mechanics=[]; flat_quality=[]
        def case(name,components,focuses,seed,blur='gaussian',shifts=None,noisy=True):
            target=out/name; target.mkdir(); acc=module.Accumulator(engine,len(origins)); gathered=[]; prepared_last=None
            source_rows=[]
            for i,focus in enumerate(focuses):
                shift=(0.,0.) if shifts is None else shifts[i]
                raw=acquisition(np,components,focus,seed+17*i,blur,shift,noisy)
                rawref=array_file(target/f'original-{i}.u16le',raw)
                source=engine.source(raw,i,noise)
                affine=[[1.,0.,shift[0]],[0.,1.,shift[1]]]
                geometry=engine.geometry(origins,affine,SOURCE_HW)
                prepared=engine.prepare_source(source,geometry)
                gathered.append(prepared.gathered.cpu().numpy())
                assert bool(torch.isfinite(prepared.variance).all() and (prepared.variance>=0).all())
                opposite=prepared.coefficients.index_select(-2,engine.opposite).index_select(-1,engine.opposite).conj()
                conjugacy=score(np,torch.view_as_real(prepared.coefficients).cpu().numpy(),torch.view_as_real(opposite.resolve_conj()).cpu().numpy())
                all_mechanics.append(conjugacy['pass_'])
                assert torch.equal(prepared.admission,prepared.admission.index_select(-2,engine.opposite).index_select(-1,engine.opposite))
                acc.add(list(range(len(origins))),prepared)
                source_rows.append(dict(original=rawref,source_id=i,geometry=geometry.evidence,conjugacy=conjugacy))
                prepared_last=prepared
                del source
            finished=acc.finish(); delivered=engine.overlap_add(finished,origins,64,64,ORIGIN)
            direct,cov=ola_reference(np,np.mean(np.stack(gathered).astype(np.float64),axis=0),origins,64,64,ORIGIN)
            uniform=delivered['uniform'].cpu().numpy(); candidate=delivered['candidate'].cpu().numpy()
            null=score(np,uniform,direct); all_mechanics.extend([null['pass_'],delivered['complete_coverage'],bool((cov>0).all())])
            if len(focuses)==1: all_mechanics.append(score(np,candidate,uniform)['pass_'])
            y,x=np.indices((64,64),dtype=np.float64); xy=(x+ORIGIN[0],y+ORIGIN[1]); truth=continuous(np,xy,components)
            truths=array_file(target/'truth-camera-dn.f64le',truth.astype('<f8'))
            arms={}
            for label,value in [('candidate',candidate),('uniform',uniform)]:
                receipt,camera=develop(np,renderer,development,value,target/label)
                arms[label]=dict(development_receipt=ref(target/label/'native/receipt.json'),scores=component_scores(np,camera,truth,components,xy))
            scores=arms['candidate']['scores']; base=arms['uniform']['scores']
            if not components:
                quality=all(scores[k]<=1.15*base[k]+.5 for k in ('rgb_rmse_dn','chroma_rmse_dn')); flat_quality.append(quality)
            else: quality=all(v['pass_'] for v in scores['components'])
            transfers=[[math.exp(-2*math.pi**2*focus[m['depth']]**2*(m['fx']**2+m['fy']**2)) if blur=='gaussian'
                        else disk_transfer(focus[m['depth']],math.hypot(m['fx'],m['fy'])) for m in components] for focus in focuses]
            if blur=='disk': assert any(v<0 for row in transfers for v in row),'sign-inverting plant is absent'
            row=dict(name=name,sources=source_rows,truth=truths,arms=arms,uniform_mean_null=null,coverage_min=float(delivered['coverage'].min()),
                     complete_coverage=delivered['complete_coverage'],quality_pass=quality,physical_blur_calibration=False,
                     component_truth=components,source_focus_widths=focuses,blur_family=blur,component_transfers=transfers,source_shifts=shifts,
                     component_recovery_lower_bound_only_not_overenhancement_guard=True)
            save(target/'case.json',row); report['cases'].append(row)
            return prepared_last
        case('constant-colours',[],[(0.,0.)],100,noisy=False)
        case('flat-noise-a',[],[(0.,0.),(0.,0.)],101)
        case('flat-noise-b',[],[(0.,0.),(0.,0.)],991)
        # The no-noise constant positive also checks actual full output amplitude.
        const=np.fromfile(out/'constant-colours/candidate/input-cfa.f32le',dtype='<f4').reshape(64,64)
        truthconst=np.empty_like(const)
        for p,(dx,dy) in enumerate(PHASE):truthconst[dy::2,dx::2]=[2048.,3072.,3072.,2560.][p]
        constant=score(np,const,truthconst,.02,.02); all_mechanics.append(constant['pass_']); report['mechanics']['constant']=constant
        # Independent physical geometry, lattice extraction and direct Fourier rows.
        modes=[mode([220.,0.,0.],.21875,.03125,.31),mode([0.,190.,0.],.30,.03,.19),mode([0.,0.,170.],.0625,.1875,.7)]
        raw=acquisition(np,modes,(0.,0.),513,noisy=False)
        report['oracle_original']=array_file(out/'oracle-original.u16le',raw)
        source=engine.source(raw,11,noise)
        angle=.12; scale=1.10; a=scale*math.cos(angle); b=scale*math.sin(angle); center=np.array([319.5,319.5])
        matrix=np.array([[a,-b],[b,a]]); translation=center-matrix@center+np.array([.31,-.43])
        affines=[identity,[[1.,0.,.37],[0.,1.,-.41]],[[a,-b,float(translation[0])],[b,a,float(translation[1])]]]
        rows=[]; full_origin=[ORIGIN]; last=None
        for ai,affine in enumerate(affines):
            geometry=engine.geometry(full_origin,affine,SOURCE_HW)
            loc,q=independent_geometry(np,full_origin,affine)
            assert loc==[[tuple(v) for v in row] for row in geometry.lattice_origins]
            geomscore=score(np,geometry.query_lattice.cpu().numpy(),q,1e-10,1e-10); all_mechanics.append(geomscore['pass_'])
            actual_lattice=engine.lattice_samples(source,geometry); got=engine.gather(source,geometry).cpu().numpy(); references=[]; predicted=[]
            for c in range(4):
                kind=(0,1,1,2)[c]; name=('R','G','B')[kind]
                lattice,_=lattice_reference(np,raw,loc[0],kind)
                assert np.array_equal(actual_lattice[name][0].cpu().numpy(),lattice.astype(np.float32))
                queries=np.array([q[0,c,y,x] for y,x in SAMPLES]); expected=direct_fourier(np,lattice,queries,affine,kind)
                measured=np.array([got[0,c,y,x] for y,x in SAMPLES]); references.append(expected); predicted.append(measured)
            parity=score(np,predicted,references); all_mechanics.append(parity['pass_'])
            cell_truth=[]; aa=np.asarray(affine)
            for c,(dx,dy) in enumerate(PHASE):
                values=[]
                for y,x in SAMPLES:
                    point=aa[:,:2]@np.array([ORIGIN[0]+2*x+dx,ORIGIN[1]+2*y+dy])+aa[:,2]
                    value=[2048.,3072.,2560.][CHANNEL[c]]
                    for m in modes:
                        f=np.array([m['fx'],m['fy']]); rf=aa[:,:2].T@f
                        value+=m['amplitudes'][CHANNEL[c]]*float(np.sinc(rf[0])*np.sinc(rf[1]))*math.cos(2*math.pi*float(f@point)+m['phase'])
                    values.append(value)
                cell_truth.append(values)
            rows.append(dict(affine=affine,geometry=geomscore,direct_fourier=parity,expected=np.array(references).tolist(),actual=np.array(predicted).tolist(),
                             independent_continuous_cell_truth=cell_truth,model_window_quantization_error=score(np,predicted,cell_truth),
                             continuous_truth_error_is_not_mechanical_gate=True))
            last=(geometry,np.array(references),q)
        geometry,reference,q=last
        wrongs={}
        for name,kwargs in [('phase-origin',dict(diagnostic_phase_shift_xy=(1,0))),('green-square',dict(diagnostic_green_square=True))]:
            gg=engine.geometry(full_origin,affines[-1],SOURCE_HW,**kwargs); wrong=engine.gather(source,gg).cpu().numpy()
            selected=np.array([[wrong[0,c,y,x] for y,x in SAMPLES] for c in range(4)])
            wrongs[name]=score(np,selected,reference); all_mechanics.append(not wrongs[name]['pass_'])
        wrong=engine.gather(source,geometry,omit_cell_ratio=True).cpu().numpy()
        wrongs['omitted-cell-ratio']=score(np,[[wrong[0,c,y,x] for y,x in SAMPLES] for c in range(4)],reference)
        all_mechanics.append(not wrongs['omitted-cell-ratio']['pass_'])
        half=matrix*.5; bt=center-half@center+np.array([.31,-.43])
        pitch_geometry=engine.geometry(full_origin,[[*half[0],bt[0]],[*half[1],bt[1]]],SOURCE_HW)
        wrong=engine.gather(source,pitch_geometry).cpu().numpy()
        wrongs['native-pitch']=score(np,[[wrong[0,c,y,x] for y,x in SAMPLES] for c in range(4)],reference)
        all_mechanics.append(not wrongs['native-pitch']['pass_'])
        report['mechanics']['fourier']=dict(rows=rows,foils=wrongs)
        # All16 actual probe paths; independent f64 FFT and pair-floor arithmetic.
        prep=engine.prepare_source(source,geometry); probe_coeff=[]; norm_samples=[]
        reflected=engine.geometry([(-64,-64),(0,0)],identity,SOURCE_HW)
        reversed_geometry=engine.geometry([(0,0),(-64,-64)],identity,SOURCE_HW)
        for draw in range(16):
            gp=engine.gather(source,geometry,draw).cpu().numpy().astype(np.float64)
            probe_coeff.append(analyse_reference(np,gp)[0])
            lattice=engine.lattice_samples(source,reflected,draw)
            reverse=engine.lattice_samples(source,reversed_geometry,draw)
            for kind,name in enumerate(('R','G','B')):
                values=lattice[name].cpu().numpy(); rev=reverse[name].cpu().numpy()
                assert np.array_equal(values,rev[::-1]), 'probe batch/order identity'
                keys=[]; samples=[]
                for p in range(2):
                    signal,indices=lattice_reference(np,raw,reflected.lattice_origins[p],kind)
                    keys.extend(indices.ravel()); samples.extend(values[p].ravel())
                keys=np.asarray(keys); samples=np.asarray(samples)
                sort=np.argsort(keys,kind='stable'); equal=keys[sort][1:]==keys[sort][:-1]
                assert np.array_equal(samples[sort][1:][equal],samples[sort][:-1][equal]), 'overlap/reflection original draw identity'
                if kind==0:
                    phase=np.zeros_like(signal,dtype=int)
                    variance=READ[0]+GAIN[0]*np.maximum(signal,0.)
                    # Unique unreflected physical sample census avoids counting repeats as independent.
                    _,unique=np.unique(indices,return_index=True)
                    norm_samples.append((values[1]/np.sqrt(variance)).ravel()[unique])
        expected=sum(np.abs(probe_coeff[i]-probe_coeff[i+1])**2 for i in range(0,16,2))/16
        actual=prep.variance.cpu().numpy().astype(np.float64)
        denominator=np.maximum(expected,1.)
        floor_error=float(np.max(np.abs(actual-expected)/denominator))
        samples=np.concatenate(norm_samples); probe_mean=float(samples.mean()); probe_var=float(samples.var())
        stats=dict(normalized_floor_max_error=floor_error,bar=2e-4,probe_mean=probe_mean,probe_variance=probe_var,
                   count=int(samples.size),pass_=floor_error<=2e-4 and abs(probe_mean)<=.04 and .90<=probe_var<=1.10)
        stats['doubled_floor_scorer_foil_error']=float(np.max(np.abs(2*actual-expected)/denominator))
        stats['pass_'] &= stats['doubled_floor_scorer_foil_error']>2e-4
        all_mechanics.append(stats['pass_']); report['mechanics']['noise']=stats
        other=engine.source(raw,12,noise)
        assert not torch.equal(engine.lattice_samples(source,geometry,0)['R'],engine.lattice_samples(other,geometry,0)['R'])
        # Actual OLA on odd dimensions, with a missing-corner causal foil.
        odd_origins=module.patch_origins(65,67,ORIGIN); oddgeom=engine.geometry(odd_origins,identity,SOURCE_HW)
        pp=engine.prepare_source(source,oddgeom); accumulator=module.Accumulator(engine,len(odd_origins)); accumulator.add(list(range(len(odd_origins))),pp)
        ff=accumulator.finish(); odd=engine.overlap_add(ff,odd_origins,65,67,ORIGIN)
        direct,cov=ola_reference(np,pp.gathered.cpu().numpy(),odd_origins,65,67,ORIGIN)
        oddscore=score(np,odd['uniform'].cpu().numpy(),direct); all_mechanics.extend([oddscore['pass_'],odd['complete_coverage']])
        reduced={k:(v[1:] if k in ('coefficients','uniform_coefficients','means','counts') else v) for k,v in ff.items()}
        missing=engine.overlap_add(reduced,odd_origins[1:],65,67,ORIGIN)
        all_mechanics.append(not missing['complete_coverage'])
        report['mechanics']['odd_coverage']=dict(null=oddscore,complete=odd['complete_coverage'],missing_patch_refused=not missing['complete_coverage'])
        del source,other,prep,pp,accumulator,ff,odd,reduced
        # Fixed positives and adverses. They are quality observations, never hidden mechanical admission.
        case('neutral-structure',[mode([100.,100.,100.],.125,.0625,.3)],[(0.,0.),(1.2,1.2)],211)
        case('independent-colours',[mode([160.,0.,0.],.1875,0.,.3),mode([0.,8.,0.],.0625,.125,.7),mode([0.,0.,130.],.0625,.1875,.2)],[(0.,0.),(1.5,1.5)],313)
        case('green-diamond',[mode([0.,140.,0.],.30,.03,.2)],[(0.,0.),(1.2,1.2)],417)
        case('shared-bin-conflict',[mode([150.,0.,0.],.20,0.,.2,0),mode([0.,150.,0.],.30,0.,.2,1)],[(0.,1.5),(1.5,0.)],521)
        case('red-cancellation-diverse',[mode([150./float(np.sinc(.2)),0.,0.],.20,0.,0.,0),mode([-150./float(np.sinc(.3)),0.,0.],.30,0.,0.,0)],[(0.,0.),(0.,0.),(1.2,1.2)],623,shifts=[(0.,0.),(1.,0.),(0.,0.)])
        case('near-fine-far-coarse',[mode([0.,160.,0.],.1875,0.,.31,0),mode([0.,160.,0.],0.,.0625,.19,1)],[(0.,2.),(2.,0.)],727)
        crossing=[mode([90.,110.,70.],.17,.09,.3,0),mode([80.,50.,120.],-.09,.17,.8,1)]
        crossing += [mode([350.,350.,350.],fx,fy,0.,1) for fx,fy in [(.03125,0.),(0.,.03125),(.0625,.0625),(.125,-.0625)]]
        case('crossed-glint-sign-inversion',crossing,[(0.,3.5),(3.5,0.)],829,blur='disk')
        report['runtime_after']=engine.metadata()
        all_mechanics.append(report['runtime_after']['maximum_discarded_imaginary_dn']<=.01)
        for value in inputs: assert ref(value['path'])==value,'bound input changed'
        report.update(status='COMPLETE_NATIVE_SPECTRAL_CONTROLS',complete=True,controls_pass=all(all_mechanics),
            quality_pass=all(v['quality_pass'] for v in report['cases']),source_bindings_unchanged=True,
            numerical_reconstruction_quality_claim=False,original_RAW_reads=0,seconds=time.perf_counter()-started,
            limits=['conditional probe variance is not estimator variance','crossed Fourier packets are not opaque visibility truth',
                    'finite-window source interpolant is not alias inversion','synthetic disk PSF is a plant, not Sony calibration'],
            libraries=dict(python=sys.version,numpy=np.__version__,torch=torch.__version__))
        save(out/'receipt.json',report)
        print(json.dumps(dict(status=report['status'],controls_pass=report['controls_pass'],quality_pass=report['quality_pass']),allow_nan=False),flush=True)
    except BaseException as error:
        report.update(error=repr(error),traceback=traceback.format_exc(),seconds=time.perf_counter()-started)
        save(out/'receipt.json',report)
        raise


if __name__=='__main__': main()
