"""Frozen independent directional challenge against the actual M189 v2 metric."""
from __future__ import annotations

import os
THREAD_KEYS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
for key in THREAD_KEYS:
    os.environ[key] = "1"

import copy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
sys.dont_write_bytecode = True

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE.parent / "M189-noise-colour-detail/metric_v2.py"
EXPECTED_SOURCE = "104f7414ce70c245af0f4d14475047c05565084ca60c4daaf2ca1ad486bc831e"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SOURCE
sys.path.insert(0, str(SOURCE.parent))
from metric_v2 import measure

SIDE, PAIRS, BATCHES = 256, 16, 8
GAIN, READ, LEVEL, AMPLITUDE = 0.221113, 1.2392, 8000.0, 600.0
INDICES = np.array([68, 71, 74])
PHASES = np.array([0.2, 1.1, 2.4])
FREQ = INDICES / SIDE
SIGMAS = {"base": 0.85, "optical_improved": 0.45, "optical_degraded": 1.30}
OUT = HERE / "out"


def file_record(path):
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def save(name, value):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True,
                                      allow_nan=False) + "\n", encoding="utf-8")


def summary(values):
    a = np.asarray(values, dtype=np.float64)
    mean, sd = float(a.mean()), float(a.std(ddof=1))
    sem = sd / np.sqrt(a.size)
    return {"values": a.tolist(), "mean": mean, "sd": sd, "sem": float(sem),
            "lower_3sem": float(mean - 3 * sem), "upper_3sem": float(mean + 3 * sem)}


def observe(scene, a, b):
    sigma = np.sqrt(GAIN * scene + (GAIN * READ) ** 2)
    return scene + sigma * a, scene + sigma * b


def stencil(image, axis=-1, amount=0.75):
    return (1 + amount) * image - 0.5 * amount * (
        np.roll(image, 1, axis=axis) + np.roll(image, -1, axis=axis))


def measure_pair(pair):
    return measure(*pair, gain_dn_per_e=GAIN, read_noise_e=READ).to_dict()


def make_scene(sigma, gains=None):
    gains = np.ones(3) if gains is None else gains
    amplitudes = AMPLITUDE * np.exp(-2 * np.pi**2 * sigma**2 * FREQ**2) * gains
    row = LEVEL + np.sum(amplitudes[:, None] * np.cos(
        2 * np.pi * FREQ[:, None] * np.arange(SIDE)[None, :] + PHASES[:, None]), axis=0)
    return np.broadcast_to(row, (SIDE, SIDE)).copy()


def population():
    """No image FFT and no candidate: harmonic powers plus mode-averaged noise."""
    fy = np.fft.fftfreq(SIDE)[:, None]
    fx = np.fft.fftfreq(SIDE)[None, :]
    radius = np.sqrt(fx**2 + fy**2)
    edges = np.linspace(0.12, 0.30, 37)
    masks = [(radius >= a) & (radius < b) for a, b in zip(edges[:-1], edges[1:])]
    mode_count = sum(int(m.sum()) for m in masks)
    kx = np.broadcast_to(1 + 0.75 * (1 - np.cos(2 * np.pi * fx)), radius.shape)
    ky = kx.T
    blur = np.broadcast_to(0.5 * (1 + np.cos(2 * np.pi * fx)), radius.shape)
    transfers = {"sharpen_x": kx, "sharpen_y": ky, "post_blur": blur}
    noise_gains = {name: [float(np.mean(k[m]**2)) for m in masks]
                   for name, k in transfers.items()}
    optical = {name: (SIDE**2 * AMPLITUDE**2 / 2) *
               np.exp(-4 * np.pi**2 * sigma**2 * FREQ**2)
               for name, sigma in SIGMAS.items()}
    base = float(optical["base"].sum() / mode_count)
    scores = {name: float(power.sum() / mode_count) for name, power in optical.items()}
    raw_ratios = {}
    for name, k in transfers.items():
        raw = float(np.sum(optical["base"] * k[0, INDICES]**2) / mode_count)
        scores[name] = raw / max(1.0, max(noise_gains[name]))
        raw_ratios[name] = raw / base
    scores["identity"] = base
    return {"licensed_modes": mode_count, "scores": scores,
            "score_ratios": {key: val/base for key, val in scores.items()},
            "raw_ratios": raw_ratios, "radial_noise_gains": noise_gains,
            "sharpen_x_scene_power_gains": (kx[0, INDICES]**2).tolist(),
            "sharpen_x_cell_power_max": float(np.max(kx[(radius >= .12) & (radius < .30)]**2))}


