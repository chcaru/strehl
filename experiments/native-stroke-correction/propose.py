"""One nominated saved-CFA sidecar proposal. No RAW reader or process launcher."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SAVED = ROOT / "experiments/native-background-stroke/run-1"
MAP = ROOT / "experiments/M-PHASE0-PHASE/out/canon/coffee-bean.warpmap.txt"
CENTRE = (414, 1630)
ORIGIN = (112, 1304)
SHAPE = (456, 640)
INDICES = (0, 26, 52, 78, 104)
TRAIN = (0, 104)
HELD = (26, 52, 78)
PHASES = {"R": (0, 0), "G1": (1, 0), "G2": (0, 1), "B": (1, 1)}
WHITE = np.float32(15360)  # Held production native.log; rawpy reports16383 instead.


def profile(x, y, centre=CENTRE):
    x, y = np.asarray(x, dtype=np.float32), np.asarray(y, dtype=np.float32)
    radius = np.hypot(x - np.float32(centre[0]), y - np.float32(centre[1]))
    angle = np.float32(np.pi / 64) * radius
    return np.where(radius < 32, np.cos(angle) ** 2, np.float32(0)).astype(np.float32)


def gain_map(amplitude, shape=SHAPE, origin=ORIGIN, centre=CENTRE):
    if not np.isfinite(amplitude) or not 0 <= amplitude <= .2:
        raise ValueError("amplitude outside[0,.2]; no clipping rescue")
    if any(v % 2 for v in (*shape, *origin)):
        raise ValueError("quad storage needs even origin and shape")
    qy, qx = np.mgrid[:shape[0]//2, :shape[1]//2].astype(np.float32)
    phi = profile(origin[0] + 2*qx + np.float32(.5), origin[1] + 2*qy + np.float32(.5), centre)
    return (np.float32(1) / (np.float32(1) - np.float32(amplitude)*phi)).astype(np.float32)


def apply_map(rawu16, black_by_phase, gainquad, white=WHITE):
    """Current dust-only sparse correction: original and restored white skip."""
    raw = np.asarray(rawu16)
    gain = np.asarray(gainquad, dtype=np.float32)
    if raw.dtype != np.uint16 or raw.shape != (2*gain.shape[0], 2*gain.shape[1]):
        raise ValueError("u16 CFA and matching quad gain required")
    blacks = np.asarray(black_by_phase, dtype=np.float32)
    if blacks.shape == (4,):
        blacks = blacks.reshape(2,2)
    if blacks.shape != (2, 2) or not np.isfinite(blacks).all():
        raise ValueError("black_by_phase must be a finite2x2 spatial matrix")
    if not np.isfinite(gain).all() or np.any(gain < 1) or np.any(gain > 1.25):
        raise ValueError("invalid stored gain")
    result = raw.copy()
    for dy in range(2):
        for dx in range(2):
            source = raw[dy::2, dx::2].astype(np.float32)
            black = blacks[dy, dx]
            restored = np.maximum(source-black, np.float32(0))*gain + black
            live = (gain > 1) & (source < white) & (restored < white)
            # Positive f32 round away from zero, followed by Rust's u16 saturation.
            rounded = np.floor(restored.astype(np.float64) + .5).clip(0, 65535).astype(np.uint16)
            result[dy::2, dx::2][live] = rounded[live]
    return result


def _plane(signal, phase, model, centre=CENTRE):
    source = np.asarray(signal, dtype=np.float32)
    if source.shape != SHAPE or not np.isfinite(source).all():
        raise ValueError("invalid saved-signal geometry or nonfinite signal")
    dx, dy = phase
    values = source[dy::2, dx::2]
    yy, xx = np.mgrid[:values.shape[0], :values.shape[1]].astype(np.float32)
    x = np.float32(ORIGIN[0]+dx-centre[0]) + 2*xx
    y = np.float32(ORIGIN[1]+dy-centre[1]) + 2*yy
    radius = np.hypot(x, y)
    ann = (radius >= 48) & (radius <= 80)
    # Scaled coordinates keep the fixed small least-squares system conditioned.
    x, y = x/np.float32(80), y/np.float32(80)
    cols = [np.ones_like(x), x, y]
    if model == "quadratic":
        cols.extend([x*x, x*y, y*y])
    elif model != "affine":
        raise ValueError("unknown background model")
    matrix = np.stack([v[ann] for v in cols], axis=1)
    coeff, _, rank, singular = np.linalg.lstsq(matrix, values[ann], rcond=None)
    if rank != len(cols):
        raise ValueError("background fit rank deficient")
    background = sum(c*v for c, v in zip(coeff, cols)).astype(np.float32)
    phi = profile(ORIGIN[0]+2*xx+np.float32(.5), ORIGIN[1]+2*yy+np.float32(.5), centre)
    support = phi > 0
    core = radius <= 16
    if not np.isfinite(background[ann | support]).all() or np.any(background[ann | support] <= 0):
        raise ValueError("nonpositive predicted background")
    residual = (values/background - np.float32(1)).astype(np.float32)
    weight = phi[support]
    numerator = float(np.sum(weight * -residual[support], dtype=np.float64))
    denominator = float(np.sum(weight*weight, dtype=np.float64))
    return {"values": values, "background": background, "phi": phi,
            "support": support, "core": core, "residual": residual,
            "coefficients": [float(v) for v in coeff],
            "amplitude": numerator/denominator,
            "core_deficit": -float(np.median(residual[core]))}


def fit_plane(signal2d, origin=ORIGIN, phase=(0, 0), centre=CENTRE, background_model="affine"):
    if tuple(origin) != ORIGIN:
        raise ValueError("this bounded fitter accepts only the saved patch origin")
    row = _plane(signal2d, phase, background_model, centre)
    return {k: row[k] for k in ("amplitude", "coefficients", "core_deficit")}


def evaluate(signals, amplitude, background_model="affine", centre=CENTRE, corrected_signals=None):
    reasons, records = [], []
    decision = {"amplitude": float(amplitude) if np.isfinite(amplitude) else None,
                "proceed": False, "reasons": reasons, "per_frame_phase": records}
    if set(signals) != set(INDICES):
        reasons.append("wrong-five-frame-population")
        return decision
    if not np.isfinite(amplitude) or not 0 < amplitude <= .2:
        reasons.append("amplitude-outside-positive-format-bound")
        return decision
    gain = gain_map(amplitude, centre=centre)
    try:
        for model in (background_model, "quadratic"):
            if model == "quadratic" and background_model == "quadratic" and records:
                continue
            for index in INDICES:
                signal = np.asarray(signals[index], dtype=np.float32)
                for name, phase in PHASES.items():
                    row = _plane(signal, phase, model, centre)
                    dx, dy = phase
                    values = (row["values"]*gain if corrected_signals is None else
                              np.asarray(corrected_signals[index], dtype=np.float32)[dy::2, dx::2])
                    after = (values/row["background"]-np.float32(1)).astype(np.float32)
                    support, core = row["support"], row["core"]
                    before = row["residual"]
                    rec = {"index": index, "phase": name, "model": model,
                        "core_deficit": row["core_deficit"],
                        "rmse_before": float(np.sqrt(np.mean(before[support]**2, dtype=np.float64))),
                        "rmse_after": float(np.sqrt(np.mean(after[support]**2, dtype=np.float64))),
                        "mean_before": float(np.mean(before[support], dtype=np.float64)),
                        "mean_after": float(np.mean(after[support], dtype=np.float64)),
                        "core_after": float(np.median(after[core])),
                        "mean_dn_before": float(np.mean(row["values"][support], dtype=np.float64)),
                        "mean_dn_after": float(np.mean(values[support], dtype=np.float64)),
                        "mean_dn_change": float(np.mean(values[support]-row["values"][support], dtype=np.float64)),
                        "background_coefficients": row["coefficients"],
                        "individual_amplitude": row["amplitude"]}
                    records.append(rec)
                    if index in HELD:
                        tag = f"{model}/{index}/{name}"
                        if rec["rmse_after"] > rec["rmse_before"]:
                            reasons.append(tag+":support-rmse-worse")
                        if abs(rec["mean_after"]) > abs(rec["mean_before"]):
                            reasons.append(tag+":support-absolute-mean-worse")
                        if rec["core_after"] > .010:
                            reasons.append(tag+":core-overbright")
            model_rows = [r for r in records if r["model"] == model]
            for name in PHASES:
                depths = [r["core_deficit"] for r in model_rows if r["phase"] == name]
                if sum(v >= .010 for v in depths) < 4:
                    reasons.append(f"{model}/{name}:not-present-four-of-five")
                if np.median(depths) < .015:
                    reasons.append(f"{model}/{name}:median-core-too-shallow")
    except (ValueError, np.linalg.LinAlgError) as error:
        reasons.append("fit-refused:"+str(error))
    decision["proceed"] = not reasons
    return decision


def fit_shared(signals, background_model="affine", centre=CENTRE):
    try:
        amplitudes = [_plane(signals[i], phase, background_model, centre)["amplitude"]
                      for i in TRAIN for phase in PHASES.values()]
        amplitude = float(np.mean(amplitudes, dtype=np.float64))
    except (ValueError, KeyError, np.linalg.LinAlgError) as error:
        return {"amplitude": None, "proceed": False, "reasons": ["training-fit-refused:"+str(error)],
                "per_frame_phase": []}
    decision = evaluate(signals, amplitude, background_model, centre)
    decision["training_amplitudes"] = amplitudes
    return decision


def binding(path):
    path = Path(path)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def sources():
    return [binding(p) for p in (Path(__file__), HERE/"charter.md", HERE/"design.md",
        HERE/"independent-controls.py", ROOT/"crates/strehl-core/src/defect_map.rs",
        ROOT/"crates/strehl-cli/src/stack.rs",
        ROOT/"experiments/native-background-stroke/sampler.py",
        ROOT/"experiments/M-PHASE0-PHASE/src/clib.py", MAP)]


def transforms():
    sampler = module("nominated_sampler", ROOT/"experiments/native-background-stroke/sampler.py")
    warp = sampler.clib.parse_warpmap(str(MAP))
    assert warp["frames"] == warp["placed_count"] == 105 and warp["reference_index"] == 52
    return {i: warp["placements"][i] for i in INDICES}


def controls(out):
    independent = module("nominated_independent", HERE/"independent-controls.py")
    result = independent.run(sys.modules[__name__], transforms())
    assert result["status"] == "PASS"
    save(out/"controls.json", {"sources": sources(), "result": result})


def load_saved():
    decode = read(SAVED/"decode-comparison.json")
    assert decode["all_identical"] and len(decode["rows"]) == 5
    raws, signals, bindings = {}, {}, [binding(SAVED/"decode-comparison.json")]
    for index in INDICES:
        path = SAVED/f"raw-{index}.npy"
        receipt_path = SAVED/f"primary-{index}.json"
        receipt = read(receipt_path)
        assert receipt["index"] == index and receipt["raw_roi_xywh"] == [*ORIGIN, SHAPE[1], SHAPE[0]]
        assert receipt["raw"] == binding(path)
        comparison = next(r for r in decode["rows"] if r["index"] == index)
        assert comparison["primary"] == receipt["raw"] and comparison["different_sensels"] == 0
        meta = receipt["decoder"]
        assert meta["raw_pattern"] == [[0,1],[3,2]] and meta["color_desc"] == "RGBG"
        blacks = np.array([[meta["black_level_per_channel"][c] for c in row]
                           for row in meta["raw_pattern"]], dtype=np.float32)
        assert np.all(blacks == 512), "held native black512 and source metadata must agree"
        raw = np.load(path, allow_pickle=False)
        assert raw.dtype == np.uint16 and raw.shape == SHAPE
        signal = raw.astype(np.float32)
        for dy in range(2):
            for dx in range(2):
                signal[dy::2,dx::2] -= blacks[dy,dx]
        raws[index], signals[index] = raw, signal
        bindings.extend([binding(path), binding(receipt_path)])
    return raws, signals, bindings


def map_text(gain):
    ys, xs = np.nonzero(gain > np.float32(1))
    qxs, qys = xs+ORIGIN[0]//2, ys+ORIGIN[1]//2
    rows = ["strehl-defect-map 2", "camera ILCE-7CM2", "sensor 7032 4688",
            f"covered {int(2*(qxs.max()+1))} {int(2*(qys.max()+1))}", "coords active", "aperture unknown",
            "# Stack-specific manual nomination; only listed sparse footprint measured.",
            "# Covered extent is an enclosing prefix required by format, not a calibrated flat field.",
            "# Saved exact-decoder-matched CFA patches; train0+104, held26+52+78; allfive visually seen.",
            "# Existing eight-frame runtime validation may refuse or rescale amplitude.",
            "# Current held CLI omits dust gain-squared variance propagation; causal visual test only.",
            "hot 0", f"dust {len(xs)}"]
    rows.extend(f"d {int(qx)} {int(qy)} {float(gain[y,x]):.9g}"
                for x,y,qx,qy in zip(xs,ys,qxs,qys))
    rows.append("end")
    return "\n".join(rows)+"\n"


def propose(out):
    control = read(out/"controls/controls.json")
    assert control["result"]["status"] == "PASS" and control["sources"] == sources()
    raws, signals, inputs = load_saved()
    fit = fit_shared(signals)
    clean = fit_shared(signals, centre=(414,1440))
    independent = module("nominated_independent", HERE/"independent-controls.py")
    moving = fit_shared(independent.scene_placebo(signals, transforms(), amplitude=.08))
    receipt = {"schema": "native-stroke-correction-proposal-v1", "sources": sources(), "inputs": inputs,
        "centre_active_native": CENTRE, "support_radius_native": 32, "annulus_native": [48,80],
        "training_indices": TRAIN, "numeric_heldout_indices": HELD, "all_five_visually_seen": True,
        "fitted_continuous_proposal": fit, "clean_proposal": clean, "scene_placebo": moving,
        "proceed_to_render": False, "map": None,
        "known_limitations": ["A manually nominated shape is not automatic dust detection.",
            "Eight-frame production validation independently rescales final amplitude.",
            "Held CLI does not propagate dust gain squared into injected variance."]}
    if fit["amplitude"] is not None and 0 < fit["amplitude"] <= .2:
        gain = gain_map(fit["amplitude"])
        corrected_signals, storage = {}, []
        support = np.repeat(np.repeat(gain > 1,2,axis=0),2,axis=1)
        for index in INDICES:
            raw = raws[index]
            corrected = apply_map(raw, np.full((2,2),512,dtype=np.float32), gain)
            assert np.array_equal(corrected[~support], raw[~support])
            corrected_signals[index] = corrected.astype(np.float32)-np.float32(512)
            new_clip = 0
            for dy in range(2):
                for dx in range(2):
                    s = raw[dy::2,dx::2].astype(np.float32)
                    restored = np.maximum(s-512,np.float32(0))*gain+512
                    new_clip += int(np.count_nonzero((gain>1) & (s<WHITE) & (restored>=WHITE)))
            storage.append({"index": index, "changed_sensels": int(np.count_nonzero(raw != corrected)),
                            "outside_support_identical": True, "restoration_white_skips": new_clip})
        rounded = evaluate(signals, fit["amplitude"], corrected_signals=corrected_signals)
        receipt["rounded_proposal"] = rounded
        receipt["storage"] = storage
        receipt["proceed_to_render"] = (rounded["proceed"] and not clean["proceed"] and not moving["proceed"] and
            all(r["restoration_white_skips"] == 0 for r in storage) and
            all(r["changed_sensels"] > 0 for r in storage))
        if receipt["proceed_to_render"]:
            path = out/"nominated-map.txt"
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(map_text(gain))
            receipt["map"] = binding(path)
    save(out/"proposal.json", receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("controls","propose"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.stage == "controls":
        args.out.mkdir(parents=True, exist_ok=False)
        controls(args.out)
    else:
        assert args.out.is_dir()
        propose(args.out)
    assert sum(p.stat().st_size for p in args.out.rglob("*") if p.is_file()) <= 64 << 20


if __name__ == "__main__":
    main()
