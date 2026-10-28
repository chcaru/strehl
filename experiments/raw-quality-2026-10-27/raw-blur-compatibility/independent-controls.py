"""Independent analytic continuous-CFA falsifier. Root runs; no RAW reader."""
from pathlib import Path
import argparse
import gc
import hashlib
import importlib.util
import json
import math
import time

import numpy as np
from PIL import Image, ImageCms
from scipy.special import j0
import torch

HERE = Path(__file__).resolve().parent
MODEL_SHA = "659da66d343908564b16262482dc55e3220dd15f8318bf49623a7b2d8d8106cc"
PANEL, APRON = 96, 72
SHAPE = (PANEL+2*APRON,)*2
SHOT = np.array([.15, .13, .17, .21], dtype=np.float64)
READ = np.array([9., 8., 11., 13.], dtype=np.float64)
BLACK = np.array([512., 512., 512., 512.], dtype=np.float64)
CHANNEL = np.array([0, 1, 1, 2])
VAR = np.array([0., .35, .8, 1.6, 3., .6, 2.3])
CASES = ("flat-neutral", "flat-colour", "compatible", "mixed-near-far",
         "annular", "changing-glint", "chromatic-asymmetric", "sharper-than-anchor")
YY, XX = np.mgrid[:PANEL, :PANEL]
XY = np.column_stack((XX.ravel(), YY.ravel())).astype(np.int32)
PHASE = ((XY[:, 1] & 1)*2+(XY[:, 0] & 1)).astype(np.uint8)
CENTRAL = ((XY[:, 0] >= 16) & (XY[:, 0] < 80)
           & (XY[:, 1] >= 16) & (XY[:, 1] < 80))
