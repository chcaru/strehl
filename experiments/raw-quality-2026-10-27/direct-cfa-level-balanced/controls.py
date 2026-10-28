"""Independent root-scheduled controls; no RAW reader or photographic admission."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import sys
import traceback

import numpy as np
import torch as t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE.parent / "direct-cfa-streamed-normal"
FIX = HERE.parent / "joint-cfa-local-fit/band-residual"
MANIFEST = ROOT / "outputs/raw-quality-2026-10-27/joint-cfa-band-prepare-1/output/fixture-manifest.json"
BASELINE = ROOT / "outputs/raw-quality-2026-10-27/joint-cfa-band-baseline-1/output/receipt.json"
LIMIT = 8 << 30
MAX_BAR, RMS_BAR, DOT_BAR = 1e-5, 2e-6, 3e-6
RATIO_BAR = 3e-5
SQ = np.float32(math.sqrt(.5))
PINS = {
    FIX / "fixtures.py": "759f3b7d24ec480ab7158e149eb3030e613c4d3e6ae7000d5dd07644c9ab1ba6",
    FIX / "controls.py": "094b633678e44e7ebfa63c9648db03c2e3aa182406383b4989d0f42ba7a36120",
    OLD / "bands-gpu.py": "d837961600d327d8aa3b5438565c357dd01327c1e6f6ffc4dc4b445b021cf1be",
    OLD / "solver-controls.py": "257bc96dbe90ec53f78854bbf94b58450d57e0dc42dbebb368b7a5fe1d638f4d",
    OLD / "measurement-paired.py": "0adbba770b06305b8bbf26a497b9b1f1ab95332edc28037634362232ebe09023",
    OLD / "delivery.py": "c59c7f6a5f218f8809de43e4315ff88f5c5cd7a124826d016da3b75563b83b3b",
    HERE.parent / "direct-cfa-forward-gpu/measurement-gpu.py": "8328b11cecf710f0020e8dfc8e8ab68467301e32290ba204fc5f9d7ebc8c0d84",
    FIX / "sensor-operator.py": "536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac",
}


def require(ok, text):
    if not ok:
        raise ValueError(text)


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(Path(path).read_bytes(), str(path), "exec"), module.__dict__)
    return module


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def array(value):
    return value.detach().cpu().numpy() if t.is_tensor(value) else np.asarray(value)


def compare(actual, expected):
    a, b = array(actual), array(expected)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), "comparison domain")
    # Accumulate only audit scalars in f64; producing/reference transforms are f32.
    d = a.astype(np.float64)-b.astype(np.float64)
    maximum = float(np.max(np.abs(d)))
    rms = float(np.sqrt(np.mean(d*d)))
    scale_max = max(1., float(np.max(np.abs(b))))
    scale_rms = max(1., float(np.sqrt(np.mean(b.astype(np.float64)**2))))
    return dict(max_abs=maximum, rms=rms, normalized_max=maximum/scale_max,
                normalized_rms=rms/scale_rms, max_bar=MAX_BAR, rms_bar=RMS_BAR,
                passed=maximum <= MAX_BAR*scale_max and rms <= RMS_BAR*scale_rms)


def relative(actual, expected):
    a, b = array(actual).astype(np.float64), array(expected).astype(np.float64)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), "relative domain")
    error, norm = float(np.linalg.norm(a-b)), float(np.linalg.norm(b))
    return dict(error_l2=error, reference_l2=norm, bar=RATIO_BAR,
                passed=error == 0 if norm == 0 else error <= RATIO_BAR*norm)


class CountHaar:
    """Independent NumPy reference, support counts from original coordinate bins."""
    def __init__(self, hw, origin=(0, 0)):
        self.hw, self.origin = tuple(hw), tuple(origin)
        self.bands, self.phases, self.sizes = [], [], []
        offset = 0
        for p in range(4):
            dx, dy = (p % 2-origin[0]) % 2, (p//2-origin[1]) % 2
            h, w = len(range(dy, hw[0], 2)), len(range(dx, hw[1], 2))
            h0, w0 = h, w
            levels, sizes = [], [(h, w)]
            for k in range(7):
                if min(h, w) < 2:
                    break
                # Each current low sample represents this clipped original bin.
                step = 1 << k
                cy = np.minimum(step, h0-np.arange(h)*step).astype(np.float32)
                cx = np.minimum(step, w0-np.arange(w)*step).astype(np.float32)
                entries = []
                for kind, shape in zip(("LH", "HL", "HH"),
                        ((h//2, (w+1)//2), ((h+1)//2, w//2), (h//2, w//2))):
                    n = shape[0]*shape[1]
                    band = dict(phase=p, level=k, kind=kind, shape=shape, start=offset, end=offset+n)
                    entries.append(band); self.bands.append(band); offset += n
                levels.append((cy, cx, entries, (h, w)))
                h, w = (h+1)//2, (w+1)//2
                sizes.append((h, w))
            low = dict(phase=p, level=len(levels), kind="LL", shape=(h, w), start=offset, end=offset+h*w)
            self.bands.append(low); offset += h*w
            self.phases.append((dy, dx, levels, low)); self.sizes.append(sizes)
        self.count = offset
        require(offset == hw[0]*hw[1], "reference completeness")

    @staticmethod
    def pair(value, axis, counts, variance=False, support=False):
        n = value.shape[axis]; pairs = n//2
        sl0, sl1 = [slice(None)]*2, [slice(None)]*2
        sl0[axis], sl1[axis] = slice(0, 2*pairs, 2), slice(1, 2*pairs, 2)
        a, b = value[tuple(sl0)], value[tuple(sl1)]
        if support:
            lo = hi = a & b
        else:
            nl, nr = counts[:2*pairs:2], counts[1:2*pairs:2]
            dims = [1, 1]; dims[axis] = pairs
            l = (np.sqrt(nl)/np.sqrt(nl+nr)).reshape(dims)
            r = (np.sqrt(nr)/np.sqrt(nl+nr)).reshape(dims)
            unequal = (nl != nr).reshape(dims)
            if variance:
                lo = np.where(unequal, l*l*a+r*r*b, (a+b)*np.float32(.5))
                hi = np.where(unequal, r*r*a+l*l*b, (a+b)*np.float32(.5))
            else:
                lo = np.where(unequal, l*a+r*b, (a+b)*SQ)
                hi = np.where(unequal, r*a-l*b, (a-b)*SQ)
        if n % 2:
            tail = [slice(None)]*2; tail[axis] = slice(n-1, n)
            lo = np.concatenate((lo, value[tuple(tail)]), axis=axis)
        return lo, hi

    @staticmethod
    def unpair(lo, hi, axis, counts):
        n = len(counts); pairs = n//2
        shape = list(lo.shape); shape[axis] = n
        result = np.empty(shape, np.float32)
        sl = [slice(None)]*2; sl[axis] = slice(0, pairs)
        a = lo[tuple(sl)]
        nl, nr = counts[:2*pairs:2], counts[1:2*pairs:2]
        dims = [1, 1]; dims[axis] = pairs
        l = (np.sqrt(nl)/np.sqrt(nl+nr)).reshape(dims)
        r = (np.sqrt(nr)/np.sqrt(nl+nr)).reshape(dims)
        unequal = (nl != nr).reshape(dims)
        first = np.where(unequal, l*a+r*hi, (a+hi)*SQ)
        second = np.where(unequal, r*a-l*hi, (a-hi)*SQ)
        s0, s1 = [slice(None)]*2, [slice(None)]*2
        s0[axis], s1[axis] = slice(0, 2*pairs, 2), slice(1, 2*pairs, 2)
        result[tuple(s0)], result[tuple(s1)] = first, second
        if n % 2:
            so, si = [slice(None)]*2, [slice(None)]*2
            so[axis], si[axis] = slice(n-1, n), slice(pairs, pairs+1)
            result[tuple(so)] = lo[tuple(si)]
        return result

    def forward(self, value, variance=False, support=False):
        result = np.empty(self.count, bool if support else np.float32)
        for dy, dx, levels, low in self.phases:
            x = value[dy::2, dx::2]
            for cy, cx, entries, _ in levels:
                lx, hx = self.pair(x, 1, cx, variance, support)
                ll, lh = self.pair(lx, 0, cy, variance, support)
                hl, hh = self.pair(hx, 0, cy, variance, support)
                for band, field in zip(entries, (lh, hl, hh)):
                    result[band["start"]:band["end"]] = field.reshape(-1)
                x = ll
            result[low["start"]:low["end"]] = x.reshape(-1)
        return result

    def inverse(self, value):
        result = np.empty(self.hw, np.float32)
        for dy, dx, levels, low in self.phases:
            x = value[low["start"]:low["end"]].reshape(low["shape"])
            for cy, cx, entries, _ in levels[::-1]:
                lh, hl, hh = [value[b["start"]:b["end"]].reshape(b["shape"]) for b in entries]
                lx, hx = self.unpair(x, lh, 0, cy), self.unpair(hl, hh, 0, cy)
                x = self.unpair(lx, hx, 1, cx)
            result[dy::2, dx::2] = x
        return result


def smooth3(a, boolean=False):
    pad = np.pad(a, 1, mode="edge")
    out = np.ones_like(a, bool) if boolean else np.zeros_like(a, np.float32)
    for y in range(3):
        for x in range(3):
            v = pad[y:y+a.shape[0], x:x+a.shape[1]]
            out = out & v if boolean else out+v
    return out if boolean else out/np.float32(9)


def cpu_source(codes, origin, noise, mode):
    plan = CountHaar(codes.shape, origin)
    obs, variance = codes.astype(np.float32), np.empty(codes.shape, np.float32)
    valid = codes < noise.saturation
    for p, (dy, dx, _, _) in enumerate(plan.phases):
        obs[dy::2, dx::2] -= np.float32(noise.black4[p])
        variance[dy::2, dx::2] = np.float32(noise.shot4[p])*np.maximum(obs[dy::2, dx::2], 0)+np.float32(noise.read4[p])
    d, v = plan.forward(obs), plan.forward(variance, variance=True)
    support = plan.forward(valid, support=True); admitted = support.copy()
    a = np.ones(plan.count, np.float32)
    for band in plan.bands:
        lo, hi = band["start"], band["end"]
        if band["kind"] != "LL":
            admitted[lo:hi] = smooth3(support[lo:hi].reshape(band["shape"]), True).reshape(-1)
            if mode == "candidate":
                E, V = smooth3(d[lo:hi].reshape(band["shape"])**2), smooth3(v[lo:hi].reshape(band["shape"]))
                a[lo:hi] = np.maximum((np.maximum(E-2*V, 0)/(64*np.maximum(V, 1)))**2, np.float32(1e-4)).reshape(-1)
    q = np.where(admitted, a/np.maximum(v, 1), np.float32(0)).astype(np.float32)
    return dict(plan=plan, d=d, variance=v, admission=a, metric=q, valid=admitted)


def normalization_controls(problem, normal, arrays, noise, mode):
    references = [cpu_source(x, (0, 0), noise, mode) for x in arrays]
    Q, R = np.zeros(7, np.float32), np.zeros(7, np.float32)
    for row in references:
        for b in row["plan"].bands:
            if b["kind"] == "LL":
                continue
            sl = slice(b["start"], b["end"]); k = b["level"]
            Q[k] += row["metric"][sl].sum(dtype=np.float32)
            R[k] += np.where(row["valid"][sl], np.float32(1)/np.maximum(row["variance"][sl], 1), 0).sum(dtype=np.float32)
    multiplier = np.divide(R, Q, out=np.zeros(7, np.float32), where=R > 0)
    checks = dict(Q=relative(problem.level_Q_f32, Q), R=relative(problem.level_R_f32, R),
                  multiplier=relative(problem.level_multipliers_f32, multiplier))
    ratio_checks = []; mass = np.zeros(7, np.float64); ll_exact = True
    for i, row in enumerate(references):
        actual = problem.current_source(i); expected = row["metric"].copy()
        for b in row["plan"].bands:
            sl = slice(b["start"], b["end"])
            if b["kind"] != "LL":
                expected[sl] *= multiplier[b["level"]]
                mass[b["level"]] += array(actual.metric[sl]).sum(dtype=np.float64)
            else:
                ll_exact = ll_exact and compare(actual.metric[sl], expected[sl])["passed"]
        ratio_checks.append(relative(actual.metric, expected))
        del actual
    checks["mass"] = relative(mass, R)
    raw = normal.prepare_source(t, arrays[0], (0, 0), noise, mode, collect_evidence=False)
    correct = problem.current_source(0).metric.detach().clone()
    wrong = problem.level_multipliers_f32.clone(); wrong[0] *= 8
    normal.apply_level_balance(raw, wrong)
    foil = relative(raw.metric, correct)
    del raw, correct
    return dict(checks=checks, source_metric_checks=ratio_checks, ll_unchanged=ll_exact,
                shared_multiplier=multiplier.tolist(), wrong_level=foil,
                passed=all(x["passed"] for x in checks.values()) and all(x["passed"] for x in ratio_checks)
                    and ll_exact and not foil["passed"])


def unsupported_controls(normal):
    Q = t.tensor([2., 4., 0., 1., 0., 9., 0.], device="cuda:0")
    R = t.tensor([4., 1., 0., 3., 0., 9., 0.], device="cuda:0")
    ordinary = normal.resolve_level_balance(t, Q, R)
    good = compare(ordinary, np.array([2., .25, 0., 3., 0., 1., 0.], np.float32))
    rejected = []
    for label, q, r in (("positiveR-zeroQ", Q.clone(), R.clone()), ("nonfiniteQ", Q.clone(), R.clone())):
        q[0] = 0 if label == "positiveR-zeroQ" else float("nan")
        try:
            normal.resolve_level_balance(t, q, r)
        except ValueError as error:
            rejected.append(dict(name=label, rejected=True, error=str(error)))
        else:
            rejected.append(dict(name=label, rejected=False))
    noise = normal.Noise((.15,)*4, (9.,)*4, (512.,)*4, 15360)
    source = normal.prepare_source(t, np.full((19,23),15360,np.uint16), (3,5), noise, collect_evidence=False)
    q, r, _, _ = normal.level_statistics(source)
    empty = normal.resolve_level_balance(t,q,r)
    omitted = not bool(source.valid_coeff.any()) and not bool(source.metric.any()) and not bool(empty.any())
    return dict(ordinary=good, refusals=rejected, actual_all_clipped_omitted=omitted,
                passed=good["passed"] and all(x["rejected"] for x in rejected) and omitted)


def haar_controls(bands, legacy):
    results = []
    for hw, origin in (((4688, 7032), (0, 0)), ((19, 23), (3, 5))):
        cpu, gpu = CountHaar(hw, origin), bands.HaarPlan(t, hw, origin)
        require(cpu.bands == gpu.bands and cpu.sizes == gpu.sizes, "independent Haar layout differs")
        one = t.ones(hw, device="cuda:0", dtype=t.float32)
        constant = gpu.forward(one); reference_constant = cpu.forward(np.ones(hw, np.float32))
        ac = np.concatenate([array(constant[b["start"]:b["end"]]) for b in gpu.bands if b["kind"] != "LL"])
        legacy_coefficients = legacy.HaarPlan(t, hw, origin).forward(one)
        old_ac = np.concatenate([array(legacy_coefficients[b["start"]:b["end"]]) for b in gpu.bands if b["kind"] != "LL"])
        constant_bar = 64*np.finfo(np.float32).eps*128
        dc = dict(max_ac=float(np.abs(ac).max()), absolute_bar=float(constant_bar),
                  passed=bool(float(np.abs(ac).max()) <= constant_bar),
                  legacy_max_ac=float(np.abs(old_ac).max()), legacy_rejected=bool(float(np.abs(old_ac).max()) > constant_bar))
        del ac, old_ac, legacy_coefficients
        y = ((np.arange(hw[0], dtype=np.float32)[:, None] % 89)-44)*2 + ((np.arange(hw[1], dtype=np.float32)[None, :] % 97)-48)*4
        v = 1+(np.arange(hw[0], dtype=np.float32)[:, None] % 13)*np.float32(.0625)+(np.arange(hw[1], dtype=np.float32)[None, :] % 17)*np.float32(.125)
        signal = t.from_numpy(y).to("cuda:0"); coefficients = gpu.forward(signal)
        cpu_coefficients = cpu.forward(y)
        band_checks = [dict(phase=b["phase"], level=b["level"], kind=b["kind"],
            comparison=compare(coefficients[b["start"]:b["end"]], cpu_coefficients[b["start"]:b["end"]])) for b in gpu.bands]
        roundtrip = compare(gpu.inverse(coefficients), y)
        variance = compare(gpu.variance(t.from_numpy(v).to("cuda:0")), cpu.forward(v, variance=True))
        valid = np.ones(hw, bool); valid[hw[0]//2,hw[1]//2] = False; valid[-1,-1] = False
        support_reference = cpu.forward(valid, support=True)
        for b in cpu.bands:
            if b["kind"] != "LL":
                support_reference[b["start"]:b["end"]] = smooth3(support_reference[b["start"]:b["end"]].reshape(b["shape"]), True).reshape(-1)
        support_exact = np.array_equal(array(gpu.support(t.from_numpy(valid).to("cuda:0"))), support_reference)
        dual = ((np.arange(cpu.count, dtype=np.int32) % 17)-8).astype(np.float32)*np.float32(.125)
        inverse = gpu.inverse(t.from_numpy(dual).to("cuda:0")); expected_inverse = cpu.inverse(dual)
        inverse_check = compare(inverse, expected_inverse)
        lhs = float(np.dot(cpu_coefficients.astype(np.float64), dual.astype(np.float64)))
        inverse_cpu = array(inverse)
        rhs = float(np.sum(y.astype(np.float64)*inverse_cpu.astype(np.float64)))
        norm_product = float(np.linalg.norm(cpu_coefficients.astype(np.float64))*np.linalg.norm(dual.astype(np.float64))
                            +np.linalg.norm(y.astype(np.float64))*np.linalg.norm(inverse_cpu.astype(np.float64)))
        dot = dict(error=abs(lhs-rhs)/norm_product, bar=DOT_BAR, passed=abs(lhs-rhs) <= DOT_BAR*norm_product)
        input_energy = float(np.sum(y.astype(np.float64)**2))
        output_energy = float(np.sum(array(coefficients).astype(np.float64)**2))
        parseval = dict(error=abs(output_energy-input_energy)/input_energy, bar=DOT_BAR,
                        passed=abs(output_energy-input_energy) <= DOT_BAR*input_energy)
        wrong_inverse = compare(gpu.inverse(t.roll(coefficients, 1)), y)
        row = dict(hw=list(hw), origin=list(origin), sizes=cpu.sizes, constant=dc,
            constant_cpu=compare(constant, reference_constant), bands=band_checks, roundtrip=roundtrip,
            variance=variance, support_exact=support_exact, inverse=inverse_check, dot=dot, parseval=parseval, wrong_inverse=wrong_inverse)
        row["passed"] = (dc["passed"] and dc["legacy_rejected"] and row["constant_cpu"]["passed"]
            and all(z["comparison"]["passed"] for z in band_checks)
            and support_exact and all(z["passed"] for z in (roundtrip, variance, inverse_check, dot, parseval)) and not wrong_inverse["passed"])
        results.append(row)
        del cpu, gpu, one, signal, coefficients, constant, inverse, cpu_coefficients, expected_inverse, inverse_cpu, y, v, dual, valid, support_reference
    return dict(cases=results, passed=all(x["passed"] for x in results))


def callback_control(solver, algebra):
    plain_problem = algebra.DiagonalProblem(solver.operator)
    callback_problem = algebra.DiagonalProblem(solver.operator)
    plain = solver.fit(plain_problem)
    visited = []
    def poison(iteration, z, metadata):
        visited.append(iteration)
        z.fill_(12345)
        metadata.clear()
    observed = solver.fit(callback_problem, checkpoint=poison)
    expected = [i for i in (1, 2, 4) if i <= plain.iterations]
    equal = t.equal(plain.x, observed.x) and t.equal(plain.correction_z, observed.correction_z)
    return dict(visited=visited, expected=expected, result_bytes_equal=bool(equal),
        history_exact=plain.history == observed.history, status_exact=plain.status == observed.status,
        scope="actual solver with deterministic algebra normal; not a claim atomic sensor adjoints are bit deterministic",
        passed=bool(equal) and plain.history == observed.history and plain.status == observed.status and visited == expected)


def run(out):
    for path, sha in PINS.items():
        require(ref(path)["sha256"] == sha, "frozen helper changed: "+str(path))
    paths = [*PINS, HERE/"controls.py", HERE/"control-notes.md", HERE/"bands-gpu.py",
             HERE/"normal-operator.py", HERE/"solver.py", MANIFEST, BASELINE]
    before = [ref(p) for p in paths]
    t.set_num_threads(4); t.set_num_interop_threads(1); t.set_default_dtype(t.float32)
    t.backends.cuda.matmul.allow_tf32 = False; t.backends.cudnn.allow_tf32 = False
    require(t.cuda.is_available(), "CUDA unavailable")
    t.cuda.set_device(0)
    props = t.cuda.get_device_properties(0)
    t.cuda.set_per_process_memory_fraction(LIMIT/props.total_memory, 0); t.cuda.reset_peak_memory_stats(0)
    solver = load(HERE/"solver.py", "level_control_solver")
    normal, bands = solver.operator, solver.operator.bands
    fx = load(FIX/"fixtures.py", "fixtures")
    scores = load(FIX/"controls.py", "level_frozen_quality_scores")
    pair = load(OLD/"measurement-paired.py", "level_frozen_pair")
    delivery = load(OLD/"delivery.py", "level_frozen_delivery")
    legacy = load(OLD/"bands-gpu.py", "level_legacy_haar")
    algebra = load(OLD/"solver-controls.py", "level_frozen_algebra")
    manifest = json.loads(MANIFEST.read_text())
    for row in manifest["cases"]:
        if row["id"] in ("flat-neutral", "independent-colour", "fine-far"):
            paths.extend(Path(s["path"]) for s in row["sources"])
            paths.extend(Path(s["path"]) for s in [row["truth"], *row["templates"].values()])
    paths = list(dict.fromkeys(paths))
    before = [ref(p) for p in paths]
    baseline, baseline_receipt = scores.read_baselines(BASELINE, manifest, out)
    save(out/"baseline-bindings.json", baseline_receipt)
    results, runtime = [], []
    for case, mode in (("flat-neutral", "candidate"), ("independent-colour", "candidate"),
                       ("fine-far", "candidate"), ("fine-far", "no-focus")):
        row, originals = fx.load_case(manifest, case)
        noise = normal.Noise(tuple(float(v) for v in np.asarray(row["noise"]["gain_dn_per_e4"], np.float32)),
            tuple(float(v) for v in np.square(np.asarray(row["noise"]["gain_dn_per_e4"], np.float32)*np.asarray(row["noise"]["read_noise_e4"], np.float32))),
            (float(row["black"]),)*4, row["white"])
        original_refs = [hashlib.sha256(x.tobytes()).hexdigest() for x in originals]
        sources = []
        for item, codes in zip(row["sources"], originals):
            ar, ai, tx, ty = item["source_to_reference"]
            A = np.asarray([[ar, -ai], [ai, ar]], np.float64)
            offset = np.array([64., 64.])-A@np.array([64., 64.])+np.array([tx, ty])+8
            affine = np.column_stack((A, offset))
            sources.append(normal.Source(item["source_id"], (0, 0, 128, 128), affine, lambda x=codes: x))
        engine = pair.PairedMeasurementGpu(t, (144, 144), device_limit_bytes=LIMIT)
        problem = normal.StreamedProblem(t, (144, 144), sources, noise, mode=mode, measurement=engine)
        mechanics = normalization_controls(problem, normal, originals, noise, mode)
        fit = solver.fit(problem)
        name = case+"-"+mode; folder = out/name; folder.mkdir()
        fit_receipt = fit.save(folder/"fit")
        renderer = delivery.ReferenceDelivery(t, (144, 144), (-8, -8), device_limit_bytes=LIMIT)
        rgb = renderer.integrate(fit.x, (0, 0, 128, 128)).cpu().numpy()
        image = fx.array_ref(folder/"camera-rgb-dn.npy", rgb)
        preview = fx.preview(folder/"complete.png", rgb)
        score, old = scores.image_score(row, rgb), scores.image_score(row, baseline[case])
        quality = scores.quality_guard(case, score, old)
        numerical = dict(status=fit.status, converged=fit.converged, iterations=fit.iterations,
            full_normal_relative=fit.evidence["restored_full_normal_relative"],
            projected_normal_relative=fit.evidence["restored_projected_normal_relative"],
            objective_no_greater=fit.evidence["restored_objective_no_greater_than_initial"])
        e = fit.evidence
        literal_numerical = (all(v is not None and math.isfinite(v) and v <= 1e-5 for v in
            (e["restored_full_normal_relative"],e["restored_projected_normal_relative"]))
            and e["restored_objective_no_greater_than_initial"])
        contract = (e["maximum_iterations"] == 4 and e["normal_tolerance"] == 1e-5
            and e["preconditioner"] is None and e["restarts"] == 0 and 0 <= fit.iterations <= 4
            and len(fit.history) == fit.iterations+1 and e["restored_numerical_pass"] == literal_numerical
            and not e["quality_claim"] and not e["prior_photographic_admission"])
        unchanged = original_refs == [hashlib.sha256(x.tobytes()).hexdigest() for x in originals]
        results.append(dict(case=case, mode=mode, mechanics=mechanics, numerical=numerical,
            fit=fit_receipt, image=image, complete_preview=preview, score=score, baseline_score=old,
            quality_guard=quality, solver_contract=bool(contract), originals_unchanged=unchanged,
            source_sha256=original_refs, no_focus_is_placebo=(mode == "no-focus")))
        runtime.append(dict(name=name, measurement=engine.metadata(strict=True), delivery=renderer.metadata()))
        save(out/(name+"-result.json"), results[-1])
        print(json.dumps(dict(event="case-complete", case=case, mode=mode, quality_pass=quality["pass_guard"])), flush=True)
        del fit, problem, engine, renderer, sources, originals
    full_haar = haar_controls(bands, legacy); save(out/"haar-controls.json", full_haar)
    unsupported = unsupported_controls(normal); save(out/"unsupported-controls.json", unsupported)
    callback = callback_control(solver, algebra); save(out/"callback-controls.json", callback)
    quality_commission = scores.destroying_controls(manifest, out)
    save(out/"quality-guard-commission.json", quality_commission)
    after = [ref(p) for p in paths]
    require(before == after, "control dependency changed")
    memory = dict(allocated=t.cuda.max_memory_allocated(0), reserved=t.cuda.max_memory_reserved(0), limit=LIMIT)
    require(max(memory["allocated"], memory["reserved"]) <= LIMIT, "Torch memory bound")
    passed = (all(x["mechanics"]["passed"] and x["originals_unchanged"] and x["solver_contract"] for x in results)
              and full_haar["passed"] and unsupported["passed"] and callback["passed"] and quality_commission["pass_guard"])
    return dict(status="COMPLETE_LEVEL_BALANCED_CONTROLS", complete=True, all_cases_completed=True,
        controls_pass=passed, mechanical_pass=passed, quality_pass=all(x["quality_guard"]["pass_guard"] for x in results),
        quality_claim=False, photographic_admission=False, admission=False, RAW_reads=0,
        old_flat_quality_failure_retained=True, results=results, haar=full_haar,
        unsupported=unsupported, callback=callback, quality_guard_commission=quality_commission, runtime=runtime, memory=memory,
        dependencies_before=before, dependencies_after=after, dependencies_unchanged=True,
        source_cases=["flat-neutral", "independent-colour", "fine-far"], actual_fit_count=4,
        threads=t.get_num_threads(), interop_threads=t.get_num_interop_threads(), TF32=False, autocast=False,
        current_quality_flags_are_not_photographic_admission=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve()
    require(out.is_relative_to(ROOT/"outputs"), "workspace outputs required")
    out.mkdir(parents=True, exist_ok=False)
    try:
        with t.inference_mode(), t.autocast(device_type="cuda", enabled=False):
            receipt = run(out)
    except BaseException as error:
        save(out/"receipt.json", dict(status="INCOMPLETE_LEVEL_BALANCED_CONTROLS", complete=False,
            all_cases_completed=False, controls_pass=False, quality_claim=False, photographic_admission=False,
            error=repr(error), traceback=traceback.format_exc()))
        raise
    save(out/"receipt.json", receipt)


if __name__ == "__main__":
    main()
