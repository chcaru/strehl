"""Bounded anchor-relative original-CFA hypothesis; no RAW reader or quality gate.

Mechanics reuse the documented Lanczos axis basis, supplied-noise NLL and
matrix-Cauchy prior. The caller owns independent truth and operational acceptance.
"""
from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import torch
import torch.nn.functional as F

RADIUS = 64
MAX_VARIANCE = 256.0
MAX_EVALUATIONS = 160
PHASE_CHANNEL = np.asarray([0, 1, 1, 2], dtype=np.int64)


@dataclass
class Config:
    field_hw: tuple
    output_xywh: tuple
    shot4: tuple
    read4: tuple
    black4: tuple
    saturation: int
    anchor_id: int
    device: str = "cuda"
    _output_matrix: object = field(default=None, init=False, repr=False)

    def __post_init__(self):
        self.field_hw = tuple(int(v) for v in self.field_hw)
        self.output_xywh = tuple(int(v) for v in self.output_xywh)
        if len(self.field_hw) != 2 or len(self.output_xywh) != 4:
            raise ValueError("field_hw and output_xywh dimensions")
        h, w = self.field_hw
        x, y, ow, oh = self.output_xywh
        if not (2 <= ow <= 128 and 2 <= oh <= 128 and h == oh+144 and w == ow+144
                and x == y == 72):
            raise ValueError("requires <=128 panel with exactly72-native apron")
        for name in ("shot4", "read4", "black4"):
            value = tuple(float(v) for v in getattr(self, name))
            if len(value) != 4 or not all(math.isfinite(v) for v in value):
                raise ValueError("four finite phase coefficients required")
            setattr(self, name, value)
        if min(self.shot4) < 0 or min(self.read4) < 0:
            raise ValueError("negative injected noise")
        if not (0 < self.saturation <= 65535 and min(self.black4) >= 0
                and max(self.black4) < self.saturation):
            raise ValueError("invalid digital levels")
        if type(self.anchor_id) is not int or self.device != "cuda":
            raise ValueError("integer anchor and explicit CUDA required")

    def public(self):
        return {k: getattr(self, k) for k in ("field_hw", "output_xywh", "shot4",
            "read4", "black4", "saturation", "anchor_id", "device")}


@dataclass
class Query:
    original_xy: np.ndarray
    phase: np.ndarray
    nodes_xy: np.ndarray
    footprint_weights: np.ndarray
    _cache: dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        xy, phase, nodes, weight = (np.asarray(v) for v in (self.original_xy,
            self.phase, self.nodes_xy, self.footprint_weights))
        n = len(xy)
        if not (xy.dtype == np.int32 and xy.shape == (n, 2) and 0 < n <= 128*128):
            raise ValueError("original_xy must be nonempty int32 Nx2 <=128square")
        if len(np.unique(xy, axis=0)) != n:
            raise ValueError("a view may observe each original sensel only once")
        if phase.dtype != np.uint8 or phase.shape != (n,) or np.any(phase > 3):
            raise ValueError("phase must be uint8 R/G1/G2/B")
        physical = (xy[:, 1] & 1)*2+(xy[:, 0] & 1)
        if not np.array_equal(phase, physical.astype(np.uint8)):
            raise ValueError("CFA phase disagrees with original physical coordinates")
        if nodes.dtype != np.float64 or nodes.shape != (n, 9, 2) or not np.isfinite(nodes).all():
            raise ValueError("nodes_xy must be finite f64 Nx9x2 latent coordinates")
        if (weight.dtype != np.float32 or weight.shape != (9,) or not np.isfinite(weight).all()
                or np.any(weight <= 0) or abs(float(weight.sum(dtype=np.float64))-1) > 1e-6):
            raise ValueError("positive normalized f32 nine-node footprint weights required")
        self.original_xy, self.phase, self.nodes_xy, self.footprint_weights = (
            np.array(v, copy=True) for v in (xy, phase, nodes, weight))
        for value in (self.original_xy, self.phase, self.nodes_xy, self.footprint_weights):
            value.flags.writeable = False


