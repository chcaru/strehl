"""Bounded oracle-optics original-CFA inverse. Author does not execute controls."""
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import math
import time
import numpy as np
import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class Config:
    width: int
    height: int
    focus_coordinates: tuple
    gain: float
    read_variance: float
    inverse_depths: tuple = (1.0, 0.0)  # near, far; supplied oracle geometry
    defocus_scale: float = 12.0        # native px / inverse-depth difference
    psf_sigma: float = 0.7            # supplied common in-focus PSF, native px
    black: int = 512
    saturation: int = 16383           # digital code, NOT development white 15360
    steps: int = 160
    device: str = "cuda"
    pupil_points: tuple | None = None # explicit oracle quadrature; 64 equal weights

    def __post_init__(self):
        if not (24 <= self.width <= 96 and 24 <= self.height <= 96):
            raise ValueError("native extent must be 24..96 per axis")
        if not (3 <= len(self.focus_coordinates) <= 9):
            raise ValueError("three to nine supplied focus coordinates required")
        vals = [*self.focus_coordinates, *self.inverse_depths, self.gain,
                self.read_variance, self.defocus_scale, self.psf_sigma]
        if not all(math.isfinite(float(v)) for v in vals):
            raise ValueError("nonfinite configuration")
        if len(self.inverse_depths) != 2 or self.inverse_depths[0] <= self.inverse_depths[1]:
            raise ValueError("ordered near/far inverse depths required")
        if self.gain <= 0 or self.read_variance <= 0 or not 0 < self.defocus_scale <= 24:
            raise ValueError("positive supplied noise and bounded optical scale required")
        if not 0.4 <= self.psf_sigma <= 2 or self.steps != 160:
            raise ValueError("fixed 160 steps and bounded supplied PSF required")
        if (self.black, self.saturation) != (512, 16383):
            raise ValueError("this experiment fixes original sensor code conventions")
        if self.pupil_points is not None:
            p = np.asarray(self.pupil_points, dtype=np.float64)
            if p.shape != (64, 2) or not np.isfinite(p).all() or np.any((p*p).sum(1) > 1.000001):
                raise ValueError("supplied pupil must contain 64 finite unit-disc points")
        if min(self.width, self.height) - 2*self.valid_margin < 8:
            raise ValueError("insufficient fully supported common interior")

    @property
    def valid_margin(self):
        radius = max(abs(f-d)*self.defocus_scale
                     for f in self.focus_coordinates for d in self.inverse_depths)
        return math.ceil(radius) + math.ceil(4*self.psf_sigma) + 1


def aperture_points(device="cpu"):
    """64 equal-weight rays: 32 equal-area golden-angle nodes and their negatives."""
    points = []
    for k in range(32):
        r, angle = math.sqrt((k+0.5)/32), k*math.pi*(3-math.sqrt(5))
        p = (r*math.cos(angle), r*math.sin(angle))
        points.extend((p, (-p[0], -p[1])))
    return torch.tensor(points, dtype=torch.float32, device=device)


def _blur(rgb, sigma):
    radius = math.ceil(4*sigma)
    x = torch.arange(-radius, radius+1, dtype=torch.float32, device=rgb.device)
    kernel = torch.exp(-0.5*(x/sigma)**2)
    kernel = kernel/kernel.sum()
    t = rgb.permute(2, 0, 1).unsqueeze(0)
    with torch.backends.cudnn.flags(allow_tf32=False):
        t = F.conv2d(t, kernel.view(1, 1, 1, -1).expand(3, 1, 1, -1),
                     padding=(0, radius), groups=3)
        t = F.conv2d(t, kernel.view(1, 1, -1, 1).expand(3, 1, -1, 1),
                     padding=(radius, 0), groups=3)
    return t[0].permute(1, 2, 0)


