"""Independent bounded ribbon reference and root-only control entry point.

Truth uses analytic vertical capsule/pupil intervals and shifted Halton3
integration; producer uses point-distance predicates and paired Sobol4 rays.
No RAW files, fitted sensor calibration, image volumes, or parameter sweeps.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import time

import numpy as np

HERE = Path(__file__).resolve().parent
SENSOR = dict(black=512.0, white=15360.0,
              read_variance=[9.0, 9.0, 9.0, 12.0], shot=[.15, .13, .13, .17])
ORIGIN = np.array([104.0, 78.0])
WIDTH, HEIGHT = 32, 28
VIEWS = np.array([[.10, 0, 0], [.25, .37, -.21], [.45, -.32, .41],
                  [.60, .48, .16], [.80, -.17, -.38], [1.0, .23, .29],
                  [1.15, -.41, -.11]], dtype=np.float32)
TRAIN_VIEWS, HELD_VIEWS = [0, 1, 3, 4, 6], [2, 5]
SCALE = 3.2
START = None


def checkpoint():
    if START is not None and time.monotonic() - START > 112:
        raise RuntimeError("independent internal112second bound; no repeat or rescue")


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scene_spec():
    return dict(endpoints=np.array([[[5.2, 8.4], [26.1, 18.75]],
                                    [[11.1, 3.4], [20.6, 24.2]]]) + ORIGIN,
                radii=np.array([.28, .19]), depths=np.array([.25, .80]),
                colors=np.array([[2600., 6100., 1900.], [6500., 2100., 5800.],
                                 [3300., 3500., 3700.]]), background_depth=1.5)


def queries():
    yy, xx = np.mgrid[:HEIGHT, :WIDTH]
    xy = np.stack([xx.ravel(), yy.ravel()], 1).astype(np.float32) + ORIGIN.astype(np.float32)
    phase = (2 * (xy[:, 1].astype(np.int64) % 2) + xy[:, 0].astype(np.int64) % 2)
    return dict(xy=np.tile(xy, (len(VIEWS), 1)), phase=np.tile(phase, len(VIEWS)),
                view=np.repeat(np.arange(len(VIEWS), dtype=np.int64), len(xy))), xy


def take(q, indices):
    return {key: value[indices] for key, value in q.items()}


def radical(index, base):
    result = np.zeros(len(index), dtype=np.float64)
    denominator = float(base)
    remaining = index.copy()
    while np.any(remaining):
        result += (remaining % base) / denominator
        remaining //= base
        denominator *= base
    return result


def halton(count, dimensions):
    # Independent of the producer's unscrambled Sobol generator. Fixed shift,
    # bases, offset, and counts are prospective, never selected from results.
    indices = np.arange(513, 513 + count, dtype=np.int64)
    shift = [.1732050807568877, .4193139346887673, .6837722339831621, .2915026221291814]
    return np.stack([(radical(indices, base) + shift[i]) % 1
                     for i, base in enumerate([2, 3, 5, 7][:dimensions])], 1)


def linear_interval(offset, coefficient, lower, upper):
    shape = np.broadcast_shapes(np.shape(offset), np.shape(coefficient), np.shape(lower), np.shape(upper))
    good = np.broadcast_to(np.abs(coefficient) > 1e-14, shape)
    a, b = np.zeros(shape), np.zeros(shape)
    np.divide(lower - offset, coefficient, out=a, where=good)
    np.divide(upper - offset, coefficient, out=b, where=good)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    inside = (offset >= lower) & (offset <= upper)
    lo = np.where(good, lo, np.where(inside, -np.inf, np.inf))
    hi = np.where(good, hi, np.where(inside, np.inf, -np.inf))
    valid_bounds = lower <= upper
    return np.where(valid_bounds, lo, np.inf), np.where(valid_bounds, hi, -np.inf)


def vertical_capsule(x, endpoint, radius):
    """Exact vertical interval from finite rectangle UNION endpoint disks."""
    a, b = endpoint
    direction = b - a
    length = float(np.linalg.norm(direction))
    tx, ty = direction / length
    dx = x - a[0]
    al, ah = linear_interval(tx * dx, ty, 0.0, length)
    nl, nh = linear_interval(-ty * dx, tx, -radius, radius)
    low, high = np.maximum(al, nl) + a[1], np.minimum(ah, nh) + a[1]
    valid = low <= high
    low, high = np.where(valid, low, np.inf), np.where(valid, high, -np.inf)
    for center in [a, b]:
        radicand = radius * radius - (x - center[0]) ** 2
        extent = np.sqrt(np.maximum(radicand, 0))
        low = np.minimum(low, np.where(radicand >= 0, center[1] - extent, np.inf))
        high = np.maximum(high, np.where(radicand >= 0, center[1] + extent, -np.inf))
    # Convexity guarantees that nonempty pieces form one contiguous interval.
    return low, high


def reference_moments(spec, q, count=8192, views=VIEWS, scale=SCALE):
    """Return P(hit0), P(hit1), P(both); integrate pupil-y analytically."""
    nodes = halton(count, 3)
    px, sx, sy = 2 * nodes[:, 0] - 1, nodes[:, 1] - .5, nodes[:, 2] - .5
    extent = np.sqrt(np.maximum(1 - px * px, 0))
    result = np.empty((len(q['xy']), 3), dtype=np.float64)
    for start in range(0, len(result), 16):
        checkpoint()
        stop = min(start + 16, len(result))
        v = views[q['view'][start:stop]]
        center = q['xy'][start:stop].astype(np.float64) + v[:, 1:3]
        intervals = []
        for layer in range(2):
            d = (scale * (spec['depths'][layer] - v[:, 0]))[:, None]
            x = center[:, 0, None] + sx + d * px
            low_y, high_y = vertical_capsule(x, spec['endpoints'][layer], spec['radii'][layer])
            low, high = linear_interval(center[:, 1, None] + sy, d, low_y, high_y)
            intervals.append((np.maximum(low, -extent), np.minimum(high, extent)))
        (lo0, hi0), (lo1, hi1) = intervals
        lengths = [np.maximum(hi0 - lo0, 0), np.maximum(hi1 - lo1, 0),
                   np.maximum(np.minimum(hi0, hi1) - np.maximum(lo0, lo1), 0)]
        result[start:stop] = np.stack([v.mean(1) * (2 / math.pi) for v in lengths], 1)
    return result


def weights(moments, depths, alpha=(1.0, 1.0), reverse=False, marginal=False):
    near, far = np.argsort(depths)
    if reverse:
        near, far = far, near
    overlap = moments[:, 0] * moments[:, 1] if marginal else moments[:, 2]
    w = np.empty_like(moments)
    w[:, near] = alpha[near] * moments[:, near]
    w[:, far] = alpha[far] * moments[:, far] - alpha[near] * alpha[far] * overlap
    w[:, 2] = 1 - w[:, 0] - w[:, 1]
    return w


def signals(spec, q, w):
    channels = np.array([0, 1, 1, 2])[q['phase']]
    return (w * spec['colors'][:, channels].T).sum(1)


def pinhole_reference(spec, xy, nodes=512, alpha=(1.0, 1.0)):
    gx, gw = np.polynomial.legendre.leggauss(nodes)
    x = xy[:, 0, None] + .5 * gx
    intervals = []
    for i in range(2):
        low, high = vertical_capsule(x, spec['endpoints'][i], spec['radii'][i])
        intervals.append((np.maximum(low, xy[:, 1, None] - .5),
                          np.minimum(high, xy[:, 1, None] + .5)))
    (l0, h0), (l1, h1) = intervals
    lengths = [np.maximum(h0-l0, 0), np.maximum(h1-l1, 0),
               np.maximum(np.minimum(h0,h1)-np.maximum(l0,l1), 0)]
    moments = np.stack([v @ (.5 * gw) for v in lengths], 1)
    w = weights(moments, spec['depths'], alpha)
    return w @ spec['colors'], moments


def sigma(signal, phase):
    return np.sqrt(np.asarray(SENSOR['read_variance'])[phase]
                   + np.asarray(SENSOR['shot'])[phase] * np.maximum(signal, 0))


def observe(signal, q, seed):
    draw = np.random.default_rng(seed).standard_normal(len(signal))
    value = SENSOR['black'] + signal + draw * sigma(signal, q['phase'])
    if not np.all((value > 1) & (value < SENSOR['white'] - 1)):
        raise ValueError('Fixture unexpectedly clips; no censor treatment or amplitude retuning')
    return np.rint(value).astype(np.uint16)


def glint_signal(q, count=4096):
    points = halton(count, 4)
    radius, angle = np.sqrt(points[:, 0]), 2 * np.pi * points[:, 1]
    pupil = np.stack([radius * np.cos(angle), radius * np.sin(angle)], 1)
    footprint = points[:, 2:4] - .5
    center, spread = ORIGIN + [16.2, 13.4], .65
    background, amplitude = np.array([3300., 3500., 3700.]), np.array([2700., 3200., 1200.])
    result = np.empty(len(q['xy']))
    channels = np.array([0, 1, 1, 2])[q['phase']]
    for start in range(0, len(result), 32):
        checkpoint()
        stop = min(start+32, len(result))
        v = VIEWS[q['view'][start:stop]]
        point = q['xy'][start:stop,None,:] + v[:,None,1:3] + footprint
        point = point + (SCALE * (.55-v[:,0]))[:,None,None] * pupil
        response = np.exp(-((point-center)**2).sum(2)/(2*spread*spread)).mean(1)
        ch = channels[start:stop]
        result[start:stop] = background[ch] + amplitude[ch]*response
    return result


def prediction_score(prediction, codes, truth_signal, phase):
    error = (prediction - codes.astype(np.float64)) / sigma(truth_signal, phase)
    return dict(rms_sigma=float(np.sqrt(np.mean(error**2))),
                mean_sigma=float(error.mean()),
                phase_rms_sigma=[float(np.sqrt(np.mean(error[phase==p]**2))) for p in range(4)])


def image_score(image, truth, moments, background):
    masks = dict(near=(moments[:,0]>.025)&(moments[:,1]<.01),
                 far=(moments[:,1]>.025)&(moments[:,0]<.01),
                 crossing=(moments[:,0]>.025)&(moments[:,1]>.025))
    result = dict(rgb_rmse_dn=float(np.sqrt(np.mean((image-truth)**2))))
    for name, mask in masks.items():
        target = truth[mask] - background
        denominator = float((target**2).sum())
        result[name] = dict(pixels=int(mask.sum()),
                            rgb_rmse_dn=float(np.sqrt(np.mean((image[mask]-truth[mask])**2))),
                            component=float(((image[mask]-background)*target).sum()/denominator))
    return result


def main():
    global START
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    START = time.monotonic()
    report = dict(status='STARTED', photographic_quality_admitted=False,
                  sensor=SENSOR, units='original-native sensor centers; signalDN; depth synthetic; scale3.2nativepx/depth',
                  views=VIEWS.tolist(), train_views=TRAIN_VIEWS, held_views=HELD_VIEWS,
                  sources={p.name:sha(p) for p in [Path(__file__),HERE/'model.py']})
    def save():
        report['elapsed_seconds'] = time.monotonic()-START
        dump(args.out/'observations.json', report)
    save()
    try:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('GPU required; no implicit CPU fit')
        torch.set_num_threads(1)
        torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        report['runtime']=dict(torch_version=torch.__version__,cuda_version=torch.version.cuda,
            matmul_allow_tf32=torch.backends.cuda.matmul.allow_tf32,
            cudnn_allow_tf32=torch.backends.cudnn.allow_tf32,cpu_workers=1)
        total = torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(min(1.0, (4*1024**3)/total), 0)
        torch.cuda.reset_peak_memory_stats()
        report['gpu'] = dict(name=torch.cuda.get_device_name(0), total_bytes=total,
                             allocator_limit_bytes=min(total,4*1024**3),
                             scope='Torch allocator cap; excludes driver/runtime/compiler memory')
        module_spec = importlib.util.spec_from_file_location('ribbon_producer', HERE/'model.py')
        model = importlib.util.module_from_spec(module_spec)
        import sys
        sys.modules[module_spec.name] = model
        module_spec.loader.exec_module(model)
        q, xy = queries()
        spec = scene_spec()
        views = torch.tensor(VIEWS, device='cuda')
        optics = model.Optics(SCALE)
        pupil, footprint = model.quadrature(11)
        allq = model.make_queries(**q)
        scene = model.make_scene(**spec)
        flat = {**spec, 'colors':np.tile([3300.,3500.,3700.],(3,1))}
        flat_scene = model.make_scene(**flat)
        channels = np.array([0,1,1,2])[q['phase']]
        flat_signal = flat['colors'][2,channels]
        flat_codes = observe(flat_signal,q,73921)
        flat_prediction = model.predict(flat_scene,allq,views,optics,pupil,footprint).cpu().numpy()
        report['flat_first'] = dict(max_forward_dn=float(np.max(np.abs(flat_prediction-SENSOR['black']-flat_signal))),
                                   noise=prediction_score(flat_signal+SENSOR['black'],flat_codes,flat_signal,q['phase']),
                                   geometry_identified=False, reason='equal colors; no-element and capsule geometry observationally equivalent')
        np.savez(args.out/'flat-observations.npz',**q,codes=flat_codes,truth_signal=flat_signal)
        save()
        if report['flat_first']['max_forward_dn']>.02:
            report['status']='FLAT_FORWARD_REFUSAL';save();return
        moments = reference_moments(spec,q)
        w = weights(moments,spec['depths'])
        signal = signals(spec,q,w)
        codes = observe(signal,q,81937)
        truth, image_moments = pinhole_reference(spec,xy)
        # Fixed selection independent of a candidate or residual, including all
        # phases and full extent plus named cap/crossing neighbourhoods.
        selected = np.unique(np.r_[np.linspace(0,len(signal)-1,40,dtype=int),
            [v*WIDTH*HEIGHT+y*WIDTH+x for v in [1,3,4] for x,y in [(5,8),(26,19),(11,3),(21,24),(16,14),(17,13)]]])
        dense_moments = reference_moments(spec,take(q,selected),32768)
        dense_signal = signals(spec,take(q,selected),weights(dense_moments,spec['depths']))
        reference_error = signal[selected]-dense_signal
        normalized = reference_error/sigma(dense_signal,q['phase'][selected])
        report['reference_precision'] = dict(standard_joint_nodes=8192,dense_joint_nodes=32768,
            selected_indices=selected.tolist(),rms_dn=float(np.sqrt(np.mean(reference_error**2))),
            max_dn=float(np.abs(reference_error).max()),rms_sigma=float(np.sqrt(np.mean(normalized**2))),
            max_sigma=float(np.abs(normalized).max()),
            scope='analytic pupil-y; independent shifted Halton3 pupil-x/footprint integral; finite density comparison not rigorous bound')
        np.savez(args.out/'crossing-observations.npz',**q,codes=codes,truth_signal=signal,
                 truth_pinhole=truth.reshape(HEIGHT,WIDTH,3),visibility_moments=moments,
                 selected=selected,dense_signal=dense_signal)
        save()
        if report['reference_precision']['rms_sigma']>.1 or report['reference_precision']['max_sigma']>.5:
            report['status']='REFERENCE_DENSITY_UNQUALIFIED';save();return
        predicted = model.predict(scene,allq,views,optics,pupil,footprint).cpu().numpy()-SENSOR['black']
        diff = (predicted-signal)/sigma(signal,q['phase'])
        reverse = signals(spec,q,weights(moments,spec['depths'],reverse=True))
        marginal = signals(spec,q,weights(moments,spec['depths'],marginal=True))
        pin = model.pinhole(scene,torch.tensor(xy,device='cuda'),footprint).cpu().numpy()
        report['forward'] = dict(rms_sigma=float(np.sqrt(np.mean(diff**2))),max_sigma=float(np.abs(diff).max()),
            reversed_order_rms_dn=float(np.sqrt(np.mean((reverse-signal)**2))),
            marginal_product_rms_dn=float(np.sqrt(np.mean((marginal-signal)**2))),
            pinhole=image_score(pin,truth,image_moments,spec['colors'][2]))
        translated = {**spec,'endpoints':spec['endpoints']+[.375,-.25]}
        shifted_views = VIEWS.copy();shifted_views[:,1:3]-=np.array([.375,-.25])
        a = model.predict(model.make_scene(**translated),allq,views,optics,pupil,footprint).cpu().numpy()
        b = model.predict(scene,allq,torch.tensor(shifted_views,device='cuda'),optics,pupil,footprint).cpu().numpy()
        report['translation_identity_max_dn']=float(np.max(np.abs(a-b)))
        report['translation_identity_scope']='ungated finite-sampling observation, not displacement-estimator validation'
        np.savez(args.out/'forward-outputs.npz',prediction=predicted,reverse_order=reverse,
                 marginal_product=marginal,producer_pinhole=pin.reshape(HEIGHT,WIDTH,3))
        # Independent mismatch data are preserved before any fit/assertion.
        translucent = signals(spec,q,weights(moments,spec['depths'],alpha=(.35,1.0)))
        glint = glint_signal(q)
        np.savez(args.out/'mismatch-observations.npz',**q,
            translucent_codes=observe(translucent,q,92713),translucent_signal=translucent,
            glint_codes=observe(glint,q,92171),glint_signal=glint)
        report['mismatch'] = dict(translucent_alpha=[.35,1.0],
            constant_background_transmittance_color_gauge=True,
            glint_has_opaque_objects=False,producer_background_model='constant',
            fixed_opaque_translucent_rms_sigma=float(np.sqrt(np.mean(((predicted-translucent)/sigma(translucent,q['phase']))**2))),
            constant_background_glint_rms_sigma=float(np.sqrt(np.mean(((flat_signal-glint)/sigma(glint,q['phase']))**2))),
            automatic_refusal_demonstrated=False,scope='fixed out-of-model observations; not additional fit campaigns')
        save()
        if report['forward']['rms_sigma']>.35 or report['forward']['max_sigma']>2:
            report['status']='FORWARD_QUADRATURE_REFUSAL';save();return
        precision = max(.02,4*report['reference_precision']['rms_dn'])
        if min(report['forward']['reversed_order_rms_dn'],report['forward']['marginal_product_rms_dn'])<=precision:
            report['status']='VISIBILITY_FOIL_UNEXERCISED';save();return
        # Independent component metric destroyers, not a source selector.
        destroyed=[]
        for index,name in [(0,'near'),(1,'far')]:
            bad=truth.copy();mask=(image_moments[:,index]>.025)&(image_moments[:,1-index]<.01)
            bad[mask]=spec['colors'][2]
            score=image_score(bad,truth,image_moments,spec['colors'][2])
            destroyed.append(dict(erased=name,component=score[name]['component'],rejected=score[name]['component']<.9))
        report['component_destroyers']=destroyed
        save()
        rng=np.random.default_rng(36271)
        train=np.sort(np.concatenate([rng.choice(np.flatnonzero((q['view']==v)&(q['phase']==p)),24,replace=False)
                                      for v in TRAIN_VIEWS for p in range(4)]))
        held=np.flatnonzero(np.isin(q['view'],HELD_VIEWS))
        initial={**spec,'endpoints':spec['endpoints']+np.array([[[-.31,.26],[.27,-.35]],[[-.22,-.28],[.33,.24]]]),
                 'radii':spec['radii']*[1.25,.80],'depths':spec['depths']+[.08,-.09],
                 'colors':np.tile([3400.,3400.,3400.],(3,1))}
        init=model.make_scene(**initial)
        parameters=np.r_[initial['endpoints'].ravel(),initial['radii'],initial['depths']]
        lower=np.r_[parameters[:8]-1.5,[.08,.08,.05,.05]]
        upper=np.r_[parameters[:8]+1.5,[.65,.65,1.25,1.25]]
        steps=np.r_[np.full(8,.25),[.06,.06,.08,.08]]
        trainq=take({**q,'codes':codes},train)
        report['fit_contract']=dict(train_indices=train.tolist(),held_indices=held.tolist(),
            initial_geometry=parameters.tolist(),lower=lower.tolist(),upper=upper.tolist(),steps=steps.tolist(),
            true_radiance_supplied=False,topology_supplied=True,optics_supplied=True)
        save()
        result=model.fit_geometry(init,model.make_queries(**trainq),views,optics,pupil,footprint,SENSOR,lower,upper,steps)
        fitted=result.pop('scene')
        fitted_predictions=model.predict(fitted,allq,views,optics,pupil,footprint).cpu().numpy()
        fitted_image=model.pinhole(fitted,torch.tensor(xy,device='cuda'),footprint).cpu().numpy()
        initial_image=model.pinhole(init,torch.tensor(xy,device='cuda'),footprint).cpu().numpy()
        score=image_score(fitted_image,truth,image_moments,spec['colors'][2])
        report['fit']=result
        report['fit']['held']=prediction_score(fitted_predictions[held],codes[held],signal[held],q['phase'][held])
        report['fit']['pinhole']=score
        report['fit']['initial_pinhole']=image_score(initial_image,truth,image_moments,spec['colors'][2])
        report['fit']['initial_pinhole_scope']='uniform3400DN null image; no radiance-refit initial-geometry image retained; gain is not attributed to geometry'
        report['fit']['geometry']={key:getattr(fitted,key).cpu().tolist() for key in ['endpoints','radii','depths','colors']}
        np.savez(args.out/'fit-outputs.npz',prediction=fitted_predictions,
            final_pinhole=fitted_image.reshape(HEIGHT,WIDTH,3),initial_pinhole=initial_image.reshape(HEIGHT,WIDTH,3),
            truth_pinhole=truth.reshape(HEIGHT,WIDTH,3),train_indices=train,held_indices=held)
        save()
        held_rng=np.random.default_rng(36621)
        independent_held=np.sort(np.concatenate([held_rng.choice(np.flatnonzero((q['view']==v)&(q['phase']==p)),8,replace=False)
                                                 for v in HELD_VIEWS for p in range(4)]))
        fitted_spec={key:np.array(value) for key,value in report['fit']['geometry'].items()}
        fitted_spec['background_depth']=float(fitted.background_depth)
        held_q=take(q,independent_held)
        held_moments=reference_moments(fitted_spec,held_q,32768)
        held_reference=signals(fitted_spec,held_q,weights(held_moments,fitted_spec['depths']))+SENSOR['black']
        report['fit']['independent_held_selected']=dict(indices=independent_held.tolist(),
            score=prediction_score(held_reference,codes[independent_held],signal[independent_held],q['phase'][independent_held]),
            producer_reference_rms_dn=float(np.sqrt(np.mean((held_reference-fitted_predictions[independent_held])**2))),
            scope='64 balanced held physical queries; dense independent final-state operator, not full held array')
        np.savez(args.out/'fit-outputs.npz',prediction=fitted_predictions,
            final_pinhole=fitted_image.reshape(HEIGHT,WIDTH,3),initial_pinhole=initial_image.reshape(HEIGHT,WIDTH,3),
            truth_pinhole=truth.reshape(HEIGHT,WIDTH,3),train_indices=train,held_indices=held,
            independent_held_indices=independent_held,independent_held_prediction=held_reference)
        report['fit']['conditional_detail_pass']=all(score[name]['component']>=.9 for name in ['near','far','crossing'])
        report['fit']['held_prediction_pass']=report['fit']['held']['rms_sigma']<=1.5
        report['status']='BOUNDED_CONTROL_COMPLETE'
        report['scope']='conditional two-capsule unknowngeometry fit; mismatch refusal/topology/fullphoto remain unimplemented'
        report['gpu']['peak_allocated_bytes']=torch.cuda.max_memory_allocated()
        report['gpu']['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
        save()
    except Exception as error:
        report['status']='ERROR_OR_BOUND_REFUSAL'
        report['error']=repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
