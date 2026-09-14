"""Fixed green-only local translation discriminator; saved CFA, no RAW decode.

delta is added in SOURCE native pixels after the saved reference->source map.
Fit/validation use disjoint raw support, and validation never refits gain/bias.
Lower guide residual is a geometry diagnostic, not a reconstructed-image verdict.
"""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
SIGMA, RADIUS, MAX_SHIFT, FD_STEP = 1.5, 6, 4.0, .02
MARGIN, SPLIT, GAP, STRIDE = 32, 196, 12, 2


def guide(cfa, origin=(0,0), usable=None):
    y,x = np.indices(cfa.shape)
    mask = (x+origin[0]+y+origin[1])%2 == 1
    if usable is not None:
        mask &= usable
    numerator = gaussian_filter(np.where(mask,cfa,np.float32(0)).astype(np.float32),
        sigma=SIGMA,mode="mirror",truncate=4.0)
    denominator = gaussian_filter(mask.astype(np.float32),sigma=SIGMA,mode="mirror",truncate=4.0)
    assert denominator.min()>0, "unsupported normalized green guide"
    result = numerator/denominator
    assert result.dtype == np.float32 and np.isfinite(result).all()
    return result


def grids():
    yy,xx = np.mgrid[MARGIN:392-MARGIN:STRIDE,MARGIN:SPLIT-GAP:STRIDE]
    left = np.column_stack((xx.ravel(),yy.ravel())).astype(np.float64)
    yy,xx = np.mgrid[MARGIN:392-MARGIN:STRIDE,SPLIT+GAP:392-MARGIN:STRIDE]
    right = np.column_stack((xx.ravel(),yy.ravel())).astype(np.float64)
    return left,right


def sample(image,xy):
    assert np.isfinite(xy).all() and (xy>=0).all()
    assert (xy[:,0]<image.shape[1]-1).all() and (xy[:,1]<image.shape[0]-1).all()
    return map_coordinates(image,[xy[:,1],xy[:,0]],order=1,mode="nearest",prefilter=False).astype(np.float64)


def profile(source,target,positions,delta):
    observed = sample(source,positions+delta)
    gain,bias = np.linalg.lstsq(np.column_stack((observed,np.ones_like(observed))),target,rcond=None)[0]
    return gain,bias,gain*observed+bias-target


def fit(source,reference_left,reference_right,source_left,source_right):
    # Include all optimizer shifts, finite-difference probes and sample support.
    source_radius = RADIUS+MAX_SHIFT+FD_STEP+1
    assert source_left[:,0].max()+source_radius < source_right[:,0].min()-source_radius, "train/validation source support overlaps"
    def residual(delta):
        return profile(source,reference_left,source_left,delta)[2]
    def jacobian(delta):
        columns = []
        for axis in (0,1):
            step = np.zeros(2,dtype=np.float64)
            step[axis] = FD_STEP
            columns.append((residual(delta+step)-residual(delta-step))/(2*FD_STEP))
        return np.column_stack(columns)
    solution = least_squares(residual,np.zeros(2),jac=jacobian,bounds=(-MAX_SHIFT,MAX_SHIFT),
        max_nfev=50,ftol=1e-8,xtol=1e-8,gtol=1e-8)
    def reading(delta):
        gain,bias,error = profile(source,reference_left,source_left,delta)
        validation = gain*sample(source,source_right+delta)+bias-reference_right
        return dict(delta_source_native=np.asarray(delta).tolist(),gain_left=float(gain),bias_left=float(bias),
            gain_positive=bool(gain>0),fit_rmse=float(np.sqrt(np.mean(error**2))),
            validation_rmse=float(np.sqrt(np.mean(validation**2))),
            validation_mean_error=float(np.mean(validation)),validation_max_abs=float(np.max(np.abs(validation))))
    return dict(before=reading(np.zeros(2)),after=reading(solution.x),delta_source_native=solution.x.tolist(),
        converged=bool(solution.success),status=int(solution.status),message=solution.message,nfev=solution.nfev,
        optimality=float(solution.optimality),at_translation_bound=bool(np.any(np.abs(solution.x)>3.99)),
        fit_samples=len(reference_left),validation_samples=len(reference_right),
        source_support_gap_native=float(source_right[:,0].min()-source_left[:,0].max()-2*source_radius)),reading


def mapped(local,origin,centre,a,b_plane,source_origin):
    z = local[:,0]+1j*local[:,1]+complex(*origin)
    s = centre+a*(z-centre)+2*b_plane-complex(*source_origin)
    return np.column_stack((s.real,s.imag))


def continuous(z,blur_sigma):
    result = np.full(z.shape,.34,dtype=np.float64)
    for amplitude,fx,fy,phase in ((.10,.033,.017,.2),(.08,-.021,.041,1.1),(.04,.063,-.029,.7)):
        attenuation = np.exp(-2*np.pi**2*blur_sigma**2*(fx*fx+fy*fy))
        result += amplitude*attenuation*np.cos(2*np.pi*(fx*z.real+fy*z.imag)+phase)
    return result.astype(np.float32)


