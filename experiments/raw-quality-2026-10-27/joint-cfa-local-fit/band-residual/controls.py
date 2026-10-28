"""Root-owned fixed original-CFA band-residual discriminator; no RAW reader.

prepare exports independent fixtures only. cost commissions actual primitives and
one neutral-flat candidate. full runs the frozen10candidate+4foil inventory.
No mode admits a photograph or replaces a missing actual product comparator.
"""
import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np
import torch

import fixtures as fx

HERE = Path(__file__).resolve().parent
MECHANICAL_REL = 2e-5
SCORE_SLICE = (slice(16, 112), slice(16, 112))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_ref(ref):
    current = fx.file_ref(ref["path"])
    for key in ("sha256", "bytes"):
        if key in ref and current[key] != ref[key]:
            raise ValueError(f"changed bound file: {ref['path']}")
    return Path(ref["path"])


def load_model(expected):
    path = HERE/"sensor-operator.py"
    if fx.file_ref(path)["sha256"] != expected:
        raise ValueError("operator source differs from root binding")
    spec = importlib.util.spec_from_file_location("independent_band_operator", path)
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    return model


def config_for(model, row):
    gain = np.asarray(row["noise"]["gain_dn_per_e4"], np.float32)
    read_e = np.asarray(row["noise"]["read_noise_e4"], np.float32)
    read_dn = (read_e*gain).astype(np.float32)
    read = (read_dn*read_dn).astype(np.float32)
    return model.Config(observed_hw=(row["height"], row["width"]),
        shot4=tuple(gain), read4=tuple(read), black4=(row["black"],)*4,
        saturation=row["white"], device="cpu")


def make_sources(model, row, arrays):
    if row["source_to_reference_center"] != [64., 64.]:
        raise ValueError("source gauge center differs")
    sources = []
    for source, codes in zip(row["sources"], arrays):
        ar, ai, tx, ty = source["source_to_reference"]
        matrix, shift = np.array([[ar, -ai], [ai, ar]]), np.array([tx, ty])
        nodes, weights = fx.nodes(matrix, shift)
        query = model.Query(fx.XY.copy(), nodes, weights)
        sources.append(model.Source(int(source["source_id"]), query, codes))
    return sources


def as_numpy(value):
    return value.detach().cpu().numpy() if torch.is_tensor(value) else np.asarray(value)


def error(a, b):
    d = as_numpy(a).astype(np.float64)-as_numpy(b).astype(np.float64)
    return dict(maximum=float(np.max(np.abs(d))), rms=float(np.sqrt(np.mean(d*d))))


def dot(a, b):
    return float(np.sum(as_numpy(a).astype(np.float64)*as_numpy(b).astype(np.float64)))


def norm(a):
    return float(np.sqrt(dot(a, a)))


def dot_guard(ax, y, x, aty):
    lhs, rhs = dot(ax, y), dot(x, aty)
    scale = max(1., norm(ax)*norm(y)+norm(x)*norm(aty))
    value = abs(lhs-rhs)/scale
    return dict(lhs=lhs, rhs=rhs, normalized_error=value,
                bound=MECHANICAL_REL, pass_guard=value <= MECHANICAL_REL)


def read_truth(row):
    return np.load(verify_ref(row["truth"]), allow_pickle=False)


