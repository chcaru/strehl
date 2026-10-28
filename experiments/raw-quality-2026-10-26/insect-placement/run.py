"""Frozen two-gap placement observation; no registration optimization or warp output."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import struct
import subprocess
import time

for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "4"

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
SECONDARY = Path("C:/dev/blog/death-of-software/projects/strehl/experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe")
MAP_SHA = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"
ORDER_SHA = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f"
INDICES = (104, 105, 106)
ORIGIN = np.array([4528., 2544.])
CENTERS = {"A": np.array([4770., 2807.]), "B": np.array([4680., 2813.])}
PHASES = {"G1": (1, 0), "G2": (0, 1)}
OFFSETS = np.arange(-16, 16.001, .25, dtype=np.float32)
GAIN = np.float32(100/436.8)
READ2 = np.float32(4.20*GAIN)**np.float32(2)
BLACK = np.float32(512.)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1 << 20), b""):
            h.update(data)
    return h.hexdigest()


def save(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def fresh(path):
    path = path.resolve()
    assert path.is_relative_to(ROOT) and not path.exists() and path.parent.is_dir()
    path.mkdir()
    return path


def transforms():
    p = BASE/"alignment.txt"
    assert sha(p) == MAP_SHA
    result = {}
    for line in p.read_text().splitlines():
        fields = line.split()
        if fields and fields[0].isdigit() and int(fields[0]) in INDICES:
            assert fields[1] == "placed"
            a, r, x, y = [struct.unpack(">d", bytes.fromhex(v))[0] for v in fields[2:6]]
            result[int(fields[0])] = (complex(a, r), complex(x, y))
    assert len(result) == 3
    return result


def stage(out):
    import rawpy
    out = fresh(out)
    order_path = BASE/"input-order.json"
    assert sha(order_path) == ORDER_SHA
    order = json.loads(order_path.read_text())
    transforms()
    nomination = json.loads((HERE/"nomination.json").read_text())
    for item in nomination["viewed_sources"]:
        assert sha(item["path"]) == item["sha256"], "nominated image changed"
    records = []
    for index in INDICES:
        src = order[index]
        p = Path(src["path"])
        assert sha(p) == src["sha256"] and p.stat().st_mtime_ns == src["mtime_ns"]
        print("DECODE_START", index, flush=True)
        with rawpy.imread(str(p)) as raw:
            assert raw.raw_pattern.tolist() == [[0, 1], [3, 2]]
            assert raw.raw_image_visible.dtype == np.uint16
            patch = raw.raw_image_visible[2544:3056, 4528:5040].copy()
            metadata = {"active_shape": list(raw.raw_image_visible.shape),
                        "black": list(raw.black_level_per_channel), "white": raw.white_level,
                        "sizes": str(raw.sizes)}
        assert patch.shape == (512, 512)
        dest = out/f"source-{index}.npy"
        np.save(dest, patch, allow_pickle=False)
        assert sha(p) == src["sha256"] and p.stat().st_mtime_ns == src["mtime_ns"]
        records.append({"index": index, "original": src, "cache": str(dest), "cache_sha256": sha(dest), "metadata": metadata})
        print("DECODE_COMPLETE", index, flush=True)
    command = [str(SECONDARY), order[105]["path"], str(out), "105", "2544", "4528", "512", "512"]
    print("INDEPENDENT_DECODE_START", 105, flush=True)
    proc = subprocess.run(command, capture_output=True, text=True, timeout=40)
    (out/"independent-decode.log").write_text(proc.stdout+proc.stderr, encoding="utf-8")
    assert proc.returncode == 0
    blob = (out/"rawler-105.bin").read_bytes()
    assert struct.unpack("<4I", blob[:16]) == (2544, 4528, 512, 512)
    independent = np.frombuffer(blob, dtype="<u2", offset=16).reshape(512, 512)
    assert np.array_equal(independent, np.load(out/"source-105.npy", allow_pickle=False))
    for row in records:
        src = row["original"]; p = Path(src["path"])
        assert sha(p) == src["sha256"] and p.stat().st_mtime_ns == src["mtime_ns"]
    save(out/"cache.json", {"status": "THREE_ORIGINALS_CACHED_ONE_INDEPENDENT_REDECODE", "records": records,
        "origin_native": ORIGIN.tolist(), "shape": [512, 512], "script_sha256": sha(__file__),
        "map_sha256": MAP_SHA, "order_sha256": ORDER_SHA,
        "nomination_sha256": sha(HERE/"nomination.json"),
        "independent_command": command, "independent_executable_sha256": sha(SECONDARY), "independent_differing_sensels": 0,
        "rawpy_version": rawpy.__version__, "originals_hash_mtime_unchanged": True})
    print("CACHE_COMPLETE", out, flush=True)


def query(center, axis, t, phase):
    a105, b105 = t[105]
    ai, bi = t["index"]
    normal = np.array([1., 0.]) if axis == "x" else np.array([0., 1.])
    tangent = normal[::-1]
    points = center + OFFSETS[:, None]*normal + np.array([-2., 0., 2.])[:, None, None]*tangent
    z = points[..., 0]/2 + 1j*points[..., 1]/2
    c = complex(1758., 1172.)
    mapped = ai*((z-c-b105)/a105)+bi+c
    xy = np.stack([2*mapped.real, 2*mapped.imag], -1)-ORIGIN
    dx, dy = phase
    uv = (xy-np.array([dx, dy]))/2
    lower = np.floor(uv).astype(np.int32)
    fraction = (uv-lower).astype(np.float32)
    assert np.all(lower >= 0) and np.all(lower+1 < 256)
    indices, weights = [], []
    for oy in (0, 1):
        for ox in (0, 1):
            ix = 2*(lower[..., 0]+ox)+dx
            iy = 2*(lower[..., 1]+oy)+dy
            fx, fy = fraction[..., 0], fraction[..., 1]
            indices.append(iy*512+ix)
            weights.append((fx if ox else 1-fx)*(fy if oy else 1-fy))
    return np.stack(indices), np.stack(weights).astype(np.float32)


def profile(data, query_tuple):
    indices, weights = query_tuple
    values = np.sum(data.reshape(-1)[indices].astype(np.float32)*weights, axis=0, dtype=np.float32)
    return np.mean(values, axis=0, dtype=np.float32)


def edges(values):
    center = float(np.median(values[np.abs(OFFSETS) <= 1]))
    answers = []
    for side in (-1, 1):
        outside = (OFFSETS*side >= 12) & (OFFSETS*side <= 16)
        shoulder = float(np.median(values[outside]))
        if shoulder-center < 30:
            raise ValueError("insufficient fixed-window gap contrast")
        threshold = .5*(shoulder+center)
        signed = (values-threshold)*side
        crossed = np.flatnonzero((signed[:-1] <= 0) & (signed[1:] > 0)
            & (OFFSETS[:-1]*side >= 1) & (OFFSETS[:-1]*side <= 10))
        if len(crossed) != 1:
            raise ValueError(f"{len(crossed)} signed crossings in fixed side{side} window")
        k = crossed[0]
        pos = float(OFFSETS[k] + .25*(-signed[k])/(signed[k+1]-signed[k]))
        answers.append(pos)
    return np.array(answers, dtype=np.float32)


def extract(data, plans):
    result, profiles, refusals = {}, {}, {}
    for key, plan in plans.items():
        values = profile(data, plan)
        profiles[key] = values
        try:
            result[key] = edges(values)
        except ValueError as error:
            refusals[key] = str(error)
    return result, profiles, refusals


def plans_for(t, index):
    t = dict(t); t["index"] = t[index]
    return {f"{feature}/{phase}/{axis}": query(center, axis, t, parity)
        for feature, center in CENTERS.items() for phase, parity in PHASES.items() for axis in ("x", "y")}


def plant(shift=(0., 0.), width=3., glint=False):
    y, x = np.indices((512, 512), dtype=np.float32)
    data = np.full((512, 512), np.float32(1600.))
    for name, center in CENTERS.items():
        cx, cy = center-ORIGIN+np.array(shift)
        data -= np.float32(900.)*np.exp(np.float32(-.5)*(((x-cx)/width)**2+((y-cy)/width)**2))
        if glint and name == "A":
            data += np.float32(1200.)*np.exp(np.float32(-.5)*(((x-cx-7)/2)**2+((y-cy-1)/3)**2))
    return data.astype(np.float32)


def common_motion(rows, all_valid):
    """The same candidate-evidence gate is exercised by controls and real data."""
    admitted = bool(all_valid) and all(v["sides_consistent"] for v in rows.values())
    vector = []
    for axis in ("x", "y"):
        keys = [f"{f}/{p}/{axis}" for f in CENTERS for p in PHASES]
        if not all(k in rows for k in keys):
            admitted = False; vector.append(0.); continue
        nominated = rows[keys[0]]
        for key in keys[1:]:
            held = rows[key]
            admitted &= abs(held["delta_center"]-nominated["delta_center"]) <= .20+3*np.hypot(held["sigma"], nominated["sigma"])
        vector.append(nominated["delta_center"])
    significant = any(abs(rows.get(f"A/G1/{axis}", {}).get("delta_center", 0)) > .20+3*rows.get(f"A/G1/{axis}", {}).get("sigma", 1e6) for axis in ("x", "y"))
    return bool(admitted and significant and np.linalg.norm(vector) >= .35), vector


def control_motion(base, current, refusals):
    rows = {}
    for key, value in current.items():
        delta = value-base[key]
        rows[key] = {"delta_center": float(np.mean(delta)), "sigma": 0.,
            "sides_consistent": abs(float(np.diff(delta)[0])) <= .20}
    return common_motion(rows, not refusals)


def controls():
    t = {i: (1+0j, 0j) for i in INDICES}
    plans = plans_for(t, 105)
    flat = np.full((512, 512), np.float32(1600.))
    _, _, refused = extract(flat, plans)
    assert len(refused) == len(plans), "flat invented boundaries"
    y, x = np.indices((512, 512), dtype=np.float32)
    ramp = 100+x+2*y
    ramp[0::2, 0::2] = -2000; ramp[1::2, 1::2] = 9000
    for phase in PHASES:
        for axis in ("x", "y"):
            key = f"A/{phase}/{axis}"
            actual = profile(ramp, plans[key])
            c = CENTERS["A"]-ORIGIN
            truth = 100+c[0]+2*c[1]+OFFSETS*(1 if axis == "x" else 2)
            assert np.max(np.abs(actual-truth)) < .002
    wrong = ramp.copy(); wrong[0::2, 1::2] += 800
    assert np.min(np.abs(profile(wrong, plans["A/G1/x"])-profile(ramp, plans["A/G1/x"]))) > 799
    base, _, reject = extract(plant(), plans); assert not reject
    moved, _, reject = extract(plant((.75, -.5)), plans); assert not reject
    wide, _, reject = extract(plant(width=4.5), plans); assert not reject
    translation_errors, width_center_errors = [], []
    for key in plans:
        delta = float(np.mean(moved[key]-base[key]))
        truth = .75 if key.endswith("/x") else -.5
        translation_errors.append(abs(delta-truth))
        width_center_errors.append(abs(float(np.mean(wide[key]-base[key]))))
        assert abs(delta-truth) <= .25, (key, delta)
        assert width_center_errors[-1] <= .20
        assert float(np.diff(wide[key])[0]-np.diff(base[key])[0]) > 2
    glint, _, glint_refusals = extract(plant(glint=True), plans)
    glint_centers = {k: float(np.mean(v-base[k])) for k, v in glint.items()}
    # A glint cannot qualify as common translation of both independent features.
    assert all(abs(v) < .01 for k,v in glint_centers.items() if k.startswith("B/"))
    assert control_motion(base, moved, {})[0], "known translation failed the actual motion gate"
    assert not control_motion(base, wide, {})[0], "stationary defocus passed the actual motion gate"
    assert not control_motion(base, glint, glint_refusals)[0], "stationary glint change passed the actual motion gate"
    return {"status": "CONTROLS_PASSED", "flat_all_refused": True, "phase_ramp_and_wrong_phase_passed": True,
        "translated_center_max_error": max(translation_errors), "stationary_defocus_center_max_error": max(width_center_errors),
        "glint_center_offsets": glint_centers, "glint_refusals": glint_refusals,
        "actual_motion_gate_exercised": True,
        "limits": "Known analytic plants only; no real optical correspondence or sensor calibration established."}


def measure(cache, out):
    cache = cache.resolve(); manifest = json.loads((cache/"cache.json").read_text())
    assert manifest["script_sha256"] == sha(__file__) and manifest["map_sha256"] == MAP_SHA
    assert manifest["nomination_sha256"] == sha(HERE/"nomination.json")
    arrays = {}
    for row in manifest["records"]:
        p = Path(row["cache"]); assert sha(p) == row["cache_sha256"]
        arrays[row["index"]] = np.load(p, allow_pickle=False)
        assert arrays[row["index"]].dtype == np.uint16 and arrays[row["index"]].shape == (512, 512)
    out = fresh(out)
    start = time.monotonic()
    print("CONTROLS_START", flush=True)
    try:
        ctl = controls()
    except Exception as error:
        save(out/"result.json", {"status": "STOP_CONTROL_FAILED", "terminal": True, "error": repr(error), "full_pair_admitted": False})
        raise
    save(out/"controls.json", ctl)
    print("CONTROLS_COMPLETE", flush=True)
    t = transforms(); records = {}; rng = np.random.default_rng(261026)
    for index in INDICES:
        plans = plans_for(t, index)
        data = arrays[index]
        observed, profiles, refusals = extract(data, plans)
        replicas = {k: [] for k in plans}
        sigma = np.sqrt(GAIN*np.maximum(data.astype(np.float32)-BLACK, 0)+READ2).astype(np.float32)
        if any(np.max(data.reshape(-1)[q[0]]) >= 15360 for q in plans.values()):
            refusals["clipping"] = "profile stencil includes a product-white-or-higher sensel"
        for replicate in range(64):
            noisy = data.astype(np.float32) + rng.normal(size=data.shape).astype(np.float32)*sigma
            rr, _, _ = extract(noisy, plans)
            for key, values in rr.items():
                replicas[key].append(values.tolist())
            assert time.monotonic()-start <= 60, "numerical wall cap exceeded"
        values = {}
        for key in plans:
            sample = np.asarray(replicas[key], dtype=np.float32)
            if key not in observed or len(sample) < 48:
                refusals[key] = refusals.get(key, "fewer than48 valid noise replicas")
                continue
            values[key] = {"edges": observed[key].tolist(), "center": float(np.mean(observed[key])),
                "width": float(np.diff(observed[key])[0]), "replicas": len(sample),
                "edge_sigma": np.std(sample, axis=0, ddof=1).tolist(),
                "center_sigma": float(np.std(np.mean(sample, axis=1), ddof=1))}
        records[index] = {"values": values, "refusals": refusals,
            "profiles": {k: v.tolist() for k,v in profiles.items()}}
        print("SOURCE_PROFILES_COMPLETE", index, "refusals", len(refusals), flush=True)
    comparisons = {}
    for index in (104, 106):
        rows = {}; admitted = not records[index]["refusals"] and not records[105]["refusals"]
        for key, baseline in records[105]["values"].items():
            if key not in records[index]["values"]:
                admitted = False; continue
            current = records[index]["values"][key]
            edge_delta = np.asarray(current["edges"])-baseline["edges"]
            sigma = float(np.hypot(current["center_sigma"], baseline["center_sigma"]))
            width_sigma = float(np.sqrt(np.sum(np.square(current["edge_sigma"])+np.square(baseline["edge_sigma"]))))
            same_side_motion = abs(float(np.diff(edge_delta)[0])) <= 3*width_sigma+.20
            rows[key] = {"delta_center": float(np.mean(edge_delta)), "delta_width": float(np.diff(edge_delta)[0]),
                         "delta_edges": edge_delta.tolist(), "sigma": sigma, "sides_consistent": same_side_motion}
            admitted &= same_side_motion
        admitted, vector = common_motion(rows, admitted)
        source_delta = (t[index][0]/t[105][0])*complex(*vector)
        comparisons[index] = {"conditional_candidate_evidence": bool(admitted), "source105_native_delta": vector,
            "source_i_native_pull_delta": [source_delta.real, source_delta.imag], "profiles": rows}
    assert time.monotonic()-start <= 60
    save(out/"result.json", {"status": "FIXED_PROFILE_OBSERVATION_COMPLETE", "terminal": True,
        "full_pair_admitted": False, "requires_independent_profile_review": True, "records": records,
        "comparisons": comparisons, "offsets_native": OFFSETS.tolist(), "elapsed_numerical_seconds": time.monotonic()-start,
        "noise_model": {"gain_dn_per_e": float(GAIN), "read_noise_e": 4.20, "black": 512, "replicas": 64, "scope": "injected baseline model; not measured temporal uncertainty"},
        "gauge": "source105 native via exact globalreference149 pulls, physical G1/G2 separate",
        "cache_manifest_sha256": sha(cache/"cache.json"), "script_sha256": sha(__file__)})
    print("MEASUREMENT_COMPLETE", json.dumps({k:v["conditional_candidate_evidence"] for k,v in comparisons.items()}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("stage", "measure"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    args = parser.parse_args()
    if args.mode == "stage":
        stage(args.out)
    else:
        assert args.cache is not None
        measure(args.cache, args.out)