def controls():
    left,right = grids()
    yy,xx = np.mgrid[:392,:392]
    z = xx+1j*yy
    centre = complex(196,196)
    a,b = complex(1.001,.0004),complex(.12,-.08)
    reference = guide(continuous(z,0))
    reference_left,reference_right = sample(reference,left),sample(reference,right)
    positions = [mapped(p,(0,0),centre,a,b,(0,0)) for p in (left,right)]
    results = []
    for label,known,blur in (("same-focus-shift",(.37,-.62),0),
                             ("mild-blur-shift",(.37,-.62),.45),("blur-only",(0,0),.45)):
        delta = complex(*known)
        world = centre+(z-centre-2*b-delta)/a
        cfa = continuous(world,blur)*np.float32(1.07)+np.float32(.013)
        # Make R/B deliberately unrelated: the guide must only consume true G.
        cfa[(xx+yy)%2==0] = np.float32(7)
        source = guide(cfa)
        result,reading = fit(source,reference_left,reference_right,*positions)
        error = float(np.linalg.norm(np.array(result["delta_source_native"])-known))
        assert result["converged"] and error<.05, "predeclared .05-native translation recovery failed"
        result.update(label=label,known_delta_source_native=list(known),source_extra_blur_sigma_native=blur,
                      translation_error_native=error,tolerance_native=.05)
        if known != (0,0):
            wrong = reading(-np.array(known))
            assert wrong["validation_rmse"]>result["before"]["validation_rmse"]
            assert wrong["validation_rmse"]>2*result["after"]["validation_rmse"], "wrong-sign control lacked power"
            result["wrong_sign"] = wrong
        results.append(result)
    return results


def main():
    started = time.process_time()
    out = HERE/"local-green-translation-1"
    out.mkdir(exist_ok=False)
    design = dict(guide_sigma_native=SIGMA,guide_support_radius_native=RADIUS,guide_boundary="whole-sample mirror",
        guide="normalized Gaussian of original G sites only; clipped G excluded; no R/B or MHC",
        coordinates="source=C+a*(reference-C)+2*b_plane+delta_source_native",
        fit="x32..182, y32..358, stride2",validation="x208..358, y32..358, stride2; no nuisance refit",
        finite_difference_absolute_step_native=FD_STEP,translation_bounds_native=[-4,4],
        nuisance="gain/bias profiled by linear least squares on left only; sign reported",
        gate="known shifted controls error<.05native, blur-only delta norm<.05; wrong sign must worsen validation",
        interpretation="predictive guide alignment only; no within-DOF, geometric-truth or photographic-quality claim")
    (out/"design.json").write_text(json.dumps(design,indent=2)+"\n",encoding="utf-8")
    control_results = controls()  # must pass before opening saved photographic CFA
    (out/"controls.json").write_text(json.dumps(control_results,indent=2)+"\n",encoding="utf-8")
    folder = HERE/"joint-raw-samples-2"
    receipt = json.loads((folder/"receipt.json").read_text())
    assert receipt["reference_index"]==149 and receipt["target_shape"]==[392,392]
    origin = receipt["target_origin_native"]
    sensor_h,sensor_w = receipt["native_sensor_shape"]
    centre = complex(sensor_w/2,sensor_h/2)
    guides = {}
    for record in receipt["frames"]:
        raw = np.load(folder/f"frame-{record['index']}-cfa.npy",allow_pickle=False)
        assert raw.dtype==np.uint16 and hashlib.sha256(raw.tobytes()).hexdigest()==record["raw_u16_sha256"]
        assert raw.shape==tuple(reversed(record["source_xywh"][2:]))
        black,white = map(np.float32,receipt["levels"])
        normalized = (raw.astype(np.float32)-black)/(white-black)
        guides[record["index"]] = guide(normalized,record["source_xywh"][:2],raw<16383)
    reference_record = next(r for r in receipt["frames"] if r["index"]==149)
    left,right = grids()
    ref_positions = [mapped(p,origin,centre,complex(*reference_record["a"]),complex(*reference_record["b_plane"]),reference_record["source_xywh"][:2]) for p in (left,right)]
    reference_left,reference_right = [sample(guides[149],p) for p in ref_positions]
    rows = []
    for record in receipt["frames"]:
        positions = [mapped(p,origin,centre,complex(*record["a"]),complex(*record["b_plane"]),record["source_xywh"][:2]) for p in (left,right)]
        result,_ = fit(guides[record["index"]],reference_left,reference_right,*positions)
        result["frame"] = record["index"]
        result["source_xywh"] = record["source_xywh"]
        result["validation_ratio"] = result["after"]["validation_rmse"]/result["before"]["validation_rmse"] if result["before"]["validation_rmse"]>0 else None
        rows.append(result)
        print(json.dumps({k:result[k] for k in ("frame","delta_source_native","validation_ratio","converged")}),flush=True)
    elapsed = time.process_time()-started
    assert elapsed<60
    result = dict(status="LOCAL_TRANSLATION_DIAGNOSTIC",design=design,controls=control_results,frames=rows,
        source_receipt=str(folder/"receipt.json"),source_map_sha256=receipt["map_sha256"],cpu_seconds=elapsed)
    (out/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