def image_score(row, rgb):
    truth = read_truth(row)[SCORE_SLICE].astype(np.float64)
    value = as_numpy(rgb)
    if value.shape == (128, 128, 3):
        value = value[SCORE_SLICE]
    if value.shape != (96, 96, 3) or not np.isfinite(value).all():
        raise ValueError("scored image must be finite96²RGB or complete128²RGB")
    delta = value.astype(np.float64)-truth
    result = dict(rgb_rmse_dn=float(np.sqrt(np.mean(delta*delta))),
        green_rmse_dn=float(np.sqrt(np.mean(delta[..., 1]**2))),
        chroma_rmse_dn=float(np.sqrt(np.mean(np.stack((delta[..., 0]-delta[..., 1],
                    delta[..., 2]-delta[..., 1]), -1)**2))),
        mean_error_dn=delta.mean((0, 1)).tolist(), components=[])
    rows = row["component_specification"]
    if rows:
        basis = [np.ones(96*96, np.float64)]
        for spec in rows:
            name, amplitude = spec["name"], spec["amplitude_dn"]
            template = np.load(verify_ref(row["templates"][name]), allow_pickle=False)[SCORE_SLICE]
            dominant = int(np.argmax(np.abs(amplitude)))
            basis.append((template[..., dominant]/amplitude[dominant]).reshape(-1))
        # Fixed known templates, fitted jointly to avoid cross-projection leakage.
        # This is a scoring decomposition, never a guide, latent fit or noise model.
        matrix = np.column_stack(basis)
        coefficients, _, rank, singular = np.linalg.lstsq(matrix, delta.reshape(-1, 3), rcond=1e-12)
        result["template_rank"] = int(rank)
        result["template_columns"] = matrix.shape[1]
        result["template_condition"] = float(singular[0]/singular[-1])
        for j, spec in enumerate(rows):
            name, amplitude = spec["name"], spec["amplitude_dn"]
            dominant = int(np.argmax(np.abs(amplitude)))
            result["components"].append(dict(name=name, dominant_channel=dominant,
                recovery=1+float(coefficients[j+1, dominant]/amplitude[dominant]),
                amplitude_error_dn=coefficients[j+1].tolist(),
                truth_radiance_amplitude_dn=list(amplitude)))
    return result


def quality_guard(case, current, baseline):
    if baseline is None:
        return dict(available=False, pass_guard=False, reason="actual product baseline unavailable")
    allowance = .5 if case in ("flat-neutral", "flat-colour") else 1.
    errors = {}
    for key in ("rgb_rmse_dn", "green_rmse_dn", "chroma_rmse_dn"):
        bound = 1.10*baseline[key]+allowance
        errors[key] = dict(value=current[key], bound=bound, pass_guard=current[key] <= bound)
    comp = []
    prior = {r["name"]: r for r in baseline["components"]}
    for row in current["components"]:
        old = prior[row["name"]]
        eligible = old["recovery"] >= .5
        lower = .95*min(old["recovery"], 1.)
        retention = not eligible or lower <= row["recovery"] <= 1.10
        weak = (row["name"] != "weak-green" or
                abs(row["amplitude_error_dn"][1]) <= abs(old["amplitude_error_dn"][1])+1.)
        comp.append(dict(name=row["name"], eligible=eligible, lower=lower, upper=1.10,
            recovery=row["recovery"], retention_pass=retention, weak_green_pass=weak))
    return dict(available=True, errors=errors, components=comp,
                pass_guard=all(v["pass_guard"] for v in errors.values())
                    and all(r["retention_pass"] and r["weak_green_pass"] for r in comp))


def read_baselines(path, manifest, out):
    if path is None:
        return {}, dict(available=False, qualification=False)
    receipt = load_json(path)
    if (receipt.get("status") != "COMPLETE_ACTUAL_PRODUCT_BASELINES"
            or receipt.get("mechanical_pass") is not True
            or receipt.get("original_inputs_unchanged") is not True):
        raise ValueError("actual baseline completion refused")
    binding = receipt["fixture_manifest"]
    verify_ref(binding)
    if binding["sha256"] != manifest["baseline_manifest"]["sha256"]:
        raise ValueError("baseline used a different original fixture manifest")
    original_rows = {r["id"]: r for r in manifest["cases"]}
    found, evidence = {}, []
    directory = out/"actual-baselines"
    directory.mkdir()
    for entry in receipt["cases"]:
        ref = entry.get("receipt", entry)
        data = load_json(verify_ref(ref))
        case = data["case_id"]
        if case not in original_rows:
            raise ValueError("unexpected actual baseline case")
        source = original_rows[case]
        if (data.get("status") != "COMPLETE_ACTUAL_PRODUCT_BASELINE"
                or data.get("mechanical_pass") is not True
                or data.get("original_inputs_unchanged") is not True
                or data.get("signal_gather_exact") is not True
                or data.get("output_native_geometry") != [96, 96]
                or data.get("output_native_origin") != [16, 16]
                or data.get("quad_crop") != [8, 8, 48, 48]
                or data.get("source_count") != len(source["sources"])):
            raise ValueError("baseline geometry/consumer identity differs")
        gain = np.asarray(source["noise"]["gain_dn_per_e4"], np.float32)
        read_e = np.asarray(source["noise"]["read_noise_e4"], np.float32)
        read_dn = (gain*read_e).astype(np.float32)
        read_variance = (read_dn*read_dn).astype(np.float32)
        for key, expected in (("noise_gain_bits_physical", gain),
                ("noise_read_e_bits_physical", read_e),
                ("noise_read_variance_bits_physical", read_variance)):
            if data.get(key) != expected.view(np.uint32).tolist():
                raise ValueError("baseline consumed a different injected noise model")
        if len(data["sources"]) != len(source["sources"]):
            raise ValueError("baseline source receipt inventory is incomplete")
        for ordinal, (actual, expected) in enumerate(zip(data["sources"], source["sources"])):
            if (actual["ordinal"] != ordinal or actual["source_id"] != expected["source_id"]
                    or actual["original"]["sha256"] != expected["sha256"]
                    or actual["original"]["bytes"] != expected["bytes"]):
                raise ValueError("baseline original source order/identity differs")
            verify_ref(actual["original"])
        bound = data["outputs"]["camera_rgb_dn"]
        rgb = np.fromfile(verify_ref(bound), dtype="<f4").reshape(96, 96, 3)
        if not np.isfinite(rgb).all():
            raise ValueError("nonfinite actual baseline")
        found[case] = rgb
        evidence.append(dict(case_id=case, receipt=ref, complete_master=bound,
            complete_display=fx.preview(directory/(case+".png"), rgb),
            actual_ac_bands=data["actual_ac_bands"], effective_exponents=data["effective_exponents"],
            boundary_caveat="actual96²MHC crop reflects at its edges; candidate scored96²lies inside128²",
            consumer=data["consumer"], writer_scope=data["writer_scope"]))
    if set(found) != set(original_rows):
        raise ValueError("incomplete actual baseline inventory")
    return found, dict(available=True, receipt=fx.file_ref(path), cases=evidence,
                       scope="actual small product consumer; not isolated basis or full TIFF writer parity")


