"""Fixed native-f32 local translation diagnostic; no execution on import.
Adapted from owned M-PHASE0-SPLIT2 unnormalized subpixel correlation.
Zero padding makes the discrete correlation linear. No transform is a merge map.
"""
import hashlib,json,math
import numpy as np
from scipy.fft import fft2,ifft2,fftshift
from scipy.ndimage import maximum_filter
from scipy.signal.windows import tukey
from skimage.registration import phase_cross_correlation

SIDE=129;RADIUS=32;PAD=2*SIDE-1;UPSAMPLE=100;ALPHA=.25
STD_MIN=1.0;CORR_MIN=.45;SECOND_MAX=.90;PEAK_EXCLUDE=3
TRUTH_LIMIT=.15;REPRO_LIMIT=.5
PAIRS=((0,1),(3,4));OFFSETS=((-96,-96),(-96,96),(96,-96),(96,96))
LUMA=(.2880402,.7118741,.0000857)
POSITIVE=('zero','integer','fractional','differential-blur')
NEGATIVE=('flat','unrelated','periodic','outside-search')
CONTROL_IDS=POSITIVE+NEGATIVE
BLOBS=((15.5,21.5,1.5,2.),(26.,99.,3.5,-1.4),(38.5,59.5,2.5,1.1),(47.5,111.5,5.5,.9),(60.5,18.,2.,-1.7),(71.,75.5,4.,1.5),(83.,44.5,3.,-1.2),(94.,105.5,2.,1.8),(108.5,28.5,4.5,1.),(115.5,87.,2.5,-1.3))
COMPONENTS=((1,2,1.2,.1),(2,-3,.8,1.3),(3,5,.6,-.4),(4,1,.5,2.1),(5,-7,.4,.7),(7,4,.35,-1.1),(9,-2,.3,1.9),(11,8,.24,-2.3),(13,-5,.2,.45),(17,3,.15,2.7))

def need(ok,message):
    if not ok:raise ValueError(message)
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def digest(a):return hashlib.sha256(np.ascontiguousarray(a,dtype='<f4').tobytes()).hexdigest()
def project(rgb):
    need(rgb.dtype==np.uint16 and rgb.shape==(SIDE,SIDE,3),'exact native RGB16 patch')
    values=rgb.astype(np.float32)
    # Same numerical CameraLinear proxy coefficients, now direct f32: no percentile stretch or u8 quantization.
    result=values[:,:,0]*np.float32(LUMA[0]);result+=values[:,:,1]*np.float32(LUMA[1]);result+=values[:,:,2]*np.float32(LUMA[2])
    return np.ascontiguousarray(result,dtype=np.float32)