@dataclass
class View:
    source_id: int
    query: Query
    codes: np.ndarray

    def __post_init__(self):
        codes = np.asarray(self.codes)
        if type(self.source_id) is not int or codes.dtype != np.uint16 or codes.shape != self.query.phase.shape:
            raise ValueError("View requires integer ID and original u16 codes matching query")
        self.codes = np.array(codes, copy=True)
        self.codes.flags.writeable = False


def _axis_weights(coordinates, integer):
    # Same normalized six-tap basis as quality-september14/joint-cfa-lanczos.py.
    offsets = np.arange(-2, 4, dtype=np.int32)
    distance = (coordinates[:, None]-(integer[:, None]+offsets[None, :])).astype(np.float32)
    angle = np.float32(np.pi)*distance
    angle3 = angle/np.float32(3)
    sinc, window = np.ones_like(distance), np.ones_like(distance)
    nonzero = distance != np.float32(0)
    np.divide(np.sin(angle), angle, out=sinc, where=nonzero)
    np.divide(np.sin(angle3), angle3, out=window, where=nonzero)
    weights = sinc*window
    weights[np.abs(distance) >= np.float32(3)] = np.float32(0)
    exact = coordinates == integer
    weights[exact, :] = np.float32(0)
    weights[exact, 2] = np.float32(1)
    weights /= np.sum(weights, axis=1, keepdims=True, dtype=np.float32)
    return weights


def _matrix(nodes, footprint_weights, channels, config):
    """Coalesce duplicate footprint taps; no dense per-source RGB image."""
    h, w = config.field_hw
    n = len(nodes)
    points = nodes.reshape(-1, 2)
    integer = np.floor(points).astype(np.int64)
    if (np.any(integer[:, 0]-2 < RADIUS) or np.any(integer[:, 1]-2 < RADIUS)
            or np.any(integer[:, 0]+3+RADIUS >= w) or np.any(integer[:, 1]+3+RADIUS >= h)):
        raise ValueError("query lacks fixed64-blur plus Lanczos footprint apron")
    wx = _axis_weights(points[:, 0], integer[:, 0])
    wy = _axis_weights(points[:, 1], integer[:, 1])
    weights = (wy[:, :, None]*wx[:, None, :]).reshape(n, 9, 36)
    weights *= footprint_weights[None, :, None]
    offsets = np.arange(-2, 4, dtype=np.int64)
    sites = ((integer[:, 1, None, None]+offsets[None, :, None])*w
        +(integer[:, 0, None, None]+offsets[None, None, :])).reshape(n, 9, 36)
    columns = sites*3+np.asarray(channels, dtype=np.int64)[:, None, None]
    rows = np.broadcast_to(np.arange(n, dtype=np.int64)[:, None, None], weights.shape)
    indices = np.stack((rows.reshape(-1), columns.reshape(-1)))
    matrix = torch.sparse_coo_tensor(torch.from_numpy(indices).to(config.device),
        torch.from_numpy(weights.reshape(-1).copy()).to(config.device),
        (n, h*w*3), dtype=torch.float32, device=config.device).coalesce()
    # The analytic footprint/basis preserves DC. Normalize only accumulated
    # finite table mass, not data values or residuals.
    mass = torch.zeros(n, dtype=torch.float32, device=config.device)
    mass.scatter_add_(0, matrix.indices()[0], matrix.values())
    if not bool(torch.isfinite(mass).all()) or bool((mass <= 0).any()):
        raise ValueError("invalid forward row mass")
    return torch.sparse_coo_tensor(matrix.indices(), matrix.values()/mass[matrix.indices()[0]],
        matrix.shape, dtype=torch.float32, device=config.device).coalesce()


