"""Original compact student for local, output-supervised adaptive-profile research.

This module contains no teacher model, teacher initializer, proprietary implementation,
or assumed Adobe renderer. All learned tensors start from fresh random or analytical
identity values. Optional initialization takes *training-label means* supplied by the
caller; do not use holdout labels there.

The input is FP32 [B, 5, H, W]. Its color encoding, RGB order, semantic mask meaning,
and normalization belong to the teacher-cache contract, not to this architecture.
An inferred matching output shape does not establish a matching photographic look.

Research constraints: FP32 parameters and arithmetic; no training, device selection,
teacher loading, or filesystem access occurs on import. A renderer is deliberately
not provided: render consistency must use a separately validated common renderer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import gcd, isfinite
from typing import Mapping

import torch
from torch import Tensor, nn
import torch.nn.functional as F


GAIN_KEYS = ("pgtm", "pgtm_hdr")
LUT_KEYS = ("rgbt_0", "rgbt_1", "rgbt_2", "rgbt_0_hdr", "rgbt_1_hdr", "rgbt_2_hdr")
EXPOSURE_KEYS = ("exposure", "exposure_hdr")
# A teacher's final normalized smoothing can overshoot one by a few FP32 ulps.
# This tolerance is only validation slack; loss targets remain numerically intact.
LUT_NUMERICAL_TOLERANCE = 2e-6
OUTPUT_NAMES = (
    "pgtm", "rgbt_0", "rgbt_1", "rgbt_2", "exposure",
    "pgtm_hdr", "rgbt_0_hdr", "rgbt_1_hdr", "rgbt_2_hdr", "exposure_hdr",
)


@dataclass(frozen=True)
class StudentConfig:
    input_size: tuple[int, int] = (384, 512)
    gain_size: tuple[int, int] = (96, 128)
    gain_knots: int = 16
    widths: tuple[int, ...] = (16, 24, 40, 64, 96)
    spatial_width: int = 32
    global_width: int = 96
    lut_grid: int = 9
    lut_output_grid: int = 32
    lut_rank: int = 4
    max_log_gain: float = 12.0
    coefficient_limit: float = 3.0
    identity_epsilon: float = 1e-3
    shared_training_residual: bool = False

    def __post_init__(self) -> None:
        # A checkpoint's JSON sidecar turns tuples into lists. Normalize those
        # without changing the configured contract on round-trip loading.
        object.__setattr__(self, "input_size", tuple(self.input_size))
        object.__setattr__(self, "gain_size", tuple(self.gain_size))
        object.__setattr__(self, "widths", tuple(self.widths))
        if len(self.widths) != 5 or min(self.widths) < 4:
            raise ValueError("widths must contain five channel counts of at least four")
        if min(self.input_size) < 32 or min(self.gain_size) < 2:
            raise ValueError("input dimensions must be >=32 and gain dimensions >=2")
        if min(self.spatial_width, self.global_width, self.gain_knots, self.lut_rank) < 1:
            raise ValueError("channel counts, knots, and rank must be positive")
        if min(self.lut_grid, self.lut_output_grid) < 2:
            raise ValueError("LUT grids must be at least two")
        if not (0 < self.max_log_gain <= 40 and 0 < self.coefficient_limit <= 100):
            raise ValueError("gain/coefficient bounds are invalid")
        if not 0 < self.identity_epsilon < 0.1:
            raise ValueError("identity_epsilon must be in (0, 0.1)")


def _norm(channels: int) -> nn.GroupNorm:
    return nn.GroupNorm(gcd(4, channels), channels)


class _DepthwiseBlock(nn.Module):
    def __init__(self, incoming: int, outgoing: int, stride: int = 1) -> None:
        super().__init__()
        self.residual = incoming == outgoing and stride == 1
        self.body = nn.Sequential(
            nn.Conv2d(incoming, incoming, 3, stride, 1, groups=incoming, bias=False),
            _norm(incoming), nn.SiLU(),
            nn.Conv2d(incoming, outgoing, 1, bias=False),
            _norm(outgoing), nn.SiLU(),
        )

    def forward(self, x: Tensor) -> Tensor:
        y = self.body(x)
        return x + y if self.residual else y


class AdaptiveStudent(nn.Module):
    """Small CNN, spatial log-gain decoder, and low-rank coarse color-table decoder.

    The color decoder reconstructs six independent 9-cubed tables by default, then
    interpolates them to the output contract's 32-cubed tables. This saves parameters
    but can miss fine color variation. Increase grid/rank only after scene-heldout
    evaluation shows that this representation, rather than the input contract or
    training corpus, is the limiting factor.
    """

    def __init__(self, config: StudentConfig | None = None) -> None:
        super().__init__()
        self.config = config or StudentConfig()
        c = self.config
        self.stem = nn.Sequential(
            nn.Conv2d(5, c.widths[0], 3, 2, 1, bias=False),
            _norm(c.widths[0]), nn.SiLU(),
            _DepthwiseBlock(c.widths[0], c.widths[0]),
        )
        self.stages = nn.ModuleList([
            nn.Sequential(_DepthwiseBlock(a, b, 2), _DepthwiseBlock(b, b))
            for a, b in zip(c.widths[:-1], c.widths[1:])
        ])
        self.spatial_projections = nn.ModuleList([
            nn.Conv2d(width, c.spatial_width, 1) for width in c.widths[1:]
        ])
        # Raw per-channel mean/std retains global exposure/mask coverage even when
        # normalization in the convolutional path removes some global amplitude.
        self.global_features = nn.Sequential(
            nn.Linear(c.widths[-1] + 10, c.global_width), nn.SiLU(),
            nn.Linear(c.global_width, c.global_width), nn.SiLU(),
        )
        self.spatial_condition = nn.Linear(c.global_width, c.spatial_width)
        self.spatial_refine = nn.Sequential(
            _DepthwiseBlock(c.spatial_width, c.spatial_width),
            _DepthwiseBlock(c.spatial_width, c.spatial_width),
        )
        self.gain_head = nn.Conv2d(c.spatial_width, 2 * c.gain_knots, 1)
        self.gain_bias = nn.Parameter(torch.zeros(2, c.gain_knots, 1, 1))
        self.coefficient_head = nn.Linear(c.global_width, len(LUT_KEYS) * c.lut_rank)
        self.exposure_head = nn.Linear(c.global_width, 2)
        self.register_buffer("shared_lut_residual", torch.zeros(
            2, 3, c.lut_output_grid, c.lut_output_grid, c.lut_output_grid,
        ) if c.shared_training_residual else None)

        # An analytical coordinate grid, not a table obtained from the teacher.
        # Axis semantics are a convention for neutral initialization only; output
        # distillation supervises the actual contract without assuming its renderer.
        axis = torch.linspace(0.0, 1.0, c.lut_grid, dtype=torch.float32)
        identity = torch.stack(torch.meshgrid(axis, axis, axis, indexing="ij"), dim=0)
        identity_logits = torch.logit(identity.clamp(c.identity_epsilon, 1 - c.identity_epsilon))
        self.lut_mean_logits = nn.Parameter(identity_logits[None].repeat(len(LUT_KEYS), 1, 1, 1, 1))
        self.lut_bases = nn.Parameter(torch.empty(
            len(LUT_KEYS), c.lut_rank, 3, c.lut_grid, c.lut_grid, c.lut_grid,
        ))
        nn.init.normal_(self.lut_bases, mean=0.0, std=0.025)
        nn.init.normal_(self.coefficient_head.weight, mean=0.0, std=0.005)
        nn.init.zeros_(self.coefficient_head.bias)
        nn.init.zeros_(self.gain_head.weight)
        nn.init.zeros_(self.gain_head.bias)
        nn.init.zeros_(self.exposure_head.weight)
        nn.init.zeros_(self.exposure_head.bias)

    def forward(self, x: Tensor) -> dict[str, Tensor]:
        c = self.config
        if x.ndim != 4 or x.shape[1] != 5 or tuple(x.shape[-2:]) != c.input_size:
            raise ValueError(f"expected [B,5,{c.input_size[0]},{c.input_size[1]}], got {tuple(x.shape)}")
        if x.dtype != torch.float32 or self.gain_bias.dtype != torch.float32:
            raise TypeError("student inputs and parameters must be FP32")
        # Caller-controlled autocast must not silently change this research contract.
        with torch.autocast(device_type=x.device.type, enabled=False):
            batch = x.shape[0]
            mean = x.mean(dim=(-2, -1))
            variance = x.var(dim=(-2, -1), unbiased=False)
            summary = torch.cat((mean, (variance + 1e-8).sqrt()), dim=1)
            features = []
            z = self.stem(x)
            for stage in self.stages:
                z = stage(z)
                features.append(z)
            global_features = self.global_features(torch.cat((z.mean(dim=(-2, -1)), summary), dim=1))
            spatial_size = features[0].shape[-2:]
            pyramid = self.spatial_projections[0](features[0])
            for projection, feature in zip(self.spatial_projections[1:], features[1:]):
                pyramid = pyramid + F.interpolate(
                    projection(feature), size=spatial_size, mode="bilinear", align_corners=False,
                )
            pyramid = pyramid * 0.25 + self.spatial_condition(global_features)[:, :, None, None]
            raw_gains = self.gain_head(self.spatial_refine(pyramid))
            raw_gains = F.interpolate(raw_gains, size=c.gain_size, mode="bilinear", align_corners=False)
            raw_gains = raw_gains.reshape(batch, 2, c.gain_knots, *c.gain_size) + self.gain_bias[None]
            log_gains = c.max_log_gain * torch.tanh(raw_gains / c.max_log_gain)
            gains = log_gains.exp()

            coefficients = self.coefficient_head(global_features).reshape(batch, len(LUT_KEYS), c.lut_rank)
            coefficients = c.coefficient_limit * torch.tanh(coefficients / c.coefficient_limit)
            residual = torch.einsum("blr,lrcxyz->blcxyz", coefficients, self.lut_bases)
            coarse_luts = torch.sigmoid(self.lut_mean_logits[None] + residual)
            # Interpolation after sigmoid preserves the coarse tables' bounded range.
            luts = F.interpolate(
                coarse_luts.reshape(batch * len(LUT_KEYS), 3, c.lut_grid, c.lut_grid, c.lut_grid),
                size=(c.lut_output_grid,) * 3, mode="trilinear", align_corners=True,
            ).reshape(batch, len(LUT_KEYS), 3, c.lut_output_grid, c.lut_output_grid, c.lut_output_grid)
            if self.shared_lut_residual is not None:
                # Preserve fine static curvature from training-output means only.
                # One SDR/HDR residual is shared across each branch's three roles.
                luts = (luts + self.shared_lut_residual.repeat_interleave(3, dim=0)[None]).clamp(0, 1)
            exposures = self.exposure_head(global_features)
            outputs = {key: gains[:, index] for index, key in enumerate(GAIN_KEYS)}
            outputs.update({key: luts[:, index] for index, key in enumerate(LUT_KEYS)})
            outputs.update({key: exposures[:, index:index + 1] for index, key in enumerate(EXPOSURE_KEYS)})
            return {key: outputs[key] for key in OUTPUT_NAMES}

    @torch.no_grad()
    def initialize_from_training_means(self, means: Mapping[str, Tensor]) -> None:
        """Optional label-based warm start, using only training-split output means.

        Pass each mean with its normal batch dimension of one. This function never
        opens a teacher model or reads initializer tensors. Means can initialize a
        strong constant baseline; validation must still beat that baseline on
        complete heldout scenes, including image-conditioned and spatial variation.
        """
        c = self.config
        expected = output_shapes(c, batch=1)
        for key in OUTPUT_NAMES:
            if key not in means or tuple(means[key].shape) != expected[key]:
                raise ValueError(f"training mean {key} must have shape {expected[key]}")
            if means[key].dtype != torch.float32 or not torch.isfinite(means[key]).all():
                raise ValueError(f"training mean {key} must be finite FP32")
        for index, key in enumerate(GAIN_KEYS):
            if not (means[key] > 0).all():
                raise ValueError(f"training mean {key} must be positive")
            log_mean = means[key].to(self.gain_bias.device).log().mean(dim=(-2, -1), keepdim=True)[0]
            unit = (log_mean / c.max_log_gain).clamp(-0.999, 0.999)
            self.gain_bias[index].copy_(c.max_log_gain * torch.atanh(unit))
        for index, key in enumerate(LUT_KEYS):
            if not ((means[key] >= -LUT_NUMERICAL_TOLERANCE)
                    & (means[key] <= 1 + LUT_NUMERICAL_TOLERANCE)).all():
                raise ValueError(f"training mean {key} must be in [0,1] within FP32 tolerance")
            coarse = F.interpolate(
                means[key].to(self.lut_mean_logits.device), size=(c.lut_grid,) * 3,
                mode="trilinear", align_corners=True,
            )[0]
            self.lut_mean_logits[index].copy_(torch.logit(coarse.clamp(c.identity_epsilon, 1 - c.identity_epsilon)))
        self.exposure_head.bias.copy_(torch.cat([
            means[key].to(self.exposure_head.bias.device).reshape(1) for key in EXPOSURE_KEYS
        ]))
        if self.shared_lut_residual is not None:
            for branch, keys in enumerate((LUT_KEYS[:3], LUT_KEYS[3:])):
                full_mean = torch.stack([means[key][0].to(self.shared_lut_residual.device) for key in keys]).mean(0)
                coarse_mean = F.interpolate(full_mean[None], size=(c.lut_grid,) * 3,
                                            mode="trilinear", align_corners=True)
                coarse_reconstruction = F.interpolate(coarse_mean, size=(c.lut_output_grid,) * 3,
                                                       mode="trilinear", align_corners=True)[0]
                self.shared_lut_residual[branch].copy_(full_mean - coarse_reconstruction)

    def describe(self) -> dict[str, object]:
        parameter_count = sum(parameter.numel() for parameter in self.parameters())
        buffer_count = sum(buffer.numel() for buffer in self.buffers())
        return {
            "config": asdict(self.config), "parameter_count": parameter_count,
            "parameter_bytes_fp32": parameter_count * 4,
            "buffer_bytes_fp32": buffer_count * 4,
            "state_tensor_bytes_fp32": (parameter_count + buffer_count) * 4,
            "output_shapes_batch_one": output_shapes(self.config),
            "note": "Tensor storage only; excludes graph/checkpoint overhead and activation memory. No speed or quality claim.",
        }


def output_shapes(config: StudentConfig | None = None, batch: int = 1) -> dict[str, tuple[int, ...]]:
    c = config or StudentConfig()
    result = {key: (batch, c.gain_knots, *c.gain_size) for key in GAIN_KEYS}
    result.update({key: (batch, 3, c.lut_output_grid, c.lut_output_grid, c.lut_output_grid) for key in LUT_KEYS})
    result.update({key: (batch, 1) for key in EXPOSURE_KEYS})
    return {key: result[key] for key in OUTPUT_NAMES}


@dataclass(frozen=True)
class LossConfig:
    gain_weight: float = 1.0
    lut_weight: float = 1.0
    exposure_weight: float = 0.25
    gain_gradient_weight: float = 0.1
    lut_gradient_weight: float = 0.0
    render_weight: float = 0.0
    validate_values: bool = True
    gain_epsilon: float = 1e-12


class DistillationLoss(nn.Module):
    """Balanced, variation-normalizable losses over all ten teacher output arrays.

    Output counts do not set family weight: six 32-cubed LUTs cannot outweigh gain
    maps merely by having more entries. Optional per-key `normalizers` should be
    measured *once on the training split*, in log-gain / LUT-value / exposure-scalar
    units, with a defensible lower floor. Defaults are one (uncalibrated), not claims
    that the three output domains have comparable perceptual significance.

    Compare validation errors with constant training-mean predictions. Low absolute
    LUT error can conceal failure to learn a small but useful image-specific delta.
    Spatial derivatives are matched to target derivatives, not maximized: adding
    noise/edges must increase this loss rather than count as better detail.
    """

    def __init__(self, config: LossConfig | None = None, normalizers: Mapping[str, float] | None = None) -> None:
        super().__init__()
        self.config = config or LossConfig()
        self.normalizers = {key: float((normalizers or {}).get(key, 1.0)) for key in OUTPUT_NAMES}
        if normalizers and set(normalizers) - set(OUTPUT_NAMES):
            raise ValueError("unknown loss normalizer output key")
        if any(not isfinite(value) or value <= 0 for value in self.normalizers.values()):
            raise ValueError("normalizers must be finite and positive")
        weights = (self.config.gain_weight, self.config.lut_weight, self.config.exposure_weight,
                   self.config.gain_gradient_weight, self.config.lut_gradient_weight, self.config.render_weight)
        if any(not isfinite(value) or value < 0 for value in weights):
            raise ValueError("loss weights must be finite and nonnegative")
        if not isfinite(self.config.gain_epsilon) or self.config.gain_epsilon <= 0:
            raise ValueError("gain_epsilon must be finite and positive")

    def forward(
        self, predictions: Mapping[str, Tensor], targets: Mapping[str, Tensor], *,
        rendered_prediction: Tensor | None = None, rendered_target: Tensor | None = None,
    ) -> dict[str, Tensor]:
        c = self.config
        missing = set(OUTPUT_NAMES) - set(predictions) | (set(OUTPUT_NAMES) - set(targets))
        if missing:
            raise ValueError(f"missing output keys: {sorted(missing)}")
        errors: dict[str, Tensor] = {}
        gradients: dict[str, Tensor] = {}
        for key in OUTPUT_NAMES:
            prediction, target = predictions[key], targets[key].detach()
            if prediction.shape != target.shape or prediction.dtype != torch.float32 or target.dtype != torch.float32:
                raise ValueError(f"{key}: prediction/target shapes must match and both must be FP32")
            if c.validate_values:
                if not torch.isfinite(prediction).all() or not torch.isfinite(target).all():
                    raise ValueError(f"{key}: prediction/target contains non-finite values")
                if key in GAIN_KEYS and (not (prediction > 0).all() or not (target > 0).all()):
                    raise ValueError(f"{key}: gains must be positive")
                if key in LUT_KEYS and (not ((prediction >= -LUT_NUMERICAL_TOLERANCE)
                                            & (prediction <= 1 + LUT_NUMERICAL_TOLERANCE)).all()
                                        or not ((target >= -LUT_NUMERICAL_TOLERANCE)
                                                & (target <= 1 + LUT_NUMERICAL_TOLERANCE)).all()):
                    raise ValueError(f"{key}: color table values must be in [0,1] within FP32 tolerance")
            if key in GAIN_KEYS:
                prediction = prediction.clamp_min(c.gain_epsilon).log()
                target = target.clamp_min(c.gain_epsilon).log()
            scale = self.normalizers[key]
            errors[key] = (prediction - target).abs().mean() / scale
            dimensions = (-2, -1) if key in GAIN_KEYS else (-3, -2, -1) if key in LUT_KEYS else ()
            enabled = c.gain_gradient_weight if key in GAIN_KEYS else c.lut_gradient_weight if key in LUT_KEYS else 0
            if enabled:
                gradients[key] = torch.stack([
                    (torch.diff(prediction, dim=dimension) - torch.diff(target, dim=dimension)).abs().mean() / scale
                    for dimension in dimensions
                ]).mean()
        family = lambda keys: torch.stack([errors[key] for key in keys]).mean()
        gain_loss, lut_loss, exposure_loss = family(GAIN_KEYS), family(LUT_KEYS), family(EXPOSURE_KEYS)
        zero = gain_loss.new_zeros(())
        gain_gradient = torch.stack([gradients[key] for key in GAIN_KEYS]).mean() if c.gain_gradient_weight else zero
        lut_gradient = torch.stack([gradients[key] for key in LUT_KEYS]).mean() if c.lut_gradient_weight else zero
        render_loss = zero
        if c.render_weight:
            if rendered_prediction is None or rendered_target is None:
                raise ValueError("render_weight requires both outputs from the same validated renderer")
            if rendered_prediction.shape != rendered_target.shape:
                raise ValueError("rendered prediction/target shapes must match")
            if rendered_prediction.dtype != torch.float32 or rendered_target.dtype != torch.float32:
                raise ValueError("rendered prediction/target must be FP32")
            if c.validate_values and (not torch.isfinite(rendered_prediction).all() or not torch.isfinite(rendered_target).all()):
                raise ValueError("rendered prediction/target must be finite")
            render_loss = (rendered_prediction - rendered_target.detach()).abs().mean()
        total = (c.gain_weight * gain_loss + c.lut_weight * lut_loss + c.exposure_weight * exposure_loss
                 + c.gain_gradient_weight * gain_gradient + c.lut_gradient_weight * lut_gradient
                 + c.render_weight * render_loss)
        return {
            "total": total, "gain": gain_loss, "lut": lut_loss, "exposure": exposure_loss,
            "gain_gradient": gain_gradient, "lut_gradient": lut_gradient, "render": render_loss,
            **{f"output/{key}": value for key, value in errors.items()},
        }


if __name__ == "__main__":
    import json

    # Tiny CPU architecture/contract smoke only. It is not a training or quality test.
    torch.set_num_threads(1)
    torch.manual_seed(731)
    model = AdaptiveStudent(StudentConfig(input_size=(64, 64))).eval()
    with torch.no_grad():
        prediction = model(torch.rand(1, 5, 64, 64, dtype=torch.float32))
        expected = output_shapes(model.config)
        for name, value in prediction.items():
            assert tuple(value.shape) == expected[name], (name, value.shape)
            assert value.dtype == torch.float32 and torch.isfinite(value).all(), name
        loss = DistillationLoss()
        self_loss = loss(prediction, prediction)
        assert float(self_loss["total"]) == 0.0
        changed = {key: value.clone() for key, value in prediction.items()}
        changed["pgtm"][..., :48, :] *= 1.2
        changed["rgbt_1"] = changed["rgbt_1"] * 0.8
        changed["exposure_hdr"] += 0.25
        changed_loss = loss(prediction, changed)
        for key in ("gain", "lut", "exposure", "gain_gradient"):
            assert float(changed_loss[key]) > 0.0, key
        wrong = dict(changed)
        wrong["exposure"] = torch.zeros(1, 2)
        try:
            loss(prediction, wrong)
        except ValueError:
            pass
        else:
            raise AssertionError("malformed target was accepted")
    print(json.dumps({
        "scope": "Tiny CPU shape, FP32, finite/range, and loss-negative-control smoke only",
        **model.describe(), "equal_target_loss": float(self_loss["total"]),
        "perturbed_target_loss": {key: float(value) for key, value in changed_loss.items()},
        "malformed_target_rejected": True,
    }, indent=2))
