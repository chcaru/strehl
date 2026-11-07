"""Local pairwise optical-change diagnostic with explicit geometry/brightness nuisance terms."""
import hashlib
import json
from pathlib import Path
import numpy as np
import cv2
from scipy.ndimage import gaussian_filter, shift

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/sony-focus-control-capture-review"
cv2.setNumThreads(1)


def response(a, b, slope, centre):
    # Both inputs remain native G1 samples. Only transient pairwise arithmetic.
    aa = gaussian_filter(a.astype(np.float32)-512,2)
    bb = gaussian_filter(b.astype(np.float32)-512,2)
    mid = (aa+bb)*np.float32(.5)
    dx = cv2.Sobel(mid,cv2.CV_32F,1,0,ksize=3,scale=.125)
    dy = cv2.Sobel(mid,cv2.CV_32F,0,1,ksize=3,scale=.125)
    lap = cv2.Laplacian(mid,cv2.CV_32F,ksize=3,scale=.25)
    h,w = mid.shape
    yy,xx = np.mgrid[4:h-4:4,4:w-4:4].astype(np.float32)
    normal = yy+slope*(xx-w/2)-centre
    valid = (xx>w*.12)&(xx<w*.88)&(np.abs(normal)<300)
    x = ((xx-w/2)/1000)[valid]
    y = ((yy-h/2)/1000)[valid]
    def take(image):
        return image[4:h-4:4,4:w-4:4][valid]
    gx,gy,ll,signal = map(take,(dx,dy,lap,mid))
    matrix = np.column_stack((gx,gy,x*gx,y*gx,x*gy,y*gy,signal/500,np.ones_like(signal),
                              ll,ll*normal[valid]/100)).astype(np.float32)
    delta = take(bb-aa)
    weights = 1/np.sqrt(np.maximum(signal,0)*np.float32(100/436.8)+np.float32((4.2*100/436.8)**2))
    norms = np.sqrt(np.mean((matrix*weights[:,None])**2,axis=0,dtype=np.float32))
    standardized = matrix*weights[:,None]/norms
    coeff,_,_,singular = np.linalg.lstsq(standardized,delta*weights,rcond=None)
    coeff /= norms
    residual = delta-matrix@coeff
    # Focus coefficient is an empirical optical-change coordinate, not distance.
    return {"focus_response":float(coeff[-1]),"uniform_blur_response":float(coeff[-2]),
            "translation_green_px":coeff[:2].tolist(),"affine_terms":coeff[2:6].tolist(),
            "brightness_terms":coeff[6:8].tolist(),"residual_rms_dn":float(np.sqrt(np.mean(residual**2))),
            "condition_number":float(singular[0]/singular[-1]),"pixels":len(delta)}


def main():
    inventory=json.loads((OUT/'inventory.json').read_text())
    bands=json.loads((OUT/'band-results.json').read_text())
    results=[]
    for run_index,run in enumerate(inventory['sessions'],1):
        slope=bands['parameters']['slopes'][run_index-1]
        baseline=[r for r in bands['records'] if r['run']==run_index and r['ordinal']==1][0]
        centre=float(np.median([f['centre_green_px'] for f in baseline['fits']]))
        pairs=[]
        pairs += [('fixed-null',None,None,i,i+1) for i in range(1,5)]
        pairs += [('command-null',None,None,i,i+1) for i in range(5,8)]
        for repeat in range(3):
            start=11+13*repeat
            # Direct adjacent comparisons at the fine end plus 4 -> 6 -> 8.
            pairs += [('fine',repeat,step,start+step,start+step+1) for step in range(6)]
        pairs += [('native',repeat,step,56+9*repeat+step,57+9*repeat+step)
                  for repeat in range(2) for step in range(3)]
        pairs += [('return',None,None,50+2*step,51+2*step) for step in range(3)]
        pairs += [('same-node-over-time',None,None,11,24),('same-node-over-time',None,None,24,37),
                  ('same-node-over-time',None,None,56,65)]
        first=np.load(OUT/'green-cfa'/f'run-{run_index}-01.npy')
        controls={
            'identity':response(first,first,slope,centre),
            'brightness':response(first,(first.astype(np.float32)-512)*1.02+515,slope,centre),
            'translation':response(first,shift(first.astype(np.float32),(.08,-.12),order=3,mode='nearest'),slope,centre)}
        assert abs(controls['identity']['focus_response'])<1e-7
        assert abs(controls['brightness']['focus_response'])<1e-4
        assert abs(controls['translation']['focus_response'])<.003,controls['translation']
        run_rows=[]
        for kind,repeat,step,first_id,second_id in pairs:
            a=np.load(OUT/'green-cfa'/f'run-{run_index}-{first_id:02d}.npy')
            b=np.load(OUT/'green-cfa'/f'run-{run_index}-{second_id:02d}.npy')
            record={"kind":kind,"repeat":repeat,"step":step,"a":first_id,"b":second_id,
                    "offset_a":run['frames'][first_id-1]['offset'],"offset_b":run['frames'][second_id-1]['offset'],
                    **response(a,b,slope,centre)}
            run_rows.append(record)
            if len(run_rows)%10==0:
                print(f'Run {run_index}: pair responses {len(run_rows)}/{len(pairs)}',flush=True)
        results.append({'run':run_index,'controls':controls,'pairs':run_rows})
    report={'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'parameters':{'smoothing_sigma_green_px':2,'sample_stride_green_px':4,'focus_band_half_width_green_px':300,
                'workers':1,'fit':'affine image motion, gain/offset, uniform Laplacian, tilt-normal times Laplacian'},
            'interpretation':'Focus coefficient distinguishes repeatable optical response after nuisance fitting; not micrometres or a calibrated actuator step.',
            'runs':results}
    (OUT/'pair-response.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