def destroying_controls(manifest, out):
    rows = {r["id"]: r for r in manifest["cases"]}
    results = []
    for name, case, kind in (("flat-added-noise", "flat-neutral", "noise"),
            ("far-erased", "fine-far", "erase-far"),
            ("weak-green-erased", "independent-colour", "erase-green"),
            ("false-green", "flat-green-colour", "false-green"),
            ("overcontrast", "independent-colour", "overcontrast")):
        row = rows[case]
        truth = read_truth(row)
        changed = truth.copy()
        if kind == "noise":
            changed += (50*(1-2*((fx.XX+fx.YY) % 2)))[..., None]
        elif kind.startswith("erase"):
            component = "far-coarse" if kind == "erase-far" else "weak-green"
            changed -= np.load(verify_ref(row["templates"][component]), allow_pickle=False)
        elif kind == "false-green":
            changed[..., 1] += 32*np.cos(.31*fx.XX+.17*fx.YY)
        else:
            changed = fx.dc(case)+1.4*(changed-fx.dc(case))
        base, score = image_score(row, truth), image_score(row, changed)
        guard = quality_guard(case, score, base)
        results.append(dict(name=name, reference="known truth only for guard commissioning",
            guard=guard, rejected=not guard["pass_guard"],
            master=fx.array_ref(out/(name+".npy"), changed.astype(np.float32)),
            display=fx.preview(out/(name+".png"), changed)))
    return dict(pass_guard=all(r["rejected"] for r in results), destroyers=results)