def forward(near_rgb, far_rgb, alpha, config, index, *, pupil=None, single_depth=None):
    """Expected black-subtracted DN RGB; inputs HWC/HW f32, identity pregeometry.

    grid_sample interpolates premultiplied near radiance and coverage together.
    Visibility and far radiance are multiplied PER RAY before pupil integration.
    Boundary predictions are defined but unsupported; use Config.valid_margin.
    """
    h, w = config.height, config.width
    if not (0 <= index < len(config.focus_coordinates)):
        raise ValueError("invalid focus index")
    if near_rgb.shape != (h, w, 3) or far_rgb.shape != (h, w, 3) or alpha.shape != (h, w):
        raise ValueError("bad latent shape")
    if any(t.dtype != torch.float32 for t in (near_rgb, far_rgb, alpha)):
        raise ValueError("latent arithmetic is f32")
    if any(not bool(torch.isfinite(t).all()) for t in (near_rgb, far_rgb, alpha)):
        raise ValueError("nonfinite latent")
    if bool((near_rgb < 0).any() or (far_rgb < 0).any() or (alpha < 0).any() or (alpha > 1).any()):
        raise ValueError("nonnegative radiance and alpha in [0,1] required")
    if pupil is not None:
        rays = pupil
    elif config.pupil_points is not None:
        rays = torch.tensor(config.pupil_points, dtype=torch.float32, device=near_rgb.device)
    else:
        rays = aperture_points(near_rgb.device)
    if rays.ndim != 2 or rays.shape[1] != 2 or not 1 <= len(rays) <= 1024:
        raise ValueError("invalid pupil quadrature")
    if rays.dtype != torch.float32 or rays.device != near_rgb.device:
        raise ValueError("pupil must share f32 device with latent")
    if pupil is not None and (not torch.isfinite(rays).all() or (rays.square().sum(-1) > 1.000001).any()):
        raise ValueError("invalid unit-disc pupil point")
    yy, xx = torch.meshgrid(torch.arange(h, device=near_rgb.device, dtype=torch.float32),
                            torch.arange(w, device=near_rgb.device, dtype=torch.float32), indexing="ij")
    focus = config.focus_coordinates[index]
    base = torch.stack((xx, yy), -1)[None]
    normalization = near_rgb.new_tensor([2/(w-1), 2/(h-1)])
    def sample(data, depth):
        d = config.defocus_scale*(focus-depth)
        grid = (base+d*rays[:, None, None, :])*normalization-1
        return F.grid_sample(data.expand(len(rays), -1, -1, -1), grid, mode="bilinear",
                             padding_mode="zeros", align_corners=True).permute(0, 2, 3, 1)
    if single_depth is not None:
        if not math.isfinite(float(single_depth)) or not config.inverse_depths[1] <= single_depth <= config.inverse_depths[0]:
            raise ValueError("single depth outside supported supplied interval")
        source = near_rgb.permute(2, 0, 1).unsqueeze(0)
        out = sample(source, single_depth).mean(0)
    else:
        near = torch.cat((alpha[..., None]*near_rgb, alpha[..., None]), -1)
        near = near.permute(2, 0, 1).unsqueeze(0)
        far = far_rgb.permute(2, 0, 1).unsqueeze(0)
        n = sample(near, config.inverse_depths[0])
        b = sample(far, config.inverse_depths[1])
        out = (n[..., :3]+(1-n[..., 3:4])*b).mean(0)
    return _blur(out, config.psf_sigma)


def cfa(rgb):
    """Active-local native RGGB, no WB or demosaic in the likelihood."""
    y, x = torch.meshgrid(torch.arange(rgb.shape[0], device=rgb.device),
                          torch.arange(rgb.shape[1], device=rgb.device), indexing="ij")
    channel = (y % 2)+(x % 2)
    return torch.gather(rgb, 2, channel[..., None])[..., 0]


def observation_nll(predicted_dn, observed_dn, *, gain, read_variance, black=512, saturation=16383):
    """Conditional heteroscedastic Gaussian NLL; exact upper-code censor tail.

    Predicted DN includes black. Injected parameters are never estimated here.
    The normal-tail likelihood is an approximation to the supplied shot/read
    model, not an empirical probability calibration of this camera.
    """
    signal = (predicted_dn-black).clamp_min(0)
    variance = gain*signal + read_variance + 1/12  # quantization approximation, DN²
    gaussian = 0.5*(torch.log(variance)+(observed_dn-predicted_dn).square()/variance)
    upper = -torch.special.log_ndtr((predicted_dn-(saturation-0.5))/torch.sqrt(variance))
    return torch.where(observed_dn >= saturation, upper, gaussian)


