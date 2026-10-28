"""Root-scheduled mechanical commissioning; no RAW reads or photo admission."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import sys
import traceback
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "direct-cfa-forward-gpu"
CPU = HERE.parent / "joint-cfa-local-fit/constant-deflation/sensor-operator.py"
CPU_SHA = "8fad7b79049b2fcb0e649eea62e6b1657a387b32b2c1c9c1a47796c55f3ccf90"
BASE = HERE.parent / "joint-cfa-local-fit/band-residual/sensor-operator.py"
BASE_SHA = "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac"
HELPER_SHA = "638c7391082b68774fc2581af014830f20dc6d1fee9e43a03b913046e1564938"
MEASUREMENT_SHA = "8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84"
LIMIT = 8 << 30
EPS = float(np.finfo(np.float32).eps)
RTOL = 3e-5
NORMAL_RTOL = 3e-4
HW = (19, 23)
NOISE = dict(shot4=(.15, .13, .17, .21), read4=(9., 8., 11., 13.),
             black4=(512., 513., 514., 515.), saturation=15360)


def ref(path):
    p = Path(path).resolve(); data = p.read_bytes()
    return dict(path=str(p), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    return module


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write("\n")


def cpu_tensor(value):
    if torch.is_tensor(value):
        return value.detach().cpu().contiguous()
    return torch.from_numpy(np.ascontiguousarray(value)).to(torch.float32)


def norm(value):
    v = cpu_tensor(value)
    if v.dtype != torch.float32 or not bool(torch.isfinite(v).all()):
        raise ValueError("finite f32 comparison required")
    maximum = float(v.abs().max())
    return 0. if maximum == 0 else maximum * float(torch.sqrt(((v / maximum)**2).sum()))


def compare(actual, expected, rtol=RTOL):
    a, b = cpu_tensor(actual), cpu_tensor(expected)
    if a.shape != b.shape:
        raise ValueError("comparison shape mismatch")
    error, reference = norm(a-b), norm(b)
    return dict(error_l2=error, reference_l2=reference, max_abs=float((a-b).abs().max()),
                relative_error=None if reference == 0 else error/reference,
                tolerance=rtol, pass_=error == 0 if reference == 0 else error <= rtol*reference)


def normal_compare(actual, expected, raw_reference, require_signal=True):
    error, signal, raw = norm(cpu_tensor(actual)-cpu_tensor(expected)), norm(expected), norm(raw_reference)
    budget = NORMAL_RTOL*signal + 32*EPS*raw
    resolvable = signal > 0 and budget <= .02*signal
    return dict(error_l2=error, reference_l2=signal, raw_reference_l2=raw,
                allowed_error=budget, signal_resolvable=resolvable,
                pass_=error <= budget and (resolvable or not require_signal))


def null_check(actual, expected, raw_reference):
    scale = norm(raw_reference); budget = 64*EPS*scale
    return dict(actual_l2=norm(actual), cpu_l2=norm(expected), raw_l2=scale,
                allowed_error=budget, pass_=scale > 0 and norm(actual) <= budget
                and norm(expected) <= budget and norm(cpu_tensor(actual)-cpu_tensor(expected)) <= budget)


def ok(records):
    return all(v["pass_"] for v in records)


def hashes(arrays):
    return [hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest() for a in arrays]


def make_inputs(helper, hw=HW):
    specs = [((0, 0), 1., 0., (0., 0.)), ((3, 5), 1., 0., (.37, -.29)),
             ((5, 2), 1.025, .051, (-.23, .31))]
    rows = []
    for sid, (origin, scale, angle, shift) in enumerate(specs):
        xy, affine = helper.geometry(hw, origin, scale, angle, shift)
        nodes, weights = helper.nodes_from_affine(xy, affine)
        phase = ((xy[..., 1] & 1)*2 + (xy[..., 0] & 1)).astype(np.int64)
        channel = np.asarray([0, 1, 1, 2])[phase]
        p = xy.astype(np.float64) @ affine[:, :2].T + affine[:, 2]
        fields = np.stack((2200+650*np.sin(.35*p[..., 0]+.17*p[..., 1]+sid*.11),
                           1300+220*np.cos(.19*p[..., 0]-.13*p[..., 1]-sid*.07),
                           3100+950*np.sin(.27*p[..., 0]-.23*p[..., 1]+sid*.13)), axis=-1)
        observed = np.take_along_axis(fields, channel[..., None], -1)[..., 0]
        codes = np.floor(observed+np.asarray(NOISE["black4"])[phase]+.5).astype(np.uint16)
        codes[0, 0] = 485  # Actual below-black datum; same injected variance rule.
        rows.append(dict(sid=sid, origin=origin, xy=xy, affine=affine, nodes=nodes,
                         weights=weights, codes=codes, valid=None))
    return rows


def build_cpu(cpu, rows, override=None):
    hw = rows[0]["codes"].shape
    cfg = cpu.Config(observed_hw=hw, **NOISE)
    sources = [cpu.Source(r["sid"], cpu.Query(r["xy"], r["nodes"], r["weights"]), r["codes"]) for r in rows]
    return cpu.prepare(sources, cfg, metric_override=override)


def build_gpu(model, measurement, rows, override=None, window=True):
    sources = [model.Source(r["sid"], (*r["origin"], r["codes"].shape[1], r["codes"].shape[0]),
                           r["affine"], lambda a=r["codes"]: a, frozen_valid=r["valid"]) for r in rows]
    return model.StreamedProblem(torch, measurement.field_hw, sources, model.Noise(**NOISE),
              metric_override=override, measurement=measurement, device_limit_bytes=LIMIT,
              diagnostic_admission_window=window)


def field(hw):
    y, x = np.mgrid[:hw[0], :hw[1]]
    a = np.stack((np.sin(.31*x+.19*y), .7*np.cos(.13*x-.23*y),
                  .9*np.sin(.17*x-.29*y+.4)), -1).astype(np.float32)
    a -= a.mean(axis=(0, 1), dtype=np.float32)
    return torch.from_numpy(a)


def mask_reference(cpu, plan, valid):
    # Exact support oracle: actual frozen H applied separately to EACH invalid
    # original impulse. No cancellation between invalid sites can hide support.
    direct = np.ones(plan.count, dtype=bool)
    for y, x in np.argwhere(~valid):
        impulse = torch.zeros(valid.shape, dtype=torch.float32); impulse[y, x] = 1
        direct &= plan.forward(impulse).numpy() == 0
    expanded = direct.copy()
    for b in plan.bands:
        if b["kind"] == "LL":
            continue
        a, z = b["start"], b["end"]; h, w = b["shape"]
        block = direct[a:z].reshape(h, w)
        # Literal coefficient neighborhood, independently indexed; replicate edge.
        result = np.empty_like(block)
        for y in range(h):
            for x in range(w):
                result[y, x] = all(block[min(max(y+dy, 0), h-1), min(max(x+dx, 0), w-1)]
                                   for dy in (-1, 0, 1) for dx in (-1, 0, 1))
        expanded[a:z] = result.reshape(-1)
    return direct, expanded


def run(out):
    dependency_paths = [Path(__file__), HERE/"independent-plan.md", HERE/"bands-gpu.py",
        HERE/"normal-operator.py", HERE/"solver.py", HERE/"measurement-paired.py",
        PARENT/"controls.py", PARENT/"measurement-gpu.py", CPU, BASE]
    before = [ref(p) for p in dependency_paths]
    for p, expected in ((CPU, CPU_SHA), (BASE, BASE_SHA), (PARENT/"controls.py", HELPER_SHA),
                        (PARENT/"measurement-gpu.py", MEASUREMENT_SHA)):
        if ref(p)["sha256"] != expected:
            raise ValueError("frozen reference changed: " + str(p))
    torch.set_num_threads(4); torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required")
    torch.cuda.set_device(0)
    props = torch.cuda.get_device_properties(0)
    torch.cuda.set_per_process_memory_fraction(min(1., LIMIT/props.total_memory), 0)
    torch.cuda.reset_peak_memory_stats()
    helper = load(PARENT/"controls.py", "streamed_independent_coordinates")
    cpu = load(CPU, "streamed_frozen_deflation")
    model = load(HERE/"normal-operator.py", "commission_streamed_normal")
    pair = load(HERE/"measurement-paired.py", "commission_paired_measurement")
    frozen = load(PARENT/"measurement-gpu.py", "commission_original_measurement")
    rows = make_inputs(helper); input_hashes = hashes([r["codes"] for r in rows])
    fhw = tuple(v+16 for v in HW)
    engine = pair.PairedMeasurementGpu(torch, fhw, device_limit_bytes=LIMIT)
    separate = frozen.MeasurementGpu(torch, fhw, device_limit_bytes=LIMIT)
    results = {}; artifacts = {}
    for r in rows:
        artifacts[f"source-{r['sid']}-original-u16"] = helper.save_array(out, f"source-{r['sid']}-original-u16", r["codes"])
    # Constant paired path FIRST, against a separately instantiated frozen CUDA
    # producer, not just forward() recompiled with the appended paired kernel.
    paired_checks = []
    for r in rows:
        rect = (*r["origin"], HW[1], HW[0])
        for label, x in (("constant", torch.ones((*fhw, 3), dtype=torch.float32)*.25),
                         ("signed", field(fhw))):
            xg = x.cuda(); a, dc = engine.forward_pair(xg, rect, r["affine"])
            original = separate.forward(xg, rect, r["affine"])
            dc_original = separate.forward(torch.ones_like(xg), rect, r["affine"])
            checks = [helper.errors(a, original), helper.errors(dc, dc_original)]
            paired_checks.append(dict(source_id=r["sid"], field=label, comparisons=checks,
                                      pass_=all(c["pass"] for c in checks)))
    results["paired_against_frozen"] = paired_checks
    candidate = build_gpu(model, engine, rows)
    reference = build_cpu(cpu, rows)
    stages = []
    for i, r in enumerate(rows):
        current = candidate.current_source(r["sid"])
        cp = reference.original.source_operators[i][1]
        entries = []
        fields = (("observed", current.observed, reference.original.observations[i]),
                  ("d", current.d, reference.original._band_observations[i]),
                  ("variance", current.variance, reference.original.variances[i]),
                  ("admission", current.admission, reference.original.admissions[i]),
                  ("metric", current.metric, reference.original.metrics[i]),
                  ("factor", current.factors(candidate.metric_scale, candidate.count), reference.original.factors[i]))
        for name, actual, expected in fields:
            if name == "observed":
                entries.append(dict(name=name, **compare(actual, expected)))
            else:
                for band in cp.bands:
                    a, b = band["start"], band["end"]
                    entries.append(dict(name=name, band=band, **compare(actual[a:b], expected[a:b])))
            artifacts[f"source-{i}-{name}"] = helper.save_array(out, f"source-{i}-{name}", actual)
        coeff = torch.sin(torch.arange(cp.count, dtype=torch.float32)*.071)
        inv = current.plan.inverse(coeff.cuda())
        entries.append(dict(name="inverse-independent-coefficients", **compare(inv, cp.inverse(coeff))))
        entries.append(dict(name="roundtrip", **compare(current.plan.inverse(current.d), current.observed)))
        stages.append(dict(source_id=i, arrays=entries, layout_exact=current.plan.bands == cp.bands
            and current.plan.sizes == cp.sizes, all_valid=bool(current.valid_coeff.all()), pass_=ok(entries)
            and current.plan.bands == cp.bands and current.plan.sizes == cp.sizes and bool(current.valid_coeff.all())))
    results["bands_noise_factor"] = stages
    results["scale_count"] = dict(scale=compare(candidate.metric_scale, reference.metric_scale),
        count=candidate.count, expected_count=3*HW[0]*HW[1], pass_=candidate.count == 3*HW[0]*HW[1]
        and compare(candidate.metric_scale, reference.metric_scale)["pass_"])
    z = field(fhw); zg = z.cuda()
    raw = reference.original.adjoint(reference.original.forward(z))
    expected = reference.adjoint(reference.forward(z)); actual = candidate.normal(zg)
    rhs_expected = reference.adjoint(reference.rhs)
    rhs_raw = reference.original.adjoint(reference.original.rhs)
    normal_records = dict(normal=normal_compare(actual, expected, raw),
                          rhs=normal_compare(candidate.rhs(), rhs_expected, rhs_raw),
                          raw_normal=compare(candidate.normal(zg, projected=False), raw))
    # Weighted source stages commission the actual factors on both sides of H.
    bw = reference.original.forward(z)
    for i in range(3):
        normal_records[f"B-{i}"] = compare(candidate.weighted_forward(zg, i), bw[i])
        one = [torch.zeros_like(v) for v in bw]; one[i] = torch.cos(torch.arange(bw[i].numel())*.053)
        normal_records[f"Bt-{i}"] = compare(candidate.weighted_adjoint(one[i].cuda(), i), reference.original.adjoint(one))
    restored = candidate.restore(zg); expected_restored = reference.projection.restore(z)
    normal_records["restore"] = compare(restored, expected_restored)
    evaluated = candidate.evaluate(zg)
    residual = reference.original.residual(expected_restored)
    full_expected = reference.original.adjoint(residual)
    projected_expected = reference.original.adjoint(reference.projection.project(residual))
    normal_records["final_full_normal"] = normal_compare(evaluated["full_normal"], full_expected, rhs_raw)
    normal_records["final_projected_normal"] = normal_compare(evaluated["projected_normal"], projected_expected, rhs_raw)
    expected_objective = cpu.norm_pair(residual).receipt()["value_f32"]
    objective = evaluated["objective"].receipt()["value_f32"]
    normal_records["objective"] = compare(np.array(objective, np.float32), np.array(expected_objective, np.float32))
    results["actual_cpu_projected_problem"] = dict(checks=normal_records, pass_=ok(normal_records.values()))
    for name, value in (("normal-gpu", actual), ("normal-cpu", expected), ("rhs-gpu", candidate.rhs()),
                        ("rhs-cpu", rhs_expected), ("restored-gpu", restored), ("restored-cpu", expected_restored)):
        artifacts[name] = helper.save_array(out, name, value)
    # Total-q=1 is a mechanical conditioning control, never the candidate metric.
    unit = build_gpu(model, engine, rows, override=1.)
    unit_cpu = build_cpu(cpu, rows, override=1.)
    constant_checks = []
    for c in range(3):
        x = torch.zeros_like(z); x[..., c] = 1
        raw_c = unit_cpu.original.adjoint(unit_cpu.original.forward(x))
        expected_c = unit_cpu.adjoint(unit_cpu.forward(x))
        constant_checks.append(dict(color=c, **null_check(unit.normal(x.cuda()), expected_c, raw_c)))
    near = z + torch.tensor([64., -32., 16.]).reshape(1, 1, 3)
    near_raw = unit_cpu.original.adjoint(unit_cpu.original.forward(near))
    near_expected = unit_cpu.adjoint(unit_cpu.forward(near))
    near_actual = unit.normal(near.cuda())
    near_check = normal_compare(near_actual, near_expected, near_raw)
    invariance = normal_compare(near_actual, unit.normal(zg), near_raw)
    wrong_projection = normal_compare(unit.normal(near.cuda(), projected=False), near_expected, near_raw)
    # Two independent fields test the produced projected normal's symmetry/PSD.
    other = torch.flip(z, (0,)).contiguous().cuda(); nx = unit.normal(zg); ny = unit.normal(other)
    dot = lambda a,b: float((cpu_tensor(a)*cpu_tensor(b)).sum())
    lhs, rh = dot(zg, ny), dot(other, nx)
    denominator = norm(zg)*norm(ny)+norm(other)*norm(nx)
    symmetry = abs(lhs-rh)/denominator if denominator else None
    curvature = dot(zg, nx); negative_budget = 64*EPS*norm(z)*norm(unit_cpu.original.adjoint(unit_cpu.original.forward(z)))
    results["constants_near_signed_symmetry"] = dict(constants=constant_checks, near=near_check,
        offset_invariance=invariance, removed_projection_foil=wrong_projection,
        symmetry_error=symmetry, curvature=curvature, negative_roundoff_budget=negative_budget,
        pass_=ok(constant_checks) and near_check["pass_"] and invariance["pass_"]
        and wrong_projection["error_l2"]>wrong_projection["allowed_error"] and symmetry is not None and symmetry <=3e-5 and curvature >= -negative_budget)
    # Physical phase foil: same mapped nodes, wrong original parity.
    wrong_rows=[]
    for r in rows:
        bad=dict(r); bad["origin"]=(r["origin"][0]+1,r["origin"][1]); bad["affine"]=r["affine"].copy()
        bad["affine"][:,2]-=bad["affine"][:,0]; wrong_rows.append(bad)
    wrong=build_gpu(model,engine,wrong_rows)
    phase_foil=normal_compare(wrong.rhs(),rhs_expected,rhs_raw)
    results["wrong_physical_phase"] = dict(comparison=phase_foil,pass_=phase_foil["error_l2"]>phase_foil["allowed_error"])
    # Frozen clipping mask: ordinary signal poison never changes admitted rows.
    clipped=[dict(r) for r in rows]
    mask=np.ones(HW,dtype=bool)
    for y,x in ((0,0),(6,8),(6,9),(7,8),(7,9),(HW[0]-1,HW[1]-1)): mask[y,x]=False
    a0=rows[0]["codes"].copy(); a1=a0.copy(); a0[~mask]=0; a1[~mask]=65535
    clipped[0]=dict(clipped[0],codes=a0,valid=mask)
    poisoned=[dict(r) for r in clipped]; poisoned[0]=dict(poisoned[0],codes=a1)
    clean=build_gpu(model,engine,clipped); poison=build_gpu(model,engine,poisoned)
    current=clean.current_source(0); altered=poison.current_source(0)
    direct, expanded=mask_reference(cpu,reference.original.source_operators[0][1],mask)
    support_exact=np.array_equal(current.support_coeff.cpu().numpy(),direct)
    support_exact &= np.array_equal(current.valid_coeff.cpu().numpy(),expanded)
    actual_codes=rows[0]["codes"].copy()
    actual_codes[~mask]=np.resize(np.asarray([15360,16383],np.uint16),int((~mask).sum()))
    actual_codes[1,2]=15359
    actual_clip=model.prepare_source(torch,actual_codes,rows[0]["origin"],model.Noise(**NOISE))
    actual_threshold_exact=np.array_equal(actual_clip.valid_original.cpu().numpy(),mask)
    actual_threshold_exact &= np.array_equal(actual_clip.valid_coeff.cpu().numpy(),expanded)
    nontrivial_spread=int((direct & ~expanded).sum())
    poison_stages={name:compare(getattr(altered,name)[current.valid_coeff],getattr(current,name)[current.valid_coeff])
                   for name in ("d","variance","admission","metric")}
    poison_stages["global_scale"]=compare(poison.metric_scale,clean.metric_scale)
    poison_stages["normal"]=normal_compare(poison.normal(zg),clean.normal(zg),clean.normal(zg,projected=False))
    poison_stages["rhs"]=normal_compare(poison.rhs(),clean.rhs(),clean.rhs(projected=False))
    bad0=build_gpu(model,engine,clipped,window=False); bad1=build_gpu(model,engine,poisoned,window=False)
    wrong_mask=normal_compare(bad1.rhs(),bad0.rhs(),bad0.rhs(projected=False))
    results["clipping"] = dict(support_exact=bool(support_exact),actual_white_threshold_exact=bool(actual_threshold_exact),additional_3x3_omissions=nontrivial_spread,
        checks=poison_stages,unexpanded_mask_poison_foil=wrong_mask,
        pass_=bool(support_exact) and bool(actual_threshold_exact) and nontrivial_spread>0 and ok(poison_stages.values()) and wrong_mask["error_l2"]>wrong_mask["allowed_error"])
    artifacts["clip-mask"]=helper.save_array(out,"clip-mask",mask)
    artifacts["coefficient-mask"]=helper.save_array(out,"coefficient-mask",current.valid_coeff)
    # Omit every actual R observation: constant support must be refused.
    no_red=[]
    for r in rows:
        phase=((r["xy"][...,1]&1)*2+(r["xy"][...,0]&1)); valid=phase!=0
        no_red.append(dict(r,valid=valid))
    refused=False; reason=None
    try: build_gpu(model,engine,no_red)
    except ValueError as error: refused=True; reason=str(error)
    results["absent_red_constant_support"] = dict(pass_=refused,reason=reason)
    unchanged=hashes([r["codes"] for r in rows])==input_hashes
    after=[ref(p) for p in dependency_paths]
    mechanical=(ok(paired_checks) and ok(stages) and results["scale_count"]["pass_"]
                and all(v["pass_"] for k,v in results.items() if isinstance(v,dict)) and unchanged and before==after)
    torch.cuda.synchronize()
    memory=dict(allocated=torch.cuda.max_memory_allocated(),reserved=torch.cuda.max_memory_reserved(),limit=LIMIT)
    if max(memory["allocated"],memory["reserved"])>LIMIT: raise ValueError("8GiB Torch cap")
    return dict(status="COMPLETE_DIRECT_CFA_STREAMED_CONTROLS",all_cases_completed=True,
        mechanical_pass=bool(mechanical),quality_claim=False,photographic_admission=False,RAW_reads=0,
        reconstruction_quality_scored=False,solver_executed=False,results=results,artifacts=artifacts,
        dependencies_before=before,dependencies_after=after,dependencies_unchanged=before==after,
        original_codes_unchanged=unchanged,original_code_sha256=input_hashes,
        source_geometry=[dict(source_id=r["sid"],origin_xy=r["origin"],affine=r["affine"].tolist()) for r in rows],
        injected_noise=NOISE,
        numerical_bars=dict(stage_relative_l2=RTOL,normal_relative=NORMAL_RTOL,
            normal_roundoff_multiple=32,constant_roundoff_multiple=64,normal_budget_max_signal_fraction=.02,
            symmetry_relative=3e-5,no_absolute_unit_floor=True),memory=memory,
        measurement=engine.metadata(strict=True),frozen_measurement=separate.metadata(strict=True),
        candidate=candidate.metadata(),threads=torch.get_num_threads(),torch_version=torch.__version__,
        cuda_version=torch.version.cuda,device=props.name)


def main():
    p=argparse.ArgumentParser(); p.add_argument("--out",type=Path,required=True); a=p.parse_args()
    out=a.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    try:
        with torch.inference_mode(),torch.autocast(device_type="cuda",enabled=False): receipt=run(out)
    except BaseException as error:
        write(out/"receipt.json",dict(status="INCOMPLETE_DIRECT_CFA_STREAMED_CONTROLS",all_cases_completed=False,
            mechanical_pass=False,quality_claim=False,photographic_admission=False,error=repr(error),traceback=traceback.format_exc()))
        raise
    write(out/"receipt.json",receipt)


if __name__=="__main__": main()
