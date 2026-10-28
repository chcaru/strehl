"""Two hard opaque capsules, original-sensel queries, paired pupil/footprint rays.

Synthetic prototype only. No RAW decoder, calibration, image-stack fusion, alpha
lattice, photographic admission, or automatic topology discovery is implemented.
All reconstruction arithmetic is float32; observed codes remain uint16 until use.
"""
from dataclasses import dataclass, replace
import math
import torch


@dataclass(frozen=True)
class Scene:
    endpoints: torch.Tensor  # [object=2, endpoint=2, xy=2], native pixel units
    radii: torch.Tensor      # [2], positive native pixels; round finite end caps
    depths: torch.Tensor     # [2], increasing away from camera
    colors: torch.Tensor     # [object0, object1, background; RGB], signal DN
    background_depth: float  # beyond both capsules; inactive for constant color


@dataclass(frozen=True)
class Optics:
    defocus_scale: float  # native-pixel pupil displacement / depth unit


def make_scene(endpoints, radii, depths, colors, background_depth=1.5, device="cuda"):
    as_float = lambda x: torch.as_tensor(x, device=device, dtype=torch.float32)
    return Scene(as_float(endpoints), as_float(radii), as_float(depths),
                 as_float(colors), float(background_depth))


def make_queries(xy, phase, view, codes=None, device="cuda"):
    result = dict(xy=torch.as_tensor(xy, device=device, dtype=torch.float32),
                  phase=torch.as_tensor(phase, device=device, dtype=torch.int64),
                  view=torch.as_tensor(view, device=device, dtype=torch.int64))
    if codes is not None:
        value = torch.as_tensor(codes, device=device)
        if value.dtype != torch.uint16:
            raise ValueError("Original observations must enter as uint16, not rounded model data")
        result["codes"] = value
    return result


def quadrature(power=11, device="cuda"):
    """Fixed UNSCRAMBLED Sobol4D, 2**power equally weighted PAIRED rows.

    u0,u1 -> uniform unit disk; u2,u3 -> unit square sensor footprint.
    These are joint quadrature samples, not independent marginal coverages.
    The independent analytic reference, not this function, supplies truth.
    """
    if power < 1 or power > 14:
        raise ValueError("Bounded quadrature power1..14 required")
    points = torch.quasirandom.SobolEngine(4, scramble=False).draw_base2(power)
    points = points.to(device=device, dtype=torch.float32)
    radius = torch.sqrt(points[:, 0])
    angle = (2.0 * math.pi) * points[:, 1]
    pupil = torch.stack((radius * torch.cos(angle), radius * torch.sin(angle)), 1)
    return pupil, points[:, 2:4] - 0.5


def _validate_scene(scene, device):
    if device.type != "cuda":
        raise ValueError("Commissioned GPU consumer required; no CPU execution fallback")
    arrays = [scene.endpoints, scene.radii, scene.depths, scene.colors]
    if any(a.device != device or a.dtype != torch.float32 or not torch.isfinite(a).all().item()
           for a in arrays):
        raise ValueError("All geometry/radiance/optics arrays must be finite same-device float32")
    if (scene.endpoints.shape != (2, 2, 2) or scene.radii.shape != (2,)
            or scene.depths.shape != (2,) or scene.colors.shape != (3, 3)):
        raise ValueError("Exactly two finite capsules and three constant RGB colors required")
    if not ((scene.radii > 0).all().item() and (scene.colors >= 0).all().item()
            and (scene.depths < scene.background_depth).all().item()
            and abs(float(scene.depths[0] - scene.depths[1])) >= 0.01):
        raise ValueError("Positive radius/radiance, finite order gap and farther background required")
    lengths = ((scene.endpoints[:, 1] - scene.endpoints[:, 0]) ** 2).sum(1)
    if not (lengths >= 0.25).all().item():
        raise ValueError("Finite capsule centerline lengths must be at least0.5native pixels")