def _prepared(query, config):
    key = (config.field_hw, config.device, config.shot4, config.read4, config.black4)
    if key not in query._cache:
        phase = torch.from_numpy(query.phase.astype(np.int64)).to(config.device)
        query._cache[key] = (_matrix(query.nodes_xy, query.footprint_weights,
            PHASE_CHANNEL[query.phase], config), phase,
            torch.tensor(config.black4, dtype=torch.float32, device=config.device)[phase],
            torch.tensor(config.shot4, dtype=torch.float32, device=config.device)[phase],
            torch.tensor(config.read4, dtype=torch.float32, device=config.device)[phase])
    return query._cache[key]


def _blur(x, variance):
    if not torch.is_tensor(variance):
        variance = x.new_tensor(float(variance))
    if variance.dtype != torch.float32 or variance.ndim != 0:
        raise ValueError("variance must be scalar f32")
    variance = variance.to(device=x.device)
    if not bool(torch.isfinite(variance)) or not 0 <= float(variance.detach()) <= MAX_VARIANCE:
        raise ValueError("relative variance out of bounds")
    if float(variance.detach()) == 0:
        return x
    offsets = torch.arange(-RADIUS, RADIUS+1, dtype=torch.float32, device=x.device)
    kernel = torch.exp(-offsets.square()/(2*variance))
    kernel = kernel/kernel.sum()
    value = x.permute(2, 0, 1).unsqueeze(0)
    value = F.conv2d(value, kernel.reshape(1, 1, 1, -1).expand(3, 1, 1, -1),
        padding=(0, RADIUS), groups=3)
    value = F.conv2d(value, kernel.reshape(1, 1, -1, 1).expand(3, 1, -1, 1),
        padding=(RADIUS, 0), groups=3)
    return value[0].permute(1, 2, 0)


def forward(x_rgb_dn_f32, variance_f32, query, config):
    """HWC signal DN -> N original sensel DN including black; differentiable."""
    x = x_rgb_dn_f32
    if not torch.is_tensor(x):
        a = np.asarray(x)
        if a.dtype != np.float32:
            raise ValueError("X must be f32")
        x = torch.from_numpy(a).to(config.device)
    if x.dtype != torch.float32 or tuple(x.shape) != (*config.field_hw, 3):
        raise ValueError("X shape/dtype differs")
    matrix, _, black, _, _ = _prepared(query, config)
    return torch.sparse.mm(matrix, _blur(x, variance_f32).reshape(-1, 1))[:, 0]+black


def _nll(mu, codes, query, config):
    _, _, black, shot, read = _prepared(query, config)
    variance = shot*(mu-black).clamp_min(0)+read+mu.new_tensor(1/12)
    # Retain original observations as u16; convert only the current view's math.
    observed = codes.to(dtype=torch.float32)
    return (torch.log(variance)+(observed-mu).square()/variance).mean()*mu.new_tensor(.5)


def _prior(x, config):
    # Physical-DN matrix-Cauchy expression, normalized per observed output area.
    # Free apron must not dilute the central data/prior balance.
    h, w, _ = x.shape
    coefficients = x.new_tensor([config.shot4[1], config.shot4[2],
        config.read4[1], config.read4[2]])
    b = torch.sqrt(2*(coefficients[:2].mean()*2048+coefficients[2:].mean()+x.new_tensor(1/12)))
    dx = torch.cat(((x[:, 1:]-x[:, :-1])*math.sqrt(w/(w-1))/b,
        torch.zeros_like(x[:, :1])), dim=1)
    dy = torch.cat(((x[1:]-x[:-1])*math.sqrt(h/(h-1))/b,
        torch.zeros_like(x[:1])), dim=0)
    cross = torch.linalg.cross(dx, dy, dim=-1)
    _, _, ow, oh = config.output_xywh
    return torch.log1p((dx.square().sum(-1)+dy.square().sum(-1))/4
        +cross.square().sum(-1)/16).sum()/(ow*oh)