def mechanics(model, manifest, out):
    """Producing seams; independent analytic/coordinate checks before image fits."""
    row, arrays = fx.load_case(manifest, "independent-colour")
    config = config_for(model, row)
    sources = make_sources(model, row, arrays)
    selected = sources[3]
    ar, ai, tx, ty = row["sources"][3]["source_to_reference"]
    matrix, shift = np.array([[ar, -ai], [ai, ar]]), np.array([tx, ty])
    measurement = model.Measurement(selected.query, config)
    ly, lx = np.mgrid[-8:136, -8:136]
    lxy = np.stack((lx, ly), -1)
    x = torch.from_numpy((800*np.sin(.13*lx)[..., None]
                         + np.stack((400*np.cos(.17*ly), 600*np.sin(.19*ly),
                                     300*np.cos(.11*lx+.07*ly)), -1)).astype(np.float32))
    y = torch.from_numpy((200*np.sin(.23*fx.XX+.15*fx.YY)+30*(fx.PHASE+1)).astype(np.float32))
    ax, aty = measurement.forward(x), measurement.adjoint(y)
    a_dot = dot_guard(ax, y, x, aty)
    wrong_phase = dot_guard(ax, ax, x, measurement.adjoint(torch.roll(ax, 1, 1)))
    constant = torch.ones_like(x)*np.float32(4096)
    constant_error = error(measurement.forward(constant), np.full((128, 128), 4096.))
    delivery_constant = error(model.integrate_reference(constant, config),
                              np.full((128, 128, 3), 4096.))
    continuous = fx.field("independent-colour", lxy, integrate=False)
    prediction = measurement.forward(torch.from_numpy(continuous)).numpy()
    exact_rgb = fx.field("independent-colour", fx.XY, matrix=matrix, shift=shift)
    exact = np.take_along_axis(exact_rgb, fx.CHANNEL[fx.PHASE][..., None], -1)[..., 0]
    forward_rows = []
    for p in range(4):
        keep = fx.PHASE == p
        rms = float(np.sqrt(np.mean((prediction[keep].astype(np.float64)-exact[keep])**2)))
        sigma = float(np.sqrt(np.mean(config.shot4[p]*np.maximum(exact[keep], 0)+config.read4[p])))
        forward_rows.append(dict(phase=p, rms_dn=rms, rms_sigma_dn=sigma,
                                 bound_dn=1+.5*sigma, pass_guard=rms <= 1+.5*sigma))
    # Independent literal geometric construction, not a second call to fx.nodes.
    axis = [-np.sqrt(3/5)/2, 0., np.sqrt(3/5)/2]
    center = (fx.XY.astype(np.float64)-64)@matrix.T+64+shift
    expected_nodes = np.stack([center+u*matrix[:, 0]+v*matrix[:, 1]+8
                              for v in axis for u in axis], axis=2)
    good_nodes = float(np.max(np.abs(selected.query.nodes_xy-expected_nodes)))
    bad_nodes, weights = fx.nodes(matrix, shift, wrong_footprint=True)
    bad_node_error = float(np.max(np.abs(bad_nodes-expected_nodes)))
    bad_measurement = model.Measurement(model.Query(fx.XY, bad_nodes, weights), config)
    bad_prediction = bad_measurement.forward(torch.from_numpy(continuous)).numpy()
    wrong_footprint = dict(node_max_native=bad_node_error, node_bound_native=2e-5,
        rejected=bad_node_error > 2e-5, prediction_change_dn=error(bad_prediction, prediction),
        constant_error=error(bad_measurement.forward(constant), np.full((128, 128), 4096.)))
    del bad_measurement, measurement
    gc.collect()
    haar_rows = []
    for shape, origin in (((128, 128), (0, 0)), ((127, 125), (2, 3))):
        h, w = shape
        yy, xx = np.mgrid[:h, :w]
        signal = torch.from_numpy((30000*np.sin(.33*xx+.12*yy)+5000*np.cos(.17*yy)).astype(np.float32))
        test = torch.from_numpy((300*np.cos(.25*xx-.17*yy)+40).astype(np.float32))
        plan = model.HaarPlan(shape, origin)
        coefficients = plan.forward(signal)
        q = plan.forward(test)
        check = dot_guard(coefficients, q, signal, plan.inverse(q))
        inverse = error(plan.inverse(coefficients), signal)
        phase = ((yy+origin[1]) % 2)*2+(xx+origin[0]) % 2
        original_v = torch.from_numpy((10+phase).astype(np.float32))
        transformed_v = plan.variance(original_v)
        variance_error = max(float((transformed_v[b["start"]:b["end"]]-(10+b["phase"])).abs().max())
                             for b in plan.bands)
        bad = coefficients.clone()
        band = plan.bands[0]
        bad[band["start"]:band["end"]] *= -1
        bad_check = dot_guard(coefficients, coefficients, signal, plan.inverse(bad))
        energy_delta = abs(dot(coefficients, coefficients)-dot(signal, signal))/max(1., dot(signal, signal))
        haar_rows.append(dict(shape=shape, origin_xy=origin, sizes=plan.sizes,
            roundtrip=inverse, adjoint=check, parseval_relative=energy_delta,
            variance_constant_phase_max=variance_error,
            one_sided_adjoint_foil=bad_check, foil_rejected=not bad_check["pass_guard"],
            pass_guard=inverse["maximum"] <= .05 and inverse["rms"] <= .01
                and check["pass_guard"] and energy_delta <= MECHANICAL_REL
                and variance_error <= 2e-5 and not bad_check["pass_guard"]))
    # q=1 is the actual weighted objective seam; use one source to keep primitives bounded.
    problem = model.prepare([sources[0]], config, metric_override=1.)
    weighted = [a-b for a, b in zip(problem.forward(x), problem.rhs)]
    m, h = problem.source_operators[0]
    raw = m.forward(x)-problem.observations[0]
    raw_energy = dot(raw, raw)/problem.count
    weighted_energy = sum(dot(v, v) for v in weighted)
    raw_gradient = m.adjoint(raw)/np.float32(problem.count)
    weighted_gradient = problem.adjoint(weighted)
    parseval = dict(energy_relative=abs(weighted_energy-raw_energy)/max(1., raw_energy),
        gradient_relative=norm(weighted_gradient-raw_gradient)/max(1., norm(raw_gradient)))
    parseval["pass_guard"] = max(parseval.values()) <= MECHANICAL_REL
    reference_forward = problem.forward(x)[0].clone()
    reference_rhs = problem.rhs[0].clone()
    repeated = model.prepare([model.Source(0, sources[0].query, sources[0].codes),
        model.Source(1, sources[0].query, sources[0].codes)], config, metric_override=1.)
    repeat_residual = [a-b for a, b in zip(repeated.forward(x), repeated.rhs)]
    repeat_energy = sum(dot(v, v) for v in repeat_residual)
    repeat_gradient = repeated.adjoint(repeat_residual)
    duplicate = dict(literal_same_original_bytes=True, independent_exposures=False,
        objective_relative=abs(repeat_energy-weighted_energy)/max(1., weighted_energy),
        gradient_relative=norm(repeat_gradient-weighted_gradient)/max(1., norm(weighted_gradient)),
        image_comparison="not a second fit; no new information or uncertainty claim")
    duplicate["pass_guard"] = max(duplicate["objective_relative"], duplicate["gradient_relative"]) <= MECHANICAL_REL
    del repeated, problem
    gc.collect()
    metric_rows = []
    for scalar in (np.float32(1e30), np.float32(1e-30)):
        p = model.prepare([sources[0]], config, metric_override=scalar)
        delta = error(p.forward(x)[0], reference_forward)
        rhs_delta = error(p.rhs[0], reference_rhs)
        metric_rows.append(dict(metric=float(scalar), common_scale=float(p.metric_scale),
            forward=delta, rhs=rhs_delta, objective=p.objective(x),
            pass_guard=delta["maximum"] <= .05 and delta["rms"] <= .01
                       and rhs_delta["maximum"] <= .05 and rhs_delta["rms"] <= .01))
        del p
        gc.collect()
    zero_metric = False
    try:
        model.prepare([sources[0]], config, metric_override=0.)
    except ValueError:
        zero_metric = True
    high = model.norm_pair(torch.tensor([3e38, -3e38], dtype=torch.float32))
    tiny = model.norm_pair(torch.tensor([1e-30, -1e-30], dtype=torch.float32))
    norms = dict(high=high.receipt(), tiny=tiny.receipt(),
        high_self_ratio=float(high.ratio(high)), tiny_self_ratio=float(tiny.ratio(tiny)),
        zero=model.norm_pair(torch.zeros(3, dtype=torch.float32)).receipt())
    norms["pass_guard"] = (norms["high_self_ratio"] == 1. and norms["tiny_self_ratio"] == 1.
                           and not high.is_zero and not tiny.is_zero and zero_metric)
    zero_source = model.Source(0, sources[0].query, np.full((128, 128), fx.BLACK, np.uint16))
    zero_problem = model.prepare([zero_source], config)
    zero_fit = model.fit(zero_problem)
    zero_saved = zero_fit.save(out/"zero-rhs-fit")
    zero_check = dict(status=zero_fit.status, iterations=zero_fit.iterations,
        output_max=float(zero_fit.output.abs().max()),
        pass_guard=zero_fit.converged and zero_fit.iterations == 0 and float(zero_fit.output.abs().max()) == 0.,
        saved=zero_saved, complete_display=fx.preview(out/"zero-rhs-fit"/"complete-output.png", zero_fit.output),
        latent_display=fx.preview(out/"zero-rhs-fit"/"latent-coefficients.png", zero_fit.x))
    clipped = np.fromfile(verify_ref(manifest["clipped_refusal"]), dtype="<u2").reshape(128, 128)
    clipping_refused = False
    try:
        model.prepare([model.Source(0, sources[0].query, clipped)], config)
    except ValueError as exc:
        clipping_refused = "clipped" in str(exc)
    missing_phase_refused = False
    try:
        model.Query(fx.XY[::2, ::2].copy(), sources[0].query.nodes_xy[::2, ::2].copy(),
                    sources[0].query.footprint_weights.copy())
    except ValueError:
        missing_phase_refused = True
    unsupported_geometry = False
    try:
        model.Measurement(model.Query(fx.XY, sources[0].query.nodes_xy+20.,
            sources[0].query.footprint_weights), config)
    except ValueError as exc:
        unsupported_geometry = "support" in str(exc)
    unblurred_red = fx.field("alias-repeated", fx.XY)[..., 0][fx.PHASE == 0]
    alias_cancellation = bool(np.all(np.rint(unblurred_red+fx.BLACK).astype(np.uint16) == round(fx.dc("alias-repeated")[0]+fx.BLACK)))
    # Independent observation-identifiability witness; no solve or fitted truth.
    alias_record = dict(noiseless_sharp_red_codes_equal_constant=alias_cancellation,
        same_original_sampling_can_hide_two_nonzero_components=True,
        truth_components=["red-020", "red-030"], diverse_companion="alias-diverse")
    # Pixel-area integration is exact; pupil quadrature is the only approximation here.
    vis128, vis256 = fx.visibility(fx.XY, index=3, pupil_count=128), fx.visibility(fx.XY, index=3, pupil_count=256)
    visibility_precision = error(vis128, vis256)
    visibility_precision["kind"] = "descriptive128vs256pupil check; no fit-kernel truth; targetpinhole cell areas exact"
    guards = destroying_controls(manifest, out)
    mechanical = (a_dot["pass_guard"] and not wrong_phase["pass_guard"]
        and constant_error["maximum"] <= .05 and constant_error["rms"] <= .01
        and delivery_constant["maximum"] <= .05 and delivery_constant["rms"] <= .01
        and good_nodes <= 2e-5 and wrong_footprint["rejected"]
        and all(r["pass_guard"] for r in haar_rows) and parseval["pass_guard"]
        and duplicate["pass_guard"] and all(r["pass_guard"] for r in metric_rows)
        and norms["pass_guard"] and zero_check["pass_guard"] and clipping_refused
        and missing_phase_refused and unsupported_geometry
        and alias_cancellation and guards["pass_guard"])
    result = dict(mechanical_pass=mechanical,
        model_adequacy_pass=all(r["pass_guard"] for r in forward_rows),
        A_adjoint=a_dot, wrong_phase_foil=wrong_phase, wrong_phase_rejected=not wrong_phase["pass_guard"],
        constant_A=constant_error, constant_delivery=delivery_constant,
        independent_forward_truth=forward_rows, physical_node_max=good_nodes,
        wrong_footprint=wrong_footprint, Haar=haar_rows, uniform_parseval=parseval,
        duplicate_identity=duplicate, common_metric_scaling=metric_rows, norm_controls=norms,
        zero_rhs=zero_check, clipping_refused=clipping_refused,
        missing_phase_domain_refused=missing_phase_refused,
        unsupported_footprint_refused=unsupported_geometry,
        alias=alias_record, visibility_quadrature=visibility_precision, destroyers=guards,
        original_input_files_unchanged=True, admission=False)
    fx.save_json(out/"mechanics.json", result)
    return result