def _validate(scene, queries, views, optics, pupil, footprint):
    device = queries["xy"].device
    _validate_scene(scene, device)
    if any(a.device != device or a.dtype != torch.float32 or not torch.isfinite(a).all().item()
           for a in (queries["xy"], views, pupil, footprint)):
        raise ValueError("Finite same-device float32 physical query/optical arrays required")
    if not math.isfinite(optics.defocus_scale) or optics.defocus_scale < 0:
        raise ValueError("Finite nonnegative defocus scale required")
    n = queries["xy"].shape[0]
    if (queries["xy"].shape != (n, 2) or views.ndim != 2 or views.shape[1] != 3
            or pupil.ndim != 2 or pupil.shape[1] != 2 or pupil.shape != footprint.shape
            or not 1 <= pupil.shape[0] <= 16384):
        raise ValueError("Paired Kx2 pupil/footprint, physical Nx2 queries and Vx3 views required")
    if not ((pupil.square().sum(1) <= 1.000001).all().item()
            and (footprint.abs() <= 0.5).all().item()):
        raise ValueError("Unit disk pupil and square[-.5,.5] footprint required")
    for key, upper in (("phase", 4), ("view", len(views))):
        value = queries[key]
        if (value.device != device or value.dtype != torch.int64 or value.shape != (n,)
                or not ((value >= 0) & (value < upper)).all().item()):
            raise ValueError("Invalid original CFA phase/view identity")
    # Source coordinates, not reference-transformed positions, choose CFA phase.
    xy = queries["xy"]
    if not torch.equal(xy, torch.round(xy)):
        raise ValueError("Observation queries must be physical integer sensel centers")
    phase = 2 * torch.remainder(xy[:, 1].long(), 2) + torch.remainder(xy[:, 0].long(), 2)
    if not torch.equal(phase, queries["phase"]):
        raise ValueError("RGGB phase does not match original physical sensel coordinate")
    if "codes" in queries and (queries["codes"].dtype != torch.uint16
                              or queries["codes"].device != device
                              or queries["codes"].shape != (n,)):
        raise ValueError("Original code storage must remain one uint16 per sensel query")


def _hit(points, endpoint, radius):
    direction = endpoint[1] - endpoint[0]
    relative = points - endpoint[0]
    t = ((relative * direction).sum(-1) / direction.square().sum()).clamp(0.0, 1.0)
    separation = relative - t[..., None] * direction
    return separation.square().sum(-1) <= radius.square()


def _weights(scene, xy, view_rows, optics, pupil, footprint):
    # One paired pupil+footprint row is reused across both layers before averaging.
    reference = xy[:, None, :] + view_rows[:, None, 1:3] + footprint[None, :, :]
    hits = []
    for layer in range(2):
        shear = optics.defocus_scale * (scene.depths[layer] - view_rows[:, 0])
        points = reference + shear[:, None, None] * pupil[None, :, :]
        hits.append(_hit(points, scene.endpoints[layer], scene.radii[layer]))
    near, far = (0, 1) if float(scene.depths[0]) < float(scene.depths[1]) else (1, 0)
    near_hit, far_hit = hits[near], ~hits[near] & hits[far]
    # The third weight uses the JOINT neither-hit event. Never multiply mean coverages.
    background = ~hits[near] & ~hits[far]
    masks = [None, None, background]
    masks[near], masks[far] = near_hit, far_hit
    return torch.stack([mask.to(torch.float32).mean(1) for mask in masks], 1)


@torch.no_grad()
def visibility_weights(scene, queries, views, optics, pupil_xy, footprint_xy, batch_queries=128):
    _validate(scene, queries, views, optics, pupil_xy, footprint_xy)
    if not 1 <= batch_queries <= 256:
        raise ValueError("Query batch1..256 required")
    result = torch.empty((len(queries["xy"]), 3), device=queries["xy"].device, dtype=torch.float32)
    for lo in range(0, len(result), batch_queries):
        hi = min(len(result), lo + batch_queries)
        result[lo:hi] = _weights(scene, queries["xy"][lo:hi], views[queries["view"][lo:hi]],
                                 optics, pupil_xy, footprint_xy)
    return result


def _channel(phase):
    return torch.tensor([0, 1, 1, 2], device=phase.device, dtype=torch.int64)[phase]


@torch.no_grad()
def predict(scene, queries, views, optics, pupil_xy, footprint_xy, black=512.0, batch_queries=128):
    weights = visibility_weights(scene, queries, views, optics, pupil_xy, footprint_xy, batch_queries)
    colors = scene.colors[:, _channel(queries["phase"])].transpose(0, 1)
    return (weights * colors).sum(1) + float(black)


