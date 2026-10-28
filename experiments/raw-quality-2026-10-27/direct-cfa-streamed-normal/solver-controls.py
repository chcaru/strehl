"""Root-scheduled fixed64 normal-CG path controls; no photo admission."""
from pathlib import Path
import argparse
import math
import traceback
import numpy as np
import torch
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
LIMIT = 8 << 30
EXPECTED = {
    HERE / "controls.py": "87639a616aa8222b5c363b9e6d27994f2b51b8adfdcac5e462520b11c99c9494",
    HERE / "solver.py": "e98dbfd8201785ce4f3e068508939d0815c6d3e500085ba0ed875512db8d9c88",
    HERE / "normal-operator.py": "0b6d8d2110ae62ddc493cd8f1d2540830884ea1257a1ec2d910208461aa3b269",
    HERE / "bands-gpu.py": "d837961600d327d8aa3b5438565c357dd01327c1e6f6ffc4dc4b445b021cf1be",
    HERE / "measurement-paired.py": "0adbba770b06305b8bbf26a497b9b1f1ab95332edc28037634362232ebe09023",
}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    return module


def sqrt_receipt(value):
    return math.sqrt(math.ldexp(value["mantissa_f32"], value["binary_exponent"]))


class DiagonalProblem:
    """Independent exact algebra fixture, not an original-CFA surrogate."""
    def __init__(self, operator, mode="ordinary", zero=False):
        self.torch = torch; self.field_hw = (1, 4); self.operator = operator
        self.diagonal = torch.tensor([.5, 1., 1.5, 2.], device="cuda:0", dtype=torch.float32).reshape(1, 4, 1).expand(1, 4, 3).clone()
        self.target = torch.tensor([.75, -.4, 1.2, -.8, .6, -.3, 1.1, -.7, .2, -.5, .9, -1.3], device="cuda:0", dtype=torch.float32).reshape(1, 4, 3)
        if zero: self.target.zero_()
        self.mode = mode; self.calls = 0; self.evaluations = 0

    def rhs(self):
        return self.diagonal * self.target

    def normal(self, x):
        self.calls += 1
        if self.mode == "negative-curvature": return -self.diagonal * x
        if self.mode == "wrong-identity-normal": return x.clone()
        return self.diagonal * x

    def evaluate(self, z):
        self.evaluations += 1
        residual = self.diagonal * (self.target - z)
        objective = self.operator.norm_pair(torch, torch.sqrt(self.diagonal) * (self.target-z))
        zero = torch.zeros(3, device="cuda:0", dtype=torch.float32)
        return dict(x=z.clone(), full_normal=residual, projected_normal=residual.clone(),
            nuisance_T_residual=zero, nuisance_U_residual=zero.clone(), objective=objective,
            original_objective=objective, restored_constants=zero.clone())

    def metadata(self):
        return dict(algebra_fixture=True, original_CFA_problem=False, diagonal=self.diagonal.cpu().tolist(),
                    normal_mode=self.mode, calls=self.calls, evaluations=self.evaluations)


def contract(result, control):
    e = result.evidence
    finite = bool(torch.isfinite(result.x).all() and torch.isfinite(result.correction_z).all())
    objective = e["restored_objective_scaled"]
    initial_objective = e["constant_initial_objective_scaled"]
    objective_pass = math.ldexp(objective["mantissa_f32"], objective["binary_exponent"]) <= math.ldexp(initial_objective["mantissa_f32"], initial_objective["binary_exponent"])
    ratios = (e["restored_full_normal_relative"], e["restored_projected_normal_relative"])
    literal_numerical_pass = all(v is not None and math.isfinite(v) and v <= 1e-5 for v in ratios) and objective_pass
    pass_logical = bool(e["restored_numerical_pass"] and
                        (e["recursive_threshold_reached"] or e["recurrence_status"] == "iteration-cap"))
    expected = "restored-original-normal-converged" if pass_logical else "refused-" + e["recurrence_status"]
    history_ok = len(result.history) == result.iterations+1 and all(
        r["iteration"] == i and r["true_objective_checked"] is False
        for i, r in enumerate(result.history))
    calls = e["normal_operator_calls_in_recurrence"]
    gates = dict(finite_complete=finite and result.x.shape == result.correction_z.shape,
        fixed_work=e["maximum_iterations"] == 64 and e["normal_tolerance"] == 1e-5
            and e["restarts"] == 0 and e["preconditioner"] is None,
        bounded_iterations=0 <= result.iterations <= 64 and result.iterations <= calls <= min(64,result.iterations+1),
        history=history_ok, status_consistent=result.converged == pass_logical and result.status == expected,
        literal_final_gate=e["restored_numerical_pass"] == literal_numerical_pass
            and e["restored_objective_no_greater_than_initial"] == objective_pass,
        no_intermediate_truth_claim=e["true_intermediate_objectives_evaluated"] is False
            and e["intermediate_objective_monotonicity_claim"] is False,
        no_photo_claim=e["quality_claim"] is False and e["prior_photographic_admission"] is False)
    return dict(gates=gates, pass_=all(gates.values()))