def predicates(result):
    ratios = result["score_ratio_summaries"]
    raw = result["raw_ratio_summaries"]
    noise = result["noise_gain_summaries"]
    return {
        "identity": all(abs(x - 1) <= 1e-12 for x in ratios["identity"]["values"]),
        "physical_improvement": ratios["optical_improved"]["lower_3sem"] > 1.05,
        "physical_degradation": ratios["optical_degraded"]["upper_3sem"] < .95,
        "post_blur": ratios["post_blur"]["upper_3sem"] < .95,
        "optical_noise_null": all(.97 <= noise[n]["lower_3sem"] and
                                  noise[n]["upper_3sem"] <= 1.03 for n in SIGMAS),
        "sharpen_intervened": raw["sharpen_x"]["lower_3sem"] > 1.05 and
                               noise["sharpen_x"]["lower_3sem"] > 1.05,
        "perpendicular_placebo": ratios["sharpen_y"]["upper_3sem"] < .95 and
            .97 <= raw["sharpen_y"]["lower_3sem"] and raw["sharpen_y"]["upper_3sem"] <= 1.03,
    }


def main():
    assert (OUT / "reproduction-check.json").exists(), "Reproduce first"
    reproduction = json.loads((OUT / "reproduction-check.json").read_text())
    assert all(reproduction["numerical_payload_exact"].values())
    files = [SOURCE, HERE / "preregistration.md", Path(__file__), HERE / "reproduce.py"]
    before = {str(p.relative_to(ROOT)): file_record(p) for p in files}
    metadata = {"argv": sys.argv, "working_directory": str(Path.cwd()),
        "python": platform.python_version(), "python_executable": sys.executable,
        "numpy": np.__version__, "thread_environment": {k: os.environ[k] for k in THREAD_KEYS},
        "captures_opened": 0, "source_before": before,
        "head_before": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()}
    save("source-freeze.json", metadata)

    # FIRST candidate calls in this challenge are flat/null, prior to scene scoring.
    flat_records = []
    for j in range(BATCHES):
        a = np.random.default_rng(189200 + 2*j).standard_normal((PAIRS, SIDE, SIDE))
        b = np.random.default_rng(189201 + 2*j).standard_normal((PAIRS, SIDE, SIDE))
        pair = observe(np.full((SIDE, SIDE), LEVEL), a, b)
        flat_records.append({"flat": measure_pair(pair),
            "sharpened_flat": measure_pair(tuple(stencil(x) for x in pair)),
            "correlated_sabotage": measure_pair((pair[0], pair[0].copy()))})
    flat = {name: summary([r[name]["score"] for r in flat_records])
            for name in flat_records[0]}
    flat_predicates = {name: abs(flat[name]["mean"]) + 3*flat[name]["sem"] < 100
                       for name in ("flat", "sharpened_flat")}
    flat_predicates["specificity_power"] = flat["correlated_sabotage"]["lower_3sem"] > 100
    save("flat-first.json", {"measurements": flat_records, "score_summaries": flat,
                              "predicates": flat_predicates})
    print("FLAT-FIRST:", json.dumps(flat_predicates), flush=True)
    assert all(flat_predicates.values()), "Flat control failed; detail arms NOT RUN"

    expected = population()
    scenes = {name: make_scene(sigma) for name, sigma in SIGMAS.items()}
    assert all(512 < x.min() and x.max() < 15500 for x in scenes.values())
    transfer_at_scene = 1 + .75 * (1 - np.cos(2*np.pi*FREQ))
    stencil_error = float(np.max(np.abs(stencil(scenes["base"]) -
                                       make_scene(SIGMAS["base"], transfer_at_scene))))
    assert stencil_error < 1e-8, stencil_error
    assert np.ptp(transfer_at_scene) > .01, "Fixture needs varying transfer"
    records = []
    for j in range(BATCHES):
        a = np.random.default_rng(189200 + 2*j).standard_normal((PAIRS, SIDE, SIDE))
        b = np.random.default_rng(189201 + 2*j).standard_normal((PAIRS, SIDE, SIDE))
        base_pair = observe(scenes["base"], a, b)
        batch = {"base": measure_pair(base_pair),
                 "identity": measure_pair(tuple(x.copy() for x in base_pair))}
        for name in ("optical_improved", "optical_degraded"):
            batch[name] = measure_pair(observe(scenes[name], a, b))
        batch["sharpen_x"] = measure_pair(tuple(stencil(x) for x in base_pair))
        batch["sharpen_y"] = measure_pair(tuple(stencil(x, axis=-2) for x in base_pair))
        batch["post_blur"] = measure_pair(tuple(stencil(x, amount=-.5) for x in base_pair))
        records.append(batch)
        print(f"BATCH {j}: sharpen_x/base={batch['sharpen_x']['score']/batch['base']['score']:.9f}", flush=True)
    names = tuple(records[0])
    result = {"schema": "m189b-directional-detail-v1", "metadata": metadata,
        "fixture": {"side": SIDE, "pairs_per_batch": PAIRS, "batches": BATCHES,
                    "indices": INDICES.tolist(), "phases": PHASES.tolist(), "sigmas": SIGMAS,
                    "gain": GAIN, "read": READ, "level": LEVEL, "amplitude": AMPLITUDE,
                    "seed_pairs": [[189200+2*j, 189201+2*j] for j in range(BATCHES)]},
        "measurements": records, "population": expected, "stencil_error_dn": stencil_error,
        "flat_summary": flat,
        "score_ratio_summaries": {n: summary([r[n]["score"]/r["base"]["score"] for r in records])
                                  for n in names},
        "raw_ratio_summaries": {n: summary([r[n]["raw_coherent_power"]/r["base"]["raw_coherent_power"]
                                           for r in records]) for n in names},
        "noise_gain_summaries": {n: summary([r[n]["weighted_noise_gain"] for r in records]) for n in names},
        "max_bin_gain_summaries": {n: summary([r[n]["bin_gain_max"] for r in records]) for n in names}}
    checks = predicates(result)
    result["controls"] = checks
    assert all(checks.values()), checks
    mutations = {}
    for arm, gate in (("optical_improved", "physical_improvement"),
                       ("optical_degraded", "physical_degradation"), ("post_blur", "post_blur")):
        mutant = copy.deepcopy(result)
        mutant["score_ratio_summaries"][arm] = summary([1.0]*BATCHES)
        mutations[gate] = not predicates(mutant)[gate]
    assert all(mutations.values()), mutations
    result["checker_mutation_rejections"] = mutations
    interval = result["score_ratio_summaries"]["sharpen_x"]
    result["candidate_safety"] = ("RED_DIRECTIONAL_COUNTEREXAMPLE" if interval["lower_3sem"] > 1.01 else
                                 "GREEN_THIS_FIXTURE_ONLY" if interval["upper_3sem"] <= 1.01 else "INCONCLUSIVE")
    after = {str(p.relative_to(ROOT)): file_record(p) for p in files}
    assert before == after, "Frozen source changed during run"
    result["source_after"] = after
    save("results.json", result)
    for name, s in result["score_ratio_summaries"].items():
        print(f"{name}/base mean={s['mean']:.9f} SEM={s['sem']:.9f} population={expected['score_ratios'][name]:.9f}")
    print("CONTROLS:", json.dumps(checks))
    print("CANDIDATE:", result["candidate_safety"])
    print("SOURCE_HASHES: unchanged")


if __name__ == "__main__":
    main()