@torch.no_grad()
def pinhole(scene, xy, footprint_xy, batch_queries=128):
    """Final footprint-integrated pinhole camera RGB, signal DN, no remosaic/MHC.

    xy may be arbitrary final-image centers; it does not choose original CFA phase.
    A zero pupil uses the same paired footprint rows as the source forward.
    """
    _validate_scene(scene, xy.device)
    if (xy.device.type != "cuda" or xy.dtype != torch.float32 or xy.ndim != 2
            or xy.shape[1] != 2 or footprint_xy.dtype != torch.float32
            or footprint_xy.device != xy.device or footprint_xy.ndim != 2
            or footprint_xy.shape[1] != 2 or not 1 <= len(footprint_xy) <= 16384
            or not torch.isfinite(xy).all().item()
            or not torch.isfinite(footprint_xy).all().item()
            or not (footprint_xy.abs() <= 0.5).all().item()
            or not 1 <= batch_queries <= 256):
        raise ValueError("GPU float32 final-image coordinates and bounded batch required")
    result = torch.empty((len(xy), 3), device=xy.device, dtype=torch.float32)
    for lo in range(0, len(xy), batch_queries):
        hi = min(len(xy), lo + batch_queries)
        weights = _weights(scene, xy[lo:hi], torch.zeros((hi-lo, 3), device=xy.device, dtype=torch.float32),
                           Optics(0.0), torch.zeros_like(footprint_xy), footprint_xy)
        result[lo:hi] = weights @ scene.colors
    return result


def _geometry(scene):
    return torch.cat((scene.endpoints.flatten(), scene.radii, scene.depths))


def _with_geometry(scene, parameters):
    return replace(scene, endpoints=parameters[:8].reshape(2, 2, 2),
                   radii=parameters[8:10], depths=parameters[10:12])


def _observation_terms(queries, sensor):
    if "codes" not in queries or queries["codes"].dtype != torch.uint16:
        raise ValueError("Original uint16 observations required for inference")
    codes = queries["codes"].to(torch.float32)
    black, white = float(sensor["black"]), float(sensor["white"])
    if not math.isfinite(black) or not math.isfinite(white) or not 0 <= black < white <= 65535:
        raise ValueError("Finite ordered uint16 sensor levels required")
    if not torch.isfinite(codes).all().item() or not ((codes > 0) & (codes < white)).all().item():
        raise ValueError("First inference has no censor likelihood: saturated/bottom-clipped queries refused")
    phase = queries["phase"]
    read = torch.as_tensor(sensor["read_variance"], device=codes.device, dtype=torch.float32)
    shot = torch.as_tensor(sensor["shot"], device=codes.device, dtype=torch.float32)
    if (read.shape != (4,) or shot.shape != (4,) or not torch.isfinite(read).all().item()
            or not torch.isfinite(shot).all().item()
            or not ((read > 0) & (shot >= 0)).all().item()):
        raise ValueError("One supplied positive four-phase noise model required")
    signal = codes - black
    variance = read[phase] + shot[phase] * signal.clamp_min(0.0)
    # Freeze supplied heteroscedastic weights at observed signal for all candidates.
    # This is feasible weighted LS, not a fitted variance or exact Gaussian NLL.
    return signal, variance.reciprocal(), white-black


def _colors(weights, channel, signal, inverse_variance, maximum):
    grams, rhs = [], []
    for c in range(3):
        keep = channel == c
        if int(keep.sum()) < 8:
            raise ValueError("At least8 original observations per physical color required")
        w, inv, y = weights[keep], inverse_variance[keep], signal[keep]
        grams.append(w.transpose(0, 1) @ (inv[:, None] * w))
        rhs.append(w.transpose(0, 1) @ (inv * y))
    gram, target = torch.stack(grams), torch.stack(rhs)
    eigen, vectors = torch.linalg.eigh(gram)
    cutoff = eigen[:, -1:] * 1e-6
    retained = eigen > cutoff
    inverse = torch.where(retained, eigen.clamp_min(torch.finfo(torch.float32).tiny).reciprocal(), 0.0)
    coefficients = (vectors @ (inverse[:, :, None] * (vectors.transpose(1, 2) @ target[:, :, None]))).squeeze(-1)
    coefficients = coefficients.clamp(0.0, maximum)
    # Always execute the fixed projected iterations, including when LS was in-box.
    # No private noise/prior, no adaptive repeat or claim of exact constrained optimum.
    step = eigen[:, -1:].clamp_min(torch.finfo(torch.float32).tiny).reciprocal()
    for _ in range(24):
        gradient = (gram @ coefficients[:, :, None]).squeeze(-1) - target
        coefficients = (coefficients - step * gradient).clamp(0.0, maximum)
    gradient = (gram @ coefficients[:, :, None]).squeeze(-1) - target
    projected = coefficients - (coefficients - step * gradient).clamp(0.0, maximum)
    info = dict(rank_by_rgb=retained.sum(1).cpu().tolist(),
                eigenvalues_by_rgb=eigen.cpu().tolist(),
                projected_step_max=float(projected.abs().max()),
                bound_components=int(((coefficients == 0) | (coefficients == maximum)).sum()),
                identified=False, reason="rank is conditional on geometry; it cannot establish geometric identifiability")
    return coefficients.transpose(0, 1).contiguous(), info


