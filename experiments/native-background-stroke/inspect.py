"""Fixed five-frame source diagnosis. Root runs bounded children; no launch on import."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCT = ROOT / "experiments/native-product-comparison"
INDICES = (0, 26, 52, 78, 104)
RAW_ROI = (112, 1304, 640, 456)
TIFF_ROI = (64, 1240, 768, 576)
RECTS = {"stroke": (274, 1572, 320, 120), "clean": (274, 1382, 320, 120)}
CONTEXT = (274, 1382, 320, 310)
MAP = ROOT / "experiments/M-PHASE0-PHASE/out/canon/coffee-bean.warpmap.txt"
MAP_SHA = "b21b247944c257ab0fd3c767c879b9abf4a5fb1112dded97c87990a7d537274c"
SECONDARY = ROOT / "experiments/m61-ptc-high-iso/decode-check/target/release/m61-decode-check.exe"
SECONDARY_SOURCE = ROOT / "experiments/m61-ptc-high-iso/decode-check/src/main.rs"
PHASES = {"G1": (1, 0), "G2": (0, 1)}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


sampler = module("background_sampler", HERE / "sampler.py")


def binding(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": h.hexdigest()}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def array_save(path, array):
    with Path(path).open("xb") as stream:
        np.save(stream, array, allow_pickle=False)
    return binding(path)


def source_bindings():
    return [binding(p) for p in (Path(__file__), HERE / "sampler.py", HERE / "independent-controls.py",
            sampler.CLIB_PATH, HERE / "charter.md", HERE / "design.md", PRODUCT / "next-rois.json", MAP,
            PRODUCT / "run-1/plan.json", SECONDARY, SECONDARY_SOURCE)]


def fixed():
    rois = read(PRODUCT / "next-rois.json")
    assert rois["stroke"] == [150, 1490, 320, 120] and rois["nearby_clean"] == [150, 1300, 320, 120]
    assert rois["crop_origin_native"] == [124, 82] and rois["crop_origin_quad"] == [62, 41]
    assert rois["maximum_initial_original_raw_files"] == 5
    assert binding(MAP)["sha256"] == MAP_SHA
    warp = sampler.clib.parse_warpmap(str(MAP))
    assert warp["frames"] == warp["placed_count"] == 105 and warp["plane"] == (3516, 2344)
    assert warp["reference_index"] == 52 and not warp["refusals"]
    return {i: warp["placements"][i] for i in INDICES}


def input_path(index, suffix):
    assert index in INDICES
    folder = "D:/personal/macro/coffee-bean" if suffix == ".ARW" else "D:/edited/macro/coffee-bean"
    path = Path(folder) / f"DSC{index + 16:05}{suffix}"
    records = read(PRODUCT / "run-1/plan.json")["inputs"]
    record = next(v for v in records if str(Path(v["path"]).resolve()).casefold() == str(path.resolve()).casefold())
    stat = path.stat()
    assert stat.st_size == record["bytes"] and stat.st_mtime_ns == record["mtime_ns"], "original metadata changed"
    return path, record


def controls(out):
    transforms = fixed()
    independent = module("background_independent_controls", HERE / "independent-controls.py")
    result = independent.run(sampler, transforms)
    assert result["status"] == "PASS", "independent controls did not pass"
    save(out / "controls.json", {"sources": source_bindings(), "result": result})


def primary(index, out):
    import rawpy
    import tifffile
    fixed()
    control = read(out / "controls/controls.json")
    assert control["result"]["status"] == "PASS" and control["sources"] == source_bindings()
    path, original = input_path(index, ".ARW")
    x, y, w, h = RAW_ROI
    with rawpy.imread(str(path)) as raw:
        # This MUST remain inside the context: LibRaw owns the uncopied view.
        patch = raw.raw_image_visible[y:y+h, x:x+w].copy()
        pattern = raw.raw_pattern.copy().tolist()
        description = bytes(raw.color_desc).decode("ascii").rstrip("\0")
        assert pattern == [[0, 1], [3, 2]] and description == "RGBG", "unexpected CFA phase convention"
        meta = {"visible_shape": list(raw.raw_image_visible.shape), "raw_pattern": pattern,
                "color_desc": description, "black_level_per_channel": list(raw.black_level_per_channel),
                "white_level": raw.white_level, "camera_whitebalance": list(raw.camera_whitebalance),
                "exposure_time_seconds": None, "iso": None, "aperture": None,
                "exposure_metadata": "unavailable in allocated rawpy interface; no new EXIF read",
                "sizes": {k: int(getattr(raw.sizes, k)) for k in
                    ("raw_height", "raw_width", "height", "width", "top_margin", "left_margin")}}
    assert patch.shape == (h, w) and patch.dtype == np.uint16
    raw_array = array_save(out / f"raw-{index}.npy", patch)
    export, export_original = input_path(index, ".tif")
    tx, ty, tw, th = TIFF_ROI
    mapped = tifffile.memmap(export)
    assert mapped.shape == (4672, 7008, 3) and mapped.dtype == np.float32
    tiff_patch = np.array(mapped[ty:ty+th, tx:tx+tw], dtype=np.float32, copy=True)
    del mapped
    assert tiff_patch.shape == (th, tw, 3) and np.isfinite(tiff_patch).all()
    tiff_array = array_save(out / f"tiff-{index}.npy", tiff_patch)
    input_path(index, ".ARW")
    input_path(index, ".tif")
    save(out / f"primary-{index}.json", {"index": index, "sources": source_bindings(),
        "raw_input": binding(path), "original_metadata": original, "raw_roi_xywh": RAW_ROI,
        "raw": raw_array, "decoder": {"name": "rawpy/LibRaw", "rawpy": rawpy.__version__,
            "libraw": list(rawpy.libraw_version), **meta},
        "tiff_original_metadata": export_original, "tiff_roi_xywh": TIFF_ROI, "tiff": tiff_array,
        "tiff_interpretation": "unregistered supplementary Linear Rec.2020 Lightroom ROI; no RAW pixel equivalence"})


def array_hash(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def checked_inputs(out, secondary):
    rows = []
    sources = source_bindings()
    for index in INDICES:
        receipt = read(out / f"primary-{index}.json")
        assert receipt["sources"] == sources and receipt["index"] == index
        path, _ = input_path(index, ".ARW")
        assert binding(path) == receipt["raw_input"], "RAW changed after primary decode"
        assert binding(out / f"raw-{index}.npy") == receipt["raw"]
        patch = np.load(out / f"raw-{index}.npy", allow_pickle=False)
        assert patch.dtype == np.uint16 and patch.shape == (456, 640)
        other_path = secondary / f"rawler-frame-{index}.bin"
        blob = other_path.read_bytes()
        assert len(blob) == 16 + patch.size * 2 and struct.unpack("<4I", blob[:16]) == (1304, 112, 456, 640)
        other = np.frombuffer(blob, dtype="<u2", offset=16).reshape(patch.shape)
        delta = patch.astype(np.int32) - other.astype(np.int32)
        comparison = {"index": index, "primary": receipt["raw"], "secondary": binding(other_path),
            "different_sensels": int(np.count_nonzero(delta)), "max_abs_dn": int(np.abs(delta).max()),
            "phases": [{"phase": [dx, dy], "values": int(patch[dy::2,dx::2].size),
                "primary_u16_sha256": array_hash(patch[dy::2,dx::2]),
                "secondary_u16_sha256": array_hash(other[dy::2,dx::2])}
                for dy in range(2) for dx in range(2)]}
        rows.append((receipt, patch, comparison))
    comparisons = [r[2] for r in rows]
    save(out / "decode-comparison.json", {"sources": sources, "rows": comparisons,
         "all_identical": all(r["different_sensels"] == 0 for r in comparisons)})
    assert all(r["different_sensels"] == 0 for r in comparisons), "independent RAW decode mismatch; no interpretation"
    return rows


def analyze(out, secondary):
    transforms = fixed()
    control = read(out / "controls/controls.json")
    assert control["result"]["status"] == "PASS" and control["sources"] == source_bindings()
    rows = checked_inputs(out, secondary)  # All five comparisons precede EVERY view/contrast.
    contrasts, views, view_files = [], {}, []
    for receipt, raw, _ in rows:
        index = receipt["index"]
        decoder = receipt["decoder"]
        signal = raw.astype(np.float32)
        for dy in range(2):
            for dx in range(2):
                signal[dy::2,dx::2] -= np.float32(decoder["black_level_per_channel"][decoder["raw_pattern"][dy][dx]])
        for gauge in ("sensor", "scene"):
            for name, phase in PHASES.items():
                view = sampler.sample(signal, RAW_ROI[:2], CONTEXT, phase, transforms[index], gauge=gauge)
                assert view.shape == (155, 160)
                views[(index, gauge, name)] = view
                view_files.append(array_save(out / f"view-{index}-{gauge}-{name}.npy", view))
                # Context starts at clean y1382; stroke starts190 native pixels later.
                clean, stroke = view[:60], view[95:155]
                cm, sm = float(np.mean(clean, dtype=np.float64)), float(np.mean(stroke, dtype=np.float64))
                contrasts.append({"index": index, "gauge": gauge, "phase": name,
                    "stroke_mean_dn": sm, "clean_mean_dn": cm, "stroke_minus_clean_dn": sm-cm,
                    "fraction_of_clean": (sm-cm)/cm if cm > 0 else None})
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # One shared linear display range, based only on the reference clean source.
    anchor = np.concatenate([views[(52, "sensor", name)][:60].ravel() for name in PHASES])
    centre = float(np.mean(anchor, dtype=np.float64))
    span = max(1.0, abs(centre) * 0.15)
    vmin, vmax = centre-span, centre+span
    charts = []
    for phase in PHASES:
        fig, axes = plt.subplots(2, 5, figsize=(15, 7), squeeze=False)
        for row, gauge in enumerate(("sensor", "scene")):
            for col, index in enumerate(INDICES):
                ax = axes[row, col]
                ax.imshow(views[(index,gauge,phase)], cmap="gray", vmin=vmin, vmax=vmax, interpolation="nearest")
                ax.axhline(59.5, color="cyan", linewidth=0.4)
                ax.axhline(94.5, color="orange", linewidth=0.4)
                ax.set_title(f"{gauge} / frame {index}")
                ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f"{phase}: uncorrected source DN; same display range {vmin:.1f}..{vmax:.1f} for every panel")
        fig.text(0.02,0.02,"Upper 60 rows: frozen clean ROI. Lower 60: frozen stroke ROI. Two native pixels per sample. No cause or noise verdict.")
        fig.tight_layout(rect=(0,0.04,1,0.94))
        chart = out / f"contact-{phase}.png"
        assert not chart.exists()
        fig.savefig(chart, dpi=130)
        plt.close(fig)
        charts.append(binding(chart))
    save(out / "result.json", {"schema": "native-background-stroke-inspection-v1", "sources": source_bindings(),
        "indices": INDICES, "raw_roi_xywh": RAW_ROI, "context_reference_native_xywh": CONTEXT,
        "rectangles_reference_native": RECTS, "contrasts": contrasts, "views": view_files, "charts": charts,
        "display": {"kind": "shared linear black-subtracted DN", "vmin": vmin, "vmax": vmax,
                    "choice": "reference52 sensor clean two-green mean +/-15%; no per-panel fit",
                    "clipping_counts": [{"index": key[0], "gauge": key[1], "phase": key[2],
                        "below": int(np.count_nonzero(v < vmin)), "above": int(np.count_nonzero(v > vmax)),
                        "values": int(v.size)} for key, v in views.items()]},
        "interpretation": "DESCRIPTIVE_ONLY: independent decode identical; five observations cannot establish dust or manufactured fusion damage. Inspect 2D endpoints; horizontal stationarity can be ambiguous.",
        "spatial_sd_is_not_temporal_noise": True, "new_alignment": False})
    assert sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) <= 64 << 20, "retained diagnostic output limit"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("controls", "primary", "analyze"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--index", type=int, choices=INDICES)
    parser.add_argument("--secondary", type=Path)
    args = parser.parse_args()
    assert args.out.is_dir(), "root creates the fresh diagnostic directory"
    if args.stage == "controls":
        controls(args.out)
    elif args.stage == "primary":
        assert args.index is not None
        primary(args.index, args.out)
    else:
        assert args.secondary is not None and args.secondary.is_dir()
        analyze(args.out, args.secondary)


if __name__ == "__main__":
    main()
