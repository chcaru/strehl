"""Four fixed majorizer-scaled CFA residual updates from an explicit initializer.

Uses the frozen Lanczos3 observation matrix, provided variances, and no L prior,
CG, hidden demosaic or private noise estimate. Four iterations are prescribed,
not optimized. Weak observation modes stay near the caller's initial image.
"""
from pathlib import Path
import hashlib
import importlib.util
import numpy as np

BASIS_PATH = Path(__file__).with_name("joint-cfa-lanczos.py")
BASIS_SHA256 = "3e5b208df4f3f43d97ef2669c95a8252b6eb9526c86216c685bb555f674e15d4"
assert hashlib.sha256(BASIS_PATH.read_bytes()).hexdigest() == BASIS_SHA256
_spec = importlib.util.spec_from_file_location("backprojection_frozen_lanczos",BASIS_PATH)
_basis = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_basis)
ITERATIONS = 4


def reconstruct(shape,xy,values,variance,channels,valid,initial_rgb):
    """Return (RGBf32, diagnostics) in the initializer's radiometric/native grid.

    Input conventions match joint-cfa-lanczos; initial_rgb is required finite
    HxWx3 f32 and is never modified. Complete6x6 support requires2<=x<W-3,
    2<=y<H-3. Invalid/clipped observations must have valid=False. D0 pixels
    and channels with no usable observations retain initial bits, not recovered
    data. Diagnostics include final predictions/residuals and support counts.
    """
    h,w = tuple(shape)
    assert isinstance(h,(int,np.integer)) and isinstance(w,(int,np.integer)) and min(h,w)>=2
    xy,values,variance,channels,valid,initial = map(np.asarray,(xy,values,variance,channels,valid,initial_rgb))
    n = len(values)
    assert xy.dtype==np.float64 and xy.shape==(n,2)
    assert values.dtype==variance.dtype==np.float32 and values.shape==variance.shape==(n,)
    assert np.issubdtype(channels.dtype,np.integer) and channels.shape==(n,) and np.isin(channels,[0,1,2]).all()
    assert valid.dtype==np.bool_ and valid.shape==(n,)
    assert initial.dtype==np.float32 and initial.shape==(h,w,3) and np.isfinite(initial).all()
    finite = np.isfinite(xy).all(axis=1)&np.isfinite(values)&np.isfinite(variance)
    positive = variance>np.float32(0)
    inside = (xy[:,0]>=2)&(xy[:,1]>=2)&(xy[:,0]<w-3)&(xy[:,1]<h-3)
    eligible = valid&finite&positive&inside
    result = initial.copy()
    predictions = np.full(n,np.nan,dtype=np.float32)
    residuals = np.full(n,np.nan,dtype=np.float32)
    support = np.zeros((h,w,3),dtype=np.uint32)
    summaries = []
    for channel,name in enumerate(("R","G","B")):
        indices = np.flatnonzero(eligible&(channels==channel))
        if not len(indices):
            summaries.append(dict(channel=name,status="NO_USABLE_DATA_INITIAL_PRESERVED",observations=0,
                data_supported_pixels=0,initial_only_pixels=h*w,iterations=0))
            continue
        a = _basis._design((h,w),xy[indices])
        transpose = a.T.tocsr()
        absolute = a.copy()
        absolute.data = np.abs(absolute.data)
        row_l1 = np.asarray(absolute.sum(axis=1)).ravel()
        v = values[indices]
        median_variance = np.float32(np.median(variance[indices]))
        weights = median_variance/variance[indices]
        assert weights.dtype==np.float32 and np.isfinite(weights).all() and (weights>0).all()
        diagonal = absolute.T@(weights*row_l1)
        assert diagonal.dtype==np.float32 and np.isfinite(diagonal).all() and (diagonal>=0).all()
        live = diagonal>np.float32(0)
        count = np.bincount(a.indices,minlength=h*w).astype(np.uint32)
        support[...,channel] = count.reshape(h,w)
        solution = initial[...,channel].ravel().copy()
        before = a@solution-v
        energy = [float(np.sum(weights*before*before,dtype=np.float32))]
        maximum_updates = []
        for _ in range(ITERATIONS):
            correction = transpose@(weights*(v-a@solution))
            update = correction[live]/diagonal[live]
            # Do not even add +0 at D0: preserve signed zero and all initial bits.
            solution[live] += update
            assert solution.dtype==np.float32 and np.isfinite(solution).all()
            error = a@solution-v
            energy.append(float(np.sum(weights*error*error,dtype=np.float32)))
            maximum_updates.append(float(np.max(np.abs(update))) if len(update) else 0.0)
        assert np.array_equal(solution[~live].view(np.uint32),initial[...,channel].ravel()[~live].view(np.uint32))
        predicted = a@solution
        residual = predicted-v
        predictions[indices] = predicted
        residuals[indices] = residual
        result[...,channel] = solution.reshape(h,w)
        summaries.append(dict(channel=name,status="FOUR_FIXED_UPDATES_COMPLETED",observations=len(indices),
            data_supported_pixels=int(live.sum()),initial_only_pixels=int((~live).sum()),
            support_min=int(count.min()),support_max=int(count.max()),iterations=ITERATIONS,
            median_provided_variance=float(median_variance),majorizer_min=float(diagonal.min()),majorizer_max=float(diagonal.max()),
            weighted_data_energy_by_step=energy,max_abs_update_by_step=maximum_updates,
            initial_data_rmse=float(np.sqrt(np.mean(before*before,dtype=np.float32))),
            data_rmse=float(np.sqrt(np.mean(residual*residual,dtype=np.float32))),
            weighted_data_rmse=float(np.sqrt(np.sum(weights*residual*residual,dtype=np.float32)/np.sum(weights,dtype=np.float32))),
            mean_residual=float(np.mean(residual,dtype=np.float32)),max_abs_residual=float(np.max(np.abs(residual))),
            mean_squared_residual_over_provided_variance=float(np.mean(residual*residual/variance[indices],dtype=np.float32))))
    diagnostic = dict(shape=[h,w],channels=summaries,fixed_iterations=ITERATIONS,basis_sha256=BASIS_SHA256,
        update="x+=A.T@(w*(v-A@x))/D on D>0, D=abs(A).T@(w*row_sum(abs(A)))",
        regularization="Fixed four updates from explicit initializer; no L prior, no CG, no adaptive stopping",
        weight_convention="median(provided channel variance)/variance; common scale cancels numerator and majorizer, no noise estimate",
        observations_total=n,observations_used=int(eligible.sum()),supplied_invalid=int((~valid).sum()),
        valid_nonfinite=int((valid&~finite).sum()),valid_finite_nonpositive_variance=int((valid&finite&~positive).sum()),
        valid_finite_positive_outside=int((valid&finite&positive&~inside).sum()),
        predictions=predictions,data_residuals=residuals,support_counts=support,used_mask=eligible,
        limits="D0 and no-data channels preserve the initial image, not recovered observations. Initializer quality is an explicit dependency. Data-residual decrease is not image-quality evidence. Noise, blur mismatch and geometry errors remain potential failures.")
    return result,diagnostic
