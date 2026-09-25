"""Root-only tiny coupled-pupil fixtures; execute through bounded run.py."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, sys
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
OPTICS = HERE.parent/'layered-raw-inverse'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
def digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
def save(out, name, a):
    a = np.ascontiguousarray(a)
    path = out/name
    with path.open('xb') as f: f.write(a.tobytes())
    return dict(file=name, shape=list(a.shape), dtype=a.dtype.str, sha256=digest(a))
def shifted(a, dx, dy, fill=4):
    """output[y,x]=input[y+dy,x+dx], explicit unsupported bit outside."""
    h,w = a.shape
    result = np.full_like(a, fill)
    x0,x1,y0,y1 = max(0,-dx),min(w,w-dx),max(0,-dy),min(h,h-dy)
    if x0<x1 and y0<y1:
        result[y0:y1,x0:x1] = a[y0+dy:y1+dy,x0+dx:x1+dx]
    return result
def support(alpha, table, radius):
    assert set(np.unique(alpha)) <= {0,1}
    labels = np.where(alpha==1,1,2).astype(np.uint8)
    rays = np.zeros_like(labels)
    # Every positive joint entry is a product from the SAME pupil ray.
    for px,py,qx,qy in table.offsets:
        p = shifted(labels,int(px),int(py))
        q = shifted(np.ones_like(labels),int(qx),int(qy))
        # Far radiance is consumed only on a transmitted (far) branch.
        term = p.copy()
        term[(p==2)&(q==4)] = 4
        rays |= term
    result = np.zeros_like(labels)
    for dy in range(-radius,radius+1):
        for dx in range(-radius,radius+1): result |= shifted(rays,dx,dy)
    return result
def scene(name):
    y,x = np.mgrid[:96,:96].astype(np.float32)
    near = np.zeros((96,96,3),np.float32)
    far = np.zeros_like(near)
    if name=='flat':
        near[:] = far[:] = np.float32(.25)
        alpha = np.ones((96,96),np.float32)
    elif name=='transparent':
        alpha = np.full((96,96),.5,np.float32)
        for c,(dx,dy,phase) in enumerate([(1.,0.,.37),(.8,.6,1.13),(-.6,.8,2.07)]):
            near[...,c] = .27+2*np.float32([.045,.05,.04][c])*np.cos(np.float32(2*np.pi*.10)*(dx*x+dy*y)+phase)
            far[...,c] = .27+2*np.float32([.09,.10,.085][c])*np.cos(np.float32(2*np.pi*.022)*(-dy*x+dx*y)+phase+.44)
    else:
        assert name=='opaque'
        alpha = ((x<32)|((x>=58)&(x<61)&(y>=35)&(y<62))).astype(np.float32)
        for c in range(3):
            near[...,c] = np.float32([.54,.60,.49][c])+np.float32(.035)*np.cos(np.float32(2*np.pi*.10)*y+.4*c)
            far[...,c] = np.float32([.18,.22,.25][c])+np.float32([.06,.07,.055][c])*np.cos(np.float32(2*np.pi*.065)*(x+.3*y)+.7*c)
    assert near.dtype==far.dtype==alpha.dtype==np.float32
    return near,far,alpha
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve();assert out.is_relative_to(HERE) and not out.exists();out.mkdir()
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    author=load('optical_support_frozen_pupil',OPTICS/'pupil-stencil.py')
    # These positive Config fields are unused by forward. Actual noise is injected
    # later by Rust's camera profile, never from these geometry-only placeholders.
    config=author.model.Config(width=96,height=96,focus_coordinates=(1.,.75,.5,.25,0.),gain=1.,read_variance=1.)
    r=np.sqrt((np.arange(128,dtype=np.float64)+.5)/128)
    theta=2*np.pi*(np.arange(128,dtype=np.float64)+.5)/128+.23
    pupil=np.stack((r[:,None]*np.cos(theta),r[:,None]*np.sin(theta)),-1).reshape(-1,2).astype(np.float32)
    tables=[author.build_table(pupil,12*(f-1),12*f) for f in config.focus_coordinates]
    independent=load('optical_support_independent_controls',HERE/'independent-controls.py')
    controls=independent.prepare_controls(sys.modules[__name__],pupil,tables)
    records=[]
    for name in ('flat','transparent','opaque'):
        near,far,alpha=scene(name)
        originals=[digest(v) for v in (near,far,alpha)]
        fields=[torch.tensor(v*np.float32(14848) if i<2 else v,device='cuda') for i,v in enumerate((near,far,alpha))]
        sharp=alpha[...,None]*near+(1-alpha[...,None])*far
        with torch.no_grad():
            truth=author.model._blur(torch.tensor(sharp,device='cuda'),.7).cpu().numpy().copy()
        folder=out/name;folder.mkdir();files=[save(folder,'truth-rgb.f32',truth.astype('<f4'))]
        # Independent scoring can recover both contributions without conflating them.
        for label,v in [('near',alpha[...,None]*near),('far',(1-alpha[...,None])*far)]:
            with torch.no_grad(): component=author.model._blur(torch.tensor(v,device='cuda'),.7).cpu().numpy().copy()
            files.append(save(folder,label+'-truth-rgb.f32',component.astype('<f4')))
        labels=np.where(alpha==1,1,2).astype(np.uint8)
        files.append(save(folder,'sharp-labels.u8',labels))
        for i,table in enumerate(tables):
            with torch.no_grad(): expected=author.forward(*fields,config,i,pupil=pupil,table=table).cpu().numpy().copy()
            assert expected.dtype==np.float32 and np.isfinite(expected).all() and expected.min()>=0 and expected.max()<14848
            # Binary source support is derived from geometry alone, never radiance.
            bits=support(alpha,table,3) if name=='opaque' else np.ones((96,96),np.uint8)
            files.append(save(folder,f'frame-{i}-rgb-dn.f32',expected.astype('<f4')))
            files.append(save(folder,f'frame-{i}-support.u8',bits))
        assert originals==[digest(v) for v in (near,far,alpha)]
        records.append(dict(name=name,files=files,opaque_veto=name=='opaque',source_unchanged=True))
    result=dict(status='PREPARED',native_size=[96,96],crop_plane=[8,8,32,32],frames=5,
        focus=list(config.focus_coordinates),psf_sigma=.7,psf_radius=3,pupil_count=16384,
        pupil_sha256=digest(pupil),tables=[t.metadata for t in tables],scenes=records,
        independent_preparation_controls=controls,
        noise='Injected only by actual Rust ISO100 NoiseModel; forward Config noise fields unused',
        runtime=author.runtime_metadata())
    with (out/'manifest.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('OPTICAL_SUPPORT_PREPARED',json.dumps(dict(scenes=len(records),frames=5)),flush=True)
if __name__=='__main__':main()
