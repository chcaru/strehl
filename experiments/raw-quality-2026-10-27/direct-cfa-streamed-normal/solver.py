"""Fixed64-step normal CG; no restart, preconditioner or hidden image prior."""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location("streamed_normal_solver_operator",HERE/"normal-operator.py")
operator=importlib.util.module_from_spec(_spec)
sys.modules[_spec.name]=operator
exec(compile((HERE/"normal-operator.py").read_bytes(),str(HERE/"normal-operator.py"),"exec"),operator.__dict__)


@dataclass
class FitResult:
    x: object
    correction_z: object
    status: str
    converged: bool
    iterations: int
    history: list
    evidence: dict

    def save(self,out_dir):
        out=Path(out_dir)
        out.mkdir(parents=True,exist_ok=False)
        records={}
        # Small controls may save these complete latent fields. Full native
        # direct-RGB cell integration/development is a separate unreleased step.
        for name,value in (("latent",self.x),("correction-z",self.correction_z)):
            array=value.detach().cpu().contiguous().numpy()
            path=out/(name+".f32le")
            array.astype("<f4",copy=False).tofile(path)
            records[name]={"path":str(path.resolve()),"shape":list(array.shape),"dtype":"<f4",
                           "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
        receipt=dict(status=self.status,converged=self.converged,iterations=self.iterations,
                     history=self.history,evidence=self.evidence,**records,
                     admission=False,quality_claim=False,reference_cell_delivery_performed=False)
        (out/"result.json").write_text(json.dumps(receipt,indent=2,allow_nan=False)+"\n",encoding="utf-8")
        return receipt


def relative(norm,initial):
    if initial.is_zero:
        return 0.0 if norm.is_zero else None
    value=norm.root_ratio(initial)
    return float(value) if bool(norm.torch.isfinite(value)) else None


def fit(problem):
    t=problem.torch
    finite,require=operator.finite,operator.require
    z=t.zeros((*problem.field_hw,3),dtype=t.float32,device="cuda:0")
    rhs=problem.rhs()
    residual=rhs.clone()
    direction=residual.clone()
    initial=operator.norm_pair(t,residual)
    gamma=initial
    history=[dict(iteration=0,recursive_relative_normal=0.0 if initial.is_zero else 1.0,
                  coordinate_system="correction z",true_objective_checked=False)]
    iterations=0
    status="zero-initial-projected-normal" if initial.is_zero else "iteration-cap"
    normal_calls=0
    reached=initial.is_zero
    for iteration in range(1,65):
        if reached:
            break
        try:
            product=finite(t,problem.normal(direction),"normal CG direction image")
            normal_calls+=1
            curvature=operator.stable_dot(t,direction,product)
            if not bool(t.isfinite(curvature)) or float(curvature)<=0:
                status="nonpositive-or-nonfinite-normal-curvature"
                break
            m,e=t.frexp(curvature)
            denominator=operator.SquaredNorm(t,m,int(e))
            alpha=gamma.ratio(denominator)
            if not bool(t.isfinite(alpha)) or float(alpha)<=0:
                status="nonfinite-or-underflowed-step"
                break
            candidate=finite(t,z+alpha*direction,"candidate correction")
            next_residual=finite(t,residual-alpha*product,"recursive normal residual")
            next_gamma=operator.norm_pair(t,next_residual)
            ratio=next_gamma.root_ratio(initial)
            finite(t,ratio,"recursive relative normal residual")
            # Retain only complete finite iterates. This history is recursive;
            # no extra measurement pass is hidden as an intermediate true check.
            z=candidate
            residual=next_residual
            iterations=iteration
            entry=dict(iteration=iteration,alpha_f32=float(alpha),curvature_f32=float(curvature),
                       recursive_relative_normal=float(ratio),recursive_normal=next_gamma.receipt(),
                       coordinate_system="correction z",true_objective_checked=False)
            history.append(entry)
            if float(ratio)<=1e-5:
                reached=True
                status="recursive-normal-threshold"
                break
            beta=next_gamma.ratio(gamma)
            if not bool(t.isfinite(beta)) or float(beta)<=0:
                status="nonfinite-or-underflowed-conjugate-step"
                break
            direction=finite(t,residual+beta*direction,"normal CG direction")
            entry["beta_f32"]=float(beta)
            gamma=next_gamma
        except (ValueError,RuntimeError) as error:
            status="numeric-refusal: "+str(error)
            break
    # Release recurrence scratch before the whole-domain final audits.
    del rhs,residual,direction
    product=candidate=next_residual=None
    initial_check=problem.evaluate(t.zeros_like(z))
    initial_objective=initial_check["objective"]
    initial_true_normal=operator.norm_pair(t,initial_check["projected_normal"])
    initial_constants=initial_check["restored_constants"].tolist()
    del initial_check
    final=problem.evaluate(z)
    true_full=operator.norm_pair(t,final["full_normal"])
    true_projected=operator.norm_pair(t,final["projected_normal"])
    full_ratio=relative(true_full,initial)
    projected_ratio=relative(true_projected,initial)
    nuisance_norm=operator.norm_pair(t,final["nuisance_U_residual"])
    objective_pass=final["objective"].le(initial_objective)
    final_pass=(full_ratio is not None and projected_ratio is not None
                and full_ratio<=1e-5 and projected_ratio<=1e-5 and objective_pass)
    # A finite64-step result can be retained even when either normal remains
    # above the unchanged bar. Recurrence convergence alone never admits it.
    converged=bool(final_pass and (reached or status=="iteration-cap"))
    final_status="restored-original-normal-converged" if converged else "refused-"+status
    evidence=problem.metadata()
    evidence.update(maximum_iterations=64,normal_tolerance=1e-5,initialization="zero correction",
        solver="normal CG",preconditioner=None,restarts=0,priors_added=False,
        recurrence_status=status,recursive_threshold_reached=reached,
        normal_operator_calls_in_recurrence=normal_calls,
        true_intermediate_objectives_evaluated=False,intermediate_objective_monotonicity_claim=False,
        actual_projected_initial_normal=initial.receipt(),
        independently_restored_initial_projected_normal=initial_true_normal.receipt(),
        restored_true_full_normal=true_full.receipt(),restored_true_projected_normal=true_projected.receipt(),
        restored_full_normal_relative=full_ratio,restored_projected_normal_relative=projected_ratio,
        restored_nuisance_U_residual_f32=final["nuisance_U_residual"].tolist(),
        restored_nuisance_T_residual_f32=final["nuisance_T_residual"].tolist(),
        restored_nuisance_norm=nuisance_norm.receipt(),
        restored_constants_f32=final["restored_constants"].tolist(),constant_initial_f32=initial_constants,
        restored_objective_scaled=final["objective"].receipt(),
        restored_objective_original=final["original_objective"].receipt(),
        constant_initial_objective_scaled=initial_objective.receipt(),
        restored_objective_no_greater_than_initial=objective_pass,restored_numerical_pass=final_pass,
        finite_last_iterate_retained=True,reference_cell_delivery_performed=False,
        implicit_completion="zero-start minimum correction norm, not necessarily minimum physical image norm",
        f32_CG_not_bit_equivalent_to_CGLS=True,old_flat_failure_retained=True,
        prior_photographic_admission=False,quality_claim=False)
    return FitResult(final["x"],z,final_status,converged,iterations,history,evidence)