def _output_matrix(config):
    if config._output_matrix is None:
        ox, oy, w, h = config.output_xywh
        yy, xx = np.mgrid[:h, :w]
        points = np.stack((xx.ravel()+ox, yy.ravel()+oy), axis=1).astype(np.float64)
        t = math.sqrt(3/5)/2
        axis = np.asarray([-t, 0., t], dtype=np.float64)
        wy, wx = np.meshgrid(axis, axis, indexing="ij")
        offsets = np.stack((wx.ravel(), wy.ravel()), axis=1)
        a = np.asarray([5/18, 4/9, 5/18], dtype=np.float32)
        weight = (a[:, None]*a[None, :]).reshape(9)
        nodes = np.repeat((points[:, None, :]+offsets[None, :, :]), 3, axis=0)
        channels = np.tile(np.arange(3, dtype=np.int64), len(points))
        config._output_matrix = _matrix(nodes, weight, channels, config)
    return config._output_matrix


def _deliver_x(x, config):
    _, _, w, h = config.output_xywh
    return torch.sparse.mm(_output_matrix(config), x.reshape(-1, 1))[:, 0].reshape(h, w, 3)


def integrate_reference(x_rgb_dn_f32, config):
    """Public known-X output integration seam; HWC f32 signal DN -> HWC f32."""
    x = x_rgb_dn_f32
    if not torch.is_tensor(x):
        a = np.asarray(x)
        if a.dtype != np.float32:
            raise ValueError("X must be f32")
        x = torch.from_numpy(a).to(config.device)
    if x.dtype != torch.float32 or tuple(x.shape) != (*config.field_hw, 3):
        raise ValueError("X shape/dtype differs")
    return _deliver_x(x, config)


def _initialize(anchor, config):
    xy, phase = anchor.query.original_xy, anchor.query.phase
    ox, oy, w, h = config.output_xywh
    x0, y0 = xy.min(axis=0)
    local = xy-np.asarray([x0, y0], dtype=np.int32)
    if (len(xy) != w*h or local[:, 0].max() != w-1 or local[:, 1].max() != h-1
            or len(np.unique(local[:, 1]*w+local[:, 0])) != w*h):
        raise ValueError("anchor initializer requires complete rectangular source panel")
    centre = (anchor.query.nodes_xy*anchor.query.footprint_weights[None, :, None]).sum(axis=1)
    if np.max(np.abs(centre-(local+np.asarray([ox, oy])))) > 2e-5:
        raise ValueError("anchor must have literal identity geometry in output gauge")
    raw = np.empty((h, w), dtype=np.float32)
    raw[local[:, 1], local[:, 0]] = (anchor.codes.astype(np.float32)
        -np.asarray(config.black4, dtype=np.float32)[phase]).clip(0)
    masks = np.zeros((3, h, w), dtype=np.float32)
    masks[PHASE_CHANNEL[phase], local[:, 1], local[:, 0]] = 1
    raw = torch.from_numpy(raw).to(config.device)
    masks = torch.from_numpy(masks).to(config.device).unsqueeze(0)
    k = torch.tensor([1., 2., 1.], dtype=torch.float32, device=config.device)
    kernel = (k[:, None]*k[None, :]).reshape(1, 1, 3, 3).expand(3, 1, 3, 3)
    value = F.conv2d(masks*raw[None, None], kernel, padding=1, groups=3)
    weight = F.conv2d(masks, kernel, padding=1, groups=3)
    image = value/weight.clamp_min(1)
    return F.pad(image, (72, 72, 72, 72), mode="replicate")[0].permute(1, 2, 0)


def _hash_view(view):
    digest = hashlib.sha256()
    for a in (view.codes, view.query.original_xy, view.query.phase,
              view.query.nodes_xy, view.query.footprint_weights):
        digest.update(str(a.dtype).encode("ascii"))
        digest.update(str(a.shape).encode("ascii"))
        digest.update(a.tobytes())
    return digest.hexdigest()


class _EvaluationLimit(RuntimeError):
    pass