def fit_one(model, manifest, case, mode, baseline, out):
    entered = time.perf_counter()
    row, arrays = fx.load_case(manifest, case)
    config = config_for(model, row)
    sources = make_sources(model, row, arrays)
    before = [hashlib.sha256(a.tobytes()).hexdigest() for a in arrays]
    start = time.perf_counter()
    problem = model.prepare(sources, config, mode=mode)
    prepared = time.perf_counter()
    forward_times, adjoint_times = [], []
    original_forward, original_adjoint = problem.forward, problem.adjoint
    def timed_forward(value):
        begin = time.perf_counter()
        answer = original_forward(value)
        forward_times.append(time.perf_counter()-begin)
        return answer
    def timed_adjoint(value):
        begin = time.perf_counter()
        answer = original_adjoint(value)
        adjoint_times.append(time.perf_counter()-begin)
        return answer
    # CPU calls are synchronous. These wrappers observe the actual calls, make
    # no extra operator evaluation, and do not modify inputs/results/algorithm.
    problem.forward, problem.adjoint = timed_forward, timed_adjoint
    try:
        result = model.fit(problem)
    finally:
        problem.forward, problem.adjoint = original_forward, original_adjoint
    finished = time.perf_counter()
    target = out/(case+"--"+mode)
    # Preserve the finite field and its exact numerical refusal before scoring.
    saved = result.save(target)
    rgb = result.output.detach().numpy()
    display = fx.preview(target/"complete-output.png", rgb)
    latent_display = fx.preview(target/"latent-coefficients.png", result.x.detach().numpy())
    score = image_score(row, rgb)
    base_score = image_score(row, baseline) if baseline is not None else None
    guard = quality_guard(case, score, base_score)
    after = [hashlib.sha256(s.codes.tobytes()).hexdigest() for s in sources]
    unchanged = before == after
    for original in row["sources"]:
        verify_ref(original)
    post_seconds = time.perf_counter()-finished
    non_operator = max(0., finished-prepared-sum(forward_times)-sum(adjoint_times))
    timing = dict(fixture_load_and_geometry_seconds=start-entered,
        prepare_seconds=prepared-start, fit_and_delivery_seconds=finished-prepared,
        postprocessing_seconds=post_seconds,
        actual_weighted_forward_call_seconds=forward_times,
        actual_weighted_adjoint_call_seconds=adjoint_times,
        weighted_forward_calls=len(forward_times), weighted_adjoint_calls=len(adjoint_times),
        forward_max_seconds=max(forward_times, default=0.),
        adjoint_max_seconds=max(adjoint_times, default=0.),
        fit_non_operator_seconds=non_operator,
        counts_match_producer=(len(forward_times) == result.evidence["weighted_forward_calls"]
            and len(adjoint_times) == result.evidence["weighted_adjoint_calls"]),
        semantics="fit_and_delivery is solver plus reference-cell integration only, excluding field saves/PNG/scoring; synchronous CPU producing calls, no extra evaluations; postprocessing excludes writing this receipt and later progress JSON")
    # A conservative finite-work projection, not a measured64-step benchmark.
    # Every full fit is charged max128B+129B^T calls and64/observed-iteration
    # nonoperator work; one-time delivery is deliberately overcharged if short.
    timing["projected_64_step_fit_seconds"] = (start-entered+prepared-start+post_seconds
        +128*timing["forward_max_seconds"]+129*timing["adjoint_max_seconds"]
        +non_operator*64/max(1, result.iterations))
    receipt = dict(case_id=case, mode=mode, status=result.status,
        converged=result.converged, iterations=result.iterations,
        prepare_seconds=prepared-start, fit_and_delivery_seconds=finished-prepared,
        algorithm_wall_seconds=finished-start,
        total_observed_seconds=time.perf_counter()-entered, complete_field=saved,
        complete_display=display, latent_display=latent_display,
        score=score, actual_baseline_score=base_score, quality_guard=guard,
        original_bytes_unchanged=unchanged, timing=timing,
        admission=False, photographic_admission=False)
    fx.save_json(target/"independent-observations.json", receipt)
    if not unchanged:
        raise ValueError("original in-memory source bytes changed")
    if not timing["counts_match_producer"]:
        raise ValueError("timed producing call counts differ from solver evidence")
    del problem, result, sources, arrays
    gc.collect()
    return receipt


