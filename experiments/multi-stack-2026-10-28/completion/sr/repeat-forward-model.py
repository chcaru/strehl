"""Bounded original-CFA forward hypothesis. No image output/admission API.

Storage is original uint16. Model arrays/solves are float32. Physical-coordinate
and independent analytic photon generation calculations use float64.
"""
import os
for _k in ["OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"]:os.environ[_k]="1"
import math
import numpy as np

MAX_SAMPLES=16384
MAX_COEFFICIENTS=400
MAX_BYTES=256<<20
class Unknown(Exception):pass

def inverse_sensor(points,pull,full):
    a=complex(*pull["a"]);b=complex(*pull["b"]);c=complex(*full)+.5+.5j
    z=np.asarray(points)[...,0]+1j*np.asarray(points)[...,1]
    r=(z-c-2*b)/a+c
    return np.stack([r.real,r.imag],axis=-1)

def forward_sensor(points,pull,full):
    a=complex(*pull["a"]);b=complex(*pull["b"]);c=complex(*full)+.5+.5j
    z=np.asarray(points)[...,0]+1j*np.asarray(points)[...,1]
    r=a*(z-c)+2*b+c
    return np.stack([r.real,r.imag],axis=-1)

def original_sites(pull,full,center,side,color):
    corners=np.array([[-1,-1],[1,-1],[-1,1],[1,1]])*side/2+center
    source=forward_sensor(corners,pull,full)
    lo=np.floor(source.min(0)-1).astype(int);hi=np.ceil(source.max(0)+1).astype(int)
    if np.any(lo<0) or np.any(hi>=2*np.array(full)):raise Unknown("outside original active geometry")
    xy=np.array([[x,y] for y in range(lo[1],hi[1]+1) for x in range(lo[0],hi[0]+1)],dtype=np.int64)
    parity=np.where((xy[:,0]%2==0)&(xy[:,1]%2==0),0,np.where((xy[:,0]%2==1)&(xy[:,1]%2==1),2,1))
    xy=xy[parity==color]
    aperture=xy[:,None,:]+np.array([[-.5,-.5],[.5,-.5],[-.5,.5],[.5,.5]])
    ref=inverse_sensor(aperture,pull,full)-center
    good=np.all(np.abs(ref)<side/2-1e-7,axis=(1,2))
    return xy[good]

def axis_basis(x,n,side):
    x=np.asarray(x,dtype=np.float32).reshape(-1)
    knots=np.r_[np.zeros(4),np.arange(1,n-3)*side/(n-3),np.full(4,side)].astype(np.float32)
    b=((x[:,None]>=knots[:-1])&(x[:,None]<knots[1:])).astype(np.float32)
    for degree in range(1,4):
        q=np.zeros((len(x),len(knots)-degree-1),dtype=np.float32)
        for i in range(q.shape[1]):
            d=knots[i+degree]-knots[i]
            if d>0:q[:,i]+=(x-knots[i])/d*b[:,i]
            d=knots[i+degree+1]-knots[i+1]
            if d>0:q[:,i]+=(knots[i+degree+1]-x)/d*b[:,i+1]
        b=q
    assert b.shape[1]==n
    b[x==side,-1]=1
    return b

def rows(sites,pull,full,center,side,n):
    if len(sites)>MAX_SAMPLES or n*n>MAX_COEFFICIENTS:raise Unknown("bounded model shape")
    q,w=np.polynomial.legendre.leggauss(4)
    offsets=np.array([[x/2,y/2] for y in q for x in q])
    weights=np.array([x*y/4 for y in w for x in w],dtype=np.float32)
    ref=inverse_sensor(sites[:,None,:]+offsets,pull,full)-center+side/2
    if np.any(ref<0) or np.any(ref>side):raise Unknown("aperture outside spline domain")
    bx=axis_basis(ref[:,:,0],n,side).reshape(len(sites),16,n)
    by=axis_basis(ref[:,:,1],n,side).reshape(len(sites),16,n)
    result=np.einsum("nqi,nqj,q->nij",bx,by,weights,optimize=True).reshape(len(sites),n*n).astype(np.float32)
    if not np.allclose(result.sum(1),1,rtol=0,atol=2e-6):raise Unknown("basis partition")
    return result

