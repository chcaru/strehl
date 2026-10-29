"""Fixed cosine-regression observer. No image reconstruction/fusion API."""
import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location("forward_base",Path(__file__).with_name("repeat-forward-model.py"));base=importlib.util.module_from_spec(s);s.loader.exec_module(base);np=base.np

def rows(sites,pull,full,center,side,n):
    if n>24 or len(sites)>base.MAX_SAMPLES:raise base.Unknown("cosine observer budget")
    ref=base.inverse_sensor(sites,pull,full)-center+side/2
    k=np.arange(n,dtype=np.float32)*np.float32(np.pi/side)
    ax=ref[:,0].astype(np.float32)[:,None,None]*k[None,:,None]
    ay=ref[:,1].astype(np.float32)[:,None,None]*k[None,None,:]
    a,b=pull["a"];inv=np.linalg.inv(np.array([[a,-b],[b,a]],dtype=float))
    # cos(u)cos(v) = [cos(u+v)+cos(u-v)]/2. Each signed
    # plane wave integrates exactly over the transformed sensor-square aperture.
    fx=np.arange(n,dtype=float)/(2*side);fy=fx.copy()
    result=np.zeros((len(sites),n,n),dtype=np.float32)
    for sign in [-1,1]:
        u=fx[:,None]*inv[0,0]+sign*fy[None,:]*inv[1,0]
        v=fx[:,None]*inv[0,1]+sign*fy[None,:]*inv[1,1]
        aperture=(np.sinc(u)*np.sinc(v)).astype(np.float32)
        result+=np.float32(.5)*np.cos(ax+sign*ay)*aperture[None,:,:]
    return result.reshape(len(sites),n*n)