@torch.no_grad()
def fit_geometry(initial, queries, views, optics, pupil_xy, footprint_xy, sensor,
                 lower, upper, steps, sweep_scales=(1.0, 0.5, 0.25), max_evaluations=73,
                 batch_queries=128):
    """One bounded derivative-free coordinate search, training queries only.

    Parameters: endpoints8, radii2, depths2. Candidate moves are +/- fixed steps
    at three predetermined scales. Each candidate refits9 constant colors using
    the same observed-noise weights. No alpha surrogate/autograd geometry, truth,
    held data, per-pixel radiance fit, topology creation or convergence claim.
    """
    _validate(initial, queries, views, optics, pupil_xy, footprint_xy)
    if not 48 <= len(queries["xy"]) <= 512 or tuple(sweep_scales) != (1.0, 0.5, 0.25) or max_evaluations != 73:
        raise ValueError("Frozen48..512 query/three-sweep/73-evaluation contract required")
    device = initial.endpoints.device
    lower, upper, steps = [torch.as_tensor(v, device=device, dtype=torch.float32) for v in (lower, upper, steps)]
    if any(v.shape != (12,) or not torch.isfinite(v).all().item() for v in (lower, upper, steps)):
        raise ValueError("Finite12-vector bounds/steps required")
    if not ((upper > lower) & (steps > 0)).all().item():
        raise ValueError("Ordered bounds and positive fixed steps required")
    parameters = _geometry(initial).clone()
    if not ((parameters >= lower) & (parameters <= upper)).all().item():
        raise ValueError("Initialization outside declared bounds")
    signal, inv, maximum = _observation_terms(queries, sensor)
    channel = _channel(queries["phase"])
    null_colors = torch.stack([(signal[channel == c] * inv[channel == c]).sum() / inv[channel == c].sum()
                               for c in range(3)]).clamp(0.0, maximum)
    null_prediction = null_colors[channel]
    null_loss = float(((null_prediction - signal).square() * inv).mean())
    evaluations, rejected_geometry = 0, 0

    def evaluate(p):
        nonlocal evaluations, rejected_geometry
        evaluations += 1
        if evaluations > max_evaluations:
            raise RuntimeError("Fixed evaluation budget exceeded")
        scene = _with_geometry(initial, p)
        try:
            weights = visibility_weights(scene, queries, views, optics, pupil_xy, footprint_xy, batch_queries)
        except ValueError:
            rejected_geometry += 1
            return math.inf, None, None
        colors, information = _colors(weights, channel, signal, inv, maximum)
        prediction = (weights * colors[:, channel].transpose(0, 1)).sum(1)
        loss = float(((prediction - signal).square() * inv).mean())
        return loss, replace(scene, colors=colors), information

    best_loss, best_scene, best_information = evaluate(parameters)
    if best_scene is None or not math.isfinite(best_loss):
        raise ValueError("Initial geometry refused")
    trace = [dict(evaluation=evaluations, phase="initial", normalized_mse=best_loss,
                  parameters=parameters.cpu().tolist())]
    for sweep, scale in enumerate(sweep_scales):
        for coordinate in range(12):
            base = parameters.clone()
            chosen = None
            for sign in (-1.0, 1.0):
                proposal = base.clone()
                proposal[coordinate] = torch.clamp(base[coordinate] + sign * scale * steps[coordinate],
                                                   lower[coordinate], upper[coordinate])
                loss, scene, information = evaluate(proposal)
                if loss < best_loss:
                    best_loss, best_scene, best_information = loss, scene, information
                    chosen = proposal
            if chosen is not None:
                parameters = chosen
            trace.append(dict(evaluation=evaluations, phase="coordinate", sweep=sweep,
                              coordinate=coordinate, changed=chosen is not None,
                              normalized_mse=best_loss, parameters=parameters.cpu().tolist()))
    return dict(scene=best_scene, trace=trace, evaluations=evaluations,
                rejected_geometry=rejected_geometry, normalized_mse=best_loss,
                null_constant_mse=null_loss, null_constant_rgb=null_colors.cpu().tolist(),
                conditional_radiance=best_information, identified=False, converged=False,
                training_queries=len(signal), held_queries_seen=0,
                saturated_training_supported=False, topology="fixed two finite capsules",
                scope="bounded joint geometry/constant-radiance research fit; no quality admission")