def centres(width,height):
    # Nearest integer; fifths cannot be exact half ties for integer dimensions.
    return [(int((2*j*height+5)//10),int((2*i*width+5)//10)) for j in range(1,5) for i in range(1,5)]
def estimate(reference,moving,observer=None):
    need(reference.dtype==moving.dtype==np.float32 and reference.shape==moving.shape==(SIDE,SIDE),'actual native-f32 equal patch path')
    need(np.isfinite(reference).all() and np.isfinite(moving).all(),'finite analysis pixels')
    original=(digest(reference),digest(moving));std=[float(np.std(x,dtype=np.float32)) for x in (reference,moving)]
    result=dict(schema='m193c-local-displacement-v1',status='REFUSED',reason=None,feature_displacement_source_minus_reference_dydx_native=None,alignment_to_apply_source_dydx_native=None,coarse_alignment_dydx_native=None,peak_global_energy_normalized_correlation=None,second_local_peak_ratio=None,input_f32_sha256=list(original),std_dn=std)
    surface=np.zeros((2*RADIUS+1,2*RADIUS+1),dtype=np.float32)
    if min(std)<STD_MIN:result['reason']='FLAT_OR_LOW_CONTRAST'
    else:
        window=np.asarray(tukey(SIDE,alpha=ALPHA),dtype=np.float32);window=window[:,None]*window[None,:]
        a=(reference-np.mean(reference,dtype=np.float32))*window;b=(moving-np.mean(moving,dtype=np.float32))*window
        af=fft2(a,s=(PAD,PAD),workers=1);bf=fft2(b,s=(PAD,PAD),workers=1)
        need(af.dtype==bf.dtype==np.complex64,'f32 Fourier path')
        cc=fftshift(ifft2(af*np.conj(bf),workers=1).real).astype(np.float32,copy=False)
        denominator=np.sqrt(np.sum(a*a,dtype=np.float32)*np.sum(b*b,dtype=np.float32),dtype=np.float32)
        cc/=denominator
        mid=SIDE-1;surface=np.ascontiguousarray(cc[mid-RADIUS:mid+RADIUS+1,mid-RADIUS:mid+RADIUS+1])
        flat=int(np.argmax(cc));py,px=divmod(flat,PAD);peak=float(cc[py,px]);coarse=(py-mid,px-mid)
        local=cc==maximum_filter(cc,size=5,mode='constant',cval=-np.inf)
        yy,xx=np.ogrid[:PAD,:PAD];local &= np.maximum(np.abs(yy-py),np.abs(xx-px))>PEAK_EXCLUDE
        second=float(np.max(cc[local])) if np.any(local) else 0.;ratio=second/peak if peak>0 else 1.
        result.update(coarse_alignment_dydx_native=list(coarse),peak_global_energy_normalized_correlation=peak,second_local_peak_ratio=ratio)
        if max(abs(v) for v in coarse)>RADIUS:result['reason']='OUTSIDE_FIXED_SEARCH'
        elif peak<CORR_MIN:result['reason']='LOW_CORRELATION'
        elif ratio>SECOND_MAX:result['reason']='AMBIGUOUS_MULTIPLE_PEAKS'
        else:
            shift,_,_=phase_cross_correlation(af,bf,space='fourier',upsample_factor=UPSAMPLE,normalization=None)
            shift=[float(v) for v in shift]
            if not all(math.isfinite(v) for v in shift) or max(abs(shift[i]-coarse[i]) for i in range(2))>1.:result['reason']='REFINEMENT_INCONSISTENT'
            elif max(abs(v) for v in shift)>RADIUS:result['reason']='OUTSIDE_FIXED_SEARCH'
            else:result.update(status='RETURNED_LOCAL_TRANSLATION',reason=None,alignment_to_apply_source_dydx_native=shift,feature_displacement_source_minus_reference_dydx_native=[-v for v in shift])
    intrinsic=canonical(result);surface_hash=digest(surface)
    if observer is not None:observer(result,surface)
    need(canonical(result)==intrinsic and digest(surface)==surface_hash and (digest(reference),digest(moving))==original,'actual observer changed input or output')
    return result,surface

def evaluate(displacement=(0.,0.),blur=0.):
    # Continuous point evaluations, never resampling a sampled image or wrapping its edges.
    yy,xx=np.indices((SIDE,SIDE),dtype=np.float32);yy-=np.float32(displacement[0]);xx-=np.float32(displacement[1])
    image=np.full((SIDE,SIDE),np.float32(20000),dtype=np.float32)
    for cy,cx,sigma,amplitude in BLOBS:
        variance=np.float32(sigma*sigma+blur*blur);radius=(yy-np.float32(cy))**2+(xx-np.float32(cx))**2
        image+=np.float32(3000*amplitude*sigma*sigma/(sigma*sigma+blur*blur))*np.exp(-np.float32(.5)*radius/variance)
    for ky,kx,amp,phase in COMPONENTS:
        gain=math.exp(-2*math.pi**2*blur**2*(ky*ky+kx*kx)/(SIDE*SIDE))
        angle=np.float32(2*math.pi/SIDE)*(np.float32(ky)*yy+np.float32(kx)*xx)+np.float32(phase)
        image+=np.float32(150*amp*gain)*np.sin(angle)
    return np.ascontiguousarray(image)
def fixture(name):
    shifts={'zero':(0.,0.),'integer':(5.,-7.),'fractional':(1.25,-.4),'differential-blur':(1.25,-.4),'outside-search':(40.,0.)}
    if name in shifts:
        shift=shifts[name];return evaluate(),evaluate(shift,2. if name=='differential-blur' else 0.),shift
    yy,xx=np.indices((SIDE,SIDE),dtype=np.float32)
    if name=='flat':return np.full_like(yy,20000),np.full_like(yy,21000),None
    if name=='unrelated':return 20000+3000*np.sin(np.float32(2*math.pi/17)*xx),20000+3000*np.sin(np.float32(2*math.pi/19)*yy),None
    if name=='periodic':
        return 20000+3000*(np.sin(np.float32(2*math.pi/16)*xx)+np.cos(np.float32(2*math.pi/16)*yy)),20000+3000*(np.sin(np.float32(2*math.pi/16)*(xx-2.25))+np.cos(np.float32(2*math.pi/16)*(yy+1.5))),None
    raise ValueError('unlisted fixed fixture')
def truth_error(result,truth):
    if result['status']!='RETURNED_LOCAL_TRANSLATION':return None
    return max(abs(result['feature_displacement_source_minus_reference_dydx_native'][i]-truth[i]) for i in range(2))
def reproduce(rows):
    need(len(rows)==4,'four disjoint fixed quadrants')
    if any(x['status']!='RETURNED_LOCAL_TRANSLATION' for x in rows):return dict(status='UNAVAILABLE_DISJOINT_EVIDENCE',diagonal_a=None,diagonal_b=None,maximum_difference_native=None)
    d=[r['feature_displacement_source_minus_reference_dydx_native'] for r in rows]
    a=[.5*(d[0][i]+d[3][i]) for i in range(2)];b=[.5*(d[1][i]+d[2][i]) for i in range(2)];difference=max(abs(a[i]-b[i]) for i in range(2))
    return dict(status='DISJOINT_DIAGONAL_AGREEMENT' if difference<=REPRO_LIMIT else 'DISAGREEMENT',diagonal_a=a,diagonal_b=b,maximum_difference_native=difference)