def linear_fit(train,held,variance_train,variance_held,condition_limit=1e6,max_ratio=4):
    n,p=train.shape;m=len(held)
    if n<p+64:raise Unknown("insufficient training rows")
    estimated=4*(n*p*3+p*p*4+m*n*3+m*m*8)
    if estimated>MAX_BYTES:raise Unknown("model workspace budget")
    if not all(np.isfinite(v).all() and np.all(v>0) for v in [variance_train,variance_held]):raise Unknown("invalid frozen variance")
    sigma=np.sqrt(variance_train).astype(np.float32)
    aw=train/sigma[:,None]
    scale=np.sqrt(np.sum(aw*aw,axis=0,dtype=np.float32))
    if np.any(scale<1e-12):raise Unknown("unobserved basis coefficient")
    aw=aw/scale;ah=held/scale
    normal=aw.T@aw;normal=(normal+normal.T)*np.float32(.5)
    ev=np.linalg.eigvalsh(normal)
    condition=float(ev[-1]/ev[0]) if ev[0]>0 else math.inf
    if not math.isfinite(condition) or condition>condition_limit:raise Unknown("scaled Gram condition "+str(condition))
    try:
        chol=np.linalg.cholesky(normal)
        zt=np.linalg.solve(chol,aw.T);zh=np.linalg.solve(chol,ah.T)
    except np.linalg.LinAlgError as exc:raise Unknown("unregularized Cholesky") from exc
    b=zh.T@zt
    covariance=b@b.T
    ratio=np.diag(covariance)/variance_held
    residual_covariance=covariance+np.diag(variance_held)
    chol_residual=np.linalg.cholesky(residual_covariance)
    return {"B":b,"sigma":sigma,"covariance":covariance,"residual_cholesky":chol_residual,
        "condition":condition,"prediction_variance_ratio_max":float(ratio.max()),
        "eligible":bool(ratio.max()<=max_ratio),"reservation_bytes":estimated,"rank":p,"train_count":n,"held_count":m}

def native_weights(sites_by_source,pulls,full,held_sites,held_pull,color):
    """Same-count native bilinear original prediction; no aligned image volume."""
    total=sum(map(len,sites_by_source));out=np.zeros((len(held_sites),total),dtype=np.float32)
    ref=inverse_sensor(held_sites,held_pull,full)
    plane_offsets=[(0,0)] if color==0 else [(1,1)] if color==2 else [(1,0),(0,1)]
    base=0
    for sites,pull in zip(sites_by_source,pulls):
        index={tuple(xy):i for i,xy in enumerate(sites)}
        point=forward_sensor(ref,pull,full)
        for ox,oy in plane_offsets:
            plane=(point-np.array([ox,oy]))/2
            i=np.floor(plane).astype(int);f=(plane-i).astype(np.float32)
            for j in range(len(held_sites)):
                for dy in range(2):
                    for dx in range(2):
                        weight=(f[j,0] if dx else 1-f[j,0])*(f[j,1] if dy else 1-f[j,1])
                        xy=(2*(i[j,0]+dx)+ox,2*(i[j,1]+dy)+oy)
                        if xy not in index:raise Unknown("native baseline missing original tap")
                        out[j,base+index[xy]]+=weight/(len(pulls)*len(plane_offsets))
        base+=len(sites)
    return out

def interval(observed,trace,frobenius2,operator,t):
    z=observed-trace;v=operator
    if v==0:return [observed,observed]
    rad=t*(frobenius2+2*v*z+4*t*v*v)
    if rad<0:return None
    upper=z+4*t*v+2*math.sqrt(rad)
    if upper<0:return None
    q=z-2*v*t
    lower=0 if q<=2*math.sqrt(t*frobenius2) else max(0,q+4*t*v-2*math.sqrt(t*(frobenius2+2*v*q+4*t*v*v)))
    return [lower,upper] if lower<=upper else None

class Quadratic:
    def __init__(self):self.q=self.trace=self.frobenius2=self.operator=0.;self.count=0
    def add(self,value,covariance):
        # f64 summaries of f32 estimator outputs, not new image arithmetic.
        v=value.astype(np.float64);c=covariance.astype(np.float64)
        self.q+=float(v@v);self.trace+=float(np.trace(c));self.frobenius2+=float(np.sum(c*c));self.operator=max(self.operator,float(np.abs(c).sum(1).max()));self.count+=len(v)
    def result(self,t):return {"observed":self.q,"trace":self.trace,"frobenius2":self.frobenius2,"operator_bound":self.operator,"count":self.count,"signal_interval":interval(self.q,self.trace,self.frobenius2,self.operator,t)}
