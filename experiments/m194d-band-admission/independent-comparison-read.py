"""Read all 120 real TIFFs; reuse commissioned independent optics/moments.

Prospective choices: fixed native ROI by literal indices; Gaussian quadrature
cell targets and numerical pupil integration; Welford temporal variance;
repeat-level paired SEM/jackknife; nearest-rank p99.9; >10 DN paired harm and
improvement counts; historical red site (142,170), all flat full9 repeats.
These descriptive choices supplement the frozen root metrics, not new bars.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXED = HERE.parent / "m194b-known-scene"
PREVIOUS = HERE.parent / "m194c-probe-layout"
BASELINE = PREVIOUS / "candidate-2/run/run-index.json"
BASELINE_SHA = "71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab"
SEEDS = [701, 709, 719, 727, 733, 739, 743, 751]
MODES = ["hard-floor", "floor-pedestal-v1"]


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--controller", type=Path, required=True)
    p.add_argument("--controller-sha", required=True)
    p.add_argument("--comparison", type=Path, required=True)
    p.add_argument("--comparison-sha", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    assert not args.out.exists()
    hashes = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        digest = sha(path)
        assert expected is None or digest == expected, f"hash mismatch: {path}"
        assert str(path) not in hashes or hashes[str(path)] == digest
        hashes[str(path)] = digest
        return path

    def bound(ref, base=ROOT):
        return load(bind(base / ref["path"], ref["sha256"]))

    sources = {}
    for path, commit in [(FIXED / "independent-optics.py", "444eb759"),
                         (PREVIOUS / "independent-comparison-controls.py", "04128e")]:
        original = subprocess.check_output(["git", "show", commit + ":" + path.relative_to(ROOT).as_posix()], cwd=ROOT)
        assert sha(path) == hashlib.sha256(original).hexdigest()
        sources[str(path)] = sha(path)
    optics = module("m194d_independent_optics", FIXED / "independent-optics.py")
    stats = module("m194d_independent_moments", PREVIOUS / "independent-comparison-controls.py")
    controller = load(bind(args.controller, args.controller_sha))
    authored = load(bind(args.comparison, args.comparison_sha))
    assert controller["status"] == "complete" and set(controller["modes"]) == set(MODES)
    assert authored["controller_sha256"] == args.controller_sha
    historical = load(bind(BASELINE, BASELINE_SHA))
    indices = {"archive": (historical, BASELINE)}
    for mode in MODES:
        ref = controller["modes"][mode]["index"]
        indices[mode] = (bound(ref), Path(ref["path"]))
    expected = {(s, n, a) for s in ("flat", "plane") for n in [None] + SEEDS for a in ("full9", "single4")}
    expected |= {(s, None, a) for s in ("color", "color-null") for a in ("full9", "single4")}
    arrays, file_hashes, signatures = {}, {}, {}

    def normalized_plan(plan, mode):
        v = copy.deepcopy(plan)
        assert v["crop_quad"] == dict(x=9, y=7, width=142, height=106)
        assert v["output_native"] == [284, 212] and v["canonical_native_offset"] == [18, 14]
        assert v["normalization"] == dict(tiff_u16_to_dn=14848 / 65535, second_black_subtraction=False)
        assert v.pop("schema") == ("m194b-consumer-plan-v1" if mode == "archive" else "m194d-consumer-plan-v1")
        if mode != "archive":
            assert v["environment"].pop("STREHL_M194D_ADMISSION") == mode
            assert v["config"].pop("admission") == ("HardFloor" if mode == MODES[0] else "FloorPedestalV1")
            formula = v["config"].pop("admission_formula")
            assert formula == ("hard-floor-v1" if mode == MODES[0] else
                               "floor-pedestal-v1: q=max(E-F,0); w=(hypot(q/max(F,1),1)/64)^p")
        else:
            assert "admission" not in v["config"] and "admission_formula" not in v["config"]
        v.pop("software")  # Build context is independently bound; TIFF bytes must still match off/archive.
        return v

    for mode, (index, index_path) in indices.items():
        assert index["status"] == "complete"
        if mode != "archive":
            assert index["admission"] == mode and index["build_record"] == controller["build_record"]
        for case in index["cases"]:
            plan = load(bind(index_path.parent / case["plan_path"], case["plan_sha256"]))
            signature = normalized_plan(plan, mode)
            manifest_path = bind(index_path.parent / case["manifest_path"], case["manifest_sha256"])
            manifest = load(manifest_path)
            for frame in manifest["frames"]:
                path = bind(manifest_path.parent / frame["path"], frame["sha256"])
                assert path.stat().st_size == frame["bytes"]
            for arm in case["arms"]:
                key = (case["scene"], case["repeat"], arm["name"])
                assert key in expected and (mode, key) not in arrays
                if mode == "archive":
                    signatures[key] = (case["manifest_sha256"], signature)
                else:
                    assert signatures[key] == (case["manifest_sha256"], signature), f"unregistered plan difference: {key}"
                receipt = load(bind(index_path.parent / arm["receipt_path"], arm["receipt_sha256"]))
                assert receipt["plan"] == plan and receipt["plan_sha256"] == case["plan_sha256"]
                path = bind(receipt["output"]["path"], receipt["output"]["sha256"])
                pixels = tifffile.imread(path)
                assert pixels.dtype == np.uint16 and pixels.shape == (212, 284, 3)
                assert hashlib.sha256(pixels.astype("<u2", copy=False).tobytes()).hexdigest() == receipt["output"]["pixel_sha256_le"]
                arrays[(mode, key)] = pixels
                file_hashes[(mode, key)] = sha(path)
        assert {k for m, k in arrays if m == mode} == expected
    off_identity = [file_hashes[("archive", key)] == file_hashes[(MODES[0], key)]
                    and np.array_equal(arrays[("archive", key)], arrays[(MODES[0], key)]) for key in expected]
    assert all(off_identity), "off-mode differs from the archived baseline"
    x, y = np.meshgrid(np.arange(64, 256, dtype=float), np.arange(64, 176, dtype=float))
    nodes, weights = np.polynomial.legendre.leggauss(32)
    scalar = np.array([.75 * float(np.float32(4/3)), 1., .6 * float(np.float32(5/3))]) * .25

    def wave(amplitude, fx, fy, phase, kind):
        if kind == "observation":
            offsets = (np.arange(4) + .5) / 4 - .5
            cell = sum(np.exp(2j * np.pi * (fx*a + fy*b)) for a in offsets for b in offsets) / 16
            transfer = optics.pupil_overlap(np.hypot(fx, fy), 5.12 / (.535 * 16))
        else:
            cell = sum(wa*wb*np.exp(1j*np.pi*(fx*a + fy*b)) for a, wa in zip(nodes, weights)
                       for b, wb in zip(nodes, weights)) / 4
            transfer = 1.
        return amplitude * transfer * np.real(cell * np.exp(1j * (2*np.pi*(fx*x + fy*y) + phase)))

    def target(scene, kind):
        if scene == "flat":
            return np.full((*x.shape, 3), 12000.) * scalar
        if scene == "plane":
            return (12000 + wave(1800, 1/16, 1/24, .2, kind) + wave(900, 1/8, -1/16, 1.1, kind))[..., None] * scalar
        lum = 3000 + wave(450, .08, .03, .2, kind) + wave(180, .19, -.07, 1.1, kind)
        c = wave(240, .11, .04, .8, kind) if scene == "color" else 0
        q = wave(120, .05, -.09, 2., kind) if scene == "color" else 0
        return np.stack([lum+c, lum+q, lum-c], axis=-1)

    def dn(mode, key):
        return arrays[(mode, key)].astype(float) * 14848 / 65535

    roi = lambda a: a[50:162, 46:238]
    root_rows = {(r["scene"], r["repeat"], r["arm"]): r for r in authored["rows"]}
    assert set(root_rows) == expected
    maximum = dict(pixel=0., rmse=0., wave=0., sparse=0., variance=0., paired_mean=0., paired_sem=0., jackknife=0.)
    rows, paired, triggers, historical_site = [], [], [], []
    for key in sorted(expected, key=str):
        a_full, b_full = dn(MODES[1], key), dn(MODES[0], key)
        a, b = roi(a_full), roi(b_full)
        delta = a_full - b_full
        rd = a - b
        authored_row = root_rows[key]
        assert authored_row["pixels"]["changed_components"] == int(np.count_nonzero(delta))
        assert authored_row["pixels"]["roi_changed_components"] == int(np.count_nonzero(rd))
        pixel_rms = np.sqrt(np.einsum("yxc,yxc->c", rd, rd) / (112*192))
        maximum["pixel"] = max(maximum["pixel"], float(np.max(abs(pixel_rms - authored_row["pixels"]["roi_rms_delta_dn_by_channel"]))))
        peak = np.unravel_index(np.argmax(abs(delta)), delta.shape)
        peak_y, peak_x, peak_c = [int(v) for v in peak]
        item = dict(scene=key[0], repeat=key[1], arm=key[2], changed_components=int(np.count_nonzero(delta)),
                    roi_pixel_rms_dn=pixel_rms.tolist(), whole_image_maximum=dict(native_xy=[peak_x+18, peak_y+14],
                    channel="RGB"[peak_c], signed_movement_dn=float(delta[peak]),
                    inside_fixed_roi=bool(64 <= peak_x+18 < 256 and 64 <= peak_y+14 < 176)))
        for kind in (["ideal", "observation"] if key[0] in ("flat", "plane") else ["ideal"]):
            truth = target(key[0], kind)
            d = stats.difference(b, a, truth)
            maximum["rmse"] = max(maximum["rmse"], float(np.max(abs(d["rmse_dn"] - authored_row[kind+"_rmse_change_dn"]))))
            old_error, new_error = b-truth, a-truth
            harm = abs(new_error) - abs(old_error)
            order = int(np.ceil(.999 * x.size)) - 1
            tail = lambda z: np.partition(abs(z).reshape(-1, 3), order, axis=0)[order]
            item[kind] = {name: value.tolist() for name, value in d.items()}
            item[kind].update(nearest_rank_p999_before_dn=tail(old_error).tolist(),
                              nearest_rank_p999_after_dn=tail(new_error).tolist(),
                              harmed_over10_dn=(harm > 10).sum(axis=(0, 1)).tolist(),
                              improved_over10_dn=(harm < -10).sum(axis=(0, 1)).tolist(),
                              moved_over10_dn=(abs(rd) > 10).sum(axis=(0, 1)).tolist(),
                              maximum_paired_error_increase_dn=harm.max(axis=(0, 1)).tolist(),
                              maximum_paired_error_decrease_dn=harm.min(axis=(0, 1)).tolist())
            for ch, authored_ch in enumerate(authored_row[kind+"_sparse_change"]["channels"]):
                for field, expected_extreme in (("maximum_absolute_error_change", np.max(harm[..., ch])),
                                                 ("minimum_absolute_error_change", np.min(harm[..., ch]))):
                    point = authored_ch[field]
                    px, py = point["native_xy"]
                    assert 64 <= px < 256 and 64 <= py < 176
                    value = harm[py-64, px-64, ch]
                    maximum["sparse"] = max(maximum["sparse"], abs(float(value - expected_extreme)),
                                             abs(float(value - point["absolute_error_change_dn"])))
            if max(d["rmse_dn"]) > 1:
                triggers.append((key, kind, "rmse"))
        if key[0] == "plane":
            waves = []
            for i, (fx, fy) in enumerate([(1/16, 1/24), (1/8, -1/16)]):
                pa, pb = stats.wave_projection(a, fx, fy), stats.wave_projection(b, fx, fy)
                amplitude, phase = abs(pa)-abs(pb), np.angle(pa*np.conj(pb))
                maximum["wave"] = max(maximum["wave"], float(np.max(abs(amplitude - authored_row["wave_amplitude_change_dn"][i]))))
                waves.append(dict(amplitude_change_dn=amplitude.tolist(), phase_change_rad=phase.tolist()))
                if key[1] is None and min(amplitude) < -1:
                    triggers.append((key, i, "wave"))
            item["waves"] = waves
        if key[0] == "flat" and key[1] in SEEDS and key[2] == "full9":
            truth = target("flat", "ideal")[106, 78, 0]
            historical_site.append(dict(repeat=key[1], native_xy=[142, 170], channel="R",
                                        before_dn=float(b[106, 78, 0]), after_dn=float(a[106, 78, 0]), truth_dn=float(truth),
                                        absolute_error_change_dn=float(abs(a[106, 78, 0]-truth)-abs(b[106, 78, 0]-truth))))
        rows.append(item)
    for scene in ("flat", "plane"):
        for arm in ("full9", "single4"):
            aa = np.stack([roi(dn(MODES[1], (scene, seed, arm))) for seed in SEEDS])
            bb = np.stack([roi(dn(MODES[0], (scene, seed, arm))) for seed in SEEDS])
            av, bv = stats.temporal_variance(aa), stats.temporal_variance(bb)
            vd, ratio = av-bv, av/bv
            if max(ratio) > 1.02:
                triggers.append(((scene, arm), None, "variance"))
            for kind in ("ideal", "observation"):
                truth = target(scene, kind)
                each = np.stack([stats.difference(b, a, truth)["mse_dn2"] for a, b in zip(aa, bb)])
                mean = each.sum(axis=0) / 8
                sem = np.sqrt(((each-mean)**2).sum(axis=0) / (8*7))
                loo = np.stack([stats.temporal_variance(np.delete(aa, i, axis=0)) -
                                stats.temporal_variance(np.delete(bb, i, axis=0)) for i in range(8)])
                jack = np.sqrt(7/8 * ((loo-loo.mean(axis=0))**2).sum(axis=0))
                r = next(r for r in authored["paired"] if (r["scene"], r["arm"], r["target"]) == (scene, arm, kind))["difference"]
                for name, value, field in [("variance", vd, "temporal_variance_difference_dn2"),
                                            ("paired_mean", mean, "mean_mse_difference_dn2"),
                                            ("paired_sem", sem, "mse_difference_sem_dn2"),
                                            ("jackknife", jack, "variance_difference_jackknife_se_dn2")]:
                    maximum[name] = max(maximum[name], float(np.max(abs(value-r[field]))))
                paired.append(dict(scene=scene, arm=arm, target=kind, mse_difference_dn2=mean.tolist(),
                                   mse_difference_sem_dn2=sem.tolist(), temporal_variance_difference_dn2=vd.tolist(),
                                   variance_ratio=ratio.tolist(), variance_jackknife_se_dn2=jack.tolist()))
    checks = dict(complete_120_actual_tiffs=len(arrays) == 120, all40_off_whole_tiff_and_pixels_identical=all(off_identity),
                  same_actual_inputs_and_narrow_plan_delta=True,
                  engineering_trigger_count_agrees=len(triggers) == len(authored["engineering_review_triggers"]),
                  original_artifact_bytes_unchanged=all(sha(p) == h for p, h in hashes.items()),
                  reused_independent_source_bytes_unchanged=all(sha(p) == h for p, h in sources.items()))
    for name, error in maximum.items():
        checks[name+"_agreement"] = error < (.001 if name in ("rmse", "sparse", "paired_mean", "paired_sem") else 1e-8)
    result = dict(schema="m194d-independent-comparison-read-v1", pass_=all(checks.values()), checks=checks,
                  command=__import__("sys").argv, script_sha256=sha(__file__), reused_sources=sources,
                  controller_sha256=args.controller_sha, comparison_sha256=args.comparison_sha,
                  max_disagreements=maximum, rows=rows, paired=paired, historical_site=historical_site,
                  independent_engineering_triggers=triggers,
                  scope="same-input software-model differences; repeat uncertainty only; no calibration, occlusion or SOTA admission")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf8", newline="\n") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps(dict(pass_=result["pass_"], checks=checks, max_disagreements=maximum, triggers=triggers)))
    assert result["pass_"]


if __name__ == "__main__":
    main()