@dataclass
class FitResult:
    x_rgb_dn: np.ndarray
    output_rgb_dn: np.ndarray
    initial_rgb_dn: np.ndarray
    variances: dict
    status: str
    converged: bool
    unsupported: list
    evaluations: int
    history: list
    calibration: dict
    source_hashes: dict
    config: Config
    training_predictions: dict
    direct_query_support_rgb: np.ndarray
    fit_counts: dict

    def save(self, out):
        """Save before any caller quality judgment; no native-baseline claim."""
        path = Path(out)
        path.mkdir(parents=True, exist_ok=False)
        np.savez(path/"fields.npz", x_rgb_dn=self.x_rgb_dn,
            output_rgb_dn=self.output_rgb_dn, initial_rgb_dn=self.initial_rgb_dn,
            direct_query_support_rgb=self.direct_query_support_rgb,
            output_support_mask=np.ones(self.output_rgb_dn.shape[:2], dtype=np.uint8))
        np.savez(path/"training-predictions.npz", **{str(k): v for k, v in self.training_predictions.items()})
        receipt = {k: getattr(self, k) for k in ("variances", "status", "converged",
            "unsupported", "evaluations", "history", "calibration", "source_hashes", "fit_counts")}
        receipt.update(schema=1, config=self.config.public(), actual_native_baseline=False,
            original_storage="u16 host and GPU", arithmetic="f32 one current observation view",
            target="reference-cell-integrated",
            holdout="spatial transfer with per-view training-cell variance calibration",
            radiance_domain="all field_hw HWC parameters free, including72pixel apron",
            initializer_extension="replicate the normalized anchor CFA interpolation",
            prior_normalization="sum matrix-Cauchy edge terms / observed output area",
            direct_query_support_definition="nonzero pre-blur training-query basis coefficients; not identifiability",
            direct_query_unsupported_scalar_count=int((~self.direct_query_support_rgb).sum()),
            blurred_observations_can_constrain_apron=True,
            central_score_does_not_remove_apron_inference=True,
            cached_small_query_matrices=7,
            production_query_streaming_implemented=False,
            full_image_lbfgs_history10_vectors_approximately_gb=7.7,
            source_hashes_unchanged=True, implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        for name in ("fields.npz", "training-predictions.npz"):
            receipt[name+"_sha256"] = hashlib.sha256((path/name).read_bytes()).hexdigest()
        (path/"receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        return receipt


def fit(train_views, calibration_views, config):
    """Train codes only; calibration values fit scalar v with X frozen."""
    if not (len(train_views) == 5 and len(calibration_views) == 2):
        raise ValueError("exactly five fit views and two spatial calibration views")
    views = list(train_views)+list(calibration_views)
    ids = [v.source_id for v in views]
    if len(set(ids)) != 7 or config.anchor_id not in [v.source_id for v in train_views]:
        raise ValueError("unique seven source IDs with anchor in training")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no CPU fallback")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    hashes = {v.source_id: _hash_view(v) for v in views}
    for view in views:
        if np.any(view.codes >= config.saturation):
            raise ValueError("first screen excludes known clipped/above-saturation codes")
        _prepared(view.query, config)
    anchor = next(v for v in train_views if v.source_id == config.anchor_id)
    initial = _initialize(anchor, config)
    initial_output = _deliver_x(initial, config).detach().cpu().numpy().copy()
    scale = np.float32(config.saturation-sum(config.black4)/4)
    normalized = (initial/float(scale)).clamp_min(1e-8)
    z = torch.nn.Parameter(torch.log(torch.expm1(normalized)).contiguous())
    varying = [v.source_id for v in train_views if v.source_id != config.anchor_id]
    theta = torch.nn.Parameter(torch.full((len(varying),), math.log(1/255),
        dtype=torch.float32, device=config.device))
    positions = {identity: p for p, identity in enumerate(varying)}
    code_tensors = {v.source_id: torch.from_numpy(v.codes.copy()).to(config.device) for v in views}
    optimizer = torch.optim.LBFGS([z, theta], lr=1, history_size=10, max_iter=64,
        max_eval=150, tolerance_grad=1e-6, tolerance_change=1e-11, line_search_fn="strong_wolfe")
    history = []
    last_finite = [z.detach().clone(), theta.detach().clone()]

    def latent():
        return F.softplus(z)*float(scale)

    def relative(identity):
        return z.new_zeros(()) if identity == config.anchor_id else MAX_VARIANCE*torch.sigmoid(theta[positions[identity]])

    def evaluate(tag):
        # Reserve one final-state observation under the fixed160 total cap.
        limit = MAX_EVALUATIONS if tag == "final" else MAX_EVALUATIONS-1
        if len(history) >= limit:
            raise _EvaluationLimit("fixed evaluation cap")
        optimizer.zero_grad(set_to_none=True)
        total = z.new_zeros(())
        row = dict(evaluation=len(history)+1, tag=tag, complete=False)
        history.append(row)
        for view in train_views:
            mu = forward(latent(), relative(view.source_id), view.query, config)
            loss = _nll(mu, code_tensors[view.source_id], view.query, config)/len(train_views)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError("nonfinite original-CFA likelihood")
            loss.backward()
            total = total+loss.detach()
        data = float(total)
        prior = _prior(latent(), config)
        if not bool(torch.isfinite(prior)):
            raise FloatingPointError("nonfinite matrix prior")
        prior.backward()
        gradient_max = 0.
        for p in (z, theta):
            if p.grad is None or not bool(torch.isfinite(p.grad).all()):
                raise FloatingPointError("nonfinite/missing gradient")
            old = p.grad.detach().reshape(-1)
            contiguous = p.grad.contiguous()
            if not torch.equal(old, contiguous.reshape(-1)):
                raise AssertionError("gradient storage repair changed values")
            p.grad = contiguous
            gradient_max = max(gradient_max, float(contiguous.abs().max()))
        total = total+prior.detach()
        row.update(complete=True, data_nll=data, prior=float(prior), total=float(total),
            gradient_max=gradient_max, optimizer_iteration=int(optimizer.state.get(z, {}).get("n_iter", 0)))
        last_finite[0].copy_(z.detach())
        last_finite[1].copy_(theta.detach())
        return total  # Explicitly f32; optimizer reads gradients already accumulated.

    status, failure = "FIT_RETURNED", None
    evaluate("initial")
    try:
        optimizer.step(lambda: evaluate("optimizer"))
    except _EvaluationLimit as error:
        status, failure = "FIT_EVALUATION_LIMIT", str(error)
    except (FloatingPointError, RuntimeError) as error:
        status, failure = "FIT_NUMERICAL_FAILURE", str(error)
    if failure is not None:
        # Preserve a finite diagnostic image; an interrupted line-search trial
        # is not silently promoted to a converged optimizer result.
        with torch.no_grad():
            z.copy_(last_finite[0])
            theta.copy_(last_finite[1])
    evaluate("final")
    iterations = int(optimizer.state.get(z, {}).get("n_iter", 0))
    converged = history[-1]["gradient_max"] <= 1e-6 and failure is None
    if converged:
        status = "FIT_GRADIENT_CONVERGED"
    elif status == "FIT_RETURNED":
        status = "FIT_ITERATION_LIMIT" if iterations >= 64 else "FIT_STOPPED_WITHOUT_GRADIENT_CONVERGENCE"
    x = latent().detach()
    variances = {v.source_id: float(relative(v.source_id).detach()) for v in train_views}
    unsupported = [] if failure is None else [failure]
    if any(v >= MAX_VARIANCE-1e-3 for v in variances.values()):
        unsupported.append("variance_ceiling")
    calibration, predictions = {}, {}
    for view in train_views:
        predictions[view.source_id] = forward(x, variances[view.source_id], view.query, config).detach().cpu().numpy()
    # A scalar bounded search; neither image parameters nor held score codes enter.
    for view in calibration_views:
        records = []
        def scalar(v):
            if len(records) >= 32:
                raise _EvaluationLimit("32 calibration evaluations")
            vf = np.float32(v)
            with torch.no_grad():
                loss = _nll(forward(x, float(vf), view.query, config),
                    code_tensors[view.source_id], view.query, config)
            value = float(loss)
            if not math.isfinite(value):
                raise FloatingPointError("nonfinite calibration objective")
            records.append(dict(variance=float(vf), nll=value))
            return value
        scalar(0.); scalar(MAX_VARIANCE); scalar(1.)
        lo, hi = np.float32(0), np.float32(MAX_VARIANCE)
        ratio = np.float32((math.sqrt(5)-1)/2)
        left, right = np.float32(hi-ratio*(hi-lo)), np.float32(lo+ratio*(hi-lo))
        fl, fr = scalar(left), scalar(right)
        while len(records) < 32:
            if fl <= fr:
                hi, right, fr = right, left, fl
                left = np.float32(hi-ratio*(hi-lo))
                fl = scalar(left)
            else:
                lo, left, fl = left, right, fr
                right = np.float32(lo+ratio*(hi-lo))
                fr = scalar(right)
        chosen = min(records, key=lambda r: r["nll"])
        variances[view.source_id] = chosen["variance"]
        interval_localized = bool(np.float32(hi-lo) <= np.float32(.001))
        chosen_in_interval = bool(float(lo) <= chosen["variance"] <= float(hi))
        calibration_converged = interval_localized and chosen_in_interval
        calibration[view.source_id] = dict(evaluations=records, chosen=chosen,
            spatial_calibration_only=True, x_frozen=True, global_optimum_claim=False,
            final_interval=[float(lo), float(hi)], interval_localized=interval_localized,
            chosen_in_final_interval=chosen_in_interval,
            interval_variance_width=float(np.float32(hi-lo)),
            numerical_converged=calibration_converged,
            status="FIXED_BUDGET_RETURNED_PARAMETER_LOCALIZED" if calibration_converged
                else "CALIBRATION_RETURNED_PARAMETER_NOT_LOCALIZED",
            nll_range=max(r["nll"] for r in records)-min(r["nll"] for r in records),
            parameter_identification_claim=False)
        if chosen["variance"] >= MAX_VARIANCE-1e-3:
            unsupported.append("calibration_variance_ceiling:"+str(view.source_id))
        predictions[view.source_id] = forward(x, chosen["variance"], view.query, config).detach().cpu().numpy()
    if hashes != {v.source_id: _hash_view(v) for v in views}:
        raise AssertionError("input changed during fit")
    output = _deliver_x(x, config).detach().cpu().numpy().copy()
    support = torch.zeros(math.prod(config.field_hw)*3, dtype=torch.float32, device=config.device)
    for view in train_views:
        matrix = _prepared(view.query, config)[0]
        support.scatter_add_(0, matrix.indices()[1], matrix.values().abs())
    support = (support > 0).reshape(*config.field_hw, 3).cpu().numpy()
    _, _, ow, oh = config.output_xywh
    field_pixels = math.prod(config.field_hw)
    counts = dict(radiance_parameters=field_pixels*3,
        observed_rectangle_rgb_parameters=ow*oh*3,
        free_apron_rgb_parameters=(field_pixels-ow*oh)*3,
        joint_variance_parameters=len(varying), calibration_variance_parameters=2,
        joint_fit_original_sensels=sum(len(v.codes) for v in train_views),
        calibration_original_sensels=sum(len(v.codes) for v in calibration_views),
        source_views=7, train_views=5, calibration_views=2,
        original_codes_gpu_bytes=sum(v.numel()*v.element_size() for v in code_tensors.values()))
    return FitResult(x.cpu().numpy().copy(), output, initial_output, variances, status,
        converged, unsupported, len(history), history, calibration, hashes, config, predictions, support, counts)


def predict(result, query, *, source_id):
    if source_id not in result.variances:
        raise ValueError("view variance was not fitted or spatially calibrated")
    with torch.no_grad():
        return forward(result.x_rgb_dn, result.variances[source_id], query, result.config).cpu().numpy()


def deliver(result):
    return np.array(result.output_rgb_dn, copy=True)
