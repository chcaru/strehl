"""Original fidelity-first student; training-output PCA, never teacher weights.

No model/file is loaded and no training is run on import. FP32 input contract is
caller-owned. PCA fitting consumes a repeatable TRAIN-ONLY batch factory, enabling
streaming over large caches. Native occupancy/render losses are explicit hooks:
this module does not invent a color renderer or exposure-unit conversion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil, gcd
from typing import Callable, Iterable, Mapping

import torch
from torch import Tensor, nn
import torch.nn.functional as F


GAIN_KEYS = ("pgtm", "pgtm_hdr")
LUT_KEYS = ("rgbt_0", "rgbt_1", "rgbt_2", "rgbt_0_hdr", "rgbt_1_hdr", "rgbt_2_hdr")
EXPOSURE_KEYS = ("exposure", "exposure_hdr")
OUTPUT_NAMES = ("pgtm", "rgbt_0", "rgbt_1", "rgbt_2", "exposure",
                "pgtm_hdr", "rgbt_0_hdr", "rgbt_1_hdr", "rgbt_2_hdr", "exposure_hdr")
LUT_DIMENSION = 3 * 32 * 32 * 32


@dataclass(frozen=True)
class V4Config:
    input_size: tuple[int, int] = (384, 512)
    gain_size: tuple[int, int] = (96, 128)
    widths: tuple[int, ...] = (24, 40, 64, 96, 128)
    spatial_width: int = 48
    global_width: int = 192
    pooled_width: int = 16
    lut_rank: int = 8
    coarse_residual_grid: int = 9
    coarse_residual_rank: int = 4
    histogram_bins: int = 16
    max_log_gain: float = 12.0

    def __post_init__(self) -> None:
        for key in ("input_size", "gain_size", "widths"):
            object.__setattr__(self, key, tuple(getattr(self, key)))
        if len(self.widths) != 5 or min(self.widths) < 4:
            raise ValueError("five widths >=4 required")
        if min(self.input_size) < 64 or min(self.gain_size) < 2:
            raise ValueError("input >=64x64 and gain >=2x2 required")
        if min(self.spatial_width, self.global_width, self.pooled_width, self.lut_rank) < 1:
            raise ValueError("widths and PCA rank must be positive")
        if self.coarse_residual_rank < 0 or self.coarse_residual_grid < 2 or self.histogram_bins < 2:
            raise ValueError("invalid residual/histogram configuration")
        if not 0 < self.max_log_gain <= 40:
            raise ValueError("invalid gain bound")


class _Block(nn.Module):
    def __init__(self, incoming: int, outgoing: int, stride: int = 1) -> None:
        super().__init__()
        self.skip = incoming == outgoing and stride == 1
        self.body = nn.Sequential(
            nn.Conv2d(incoming, incoming, 3, stride, 1, groups=incoming, bias=False),
            nn.GroupNorm(gcd(4, incoming), incoming), nn.SiLU(),
            nn.Conv2d(incoming, outgoing, 1, bias=False),
            nn.GroupNorm(gcd(4, outgoing), outgoing), nn.SiLU(),
        )

    def forward(self, value: Tensor) -> Tensor:
        result = self.body(value)
        return value + result if self.skip else result


class StudentV4(nn.Module):
    def __init__(self, config: V4Config | None = None) -> None:
        super().__init__()
        self.config = config or V4Config()
        c = self.config
        self.stem = nn.Sequential(nn.Conv2d(5, c.widths[0], 3, 2, 1, bias=False),
                                  nn.GroupNorm(gcd(4, c.widths[0]), c.widths[0]), nn.SiLU(),
                                  _Block(c.widths[0], c.widths[0]))
        self.stages = nn.ModuleList([
            nn.Sequential(_Block(a, b, 2), _Block(b, b), _Block(b, b))
            for a, b in zip(c.widths[:-1], c.widths[1:])
        ])
        self.projections = nn.ModuleList([nn.Conv2d(width, c.spatial_width, 1) for width in c.widths[1:]])
        self.pool_projection = nn.Conv2d(c.widths[-1], c.pooled_width, 1)
        global_inputs = c.widths[-1] + c.pooled_width * 20 + 10 + 3 * c.histogram_bins
        self.context = nn.Sequential(nn.Linear(global_inputs, c.global_width), nn.SiLU(),
                                     nn.Linear(c.global_width, c.global_width), nn.SiLU())
        self.context_to_spatial = nn.Linear(c.global_width, c.spatial_width)
        self.spatial_fuse = nn.Conv2d(c.spatial_width + 7, c.spatial_width, 1)
        self.refine = nn.Sequential(_Block(c.spatial_width, c.spatial_width),
                                    _Block(c.spatial_width, c.spatial_width),
                                    _Block(c.spatial_width, c.spatial_width))
        self.gain_head = nn.Conv2d(c.spatial_width, 32, 1)
        self.lut_coefficient_head = nn.Linear(c.global_width, 6 * c.lut_rank)
        self.exposure_head = nn.Linear(c.global_width, 2)
        for head in (self.gain_head, self.lut_coefficient_head, self.exposure_head):
            nn.init.zeros_(head.weight)
            nn.init.zeros_(head.bias)

        # These are fitted from training OUTPUTS only. No teacher parameters enter.
        axis = torch.linspace(0, 1, 32)
        identity = torch.stack(torch.meshgrid(axis, axis, axis, indexing="ij")).reshape(1, LUT_DIMENSION)
        self.register_buffer("lut_mean", identity.repeat(6, 1))
        self.register_buffer("lut_basis", torch.zeros(c.lut_rank, LUT_DIMENSION))
        self.register_buffer("lut_coefficient_scale", torch.ones(6, c.lut_rank))
        self.register_buffer("gain_log_center", torch.zeros(2, 16, 1, 1))
        self.register_buffer("exposure_center", torch.zeros(2))
        self.register_buffer("exposure_scale", torch.ones(2))
        self.register_buffer("histogram_centers", torch.linspace(0, 1, c.histogram_bins).reshape(1, 1, -1, 1, 1))
        y, x = torch.meshgrid(torch.linspace(-1, 1, c.gain_size[0]),
                              torch.linspace(-1, 1, c.gain_size[1]), indexing="ij")
        self.register_buffer("coordinates", torch.stack((x, y))[None])
        if c.coarse_residual_rank:
            self.residual_head = nn.Linear(c.global_width, 6 * c.coarse_residual_rank)
            self.residual_basis = nn.Parameter(torch.empty(6, c.coarse_residual_rank,
                                                           3 * c.coarse_residual_grid ** 3))
            nn.init.normal_(self.residual_basis, std=.002)
            nn.init.zeros_(self.residual_head.weight)
            nn.init.zeros_(self.residual_head.bias)
        else:
            self.residual_head, self.residual_basis = None, None

    def _forward(self, inputs: Tensor) -> tuple[dict[str, Tensor], dict[str, Tensor]]:
        c = self.config
        if inputs.ndim != 4 or inputs.shape[1] != 5 or tuple(inputs.shape[-2:]) != c.input_size:
            raise ValueError(f"expected FP32 [B,5,{c.input_size[0]},{c.input_size[1]}]")
        if inputs.dtype != torch.float32 or self.lut_basis.dtype != torch.float32:
            raise TypeError("FP32 input/model required")
        with torch.autocast(device_type=inputs.device.type, enabled=False):
            batch = inputs.shape[0]
            mean = inputs.mean((-2, -1))
            std = (inputs.var((-2, -1), unbiased=False) + 1e-8).sqrt()
            # Histograms are context features of declared 0..1 image channels, not
            # an inferred physical luminance, color space, or exposure conversion.
            small = F.interpolate(inputs[:, :3], size=(24, 32), mode="bilinear", align_corners=False)
            triangular = (1 - (small[:, :, None] - self.histogram_centers).abs() * (c.histogram_bins - 1)).clamp_min(0)
            histogram = triangular.mean((-2, -1)).flatten(1)
            features = []
            value = self.stem(inputs)
            for stage in self.stages:
                value = stage(value)
                features.append(value)
            reduced = self.pool_projection(value)
            pooled = torch.cat((value.mean((-2, -1)), F.adaptive_avg_pool2d(reduced, 2).flatten(1),
                                F.adaptive_avg_pool2d(reduced, 4).flatten(1), mean, std, histogram), dim=1)
            context = self.context(pooled)
            pyramid = F.interpolate(self.projections[0](features[0]), size=c.gain_size,
                                     mode="bilinear", align_corners=False)
            for projection, feature in zip(self.projections[1:], features[1:]):
                pyramid = pyramid + F.interpolate(projection(feature), size=c.gain_size,
                                                   mode="bilinear", align_corners=False)
            pyramid = pyramid * .25 + self.context_to_spatial(context)[:, :, None, None]
            raw_input = F.interpolate(inputs, size=c.gain_size, mode="bilinear", align_corners=False)
            spatial = self.spatial_fuse(torch.cat((pyramid, raw_input, self.coordinates.expand(batch, -1, -1, -1)), dim=1))
            raw_log_gain = self.gain_head(self.refine(spatial)).reshape(batch, 2, 16, *c.gain_size)
            raw_log_gain = raw_log_gain + self.gain_log_center[None]
            log_gain = raw_log_gain.clamp(-c.max_log_gain, c.max_log_gain)
            gains = log_gain.exp()
            unit_coefficients = self.lut_coefficient_head(context).reshape(batch, 6, c.lut_rank)
            coefficients = unit_coefficients * self.lut_coefficient_scale[None]
            raw_tables = (coefficients.reshape(batch * 6, c.lut_rank) @ self.lut_basis).reshape(batch, 6, LUT_DIMENSION)
            raw_tables = raw_tables + self.lut_mean[None]
            if self.residual_head is not None:
                coarse_coefficients = self.residual_head(context).reshape(batch, 6, c.coarse_residual_rank)
                coarse = torch.matmul(coarse_coefficients.permute(1, 0, 2), self.residual_basis).permute(1, 0, 2)
                coarse = coarse.reshape(batch * 6, 3, c.coarse_residual_grid, c.coarse_residual_grid, c.coarse_residual_grid)
                residual = F.interpolate(coarse, size=(32, 32, 32), mode="trilinear", align_corners=True)
                raw_tables = raw_tables + residual.reshape(batch, 6, LUT_DIMENSION)
            tables = raw_tables.clamp(0, 1).reshape(batch, 6, 3, 32, 32, 32)
            exposures = self.exposure_head(context) * self.exposure_scale[None] + self.exposure_center[None]
            outputs = {key: gains[:, i] for i, key in enumerate(GAIN_KEYS)}
            outputs.update({key: tables[:, i] for i, key in enumerate(LUT_KEYS)})
            outputs.update({key: exposures[:, i:i + 1] for i, key in enumerate(EXPOSURE_KEYS)})
            return ({key: outputs[key] for key in OUTPUT_NAMES},
                    {"lut_coefficients": unit_coefficients, "lut_raw": raw_tables,
                     "gain_log": log_gain, "context": context})

    def forward(self, inputs: Tensor) -> dict[str, Tensor]:
        return self._forward(inputs)[0]

    def forward_with_aux(self, inputs: Tensor) -> tuple[dict[str, Tensor], dict[str, Tensor]]:
        return self._forward(inputs)

    @torch.no_grad()
    def initialize_from_training(self, pca: Mapping[str, Tensor], *,
                                 gain_log_center: Tensor | None = None,
                                 exposure_center: Tensor | None = None,
                                 exposure_scale: Tensor | None = None) -> None:
        for key in ("lut_mean", "lut_basis", "lut_coefficient_scale"):
            destination, source = getattr(self, key), pca[key]
            if source.shape != destination.shape or source.dtype != torch.float32 or not torch.isfinite(source).all():
                raise ValueError(f"invalid training-fit tensor: {key}")
            destination.copy_(source.to(destination.device))
        if not (self.lut_coefficient_scale > 0).all():
            raise ValueError("PCA coefficient scales must be positive")
        for key, source in (("gain_log_center", gain_log_center), ("exposure_center", exposure_center),
                            ("exposure_scale", exposure_scale)):
            if source is not None:
                destination = getattr(self, key)
                if source.numel() != destination.numel() or not torch.isfinite(source).all():
                    raise ValueError(f"invalid training center/scale: {key}")
                destination.copy_(source.reshape_as(destination).to(destination.device, torch.float32))
        if not (self.exposure_scale > 0).all():
            raise ValueError("exposure scales must be positive")

    def coefficient_targets(self, targets: Mapping[str, Tensor]) -> Tensor:
        tables = torch.stack([targets[key] for key in LUT_KEYS], dim=1).flatten(2)
        projected = (tables - self.lut_mean[None]) @ self.lut_basis.T
        return projected / self.lut_coefficient_scale[None]

    def describe(self) -> dict:
        parameters = sum(value.numel() for value in self.parameters())
        buffers = sum(value.numel() for value in self.buffers())
        return {"config": asdict(self.config), "parameter_count": parameters, "buffer_count": buffers,
                "fp32_state_bytes": 4 * (parameters + buffers),
                "scope": "tensor storage only; no quality or speed claim"}


LutBatchFactory = Callable[[], Iterable[tuple[Tensor, Tensor | None]]]


@torch.no_grad()
def fit_lut_pca(batch_factory: LutBatchFactory, *, rank: int = 8, oversample: int = 8,
                power_iterations: int = 1, device: str = "cpu", seed: int = 41022) -> dict[str, Tensor]:
    """Fit shared value-space PCA from repeatable TRAIN-only output batches.

    Each yielded pair is (FP32[B,6,3,32,32,32], optional positive FP32[B] weights).
    Use inverse-frequency physical-subject weights, not validation/test examples.
    Multiple passes stream O(D*(rank+oversample)) state; no full corpus/device copy.
    Calling this function performs substantial work: the coordinator schedules it.
    """
    if rank < 1 or rank > LUT_DIMENSION or oversample < 0 or power_iterations < 0:
        raise ValueError("invalid PCA configuration")
    width = min(rank + oversample, LUT_DIMENSION)
    mean_sum = torch.zeros(6, LUT_DIMENSION, dtype=torch.float32, device=device)
    total_weight, count = 0.0, 0
    expected_count, expected_weight = None, None

    def batches():
        rows_seen, weight_seen = 0, 0.0
        for table, weights in batch_factory():
            if table.dtype != torch.float32 or table.ndim != 6 or table.shape[1:] != (6, 3, 32, 32, 32):
                raise ValueError("PCA expects FP32[B,6,3,32,32,32]")
            table = table.to(device).flatten(2)
            if weights is not None and weights.dtype != torch.float32:
                raise ValueError("PCA weights must be FP32")
            weight = torch.ones(table.shape[0], dtype=torch.float32, device=device) if weights is None else weights.to(device)
            if weight.shape != (table.shape[0],) or not torch.isfinite(weight).all() or not (weight > 0).all():
                raise ValueError("PCA sample weights must be finite and positive")
            if not torch.isfinite(table).all():
                raise ValueError("non-finite training LUT")
            rows_seen += table.shape[0]
            weight_seen += float(weight.sum())
            yield table, weight
        if expected_count is not None and (rows_seen != expected_count
                or abs(weight_seen - expected_weight) > max(1e-6, abs(expected_weight) * 1e-6)):
            raise ValueError("PCA factory changed row count/weight between passes")

    for tables, weights in batches():
        mean_sum += (tables * weights[:, None, None]).sum(0)
        total_weight += float(weights.sum())
        count += tables.shape[0]
    if count < 2 or total_weight <= 0:
        raise ValueError("PCA needs at least two training examples")
    expected_count, expected_weight = count, total_weight
    mean = mean_sum / total_weight
    generator = torch.Generator(device=device).manual_seed(seed)
    omega = torch.randn(LUT_DIMENSION, width, generator=generator, dtype=torch.float32, device=device)
    for _ in range(power_iterations + 1):
        sketch = torch.zeros_like(omega)
        for tables, weights in batches():
            centered = (tables - mean[None]).reshape(-1, LUT_DIMENSION)
            row_weights = weights[:, None].expand(-1, 6).reshape(-1, 1)
            sketch += centered.T @ ((centered @ omega) * row_weights)
        omega = torch.linalg.qr(sketch, mode="reduced").Q
    covariance = torch.zeros(width, width, dtype=torch.float32, device=device)
    for tables, weights in batches():
        projected = ((tables - mean[None]).reshape(-1, LUT_DIMENSION) @ omega)
        row_weights = weights[:, None].expand(-1, 6).reshape(-1, 1)
        covariance += projected.T @ (projected * row_weights)
    eigenvalues, eigenvectors = torch.linalg.eigh(covariance)
    basis = (omega @ eigenvectors[:, -rank:].flip(1)).T.contiguous()
    coefficient_square = torch.zeros(6, rank, dtype=torch.float32, device=device)
    for tables, weights in batches():
        coefficients = (tables - mean[None]) @ basis.T
        coefficient_square += (coefficients.square() * weights[:, None, None]).sum(0)
    scale = (coefficient_square / total_weight).sqrt().clamp_min(1e-4)
    return {"lut_mean": mean.cpu(), "lut_basis": basis.cpu(), "lut_coefficient_scale": scale.cpu(),
            "eigenvalues": (eigenvalues[-rank:].flip(0) / (6 * total_weight)).cpu(),
            "training_examples": torch.tensor(count, dtype=torch.int64)}


@dataclass(frozen=True)
class V4LossConfig:
    gain_weight: float = 1.0
    lut_weight: float = 1.0
    exposure_weight: float = 1.0
    coefficient_weight: float = .25
    gain_gradient_weight: float = .05
    tail_weight: float = .1
    tail_fraction: float = .05
    raw_lut_weight: float = .1
    occupancy_weight: float = .25
    render_weight: float = 0.0
    validate_values: bool = False


class V4Loss(nn.Module):
    def __init__(self, normalizers: Mapping[str, float], config: V4LossConfig | None = None) -> None:
        super().__init__()
        self.config = config or V4LossConfig()
        self.normalizers = {key: float(normalizers[key]) for key in OUTPUT_NAMES}
        if any(not torch.isfinite(torch.tensor(value)) or value <= 0 for value in self.normalizers.values()):
            raise ValueError("positive finite training-only normalizers required")
        if not 0 < self.config.tail_fraction <= 1:
            raise ValueError("tail fraction must be in (0,1]")

    def forward(self, predictions: Mapping[str, Tensor], targets: Mapping[str, Tensor], *,
                aux: Mapping[str, Tensor], coefficient_target: Tensor,
                occupancy: Mapping[str, Tensor] | None = None,
                rendered_prediction: Tensor | None = None, rendered_target: Tensor | None = None) -> dict[str, Tensor]:
        c = self.config
        errors, tails, occupied = {}, {}, {}
        gain_gradients = []
        for key in OUTPUT_NAMES:
            prediction, target = predictions[key], targets[key].detach()
            if prediction.shape != target.shape or prediction.dtype != torch.float32 or target.dtype != torch.float32:
                raise ValueError(f"{key}: exact equal FP32 shapes required")
            if c.validate_values and (not torch.isfinite(prediction).all() or not torch.isfinite(target).all()):
                raise ValueError(f"{key}: non-finite tensor")
            if key in GAIN_KEYS:
                if c.validate_values and (not (prediction > 0).all() or not (target > 0).all()):
                    raise ValueError("gains must be positive")
                prediction, target = prediction.log(), target.log()
                gain_gradients.append(torch.stack([
                    (torch.diff(prediction, dim=axis) - torch.diff(target, dim=axis)).abs().mean() / self.normalizers[key]
                    for axis in (-2, -1)
                ]).mean())
            absolute = (prediction - target).abs() / self.normalizers[key]
            errors[key] = absolute.mean()
            if key in GAIN_KEYS or key in LUT_KEYS:
                flattened = absolute.flatten(1)
                top = max(1, ceil(flattened.shape[1] * c.tail_fraction))
                tails[key] = flattened.topk(top, dim=1, sorted=False).values.mean()
            if occupancy is not None and key in occupancy:
                weights = occupancy[key].detach()
                if weights.shape != absolute.shape:
                    raise ValueError(f"{key}: occupancy must match tensor exactly")
                if c.validate_values and (not torch.isfinite(weights).all() or not (weights >= 0).all()):
                    raise ValueError("occupancy weights must be finite and nonnegative")
                mass = weights.flatten(1).sum(1)
                weighted = (absolute * weights).flatten(1).sum(1) / mass.clamp_min(1e-12)
                occupied[key] = torch.where(mass > 0, weighted, torch.zeros_like(weighted)).mean()
        family = lambda keys: torch.stack([errors[key] for key in keys]).mean()
        gain, lut, exposure = family(GAIN_KEYS), family(LUT_KEYS), family(EXPOSURE_KEYS)
        zero = gain.new_zeros(())
        coefficients = (aux["lut_coefficients"] - coefficient_target.detach()).abs().mean()
        target_tables = torch.stack([targets[key] for key in LUT_KEYS], dim=1).flatten(2).detach()
        scales = gain.new_tensor([self.normalizers[key] for key in LUT_KEYS])[None, :, None]
        raw_lut = ((aux["lut_raw"] - target_tables).abs() / scales).mean()
        tail = .5 * (torch.stack([tails[key] for key in GAIN_KEYS]).mean()
                     + torch.stack([tails[key] for key in LUT_KEYS]).mean())
        gradient = torch.stack(gain_gradients).mean()
        occupied_loss = torch.stack(list(occupied.values())).mean() if occupied else zero
        render = zero
        if c.render_weight:
            if rendered_prediction is None or rendered_target is None or rendered_prediction.shape != rendered_target.shape:
                raise ValueError("same validated renderer outputs required for render loss")
            if rendered_prediction.dtype != torch.float32 or rendered_target.dtype != torch.float32:
                raise ValueError("FP32 rendered tensors required")
            render = (rendered_prediction - rendered_target.detach()).abs().mean()
        total = (c.gain_weight * gain + c.lut_weight * lut + c.exposure_weight * exposure
                 + c.coefficient_weight * coefficients + c.gain_gradient_weight * gradient
                 + c.tail_weight * tail + c.raw_lut_weight * raw_lut
                 + c.occupancy_weight * occupied_loss + c.render_weight * render)
        return {"total": total, "gain": gain, "lut": lut, "exposure": exposure,
                "coefficients": coefficients, "tail": tail, "gain_gradient": gradient,
                "raw_lut": raw_lut, "occupancy": occupied_loss, "render": render,
                **{f"output/{key}": value for key, value in errors.items()}}


if __name__ == "__main__":
    import json

    torch.set_num_threads(1)
    torch.manual_seed(41022)
    model = StudentV4(V4Config(input_size=(64, 64), gain_size=(16, 16))).eval()
    with torch.no_grad():
        outputs, aux = model.forward_with_aux(torch.rand(1, 5, 64, 64))
        assert tuple(outputs) == OUTPUT_NAMES
        assert all(value.dtype == torch.float32 and torch.isfinite(value).all() for value in outputs.values())
        criterion = V4Loss({key: 1.0 for key in OUTPUT_NAMES}, V4LossConfig(validate_values=True))
        identical = criterion(outputs, outputs, aux=aux, coefficient_target=aux["lut_coefficients"])
        assert float(identical["total"]) == 0.0
        altered = {key: value.clone() for key, value in outputs.items()}
        altered["pgtm"][..., :8, :] *= 1.2
        altered["rgbt_0"] *= .8
        altered["exposure"] += .2
        disturbed = criterion(outputs, altered, aux=aux, coefficient_target=aux["lut_coefficients"])
        assert all(float(disturbed[key]) > 0 for key in ("gain", "lut", "exposure", "tail", "gain_gradient"))
    print(json.dumps({"scope": "Tiny architecture/loss smoke only, no training/teacher/image-quality test",
                      **model.describe(), "same_target_loss": float(identical["total"]),
                      "disturbed_target_loss": float(disturbed["total"])}, indent=2))
