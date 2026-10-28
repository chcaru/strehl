"""Independent fixed controls for exact constant-color elimination.

Root alone executes. Reuses original fixtures, actual baselines and image guards;
no altered acquisition, repeated fit of the old recipe, or photographic admission.
"""
import argparse
import gc
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "band-residual"
sys.path.insert(0, str(PARENT))
spec = importlib.util.spec_from_file_location("frozen_band_controls", PARENT / "controls.py")
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)
fx = c.fx

FROZEN_PARENT = {
    "sensor-operator.py": "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac",
    "controls.py": "094b633678e44e7ebfa63c9648db03c2e3aa182406383b4989d0f42ba7a36120",
    "fixtures.py": "759f3b7d24ec480ab7158e149eb3030e613c4d3e6ae7000d5dd07644c9ab1ba6",
}
REL = 2e-5


def load_model(expected):
    for name, digest in FROZEN_PARENT.items():
        if fx.file_ref(PARENT / name)["sha256"] != digest:
            raise ValueError("frozen parent source changed: " + name)
    path = HERE / "sensor-operator.py"
    if fx.file_ref(path)["sha256"] != expected:
        raise ValueError("deflated operator differs from root binding")
    module_spec = importlib.util.spec_from_file_location("independent_constant_operator", path)
    model = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = model
    module_spec.loader.exec_module(model)
    return model


def flat(rows):
    return torch.cat([v.reshape(-1) for v in rows])


def subtract(left, right):
    return [a-b for a, b in zip(left, right)]


def relative_error(left, right):
    return c.norm(left-right) / max(1., c.norm(left), c.norm(right))


