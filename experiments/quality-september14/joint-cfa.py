"""Fixed native1x CFA least squares prototype; no RAW decoder or demosaic.

Geometry is f64, image arithmetic f32. Each channel minimizes
sum_j w_j*(A_j*x-v_j)^2 + .01*x.T*L*x, where L is the 5-point graph
Laplacian: a first-difference prior, NOT a squared-Laplacian penalty.
Bilinear A can attenuate real continuous detail and exaggerate inferred contrast;
independent continuous-scene truth must test this model discrepancy.
"""
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import LinearOperator, cg

LAMBDA = np.float32(0.01)
MAX_ITERATIONS = 80
RTOL = 1e-5


def _laplacian(shape):
    h, w = shape
    n = h*w
    degree = np.full(shape, np.float32(4))
    degree[0] -= np.float32(1)
    degree[-1] -= np.float32(1)
    degree[:, 0] -= np.float32(1)
    degree[:, -1] -= np.float32(1)
    horizontal = -np.ones(n-1, dtype=np.float32)
    horizontal[np.arange(w-1, n-1, w)] = np.float32(0)
    vertical = -np.ones(n-w, dtype=np.float32)
    matrix = sparse.diags((vertical, horizontal, degree.ravel(), horizontal, vertical),
                          (-w, -1, 0, 1, w), shape=(n,n), dtype=np.float32, format="csr")
    matrix.eliminate_zeros()
    return matrix, degree.ravel()


def _design(shape, xy):
    h, w = shape
    ix = np.floor(xy[:,0]).astype(np.int32)
    iy = np.floor(xy[:,1]).astype(np.int32)
    fx = (xy[:,0]-ix).astype(np.float32)
    fy = (xy[:,1]-iy).astype(np.float32)
    one = np.float32(1)
    weights = np.column_stack(((one-fx)*(one-fy), fx*(one-fy), (one-fx)*fy, fx*fy))
    base = iy*w+ix
    columns = np.column_stack((base, base+1, base+w, base+w+1))
    rows = np.repeat(np.arange(len(xy), dtype=np.int32),4)
    matrix = sparse.coo_matrix((weights.ravel(),(rows,columns.ravel())),
                               shape=(len(xy),h*w),dtype=np.float32).tocsr()
    matrix.eliminate_zeros()
    return matrix