CALIB = ((XY[:, 0]//16+XY[:, 1]//16) % 2 == 0)
HELD = ~CALIB
ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def save_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(value, indent=2, allow_nan=False, default=json_scalar)+"\n")


def sha_bytes(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def file_ref(path):
    p = Path(path)
    return dict(path=str(p.resolve()), bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def preview(path, rgb):
    # Fixed diagnostic display, not a Sony camera colour-development claim.
    value = np.clip(np.asarray(rgb, np.float32)*np.float32(3/15871), 0, 1)
    shown = np.where(value <= .0031308, 12.92*value,
                     1.055*np.power(value, 1/2.4)-.055)
    Image.fromarray(np.rint(shown*255).astype(np.uint8)).save(path, icc_profile=ICC)


def geometry(i):
    scale = [1., 1.005, .996, 1.009, .993, 1.004, .998][i]
    angle = [0., .004, -.006, .003, -.005, .006, -.003][i]
    shift = [(0., 0.), (.37, -.41), (-.28, .23), (.43, .31),
             (-.39, -.27), (.19, -.36), (-.33, .42)][i]
    c, s = math.cos(angle), math.sin(angle)
    return scale*np.array([[c, -s], [s, c]]), np.array(shift)


def mapped(xy, matrix, shift):
    return (np.asarray(xy, np.float64)-(PANEL-1)/2)@matrix.T+(PANEL-1)/2+shift


def query(model, matrix, shift, mask=None, wrong_footprint=False):
    xy = XY if mask is None else XY[mask]
    nodes, weights = np.polynomial.legendre.leggauss(3)
    dx, dy = np.meshgrid(nodes*.5, nodes*.5)
    points = np.column_stack((dx.ravel(), dy.ravel()))
    weight = np.outer(weights, weights).ravel().astype(np.float32)/4
    center = mapped(xy, matrix, shift)
    offsets = points if wrong_footprint else points@matrix.T
    phase = ((xy[:, 1] & 1)*2+(xy[:, 0] & 1)).astype(np.uint8)
    return model.Query(xy.copy(), phase, (center[:, None, :]+offsets[None]+APRON), weight)


def terms(case):
    # Each real cosine is independently integrated over the ORIGINAL square.
    # Integer multiples of1/64 make the central64 truth components orthogonal.
    if case.startswith("flat-"):
        return []
    result = [
        ("neutral-coarse", (.0625, 0.), .21, (160., 160., 160.), "near"),
        ("near-fine", (.15625, .03125), .63, (240., 220., 210.), "near"),
        ("far-coarse", (.03125, .015625), 1.13, (190., 110., 280.), "far"),
        ("blue-diagonal", (.09375, -.0625), .83, (0., 0., 220.), "far"),
        ("weak-green-crossing", (-.0625, .125), .39, (220., 8., -160.), "near"),
    ]
    for k in range(1, 4):
        result.append((f"red-thin-lines-h{k}", (0., k/16), .47*k,
                       (280./k, 0., 0.), "near"))
    if case == "changing-glint":
        # Periodic compact positive bump: cos^8(pi*(x-48)/96)*cos^8(...).
        # Analytic Fourier coefficients avoid a shared raster/blur generator.
        for k in range(-4, 5):
            for l in range(-4, 5):
                a = math.comb(8, k+4)*math.comb(8, l+4)/65536
                result.append(("glint", (k/96, l/96), -2*math.pi*(k+l)*.5,
                               tuple(1800*a for _ in range(3)), "glint"))
    return result


def dc(case):
    return np.array([2048., 2048., 2048.] if case == "flat-neutral"
                    else [1800., 2100., 2400.])


def transfer(case, i, frequency, owner):
    f = np.array(frequency)
    v = VAR[i]
    if case == "mixed-near-far" and owner == "far":
        v = [6., 3., 1.2, .4, 0., 4., .8][i]
    if case == "sharper-than-anchor":
        v = [4., 0., .4, 1.8, 3., 0., 2.][i]
    if case == "annular":
        return np.full(3, j0(2*math.pi*math.sqrt(2*v)*np.linalg.norm(f)), complex)
    if case == "chromatic-asymmetric":
        result = []
        for scale, sx, sy in [(0.4, .25, 0.), (1., 0., 0.), (2., 0., -.2)]:
            result.append(np.exp(-2*math.pi**2*v*scale*np.dot(f, f))
                          *np.exp(-2j*math.pi*math.sqrt(v)*(f[0]*sx+f[1]*sy)))
        return np.array(result)
    factor = np.exp(-2*math.pi**2*v*np.dot(f, f))
    if owner == "glint":
        factor *= [1., .45, 1.5, .7, 1.35, 1.7, .35][i]
    return np.full(3, factor, complex)


def field(case, xy, *, view=None, matrix=None, shift=None, integrate=False,
          wrong_footprint=False, selected=None):
    xy = np.asarray(xy, np.float64)
    matrix = np.eye(2) if matrix is None else matrix
    shift = np.zeros(2) if shift is None else shift
    q = mapped(xy, matrix, shift)
    out = np.broadcast_to(dc(case) if selected is None else np.zeros(3), (len(q), 3)).copy()
    for name, frequency, phase, amplitude, owner in terms(case):
        if selected is not None and name != selected:
            continue
        f = np.array(frequency)
        footprint = 1.
        if integrate:
            source_f = f if wrong_footprint else matrix.T@f
            footprint = np.sinc(source_f[0])*np.sinc(source_f[1])
        attenuation = np.ones(3) if view is None else transfer(case, view, f, owner)
        wave = np.exp(1j*(2*math.pi*(q@f)+phase))
        out += (wave[:, None]*attenuation[None]).real*np.array(amplitude)*footprint
    return out.astype(np.float32)


def noise_variance(mu, phase):
    return SHOT[phase]*np.maximum(np.asarray(mu, np.float64)-BLACK[phase], 0)+READ[phase]+1/12


def held_guard(prediction, codes, phase, xy):
    z = (np.asarray(codes, np.float64)-prediction)/np.sqrt(noise_variance(prediction, phase))
    rms = float(np.sqrt(np.mean(z*z)))
    rows = []
    for p in range(4):
        values = z[phase == p]
        rows.append(dict(phase=p, n=len(values), rms=float(np.sqrt(np.mean(values*values)))))
    cells = []
    ids = xy[:, 0]//16+6*(xy[:, 1]//16)
    for cell in np.unique(ids):
        for p in range(4):
            values = z[(ids == cell) & (phase == p)]
            if len(values):
                cells.append(dict(cell=int(cell), phase=p, n=len(values),
                    rms=float(np.sqrt(np.mean(values*values))), bias=float(np.mean(values))))
    passed = (rms <= 1.25 and all(r["rms"] <= 1.35 for r in rows)
              and all(r["rms"] <= 1.8 and abs(r["bias"]) <= .75 for r in cells))
    return dict(pass_guard=passed, rms=rms, phases=rows, cells=cells)


def image_score(case, image):
    truth = field(case, XY, integrate=True).reshape(PANEL, PANEL, 3)
    good = np.asarray(image, np.float64)[16:80, 16:80]
    ref = truth[16:80, 16:80].astype(np.float64)
    delta = good-ref
    rgb = float(np.sqrt(np.mean(delta*delta)))
    chroma = float(np.sqrt(np.mean(np.stack((delta[..., 0]-delta[..., 1],
                                           delta[..., 2]-delta[..., 1]), -1)**2)))
    components = []
    for name in dict.fromkeys(t[0] for t in terms(case)):
        if name == "glint":
            continue
        template = field(case, XY, integrate=True, selected=name).reshape(PANEL, PANEL, 3)[16:80, 16:80].astype(np.float64)
        norm = float(np.sum(template*template))
        # Score error projected onto a known component; truth itself is exactly1.
        recovery = 1+float(np.sum(delta*template))/norm
        amplitude = np.array(next(t[3] for t in terms(case) if t[0] == name))
        dominant = int(np.argmax(np.abs(amplitude)))
        basis = template[..., dominant]/amplitude[dominant]
        amplitude_error = np.sum(delta*basis[..., None], axis=(0, 1))/np.sum(basis*basis)
        limits = np.maximum(5., .1*np.abs(amplitude))
        components.append(dict(name=name, recovery=recovery,
            per_channel_amplitude_error_dn=amplitude_error.tolist(),
            per_channel_amplitude_error_limits_dn=limits.tolist(),
            colour_component_pass=bool(np.all(np.abs(amplitude_error) <= limits))))
    scale = float(np.sqrt(np.mean((ref-dc(case))**2)))
    color = np.stack((ref[..., 0]-ref[..., 1], ref[..., 2]-ref[..., 1]), -1)
    color -= color.mean((0, 1), keepdims=True)
    color_scale = float(np.sqrt(np.mean(color*color)))
    passed = (rgb <= max(25., .15*scale) and chroma <= max(25., .15*color_scale)
              and all(.9 <= r["recovery"] <= 1.1 and r["colour_component_pass"] for r in components))
    return dict(rgb_rmse_dn=rgb, chroma_rmse_dn=chroma, components=components,
                known_detail_pass=passed, rgb_bar_dn=max(25., .15*scale),
                chroma_bar_dn=max(25., .15*color_scale))


def flat_mean(codes):
    mean = np.mean(np.stack(codes[:5]).astype(np.float32), axis=0).reshape(PANEL, PANEL)-512
    rgb = np.stack((mean[0::2, 0::2], (mean[0::2, 1::2]+mean[1::2, 0::2])*.5,
                    mean[1::2, 1::2]), -1)
    return np.repeat(np.repeat(rgb, 2, 0), 2, 1)


def generate(out):
    cases = {}
    fy, fx = np.mgrid[:SHAPE[0], :SHAPE[1]]
    latent_xy = np.column_stack((fx.ravel()-APRON, fy.ravel()-APRON))
    for k, name in enumerate(CASES):
        folder = out/name
        folder.mkdir()
        truth = field(name, XY, integrate=True).reshape(PANEL, PANEL, 3)
        latent = field(name, latent_xy).reshape(*SHAPE, 3)
        np.save(folder/"truth-cell-rgb.npy", truth)
        np.save(folder/"truth-latent-rgb.npy", latent)
        preview(folder/"truth-complete.png", truth)
        codes, means = [], []
        for i in range(7):
            a, t = geometry(i)
            rgb = field(name, XY, view=i, matrix=a, shift=t, integrate=True)
            mu = rgb[np.arange(len(XY)), CHANNEL[PHASE]].astype(np.float64)+BLACK[PHASE]
            rng = np.random.default_rng(0x61437+100*k+i)
            noise = rng.standard_normal(len(XY))*np.sqrt(noise_variance(mu, PHASE)-1/12)
            original = np.rint(mu+noise)
            assert original.min() >= 0 and original.max() < 16383
            original = original.astype(np.uint16)
            codes.append(original)
            means.append(mu.astype(np.float32))
            np.save(folder/f"source-{i}-original-cfa.npy", original.reshape(PANEL, PANEL))
            # Complete literal source mosaic; no demosaicer creates a comparator.
            preview(folder/f"source-{i}-mosaic.png", np.repeat((original.reshape(PANEL, PANEL)-512).astype(np.float32)[..., None], 3, axis=2))
        np.savez(folder/"original-observations.npz", codes=np.stack(codes),
                 noiseless_means=np.stack(means), original_xy=XY, phase=PHASE,
                 calibration_mask=CALIB, held_mask=HELD)
        cases[name] = dict(folder=folder, truth=truth, latent=latent, codes=codes, means=means)
    return cases


def commission(model, config, cases):
    result = {}
    identity = query(model, *geometry(0))
    flat = cases["flat-colour"]
    pred = model.forward(flat["latent"], 0., identity, config).detach().cpu().numpy()
    exact = flat["means"][0]
    # Conservative allowance for ~1024 f32 weighted operations at this DC.
    allowance = 1024*np.finfo(np.float32).eps*float(np.max(exact))
    result["flat_forward"] = dict(max_dn=float(np.max(np.abs(pred-exact))), allowance_dn=allowance)
    result["flat_forward"]["pass_guard"] = result["flat_forward"]["max_dn"] <= allowance
    try:
        model.Query(identity.original_xy, ((identity.phase+1)%4).astype(np.uint8),
                    identity.nodes_xy, identity.footprint_weights)
        phase_rejected = False
    except ValueError:
        phase_rejected = True
    result["literal_phase_destroyer_rejected"] = phase_rejected
    c, s = math.cos(.17), math.sin(.17)
    a = 1.12*np.array([[c, -s], [s, c]])
    t = np.array([.37, -.41])
    q = query(model, a, t, CENTRAL)
    wrong = query(model, a, t, CENTRAL, wrong_footprint=True)
    data = cases["compatible"]
    x = torch.tensor(data["latent"], device="cuda", dtype=torch.float32, requires_grad=True)
    rows = []
    for variance in (0., .35, 2.3):
        # Independently attenuate Fourier terms at the requested physical variance.
        rgb = dc("compatible")+sum(
            (field("compatible", XY[CENTRAL], matrix=a, shift=t, integrate=True, selected=name)
             *np.float32(np.exp(-2*math.pi**2*variance*np.dot(f, f))))
            for name, f, _, _, _ in terms("compatible"))
        expected = rgb[np.arange(len(q.phase)), CHANNEL[q.phase]]+BLACK[q.phase]
        got = model.forward(x, variance, q, config).detach().cpu().numpy()
        sigma = np.sqrt(noise_variance(expected, q.phase))
        error = (got-expected)/sigma
        row = dict(variance=variance, rms_sigma=float(np.sqrt(np.mean(error*error))),
                   max_sigma=float(np.max(np.abs(error))))
        row["pass_guard"] = row["rms_sigma"] <= .25 and row["max_sigma"] <= .75
        if variance == 0:
            bad = model.forward(x, 0., wrong, config).detach().cpu().numpy()
            wrong_error = (bad-expected)/sigma
            row["wrong_reference_footprint_rms_sigma"] = float(np.sqrt(np.mean(wrong_error**2)))
            row["wrong_footprint_exercised"] = row["wrong_reference_footprint_rms_sigma"] > 1.5*row["rms_sigma"]
        rows.append(row)
    result["independent_continuous_forward"] = rows
    delivered = model.integrate_reference(x, config).detach().cpu().numpy()
    result["known_output_integration"] = image_score("compatible", delivered)
    output_error = delivered[16:80, 16:80]-data["truth"][16:80, 16:80]
    output_sigma = np.sqrt(np.array([SHOT[0], .5*(SHOT[1]+SHOT[2]), SHOT[3]])
        *data["truth"][16:80, 16:80]+np.array([READ[0], .5*(READ[1]+READ[2]), READ[3]])+1/12)
    result["known_output_integration"]["rms_sigma"] = float(np.sqrt(np.mean((output_error/output_sigma)**2)))
    wrong_map = query(model, a, t+np.array([2., 0.]), CENTRAL)
    wrong_prediction = model.forward(x, 0., wrong_map, config).detach().cpu().numpy()
    true_rgb = field("compatible", XY[CENTRAL], matrix=a, shift=t, integrate=True)
    true_mu = true_rgb[np.arange(len(q.phase)), CHANNEL[q.phase]]+BLACK[q.phase]
    wrong_map_rms = float(np.sqrt(np.mean((wrong_prediction-true_mu)**2/noise_variance(true_mu, q.phase))))
    result["wrong_map_destroyer"] = dict(rms_sigma=wrong_map_rms, pass_guard=wrong_map_rms > 1.)
    # Full linear path: an all-colour signed direction, unequal G1/G2 noise.
    direction = np.empty_like(data["latent"])
    iy, ix = np.mgrid[:SHAPE[0], :SHAPE[1]]
    for channel in range(3):
        direction[..., channel] = np.sin(.19*ix+.13*iy+.7*channel)
    d = torch.tensor(direction, device="cuda")
    z = np.sin(np.arange(len(q.phase))*.173)/noise_variance(rows[0]["variance"]+exact[CENTRAL], q.phase)
    p = model.forward(x, .8, q, config)
    gradient = torch.autograd.grad((p*torch.tensor(z, dtype=torch.float32, device="cuda")).sum(), x)[0]
    lhs = float((gradient.double()*d.double()).sum())
    with torch.no_grad():
        directional = (model.forward(x+128*d, .8, q, config)-model.forward(x-128*d, .8, q, config))/256
    rhs = float(np.dot(directional.cpu().numpy().astype(np.float64), z))
    tolerance = 2e-3*max(abs(lhs), abs(rhs))+1e-6
    result["all_phase_directional_gradient"] = dict(adjoint_dot=lhs, forward_dot=rhs,
        tolerance=tolerance, pass_guard=abs(lhs-rhs) <= tolerance)
    good = held_guard(data["means"][5][HELD], data["codes"][5][HELD], PHASE[HELD], XY[HELD])
    sigma = np.sqrt(noise_variance(data["means"][5][HELD], PHASE[HELD]))
    bad = held_guard(data["means"][5][HELD]+12*sigma, data["codes"][5][HELD], PHASE[HELD], XY[HELD])
    truth = data["truth"]
    erased = truth-field("compatible", XY, integrate=True, selected="far-coarse").reshape(PANEL, PANEL, 3)
    over = dc("compatible")+1.3*(truth-dc("compatible"))
    result["guard_commission"] = dict(compatible_known_forward_pass=good["pass_guard"],
        biased_prediction_refused=not bad["pass_guard"], truth_image_pass=image_score("compatible", truth)["known_detail_pass"],
        erased_far_refused=not image_score("compatible", erased)["known_detail_pass"],
        overcontrast_refused=not image_score("compatible", over)["known_detail_pass"])
    result["pass_guard"] = (result["flat_forward"]["pass_guard"] and phase_rejected
        and all(r["pass_guard"] for r in rows) and rows[0]["wrong_footprint_exercised"]
        and result["known_output_integration"]["known_detail_pass"]
        and result["known_output_integration"]["rms_sigma"] <= .25
        and result["wrong_map_destroyer"]["pass_guard"]
        and result["all_phase_directional_gradient"]["pass_guard"]
        and all(result["guard_commission"].values()))
    del x, p, gradient, d
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    start = time.monotonic()
    args.out.mkdir(parents=True, exist_ok=False)
    before = [file_ref(Path(__file__)), file_ref(HERE/"model.py")]
    assert before[1]["sha256"] == MODEL_SHA, "producer source differs from reviewed frozen model"
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        save_json(args.out/"observations.json", dict(status="CUDA_UNAVAILABLE", quality_claim=False))
        return
    torch.cuda.set_per_process_memory_fraction(min(1., (4 << 30)/torch.cuda.get_device_properties(0).total_memory))
    spec = importlib.util.spec_from_file_location("independently_screened_raw_blur", HERE/"model.py")
    model = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    config = model.Config(field_hw=SHAPE, output_xywh=(APRON, APRON, PANEL, PANEL),
        shot4=tuple(SHOT), read4=tuple(READ), black4=tuple(BLACK), saturation=16383, anchor_id=0)
    cases = generate(args.out)
    commission_result = commission(model, config, cases)
    save_json(args.out/"commission.json", commission_result)
    records = []
    status = "OPERATOR_REFUSAL" if not commission_result["pass_guard"] else "SCREEN_COMPLETE"
    if commission_result["pass_guard"]:
        for name, data in cases.items():
            if time.monotonic()-start > 100:
                status = "RESOURCE_ENVELOPE_NOT_ALL_CASES_RUN"
                break
            views = []
            input_hashes = [sha_bytes(v) for v in data["codes"]]
            for i in range(7):
                mask = None if i < 5 else CALIB
                q = query(model, *geometry(i), mask)
                code = data["codes"][i] if mask is None else data["codes"][i][mask]
                views.append(model.View(i, q, code))
            result = model.fit(views[:5], views[5:], config)
            result.save(data["folder"]/"fit")
            preview(data["folder"]/"fit-complete.png", result.output_rgb_dn)
            preview(data["folder"]/"initial-complete.png", result.initial_rgb_dn)
            score = image_score(name, result.output_rgb_dn)
            held = []
            for i in (5, 6):
                q = query(model, *geometry(i), HELD)
                prediction = model.predict(result, q, source_id=i)
                held.append(dict(source=i, **held_guard(prediction, data["codes"][i][HELD], PHASE[HELD], XY[HELD])))
                np.save(data["folder"]/f"held-{i}-prediction.npy", prediction)
            calibration_localized = all(c["numerical_converged"] for c in result.calibration.values())
            # A flat cannot identify blur. Its scalar-calibration ambiguity is
            # recorded, not relabelled as a well-identified variance estimate.
            numerical = bool(result.converged) and not result.unsupported
            if not name.startswith("flat-"):
                numerical = numerical and calibration_localized
            operational = numerical and all(v["pass_guard"] for v in held)
            if name.startswith("flat-"):
                mean = flat_mean(data["codes"])
                preview(data["folder"]/"same-data-flat-mean-complete.png", mean)
                reference = image_score(name, mean)
                truth_pass = (score["rgb_rmse_dn"] <= 1.1*reference["rgb_rmse_dn"]+.5
                    and score["chroma_rmse_dn"] <= 1.1*reference["chroma_rmse_dn"]+.5)
                passed = operational and truth_pass
                score["flat_mean_reference"] = reference
                score["flat_relative_noise_pass"] = truth_pass
                interpretation = "Flat variances are unidentifiable; prediction cannot calibrate blur."
            elif name == "compatible":
                passed = operational and score["known_detail_pass"]
                interpretation = "Compatible positive must be accepted and preserve known colour/detail."
            else:
                passed = numerical and ((not operational) or score["known_detail_pass"])
                if name == "sharper-than-anchor":
                    passed = numerical and not operational
                interpretation = "Numerical failure is not operational physical-mismatch refusal; accepted detail loss fails."
            row = dict(case=name, numerical_converged=numerical, fit_status=result.status,
                operationally_accepted=operational, held=held, image=score, pass_case=passed,
                interpretation=interpretation, variances=result.variances,
                calibration_parameter_localized=calibration_localized,
                blur_identification_claim=False if name.startswith("flat-") else None,
                original_u16_unchanged=input_hashes == [sha_bytes(v) for v in data["codes"]],
                full_input_hashes=input_hashes, numerical_evaluations=result.evaluations)
            save_json(data["folder"]/"decision.json", row)
            records.append(row)
            del result, views
            gc.collect()
            torch.cuda.empty_cache()
            if not passed:
                status = "NUMERICAL_REFUSAL" if not numerical else "FIXED_SCREEN_REFUSAL"
                break
    after = [file_ref(Path(__file__)), file_ref(HERE/"model.py")]
    assert before == after
    save_json(args.out/"observations.json", dict(status=status,
        all_cases_completed=len(records) == len(CASES), all_pass=status == "SCREEN_COMPLETE",
        photographic_admission=False, actual_native_baseline=False, RAW_reads=0,
        full_design_qualified=False,
        deferred_guards=["Spatially separated cells with changing least-blurred source; current mixed-frequency case does not test that spatial ordering."],
        command=[sys.executable, *sys.orig_argv[1:]], source_bindings=before,
        torch_version=torch.__version__, cuda_version=torch.version.cuda,
        tf32_matmul=torch.backends.cuda.matmul.allow_tf32, tf32_cudnn=torch.backends.cudnn.allow_tf32,
        display="All complete96x96 panels; fixed signalDN/15871 gain3 sRGB, original source mosaics, no resampling.",
        split="Five full training views. Views5/6 carry only even16px checker cells into scalar calibration; odd cells only score after fit.",
        commission=commission_result, cases=records, skipped=list(CASES[len(records):]),
        seconds=time.monotonic()-start, cuda_peak_allocated=torch.cuda.max_memory_allocated(),
        cuda_peak_reserved=torch.cuda.max_memory_reserved()))
    print(json.dumps(dict(status=status, cases=len(records), photographic_admission=False)))


if __name__ == "__main__":
    main()