def projection_mechanics(model, manifest, out):
    """Known fields commission algebra only; no fixture truth enters a fit."""
    row, arrays = fx.load_case(manifest, "independent-colour")
    config = c.config_for(model, row)
    all_sources = c.make_sources(model, row, arrays)
    # Unequal color content, geometry and physical G noise; fixed before results.
    problem = model.prepare([all_sources[0], all_sources[3]], config)
    original, projection = problem.original, problem.projection
    frozen = [v.clone() for v in original.metrics + original.factors]
    rhs_before = [v.clone() for v in original.rhs]
    columns, literal = projection.columns, []
    fields = []
    for channel in range(3):
        field = torch.zeros((*config.field_hw, 3), dtype=torch.float32)
        field[..., channel] = 1.
        fields.append(field)
        literal.append(original.forward(field))
    column_errors = [c.error(flat(a), flat(b)) for a, b in zip(columns, literal)]
    u = np.stack([flat(v).numpy().astype(np.float64) for v in literal])
    gram = u @ u.T
    diagonal = np.diag(gram)
    normalized_gram = gram / np.sqrt(diagonal[:, None]*diagonal[None, :])
    cross = normalized_gram-np.eye(3)
    disjoint = all(not np.any((u[a] != 0) & (u[b] != 0))
                   for a in range(3) for b in range(a))
    gram_ok = bool(np.isfinite(gram).all() and np.all(diagonal > 0)
                   and np.max(np.abs(cross)) <= REL and disjoint)

    # Deterministic weighted-space vectors include all three DC columns.
    rows = []
    for index, value in enumerate(original.rhs):
        j = torch.arange(value.numel(), dtype=torch.float32).reshape(value.shape)
        rows.append(torch.sin(j*.017 + index*.3) + .4*torch.cos(j*.031)
                    + 17*literal[0][index]-11*literal[1][index]+7*literal[2][index])
    other = [torch.cos(torch.arange(v.numel(), dtype=torch.float32).reshape(v.shape)*.023)
             + 5*literal[1][i] for i, v in enumerate(rows)]
    projected = projection.project(rows)
    twice = projection.project(projected)
    reference = flat(rows).numpy().astype(np.float64)
    reference = reference - np.sum(u * ((u @ reference)/diagonal)[:, None], axis=0)
    literal_projection = c.norm(flat(projected).numpy()-reference)/max(1., c.norm(reference))
    idempotence = relative_error(flat(twice), flat(projected))
    symmetry = c.dot_guard(flat(projected), flat(other), flat(rows),
                           flat(projection.project(other)))
    annihilation = [c.norm(flat(projection.project(v)))/max(1., c.norm(flat(v)))
                    for v in literal]

    yy, xx = np.mgrid[:config.field_hw[0], :config.field_hw[1]]
    z = torch.from_numpy(np.stack((400*np.sin(.13*xx)+90*np.cos(.17*yy),
        250*np.cos(.11*xx-.07*yy), 320*np.sin(.09*xx+.15*yy)), -1).astype(np.float32))
    t_forward = problem.forward(z)
    expected_forward = projection.project(original.forward(z))
    forward_error = relative_error(flat(t_forward), flat(expected_forward))
    expected_adjoint = original.adjoint(projection.project(other))
    transpose_error = relative_error(problem.adjoint(other), expected_adjoint)
    t_adjoint = c.dot_guard(flat(t_forward), flat(other), z, problem.adjoint(other))
    t_constants = [c.norm(flat(problem.forward(field)))/max(1., c.norm(flat(col)))
                   for field, col in zip(fields, literal)]
    # Deliberately remove P only from the transpose, leaving producing PB intact.
    foil_x = fields[0]*4096
    foil_y = [v*4096 for v in literal[0]]
    wrong_one_sided = c.dot_guard(flat(problem.forward(foil_x)), flat(foil_y),
                                 foil_x, original.adjoint(foil_y))

    restored = projection.restore(z)
    raw_residual = subtract(original.rhs, original.forward(restored))
    projected_residual = projection.project(subtract(original.rhs, original.forward(z)))
    residual_identity = relative_error(flat(raw_residual), flat(projected_residual))
    raw_objective = c.dot(flat(raw_residual), flat(raw_residual))
    projected_objective = c.dot(flat(projected_residual), flat(projected_residual))
    objective_identity = abs(raw_objective-projected_objective)/max(1., raw_objective, projected_objective)

    # Frozen-q affine equivariance is an algebra control, never changed codes or a second fit.
    delta = torch.tensor([37., -23., 11.], dtype=torch.float32)
    dc_field = torch.ones_like(z)*delta
    dc_rows = original.forward(dc_field)
    shifted_rhs = [b+d for b, d in zip(original.rhs, dc_rows)]
    shifted = projection.restore(z, rhs=shifted_rhs)
    dc_error = c.error(shifted-restored, dc_field)
    projected_rhs_error = relative_error(flat(projection.project(shifted_rhs)),
                                         flat(projection.project(original.rhs)))
    unchanged = (all(torch.equal(a, b) for a, b in zip(frozen, original.metrics+original.factors))
                 and all(torch.equal(a, b) for a, b in zip(rhs_before, original.rhs)))
    for source in row["sources"]:
        c.verify_ref(source)

    result = dict(physical_source_ids=[0, 3], literal_BC_errors=column_errors,
        gram=gram.tolist(), normalized_gram=normalized_gram.tolist(),
        disjoint_color_support=disjoint, gram_pass=gram_ok,
        literal_P_relative_error=literal_projection, idempotence_relative_error=idempotence,
        P_symmetry=symmetry, U_annihilation_relative=annihilation,
        producing_T_forward_relative_error=forward_error,
        producing_T_transpose_relative_error=transpose_error,
        T_adjoint=t_adjoint, T_constants_annihilation_relative=t_constants,
        wrong_one_sided=wrong_one_sided, wrong_one_sided_rejected=not wrong_one_sided["pass_guard"],
        restored_residual_relative_error=residual_identity,
        restored_objective=raw_objective, projected_objective=projected_objective,
        restored_objective_relative_error=objective_identity,
        frozen_q_DC_offset=dict(offset_camera_dn=delta.tolist(), restored_delta_error=dc_error,
            projected_rhs_relative_error=projected_rhs_error, original_metric_factors_rhs_unchanged=unchanged,
            fit_performed=False, acquisition_recomputed=False),
        relative_bound=REL, DN_bound=dict(maximum=.05, rms=.01),
        truth_initialization=False, photographic_admission=False)
    result["pass_guard"] = bool(gram_ok and all(e["maximum"] <= .05 and e["rms"] <= .01 for e in column_errors)
        and max(literal_projection, idempotence, *annihilation, forward_error,
                transpose_error, *t_constants, residual_identity, objective_identity,
                projected_rhs_error) <= REL
        and symmetry["pass_guard"] and t_adjoint["pass_guard"] and not wrong_one_sided["pass_guard"]
        and dc_error["maximum"] <= .05 and dc_error["rms"] <= .01 and unchanged)
    fx.save_json(out/"projection-algebra.json", result)
    del problem, original, projection, arrays, all_sources
    gc.collect()
    # Actual projected zero-RHS path; zero iterations is not an extra image campaign.
    zero_row, zero_arrays = fx.load_case(manifest, "flat-neutral")
    zero_sources = c.make_sources(model, zero_row, zero_arrays)
    zero_source = model.Source(0, zero_sources[0].query, np.full((128, 128), fx.BLACK, np.uint16))
    zero_problem = model.prepare([zero_source], c.config_for(model, zero_row))
    zero_fit = model.fit(zero_problem)
    saved = zero_fit.save(out/"projected-zero-rhs")
    zero = dict(status=zero_fit.status, converged=zero_fit.converged, iterations=zero_fit.iterations,
        complete_field=saved, output_max=float(zero_fit.output.abs().max()),
        complete_display=fx.preview(out/"projected-zero-rhs"/"complete-output.png", zero_fit.output))
    zero["pass_guard"] = bool(zero_fit.converged and zero_fit.iterations == 0 and zero["output_max"] == 0.)
    result["projected_zero_rhs"] = zero
    result["pass_guard"] = result["pass_guard"] and zero["pass_guard"]
    fx.save_json(out/"projection-mechanics.json", result)
    return result