def _interpolate_cfa(codes, config, device):
    raw = torch.as_tensor(np.array(codes, dtype=np.float32, copy=True), device=device)
    raw = (raw-config.black).clamp_min(0)/(config.saturation-config.black)
    masks = torch.zeros((1, 3, config.height, config.width), dtype=torch.float32, device=device)
    masks[0, 0, 0::2, 0::2] = 1
    masks[0, 1, 0::2, 1::2] = masks[0, 1, 1::2, 0::2] = 1
    masks[0, 2, 1::2, 1::2] = 1
    k = torch.tensor([1., 2., 1.], device=device)
    k = (k[:, None]*k[None, :]).expand(3, 1, 3, 3)
    with torch.backends.cudnn.flags(allow_tf32=False):
        numerator = F.conv2d(masks*raw[None, None], k, padding=1, groups=3)
        denominator = F.conv2d(masks, k, padding=1, groups=3)
    return (numerator/denominator.clamp_min(1))[0].permute(1, 2, 0)


def _vector_huber(image, gradient_scale):
    # Mean per direction; RGB differences reduced by their Euclidean norm.
    result = image.new_zeros(())
    for d in (image[1:]-image[:-1], image[:, 1:]-image[:, :-1]):
        magnitude = torch.sqrt(d.square().sum(-1)+1e-12)/gradient_scale
        result = result + torch.where(magnitude <= 2, 0.5*magnitude.square(),
                                      2*magnitude-2).mean()/2
    return result


class _State(torch.nn.Module):
    def __init__(self, near, far, mode, config):
        super().__init__()
        self.dn_scale = config.saturation-config.black
        # 2048DN is a chosen prior reference, never an estimated scene constant.
        self.gradient_scale = math.sqrt(2*(config.gain*2048+config.read_variance+1/12))
        def parameter(a):
            return torch.nn.Parameter(torch.log(torch.expm1(a.clamp_min(1e-4))))
        self.near = parameter(near)
        self.far = parameter(far) if mode == "two-layer" else None
        self.alpha_logit = torch.nn.Parameter(torch.zeros_like(near[..., 0])) if self.far is not None else None

    def fields(self):
        near = F.softplus(self.near)
        if self.far is None:
            return near, near, torch.ones_like(near[..., 0])
        return near, F.softplus(self.far), torch.sigmoid(self.alpha_logit)

    def prior(self):
        near, far, alpha = self.fields()
        images = [near] if self.far is None else [near, far]
        image = sum(_vector_huber(v*self.dn_scale, self.gradient_scale) for v in images)/len(images)
        flux = sum(v.square().mean() for v in images)/len(images)
        alpha_tv = (torch.abs(alpha[1:]-alpha[:-1]).mean()+
                    torch.abs(alpha[:, 1:]-alpha[:, :-1]).mean())/2
        binary = (alpha*(1-alpha)).mean()
        return image + 0.02*alpha_tv + 0.002*binary + 0.0001*flux


class FitResult:
    def __init__(self, state, config, mode, history, training_hashes):
        self.state, self.config, self.mode = state, config, mode
        self.history, self.training_hashes = history, training_hashes
        with torch.no_grad():
            near, far, alpha = state.fields()
            scale = config.saturation-config.black
            self.near_rgb = (near*scale).cpu().numpy().copy()
            self.far_rgb = (far*scale).cpu().numpy().copy()
            self.alpha = alpha.cpu().numpy().copy()
            self.pinhole_rgb = (alpha[..., None]*near*scale+(1-alpha[..., None])*far*scale).cpu().numpy().copy()
        if not all(np.isfinite(v).all() for v in (self.near_rgb, self.far_rgb, self.alpha, self.pinhole_rgb)):
            raise FloatingPointError("nonfinite reconstructed state")

    def predict_rgb(self, index):
        with torch.no_grad():
            near, far, alpha = self.state.fields()
            scale = self.config.saturation-self.config.black
            single = self.config.inverse_depths[1] if self.mode == "one-layer" else None
            return forward(near*scale, far*scale, alpha, self.config, index, single_depth=single).cpu().numpy()

    def predict(self, index):
        rgb = self.predict_rgb(index)
        result = np.empty(rgb.shape[:2], dtype=np.float32)
        result[0::2, 0::2], result[1::2, 1::2] = rgb[0::2, 0::2, 0], rgb[1::2, 1::2, 2]
        result[0::2, 1::2], result[1::2, 0::2] = rgb[0::2, 1::2, 1], rgb[1::2, 0::2, 1]
        return result+self.config.black


