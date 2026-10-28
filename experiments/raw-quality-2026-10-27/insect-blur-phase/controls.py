"""Independent fixed BIPC screen; root schedules execution, no corpus pixels."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import struct
import sys
import time
import traceback

import numpy as np
import scipy
from scipy.special import j1
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCER = HERE / "phase.py"
MAP = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline/alignment.txt"
MAP_SHA = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"
LIMIT = 4 << 30
ERROR_BAR = .10  # Euclidean native sensor pixels, every declared positive.
ADVANTAGE_ERROR = .20
SHIFTS = ((.625, -.375), (-1.375, .8125), (1.125, 1.625))
RUNG_IDS = (0, 49, 99, 149, 199, 249, 298)
PHASES = {"G1": (4001, 2400), "G2": (4000, 2401)}
GAIN = np.float32(.22893773)
READ_E = np.float32(4.2)
READ_DN = np.float32(GAIN * READ_E)
READ_VARIANCE = np.float32(READ_DN * READ_DN)
BLACK, WHITE, DC = 512., 15360., 4096.
# Independent continuous scene: physical cycles/native-pixel, not an FFT shift.
LOW = np.asarray(((8, 3), (4, 14), (18, -3), (-9, 12)), np.float64) / 256.
HIGH = np.asarray(((35, 7), (29, 27), (-25, 31), (9, 43), (41, -11),
                   (33, -25), (-13, 45), (-37, -17), (19, -39), (45, 5),
                   (-43, 13), (23, 37), (39, 21), (5, -47), (-31, 35),
                   (17, 43)), np.float64) / 256.
FREQUENCIES = np.concatenate((LOW, HIGH))
AMPLITUDES = np.asarray([35.] * 4 + [180.] * 16, np.float64)
ANGLES = np.mod(np.arange(20, dtype=np.float64) * 2.399963229728653 + .31, 2*np.pi)


def require(ok, why):
    if not ok:
        raise ValueError(why)


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def plain(value):
    if torch.is_tensor(value):
        return plain(value.detach().cpu().numpy())
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def source_track():
    require(ref(MAP)["sha256"] == MAP_SHA, "held map bytes changed")
    lines = MAP.read_text(encoding="utf-8").splitlines()
    for line in ("frames 299", "plane 3516x2344", "reference 149", "resampler catmull-rom"):
        require(line in lines, "held map header: " + line)
    maps, positions = [], []
    point, center = np.asarray((4650., 2680.)), np.asarray((3516., 2344.))
    for line in lines:
        parts = line.split("#", 1)[0].split()
        if not parts or not parts[0].isdigit():
            continue
        require(len(parts) == 6 and parts[1] == "placed" and int(parts[0]) == len(maps),
                "complete placed map order")
        ar, ai, bx, by = [struct.unpack("<d", struct.pack("<Q", int(s, 16)))[0] for s in parts[2:]]
        a = np.asarray(((ar, -ai), (ai, ar)))
        positions.append(center + a @ (point-center) + 2*np.asarray((bx, by)))
        maps.append(parts[2:])
    require(len(maps) == 299, "299 map rows")
    positions = np.asarray(positions)
    shifts = positions - positions[149]
    chord = positions[0] + np.arange(299)[:, None]/298.*(positions[-1]-positions[0])
    deviation = np.linalg.norm(positions-chord, axis=1)
    require(float(np.max(deviation)) > 0 and float(np.max(np.linalg.norm(shifts, axis=1))) > 5,
            "nonlinear nontrivial held-track plant")
    return shifts, {"map": ref(MAP), "reference": 149, "source_ids": list(RUNG_IDS),
                    "native_point": point.tolist(), "native_center": center.tolist(),
                    "guide_to_native_pitch": 2, "all299_track_positions_native": positions.tolist(),
                    "max_departure_from_endpoint_chord_native": float(np.max(deviation)),
                    "input_f64_bits": maps, "physical_calibration": False,
                    "interpretation": "Saved estimated-map curvature reused as a synthetic plant only"}


def transfer(freq, psf):
    radial = np.linalg.norm(freq, axis=1)
    kind, size = psf
    if kind == "gaussian":
        return np.exp(-2*np.pi**2*size**2*radial**2).astype(np.complex128)
    if kind == "disk":
        z = 2*np.pi*size*radial
        return np.where(z == 0, 1., 2*j1(z)/np.where(z == 0, 1., z)).astype(np.complex128)
    if kind == "asymmetric":
        return (.75 + .25*np.exp(-2j*np.pi*(freq @ np.asarray((3., -2.)))))
    raise ValueError("unknown analytic PSF")


def field(origin, shift=(0., 0.), psf=("gaussian", .35), *, kind="structured",
          matrix=None, far=False):
    """Exact continuous Fourier transfer and source-square integration in f64."""
    yy, xx = np.mgrid[:128, :128]
    xy = np.stack((origin[0]+2*xx-4000., origin[1]+2*yy-2400.), axis=-1)
    if kind == "flat":
        return np.full((128, 128), DC, np.float64)
    freq, amp, phase = FREQUENCIES.copy(), AMPLITUDES.copy(), ANGLES.copy()
    if kind == "rank-x":
        freq, amp, phase = np.asarray(((.15625, 0.),)), np.asarray((900.,)), np.asarray((.31,))
    elif kind == "rank-y":
        freq, amp, phase = np.asarray(((0., .15625),)), np.asarray((900.,)), np.asarray((.31,))
    elif kind == "nonperiodic":
        freq = freq + np.asarray((.37, -.23))/256.
    elif kind == "branch":
        # Every x index is odd: a128-native shift changes all AC signs exactly.
        freq = HIGH.copy()
        amp, phase = np.full(16, 180.), ANGLES[4:].copy()
    if far:
        phase = phase + np.linspace(.6, 2.2, len(phase))
    a = np.eye(2) if matrix is None else np.asarray(matrix, np.float64)
    center = np.asarray((127.5, 127.5))
    q = (xy-center-np.asarray(shift)) @ a.T + center
    # A acts on physical sample positions; source-cell frequencies are A^T f.
    source_freq = freq @ a
    cell = np.sinc(source_freq[:, 0])*np.sinc(source_freq[:, 1])
    coefficient = amp * cell * transfer(source_freq, psf) * np.exp(1j*phase)
    angle = 2*np.pi*np.einsum("...d,kd->...k", q, freq)
    return DC + np.real(np.exp(1j*angle) @ coefficient)


def acquire(signal, seed, noisy=True):
    require(np.isfinite(signal).all() and float(signal.min()) >= 0, "finite positive analytic scene")
    variance = float(GAIN)*signal + float(READ_VARIANCE)
    disturbance = np.random.default_rng(seed).normal(size=signal.shape)*np.sqrt(variance) if noisy else 0.
    raw = np.rint(signal + BLACK + disturbance)
    require(float(raw.min()) >= 0 and float(raw.max()) < WHITE, "no synthetic clipping")
    return raw.astype(np.uint16)


def error_record(arm, truth):
    measured = arm.get("displacement_native_xy")
    error = None if measured is None else float(np.linalg.norm(np.asarray(measured)-truth))
    return {"accepted": bool(arm["accepted"]), "native_error": error,
            "bar_native": ERROR_BAR,
            "passed": bool(arm["accepted"] and error is not None and error <= ERROR_BAR)}


def specifications(shifts):
    cases = []
    for phase in PHASES:
        cases.append(dict(name="flat-exact-"+phase, phase=phase, kind="flat", noisy=False, policy="refuse"))
    for phase in PHASES:
        cases.append(dict(name="flat-noise-"+phase, phase=phase, kind="flat", policy="refuse"))
    for phase, kind in (("G1", "rank-x"), ("G2", "rank-y")):
        cases.append(dict(name=kind, phase=phase, kind=kind, policy="refuse"))
    for n, delta in enumerate(SHIFTS):
        for phase in PHASES:
            cases.append(dict(name=f"gaussian-{n}-{phase}", phase=phase, shift=delta,
                              moving_psf=("gaussian", 1.1), policy="both-positive"))
    for n, delta in enumerate(SHIFTS[:2]):
        for phase in PHASES:
            cases.append(dict(name=f"disk-{n}-{phase}", phase=phase, shift=delta,
                              moving_psf=("disk", 5.), policy="disk-positive"))
    for i in RUNG_IDS:
        for phase in PHASES:
            cases.append(dict(name=f"track-{i}-{phase}", phase=phase, shift=shifts[i].tolist(),
                              follow_origin=True, moving_psf=("disk", 5.), policy="track-positive", source_id=i))
    for phase in PHASES:
        cases.extend((dict(name="adverse-asymmetric-"+phase, phase=phase, moving_psf=("asymmetric", 0), policy="adverse"),
                      dict(name="adverse-window-"+phase, phase=phase, kind="nonperiodic", shift=SHIFTS[0],
                           moving_psf=("disk", 5.), policy="adverse"),
                      dict(name="adverse-similarity-"+phase, phase=phase, shift=SHIFTS[0],
                           similarity=True, moving_psf=("disk", 5.), policy="adverse"),
                      dict(name="adverse-depth-"+phase, phase=phase, mixed_depth=True, policy="adverse")))
    for seed in (0, 128):
        cases.append(dict(name=f"branch-seed-{seed}", phase="G1", kind="branch", shift=(128., 0.),
                          noisy=False, seed=(seed, 0), policy="branch"))
    return cases


def run(out):
    started = time.perf_counter()
    out.mkdir(parents=True, exist_ok=False)
    bindings = [ref(p) for p in (Path(__file__), HERE/"controls-protocol.md", HERE/"brief.md", PRODUCER, MAP)]
    require(torch.cuda.is_available(), "CUDA required by bounded screen")
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.set_per_process_memory_fraction(LIMIT/torch.cuda.get_device_properties(0).total_memory, 0)
    torch.cuda.reset_peak_memory_stats()
    module = load(PRODUCER, "insect_blur_phase_frozen")
    reader = module.Reader(torch, device="cuda")
    noise = module.PhaseNoise(gain=float(GAIN), read_variance=float(READ_VARIANCE), black=BLACK, white=WHITE)
    shifts, track = source_track()
    save(out/"track-plant.json", track)
    records, references, failures = [], [], []
    for ordinal, spec in enumerate(specifications(shifts)):
        phase = spec["phase"]
        origin_ref = PHASES[phase]
        truth = np.asarray(spec.get("shift", (0., 0.)), np.float64)
        origin_delta = (2*np.rint(truth/2.)).astype(np.int64) if spec.get("follow_origin") else np.zeros(2, np.int64)
        origin_mov = tuple(int(origin_ref[k]+origin_delta[k]) for k in (0, 1))
        kind = spec.get("kind", "structured")
        reference = field(origin_ref, kind=kind)
        moving_matrix = None
        if spec.get("similarity"):
            theta = .012
            moving_matrix = np.asarray(((math.cos(theta), -math.sin(theta)),
                                        (math.sin(theta), math.cos(theta)))) / 1.008
        moving = field(origin_mov, truth, spec.get("moving_psf", ("gaussian", .35)), kind=kind, matrix=moving_matrix)
        if spec.get("mixed_depth"):
            reference = .5*field(origin_ref, psf=("gaussian", .35)) + .5*field(origin_ref, psf=("disk", 5.), far=True)
            moving = .5*field(origin_mov, psf=("disk", 5.)) + .35*field(origin_mov, psf=("gaussian", .35), far=True) + .15*DC
        reference = acquire(reference, 71000+2*ordinal, spec.get("noisy", True))
        moving = acquire(moving, 71001+2*ordinal, spec.get("noisy", True))
        directory = out/spec["name"]
        directory.mkdir()
        for name, array in (("reference", reference), ("moving", moving)):
            path = directory/(name+".npy")
            np.save(path, array, allow_pickle=False)
            references.append(ref(path))
        before = (reference.tobytes(), moving.tobytes())
        result = plain(reader.compare(reference, moving, noise, seed_native_xy=tuple(spec.get("seed", (0, 0))),
                                      phase=phase, reference_origin_native_xy=origin_ref,
                                      moving_origin_native_xy=origin_mov, return_surfaces=True))
        require(before == (reference.tobytes(), moving.tobytes()), "producer changed original u16 arrays")
        for arm in ("p1", "p2"):
            surface = np.asarray(result[arm].pop("score_surface"), dtype=np.float32)
            require(surface.shape == (257,257) and np.isfinite(surface).all(), "complete producing score surface")
            path = directory/(arm+"-score-surface.npy")
            np.save(path, surface, allow_pickle=False)
            result[arm]["score_surface_file"] = ref(path)
            references.append(ref(path))
        scores = {arm: error_record(result[arm], truth) for arm in ("p1", "p2")}
        policy = spec["policy"]
        passed = (not result["p1"]["accepted"] and not result["p2"]["accepted"]) if policy == "refuse" else (
            all(s["passed"] for s in scores.values()) if policy == "both-positive" else (
                scores["p2"]["passed"] if policy in ("disk-positive", "track-positive") else None))
        if passed is False:
            failures.append(spec["name"])
        record = dict(specification=spec, truth_native=truth.tolist(), reference_origin_native=list(origin_ref),
                      moving_origin_native=list(origin_mov), producer=result, scores=scores, required_pass=passed,
                      adverse_admitted_errors={a: s["native_error"] for a, s in scores.items() if s["accepted"] and not s["passed"]},
                      interpretation="Out-of-model adversities never certify physical motion" if policy == "adverse" else None)
        save(directory/"result.json", record)
        references.append(ref(directory/"result.json"))
        records.append(record)
        print(spec["name"], "required_pass", passed, "p1/p2 errors", scores["p1"]["native_error"], scores["p2"]["native_error"], flush=True)

    by_name = {r["specification"]["name"]: r for r in records}
    batch_names = ("gaussian-0-G1", "disk-0-G1")
    batch_reference = np.stack([np.load(out/name/"reference.npy", allow_pickle=False) for name in batch_names])
    batch_moving = np.stack([np.load(out/name/"moving.npy", allow_pickle=False) for name in batch_names])
    batch_before = (batch_reference.tobytes(), batch_moving.tobytes())
    batch = plain(reader.compare_batch(batch_reference, batch_moving, noise, phase="G1", seed_native_xy=(0,0),
                                       reference_origin_native_xy=PHASES["G1"], moving_origin_native_xy=PHASES["G1"],
                                       return_surfaces=True))
    require(batch_before == (batch_reference.tobytes(), batch_moving.tobytes()), "batch changed input arrays")
    require(len(batch) == 2, "complete batch population")
    batch_checks = []
    for name, observed in zip(batch_names, batch):
        original = by_name[name]["producer"]
        for arm in ("p1", "p2"):
            surface = np.asarray(observed[arm].pop("score_surface"), np.float32)
            old_surface = np.load(original[arm]["score_surface_file"]["path"], allow_pickle=False)
            require(surface.shape == old_surface.shape and np.isfinite(surface).all(), "finite batch surface")
            maximum = float(np.max(np.abs(surface-old_surface)))
            exact_fields = ("accepted", "refusals", "displacement_native_xy", "patch_displacement_native_xy", "peak_grid_yx")
            decision_exact = all(observed[arm][key] == original[arm][key] for key in exact_fields)
            batch_checks.append(dict(name=name, arm=arm, decision_exact=decision_exact,
                                     surface_max_error=maximum, surface_bar=2e-6,
                                     passed=decision_exact and maximum <= 2e-6))
    batch_pass = all(row["passed"] for row in batch_checks)
    save(out/"batch-parity.json", dict(passed=batch_pass, checks=batch_checks, producing_results=batch))
    references.append(ref(out/"batch-parity.json"))
    if not batch_pass:
        failures.append("batch-singleton-parity")
    disk = [r for r in records if r["specification"]["policy"] == "disk-positive"]
    advantage = any(not r["scores"]["p1"]["accepted"] or
                    (r["scores"]["p1"]["native_error"] is not None and r["scores"]["p1"]["native_error"] >= ADVANTAGE_ERROR)
                    for r in disk)
    if not advantage:
        failures.append("no-distinct-disk-advantage")
    positive = by_name["gaussian-0-G1"]
    actual = positive["producer"]["p2"].get("displacement_native_xy")
    truth = np.asarray(positive["truth_native"])
    foil_scores = {}
    for name, multiplier in (("wrong-sign", -1), ("missing-factor-two", 2)):
        changed_arm = dict(positive["producer"]["p2"])
        changed_arm["displacement_native_xy"] = None if actual is None else (multiplier*np.asarray(actual)).tolist()
        foil_scores[name] = error_record(changed_arm, truth)
    foils = {name: positive["scores"]["p2"]["passed"] and not score["passed"]
             for name, score in foil_scores.items()}
    track_rows = [r for r in records if r["specification"]["policy"] == "track-positive"]
    ignored_origin = [float(np.linalg.norm(np.asarray(r["producer"]["p2"]["patch_displacement_native_xy"])-r["truth_native"]))
                      for r in track_rows if r["producer"]["p2"].get("patch_displacement_native_xy") is not None]
    foils["ignored-physical-origin"] = bool(ignored_origin and max(ignored_origin) > 5.)
    try:
        reader.compare(np.full((128,128), 4608, np.uint16), np.full((128,128), 4608, np.uint16), noise,
                       phase="G1", reference_origin_native_xy=(4000,2400), moving_origin_native_xy=(4000,2400))
        foils["wrong-green-physical-phase"] = False
    except ValueError:
        foils["wrong-green-physical-phase"] = True
    b0, b128 = by_name["branch-seed-0"], by_name["branch-seed-128"]
    alias_local = error_record(b0["producer"]["p2"], np.asarray((0., 0.)))
    branch = dict(local_alias_accepted=alias_local["passed"], valid_seed_recovers=b128["scores"]["p2"]["passed"],
                  wrong_seed_fails_physical_truth=not b0["scores"]["p2"]["passed"],
                  interpretation="UNIDENTIFIABLE_WITHOUT_VALID_BRANCH_SEED", automatic_global_ambiguity_detection=False)
    branch["passed"] = branch["local_alias_accepted"] and branch["valid_seed_recovers"] and branch["wrong_seed_fails_physical_truth"]
    if not branch["passed"]:
        failures.append("half-period-producing-branch")
    failures.extend("foil-"+key for key, passed in foils.items() if not bool(passed))
    after = [ref(row["path"]) for row in bindings]
    require(after == bindings, "bound source or held map changed")
    peaks = dict(allocated=torch.cuda.max_memory_allocated(), reserved=torch.cuda.max_memory_reserved())
    require(max(peaks.values()) <= LIMIT, "Torch allocator limit")
    receipt = dict(status="COMPLETE_INSECT_BLUR_PHASE_CONTROLS", complete=True, all_cases_completed=True,
                   controls_pass=not failures, failures=failures, quality_claim=False, photographic_admission=False,
                   source_bindings=bindings, source_bindings_unchanged=True, artifacts=references+[ref(out/"track-plant.json")],
                   source_count=0, RAW_reads=0, original_corpus_pixels_read=False, case_count=len(records),
                   case_results=[{"name": r["specification"]["name"], "policy": r["specification"]["policy"],
                                  "required_pass": r["required_pass"], "scores": r["scores"],
                                  "adverse_admitted_errors": r["adverse_admitted_errors"]} for r in records],
                   disk_advantage_present=advantage, scorer_foils={k: bool(v) for k,v in foils.items()},
                   scorer_foil_scores=foil_scores, branch_control=branch, batch_singleton_parity=batch_pass,
                   reader_metadata=plain(reader.metadata()),
                   noise={"gain_dn_per_e": float(GAIN), "read_noise_e": float(READ_E),
                          "read_variance_dn2": float(READ_VARIANCE), "black": BLACK, "white": WHITE,
                          "acquisition": "one Gaussian shot/read draw before nearest-u16 rounding; no added rounding floor"},
                   scene={"frequencies_cycles_per_native_pixel": FREQUENCIES.tolist(), "amplitudes_DN": AMPLITUDES.tolist(),
                          "phases_radians": ANGLES.tolist(), "disk_radius_native": 5.,
                          "disk_transfer": transfer(FREQUENCIES, ("disk", 5.)).real.tolist(),
                          "analytic_generator": "continuous f64 Fourier/OTF plus exact unit-square sinc; producer f32, storageu16"},
                   bounds={"positive_error_native": ERROR_BAR, "p1_advantage_error_native": ADVANTAGE_ERROR},
                   runtime={"torch_version": torch.__version__, "numpy_version": np.__version__,
                            "scipy_version":scipy.__version__, "device": torch.cuda.get_device_name(0), "threads":4, "interop":1,
                            "tf32":False, "torch_peak_bytes":peaks, "wall_seconds":time.perf_counter()-started})
    save(out/"receipt.json", receipt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.out)
    except Exception:
        traceback.print_exc()
        raise