def run(args):
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    model = load_model(args.expected_operator_sha)
    manifest_ref = fx.file_ref(Path(args.fixtures).resolve())
    manifest = c.load_json(c.verify_ref(manifest_ref))
    if manifest["cases_order"] != list(fx.CASES) or manifest["total_full_screen_fits"] != 14:
        raise ValueError("fixed ten-candidate/four-foil inventory differs")
    fx.ICC = c.verify_ref(manifest["display_icc"]).read_bytes()
    baselines, baseline_evidence = c.read_baselines(args.baseline, manifest, out)
    if set(baselines) != set(fx.CASES):
        raise ValueError("all ten bound actual product baselines are required")
    sources = [fx.file_ref(PARENT/name) for name in FROZEN_PARENT]
    sources += [fx.file_ref(HERE/name) for name in ("controls.py", "sensor-operator.py", "brief.md")]
    started = dict(command=[sys.executable, *sys.argv], stage=args.stage,
        sources=sources, fixture_manifest=manifest_ref, actual_baseline=baseline_evidence,
        torch_version=torch.__version__, cpu_workers=torch.get_num_threads(), tf32=False,
        maximum_iterations=64, normal_tolerance=1e-5, candidate_fits=1 if args.stage == "cost" else 10,
        auxiliary_fits=0 if args.stage == "cost" else 4, score_xywh=[16, 16, 96, 96],
        timing_semantics="inherited fit_one times producing projected T/T-transpose calls; unprojected restoration and physical diagnostics remain in fit_and_delivery/non-operator time; prepare includes actual constant columns",
        completion_semantics="projected zero-start correction can choose different physical minimum-norm completion; same objective/minimizer family is not identical finite output",
        admission=False, photographic_admission=False)
    fx.save_json(out/"started.json", started)
    screen = dict(status="STARTED", stage=args.stage, all_cases_completed=False,
        mechanical_pass=False, model_adequacy_pass=False, numerical_pass=False, quality_pass=False,
        admission=False, photographic_admission=False, full_design_qualified=False, cases=[])
    try:
        begin = time.perf_counter()
        base_out, projection_out = out/"base-commission", out/"projection-commission"
        base_out.mkdir()
        projection_out.mkdir()
        base_checks = c.mechanics(model.base, manifest, base_out)
        projection_checks = projection_mechanics(model, manifest, projection_out)
        screen["mechanics_wall_seconds"] = time.perf_counter()-begin
        screen["base_mechanics"] = fx.file_ref(base_out/"mechanics.json")
        screen["projection_mechanics"] = fx.file_ref(projection_out/"projection-mechanics.json")
        screen["mechanical_pass"] = base_checks["mechanical_pass"] and projection_checks["pass_guard"]
        screen["model_adequacy_pass"] = base_checks["model_adequacy_pass"]
        if not screen["mechanical_pass"]:
            screen["status"] = "MECHANICAL_REFUSAL"
        else:
            cases = ("flat-neutral",) if args.stage == "cost" else fx.CASES
            for case in cases:
                modes = ("candidate",) if args.stage == "cost" else ("candidate", *fx.EXTRA_FIT_MODES.get(case, ()))
                for mode in modes:
                    row = c.fit_one(model, manifest, case, mode, baselines[case], out)
                    screen["cases"].append(row)
                    fx.save_json(out/f"progress-{len(screen['cases']):02d}.json", screen)
            screen["all_cases_completed"] = True
            candidates = [r for r in screen["cases"] if r["mode"] == "candidate"]
            screen["numerical_pass"] = all(r["converged"] for r in candidates)
            screen["quality_pass"] = all(r["quality_guard"]["pass_guard"] for r in candidates)
            if args.stage == "cost":
                screen["fixed_full_projection"] = dict(
                    rule="mechanics_wall_seconds+14*inherited_projected_64_step_fit_seconds",
                    seconds=screen["mechanics_wall_seconds"]+14*candidates[0]["timing"]["projected_64_step_fit_seconds"],
                    measured_full_screen=False, automatic_release=False, fits=14, maximum_iterations=64)
            screen["status"] = ("COMPLETE_CONSTANT_DEFLATION_COST_DIAGNOSTIC" if args.stage == "cost"
                                else "COMPLETE_CONSTANT_DEFLATION_GENERATED_DIAGNOSTIC")
        screen["all_pass"] = bool(screen["all_cases_completed"] and screen["mechanical_pass"]
            and screen["model_adequacy_pass"] and screen["numerical_pass"] and screen["quality_pass"])
        for ref in [manifest_ref, *sources]:
            c.verify_ref(ref)
        screen["bound_sources_unchanged"] = True
    except Exception as exc:
        screen.update(status="HARD_FAILURE_WITH_RETAINED_EVIDENCE", error=str(exc),
                      traceback=traceback.format_exc(), all_pass=False)
        fx.save_json(out/"screen.json", screen)
        raise
    fx.save_json(out/"screen.json", screen)
    print(json.dumps({k: screen[k] for k in ("status", "all_cases_completed", "mechanical_pass",
        "model_adequacy_pass", "numerical_pass", "quality_pass", "admission", "photographic_admission")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("cost", "full"))
    parser.add_argument("--fixtures", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--expected-operator-sha", required=True)
    parser.add_argument("--out", required=True)
    run(parser.parse_args())