def run(args):
    out = Path(args.out).resolve()
    if args.stage == "prepare":
        manifest = fx.export_all(out)
        print(json.dumps(dict(status="FIXED_INDEPENDENT_FIXTURES_PREPARED",
            fixture_manifest=fx.file_ref(out/"fixture-manifest.json"),
            baseline_manifest=manifest["baseline_manifest"], cases=len(manifest["cases"]))))
        return
    if args.fixtures is None or args.expected_operator_sha is None:
        raise ValueError("cost/full require fixtures and expected-operator-sha")
    out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    model = load_model(args.expected_operator_sha)
    manifest_path = Path(args.fixtures).resolve()
    manifest_ref = fx.file_ref(manifest_path)
    manifest = load_json(manifest_path)
    if manifest["cases_order"] != list(fx.CASES) or manifest["total_full_screen_fits"] != 14:
        raise ValueError("fixed case inventory differs")
    fx.ICC = verify_ref(manifest["display_icc"]).read_bytes()
    baselines, baseline_receipt = read_baselines(args.baseline, manifest, out)
    started = dict(stage=args.stage, command=[sys.executable, *sys.argv],
        sources=[fx.file_ref(HERE/n) for n in ("controls.py", "fixtures.py", "sensor-operator.py", "api.md")],
        fixture_manifest=manifest_ref, actual_baseline=baseline_receipt,
        torch_version=torch.__version__, cpu_workers=torch.get_num_threads(),
        cuda_math=False, tf32=False, candidate_fits=1 if args.stage == "cost" else 10,
        auxiliary_fits=0 if args.stage == "cost" else 4,
        score_xywh=[16, 16, 96, 96], admission=False, photographic_admission=False)
    fx.save_json(out/"started.json", started)
    screen = dict(status="STARTED", stage=args.stage, all_cases_completed=False,
        mechanical_pass=False, model_adequacy_pass=False, numerical_pass=False,
        quality_pass=False, admission=False, photographic_admission=False,
        full_design_qualified=False, cases=[])
    try:
        commission = out/"commission"
        commission.mkdir()
        mechanical_start = time.perf_counter()
        mechanical = mechanics(model, manifest, commission)
        screen["mechanics_wall_seconds"] = time.perf_counter()-mechanical_start
        screen["mechanics"] = fx.file_ref(commission/"mechanics.json")
        screen["mechanical_pass"] = mechanical["mechanical_pass"]
        screen["model_adequacy_pass"] = mechanical["model_adequacy_pass"]
        if not mechanical["mechanical_pass"]:
            screen["status"] = "MECHANICAL_REFUSAL"
        else:
            cases = ("flat-neutral",) if args.stage == "cost" else fx.CASES
            for case in cases:
                modes = ("candidate",) if args.stage == "cost" else ("candidate", *fx.EXTRA_FIT_MODES.get(case, ()))
                for mode in modes:
                    row = fit_one(model, manifest, case, mode, baselines.get(case), out)
                    screen["cases"].append(row)
                    # Incremental receipts preserve each finite refused field if a later case fails.
                    fx.save_json(out/f"progress-{len(screen['cases']):02d}.json", screen)
            screen["all_cases_completed"] = True
            candidates = [r for r in screen["cases"] if r["mode"] == "candidate"]
            screen["numerical_pass"] = all(r["converged"] for r in candidates)
            screen["quality_pass"] = all(r["quality_guard"]["pass_guard"] for r in candidates)
            if args.stage == "cost":
                per_fit = candidates[0]["timing"]["projected_64_step_fit_seconds"]
                screen["fixed_full_projection"] = dict(
                    rule="mechanics_wall_seconds+14*projected_64_step_fit_seconds",
                    seconds=screen["mechanics_wall_seconds"]+14*per_fit,
                    fit_count=14, max_iterations_each=64,
                    assumptions="same fixed128²/7source matrices; per-call observed maxima; no cost-based fixture shrink or cap change",
                    measured_full_screen=False, automatic_release=False)
            screen["status"] = ("COMPLETE_BAND_RESIDUAL_COST_DIAGNOSTIC" if args.stage == "cost"
                                else "COMPLETE_BAND_RESIDUAL_GENERATED_DIAGNOSTIC")
        screen["all_pass"] = bool(screen["all_cases_completed"] and screen["mechanical_pass"]
            and screen["model_adequacy_pass"] and screen["numerical_pass"] and screen["quality_pass"])
        verify_ref(manifest_ref)
        for item in started["sources"]:
            verify_ref(item)
        screen["bound_sources_unchanged"] = True
    except Exception as exc:
        screen["status"] = "HARD_FAILURE_WITH_RETAINED_EVIDENCE"
        screen["error"] = str(exc)
        screen["traceback"] = traceback.format_exc()
        screen["all_pass"] = False
        fx.save_json(out/"screen.json", screen)
        raise
    fx.save_json(out/"screen.json", screen)
    print(json.dumps({k: screen[k] for k in ("status", "all_cases_completed", "mechanical_pass",
        "model_adequacy_pass", "numerical_pass", "quality_pass", "admission", "photographic_admission")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("prepare", "cost", "full"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--fixtures")
    parser.add_argument("--baseline")
    parser.add_argument("--expected-operator-sha")
    run(parser.parse_args())
