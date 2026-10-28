"""Root-only accounting of retained merged-CFA highlight support; no RAW decoding."""
from pathlib import Path
import hashlib
import json
import sys
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "outputs/raw-quality-2026-10-26/weevil-107-sensor-ca-off/sensor-master.tiff"
SIDECAR = SOURCE.with_suffix(".tiff.json")
MANIFEST = ROOT / "experiments/raw-quality-2026-10-26/photo-review/baseline-witnesses.json"
DEMOSAIC = ROOT / "crates/strehl-core/src/demosaic.rs"
OUT = ROOT / "outputs/raw-quality-2026-10-26/highlight-location-1"
EXPECTED = "fa5825b834121b28547fc6e2154623740a24acc4e1616915c1c197bc90be2b02"
SIDE_SHA = "e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21"
OFFSETS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1),
           (-2, 0), (2, 0), (0, -2), (0, 2),
           (-1, -1), (1, -1), (-1, 1), (1, 1))
PHASES = ("R", "G1", "G2", "B")
PALETTE = np.array(((255, 60, 60), (40, 255, 40), (40, 255, 255), (70, 90, 255)), dtype=np.uint8)
REGIONS = (("bright-wing-rim", 4050, 1810, 384), ("upper-occlusion", 3850, 1300, 384))


def binding(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1 << 20):
            h.update(block)
    stat = path.stat()
    return dict(path=str(path), bytes=stat.st_size, sha256=h.hexdigest(), mtime_ns=stat.st_mtime_ns)


def support(expanded):
    h, w = expanded.shape
    assert h >= 5 and w >= 5 and expanded.dtype == np.bool_
    result = np.zeros((h - 4, w - 4), dtype=np.bool_)
    for dx, dy in OFFSETS:
        result |= expanded[2 + dy:h - 2 + dy, 2 + dx:w - 2 + dx]
    return result


def controls():
    a = np.zeros((13, 13), dtype=np.float32)
    assert not support(a > 10).any()
    a[6, 6] = 10
    assert not support(a > 10).any()
    a[6, 6] = 11
    observed = support(a > 10)
    expected = np.zeros((9, 9), dtype=np.bool_)
    for dx, dy in OFFSETS:
        expected[4 - dy, 4 - dx] = True
    assert np.array_equal(observed, expected) and observed.sum() == 13
    shifted = np.zeros_like(a)
    shifted[6, 7] = 11
    assert not np.array_equal(support(shifted > 10), expected)
    phase = np.indices((2, 2))
    assert ((phase[0] % 2) * 2 + phase[1] % 2).tolist() == [[0, 1], [2, 3]]
    return dict(flat=True, strict_threshold=True, exact_impulse_support=True,
                shifted_foil_refused=True, phase_labels=True)


def save_map(path, values):
    Image.fromarray(values).save(path)
    with Image.open(path) as readback:
        assert np.array_equal(np.asarray(readback), values)
    return binding(path)


def main():
    start = time.monotonic()
    checked = controls()
    assert not OUT.exists()
    paths = (SOURCE, SIDECAR, MANIFEST, DEMOSAIC, Path(__file__).resolve())
    before = [binding(p) for p in paths]
    assert before[0]["sha256"] == EXPECTED and before[1]["sha256"] == SIDE_SHA
    meta = json.loads(SIDECAR.read_text())
    encoded = meta["encoded"]
    assert meta["contract"] == "strehl-merged-cfa-f32-v1"
    assert meta["cfa_pattern"] == [["R", "G1"], ["G2", "B"]]
    assert [encoded["width"], encoded["height"], encoded["payload_offset"], encoded["payload_bytes"]] == [6896, 4596, 292, 126776064]
    assert before[0]["bytes"] == 292 + 126776064
    witnesses = {r["name"]: r["rect_xywh"] for r in json.loads(MANIFEST.read_text())["witnesses"]}
    for name, x, y, size in REGIONS:
        assert witnesses[name] == [x, y, size, size]
    cfa = np.memmap(SOURCE, mode="r", dtype="<f4", offset=292, shape=(4596, 6896))
    OUT.mkdir()
    results = []
    for name, x, y, size in REGIONS:
        assert x % 2 == y % 2 == 0 and x >= 2 and y >= 2 and x + size + 2 <= 6896 and y + size + 2 <= 4596
        expanded = np.array(cfa[y - 2:y + size + 2, x - 2:x + size + 2], copy=True)
        assert np.isfinite(expanded).all()
        core = expanded[2:-2, 2:-2]
        phase = np.indices(core.shape)
        phase = (phase[0] % 2) * 2 + phase[1] % 2
        rows = []
        for label, threshold in (("working-white", 14848.0), ("nominal-container", 15871.0)):
            detected = expanded > np.float32(threshold)
            sites = detected[2:-2, 2:-2]
            affected = support(detected)
            colored = np.zeros((size, size, 3), dtype=np.uint8)
            colored[sites] = PALETTE[phase[sites]]
            rows.append(dict(label=label, threshold_dn=threshold, comparison="strictly greater than",
                             core_counts={p: int(np.count_nonzero(sites & (phase == i))) for i, p in enumerate(PHASES)},
                             expanded_count=int(detected.sum()), possible_rgb_dependency_sites=int(affected.sum()),
                             phase_map=save_map(OUT / f"{name}-{label}-phase.png", colored),
                             dependency_map=save_map(OUT / f"{name}-{label}-mhc-support.png", affected.astype(np.uint8) * 255)))
        results.append(dict(name=name, delivered_xywh=[x, y, size, size], active149_xywh=[x + 68, y + 46, size, size],
                            expanded_xywh=[x - 2, y - 2, size + 4, size + 4],
                            phase_maximum_dn={p: float(core[phase == i].max()) for i, p in enumerate(PHASES)}, thresholds=rows))
    del cfa
    assert [binding(p) for p in paths] == before
    result = dict(status="LOCATION_OBSERVATION_COMPLETE", quality_claim=False, controls=checked, command=sys.argv,
                  concurrent_work="Root green-phase complete299 trial; timing is operational only.",
                  inputs=before, original_raw_reads=0, input_files_unchanged=True,
                  support="Union of final MHC RGB nonzero taps: center, axial distances1/2, diagonal distance1. Dependency only, no causal or contribution-magnitude claim.",
                  offsets_dxdy=OFFSETS, palette=dict(zip(PHASES, PALETTE.tolist())), regions=results,
                  seconds=time.monotonic() - start)
    with (OUT / "result.json").open("x", encoding="utf-8", newline="\n") as out:
        json.dump(result, out, indent=2, allow_nan=False)
        out.write("\n")
    print(json.dumps({"status": result["status"], "seconds": result["seconds"], "regions": [dict(name=r["name"], phase_maximum_dn=r["phase_maximum_dn"], thresholds=[{k: t[k] for k in ("label", "expanded_count", "possible_rgb_dependency_sites")} for t in r["thresholds"]]) for r in results]}))


if __name__ == "__main__":
    main()