def fit(observations, config, train_indices, output_dir=None, *, mode="two-layer", optimize=True):
    """Stream one observed uint16 frame per backward; held-out bytes never read.

    optimize=False returns the identical observation-only initialization.
    It is a disabled-optimization diagnostic, not the canonical focus stacker.
    """
    if mode not in ("one-layer", "two-layer"):
        raise ValueError("unknown model mode")
    if observations.dtype != np.uint16 or observations.shape != (len(config.focus_coordinates), config.height, config.width):
        raise ValueError("original uint16 CFA shape required")
    if any(not isinstance(i, (int, np.integer)) or isinstance(i, (bool, np.bool_)) for i in train_indices):
        raise ValueError("training indices must be integers")
    indices = tuple(int(i) for i in train_indices)
    if len(indices) < 3 or len(set(indices)) != len(indices) or any(i < 0 or i >= len(observations) for i in indices):
        raise ValueError("at least three distinct explicit training indices required")
    device = torch.device(config.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA required by this run; no silent CPU fallback")
    hashes, mean = [], None
    for i in indices:
        if np.any(observations[i] > config.saturation):
            raise ValueError("training observation exceeds declared digital maximum")
        hashes.append(hashlib.sha256(observations[i].tobytes()).hexdigest())
        v = _interpolate_cfa(observations[i], config, device)
        mean = v.clone() if mean is None else mean+v
    mean = mean/len(indices)
    # Initialization uses endpoint training observations; no held-out values.
    ordered = sorted(indices, key=lambda i: config.focus_coordinates[i])
    near = _interpolate_cfa(observations[ordered[-1]], config, device)
    far = _interpolate_cfa(observations[ordered[0]], config, device)
    state = _State(near if mode == "two-layer" else mean, far, mode, config).to(device)
    optimizer = torch.optim.Adam(state.parameters(), lr=0.03)
    m, history, started = config.valid_margin, [], time.monotonic()
    scale = config.saturation-config.black
    for step in range(config.steps if optimize else 0):
        learning_rate = 0.001 + 0.5*(0.03-0.001)*(1+math.cos(math.pi*step/159))
        for group in optimizer.param_groups:
            group["lr"] = learning_rate
        optimizer.zero_grad(set_to_none=True)
        data_value = 0.0
        for i in indices:
            near, far, alpha = state.fields()
            single = config.inverse_depths[1] if mode == "one-layer" else None
            rgb = forward(near*scale, far*scale, alpha, config, i, single_depth=single)
            observed = torch.as_tensor(np.array(observations[i], dtype=np.float32, copy=True), device=device)
            loss = observation_nll(cfa(rgb)+config.black, observed, gain=config.gain,
                                   read_variance=config.read_variance, black=config.black,
                                   saturation=config.saturation)[m:-m, m:-m].mean()/len(indices)
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite training likelihood")
            loss.backward()
            data_value += float(loss.detach())
            del rgb, observed, loss, near, far, alpha
        prior = state.prior()
        prior.backward()
        gradient = torch.sqrt(sum(p.grad.square().sum() for p in state.parameters()))
        if not torch.isfinite(gradient):
            raise FloatingPointError("nonfinite training gradient")
        history.append(dict(step=step, data_nll=data_value, prior=float(prior.detach()),
                            gradient_norm=float(gradient), learning_rate=learning_rate,
                            elapsed_seconds=time.monotonic()-started))
        optimizer.step()
    result = FitResult(state, config, mode, history, hashes)
    if output_dir is not None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=False)
        np.savez_compressed(path/"reconstruction.npz", near_rgb=result.near_rgb,
                            far_rgb=result.far_rgb, alpha=result.alpha, pinhole_rgb=result.pinhole_rgb)
        torch.save(state.state_dict(), path/"state.pt")
        (path/"receipt.json").write_text(json.dumps(dict(config=asdict(config), mode=mode,
            train_indices=indices, training_sha256=hashes, optimized=optimize, history=history,
            status="iteration_limit" if optimize else "initialization_only"), indent=2), encoding="utf-8")
    return result
