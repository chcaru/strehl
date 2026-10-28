"""Three measured camera-constant nuisances; frozen original-CFA objective."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

import numpy as np
import torch

PARENT = Path(__file__).resolve().parent.parent / "band-residual" / "sensor-operator.py"
PARENT_SHA = "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac"
if hashlib.sha256(PARENT.read_bytes()).hexdigest() != PARENT_SHA:
    raise ValueError("frozen original-CFA operator changed")
_spec = importlib.util.spec_from_file_location("constant_deflation_frozen_base", PARENT)
base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = base
_spec.loader.exec_module(base)

Config, Query, Source = base.Config, base.Query, base.Source
Measurement, HaarPlan = base.Measurement, base.HaarPlan
norm_pair, SquaredNorm = base.norm_pair, base.SquaredNorm
integrate_reference = base.integrate_reference


def _dot(a, b):
    if len(a) != len(b):
        raise ValueError("projection row inventory differs")
    total = torch.tensor(0, dtype=torch.float32)
    for x, y in zip(a, b):
        if x.shape != y.shape:
            raise ValueError("projection row shape differs")
        total = total + (base._f32(x) * base._f32(y)).sum(dtype=torch.float32)
    return base._finite(total, "projection inner product")


def _one_norm():
    return SquaredNorm(torch.tensor(.5, dtype=torch.float32), 1)


class ConstantProjection:
    """P=I-T(T'T)^-1T', actual T=B C, one G constant for both G phases."""
    def __init__(self, problem):
        self.problem = problem
        self.columns = []
        for color in range(3):
            constant = torch.zeros((*problem.config.field_hw, 3), dtype=torch.float32)
            constant[..., color] = 1
            column = [base._finite(v, "actual B(constant)") for v in problem.forward(constant)]
            self.columns.append(column)
        self.column_norms = torch.stack([norm_pair(v).root_ratio(_one_norm()) for v in self.columns])
        if not bool(torch.isfinite(self.column_norms).all()) or bool((self.column_norms <= 0).any()):
            raise ValueError("unsupported zero/nonfinite camera-constant direction")
        self.normalized_columns = [[v / self.column_norms[c] for v in col]
                                   for c, col in enumerate(self.columns)]
        gram = torch.stack([torch.stack([_dot(a, b) for b in self.normalized_columns])
                            for a in self.normalized_columns])
        self.gram_diagonal = torch.diag(gram).clone()
        # Actual original-photosite channels are disjoint; do not silently use
        # a diagonal inverse if a different producing operator couples them.
        for c in range(3):
            for d in range(c):
                if any(bool(((a != 0) & (b != 0)).any())
                       for a, b in zip(self.columns[c], self.columns[d])):
                    raise ValueError("camera-constant supports overlap")
                if float(gram[c, d]) != 0 or float(gram[d, c]) != 0:
                    raise ValueError("camera-constant Gram not color-disjoint")
        if (not bool(torch.isfinite(gram).all()) or bool((self.gram_diagonal <= 0).any())
                or bool((self.gram_diagonal - 1).abs().gt(2e-5).any())):
            raise ValueError("constant Gram normalization unsupported")
        self.evidence = dict(constant_channels=["R", "G", "B"],
            green_constant_covers_both_physical_phases=True,
            actual_B_constant_calls=3, actual_color_supports_disjoint=True,
            column_norms_f32=self.column_norms.tolist(),
            normalized_gram_f32=gram.tolist(), scalar_gram_inverse=True,
            constant_basis_includes_full_free_apron=True)

    def project(self, rows):
        amplitudes = [_dot(col, rows) / self.gram_diagonal[c]
                      for c, col in enumerate(self.normalized_columns)]
        result = [base._f32(v).clone() for v in rows]
        for amplitude, col in zip(amplitudes, self.normalized_columns):
            result = [v - amplitude * u for v, u in zip(result, col)]
        return [base._finite(v, "projected rows") for v in result]

    def coefficients(self, rows):
        return torch.stack([_dot(col, rows) / self.gram_diagonal[c] / self.column_norms[c]
                            for c, col in enumerate(self.normalized_columns)])

    def nuisance_coordinates(self, rows):
        return torch.stack([_dot(col, rows) for col in self.normalized_columns])

    def restore_with_coefficients(self, z, rhs=None):
        rhs = self.problem.rhs if rhs is None else rhs
        residual = [b - v for b, v in zip(rhs, self.problem.forward(z))]
        coefficients = self.coefficients(residual)
        x = base._f32(z) + coefficients.reshape(1, 1, 3)
        return base._finite(x, "restored physical X"), coefficients

    def restore(self, z, rhs=None):
        return self.restore_with_coefficients(z, rhs)[0]


class ProjectedProblem:
    def __init__(self, original):
        self.original = original
        self.projection = ConstantProjection(original)
        self.rhs = self.projection.project(original.rhs)
        self.evidence = dict(original.evidence)
        self.evidence.update(parent_operator_sha256=PARENT_SHA,
            projection=self.projection.evidence,
            objective="projected correction coordinates: ||P(Bz-b)||^2; same original objective after constant restoration",
            history_coordinate_system="projected correction z, not restored physical X",
            implicit_completion="zero-start minimum correction norm; not necessarily old minimum physical-image norm",
            nuisance_truth_used=False, priors_added=False, weights_changed=False)

    def __getattr__(self, name):
        return getattr(self.original, name)

    def forward(self, z):
        return self.projection.project(self.original.forward(z))

    def adjoint(self, rows):
        return self.original.adjoint(self.projection.project(rows))

    def residual(self, z):
        return [b - v for b, v in zip(self.rhs, self.forward(z))]

    def objective(self, z):
        value = norm_pair(self.residual(z))
        return {"scaled": value.receipt(), "original": value.scaled(self.metric_scale).receipt()}


def prepare(sources, config, mode="candidate", metric_override=None):
    return ProjectedProblem(base.prepare(sources, config, mode, metric_override))


class FitResult(base.FitResult):
    def save(self, out_dir):
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=False)
        records = {}
        for name, value in (("latent", self.x), ("output", self.output),
                            ("correction-z", self.correction_z)):
            base._finite(value, "saved " + name)
            path = out / (name + ".npy")
            np.save(path, value.detach().numpy(), allow_pickle=False)
            records[name] = dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        receipt = dict(status=self.status, converged=self.converged, iterations=self.iterations,
            history=self.history, evidence=self.evidence, **records,
            admission=False, quality_claim=False)
        (out / "result.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        return receipt


def _relative(current, initial):
    if initial.is_zero:
        return 0.0 if current.is_zero else None
    ratio = current.root_ratio(initial)
    return float(ratio) if bool(torch.isfinite(ratio)) else None


def fit(problem):
    if not isinstance(problem, ProjectedProblem):
        raise ValueError("constant-deflation prepare result required")
    # The complete recursive CGLS implementation and its64-step work cap remain
    # byte-frozen. Its history refers ONLY to projected correction coordinates.
    projected_result = base.fit(problem)
    z = projected_result.x
    original = problem.original
    projection = problem.projection
    x, coefficients = projection.restore_with_coefficients(z)
    zero = torch.zeros_like(z)
    initial_x, initial_constants = projection.restore_with_coefficients(zero)
    actual_residual = original.residual(x)
    initial_residual = original.residual(initial_x)
    projected_initial_normal = original.adjoint(projection.project(problem.rhs))
    initial_norm = norm_pair(projected_initial_normal)
    actual_full_normal = original.adjoint(actual_residual)
    actual_projected_normal = original.adjoint(projection.project(actual_residual))
    full_relative = _relative(norm_pair(actual_full_normal), initial_norm)
    projected_relative = _relative(norm_pair(actual_projected_normal), initial_norm)
    nuisance = projection.nuisance_coordinates(actual_residual)
    original_objective = norm_pair(actual_residual)
    initial_objective = norm_pair(initial_residual)
    final_projected = norm_pair(projection.project(actual_residual))
    raw_zero_normal = norm_pair(original.adjoint(original.rhs))
    old_reference_ratio = _relative(norm_pair(actual_full_normal), raw_zero_normal)
    restored_pass = (full_relative is not None and projected_relative is not None
        and full_relative <= 1e-5 and projected_relative <= 1e-5
        and original_objective.le(initial_objective))
    converged = bool(projected_result.converged and restored_pass)
    status = ("restored-original-normal-converged" if converged else
              "restored-original-normal-refused" if projected_result.converged else
              "projected-" + projected_result.status)
    output = base._finite(integrate_reference(x, problem.config), "restored delivered output")
    history = [dict(entry, coordinate_system="projected correction z")
               for entry in projected_result.history]
    evidence = dict(projected_result.evidence)
    evidence.update(projected_solver_status=projected_result.status,
        projected_solver_converged=projected_result.converged,
        restored_numerical_pass=restored_pass,
        restored_constants_f32=coefficients.tolist(),
        constant_only_initial_f32=initial_constants.tolist(),
        actual_projected_initial_normal=initial_norm.receipt(),
        restored_true_full_normal=norm_pair(actual_full_normal).receipt(),
        restored_true_projected_normal=norm_pair(actual_projected_normal).receipt(),
        restored_full_normal_relative=full_relative,
        restored_projected_normal_relative=projected_relative,
        old_zero_start_full_normal_relative=old_reference_ratio,
        restored_nuisance_normalized_coordinates_f32=nuisance.tolist(),
        restored_nuisance_coordinate_norm=norm_pair(nuisance).receipt(),
        restored_nuisance_raw_T_coordinates_f32=(nuisance * projection.column_norms).tolist(),
        restored_objective_scaled=original_objective.receipt(),
        restored_objective_original=original_objective.scaled(original.metric_scale).receipt(),
        restored_projected_objective_original=final_projected.scaled(original.metric_scale).receipt(),
        constant_only_initial_objective_original=initial_objective.scaled(original.metric_scale).receipt(),
        restored_original_objective_no_greater_than_constant_initial=original_objective.le(initial_objective),
        # Additional calls are to the original B/B-transpose, outside the
        # inherited projected-call timing seam. All are within fit wall time.
        extra_original_forward_calls=4, extra_original_adjoint_calls=4,
        extra_actual_weighted_operator_calls_not_hidden=True,
        reference_cell_delivery_count=2,
        physical_output_is_restored_X=True, correction_z_retained=True,
        physical_original_objective_history="final and constant-only initial evaluated; per-iteration history is explicitly projected z",
        parent_source_unchanged=hashlib.sha256(PARENT.read_bytes()).hexdigest() == PARENT_SHA)
    if not evidence["parent_source_unchanged"]:
        raise ValueError("frozen parent changed during fit")
    result = FitResult(x, output, status, converged, projected_result.iterations, history, evidence)
    result.correction_z = z
    return result
