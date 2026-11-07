"""Fixed natural-boundary constrained spline hypothesis; no hidden penalty."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("forward_base",Path(__file__).with_name("repeat-forward-model.py"));base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base);np=base.np

def transform(n):
    t=np.zeros((n,n-2),dtype=np.float32);t[1:-1]=np.eye(n-2,dtype=np.float32)
    # For repeated end knots, s''(0)=(6c0-9c1+3c2)/h².
    t[0,0]=1.5;t[0,1]=-.5;t[-1,-1]=1.5;t[-1,-2]=-.5
    return t

def rows(sites,pull,full,center,side,n):
    a=base.rows(sites,pull,full,center,side,n).reshape(len(sites),n,n);t=transform(n)
    return np.einsum("nij,ik,jl->nkl",a,t,t,optimize=True).reshape(len(sites),(n-2)**2).astype(np.float32)
