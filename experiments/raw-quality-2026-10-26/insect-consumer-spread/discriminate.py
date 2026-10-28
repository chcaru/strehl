"""One frozen bristle: original/gather green versus exact CA-off sensor collapse.

Root executes. No RAW decoder, alignment implementation, reconstruction or tuning.
The positive three-tap fit describes sampled-image transfer, not a physical PSF.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-baseline"
SENSOR = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/sensor-master.tiff"
SENSOR_SHA = "fa5825b834121b28547fc6e2154623740a24acc4e1616915c1c197bc90be2b02"
SIDECAR_SHA = "e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21"
COMPANION = ROOT / "outputs/raw-quality-2026-10-26/weevil-source143-gather-ca-off/capture.json"
COMPANION_SHA = "880c376fb0d52631d9e8ac2f67da8d92800c7290bcf63d6cee0eccd4d0d5ccfd"
DECODE = ROOT / "outputs/raw-quality-2026-10-26/source143-gather-job-1/independent-decode.json"
DECODE_SHA = "79d00e9982d2df520c22dad6f392647043ef9665c192d80d9a9b845597a02359"
NOMINATION_SHA = "da2dae3d77c6321b67281865eba25b20c08056abeb47f4dab2f74c004b36c1bb"
CAPTURE_SHA = "b453d78399ad2ce7e0d50eef25326c29e177d28d025a956c298f0ee045578d69"
MAP_SHA = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225"
ORDER_SHA = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f"
EXE_SHA = "89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388"
RECT = (1920, 748, 28, 24)
FLAT_RECT = (3978, 680, 28, 24)  # Center of already frozen black-background384.
HALO = 4
F = np.float32
PITCH = F(np.sqrt(F(8)))  # Same-phase diagonal step (2,-2), native pixels.
PHASES = {"G1": (1, 0), "G2": (0, 1)}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def variance(signal, gain, read_e):
    return F(read_e * gain) ** F(2) + gain * np.maximum(signal, F(0))


def views(patch):
    assert patch.shape == (32, 36) and patch.dtype == np.float32
    center = patch[4:28, 4:32]
    # Source pull offsets in original native coordinates, never interpolated.
    return np.stack((patch[6:30, 2:30], center, patch[2:26, 6:34]), axis=-1)


def masks(phase):
    y, x = np.indices((24, 28))
    dx, dy = PHASES[phase]
    use = (x % 2 == dx) & (y % 2 == dy) & (np.abs(x - y + 1) <= 10)
    # Along-shaft cuts frozen from visual orientation, not measured intensities.
    return use & (x+y >= 14) & (x+y <= 22), use & (x+y >= 26) & (x+y <= 34)


def fit(source, target, phase, gain, read_e):
    train, held = masks(phase)
    a = views(source)
    b = target[4:28, 4:32]
    x, y = a[train], b[train]
    v = variance(x[:, 1], gain, read_e)
    w = F(1) / v
    w = w / w.sum(dtype=np.float32)
    mean = (x * w[:, None]).sum(axis=0, dtype=np.float32)
    ym = (y * w).sum(dtype=np.float32)
    xc, yc = x - mean, y - ym
    source_sd = F(np.sqrt((w * xc[:, 1] ** F(2)).sum(dtype=np.float32)))
    sigma = F(np.sqrt(v.mean(dtype=np.float32)))
    result = {"phase": phase, "train_sites": int(train.sum()), "held_sites": int(held.sum()),
              "source_sd_dn": float(source_sd), "injected_sensor_reference_sigma_dn": float(sigma)}
    if min(int(train.sum()), int(held.sum())) < 16 or source_sd < F(4) * sigma:
        return dict(result, status="REFUSED_SOURCE_SUPPORT"), None
    norms = np.sqrt((w[:, None] * xc ** F(2)).sum(axis=0, dtype=np.float32))
    normalized = xc / np.maximum(norms, F(1e-8))
    gram = normalized.T @ (w[:, None] * normalized)
    singular = np.linalg.svd(gram, compute_uv=False)
    condition = F(singular[0] / max(singular[-1], F(1e-12)))
    result["normalized_design_condition"] = float(condition)
    if condition > F(1e6):
        return dict(result, status="REFUSED_RANK"), None
    # Exhaust the seven active subsets of three nonnegative taps. This is the
    # exact small NNLS active-set problem, not a sweep of kernel families.
    best = None
    subsets = [(1,), (0,), (2,), (0, 1), (1, 2), (0, 2), (0, 1, 2)]
    for subset in subsets:
        xx = xc[:, subset]
        h = xx.T @ (w[:, None] * xx)
        rhs = xx.T @ (w * yc)
        try:
            weights = np.linalg.solve(h, rhs).astype(np.float32)
        except np.linalg.LinAlgError:
            continue
        if np.any(weights < F(-1e-6)):
            continue
        weights = np.maximum(weights, F(0))
        taps = np.zeros(3, np.float32)
        taps[list(subset)] = weights
        amplitude = taps.sum(dtype=np.float32)
        if not F(.5) <= amplitude <= F(1.5):
            continue
        offset = F(ym - mean @ taps)
        residual = y - (x @ taps + offset)
        loss = F((w * residual ** F(2)).sum(dtype=np.float32))
        if best is None or loss < best[0]:
            best = (loss, taps, offset)
    if best is None:
        return dict(result, status="REFUSED_POSITIVE_FAMILY"), None
    loss, taps, offset = best
    prediction = a @ taps + offset
    residual = b - prediction
    held_rmse = F(np.sqrt(np.mean(residual[held] ** F(2), dtype=np.float32)))
    held_sigma = F(np.sqrt(np.mean(variance(a[held, 1], gain, read_e), dtype=np.float32)))
    amplitude = taps.sum(dtype=np.float32)
    kernel = taps / amplitude
    centroid = F(PITCH * (kernel[2] - kernel[0]))
    second = F(PITCH * PITCH * (kernel[0] + kernel[2]) - centroid * centroid)
    result.update(taps_with_gain=taps.tolist(), normalized_taps=kernel.tolist(),
                  gain=float(amplitude), offset_dn=float(offset),
                  pull_centroid_native_px=float(centroid),
                  sampled_kernel_spread_native_px=float(np.sqrt(max(second, F(0)))),
                  train_rmse_dn=float(np.sqrt(loss)), held_rmse_dn=float(held_rmse),
                  held_rmse_over_source_sd=float(held_rmse / source_sd),
                  held_rmse_over_injected_sensor_reference_sigma=float(held_rmse / held_sigma),
                  held_signed_mean_dn=float(residual[held].mean(dtype=np.float32)))
    # Descriptive source-noise budget, not a calibrated merged-noise likelihood:
    # source and final merge share samples and have unknown covariance here.
    supported = held_rmse <= F(.10) * source_sd and held_rmse <= F(3) * F(np.sqrt(F(2))) * held_sigma
    result["status"] = "SUPPORTED_LOCAL_TRANSFER" if supported else "REFUSED_HELD_TRANSFER"
    return result, prediction.astype(np.float32)


def observed(clean):
    return np.maximum(np.rint(clean + F(512)).clip(0, 16383).astype(np.uint16).astype(np.float32) - F(512), F(0))


def controls(gain, read_e):
    yy, xx = np.indices((32, 36), dtype=np.float32)
    xx, yy = xx-F(4), yy-F(4)
    normal, shaft = (xx-yy+F(1))/F(np.sqrt(F(2))), (xx+yy)/F(np.sqrt(F(2)))
    def scene(delta=F(0), width=F(3)):
        return F(100) + F(350)*F(3)/width*np.exp(-F(.5)*((normal+delta)/width)**F(2))*(F(1)+F(.12)*np.sin(shaft/F(7)))
    original = observed(scene())
    rng = np.random.default_rng(26027)
    flat = observed(np.full((32,36), F(600)) + rng.standard_normal((32,36), dtype=np.float32)*np.sqrt(variance(F(600),gain,read_e)))
    flat_b = observed(np.full((32,36), F(600)) + rng.standard_normal((32,36), dtype=np.float32)*np.sqrt(variance(F(600),gain,read_e)))
    flat_results = [fit(flat, flat_b, phase, gain, read_e)[0] for phase in PHASES]
    assert all(r["status"] == "REFUSED_SOURCE_SUPPORT" for r in flat_results), "flat destroyer did not refuse"
    cases = {"identity": original, "analytic_normal_shift_0.5": observed(scene(F(.5))),
             "analytic_gaussian_added_sigma1": observed(scene(width=F(np.sqrt(F(10)))))}
    # Fixed sharpening placebo: same noise-realization/source, signed high boost.
    sharp = original.copy()
    stencil = views(original)
    sharp[4:28,4:32] += F(.5)*(stencil[:,:,1] - F(.5)*(stencil[:,:,0]+stencil[:,:,2]))
    cases["sharpness_boost_placebo"] = sharp
    rows = {name: [fit(original,target,phase,gain,read_e)[0] for phase in PHASES]
            for name,target in cases.items()}
    ok = all(r["status"] == "SUPPORTED_LOCAL_TRANSFER" and abs(r["pull_centroid_native_px"]) < .02
             and r["sampled_kernel_spread_native_px"] < .10 for r in rows["identity"])
    ok &= all(r["status"] == "SUPPORTED_LOCAL_TRANSFER" and abs(r["pull_centroid_native_px"]-.5)<.20
              for r in rows["analytic_normal_shift_0.5"])
    ok &= all(r["status"] == "SUPPORTED_LOCAL_TRANSFER" and abs(r["pull_centroid_native_px"])<.20
              and abs(r["sampled_kernel_spread_native_px"]-1)<.35 for r in rows["analytic_gaussian_added_sigma1"])
    ok &= all(r["status"] != "SUPPORTED_LOCAL_TRANSFER" or r["sampled_kernel_spread_native_px"]<.15
              for r in rows["sharpness_boost_placebo"])
    return {"flat_first": flat_results, "cases": rows, "passed": bool(ok),
            "limits": "Positive coarse three-tap family. A shifted continuous feature may acquire apparent fitted spread; this is not physical PSF variance."}


def extract(a, rectangle=RECT):
    x,y,w,h = rectangle
    return np.asarray(a[y-HALO:y+h+HALO,x-HALO:x+w+HALO], dtype=np.float32).copy()


def run(args):
    out = args.out.resolve()
    assert not out.exists() and out.is_relative_to(ROOT / "outputs")
    out.mkdir(parents=True)
    started = time.monotonic()
    sidecar = Path(str(SENSOR)+".json")
    assert sha(SENSOR) == SENSOR_SHA and sha(sidecar) == SIDECAR_SHA
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    assert metadata["contract"] == "strehl-merged-cfa-f32-v1"
    assert metadata["encoded"]["tiff_sha256"] == SENSOR_SHA
    assert metadata["geometry"] == {"full_quad_width":3516,"full_quad_height":2344,"crop_quad":[34,23,3448,2298]}
    assert metadata["mosaic_origin_in_reference_active_pixels"] == [68,46]
    assert metadata["plane_order"] == ["R","G1","G2","B"]
    assert metadata["binary"]["sha256"] == EXE_SHA
    assert metadata["environment"].get("STREHL_FIX_CA") == "off"
    assert metadata["process"]["full_resolution_gather"] and metadata["process"]["alignment_anchor_index"] == 149
    assert not metadata["process"]["restoration_applied"] and not metadata["process"]["photometric_correction_applied"]
    assert sha(BASE/"alignment.txt") == MAP_SHA and sha(BASE/"input-order.json") == ORDER_SHA
    order = json.loads((BASE/"input-order.json").read_text(encoding="utf-8"))
    assert len(metadata["sources"]) == len(order) == 299
    assert all(a["sha256"] == b["sha256"] and a["bytes"] == b["bytes"] for a,b in zip(metadata["sources"],order))
    assert any(a["sha256"] == MAP_SHA for a in metadata["auxiliary_files"])
    # Read the actual injected model from the observer receipt; no private fit.
    noise = metadata["process"]["noise_model"]
    gains = re.findall(r"gain_dn_per_e: ([0-9.eE+-]+)", noise)
    reads = re.findall(r"read_noise_e: ([0-9.eE+-]+)", noise)
    assert len(gains) == len(reads) == 4 and len(set(gains)) == len(set(reads)) == 1
    gain, read_e = F(gains[0]), F(reads[0])
    assert abs(float(gain)-100/436.8)<1e-6 and abs(float(read_e)-4.2)<1e-6
    commission = controls(gain, read_e)
    save(out/"controls.json",commission)
    assert commission["passed"], "fixed generated controls failed; no photographic pixels read"
    nomination_path = HERE/"feature-nomination.json"
    assert sha(nomination_path) == NOMINATION_SHA
    nomination = json.loads(nomination_path.read_text(encoding="utf-8"))
    assert nomination["feature"]["delivered_master_support_xywh"] == list(RECT)
    capture_path = Path(nomination["gauge"]["capture_receipt_path"])
    assert sha(capture_path) == CAPTURE_SHA
    arrays, bindings, mapped = {}, [], {}
    for name, key in (("original","original_u16"),("gathered","actual_gather_u16")):
        record = nomination["gauge"][key]
        path = Path(record["path"])
        assert sha(path) == record["sha256"]
        mapped[name] = np.memmap(path, mode="r", dtype="<u2", shape=(4596,6896))
        bindings.append({"path":str(path),"sha256":record["sha256"]})
    assert sha(COMPANION) == COMPANION_SHA and sha(DECODE) == DECODE_SHA
    companion = json.loads(COMPANION.read_text(encoding="utf-8"))
    independent = json.loads(DECODE.read_text(encoding="utf-8"))
    assert companion["status"] == "SOURCE143_ACTUAL_CA_OFF_GATHER_CAPTURED_NO_QUALITY_CLAIM"
    assert companion["source"]["index_zero_based"] == 143
    assert companion["source"]["sha256"] == order[143]["sha256"]
    assert companion["map"]["sha256"] == MAP_SHA and companion["map"]["reference"] == 149
    assert companion["input_order_sha256"] == ORDER_SHA
    assert companion["ca_disabled_explicitly"] and companion["resolved_ca_profile_none"]
    assert companion["original_map_order_unchanged"]
    assert independent["source"]["sha256"] == companion["source"]["sha256"]
    assert independent["native_original"]["sha256"] == companion["original"]["sha256"]
    assert all(row["different"] == 0 for row in independent["phases"].values())
    record = companion["gathered"]
    assert record["native_crop_xywh"] == [68,46,6896,4596]
    assert record["coordinate_gauge"] == "reference149 active sensor after the actual source143 production pull"
    assert sha(record["path"]) == record["sha256"]
    mapped["gathered143"] = np.memmap(record["path"],mode="r",dtype="<u2",shape=(4596,6896))
    bindings.append({"path":record["path"],"sha256":record["sha256"]})
    bindings.append({"path":str(COMPANION),"sha256":COMPANION_SHA})
    bindings.append({"path":str(DECODE),"sha256":DECODE_SHA})
    with tifffile.TiffFile(SENSOR) as tiff:
        page = tiff.pages[0]
        assert page.shape == (4596,6896) and page.dtype == np.dtype("float32")
        assert int(page.tags[262].value) == 32803
    sensor = tifffile.memmap(SENSOR, mode="r")
    # Inspect the fixed actual background before reading subject-support pixels.
    flat_arrays = {name:np.maximum(extract(a,FLAT_RECT)-F(512),F(0)) for name,a in mapped.items()}
    flat_target = extract(sensor,FLAT_RECT)
    flat_results = {name:[fit(a,flat_target,phase,gain,read_e)[0] for phase in PHASES]
                    for name,a in flat_arrays.items()}
    save(out/"actual-flat-first.json",{"rect_master_xywh":FLAT_RECT,"rows":flat_results,
                                      "scope":"Frozen background fixture; no source-noise estimate fitted."})
    assert all(r["status"] != "SUPPORTED_LOCAL_TRANSFER" for rows in flat_results.values() for r in rows), "actual flat admitted a transfer"
    raw_cuts = {name:extract(a) for name,a in mapped.items()}
    arrays.update({name:np.maximum(a-F(512),F(0)) for name,a in raw_cuts.items()})
    arrays["sensor_ca_off_signed"] = extract(sensor)
    assert all(np.isfinite(a).all() for a in arrays.values())
    rows, predictions = {}, {}
    # Whole halo green identity is a real production-gather null, not a port.
    yy,xx = np.indices((32,36))
    green = (xx+yy)%2 == 1
    assert np.array_equal(raw_cuts["original"][green],raw_cuts["gathered"][green])
    for phase in PHASES:
        null, _ = fit(arrays["original"], arrays["gathered"], phase, gain, read_e)
        rows[phase] = {"actual_gather149_null":null,"references":{}}
        for reference in ("gathered143","gathered"):
            result, prediction = fit(arrays[reference],arrays["sensor_ca_off_signed"],phase,gain,read_e)
            # Fixed wrong-position foil shifts actual target by eight native columns.
            destroyer = np.roll(arrays["sensor_ca_off_signed"],8,axis=1)
            foil, _ = fit(arrays[reference],destroyer,phase,gain,read_e)
            label = "source143" if reference == "gathered143" else "source149"
            rows[phase]["references"][label] = {"final_ca_off":result,"actual_shift8_destroyer":foil}
            if prediction is not None:
                predictions[phase+"_"+label+"_prediction"] = prediction
    live_foil = all(r["actual_shift8_destroyer"]["status"] != "SUPPORTED_LOCAL_TRANSFER"
                    for phases in rows.values() for r in phases["references"].values())
    np.savez(out/"complete-support-arrays.npz", **arrays, **predictions)
    result = {"status":"OBSERVATION_ONLY" if live_foil else "INSTRUMENT_FAILED_ACTUAL_DESTROYER",
              "arm":"complete299 CA-off; fixed actual gathered143 and149 green references, neither selected by fit",
              "sensor_sha256":SENSOR_SHA,"sidecar_sha256":SIDECAR_SHA,
              "nomination_sha256":NOMINATION_SHA,"script_sha256":sha(__file__),"bindings":bindings,
              "noise_model_exact":noise,"gain_dn_per_e":float(gain),"read_noise_e":float(read_e),
              "rect_master_xywh":list(RECT),"halo":HALO,"rows":rows,
              "signed_sensor_negative_samples":int((arrays["sensor_ca_off_signed"]<0).sum()),
              "actual_destroyer_live":live_foil,"seconds":time.monotonic()-started,
              "limits":["One visually frozen bristle; held along-shaft samples, no independent held feature or field.",
                        "143 and149 are both fixed references; neither is assumed the latent sharp truth or chosen by outcome.",
                        "Positive three-tap sampled-image family; centroid/spread do not identify physical PSF or placement.",
                        "Read the analytic pure-shift control spread alongside every photographic spread; sampling shift and fitted spread are coupled.",
                        "G1/G2 are separate phase fits, not independent statistical replicates to pool.",
                        "Gain and offset reported; a better fit does not establish preserved detail or quality.",
                        "Injected sensor-noise budget is descriptive, not propagated through143 resampling or fitted to merged noise; covariance is unknown.",
                        "Raw originals not opened; retained original u16, actual product gather and final f32 CFA only."]}
    assert sha(SENSOR) == SENSOR_SHA and sha(sidecar) == SIDECAR_SHA
    assert all(sha(row["path"]) == row["sha256"] for row in bindings)
    result["bound_inputs_unchanged"] = True
    save(out/"result.json",result)
    print(result["status"],json.dumps(rows),flush=True)
    return 0 if live_foil else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