def record_fit(out, name, problem, solver, control):
    result = solver.fit(problem)
    receipt = result.save(out / name)
    return result, dict(result=receipt, contract=contract(result, control))


def run(out, control):
    paths = [Path(__file__), HERE/"solver-controls-plan.md", *EXPECTED,
             control.PARENT/"controls.py", control.PARENT/"measurement-gpu.py", control.CPU, control.BASE]
    before = [control.ref(p) for p in paths]
    pins = {**EXPECTED, control.CPU:control.CPU_SHA, control.BASE:control.BASE_SHA,
            control.PARENT/"controls.py":control.HELPER_SHA,
            control.PARENT/"measurement-gpu.py":control.MEASUREMENT_SHA}
    for p, value in pins.items():
        if control.ref(p)["sha256"] != value: raise ValueError("frozen dependency changed: " + str(p))
    torch.set_num_threads(4); torch.set_num_interop_threads(1); torch.set_default_dtype(torch.float32)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available(): raise RuntimeError("CUDA required")
    torch.cuda.set_device(0); props = torch.cuda.get_device_properties(0)
    torch.cuda.set_per_process_memory_fraction(min(1., LIMIT/props.total_memory), 0)
    torch.cuda.reset_peak_memory_stats()
    solver = load(HERE/"solver.py", "commission_fixed64_solver")
    results = {}
    zero = DiagonalProblem(solver.operator, zero=True)
    r, entry = record_fit(out,"zero-rhs",zero,solver,control)
    entry["pass_"] = entry["contract"]["pass_"] and r.converged and r.iterations == 0 and bool((r.x == 0).all())
    results["zero_rhs"] = entry
    spd = DiagonalProblem(solver.operator)
    r, entry = record_fit(out,"known-spd",spd,solver,control)
    entry["solution"] = control.compare(r.x,spd.target)
    entry["pass_"] = entry["contract"]["pass_"] and r.converged and entry["solution"]["pass_"] and 0 < r.iterations <= 64
    results["known_spd"] = entry
    negative = DiagonalProblem(solver.operator, mode="negative-curvature")
    r, entry = record_fit(out,"negative-curvature",negative,solver,control)
    entry["pass_"] = entry["contract"]["pass_"] and not r.converged and r.iterations == 0 and bool((r.x == 0).all()) and r.status == "refused-nonpositive-or-nonfinite-normal-curvature"
    results["negative_curvature"] = entry
    wrong = DiagonalProblem(solver.operator, mode="wrong-identity-normal")
    r, entry = record_fit(out,"false-recursive-convergence",wrong,solver,control)
    entry["pass_"] = entry["contract"]["pass_"] and not r.converged and r.iterations == 1 and r.evidence["recursive_threshold_reached"] and r.evidence["restored_objective_no_greater_than_initial"] and not r.evidence["restored_numerical_pass"]
    results["false_recursive_convergence"] = entry
    # Actual candidate, independent CPU original objective at returned physical X.
    helper = control.load(control.PARENT/"controls.py", "solver_original_coordinates")
    cpu = control.load(control.CPU, "solver_frozen_cpu_reference")
    pair = control.load(HERE/"measurement-paired.py", "solver_paired_measurement")
    rows = control.make_inputs(helper); original_hashes = control.hashes([r["codes"] for r in rows])
    artifacts = {}
    for row in rows:
        artifacts[f"source-{row['sid']}"] = helper.save_array(out,f"source-{row['sid']}-original-u16",row["codes"])
    fhw = tuple(v+16 for v in control.HW)
    engine = pair.PairedMeasurementGpu(torch,fhw,device_limit_bytes=LIMIT)
    problem = control.build_gpu(solver.operator,engine,rows)
    reference = control.build_cpu(cpu,rows)
    r, entry = record_fit(out,"actual-original-cfa",problem,solver,control)
    x = control.cpu_tensor(r.x); z = control.cpu_tensor(r.correction_z)
    residual = reference.original.residual(x)
    full = reference.original.adjoint(residual)
    projected = reference.original.adjoint(reference.projection.project(residual))
    raw = reference.original.adjoint(reference.original.rhs)
    restored = reference.projection.restore(z)
    initial = reference.adjoint(reference.rhs)
    init_norm = control.norm(initial); raw_norm = control.norm(raw)
    objective = cpu.norm_pair(residual).receipt()["value_f32"]
    reported_objective = r.evidence["restored_objective_scaled"]["value_f32"]
    checks = {"restored_x":control.compare(x,restored),
              "objective":control.compare(np.float32(reported_objective),np.float32(objective))}
    for name, value in (("full",full),("projected",projected)):
        expected_norm = control.norm(value)
        recorded_norm = sqrt_receipt(r.evidence[f"restored_true_{name}_normal"])
        budget = control.NORMAL_RTOL*expected_norm+32*control.EPS*raw_norm
        scalar_error = abs(recorded_norm-expected_norm)
        checks[name+"_normal_magnitude"] = dict(expected_l2=expected_norm,recorded_l2=recorded_norm,
            error_l2=scalar_error,allowed_error=budget,pass_=scalar_error <= budget)
        ratio = r.evidence[f"restored_{name}_normal_relative"]
        expected_ratio = expected_norm/init_norm
        # Account independently for both numerator and initial-normal comparison.
        initial_error_budget=control.NORMAL_RTOL*init_norm+32*control.EPS*raw_norm
        ratio_budget=budget/init_norm+expected_ratio*initial_error_budget/init_norm
        checks[name+"_normal_ratio"] = dict(expected=expected_ratio,recorded=ratio,
            allowed_error=ratio_budget,pass_=ratio is not None and abs(ratio-expected_ratio) <= ratio_budget,
            threshold_resolved=abs(expected_ratio-1e-5)>ratio_budget)
        artifacts["actual-cpu-"+name+"-normal"] = helper.save_array(out,"actual-cpu-"+name+"-normal",value)
    initial_recorded=sqrt_receipt(r.evidence["actual_projected_initial_normal"])
    initial_budget=control.NORMAL_RTOL*init_norm+32*control.EPS*raw_norm
    checks["initial_normal"] = dict(expected=init_norm,recorded=initial_recorded,allowed_error=initial_budget,
        pass_=abs(initial_recorded-init_norm)<=initial_budget)
    # Crosscheck convergence truth when numerical comparison resolves the bar.
    resolved=all(checks[n+"_normal_ratio"]["threshold_resolved"] for n in ("full","projected"))
    cpu_norm_pass=all(checks[n+"_normal_ratio"]["expected"]<=1e-5 for n in ("full","projected"))
    reported_norm_pass=all(r.evidence[f"restored_{n}_normal_relative"]<=1e-5 for n in ("full","projected"))
    checks["resolved_normal_gate"] = dict(resolved=resolved,cpu_pass=cpu_norm_pass,
        reported_pass=reported_norm_pass,pass_=not resolved or cpu_norm_pass==reported_norm_pass)
    unchanged=control.hashes([row["codes"] for row in rows])==original_hashes
    entry.update(checks=checks,original_codes_unchanged=unchanged,
        numerical_status_is_quality_gate=False,complete_field_shape=list(r.x.shape),
        pass_=entry["contract"]["pass_"] and all(v["pass_"] for v in checks.values())
              and unchanged and list(r.x.shape)==[35,39,3])
    results["actual_original_cfa"] = entry
    after=[control.ref(p) for p in paths]
    torch.cuda.synchronize()
    memory=dict(allocated=torch.cuda.max_memory_allocated(),reserved=torch.cuda.max_memory_reserved(),limit=LIMIT)
    if max(memory["allocated"],memory["reserved"])>LIMIT: raise ValueError("8GiB Torch cap")
    return dict(status="COMPLETE_DIRECT_CFA_SOLVER_CONTROLS",all_cases_completed=True,
        mechanical_pass=all(v["pass_"] for v in results.values()) and before==after,
        photographic_admission=False,quality_claim=False,RAW_reads=0,reconstruction_quality_scored=False,
        maximum_iterations=64,normal_tolerance=1e-5,results=results,artifacts=artifacts,
        dependencies_before=before,dependencies_after=after,dependencies_unchanged=before==after,
        original_code_sha256=original_hashes,measurement=engine.metadata(strict=True),
        memory=memory,threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads(),
        torch_version=torch.__version__,cuda_version=torch.version.cuda,device=props.name,
        matmul_tf32=torch.backends.cuda.matmul.allow_tf32,cudnn_tf32=torch.backends.cudnn.allow_tf32,
        prior_flat_quality_failure_unchanged=True)


def main():
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args()
    # Read-only shared helper; its __main__ campaign is never invoked.
    import hashlib
    if hashlib.sha256((HERE/"controls.py").read_bytes()).hexdigest()!=EXPECTED[HERE/"controls.py"]:
        raise ValueError("frozen control helper changed")
    control=load(HERE/"controls.py","solver_frozen_control_helpers")
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    try:
        with torch.inference_mode(),torch.autocast(device_type="cuda",enabled=False):receipt=run(out,control)
    except BaseException as error:
        control.write(out/"receipt.json",dict(status="INCOMPLETE_DIRECT_CFA_SOLVER_CONTROLS",
            all_cases_completed=False,mechanical_pass=False,quality_claim=False,photographic_admission=False,
            error=repr(error),traceback=traceback.format_exc()))
        raise
    control.write(out/"receipt.json",receipt)


if __name__=="__main__":main()