def reconstruct(shape, xy, values, variance, channels, valid):
    """Return (HxWx3 f32 RGB, diagnostics), no clipping or hidden noise estimate.

    xy is Nx2 f64 in patch-local native pixel centres (x,y). values/variance
    are f32 in identical radiometric units, channels integer 0=R,1=G,2=B;
    valid is boolean and must already exclude clipped/unusable observations.
    Strict complete4tap support excludes x>=W-1 or y>=H-1. Diagnostics retain
    f32 predictions/residuals and uint32 support_counts; unused observations
    have NaN predictions. A channel with no usable observations remains NaN.
    """
    h, w = tuple(shape)
    assert isinstance(h,(int,np.integer)) and isinstance(w,(int,np.integer)) and min(h,w)>=2
    xy,values,variance,channels,valid = map(np.asarray,(xy,values,variance,channels,valid))
    n = len(values)
    assert xy.dtype == np.float64 and xy.shape == (n,2)
    assert values.dtype == variance.dtype == np.float32 and values.shape == variance.shape == (n,)
    assert np.issubdtype(channels.dtype,np.integer) and channels.shape == (n,) and np.isin(channels,[0,1,2]).all()
    assert valid.dtype == np.bool_ and valid.shape == (n,)
    finite = np.isfinite(xy).all(axis=1) & np.isfinite(values) & np.isfinite(variance)
    positive = variance > np.float32(0)
    inside = (xy[:,0]>=0)&(xy[:,1]>=0)&(xy[:,0]<w-1)&(xy[:,1]<h-1)
    eligible = valid & finite & positive & inside
    result = np.full((h,w,3),np.nan,dtype=np.float32)
    predictions = np.full(n,np.nan,dtype=np.float32)
    residuals = np.full(n,np.nan,dtype=np.float32)
    support = np.zeros((h,w,3),dtype=np.uint32)
    laplacian,degree = _laplacian((h,w))
    summaries = []
    for channel,name in enumerate(("R","G","B")):
        indices = np.flatnonzero(eligible & (channels==channel))
        if not len(indices):
            summaries.append(dict(channel=name,status="NO_USABLE_OBSERVATIONS",observations=0,
                data_supported_pixels=0,prior_only_pixels=h*w,converged=False))
            continue
        a = _design((h,w),xy[indices])
        v = values[indices]
        median_variance = np.float32(np.median(variance[indices]))
        weights = median_variance/variance[indices]
        assert weights.dtype==np.float32 and np.isfinite(weights).all() and (weights>0).all()
        transpose = a.T.tocsr()
        rhs = transpose @ (weights*v)
        diagonal = a.multiply(a).T @ weights + LAMBDA*degree
        assert (diagonal>0).all() and np.isfinite(diagonal).all()
        count = np.bincount(a.indices,minlength=h*w).astype(np.uint32)
        support[...,channel] = count.reshape(h,w)
        normalization = transpose @ weights
        mean = np.sum(weights*v,dtype=np.float32)/np.sum(weights,dtype=np.float32)
        initial = np.full(h*w,mean,dtype=np.float32)
        np.divide(rhs,normalization,out=initial,where=normalization>0)
        def multiply(x):
            assert x.dtype==np.float32
            return transpose @ (weights*(a@x)) + LAMBDA*(laplacian@x)
        operator = LinearOperator((h*w,h*w),matvec=multiply,dtype=np.float32)
        preconditioner = LinearOperator((h*w,h*w),matvec=lambda x:x/diagonal,dtype=np.float32)
        iterations = [0]
        def callback(_):
            iterations[0] += 1
        solution,info = cg(operator,rhs,x0=initial,rtol=RTOL,atol=0.0,maxiter=MAX_ITERATIONS,
                           M=preconditioner,callback=callback)
        assert solution.dtype==np.float32 and np.isfinite(solution).all()
        predicted = a@solution
        residual = predicted-v
        predictions[indices] = predicted
        residuals[indices] = residual
        result[...,channel] = solution.reshape(h,w)
        normal_residual = multiply(solution)-rhs
        rhs_norm = np.linalg.norm(rhs)
        relative = float(np.linalg.norm(normal_residual)/rhs_norm) if rhs_norm>0 else float(np.linalg.norm(normal_residual))
        summaries.append(dict(channel=name,status="CONVERGED" if info==0 else "CG_NOT_CONVERGED",
            observations=len(indices),data_supported_pixels=int(np.count_nonzero(count)),
            prior_only_pixels=int(np.count_nonzero(count==0)),support_min=int(count.min()),support_max=int(count.max()),
            median_provided_variance=float(median_variance),converged=info==0,cg_info=int(info),iterations=iterations[0],
            relative_normal_residual=relative,
            data_rmse=float(np.sqrt(np.mean(residual*residual,dtype=np.float32))),
            weighted_data_rmse=float(np.sqrt(np.sum(weights*residual*residual,dtype=np.float32)/np.sum(weights,dtype=np.float32))),
            mean_residual=float(np.mean(residual,dtype=np.float32)),max_abs_residual=float(np.max(np.abs(residual))),
            mean_squared_residual_over_provided_variance=float(np.mean(residual*residual/variance[indices],dtype=np.float32))))
    diagnostics = dict(shape=[h,w],channels=summaries,lambda_first_difference=float(LAMBDA),max_iterations=MAX_ITERATIONS,rtol=RTOL,
        observations_total=n,observations_used=int(eligible.sum()),supplied_invalid=int((~valid).sum()),
        valid_nonfinite=int((valid&~finite).sum()),valid_finite_nonpositive_variance=int((valid&finite&~positive).sum()),
        valid_finite_positive_outside=int((valid&finite&positive&~inside).sum()),
        predictions=predictions,data_residuals=residuals,support_counts=support,used_mask=eligible,
        limits="First-difference algorithm prior, not sensor calibration. Unsupported pixels may be prior-filled; no all-clipped recovery claim. CG convergence is algebraic, not image quality. Bilinear forward-model error, blur mismatch and geometry error are unmodelled.")
    return result,diagnostics
